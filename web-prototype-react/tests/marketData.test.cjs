const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const roots = [path.resolve(__dirname, '..'), path.resolve(__dirname, '../../mobile')];
const deferred = () => { let resolve; const promise = new Promise(r => resolve = r); return { promise, resolve }; };

function load(root, file, mocks = {}, globals = {}) {
  const module = { exports: {} };
  const code = ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React, esModuleInterop: true },
  }).outputText;
  vm.runInNewContext(code, { module, exports: module.exports, AbortController, Date, setTimeout, clearTimeout,
    require(name) { assert.ok(name in mocks, 'Unmocked ' + name); return mocks[name]; }, ...globals });
  return module.exports;
}

function harness() {
  const slots = []; let cursor = 0, effects = [], render, value, dirty;
  const same = (a, b) => a && b && a.length === b.length && a.every((v, i) => Object.is(v, b[i]));
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial;
      return [slots[i], next => { const resolved = typeof next === 'function' ? next(slots[i]) : next; if (!Object.is(resolved, slots[i])) { slots[i] = resolved; dirty = true; } }]; },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useMemo(fn, deps) { const i = cursor++; if (!same(slots[i]?.deps, deps)) slots[i] = { deps, value: fn() }; return slots[i].value; },
    useCallback(fn, deps) { return react.useMemo(() => fn, deps); },
    useEffect(fn, deps) { const i = cursor++; if (!same(slots[i]?.deps, deps)) { const old = slots[i]; slots[i] = { deps }; effects.push(() => { old?.cleanup?.(); slots[i].cleanup = fn(); }); } },
  };
  return { react, mount(fn) { render = fn; this.render(); },
    render() { dirty = false; cursor = 0; value = render(); const pending = effects; effects = []; pending.forEach(fn => fn()); },
    async settle() { for (let i = 0; i < 20; i++) { await new Promise(r => setImmediate(r)); if (dirty) this.render(); } assert.equal(dirty, false); },
    unmount() { for (const slot of slots) slot?.cleanup?.(); }, get value() { return value; },
  };
}
const status = {
  mode: 'daily', checked_at: '2026-10-06T01:00:00Z', worker_status: 'online', last_run_status: 'success', data_status: 'missing',
  observations: [
    { symbol: 'AAPL', latest_price_date: '2026-10-05', is_current: true },
    { symbol: 'BTC-USD', latest_price_date: null, is_current: false },
    { symbol: 'THB=X', latest_price_date: '2026-09-20', is_current: false },
  ],
};

function mountRefresh(root, options = {}) {
  const h = harness(); let account = 'a', enabled = true, active = true, foreground, activity, stops = 0, reloads = 0;
  let api = async () => status; const calls = [], timers = new Map();
  const hooks = load(root, 'src/marketData/useMarketDataRefresh.ts', {
    react: h.react,
    '@react-navigation/native': { useFocusEffect: fn => h.react.useEffect(fn, [fn]) },
    '../auth/useAuth': { useAuth: () => ({ user: account ? { id: account } : null, status: account ? 'authenticated' : 'unauthenticated' }) },
    '../api/marketDataApi': { getMarketDataStatus: args => { calls.push(args); return api(args); } },
    './marketDataForeground': { watchMarketDataForeground: (fn, change) => { foreground = fn; activity = change; change(active); return () => stops++; } },
  }, { setTimeout: fn => { const id = Symbol(); timers.set(id, fn); return id; }, clearTimeout: id => timers.delete(id) });
  if (options.api) api = options.api;
  h.mount(() => hooks.useMarketDataRefresh(() => reloads++, enabled));
  return { h, calls, timers, setApi(value) { api = value; },
    setAccount(value) { account = value; h.render(); }, setEnabled(value) { enabled = value; h.render(); },
    foreground() { foreground(); }, activity(value) { active = value; activity(value); },
    get reloads() { return reloads; }, get stops() { return stops; } };
}

for (const root of roots) {
  const name = path.basename(root);
  test(name + ': status adapter is read-only and forwards authentication/cancellation', async () => {
    const calls = [], signal = new AbortController().signal;
    const api = load(root, 'src/api/marketDataApi.ts', { './apiClient': { apiRequest: async (...args) => { calls.push(args); return status; } } });
    assert.equal(await api.getMarketDataStatus({ token: 'test', signal }), status);
    assert.equal(calls[0][0], '/api/market-data/status');
    assert.equal(calls[0][1].token, 'test'); assert.equal(calls[0][1].signal, signal);
    assert.equal(calls[0][1].method, undefined); assert.equal(calls[0][1].body, undefined);
  });
  test(name + ': scoped freshness, missing/stale FX, partial/failure and offline states remain truthful', () => {
    const { marketDataPresentation: show } = load(root, 'src/marketData/marketDataPresentation.ts');
    assert.equal(show(status, false, ['AAPL']).tone, 'success'); // unrelated missing crypto is not a portfolio warning
    assert.match(show(status, false, ['BTC-USD']).title, /missing/);
    assert.match(show(status, false, ['AAPL', 'THB=X']).title, /outdated/);
    assert.match(show(status, false, ['unknown']).title, /missing/);
    assert.equal(show(status, false, []).tone, 'muted');
    assert.match(show({ ...status, last_run_status: 'partial' }, false, ['AAPL']).detail, /partial/);
    assert.equal(show({ ...status, last_run_status: 'partial' }, false, ['AAPL']).tone, 'warning');
    assert.match(show({ ...status, last_run_status: 'failed' }, false, ['AAPL']).detail, /failed/);
    const offline = show({ ...status, worker_status: 'offline', last_run_status: 'running' }, false, ['AAPL']);
    assert.match(offline.detail, /offline/); assert.doesNotMatch(offline.title, /updating/i);
    assert.match(show({ ...status, worker_status: 'unknown' }, false, ['AAPL']).detail, /not connected/);
    assert.match(show(status, true, ['AAPL']).title, /unavailable/);
    assert.match(show(null, false, ['AAPL']).title, /Checking/);
    assert.match(show(status, false, ['AAPL']).detail, /Not live quotes/);
  });
  test(name + ': foreground/manual refresh coalesces requests and status failure does not block price reads', async () => {
    const c = mountRefresh(root); await c.h.settle();
    assert.equal(c.calls.length, 1); assert.equal(c.reloads, 0);
    const pending = deferred(); c.setApi(() => pending.promise);
    c.foreground(); c.foreground(); c.h.value.refresh(); await c.h.settle();
    assert.equal(c.calls.length, 2); assert.equal(c.reloads, 1); assert.equal(c.h.value.refreshing, true);
    pending.resolve(status); await c.h.settle();
    c.setApi(async () => { throw Error('secret URL'); }); c.h.value.refresh(); await c.h.settle();
    assert.equal(c.reloads, 2); assert.equal(c.h.value.unavailable, true); assert.equal(c.h.value.status, null);
    c.setApi(async () => status); c.h.value.refresh(); await c.h.settle();
    assert.equal(c.h.value.unavailable, false); assert.equal(c.h.value.status.mode, 'daily');
    c.h.unmount(); assert.equal(c.timers.size, 0);
  });
  test(name + ': inactive/unmounted screens abort and suppress late completions; returning refreshes', async () => {
    const pending = deferred(), c = mountRefresh(root, { api: () => pending.promise });
    await c.h.settle(); c.activity(false); await c.h.settle();
    assert.equal(c.calls[0].signal.aborted, true); assert.equal(c.h.value.refreshing, false);
    c.foreground(); c.h.value.refresh(); assert.equal(c.calls.length, 1);
    pending.resolve(status); await c.h.settle(); assert.equal(c.h.value.status, null);
    c.setApi(async () => status); c.activity(true); c.foreground(); await c.h.settle();
    assert.equal(c.calls.length, 2); assert.equal(c.reloads, 1);
    const late = deferred(); c.setApi(() => late.promise); c.h.value.refresh(); await c.h.settle();
    c.h.unmount(); assert.equal(c.calls.at(-1).signal.aborted, true);
    late.resolve({ ...status, mode: 'invalid-late' }); await c.h.settle();
    assert.equal(c.h.value.status.mode, 'daily'); assert.equal(c.stops, 1);
  });
  test(name + ': account changes and disabled planned/legacy contexts cannot expose stale status', async () => {
    const old = deferred(), newer = deferred(), c = mountRefresh(root, { api: () => old.promise });
    c.setApi(() => newer.promise); c.setAccount('b'); await c.h.settle();
    assert.equal(c.calls[0].signal.aborted, true); assert.equal(c.h.value.status, null);
    old.resolve({ ...status, mode: 'old-account' }); await c.h.settle(); assert.equal(c.h.value.status, null);
    newer.resolve(status); await c.h.settle(); assert.equal(c.h.value.status.mode, 'daily');
    c.setEnabled(false); await c.h.settle(); assert.equal(c.h.value.status, null);
    const count = c.calls.length; c.h.value.refresh(); assert.equal(c.calls.length, count);
    c.setAccount(null); c.setEnabled(true); await c.h.settle(); assert.equal(c.calls.length, count);
    c.h.unmount();
  });
  test(name + ': stalled status requests time out safely and can be retried without late overwrite', async () => {
    const late = deferred(), c = mountRefresh(root, { api: () => late.promise });
    await c.h.settle(); [...c.timers.values()][0](); await c.h.settle();
    assert.equal(c.calls[0].signal.aborted, true); assert.equal(c.h.value.unavailable, true);
    c.setApi(async () => status); c.h.value.refresh(); await c.h.settle();
    late.resolve({ ...status, mode: 'too-late' }); await c.h.settle();
    assert.equal(c.h.value.status.mode, 'daily'); c.h.unmount();
  });
  test(name + ': five-minute polling stops in background and disposes listeners', () => {
    const timers = new Map(), listeners = new Map(); let count = 0, active = true; const changes = [];
    const document = { visibilityState: 'visible', addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: name => listeners.delete(name) };
    const AppState = { currentState: 'active', addEventListener: (_, fn) => { listeners.set('change', fn); return { remove: () => listeners.delete('change') }; } };
    const globals = { document, window: { addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: name => listeners.delete(name) },
      setInterval: (fn, delay) => { assert.equal(delay, 300000); const id = Symbol(); timers.set(id, fn); return id; }, clearInterval: id => timers.delete(id) };
    const { watchMarketDataForeground: watch } = load(root, 'src/marketData/marketDataForeground.ts', { 'react-native': { AppState } }, globals);
    const stop = watch(() => count++, value => { active = value; changes.push(value); });
    assert.equal(timers.size, 1); [...timers.values()][0](); assert.equal(count, 1);
    function visibility(value) { if (name === 'mobile') listeners.get('change')(value ? 'active' : 'background'); else { document.visibilityState = value ? 'visible' : 'hidden'; listeners.get('visibilitychange')(); } }
    visibility(false); assert.equal(active, false); assert.equal(timers.size, 0);
    visibility(true); assert.equal(active, true); assert.equal(count, 2); assert.equal(timers.size, 1);
    visibility(true); assert.equal(count, 2); assert.equal(timers.size, 1);
    assert.deepEqual(changes, [true, false, true]);
    stop(); assert.equal(timers.size, 0); assert.equal(listeners.size, 0);
  });
}

test('clients limit automatic reads to Watchlist/current values and leave immutable history untouched', () => {
  for (const root of roots) {
    const mobile = path.basename(root) === 'mobile';
    const files = mobile ? ['src/screens/watchlist/WatchlistScreen.tsx', 'src/screens/dashboard/DashboardScreen.tsx', 'src/screens/portfolios/PortfolioDetailScreen.tsx']
      : ['src/pages/watchlist/WatchlistPage.tsx', 'src/pages/dashboard/DashboardPage.tsx', 'src/pages/portfolios/PortfolioDetailView.tsx'];
    for (const file of files) {
      const source = fs.readFileSync(path.join(root, file), 'utf8');
      assert.match(source, /useMarketDataRefresh/); assert.match(source, /<MarketDataStatus/);
      if (!file.includes('watchlist')) { assert.match(source, /portfolio_type === 'CURRENT'/); assert.match(source, /THB=X/); }
    }
    const watchlist = fs.readFileSync(path.join(root, files[0]), 'utf8');
    assert.match(watchlist, /read.current\?\.abort\(\)/);
    assert.match(watchlist, /if \(!controller.signal.aborted\) setItems/);
    assert.doesNotMatch(watchlist, /Saved market data<\/span>/);
    const walk = dir => fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => entry.isDirectory() ? walk(path.join(dir, entry.name)) : [path.join(dir, entry.name)]);
    for (const file of walk(path.join(root, 'src')).filter(file => /(?:reports|simulations)[\\/]/.test(file) && /tsx?$/.test(file))) {
      assert.doesNotMatch(fs.readFileSync(file, 'utf8'), /useMarketDataRefresh/, file);
    }
  }
});

function descendants(tree) {
  const nodes = [];
  const walk = node => { if (Array.isArray(node)) return node.forEach(walk); if (!node || typeof node !== 'object') return; nodes.push(node); node.children?.forEach(walk); };
  walk(tree); return nodes;
}

for (const root of roots) {
  const mobile = path.basename(root) === 'mobile';
  test(path.basename(root) + ': refreshing Watchlist cannot restore a deleted asset; failed reads retain saved prices', async () => {
    const h = harness(), late = deferred(); let foreground, calls = 0, fail = false;
    const observed = { id: 'w', symbol: 'AAPL', latest_price: 100, latest_price_date: '2026-10-05', daily_change_percent: 1, ytd_change_percent: 2 };
    const signals = [];
    const list = async options => {
      signals.push(options.signal); calls++;
      if (fail) throw Error('read unavailable');
      if (calls === 2) return late.promise;
      return { items: calls === 1 ? [observed] : [] };
    };
    const api = { list, add: async () => observed, remove: async () => {} };
    const mocks = {
      react: h.react,
      '../../marketData/MarketDataStatus': { MarketDataStatus: 'MarketDataStatus' },
      '../../marketData/useMarketDataRefresh': { useMarketDataRefresh: callback => {
        foreground = callback; return { refresh: () => foreground(), status, refreshing: false, unavailable: false };
      } },
      '../../types/watchlist': {},
    };
    const ui = ['Button', 'Card', 'ConfirmationDialog', 'EmptyState', 'LoadingState', 'PageTitle', 'Icon'];
    for (const name of ui) mocks['../../components/ui/' + name] = { [name]: name };
    const errorFile = mobile ? 'ErrorState' : 'ApiErrorState';
    mocks['../../components/ui/' + errorFile] = { InlineErrorCard: 'InlineErrorCard', ScreenErrorState: 'ScreenErrorState' };
    if (mobile) {
      mocks['@react-navigation/native'] = { useFocusEffect: fn => h.react.useEffect(fn, [fn]) };
      mocks['@expo/vector-icons'] = { Ionicons: 'Ionicons' };
      mocks['react-native'] = { Pressable: 'Pressable', RefreshControl: 'RefreshControl', ScrollView: 'ScrollView', Text: 'Text', TextInput: 'TextInput', View: 'View', StyleSheet: { create: value => value } };
      mocks['react-native-safe-area-context'] = { SafeAreaView: 'SafeAreaView' };
      mocks['../../api/watchlistApi'] = { watchlistApi: api };
      mocks['../../portfolio/supportedAssetSymbols'] = { supportedAssets: [{ symbol: 'AAPL', name: 'Apple' }] };
      mocks['../../theme/theme'] = { colors: {}, spacing: {} };
      mocks['../../watchlist/watchlistUi'] = { watchlistErrorMessage: () => 'Failed', formatWatchlistDate: value => value, formatWatchlistPercent: value => value, formatWatchlistPrice: value => value };
    } else {
      mocks['../../api/watchlistApi'] = { listWatchlist: list, addWatchlistItem: api.add, deleteWatchlistItem: api.remove };
      mocks['../portfolios/supportedAssetSymbols'] = { supportedAssets: [{ symbol: 'AAPL', name: 'Apple' }] };
      mocks['./components/WatchlistTable'] = { WatchlistTable: 'WatchlistTable' };
      mocks['./components/WatchlistToolbar'] = { WatchlistToolbar: 'WatchlistToolbar' };
      mocks['./watchlistUi'] = { watchlistErrorMessage: () => 'Failed' };
    }
    const file = mobile ? 'src/screens/watchlist/WatchlistScreen.tsx' : 'src/pages/watchlist/WatchlistPage.tsx';
    const page = load(root, file, mocks, { React: h.react });
    h.mount(mobile ? page.WatchlistScreen : page.WatchlistPage); await h.settle();
    const remove = () => {
      const nodes = descendants(h.value);
      if (mobile) nodes.find(node => node.props.accessibilityLabel === 'Remove AAPL from Watchlist').props.onPress();
      else nodes.find(node => node.type === 'WatchlistTable').props.onRemove('AAPL');
    };
    foreground(); await h.settle(); assert.equal(calls, 2);
    remove(); await h.settle();
    descendants(h.value).find(node => node.type === 'ConfirmationDialog').props.onConfirm(); await h.settle();
    assert.equal(signals[1].aborted, true); assert.equal(calls, 3);
    late.resolve({ items: [observed] }); await h.settle();
    if (mobile) assert.ok(!descendants(h.value).some(node => node.props.accessibilityLabel === 'Remove AAPL from Watchlist'));
    else assert.equal(descendants(h.value).find(node => node.type === 'WatchlistTable').props.assets.length, 0);
    h.unmount();

    // A separate session checks that a failed read does not wipe successfully loaded rows.
    const fresh = harness(); mocks.react = fresh.react;
    if (mobile) mocks['@react-navigation/native'].useFocusEffect = fn => fresh.react.useEffect(fn, [fn]);
    calls = 0; fail = false;
    const second = load(root, file, mocks, { React: fresh.react });
    fresh.mount(mobile ? second.WatchlistScreen : second.WatchlistPage); await fresh.settle();
    fail = true; foreground(); await fresh.settle();
    const nodes = descendants(fresh.value); assert.ok(nodes.some(node => node.type === 'InlineErrorCard'));
    if (mobile) assert.ok(nodes.some(node => node.props.accessibilityLabel === 'Remove AAPL from Watchlist'));
    else assert.equal(nodes.find(node => node.type === 'WatchlistTable').props.assets[0].latest_price, 100);
    fresh.unmount();
  });
}
