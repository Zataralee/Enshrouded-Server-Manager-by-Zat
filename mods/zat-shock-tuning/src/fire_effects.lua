-- Integrated native fire visuals. No separate mod or cross-mod require.
local M={}
local catalog=require("fire_effect_catalog")
local B=require("impact_builder")
local P=require("fire_effect_preview")
function M.defaults()
    local effects={};for name in pairs(catalog) do effects[name]=false end
    return {burn_time_ms=10000,visual_scale=1,effects=effects}
end
function M.validate(c,api)
    api.keys(c,{burn_time_ms=true,visual_scale=true,effects=true},"fire_effects")
    api.keys(c.effects,catalog,"fire_effects.effects")
    api.number(c.burn_time_ms,"uint32","fire_effects.burn_time_ms")
    api.number(c.visual_scale,"float32","fire_effects.visual_scale")
    local selected={}
    for name in pairs(catalog) do
        if type(c.effects[name])~="boolean" then api.fail("fire_effects.effects."..name.." must be true or false") end
        if c.effects[name] then selected[#selected+1]=name end
    end
    table.sort(selected)
    return selected
end
function M.apply(c,selected,profiles,api)
    if #selected==0 or c.burn_time_ms==0 then return end
    local fail=api.fail
    local eligible=0
    for _,tier in ipairs({"fire_15","fire_28","fire_45"}) do
        local s=profiles[tier]
        if s.enabled and s.chance_percent>0 and s.burn_duration_ms>0
            and s.ground_fire_enabled and s.initial_radius>0 and s.ground_fire_duration_ms>0 then
            eligible=eligible+1
            api.number(s.burn_damage_multiplier_per_second*(c.burn_time_ms/1000),
                "float32","fire_effects shared total burn multiplier for "..tier)
        end
    end
    -- Selected visuals may be saved while fire is off. Respect the user's fire
    -- switches; an inactive profile must not block unrelated arrows or startup.
    if eligible==0 then
        print("[Zat Fire Effects] Inactive: no enabled ground-fire profile; saved visual selections retained. Other tuning still applies.")
        return
    end
    local packed=string.pack("<f",c.visual_scale)
    -- Multiple helper names share one native visual. Spawn that visual only once.
    local effects,seen={},{}
    for _,key in ipairs(selected) do
        local def=catalog[key]
        if not seen[def[1]] then
            effects[#effects+1]={key=key,def=def};seen[def[1]]=true
        end
    end
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
        if not e or e.size~=size or e.type.value~=typ then fail("Missing compatible ground hook. The combined fire-arrow program did not expose its expected fields; restore the baseline and disable overlapping mods.") end
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
    if #active==0 then fail("Internal ground-fire profile mismatch") end
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
    print("[Zat Fire Effects] "..table.concat(selected,", ").."; "..#effects.." unique visuals; shared burn time "..c.burn_time_ms.." ms; native visual scale "..c.visual_scale.."; "..#active.." fire tier(s). Native rendering and multiplayer behavior require in-game verification.")

end
return M
