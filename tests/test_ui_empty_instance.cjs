const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../enshrouded_manager/static/app.js'), 'utf8');
function extract(start, end) {
  return source.slice(source.indexOf(start), source.indexOf(end));
}
function fixture(selected) {
  const requests = [];
  const storage = new Map([['esm_active_instance_id', 'removed-server']]);
  const elements = new Map();
  const context = vm.createContext({
    requests, storage,
    document: { querySelector: selector => {
      if (!elements.has(selector)) elements.set(selector, { innerHTML: 'old data' });
      return elements.get(selector);
    } },
    localStorage: {
      setItem: (key, value) => storage.set(key, value),
      removeItem: key => storage.delete(key),
    },
    can: () => true,
    api: async url => {
      requests.push(url);
      if (url.startsWith('/api/status')) return { selected_instance: selected };
      return { backups: [], imports: [] };
    },
  });
  for (const name of ['renderStatus', 'renderAccess', 'renderInstances', 'renderNewInstallDefaults',
    'renderInstallJobs', 'renderServerForm', 'renderAccounts', 'renderSchedules', 'renderLogs',
    'renderManagerUpdateStatus', 'renderManagerForm', 'renderBackupSchedule', 'renderWebhookForm',
    'renderUsers', 'renderInvites', 'renderInstructions', 'renderUpdateLog', 'renderDiscoveredSaves']) {
    context[name] = () => {};
  }
  vm.runInContext(`let state = {}; let serverConfig = {}; let activeInstanceId = 'removed-server'; let managerUpdatePoll = false;
    function selectedInstance() { return state.selected_instance || {}; }
    function selectedInstanceId() { return activeInstanceId || selectedInstance().id; }
    ${extract('async function renderBackups()', 'function renderDiscoveredSaves()')}
    ${extract('async function renderSaveImports()', 'function renderManagerForm()')}
    ${extract('async function refresh()', 'function startAutoRefresh()')}`, context);
  return { context, requests, storage, elements };
}

test('empty manager clears stale selection and skips instance-only polling', async () => {
  const f = fixture(null);
  await vm.runInContext('refresh()', f.context);
  assert.deepEqual(f.requests, ['/api/status?instance_id=removed-server']);
  assert.equal(f.storage.has('esm_active_instance_id'), false);
  assert.equal(f.elements.get('#backupList').innerHTML, '');
  assert.equal(f.elements.get('#saveImportHistory').innerHTML, '');
  await vm.runInContext('refresh()', f.context);
  assert.equal(f.requests.at(-1), '/api/status');
});

test('valid status selection replaces stale id before polling its saves and backups', async () => {
  const f = fixture({ id: 'new-server' });
  await vm.runInContext('refresh()', f.context);
  assert.equal(f.storage.get('esm_active_instance_id'), 'new-server');
  assert.deepEqual(f.requests.slice(1), [
    '/api/backups?instance_id=new-server', '/api/savegame/imports?instance_id=new-server',
  ]);
});
