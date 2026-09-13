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
    '../types/portfolio': { portfolioHoldingMode: holdings => holdings.some(item => item.weight === null) ? 'real' : holdings.length ? 'legacy' : 'empty' },
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
    assert.equal(harness.value.sessionExpired, kind === 'authentication');
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

test('mobile error presentation distinguishes auth, not-found, validation, server, and network failures', () => {
  class ApiError extends Error {
    constructor(options) {
      super(options.message ?? 'Request failed');
      Object.assign(this, options);
    }
  }
  const presentation = load('src/api/apiErrorPresentation.ts', {
    './apiClient': { ApiError }
  });
  const classify = (options, extra) => presentation.apiErrorPresentation(
    new ApiError(options),
    extra
  );

  assert.deepEqual(
    [
      classify({ kind: 'authentication', status: 401 }).code,
      classify({ kind: 'http', status: 404 }, { resourceName: 'Portfolio' }).code,
      classify({ kind: 'http', status: 422, detail: [] }).code,
      classify({ kind: 'http', status: 500 }).code,
      classify({ kind: 'network', status: null }).code
    ],
    ['401', '404', '422', '500', 'NETWORK']
  );
  assert.equal(classify({ kind: 'http', status: 404 }).retryable, false);
  assert.equal(classify({ kind: 'http', status: 500 }).retryable, true);
  assert.equal(classify({ kind: 'network', status: null }).retryable, true);

  const issues = presentation.apiValidationIssues(new ApiError({
    kind: 'http',
    status: 422,
    detail: [
      { loc: ['body', 'holdings', 0, 'shares'], msg: 'Must be positive' },
      { loc: ['body', 'name'], msg: 'Required' }
    ]
  }));
  assert.deepEqual(JSON.parse(JSON.stringify(issues)), [
    { path: 'holdings.0.shares', message: 'Must be positive' },
    { path: 'name', message: 'Required' }
  ]);
});

test('blocking, inline, and form error surfaces are shared across mobile workflows', () => {
  const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
  const detailScreens = [
    'src/screens/portfolios/PortfolioDetailScreen.tsx',
    'src/screens/reports/ReportDetailScreen.tsx',
    'src/screens/simulations/SimulationResultScreen.tsx'
  ].map(read).join('\n');
  const formScreens = [
    'src/screens/auth/LoginScreen.tsx',
    'src/screens/auth/RegisterScreen.tsx',
    'src/screens/portfolios/CreatePortfolioScreen.tsx',
    'src/components/portfolio/HoldingsEditor.tsx',
    'src/screens/analytics/PortfolioAnalysisScreen.tsx'
  ].map(read).join('\n');

  assert.match(detailScreens, /ScreenErrorState/);
  assert.match(detailScreens, /InlineErrorCard/);
  assert.match(formScreens, /FormErrorSummary/);
  assert.match(formScreens, /apiValidationIssues/);
  assert.ok(!/Alert\.alert\(['"](?:Unable|Check)/.test(formScreens));
});

test('interactive controls expose accessibility semantics and compact layouts can wrap', () => {
  const sourceRoot = path.join(root, 'src');
  const sourceFiles = [];
  const collect = directory => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const target = path.join(directory, entry.name);
      if (entry.isDirectory()) collect(target);
      else if (/\.tsx$/.test(entry.name)) sourceFiles.push(target);
    }
  };
  collect(sourceRoot);

  let pressableCount = 0;
  let textInputCount = 0;
  for (const file of sourceFiles) {
    const source = ts.createSourceFile(
      file,
      fs.readFileSync(file, 'utf8'),
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX
    );
    const visit = node => {
      if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
        const tag = node.tagName.getText(source);
        const attributes = new Set(node.attributes.properties
          .filter(ts.isJsxAttribute)
          .map(attribute => attribute.name.getText(source)));
        const location = source.getLineAndCharacterOfPosition(node.getStart(source));
        const label = `${path.relative(root, file)}:${location.line + 1}`;
        if (tag === 'Pressable') {
          pressableCount += 1;
          assert.ok(attributes.has('accessibilityRole'), `${label} Pressable needs an accessibility role`);
        }
        if (tag === 'TextInput') {
          textInputCount += 1;
          assert.ok(attributes.has('accessibilityLabel'), `${label} TextInput needs an accessibility label`);
        }
      }
      ts.forEachChild(node, visit);
    };
    visit(source);
  }

  assert.ok(pressableCount > 20);
  assert.ok(textInputCount > 5);
  const compactLayouts = [
    'src/screens/portfolios/CreatePortfolioScreen.tsx',
    'src/components/portfolio/HoldingsEditor.tsx',
    'src/screens/analytics/PortfolioAnalysisScreen.tsx',
    'src/screens/simulations/AllocationChangeScreen.tsx',
    'src/components/ui/ErrorState.tsx'
  ].map(file => fs.readFileSync(path.join(root, file), 'utf8')).join('\n');
  assert.ok((compactLayouts.match(/flexWrap:\s*['"]wrap['"]/g) ?? []).length >= 5);
  assert.match(fs.readFileSync(path.join(root, 'src/components/ui/DateRangeSelector.tsx'), 'utf8'), /minHeight:\s*44/);
  assert.match(fs.readFileSync(path.join(root, 'src/components/ui/SegmentedTabs.tsx'), 'utf8'), /minHeight:\s*44/);
});

test('real holding contracts preserve precision, order, modes, and valuation allocations', () => {
  const validation = load('src/portfolio/portfolioValidation.ts');
  const portfolioTypes = load('src/types/portfolio.ts');
  const simulation = load('src/simulation/simulationValidation.ts');

  const result = validation.validateRealHoldingDrafts([
    {
      id: 'first', symbol: ' msft ', investedAmount: '1500.250000000000',
      investedCurrency: 'THB', shares: '10.125', purchaseDate: '2026-01-10'
    },
    {
      id: 'second', symbol: 'AAPL', investedAmount: '900',
      investedCurrency: 'USD', shares: '4.5', purchaseDate: '2025-12-01'
    }
  ]);
  assert.equal(result.error, null);
  assert.deepEqual(JSON.parse(JSON.stringify(result.holdings)), [
    {
      symbol: 'MSFT', invested_amount: '1500.250000000000',
      invested_currency: 'THB', shares: '10.125', purchase_date: '2026-01-10'
    },
    {
      symbol: 'AAPL', invested_amount: '900', invested_currency: 'USD',
      shares: '4.5', purchase_date: '2025-12-01'
    }
  ]);
  assert.match(
    validation.validateRealHoldingDrafts([
      { id: 'a', symbol: 'AAPL', investedAmount: '0', investedCurrency: 'USD', shares: '1', purchaseDate: '2026-01-01' }
    ]).error,
    /positive invested amount/i
  );
  assert.match(
    validation.validateRealHoldingDrafts([
      { id: 'a', symbol: 'AAPL', investedAmount: '1', investedCurrency: 'USD', shares: '1', purchaseDate: '9999-01-01' }
    ]).error,
    /not in the future/i
  );

  const legacy = { symbol: 'AAPL', weight: 1, invested_amount: null, invested_currency: null, shares: null, purchase_date: null, position: 0 };
  const real = { symbol: 'MSFT', weight: null, invested_amount: '1', invested_currency: 'USD', shares: '1', purchase_date: '2026-01-01', position: 0 };
  assert.equal(portfolioTypes.portfolioHoldingMode([]), 'empty');
  assert.equal(portfolioTypes.portfolioHoldingMode([legacy]), 'legacy');
  assert.equal(portfolioTypes.portfolioHoldingMode([real]), 'real');
  assert.equal(portfolioTypes.portfolioHoldingMode([legacy, real]), 'mixed');

  const inputs = simulation.allocationInputsFromValuation({ holdings: [
    { symbol: 'MSFT', current_allocation: '0.625' },
    { symbol: 'AAPL', current_allocation: '0.375' }
  ] });
  assert.deepEqual(JSON.parse(JSON.stringify(inputs)), { MSFT: '62.5', AAPL: '37.5' });
});

test('purchase-date picker accepts backend-safe past dates through today', () => {
  const purchaseDates = load('src/portfolio/purchaseDate.ts');
  const validation = load('src/portfolio/portfolioValidation.ts');
  const now = new Date();
  const maximumDate = purchaseDates.maximumPurchaseDate(now);
  const today = now.toISOString().slice(0, 10);
  const yesterday = new Date(now.getTime() - 86_400_000).toISOString().slice(0, 10);
  const tomorrow = new Date(now.getTime() + 86_400_000).toISOString().slice(0, 10);
  const holding = purchaseDate => [{
    id: purchaseDate,
    symbol: 'AAPL',
    investedAmount: '1000',
    investedCurrency: 'USD',
    shares: '5',
    purchaseDate
  }];

  assert.equal(purchaseDates.formatPurchaseDate(maximumDate), today);
  assert.equal(
    purchaseDates.formatPurchaseDate(
      purchaseDates.purchaseDatePickerValue(yesterday, maximumDate)
    ),
    yesterday
  );
  assert.equal(validation.validateRealHoldingDrafts(holding(today)).error, null);
  assert.equal(validation.validateRealHoldingDrafts(holding(yesterday)).error, null);
  assert.match(validation.validateRealHoldingDrafts(holding(tomorrow)).error, /not in the future/i);

  const picker = fs.readFileSync(path.join(root, 'src/components/portfolio/PurchaseDateField.tsx'), 'utf8');
  const create = fs.readFileSync(path.join(root, 'src/screens/portfolios/CreatePortfolioScreen.tsx'), 'utf8');
  const edit = fs.readFileSync(path.join(root, 'src/components/portfolio/HoldingsEditor.tsx'), 'utf8');
  assert.match(picker, /calendar-outline/);
  assert.match(picker, /maximumDate=\{maximumDate\}/);
  assert.match(create, /<PurchaseDateField/);
  assert.match(edit, /<PurchaseDateField/);
});

test('portfolio report entry points preserve newest-report AI grounding', () => {
  const reportDetail = fs.readFileSync(
    path.join(root, 'src/screens/reports/ReportDetailScreen.tsx'),
    'utf8'
  );
  const portfolios = fs.readFileSync(
    path.join(root, 'src/screens/portfolios/PortfoliosScreen.tsx'),
    'utf8'
  );
  const portfolioCard = fs.readFileSync(
    path.join(root, 'src/components/portfolio/PortfolioCard.tsx'),
    'utf8'
  );
  const assistant = fs.readFileSync(
    path.join(root, 'src/screens/assistant/AssistantScreen.tsx'),
    'utf8'
  );

  assert.match(reportDetail, /Ask Aura About This Portfolio/);
  assert.match(reportDetail, /newest saved report/);
  assert.match(reportDetail, /navigate\('AI', \{ portfolioId \}\)/);
  assert.match(portfolios, /refreshReportHistory\(portfolios\)/);
  assert.match(portfolios, /latestReportByPortfolio/);
  assert.match(portfolioCard, /View Latest Report/);
  assert.match(assistant, /requestedPortfolioId/);
  assert.ok(!/navigate\('AI',\s*\{[^}]*reportId/.test(reportDetail));
});

test('real holding API clients send explicit currency and real holding payloads', async () => {
  const calls = [];
  const request = async (path, options = {}) => {
    calls.push({ path, options });
    return {};
  };
  const { portfoliosApi } = load('src/api/portfoliosApi.ts', {
    './apiClient': { apiRequest: request }
  });
  const { analyticsApi } = load('src/api/analyticsApi.ts', {
    './apiClient': { apiRequest: request }
  });
  const portfolioId = 'e6518442-58cb-408f-af47fb00b555';
  const holdings = [{
    symbol: 'AAPL', invested_amount: '1000', invested_currency: 'USD',
    shares: '5', purchase_date: '2026-01-01'
  }];

  await portfoliosApi.getValuation(portfolioId, 'THB');
  await portfoliosApi.replaceRealHoldings(portfolioId, holdings);
  await analyticsApi.analyze(
    portfolioId,
    { start_date: '2025-01-01', end_date: '2025-12-31' },
    'THB'
  );

  assert.equal(calls[0].path, `/api/portfolios/${portfolioId}/valuation?currency=THB`);
  assert.equal(calls[1].options.method, 'PUT');
  assert.deepEqual(
    JSON.parse(JSON.stringify(calls[1].options.body)),
    { holdings }
  );
  assert.equal(calls[2].path, `/api/portfolios/${portfolioId}/reports?currency=THB`);
  assert.equal(calls[2].options.method, 'POST');
});

test('Create Portfolio records real holdings and leaves allocation to the backend', () => {
  const source = fs.readFileSync(
    path.join(root, 'src/screens/portfolios/CreatePortfolioScreen.tsx'),
    'utf8'
  );

  assert.match(source, /createPortfolioWithRealHoldings/);
  assert.match(source, /validateRealHoldingDrafts/);
  assert.match(source, /Invested Amount/);
  assert.match(source, /Shares Owned/);
  assert.match(source, /<PurchaseDateField/);
  assert.match(source, /Automatic allocation/);
  assert.ok(!/Weight %|TOTAL ALLOCATION|totalPercent/.test(source));
  assert.ok(!/current_allocation|asset_price|current_value/.test(source));
});

test('all portfolio CRUD screens use real holdings and never submit manual weights', () => {
  const create = fs.readFileSync(path.join(root, 'src/screens/portfolios/CreatePortfolioScreen.tsx'), 'utf8');
  const editor = fs.readFileSync(path.join(root, 'src/components/portfolio/HoldingsEditor.tsx'), 'utf8');
  const provider = fs.readFileSync(path.join(root, 'src/portfolio/PortfolioProvider.tsx'), 'utf8');
  const api = fs.readFileSync(path.join(root, 'src/api/portfoliosApi.ts'), 'utf8');

  assert.match(editor, /replaceRealHoldings/);
  assert.match(editor, /Convert legacy allocation/);
  assert.match(editor, /Invested Amount/);
  assert.match(editor, /Shares Owned/);
  assert.match(editor, /<PurchaseDateField/);
  assert.ok(!/Weight %|TOTAL ALLOCATION|weightPercent/.test(`${create}\n${editor}`));
  assert.ok(!/createPortfolioWithHoldings|replaceHoldings\s*[:=(]/.test(`${provider}\n${api}`));
});

test('valuation, report V2, and simulation V2 pages preserve backend authority', () => {
  const detail = fs.readFileSync(path.join(root, 'src/screens/portfolios/PortfolioDetailScreen.tsx'), 'utf8');
  const dashboard = fs.readFileSync(path.join(root, 'src/dashboard/useDashboard.ts'), 'utf8');
  const analysis = fs.readFileSync(path.join(root, 'src/components/analytics/AnalysisResults.tsx'), 'utf8');
  const reportDetail = fs.readFileSync(path.join(root, 'src/screens/reports/ReportDetailScreen.tsx'), 'utf8');
  const allocation = fs.readFileSync(path.join(root, 'src/screens/simulations/AllocationChangeScreen.tsx'), 'utf8');
  const combined = fs.readFileSync(path.join(root, 'src/screens/simulations/CombinedSimulationScreen.tsx'), 'utf8');
  const simulationDetail = fs.readFileSync(path.join(root, 'src/screens/simulations/SimulationResultScreen.tsx'), 'utf8');

  assert.match(detail, /getPortfolioValuation/);
  assert.match(detail, /current_allocation/);
  assert.match(dashboard, /getPortfolioValuation/);
  assert.match(analysis, /FROZEN VALUATION · V2/);
  assert.match(reportDetail, /does not rerun analysis[\s\S]*fresh portfolio valuation/);
  assert.match(allocation, /allocationInputsFromValuation/);
  assert.match(combined, /allocationInputsFromValuation/);
  assert.match(simulationDetail, /isSimulationHistoryV2/);
  assert.ok(!/getPortfolioValuation/.test(`${analysis}\n${reportDetail}\n${simulationDetail}`));
});

test('AI client uses the authenticated backend contract and rejects malformed success bodies', async () => {
  class ApiError extends Error {
    constructor(options) {
      super(options.message);
      Object.assign(this, options);
    }
  }
  const portfolioId = 'e6518442-58cb-408f-ae3f-bf47fb00b555';
  const reportId = '10000000-0000-0000-0000-000000000001';
  const request = { portfolio_id: portfolioId, message: 'Why is this risky?' };
  let response = {
    answer: 'The saved report shows historical concentration risk.',
    sources: [
      { type: 'portfolio', id: portfolioId },
      { type: 'report', id: reportId }
    ],
    limitations: ['This explanation uses historical data.']
  };
  let call;
  const { agentApi } = load('src/api/agentApi.ts', {
    './apiClient': {
      ApiError,
      apiRequest: async (path, options) => {
        call = { path, options };
        return response;
      }
    }
  });

  assert.equal(
    JSON.stringify(await agentApi.explain(request)),
    JSON.stringify(response)
  );
  assert.equal(call.path, '/api/agent/explain');
  assert.equal(call.options.method, 'POST');
  assert.deepEqual(call.options.body, request);

  for (const malformed of [
    { answer: '', sources: [], limitations: [] },
    { answer: 'Answer', sources: null, limitations: [] },
    { answer: 'Answer', sources: [{ type: 'unknown', id: portfolioId }], limitations: [] },
    { answer: 'Answer', sources: [{ type: 'portfolio', id: 'not-a-uuid' }], limitations: [] },
    { answer: 'Answer', sources: [], limitations: [42] }
  ]) {
    response = malformed;
    await assert.rejects(
      () => agentApi.explain(request),
      error => error.kind === 'malformed-response'
    );
  }
});

test('AI errors remain truthful and retryable without exposing provider details', () => {
  class ApiError extends Error {
    constructor(options) {
      super(options.message);
      Object.assign(this, options);
    }
  }
  const { agentErrorMessage } = load('src/agent/agentErrors.ts', {
    '../api/apiClient': { ApiError }
  });

  assert.match(agentErrorMessage(new ApiError({ status: 401 })), /sign in again/i);
  assert.match(agentErrorMessage(new ApiError({ status: 404 })), /could not be found/i);
  assert.match(agentErrorMessage(new ApiError({ status: 422 })), /could not process/i);
  assert.match(agentErrorMessage(new ApiError({ status: 502 })), /invalid AI explanation/i);
  assert.match(agentErrorMessage(new ApiError({ status: 503 })), /temporarily unavailable/i);
  assert.match(agentErrorMessage(new ApiError({ kind: 'network' })), /check the connection/i);
  assert.match(agentErrorMessage(new ApiError({ kind: 'configuration' })), /not configured/i);
  assert.match(agentErrorMessage(new ApiError({ kind: 'malformed-response' })), /unexpected AI response/i);
});

test('mobile Assistant has no direct provider access or synthetic conversation authority', () => {
  const api = fs.readFileSync(path.join(root, 'src/api/agentApi.ts'), 'utf8');
  const screen = fs.readFileSync(path.join(root, 'src/screens/assistant/AssistantScreen.tsx'), 'utf8');

  assert.match(api, /apiRequest/);
  assert.match(api, /\/api\/agent\/explain/);
  assert.match(screen, /usePortfolios/);
  assert.match(screen, /AbortController/);
  assert.match(screen, /newest saved report/);
  assert.ok(!/OPENAI_API_KEY|GROQ_API_KEY|api\.openai|api\.groq/i.test(`${api}\n${screen}`));
  assert.ok(!/AsyncStorage|SecureStore|conversationHistory|chatHistory/.test(screen));
});
