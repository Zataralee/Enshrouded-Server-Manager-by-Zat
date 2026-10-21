# Windows beta channel

Version 0.9.6.1a adds **Manager > Run beta version**. Save the setting, choose
**Check Now**, then **Download & Install Update** and restart ESM-Z. Installation
remains manual. The checkbox selects Windows beta releases and excludes the
separate Linux alpha channel.

Version 0.9.6.1b adds **Server Setup & Config > Mods**. Mod installation is an
administrator operation because mod packages execute code on the server host.
Players may still need EML and matching mods on their own computers.

To return to the paired stable version, disable modding on each managed server
first, uncheck **Run beta version**, save, check, install, and restart ESM-Z.
Server worlds and manager data are preserved by manager updates.

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
