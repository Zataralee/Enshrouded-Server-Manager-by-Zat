# Eternal arrow AOE: findings and implementation plan

Updated 2026-10-21 against Enshrouded internal revision 1273043. AOE means area
of effect. This records the expanded scope requested after the shock prototype.

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
