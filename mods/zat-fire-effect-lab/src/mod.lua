local c=require("config")
local catalog=require("catalog")
local B=require("impact_builder")
local P=require("preview")
local function fail(s) error("[Zat Fire Effect Lab] "..s,0) end
local function keys(t,allowed,label)
    if type(t)~="table" then fail(label.." must be a table") end
    for k in pairs(t) do if not allowed[k] then fail("Unknown "..label.." setting: "..tostring(k)) end end
    for k in pairs(allowed) do if t[k]==nil then fail("Missing "..label.." setting: "..k) end end
end
keys(c,{schema_version=true,burn_time_ms=true,visual_scale=true,effects=true},"config")
keys(c.effects,catalog,"effects")
if c.schema_version~=1 then fail("Unsupported schema") end
if type(c.burn_time_ms)~="number" or c.burn_time_ms~=c.burn_time_ms or c.burn_time_ms<0
    or c.burn_time_ms>4294967295 or c.burn_time_ms%1~=0 then fail("burn_time_ms must be a nonnegative uint32 whole number") end
if type(c.visual_scale)~="number" or c.visual_scale~=c.visual_scale or c.visual_scale<0 then fail("visual_scale must be finite and nonnegative") end
local ok,packed=pcall(string.pack,"<f",c.visual_scale)
if not ok or string.unpack("<f",packed)==math.huge or (c.visual_scale>0 and string.unpack("<f",packed)==0) then fail("visual_scale must fit float32") end
local selected={}
for key in pairs(catalog) do
    if type(c.effects[key])~="boolean" then fail(key.." must be true or false") end
    if c.effects[key] then
        selected[#selected+1]=key
    end
end
table.sort(selected)
if #selected==0 or c.burn_time_ms==0 then print("[Zat Fire Effect Lab] Disabled: no test overrides");return end
-- Multiple helper names share one native visual. Spawn that visual only once.
local effects,seen={},{}
for _,key in ipairs(selected) do
    local def=catalog[key]
    if not seen[def[1]] then
        effects[#effects+1]={key=key,def=def};seen[def[1]]=true
    end
end
local revision=tostring(game.version):match("^(%d+)|")
if revision~="1273043" and revision~="1285601" and revision~="1287369" then
    fail("Unsupported game revision "..tostring(game.version).."; supported revisions: 1273043, 1285601, 1287369")
end
-- ESM beta rejects manifest dependencies. Explicit require is deterministic even
-- when EML enumerates mods in hash-map order, and caches the main mod once.
local loaded,message=pcall(require,"mods.zat-shock-tuning")
if not loaded then fail("Enable Zat Shock Tuning 0.4.0-alpha.5 alongside this mod. "..tostring(message)) end
local function resource(guid,kind)
    local r=game.assets.get_resource(guid,kind)
    if not r then fail("Missing native resource "..guid) end
    return r.data
end
local api={fail=fail,resource=resource}
local arrow=resource("c0a8231a-f87f-467c-ad9d-6d4fe93ecda7","keen::ImpactProgram")
local arrow_bytes=B.array(arrow.data)
local entries={};for _,e in ipairs(arrow.dataLayout) do entries[e.dbgName]=e end
local function field(name,size,typ)
    local e=entries["ZatArrowChain::"..name]
    if not e or e.size~=size or e.type.value~=typ then fail("Missing compatible ground hook. Enable fire_arrows.<tier>.enabled and ground_fire_enabled in Zat Shock Tuning 0.4.0-alpha.5, with positive radius, chance and burn duration.") end
    return e
end
local function bytes(e,s)
    if #s~=e.size then fail("Internal field size mismatch") end
    for i=1,#s do arrow_bytes[e.offsetInBytes+i]=s:byte(i) end
end
local function uint(e)
    local s={};for i=1,4 do s[i]=string.char(arrow.data[e.offsetInBytes+i]) end
    return string.unpack("<I4",table.concat(s))
end
local pointer=field("fire_ground_template",16,709155311)
local active={}
for _,tier in ipairs({15,28,45}) do
    local prefix="fire_"..tier.."_fire_"
    local e=entries["ZatArrowChain::"..prefix.."ground_duration"]
    if e and uint(e)>0 then
        active[#active+1]={field(prefix.."duration",4,848563180),e,field(prefix.."ground_scale",4,3902764048)}
    end
end
if #active==0 then fail("No active eternal-fire ground hook. Enable ground_fire_enabled and a positive ground_fire_duration_ms in the main mod.") end
local template_changes,programs={},{}
local function plan_template(effect,leader)
local def=effect.def;local template=resource(def[1],"keen::ecs::TemplateResource")
local components={};local config;local impact;local lifetime=0;local visual
for _,v in ipairs(template.components) do
    if v.type=="keen::ecs::LifeTime" then
        lifetime=v.value.lifeTime.value/1000000
        if lifetime%1~=0 or lifetime<0 or lifetime>4294967295 or v.value.preventDestroy or v.value.enforceDestroy then fail("Unsupported native lifetime") end
    else components[#components+1]=v end
    if v.type=="keen::ecs::Impact" then impact=v.value end
    if v.type=="keen::ecs::ImpactConfiguration" then config=v.value.configValues end
    if v.type=="keen::ecs::VfxComponentResource" then visual=v.value.vfx end
end
if visual~=def[2] then fail("Effect visual differs from the supported baseline") end
-- Visual-only templates gain a server controller using the existing GetRoot stub.
-- The original client-known template/VFX identity remains unchanged.
if not impact then
    local stub=resource("db121f88-5c64-4948-bfdc-5c02462368e3","keen::ImpactProgram")
    impact={program=stub.programGuid,programId={value=stub.id.value},impactId={id=0}}
    components[#components+1]={type="keen::ecs::Impact",value=impact}
    components[#components+1]={type="keen::ecs::ImpactHierarchy",value={parentImpactId={id=0},rootImpactId={id=0},weaponPideId={id=0},permissionCheckId={id=0}}}
end
if not config then
    config={simple={},scaled={}}
    components[#components+1]={type="keen::ecs::ImpactConfiguration",value={configValues=config,
        damageDistribution={physicalCutDamage=0,physicalPierceDamage=0,physicalBluntDamage=0,
            magicalFireDamage=0,magicalIceDamage=0,magicalFogDamage=0,magicalLightningDamage=0,
            healing=0,poisonDamage=0,woodDamage=0,stoneDamage=0,metalDamage=0,explosionDamage=0},damageDistributionIsSet=false}}
end
local values={};for _,v in ipairs(config.simple) do
    if v.value.configId.value==P.selected_config or v.value.configId.value==P.lifetime_config
        or v.value.configId.value==P.leader_config then fail("Duplicate test configuration") end
    values[#values+1]=v
end
values[#values+1]=P.config("Bool",P.selected_config,true,"c7416a75-c9d3-4d16-8fc0-7792e4d0f925")
values[#values+1]=P.config("Uint32",P.lifetime_config,lifetime,"226427c6-7ed4-47c6-ac32-1be86859c548")
values[#values+1]=P.config("Bool",P.leader_config,leader,"355bd709-3700-4357-a1ed-8f81b8ed053b")
local plan=programs[impact.program] or {guid=impact.program}
plan.suppress=impact.program=="80024779-8439-4e3c-afde-bb1f80ec10bc"
if leader then plan.siblings={};for i=2,#effects do plan.siblings[#plan.siblings+1]=effects[i].def[1] end end
programs[impact.program]=plan
template_changes[#template_changes+1]=function() config.simple=values;template.components=components end
end
for i,effect in ipairs(effects) do plan_template(effect,i==1) end
if c.effects.construct_heavy_flamethrower then
    local guid="80024779-8439-4e3c-afde-bb1f80ec10bc"
    programs[guid]=programs[guid] or {guid=guid,suppress=true}
end
local changes={};local ids={};for guid in pairs(programs) do ids[#ids+1]=guid end;table.sort(ids)
for _,guid in ipairs(ids) do
    local plan=programs[guid]
    changes[#changes+1]=P.plan(resource(guid,"keen::ImpactProgram"),api,c.burn_time_ms,plan.suppress,plan.siblings)
end
-- All validation and bytecode planning above must succeed before mutation.
for _,apply in ipairs(changes) do apply() end
for _,apply in ipairs(template_changes) do apply() end
bytes(pointer,P.guid_bytes(effects[1].def[1]))
for _,a in ipairs(active) do
    bytes(a[1],string.pack("<I4",c.burn_time_ms));bytes(a[2],string.pack("<I4",c.burn_time_ms));bytes(a[3],packed)
end
arrow.data=arrow_bytes
print("[Zat Fire Effect Lab] "..table.concat(selected,", ").."; "..#effects.." unique visuals; shared burn time "..c.burn_time_ms.." ms; native visual scale "..c.visual_scale.."; "..#active.." fire tier(s). Native rendering and multiplayer behavior require in-game verification.")
