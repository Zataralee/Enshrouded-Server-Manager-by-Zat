/* Admin-only controls for the selected dedicated server's upstream EML adapter. */
(() => {
  const element = id => document.getElementById(id);
  let snapshot = {}, busy = false, selected = "", editor = null, editingDirty = false;
  const query = id => `instance_id=${encodeURIComponent(id)}`;
  const modQuery = () => `${query(editor.instanceId)}&mod_id=${encodeURIComponent(editor.modId)}`;

  function controls() {
    const stopped = selected && !state.server?.running && !busy && isAdmin();
    element("emlToggle").disabled = !stopped;
    element("emlApply").disabled = !stopped || !snapshot.enabled;
    element("modUploadButton").disabled = !stopped;
    element("modConfigSave").disabled = !stopped || editor?.instanceId !== selected;
    element("emlToggle").textContent = snapshot.enabled ? "Disable EML & Restore Game" : "Enable EML";
    element("modList").querySelectorAll("button").forEach(button => { button.disabled = !stopped; });
  }

  async function refreshMods() {
    if (!element("mods").classList.contains("active") || !isAdmin() || busy) return;
    const instanceId = selectedInstanceId() || "";
    if (selected !== instanceId) {
      selected = instanceId;
      snapshot = {};
      editor = null;
      editingDirty = false;
      element("modEditor").classList.add("hidden");
      element("emlLogText").classList.add("hidden");
    }
    controls();
    if (!selected) {
      element("emlStatus").textContent = "Select or install a server to manage mods.";
      element("modList").replaceChildren();
      return;
    }
    try {
      const result = await api(`/api/mods?${query(instanceId)}`);
      if (instanceId !== selectedInstanceId() || busy) return;
      snapshot = result;
      const condition = state.server?.running ? "Server running — stop it to make changes." : "Server stopped.";
      element("emlStatus").textContent = `EML ${result.version}: ${result.installed ? "installed" : "missing"}, ${result.enabled ? "enabled" : "disabled"}. ${condition} ${result.recovery_required ? "Steam validation required." : ""} ${result.last_error || ""}`;
      element("modList").innerHTML = (result.mods || []).map(mod => `
        <div class="panel"><strong>${escapeHtml(mod.name)}</strong> v${escapeHtml(mod.version)} — ${mod.enabled ? "Enabled" : "Disabled"}
          <p>${escapeHtml(mod.multiplayer)}</p>
          <div class="actions">
            <button type="button" data-eml-mod="${escapeHtml(mod.id)}" data-eml-action="${mod.enabled ? "disable" : "enable"}">${mod.enabled ? "Disable" : "Enable"}</button>
            <button type="button" data-eml-mod="${escapeHtml(mod.id)}" data-eml-action="configure">Configure</button>
            <button type="button" data-eml-mod="${escapeHtml(mod.id)}" data-eml-action="remove">Remove</button>
          </div></div>`).join("") || "<p>No mods installed. Upload an EML mod ZIP to begin.</p>";
      controls();
    } catch (error) {
      element("emlStatus").textContent = error.message;
    }
  }

  async function operation(callback) {
    if (busy) return;
    if (!selected || selected !== selectedInstanceId()) { await refreshMods(); toast("Server selection changed. Review the selected server and retry."); return; }
    busy = true;
    controls();
    element("emlStatus").textContent = "Working… keep this page open. Patching may take a few minutes.";
    try { await callback(); }
    catch (error) { toast(error.message); element("emlLogText").textContent = error.message; element("emlLogText").classList.remove("hidden"); }
    finally { busy = false; await refreshMods(); controls(); }
  }

  const post = (route, body) => api(`/api/mods/${route}`, { method: "POST", body: JSON.stringify({ instance_id: selected, ...body }) });
  element("emlToggle").addEventListener("click", () => operation(async () => {
    await post("loader", { enabled: !snapshot.enabled });
    toast(snapshot.enabled ? "Original game restored; EML disabled" : "EML enabled for this server");
  }));
  element("emlApply").addEventListener("click", () => operation(async () => {
    await post("apply", {});
    toast("EML patch completed. Check the log before starting the server.");
  }));
  element("emlRefresh").addEventListener("click", refreshMods);
  element("emlLog").addEventListener("click", () => operation(async () => {
    const result = await api(`/api/mods/log?${query(selected)}`);
    element("emlLogText").textContent = result.content;
    element("emlLogText").classList.remove("hidden");
  }));
  element("modUploadForm").addEventListener("submit", event => {
    event.preventDefault();
    const file = element("modZip").files[0];
    if (!file || !selected || file.size > 32 * 1024 * 1024) { toast("Select a server and a ZIP no larger than 32 MiB"); return; }
    operation(async () => {
      await api(`/api/mods/upload?${query(selected)}`, { method: "POST", headers: { "Content-Type": "application/zip" }, body: file });
      element("modZip").value = "";
      toast("Mod installed and disabled. Review its configuration and client requirements before enabling.");
    });
  });

  async function loadConfig() {
    const file = element("modConfigFile").value;
    if (!editor || !file) return;
    const current = editor;
    const result = await api(`/api/mods/config?${modQuery()}&file=${encodeURIComponent(file)}`);
    if (editor !== current) return;
    element("modConfigText").value = result.content;
    editor.file = file;
    editingDirty = false;
  }
  element("modList").addEventListener("click", event => {
    const button = event.target.closest("[data-eml-mod]");
    if (!button || button.disabled) return;
    const modId = button.dataset.emlMod, action = button.dataset.emlAction;
    if (action === "remove" && !confirm("Remove this mod and its edited configuration?")) return;
    operation(async () => {
      if (action === "configure") {
        if (editingDirty && !confirm("Discard unsaved mod edits?")) return;
        editor = { instanceId: selected, modId };
        const result = await api(`/api/mods/config?${modQuery()}`);
        element("modConfigFile").innerHTML = result.files.map(file => `<option>${escapeHtml(file)}</option>`).join("");
        element("modEditorTitle").textContent = `Configure ${modId}`;
        element("modConfigText").value = "";
        element("modEditor").classList.remove("hidden");
        await loadConfig();
      } else {
        await post("action", { mod_id: modId, action });
        if (editor?.modId === modId) { editor = null; editingDirty = false; element("modEditor").classList.add("hidden"); }
        toast("Mod updated; changes apply on the next server start.");
      }
    });
  });
  element("modConfigText").addEventListener("input", () => { editingDirty = true; });
  element("modConfigFile").addEventListener("change", () => {
    if (editingDirty && !confirm("Discard unsaved mod edits?")) { element("modConfigFile").value = editor.file; return; }
    operation(loadConfig);
  });
  element("modConfigSave").addEventListener("click", () => operation(async () => {
    if (!editor || editor.instanceId !== selected || editor.instanceId !== selectedInstanceId()) throw new Error("Select the original server before saving");
    await post("config", { mod_id: editor.modId, file: editor.file, content: element("modConfigText").value });
    editingDirty = false;
    toast("Mod configuration saved");
  }));
  element("modConfigClose").addEventListener("click", () => {
    if (editingDirty && !confirm("Discard unsaved mod edits?")) return;
    editor = null; editingDirty = false; element("modEditor").classList.add("hidden");
  });
  document.addEventListener("click", event => { if (event.target.closest('[data-tab="mods"]')) refreshMods(); });
  window.addEventListener("beforeunload", event => { if (editingDirty || busy) { event.preventDefault(); event.returnValue = ""; } });
  setInterval(refreshMods, 5000);
})();
