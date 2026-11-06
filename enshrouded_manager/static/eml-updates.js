/* Upstream tool updates are global; mod package compatibility stays independent. */
(() => {
  const el = id => document.getElementById(id);
  let snapshot = {}, busy = false, refreshing = false;
  function render() {
    const installed = snapshot.installed_version || "unknown";
    const available = snapshot.update_available ? `EML ${snapshot.latest_version} is available.` : "No newer EML release found.";
    const checked = snapshot.last_checked ? ` Last checked ${new Date(snapshot.last_checked * 1000).toLocaleString()}.` : " Not checked yet.";
    el("emlUpdateStatus").textContent = `Installed EML ${installed}${snapshot.bundled ? " (bundled)" : ""}. ${available}${checked} ${snapshot.verification_message || ""} ${snapshot.last_error || ""}`;
    el("emlCheckUpdate").disabled = busy || !isAdmin();
    el("emlInstallUpdate").disabled = busy || !isAdmin() || !snapshot.install_available;
    el("emlRollback").disabled = busy || !isAdmin() || !snapshot.rollback_available;
    const url = snapshot.release_url || "https://github.com/Brabb3l/kfc-parser/releases";
    if (url.startsWith("https://github.com/Brabb3l/kfc-parser/releases")) el("emlReleaseNotes").setAttribute("href", url);
  }
  async function refresh() {
    if (!isAdmin() || !el("mods").classList.contains("active") || busy || refreshing) return;
    refreshing = true;
    try { snapshot = await api("/api/eml/updates"); render(); }
    catch (error) { el("emlUpdateStatus").textContent = error.message; }
    finally { refreshing = false; }
  }
  async function action(route, body = {}) {
    if (busy || !isAdmin()) return;
    busy = true; render();
    el("emlUpdateStatus").textContent = route === "check-update" ? "Checking upstream EML releases…" : "Verifying EML update. Current tool remains selected until verification finishes…";
    try {
      snapshot = await api(`/api/eml/${route}`, {method:"POST", body:JSON.stringify(body)});
      if (snapshot.last_error && route === "check-update") toast(snapshot.last_error);
      else toast(route === "check-update" ? "EML update check completed" : `EML ${snapshot.installed_version} selected for subsequent mod operations`);
    } catch (error) { snapshot.last_error = error.message; toast(error.message); }
    finally { busy = false; render(); }
  }
  el("emlCheckUpdate").addEventListener("click", () => action("check-update"));
  el("emlInstallUpdate").addEventListener("click", () => {
    if (snapshot.install_available) action("install-update", {version:snapshot.latest_version});
  });
  el("emlRollback").addEventListener("click", () => {
    if (snapshot.rollback_available) action("rollback");
  });
  document.addEventListener("click", event => { if (event.target.closest('[data-tab="mods"]')) refresh(); });
  window.addEventListener("beforeunload", event => { if (busy) { event.preventDefault(); event.returnValue = ""; } });
  setInterval(refresh, 30000);
})();
