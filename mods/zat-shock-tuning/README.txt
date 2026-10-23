Zat Shock Tuning 0.4.0-alpha.2 - ETERNAL FIRE ARROW IGNITION AND SPREADING BURNS

BURN DAMAGE FIX AND LINGERING GROUND FIRE (EXPERIMENTAL SERVER TEST)
Alpha.1 set ignoreConsecutiveHits=true, which tells the engine to SKIP enemies
already hit. Alpha.2 sets it false for burn ticks. The explicit ignition ledger
still prevents repeated ignition. Your original damage settings can be retained.
Eternal fire arrows 15/28/45 now have independent fire_arrows profiles. Defaults
are disabled. Old configs without this section keep fire propagation disabled.
Normal impact damage remains intact. The new effect ignites the initial victim
and living hostiles in initial_radius, without a blast, knockback or terrain edit.
After spread_delay_ms, each burning victim chooses up to targets_per_spread
nearest unvisited living hostiles inside ITS spread_radius. Targets can be above,
below or in any direction. No extra line-of-sight test is applied.

Each enemy burns for burn_duration_ms starting from its own ignition. Death,
Soaked or loss of that enemy ends its burn and pending spread; a lost shooter
ends the controller. An initial killing hit can still seed the impact area.
Damage ticks do not trigger additional propagation. Native visual-only burning
buffs are refreshed with a 0.5-second lease, so visuals retire after extinguishing
without removing another spell/arrow's shared visual buff. Untagged enemy sizes
can still take damage and spread, but may not show the size-specific burn visual.

Configure > src/config.lua, under fire_arrows, example:
    fire_45 = {
        enabled = true, chance_percent = 100,
        initial_radius = 3.0, spread_radius = 5.0,
        targets_per_spread = 3, spread_delay_ms = 350, max_jumps = 0,
        burn_duration_ms = 5000, burn_tick_ms = 500,
        burn_damage_multiplier_per_second = 0.2,
        ground_fire_enabled = true, ground_fire_duration_ms = 5000,
        ground_fire_visual_scale = 1.0,
    },
The fire_15 and fire_28 profiles have exactly the same settings.

chance_percent is one roll after a successful, unblocked enemy hit. max_jumps
counts ALL additional ignitions, including initial-area victims, excluding the
original enemy. 0 removes the configured budget. targets_per_spread = 0 disables
later propagation but keeps initial-area ignition. initial_radius = 0 limits the
first ignition to the struck enemy; spread_radius = 0 disables later spread.
burn_duration_ms = 0 disables the burn entirely. Tick/delay 0 means next engine
update, never an unbounded no-wait loop. Delays longer than the remaining burn
cannot propagate after it expires. Recommendations are not balance caps.

LINGERING GROUND FIRE
Optional per tier, disabled by default and when omitted from an old config.
ground_fire_enabled=true creates an ignition area at the initial victim's saved
feet/root position, using initial_radius and ground_fire_duration_ms. It remains
stationary and checks for new living hostile, non-Soaked enemies each update.
Each entrant receives a full independent burn using that arrow's existing damage,
timing and spread settings; it can spread onward. Existing victims are not refreshed
or re-ignited by this same arrow. Entrants share max_jumps and the retained ledger.
No instant explosion or separate damage multiplier is added. Zero ground duration
or initial radius disables the area. A missed/blocked arrow does not create it.

A client-known bonfire visual marks the area. Its horizontal transform scale is
initial_radius * ground_fire_visual_scale; height stays at native scale. A visual
scale of zero hides the flame without disabling ignition. This is an approximate
visual footprint, not an exact radius outline. The effect is anchored at the first
victim's feet, not terrain-conforming: hills, stairs and flying enemies can produce
clipping or floating flames. Native client replication/scaling needs live testing.
The area uses the same 3D sphere query as initial ignition, not a ground collision
mesh or line-of-sight raycast. It cannot spread fire to buildings or terrain.

Ground expiry removes the visual and stops new entrants; existing enemy burns
finish independently. Shooter disappearance and Impact shutdown remove the visual.
The spawned visual is DoNotSave, linked to the arrow for despawn, and has no combat
program/collider. No shared bonfire template or global fire buff is changed.

FIRE DAMAGE AND BOW BONUSES
burn_damage_multiplier_per_second scales the shot's FIRE component per second.
0.2 for 5 seconds supplies approximately one shot's pre-resistance fire damage
over the burn. Tick amounts include elapsed time and the final partial interval;
changing burn_tick_ms changes cadence, not the intended total. Engine rounding,
resistance, immunity and combat attributes still affect actual health loss.
The controller preserves the populated projectile fire component, original
attack coefficient, shooter, weapon category, attack category and damage-scaling
attribute. It excludes physical/ice/shock/poison/terrain components, extra crits,
stagger and mana/stamina costs. This is the native path intended to carry the
bow's Magic Fire Damage and All Fire Damage exactly once, not a manual sum of
melee/magic/ranged modifiers. Each victim uses its own resistance.
The raw fire component and coefficient come from the original shot; native
attributes may still be evaluated at tick time. Exact bow-perk inheritance,
bow swaps and damage credit need live combat verification. Tests do NOT prove
the engine's damage formula. Compare no fire bonuses, each bonus alone, and both.

REAPPLICATION AND NATIVE STORAGE
Each shot has its own burn/controller. Repeated arrows STACK independently;
they do not refresh or replace a previous shot's damage. Two shooters likewise
retain separate source IDs. One shot cannot ignite a victim twice, even at zero
burn strength or when branches meet. This uses an explicit retained ID ledger.
Unlike the shock queue, its visited slots are NOT reused after burn expiry.
The compiled capacity is derived from remaining native 16-bit instruction/data
limits and logged on Apply for your exact configuration.
At capacity, new ignitions stop and all existing burns finish normally. Thus
max_jumps = 0 does not promise an infinite or map-wide fire chain. Only loaded,
queryable hostiles participate. Large radii, many victims or repeated stacking
shots can be expensive for the server. No global gameplay or damage cap is added.

INSTALL THIS UPDATE THROUGH ESM-Z
Stop the server and copy your current config text before removing the old mod.
Upload this ZIP intact under Server Setup & Config > Mods, enable it, and open
Configure > src/config.lua. Restore your previous tuning, keeping the new
fire_arrows section, then enable the fire tier you want to test. Save, Apply &
Validate Mods, inspect the log and start the server. No server desktop access is
needed. config.defaults.lua is the shipped backup. Unmodified-client multiplayer
combat and visual replication remain test requirements, not verified guarantees.

EXISTING LIGHTNING AND SCALAR FEATURES

This build implements nearest-first branching for eternal lightning arrows
(levels 20/36/45) and an opt-in replacement for propagation in the five player
chain-lightning spells. Requires upstream EML 0.2.0 and game revision 1273043.
Defaults leave the new behavior disabled and preserve vanilla gameplay.

PROPAGATION
Each spreader chooses the nearest living hostile enemies within its own spread_radius,
using 3D position distance. An equally distant tie uses the entity ID. The query's
internal enumeration order no longer decides which enemy is struck first.
There is no additional line-of-sight test; distance and enemy eligibility decide.
Candidates must exist, not have the Dead state, and have positive current HP.
Queries include every faction; hostility is tested against the caster, without
matching the initial victim's faction or species. The chosen ID is stored exactly
without reopening the query by index. Query order cannot substitute another ID.

targets_per_spread = 1 gives a linear chain. At 3, the initial victim can hit
three enemies; each of those can hit three more, then those can spread again.
spread_delay_ms = 250 waits 0.25 seconds before the first spread and between
generations. 100 is faster; 500 is slower. Whole milliseconds, 0..4294967295;
0 still yields one engine update for damage processing. Missing settings use 250.
All parents in a generation submit their hits before the next generation waits. Different branches reserve pending targets immediately and
share native completed-hit history, so converging branches do not double-hit.
The initial victim and allies are excluded. Separate shots/casts have separate
state. After each delay, surviving spreaders use their current position. A
killing hit may still spread from its recorded position if the actor disappeared.
A missing native hit confirmation skips that branch, allowing siblings to proceed.

max_jumps counts TOTAL secondary targets across the whole chain, excluding the
initial hit. It is not a generation/depth limit or a separate allowance per branch.
0 removes the configured total-target limit. targets_per_spread = 0 disables
secondary propagation. An arrow rolls chance_percent once when starting a chain,
not once for every branch. Direct-hit and secondary damage remain independent.

CONFIGURE ARROWS
Under arrow_chain, edit the tier you use. Example:
    eternal_45 = { enabled = true, chance_percent = 100, spread_radius = 7.0,
                   damage = 0.5, max_jumps = 0, targets_per_spread = 3, spread_delay_ms = 250 },
Keep your existing radius/damage/chance values if preferred; add the new
targets_per_spread key to your saved profile. Old profiles missing it use 1.

CONFIGURE SPELLS
Under chain_lightning, add or edit:
    propagation = { enabled = true, targets_per_spread = 3, max_jumps = 0, spread_delay_ms = 250 },
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
build derives capacity from the remaining native storage. Finite
max_jumps and linear profiles allocate smaller queues. The actual capacity is
printed in the EML log on Apply. It is NOT a total-victim limit: slots are reused
and the modeled bytecode traverses a 1,100-target line. An exceptionally wide
frontier stops if the queue fills, before writing outside native storage.

For enabled shock and fire arrows, the server LifeTime component is replaced with
a five-second flight watchdog in the Impact program. Missed arrows still expire;
once chaining starts, that flight timeout no longer ends propagation. Completion
still uses the original destruction path. This lifecycle change needs live combat
and missed-shot cleanup testing. Only loaded/queryable enemies can be selected.
With max_jumps = 0 there is no configured depth, total-target or duration limit.
Native frontier capacity, streaming, entity ownership and shutdown still apply;
map-wide propagation has not been verified.
Large radii, crowded queries and branching can create substantial server work.

OTHER SETTINGS RETAINED
- Five chain-lightning spells: targeting range, raw damage coefficient, mana.
- All 11 eternal arrows: independent direct-hit coefficients and original types.
- Existing Mass Destruction skill: radius and damage per Intelligence.
AOE for ice/bone arrows, damage falloff, global shock debuffs and
stun controls are not included. No client resources or native DLLs are bundled.

INSTALL OR UPGRADE ENTIRELY THROUGH ESM-Z
1. Stop the game server. Keep a copy of your current src/config.lua text.
2. Server Setup & Config > Mods: remove the old Zat Shock Tuning mod if installed.
   The manager rejects duplicate IDs; removing it deletes that stored config.
3. Upload this ZIP intact, enable the mod, then open Configure > src/config.lua.
4. Restore your tuning and keep the new fire_arrows section to configure burns.
   Add spread_delay_ms = 250 to your enabled shock arrow tiers
   and the spell propagation block (omitting it also defaults to 250). Keep your
   targets_per_spread, radius, damage and max_jumps values. Old configs work.
5. Save, Apply & Validate Mods, inspect the EML log, and start the game server.
No server desktop access, compiler or manual archive editing is needed.
The mod reads src/config.lua; config.defaults.lua is a backup to copy from.

VALIDATION AND COMBAT CHECK
Automated tests execute the emitted instructions with modeled native calls,
including far-first enumeration, elevation, three-then-nine branching, converging
branches, killed victims, full-width IDs, queue reuse, budgets and failure paths.
They do not establish live combat timing, damage authority or VFX replication.
Use a test world and unmodified clients first. Check mixed species around corpses,
and verify missed shots disappear while a populated chain continues past 5 s. Check actual health loss on the
nearest enemies, then on each branch's children beyond the first victim's radius.
Confirm no repeat hits and that ordinary/disabled arrows still work. Repeat with
a chain-lightning spell and with two players casting/shooting independently.

Baseline guards reject unsupported builds and conflicting resource edits. To
restore, stop the server, disable/remove this mod in ESM-Z, apply remaining mods,
and restart. Preserve your config text before removing or upgrading.
