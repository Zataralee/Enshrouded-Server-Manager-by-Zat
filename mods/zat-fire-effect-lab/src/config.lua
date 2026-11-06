-- Zat Fire Effect Lab 0.1.0-alpha.4. Configure this mod separately in ESM-Z.
-- Keep Zat Shock Tuning 0.4.0-alpha.5 installed and enabled.
-- In its fire_arrows profile, enabled and ground_fire_enabled must both be true,
-- with positive chance_percent, initial_radius and burn_duration_ms.
-- Stop server, save, Apply & Validate Mods, then start. No machine access needed.
-- Enable any combination, including ALL effects. All false = no test overrides.
-- Aliases referencing the same native visual are spawned once, not stacked.
-- Applies to EVERY eternal-fire tier with an active ground hook in the main mod.
-- Shoot EMPTY GROUND first so normal target burns do not obscure the preview.
return {
    schema_version = 1,
    burn_time_ms = 10000, -- Shared ground-entity and victim burn duration. 0 = lab off.
    visual_scale = 1.0,  -- Native size at 1; independent of main mod's damage radius.
    effects = {
        construct_incendiary_ground = false, -- Current mod's nine-second native zone.
        construct_heavy_fire_ground = false, -- Heavy_Fire area; native lifetime 24 s.
        construct_barrage_explosion = false, -- Explosion VISUAL only; no native blast.
        construct_barrage_fuse = false,      -- Fuse VISUAL only; no follow-up explosion.
        construct_heavy_flamethrower = false,
        construct_heavy_firebeam = false,
        construct_modular_flamethrower_on = false,
        construct_modular_flamethrower_off = false,
        -- These attack helpers have no separate VFX. Preview their associated ON visual.
        construct_modular_left_flame = false,
        construct_modular_right_flame = false,
        construct_modular_onehanded_flame = false,
        construct_modular_firebeam = false,
        -- Earlier ground-fire candidates for comparison:
        player_incendiary_ground = false,
        dragon_artillery_ground = false,
        dragon_germination_ground = false,
        bonfire_baseline = false,
    },
}
