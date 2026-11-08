# Stable and beta channels

## Mods permission update: 0.9.6.7a/b

Sign in as an administrator, open **Manager**, keep **Run beta version** set to
your current channel, then click **Check for Updates** and **Download, Install &
Restart**. Confirm and keep the progress dialog open until reconnection. Verify
**0.9.6.7a** (stable) or **0.9.6.7b** (Windows beta) in the header.

Under **Account > Users**, select **mods** for ordinary users and assign their
servers, then save the account. Existing admins and owners receive Mods on first
upgrade. New admins and owners receive it by default. Existing sessions pick up
permission changes on their next request. Refresh the browser to update tab visibility.
Server owners retain their existing server scope; no additional servers are assigned.
The manager update preserves game-server processes, accounts, sessions and mod data.
No game-server restart is required to enable this permission. Mod changes still
require a stopped selected server. Global EML tool updates remain admin-only.

An older 0.9.6.3b manager can remain on beta and install 0.9.6.7b directly. If you
then want stable, uncheck beta and install 0.9.6.7a. Both include EML. The older
bridge instructions below remain applicable when using historical release packages.

**EML integration is included in the full Windows stable release from 0.9.6.5a.**
Beta is no longer required for EML mods. Both current channels include the same
EML functionality and complete log downloads. Mods must be **EML-compatible,
self-contained Lua patch mod ZIPs**. See [EML Mods](EML_MODS.md).

## Existing EML beta users: move to stable

Managers up to 0.9.6.4b assume that every stable package lacks EML and block a
channel switch while EML is enabled. Use the bridge update to preserve mods:

1. Keep **Manager > Run beta version** checked.
2. Click **Check for Updates**, then **Download, Install & Restart** to install
   **0.9.6.5b**. Wait for the running version in the header to change.
3. Uncheck **Run beta version**, then click **Check for Updates** again.
4. Install **0.9.6.5a** and wait for reconnection. The manager now uses stable.

No EML disable/re-enable or game-server stop is required for this channel switch.
Stored mod packages, edited configurations, EML state, accounts, sessions and
world saves are preserved. The new updater checks whether the target package
actually contains the verified EML integration. Returning to a historical package
without EML still requires disabling EML first.

A manual alternative is to back up the installation, stop only ESM-Z, and extract
the stable package over the program files while preserving `enshrouded_manager/data`.
Start one manager copy afterward. Do not replace live files while ESM-Z is running.

## Stable users and new installs

Leave **Run beta version** unchecked and install 0.9.6.5a normally. EML is optional
and is disabled until an administrator enables it for a stopped server. Existing
EML-enabled servers retain their settings when moving from beta.

Channel selection takes effect with **Check for Updates** without saving unrelated
Manager fields. The updater downloads and verifies the package, restarts ESM-Z,
checks startup health, and reconnects the browser. Game server processes keep running.
See [Remote Updates](REMOTE_UPDATES.md) for recovery and older-updater activation.

## Upgrading from 0.9.6 or earlier

The older updater compares only three numeric version components. Install the
current package manually once, preserving manager data, then use the corrected
in-app updater for subsequent releases.

The Windows beta checkbox does not select the experimental Linux alpha channel.
