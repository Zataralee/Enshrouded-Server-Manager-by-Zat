# Remote Manager Updates

Starting with Windows stable v0.9.6.2a and EML beta v0.9.6.2b, an administrator
can complete subsequent ESM-Z updates from the browser without remote desktop.
Update checks remain notification-only; installation always needs an admin click.

Linux alpha.8 carries the same experimental updater with Linux archive handling
and an independent process session. Its POSIX process-exit path uses pidfd when
available to recognize an exited process even before its parent reaps it.
Real Linux host verification is still needed. It does not install a systemd service.

## First Upgrade

An older running manager cannot use restart functionality it has not loaded yet.
Install the appropriate new stable or beta package using its existing updater,
then restart ESM-Z manually once. Alternatively, stop the manager and extract the
new package over the installation, preserving `enshrouded_manager/data`.
All later compatible updates use the new flow. Versions 0.9.6 and earlier also
need the manual file upgrade described in [Beta Channel](BETA_CHANNEL.md).

## Browser Workflow

1. Open Manager, select the appropriate release channel, and click Check Now.
2. Click Download & Install Update and confirm.
3. Leave the progress dialog open. It waits for existing installs, backups,
   restarts, and other critical operations, then downloads and verifies the package.
4. The independent helper replaces manager files only after the old manager exits.
   ESM-Z restarts on the same address and port; the browser reconnects and reloads.
5. Check the running version in the header. Remote login sessions survive the restart.

New mutations are temporarily rejected during the update. Active operations get
up to ten minutes to finish; if they do not, the update is cancelled before shutdown.
Apply any pending listen-address/port change before starting an update. Release
packages must include a matching SHA-256 checksum and remote restart support.

## Game Servers and Data

The updater never stops or kills game servers. Monitoring and scheduled manager
tasks briefly pause while ESM-Z restarts. Server directories, saves, manager
configuration, accounts, and session data are not replaced by the update.
The restarted manager preserves each instance's desired state instead of applying
the ordinary start-on-manager-launch preference again.

Session tokens are stored only as SHA-256 digests, expire after 24 hours, and
are invalidated on logout, account deletion, or password changes. The first manual
upgrade cannot retain sessions issued by the old in-memory-only session system.

## Recovery

The helper checks that its newly launched process serves the expected version
and process ID. It allows up to 60 seconds for startup. On failure it terminates
only that replacement manager, restores the backed-up manager files, and relaunches
the previous version. Data is not rolled back. New releases must keep persistent
data compatible with the previous release for file rollback to remain safe.

Update status, staged packages, file backups, and helper logs are under
`enshrouded_manager/data/manager_updates`. `update-console.log` captures restarted
manager output; each job contains `helper.log`. If both startup and recovery fail,
the browser reports that it could not reconnect; inspect those host logs.

This release is verified with the standalone Python launcher on Windows, including
real-process success and rollback tests, retained remote login, and browser reload.
It does not install a Windows service or change existing service supervision.
