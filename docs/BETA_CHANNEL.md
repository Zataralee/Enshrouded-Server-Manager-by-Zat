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

## EML beta operation

The beta package bundles the unmodified upstream `emm.exe` 0.2.0, its GPL-3.0
license, and matching upstream source archive. No proxy DLL or loader fork is
installed. ESM-Z verifies the binary's pinned SHA-256 before invoking the CLI.

1. Select an installed dedicated server and stop it.
2. Open **Server Setup & Config > Mods (Beta)** as an administrator.
3. Choose **Enable EML**. Existing proxy loaders or unmanaged mods must be
   removed from this installation first. Keep a separate copy if you use them.
4. Download a compatible EML Lua patch mod from Nexus Mods or its author's
   release page. Upload its ZIP from your browser, including when accessing
   ESM-Z from another computer. Nothing needs to be copied manually to the host.
5. Use **Configure** if the mod exposes settings in Lua, JSON, TOML, INI, CFG,
   or text files. Enable the mod, then **Apply & Validate Mods** to review errors
   before starting. Enabled mods are also reapplied before every server start.
6. Check the mod author's multiplayer requirements. The dashboard labels client
   requirements unverified; server-side installation does not prove server-only
   compatibility.

This beta accepts one mod per ZIP, with `mod.json` and `src/mod.lua`, either at
ZIP root or under a wrapper folder. Limits are 32 MiB uploaded, 128 MiB expanded,
and 2,000 entries. Only self-contained mods with `capabilities: ["patch"]` are
supported. Native DLL mods, runtime/export mods, and automatic dependencies are
not supported. Installing a ZIP does not automatically enable it.

All mod changes require an administrator and a stopped server. Server startup
is blocked if EML fails. The original game index is saved under manager data,
restored when mods are disabled/removed, and restored before Steam validation.
Backups from another game executable are never restored. An interrupted Steam
validation requires a successful **Dashboard > Update Check** before launch.
Extra EML-generated containers can remain on disk after restoring the original
index, but the restored game does not reference them.

Keep backups of `enshrouded_manager/data/eml` as well as world saves: this
contains imported packages, edited configurations, and original game indexes.
The ordinary world-backup feature does not include mod packages. Do not change
the instance directory or edit active mod files outside ESM-Z while EML is in use.

## Validation for 0.9.6.1b

On an isolated copy of dedicated server build 25988414 (Enshrouded 1.0), EML
changed a BalancingTable stamina value from 100 to 123. Independent extraction
confirmed the patched value; the dedicated server reached its online state.
Disabling EML restored the original index with an identical SHA-256. The
dashboard configuration editor was also exercised. These checks establish the
loader lifecycle, not multiplayer correctness of individual third-party mods.

## Remote updates from 0.9.6.2a/b

After this updater has been activated, Download & Install Update also restarts
ESM-Z and reconnects the browser automatically. It preserves the selected channel;
beta retains Mods and stable does not acquire it. Installing this updater through
an older manager still requires one final manual restart. See [Remote Updates](REMOTE_UPDATES.md).
