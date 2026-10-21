const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../enshrouded_manager/static/mods.js'), 'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));

function fixture() {
  const elements = new Map(), requests = [], notices = [];
  const get = id => {
    if (!elements.has(id)) elements.set(id, {
      value: '', disabled: false, events: {},
      classList: {contains: () => true, add() {}, remove() {}},
      querySelectorAll: () => [], replaceChildren() {},
      addEventListener(type, callback) { this.events[type] = callback; },
    });
    return elements.get(id);
  };
  const f = {get, requests, failRead: false, selected: 'server-a'};
  const context = vm.createContext({
    state: {server: {running: false}}, isAdmin: () => true,
    selectedInstanceId: () => f.selected, escapeHtml: x => x,
    toast: text => notices.push(text), confirm: () => true,
    document: {getElementById: get, addEventListener() {}}, window: {addEventListener() {}},
    setInterval(callback) { f.refresh = callback; },
    api: async (url, options) => {
      requests.push({url, options});
      if (options) return {};
      if (url.startsWith('/api/mods/config')) {
        if (url.includes('&file=')) {
          if (f.failRead) throw new Error('Configuration could not be loaded');
          return {content: 'return { radius = 7 }'};
        }
        // Explicit recommendation must win even if a server returns an unsorted list.
        return {files: ['LICENSE.txt', 'src/config.defaults.lua', 'src/config.lua'], default_file: 'src/config.lua'};
      }
      return {enabled: true, installed: true, version: '0.2.0', mods: []};
    },
  });
  vm.runInContext(source, context);
  f.configure = async () => {
    await f.refresh();
    get('modList').events.click({target: {closest: () => ({dataset: {emlMod: 'shock', emlAction: 'configure'}})}});
    await settle();
  };
  return f;
}

test('Configure opens live settings and Save sends their contents to the selected server', async () => {
  const f = fixture(); await f.configure();
  assert.equal(f.get('modConfigFile').value, 'src/config.lua');
  assert.equal(f.get('modConfigText').value, 'return { radius = 7 }');
  assert.equal(f.get('modConfigSave').disabled, false);
  f.get('modConfigText').value = 'return { radius = 10 }';
  f.get('modConfigText').events.input();
  await f.get('modConfigSave').events.click();
  const saved = f.requests.find(r => r.options);
  assert.equal(saved.url, '/api/mods/config');
  assert.deepEqual(JSON.parse(saved.options.body), {instance_id: 'server-a', mod_id: 'shock', file: 'src/config.lua', content: 'return { radius = 10 }'});
});

test('failed file load clears stale contents and disables Save', async () => {
  const f = fixture(); await f.configure(); f.failRead = true;
  f.get('modConfigFile').value = 'LICENSE.txt';
  f.get('modConfigFile').events.change(); await settle();
  assert.equal(f.get('modConfigText').value, '');
  assert.equal(f.get('modConfigSave').disabled, true);
  assert.equal(f.get('modConfigText').readOnly, true);
});

test('changing server cannot save the old editor into the newly selected server', async () => {
  const f = fixture(); await f.configure(); f.selected = 'server-b';
  await f.get('modConfigSave').events.click();
  assert.equal(f.requests.filter(r => r.options).length, 0);
});
