-- Wrap native effect execution, preserving ordinary instances and native visuals.
-- Marked-arrow instances wait without running blast/buff/terraform programs.
local B=require("impact_builder")
local M={}
M.selected_config=B.fnv("ZatFireEffectLab.SelectedTemplate")
M.lifetime_config=B.fnv("ZatFireEffectLab.NativeLifetimeMs")
M.leader_config=B.fnv("ZatFireEffectLab.SpawnCompanions")
function M.guid_bytes(g)
    local a,b,d,e,f=g:match("^(%x+)%-(%x+)%-(%x+)%-(%x+)%-(%x+)$")
    local tail=(e..f):gsub("..",function(h)return string.char(tonumber(h,16))end)
    return string.pack("<I4I2I2",tonumber(a,16),tonumber(b,16),tonumber(d,16))..tail
end
local marker=string.pack("<I4I2I2",0xb7ab3989,0xb293,0x45f6)..string.char(0xb7,0x0f,0x99,0x8a,0x2b,0xf2,0x48,0xde)
function M.plan(p,api,duration,suppress_children,siblings)
    local original=B.array(p.code)
    local b=B.new(p,api,"ZatFireEffectLab")
    for _,e in ipairs(p.dataLayout) do
        if e.dbgName:find("ZatFireEffectLab::",1,true) then api.fail("Effect program already patched") end
    end
    b.code={};b.queries=B.array(p.queryCallIds)
    b.bool("selected",false,M.selected_config)
    b.bool("leader",false,M.leader_config)
    b.add("native_lifetime",848563180,string.pack("<I4",0),4,M.lifetime_config)
    b.uint("duration",duration);b.uint("clock",0);b.uint("elapsed",0);b.uint("sign_flip",2147483648)
    b.add("parent",1937543046,string.pack("<I4",0),4)
    b.add("ancestor",1937543046,string.pack("<I4",0),4)
    b.add("marker",3282758806,marker,4)
    b.emit(25);b.save("clock")
    b.done("GetParent",{"parent"})
    b.call("IsValidEntity",{"parent"});b.branch(10,"original_0")
    b.call("HasEntityTag",{"marker","parent"});b.branch(10,"ancestor_check")
    b.load("selected");b.branch(9,"preview_start")
    if suppress_children then b.branch(8,"destroy") else b.branch(8,"original_0") end
    b.mark("ancestor_check")
    if suppress_children then
        -- Heavy flamethrower actor emits beam children independently of Impact.
        -- Suppress only descendants of our marked preview arrow.
        b.call("GetEntityParent",{"parent","ancestor"});b.emit(27)
        b.call("IsValidEntity",{"ancestor"});b.branch(10,"original_0")
        b.call("HasEntityTag",{"marker","ancestor"});b.branch(9,"destroy")
    end
    b.branch(8,"original_0")
    b.mark("preview_start")
    if siblings and #siblings>0 then
        b.bool("spawn_true",true);b.bool("spawn_false",false)
        b.add("self",1937543046,string.pack("<I4",0),4)
        b.native("spawn_transform","e28f0d79-e2fe-46ba-8d82-9ba368cb30c7","ImpactTransform::transform")
        b.load("leader");b.branch(10,"preview")
        b.done("GetSelf",{"self"})
        b.done("GetTransform",{"self",false,"spawn_transform"})
        for i,guid in ipairs(siblings) do
            b.add("sibling_"..i,709155311,M.guid_bytes(guid),4)
            -- Siblings belong directly to the original arrow, not to the leader.
            -- Each receives the same transform/scale and its own preview timer.
            -- The parent despawn link also cleans up on early arrow cancellation.
            b.done("SpawnEntity",{false,false,false,"parent",false,false,"spawn_transform",
                "sibling_"..i,"spawn_false","spawn_false","spawn_true","spawn_false",false})
        end
    end
    b.mark("preview")
    b.call("IsValidEntity",{"parent"});b.branch(10,"destroy")
    b.emit(25);b.load("clock");b.emit(2);b.save("elapsed")
    b.uless("elapsed","duration");b.branch(10,"destroy")
    b.emit(28);b.branch(8,"preview")
    b.mark("destroy");b.emit(29,30)
    -- Relocate every native branch. RVM/Halt watchdogs replace only the removed
    -- LifeTime on the selected template; other instances take original semantics.
    local pc=0;local waits={}
    while pc<#original do
        b.mark("original_"..pc)
        local op=original[pc+1]
        local width=(op==18 or op==19) and 3 or ((op>=8 and op<=11) or (op>=21 and op<=24)) and 2 or 1
        if pc+width>#original then api.fail("Malformed native bytecode") end
        if op==8 or op==9 or op==10 then b.branch(op,"original_"..original[pc+2])
        elseif op==28 or op==30 then
            b.branch(8,"watch_"..pc);waits[#waits+1]={pc=pc,op=op,next=pc+width}
        else for i=1,width do b.emit(original[pc+i]) end end
        pc=pc+width
    end
    for _,w in ipairs(waits) do
        b.mark("watch_"..w.pc)
        -- Check on resume, before native code can deliver another collision tick.
        if w.op==28 then b.emit(28) end
        b.load("native_lifetime");b.branch(10,"resume_"..w.pc)
        b.emit(25);b.load("clock");b.emit(2);b.save("elapsed")
        b.uless("elapsed","native_lifetime");b.branch(9,"alive_"..w.pc)
        -- A native wait can hold a deadline on the stack. Its terminal path
        -- must not merge with a zero-stack preview/other native wait.
        b.emit(29,30);b.mark("alive_"..w.pc)
        if w.op==30 then b.emit(28);b.branch(8,"watch_"..w.pc) end
        b.mark("resume_"..w.pc)
        if w.op==28 then b.branch(8,"original_"..w.next) else b.emit(30) end
    end
    b.finish();b.shutdown=B.array(p.codeShutdown)
    return b.apply
end
function M.config(kind,id,value,guid)
    return {type="keen::impact::"..kind.."ImpactConfig",value={locaTag="00000000-0000-0000-0000-000000000000",isSigned=false,valueFormat="Normal",
        id=guid,configId={value=id},type={value=kind=="Bool" and 3365180733 or 848563180},
        configGuid=guid,objectId=guid,value=value}}
end
return M
