-- Zat Shock Tuning 0.1.1. Edit this file through ESM-Z > Mods > Configure.
-- Stop the server, save, Apply & Validate Mods, then start the server.
-- All shipped numbers preserve vanilla gameplay. config.defaults.lua is a backup.
-- Distances are game units; the exact in-game geometry needs multiplayer testing.
-- Rejects unknown settings, unsupported builds, and conflicting baseline edits.
-- Recommended ranges below are suggestions only, NOT enforced balance caps.
-- Numbers must be finite, nonnegative and fit the game's field type.
-- Zero is accepted. Integer fields require whole numbers.
-- Numeric representability does NOT guarantee runtime safety for extreme values.
return {
    schema_version = 1,
    chain_lightning = {
        targeting_range = 24.0, -- Initial target acquisition. Suggested: 1 to 48; float32.
        spread_radius = 7.0,    -- Combat sphere used between targets. Suggested: 1 to 14; float32.
        -- Raw item damage coefficients, NOT displayed damage or final health loss.
        -- Suggested damage: 0 to 3 (float32); mana: 0 to 500 (signed 32-bit integer).
        spells = {
            eternal_10 = { damage = 1.12, mana = 70 },
            consumable_12 = { damage = 1.12, mana = 65 },
            eternal_28 = { damage = 1.22, mana = 167 },
            eternal_45 = { damage = 1.22, mana = 220 },
            consumable_47 = { damage = 1.22, mana = 200 },
        },
    },
    lightning_arrows = {
        -- Direct-hit raw damage coefficient. Does NOT add an explosion or change crit chance.
        -- Suggested: 0 to 2 (float32). Bow, stats and defenses still affect damage.
        eternal_20_damage = 0.5,
        eternal_36_damage = 0.5,
        eternal_45_damage = 0.5,
    },
    eternal_arrows = {
        -- Other eternal arrows: direct-hit coefficients, vanilla 0.5 for each.
        -- Suggested: 0 to 2 (float32). Each level is independent.
        -- Preserves each arrow's damage type; this does NOT enable AOE yet.
        -- Lightning settings remain in lightning_arrows for config compatibility.
        ice_10_damage = 0.5,
        ice_28_damage = 0.5,
        ice_45_damage = 0.5,
        fire_15_damage = 0.5,
        fire_28_damage = 0.5,
        fire_45_damage = 0.5,
        bone_36_damage = 0.5,
        bone_45_damage = 0.5,
    },
    mass_destruction = {
        -- Existing skill only: retains its staff/wand critical-hit requirement.
        radius = 15,                 -- Suggested: 1 to 30; nonnegative signed 32-bit integer.
        damage_per_intelligence = 2, -- Suggested: 0 to 10; unsigned 32-bit integer, before combat processing.
    },
    -- This prototype does NOT implement new random AOE-on-hit, jump caps,
    -- per-jump falloff, global shock debuffs or stun changes. No inactive toggles.
}
