# Chain lightning and shock mod investigation and plan

Investigation date: October 21, 2026. Status: design and static inspection; no gameplay patch applied.

Follow-up: [Eternal arrow AOE findings](ETERNAL_ARROW_AOE_PLAN.md) expands this
scope to all eternal arrows and records the implemented 0.1.1 scalar settings.
The user explicitly rejected arbitrary balance caps; recommendations remain
advisory and only technical/semantic validity checks are enforced.
The follow-up now also specifies optional hit-seeded chain lightning for all
three eternal shock-arrow tiers, with independent spread/damage/chance controls,
an optional user-selected jump count, and separate radial AOE. Chains are now
implemented in the opt-in 0.2.0-alpha.1 prototype; see that follow-up's current
implementation/validation section. Circular arrow AOE remains planned.

Build one configurable EML mod for existing chain-lightning and shock effects, plus an optional shock burst on qualifying weapon hits. The user explicitly requested both tuning existing effects and optionally adding shock AOE on hit. Multiplayer compatibility and easy installation through ESM-Z are release requirements. Server-only operation is the preferred test target, not an established capability.

## Current installation and evidence

The installed client has updated to Steam build **26082781**, internal revision **1273043**, release_1.0. Its executable, KFC index, and resource file differ from the October 20 fingerprints. The earlier isolated server remains at internal revision **1269579**; its three recorded fingerprints still match. Obtain a matching disposable server before multiplayer testing; do not treat yesterday's matching client/server comparison as verification of this build.

Read-only extraction with upstream kfc-parser 0.2.0 decoded 19,259 selected descriptors without failure, followed by 367 perk/registry/localization descriptors without failure. Seventy selected skill/projectile programs were disassembled successfully, followed by three referenced AOE programs. Output is under `dist/shock-research-20261021`; raw extracted game data stays local and is not a distributable mod.

EML supports typed resource edits before game startup. Its Lua code is not a per-hit gameplay callback. A probability roll must execute in the game's Impact behavior, not once in Lua while applying the mod. [EML scope](https://brabb3l.github.io/kfc-parser/eml/index.html), [resource API](https://brabb3l.github.io/kfc-parser/eml/api/assets/resource.html).

## Confirmed modification candidates

Values below are decoded parameters, not measured final damage or experimentally calibrated distances.

| Feature | Current evidence | Implementation assessment |
| --- | --- | --- |
| Chain spell initial targeting | All five spell items have `itemTargetingSetup.targetingRange = 24.0` | Narrow item edit; separate from spread |
| Chain spell spread | All five items select sequence `12f3cda4-c44d-4a09-bc76-749e40f1c60f`. Its SpawnImpact event has a combat sphere radius of **7.0** | Strong candidate for inter-target spread; verify geometry in play |
| Chain spell strength | Item `damageSetup.dmgMod` is approximately **1.12** for the two tier-2 entries and **1.22** for the three higher-tier entries | Per-tier multiplier; preserve other damage components |
| Chain spell stun contribution | Separate stamina-damage templates expose `BaseStamDamage` and `StamDamageMul` | Expose separately from health damage; trace scaling in gameplay |
| Related chain debuff spread | Buff ID **4180509149**, program `b1e3f38c-23bd-4808-b6f6-6a014895aeff`, overrides `Range` to **10.0** and `AttackMod` to **1.0** | Distinct from active spell; shared effect, so trace every user before editing |
| Lightning arrows | Three tiered items use direct-hit projectile program `c0a8231a-f87f-467c-ad9d-6d4fe93ecda7`; item damage modifier **0.5**, targeting **30.0** | Damage is a scalar candidate. No native radial burst was identified in this direct-hit program |
| Existing magic AOE reference | Mass Destruction skill ID **4208308624** uses a critical-hit listener restricted to `RangedStaff` and `RangedWand`, spawning `Skill_MassDestruction_DealDamageSphere_AllEnemy` | Useful existing behavior to adapt, not a ready-made arbitrary-weapon proc |
| Mass Destruction range and strength | Spawned program `56188199-e5b1-452a-ba03-0915ea989fec` queries enemies within **15.0** and multiplies Intelligence by `BaseDamge` default **2** | Concrete range and scaling candidates; final health loss still includes game combat processing |
| Configurable new shock burst chance | Other inspected skill programs call `RandomBranchNode` with a float chance | The engine has the building block; attaching it correctly to our hit path remains implementation work |

The chain spell's program moves its effect transform to a hit target and resumes collision processing, with a consecutive-hit filter. This supports interpreting the sequence sphere as propagation reach. No simple maximum-jump counter was found. A strict target limit, jump count, nearest-target ordering, or per-hop falloff would require behavior work and separate validation.

Three other sequences use the same chain spell program with approximately **3.6** radius. The five identified player spell items select the **7.0** sequence. Do not blindly edit every sequence sharing that program.

Several deceptively similar controls must remain distinct:

- `NoiseRange` controls noise input, not combat AOE. The arrow projectile override **7.5** is not an explosion radius.
- The arrow's random calculation varies damage; it is not an AOE activation chance.
- The chain casting event's `chance = 1.0` governs spawning that event, not an independent secondary burst.
- Shock health damage, stun/stamina damage, debuff duration, and chaining are separate effects.
- A skill configuration labelled Range can be a different numeric type from the receiving program's range field. Follow actual consumers; do not copy configuration entries between contexts blindly.

## Proposed user settings

Use three independently enabled sections. Existing effects default to vanilla; the new on-hit burst defaults to disabled. Store shared defaults with per-family and per-item overrides. Configuration is applied while the server is stopped and takes effect at startup.

| Section | Proposed controls | Scope |
| --- | --- | --- |
| Chain spell | Initial targeting range, spread radius, health-damage multiplier, mana multiplier, stun multiplier | Five existing spell items; per-tier strength overrides |
| Existing shock effects | Effect range, strength, duration, cooldown, existing trigger conditions where traced | Explicit allowlist of identified effects, not every lightning-related resource |
| Optional shock burst | Enabled, chance percentage, radius, damage multiplier, eligible weapon/item list, cooldown, maximum victims, trigger mode | Magic arrows first; then wands, other spells, and explicitly selected shock weapons |

Advanced chain controls such as maximum jumps, damage falloff, repeat-target policy, and line-of-sight restrictions remain experimental until implemented. Do not show a working setting for a feature that has no verified consumer.

For the new burst, proposed behavior is one probability roll per qualifying direct-hit event, with at most one successful burst per attack/projectile. Multi-projectile shots need an explicit policy and testing before release. Offer direct-hit, critical-hit, or kill trigger modes only as each is implemented. Keep proc chance independent of the character's normal critical-hit chance.

Proposed damage definition: burst damage is a configurable fraction of the triggering attack's shock component before target mitigation, then each secondary target resolves its own defenses. This avoids applying one victim's resistance twice. Capturing that value accurately is an implementation prerequisite; the first prototype may instead use the existing Intelligence-based damage path, clearly labelled as such.

Exclude allies and the caster, avoid terrain damage, and prevent generated burst hits from triggering further bursts. Cooldown and victim limits should be user-configurable and optional; do not enforce hidden balance caps. Enemies are excluded from the initial item/weapon allowlist. The directly struck victim should be excluded from secondary burst damage by default; make any double-hit behavior deliberate.

An illustrative test profile is **25% chance, 4-unit radius, 50% shock-damage scaling, 1-second cooldown, at most 6 secondary enemies**. These are design examples, not a working configuration or recommended final balance. Publish recommendations without imposing balance caps; validate finite values, actual storage constraints and probability semantics of 0–100%.

## Implementation stages

1. **Existing spell prototype.** Patch the five item descriptors and their selected sequence. First prove spread and damage changes independently at vanilla, reduced, and increased settings. Include a no-change preset and restoration check. Keep all item IDs and inventory identities unchanged.
2. **Existing AOE prototype.** Isolate Mass Destruction range and strength. Confirm its current trigger, origin point, eligible weapons, and which process calculates damage. Preserve the original skill requirement. This establishes a known AOE reference without introducing a new trigger yet.
3. **Arrow burst prototype.** Add the probability branch to a player-arrow hit path and invoke an isolated shock AOE behavior. Prove damage attribution, correct triggering, enemy filtering, secondary-hit exclusion, cooldown, and recursion protection. Inspect all references before modifying shared programs. Creating new resource GUIDs may introduce client requirements; do not assume they are replicated.
4. **Other weapon families.** Extend by explicit allowlists only after arrow results pass. Distinguish natural shock damage from added shock perks and mixed-damage weapons. Confirm whether equipped-item perks are active in each damage path.
5. **Package and compatibility release.** Produce one EML patch ZIP, a documented settings file, supported-build checks, baseline assertions, a change report, and a tested restore path. No modified full game archives or executable patches in the package.

EML data patching remains the preferred mechanism for the first two stages. The new trigger is an Impact-program adaptation and is substantially more work than scalar edits. If safe Impact changes cannot implement the required event attribution/caps, reassess a runtime framework rather than pretending EML Lua receives live combat events.

## Multiplayer acceptance tests

Use a disposable server at the same game revision as two test clients. First try server-only installation with both clients unmodified. Repeat with matching mod/configuration on server and clients to establish whether each feature can be advertised as server-only. A successful join or visible lightning effect is insufficient.

Measure initial targeting, distances between secondary targets, actual health loss, stun buildup, mana cost, triggering counts, and what each player sees. Test both players as the attacker, simultaneous attacks, elevation, walls, moving enemies, missed arrows, blocked hits, crits, kills, and multi-hit attacks. Explicitly test 0% and 100% chance; then collect enough eligible attempts to assess an intermediate chance statistically, recording attempts suppressed by cooldown separately.

Test dense groups, repeated hits, secondary effects interacting with Mass Destruction, and whether a burst can trigger itself. Check restart, reconnect, uninstall, game-update refusal, and conflicts with other combat mods. A branch that changes server damage but leaves client presentation misleading needs either a documented client component or a restricted supported feature set.

The old server copy is unsuitable for this gate until a matching current build is obtained. No multiplayer certification or active game changes are part of this investigation.

## Packaging for ESM-Z

The intended ZIP contains `mod.json`, `src/mod.lua`, a self-contained editable configuration, README, and license. Declare the EML `patch` capability. Use a configuration format the Lua package demonstrably reads; a Lua table is the simplest initial option. ESM-Z's current Mods tab can upload and edit supported text files, but it does not yet provide dedicated sliders for this proposed mod.

Give every setting clear units and explain whether it affects targeting, propagation, health damage, or stun. Provide restore-to-vanilla values and log matched resources before applying changes. Validate the supported schema and all requested settings before changing any resource; the install/apply wrapper must also handle rollback if EML fails. Reject conflicting edits rather than silently stacking multipliers on an already modified baseline.

Changing the manager release is not required to conduct the prototypes. A future structured settings panel is a separate manager enhancement. Publish the mod as server-only only after the unmodified-client tests pass; otherwise state the exact matching client requirements.

## Local evidence paths

- `dist/shock-research-20261021/client-export.log`: current-build extraction result.
- `dist/shock-research-20261021/reflection_data.json`: current internal revision and types.
- `dist/shock-research-20261021/baseline-check.json`: comparison against the October 20 client/server fingerprints.
- `dist/shock-research-20261021/client-current/ItemInfo`: current spell and arrow definitions.
- `dist/shock-research-20261021/client-current/ActorSequenceResource`: chain sphere and spawn-event settings.
- `dist/shock-research-20261021/disassembled`: named Impact values and instructions.
- `dist/shock-research-20261021/skill-evidence.json`: Mass Destruction skill-to-template trace and related AOE candidates.
- `dist/shock-research-20261021/templates.json`: selected projectile/effect templates.

`items.json` in the research directory was produced from the October 20 export for comparison; use `client-current/ItemInfo` for current-build values. Inspection scripts in `dist` read local data and invoke only extraction/disassembly commands. No production server, world save, or installed client file was edited.
