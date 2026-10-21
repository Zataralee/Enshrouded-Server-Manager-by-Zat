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
    {key="eternal_20", guid="bf55416d-0e18-42b0-8585-73a48e0c3fdf", id=3133483038},
    {key="eternal_36", guid="5c93fd11-e43e-4f09-9996-ad0bed771c1d", id=2453015274},
    {key="eternal_45", guid="a3ef08e9-f08d-4f27-a250-e42a46d0f8e4", id=2369196415},
}
function M.plan(settings, api)
    if settings == nil then return end -- Legacy configs retain disabled chains.
    local fail,keys,number,resource = api.fail,api.keys,api.number,api.resource
    keys(settings,{eternal_20=true,eternal_36=true,eternal_45=true},"arrow_chain")
    local active={}
    for _,d in ipairs(defs) do
        local s=settings[d.key]; local label="arrow_chain."..d.key
        if type(s)=="table" and s.targets_per_spread==nil then s.targets_per_spread=1 end
        keys(s,{enabled=true,chance_percent=true,spread_radius=true,damage=true,max_jumps=true,targets_per_spread=true},label)
        if type(s.enabled)~="boolean" then fail(label..".enabled must be true or false") end
        number(s.chance_percent,"float32",label..".chance_percent")
        if s.chance_percent>100 then fail(label..".chance_percent must be between 0 and 100") end
        number(s.spread_radius,"float32",label..".spread_radius")
        number(s.damage,"float32",label..".damage")
        number(s.max_jumps,"uint32",label..".max_jumps")
        number(s.targets_per_spread,"uint32",label..".targets_per_spread")
        if s.chance_percent>0 then number(s.chance_percent/100,"float32",label..".chance_percent / 100") end
        if s.enabled and s.chance_percent>0 and s.spread_radius>0 and s.targets_per_spread>0 then
            if resource(d.guid,"keen::ItemInfo").itemId.value~=d.id then fail(label..": unexpected ammunition ID") end
            active[#active+1]={def=d,config=s}
        end
    end
    if #active==0 then return end
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
    for _,a in ipairs(active) do a.key=a.def.key;b.uint(a.key.."_id",a.def.id) end
    propagation.prepare(b,active,api)
    local function gate(a,target)
        b.equal("ammunition_value",a.key.."_id");b.branch(9,target)
    end
    local pre=#b.code
    for _,a in ipairs(active) do gate(a,"capture") end
    b.emit(8,94)
    b.mark("capture")
    b.call("IsEnemy",{"GetRoot::entityId","ForEach::otherEntity"});b.save("eligible")
    b.done("GetTransform",{"ForEach::otherEntity",false,"origin"})
    b.emit(8,94)
    local post=#b.code
    for _,a in ipairs(active) do gate(a,a.key.."_start") end
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
    b.finish();b.code[90]=pre;b.code[212]=post
    return {label="arrow_chain.nearest_fanout_program",before=0,after=#active,apply=function()
        print("[Zat Shock Tuning] Arrow frontier native storage: "..b.capacity.." pending spreaders; slots are reused")
        b.apply()
    end}
end
return M
