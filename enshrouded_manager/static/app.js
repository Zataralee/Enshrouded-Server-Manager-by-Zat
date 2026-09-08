const app = document.querySelector("#app");
const login = document.querySelector("#login");
let state = {};
let serverConfig = {};
let managerFormDirty = false;
let serverConfigDirty = false;
let accountsDirty = false;
let updateActionDirty = false;
let newInstallDirty = false;
let newInstallDirectoryDirty = false;
let inviteFormDirty = false;
let inviteProfilesDirty = false;
let userListDirty = false;
let backupScheduleDirty = false;
let webhookDirty = false;
let editingWebhookId = "";
let webhookInstanceId = "";
let installPoll = null;
let autoRefreshPoll = null;
let activeInstanceId = localStorage.getItem("esm_active_instance_id") || "";
let discoveredSaves = [];
let uploadedSaveFiles = [];
let uploadedSaveWorlds = [];
const permissions = ["setup", "control", "settings", "accounts", "logs", "saves", "backups"];

function selectedInstance() {
  return state.selected_instance || {};
}

function selectedInstanceId() {
  return activeInstanceId || selectedInstance().id;
}

function currentUser() {
  return (state.manager || {}).current_user || {};
}

function isAdmin() {
  return currentUser().role === "admin";
}

function can(permission) {
  return isAdmin() || (currentUser().permissions || []).includes(permission);
}

function canManageInvites() {
  return isAdmin() || currentUser().role === "server_owner";
}

function canViewUsers() {
  return isAdmin() || currentUser().role === "server_owner";
}

function inviteTypeLabel(type) {
  return ({ basic_user: "Basic User", server_manager: "Server Manager", server_owner: "Server Owner" })[type] || type;
}

function inviteUrl(code) {
  const url = new URL(location.href);
  url.search = "";
  url.hash = "";
  url.searchParams.set("invite", code);
  return url.toString();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

async function copyText(text, label) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
  } else {
    const input = document.createElement("textarea");
    input.value = text;
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.appendChild(input);
    input.select();
    document.execCommand("copy");
    input.remove();
  }
  toast(`${label} copied`);
}

function inviteActions(invite) {
  if (!invite || !invite.code) return "";
  return `
    <div class="inline wide">
      <button type="button" data-copy-text="${invite.code}" data-copy-label="Invite code">Copy code</button>
      <span>OR</span>
      <button type="button" data-copy-text="${inviteUrl(invite.code)}" data-copy-label="Invite URL">Copy Invite URL</button>
    </div>
  `;
}

function inviteNotes(invite) {
  const title = (invite.title || "").trim();
  const description = (invite.description || "").trim();
  if (!title && !description) return "";
  return `
    ${title ? `<small><strong>Title:</strong> ${escapeHtml(title)}</small>` : ""}
    ${description ? `<small class="invite-description"><strong>Description:</strong> ${escapeHtml(description)}</small>` : ""}
  `;
}

function ensureInviteMetadataFields() {
  const form = document.querySelector("#inviteForm");
  if (!form || form.querySelector("[name=title]")) return;
  const codeType = form.querySelector("[name=code_type]")?.closest("label");
  if (!codeType) return;
  codeType.insertAdjacentHTML("afterend", `
    <label>Title <input name="title" placeholder="Optional"></label>
    <label class="wide-field">Description <textarea name="description" class="short-textarea" maxlength="240" placeholder="Optional short note"></textarea></label>
  `);
}

function parseInviteDuration(value) {
  const match = String(value || "").trim().replace(/\s+/g, "").match(/^(\d{1,3})\/(\d{1,2})\/(\d{1,2})$/);
  if (!match) throw new Error("Use duration format dd/hh/mm, for example 01/00/00");
  const days = Number(match[1]);
  const hours = Number(match[2]);
  const minutes = Number(match[3]);
  if (hours > 23 || minutes > 59) throw new Error("Duration hours must be 0-23 and minutes must be 0-59");
  const total = (days * 24 * 60) + (hours * 60) + minutes;
  if (total < 1) throw new Error("Invite duration must be at least one minute");
  return total;
}

function renderLatestInvite(invite) {
  const target = document.querySelector("#latestInvite");
  if (!invite || !invite.code) {
    target.classList.add("hidden");
    target.innerHTML = "";
    delete target.dataset.locked;
    return;
  }
  target.classList.remove("hidden");
  target.dataset.locked = "true";
  target.innerHTML = `
    <strong>Generated invite code</strong>
    ${inviteNotes(invite)}
    <code>${invite.code}</code>
    <small>Copy code OR copy URL.</small>
    ${inviteActions(invite)}
  `;
}

function toast(message) {
  const el = document.querySelector("#toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: options.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function field(label, key, value, type = "text") {
  return `<label>${label}<input name="${key}" type="${type}" value="${String(value ?? "").replaceAll('"', "&quot;")}"></label>`;
}

function boolField(label, key, value) {
  return `<label class="check"><input name="${key}" type="checkbox" ${value ? "checked" : ""}> ${label}</label>`;
}

function formHasFocus(selector) {
  const el = document.querySelector(selector);
  return !!(el && document.activeElement && el.contains(document.activeElement));
}

function saveWorldId(filename) {
  const name = String(filename || "").split(/[\\/]/).pop();
  const match = name.match(/^([0-9a-fA-F]{8,16})(?:$|[-_].*)/);
  return match ? match[1].toLowerCase() : "";
}

function fileRelativePath(file) {
  return file.webkitRelativePath || file.name;
}

function formatBytes(size) {
  const value = Number(size || 0);
  if (value > 1024 * 1024) return `${Math.round(value / 1024 / 1024)} MB`;
  return `${Math.max(1, Math.round(value / 1024))} KB`;
}

function groupUploadedSaveFiles(files) {
  const groups = new Map();
  const ungrouped = [];
  files.forEach(file => {
    const worldId = saveWorldId(file.name);
    if (!worldId) {
      ungrouped.push(file);
      return;
    }
    if (!groups.has(worldId)) {
      groups.set(worldId, { world_id: worldId, files: [], size: 0, modified: 0 });
    }
    const group = groups.get(worldId);
    group.files.push(file);
    group.size += file.size || 0;
    group.modified = Math.max(group.modified, file.lastModified || 0);
  });
  return [...groups.values()].map(group => ({
    ...group,
    ungrouped,
    modified_label: group.modified ? new Date(group.modified).toLocaleString() : "",
  })).sort((a, b) => b.modified - a.modified);
}

function renderUploadedWorlds() {
  const target = document.querySelector("#uploadedWorldList");
  const submit = document.querySelector("#folderImportForm button[type=submit]");
  if (!target) return;
  if (!uploadedSaveFiles.length) {
    target.innerHTML = "";
    submit.classList.add("hidden");
    return;
  }
  if (!uploadedSaveWorlds.length) {
    target.innerHTML = `<p>No Enshrouded world files were found. Choose the folder that contains files like <code>3ad85aea</code>, <code>3ad85aea-0</code>, and <code>3ad85aea-index</code>.</p>`;
    submit.classList.add("hidden");
    return;
  }
  target.innerHTML = `
    <p class="form-note">Select one world to import. The manager will install that world as the server's primary save so the dedicated server loads it on startup. Enshrouded stores local worlds as file IDs, so this ID may not match the world name you see in-game.</p>
    ${uploadedSaveWorlds.map((world, index) => `
      <label class="save-row selectable ${index === 0 ? "active" : ""}">
        <input type="radio" name="uploaded_world_id" value="${world.world_id}" ${index === 0 ? "checked" : ""}>
        <div>
          <strong>World file ID ${escapeHtml(world.world_id)}</strong>
          <small>${world.files.length} matching file(s), ${formatBytes(world.size)}, modified ${escapeHtml(world.modified_label)}</small>
          <small>${escapeHtml(world.files.slice(0, 5).map(file => file.name).join(", "))}${world.files.length > 5 ? "..." : ""}</small>
        </div>
      </label>
    `).join("")}
  `;
  submit.classList.remove("hidden");
}

function renderStatus() {
  const s = state.server || {};
  const inst = selectedInstance();
  const select = document.querySelector("#instanceSelect");
  if (document.activeElement !== select) {
    select.innerHTML = (state.instances || []).map(item => `<option value="${item.id}">${item.name}</option>`).join("");
    if (inst.id) select.value = inst.id;
  }
  document.querySelector("#stateDot").classList.toggle("running", !!s.running);
  document.querySelector("#stateText").textContent = inst.name ? `${inst.name}: ${s.running ? "Running" : "Stopped"}` : "No server configured";
  document.querySelector("#currentUserLabel").textContent = currentUser().username ? `Logged in as ${currentUser().username}` : "";
  document.querySelector("#address").textContent = `UI: http://${location.host}${inst.path ? " | " + inst.path : ""}`;
  if (!updateActionDirty) {
    document.querySelector("#updateAction").checked = !!inst.update_before_start;
  }
  document.querySelector("#serverFacts").innerHTML = `
    <dt>Install</dt><dd>${inst.path || "None configured"}</dd>
    <dt>PID</dt><dd>${s.pid || "None"}</dd>
    <dt>Started</dt><dd>${s.started_at || "Not running"}</dd>
    <dt>Last restart</dt><dd>${s.last_restarted_at || "None"}</dd>
    <dt>Last update</dt><dd>${s.last_updated_at || "None"}</dd>
    <dt>Last stopped</dt><dd>${s.last_stopped_at || "None"}</dd>
    <dt>Uptime</dt><dd>${Math.floor((s.uptime_seconds || 0) / 60)} min</dd>
    <dt>Last exit</dt><dd>${s.last_exit_code ?? "None"}</dd>
    <dt>Manager activity</dt><dd>${s.activity || "idle"}</dd>
  `;
}

function parentSectionForTab(tab) {
  const subButton = document.querySelector(`#subNav [data-tab="${tab}"]`);
  return subButton?.dataset.parentSection || "";
}

function firstVisibleSubTab(section) {
  return document.querySelector(`#subNav [data-subnav="${section}"] button:not(.hidden)`)?.dataset.tab || "";
}

function activateTab(tab, section = "") {
  const parentSection = section || parentSectionForTab(tab);
  const targetTab = tab || firstVisibleSubTab(parentSection) || "dashboard";
  document.querySelectorAll("nav button, #subNav button, .tab").forEach(el => el.classList.remove("active"));
  document.querySelectorAll("#subNav .sub-nav-group").forEach(el => el.classList.add("hidden"));
  if (parentSection) {
    document.querySelector(`nav button[data-nav-section="${parentSection}"]`)?.classList.add("active");
    document.querySelector(`#subNav [data-subnav="${parentSection}"]`)?.classList.remove("hidden");
    document.querySelector(`#subNav [data-tab="${targetTab}"]`)?.classList.add("active");
  } else {
    document.querySelector(`nav button[data-tab="${targetTab}"]`)?.classList.add("active");
  }
  document.querySelector(`#${targetTab}`)?.classList.add("active");
}

function renderAccess() {
  document.querySelectorAll("[data-admin-only]").forEach(el => el.classList.toggle("hidden", !isAdmin()));
  document.querySelectorAll("[data-invites-only]").forEach(el => el.classList.toggle("hidden", !canManageInvites()));
  document.querySelectorAll("[data-users-only]").forEach(el => el.classList.toggle("hidden", !canViewUsers()));
  document.querySelectorAll("[data-permission]").forEach(el => el.classList.toggle("hidden", !can(el.dataset.permission)));
  document.querySelector("#managerForm").classList.toggle("hidden", !isAdmin());
  document.querySelector("#newUserForm")?.classList.toggle("hidden", !isAdmin());
  const visibleActive = document.querySelector("nav button.active:not(.hidden), #subNav button.active:not(.hidden)");
  if (!visibleActive) {
    const first = document.querySelector("nav button:not(.hidden)");
    if (first?.dataset.navSection) activateTab(first.dataset.defaultTab, first.dataset.navSection);
    else if (first?.dataset.tab) activateTab(first.dataset.tab);
  }
}

function renderServerForm() {
  if (serverConfigDirty) return;
  const c = serverConfig;
  document.querySelector("#serverForm").innerHTML = `
    <h2>Basic Server Config</h2>
    ${field("Server name", "name", c.name)}
    ${field("IP bind", "ip", c.ip)}
    ${field("Query port", "queryPort", c.queryPort, "number")}
    ${field("Slots", "slotCount", c.slotCount, "number")}
    ${field("Save directory", "saveDirectory", c.saveDirectory)}
    ${field("Log directory", "logDirectory", c.logDirectory)}
    <label>Voice chat mode<select name="voiceChatMode"><option>Proximity</option><option>Global</option></select></label>
    ${boolField("Enable voice chat", "enableVoiceChat", c.enableVoiceChat)}
    ${boolField("Enable text chat", "enableTextChat", c.enableTextChat)}
    <label>Difficulty preset<select name="gameSettingsPreset"><option>Default</option><option>Relaxed</option><option>Hard</option><option>Survival</option><option>Custom</option></select></label>
    <button type="submit">Save Server Config</button>
  `;
  document.querySelector("[name=voiceChatMode]").value = c.voiceChatMode || "Proximity";
  document.querySelector("[name=gameSettingsPreset]").value = c.gameSettingsPreset || "Default";
  document.querySelector("#rawConfig").value = JSON.stringify(c, null, "\t");
}

function renderAccounts(force = false) {
  if (accountsDirty && !force) return;
  const groups = serverConfig.userGroups || [];
  document.querySelector("#groups").innerHTML = groups.map((g, i) => `
    <div class="group" data-index="${i}">
      ${field("Name", "name", g.name)}
      ${field("Password", "password", g.password)}
      ${boolField("Can kick/ban", "canKickBan", g.canKickBan)}
      ${boolField("Can access inventories", "canAccessInventories", g.canAccessInventories)}
      ${boolField("Can edit world", "canEditWorld", g.canEditWorld)}
      ${boolField("Can edit base", "canEditBase", g.canEditBase)}
      ${boolField("Can extend base", "canExtendBase", g.canExtendBase)}
      ${field("Reserved slots", "reservedSlots", g.reservedSlots || 0, "number")}
      <button class="wide" data-remove-group="${i}">Remove Group</button>
    </div>
  `).join("");
  const bans = serverConfig.bans || serverConfig.bannedAccounts || [];
  document.querySelector("#bans").innerHTML = bans.map((b, i) => `
    <div class="ban" data-index="${i}">
      ${field("Display name", "displayName", b.displayName)}
      ${field("Character name", "characterName", b.characterName)}
      ${field("Account ID hash", "accountIDHash", b.accountIDHash)}
      ${field("Ban date", "banDate", b.banDate || Math.floor(Date.now() / 1000), "number")}
      <button class="wide" data-remove-ban="${i}">Remove Ban</button>
    </div>
  `).join("");
}

function renderSchedules() {
  const schedules = selectedInstance().scheduled_restarts || [];
  document.querySelector("#scheduleList").innerHTML = schedules.map(t => `
    <span class="chip">${t}<button data-remove-schedule="${t}">x</button></span>
  `).join("");
}

function renderInstances() {
  const firstRun = document.querySelector("#firstRun");
  firstRun.classList.toggle("hidden", !((state.manager || {}).setup_required));
  document.querySelector("#instanceList").innerHTML = (state.instances || []).map(item => `
    <div class="instance-row ${item.id === selectedInstanceId() ? "active" : ""}">
      <div>
        <strong>${item.name}</strong>
        <small>${item.path}</small>
      </div>
      <span>${item.installed ? "Installed" : "Missing server files"}</span>
      <button data-select-instance="${item.id}">Use</button>
      <button data-remove-instance="${item.id}">Remove</button>
    </div>
  `).join("");
  const removed = ((state.manager || {}).removed_instances || []);
  document.querySelector("#removedInstanceList").innerHTML = removed.length ? removed.map(item => `
    <div class="instance-row">
      <div>
        <strong>${item.name}</strong>
        <small>${item.path}</small>
      </div>
      <span>Removed ${item.removed_at || ""}</span>
      <button data-restore-instance="${item.id}">Restore</button>
      <button data-delete-removed-instance="${item.id}">Delete Files</button>
    </div>
  `).join("") : "<p>No removed servers.</p>";
}

function suggestedQueryPort() {
  const used = new Set((state.instances || []).map(item => Number(item.query_port || 15637)));
  let port = 15637;
  while (used.has(port)) port += 10;
  return port;
}

function usedQueryPorts() {
  const managerPorts = ((state.manager || {}).used_query_ports || []).map(Number);
  const visiblePorts = (state.instances || []).map(item => Number(item.query_port || 15637));
  return new Set([...managerPorts, ...visiblePorts].filter(Boolean));
}

function updateInstallPortState() {
  const form = document.querySelector("#newInstallForm");
  if (!form) return true;
  const input = form.queryPort;
  const note = document.querySelector("#queryPortNote");
  const value = Number(input.value);
  const inUse = !!input.value && usedQueryPorts().has(value);
  input.classList.toggle("field-error", inUse);
  note.textContent = inUse ? "Port in use. Select a new port" : "";
  return !inUse;
}

function renderNewInstallDefaults() {
  if (newInstallDirty) return;
  const form = document.querySelector("#newInstallForm");
  form.name.value = "";
  form.folder_name.value = "";
  newInstallDirectoryDirty = false;
  form.queryPort.value = "";
  updateInstallPortState();
}

function renderInstallJobs() {
  const jobs = state.install_jobs || [];
  const panel = document.querySelector("#installStatus");
  const list = document.querySelector("#installJobList");
  const button = document.querySelector("#newInstallForm button[type=submit]");
  const running = jobs.filter(job => job.status === "running");
  const recent = jobs.slice(0, 20);
  if (!recent.length) {
    panel.classList.add("hidden");
    if (!installPoll) button.disabled = false;
    return;
  }
  const primary = running[0] || recent[0];
  panel.classList.remove("hidden", "complete", "failed");
  panel.classList.toggle("complete", primary.status === "complete");
  panel.classList.toggle("failed", primary.status === "failed");
  document.querySelector("#installStatusText").textContent = primary.status === "running" ? `Installing ${primary.instance_name || "server"}` : primary.message;
  document.querySelector("#installStatusDetail").textContent = primary.status === "running"
    ? `${primary.message}. Please wait and do not start another install for this server.`
    : (primary.status === "complete" ? "The server is ready. Use Server selects it and opens Server Config; Dismiss clears this status." : (primary.error || "Install job finished."));
  list.innerHTML = recent.map(job => `
    <div class="job-row ${job.status}">
      <strong>${job.instance_name || "Server install"}</strong>
      <span>${job.status}</span>
      <small>${job.message}${job.error ? ": " + job.error : ""}</small>
      <small>Started by ${job.owner_username || "unknown"}</small>
      <small>${job.updated_at || ""}</small>
      <div class="inline wide">
        ${job.status === "complete" && job.result && job.result.instance ? `<button data-use-installed-instance="${job.result.instance.id}" data-dismiss-job="${job.id}">Use Server</button>` : ""}
        ${job.status !== "running" ? `<button data-dismiss-job="${job.id}">Dismiss</button>` : ""}
      </div>
    </div>
  `).join("");
  button.disabled = running.length > 0;
}

function renderLogs() {
  document.querySelector("#logList").innerHTML = (state.logs || []).map(log => `
    <button data-log="${log.name}"><span>${log.name}</span><small>${Math.round(log.size / 1024)} KB</small></button>
  `).join("");
}

async function renderBackups() {
  if (!can("backups")) return;
  const data = await api(`/api/backups?instance_id=${encodeURIComponent(selectedInstanceId() || "")}`);
  document.querySelector("#backupList").innerHTML = data.backups.map(b => `
    <button><span>${b.name}</span><small>${Math.round(b.size / 1024)} KB</small></button>
  `).join("");
}

function renderDiscoveredSaves() {
  const target = document.querySelector("#localSaveList");
  if (!target || !can("saves")) return;
  target.innerHTML = discoveredSaves.length ? discoveredSaves.map(save => `
    <div class="save-row">
      <div>
        <strong>${escapeHtml(save.name)}</strong>
        <small>${escapeHtml(save.path)}</small>
        <small>${save.file_count} file(s), ${Math.round((save.size || 0) / 1024)} KB, modified ${save.modified || ""}</small>
      </div>
      <button data-import-local-save="${save.id}">Import</button>
    </div>
  `).join("") : "<p>No local saves discovered yet.</p>";
}

async function renderSaveImports() {
  if (!can("saves")) return;
  const target = document.querySelector("#saveImportHistory");
  const data = await api(`/api/savegame/imports?instance_id=${encodeURIComponent(selectedInstanceId() || "")}`);
  target.innerHTML = data.imports.length ? data.imports.map(item => `
    <div class="save-row">
      <div>
        <strong>${escapeHtml(item.source_name || "Imported save")}</strong>
        <small>${escapeHtml(item.source_path || "")}</small>
        <small>Imported ${item.imported_at || ""}${item.previous_backup ? `; previous backup ${escapeHtml(item.previous_backup)}` : ""}</small>
      </div>
    </div>
  `).join("") : "<p>No saves imported for this server yet.</p>";
}

function renderManagerForm() {
  if (managerFormDirty) return;
  const f = document.querySelector("#managerForm");
  if (!f || !isAdmin()) return;
  const m = state.manager || {};
  const inst = selectedInstance();
  const ftp = inst.ftp_backup || {};
  f.username.value = m.username || "admin";
  f.bind_host.value = m.bind_host || "127.0.0.1";
  f.port.value = m.port || 8080;
  f.allow_local_bypass.checked = !!m.allow_local_bypass;
  f.server_root.value = m.server_root || "";
  f.backup_root.value = m.backup_root || "";
  f.min_backup_interval_minutes.value = m.min_backup_interval_minutes || 15;
  f.max_backup_interval_minutes.value = m.max_backup_interval_minutes || 10080;
  f.max_servers_per_owner.value = m.max_servers_per_owner || 0;
  f.server_create_cooldown_minutes.value = m.server_create_cooldown_minutes || 0;
  const updates = m.manager_updates || {};
  f.manager_updates_enabled.checked = updates.enabled !== false;
  f.manager_updates_repo.value = updates.repo || "Zataralee/Enshrouded-Server-Manager-by-Zat";
  f.manager_updates_interval_hours.value = updates.interval_hours || 24;
  f.manager_updates_github_token.placeholder = updates.github_token ? "Saved token hidden; leave blank to keep current" : "GitHub token for private repo";
  f.manager_updates_clear_github_token.checked = false;
  f.manager_updates_auto_install.checked = !!updates.auto_install;
  renderManagerUpdateStatus();
  f.auto_restart.checked = !!inst.auto_restart;
  f.start_on_manager_launch.checked = !!inst.start_on_manager_launch;
  f.update_before_start.checked = !!inst.update_before_start;
  f.stop_timeout_seconds.value = m.stop_timeout_seconds || 25;
  f.ftp_enabled.checked = !!ftp.enabled;
  f.ftp_host.value = ftp.host || "";
  f.ftp_port.value = ftp.port || 21;
  f.ftp_username.value = ftp.username || "";
  f.ftp_remote_dir.value = ftp.remote_dir || "/";
  f.ftp_passive.checked = ftp.passive !== false;
}

function renderBackupSchedule() {
  if (backupScheduleDirty) return;
  const form = document.querySelector("#backupScheduleForm");
  const inst = selectedInstance();
  form.scheduled_backup_enabled.checked = !!inst.scheduled_backup_enabled;
  form.backup_interval_minutes.value = inst.backup_interval_minutes || 1440;
  form.classList.toggle("hidden", !can("backups"));
}

function renderWebhookForm() {
  const form = document.querySelector("#webhookForm");
  if (!form) return;
  const inst = selectedInstance();
  if (inst.id !== webhookInstanceId) {
    webhookInstanceId = inst.id || "";
    editingWebhookId = "";
    webhookDirty = false;
  }
  const webhooks = inst.webhooks || [];
  const webhook = webhooks.find(item => item.id === editingWebhookId) || null;
  const events = (state.manager || {}).webhook_events || {};
  renderCurrentWebhooks();
  form.classList.toggle("hidden", !can("settings") || !selectedInstanceId());
  if (webhookDirty) return;
  if (editingWebhookId && !webhook) editingWebhookId = "";
  const selectedEvents = webhook
    ? (webhook.events || [])
    : ((state.manager || {}).default_webhook_events || Object.keys(events));
  document.querySelector("#webhookFormTitle").textContent = webhook ? `Edit ${webhook.name}` : "Add Webhook";
  document.querySelector("#webhookServerNote").textContent = inst.name ? `Webhook settings for ${inst.name}.` : "Select a server to configure its webhooks.";
  form.querySelector("[name=name]").value = webhook?.name || "";
  form.querySelector("[name=enabled]").checked = webhook ? !!webhook.enabled : true;
  form.querySelector("[name=mode]").value = webhook?.mode || "discord";
  const urlInput = form.querySelector("[name=url]");
  urlInput.value = "";
  urlInput.placeholder = webhook?.url ? "Saved URL hidden; leave blank to keep current" : "Discord or JSON webhook URL";
  document.querySelector("#webhookEvents").innerHTML = Object.entries(events).map(([key, label]) => `
    <label class="check"><input type="checkbox" name="events" value="${escapeHtml(key)}" ${selectedEvents.includes(key) ? "checked" : ""}> ${escapeHtml(label)}</label>
  `).join("");
  document.querySelector("#saveWebhookButton").textContent = webhook ? "Save Changes" : "Add Webhook";
  document.querySelector("#cancelWebhookEdit").classList.toggle("hidden", !webhook);
}

function renderCurrentWebhooks() {
  const target = document.querySelector("#currentWebhookList");
  if (!target) return;
  const inst = selectedInstance();
  const events = (state.manager || {}).webhook_events || {};
  const note = document.querySelector("#currentWebhookNote");
  note.textContent = inst.name
    ? `Only webhooks for ${inst.name} are shown here.`
    : "Select a server to view its webhooks.";
  const rows = (inst.webhooks || []).map(webhook => {
    const enabled = !!webhook.enabled;
    const eventNames = (webhook.events || []).map(key => events[key] || key);
    return `
      <div class="instance-row webhook-row ${webhook.id === editingWebhookId ? "active" : ""}">
        <div>
          <strong>${escapeHtml(webhook.name || "Webhook")}</strong>
          <small>${enabled ? "Enabled" : "Disabled"} - ${escapeHtml(webhook.mode || "discord")} - URL saved</small>
          <small>${eventNames.length ? escapeHtml(eventNames.join(", ")) : "No events selected"}</small>
        </div>
        <div class="actions webhook-actions">
          <button type="button" data-edit-webhook="${escapeHtml(webhook.id)}">Edit</button>
          <button type="button" data-test-webhook="${escapeHtml(webhook.id)}">Test</button>
          <button type="button" data-toggle-webhook="${escapeHtml(webhook.id)}" data-webhook-enabled="${enabled}">${enabled ? "Disable" : "Enable"}</button>
          <button type="button" data-delete-webhook="${escapeHtml(webhook.id)}">Delete</button>
        </div>
      </div>
    `;
  });
  target.innerHTML = rows.length ? rows.join("") : `<p>No webhooks are configured for ${escapeHtml(inst.name || "this server")}.</p>`;
}

function renderManagerUpdateStatus() {
  const updates = (state.manager || {}).manager_updates || {};
  const title = document.querySelector("#managerUpdateStatus");
  const detail = document.querySelector("#managerUpdateDetail");
  const installed = document.querySelector("#managerInstalledVersion");
  const published = document.querySelector("#managerPublishedVersion");
  const checked = document.querySelector("#managerLastChecked");
  const installButton = document.querySelector("#installManagerUpdateButton");
  if (!title || !detail) return;
  const installedVersion = updates.installed_version || (state.manager || {}).app_version || "";
  if (installed) installed.textContent = installedVersion ? `v${installedVersion}` : "Unknown";
  if (published) published.textContent = updates.latest_version ? `v${updates.latest_version}` : "Not checked";
  if (checked) checked.textContent = updates.last_checked_at || "Never";
  if (installButton) installButton.disabled = !(updates.release_state === "available" && updates.package_available);
  if (updates.last_error) {
    title.textContent = "Update check failed";
    detail.textContent = updates.last_error;
    detail.classList.add("error");
    return;
  }
  detail.classList.remove("error");
  if (updates.release_state === "available") {
    title.textContent = `ESM-Z update available: v${updates.latest_version}`;
    detail.textContent = updates.latest_url ? `Install package: ${updates.latest_url}` : "The release is newer, but no package URL was reported.";
    return;
  }
  if (updates.release_state === "package_missing") {
    title.textContent = `ESM-Z v${updates.latest_version} is published without an install package`;
    detail.textContent = "The release exists, but it cannot be installed from this page until a Python-required ZIP is attached.";
    return;
  }
  if (updates.release_state === "current") {
    title.textContent = "Installed version matches the latest published release";
    detail.textContent = updates.latest_published_at ? `Published ${updates.latest_published_at}` : "No newer published release was found.";
    return;
  }
  if (updates.release_state === "local_newer") {
    title.textContent = "Installed files are newer than the latest published release";
    detail.textContent = "This usually means ESM-Z was updated manually or newer Git tags have not yet been published as a GitHub Release.";
    return;
  }
  title.textContent = "ESM-Z updates have not been checked yet";
  detail.textContent = "Use Check Now or wait for the scheduled interval.";
}

function renderUsers() {
  if (!canViewUsers()) return;
  if (userListDirty) return;
  const allInstances = state.instances || [];
  const users = (state.manager || {}).users || [];
  const canEditAll = isAdmin();
  document.querySelector("#userList").innerHTML = users.map(user => {
    const admin = user.role === "admin";
    const permBoxes = permissions.map(p => `<label class="check"><input type="checkbox" data-user-permission="${p}" ${admin || (user.permissions || []).includes(p) ? "checked" : ""} ${admin ? "disabled" : ""}> ${p}</label>`).join("");
    const serverBoxes = allInstances.map(inst => `<label class="check"><input type="checkbox" data-user-instance="${inst.id}" ${(user.assigned_instance_ids || []).includes(inst.id) ? "checked" : ""} ${admin ? "disabled" : ""}> ${inst.name}</label>`).join("");
    if (!canEditAll) {
      const assignedNames = (user.assigned_instance_ids || []).map(id => allInstances.find(inst => inst.id === id)?.name || id).join(", ") || "No server assignment";
      return `
        <div class="user-row" data-user-id="${user.id}">
          <label>Username <input name="username" value="${escapeHtml(user.username || "")}" disabled></label>
          <label>Role <input value="${escapeHtml(user.role || "user")}" disabled></label>
          <label>Steam name <input name="steam_name" value="${escapeHtml(user.steam_name || "")}" disabled></label>
          <label>Steam email <input name="steam_email" type="email" value="${escapeHtml(user.steam_email || "")}" disabled></label>
          <small class="wide">Servers: ${escapeHtml(assignedNames)}</small>
          <div class="inline wide">
            <input name="reset_password" type="password" placeholder="New password for reset">
            <button data-reset-user="${user.id}">Reset Password</button>
            <button data-delete-user="${user.id}">Delete</button>
          </div>
        </div>
      `;
    }
    return `
      <div class="user-row" data-user-id="${user.id}">
        <label>Username <input name="username" value="${escapeHtml(user.username || "")}"></label>
        <label>Role
          <select name="role">
            <option value="user">User</option>
            <option value="server_owner">Server Owner</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <label>Steam name <input name="steam_name" value="${escapeHtml(user.steam_name || "")}"></label>
        <label>Steam email <input name="steam_email" type="email" value="${escapeHtml(user.steam_email || "")}"></label>
        <div class="perm-grid">${permBoxes}</div>
        <div class="perm-grid">${serverBoxes || "<p>No servers configured.</p>"}</div>
        <div class="inline wide">
          <input name="reset_password" type="password" placeholder="New password for reset">
          <button data-save-user="${user.id}">Save User</button>
          <button data-reset-user="${user.id}">Reset Password</button>
          <button data-delete-user="${user.id}">Delete</button>
        </div>
      </div>
    `;
  }).join("");
  document.querySelectorAll(".user-row").forEach(row => {
    const user = users.find(item => item.id === row.dataset.userId);
    const role = row.querySelector("[name=role]");
    if (role) role.value = user.role || "user";
  });
}

function renderInvites() {
  if (!canManageInvites()) return;
  const manager = state.manager || {};
  const allowed = manager.allowed_invite_types || [];
  const form = document.querySelector("#inviteForm");
  ensureInviteMetadataFields();
  if (!inviteFormDirty) {
    const selectedCodeType = form.code_type.value;
    form.code_type.innerHTML = allowed.map(type => `<option value="${type}">${inviteTypeLabel(type)}</option>`).join("");
    if (allowed.includes(selectedCodeType)) form.code_type.value = selectedCodeType;
  }
  const serverChoices = state.instances || [];
  if (!inviteFormDirty) {
    document.querySelector("#inviteServerChoices").innerHTML = serverChoices.length ? serverChoices.map(inst => `
      <label class="check"><input type="checkbox" data-invite-instance="${inst.id}" ${!isAdmin() ? "checked" : ""}> ${inst.name}</label>
    `).join("") : "<p>No servers available for invite assignment.</p>";
  }

  const profiles = manager.invite_profiles || {};
  if (!inviteProfilesDirty) {
    document.querySelector("#inviteProfiles").innerHTML = Object.keys(profiles).map(type => {
      const profile = profiles[type];
      const boxes = permissions.map(p => `<label class="check"><input type="checkbox" data-profile-permission="${p}" ${(profile.permissions || []).includes(p) ? "checked" : ""}> ${p}</label>`).join("");
      return `<div class="user-row" data-profile-type="${type}"><h3>${profile.label || inviteTypeLabel(type)}</h3><div class="perm-grid">${boxes}</div></div>`;
    }).join("");
  }

  const invites = manager.invite_codes || [];
  if (!document.querySelector("#latestInvite").dataset.locked) renderLatestInvite(null);
  const renderList = (selector, status) => {
    const items = invites.filter(invite => invite.status === status);
    document.querySelector(selector).innerHTML = items.length ? items.map(invite => {
      const assignedNames = (invite.assigned_instance_ids || []).map(id => (state.instances || []).find(inst => inst.id === id)?.name || id).join(", ") || "No server assignment";
      const url = status === "generated" ? inviteUrl(invite.code) : "";
      const canClearExpired = isAdmin() || invite.created_by_user_id === currentUser().id;
      return `
        <div class="invite-card">
          <span><strong>${invite.label || inviteTypeLabel(invite.code_type)}</strong> ${status === "generated" ? invite.code : ""}</span>
          ${inviteNotes(invite)}
          ${status === "generated" ? `<small>Copy code OR copy URL.</small>${inviteActions(invite)}` : ""}
          ${url ? `<small>Invite URL: ${url}</small>` : ""}
          <small>${assignedNames}</small>
          <small>Created by ${invite.created_by_username || "unknown"} at ${invite.created_at || ""}</small>
          <small>${invite.never_expires ? "Does not expire" : "Expires " + (invite.expires_at || "")}</small>
          ${invite.used_by_username ? `<small>Used by ${invite.used_by_username} at ${invite.used_at || ""}</small>` : ""}
          ${status === "generated" ? `<span data-invalidate-invite="${invite.id}">Invalidate</span>` : ""}
          ${status === "used" && canClearExpired ? `<span data-clear-used-invite="${invite.id}">Clear</span>` : ""}
          ${status === "expired" && canClearExpired ? `<span data-clear-expired-invite="${invite.id}">Clear</span>` : ""}
        </div>
      `;
    }).join("") : "<p>None.</p>";
  };
  renderList("#generatedInviteList", "generated");
  renderList("#usedInviteList", "used");
  renderList("#expiredInviteList", "expired");
}

function instructionSection(title, body) {
  return `<div class="panel"><h2>${title}</h2>${body}</div>`;
}

function renderInstructions() {
  const parts = [];
  parts.push(instructionSection("Signing In", `
    <p>Open the manager URL, sign in with your username and password, then use My Account to change your password when needed.</p>
    <p>If you forget your password, ask an admin or your server owner to reset it.</p>
  `));
  parts.push(instructionSection("Choosing a Server", `
    <p>Use the server dropdown in the header to switch between servers assigned to you. You can only see servers you created or were assigned to.</p>
  `));
  if (can("control")) {
    parts.push(instructionSection("Dashboard", `
      <p>Use Dashboard to start, stop, restart, run update checks, enable update checks before start/restart, and add scheduled restart times.</p>
      <p>If start fails with a query port warning, change the server query port in Server Config before starting it.</p>
    `));
  }
  if (can("setup")) {
    parts.push(instructionSection("Setup & Instances", `
      <p>Use Existing Install when the server files already exist on this hosting machine. The folder must contain enshrouded_server.exe.</p>
      <p>Use Install New Server for a fresh install. Enter an instance name, adjust Directory only if you want a different folder name, and enter a query port only if you do not want the default. The manager checks for duplicate ports before install.</p>
      <p>New installs can take several minutes, sometimes 10-20 minutes on first SteamCMD setup. Click the install button once and watch Install Status.</p>
      <p>Admins can see install jobs from all users. Completed and failed install jobs remain visible for review.</p>
      <p>Removed servers can be restored or permanently deleted from Removed Servers. Deleting files cannot be undone.</p>
    `));
  }
  if (can("settings")) {
    parts.push(instructionSection("Server Setup & Config", `
      <p>Edit the selected server's enshrouded_server.json, including server name, IP bind, query port, slots, save/log folders, chat options, and difficulty.</p>
      <p>If the server is running, the manager warns before applying changes that require a restart.</p>
    `));
    parts.push(instructionSection("Webhooks", `
      <p>Webhooks belong to the server selected in the header. Only that server's webhooks appear in Current Webhooks.</p>
      <p>You can add multiple Discord or generic JSON destinations, choose events for each one, and edit, test, enable, disable, or delete them independently.</p>
    `));
  }
  if (can("accounts")) {
    parts.push(instructionSection("Game Server Accounts", `
      <p>This tab manages Enshrouded in-game user groups and bans, not manager login accounts. Groups control which players can join and what they can do in-game.</p>
      <p>A blank group password allows users to join that group without a group password. Only one group should be passwordless.</p>
    `));
  }
  if (can("logs")) {
    parts.push(instructionSection("Logs", `
      <p>Use Logs to inspect manager and server log files when a server will not start, players cannot connect, or an update/backup needs confirmation.</p>
    `));
  }
  if (can("saves") || can("backups")) {
    parts.push(instructionSection("Saves & Backups", `
      ${can("saves") ? "<p>After installing your server, use Import Save Game to move your existing world to the dedicated server.</p><p>For most remote users, choose the save folder from your own PC. Steam Cloud saves are usually in C:\\Program Files (x86)\\Steam\\userdata\\YOUR_STEAM_ID\\1203620\\remote. Local saves with Steam Cloud disabled are usually in %USERPROFILE%\\Saved Games\\enshrouded.</p><p>After you choose a folder, the manager groups the files into separate Enshrouded worlds. Pick one world file ID to import. The ID may not match the world name you see in-game because Enshrouded names local save files by creation order.</p><p>During import, the manager stops the server if needed, backs up the current save, and installs the selected world into the server's primary save slot so the dedicated server loads it on startup. Imported Saves shows the history for the selected server.</p>" : ""}
      ${can("backups") ? "<p>Create local backups, push FTP backups when configured, and enable automatic backups for the selected server.</p>" : ""}
    `));
  }
  if (canManageInvites()) {
    parts.push(instructionSection("Invites", `
      <p>Create one-time invite codes for users. Optional title and description fields help track who received a code and why.</p>
      <p>Expires in uses days / hours / minutes. Example: 01 / 00 / 00 means 1 day.</p>
      <p>Use Copy code or Copy Invite URL after generating a code. Generated, used, and expired codes can be cleaned up from their lists.</p>
    `));
  }
  if (canViewUsers()) {
    parts.push(instructionSection("Users", `
      <p>Admins can see all manager users. Server owners can see users who joined with invite codes they generated.</p>
      <p>Use password reset when a user cannot sign in. Admins can also create and edit manager accounts directly.</p>
    `));
  }
  if (isAdmin()) {
    parts.push(instructionSection("Manager", `
      <p>Admins can configure manager access, listen address, web UI port, storage roots, backup limits, crash restart behavior, launch behavior, and FTP backup settings.</p>
      <p>Admins can also limit how many servers each server owner may create and how long a server owner must wait between server creations.</p>
      <p>Listen address and web UI port changes require restarting the manager.</p>
    `));
  }
  parts.push(instructionSection("If Something Seems Stuck", `
    <p>For new installs, wait longer than you think you need to. Check Install Status, Instances, and Logs before creating another server.</p>
  `));
  document.querySelector("#instructionsContent").innerHTML = parts.join("");
}

function renderUpdateLog() {
  const manager = state.manager || {};
  const current = manager.app_version || "";
  document.querySelector("#versionTitle").textContent = current ? `ESM-Z Updates - Version ${current}` : "ESM-Z Updates";
  const updates = manager.update_log || [];
  document.querySelector("#updateLog").innerHTML = updates.length ? updates.map(item => `
    <div class="update-row">
      <div>
        <strong>Version ${escapeHtml(item.version || "")}</strong>
        <small>${escapeHtml(item.date || "")}</small>
      </div>
      <ul>
        ${(item.changes || []).map(change => `<li>${escapeHtml(change)}</li>`).join("")}
      </ul>
    </div>
  `).join("") : "<p>No update log is available.</p>";
}

async function refresh() {
  const suffix = activeInstanceId ? `?instance_id=${encodeURIComponent(activeInstanceId)}` : "";
  const data = await api(`/api/status${suffix}`);
  state = data;
  if (data.selected_instance && data.selected_instance.id && data.selected_instance.id !== activeInstanceId) {
    activeInstanceId = data.selected_instance.id;
    localStorage.setItem("esm_active_instance_id", activeInstanceId);
  }
  serverConfig = data.server_config || {};
  renderStatus();
  renderAccess();
  renderInstances();
  renderNewInstallDefaults();
  renderInstallJobs();
  renderServerForm();
  renderAccounts();
  renderSchedules();
  renderLogs();
  renderManagerForm();
  renderBackupSchedule();
  renderWebhookForm();
  renderUsers();
  renderInvites();
  renderInstructions();
  renderUpdateLog();
  renderBackups().catch(() => {});
  renderDiscoveredSaves();
  renderSaveImports().catch(() => {});
}

function startAutoRefresh() {
  if (autoRefreshPoll) return;
  autoRefreshPoll = setInterval(refresh, 5000);
}

async function saveServerConfig() {
  const running = !!(state.server && state.server.running);
  if (running) {
    const ok = confirm("This server is currently running. Saving config changes requires the manager to stop the server, save the config, then start it again. Continue?");
    if (!ok) return;
  }
  const result = await api("/api/config/server", {
    method: "POST",
    body: JSON.stringify({
      instance_id: selectedInstanceId(),
      server_config: serverConfig,
      restart_if_running: running,
    }),
  });
  serverConfigDirty = false;
  accountsDirty = false;
  toast(result.restarted ? "Config saved and server restarted" : "Server config saved");
  refresh();
}

function readAccountForms() {
  serverConfig.userGroups = [...document.querySelectorAll(".group")].map(el => {
    const q = name => el.querySelector(`[name=${name}]`);
    return {
      name: q("name").value,
      password: q("password").value,
      canKickBan: q("canKickBan").checked,
      canAccessInventories: q("canAccessInventories").checked,
      canEditWorld: q("canEditWorld").checked,
      canEditBase: q("canEditBase").checked,
      canExtendBase: q("canExtendBase").checked,
      reservedSlots: Number(q("reservedSlots").value || 0),
    };
  });
  const bans = [...document.querySelectorAll(".ban")].map(el => {
    const q = name => el.querySelector(`[name=${name}]`);
    return {
      accountIDHash: q("accountIDHash").value,
      displayName: q("displayName").value,
      characterName: q("characterName").value,
      banDate: Number(q("banDate").value || Math.floor(Date.now() / 1000)),
    };
  });
  if ("bans" in serverConfig) serverConfig.bans = bans;
  else serverConfig.bannedAccounts = bans;
}

document.addEventListener("click", async event => {
  const invalidateInvite = event.target.closest("[data-invalidate-invite]");
  if (invalidateInvite) {
    const result = await api("/api/invites/invalidate", { method: "POST", body: JSON.stringify({ invite_id: invalidateInvite.dataset.invalidateInvite }) });
    if (result.invite) {
      state.manager = state.manager || {};
      state.manager.invite_codes = (state.manager.invite_codes || []).map(invite => invite.id === result.invite.id ? result.invite : invite);
      renderInvites();
    }
    toast("Invite code invalidated");
    refresh();
    return;
  }
  const clearExpiredInvite = event.target.closest("[data-clear-expired-invite]");
  if (clearExpiredInvite) {
    await api("/api/invites/clear-expired-one", { method: "POST", body: JSON.stringify({ invite_id: clearExpiredInvite.dataset.clearExpiredInvite }) });
    state.manager = state.manager || {};
    state.manager.invite_codes = (state.manager.invite_codes || []).filter(invite => invite.id !== clearExpiredInvite.dataset.clearExpiredInvite);
    renderInvites();
    toast("Expired invite cleared");
    refresh();
    return;
  }
  const clearUsedInvite = event.target.closest("[data-clear-used-invite]");
  if (clearUsedInvite) {
    await api("/api/invites/clear-used-one", { method: "POST", body: JSON.stringify({ invite_id: clearUsedInvite.dataset.clearUsedInvite }) });
    state.manager = state.manager || {};
    state.manager.invite_codes = (state.manager.invite_codes || []).filter(invite => invite.id !== clearUsedInvite.dataset.clearUsedInvite);
    renderInvites();
    toast("Used invite cleared");
    refresh();
    return;
  }
  const btn = event.target.closest("button");
  if (!btn) return;
  if (btn.dataset.clearUsedInvites) {
    if (!confirm("Clear all used invite codes from this list?")) return;
    await api("/api/invites/clear-used", { method: "POST" });
    state.manager = state.manager || {};
    state.manager.invite_codes = (state.manager.invite_codes || []).filter(invite => {
      if (invite.status !== "used") return true;
      return !isAdmin() && invite.created_by_user_id !== currentUser().id;
    });
    renderInvites();
    toast("Used invite codes cleared");
    refresh();
    return;
  }
  if (btn.dataset.clearExpiredInvites) {
    if (!confirm("Clear all expired invite codes from this list?")) return;
    await api("/api/invites/clear-expired", { method: "POST" });
    state.manager = state.manager || {};
    state.manager.invite_codes = (state.manager.invite_codes || []).filter(invite => {
      if (invite.status !== "expired") return true;
      return !isAdmin() && invite.created_by_user_id !== currentUser().id;
    });
    renderInvites();
    toast("Expired invite codes cleared");
    refresh();
    return;
  }
  if (btn.dataset.copyText) {
    await copyText(btn.dataset.copyText, btn.dataset.copyLabel || "Text");
    return;
  }
  if (btn.dataset.navSection) {
    activateTab(firstVisibleSubTab(btn.dataset.navSection) || btn.dataset.defaultTab, btn.dataset.navSection);
    return;
  }
  if (btn.dataset.tab) {
    activateTab(btn.dataset.tab, btn.dataset.parentSection || "");
    return;
  }
  if (btn.dataset.log) {
    const data = await api(`/api/log?path=${encodeURIComponent(btn.dataset.log)}&instance_id=${encodeURIComponent(selectedInstanceId() || "")}`);
    document.querySelector("#logTitle").textContent = btn.dataset.log;
    document.querySelector("#logOutput").textContent = data.content;
    return;
  }
  if (btn.dataset.removeSchedule) {
    const schedules = (selectedInstance().scheduled_restarts || []).filter(t => t !== btn.dataset.removeSchedule);
    await api("/api/instances/update", { method: "POST", body: JSON.stringify({ instance_id: selectedInstanceId(), scheduled_restarts: schedules }) });
    toast("Schedule removed");
    refresh();
    return;
  }
  if (btn.dataset.selectInstance) {
    if ((serverConfigDirty || accountsDirty) && !confirm("Discard unsaved config edits and switch instances?")) return;
    serverConfigDirty = false;
    accountsDirty = false;
    activeInstanceId = btn.dataset.selectInstance;
    localStorage.setItem("esm_active_instance_id", activeInstanceId);
    toast("Instance selected");
    refresh();
    return;
  }
  if (btn.dataset.removeInstance) {
    const item = (state.instances || []).find(inst => inst.id === btn.dataset.removeInstance);
    const ok = confirm(`Remove "${item ? item.name : "this instance"}" from the manager?`);
    if (!ok) return;
    const deleteFiles = confirm("Do you also want to delete the server files? Choose Cancel to only remove it from the instance list.");
    await api("/api/instances/remove", { method: "POST", body: JSON.stringify({ instance_id: btn.dataset.removeInstance, delete_files: deleteFiles }) });
    if (activeInstanceId === btn.dataset.removeInstance) {
      activeInstanceId = "";
      localStorage.removeItem("esm_active_instance_id");
    }
    if (item) {
      state.instances = (state.instances || []).filter(inst => inst.id !== btn.dataset.removeInstance);
      if (!deleteFiles) {
        state.manager = state.manager || {};
        state.manager.removed_instances = [{ ...item, removed_at: "Just now" }, ...((state.manager || {}).removed_instances || []).filter(inst => inst.id !== item.id)];
      }
      renderInstances();
    }
    updateActionDirty = false;
    toast(deleteFiles ? "Instance removed and files deleted" : "Instance removed");
    refresh();
    return;
  }
  if (btn.dataset.restoreInstance) {
    const result = await api("/api/instances/restore", { method: "POST", body: JSON.stringify({ instance_id: btn.dataset.restoreInstance }) });
    if (result.instance && result.instance.id) {
      activeInstanceId = result.instance.id;
      localStorage.setItem("esm_active_instance_id", activeInstanceId);
    }
    state.manager = state.manager || {};
    state.manager.removed_instances = ((state.manager || {}).removed_instances || []).filter(inst => inst.id !== btn.dataset.restoreInstance);
    if (result.instance) state.instances = [result.instance, ...(state.instances || []).filter(inst => inst.id !== result.instance.id)];
    renderInstances();
    toast("Server restored");
    refresh();
    return;
  }
  if (btn.dataset.deleteRemovedInstance) {
    const item = ((state.manager || {}).removed_instances || []).find(inst => inst.id === btn.dataset.deleteRemovedInstance);
    if (!confirm(`Delete all files for "${item ? item.name : "this removed server"}"? This cannot be undone.`)) return;
    await api("/api/instances/delete-removed", { method: "POST", body: JSON.stringify({ instance_id: btn.dataset.deleteRemovedInstance }) });
    state.manager = state.manager || {};
    state.manager.removed_instances = ((state.manager || {}).removed_instances || []).filter(inst => inst.id !== btn.dataset.deleteRemovedInstance);
    renderInstances();
    toast("Removed server files deleted");
    refresh();
    return;
  }
  if (btn.dataset.importLocalSave) {
    if (!confirm("Import this save into the selected server? The current server save will be backed up first.")) return;
    await api("/api/savegame/import-local", { method: "POST", body: JSON.stringify({ instance_id: selectedInstanceId(), save_id: btn.dataset.importLocalSave }) });
    toast("Local save imported");
    refresh();
    return;
  }
  if (btn.dataset.useInstalledInstance) {
    activeInstanceId = btn.dataset.useInstalledInstance;
    localStorage.setItem("esm_active_instance_id", activeInstanceId);
    if (btn.dataset.dismissJob) {
      await api("/api/jobs/dismiss", { method: "POST", body: JSON.stringify({ job_id: btn.dataset.dismissJob }) });
    }
    const targetTab = can("settings") ? "settings" : "dashboard";
    activateTab(targetTab);
    toast("Installed server selected");
    refresh();
    return;
  }
  if (btn.dataset.dismissJob) {
    await api("/api/jobs/dismiss", { method: "POST", body: JSON.stringify({ job_id: btn.dataset.dismissJob }) });
    state.install_jobs = (state.install_jobs || []).filter(job => job.id !== btn.dataset.dismissJob);
    renderInstallJobs();
    toast("Install status dismissed");
    refresh();
    return;
  }
  if (btn.dataset.saveUser) {
    const row = btn.closest(".user-row");
    const payload = {
      user_id: btn.dataset.saveUser,
      username: row.querySelector("[name=username]").value,
      role: row.querySelector("[name=role]").value,
      steam_name: row.querySelector("[name=steam_name]").value,
      steam_email: row.querySelector("[name=steam_email]").value,
      permissions: [...row.querySelectorAll("[data-user-permission]:checked")].map(el => el.dataset.userPermission),
      assigned_instance_ids: [...row.querySelectorAll("[data-user-instance]:checked")].map(el => el.dataset.userInstance),
    };
  await api("/api/users/update", { method: "POST", body: JSON.stringify(payload) });
    userListDirty = false;
    toast("User saved");
    refresh();
    return;
  }
  if (btn.dataset.resetUser) {
    const row = btn.closest(".user-row");
    const password = row.querySelector("[name=reset_password]").value;
    await api("/api/users/reset-password", { method: "POST", body: JSON.stringify({ user_id: btn.dataset.resetUser, password }) });
    row.querySelector("[name=reset_password]").value = "";
    toast("Password reset");
    refresh();
    return;
  }
  if (btn.dataset.deleteUser) {
    if (!confirm("Delete this manager user?")) return;
    await api("/api/users/delete", { method: "POST", body: JSON.stringify({ user_id: btn.dataset.deleteUser }) });
    toast("User deleted");
    refresh();
    return;
  }
  if (btn.dataset.editWebhook) {
    editingWebhookId = btn.dataset.editWebhook;
    webhookDirty = false;
    renderWebhookForm();
    document.querySelector("#webhookForm")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  if (btn.dataset.testWebhook) {
    try {
      await api("/api/webhooks/test", {
        method: "POST",
        body: JSON.stringify({
          instance_id: selectedInstanceId(),
          webhook_id: btn.dataset.testWebhook,
        }),
      });
      toast("Test webhook sent");
    } catch (err) {
      toast(err.message);
    }
    return;
  }
  if (btn.dataset.toggleWebhook) {
    const enabled = btn.dataset.webhookEnabled !== "true";
    try {
      await api("/api/webhooks/save", {
        method: "POST",
        body: JSON.stringify({
          instance_id: selectedInstanceId(),
          webhook: { id: btn.dataset.toggleWebhook, enabled },
        }),
      });
      editingWebhookId = "";
      webhookDirty = false;
      toast(`Webhook ${enabled ? "enabled" : "disabled"}`);
      refresh();
    } catch (err) {
      toast(err.message);
    }
    return;
  }
  if (btn.dataset.deleteWebhook) {
    const webhook = (selectedInstance().webhooks || []).find(item => item.id === btn.dataset.deleteWebhook);
    if (!confirm(`Delete "${webhook?.name || "this webhook"}" from ${selectedInstance().name || "this server"}?`)) return;
    try {
      await api("/api/webhooks/delete", {
        method: "POST",
        body: JSON.stringify({ instance_id: selectedInstanceId(), webhook_id: btn.dataset.deleteWebhook }),
      });
      if (editingWebhookId === btn.dataset.deleteWebhook) editingWebhookId = "";
      webhookDirty = false;
      toast("Webhook deleted");
      refresh();
    } catch (err) {
      toast(err.message);
    }
    return;
  }
  if (btn.dataset.cancelWebhookEdit !== undefined) {
    editingWebhookId = "";
    webhookDirty = false;
    renderWebhookForm();
    return;
  }
  if (btn.dataset.removeGroup) {
    serverConfig.userGroups.splice(Number(btn.dataset.removeGroup), 1);
    accountsDirty = true;
    renderAccounts(true);
    return;
  }
  if (btn.dataset.removeBan) {
    const key = "bans" in serverConfig ? "bans" : "bannedAccounts";
    serverConfig[key].splice(Number(btn.dataset.removeBan), 1);
    accountsDirty = true;
    renderAccounts(true);
    return;
  }
  const action = btn.dataset.action;
  if (!action) return;
  try {
    if (action === "start") await api("/api/server/start", { method: "POST", body: JSON.stringify({ instance_id: selectedInstanceId(), update: document.querySelector("#updateAction").checked }) });
    if (action === "stop") await api("/api/server/stop", { method: "POST", body: JSON.stringify({ instance_id: selectedInstanceId() }) });
    if (action === "restart") await api("/api/server/restart", { method: "POST", body: JSON.stringify({ instance_id: selectedInstanceId(), update: document.querySelector("#updateAction").checked }) });
    if (action === "update") await api("/api/server/update", { method: "POST", body: JSON.stringify({ instance_id: selectedInstanceId() }) });
    if (action === "saveRawConfig") {
      serverConfig = JSON.parse(document.querySelector("#rawConfig").value);
      await saveServerConfig();
    }
    if (action === "addGroup") {
      serverConfig.userGroups = serverConfig.userGroups || [];
      serverConfig.userGroups.push({ name: "New Group", password: "", canKickBan: false, canAccessInventories: false, canEditWorld: true, canEditBase: false, canExtendBase: false, reservedSlots: 0 });
      accountsDirty = true;
      renderAccounts(true);
      return;
    }
    if (action === "addBan") {
      const key = "bans" in serverConfig ? "bans" : "bannedAccounts";
      serverConfig[key] = serverConfig[key] || [];
      serverConfig[key].push({ accountIDHash: "", displayName: "", characterName: "", banDate: Math.floor(Date.now() / 1000) });
      accountsDirty = true;
      renderAccounts(true);
      return;
    }
    if (action === "saveAccounts") {
      readAccountForms();
      await saveServerConfig();
    }
    if (action === "addSchedule") {
      const t = document.querySelector("#scheduleTime").value;
      if (t) {
        const schedules = [...new Set([...(selectedInstance().scheduled_restarts || []), t])].sort();
        await api("/api/instances/update", { method: "POST", body: JSON.stringify({ instance_id: selectedInstanceId(), scheduled_restarts: schedules }) });
        toast("Schedule saved");
      }
    }
    if (action === "backup") await api("/api/backup/create", { method: "POST", body: JSON.stringify({ instance_id: selectedInstanceId(), ftp: false }) });
    if (action === "backupFtp") await api("/api/backup/create", { method: "POST", body: JSON.stringify({ instance_id: selectedInstanceId(), ftp: true }) });
    if (action === "checkManagerUpdate") {
      const result = await api("/api/manager/check-update", { method: "POST" });
      state.manager.manager_updates = result.manager_updates;
      renderManagerUpdateStatus();
      const messages = {
        available: "ESM-Z update available",
        package_missing: "New release found, but its install package is missing",
        current: "Installed version matches the latest published release",
        local_newer: "Installed files are newer than the latest published release",
        error: "Update check failed",
      };
      toast(messages[result.manager_updates.release_state] || "Update check completed");
      return;
    }
    if (action === "installManagerUpdate") {
      if (!confirm("Install the available manager update package? Restart the manager after it finishes to run the new version.")) return;
      const result = await api("/api/manager/install-update", { method: "POST" });
      state.manager.manager_updates = result.manager_updates;
      renderManagerUpdateStatus();
      toast("Manager update installed. Restart the manager to use it.");
      return;
    }
    if (action === "discoverSaves") {
      const data = await api("/api/savegame/discover");
      discoveredSaves = data.saves || [];
      renderDiscoveredSaves();
      toast(discoveredSaves.length ? "Local saves found" : "No local saves found");
      return;
    }
    if (action === "clearRemoved") await api("/api/instances/clear-removed", { method: "POST" });
    if (action === "logout") {
      await fetch("/api/auth/logout", { method: "POST" });
      location.reload();
      return;
    }
    toast("Done");
    refresh();
  } catch (err) {
    toast(err.message);
  }
});

document.querySelector("#serverForm").addEventListener("submit", async event => {
  event.preventDefault();
  const data = new FormData(event.target);
  for (const [key, value] of data.entries()) {
    if (key === "public_server") continue;
    const old = serverConfig[key];
    serverConfig[key] = typeof old === "number" ? Number(value) : value;
  }
  for (const key of ["enableVoiceChat", "enableTextChat"]) {
    serverConfig[key] = event.target.querySelector(`[name=${key}]`).checked;
  }
  await saveServerConfig();
});

document.querySelector("#serverForm").addEventListener("input", () => {
  serverConfigDirty = true;
});

document.querySelector("#serverForm").addEventListener("change", () => {
  serverConfigDirty = true;
});

document.querySelector("#rawConfig").addEventListener("input", () => {
  serverConfigDirty = true;
});

document.querySelector("#groups").addEventListener("input", () => {
  accountsDirty = true;
});

document.querySelector("#groups").addEventListener("change", () => {
  accountsDirty = true;
});

document.querySelector("#bans").addEventListener("input", () => {
  accountsDirty = true;
});

document.querySelector("#bans").addEventListener("change", () => {
  accountsDirty = true;
});

document.querySelector("#managerForm").addEventListener("submit", async event => {
  event.preventDefault();
  const f = event.target;
  const data = new FormData(f);
  const managerPayload = {
    username: data.get("username"),
    password: data.get("password"),
    bind_host: data.get("bind_host"),
    port: Number(data.get("port") || 8080),
    allow_local_bypass: data.has("allow_local_bypass"),
    stop_timeout_seconds: Number(data.get("stop_timeout_seconds") || 25),
    server_root: data.get("server_root"),
    backup_root: data.get("backup_root"),
    min_backup_interval_minutes: Number(data.get("min_backup_interval_minutes") || 15),
    max_backup_interval_minutes: Number(data.get("max_backup_interval_minutes") || 10080),
    max_servers_per_owner: Number(data.get("max_servers_per_owner") || 0),
    server_create_cooldown_minutes: Number(data.get("server_create_cooldown_minutes") || 0),
    manager_updates: {
      enabled: data.has("manager_updates_enabled"),
      repo: data.get("manager_updates_repo"),
      interval_hours: Number(data.get("manager_updates_interval_hours") || 24),
      github_token: data.get("manager_updates_github_token"),
      clear_github_token: data.has("manager_updates_clear_github_token"),
      auto_install: data.has("manager_updates_auto_install"),
    },
  };
  const instancePayload = {
    instance_id: selectedInstanceId(),
    auto_restart: data.has("auto_restart"),
    start_on_manager_launch: data.has("start_on_manager_launch"),
    update_before_start: data.has("update_before_start"),
    scheduled_backup_enabled: document.querySelector("#backupScheduleForm").scheduled_backup_enabled.checked,
    backup_interval_minutes: Number(document.querySelector("#backupScheduleForm").backup_interval_minutes.value || 1440),
    ftp_backup: {
      enabled: data.has("ftp_enabled"),
      host: data.get("ftp_host"),
      port: Number(data.get("ftp_port") || 21),
      username: data.get("ftp_username"),
      password: data.get("ftp_password"),
      remote_dir: data.get("ftp_remote_dir") || "/",
      passive: data.has("ftp_passive"),
    },
  };
  await api("/api/config/manager", { method: "POST", body: JSON.stringify(managerPayload) });
  if (selectedInstanceId()) {
    await api("/api/instances/update", { method: "POST", body: JSON.stringify(instancePayload) });
  }
  f.password.value = "";
  f.ftp_password.value = "";
  f.manager_updates_github_token.value = "";
  managerFormDirty = false;
  toast("Manager settings saved. Restart the manager for listen address or port changes.");
  refresh();
});

document.querySelector("#managerForm").addEventListener("input", () => {
  managerFormDirty = true;
});

document.querySelector("#managerForm").addEventListener("change", () => {
  managerFormDirty = true;
});

document.querySelector("#webhookForm").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.target;
  const data = new FormData(form);
  const payload = {
    instance_id: selectedInstanceId(),
    webhook: {
      id: editingWebhookId,
      name: data.get("name"),
      enabled: data.has("enabled"),
      mode: data.get("mode") || "discord",
      url: data.get("url"),
      events: [...form.querySelectorAll("[name=events]:checked")].map(el => el.value),
    },
  };
  try {
    await api("/api/webhooks/save", { method: "POST", body: JSON.stringify(payload) });
    form.url.value = "";
    editingWebhookId = "";
    webhookDirty = false;
    toast("Webhook saved");
    refresh();
  } catch (err) {
    toast(err.message);
  }
});

document.querySelector("#webhookForm").addEventListener("input", () => {
  webhookDirty = true;
});

document.querySelector("#webhookForm").addEventListener("change", () => {
  webhookDirty = true;
});

document.querySelector("#passwordForm").addEventListener("submit", async event => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.target).entries());
  await api("/api/users/change-password", { method: "POST", body: JSON.stringify(body) });
  event.target.reset();
  toast("Password changed");
  refresh();
});

document.querySelector("#newUserForm").addEventListener("submit", async event => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.target).entries());
  await api("/api/users/create", { method: "POST", body: JSON.stringify(body) });
  event.target.reset();
  toast("User created");
  refresh();
});

document.querySelector("#userList").addEventListener("input", () => {
  userListDirty = true;
});

document.querySelector("#userList").addEventListener("change", () => {
  userListDirty = true;
});

document.querySelector("#inviteForm").addEventListener("submit", async event => {
  event.preventDefault();
  const data = new FormData(event.target);
  const payload = Object.fromEntries(data.entries());
  payload.never_expires = data.has("never_expires");
  if (!payload.never_expires) {
    if (payload.duration !== undefined) {
      try {
        payload.duration_amount = parseInviteDuration(payload.duration);
        payload.duration_unit = "minutes";
      } catch (err) {
        toast(err.message);
        return;
      }
    } else {
      payload.duration_amount = Number(payload.duration_amount || 1);
    }
  }
  payload.assigned_instance_ids = [...event.target.querySelectorAll("[data-invite-instance]:checked")].map(el => el.dataset.inviteInstance);
  const button = event.target.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    const result = await api("/api/invites/generate", { method: "POST", body: JSON.stringify(payload) });
    state.manager = state.manager || {};
    state.manager.invite_codes = [result.invite, ...(state.manager.invite_codes || []).filter(invite => invite.id !== result.invite.id)];
    inviteFormDirty = false;
    renderLatestInvite(result.invite);
    renderInvites();
    toast("Invite code generated");
    event.target.reset();
    refresh();
  } catch (err) {
    toast(`Invite failed: ${err.message}`);
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#inviteForm").addEventListener("input", () => {
  inviteFormDirty = true;
});

document.querySelector("#inviteForm").addEventListener("change", () => {
  inviteFormDirty = true;
});

document.querySelector("#inviteProfilesForm").addEventListener("submit", async event => {
  event.preventDefault();
  const payload = {};
  document.querySelectorAll("[data-profile-type]").forEach(row => {
    payload[row.dataset.profileType] = {
      permissions: [...row.querySelectorAll("[data-profile-permission]:checked")].map(el => el.dataset.profilePermission),
    };
  });
  await api("/api/invites/profiles", { method: "POST", body: JSON.stringify(payload) });
  inviteProfilesDirty = false;
  toast("Invite permissions saved");
  refresh();
});

document.querySelector("#inviteProfilesForm").addEventListener("input", () => {
  inviteProfilesDirty = true;
});

document.querySelector("#inviteProfilesForm").addEventListener("change", () => {
  inviteProfilesDirty = true;
});

document.querySelector("#backupScheduleForm").addEventListener("submit", async event => {
  event.preventDefault();
  const data = new FormData(event.target);
  await api("/api/instances/update", {
    method: "POST",
    body: JSON.stringify({
      instance_id: selectedInstanceId(),
      scheduled_backup_enabled: data.has("scheduled_backup_enabled"),
      backup_interval_minutes: Number(data.get("backup_interval_minutes") || 1440),
    }),
  });
  backupScheduleDirty = false;
  toast("Backup schedule saved");
  refresh();
});

document.querySelector("#backupScheduleForm").addEventListener("input", () => {
  backupScheduleDirty = true;
});

document.querySelector("#backupScheduleForm").addEventListener("change", () => {
  backupScheduleDirty = true;
});

document.querySelector("#importForm").addEventListener("submit", async event => {
  event.preventDefault();
  const data = new FormData(event.target);
  await api(`/api/savegame/import?instance_id=${encodeURIComponent(selectedInstanceId() || "")}`, { method: "POST", body: data });
  toast("Save imported");
  event.target.reset();
  refresh();
});

document.querySelector("#folderImportForm").addEventListener("submit", async event => {
  event.preventDefault();
  const selected = event.target.querySelector("[name=uploaded_world_id]:checked")?.value || "";
  const world = uploadedSaveWorlds.find(item => item.world_id === selected);
  if (!world) {
    toast("Select one world to import");
    return;
  }
  if (!confirm(`Import world file ID ${world.world_id} into the selected server? The manager will stop the server if needed, back up the current save, and install this world as the server's primary save.`)) return;
  const data = new FormData();
  world.files.forEach(file => {
    data.append("savefiles", file, fileRelativePath(file));
  });
  await api(`/api/savegame/import-folder?instance_id=${encodeURIComponent(selectedInstanceId() || "")}`, { method: "POST", body: data });
  toast("Selected world imported");
  uploadedSaveFiles = [];
  uploadedSaveWorlds = [];
  event.target.reset();
  renderUploadedWorlds();
  refresh();
});

document.querySelector("#folderImportForm [name=savefiles]").addEventListener("change", event => {
  uploadedSaveFiles = [...event.target.files];
  uploadedSaveWorlds = groupUploadedSaveFiles(uploadedSaveFiles);
  renderUploadedWorlds();
});

document.querySelector("#existingInstallForm").addEventListener("submit", async event => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  const result = await api("/api/instances/import", { method: "POST", body: JSON.stringify(payload) });
  if (result.instance && result.instance.id) {
    activeInstanceId = result.instance.id;
    localStorage.setItem("esm_active_instance_id", activeInstanceId);
  }
  toast("Existing server added");
  event.target.reset();
  refresh();
});

document.querySelector("#newInstallForm").addEventListener("submit", async event => {
  event.preventDefault();
  if (!updateInstallPortState()) {
    toast("Port in use. Select a new port");
    return;
  }
  const payload = Object.fromEntries(new FormData(event.target).entries());
  if (payload.folder_name && !payload.name) payload.name = payload.folder_name;
  if (payload.folder_name) payload.path = "";
  payload.queryPort = Number(payload.queryPort || 15637);
  const button = event.target.querySelector("button[type=submit]");
  button.disabled = true;
  const statusPanel = document.querySelector("#installStatus");
  statusPanel.classList.remove("hidden", "complete", "failed");
  document.querySelector("#installStatusText").textContent = "Starting install";
  document.querySelector("#installStatusDetail").textContent = "Preparing the install job.";
  try {
    const started = await api("/api/instances/install", { method: "POST", body: JSON.stringify(payload) });
    newInstallDirty = false;
    newInstallDirectoryDirty = false;
    pollInstallJob(started.job_id, button);
  } catch (err) {
    button.disabled = false;
    statusPanel.classList.add("failed");
    document.querySelector("#installStatusText").textContent = "Install failed";
    document.querySelector("#installStatusDetail").textContent = err.message;
  }
});

document.querySelector("#newInstallForm").addEventListener("input", event => {
  const form = event.currentTarget;
  if (event.target.name === "folder_name") {
    newInstallDirectoryDirty = true;
  }
  if (event.target.name === "name" && !newInstallDirectoryDirty) {
    form.folder_name.value = event.target.value;
  }
  newInstallDirty = true;
  updateInstallPortState();
});

document.querySelector("#newInstallForm").addEventListener("change", event => {
  if (event.target.name === "folder_name") {
    newInstallDirectoryDirty = true;
  }
  newInstallDirty = true;
  updateInstallPortState();
});

async function pollInstallJob(jobId, button) {
  if (installPoll) clearInterval(installPoll);
  const tick = async () => {
    const statusPanel = document.querySelector("#installStatus");
    try {
      const data = await api(`/api/jobs?id=${encodeURIComponent(jobId)}`);
      const job = data.job;
      const others = (state.install_jobs || []).filter(item => item.id !== job.id);
      state.install_jobs = [job, ...others];
      renderInstallJobs();
      if (job.status === "complete") {
        clearInterval(installPoll);
        installPoll = null;
        if (job.result && job.result.instance && job.result.instance.id) {
          activeInstanceId = job.result.instance.id;
          localStorage.setItem("esm_active_instance_id", activeInstanceId);
        }
        toast("Server installed and ready for config");
        refresh();
      }
      if (job.status === "failed") {
        clearInterval(installPoll);
        installPoll = null;
      }
    } catch (err) {
      clearInterval(installPoll);
      installPoll = null;
      button.disabled = false;
      statusPanel.classList.add("failed");
      document.querySelector("#installStatusText").textContent = "Install status unavailable";
      document.querySelector("#installStatusDetail").textContent = err.message;
    }
  };
  await tick();
  installPoll = setInterval(tick, 1500);
}

document.querySelector("#instanceSelect").addEventListener("change", async event => {
  if (!event.target.value) return;
  if ((serverConfigDirty || accountsDirty) && !confirm("Discard unsaved config edits and switch instances?")) {
    event.target.value = selectedInstanceId() || "";
    return;
  }
  serverConfigDirty = false;
  accountsDirty = false;
  updateActionDirty = false;
  webhookDirty = false;
  editingWebhookId = "";
  activeInstanceId = event.target.value;
  localStorage.setItem("esm_active_instance_id", activeInstanceId);
  refresh();
});

document.querySelector("#updateAction").addEventListener("change", async event => {
  updateActionDirty = true;
  try {
    await api("/api/instances/update", {
      method: "POST",
      body: JSON.stringify({ instance_id: selectedInstanceId(), update_before_start: event.target.checked }),
    });
    updateActionDirty = false;
    toast("Update check preference saved");
    refresh();
  } catch (err) {
    toast(err.message);
  }
});

document.querySelector("#loginForm").addEventListener("submit", async event => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.target).entries());
  try {
    await api("/api/auth/login", { method: "POST", body: JSON.stringify(body) });
    login.classList.add("hidden");
    app.classList.remove("hidden");
    await refresh();
    startAutoRefresh();
  } catch (err) {
    document.querySelector("#loginError").textContent = err.message;
  }
});

document.querySelector("#inviteRedeemForm").addEventListener("submit", async event => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.target).entries());
  try {
    await api("/api/invites/redeem", { method: "POST", body: JSON.stringify(body) });
    login.classList.add("hidden");
    app.classList.remove("hidden");
    await refresh();
    startAutoRefresh();
  } catch (err) {
    document.querySelector("#inviteError").textContent = err.message;
  }
});

function prefillInviteFromUrl() {
  const params = new URLSearchParams(location.search);
  const code = params.get("invite") || params.get("code");
  if (!code) return;
  const form = document.querySelector("#inviteRedeemForm");
  form.code.value = code;
  form.username.focus();
}

async function boot() {
  prefillInviteFromUrl();
  const auth = await api("/api/auth/state").catch(() => ({ authenticated: false }));
  if (auth.authenticated) {
    app.classList.remove("hidden");
    await refresh();
    startAutoRefresh();
  } else {
    login.classList.remove("hidden");
  }
}

boot();
