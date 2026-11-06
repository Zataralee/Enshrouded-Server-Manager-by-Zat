const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../enshrouded_manager/static/eml-updates.js'),'utf8');
function fixture(){
  const elements=new Map(),requests=[];let refresh,admin=true,active=true;
  const get=id=>{if(!elements.has(id))elements.set(id,{events:{},attributes:{},classList:{contains:()=>active},
    addEventListener(t,h){this.events[t]=h;},setAttribute(k,v){this.attributes[k]=v;}});return elements.get(id);};
  vm.runInNewContext(source,{document:{getElementById:get,addEventListener(){}},window:{addEventListener(){}},
    isAdmin:()=>admin,toast(){},setInterval(f){refresh=f;},
    api:async(url,options)=>{requests.push({url,options});return {installed_version:'0.2.0',latest_version:'0.3.0',
      update_available:true,install_available:true,rollback_available:false,last_checked:1234,bundled:true};}});
  return {get,requests,refresh:()=>refresh(),setAdmin(v){admin=v;},setActive(v){active=v;}};
}
test('visible admin page reads cached status without triggering upstream checks',async()=>{
  const f=fixture();await f.refresh();
  assert.equal(f.requests[0].url,'/api/eml/updates');
  assert.equal(f.get('emlInstallUpdate').disabled,false);
  assert.match(f.get('emlUpdateStatus').textContent,/Installed EML 0.2.0.*0.3.0/);
  f.setActive(false);await f.refresh();f.setActive(true);f.setAdmin(false);await f.refresh();
  assert.equal(f.requests.length,1);
});
test('install sends only selected version and never patches or starts a game',async()=>{
  const f=fixture();await f.refresh();await f.get('emlInstallUpdate').events.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.requests[1].url,'/api/eml/install-update');
  assert.deepEqual(JSON.parse(f.requests[1].options.body),{version:'0.3.0'});
  assert.equal(f.requests.length,2);
});
test('page distinguishes upstream tool updates from game revision compatibility',()=>{
  const html=fs.readFileSync(path.join(__dirname,'../enshrouded_manager/static/index.html'),'utf8');
  assert.match(html,/Mod compatibility is separate/);
  assert.match(html,/Updating EML does not update mod packages/);
  assert.match(html,/Roll Back EML/);
});
