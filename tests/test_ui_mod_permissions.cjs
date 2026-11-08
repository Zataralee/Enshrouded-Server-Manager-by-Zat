const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'enshrouded_manager/static/mods.js'), 'utf8');

function fixture() {
  const elements = new Map(), requests = [];
  let permission = true, logs = false, selected = 'assigned', refresh;
  const state = {server: {running: false}};
  const get = id => {
    if (!elements.has(id)) elements.set(id, {
      events: {}, attributes: {}, value: '',
      classList: {contains: () => true, toggle() {}, add() {}, remove() {}},
      addEventListener(t, h) {this.events[t] = h;},
      setAttribute(k, v) {this.attributes[k] = v;},
      removeAttribute(k) {delete this.attributes[k];},
      querySelectorAll: () => [], replaceChildren() {this.innerHTML = '';},
    });
    return elements.get(id);
  };
  vm.runInNewContext(source, {
    document: {getElementById: get, addEventListener() {}}, window: {addEventListener() {}},
    state, can: p => p === 'mods' ? permission : logs,
    selectedInstanceId: () => selected, escapeHtml: s => s, toast() {}, confirm: () => true,
    setInterval(f) {refresh = f;},
    api: async (url, options) => {
      requests.push({url, options});
      return {installed: true, enabled: true, version: '0.2.0', log_available: true, mods: []};
    },
  });
  return {get, requests, state, refresh: () => refresh(), setPermission(v) {permission = v;},
    setLogs(v) {logs = v;}, setSelected(v) {selected = v;}};
}

test('ordinary user with Mods can manage selected server; revocation stops reads and mutations', async () => {
  const f = fixture();
  await f.refresh();
  assert.equal(f.requests[0].url, '/api/mods?instance_id=assigned');
  assert.equal(f.get('emlToggle').disabled, false);
  await f.get('emlToggle').events.click();
  assert.equal(f.requests[1].url, '/api/mods/loader');
  assert.equal(JSON.parse(f.requests[1].options.body).instance_id, 'assigned');
  f.get('modConfigText').value = 'old private configuration';
  f.setPermission(false);
  await f.refresh();
  const count = f.requests.length;
  await f.get('emlToggle').events.click();
  assert.equal(f.requests.length, count);
  assert.equal(f.get('emlToggle').disabled, true);
  assert.equal(f.get('modConfigText').value, '');
  assert.equal(f.get('modList').innerHTML, '');
});

test('running and changed servers prevent mutations; EML log still requires Logs', async () => {
  const f = fixture();
  await f.refresh();
  assert.equal(f.get('emlLog').attributes['aria-disabled'], 'true');
  f.setLogs(true); f.state.server.running = true;
  await f.refresh();
  assert.equal(f.get('emlToggle').disabled, true);
  assert.match(f.get('emlLog').attributes.href, /instance_id=assigned/);
  f.state.server.running = false; f.setSelected('other');
  await f.get('emlToggle').events.click();
  assert.ok(f.requests.every(r => !r.options));
});

test('account editor persists selectable Mods; tab uses permission while global updater stays admin only', () => {
  const app = fs.readFileSync(path.join(root, 'enshrouded_manager/static/app.js'), 'utf8');
  const html = fs.readFileSync(path.join(root, 'enshrouded_manager/static/index.html'), 'utf8');
  assert.match(html, /data-tab="mods"[^>]*data-permission="mods"/);
  assert.match(html, /id="emlUpdates" data-admin-only="true"/);
  const start = app.indexOf('function renderUsers()');
  const end = app.indexOf('\nfunction ', start + 1);
  const elements = new Map();
  const context = vm.createContext({
    canViewUsers: () => true, isAdmin: () => true, userListDirty: false, escapeHtml: s => String(s || ''),
    state: {instances: [], manager: {users: [{id: 'ordinary', username: 'ordinary', role: 'user', permissions: ['mods']}] }},
    document: {querySelectorAll: () => [], querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, {innerHTML: '', querySelectorAll: () => []});
      return elements.get(selector);
    }},
  });
  vm.runInContext(`${app.match(/const permissions = .*;/)[0]}\n${app.slice(start, end)}\nrenderUsers();`, context);
  assert.match(elements.get('#userList').innerHTML, /data-user-permission="mods" checked/);
  assert.match(app, /permissions: \[\.\.\.row.querySelectorAll\("\[data-user-permission\]:checked"\)/);
});
