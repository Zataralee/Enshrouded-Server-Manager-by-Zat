-- Author-written Impact extension. Uses the installed program, not bundled game code.
-- Experimental: native hit history and multiplayer authority require combat testing.
local M = {}
local function fnv(s)
    local h = 2166136261
    for i=1,#s do h = ((h ~ s:byte(i)) * 16777619) & 0xffffffff end
    return h
end
local function array(a)
    local out = {}; for _,v in ipairs(a) do out[#out+1]=v end; return out
end
local function hash_array(a, encoding)
    local h=2166136261
    for _,v in ipairs(a) do
        local s=string.pack(encoding,v)
        for i=1,#s do h=((h ~ s:byte(i))*16777619)&0xffffffff end
    end
    return h
end
local defs = {
    {key="eternal_20", guid="bf55416d-0e18-42b0-8585-73a48e0c3fdf", id=3133483038, template="9e8b9693-f81f-4dbd-82a2-f9a638d7fe6f"},
    {key="eternal_36", guid="5c93fd11-e43e-4f09-9996-ad0bed771c1d", id=2453015274, template="805d84da-8e66-4757-abee-03271ada0155"},
    {key="eternal_45", guid="a3ef08e9-f08d-4f27-a250-e42a46d0f8e4", id=2369196415, template="ee33f908-7e96-449c-b1fe-8596a1e7fe28"},
}
function M.plan(settings, api, fire_settings)
    if settings == nil then return end -- Legacy configs retain disabled chains.
    local fail,keys,number,resource = api.fail,api.keys,api.number,api.resource
    keys(settings,{eternal_20=true,eternal_36=true,eternal_45=true},"arrow_chain")
    local active={}
    for _,d in ipairs(defs) do
        local s=settings[d.key]; local label="arrow_chain."..d.key
        if type(s)=="table" and s.targets_per_spread==nil then s.targets_per_spread=1 end
        if type(s)=="table" and s.spread_delay_ms==nil then s.spread_delay_ms=250 end
        keys(s,{enabled=true,chance_percent=true,spread_radius=true,damage=true,max_jumps=true,targets_per_spread=true,spread_delay_ms=true},label)
        if type(s.enabled)~="boolean" then fail(label..".enabled must be true or false") end
        number(s.chance_percent,"float32",label..".chance_percent")
        if s.chance_percent>100 then fail(label..".chance_percent must be between 0 and 100") end
        number(s.spread_radius,"float32",label..".spread_radius")
        number(s.damage,"float32",label..".damage")
        number(s.max_jumps,"uint32",label..".max_jumps")
        number(s.targets_per_spread,"uint32",label..".targets_per_spread")
        number(s.spread_delay_ms,"uint32",label..".spread_delay_ms")
        if s.chance_percent>0 then number(s.chance_percent/100,"float32",label..".chance_percent / 100") end
        if s.enabled and s.chance_percent>0 and s.spread_radius>0 and s.targets_per_spread>0 then
            if resource(d.guid,"keen::ItemInfo").itemId.value~=d.id then fail(label..": unexpected ammunition ID") end
            active[#active+1]={def=d,config=s}
        end
    end
    local fire=require("fire_arrows")
    local fire_active=fire.validate(fire_settings,api)
    if #active==0 and #fire_active==0 then return end
    local all_active={};for _,a in ipairs(active) do all_active[#all_active+1]=a end
    for _,a in ipairs(fire_active) do all_active[#all_active+1]=a end
    local p=resource("c0a8231a-f87f-467c-ad9d-6d4fe93ecda7","keen::ImpactProgram")
    local layout_signature={}
    for _,e in ipairs(p.dataLayout) do
        layout_signature[#layout_signature+1]=string.pack("<I4I4I4I4I4",e.name.value,e.configId.value,
            e.type.value,e.size,e.offsetInBytes)..e.dbgName..string.char(0)
    end
    if #p.code~=223 or hash_array(p.code,"<I4")~=3177271816
        or #p.data~=705 or hash_array(p.data,"B")~=3142341583
        or #p.codeShutdown~=1 or p.codeShutdown[1]~=30 or #p.queryCallIds~=0
        or #p.dataLayout~=55 or p.stackSize~=256 or fnv(table.concat(layout_signature))~=145110366
        or #p.usedStreams~=1 or p.usedStreams[1]~="OnCollision"
        or p.id.value~=102728174 or p.programGuid~="c0a8231a-f87f-467c-ad9d-6d4fe93ecda7" then
        fail("Arrow chain: conflicting or unsupported projectile program; restore vanilla")
    end
    local B=require("impact_builder")
    local propagation=require("chain_propagation")
    local b=B.new(p,api,"ZatArrowChain")
    local ammo=b.entry("Ammunition::value")
    if ammo.type.value~=1543245243 or ammo.size~=4 then fail("Unexpected ItemId representation") end
    b.alias("ammunition_value","Ammunition::value",848563180)
    local chain="e28f0d79-e2fe-46ba-8d82-9ba368cb30c7"
    if hash_array(resource(chain,"keen::ImpactProgram").data,"B")~=1813197745 then
        fail("Arrow chain: conflicting or unsupported native chain constants")
    end
    for _,a in ipairs(all_active) do a.key=a.def.key;b.uint(a.key.."_id",a.def.id) end
    local flight_config=B.fnv("ZatArrowChain.ManagedFlight")
    b.bool("managed_flight",false,flight_config)
    b.bool("flight_started",false);b.uint("flight_start",0);b.uint("flight_limit",5000)
    b.uint("flight_elapsed",0)
    -- Replace only enabled shock projectiles' server-only LifeTime component
    -- with a VM flight watchdog. Propagation owns destruction after a hit.
    -- Removing a shared program's generic timeout would leak missed arrows.
    local lifetimes={}
    for _,a in ipairs(all_active) do
        local template=resource(a.def.template,"keen::ecs::TemplateResource")
        local remaining={};local count=0;local impact=false;local config_values
        for _,c in ipairs(template.components) do
            if c.type=="keen::ecs::LifeTime" then
                local v=c.value;count=count+1
                if v.lifeTime.value~=5000000000 or v.endOfLife.value~=0 or v.enforceDestroy
                    or v.preventDestroy or v.triggeredDestroy then fail("Arrow chain: conflicting projectile lifetime") end
            else
                remaining[#remaining+1]=c
                if c.type=="keen::ecs::Impact" then impact=c.value.program==p.programGuid end
                if c.type=="keen::ecs::ImpactConfiguration" then config_values=c.value.configValues end
            end
        end
        if count~=1 or not impact or not config_values or #config_values.simple==0 then
            fail("Arrow chain: unsupported projectile lifetime/program/config") end
        for _,entry in ipairs(config_values.simple) do
            if entry.value.configId.value==flight_config then fail("Arrow chain: conflicting flight configuration") end
        end
        lifetimes[#lifetimes+1]={template=template,components=remaining,config=config_values}
    end
    local ground_apply=require("ground_fire").plan(fire_active,api)
    fire.prepare(b,fire_active,api)
    local storage_profiles=active
    if #fire_active>0 then
        -- Fire and shock are mutually exclusive for a shot and share one arena.
        -- Reserve the native maximum even if shock uses a small finite frontier.
        storage_profiles={};for _,a in ipairs(active) do storage_profiles[#storage_profiles+1]=a end
        storage_profiles[#storage_profiles+1]={key="fire_storage",config={spread_radius=0,
            targets_per_spread=2,max_jumps=0,chance_percent=100,spread_delay_ms=0}}
    end
    propagation.prepare(b,storage_profiles,api)
    local function gate(a,target)
        b.equal("ammunition_value",a.key.."_id");b.branch(9,target)
    end
    local flight=#b.code
    b.load("managed_flight");b.branch(10,"flight_return")
    b.mark("flight");b.load("flight_started");b.branch(9,"flight_check")
    b.emit(25);b.save("flight_start");b.emit(13);b.save("flight_started")
    b.mark("flight_check")
    b.emit(25);b.load("flight_start");b.emit(2);b.save("flight_elapsed")
    b.uless("flight_elapsed","flight_limit");b.branch(9,"flight_return")
    b.emit(29,30)
    b.mark("flight_return");b.emit(p.code[1],p.code[2],8,2)
    local collision,ground
    if #fire_active>0 then
        collision=#b.code
        b.call("ForEachCollisionInStream",{"SameRoot::eventStream","ForEach::index",false,
            "ForEach::isCombatTarget",false,"ForEach::materialId","fire_impact_transform",
            "ForEach::normal","ForEach::position",false,"ForEach::otherEntity"},3996774287)
        b.emit(8,60)
        ground=#b.code
        for _,a in ipairs(fire_active) do
            local s=a.config
            if s.ground_fire_enabled and s.ground_fire_duration_ms>0 and s.initial_radius>0 then gate(a,a.key.."_ground_hit") end
        end
        b.emit(8,92)
        for _,a in ipairs(fire_active) do
            b.mark(a.key.."_ground_hit")
            b.emit(13);b.save("fire_ground_hit")
            b.copy("fire_impact_transform","origin")
            -- Same native random/coefficient calculation as an enemy hit, without
            -- applying direct damage to terrain. Burn keeps the shot's bow scaling.
            for i=95,136 do b.emit(p.code[i]) end
            b.branch(8,a.key.."_fire_start")
        end
    end
    local pre=#b.code
    for _,a in ipairs(all_active) do gate(a,"capture") end
    b.emit(8,94)
    b.mark("capture")
    propagation.capture(b,"ForEach::otherEntity","GetRoot::entityId")
    b.emit(8,94)
    local post=#b.code
    for _,a in ipairs(active) do gate(a,a.key.."_start") end
    for _,a in ipairs(fire_active) do gate(a,a.key.."_fire_start") end
    b.emit(8,191)
    local context={initial="ForEach::otherEntity",root="GetRoot::entityId",damage_args=function(prefix)
        return {false,"true",false,false,"false","CanBeBlocked::value",false,
            "material::valueId","WeaponCategory::value","AttackCategory::value","Damage::value",
            "hitReactionType::value","PushBackStrength::value","DamageScaleAttribute::value",false,
            false,"NoiseRange::value","staminaMod::value",prefix.."damage","HitDirection::value",
            "ForEach::normal","position","best","GetRoot::entityId","was_blocked"}
    end}
    for _,a in ipairs(active) do propagation.emit(b,a,context) end
    propagation.finish(b);b.emit(8,191)
    fire.emit(b,fire_active,api)
    b.finish();if collision then b.code[40]=8;b.code[41]=collision;b.code[222]=ground end
    b.code[1]=8;b.code[2]=flight;b.code[90]=pre;b.code[212]=post
    return {label="arrow_chain.nearest_fanout_program",before=0,after=#all_active,apply=function()
        print("[Zat Shock Tuning] Arrow frontier native storage: "..b.capacity.." pending spreaders; slots are reused")
        if b.fire_capacity then print("[Zat Shock Tuning] Fire ignition ledger native storage: "..b.fire_capacity.." unique victims per shot (includes first); full ledgers stop spreading and finish existing burns") end
        b.apply()
        for _,v in ipairs(lifetimes) do
            local values={};for _,entry in ipairs(v.config.simple) do values[#values+1]=entry end
            local guid="d61966d4-864b-48ac-8906-3e69921ec5ed"
            values[#values+1]={type="keen::impact::BoolImpactConfig",value={locaTag=values[1].value.locaTag,
                isSigned=false,valueFormat="Normal",id=guid,configId={value=flight_config},
                type={value=3365180733},configGuid=guid,objectId="51fe97d0-593a-4193-b1db-b64bf09a22f9",value=true}}
            v.config.simple=values
            v.template.components=v.components
        end
        ground_apply()
    end}
end
return M
