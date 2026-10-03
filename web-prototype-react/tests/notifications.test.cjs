// Shared contract/interaction regressions run against both client implementations.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const webRoot = path.resolve(__dirname, '..');
const roots = [webRoot, path.resolve(webRoot, '../mobile')];
const plain = value => JSON.parse(JSON.stringify(value));
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

function load(root, file, mocks = {}, globals = {}) {
  const module = { exports: {} };
  const code = ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText;
  vm.runInNewContext(code, { module, exports: module.exports, AbortController, Date, Set,
    require(name) { assert.ok(name in mocks, `Unmocked module ${name}`); return mocks[name]; }, ...globals });
  return module.exports;
}

function descendants(tree) {
  const nodes = [];
  const visit = node => { if (Array.isArray(node)) return node.forEach(visit); if (!node || typeof node !== 'object') return; nodes.push(node); node.children?.forEach(visit); };
  visit(tree); return nodes;
}

function hookHarness() {
  const slots = []; let cursor = 0, effects = [], render, value, dirty;
  const same = (a, b) => a && b && a.length === b.length && a.every((v, i) => Object.is(v, b[i]));
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial;
      return [slots[i], next => { const resolved = typeof next === 'function' ? next(slots[i]) : next; if (!Object.is(resolved, slots[i])) { slots[i] = resolved; dirty = true; } }]; },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useMemo(fn, deps) { const i = cursor++; if (!same(slots[i]?.deps, deps)) slots[i] = { deps, value: fn() }; return slots[i].value; },
    useCallback(fn, deps) { return react.useMemo(() => fn, deps); },
    useEffect(fn, deps) { const i = cursor++; if (!same(slots[i]?.deps, deps)) { const previous = slots[i]; slots[i] = { deps }; effects.push(() => { previous?.cleanup?.(); slots[i].cleanup = fn(); }); } },
  };
  return { react, mount(fn) { render = fn; this.render(); },
    render() { dirty = false; cursor = 0; value = render(); const pending = effects; effects = []; pending.forEach(fn => fn()); },
    async settle() { for (let i = 0; i < 20; i++) { await new Promise(resolve => setImmediate(resolve)); if (dirty) this.render(); } assert.equal(dirty, false); },
    unmount() { for (const slot of slots) slot?.cleanup?.(); }, get value() { return value; },
  };
}

function mountCenter(root, settings = false, overrides = {}) {
  const h = hookHarness(); let account = 'a', stopped = 0, foreground, changed;
  let prefs = { enabled: true, analysis_enabled: true, simulation_enabled: true };
  let feed = { items: [{ id: 'n', kind: 'analysis', portfolio_id: 'p', resource_id: 'exact-report', read_at: null }], total: 26, unread_count: 1 };
  const calls = [];
  const api = {
    list: async offset => { calls.push(['list', offset]); return feed; },
    preferences: async () => prefs,
    savePreferences: async body => { calls.push(['save', plain(body)]); prefs = body; return body; },
    markRead: async id => { calls.push(['read', id]); feed = { ...feed, unread_count: 0, items: feed.items.map(item => ({ ...item, read_at: 'now' })) }; },
    markAllRead: async () => { calls.push(['all']); feed = { ...feed, unread_count: 0 }; },
    clear: async id => { calls.push(['clear', id]); feed = { ...feed, items: feed.items.filter(item => item.id !== id), total: feed.total - 1, unread_count: 0 }; },
    clearAll: async () => { calls.push(['clear-all']); feed = { items: [], total: 0, unread_count: 0 }; },
    ...overrides,
  };
  const hooks = load(root, 'src/notifications/useNotifications.ts', {
    react: h.react, '../auth/useAuth': { useAuth: () => ({ status: account ? 'authenticated' : 'unauthenticated', user: account ? { id: account } : null }) },
    '../api/notificationsApi': { notificationsApi: api, notificationsChanged: () => calls.push(['changed']), subscribeNotifications: listener => { changed = listener; return () => stopped++; } },
    './notificationForeground': { watchNotificationForeground: listener => { foreground = listener; return () => stopped++; } },
  });
  h.mount(() => hooks.useNotificationCenter(settings));
  return { h, api, hooks, calls, setAccount(value) { account = value; h.render(); }, setFeed(value) { feed = value; }, get foreground() { return foreground; }, get changed() { return changed; }, get stopped() { return stopped; } };
}

for (const root of roots) {
  const client = path.basename(root);
  test(`${client}: notification transport uses authenticated shared APIs and empty mutation responses`, async () => {
    const calls = [];
    const { notificationsApi: api } = load(root, 'src/api/notificationsApi.ts', { './apiClient': { apiRequest: async (...args) => { calls.push(args); return {}; } } });
    await api.list(25, 25, { token: 'test-token' });
    await api.preferences(); await api.savePreferences({ enabled: false, analysis_enabled: true, simulation_enabled: true });
    await api.markRead('n/id'); await api.markAllRead();
    await api.clear('n/id'); await api.clearAll();
    assert.equal(calls[0][0], '/api/notifications?limit=25&offset=25'); assert.equal(calls[0][1].token, 'test-token');
    assert.equal(calls[2][1].method, 'PUT'); assert.equal(calls[3][0], '/api/notifications/n%2Fid/read');
    assert.equal(calls[4][1].method, 'POST');
    assert.equal(calls[5][0], '/api/notifications/n%2Fid'); assert.equal(calls[5][1].method, 'DELETE');
    assert.equal(calls[6][0], '/api/notifications'); assert.equal(calls[6][1].method, 'DELETE');
    if (client === 'mobile') assert.equal(calls[5][1].responseMode, 'none');
    if (client === 'mobile') assert.equal(calls[3][1].responseMode, 'none');
    assert.ok(calls.every(([url]) => url.startsWith('/api/notifications')));
  });

  test(`${client}: inbox paginates, marks read/all, then opens exact results without creating events`, async () => {
    const c = mountCenter(root); await c.h.settle();
    assert.equal(c.h.value.feed.unread_count, 1);
    let navigated = false;
    await c.h.value.open(c.h.value.feed.items[0], () => { navigated = true; }); await c.h.settle();
    assert.equal(navigated, true); assert.deepEqual(c.calls.find(call => call[0] === 'read'), ['read', 'n']);
    assert.equal(c.h.value.feed.unread_count, 0);
    c.h.value.next(); await c.h.settle(); assert.equal(c.h.value.offset, 25);
    c.h.value.previous(); await c.h.settle(); assert.equal(c.h.value.offset, 0);
    await c.h.value.markAll(); await c.h.settle(); assert.ok(c.calls.some(call => call[0] === 'all'));
    c.h.unmount();
  });

  test(`${client}: preference saves are server-owned and duplicate taps are guarded`, async () => {
    const delayed = deferred(); let saves = 0;
    const c = mountCenter(root, true, { savePreferences: async body => { saves++; await delayed.promise; return body; } });
    await c.h.settle(); const action = c.h.value.toggle;
    const pending = action('enabled', false); await action('enabled', false); await c.h.settle();
    assert.equal(saves, 1); assert.equal(c.h.value.busy, true); assert.equal(c.h.value.prefs.enabled, true);
    c.api.preferences = async () => ({ enabled: false, analysis_enabled: true, simulation_enabled: true });
    delayed.resolve(); await pending; await c.h.settle(); assert.equal(c.h.value.prefs.enabled, false);
    assert.match(c.h.value.notice, /saved to your account/); c.h.unmount();
  });

  test(`${client}: clearing requires confirmation, cancel revokes authorization and success updates counts`, async () => {
    const c = mountCenter(root); await c.h.settle();
    const item = c.h.value.feed.items[0];
    await c.h.value.confirmClear();
    c.h.value.requestClear(item); await c.h.settle();
    assert.equal(c.h.value.clearTarget.id, item.id);
    const staleConfirm = c.h.value.confirmClear;
    c.h.value.cancelClear(); await c.h.settle(); await staleConfirm();
    assert.equal(c.h.value.clearTarget, null);
    assert.equal(c.calls.filter(call => call[0] === 'clear').length, 0);
    c.h.value.requestClear(item); await c.h.settle();
    await c.h.value.confirmClear(); await c.h.settle();
    assert.deepEqual(c.calls.find(call => call[0] === 'clear'), ['clear', item.id]);
    assert.equal(c.h.value.clearTarget, null); assert.equal(c.h.value.feed.unread_count, 0);
    assert.match(c.h.value.notice, /saved result is unchanged/);
    assert.ok(c.calls.some(call => call[0] === 'changed')); c.h.unmount();
  });

  test(`${client}: clear retries failures, guards duplicate confirms and treats already-cleared 404 as success`, async () => {
    const c = mountCenter(root, false, { clear: async () => { throw Error('offline'); } }); await c.h.settle();
    c.h.value.requestClear(c.h.value.feed.items[0]); await c.h.settle();
    await c.h.value.confirmClear(); await c.h.settle();
    assert.ok(c.h.value.clearTarget); assert.match(c.h.value.error, /could not be confirmed/);
    const pending = deferred(); let calls = 0;
    c.api.clear = async () => { calls++; await pending.promise; throw { status: 404 }; };
    const confirm = c.h.value.confirmClear, mutation = confirm(); await confirm(); await c.h.settle();
    assert.equal(calls, 1); assert.equal(c.h.value.busy, true);
    c.h.value.cancelClear(); await c.h.settle(); assert.ok(c.h.value.clearTarget);
    c.setFeed({ items: [], total: 0, unread_count: 0 }); pending.resolve(); await mutation; await c.h.settle();
    assert.equal(c.h.value.clearTarget, null); assert.equal(c.h.value.feed.total, 0);
    assert.equal(c.h.value.error, null); c.h.unmount();
  });

  test(`${client}: clear all removes every page and safely returns an empty late page to page one`, async () => {
    const c = mountCenter(root); await c.h.settle(); c.h.value.next(); await c.h.settle();
    assert.equal(c.h.value.offset, 25);
    c.h.value.requestClear('all'); await c.h.settle(); await c.h.value.confirmClear(); await c.h.settle();
    assert.equal(c.h.value.feed.total, 0); assert.equal(c.h.value.feed.unread_count, 0);
    assert.equal(c.h.value.offset, 0); assert.equal(c.h.value.clearTarget, null);
    assert.equal(c.calls.filter(call => call[0] === 'clear-all').length, 1);
    assert.match(c.h.value.notice, /All notifications cleared/); c.h.unmount();
  });

  test(`${client}: account changes revoke clear confirmation and unmount blocks subsequent actions`, async () => {
    const c = mountCenter(root); await c.h.settle();
    c.h.value.requestClear('all'); await c.h.settle(); const staleConfirm = c.h.value.confirmClear;
    c.setAccount('b'); await c.h.settle(); await staleConfirm(); await c.h.value.confirmClear();
    assert.equal(c.h.value.clearTarget, null); assert.equal(c.calls.filter(call => call[0] === 'clear-all').length, 0);
    c.h.value.requestClear('all'); await c.h.settle(); const confirm = c.h.value.confirmClear;
    c.h.unmount(); await confirm(); assert.equal(c.calls.filter(call => call[0] === 'clear-all').length, 0);
  });

  test(`${client}: failed mutations remain retryable and never navigate or falsely mark read`, async () => {
    const c = mountCenter(root, false, { markRead: async () => { throw Error('offline'); } }); await c.h.settle();
    let navigations = 0;
    await c.h.value.open(c.h.value.feed.items[0], () => navigations++); await c.h.settle();
    assert.equal(navigations, 0); assert.equal(c.h.value.feed.unread_count, 1); assert.match(c.h.value.error, /could not be confirmed/);
    c.api.markRead = async () => {};
    await c.h.value.open(c.h.value.feed.items[0], () => navigations++); await c.h.settle(); assert.equal(navigations, 1); c.h.unmount();
  });

  test(`${client}: late account responses and unmounted mutations cannot reveal or navigate old context`, async () => {
    const delayed = deferred(), c = mountCenter(root, false, { list: () => delayed.promise });
    c.setAccount('b'); c.api.list = async () => ({ items: [], total: 0, unread_count: 0 });
    await c.h.value.refresh(); await c.h.settle();
    delayed.resolve({ items: [{ id: 'private-account-a' }], total: 1, unread_count: 1 }); await c.h.settle();
    assert.equal(c.h.value.feed.items.length, 0);
    const pendingRead = deferred(); c.api.markRead = () => pendingRead.promise;
    let navigations = 0;
    const pending = c.h.value.open({ id: 'n', read_at: null }, () => navigations++);
    c.h.unmount(); pendingRead.resolve(); await pending; assert.equal(navigations, 0);
  });

  test(`${client}: badge preserves unknown on error and coalesces changes during an in-flight refresh`, async () => {
    const c = mountCenter(root); await c.h.settle(); c.h.unmount();
    const h = hookHarness(); let currentUser = 'a', refresh, changed, stops = 0, calls = 0;
    const first = deferred();
    const hook = load(root, 'src/notifications/useNotifications.ts', {
      react: h.react, '../auth/useAuth': { useAuth: () => ({ status: 'authenticated', user: { id: currentUser } }) },
      '../api/notificationsApi': { notificationsApi: { list: async () => { calls++; return calls === 1 ? first.promise : { unread_count: 0 }; } }, subscribeNotifications: fn => { changed = fn; return () => stops++; } },
      './notificationForeground': { watchNotificationForeground: fn => { refresh = fn; return () => stops++; } },
    });
    h.mount(() => hook.useNotificationBadge()); changed(); first.resolve({ unread_count: 9 }); await h.settle();
    assert.equal(h.value, 0); assert.equal(calls, 2);
    currentUser = 'b'; h.render(); assert.equal(h.value, null); await h.settle();
    refresh(); await h.settle(); h.unmount(); assert.equal(stops, 4);
  });
}

test('web notification page renders theme switches, exact result links, empty/error states and pagination', () => {
  const h = hookHarness(), paths = [], opened = []; let confirms = 0;
  const center = { loading: false, busy: false, offset: 0, error: null, notice: null, refresh: () => {}, next: () => {}, previous: () => {}, markAll: () => {}, markRead: () => {}, open: (item, navigate) => { opened.push(item.resource_id); navigate(); },
    clearTarget: null, requestClear: target => { center.clearTarget = target; }, cancelClear: () => { center.clearTarget = null; }, confirmClear: () => { confirms++; },
    feed: { unread_count: 1, total: 1, items: [{ id: 'n', kind: 'simulation', title: 'Simulation saved', message: 'Ready', portfolio_id: 'p', resource_id: 'exact-simulation', created_at: '2026-10-03T12:00:00Z', read_at: null }] } };
  const { NotificationsPage } = load(webRoot, 'src/pages/notifications/NotificationsPage.tsx', {
    react: h.react, '../../app/routes': { go: route => paths.push(route) }, '../../components/ui/Card': { Card: 'Card' }, '../../components/ui/Icon': { Icon: 'Icon' },
    '../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
    '../../notifications/useNotifications': { useNotificationCenter: () => center, notificationPreferenceRows: [] },
    '../../notifications/notificationForeground': { watchNotificationForeground: () => () => {} }, './NotificationsPage.module.css': {},
  }, { React: h.react, window: { scrollTo() {} } });
  const nodes = [];
  const visit = node => { if (Array.isArray(node)) return node.forEach(visit); if (!node || typeof node !== 'object') return; nodes.push(node); node.children?.forEach(visit); };
  h.mount(() => NotificationsPage({})); visit(h.value);
  nodes.find(node => node.type === 'button' && node.children.join('').startsWith('View simulation')).props.onClick();
  assert.deepEqual(paths, ['simulations/p/exact-simulation']); assert.deepEqual(opened, ['exact-simulation']);
  assert.ok(nodes.some(node => node.type === 'time')); assert.ok(nodes.some(node => node.children?.join('') === 'Mark all as read'));
  nodes.find(node => node.type === 'button' && node.children.join('') === 'Clear notification').props.onClick(); h.render();
  let dialog = descendants(h.value).find(node => node.type === 'Dialog');
  assert.equal(dialog.props.tone, 'danger'); assert.equal(dialog.props.subject, 'Simulation saved');
  assert.match(dialog.props.description, /reports, simulations, and notification preferences stay unchanged/);
  assert.equal(confirms, 0); dialog.props.onCancel(); h.render(); assert.ok(!descendants(h.value).some(node => node.type === 'Dialog'));
  descendants(h.value).find(node => node.type === 'button' && node.children.join('') === 'Clear all notifications').props.onClick(); h.render();
  dialog = descendants(h.value).find(node => node.type === 'Dialog'); assert.match(dialog.props.subject, /including other pages/);
  dialog.props.onConfirm(); assert.equal(confirms, 1);
  center.feed = { items: [], total: 0, unread_count: 0 }; center.clearTarget = null; h.render();
  assert.equal(descendants(h.value).find(node => node.type === 'button' && node.children.join('') === 'Clear all notifications').props.disabled, true);
});

test('mobile notification screen opens exact report/simulation and disables category switches under master Off', () => {
  const root = roots[1], h = hookHarness(), routes = [], updates = []; let confirms = 0;
  const rows = [{ key: 'enabled', title: 'In-app notifications', description: 'Inside Aura' }, { key: 'analysis_enabled', title: 'Analysis reports', description: 'Saved reports' }, { key: 'simulation_enabled', title: 'Saved simulations', description: 'Saved simulations' }];
  const center = { loading: false, busy: false, offset: 0, error: null, notice: null, refresh: () => {}, next() {}, previous() {}, markAll() {}, markRead() {}, toggle: (...args) => updates.push(args), open: (_, navigate) => navigate(),
    clearTarget: null, requestClear: target => { center.clearTarget = target; }, cancelClear: () => { center.clearTarget = null; }, confirmClear: () => { confirms++; },
    prefs: { enabled: false, analysis_enabled: true, simulation_enabled: true },
    feed: { unread_count: 2, total: 2, items: ['analysis', 'simulation'].map(kind => ({ id: kind, kind, title: `${kind} saved`, message: 'Ready', portfolio_id: 'p', resource_id: `exact-${kind}`, created_at: '2026-10-03T12:00:00Z', read_at: null })) } };
  const { NotificationsScreen } = load(root, 'src/screens/notifications/NotificationsScreen.tsx', {
    react: h.react,
    'react-native': { Pressable: 'Pressable', RefreshControl: 'Refresh', ScrollView: 'Scroll', Switch: 'Switch', Text: 'Text', View: 'View', StyleSheet: { create: value => value } },
    'react-native-safe-area-context': { SafeAreaView: 'Safe' }, '@expo/vector-icons': { Ionicons: 'Icon' },
    '@react-navigation/native': { useFocusEffect: () => {} },
    '../../components/ui/Card': { Card: 'Card' }, '../../components/ui/Button': { Button: 'Button' }, '../../components/ui/PageTitle': { PageTitle: 'Title' },
    '../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
    '../../notifications/useNotifications': { useNotificationCenter: () => center, notificationPreferenceRows: rows },
    '../../notifications/notificationForeground': { watchNotificationForeground: () => () => {} },
    '../../theme/theme': { colors: { background: 'navy', primary: 'teal' }, spacing: { sm: 8, md: 12, lg: 20 } },
  });
  const navigation = { navigate: (...args) => routes.push(args), getParent: () => ({ navigate: (...args) => routes.push(args) }) };
  let screen = 'Notifications'; h.mount(() => NotificationsScreen({ route: { name: screen }, navigation }));
  const nodes = [];
  const visit = node => { if (Array.isArray(node)) return node.forEach(visit); if (!node || typeof node !== 'object') return; nodes.push(node); node.children?.forEach(visit); };
  visit(h.value);
  nodes.find(node => node.props.title === 'View report →').props.onPress();
  nodes.find(node => node.props.title === 'View simulation →').props.onPress();
  assert.deepEqual(plain(routes), [['ReportDetail', { portfolioId: 'p', reportId: 'exact-analysis' }], ['Simulate', { screen: 'SimulationResult', params: { portfolioId: 'p', simulationId: 'exact-simulation' } }]]);
  nodes.find(node => node.props.title === 'Clear notification').props.onPress(); h.render();
  let dialog = descendants(h.value).find(node => node.type === 'Dialog');
  assert.equal(dialog.props.visible, true); assert.equal(dialog.props.tone, 'danger'); assert.equal(dialog.props.subject, 'analysis saved');
  assert.equal(confirms, 0); dialog.props.onCancel(); h.render(); assert.ok(!descendants(h.value).some(node => node.type === 'Dialog'));
  descendants(h.value).find(node => node.props.title === 'Clear all notifications').props.onPress(); h.render();
  dialog = descendants(h.value).find(node => node.type === 'Dialog'); assert.match(dialog.props.subject, /including other pages/);
  dialog.props.onConfirm(); assert.equal(confirms, 1);
  screen = 'NotificationSettings'; h.render(); nodes.length = 0; visit(h.value);
  const switches = nodes.filter(node => node.type === 'Switch');
  assert.equal(switches.length, 3); assert.equal(switches[0].props.disabled, false);
  assert.equal(switches[1].props.disabled, true); assert.equal(switches[2].props.disabled, true);
  switches[0].props.onValueChange(true); assert.deepEqual(updates, [['enabled', true]]);
});

test('web bell shows a red top-corner dot only for positive unread counts and preserves its accessible count', () => {
  const h = hookHarness(), routes = []; let unread = 3;
  const { TopNavigation } = load(webRoot, 'src/components/navigation/TopNavigation.tsx', {
    '../../app/navigation': { navItems: [] }, '../../app/routes': { go: route => routes.push(route) },
    '../ui/Icon': { Icon: 'Icon' }, './ProfileMenu': { ProfileMenu: 'Profile' },
    '../../notifications/useNotifications': { useNotificationBadge: () => unread },
  }, { React: h.react });
  h.mount(() => TopNavigation({ route: { page: 'dashboard' } }));
  assert.equal(descendants(h.value).filter(node => node.props.className === 'notification-dot').length, 1);
  const bell = descendants(h.value).find(node => node.props.title === 'Open notifications');
  assert.equal(bell.props['aria-label'], 'Notifications, 3 unread'); bell.props.onClick(); assert.deepEqual(routes, ['notifications']);
  for (const count of [0, null]) { unread = count; h.render(); assert.ok(!descendants(h.value).some(node => node.props.className === 'notification-dot')); }
  const css = fs.readFileSync(path.join(webRoot, 'src/styles.css'), 'utf8');
  assert.match(css, /\.notification-dot\{[^}]*position:absolute[^}]*top:5px[^}]*background:var\(--red-primary\)/);
});

test('mobile Notifications icon shows a red top-corner dot only while unread and remains navigable', () => {
  const h = hookHarness(), routes = []; let unread = 3;
  const { MoreScreen } = load(roots[1], 'src/screens/settings/MoreScreen.tsx', {
    react: h.react, 'react-native': { Pressable: 'Pressable', ScrollView: 'Scroll', Text: 'Text', View: 'View', StyleSheet: { create: value => value } },
    'react-native-safe-area-context': { SafeAreaView: 'Safe' }, '@expo/vector-icons': { Ionicons: 'Icon' },
    '@react-navigation/native': { useFocusEffect: () => {} }, '../../components/ui/Card': { Card: 'Card' },
    '../../components/ui/ErrorState': { InlineErrorCard: 'Error' }, '../../components/ui/PageTitle': { PageTitle: 'Title' },
    '../../portfolio/usePortfolios': { usePortfolios: () => ({ portfolios: [], listStatus: 'ready', refreshPortfolios() {} }) },
    '../../report/useReports': { useReports: () => ({ reports: [], historyStatus: 'ready', refreshReportHistory() {} }) },
    '../../simulation/useSimulations': { useSimulations: () => ({ history: [], historyStatus: 'ready', refreshHistory() {} }) },
    '../../notifications/useNotifications': { useNotificationBadge: () => unread },
    '../../theme/theme': { colors: { danger: 'red', surface: 'navy' }, spacing: {} },
  });
  h.mount(() => MoreScreen({ navigation: { navigate: route => routes.push(route) } }));
  const dot = descendants(h.value).find(node => node.props.style?.backgroundColor === 'red');
  assert.equal(dot.props.style.position, 'absolute'); assert.equal(dot.props.style.top, 9);
  assert.equal(dot.props.accessible, false);
  const entry = descendants(h.value).find(node => node.props.accessibilityLabel === 'Notifications, 3 unread');
  entry.props.onPress(); assert.deepEqual(routes, ['Notifications']);
  for (const count of [0, null]) { unread = count; h.render(); assert.ok(!descendants(h.value).some(node => node.props.style?.backgroundColor === 'red')); }
});

test('both clients keep preferences account-owned and implement no push permissions, tokens or background delivery', () => {
  for (const root of roots) {
    const hooks = fs.readFileSync(path.join(root, 'src/notifications/useNotifications.ts'), 'utf8');
    assert.doesNotMatch(hooks, /localStorage|AsyncStorage|Notification\.requestPermission|expo-notifications|pushToken/);
    const foreground = fs.readFileSync(path.join(root, 'src/notifications/notificationForeground.ts'), 'utf8');
    assert.match(foreground, /30000/); assert.match(foreground, /active|visible/);
  }
  const nav = fs.readFileSync(path.join(roots[1], 'src/navigation/MainTabNavigator.tsx'), 'utf8');
  assert.match(nav, /name="Notifications"/); assert.match(nav, /name="NotificationSettings"/);
  const screen = fs.readFileSync(path.join(roots[1], 'src/screens/notifications/NotificationsScreen.tsx'), 'utf8');
  assert.match(screen, /screen: 'SimulationResult'/); assert.match(screen, /simulationId: item.resource_id/);
  assert.match(screen, /reportId: item.resource_id/);
});
