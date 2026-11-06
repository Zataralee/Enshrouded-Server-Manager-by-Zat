const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.join(__dirname,'..');
const source=fs.readFileSync(path.join(root,'enshrouded_manager/static/mods.js'),'utf8');

test('EML download stays separate from mutations and follows the selected server',async()=>{
  const elements=new Map(), requests=[];
  let selected='one',refresh;
  const get=id=>{
    if(!elements.has(id))elements.set(id,{events:{},attributes:{},classList:{contains:()=>true,toggle(){},add(){},remove(){}},
      addEventListener(t,h){this.events[t]=h;},setAttribute(k,v){this.attributes[k]=v;},removeAttribute(k){delete this.attributes[k];},
      querySelectorAll:()=>[],replaceChildren(){},value:''});
    return elements.get(id);
  };
  vm.runInNewContext(source,{
    document:{getElementById:get,addEventListener(){}},window:{addEventListener(){}},
    state:{server:{running:true}},isAdmin:()=>true,selectedInstanceId:()=>selected,escapeHtml:s=>s,
    toast(){},confirm:()=>true,setInterval(callback){refresh=callback;},
    api:async url=>{requests.push(url);return {installed:true,enabled:true,log_available:true,version:'0.2.0',mods:[]};}
  });
  await refresh();
  assert.match(get('emlLog').attributes.href,/\/api\/logs\/download\?log_id=server%3Aesm-eml.log&instance_id=one/);
  assert.equal(get('emlLog').attributes['aria-disabled'],'false');
  assert.equal(get('modUploadButton').disabled,true);
  assert.equal(get('emlLog').events.click,undefined);
  selected='two';await refresh();
  assert.match(get('emlLog').attributes.href,/instance_id=two/);
  assert.ok(requests.every(url=>!url.startsWith('/api/mods/log')));
});

test('stable mod page clearly requires EML Lua patch packages and has no inline log viewer',()=>{
  const html=fs.readFileSync(path.join(root,'enshrouded_manager/static/index.html'),'utf8');
  assert.match(html,/Mods \(EML\)/);
  assert.match(html,/EML-compatible mods only/);
  assert.match(html,/EML Lua patch mod ZIP from this computer/);
  assert.match(html,/>Upload EML Mod</);
  assert.match(html,/Download EML Log/);
  assert.doesNotMatch(html,/Mods \(Beta\)|View EML Log/);
});
