# EML-compatible mods

Optional **Enshrouded Mod Loader (EML)** integration is part of the full Windows
stable release starting with **0.9.6.5a**. The package includes the unmodified
upstream EML/EMM CLI 0.2.0, its GPL-3.0 license, and corresponding source archive.
ESM-Z verifies the bundled executable's pinned SHA-256 before running it.

## Which mods work here?

Use mods explicitly made for **EML**, packaged as a self-contained **Lua patch
mod ZIP** with exactly one `mod.json` and a `src/mod.lua` entry point. A wrapper
folder is accepted. The manifest must declare `capabilities: ["patch"]`.

A ZIP extension or an Enshrouded download category does not establish EML
compatibility. Check the mod author's requirements for EML support, game version,
server suitability and any matching client installation. ESM-Z does not verify
that a particular mod is server-only or safe for multiplayer.

Native DLL loaders, executable installers, runtime/export mods and automatic
dependencies are not supported by this integration. Upload limits are 32 MiB,
128 MiB expanded, and 2,000 entries. Invalid or incompatible packages are rejected.

## Install and configure

1. Sign in with **Mods** permission and select an assigned or owned server.
2. Stop that server and open **Server Setup & Config > Mods (EML)**.
3. Enable EML for the selected server. Use a clean installation without another
   loader or unmanaged mods.
4. Select an **EML Lua patch mod ZIP** from the computer using the browser, then
   click **Upload EML Mod**. The uploaded mod starts disabled.
5. Review **Configure**, the author's documentation and client requirements,
   then enable the mod and click **Apply & Validate Mods**.
6. Use **Download EML Log** to save the complete patch log and open it locally.
   This requires **Logs** permission and is also available as `esm-eml.log` under **Logs**.
7. Start the server after validation succeeds. Enabled mods are reapplied before
   subsequent starts; a failed patch blocks startup.

Disabling EML restores the original game index. Steam validation restores original
assets first and records recovery state if interrupted. Backups from another game
build are never restored. Do not change the installation directory while EML is active.

Back up `enshrouded_manager/data/eml` as well as world saves. It contains imported
mods, edited configurations and original game indexes; ordinary world backups do
not include it. See [channel switching](BETA_CHANNEL.md) when coming from an older beta.

## Account permissions

From 0.9.6.7a/b, admins can select **mods** under **Account > Users** and in invite
type permissions. Ordinary users need both Mods permission and a server assignment.
The permission covers mod status, upload, configuration, enable/disable, removal,
EML enable/disable for the selected server, and Apply & Validate Mods. Stop the
selected server before making changes; stopping/starting it requires Control permission.

Admins have every permission. New server-owner accounts and accounts promoted to
server owner receive Mods by default. The first upgrade also grants Mods to existing
admins, server owners, owner invite profiles and outstanding owner invite codes.
This migration runs once, preserving any later explicit owner revocation. Owners
remain limited to their owned or assigned servers. Global EML tool check/install/
rollback controls remain administrator-only because they affect every server.
