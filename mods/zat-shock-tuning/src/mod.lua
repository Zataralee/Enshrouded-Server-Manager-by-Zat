-- Asset-only EML patch. No live Lua callbacks, native hooks, or new resource IDs.
local config = require("config")
local changes = {}
local checked = 0
local function fail(message)
    error("[Zat Shock Tuning] " .. message, 0)
end
local function keys(value, allowed, label)
    if type(value) ~= "table" then fail(label .. " must be a table") end
    for key in pairs(value) do
        if not allowed[key] then fail("Unknown setting: " .. label .. "." .. tostring(key)) end
    end
    for key in pairs(allowed) do
        if value[key] == nil then fail("Missing setting: " .. label .. "." .. key) end
    end
end
local function number(value, storage, label)
    if type(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then
        fail(label .. " must be a finite number")
    end
    if value < 0 then fail(label .. " cannot be negative") end
    if storage == "float32" then
        local ok, packed = pcall(string.pack, "<f", value)
        if not ok then fail(label .. " cannot be stored in the game's float32 field") end
        local stored = string.unpack("<f", packed)
        if stored == math.huge or stored == -math.huge or (value > 0 and stored == 0) then
            fail(label .. " overflows or underflows the game's float32 field")
        end
    else
        local maximum = storage == "uint32" and 4294967295 or 2147483647
        if value % 1 ~= 0 or value > maximum then
            fail(label .. " must be a whole number representable by the game's " .. storage .. " field (maximum " .. maximum .. ")")
        end
    end
end
local function close(a, b)
    return type(a) == "number" and math.abs(a - b) < 0.00001
end
local function resource(guid, kind)
    local value = game.assets.get_resource(guid, kind)
    if not value then fail("Missing " .. kind .. " " .. guid .. "; unsupported game data") end
    return value.data
end
local function unique(array, predicate, label)
    local result, count = nil, 0
    for _, entry in ipairs(array) do
        if predicate(entry) then result, count = entry, count + 1 end
    end
    if count ~= 1 then fail(label .. ": expected one match, found " .. count) end
    return result
end
local function plan(object, field, expected, desired, label)
    checked = checked + 1
    if not close(object[field], expected) then
        fail(label .. ": expected vanilla " .. expected .. ", found " .. tostring(object[field])
            .. ". Disable overlapping combat mods and restore the clean baseline.")
    end
    if not close(object[field], desired) then
        changes[#changes + 1] = { label = label, before = object[field], after = desired,
            apply = function() object[field] = desired end }
    end
end
local function impact_config(values, id, kind, label)
    local entry = unique(values.simple, function(x) return x.value.configId.value == id end, label)
    if entry.type ~= kind then fail(label .. ": unexpected config type " .. tostring(entry.type)) end
    return entry.value
end
local function component(template, kind)
    return unique(template.components, function(x) return x.type == kind end, kind).value
end
local function program_scalar(program, id, name, type_id, encoding, expected, desired, label)
    local entry = unique(program.dataLayout, function(x) return x.configId.value == id end, label)
    if entry.dbgName ~= name or entry.type.value ~= type_id or entry.size ~= 4 then
        fail(label .. ": unexpected Impact layout")
    end
    local offset = entry.offsetInBytes
    if offset < 0 or offset + 4 > #program.data then fail(label .. ": invalid data offset") end
    local packed = string.char(program.data[offset + 1], program.data[offset + 2],
        program.data[offset + 3], program.data[offset + 4])
    local actual = string.unpack(encoding, packed)
    checked = checked + 1
    if not close(actual, expected) then fail(label .. ": conflicting or unsupported program default") end
    if not close(actual, desired) then
        local bytes = string.pack(encoding, desired)
        changes[#changes + 1] = {label = label, before = actual, after = desired, apply = function()
            for i = 1, 4 do program.data[offset + i] = string.byte(bytes, i) end
        end}
    end
end

-- Validate the COMPLETE configuration and baseline before mutating any resource.
-- Optional in schema 1 so existing 0.1.0 configs retain their meaning.
if config.eternal_arrows == nil then
    config.eternal_arrows = {
        ice_10_damage=0.5, ice_28_damage=0.5, ice_45_damage=0.5,
        fire_15_damage=0.5, fire_28_damage=0.5, fire_45_damage=0.5,
        bone_36_damage=0.5, bone_45_damage=0.5,
    }
end
if config.arrow_chain == nil then
    config.arrow_chain = {}
    for _, tier in ipairs({"eternal_20", "eternal_36", "eternal_45"}) do
        config.arrow_chain[tier] = {enabled=false,chance_percent=100,spread_radius=7,damage=0.5,max_jumps=0}
    end
end
if config.fire_arrows == nil then config.fire_arrows = require("fire_arrows").defaults() end
keys(config, {schema_version=true, chain_lightning=true, lightning_arrows=true, eternal_arrows=true, mass_destruction=true, arrow_chain=true, fire_arrows=true}, "config")
if config.schema_version ~= 1 then fail("Unsupported configuration schema") end
local revision = tostring(game.version):match("^(%d+)|")
if revision ~= "1273043" then
    fail("Unsupported game revision " .. tostring(game.version) .. "; this prototype supports 1273043 only")
end
local chain, arrows, aoe = config.chain_lightning, config.lightning_arrows, config.mass_destruction
if type(chain)=="table" and chain.propagation==nil then
    chain.propagation={enabled=false,targets_per_spread=1,max_jumps=0}
end
keys(chain, {targeting_range=true, spread_radius=true, spells=true, propagation=true}, "chain_lightning")
keys(chain.spells, {eternal_10=true, consumable_12=true, eternal_28=true, eternal_45=true, consumable_47=true}, "spells")
keys(arrows, {eternal_20_damage=true, eternal_36_damage=true, eternal_45_damage=true}, "lightning_arrows")
keys(config.eternal_arrows, {ice_10_damage=true, ice_28_damage=true, ice_45_damage=true,
    fire_15_damage=true, fire_28_damage=true, fire_45_damage=true,
    bone_36_damage=true, bone_45_damage=true}, "eternal_arrows")
keys(aoe, {radius=true, damage_per_intelligence=true}, "mass_destruction")
number(chain.targeting_range, "float32", "targeting_range")
number(chain.spread_radius, "float32", "spread_radius")
number(aoe.radius, "int32", "mass_destruction.radius")
number(aoe.damage_per_intelligence, "uint32", "damage_per_intelligence")
local spell_defs = {
    {"eternal_10", "3cb0ef06-8586-40a3-86f5-8c34eaf0a18b", 1.12, 70},
    {"consumable_12", "4d0bab0f-27b3-4709-8699-d2ff4ec184f1", 1.12, 65},
    {"eternal_28", "d033d5d2-7fce-40fb-98dc-10f193aadc92", 1.22, 167},
    {"eternal_45", "fcf60ecf-6c33-4339-a8db-80caf141cde6", 1.22, 220},
    {"consumable_47", "4c425eba-2c6e-4dd1-a82e-60ab12f4845f", 1.22, 200},
}
for _, def in ipairs(spell_defs) do
    local settings = chain.spells[def[1]]
    keys(settings, {damage=true, mana=true}, def[1])
    number(settings.damage, "float32", def[1] .. ".damage")
    number(settings.mana, "int32", def[1] .. ".mana")
    local item = resource(def[2], "keen::ItemInfo")
    if not item.damageSetup.isSet or not item.itemTargetingSetup.isSet
        or not close(item.damageSetup.distribution.magicalLightningDamage, 1) then
        fail(def[1] .. ": unexpected item damage/targeting setup")
    end
    unique(item.sequences, function(x) return x.sequence == "12f3cda4-c44d-4a09-bc76-749e40f1c60f" end,
        def[1] .. ".sequence")
    plan(item.damageSetup, "dmgMod", def[3], settings.damage, def[1] .. ".damage")
    plan(item.itemTargetingSetup, "targetingRange", 24, chain.targeting_range, def[1] .. ".targeting_range")
    local mana = impact_config(item.impactValues, 2938334926, "keen::impact::Sint32ImpactConfig", def[1] .. ".mana")
    plan(mana, "value", def[4], settings.mana, def[1] .. ".mana")
end
local sequence = resource("12f3cda4-c44d-4a09-bc76-749e40f1c60f", "keen::actor::ActorSequenceResource")
local events = {}
for _, sub in ipairs(sequence.subSequences) do
    for _, event in ipairs(sub.events) do events[#events + 1] = event end
end
local cast = unique(events, function(x)
    return x.type == "keen::actor::SpawnImpact" and x.value.impact == "e28f0d79-e2fe-46ba-8d82-9ba368cb30c7"
end, "chain cast").value
local sphere = unique(cast.colliderData.dataArray, function(x) return x.type == "keen::ecs::SphereColliderData" end,
    "chain sphere").value
plan(sphere.shape, "radius", 7, chain.spread_radius, "chain_lightning.spread_radius")
for _, def in ipairs({
    {"lightning_arrows", "eternal_20_damage", "bf55416d-0e18-42b0-8585-73a48e0c3fdf", "magicalLightningDamage"},
    {"lightning_arrows", "eternal_36_damage", "5c93fd11-e43e-4f09-9996-ad0bed771c1d", "magicalLightningDamage"},
    {"lightning_arrows", "eternal_45_damage", "a3ef08e9-f08d-4f27-a250-e42a46d0f8e4", "magicalLightningDamage"},
    {"eternal_arrows", "ice_10_damage", "160e2952-5967-4dd9-9ea4-f3e4d63b9cad", "magicalIceDamage"},
    {"eternal_arrows", "ice_28_damage", "a5c0b376-74fc-4c6c-bd11-701e1e1821f2", "magicalIceDamage"},
    {"eternal_arrows", "ice_45_damage", "a8268d14-b644-4e8f-a5ff-5d0100330553", "magicalIceDamage"},
    {"eternal_arrows", "fire_15_damage", "2a96b858-8d2d-4564-bc85-93ea79851c0e", "magicalFireDamage"},
    {"eternal_arrows", "fire_28_damage", "686f82e2-fcf3-47ea-8199-d0157504f9f0", "magicalFireDamage"},
    {"eternal_arrows", "fire_45_damage", "232ca542-0832-4607-b827-f7c50de1603e", "magicalFireDamage"},
    {"eternal_arrows", "bone_36_damage", "d94908b5-2cca-4568-a914-9edf1e1fa492", "physicalBluntDamage"},
    {"eternal_arrows", "bone_45_damage", "e5a01755-0170-4702-887f-6d9fc4dd1d16", "physicalBluntDamage"},
}) do
    local label = def[1] .. "." .. def[2]
    local desired = config[def[1]][def[2]]
    number(desired, "float32", label)
    local item = resource(def[3], "keen::ItemInfo")
    if not item.damageSetup.isSet or not close(item.damageSetup.distribution[def[4]], 1) then
        fail(label .. ": unexpected damage setup")
    end
    plan(item.damageSetup, "dmgMod", 0.5, desired, label)
end
local skill_tree = resource("108ac23f-a77d-4f18-bfac-acc397edaaf0", "keen::SkillTreeResource")
local skill = unique(skill_tree.nodes, function(x) return x.id.value == 4208308624 end, "Mass Destruction skill")
if skill.impactReference ~= "82169841-f83e-49cb-a950-e7f0f8c22a11" then fail("Unexpected Mass Destruction trigger") end
local range = impact_config(skill.configValues, 1815063917, "keen::impact::Sint32ImpactConfig", "Mass Destruction range")
plan(range, "value", 15, aoe.radius, "mass_destruction.skill_range")
local template = resource("674340cf-757c-4672-8f60-3bec5c07b5eb", "keen::ecs::TemplateResource")
if component(template, "keen::ecs::Impact").program ~= "56188199-e5b1-452a-ba03-0915ea989fec" then
    fail("Unexpected Mass Destruction damage program")
end
local collider = component(template, "keen::ecs::ColliderResourceComponent")
if #collider.colliders ~= 1 then fail("Unexpected AOE collider count") end
local aoe_sphere = unique(collider.colliders[1].dataArray,
    function(x) return x.type == "keen::ecs::SphereColliderData" end, "AOE sphere").value
plan(aoe_sphere.shape, "radius", 15, aoe.radius, "mass_destruction.collider_radius")
local program = resource("56188199-e5b1-452a-ba03-0915ea989fec", "keen::ImpactProgram")
program_scalar(program, 1815063917, "impact_nodes.FloatValueNode::value", 3902764048, "<f", 15, aoe.radius,
    "mass_destruction.query_radius")
program_scalar(program, 4130293191, "BaseDamge::value", 848563180, "<I4", 2, aoe.damage_per_intelligence,
    "mass_destruction.damage_per_intelligence")
local chain_change = require("arrow_chain").plan(config.arrow_chain,
    {fail=fail,keys=keys,number=number,resource=resource}, config.fire_arrows)
if chain_change then changes[#changes+1]=chain_change end
local spell_change=require("spell_chain").plan(chain.propagation,chain.spread_radius,cast,
    {fail=fail,keys=keys,number=number,resource=resource})
if spell_change then changes[#changes+1]=spell_change end
print("[Zat Shock Tuning] Validated revision " .. revision .. ", " .. checked .. " baseline fields")
for _, change in ipairs(changes) do
    print("[Zat Shock Tuning] " .. change.label .. ": " .. change.before .. " -> " .. change.after)
end
for _, change in ipairs(changes) do change.apply() end
print("[Zat Shock Tuning] Applied " .. #changes .. " setting changes; server-only gameplay remains unverified")
