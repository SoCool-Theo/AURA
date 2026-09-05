// Node-only orchestration checks using the installed TypeScript compiler.
// The minimal hook harness is not a React Native renderer or device E2E test.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');

function load(file, mocks = {}, globals = {}) {
  const module = { exports: {} };
  const code = ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, target: ts.ScriptTarget.ES2022, esModuleInterop: true }
  }).outputText;
  vm.runInNewContext(code, {
    module, exports: module.exports, URL, Headers, ...globals,
    require: (name) => {
      assert.ok(name in mocks, `Unmocked module ${name} in ${file}`);
      return mocks[name];
    }
  }, { filename: file });
  return module.exports;
}

function hookHarness() {
  const slots = [];
  let cursor = 0, effects = [], render, value, dirty;
  const same = (a, b) => a && b && a.length === b.length && a.every((v, i) => Object.is(v, b[i]));
  const react = {
    createContext: () => ({ Provider: 'provider' }),
    createElement: (_type, props) => props.value,
    useState(initial) {
      const i = cursor++;
      if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial;
      return [slots[i], (next) => {
        const resolved = typeof next === 'function' ? next(slots[i]) : next;
        if (!Object.is(resolved, slots[i])) { slots[i] = resolved; dirty = true; }
      }];
    },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useMemo(fn, deps) {
      const i = cursor++;
      if (!same(slots[i]?.deps, deps)) slots[i] = { deps, value: fn() };
      return slots[i].value;
    },
    useCallback(fn, deps) { return react.useMemo(() => fn, deps); },
    useEffect(fn, deps) {
      const i = cursor++;
      if (!same(slots[i]?.deps, deps)) {
        const previous = slots[i];
        slots[i] = { deps };
        effects.push(() => { previous?.cleanup?.(); slots[i].cleanup = fn(); });
      }
    }
  };
  return {
    react,
    mount(fn) { render = fn; this.render(); },
    render() { dirty = false; cursor = 0; value = render(); const pending = effects; effects = []; pending.forEach(fn => fn()); },
    async settle() {
      for (let i = 0; i < 20; i++) { await new Promise(resolve => setImmediate(resolve)); if (dirty) this.render(); }
      assert.equal(dirty, false, 'state settled');
      return value;
    },
    get value() { return value; }
  };
}
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

test('production import graph isolates all financial demos and local calculations', () => {
  const visited = new Set();
  function walk(file) {
    if (visited.has(file)) return;
    visited.add(file);
    const source = ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true);
    for (const node of source.statements) {
      if (!(ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) || !node.moduleSpecifier) continue;
      if (node.isTypeOnly || node.importClause?.isTypeOnly) continue;
      const spec = node.moduleSpecifier.text;
      if (!spec.startsWith('.')) continue;
      const base = path.resolve(path.dirname(file), spec);
      const target = ['', '.ts', '.tsx', '/index.ts', '/index.tsx'].map(ext => base + ext).find(p => fs.existsSync(p) && fs.statSync(p).isFile());
      assert.ok(target, `Resolve ${spec}`);
      walk(target);
    }
  }
  walk(path.join(root, 'App.tsx'));
  const files = [...visited].map(file => path.relative(root, file).replaceAll('\\', '/'));
  assert.deepEqual(files.filter(file => file.includes('/mocks/')).sort(), ['src/mocks/learn.mock.ts']);
  assert.ok(!files.some(file => /localCalculations|PortfolioPerformanceChart|types\/demo/.test(file)));
  for (const file of visited) {
    const text = fs.readFileSync(file, 'utf8');
    if (/\bfetch\s*\(/.test(text)) assert.ok(file.endsWith('apiClient.ts'));
    assert.ok(!/console\.(log|debug|warn|error)\(/.test(text));
  }
});

test('transport distinguishes errors, sanitizes 5xx, and invalidates 401 before body reads', async () => {
  const environment = { apiBaseUrl: 'http://example.invalid:8000' };
  let status = 200, body = '{}', network = false, bodyFailure = false, invalidations = 0;
  const api = load('src/api/apiClient.ts', {
    '../auth/authStorage': { getToken: async () => null }, '../config/environment': { environment }
  }, { fetch: async () => {
    if (network) throw Error('unreachable');
    return { status, ok: status < 400, text: async () => { if (bodyFailure) throw Error('body'); return body; } };
  } });
  api.configureApiAuthentication({ getAccessToken: async () => null, onAuthenticationRejected: async () => { invalidations++; } });
  const request = () => api.apiRequest('/api/test');
  environment.apiBaseUrl = '';
  await assert.rejects(request, { kind: 'configuration' });
  environment.apiBaseUrl = 'http://example.invalid:8000';
  network = true;
  await assert.rejects(request, { kind: 'network' });
  network = false;
  for (const code of [401, 404, 409, 422, 503]) {
    status = code; body = JSON.stringify({ detail: [{ msg: 'internal database exception' }] });
    await assert.rejects(request, error => error.status === code && (code !== 503 || error.detail === null && !error.message.includes('database')));
  }
  status = 401; bodyFailure = true;
  await assert.rejects(request, { status: 401 });
  assert.equal(invalidations, 2);
  bodyFailure = false; status = 200;
  for (const invalid of ['', 'not JSON', 'null', '[]', '42']) {
    body = invalid;
    await assert.rejects(request, { kind: 'malformed-response' });
  }
  body = '{}'; assert.equal(typeof await request(), 'object');
  status = 204; body = '';
  assert.equal(await api.apiRequest('/api/test', { responseMode: 'none' }), undefined);
});

test('selected report history is independent; global failure retains prior complete list; deletion cannot resurrect', async () => {
  const harness = hookHarness();
  let failB = false, pendingB;
  const a = { id: 'a', name: 'A' }, b = { id: 'b', name: 'B' };
  const old = { id: 'old', portfolio_id: 'a', created_at: '2026-01-01T00:00:00Z' };
  const recent = { id: 'recent', portfolio_id: 'a', created_at: '2026-02-01T00:00:00Z' };
  const api = {
    list: async id => {
      if (id === 'b' && failB) throw Error('B unavailable');
      if (id === 'b' && pendingB) return pendingB.promise;
      return { reports: id === 'a' ? [old, recent] : [] };
    }, delete: async () => {}, get: async () => ({})
  };
  const { ReportProvider } = load('src/report/ReportProvider.tsx', {
    react: harness.react, '../api/analyticsApi': { analyticsApi: {} }, '../api/reportsApi': { reportsApi: api },
    '../auth/useAuth': { useAuth: () => ({ status: 'authenticated', user: { id: 'user' } }) }
  });
  harness.mount(() => ReportProvider({})); await harness.settle();
  await harness.value.refreshReportHistory([a, b]); await harness.settle();
  assert.equal(harness.value.reports.map(r => r.id).join(), 'recent,old');
  failB = true;
  assert.equal((await harness.value.getPortfolioReportHistory(a))[0].id, 'recent');
  await harness.value.refreshReportHistory([a, b]); await harness.settle();
  assert.equal(harness.value.historyStatus, 'error');
  assert.equal(harness.value.reports.length, 2);
  failB = false; pendingB = deferred();
  const refresh = harness.value.refreshReportHistory([a, b]);
  await harness.settle();
  await harness.value.deleteReport('a', 'recent');
  pendingB.resolve({ reports: [] }); await refresh; await harness.settle();
  assert.equal(harness.value.reports.map(r => r.id).join(), 'old');
});

test('Dashboard ignores global-history failure and stale selected-portfolio completions', async () => {
  const harness = hookHarness();
  const pendingA = deferred();
  let historyFails = false;
  const state = {
    portfolios: [{ id: 'a', name: 'A' }, { id: 'b', name: 'B' }], activePortfolioId: 'a',
    listStatus: 'ready', isRefreshing: false, selectPortfolio: () => {}, refreshPortfolios: async () => {},
    getPortfolio: async id => ({ id, holdings: [{ symbol: id, weight: 1 }] })
  };
  const reportState = {
    historyStatus: 'error', historyError: Error('unrelated global request'),
    getPortfolioReportHistory: async item => {
      if (historyFails) throw Error('selected history unavailable');
      return item.id === 'a' ? pendingA.promise : [{ id: 'rb', portfolio_id: 'b', created_at: '2026-02-01' }];
    }, getReport: async (portfolio_id, id) => ({ portfolio_id, id, analysis: {} })
  };
  const { useDashboard } = load('src/dashboard/useDashboard.ts', {
    react: harness.react,
    '@react-navigation/native': { useIsFocused: () => true, useFocusEffect: fn => harness.react.useEffect(fn, [fn]) },
    '../portfolio/usePortfolios': { usePortfolios: () => state }, '../report/useReports': { useReports: () => reportState },
    '../api/apiClient': { ApiError: class extends Error {} }
  });
  harness.mount(useDashboard); await harness.settle();
  state.activePortfolioId = 'b'; harness.render(); await harness.settle();
  assert.equal(harness.value.report.id, 'rb');
  pendingA.resolve([{ id: 'ra', portfolio_id: 'a' }]); await harness.settle();
  assert.equal(harness.value.report.id, 'rb');
  historyFails = true; harness.value.retryDetails(); await harness.settle();
  assert.equal(harness.value.reportsState.historyStatus, 'error');
  assert.equal(harness.value.report, null);
  assert.equal(harness.value.portfolio.id, 'b');
  assert.equal(harness.value.refreshing, false);
  historyFails = false; harness.value.retryDetails(); await harness.settle();
  assert.equal(harness.value.report.id, 'rb');
});

test('login verification preserves sessions on temporary failure, clears 401, and allows storage-cleanup retry', async () => {
  class ApiError extends Error { constructor(options) { super(options.message); Object.assign(this, options); } }
  for (const kind of ['network', 'configuration', 'http', 'malformed-response', 'authentication']) {
    const harness = hookHarness();
    let stored = null, failure = new ApiError({ kind, status: kind === 'authentication' ? 401 : 503 });
    let cleanupFails = false;
    const storage = {
      getToken: async () => stored,
      saveToken: async token => { stored = token; },
      clearToken: async () => { if (cleanupFails) throw Error('storage unavailable'); stored = null; }
    };
    const { AuthProvider } = load('src/auth/AuthProvider.tsx', {
      react: harness.react, './authStorage': storage,
      '../api/apiClient': { ApiError, configureApiAuthentication: () => () => {} },
      './authErrors': { sessionRestoreErrorMessage: () => 'Retry verification' },
      '../api/authApi': { authApi: {
        login: async () => ({ access_token: require('node:crypto').randomUUID() }),
        me: async () => { if (failure) throw failure; return { id: 'user', email: 'test@example.invalid' }; }
      } }
    });
    harness.mount(() => AuthProvider({})); await harness.settle();
    await assert.rejects(() => harness.value.signIn({})); await harness.settle();
    assert.equal(harness.value.user, null);
    assert.equal(harness.value.status, kind === 'authentication' ? 'unauthenticated' : 'error');
    assert.equal(stored === null, kind === 'authentication');
    if (kind === 'authentication') continue;
    failure = null;
    await harness.value.retrySessionRestore(); await harness.settle();
    assert.equal(harness.value.status, 'authenticated');
    cleanupFails = true;
    await assert.rejects(() => harness.value.signOut()); await harness.settle();
    assert.equal(harness.value.status, 'error');
    assert.equal(harness.value.user, null);
    assert.ok(stored);
    cleanupFails = false;
    await harness.value.signOut(); await harness.settle();
    assert.equal(harness.value.status, 'unauthenticated');
    assert.equal(stored, null);
  }
});

test('portfolio deletion cannot be undone by an in-flight list or detail response', async () => {
  const harness = hookHarness();
  class ApiError extends Error { constructor(options) { super(options.message); Object.assign(this, options); } }
  const item = { id: 'a', name: 'A', holdings: [] };
  let delayedList = null, delayedDetail = null;
  const { PortfolioProvider } = load('src/portfolio/PortfolioProvider.tsx', {
    react: harness.react, '../api/apiClient': { ApiError },
    '../auth/useAuth': { useAuth: () => ({ status: 'authenticated', user: { id: 'user' } }) },
    './portfolioErrors': { PortfolioCreatedWithoutHoldingsError: Error },
    '../api/portfoliosApi': { portfoliosApi: {
      list: async () => delayedList ? delayedList.promise : { portfolios: [item] },
      get: async () => delayedDetail.promise, delete: async () => {}
    } }
  });
  harness.mount(() => PortfolioProvider({})); await harness.settle();
  delayedList = deferred(); delayedDetail = deferred();
  const refreshing = harness.value.refreshPortfolios();
  const detail = harness.value.getPortfolio('a');
  await harness.value.deletePortfolio('a');
  delayedList.resolve({ portfolios: [item] }); delayedDetail.resolve(item);
  await refreshing; await assert.rejects(() => detail, { status: 404 }); await harness.settle();
  assert.equal(harness.value.portfolios.length, 0);
  assert.equal(harness.value.activePortfolioId, null);
});

test('local storage reads only Learn progress and rejects malformed values', async () => {
  let raw = null;
  const reads = [], writes = [], removed = [];
  const api = load('src/storage/appStorage.ts', {
    '@react-native-async-storage/async-storage': {
      getItem: async key => { reads.push(key); return raw; },
      setItem: async (key, value) => { writes.push([key, value]); },
      multiRemove: async keys => { removed.push(...keys); }
    }
  });
  assert.equal(Object.keys(await api.loadLearnProgress()).length, 0);
  for (const invalid of ['null', '[]', 'invalid', '{"lesson":42}']) {
    raw = invalid; await assert.rejects(() => api.loadLearnProgress());
  }
  raw = '{"lesson":true}'; assert.equal((await api.loadLearnProgress()).lesson, true);
  await api.saveLearnProgress({ lesson: true });
  assert.equal(new Set(reads).size, 1);
  assert.equal(writes[0][0], reads[0]);
  await api.clearLocalAuraData();
  assert.ok(removed.includes(reads[0]));
  assert.ok(!removed.some(key => /token|auth/i.test(key)));
});

test('financial presentation preserves signs/nulls and allocation preserves saved order and zero weights', () => {
  const formatting = load('src/report/reportFormatting.ts');
  const dashboard = load('src/dashboard/dashboardPresentation.ts', { '../report/reportFormatting': formatting });
  assert.equal(dashboard.dashboardPercent(null), 'N/A');
  assert.equal(dashboard.dashboardPercent(undefined), 'N/A');
  assert.equal(dashboard.dashboardPercent(-0.25), '-25.00%');
  assert.equal(dashboard.dashboardPercent(0), '0.00%');
  const points = [{ date: '2026-02-01', return: -0.2 }, { date: '2026-04-01', return: 0.1 }];
  const filtered = dashboard.filterDashboardReturns(points, '1M');
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0], points[1]);
  assert.equal(points.length, 2);
  const validation = load('src/simulation/simulationValidation.ts');
  const result = validation.validateModifiedAllocation({ holdings: [{ symbol: 'B', weight: 0 }, { symbol: 'A', weight: 1 }] }, { A: '100', B: '0' });
  assert.equal(result.error, null);
  assert.equal(result.allocation.map(item => item.symbol).join(), 'B,A');
  assert.equal(result.allocation[0].weight, 0);
  assert.equal(result.allocation[1].weight, 1);
});
