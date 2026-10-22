# Eternal arrow AOE: findings and implementation plan

Updated 2026-10-21 against Enshrouded internal revision 1273043. AOE means area
of effect. This records the expanded scope requested after the shock prototype.

## Alpha.1 field failure and alpha.2 correction

The user reported that enabling only the level-45 chain removed direct damage
from all tested eternal arrows. Setting that one switch false, applying and
restarting restored damage. The reported values (spread 48, damage 3, limit 20)
are saved as a regression fixture; none needed clamping to correct this defect.

The alpha.1 ammunition gate executed `GLoad Ammunition::value` on a `keen::ItemId`
wrapper before the original damage path. Inspection of the current dedicated
server's native VM establishes that GLoad only accepts uint32, sint32, float32,
bool and Time. ItemId falls into its error branch and sets the VM abort flag.
This applies to every projectile entering the shared program's combat branch,
before its ammunition can be excluded. The equality instruction itself is
implemented; the earlier suspicion about its unused status was ruled out.

Alpha.2 adds a uint32 alias for the ItemId value at exactly the same data offset,
so it sees runtime ammunition configuration instead of a copied startup zero.
Existing code/data is retained and the gate reads this supported scalar type.
The simulator now checks the native load/store type allowlist and models aliases
as shared storage. Against the original alpha.1 ZIP and the user's exact config,
the new regression rejects the pre-damage load for both matching and unrelated
ammunition. Alpha.2 passes that regression and the existing modeled scenarios.
Native combat/replication still requires a player retest; startup alone was not
and is not adequate to detect this class of failure.

Local native evidence, internal revision 1273043:

- Dedicated executable SHA-256:
  `d7baa768eb00aa895d9f5a1cd8747ccf66858c7b542f50983092b2e3261588ee`.
- VM dispatch at RVA `0x9862fd` selects opcode minus one from table `0x986d9c`.
- GLoad handler starts at `0x986364`; type comparisons at `0x9863ab` through
  `0x9863dc` whitelist hashes `32940bec`, `9859f31e`, `c894953d`, `dfe4e404`,
  `e89f7410`. Reflection maps these to the five scalar types above.
- ItemId hash `5bfc0dbb` is absent. Failure sets flag `0x10` at `0x986436`.
- Error string at `0x131bc78`: `Can not laod Type '0x%08x' onto stack` (native typo).
- IEQ handler at `0x986aa4` compares two stack words and writes its boolean result.
- Disassembly stayed local in `dist/impact-vm-disassembly.txt`; no executable
  code or game data is bundled with the upload ZIP.

## Implementation update: 0.2.0-alpha.1

An experimental hit-seeded lightning-arrow chain is now implemented in
`mods/zat-shock-tuning/src/arrow_chain.lua`. Its supported configuration is the
top-level `arrow_chain` section in the packaged `src/config.lua`, with independent
`eternal_20`, `eternal_36` and `eternal_45` blocks. The nested schema below remains
a future proposal; no migration of existing damage keys is required in this alpha.
Old configs omit `arrow_chain` and keep chains disabled.

The extension preserves the shared projectile program's original code except
for two branch destinations, gates by exact ammunition ID, records target origin
and enemy eligibility before the direct hit, then runs secondary queries after
the successful unblocked hit. Chance, radius, damage and optional jump limits
have actual consumers. A zero limit imposes no user-selected count limit. It
uses native hit history and stops if that history fails to record progress.
The original collider, item IDs and resource GUIDs stay unchanged.

This first alpha performs a rapid synchronous chain with the native link VFX,
instead of a detached effect with timed hops. That avoids new effect resources
and a chain tied to the flying projectile's remaining lifetime, but large queries
can monopolize a frame. Native history must still be verified as a complete root
history during combat. The implementation does not claim a proven explicit
visited set, wall occlusion, or an engine performance guarantee.

Validation: 23 existing scalar integration checks and 21 chain checks passed.
The chain checks include decoding, full stack/control-flow audit and execution
of emitted words with modeled native calls. A loopback dedicated server reached
Run with all three chains enabled. No live combat or client replication was
tested. The ZIP is an opt-in test alpha, not a certified server-only release.
Circular AOE for the eleven eternal arrows remains a separate outstanding feature.

## Implemented in the 0.1.1 test package

All 11 eternal arrow variants now have independently editable direct-hit damage
coefficients. The three original lightning keys remain compatible; eight new
ice/fire/bone keys live in `eternal_arrows`. Omitting that new section keeps those
eight variants at vanilla values. These scalar changes do not add AOE.

The arbitrary balance caps on damage, range, radius and mana have been removed.
Config comments recommend ranges without enforcing them. Validation retains
finite-number checks, nonnegative values (including zero), integer
requirements, and the actual float32/signed32/unsigned32 storage constraints.
No values are silently clamped. Storage checks cannot establish a universal
crash-free maximum: downstream damage arithmetic and large spatial queries still
need runtime testing. A future safety rejection must have a concrete technical
reason, not a preferred balance threshold.

## Confirmed inventory

The current ItemRegistryResource pairs its 4,207 item references with 4,207 debug
names. Exactly 11 registered item names contain both Arrow and Eternal.

| Family | Item levels | Vanilla coefficient | Existing damage type |
|---|---|---|---|
| Ice | 10, 28, 45 | 0.5 each | Magical ice |
| Fire | 15, 28, 45 | 0.5 each | Magical fire |
| Lightning | 20, 36, 45 | 0.5 each | Magical lightning |
| Bone | 36, 45 | 0.5 each | Physical blunt |

Damage type should default to the arrow's existing type. Do not convert every
arrow's burst to shock. Bone should receive a configurable physical burst unless
the user explicitly selects an elemental override. Existing burn/freeze/shock
status behavior and additional status application are separate from damage type.

## AOE implementation requirements (not shipped yet)

Each of the 11 variants needs its own settings, including:

- AOE enable/disable, default off to preserve vanilla behavior.
- Chance per eligible impact, mathematically 0–100%; 100 means every eligible hit.
- AOE radius and damage coefficient independent of direct-hit damage.
- Damage type, default matching the original arrow.
- Trigger choice: enemy hit first; ground/wall impact as a separate option.
- Whether the direct-hit target also receives the burst, default false.
- Friendly fire, self damage and terrain damage, default false.
- Optional cooldown and target count limit. Zero cooldown means no cooldown;
  zero target limit means no user-selected limit. No hidden balance cap.
- Optional status effect strength/duration only once its actual engine path and
  stacking semantics are established. Do not present nonfunctional settings.

Proposed future shape, **not valid input to 0.1.1**:

```lua
eternal_arrows = {
    fire_45 = {
        direct_damage = 0.5,
        aoe = {
            enabled = false,
            chance_percent = 25,
            radius = 4.0,
            damage_coefficient = 0.25,
            damage_type = "inherit",
            trigger = "enemy_hit",
            include_direct_target = false,
            friendly_fire = false,
            self_damage = false,
            terrain_damage = false,
            cooldown_seconds = 0,
            target_limit = 0,
        },
    },
}
```

These example values are a proposed starting profile, not tested balance advice
or implemented defaults. The final schema must migrate old settings deliberately.
Chance is rolled once per eligible arrow impact, not separately for each nearby
victim. A burst must not generate another burst, regardless of cooldown settings.
Each target/root should be damaged at most once per burst even with multiple
colliders. Define the cooldown's owner and scope explicitly before implementing it.

## Engine paths and feasibility

### Optional chain lightning for eternal shock arrows

Added requirement, October 21: the level-20, level-36 and level-45 eternal
lightning arrows must each be able to start a chain-lightning effect. This is
separate from their direct hit and optional radial AOE. All three effects have
independent settings. The other eight eternal arrows retain their planned AOE
support; this request does not implicitly turn their damage into lightning.

Intended behavior: a successful, unblocked enemy hit seeds the chain at the
actual struck enemy. The original arrow resolves its direct hit once. The chain
then searches around that enemy, damages another eligible enemy, moves its
origin to that enemy and continues. Use the game's lightning-link visuals where
their ownership and replication permit it. Do not acquire an unrelated target
from the shooter's current aim lock. A miss, ground impact or blocked hit does
not start a chain in the first implementation. A killing hit should still seed
at its recorded impact position if the original entity disappears.

Proposed future per-tier configuration, **not accepted by package 0.1.1**:

```lua
eternal_arrows = {
    lightning_20 = {
        direct_damage = 0.5,
        chain = {
            enabled = false,
            chance_percent = 100,
            spread_radius = 7.0,
            damage = 0.5,
            max_jumps = 0,
        },
        -- Separate aoe settings use the radial-burst schema above.
    },
    -- lightning_36 and lightning_45 get independent copies of these settings.
}
```

- `enabled`: off by default because vanilla arrows do not have this chain.
- `chance_percent`: one roll per eligible projectile hit; 100 always starts a
  chain when another eligible target exists. Further jumps do not reroll it.
- `spread_radius`: distance from the most recently struck enemy to the next
  candidate, in the same game-distance units as the spell's spread setting.
  The starting value 7.0 matches the inspected player spell sequence. It is not
  a recommended maximum. Arrow flight distance is a separate mechanic; the
  spell's initial `targeting_range` does not apply to this hit-seeded chain.
- `damage`: the secondary hit's attack coefficient, independently configurable
  from the arrow's direct coefficient and from spell tiers. Preserve the
  arrow/bow damage context and lightning distribution rather than accidentally
  importing the spell's Intelligence scaling. Starting at 0.5 copies the
  existing arrow coefficient; this is a proposed prototype value, not measured
  final health loss. Define and verify the engine's inherited damage context
  before publishing this setting. Never use the first victim's post-mitigation
  health loss as the damage base for every later victim.
- `max_jumps`: optional user-selected count of secondary enemies, excluding the
  initial victim. Zero means no user-selected count limit. This needs new logic;
  no existing maximum-jump scalar was identified in the spell. There must be no
  hidden replacement balance cap. Stop when there is no eligible unvisited
  target, and yield between hops so the traversal does not monopolize a frame.

The first implementation must exclude the initial victim and every previously
visited entity root from later chain hits. This prevents bouncing forever
between two enemies without imposing a damage/range/count balance cap. Keep
shooter/allies excluded and terrain unaffected. Preserve the existing arrow
shot's mana cost; do not import the spell's cost or charge once per jump.
Stamina damage/stun, critical behavior and damage falloff are separate mechanics
and must not be advertised as configurable before their consumers are tested.

The chain and radial AOE may both be enabled on the original arrow hit, with
separate chance rolls. Each may damage the same secondary enemy if it qualifies
for both, so the combined damage must be documented. Neither effect may launch
another chain or radial burst; secondary hits must carry explicit provenance or
remain outside the original-projectile trigger path. Multi-projectile shots
roll once for each eligible projectile, not once for the entire bow animation.

All controls belong in the same remotely editable configuration delivered in
the EML ZIP. Provide the three complete tier blocks with comments; preserve old
direct-damage values during schema migration. Do not add inert `chain` keys to
the current package merely to make the editor appear to support the feature.

#### Native chain evidence and implementation consequences

The five chain spell items use sequence
`12f3cda4-c44d-4a09-bc76-749e40f1c60f`, whose SpawnImpact event creates program
`e28f0d79-e2fe-46ba-8d82-9ba368cb30c7` with a continuous combat sphere of radius
7.0. The event copies combat attributes and faction and adds the weapon reference.

The program starts with `GetLockedTarget(HardLockCandidate)`, applies the first
hit, moves its own transform to the target, then processes collision candidates
through same-root, root-entity, consecutive-hit and faction filters. Subsequent
hits also move its transform before repeating collision processing. This is
evidence for a moving propagation origin; it does not prove nearest-target
ordering, wall occlusion or lifetime-wide deduplication.

The native timing values include 0.25 seconds before the first damage call,
0.25 seconds after the initial target move, and 0.10 seconds before secondary
damage plus 0.25 seconds after each secondary move. Engine ticks and animation
may add latency. The initial and subsequent visual templates are respectively
`a9bbe18d-ac1f-4964-9922-414455b7dbcf` and
`c60faca7-06a1-414c-a84e-cef42a74aa3a`. The program also spawns a separate stamina
damage template; copying that behavior would add another effect beyond health
damage and must be deliberate.

Replacing an arrow projectile's program with the spell program is not a valid
implementation: the spell expects a locked target, a stationary combat sphere,
spell scaling and cast-provided ownership/configuration. The projectile has
flight physics, a small collision shape and a destroy-on-hit lifecycle. Enlarging
its flight collider to the chain radius would also change which enemy the arrow
hits. Preserve the original projectile hit and launch/adapt a distinct chain
execution context at the recorded hit position with the shooter's ownership.

An existing chain-related debuff (`b1e3f38c-23bd-4808-b6f6-6a014895aeff`, buff ID
4180509149) is not an equivalent shortcut. Its program listens for subsequent
hit events, checks debuffs/cooldowns and queries around its assigned target.
Applying that shared buff would not by itself implement the requested immediate,
independently configured per-arrow chain and could interact with other users
of the buff. The inspected arrow hit program's default BuffType is null; the
three lightning projectile templates do not override it.

Prototype order:

1. Establish the exact ammo identity, shooter ownership and damage inputs at an
   eligible lightning-arrow hit in a disposable multiplayer fixture.
2. Gate the extension by one approved arrow tier, disabled by default. Preserve
   every existing direct-hit path and the shared program's unrelated users.
3. Prove one secondary enemy hit with the correct lightning visual, origin and
   ownership before adding the repeated traversal, visited set and jump setting.
4. Add chance and independent tier settings, then interaction with radial AOE.
5. Test death/despawn during a hop, movement, walls, repeated shots, two shooters,
   multiple colliders, secondary proc recursion and dense groups. Use a layout
   A--B--C where C is outside A's radius but inside B's to distinguish a moving
   chain from a single radial burst. A--B must never ping-pong indefinitely.
6. Validate actual damage and visuals with two unmodified clients, switching
   which client shoots. If a separate effect resource is necessary, test whether
   clients require that resource; shared GUIDs alone do not prove server authority.

Original design status: the native path and proposed contract were identified
before implementation. See the implementation update above for the alpha's
current scope and remaining differences from this proposed contract.

### Existing arrow paths

The nine elemental item definitions point via `equipment.placedEntity` to their
projectile templates. Those templates use Impact program
`c0a8231a-f87f-467c-ad9d-6d4fe93ecda7`. It receives collision events, filters friends
and the same root, performs the direct hit, checks blocking, applies a buff and
destroys the projectile. There is no existing configurable radial-damage query
or AOE probability in this program. Its random value drives direct-damage
variation; NoiseRange is noise, not damage radius.

That same program is referenced by **123 templates**, including enemy projectiles
and wands. An unconditional edit would have excessive scope. Any in-place
extension must default off and require the exact approved ammunition ID before
using one of the 11 sets of values. The program already contains an Ammunition
ItemId input, but runtime propagation and identity must be tested rather than
assumed from its name.

Both eternal bone tiers point to `e51ee4b6-13bc-4a9c-9642-518c4ec04130`, named
Projectile_Player_ArrowT2_Bone. It uses a different hit program,
`d7cd3251-d0fc-4078-9512-381799650f0b`, with consecutive-hit filtering and an enemy
test. Sharing a template with ordinary bone arrows means template-wide changes
alone cannot safely implement independent level-36/45 behavior. Preserve its
existing collision handling; use the ammunition identity to select settings.

The existing explosive-arrow program `bae6dc9c-1fa1-422f-9dfd-b42e204f6826` shows
how the engine spawns an effect at the collision position, including special
water handling. It is useful as a reference, not a safe drop-in replacement:
explosive arrows may have different damage, terrain and lifecycle behavior.
Mass Destruction supplies another reference for faction-filtered spatial queries,
but its current origin is the player; copying it unchanged would put an arrow
burst at the wrong position and retain unwanted skill/scaling behavior.

Preferred first experiment: append a tightly gated AOE branch to the existing hit
programs after the eligible direct-hit result, querying around the recorded
impact position and preserving the original direct-hit branches. This avoids new
network-visible resource identities. A separate cloned program is another option,
but new resources may require matching client installation. EML's startup Lua can
build/patch Impact data; it is not a live Lua hit callback.

## Toolchain experiment

Upstream EML/kfc-parser 0.2.0 supports Impact disassembly and assembly. The direct
hit program was reassembled locally after normalizing variable names into legal
assembler symbols, including nested parent references. The rebuilt code,
shutdown code, data bytes, stack size, event streams and query-call IDs match the
original. Debug-layout names and descriptor-envelope metadata need separate
handling. This establishes a usable assembly path, not a tested new AOE program.
The tools and generated game programs are research artifacts, not upload content.

## Validation before an AOE package

1. With AOE disabled, all direct-hit and unrelated projectile behavior must
   remain equivalent. Confirm the exact ammunition ID for all 11 variants.
2. Enable a 100% modest-radius burst for one arrow on an isolated world. Verify
   impact origin, damage ownership, damage type, target filtering and one burst.
3. Test 0%, 100% and an intermediate chance; check blocks, weak spots, kills,
   missed shots, ground/water impacts, multishot and simultaneous players.
4. Verify that secondary damage cannot retrigger bursts, that entity roots are
   deduplicated, and that terrain remains untouched when disabled.
5. Test bone separately, including ordinary bone arrows as an unaffected control.
6. Start with two unmodified clients, both taking turns shooting. Measure actual
   health loss and targets, not just graphics. A successful server boot does not
   establish server-only compatibility. Repeat with matching clients if needed.
7. Exercise restore, config reload, client reconnect and game-build refusal.

The upload must remain one self-contained EML ZIP. All supported settings should
be editable in ESM-Z, saved remotely and applied on server restart. Users must
not need a local compiler, copied game archives or server desktop access.

## Local evidence

- `dist/shock-research-20261021/client-current`: current extracted assets.
- `dist/eternal-arrow-research-20261021/inventory.json`: 11 arrow definitions.
- `dist/eternal-arrow-research-20261021/projectiles.json`: elemental projectile paths.
- `dist/eternal-arrow-research-20261021/shared-program-users.json`: 123 references.
- `dist/eternal-arrow-research-20261021/bone-projectiles.json`: bone-related paths.
- `dist/eternal-arrow-research-20261021/assembler-roundtrip-results.json`: assembler checks.
- `dist/shock-mod-validation-20261021/test-run-011.log`: package validation.

No production server, installed game client or user world was modified.


## 0.3.0-alpha.2 testing fixes

The next server-test package filters initial and secondary targets by Dead state
and positive current HP, queries all factions before caster-hostility filtering,
and stores selected IDs directly without reopening queries by index. A missing
hit confirmation skips one branch instead of canceling its siblings.
`spread_delay_ms` defaults to 250 before the first spread and between generations;
old configurations inherit that default. Living spreaders refresh position after
the delay. Enabled shock-arrow templates replace only their server LifeTime
component with a five-second flight watchdog; active chains use their own cleanup
and are no longer deliberately cut off by the flight timer. This requires live
combat/cleanup testing. Native storage and streaming limits remain; no map-wide
multiplayer claim. See `mods/zat-shock-tuning/VALIDATION.txt` for evidence and limits.

## Eternal fire-arrow investigation — 2026-10-22

Researched, not implemented or deployed. Scope: eternal fire arrows 15/28/45,
initial area ignition, subsequent enemy-to-enemy spread, configurable DoT, and
scaling with the firing bow's Magic Fire Damage and All Fire Damage. No game,
server, save, installed mod or release package was changed during this research.

Recommendation: a weapon-aware burn controller using native burning visuals and
the nearest-living-target propagation approach. Do not substitute the entire
explosive-arrow effect or globally edit an existing shared burning debuff.

### Installed asset findings

Six central resources were re-exported read-only from the installed game on
October 22 and compared as parsed JSON with the revision-1273043 research export:
level-45 fire arrow, two relevant perks, buff collection, fixed-damage burn
program and explosive-arrow explosion template. All six match.

- Eternal fire arrows share Impact `c0a8231a-f87f-467c-ad9d-6d4fe93ecda7` with the
  shock arrows. Their vanilla raw damage coefficient is 0.5. The shared program
  has an optional ApplyBuff path, but its default buff is null. Extend one shared
  assembler plan with ammo gates; do not independently overwrite this program.
- Explosive projectile `bae6dc9c-1fa1-422f-9dfd-b42e204f6826` spawns template
  `33c000db-c758-4a33-915d-d11ac9d17f55`. Its explosion program
  `bddf8631-6be9-462e-b1d1-f35e03cc18ad` includes damage, visual, terrain-template
  and skill-effect paths. Zero blast damage does not remove these other paths or
  create a burn. A visual can be reused separately if appropriate.
- Fireball uses the impact-spawning projectile family and explosion program
  `80a2448f-945c-45f6-8fce-9b09ed61620c`. It is an impact-spawn reference, not an
  independently scaling contagious burn ready to enable on arrows.
- Fire pillar zone `cd3f5468-b90c-4ba7-b834-47c467e12cf4` uses program
  `62b4d50e-cebd-4e06-902f-b9321fa1bc0d`: area damage followed by debuff application.
  It references burning buff `2ba4a810-3764-408b-806e-bb5820f6b70d`.
- Environmental fire template `525ef703-6dfc-40a2-90a4-f6d303e7d2a3` applies buff
  `8237de3a-58d2-4239-9b95-36d714ce772a`. Both this and the pillar buff map to
  burn program `51a10f44-8a11-46e4-90a1-ff5abd0b8b9b`: timed ticks, a Soaked check,
  fire-only CreateDamageSetup, ApplyDamage, and size-specific burn visuals.
  Pillar variants configure fire values 3/6/9/12 and lifetimes 9/10/11/12 seconds.
  This explicit FireDamage path lacks the weapon/category scaling inputs needed
  to establish the requested bow inheritance. Copying it unchanged is insufficient.
- A second burning program, `11dc1506-843b-4034-8d54-6a17dfc9682a`, accepts a
  DamageSetup, attack coefficient, weapon-category configuration and tick time,
  with native burning visuals. ApplyBuff accepts DamageSetup, used-item ID and
  duration. This is a promising prototype candidate, but these parameters do not
  prove ownership, per-arrow isolation or bonus inheritance at runtime.

Existing buffs serve world hazards and other spells. New buff/resource IDs may
introduce client dependencies. Prefer existing client-known visuals with
server-owned logic, then test with unmodified clients. No server-only guarantee
follows from asset inspection, successful apply, or startup alone.

### Bow scaling contract

`Perk_Damage_Fire` (`79e0cf57-12ce-403c-93ad-f20d391a75ca`) contributes about 0.1
to its fire-only damageModifier distribution. Actual bow definitions reference
it, sometimes more than once. This is a native coefficient, not flat +0.1 HP.

`Perk_DamageMod_Fire_All_Magical_5` and `_10` (`3fefd54b-e8cf-427c-bcb0-9a45cd45a347`
and `53095b4b-f5c3-48f3-93cd-fb795a65c8c2`) configure about 0.05 and 0.10.
Their program `d02c0f04-ae3e-471c-87d6-9fd194f37786` adds to melee, magic and
ranged fire modifiers. The ranged attribute is
`93751533-ce64-455b-936c-895ee43eae4d`. Use the appropriate category path once,
not the sum of all three categories.

Burn strength should derive from the shot's fire contribution, including arrow
and active bow fire contribution, multiplied by the configured burn strength.
Preserve original shooter/weapon ownership and the native fire-modifier path.
Do not convert physical/ice/shock/poison components into extra fire implicitly.
Do not copy the first victim's post-resistance health loss to subsequent victims;
each victim must apply its own resistance.

Prefer capturing the shot's offensive context so a later bow swap does not alter
an existing burn. Native snapshot/ownership and arithmetic order still need
verification. Do not add a manual multiplier on top of an already applied native
bonus. No final numeric formula or automatic ApplyBuff inheritance is proven.

### Proposed behavior and controls — not released config keys

The hit retains normal direct-arrow damage, then ignites the struck enemy and
all eligible living hostiles in an initial radius, without an additional blast,
pushback or terrain operation. Each newly ignited enemy can spread after a delay
to its nearest unvisited living enemies within its own radius. Fan-out controls
how many. This spreads through enemies in any direction; it does not force a
geometric ring when the enemies themselves are unevenly distributed.

Each victim's burn duration starts on ignition and can outlive propagation.
Burn ticks must not start new chains. Proposed settings, independent per tier:

- `enabled`, `chance_percent`, `initial_radius`.
- `spread_radius`, `targets_per_spread`, `spread_delay_ms`.
- `max_jumps`: shared total additional ignitions, including initial-area victims;
  original struck enemy excluded. Zero removes the configured target budget.
- `burn_duration_ms`, `burn_tick_ms`.
- `burn_damage_multiplier_per_second`: strength relative to the shot's fire basis;
  scale each tick by elapsed seconds so frequency changes do not multiply DPS.
  Define the partial final tick explicitly.
- A documented reapplication policy. Recommend refreshing same-shooter burns
  initially; different shooters need explicit independent attribution.

Keep normal direct-damage keys compatible and ship the addition disabled.
No arbitrary balance caps. Validate finite native-representable values. A zero
tick interval needs explicit semantics, not division by zero or a busy loop.
Native storage, streaming and query limits still apply.

Initially target enemies only. Burning ground, structures, allies and players
are separate features. Preserve native Soaked extinguishing initially and test
immunities. Recommend that an extinguished/dead pending spreader stop its branch;
an initial killing hit can still seed its impact-area ignition. These are design
recommendations rather than claims about existing behavior.

### Development and acceptance gates

1. Prove single-target fire-only DoT, visual lifetime and source credit. Compare
   no bow bonus, Magic Fire Damage only, All Fire Damage only, and both. Repeat
   against different resistances and with a bow swap after the shot.
2. Test active perk unlock levels, reapplication, two shooters, Soaked, death,
   despawn and separation of direct-hit damage from burn damage.
3. Add initial ignition radius with no explosion/terrain side effects.
4. Add propagation and explicit ignition accounting. The shock queue currently
   depends on native damage-hit history: replacing ApplyDamage with ApplyBuff
   alone does not establish that history. DoT repeats must neither suppress
   required ticks nor create fresh branches. Zero damage must not cause retries
   forever. Model these cases before asking for another combat test.
5. Keep active burns alive independently of projectile flight and propagation
   completion, and clean them up on expiry/death. Check source logout and actual
   native storage boundaries.
6. Test unmodified multiplayer clients, normal arrows, other spells and shock,
   ESM remote configuration, restart and restoration before packaging.

Read-only evidence: `dist/fire-spread-research-20261022`, including decoded
programs/data, `templates.json`, `bow-fire-perks.json`, `provenance.json` and
`current-check.json`. Extracted game assets stay local and out of release ZIPs.

## Fire-arrow implementation — 0.4.0-alpha.1, 2026-10-22

Implemented in `mods/zat-shock-tuning/src/fire_arrows.lua`, composed into the
existing single arrow-program patch. All three fire tiers ship disabled and use
the proposed settings above. Initial radius and delayed nearest-living-target
fan-out are distinct from per-victim fire-only DoT. The controller preserves the
shot's populated fire component, original attack coefficient, source, ranged
category and native scaling attribute, without manually adding the three All
Fire modifiers. Actual perk arithmetic and server-only combat remain unverified.

Two explicit departures from the initial recommendation:

- Each arrow stacks independently instead of refreshing earlier same-shooter
  burns. There is no reliable shared per-shooter burn registry in this asset-only
  controller; ownership remains local to each shot. The policy is documented.
- A retained visited-ID ledger guarantees no revisits even at zero damage. It
  cannot recycle completed entries without losing that guarantee. Native 16-bit
  data/instruction storage yields 970 victims with all fire tiers alone or 398
  with all three shock and fire tiers enabled at fan-out 3. Actual capacity is
  logged. At capacity, new ignition stops and current burns finish. `max_jumps=0`
  removes the configured budget, not this native bound.

The damage-bearing native burn programs are not installed onto victims. Only
existing size-specific visual buffs are reused; they have null Impact programs,
ResetTime semantics and despawnOnDeath. Short 500-ms visual leases refresh while
the victim burns, then expire after Soaked/logout without deleting another
effect's shared visual. Damage stops on expiry/death/Soaked/source loss. Initial
killing hits may still seed the impact area. Existing lightning behavior stays
unchanged behind its separate ammo gates.

`mods/validate_fire_arrows.py` imports the real ZIP through ESM's EML adapter,
exports/disassembles emitted assets, audits native operands/stack/branches, and
executes emitted words with modeled native calls. It covers 30 fire-specific
checks, including the first/middle/last physical ledger records, finite and
full-width time values, partial ticks, mixed shock/fire and old-config behavior.
Tests restore the exact clean game index. Combat validation remains required
before describing bow bonuses or unmodified-client multiplayer as proven.
