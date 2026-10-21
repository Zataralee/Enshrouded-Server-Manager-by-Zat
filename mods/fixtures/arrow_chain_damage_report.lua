-- Exact setting values supplied in the alpha.1 no-arrow-damage report.
-- Test input only; not the shipped default configuration.
return {
    schema_version = 1,
    chain_lightning = {
        targeting_range = 48.0,
        spread_radius = 14.0,
        spells = {
            eternal_10 = { damage = 1.12, mana = 70 },
            consumable_12 = { damage = 1.12, mana = 65 },
            eternal_28 = { damage = 1.22, mana = 167 },
            eternal_45 = { damage = 1.22, mana = 220 },
            consumable_47 = { damage = 1.22, mana = 200 },
        },
    },
    lightning_arrows = {
        eternal_20_damage = 0.5,
        eternal_36_damage = 0.5,
        eternal_45_damage = 3.0,
    },
    eternal_arrows = {
        ice_10_damage = 0.5, ice_28_damage = 0.5, ice_45_damage = 3.0,
        fire_15_damage = 0.5, fire_28_damage = 0.5, fire_45_damage = 3.0,
        bone_36_damage = 0.5, bone_45_damage = 0.5,
    },
    arrow_chain = {
        eternal_20 = { enabled = false, chance_percent = 100, spread_radius = 7.0, damage = 0.5, max_jumps = 0 },
        eternal_36 = { enabled = false, chance_percent = 100, spread_radius = 7.0, damage = 0.5, max_jumps = 0 },
        eternal_45 = { enabled = true, chance_percent = 100, spread_radius = 48.0, damage = 3.0, max_jumps = 20 },
    },
    mass_destruction = { radius = 15, damage_per_intelligence = 2 },
}
