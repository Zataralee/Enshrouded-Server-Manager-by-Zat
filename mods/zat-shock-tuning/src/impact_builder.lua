-- Author-written assembler for existing Impact resources; no game code bundled.
local M = {}
function M.fnv(s)
    local h=2166136261
    for i=1,#s do h=((h ~ s:byte(i))*16777619)&0xffffffff end
    return h
end
function M.array(a) local b={};for _,v in ipairs(a) do b[#b+1]=v end;return b end
function M.hash(a,format)
    local chunks={};for _,v in ipairs(a) do chunks[#chunks+1]=string.pack(format,v) end
    return M.fnv(table.concat(chunks))
end
function M.new(p,api,namespace)
    local b={code=M.array(p.code),data=M.array(p.data),layout={},vars={},queries={},
        shutdown={},labels={},fixups={},serial=0,namespace=namespace}
    local fail=api.fail
    for i,e in ipairs(p.dataLayout) do
        b.layout[i]={name={value=e.name.value},configId={value=e.configId.value},type={value=e.type.value},
            size=e.size,offsetInBytes=e.offsetInBytes,dbgName=e.dbgName}
        b.vars[e.dbgName]=0xffff0000+i-1
    end
    function b.entry(name) return b.layout[(b.vars[name]&0xffff)+1] end
    function b.view(name,typ,size,offset,config)
        if #b.layout>=65535 or offset+size>65535 then fail("Chain exceeds native Impact layout") end
        local dbg=namespace.."::"..name
        b.vars[name]=0xffff0000+#b.layout
        b.layout[#b.layout+1]={name={value=M.fnv(dbg)},configId={value=config or 0},type={value=typ},
            size=size,offsetInBytes=offset,dbgName=dbg}
        return name
    end
    function b.add(name,typ,bytes,alignment,config)
        alignment=alignment or math.max(#bytes,16)
        while #b.data%alignment~=0 do b.data[#b.data+1]=0 end
        b.view(name,typ,#bytes,#b.data,config)
        for i=1,#bytes do b.data[#b.data+1]=bytes:byte(i) end
        return name
    end
    function b.uint(name,v) return b.add(name,848563180,string.pack("<I4",v)) end
    function b.float(name,v) return b.add(name,3902764048,string.pack("<f",v)) end
    function b.bool(name,v,config) return b.add(name,3365180733,string.char(v and 1 or 0),nil,config) end
    function b.alias(name,source,typ,size,offset)
        local e=b.entry(source)
        return b.view(name,typ,size or e.size,e.offsetInBytes+(offset or 0))
    end
    function b.native(name,guid,entry)
        local source=api.resource(guid,"keen::ImpactProgram");local found
        for _,e in ipairs(source.dataLayout) do if e.dbgName==entry then
            if found then fail("Duplicate native chain constant "..entry) end
            found=e
        end end
        if not found then fail("Missing native chain constant "..entry) end
        local bytes={};for i=1,found.size do bytes[i]=string.char(source.data[found.offsetInBytes+i]) end
        return b.add(name,found.type.value,table.concat(bytes))
    end
    function b.emit(...) for _,v in ipairs({...}) do b.code[#b.code+1]=v end end
    function b.mark(name) b.labels[name]=#b.code end
    function b.branch(op,name) b.emit(op,0);b.fixups[#b.fixups+1]={#b.code,name} end
    function b.load(name) b.emit(22,(assert(b.vars[name],name))) end
    function b.save(name) b.emit(24,(assert(b.vars[name],name))) end
    function b.ptr(name)
        if name==false then b.emit(12)
        elseif type(name)=="table" then b.load(name.dynamic)
        else b.emit(11,(assert(b.vars[name],name))) end
    end
    function b.call(name,args,id)
        for _,a in ipairs(args) do b.ptr(a) end
        b.serial=b.serial+1
        b.emit(19,id or M.fnv(namespace..".Call."..b.serial),M.fnv(name))
    end
    function b.done(name,args,id) b.call(name,args,id);b.emit(27) end
    function b.copy(source,target) b.done("ApplyOffset",{false,false,false,source,target}) end
    function b.less(a,c) b.call("IsLess",{c,a,"less_op"}) end
    function b.uless(a,c)
        -- ILT is signed. Flip the sign bit through wrapping IAdd to compare
        -- the full uint32 range without float conversion/rounding.
        b.load(a);b.load("sign_flip");b.emit(1);b.load(c);b.load("sign_flip");b.emit(1,5)
    end
    function b.equal(a,c) b.load(a);b.load(c);b.emit(6) end
    function b.zero(name) b.emit(12);b.save(name) end
    function b.inc(name) b.load(name);b.emit(14);b.save(name) end
    function b.finish()
        for _,f in ipairs(b.fixups) do b.code[f[1]]=assert(b.labels[f[2]],f[2]) end
        if #b.code>65535 or #b.shutdown>65535 then fail("Chain exceeds native 16-bit instruction addresses") end
        b.shutdown[#b.shutdown+1]=30
    end
    function b.apply()
        p.code=b.code;p.data=b.data;p.dataLayout=b.layout;p.codeShutdown=b.shutdown;p.queryCallIds=b.queries
    end
    return b
end
return M
