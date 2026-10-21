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
