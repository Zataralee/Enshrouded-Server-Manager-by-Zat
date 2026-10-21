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
        keys(s,{enabled=true,chance_percent=true,spread_radius=true,damage=true,max_jumps=true},label)
        if type(s.enabled)~="boolean" then fail(label..".enabled must be true or false") end
        number(s.chance_percent,"float32",label..".chance_percent")
        if s.chance_percent>100 then fail(label..".chance_percent must be between 0 and 100") end
        number(s.spread_radius,"float32",label..".spread_radius")
        number(s.damage,"float32",label..".damage")
        number(s.max_jumps,"uint32",label..".max_jumps")
        if s.chance_percent>0 then number(s.chance_percent/100,"float32",label..".chance_percent / 100") end
        if s.enabled and s.chance_percent>0 and s.spread_radius>0 then
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
    local code,data,layout,queries=array(p.code),array(p.data),{},{}
    local vars={}
    for i,e in ipairs(p.dataLayout) do
        layout[i]={name={value=e.name.value},configId={value=e.configId.value},type={value=e.type.value},
            size=e.size,offsetInBytes=e.offsetInBytes,dbgName=e.dbgName}
        vars[e.dbgName]=0xffff0000+i-1
    end
    local function add(name,typ,bytes)
        local alignment=math.max(#bytes,16)
        while #data % alignment~=0 do data[#data+1]=0 end
        if #data+#bytes>65535 or #layout>=65535 then fail("Arrow chain exceeds Impact storage format") end
        local index=0xffff0000+#layout
        local dbg="ZatArrowChain::"..name
        layout[#layout+1]={name={value=fnv(dbg)},configId={value=0},type={value=typ},
            size=#bytes,offsetInBytes=#data,dbgName=dbg}
        for i=1,#bytes do data[#data+1]=bytes:byte(i) end
        vars[name]=index
        return name
    end
    local function uint(name,v) return add(name,848563180,string.pack("<I4",v)) end
    local function float(name,v) return add(name,3902764048,string.pack("<f",v)) end
    local function from_native(name,guid,entry)
        local source=resource(guid,"keen::ImpactProgram")
        local found
        for _,e in ipairs(source.dataLayout) do if e.dbgName==entry then
            if found then fail("Duplicate native chain constant "..entry) end
            found=e
        end end
        if not found then fail("Missing native chain constant "..entry) end
        local bytes={}
        for i=1,found.size do bytes[i]=string.char(source.data[found.offsetInBytes+i]) end
        return add(name,found.type.value,table.concat(bytes))
    end
    local chain="e28f0d79-e2fe-46ba-8d82-9ba368cb30c7"
    if hash_array(resource(chain,"keen::ImpactProgram").data,"B")~=1813197745 then
        fail("Arrow chain: conflicting or unsupported native chain constants")
    end
    from_native("origin",chain,"ImpactTransform::transform")
    from_native("visual",chain,"Template::value")
    from_native("factions",chain,"impact_nodes.FilterFaction::faction")
    add("true",3365180733,string.char(1))
    add("false",3365180733,string.char(0))
    add("eligible",3365180733,string.char(0))
    add("candidate",1937543046,string.pack("<I4",0))
    local position_type=layout[(vars["ForEach::position"] & 0xffff)+1].type.value
    add("position",position_type,string.rep(string.char(0),12))
    uint("index",0); uint("jumps",0); uint("hits_before",0); uint("hits_after",0)
    local labels,fixups={},{}
    local serial=0
    local function emit(...) for _,v in ipairs({...}) do code[#code+1]=v end end
    local function mark(name) labels[name]=#code end
    local function branch(op,name) emit(op,0); fixups[#fixups+1]={#code,name} end
    local function ptr(name)
        if name==false then emit(12) else
            if not vars[name] then fail("Arrow chain: missing variable "..tostring(name)) end
            emit(11,vars[name])
        end
    end
    local function load(name) emit(22,vars[name]) end
    local function save(name) emit(24,vars[name]) end
    local function call(name,args,id)
        for _,a in ipairs(args) do ptr(a) end
        serial=serial+1
        emit(19,id or fnv("ZatArrowChain.Call."..serial),fnv(name))
    end
    local function donecall(name,args,id) call(name,args,id); emit(27) end
    local function ammo_gate(d,target)
        load("Ammunition::value");load(d.key.."_id");emit(6);branch(9,target)
    end
    for _,a in ipairs(active) do
        local d,s=a.def,a.config
        uint(d.key.."_id",d.id); float(d.key.."_radius",s.spread_radius)
        float(d.key.."_damage",s.damage);float(d.key.."_chance",s.chance_percent/100)
        uint(d.key.."_limit",s.max_jumps)
    end
    -- Only the combat branch and the post-buff unblocked-hit branch are redirected.
    -- All original instruction addresses and all other paths remain intact.
    local pre=#code
    for _,a in ipairs(active) do ammo_gate(a.def,"capture") end
    emit(8,94)
    mark("capture")
    call("IsEnemy",{"GetRoot::entityId","ForEach::otherEntity"});save("eligible")
    donecall("GetTransform",{"ForEach::otherEntity",false,"origin"})
    emit(8,94)
    local post=#code
    for _,a in ipairs(active) do ammo_gate(a.def,a.def.key.."_start") end
    emit(8,191)
    local shutdown={}
    for _,a in ipairs(active) do
        local d,s=a.def,a.config;local prefix=d.key.."_"
        local qid=fnv("ZatArrowChain.Query."..d.key)
        queries[#queries+1]=qid
        local query_args={prefix.."radius","origin","factions","index",false,"candidate"}
        mark(prefix.."start")
        load("eligible");branch(10,"finish")
        if s.chance_percent<100 then
            call("RandomBranchNode",{prefix.."chance"});branch(10,"finish")
        end
        emit(12);save("jumps")
        mark(prefix.."query")
        emit(12);save("index")
        mark(prefix.."candidate")
        call("ForEachEntityWithFactionInRange",query_args,qid);branch(10,prefix.."close")
        call("IsValidEntity",{"candidate"});branch(10,prefix.."candidate")
        call("IsSameEntity",{"candidate","ForEach::otherEntity"});branch(9,prefix.."candidate")
        call("IsEnemy",{"GetRoot::entityId","candidate"});branch(10,prefix.."candidate")
        call("IsConsecutiveHit",{"candidate"});branch(9,prefix.."candidate")
        donecall("GetConsecutiveHitCount",{"hits_before"})
        -- Native link VFX starts at the previous target's recorded transform.
        -- No despawn link to the arrow: the link must outlive projectile destruction.
        donecall("SpawnEntity",{false,false,"candidate",false,false,false,"origin","visual",
            "true","true","false","false",false})
        donecall("DestroyFactionQuery",query_args,qid)
        -- Capture before damage so a killing hit can still seed the next search.
        donecall("GetTransform",{"candidate","position","origin"})
        call("ApplyDamage",{false,"true",false,false,"false","CanBeBlocked::value",false,
            "material::valueId","WeaponCategory::value","AttackCategory::value","Damage::value",
            "hitReactionType::value","PushBackStrength::value","DamageScaleAttribute::value",false,
            false,"NoiseRange::value","staminaMod::value",prefix.."damage","HitDirection::value",
            "ForEach::normal","position","candidate","GetRoot::entityId","ApplyDamage::wasBlocked"})
        branch(10,"finish")
        load("ApplyDamage::wasBlocked");branch(9,"finish")
        -- Fail closed if the native history does not record this secondary hit.
        call("IsConsecutiveHit",{"candidate"});branch(10,"finish")
        donecall("GetConsecutiveHitCount",{"hits_after"})
        load("hits_before");load("hits_after");emit(5);branch(10,"finish")
        load("jumps");emit(14);save("jumps")
        if s.max_jumps>0 then
            load("jumps");load(prefix.."limit");emit(5);branch(10,"finish")
        end
        -- Same-impact native history is retained. No ClearConsecutiveHits is issued.
        -- Resolve the chain in this hit execution; VFX has its own native lifetime.
        branch(8,prefix.."query")
        mark(prefix.."close");donecall("DestroyFactionQuery",query_args,qid);branch(8,"finish")
        -- Match the native query's shutdown signature and call ID.
        local saved=code;code=shutdown
        donecall("DestroyFactionQuery",query_args,qid)
        code=saved
    end
    mark("finish");emit(8,191)
    for _,f in ipairs(fixups) do
        if not labels[f[2]] then fail("Arrow chain: unresolved branch "..f[2]) end
        code[f[1]]=labels[f[2]]
    end
    shutdown[#shutdown+1]=30
    code[90]=pre -- operand of original BRT at word offset 88
    code[212]=post -- operand of original BR at word offset 210
    return {label="arrow_chain.experimental_program",before=0,after=#active,apply=function()
        p.code=code;p.data=data;p.dataLayout=layout;p.codeShutdown=shutdown;p.queryCallIds=queries
    end}
end
return M
