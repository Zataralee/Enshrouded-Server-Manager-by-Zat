Zat Shock Tuning 0.2.0-alpha.3 - DIAGNOSTIC SERVER TEST

ALPHA.3 SINGLE-HOP DIAGNOSTIC
Alpha.2 was reported to restore direct damage, but stop after one secondary hit.
The native ApplyDamage function queues work; alpha.2 checked hit history before
allowing an engine update. Alpha.3 yields once before that check. The original
damage path and ammunition alias are unchanged. This is a targeted diagnostic,
not the requested branching implementation. Nearest-first selection, fan-out,
and new spell propagation controls are NOT included.

A game update between hits is modeled in the regression harness. The alpha.2
package reproduces the single-hop result in that model. The real server update
order still requires a combat retest. If it still stops, do not remove the
history guard: it prevents re-hitting targets when history is unavailable.

The original arrow has a finite lifetime. max_jumps = 0 removes the configured
count limit; this diagnostic cannot promise a map-spanning or indefinitely
living chain. A separate propagation lifecycle is still under investigation.

ALPHA.1 DAMAGE REGRESSION FIX
Do not use alpha.1 with chains enabled. Its ammunition check loaded an ItemId
wrapper using a native instruction that rejects that type, aborting the shared
projectile program before direct damage. Enabling even one tier affected other
projectiles using that program. Alpha.2 reads the ItemId's uint32 value through
an alias at the same runtime storage address. Your existing config remains valid;
no reduction in damage, radius or jump count is required for this fix.

The original alpha.1 package fails the new native-type regression check using
the reported settings; alpha.2 passes. Live multiplayer damage and chaining must
still be retested. Until upgrading, setting all arrow_chain enabled flags to
false, applying and restarting removes the faulty shared-program patch.

Requires ESM-Z beta with upstream EML 0.2.0 and Enshrouded internal revision 1273043.
Other game revisions are rejected before any changes. See the EML log for the
reported revision. Do not bypass the check when a game update changes it.

This is an asset patch for initial server-only testing. No client installation
is requested for that test. Multiplayer authority, visual consistency, and
server-only gameplay are NOT yet certified. Starting successfully does not
establish that unmodified clients use the changed values.

WHAT WORKS IN THIS PROTOTYPE
- Experimental eternal lightning-arrow chains: levels 20/36/45 independently
  enable a chain after an unblocked enemy hit. Per-tier chance, spread radius,
  secondary attack coefficient and optional maximum jumps. Disabled by default.
  This is implemented behavior awaiting real multiplayer combat verification.
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
Branching/fan-out; nearest-target ordering; new spell propagation controls;
new circular shock AOE on hit; circular AOE activation probability;
per-jump damage falloff; global shock/debuff changes; stun strength changes;
new wands, melee effects, skills, items, or visual assets.

ARROW CHAIN ALPHA
In src/config.lua, find arrow_chain and set enabled = true for the arrow tier
you use. For a first test, keep chance_percent = 100, spread_radius = 7.0 and
damage = 0.5; optionally set max_jumps = 2 to make the expected count clear.
max_jumps counts SECONDARY enemies; 0 removes the user-selected count limit.
These values are a test profile, not enforced maximums. A chance of 0 or spread
of 0 disables that tier's chain behavior. Each tier can have different numbers.

The search moves to each successive victim. Direct-hit damage remains in
lightning_arrows; changing chain damage does not alter that setting or spell
damage. Chain damage uses the arrow's existing combat context, with its own
raw attack coefficient and no secondary critical roll or extra mana cost.
Final health loss still depends on the game and the victim's defenses.

This diagnostic yields after each secondary damage request before checking
history. It does not reproduce the spell's timed hop cadence. It reuses the native
lightning-link visual, with no new asset IDs. It does not enlarge the flying
arrow's collider. Ground hits, blocked hits and unrelated ammunition retain
their original paths. The chain uses enemy checks and the game's hit history;
it stops if a secondary hit fails to be recorded. It does not reset hit history.
No custom terrain damage or circular explosion is added. Wall occlusion and
native root/collider deduplication still need gameplay verification.

The existing projectile program is shared, so mods editing it can conflict.
Baseline checks refuse an already changed program. Having no new IDs does NOT
prove unmodified clients execute the new branch or display identical effects.
No live combat was exercised by automated checks. If chaining does not occur,
record whether direct damage changed and whether either player saw a link;
do not assume an invisible effect means no server damage, or vice versa.

There is no added balance cap on jump/range/damage settings. The original
projectile lifetime and native storage still apply. Very large ranges can
produce substantial query work. No crash-free upper bound is
known; the validator checks storage and semantics, not live server performance.

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

UPGRADING FROM 0.1.0, 0.1.1 OR 0.2.0-alpha.1 THROUGH THE BROWSER
Existing keys/defaults are unchanged. An old config without arrow_chain is
accepted with chains disabled. An old config without eternal_arrows leaves the
eight ice/fire/bone coefficients at vanilla values.
Stop the server. Copy your current src/config.lua text to retain your settings.
Remove the old mod through ESM-Z, upload the new ZIP, enable it, and paste your
saved settings into Configure > src/config.lua. To use chains, merge your old
settings into the new config so the arrow_chain section is retained.
Save, Apply & Validate Mods, start.
The current manager does not replace an installed mod through a duplicate upload.
No server machine access is needed. Removing a mod deletes its stored config,
so keep the copied text before removing it. No server has been upgraded for you.

To restore defaults, copy all contents of src/config.defaults.lua into src/config.lua.
The defaults file is documentation only; the mod reads src/config.lua.
Keep a copy of your edited config before upgrading/re-uploading the mod.

FIRST CONTROLLED TEST
Arrow chains: use two unmodified clients on an isolated server and take turns
shooting. Arrange enemies A--B--C so C is outside A's radius but within B's.
At 100% chance and max_jumps = 2, verify two secondary victims, correct health
loss and links. Repeat at max_jumps = 1, 0% chance, and then unlimited with two
enemies to check that they never bounce indefinitely. Check allies, blocked
shots, killing shots and ordinary arrows. Confirm that changing each tier's
damage/radius only affects that tier. Test a 25% chance over many eligible hits.
Report server/client revision, equipment, skills, config and both viewpoints.

Existing scalar controls:
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
