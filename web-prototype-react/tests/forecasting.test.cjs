const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const plain = value => JSON.parse(JSON.stringify(value));
const deferred = () => { let resolve; const promise = new Promise(r => resolve = r); return { promise, resolve }; };
class ApiError extends Error { constructor(status, detail, kind = 'http') { super('unsafe internal message'); this.status = status; this.detail = detail; this.kind = kind; } }
function load(file, mocks = {}, globals = {}) {
  const module = { exports: {} };
  const code = ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React, esModuleInterop: true },
  }).outputText;
  vm.runInNewContext(code, { module, exports: module.exports, Date, AbortController, setTimeout, clearTimeout,
    require(name) { assert.ok(name in mocks, 'Unmocked ' + name); return mocks[name]; }, ...globals });
  return module.exports;
}
const ui = load('src/pages/forecasting/forecastingUi.ts', { '../../api/apiClient': { ApiError } });
const css = new Proxy({}, { get: (_, key) => key === '__esModule' ? false : String(key) });
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
function nodes(tree) {
  const found = []; const visit = node => { if (Array.isArray(node)) return node.forEach(visit); if (!node || typeof node !== 'object') return; found.push(node); node.children?.forEach(visit); };
  visit(tree); return found;
}
function text(tree) { if (Array.isArray(tree)) return tree.map(text).join(' '); if (!tree || typeof tree !== 'object') return String(tree ?? ''); return text(tree.children ?? []); }
const asset = {
  symbol: 'AAPL', horizon_days: 30, expected_return_30d: -0.03, forecast_realized_volatility_30d: 0.08,
  return_prediction_interval: { lower: -0.15, upper: 0.12, coverage: 0.80 },
  volatility_prediction_interval: { lower: 0.04, upper: 0.18, coverage: 0.80 },
  forecast_origin_date: '2026-10-06', market_data_as_of: '2026-10-06', market_data_age_days: 1,
  artifact_version: 'forecast-v1-20260917', return_model_id: 'historical_average', volatility_model_id: 'volatility_linear_regression_v1',
  limitations: ['Forecasts are probabilistic estimates, not guarantees of future performance.'],
};
const portfolio = {
  portfolio_id: 'p', portfolio_name: 'Example', baseline_kind: 'current', horizon_days: 30, expected_return_30d: 0.025,
  forecast_realized_volatility_30d: 0.06, market_data_as_of: '2026-10-05', correlation_as_of_date: '2026-10-05',
  correlation_observation_count: 120, artifact_version: asset.artifact_version,
  components: [
    { ...asset, current_weight: 0.4, forecast_volatility_contribution: -0.012, forecast_volatility_contribution_share: -0.2 },
    { ...asset, symbol: 'MSFT', forecast_origin_date: '2026-10-05', current_weight: 0.6, forecast_volatility_contribution: 0.072, forecast_volatility_contribution_share: 1.2 },
  ], limitations: ['No calibrated portfolio prediction interval is provided.'],
};
function weeklyAsset(days = 7, symbol = 'AAPL') {
  const { expected_return_30d, forecast_realized_volatility_30d, ...rest } = asset;
  return { ...rest, symbol, horizon_days: days, horizon_unit: 'calendar_days', expected_return: -.011,
    forecast_realized_volatility: .027, artifact_version: 'forecast-weekly-v1-20260917', experimental: true,
    predictive_quality_approved: false, quality_status: 'experimental_educational_not_predictive_quality_approved',
    return_warning_codes: ['final_interval_coverage_below_nominal'], volatility_warning_codes: ['arima_fit_convergence_warning'] };
}
function weeklyPortfolio(days = 7) {
  const { expected_return_30d, forecast_realized_volatility_30d, ...rest } = portfolio;
  const { symbol, return_prediction_interval, volatility_prediction_interval, forecast_origin_date, market_data_age_days,
    return_model_id, volatility_model_id, return_warning_codes, volatility_warning_codes, ...common } = weeklyAsset(days);
  return { ...rest, ...common, components: portfolio.components.map(item => ({ ...item, ...weeklyAsset(days, item.symbol) })) };
}
function mountHook(options = {}) {
  const h = harness(), calls = [], timers = new Map();
  let account = 'a', scope = 'asset', selection = 'AAPL', horizon = options.horizon ?? 30, compare = options.compare ?? false,
    operation = options.operation ?? (async (kind, id, days = 30) => days === 30
      ? kind === 'asset' ? { ...asset, symbol: id } : { ...portfolio, portfolio_id: id }
      : kind === 'asset' ? weeklyAsset(days, id) : { ...weeklyPortfolio(days), portfolio_id: id });
  const auth = { useAuth: () => ({ status: account ? 'authenticated' : 'unauthenticated', user: account ? { id: account } : null }) };
  const api = { getAssetOutlook: (id, opts) => { calls.push(['asset', id, opts, 30]); return operation('asset', id, 30); }, getPortfolioOutlook: (id, opts) => { calls.push(['portfolio', id, opts, 30]); return operation('portfolio', id, 30); },
    getWeeklyAssetOutlook: (id, days, opts) => { calls.push(['asset', id, opts, days]); return operation('asset', id, days); },
    getWeeklyPortfolioOutlook: (id, days, opts) => { calls.push(['portfolio', id, opts, days]); return operation('portfolio', id, days); } };
  const { useForecasting } = load('src/pages/forecasting/useForecasting.ts', { react: h.react, '../../auth/useAuth': auth, '../../api/forecastingApi': api, './forecastingUi': ui },
    { setTimeout: (fn, delay) => { assert.equal(delay, 60000); const key = Symbol(); timers.set(key, fn); return key; }, clearTimeout: key => timers.delete(key) });
  h.mount(() => useForecasting(scope, selection, horizon, compare));
  return { h, calls, timers, auth, useForecasting, setOperation(value) { operation = value; },
    select(kind, id) { scope = kind; selection = id; h.render(); }, account(value) { account = value; h.render(); },
    horizon(value) { horizon = value; h.render(); }, compare(value) { compare = value; h.render(); } };
}
test('forecast API uses authenticated read-only endpoints, encoded IDs, no horizon/weights/provider requests', async () => {
  const calls = [], signal = new AbortController().signal;
  const api = load('src/api/forecastingApi.ts', { './apiClient': { apiRequest: async (...args) => { calls.push(args); return asset; } } });
  await api.getAssetOutlook('BTC-USD', { token: 'test', signal }); await api.getPortfolioOutlook('p/id');
  assert.equal(calls[0][0], '/api/forecasting/assets/BTC-USD/outlook'); assert.equal(calls[0][1].token, 'test');
  assert.equal(calls[0][1].signal, signal); assert.equal(calls[1][0], '/api/forecasting/portfolios/p%2Fid/outlook');
  assert.equal(calls[0][1].body, undefined); assert.equal(calls[0][1].method, undefined);
});
test('V1 displays backend values without generating weekly estimates or portfolio intervals', () => {
  assert.deepEqual(plain(ui.forecastHorizons), [7, 14, 21, 30]);
  assert.deepEqual(plain(ui.forecastPoints(asset, 'return')), [{ horizonDays: 30, estimate: -0.03, interval: asset.return_prediction_interval }]);
  assert.equal(ui.forecastPoints(portfolio, 'return')[0].interval, undefined);
  assert.equal(ui.forecastPoints(asset, 'volatility')[0].estimate, 0.08);
  assert.equal(ui.forecastPercent(-0.03, true), '-3.00%'); assert.equal(ui.forecastPercent(1.2, true), '+120.00%');
  assert.equal(ui.forecastPercent(NaN), 'N/A');
});
test('response validation rejects malformed/mismatched contracts, while preserving signed contributions', () => {
  assert.equal(ui.validOutlookResponse(asset, 'asset', 'AAPL'), true);
  for (const result of [null, {}, { ...asset, symbol: 'MSFT' }, { ...asset, horizon_days: 7 }, { ...asset, expected_return_30d: NaN }, { ...asset, volatility_prediction_interval: { lower: -1, upper: 0, coverage: .8 } }]) assert.ok(!ui.validOutlookResponse(result, 'asset', 'AAPL'));
  for (const kind of ['current', 'planned', 'legacy']) assert.equal(ui.validOutlookResponse({ ...portfolio, baseline_kind: kind }, 'portfolio', 'p'), true);
  assert.ok(!ui.validOutlookResponse({ ...portfolio, components: undefined }, 'portfolio', 'p'));
  assert.ok(!ui.validOutlookResponse({ ...portfolio, components: [] }, 'portfolio', 'p'));
});
test('forecast error wording sanitizes exceptions and distinguishes stale/history/holding failures', () => {
  assert.match(ui.forecastErrorMessage(new ApiError(503, 'Forecast unavailable because current market data is stale.'), 'asset'), /too old/);
  assert.match(ui.forecastErrorMessage(new ApiError(503, 'Forecast unavailable because market history is insufficient.'), 'asset'), /not enough/);
  assert.match(ui.forecastErrorMessage(new ApiError(409), 'portfolio'), /holding state/);
  assert.match(ui.forecastErrorMessage(new ApiError(404), 'portfolio'), /unavailable/);
  assert.match(ui.forecastErrorMessage(new ApiError(401), 'asset'), /session/);
  for (const error of [new ApiError(503, 'postgres secret'), new ApiError(500, 'private path'), Error('secret')]) assert.doesNotMatch(ui.forecastErrorMessage(error, 'asset'), /secret|postgres|private/);
});
test('forecast loader uses selected endpoints, refreshes without saving and suppresses late selection completions', async () => {
  const late = deferred(), c = mountHook({ operation: () => late.promise });
  c.setOperation(async (_, id) => ({ ...asset, symbol: id })); c.select('asset', 'MSFT'); await c.h.settle();
  assert.equal(c.calls[0][2].signal.aborted, true); assert.equal(c.h.value.result.symbol, 'MSFT');
  late.resolve(asset); await c.h.settle(); assert.equal(c.h.value.result.symbol, 'MSFT');
  c.h.value.refresh(); await c.h.settle(); assert.equal(c.calls.length, 3);
  c.setOperation(async (_, id) => ({ ...portfolio, portfolio_id: id, baseline_kind: 'planned' }));
  c.select('portfolio', 'p'); await c.h.settle(); assert.equal(c.h.value.result.baseline_kind, 'planned');
  assert.equal(c.calls.at(-1)[0], 'portfolio'); c.h.unmount(); assert.equal(c.timers.size, 0);
});
test('forecast loader discards old account data, cancels on unmount, handles failure and timeout retries', async () => {
  const c = mountHook(); await c.h.settle();
  const late = deferred(); c.setOperation(() => late.promise); c.account('b'); await c.h.settle();
  assert.equal(c.h.value.result, null);
  [...c.timers.values()][0](); await c.h.settle(); assert.equal(c.calls.at(-1)[2].signal.aborted, true);
  assert.ok(c.h.value.error); c.setOperation(async () => asset); c.h.value.refresh(); await c.h.settle();
  late.resolve({ ...asset, symbol: 'wrong' }); await c.h.settle(); assert.equal(c.h.value.result.symbol, 'AAPL');
  c.setOperation(async () => { throw new ApiError(503); }); c.h.value.refresh(); await c.h.settle();
  assert.equal(c.h.value.result, null); assert.ok(c.h.value.error);
  const pending = deferred(); c.setOperation(() => pending.promise); c.h.value.refresh(); await c.h.settle();
  c.h.unmount(); assert.equal(c.calls.at(-1)[2].signal.aborted, true); assert.equal(c.timers.size, 0);
  pending.resolve(asset); await c.h.settle(); assert.equal(c.h.value.result, null);
});
test('unauthenticated/empty selections never request a forecast', async () => {
  const c = mountHook(); await c.h.settle(); const count = c.calls.length;
  c.select('portfolio', ''); await c.h.settle(); assert.equal(c.h.value.loading, false); assert.equal(c.calls.length, count);
  c.account(null); c.select('asset', 'AAPL'); await c.h.settle(); assert.equal(c.calls.length, count); assert.equal(c.h.value.result, null); c.h.unmount();
});
test('forecast chart stays compact on wide screens without distorting axes or changing narrow-screen scrolling', () => {
  const stylesheet = fs.readFileSync(path.join(root, 'src/pages/forecasting/Forecasting.module.css'), 'utf8');
  const chart = stylesheet.match(/\.chart\s*\{([^}]+)\}/)[1];
  assert.match(chart, /width:\s*100%/);
  assert.match(chart, /max-width:\s*1100px/);
  assert.match(chart, /min-width:\s*530px/);
  assert.match(chart, /height:\s*auto/);
  assert.match(chart, /margin-inline:\s*auto/);
  assert.match(stylesheet, /\.chartScroll,\s*\.tableScroll\s*\{[^}]*overflow:\s*auto/);
});

test('chart has labeled axes, a single actual point, asset range bars and no invented V1 line', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { OutlookChart } = load('src/pages/forecasting/components/OutlookChart.tsx', { '../forecastingUi': ui, '../Forecasting.module.css': css }, { React: react });
  const tree = OutlookChart({ points: ui.forecastPoints(asset, 'return'), metric: 'return' });
  const elements = nodes(tree); assert.equal(elements.filter(node => node.type === 'circle').length, 1);
  assert.equal(elements.filter(node => node.type === 'polyline').length, 0);
  assert.ok(elements.some(node => node.type === 'g' && node.props.className === 'interval'));
  assert.match(text(tree), /Calendar days ahead/); assert.match(text(tree), /not a daily price path/);
  const portfolioTree = OutlookChart({ points: ui.forecastPoints(portfolio, 'volatility'), metric: 'volatility' });
  assert.ok(!nodes(portfolioTree).some(node => node.props.className === 'interval'));
  assert.match(text(portfolioTree), /non-annualized/);
});
test('asset and portfolio results preserve backend ranges, planned wording, signed bars and actual model metadata', () => {
  const h = harness(), destinations = [];
  const { ForecastingResults } = load('src/pages/forecasting/components/ForecastingResults.tsx', {
    react: h.react, '../../../app/routes': { go: value => destinations.push(value) }, '../../../components/ui/Card': { Card: 'Card' },
    '../forecastingUi': ui, './OutlookChart': { OutlookChart: 'OutlookChart' }, '../Forecasting.module.css': css,
  }, { React: h.react });
  let result = { ...portfolio, baseline_kind: 'planned' }; h.mount(() => ForecastingResults({ result }));
  assert.match(text(h.value), /hypothetical/); assert.doesNotMatch(text(h.value), /Low risk|High risk|80% prediction range/);
  const bars = nodes(h.value).filter(node => ['negativeBar', 'positiveBar'].includes(node.props.className));
  assert.equal(bars.length, 2); assert.ok(bars.every(node => parseFloat(node.props.style.width) >= 0 && parseFloat(node.props.style.width) <= 100));
  assert.match(text(h.value), /-20.00%/); assert.match(text(h.value), /volatility_linear_regression_v1/);
  nodes(h.value).find(node => node.type === 'button' && /AAPL\s+↗/.test(text(node))).props.onClick(); assert.equal(destinations[0], 'forecasting/asset/AAPL');
  result = asset; h.render(); assert.match(text(h.value), /-15.00%\s+to\s+12.00%/);
  assert.equal(nodes(h.value).find(node => node.type === 'OutlookChart').props.points[0].estimate, -0.03);
  nodes(h.value).find(node => node.type === 'button' && text(node) === 'Volatility').props.onClick(); h.render();
  assert.equal(nodes(h.value).find(node => node.type === 'OutlookChart').props.points[0].estimate, 0.08);
});
test('page supports no-portfolio asset access, retained search selections, weekly horizons and optional comparison', async () => {
  const h = harness(); let loaded = { result: null, loading: false, error: null, refresh: () => refreshed++ }, refreshed = 0;
  const selections = [], destinations = [];
  const { ForecastingPage } = load('src/pages/forecasting/ForecastingPage.tsx', {
    react: h.react, '../../auth/useAuth': { useAuth: () => ({ status: 'authenticated', user: { id: 'a' } }) },
    '../../api/portfoliosApi': { listPortfolios: async () => ({ portfolios: [] }) }, '../../app/routes': { go: value => destinations.push(value) },
    '../../components/ui/Card': { Card: 'Card' }, '../../components/ui/AuraSelect': { AuraSelect: 'AuraSelect' },
    '../../components/ui/ApiErrorState': { InlineErrorCard: 'InlineErrorCard' },
    '../portfolios/supportedAssetSymbols': { supportedAssets: [{ symbol: 'AAPL', name: 'Apple' }, { symbol: 'MSFT', name: 'Microsoft' }] },
    './forecastingUi': ui, './useForecasting': { useForecasting: (scope, value, horizon, compare) => { selections.push([scope, value, horizon, compare]); return loaded; } },
    './components/ForecastingResults': { ForecastingResults: 'ForecastingResults' }, './Forecasting.module.css': css,
    './components/ForecastHorizonComparison': { ForecastHorizonComparison: 'ForecastHorizonComparison' },
  }, { React: h.react });
  h.mount(() => ForecastingPage({})); await h.settle();
  assert.match(text(h.value), /No portfolios yet/);
  const horizonGroup = nodes(h.value).find(node => node.props['aria-label'] === 'Forecast horizon');
  const horizons = nodes(horizonGroup).filter(node => node.type === 'button');
  assert.ok(horizons.every(node => !node.props.disabled));
  assert.deepEqual(horizons.map(node => node.props['aria-pressed']), [false, false, false, true]);
  nodes(h.value).find(node => node.type === 'button' && text(node) === 'Explore Assets').props.onClick(); await h.settle();
  assert.deepEqual(selections.at(-1), ['asset', 'AAPL', 30, false]);
  nodes(h.value).find(node => node.type === 'input' && node.props.type !== 'checkbox').props.onChange({ target: { value: 'nothing' } }); await h.settle();
  assert.match(text(h.value), /No matching assets/);
  const picker = nodes(h.value).find(node => node.type === 'AuraSelect'); assert.equal(picker.props.value, 'AAPL'); assert.equal(picker.props.options[0].value, 'AAPL');
  nodes(h.value).find(node => node.type === 'button' && text(node) === 'Refresh Outlook').props.onClick(); assert.equal(refreshed, 1);
  loaded = { ...loaded, result: asset }; h.render(); assert.equal(nodes(h.value).find(node => node.type === 'ForecastingResults').props.result, asset);
  horizons[0].props.onClick(); await h.settle(); assert.deepEqual(selections.at(-1), ['asset', 'AAPL', 7, false]);
  assert.match(text(h.value), /Experimental Weekly V1/);
  nodes(h.value).find(node => node.props.type === 'checkbox').props.onChange({ target: { checked: true } }); await h.settle();
  assert.deepEqual(selections.at(-1), ['asset', 'AAPL', 7, true]);
  assert.equal(nodes(h.value).find(node => node.type === 'ForecastingResults').props.showChart, false);
  assert.ok(nodes(h.value).some(node => node.type === 'ForecastHorizonComparison'));
  h.unmount();
});

test('weekly GET adapters encode selections and use actual horizon routes, preserving auth/abort and 30-day APIs', async () => {
  const calls = [], signal = new AbortController().signal;
  const api = load('src/api/forecastingApi.ts', { './apiClient': { apiRequest: async (...args) => { calls.push(args); return weeklyAsset(); } } });
  for (const days of [7, 14, 21]) { await api.getWeeklyAssetOutlook('BTC-USD', days, { token: 'test', signal }); await api.getWeeklyPortfolioOutlook('p/id', days, { signal }); }
  assert.deepEqual(calls.map(call => call[0]), [7, 14, 21].flatMap(days => [`/api/forecasting/assets/BTC-USD/horizons/${days}/outlook`, `/api/forecasting/portfolios/p%2Fid/horizons/${days}/outlook`]));
  assert.ok(calls.every(call => call[1].signal === signal && !call[1].body && !call[1].method));
  assert.equal(calls[0][1].token, 'test');
});

test('weekly contract gates reject wrong horizons, missing quality/warnings, mixed components and 30-day substitutions', () => {
  for (const days of [7, 14, 21]) {
    const result = weeklyAsset(days);
    assert.ok(ui.validOutlookResponse(result, 'asset', 'AAPL', days));
    for (const invalid of [{ ...result, expected_return: undefined, expected_return_30d: .1 }, { ...result, predictive_quality_approved: true },
      { ...result, experimental: false }, { ...result, quality_status: 'approved' }, { ...result, horizon_unit: 'trading_days' },
      { ...result, return_warning_codes: undefined }, { ...result, volatility_warning_codes: [42] }, { ...result, artifact_version: 'forecast-v1-20260917' },
      { ...result, horizon_days: 30 }, { ...result, forecast_realized_volatility: Infinity }, { ...result, market_data_age_days: 5 }]) {
      assert.ok(!ui.validOutlookResponse(invalid, 'asset', 'AAPL', days));
    }
    assert.ok(!ui.validOutlookResponse(result, 'asset', 'AAPL', 30));
    const p = weeklyPortfolio(days);
    assert.ok(ui.validOutlookResponse(p, 'portfolio', 'p', days));
    assert.ok(!ui.validOutlookResponse({ ...p, components: [{ ...p.components[0], horizon_days: 30 }] }, 'portfolio', 'p', days));
    assert.ok(!ui.validOutlookResponse({ ...p, components: [{ ...p.components[0], artifact_version: 'other' }] }, 'portfolio', 'p', days));
    assert.equal(ui.forecastPoints(p, 'volatility')[0].interval, undefined);
    assert.equal(ui.forecastPoints(result, 'return')[0].estimate, result.expected_return);
    assert.equal(ui.forecastPoints(result, 'volatility')[0].estimate, result.forecast_realized_volatility);
  }
});

test('weekly selection races clear old results, cancel requests and never fallback to 30 days', async () => {
  const late = deferred(), c = mountHook({ operation: () => late.promise });
  c.setOperation(async (_, id, days) => weeklyAsset(days, id)); c.horizon(7); await c.h.settle();
  assert.equal(c.calls[0][2].signal.aborted, true); assert.equal(c.h.value.result.horizon_days, 7);
  late.resolve(asset); await c.h.settle(); assert.equal(c.h.value.result.horizon_days, 7);
  c.setOperation(async () => { throw new ApiError(503); }); c.horizon(14); await c.h.settle();
  assert.equal(c.h.value.result, null); assert.ok(c.h.value.error); assert.deepEqual(plain(c.h.value.unavailableHorizons), [14]);
  assert.deepEqual(c.calls.map(call => call[3]), [30, 7, 14]); c.h.unmount();
});

test('comparison tolerates a failed horizon independently, retains actual values and aborts all work on account changes', async () => {
  const c = mountHook({ compare: true, operation: async (_, id, days) => {
    if (days === 14) throw new ApiError(503); return days === 30 ? asset : weeklyAsset(days, id);
  } }); await c.h.settle();
  assert.equal(c.h.value.result.horizon_days, 30); assert.equal(c.h.value.error, null);
  assert.deepEqual(plain(c.h.value.outlooks.map(r => r.horizon_days)), [7, 21, 30]);
  assert.deepEqual(plain(c.h.value.unavailableHorizons), [14]); assert.equal(c.h.value.comparisonLoading, false);
  const points = ui.comparisonPoints(c.h.value.outlooks, 'return');
  assert.equal(points.length, 3); assert.equal(points[0].estimate, -.011); assert.equal(points[2].estimate, -.03);
  assert.equal(points[0].experimental, true); assert.equal(points[2].experimental, false);
  const callCount = c.calls.length; c.horizon(7); await c.h.settle();
  assert.equal(c.h.value.result.horizon_days, 7); assert.equal(c.calls.length, callCount);
  c.horizon(14); await c.h.settle(); assert.equal(c.h.value.result, null); assert.ok(c.h.value.error);
  assert.equal(c.calls.length, callCount); // presentation selection must not repeat all four GETs
  const pending = deferred(); c.setOperation(() => pending.promise); c.account('other'); await c.h.settle();
  assert.equal(c.h.value.result, null); assert.deepEqual(plain(c.h.value.outlooks), []);
  assert.ok(c.calls.slice(0, 4).every(call => call[2].signal.aborted)); c.h.unmount();
  assert.ok(c.calls.every(call => call[2].signal.aborted)); assert.equal(c.timers.size, 0);
});

test('comparison keeps weekly estimates when selected 30-day request fails and isolates per-horizon timeouts', async () => {
  const late = deferred(), c = mountHook({ compare: true, operation: async (_, id, days) => {
    if (days === 30) throw new ApiError(503); if (days === 14) return late.promise; return weeklyAsset(days, id);
  } }); await c.h.settle();
  assert.ok(c.h.value.error); assert.equal(c.h.value.result, null); assert.deepEqual(plain(c.h.value.outlooks.map(r => r.horizon_days)), [7, 21]);
  assert.equal(c.h.value.comparisonLoading, true); [...c.timers.values()][0](); await c.h.settle();
  assert.equal(c.h.value.comparisonLoading, false); assert.deepEqual(plain(c.h.value.unavailableHorizons), [14, 30]);
  late.resolve(weeklyAsset(14)); await c.h.settle(); assert.equal(c.h.value.outlooks.length, 2); c.h.unmount();
});

test('comparison lines do not bridge missing horizons or different origins and never add portfolio intervals', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { OutlookChart } = load('src/pages/forecasting/components/OutlookChart.tsx', { '../forecastingUi': ui, '../Forecasting.module.css': css }, { React: react });
  let points = ui.comparisonPoints([weeklyPortfolio(7), weeklyPortfolio(21), portfolio], 'return');
  let tree = OutlookChart({ points, metric: 'return' });
  assert.equal(nodes(tree).filter(node => node.type === 'circle').length, 3);
  assert.equal(nodes(tree).filter(node => node.type === 'polyline').length, 0); // gap then different date
  assert.ok(!nodes(tree).some(node => node.props.className === 'interval'));
  points = ui.comparisonPoints([weeklyAsset(7), weeklyAsset(14), weeklyAsset(21), asset], 'return');
  tree = OutlookChart({ points, metric: 'return' });
  assert.equal(nodes(tree).filter(node => node.type === 'circle').length, 4);
  assert.equal(nodes(tree).filter(node => node.type === 'polyline').length, 3);
  assert.match(text(tree), /not guaranteed achieved coverage/); assert.match(text(tree), /not a daily price path/);
});

test('weekly cards and comparison display truthful horizon labels, experimental status and target-specific warnings', () => {
  assert.equal(ui.forecastWarnings([{ ...weeklyAsset(), return_warning_codes: ['constructor'] }])[0].message,
    'The backend retained an additional model-quality warning.');
  const h = harness();
  const { ForecastingResults } = load('src/pages/forecasting/components/ForecastingResults.tsx', {
    react: h.react, '../../../app/routes': { go: () => {} }, '../../../components/ui/Card': { Card: 'Card' },
    '../forecastingUi': ui, './OutlookChart': { OutlookChart: 'OutlookChart' }, '../Forecasting.module.css': css,
  }, { React: h.react });
  h.mount(() => ForecastingResults({ result: weeklyPortfolio(21) }));
  assert.match(text(h.value), /Expected\s+21\s*-Day Return/); assert.doesNotMatch(text(h.value), /30-day return|30-Day Return/);
  assert.match(text(h.value), /Not approved as reliable predictions/); assert.match(text(h.value), /21-day AAPL return/);
  assert.match(text(h.value), /below the nominal 80%/); assert.match(text(h.value), /fit-convergence/);
  assert.ok(nodes(h.value).some(node => node.type === 'i' && node.props.className === 'negativeBar'));
  const c = harness();
  const { ForecastHorizonComparison } = load('src/pages/forecasting/components/ForecastHorizonComparison.tsx', {
    react: c.react, '../../../components/ui/Card': { Card: 'Card' }, '../forecastingUi': ui,
    './OutlookChart': { OutlookChart: 'OutlookChart' }, '../Forecasting.module.css': css,
  }, { React: c.react });
  c.mount(() => ForecastHorizonComparison({ results: [weeklyAsset(7), asset], loading: false, unavailable: [14, 21] }));
  assert.match(text(c.value), /Unavailable/); assert.match(text(c.value), /Missing points are not estimated/);
  assert.match(text(c.value), /7-day AAPL volatility/); assert.match(text(c.value), /2026-10-06/);
  assert.equal(nodes(c.value).find(node => node.type === 'OutlookChart').props.points.length, 2);
  nodes(c.value).find(node => node.type === 'button' && text(node) === 'Volatility').props.onClick(); c.render();
  assert.equal(nodes(c.value).find(node => node.type === 'OutlookChart').props.points[0].estimate, .027);
});
test('forecast routes/entry points are protected, Analytics stays active, history and mobile remain unmodified', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  assert.match(read('src/app/App.tsx'), /case 'forecasting'/);
  assert.match(read('src/app/App.tsx'), /<ProtectedRoute>/);
  assert.match(read('src/components/navigation/TopNavigation.tsx'), /key === 'analytics' && route.page === 'forecasting'/);
  assert.match(read('src/pages/analytics/AnalyticsPage.tsx'), /Forecast Outlook/);
  for (const file of ['src/pages/portfolios/PortfolioDetailView.tsx', 'src/pages/dashboard/components/PortfolioAnalysisCard.tsx']) assert.match(read(file), /forecasting\/portfolio/);
  assert.match(read('src/pages/watchlist/components/WatchlistTable.tsx'), /forecasting\/asset/);
  assert.doesNotMatch(read('src/pages/forecasting/ForecastingPage.tsx'), /createPortfolioReport|createSimulation|localStorage|sessionStorage|agent\/explain/);
  const walk = dir => fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => entry.isDirectory() ? walk(path.join(dir, entry.name)) : [path.join(dir, entry.name)]);
  for (const file of walk(path.join(root, 'src/pages')).filter(file => /(?:reports|simulations)[\\/]/.test(file) && /tsx?$/.test(file))) assert.doesNotMatch(fs.readFileSync(file, 'utf8'), /getAssetOutlook|getPortfolioOutlook|useForecasting/, file);
});

test('App opens authenticated scope/selection deep links and rejects unsupported forecast routes', () => {
  let route = { page: 'forecasting' };
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }), useEffect: () => {} };
  const mocks = { react, '../auth/useAuth': { useAuth: () => ({ status: 'authenticated', user: { id: 'account-a' } }) },
    '../hooks/useHashRoute': { useHashRoute: () => route }, './routes': { go: () => {} } };
  const source = fs.readFileSync(path.join(root, 'src/app/App.tsx'), 'utf8');
  for (const match of source.matchAll(/import \{ ([A-Z]\w*) \} from '([^']+)'/g)) mocks[match[2]] = { [match[1]]: match[1] };
  const App = load('src/app/App.tsx', mocks, { React: react }).default;
  const content = () => App().children[0].children[0];
  assert.equal(content().type, 'ForecastingPage'); assert.equal(content().props.scope, 'portfolio');
  route = { page: 'forecasting', id: 'portfolio', reportId: 'p' };
  assert.equal(content().props.selection, 'p'); assert.match(content().props.key, /account-a/);
  route = { page: 'forecasting', id: 'asset', reportId: 'BTC-USD' };
  assert.equal(content().props.scope, 'asset'); assert.equal(content().props.selection, 'BTC-USD');
  route = { page: 'forecasting', id: 'unsupported' }; assert.equal(content().type, 'NotFoundPage');
});

test('forecasting keeps Analytics active in the existing top navigation', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { TopNavigation } = load('src/components/navigation/TopNavigation.tsx', {
    '../../app/navigation': { navItems: [['dashboard', 'dashboard', 'Dashboard'], ['analytics', 'analytics', 'Analytics'], ['reports', 'reports', 'Reports']] },
    '../../app/routes': { go: () => {} }, '../ui/Icon': { Icon: 'Icon' }, './ProfileMenu': { ProfileMenu: 'ProfileMenu' },
    '../../notifications/useNotifications': { useNotificationBadge: () => 0 },
  }, { React: react });
  const tree = TopNavigation({ route: { page: 'forecasting' } });
  const active = nodes(tree).filter(node => node.props['aria-current'] === 'page');
  assert.equal(active.length, 1); assert.match(text(active[0]), /Analytics/);
});
