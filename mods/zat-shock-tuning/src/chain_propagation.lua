-- Nearest-first breadth-first propagation, shared by arrows and player spells.
-- Native history owns completed hits; the circular queue reserves pending hits.
local M={}
local B=require("impact_builder")
function M.prepare(b,profiles,api)
    local chain="e28f0d79-e2fe-46ba-8d82-9ba368cb30c7"
    for _,name in ipairs({"origin","candidate_transform","best_transform"}) do
        b.native(name,chain,"ImpactTransform::transform")
    end
    b.native("visual",chain,"Template::value")
    b.native("factions",chain,"impact_nodes.FilterFaction::faction")
    for _,name in ipairs({"true","false","eligible","found","last_set","was_blocked","pending_work"}) do b.bool(name,name=="true") end
    for _,name in ipairs({"candidate","best"}) do
        b.add(name,1937543046,string.pack("<I4",0));b.alias(name.."_value",name,848563180)
    end
    for _,name in ipairs({"origin_position","position","delta"}) do
        b.add(name,1025475970,string.rep(string.char(0),12))
        for i,axis in ipairs({"x","y","z"}) do b.alias(name.."_"..axis,name,3902764048,4,(i-1)*4) end
    end
    for _,name in ipairs({"distance","best_distance","last_distance"}) do b.float(name,0) end
    for _,name in ipairs({"index","best_index","jumps","children","last_id","head","tail","queued","wave",
        "scan","scan_left","q_transform","q_entity","capacity"}) do b.uint(name,0) end
    b.add("less_op",1883392102,string.char(1))
    b.add("sub_op",38291025,string.char(1))
    b.uint("sign_flip",2147483648);b.uint("queue_stride",2)
    local required=0
    for _,profile in ipairs(profiles) do
        local s=profile.config;local k=profile.key.."_"
        b.float(k.."radius",s.spread_radius);b.uint(k.."fanout",s.targets_per_spread)
        b.uint(k.."limit",s.max_jumps);b.float(k.."chance",s.chance_percent/100)
        if s.damage then b.float(k.."damage",s.damage) end
        if required~=-1 then
            if s.targets_per_spread<=1 then required=math.max(required,1)
            elseif s.max_jumps==0 then required=-1
            else required=math.max(required,s.max_jumps) end
        end
    end
    -- Each live frontier record needs a 56-byte WorldTransform + 4-byte ID,
    -- padded to the transform's native 8-byte alignment. This is the actual
    -- 16-bit data-offset ceiling, NOT a limit on total victims/generations.
    local start=math.ceil(#b.data/8)*8
    local storage=math.floor((65535-start)/64)
    local capacity=required==-1 and storage or math.min(required,storage)
    if capacity<1 then api.fail("No native Impact storage remains for the chain frontier") end
    local offset=b.entry("capacity").offsetInBytes
    local packed=string.pack("<I4",capacity)
    for i=1,4 do b.data[offset+i]=packed:byte(i) end
    b.queue_base=0xffff0000+#b.layout
    for i=0,capacity-1 do
        b.add("frontier_"..i,2492704965,string.rep(string.char(0),56),8)
        b.add("frontier_id_"..i,1937543046,string.pack("<I4",0),4)
    end
    b.capacity=capacity
end
function M.emit(b,profile,context)
    local p=profile.key.."_";local s=profile.config
    local qid=B.fnv(b.namespace..".Query."..profile.key)
    b.queries[#b.queries+1]=qid
    local qa={p.."radius","origin","factions","index","candidate_transform","candidate"}
    local function branch(op,label) b.branch(op,p..label) end
    local function mark(label) b.mark(p..label) end
    local function qptr(index)
        b.load(index);b.load("queue_stride");b.emit(3,11,b.queue_base,1);b.save("q_transform")
        b.load("q_transform");b.emit(14);b.save("q_entity")
    end
    local function advance(index,label)
        b.inc(index);b.equal(index,"capacity");branch(10,label);b.zero(index);mark(label)
    end
    mark("start")
    b.load("eligible");b.branch(10,"finish")
    if s.chance_percent<100 then b.call("RandomBranchNode",{p.."chance"});b.branch(10,"finish") end
    for _,name in ipairs({"jumps","head","tail","queued","wave"}) do b.zero(name) end
    mark("parent")
    b.zero("children");b.zero("last_set")
    b.done("FromTransform",{false,"origin",false,false,false,"origin_position"})
    mark("select")
    if s.max_jumps>0 then b.equal("jumps",p.."limit");b.branch(9,"finish") end
    b.equal("children",p.."fanout");branch(9,"parent_done")
    b.zero("found");b.zero("index")
    mark("candidate")
    b.call("ForEachEntityWithFactionInRange",qa,qid);branch(10,"selected")
    b.call("IsValidEntity",{"candidate"});branch(10,"candidate")
    b.call("IsSameEntity",{"candidate",context.initial});branch(9,"candidate")
    b.call("IsEnemy",{context.root,"candidate"});branch(10,"candidate")
    b.call("IsConsecutiveHit",{"candidate"});branch(9,"candidate")
    -- Pending siblings/branches are excluded before native history catches up.
    b.load("head");b.save("scan");b.load("queued");b.save("scan_left")
    mark("reservation")
    b.load("scan_left");branch(10,"distance")
    qptr("scan")
    b.call("IsSameEntity",{"candidate",{dynamic="q_entity"}});branch(9,"candidate")
    b.load("scan_left");b.emit(15);b.save("scan_left")
    advance("scan","scan_advanced");branch(8,"reservation")
    mark("distance")
    -- FromTransform.position is WORLD position (referenceTransform does NOT
    -- subtract the origin); calculate all three deltas explicitly.
    b.done("FromTransform",{false,"candidate_transform",false,false,false,"position"})
    for _,axis in ipairs({"x","y","z"}) do
        b.done("SubValues",{"origin_position_"..axis,"position_"..axis,"sub_op","delta_"..axis})
    end
    b.done("GetLength",{"delta","distance"})
    -- Strict rank cursor prevents retrying a rejected/blocked target forever.
    b.load("last_set");branch(10,"rank_best")
    b.less("distance","last_distance");branch(9,"candidate")
    b.equal("distance","last_distance");branch(10,"rank_best")
    b.uless("last_id","candidate_value");branch(10,"candidate")
    mark("rank_best")
    b.load("found");branch(10,"remember")
    b.less("distance","best_distance");branch(9,"remember")
    b.equal("distance","best_distance");branch(10,"candidate")
    b.uless("candidate_value","best_value");branch(10,"candidate")
    mark("remember")
    b.load("candidate_value");b.save("best_value")
    b.load("index");b.emit(15);b.save("best_index")
    b.load("distance");b.save("best_distance")
    b.copy("candidate_transform","best_transform")
    b.emit(13);b.save("found");branch(8,"candidate")
    mark("selected")
    b.done("DestroyFactionQuery",qa,qid)
    b.load("found");branch(10,"parent_done")
    -- Do not write past the native ring buffer when a very wide frontier fills it.
    b.equal("queued","capacity");b.branch(9,"finish")
    b.load("best_distance");b.save("last_distance")
    b.load("best_value");b.save("last_id");b.emit(13);b.save("last_set")
    -- Copy the selected entity ID through the native query output. The generic
    -- AddValues node converts even uint32 through float32 and cannot copy IDs
    -- exactly above 2^24. Re-query the saved index without yielding, then verify
    -- identity before damage; a reordered/disappearing result is skipped.
    qptr("tail");b.load("best_index");b.save("index")
    b.call("ForEachEntityWithFactionInRange",{p.."radius","origin","factions","index",false,{dynamic="q_entity"}},qid)
    branch(10,"recheck_failed")
    b.call("IsSameEntity",{"best",{dynamic="q_entity"}});branch(10,"recheck_failed")
    b.done("DestroyFactionQuery",qa,qid)
    b.done("FromTransform",{false,"best_transform",false,false,false,"position"})
    local args=context.damage_args(p)
    b.call("ApplyDamage",args);branch(10,"select")
    b.load("was_blocked");branch(9,"select")
    b.done("SpawnEntity",{false,false,"best",false,false,false,"origin","visual",
        "true","true","false","false",false})
    if context.after_hit then context.after_hit() end
    qptr("tail")
    b.copy("best_transform",{dynamic="q_transform"})
    advance("tail","tail_advanced")
    b.inc("queued");b.inc("children");b.inc("jumps")
    b.emit(13);b.save("pending_work")
    branch(8,"select")
    mark("recheck_failed");b.done("DestroyFactionQuery",qa,qid);branch(8,"select")
    mark("parent_done")
    b.load("wave");branch(9,"dequeue")
    b.load("queued");b.branch(10,"finish")
    -- All parents in a generation fan out before yielding. One engine update
    -- completes the generation's damage, then its children become spreaders.
    b.emit(28);b.zero("pending_work");b.load("queued");b.save("wave")
    mark("dequeue")
    qptr("head")
    b.call("IsConsecutiveHit",{{dynamic="q_entity"}});b.branch(10,"finish")
    b.copy({dynamic="q_transform"},"origin")
    advance("head","head_advanced")
    b.load("queued");b.emit(15);b.save("queued")
    b.load("wave");b.emit(15);b.save("wave")
    branch(8,"parent")
    local saved=b.code;b.code=b.shutdown;b.done("DestroyFactionQuery",qa,qid);b.code=saved
end
function M.finish(b)
    b.mark("finish")
    -- A finite budget or full frontier may end in the middle of a generation.
    -- Let already submitted damage finish before destroying its source Impact.
    b.load("pending_work");b.branch(10,"finish_ready");b.emit(28)
    b.mark("finish_ready")
end
return M
