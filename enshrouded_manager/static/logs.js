/* Download files directly with the browser; log contents never enter page state. */
const logDownloads = (() => {
  let context = "", generation = 0, loaded = false, loading = false;
  let files = [], unavailable = [], error = "";
  const element = id => document.getElementById(id);
  const visible = () => element("logs").classList.contains("active");
  const key = () => JSON.stringify([selectedInstanceId() || "", currentUser().id || "", isAdmin(), can("logs")]);

  function syncContext() {
    const next = key();
    if (next === context) return false;
    context = next;
    generation += 1;
    loaded = false;
    loading = false;
    files = [];
    unavailable = [];
    error = "";
    render();
    return true;
  }

  function bytes(size) {
    if (size < 1024) return `${size} B`;
    const units = ["KB", "MB", "GB", "TB"];
    let value = size / 1024, unit = 0;
    while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
    return `${value.toFixed(value < 10 ? 1 : 0)} ${units[unit]}`;
  }

  function render() {
    const allowed = can("logs");
    element("refreshLogs").disabled = loading || !allowed;
    const query = element("logSearch").value.trim().toLowerCase();
    const shown = files.filter(file => `${file.name} ${file.scope}`.toLowerCase().includes(query));
    let status = !allowed ? "Your account does not have log access." : loading ? "Loading file list…" : error;
    if (!status && loaded) {
      status = `${shown.length} of ${files.length} files · ${bytes(files.reduce((sum, file) => sum + file.size, 0))} total`;
      if (unavailable.length) status += `. Some ${unavailable.join(", ")} logs could not be listed.`;
    }
    element("logStatus").textContent = status;
    element("logStatus").classList.toggle("error", !!error);
    const instance = selectedInstanceId() || "";
    element("logList").innerHTML = shown.map(file => {
      const href = `/api/logs/download?log_id=${encodeURIComponent(file.id)}${instance ? `&instance_id=${encodeURIComponent(instance)}` : ""}`;
      const modified = new Date(file.modified);
      const date = Number.isNaN(modified.getTime()) ? "Unknown date" : modified.toLocaleString();
      return `<div class="log-file">
        <div class="log-file-info"><strong>${escapeHtml(file.name)}</strong>
          <small>${escapeHtml(file.scope)} · ${bytes(file.size)} · Modified ${escapeHtml(date)}</small></div>
        <a class="log-download" href="${escapeHtml(href)}" download aria-label="Download ${escapeHtml(file.name)}">Download</a>
      </div>`;
    }).join("") || (loaded && !loading && !error ? `<p class="log-empty">${files.length ? "No files match your search." : "No log files are available yet."}</p>` : "");
  }

  async function load(force = false) {
    syncContext();
    if (!can("logs") || loading || (loaded && !force)) return;
    const requestContext = context, requestGeneration = ++generation;
    loading = true;
    error = "";
    render();
    try {
      const instance = selectedInstanceId() || "";
      const result = await api(`/api/logs${instance ? `?instance_id=${encodeURIComponent(instance)}` : ""}`);
      if (requestGeneration !== generation || requestContext !== key()) return;
      files = result.logs || [];
      unavailable = result.unavailable || [];
      loaded = true;
    } catch (failure) {
      if (requestGeneration !== generation || requestContext !== key()) return;
      error = `Could not load logs: ${failure.message}. Select Refresh to retry.`;
    } finally {
      if (requestGeneration === generation && requestContext === key()) {
        loading = false;
        render();
      }
    }
  }

  element("refreshLogs").addEventListener("click", () => load(true));
  element("logSearch").addEventListener("input", render);
  return {
    open: () => load(),
    contextChanged() { if (syncContext() && visible()) load(); },
  };
})();
