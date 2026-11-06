# Manager startup and update handoff

An update restarts ESM-Z in the background. The original console can close while
the new manager remains available in the browser. Launching the shortcut again
prints the existing manager URL and exits successfully instead of starting a
second copy or triggering the launcher's Python fallback.

ESM-Z holds an operating-system file lock for its data directory before reading
or migrating configuration, scheduling servers, or binding its HTTP listener.
The lock remains owned until the manager process actually exits. A crash releases
the OS lock automatically; the existence of `data/manager.lock` alone does not
mean a manager is running. Do not delete lock files to bypass ownership.

On Windows, the HTTP listener also uses exclusive address ownership. Another
installation cannot share its listening address and port.

The update helper reserves a separate startup gate before the current manager
shuts down. It holds this reservation through file replacement and successor
health checks, including rollback. Only the helper's successor receives the
matching handoff token. Manual launches during the handoff exit with an update
message. The helper waits for the old process to exit; it does not kill manager
or game-server process trees. If that process lingers, it reports the failure and
leaves installed files unchanged.

These protections take effect when this version runs. During the first upgrade
from an older release, let its existing updater finish before launching another
manager manually. Existing duplicates from older versions still need to be
closed once; the update does not terminate arbitrary older processes.
