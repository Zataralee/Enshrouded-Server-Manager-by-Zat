-- Zat Shock Tuning 0.1.0. Edit this file through ESM-Z > Mods > Configure.
-- Stop the server, save, Apply & Validate Mods, then start the server.
-- All shipped numbers preserve vanilla gameplay. config.defaults.lua is a backup.
-- Distances are game units; the exact in-game geometry needs multiplayer testing.
-- Rejects unknown settings, unsupported builds, and conflicting baseline edits.
return {
    schema_version = 1,
    chain_lightning = {
        targeting_range = 24.0, -- Initial target acquisition. Allowed: 1 to 48.
        spread_radius = 7.0,    -- Combat sphere used between targets. Allowed: 1 to 14.
        -- Raw item damage coefficients, NOT displayed damage or final health loss.
        -- Damage: 0 to 3; mana: whole number 0 to 500.
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
        -- Allowed: 0 to 2. The bow, character stats and defenses still affect damage.
        eternal_20_damage = 0.5,
        eternal_36_damage = 0.5,
        eternal_45_damage = 0.5,
    },
    mass_destruction = {
        -- Existing skill only: retains its staff/wand critical-hit requirement.
        radius = 15,                 -- Whole game units: 1 to 30.
        damage_per_intelligence = 2, -- Whole number: 0 to 10; before combat processing.
    },
    -- This prototype does NOT implement new random AOE-on-hit, jump caps,
    -- per-jump falloff, global shock debuffs or stun changes. No inactive toggles.
}
