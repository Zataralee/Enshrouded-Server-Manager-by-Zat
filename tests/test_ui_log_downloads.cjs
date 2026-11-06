const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../enshrouded_manager/static/logs.js'), 'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));

function fixture() {
  const elements = new Map(), requests = [], pending = [];
  const get = id => {
    if (!elements.has(id)) elements.set(id, {value:'', innerHTML:'', textContent:'', disabled:false, events:{},
      classList:{contains:()=>f.visible, toggle(){}}, addEventListener(type, handler){this.events[type]=handler;}});
    return elements.get(id);
  };
  const f = {get, requests, pending, visible:false, instance:'one', allowed:true, admin:false};
  const context = vm.createContext({
    document:{getElementById:get}, selectedInstanceId:()=>f.instance, currentUser:()=>({id:'owner'}),
    isAdmin:()=>f.admin, can:()=>f.allowed,
    escapeHtml:s=>String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
    api:url=>{requests.push(url);return new Promise((resolve,reject)=>pending.push({resolve,reject}));},
  });
  vm.runInContext(source, context);
  f.call = expression => vm.runInContext(expression, context);
  return f;
}

test('routine status refreshes never fetch logs; opening coalesces requests and keeps the list stable', async()=>{
  const f=fixture();for(let n=0;n<10;n++)f.call('logDownloads.contextChanged()');
  assert.equal(f.requests.length,0);
  f.visible=true;f.call('logDownloads.open()');f.call('logDownloads.open()');
  assert.deepEqual(f.requests,['/api/logs?instance_id=one']);
  f.pending.shift().resolve({logs:[{id:'server:full.log',name:'full.log',scope:'Server',size:12000000,modified:'2026-11-06T16:00:00Z'}]});await settle();
  const html=f.get('logList').innerHTML;
  assert.match(html,/\/api\/logs\/download\?log_id=server%3Afull.log&amp;instance_id=one/);
  assert.match(html,/ download /);assert.match(html,/Download/);
  for(let n=0;n<10;n++)f.call('logDownloads.contextChanged()');
  assert.equal(f.requests.length,1);assert.equal(f.get('logList').innerHTML,html);
  f.get('refreshLogs').events.click();assert.equal(f.requests.length,2);
});

test('switching servers clears old download links and rejects an old asynchronous response', async()=>{
  const f=fixture();f.visible=true;f.call('logDownloads.open()');
  f.instance='two';f.call('logDownloads.contextChanged()');
  assert.deepEqual(f.requests,['/api/logs?instance_id=one','/api/logs?instance_id=two']);
  f.pending[0].resolve({logs:[{id:'server:private.log',name:'private.log',scope:'Server',size:1,modified:''}]});await settle();
  assert.doesNotMatch(f.get('logList').innerHTML,/private.log/);
  f.pending[1].resolve({logs:[{id:'server:new.log',name:'new.log',scope:'Server',size:0,modified:''}]});await settle();
  assert.match(f.get('logList').innerHTML,/instance_id=two/);assert.match(f.get('logList').innerHTML,/0 B/);
});

test('filenames are escaped, filtering is local, and a failed refresh can be retried', async()=>{
  const f=fixture();f.call('logDownloads.open()');f.pending.shift().reject(new Error('Network unavailable'));await settle();
  assert.match(f.get('logStatus').textContent,/Refresh to retry/);assert.equal(f.get('refreshLogs').disabled,false);
  f.get('refreshLogs').events.click();f.pending.shift().resolve({logs:[{id:'server:x.log',name:'<img>.log',scope:'Server',size:2,modified:''}]});await settle();
  assert.doesNotMatch(f.get('logList').innerHTML,/<img>/);assert.match(f.get('logList').innerHTML,/&lt;img&gt;/);
  f.get('logSearch').value='missing';f.get('logSearch').events.input();
  assert.match(f.get('logList').innerHTML,/No files match/);assert.equal(f.requests.length,2);
});

test('permission loss clears downloads and prevents new requests', async()=>{
  const f=fixture();f.call('logDownloads.open()');f.allowed=false;f.call('logDownloads.contextChanged()');
  f.pending.shift().resolve({logs:[{id:'server:private.log',name:'private.log',scope:'Server',size:5,modified:''}]});await settle();
  f.call('logDownloads.open()');assert.equal(f.requests.length,1);
  assert.doesNotMatch(f.get('logList').innerHTML,/private.log/);assert.equal(f.get('refreshLogs').disabled,true);
});
