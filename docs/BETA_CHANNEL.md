# Windows beta channel

Starting with 0.9.6.3a/b, **Manager > Run beta version** selects the channel
used by **Check for Updates** immediately. No separate **Save Manager Settings**
step is required. Check for Updates saves only the channel choice, leaving other
unsaved Manager fields alone.

1. Check **Run beta version** for beta, or uncheck it for stable.
2. Click **Check for Updates**.
3. Click **Download, Install & Restart** and confirm.
4. Keep the progress dialog open. ESM-Z downloads, verifies, installs, restarts,
   and reconnects the browser automatically. Check the running version in the header.

To return from beta to its paired stable version, first disable EML on every
managed instance. Stable contains no EML integration; beta retains the Mods tab.
The checkbox selects Windows beta releases and excludes the Linux alpha channel.
Running game servers and remote login sessions are preserved by manager updates.

Existing 0.9.6.2a/b users can install this fix using their current channel's
updater; no manual restart is needed. Older managers require the one-time
activation described in [Remote Updates](REMOTE_UPDATES.md).

## Upgrading from 0.9.6 or earlier

The old updater compares only three numeric version components. Install
0.9.6.1a manually once: stop ESM-Z, back up the existing installation, extract
the package over it while preserving `enshrouded_manager/data`, and restart.
The corrected updater then distinguishes 0.9.6.1a from 0.9.6.1b.

The stable package has no EML integration or third-party EML binary.

## Remote updates from 0.9.6.2a/b

After this updater has been activated, Download & Install Update also restarts
ESM-Z and reconnects the browser automatically. It preserves the selected channel;
beta retains Mods and stable does not acquire it. Installing this updater through
an older manager still requires one final manual restart. See [Remote Updates](REMOTE_UPDATES.md).
