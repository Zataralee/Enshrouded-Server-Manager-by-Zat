# EML tool updates

Administrators can open **Server Setup & Config > Mods (EML) > EML Updates**.
The panel shows installed and latest stable upstream EML versions, last check,
verification failures, and a link to the upstream release notes.

ESM-Z checks the official Brabb3l/kfc-parser GitHub releases every six hours in
its own background thread. **Check for EML Updates** checks immediately.
Checks never install or run a new tool. **Install EML Update** is explicit and
uses the version shown in the panel; changed upstream selections require another check.

An installation downloads only the upstream Windows `emm.exe`, verifies its
GitHub SHA-256 digest, retains the matching upstream source archive and license,
and checks the tool's version and required command-line options. TLS validation
remains enabled. An asset without a published digest cannot be installed, except
for the original bundled version whose checksum is already pinned.

The verified tool is stored in a new immutable directory under
`enshrouded_manager/data/eml_runtime`. An atomic pointer changes the selected
version only after verification succeeds. The bundled tool and previous installed
tool remain available. **Roll Back EML** verifies and selects the previous tool;
the original bundle is the fallback when there is no earlier installed update.
Manager updates preserve this data alongside accounts, configurations and saves.

Tool selection affects subsequent mod operations. Installing or rolling back the
tool does not patch game assets, stop/restart a game server, enable mods, or edit
mod configurations. Every tool invocation verifies the selected executable again.

## Game updates and mods

An EML tool update and a mod compatibility update solve different problems.
Each mod must support the installed game revision. A message such as
`Unsupported game revision 1287369; supported revisions: 1273043, 1285601` is a
mod's compatibility guard. Update and validate that mod package; installing a
new EML tool does not remove its guard or establish compatibility.

Before replacing a mod ZIP, back up its edited configuration from Configure.
The current mod importer rejects duplicate mod IDs, so replacing a ZIP requires
removing that mod and then importing the new package. Restore its configuration
before applying. Companion mods must be upgraded together when their author
requires matching versions. Leave the game stopped until ready to test it.
