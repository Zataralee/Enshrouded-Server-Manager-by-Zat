Zat Shock Tuning 0.3.0-alpha.1 - NEAREST FIRST AND FAN-OUT SERVER TEST

This build implements nearest-first branching for eternal lightning arrows
(levels 20/36/45) and an opt-in replacement for propagation in the five player
chain-lightning spells. Requires upstream EML 0.2.0 and game revision 1273043.
Defaults leave the new behavior disabled and preserve vanilla gameplay.

PROPAGATION
Each spreader chooses the nearest eligible enemies within its own spread_radius,
using 3D position distance. An equally distant tie uses the entity ID. The query's
internal enumeration order no longer decides which enemy is struck first.
There is no additional line-of-sight test; distance and enemy eligibility decide.

targets_per_spread = 1 gives a linear chain. At 3, the initial victim can hit
three enemies; each of those can hit three more, then those can spread again.
All parents in a generation submit their hits before an engine update permits
the next generation. Different branches reserve pending targets immediately and
share native completed-hit history, so converging branches do not double-hit.
The initial victim and allies are excluded. Separate shots/casts have separate
state. A killing hit can spread from its recorded pre-damage position.

max_jumps counts TOTAL secondary targets across the whole chain, excluding the
initial hit. It is not a generation/depth limit or a separate allowance per branch.
0 removes the configured total-target limit. targets_per_spread = 0 disables
secondary propagation. An arrow rolls chance_percent once when starting a chain,
not once for every branch. Direct-hit and secondary damage remain independent.

CONFIGURE ARROWS
Under arrow_chain, edit the tier you use. Example:
    eternal_45 = { enabled = true, chance_percent = 100, spread_radius = 7.0,
                   damage = 0.5, max_jumps = 0, targets_per_spread = 3 },
Keep your existing radius/damage/chance values if preferred; add the new
targets_per_spread key to your saved profile. Old profiles missing it use 1.

CONFIGURE SPELLS
Under chain_lightning, add or edit:
    propagation = { enabled = true, targets_per_spread = 3, max_jumps = 0 },
The existing chain_lightning.spread_radius controls every spreader's radius.
The five spells retain their existing targeting, damage, mana and native stamina
effect settings. Unrelated sequences using the same game program retain their
original path: only the selected player casting sequence opts into this behavior.
An old config missing propagation keeps the original spell behavior.

NATIVE LIMITS
There are no added balance caps on radius, damage, fan-out or max_jumps. Values
must be finite, nonnegative and representable in the appropriate native type;
probability is 0..100 percent. Numeric validity does not guarantee runtime safety.

This asset-only Impact implementation has finite native storage. Pending
spreaders use a reusable circular queue within the game's 16-bit data offsets.
With all three arrow tiers enabled, fan-out 3 and unlimited total targets, this
build holds 996 pending arrow spreaders; the spell program holds 989. Finite
max_jumps and linear profiles allocate smaller queues. The actual capacity is
printed in the EML log on Apply. It is NOT a total-victim limit: slots are reused
and the modeled bytecode traverses a 1,100-target line. An exceptionally wide
frontier stops if the queue fills, before writing outside native storage.

The original arrow's five-second lifetime remains in effect, so a sufficiently
long chain may end when the projectile expires. This build does not promise
map-wide propagation. Only loaded/queryable targets can be selected. If native
history fails to record a queued victim, propagation stops to avoid repeats.
Large radii, crowded queries and branching can create substantial server work.

OTHER SETTINGS RETAINED
- Five chain-lightning spells: targeting range, raw damage coefficient, mana.
- All 11 eternal arrows: independent direct-hit coefficients and original types.
- Existing Mass Destruction skill: radius and damage per Intelligence.
New circular AOE for other arrow types, damage falloff, global shock debuffs and
stun controls are not included. No client resources or native DLLs are bundled.

INSTALL OR UPGRADE ENTIRELY THROUGH ESM-Z
1. Stop the game server. Keep a copy of your current src/config.lua text.
2. Server Setup & Config > Mods: remove the old Zat Shock Tuning mod if installed.
   The manager rejects duplicate IDs; removing it deletes that stored config.
3. Upload this ZIP intact, enable the mod, then open Configure > src/config.lua.
4. Restore your tuning and add targets_per_spread to the arrow profiles, and/or
   the spell propagation block. The old settings remain compatible.
5. Save, Apply & Validate Mods, inspect the EML log, and start the game server.
No server desktop access, compiler or manual archive editing is needed.
The mod reads src/config.lua; config.defaults.lua is a backup to copy from.

VALIDATION AND COMBAT CHECK
Automated tests execute the emitted instructions with modeled native calls,
including far-first enumeration, elevation, three-then-nine branching, converging
branches, killed victims, full-width IDs, queue reuse, budgets and failure paths.
They do not establish live combat timing, damage authority or VFX replication.
Use a test world and unmodified clients first. Check actual health loss on the
nearest enemies, then on each branch's children beyond the first victim's radius.
Confirm no repeat hits and that ordinary/disabled arrows still work. Repeat with
a chain-lightning spell and with two players casting/shooting independently.

Baseline guards reject unsupported builds and conflicting resource edits. To
restore, stop the server, disable/remove this mod in ESM-Z, apply remaining mods,
and restart. Preserve your config text before removing or upgrading.
