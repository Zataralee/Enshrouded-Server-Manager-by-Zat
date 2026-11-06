Zat Fire Effect Lab 0.1.0-alpha.4

Separate companion upload ZIP for Zat Shock Tuning 0.4.0-alpha.5, game revisions
1273043, 1285601 and 1287369. This compatibility update retains all resource and
bytecode checks and keeps the existing config keys and defaults.
Keep the main mod installed; this does not replace its ZIP or config.
The package deliberately has a different mod ID and its own Configure file.

INSTALL AND TEST THROUGH ESM-Z
1. Stop the server. Upload this ZIP under Mods and enable it alongside Shock Tuning.
2. In Shock Tuning's fire_arrows profile for the arrow you will use, enable both
   enabled and ground_fire_enabled. chance_percent, initial_radius,
   burn_duration_ms and ground_fire_duration_ms must be positive.
   Your reported fire_45 test configuration already meets these requirements.
3. Configure Fire Effect Lab. Set any or all effects entries to true. All entries
   ship false so installation alone does not change the current effects.
4. Set burn_time_ms (10000 = ten seconds). This applies to the selected ground
   entity and the existing victim burn duration on all active fire-arrow tiers.
5. Save, Apply & Validate Mods, and start the server. Shoot an eternal fire arrow
   at empty ground first, then test an enemy hit. Repeat step 1 for each change.
6. To restore ordinary behavior, disable this companion, Apply & Validate Mods,
   and restart. The original mod config is never rewritten by this package.

UPDATING THE LAB ONLY
Stop the server, copy your lab config from Configure, remove Fire Effect Lab only,
then upload this newer ZIP and enable it; keep Shock Tuning installed.
The setting names are unchanged. This ESM beta requires removing an installed
mod ID before replacement, which removes its config too. Restore your saved
selections afterward. Any number of true values is now accepted.

COMBINATIONS
Every distinct selected native visual spawns at the impact area once. The original
arrow creates one leader visual, whose guarded preview startup creates the others
with the same transform and scale, parented directly to that arrow. Shared native
programs are patched once. Each preview uses burn_time_ms and an arrow despawn
link, so early arrow cleanup also removes its companions. Aliases share a visual
and are deduplicated, even with every switch true. This adds visual layers, not
extra copies of the main mod damage. One-shot effects are not continuously replayed.

No dependency declaration is used because this ESM beta rejects such manifests.
The companion explicitly requires the main mod at apply time, which handles EML's
unordered module enumeration without applying the main mod twice. A missing main
mod or missing enabled ground hook produces an actionable Apply error.

WHAT THE SWITCHES MEAN
construct_incendiary_ground: existing native construct barrage's lingering area.
construct_heavy_fire_ground: different Heavy_Fire area candidate.
construct_barrage_explosion: explosion visual without its blast or child area.
construct_barrage_fuse: pre-explosion fuse visual without its child explosion.
construct_heavy_flamethrower: attached heavy-construct flame visual. Its emitted
  beam descendants are suppressed when identified as preview descendants.
construct_heavy_firebeam: heavy flame projectile's own visual, without damage.
construct_modular_flamethrower_on / off: separate native on/off visual templates.
construct_modular_left_flame / right_flame / onehanded_flame / firebeam:
  aliases for the associated modular ON visual; those attack helpers do not have
  separate VFX resources. These do not create additional unique fire appearances.
player_incendiary_ground: player throwable's ground visual.
dragon_artillery_ground / dragon_germination_ground: earlier dragon-area candidates.
bonfire_baseline: earlier campfire-style comparison visual.

There are 16 switches and 12 distinct template/VFX pairs. The BurningHeadPlate
debuff helper and Terraform_SnowMelt_FireBeam_Enemy are not standalone visual
templates. They are not presented as selectable, working flame previews: the
former applies a target-specific buff and the latter performs terrain changes.
Lasers, shields and non-fire rockets from the broader catalog are outside scope.

DURATION AND APPEARANCE
burn_time_ms is a nonnegative uint32 whole millisecond value; zero disables lab
overrides. There is no balance cap. visual_scale must fit nonnegative float32;
1 means the asset's native size. It does not alter the main mod's damage radius.
These settings replace the main mod's ground scale/durations only while active.

The shared time controls the spawned entity's lifetime. A one-shot explosion,
fuse or projectile particle animation can still finish earlier. It is not
repeated every tick, and a ten-second lifetime cannot convert a one-shot particle
program into ten seconds of continuous flames. Attached/toggle-driven effects
may be invisible or misplaced without their original enemy/joints/phase; that
is one of the things this identification test is intended to reveal.

Native effect identities and VFX parameters remain client-known and unchanged.
Selected preview instances skip native impact damage, burns, follow-up explosions
and terrain changes. The original mod still supplies its configured damage and
victim flames, so compare ground appearances on empty terrain first. Ordinary
enemy/throwable instances keep their native Impact behavior and natural lifetime
through a template-specific watchdog when their LifeTime component is removed.
The test does not fix Shroud target selection or mine/trap propagation.

This is experimental server-side resource logic. Guard ancestry, native emitter
visibility, multiplayer replication and actual combat need live verification.
Use a test world. No game resources, textures, executables or saves are included.
