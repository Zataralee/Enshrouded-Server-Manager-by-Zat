const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../enshrouded_manager/static/app.js'), 'utf8');
function fixture(checked) {
  const elements = new Map();
  const checkbox = { checked };
  const requests = [];
  const context = vm.createContext({
    checkbox, requests,
    state: {manager: {manager_updates: {channel: 'stable', release_state: 'available', package_available: true}}},
    managerFormDirty: true, managerUpdatePoll: false, activeUpdatePhases: [], isAdmin: () => true,
    toast: () => {},
    document: {
      querySelector(selector) {
        if (selector === '#managerForm') return {manager_updates_beta: checkbox};
        if (!elements.has(selector)) elements.set(selector, {classList: {toggle() {}, add() {}, remove() {}}});
        return elements.get(selector);
      }, querySelectorAll: () => [],
    },
    api: async (url, options) => {
      requests.push({url, body: JSON.parse(options.body)});
      return {manager_updates: {channel: checked ? 'beta' : 'stable', release_state:'available', package_available:true}};
    },
  });
  vm.runInContext(source.slice(source.indexOf('let managerUpdateCheckPending'), source.indexOf('async function reconnectManagerUpdate')), context);
  return {context, checkbox, requests, elements};
}
test('checkbox is sent by Check for Updates without saving other settings', async () => {
  const f = fixture(true);
  vm.runInContext('renderManagerUpdateStatus()', f.context);
  assert.equal(f.elements.get('#installManagerUpdateButton').disabled, true);
  await vm.runInContext('checkSelectedManagerUpdate()', f.context);
  assert.equal(f.requests.length, 1);
  assert.deepEqual(f.requests[0], {url:'/api/manager/check-update', body:{channel:'beta'}});
  assert.equal(f.elements.get('#installManagerUpdateButton').disabled, false);
  f.checkbox.checked = false;
  vm.runInContext('renderManagerUpdateStatus()', f.context);
  assert.equal(f.elements.get('#installManagerUpdateButton').disabled, true);
  assert.equal(f.elements.get('#bannerInstallManagerUpdateButton').disabled, true);
});
test('unchecking beta selects stable directly', async () => {
  const f = fixture(false);
  await vm.runInContext('checkSelectedManagerUpdate()', f.context);
  assert.equal(f.requests[0].body.channel, 'stable');
});
test('late checkbox check response cannot enable installation for another selection', async () => {
  const f = fixture(true);
  f.context.api = async () => {
    f.checkbox.checked = false;
    return {manager_updates:{channel:'beta',release_state:'available',package_available:true}};
  };
  await vm.runInContext('checkSelectedManagerUpdate()', f.context);
  assert.equal(f.context.state.manager.manager_updates.channel,'stable');
  assert.equal(f.elements.get('#installManagerUpdateButton').disabled,true);
});
