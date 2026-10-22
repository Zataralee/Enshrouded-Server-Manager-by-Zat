-- Server-owned ignition ledger and timed fire-only damage on the original shot.
-- No new replicated IDs, global buff edits, explosion or terrain operations.
local M={}
local B=require("impact_builder")
local burn="11dc1506-843b-4034-8d54-6a17dfc9682a"
local defs={
    {key="fire_15",guid="2a96b858-8d2d-4564-bc85-93ea79851c0e",id=685713190,template="f1174ce0-7b9f-40c8-a208-2018a58e532c"},
    {key="fire_28",guid="686f82e2-fcf3-47ea-8199-d0157504f9f0",id=225262139,template="12056e78-fbb4-4929-9765-be94c69b91b9"},
    {key="fire_45",guid="232ca542-0832-4607-b827-f7c50de1603e",id=678529367,template="d6dca074-b8df-454b-a973-608740cf86c4"},
}
function M.defaults()
    local result={}
    for _,d in ipairs(defs) do result[d.key]={enabled=false,chance_percent=100,initial_radius=3,
        spread_radius=5,targets_per_spread=3,spread_delay_ms=350,max_jumps=0,
        burn_duration_ms=5000,burn_tick_ms=500,burn_damage_multiplier_per_second=0.2} end
    return result
end
function M.validate(settings,api)
    if settings==nil then settings=M.defaults() end
    api.keys(settings,{fire_15=true,fire_28=true,fire_45=true},"fire_arrows")
    local active={}
    for _,d in ipairs(defs) do
        local s=settings[d.key];local label="fire_arrows."..d.key
        api.keys(s,{enabled=true,chance_percent=true,initial_radius=true,spread_radius=true,
            targets_per_spread=true,spread_delay_ms=true,max_jumps=true,burn_duration_ms=true,
            burn_tick_ms=true,burn_damage_multiplier_per_second=true},label)
        if type(s.enabled)~="boolean" then api.fail(label..".enabled must be true or false") end
        for _,key in ipairs({"chance_percent","initial_radius","spread_radius","burn_damage_multiplier_per_second"}) do
            api.number(s[key],"float32",label.."."..key)
        end
        for _,key in ipairs({"targets_per_spread","spread_delay_ms","max_jumps","burn_duration_ms","burn_tick_ms"}) do
            api.number(s[key],"uint32",label.."."..key)
        end
        if s.chance_percent>100 then api.fail(label..".chance_percent must be between 0 and 100") end
        if s.chance_percent>0 then api.number(s.chance_percent/100,"float32",label.." chance fraction") end
        -- Validate derived coefficients as well. This is storage safety, not a balance cap.
        api.number(s.burn_damage_multiplier_per_second*(s.burn_duration_ms/1000),"float32",label.." total burn multiplier")
        if s.enabled and s.chance_percent>0 and s.burn_duration_ms>0 then
            if api.resource(d.guid,"keen::ItemInfo").itemId.value~=d.id then api.fail(label..": unexpected ammunition ID") end
            active[#active+1]={key=d.key,def=d,config=s}
        end
    end
    return active
end
local fields={"id","remaining","unpaid","spread_left","clock","pending"}
function M.prepare(b,profiles,api)
    if #profiles==0 then return end
    if B.hash(api.resource(burn,"keen::ImpactProgram").data,"B")~=1654930042 then
        api.fail("Fire arrows: conflicting or unsupported native burn constants") end
    local buffs=api.resource("02022e86-8efe-40cb-8f6f-d22071cc3be3","keen::BuffTypeCollectionResource")
    for _,id in ipairs({3212007770,1887941974,2988994531}) do
        local count=0
        for _,buff in ipairs(buffs.buffs) do
            if buff.buffTypeId.value==id then
                count=count+1
                if (buff.impact~=nil and buff.impact~="00000000-0000-0000-0000-000000000000")
                    or buff.applyType~="ResetTime" or not buff.despawnOnDeath or buff.onTimeoutIsSet then
                    api.fail("Fire arrows: native visual-only buff has conflicting behavior ("..tostring(buff.impact)..", "..tostring(buff.applyType)..", "..tostring(buff.despawnOnDeath)..", "..tostring(buff.onTimeoutIsSet)..")") end
            end
        end
        if count~=1 then api.fail("Fire arrows: missing or duplicate native burning visual") end
    end
    for _,name in ipairs({"count","batch","slot","cursor","scan_id","capacity","now","dt","step",
        "jumps","children","radius_mode","write_append","secondary","spread_due","any_work","record_stride","ledger_pointer","visual_refresh"}) do b.uint("fire_"..name,0) end
    -- Immutable dispatch thresholds live outside the shared writable arena.
    for i=0,math.floor(65535/66) do b.add("fire_index_"..i,848563180,string.pack("<I4",i),4) end
    for _,field in ipairs(fields) do b.uint("fire_r_"..field,0) end
    b.alias("fire_target","fire_r_id",1937543046)
    b.alias("fire_initial_value","ForEach::otherEntity",848563180)
    for _,field in ipairs({"duration","tick","delay","fanout","limit"}) do b.uint("fire_"..field,0) end
    for _,field in ipairs({"initial_radius","radius","strength","seconds","scaled_fire","base_fire","query_radius"}) do b.float("fire_"..field,0) end
    b.float("fire_ms_to_seconds",0.001)
    b.native("fire_damage",burn,"DamageSetup::value")
    b.alias("fire_damage_component","fire_damage",3902764048,4,12)
    b.native("fire_soaked",burn,"SoakedDebuff::value")
    b.native("fire_no_push",burn,"PushBack::value")
    b.native("fire_no_reaction",burn,"HitReaction::value")
    -- Refresh client-known visual-only buffs while alive. Their short lease
    -- expires after Soaked/logout without removing another shot's shared VFX.
    b.add("fire_visual_lease",3756319748,string.pack("<I8",500000000),8)
    for _,size in ipairs({"Small","Medium","Large"}) do
        b.native("fire_tag_"..size,burn,"EnemyTag_Size_"..size.."_Tag::value")
        b.native("fire_vfx_"..size,burn,"EnemyTag_Size_"..size.."_BurnVFX::value")
    end
    -- Per-shot configuration selected before entering the shared controller.
    for _,a in ipairs(profiles) do
        local s=a.config;local p=a.key.."_fire_"
        local values={duration=s.burn_duration_ms,tick=s.burn_tick_ms,delay=s.spread_delay_ms,
            fanout=s.targets_per_spread,limit=s.max_jumps,initial_radius=s.initial_radius,radius=s.spread_radius,
            strength=s.burn_damage_multiplier_per_second,chance=s.chance_percent/100}
        for _,key in ipairs({"duration","tick","delay","fanout","limit"}) do b.uint(p..key,values[key]) end
        for _,key in ipairs({"initial_radius","radius","strength","chance"}) do b.float(p..key,values[key]) end
    end
end
function M.emit(b,profiles,api)
    if #profiles==0 then return end
    local function mark(s) b.mark("fire_"..s) end
    local function branch(op,s) b.branch(op,"fire_"..s) end
    local function set(a,c) b.load(a);b.save(c) end
    local function living(entity,reject)
        b.call("IsValidEntity",{entity});branch(10,reject)
        b.call("IsInState",{entity,"dead_state"});branch(9,reject)
        b.call("FetchOptionalAttribute",{entity,"health_attribute","health"});branch(10,reject)
        b.emit(12);b.load("health");b.emit(5);branch(10,reject)
        b.call("IsEnemy",{"GetRoot::entityId",entity});branch(10,reject)
        b.call("HasBuffNode",{entity,"fire_soaked"});branch(9,reject)
    end
    local qid=B.fnv(b.namespace..".FireQuery")
    b.queries[#b.queries+1]=qid
    local qa={"fire_query_radius","origin","factions","index","candidate_transform","candidate"}
    for _,a in ipairs(profiles) do
        b.mark(a.key.."_fire_start")
        b.load("eligible");branch(10,"finish")
        if a.config.chance_percent<100 then b.call("RandomBranchNode",{a.key.."_fire_chance"});branch(10,"finish") end
        for _,field in ipairs({"duration","tick","delay","fanout","limit","initial_radius","radius","strength"}) do
            set(a.key.."_fire_"..field,"fire_"..field)
        end
        branch(8,"start")
    end
    mark("start")
    for _,name in ipairs({"count","jumps","radius_mode","children"}) do b.zero("fire_"..name) end
    -- Damage::value is the projectile's populated damage setup. Keep only fire;
    -- the original AttackMod, DamageScaleAttribute and ranged category are used
    -- by ApplyDamage, so do NOT multiply the three All Fire attributes manually.
    set("Damage.Magical_Fire::value","fire_base_fire")
    b.emit(25);b.save("fire_now")
    set("fire_initial_value","best_value");b.zero("fire_secondary")
    living("best","initial_area")
    branch(8,"ignite")
    mark("initial_area")
    b.zero("fire_radius_mode");set("fire_initial_radius","fire_query_radius")
    b.zero("fire_children");branch(8,"select")
    mark("frame")
    b.emit(28)
    b.call("IsValidEntity",{"GetRoot::entityId"});branch(10,"finish")
    b.emit(25);b.save("fire_now")
    set("fire_count","fire_batch");b.zero("fire_cursor");b.zero("fire_any_work")
    mark("next_record")
    b.equal("fire_cursor","fire_batch");branch(9,"frame_done")
    set("fire_cursor","fire_slot");branch(8,"read_record")
    mark("record_loaded")
    b.zero("fire_spread_due")
    b.load("fire_r_remaining");branch(10,"record_next")
    living("fire_target","extinguish")
    b.emit(13);b.save("fire_visual_refresh");branch(8,"visual")
    mark("record_step")
    b.load("fire_now");b.load("fire_r_clock");b.emit(2);b.save("fire_dt")
    set("fire_now","fire_r_clock")
    set("fire_dt","fire_step")
    b.uless("fire_step","fire_r_remaining");branch(9,"step_ready")
    set("fire_r_remaining","fire_step")
    mark("step_ready")
    b.load("fire_r_remaining");b.load("fire_step");b.emit(2);b.save("fire_r_remaining")
    b.load("fire_r_unpaid");b.load("fire_step");b.emit(1);b.save("fire_r_unpaid")
    b.load("fire_r_remaining");branch(10,"tick")
    b.uless("fire_r_unpaid","fire_tick");branch(9,"spread_clock")
    mark("tick")
    b.load("fire_r_unpaid");branch(10,"spread_clock")
    b.done("MulValues",{"fire_ms_to_seconds","fire_r_unpaid","mul2::op","fire_seconds"})
    b.done("MulValues",{"fire_strength","fire_seconds","mul2::op","fire_scaled_fire"})
    b.done("MulValues",{"fire_base_fire","fire_scaled_fire","mul2::op","fire_damage_component"})
    b.done("GetTransform",{"fire_target","position",false})
    -- Repeated ticks bypass hit-history suppression, cannot crit or push/stagger,
    -- consume no mana/stamina, and never enter the ignition selection path.
    b.done("ApplyDamage",{false,"true",false,false,"false","false",false,
        "material::valueId","WeaponCategory::value","AttackCategory::value","fire_damage",
        "fire_no_reaction","fire_no_push","DamageScaleAttribute::value",false,false,false,false,
        "mul2::result","HitDirection::value","ForEach::normal","position","fire_target","GetRoot::entityId",false})
    b.zero("fire_r_unpaid")
    mark("spread_clock")
    b.load("fire_r_pending");branch(10,"save_record")
    -- Expiry, death and Soaked end a pending branch; the initial killing hit can
    -- still seed the impact radius. Zero delay always waits at least one update.
    b.load("fire_r_remaining");branch(10,"clear_pending")
    b.uless("fire_dt","fire_r_spread_left");branch(9,"delay_pending")
    b.emit(13);b.save("fire_spread_due")
    mark("clear_pending");b.zero("fire_r_pending");branch(8,"save_record")
    mark("delay_pending")
    b.load("fire_r_spread_left");b.load("fire_dt");b.emit(2);b.save("fire_r_spread_left")
    branch(8,"save_record")
    mark("extinguish")
    b.zero("fire_r_remaining");b.zero("fire_r_pending");b.zero("fire_r_unpaid")
    mark("save_record")
    b.load("fire_r_remaining");branch(10,"save_ready")
    b.emit(13);b.save("fire_any_work")
    mark("save_ready")
    b.zero("fire_write_append");branch(8,"write_record")
    mark("record_saved")
    b.load("fire_spread_due");branch(10,"record_next")
    living("fire_target","record_next")
    b.done("GetTransform",{"fire_target",false,"origin"})
    b.emit(13);b.save("fire_radius_mode")
    set("fire_radius","fire_query_radius");b.zero("fire_children")
    branch(8,"select")
    mark("record_next")
    b.inc("fire_cursor");branch(8,"next_record")
    mark("frame_done")
    b.load("fire_any_work");branch(9,"frame")
    b.equal("fire_count","fire_batch");branch(10,"frame")
    branch(8,"finish")

    -- Exhaustively rank the query by distance, independent of faction order.
    mark("select")
    b.equal("fire_count","fire_capacity");branch(9,"selection_done")
    b.load("fire_limit");branch(10,"budget_ok")
    b.equal("fire_jumps","fire_limit");branch(9,"selection_done")
    mark("budget_ok")
    b.load("fire_query_radius");branch(10,"selection_done")
    b.load("fire_radius_mode");branch(10,"fanout_ok")
    b.equal("fire_children","fire_fanout");branch(9,"selection_done")
    mark("fanout_ok")
    b.done("FromTransform",{false,"origin",false,false,false,"origin_position"})
    b.zero("found");b.zero("index")
    mark("candidate")
    b.call("ForEachEntityWithFactionInRange",qa,qid);branch(10,"selected")
    living("candidate","candidate")
    b.call("IsSameEntity",{"candidate","ForEach::otherEntity"});branch(9,"candidate")
    b.zero("fire_scan_id")
    mark("visited")
    b.equal("fire_scan_id","fire_count");branch(9,"distance")
    -- Entity pointers use typed uint32 aliases only; never round IDs via float.
    -- The layout base is filled after emitting the common scheduler.
    b.load("fire_scan_id");b.load("fire_record_stride");b.emit(3)
    b.load("fire_ledger_pointer");b.emit(1);b.save("q_entity")
    b.call("IsSameEntity",{"candidate",{dynamic="q_entity"}});branch(9,"candidate")
    b.inc("fire_scan_id");branch(8,"visited")
    mark("distance")
    b.done("FromTransform",{false,"candidate_transform",false,false,false,"position"})
    for _,axis in ipairs({"x","y","z"}) do b.done("SubValues",{"origin_position_"..axis,"position_"..axis,"sub_op","delta_"..axis}) end
    b.done("GetLength",{"delta","distance"})
    b.load("found");branch(10,"remember")
    b.less("distance","best_distance");branch(9,"remember")
    b.equal("distance","best_distance");branch(10,"candidate")
    b.uless("candidate_value","best_value");branch(10,"candidate")
    mark("remember")
    set("candidate_value","best_value");set("distance","best_distance")
    b.emit(13);b.save("found");branch(8,"candidate")
    mark("selected")
    b.done("DestroyFactionQuery",qa,qid)
    b.load("found");branch(10,"selection_done")
    b.emit(13);b.save("fire_secondary")
    mark("ignite")
    -- No damage at ignition. Each victim receives its own timer and one visit.
    set("fire_count","fire_slot");set("best_value","fire_r_id")
    set("fire_duration","fire_r_remaining");b.zero("fire_r_unpaid")
    set("fire_delay","fire_r_spread_left");set("fire_now","fire_r_clock")
    b.emit(13);b.save("fire_r_pending")
    b.zero("fire_visual_refresh")
    mark("visual")
    for _,size in ipairs({"Small","Medium","Large"}) do
        b.call("HasEntityTag",{"fire_tag_"..size,"fire_target"});branch(10,"visual_"..size)
        b.done("ApplyBuff",{"fire_visual_lease",false,false,"fire_target","fire_vfx_"..size})
        branch(8,"visual_done")
        mark("visual_"..size)
    end
    mark("visual_done")
    b.load("fire_visual_refresh");branch(9,"record_step")
    b.emit(13);b.save("fire_write_append");branch(8,"write_record")
    mark("appended")
    b.inc("fire_count")
    b.load("fire_secondary");branch(10,"initial_area")
    b.inc("fire_jumps");b.inc("fire_children");branch(8,"select")
    mark("selection_done")
    b.load("fire_radius_mode");branch(9,"record_next")
    branch(8,"frame")
    mark("finish")
    b.done("DestroyFactionQuery",qa,qid)
    -- Submit the final partial tick before retiring the projectile controller.
    b.emit(28,8,191)
    local saved=b.code;b.code=b.shutdown;b.done("DestroyFactionQuery",qa,qid);b.code=saved

    -- Two exact scalar dispatches cost 66*N-14 words. The ledger overlays the
    -- shock frontier because a projectile can execute only one ammunition path.
    -- Retain visited IDs after burn expiry: no native damage-history assumption,
    -- no cycling even at zero damage. Capacity is a real bytecode/data limit.
    local capacity=math.min(math.floor(b.capacity*64/24),math.floor((65535-#b.code-6+14)/66))
    if capacity<1 then api.fail("No native Impact instruction storage remains for fire records") end
    b.fire_capacity=capacity
    local function constant(name,value)
        local offset=b.entry(name).offsetInBytes;local bytes=string.pack("<I4",value)
        for i=1,4 do b.data[offset+i]=bytes:byte(i) end
    end
    constant("fire_capacity",capacity);constant("fire_record_stride",7)
    local arena=b.entry("frontier_0").offsetInBytes
    for i=0,capacity-1 do
        b.view("fire_slot_"..i.."_entity",1937543046,4,arena+i*24)
        if i==0 then constant("fire_ledger_pointer",b.vars.fire_slot_0_entity) end
        for j,field in ipairs(fields) do b.view("fire_slot_"..i.."_"..field,848563180,4,arena+i*24+(j-1)*4) end
    end
    local function dispatch(mode,lo,hi)
        if lo==hi then
            for _,field in ipairs(fields) do
                local slot="fire_slot_"..lo.."_"..field;local scratch="fire_r_"..field
                if mode=="read" then set(slot,scratch) else set(scratch,slot) end
            end
            branch(8,mode=="read" and "record_loaded" or "written")
        else
            local mid=math.floor((lo+hi+1)/2);local right=mode.."_"..mid
            b.load("fire_slot");b.load("fire_index_"..mid);b.emit(5);branch(10,right)
            dispatch(mode,lo,mid-1);mark(right);dispatch(mode,mid,hi)
        end
    end
    mark("read_record");dispatch("read",0,capacity-1)
    mark("write_record");dispatch("write",0,capacity-1)
    mark("written")
    b.load("fire_write_append");branch(9,"appended");branch(8,"record_saved")
end
return M
