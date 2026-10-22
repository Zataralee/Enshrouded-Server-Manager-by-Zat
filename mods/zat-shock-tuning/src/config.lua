-- Zat Shock Tuning 0.4.0-alpha.1. Edit through ESM-Z > Mods > Configure.
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
        -- Opt in to nearest-first branching for all five player spells below.
        -- 1 target per spread = linear; 3 = each victim can fan out to 3 more.
        -- max_jumps counts TOTAL secondary targets across all branches; 0 = no configured limit.
        -- spread_delay_ms is also independent for the spells; 250 = 0.25 seconds.
        propagation = { enabled = false, targets_per_spread = 1, max_jumps = 0, spread_delay_ms = 250 },
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
        -- Preserves each arrow's damage type; fire ignition is enabled separately in fire_arrows.
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
    arrow_chain = {
        -- EXPERIMENTAL: opt in on a test world. Server-only combat is unverified.
        -- One chance roll per successful, unblocked enemy arrow hit; 100 = always.
        -- spread_radius: distance from the last hit enemy; 7 matches the spell.
        -- damage: secondary attack coefficient, independent of the direct hit.
        -- max_jumps: secondary targets; 0 = no user limit. Nonnegative uint32.
        -- Native hit history excludes previous victims. No extra mana per jump.
        -- Nearest living, hostile targets first, measured from EACH spreader in 3D.
        -- targets_per_spread: 1 = linear, 3 = branching; 0 disables propagation.
        -- max_jumps is a shared TOTAL secondary-target budget; 0 = no configured limit.
        -- spread_delay_ms: delay before first spread and between generations (250 = 0.25 s).
        -- Whole milliseconds, 0 = next engine update; uint32, no balance cap.
        -- Shared pending reservations and hit history prevent duplicate targets.
        -- Native frontier storage is finite and logged on Apply; slots are reused.
        -- Missed arrows expire after 5 seconds; active chains have no flight timeout.
        -- No balance caps; range/damage use float32, chance is 0..100 percent.
        eternal_20 = { enabled = false, chance_percent = 100, spread_radius = 7.0, damage = 0.5, max_jumps = 0, targets_per_spread = 1, spread_delay_ms = 250 },
        eternal_36 = { enabled = false, chance_percent = 100, spread_radius = 7.0, damage = 0.5, max_jumps = 0, targets_per_spread = 1, spread_delay_ms = 250 },
        eternal_45 = { enabled = false, chance_percent = 100, spread_radius = 7.0, damage = 0.5, max_jumps = 0, targets_per_spread = 1, spread_delay_ms = 250 },
    },
    fire_arrows = {
        -- EXPERIMENTAL: initially disabled. Each tier is independent.
        -- Normal arrow impact stays intact. Ignition adds NO instant blast.
        -- initial_radius ignites living hostiles around the first hit.
        -- Each burning victim spreads to its nearest living, non-Soaked hostiles.
        -- targets_per_spread = 0 disables later spread, not initial ignition.
        -- max_jumps counts ALL additional ignitions, including the initial area;
        -- 0 = no configured budget. Native ledger capacity is logged on Apply.
        -- Full ledger: stop new ignitions and finish existing burns safely.
        -- Damage uses the shot's FIRE component and native bow/ranged modifiers.
        -- strength is damage per second relative to that shot, NOT flat HP.
        -- Tick timing is normalized, including the last partial tick.
        -- Tick/delay 0 = next update; duration 0 disables this tier's burn.
        -- Death, Soaked, expiry or lost shooter end the corresponding burn.
        -- Each arrow has its OWN burn: repeated arrows stack independently.
        -- Suggested start: radius 3/5, fan-out 3, delay 350 ms, duration 5000 ms,
        -- tick 500 ms, strength 0.2. Suggestions only; no balance caps.
        fire_15 = { enabled = false, chance_percent = 100, initial_radius = 3.0, spread_radius = 5.0, targets_per_spread = 3, spread_delay_ms = 350, max_jumps = 0, burn_duration_ms = 5000, burn_tick_ms = 500, burn_damage_multiplier_per_second = 0.2 },
        fire_28 = { enabled = false, chance_percent = 100, initial_radius = 3.0, spread_radius = 5.0, targets_per_spread = 3, spread_delay_ms = 350, max_jumps = 0, burn_duration_ms = 5000, burn_tick_ms = 500, burn_damage_multiplier_per_second = 0.2 },
        fire_45 = { enabled = false, chance_percent = 100, initial_radius = 3.0, spread_radius = 5.0, targets_per_spread = 3, spread_delay_ms = 350, max_jumps = 0, burn_duration_ms = 5000, burn_tick_ms = 500, burn_damage_multiplier_per_second = 0.2 },
    },
    mass_destruction = {
        -- Existing skill only: retains its staff/wand critical-hit requirement.
        radius = 15,                 -- Suggested: 1 to 30; nonnegative signed 32-bit integer.
        damage_per_intelligence = 2, -- Suggested: 0 to 10; unsigned 32-bit integer, before combat processing.
    },
    -- No persistent burning ground, ice/bone AOE,
    -- per-jump falloff, global shock debuffs or stun changes. No inactive toggles.
}
