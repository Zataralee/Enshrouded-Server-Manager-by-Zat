Zat Shock Tuning 0.1.1 - SERVER TEST PROTOTYPE

Requires ESM-Z beta with upstream EML 0.2.0 and Enshrouded internal revision 1273043.
Other game revisions are rejected before any changes. See the EML log for the
reported revision. Do not bypass the check when a game update changes it.

This is an asset patch for initial server-only testing. No client installation
is requested for that test. Multiplayer authority, visual consistency, and
server-only gameplay are NOT yet certified. Starting successfully does not
establish that unmodified clients use the changed values.

WHAT WORKS IN THIS PROTOTYPE
- Chain lightning: initial targeting range, propagation sphere radius, five
  spell variants' raw damage coefficients and mana costs.
- All 11 eternal arrow variants: independent direct-hit damage coefficients.
  Ice levels 10/28/45, fire 15/28/45, lightning 20/36/45, and bone 36/45.
  The lightning_arrows section retains the original lightning settings;
  eternal_arrows contains the eight ice/fire/bone settings. Each defaults to 0.5.
  Damage types are preserved: ice, fire, lightning, and physical blunt for bone.
- Existing Mass Destruction skill: AOE radius and damage per Intelligence.
  Its staff/wand critical-hit requirement and skill requirement remain intact.

NOT INCLUDED YET
New random shock AOE on hit; AOE activation probability; maximum chain jumps;
per-jump damage falloff; global shock/debuff changes; stun strength changes;
new wands, melee effects, skills, items, or visual assets.

INSTALL THROUGH ESM-Z
1. Back up your world and use a test instance or a test copy of it initially.
2. Stop the game server. ESM-Z may keep running.
3. Open Server Setup & Config > Mods, and enable EML if necessary.
4. Upload the ZIP intact. Enable "Zat Shock Tuning - Server Test".
5. Configure > src/config.lua. Defaults preserve vanilla gameplay, so leave
   them unchanged for the first validation. Do not edit src/mod.lua.
6. Apply & Validate Mods. Check the EML log for the Zat Shock Tuning validation
   message and for errors. Zero setting changes with the defaults is expected.
7. Start the server and join with an unmodified client.

CONFIGURATION
Stop the server before editing. Use Configure > src/config.lua, save the file,
Apply & Validate Mods, and start again. The config comments suggest tuning ranges;
these are NOT enforced balance caps. Values above those suggestions are accepted.
Only numeric validity is enforced: finite nonnegative numbers (zero is accepted),
integer values for integer fields, and values
representable in the game's float32/signed32/unsigned32 storage as applicable.
Unknown or missing settings and incompatible game data are still rejected.
Representation checks cannot guarantee crash-free gameplay: very large queries
can be expensive and later damage calculations can overflow. No universal safe
maximum has been established; increase values incrementally in a test world.

UPGRADING FROM 0.1.0 THROUGH THE BROWSER
This release removes the previous balance caps and adds eight arrow settings.
Existing keys/defaults are unchanged; an old config without eternal_arrows is
accepted and leaves those additional arrows at vanilla values.
Stop the server. Copy your current src/config.lua text to retain your settings.
Remove the old mod through ESM-Z, upload the new ZIP, enable it, and paste your
saved settings into Configure > src/config.lua. To tune the new arrows, merge your
previous settings into the new config so its eternal_arrows section is retained.
Save, Apply & Validate Mods, start.
The current manager does not replace an installed mod through a duplicate upload.
No server machine access is needed. Removing a mod deletes its stored config,
so keep the copied text before removing it. No server has been upgraded for you.

To restore defaults, copy all contents of src/config.defaults.lua into src/config.lua.
The defaults file is documentation only; the mod reads src/config.lua.
Keep a copy of your edited config before upgrading/re-uploading the mod.

FIRST CONTROLLED TEST
1. With vanilla config, cast the same chain spell on a repeatable group with
   fixed equipment, skills and difficulty. Record secondary targets and damage.
2. Stop the server and change ONLY spread_radius from 7.0 to 10.0. Apply and
   restart. Repeat with two unmodified clients, taking turns as the caster.
3. Check enemies outside the original reach as well as health loss, not merely
   the lightning graphics. If behavior does not change, report it; do not
   assume the patch failed solely from a client tooltip.
4. Restore radius 7.0, then separately test eternal_10.damage 1.12 -> 1.68
   (only when using that exact spell), or the appropriate spell's coefficient.
5. Test Mass Destruction separately with its skill active and a staff/wand
   critical hit. Do not expect this setting to add AOE to arrows.
6. Record game revision, mod config, spell/weapon, character skills, observed
   target count, damage, client installation state, and both players' results.

CONFLICTS AND RESTORE
Test alone first. Mods changing these same items, sequences, skill or Impact
program may conflict. The mod checks vanilla values before applying its edits;
some other mod load orders can still overwrite this mod afterward.
ESM-Z restores the original index and reapplies enabled mods from baseline.
Do not manually multiply already patched game archives or delete backup files.
To uninstall: stop server, disable/remove this mod in ESM-Z, apply remaining
mods if any, then start. Disable EML to return all managed patches to vanilla.
Do not restore a backup from a different game build; use Steam validation.

No altered game archives, game executable, EML executable, or native DLL is in
this ZIP. The package contains only the mod's scripts, configuration and docs.
