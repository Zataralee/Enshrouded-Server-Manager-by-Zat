-- Reuse the client-known construct incendiary zone, with a guarded server path.
-- Only zones parented to our marked arrows suppress their native burn buffs.
local M={}
local B=require("impact_builder")
M.template="44cb7678-8c69-435a-802e-69adb11375a9"
M.marker="b7ab3989-b293-45f6-b70f-998a2bf248de"
local marker_bytes=string.pack("<I4I2I2",0xb7ab3989,0xb293,0x45f6)..string.char(0xb7,0x0f,0x99,0x8a,0x2b,0xf2,0x48,0xde)
function M.plan(profiles,api)
    local arrows={}
    for _,a in ipairs(profiles) do
        local s=a.config
        if s.ground_fire_enabled and s.ground_fire_duration_ms>0 and s.initial_radius>0 then
            arrows[#arrows+1]=api.resource(a.def.template,"keen::ecs::TemplateResource")
        end
    end
    if #arrows==0 then return function() end end
    local p=api.resource("47746ed5-c7ab-4835-850b-0dc02b1665b7","keen::ImpactProgram")
    local layout={}
    for _,e in ipairs(p.dataLayout) do
        layout[#layout+1]=string.pack("<I4I4I4I4I4",e.name.value,e.configId.value,e.type.value,e.size,e.offsetInBytes)..e.dbgName..string.char(0)
    end
    if #p.code~=85 or B.hash(p.code,"<I4")~=325353938 or B.hash(p.data,"B")~=2201549116
        or #p.codeShutdown~=1 or p.codeShutdown[1]~=30 or #p.queryCallIds~=0
        or B.fnv(table.concat(layout))~=2821029485 or p.stackSize~=256
        or #p.usedStreams~=1 or p.usedStreams[1]~="OnCollision" or p.id.value~=1498937540 then
        api.fail("Ground fire: unsupported or conflicting incendiary zone program")
    end
    local template=api.resource(M.template,"keen::ecs::TemplateResource")
    local components={};local life=0;local visual=false;local impact=false;local config
    for _,c in ipairs(template.components) do
        if c.type=="keen::ecs::LifeTime" then
            life=life+1
            local v=c.value
            if v.lifeTime.value~=9000000000 or v.endOfLife.value~=0 or v.enforceDestroy or v.preventDestroy or v.triggeredDestroy then
                api.fail("Ground fire: conflicting incendiary lifetime") end
        else components[#components+1]=c end
        if c.type=="keen::ecs::VfxComponentResource" then visual=c.value.vfx=="91f01b78-adac-4148-8d08-a5bb08842c40" end
        if c.type=="keen::ecs::Impact" then impact=c.value.program==p.programGuid end
        if c.type=="keen::ecs::ImpactConfiguration" then config=c.value.configValues end
    end
    if life~=1 or not visual or not impact or not config or template.omitTransformReplication then
        api.fail("Ground fire: unsupported incendiary template") end
    local b=B.new(p,api,"ZatIncendiaryGround")
    local life_config=B.fnv("ZatIncendiaryGround.ManagedLifetime")
    b.bool("managed_lifetime",false,life_config);b.bool("started",false)
    b.uint("start",0);b.uint("elapsed",0);b.uint("duration",9000);b.uint("sign_flip",2147483648)
    b.add("parent",1937543046,string.pack("<I4",0),4)
    b.add("marker",3282758806,marker_bytes,4)
    local boot=#b.code
    b.load("started");b.branch(9,"original")
    b.emit(13);b.save("started");b.emit(25);b.save("start")
    b.done("GetParent",{"parent"})
    b.call("IsValidEntity",{"parent"});b.branch(10,"original")
    b.call("HasEntityTag",{"marker","parent"});b.branch(10,"original")
    b.mark("visual_only")
    b.call("IsValidEntity",{"parent"});b.branch(10,"destroy")
    b.emit(28);b.branch(8,"visual_only")
    b.mark("destroy");b.emit(29,30)
    b.mark("original");b.emit(p.code[1],p.code[2],8,2)
    -- Preserve the original grenade's nine-second lifetime, checked each frame.
    -- Other grenade templates retain their existing engine LifeTime components.
    local function wait_hook(resume,label)
        local offset=#b.code
        b.load("managed_lifetime");b.branch(10,label)
        b.emit(25);b.load("start");b.emit(2);b.save("elapsed")
        b.uless("elapsed","duration");b.branch(10,resume==45 and "destroy_wait" or "destroy")
        b.mark(label);b.emit(28,8,resume)
        return offset
    end
    local wait=wait_hook(45,"wait");local cycle=wait_hook(0,"cycle")
    b.mark("destroy_wait");b.emit(27,29,30)
    b.finish();b.code[1]=8;b.code[2]=boot
    b.code[51]=8;b.code[52]=wait;b.code[53]=30
    b.code[55]=8;b.code[56]=cycle;b.code[57]=30
    for _,v in ipairs(config.simple) do
        if v.value.configId.value==life_config then api.fail("Ground fire: conflicting lifetime marker") end
    end
    return function()
        b.apply();template.components=components
        local guid="028fbc12-1421-491b-975e-b321d2923926"
        local values={};for _,v in ipairs(config.simple) do values[#values+1]=v end
        values[#values+1]={type="keen::impact::BoolImpactConfig",value={locaTag=config.simple[1].value.locaTag,
            isSigned=false,valueFormat="Normal",id=guid,configId={value=life_config},type={value=3365180733},
            configGuid=guid,objectId="fa5182de-38bd-4589-8642-9cc27da3b4e2",value=true}}
        config.simple=values
        for _,arrow in ipairs(arrows) do
            local tags;local list={}
            for _,c in ipairs(arrow.components) do
                if c.type=="keen::ecs::EntityTagContainer" then tags=c.value else list[#list+1]=c end
            end
            local entries={};if tags then for _,v in ipairs(tags.tags) do entries[#entries+1]=v end end
            entries[#entries+1]={tag=M.marker}
            list[#list+1]={type="keen::ecs::EntityTagContainer",value={tags=entries}}
            arrow.components=list
        end
    end
end
return M
