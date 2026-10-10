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
const money = load('src/forecasting/forecastingMoney.ts');
const ui = load('src/forecasting/forecastingUi.ts', { '../api/apiClient': { ApiError }, './forecastingMoney': money });
const privacy = { usePortfolioPrivacy: () => ({ hideValues: false }), usePrivateValue: () => value => value };
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
function moneyProjection(amount = '10000', change = '250', ending = '10250', price = null) {
  return { currency: 'USD', baseline_source: 'current_market_value', baseline_amount: amount,
    expected_change_amount: change, estimated_ending_value: ending, hypothetical: false, assumes_unchanged_fx: false,
    valuation_requested_date: '2026-10-07', oldest_price_as_of: price ?? '2026-10-05', newest_price_as_of: price ?? '2026-10-06',
    limitations: ['Monetary estimates are not guaranteed balances.', 'No calibrated portfolio monetary prediction interval is provided.'] };
}
const portfolio = {
  portfolio_id: 'p', portfolio_name: 'Example', baseline_kind: 'current', horizon_days: 30, expected_return_30d: 0.025,
  forecast_realized_volatility_30d: 0.06, market_data_as_of: '2026-10-05', correlation_as_of_date: '2026-10-05',
  correlation_observation_count: 120, artifact_version: asset.artifact_version,
  monetary_projection: moneyProjection(),
  components: [
    { ...asset, current_weight: 0.4, forecast_volatility_contribution: -0.012, forecast_volatility_contribution_share: -0.2,
      monetary_projection: moneyProjection('4000', '-120', '3880', '2026-10-06') },
    { ...asset, symbol: 'MSFT', expected_return_30d: .06166666666666667, forecast_origin_date: '2026-10-05', current_weight: 0.6, forecast_volatility_contribution: 0.072, forecast_volatility_contribution_share: 1.2,
      monetary_projection: moneyProjection('6000', '370', '6370', '2026-10-05') },
  ], limitations: ['No calibrated portfolio prediction interval is provided.'],
};
function portfolioMode(source, kind, currency = 'USD') {
  const convert = value => kind === 'legacy' ? null : kind === 'current' ? value : { ...value,
    currency, baseline_source: 'planned_investment', hypothetical: true, assumes_unchanged_fx: currency === 'THB',
    valuation_requested_date: null, oldest_price_as_of: null, newest_price_as_of: null };
  return { ...source, baseline_kind: kind, monetary_projection: convert(source.monetary_projection),
    components: source.components.map(item => ({ ...item, monetary_projection: convert(item.monetary_projection) })) };
}
function weekly(value, days) {
  const { expected_return_30d, forecast_realized_volatility_30d, components, ...rest } = value;
  const result = {
    ...rest, horizon_days: days, horizon_unit: 'calendar_days',
    expected_return: expected_return_30d, forecast_realized_volatility: forecast_realized_volatility_30d,
    artifact_version: 'forecast-weekly-v1-20260917', experimental: true, predictive_quality_approved: false,
    quality_status: 'experimental_educational_not_predictive_quality_approved',
  };
  if (components) result.components = components.map(item => weekly(item, days));
  else Object.assign(result, { market_data_as_of: result.forecast_origin_date, return_warning_codes: [], volatility_warning_codes: [] });
  return result;
}

function mountHook(options = {}) {
  const h = harness(), calls = [], timers = new Map();
  let focused = true;
  let account = 'a', scope = 'asset', selection = 'AAPL', horizon = options.horizon ?? 30, compare = options.compare ?? false;
  let operation = options.operation ?? (async (kind, id, days) => {
    const value = kind === 'asset' ? { ...asset, symbol: id } : { ...portfolio, portfolio_id: id };
    return days === 30 ? value : weekly(value, days);
  });
  const auth = { useAuth: () => ({ status: account ? 'authenticated' : 'unauthenticated', user: account ? { id: account } : null }) };
  const request = (kind, id, opts, days) => { calls.push([kind, id, opts, days]); return operation(kind, id, days); };
  const api = {
    getAssetOutlook: (id, opts) => request('asset', id, opts, 30),
    getPortfolioOutlook: (id, opts) => request('portfolio', id, opts, 30),
    getWeeklyAssetOutlook: (id, days, opts) => request('asset', id, opts, days),
    getWeeklyPortfolioOutlook: (id, days, opts) => request('portfolio', id, opts, days),
  };
  const { useForecasting } = load('src/forecasting/useForecasting.ts', { react: h.react, '@react-navigation/native': { useFocusEffect: cb => h.react.useEffect(() => focused ? cb() : undefined, [cb, focused]) }, '../auth/useAuth': auth, '../api/forecastingApi': api, './forecastingUi': ui },
    { setTimeout: (fn, delay) => { assert.equal(delay, 60000); const key = Symbol(); timers.set(key, fn); return key; }, clearTimeout: key => timers.delete(key) });
  h.mount(() => useForecasting(scope, selection, horizon, compare));
  return { h, calls, timers, auth, useForecasting, setOperation(value) { operation = value; },
    focus(value) { focused = value; h.render(); },
    horizon(value) { horizon = value; h.render(); }, compare(value) { compare = value; h.render(); },
    select(kind, id) { scope = kind; selection = id; h.render(); }, account(value) { account = value; h.render(); } };
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
  for (const kind of ['current', 'planned', 'legacy']) assert.equal(ui.validOutlookResponse(portfolioMode(portfolio, kind), 'portfolio', 'p'), true);
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
  c.setOperation(async (_, id) => ({ ...portfolioMode(portfolio, 'planned'), portfolio_id: id }));
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

const native = { View: 'View', Text: 'Text', Pressable: 'Pressable', ScrollView: 'Scroll', RefreshControl: 'RefreshControl', TextInput: 'TextInput' };
const styles = new Proxy({}, { get: (_, name) => String(name) });
test('focus loss aborts pending requests and focus return reloads the current selection', async () => {
  const late = deferred(), c = mountHook({ operation: () => late.promise });
  c.focus(false); await c.h.settle(); assert.equal(c.calls[0][2].signal.aborted, true);
  late.resolve(asset); await c.h.settle(); assert.equal(c.h.value.result, null);
  c.setOperation(async () => asset); c.focus(true); await c.h.settle();
  assert.equal(c.calls.length, 2); assert.equal(c.h.value.result.symbol, 'AAPL'); c.h.unmount();
});
test('native chart labels axes, renders only actual estimates, and has asset-only ranges', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { OutlookChart } = load('src/components/forecasting/OutlookChart.tsx', {
    react, 'react-native': native, 'react-native-svg': { __esModule: true, default: 'Svg', Circle: 'Circle', G: 'G', Line: 'Line', Polyline: 'Polyline', Text: 'SvgText' },
    '../../theme/theme': { colors: {} }, '../../forecasting/forecastingUi': ui,
    '../../forecasting/forecastingStyles': { forecastingStyles: styles },
  });
  const tree = OutlookChart({ points: ui.forecastPoints(asset, 'return'), metric: 'return' });
  assert.equal(nodes(tree).filter(n => n.type === 'Circle').length, 1);
  assert.equal(nodes(tree).filter(n => n.type === 'Polyline').length, 0);
  assert.equal(nodes(tree).filter(n => n.type === 'Line' && n.props.strokeWidth === 2).length, 3);
  assert.match(text(tree), /Calendar days ahead/);
  assert.match(nodes(tree).find(n => n.props.accessibilityRole === 'image').props.accessibilityLabel, /-3.00%.*-15.00%.*12.00%/);
  const port = OutlookChart({ points: ui.forecastPoints(portfolio, 'volatility'), metric: 'volatility' });
  assert.equal(nodes(port).filter(n => n.type === 'Line' && n.props.strokeWidth === 2).length, 0);
  assert.match(text(port), /non-annualized/);
  const comparison = OutlookChart({ points: ui.comparisonPoints([weekly(asset, 7), asset], 'return'), metric: 'return' });
  for (const chart of [tree, port, comparison]) {
    const ticks = nodes(chart).filter(node => node.type === 'SvgText' && node.props.y === 191);
    // One string avoids separate centered native SVG spans for number/unit.
    assert.deepEqual(ticks.map(node => node.children), [['7 days'], ['14 days'], ['21 days'], ['30 days']]);
    assert.ok(ticks.every(node => node.props.textAnchor === 'middle'));
    assert.ok(ticks.every((node, index) => index === 0 || node.props.x > ticks[index - 1].props.x));
  }
});
test('native results retain planned baseline, negative shares, ranges, metadata and asset drill-down', async () => {
  const h = harness(), destinations = [];
  const { ForecastingResults } = load('src/components/forecasting/ForecastingResults.tsx', {
    react: h.react, 'react-native': native, '../ui/Card': { Card: 'Card' }, '../ui/Button': { Button: 'Button' },
    './OutlookChart': { OutlookChart: 'Chart' }, '../../forecasting/forecastingUi': ui,
    './ForecastHorizonComparison': { ForecastQualityNotice: 'Quality' },
    '../../privacy/PortfolioPrivacy': privacy,
    '../../forecasting/forecastingStyles': { forecastingStyles: styles },
  });
  let result = portfolioMode(portfolio, 'planned');
  h.mount(() => ForecastingResults({ result, onAsset: value => destinations.push(value) }));
  assert.match(text(h.value), /hypothetical/); assert.match(text(h.value), /-20.00%/);
  assert.doesNotMatch(text(h.value), /Low risk|High risk|80% prediction range/);
  const bars = nodes(h.value).filter(n => Array.isArray(n.props.style) && n.props.style[0] === 'bar');
  assert.equal(bars.length, 2);
  assert.ok(bars.every(n => parseFloat(n.props.style.at(-1).width) >= 0 && parseFloat(n.props.style.at(-1).width) <= 100));
  nodes(h.value).find(n => n.props.accessibilityLabel === 'View AAPL outlook').props.onPress();
  assert.deepEqual(destinations, ['AAPL']);
  nodes(h.value).find(n => n.props.accessibilityLabel === 'Model details and limitations').props.onPress();
  await h.settle();
  // DataRow is intentionally not mounted by this minimal tree harness.
  assert.ok(nodes(h.value).some(n => n.props.value === asset.volatility_model_id));
  result = asset; h.render(); assert.match(text(h.value), /-15.00%\s+to\s+12.00%/);
  nodes(h.value).find(n => n.props.accessibilityLabel === 'Volatility chart').props.onPress();
  await h.settle(); assert.equal(nodes(h.value).find(n => n.type === 'Chart').props.points[0].estimate, 0.08);
  h.unmount();
});
function mountScreen(params = {}, operation = async () => ({ portfolios: [] })) {
  const h = harness(), selections = [], destinations = [], requests = [];
  let refreshed = 0;
  const forecast = { result: null, error: null, loading: false, outlooks: [], comparisonLoading: false, unavailableHorizons: [], refresh: () => refreshed++ };
  const { AccountForecasting } = load('src/screens/forecasting/ForecastingScreen.tsx', {
    react: h.react, '@react-navigation/native': { useFocusEffect: cb => h.react.useEffect(cb, [cb]) },
    'react-native': native, 'react-native-safe-area-context': { SafeAreaView: 'Safe' },
    '../../theme/theme': { colors: {} }, '../../auth/useAuth': { useAuth: () => ({ status: 'authenticated', user: { id: 'a' } }) },
    '../../api/portfoliosApi': { portfoliosApi: { list: operation } },
    '../../components/ui/Button': { Button: 'Button' }, '../../components/ui/Card': { Card: 'Card' },
    '../../components/ui/PageTitle': { PageTitle: 'Title' }, '../../components/ui/ErrorState': { InlineErrorCard: 'ErrorCard' },
    '../../components/simulations/PortfolioSelector': { PortfolioSelector: 'PortfolioSelector' },
    '../../components/forecasting/ForecastingResults': { ForecastingResults: 'Results' },
    '../../components/forecasting/ForecastHorizonComparison': { ForecastHorizonComparison: 'Comparison' },
    '../../forecasting/useForecasting': { useForecasting: (scope, selection, horizon, compare) => { selections.push([scope, selection]); requests.push([scope, selection, horizon, compare]); return forecast; } },
    '../../forecasting/forecastingUi': ui, '../../forecasting/forecastingStyles': { forecastingStyles: styles },
    '../../portfolio/supportedAssetSymbols': { supportedAssets: [{ symbol: 'AAPL', name: 'Apple' }, { symbol: 'MSFT', name: 'Microsoft' }] },
  });
  const navigation = {
    navigate: (...args) => destinations.push(args), push: (...args) => destinations.push(args),
    getState: () => ({ routeNames: ['More', 'Analytics', 'Forecasting'] }),
    getParent: () => ({ navigate: (...args) => destinations.push(args) }),
  };
  h.mount(() => AccountForecasting({ route: { params }, navigation }));
  return { h, selections, forecast, destinations, requests, get refreshed() { return refreshed; } };
}
test('mobile screen offers asset access without portfolios, keeps search selection and enables all horizons', async () => {
  const c = mountScreen(); await c.h.settle();
  assert.match(text(c.h.value), /No portfolios yet/);
  const horizons = nodes(c.h.value).filter(n => /calendar days/.test(n.props.accessibilityLabel ?? ''));
  assert.deepEqual(horizons.map(n => Boolean(n.props.disabled)), [false, false, false, false]);
  assert.deepEqual(horizons.map(n => n.props.accessibilityState.selected), [false, false, false, true]);
  nodes(c.h.value).find(n => n.props.title === 'Explore Assets').props.onPress(); await c.h.settle();
  assert.deepEqual(c.selections.at(-1), ['asset', 'AAPL']);
  nodes(c.h.value).find(n => n.type === 'TextInput').props.onChangeText('nothing'); await c.h.settle();
  assert.match(text(c.h.value), /No matching assets/); assert.deepEqual(c.selections.at(-1), ['asset', 'AAPL']);
  nodes(c.h.value).find(n => n.type === 'Title').props.right.props.onPress();
  assert.equal(c.refreshed, 1); c.h.unmount();
});
test('mobile screen honors entry selection, portfolio selection and asset drill navigation', async () => {
  const c = mountScreen({ portfolioId: 'p' }, async () => ({ portfolios: [{ id: 'p' }, { id: 'other' }] }));
  await c.h.settle(); assert.deepEqual(c.selections.at(-1), ['portfolio', 'p']);
  nodes(c.h.value).find(n => n.type === 'PortfolioSelector').props.onSelect('other'); await c.h.settle();
  assert.deepEqual(c.selections.at(-1), ['portfolio', 'other']);
  c.forecast.result = portfolio; c.h.render();
  nodes(c.h.value).find(n => n.type === 'Results').props.onAsset('MSFT');
  assert.deepEqual(plain(c.destinations[0]), ['Forecasting', { scope: 'asset', symbol: 'MSFT' }]);
  c.h.unmount();
  const a = mountScreen({ scope: 'asset', symbol: ' btc-usd ' }); await a.h.settle();
  assert.deepEqual(a.selections.at(-1), ['asset', 'BTC-USD']); a.h.unmount();
});
test('portfolio list failure does not block standalone asset outlooks and has retry', async () => {
  const c = mountScreen({}, async () => { throw Error('offline'); }); await c.h.settle();
  assert.ok(nodes(c.h.value).some(n => n.type === 'ErrorCard' && n.props.onRetry));
  nodes(c.h.value).find(n => n.props.accessibilityLabel === 'Asset Outlook').props.onPress(); await c.h.settle();
  assert.deepEqual(c.selections.at(-1), ['asset', 'AAPL']); assert.equal(nodes(c.h.value).filter(n => n.type === 'ErrorCard').length, 0); c.h.unmount();
});
test('weekly GET transport preserves 30-day endpoints and forwards cancellation', async () => {
  const calls = [], signal = new AbortController().signal;
  const api = load('src/api/forecastingApi.ts', { './apiClient': { apiRequest: async (...args) => { calls.push(args); return weekly(asset, 7); } } });
  for (const days of [7, 14, 21]) {
    await api.getWeeklyAssetOutlook('BTC-USD', days, { signal, token: 'test' });
    await api.getWeeklyPortfolioOutlook('p/id', days, { signal });
  }
  assert.deepEqual(calls.map(call => call[0]), [7, 14, 21].flatMap(days => [
    `/api/forecasting/assets/BTC-USD/horizons/${days}/outlook`, `/api/forecasting/portfolios/p%2Fid/horizons/${days}/outlook`,
  ]));
  assert.ok(calls.every(call => call[1].signal === signal && call[1].body === undefined && call[1].method === undefined));
});

test('weekly contracts retain experimental quality, actual values, and same-horizon components', () => {
  for (const days of [7, 14, 21]) {
    const a = { ...weekly(asset, days), expected_return: .017 + days / 10000, forecast_realized_volatility: .025 };
    assert.equal(ui.validOutlookResponse(a, 'asset', 'AAPL', days), true);
    assert.equal(ui.forecastPoints(a, 'return')[0].estimate, a.expected_return);
    assert.equal(ui.forecastPoints(a, 'volatility')[0].estimate, .025);
    assert.equal(ui.forecastPoints(a, 'return')[0].interval, a.return_prediction_interval);
    for (const result of [
      { ...a, experimental: false }, { ...a, predictive_quality_approved: true }, { ...a, quality_status: 'approved' },
      { ...a, horizon_unit: 'trading_days' }, { ...a, return_warning_codes: undefined }, { ...a, volatility_warning_codes: [42] },
      { ...a, expected_return: NaN }, { ...a, forecast_realized_volatility: -1 }, { ...a, artifact_version: asset.artifact_version },
      { ...a, market_data_age_days: 5 }, { ...a, forecast_origin_date: '2026-10-01' }, { ...a, horizon_days: 30 },
    ]) assert.equal(ui.validOutlookResponse(result, 'asset', 'AAPL', days), false);
    for (const baseline_kind of ['current', 'planned', 'legacy']) {
      const p = portfolioMode(weekly(portfolio, days), baseline_kind);
      assert.equal(ui.validOutlookResponse(p, 'portfolio', 'p', days), true);
      assert.equal(ui.forecastPoints(p, 'return')[0].interval, undefined);
      assert.equal(ui.validOutlookResponse({ ...p, components: [weekly(portfolio.components[0], days === 7 ? 14 : 7)] }, 'portfolio', 'p', days), false);
      assert.equal(ui.validOutlookResponse({ ...p, components: [{ ...p.components[0], predictive_quality_approved: true }] }, 'portfolio', 'p', days), false);
    }
  }
});

test('weekly selection races cancel old horizons and never fall back to 30-day estimates', async () => {
  const late = deferred(), c = mountHook({ horizon: 7, operation: () => late.promise });
  assert.equal(c.calls[0][3], 7);
  c.setOperation(async (_, id, days) => weekly({ ...asset, symbol: id }, days));
  c.horizon(14); await c.h.settle();
  assert.equal(c.calls[0][2].signal.aborted, true);
  assert.equal(c.h.value.result.horizon_days, 14);
  late.resolve(weekly(asset, 7)); await c.h.settle(); assert.equal(c.h.value.result.horizon_days, 14);
  c.setOperation(async () => asset); c.horizon(21); await c.h.settle();
  assert.equal(c.h.value.result, null); assert.ok(c.h.value.error);
  assert.deepEqual(plain(c.h.value.unavailableHorizons), [21]); c.h.unmount();
});

test('comparison requests fail independently, retain completed horizons, and time out separately', async () => {
  const late = deferred();
  const c = mountHook({ compare: true, operation: async (_, id, days) => {
    if (days === 14) throw new ApiError(503);
    if (days === 21) return late.promise;
    return days === 30 ? asset : weekly({ ...asset, symbol: id }, days);
  } });
  await c.h.settle();
  assert.deepEqual(c.calls.map(call => call[3]), [7, 14, 21, 30]);
  assert.deepEqual(plain(c.h.value.outlooks.map(item => item.horizon_days)), [7, 30]);
  assert.deepEqual(plain(c.h.value.unavailableHorizons), [14]); assert.equal(c.h.value.comparisonLoading, true);
  const count = c.calls.length; c.horizon(7); await c.h.settle();
  assert.equal(c.calls.length, count); assert.equal(c.h.value.result.horizon_days, 7);
  [...c.timers.values()][0](); await c.h.settle();
  assert.equal(c.calls.find(call => call[3] === 21)[2].signal.aborted, true);
  assert.deepEqual(plain(c.h.value.unavailableHorizons), [14, 21]); assert.equal(c.h.value.comparisonLoading, false);
  late.resolve(weekly(asset, 21)); await c.h.settle();
  assert.deepEqual(plain(c.h.value.outlooks.map(item => item.horizon_days)), [7, 30]);
  c.setOperation(async (_, id, days) => days === 30 ? asset : weekly({ ...asset, symbol: id }, days));
  c.h.value.refresh(); await c.h.settle(); assert.equal(c.h.value.outlooks.length, 4);
  c.h.unmount(); assert.equal(c.timers.size, 0);
});

test('comparison cancels every request on blur or account change and rejects late completions', async () => {
  const old = deferred(), c = mountHook({ compare: true, operation: () => old.promise });
  c.focus(false); await c.h.settle(); assert.ok(c.calls.every(call => call[2].signal.aborted));
  c.setOperation(async (_, id, days) => days === 30 ? { ...asset, symbol: id } : weekly({ ...asset, symbol: id }, days));
  c.focus(true); await c.h.settle(); assert.equal(c.h.value.outlooks.length, 4);
  c.account(null); await c.h.settle(); assert.equal(c.h.value.outlooks.length, 0);
  assert.ok(c.calls.every(call => call[2].signal.aborted));
  old.resolve(asset); await c.h.settle(); assert.equal(c.h.value.outlooks.length, 0); c.h.unmount();
});

test('native comparison chart does not bridge failed horizons or different data dates', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { OutlookChart } = load('src/components/forecasting/OutlookChart.tsx', {
    react, 'react-native': native, 'react-native-svg': { __esModule: true, default: 'Svg', Circle: 'Circle', G: 'G', Line: 'Line', Polyline: 'Polyline', Text: 'SvgText' },
    '../../theme/theme': { colors: { primary: 'teal', warning: 'amber' } }, '../../forecasting/forecastingUi': ui,
    '../../forecasting/forecastingStyles': { forecastingStyles: styles },
  });
  const results = [weekly(asset, 7), weekly(asset, 14), weekly(asset, 21), asset];
  const render = values => OutlookChart({ points: ui.comparisonPoints(values, 'return'), metric: 'return' });
  const full = render(results);
  assert.equal(nodes(full).filter(node => node.type === 'Polyline').length, 3);
  assert.deepEqual(nodes(full).filter(node => node.type === 'Circle').map(node => node.props.fill), ['amber', 'amber', 'amber', 'teal']);
  assert.equal(nodes(render([results[0], results[2], results[3]])).filter(node => node.type === 'Polyline').length, 1);
  assert.equal(nodes(render([results[0], { ...results[1], market_data_as_of: '2026-10-05' }])).filter(node => node.type === 'Polyline').length, 0);
  assert.equal(nodes(full).filter(node => node.type === 'Circle').length, 4);
  assert.match(text(full), /visual guides only/);
});

test('mobile comparison cards retain unavailable dates/status and model-quality warnings', async () => {
  const h = harness();
  const { ForecastHorizonComparison, ForecastQualityNotice } = load('src/components/forecasting/ForecastHorizonComparison.tsx', {
    react: h.react, 'react-native': native, '../ui/Card': { Card: 'Card' },
    '../../privacy/PortfolioPrivacy': privacy,
    './OutlookChart': { OutlookChart: 'Chart' }, '../../forecasting/forecastingUi': ui,
    '../../forecasting/forecastingStyles': { forecastingStyles: styles },
  });
  const a = { ...weekly(asset, 7), volatility_warning_codes: ['arima_fit_convergence_warning', 'final_interval_coverage_below_nominal', 'constructor'] };
  h.mount(() => ForecastHorizonComparison({ results: [a, asset], loading: false, unavailable: [14, 21] }));
  assert.match(text(h.value), /14\s+days ·\s+Unavailable/); assert.match(text(h.value), /21\s+days ·\s+Unavailable/);
  assert.match(text(h.value), /2026-10-06/); assert.match(text(h.value), /not approved as reliable/);
  assert.equal(nodes(h.value).find(node => node.type === 'Chart').props.points.length, 2);
  nodes(h.value).find(node => node.props.accessibilityLabel === 'Comparison Volatility chart').props.onPress();
  await h.settle(); assert.equal(nodes(h.value).find(node => node.type === 'Chart').props.points[0].estimate, .08);
  const notice = ForecastQualityNotice({ results: [a] });
  assert.match(text(notice), /7-day AAPL volatility.*fit-convergence/);
  assert.match(text(notice), /below the nominal 80%/); assert.match(text(notice), /additional model-quality warning/);
  assert.doesNotMatch(text(notice), /function Object/);
  nodes(h.value).find(node => node.props.accessibilityLabel === 'Comparison model details and limitations').props.onPress();
  await h.settle(); assert.match(text(h.value), /historical_average/); assert.match(text(h.value), /not guarantees/);
  h.unmount();
});

test('mobile horizon selection and comparison controls scope requests and keep successful comparison on selected failure', async () => {
  const c = mountScreen({ scope: 'asset', symbol: 'AAPL' }); await c.h.settle();
  assert.deepEqual(c.requests.at(-1), ['asset', 'AAPL', 30, false]);
  nodes(c.h.value).find(node => node.props.accessibilityLabel === '14 calendar days').props.onPress();
  await c.h.settle(); assert.deepEqual(c.requests.at(-1), ['asset', 'AAPL', 14, false]);
  nodes(c.h.value).find(node => node.props.accessibilityLabel === 'Compare all forecast horizons').props.onPress();
  await c.h.settle(); assert.deepEqual(c.requests.at(-1), ['asset', 'AAPL', 14, true]);
  c.forecast.error = new ApiError(503); c.forecast.outlooks = [asset]; c.forecast.unavailableHorizons = [14]; c.h.render();
  assert.ok(nodes(c.h.value).some(node => node.type === 'Comparison'));
  assert.ok(nodes(c.h.value).some(node => node.type === 'ErrorCard'));
  assert.equal(nodes(c.h.value).filter(node => node.type === 'Results').length, 0);
  c.forecast.error = null; c.forecast.result = weekly(asset, 14); c.h.render();
  assert.equal(nodes(c.h.value).find(node => node.type === 'Results').props.showChart, false);
  c.h.unmount();
});

test('native weekly cards and breakdowns use neutral backend values and selected-horizon labels', () => {
  const h = harness();
  const { ForecastingResults } = load('src/components/forecasting/ForecastingResults.tsx', {
    react: h.react, 'react-native': native, '../ui/Card': { Card: 'Card' }, '../ui/Button': { Button: 'Button' },
    './OutlookChart': { OutlookChart: 'Chart' }, './ForecastHorizonComparison': { ForecastQualityNotice: 'Quality' },
    '../../privacy/PortfolioPrivacy': privacy,
    '../../forecasting/forecastingUi': ui, '../../forecasting/forecastingStyles': { forecastingStyles: styles },
  });
  const result = { ...portfolioMode(weekly(portfolio, 21), 'planned'), expected_return: -.04,
    monetary_projection: { ...portfolioMode(portfolio, 'planned').monetary_projection, expected_change_amount: '-400', estimated_ending_value: '9600' } };
  h.mount(() => ForecastingResults({ result, onAsset() {} }));
  assert.match(text(h.value), /Expected\s+21\s*-Day Return/); assert.match(text(h.value), /-4.00%/);
  assert.match(text(h.value), /hypothetical/); assert.doesNotMatch(text(h.value), /30-Day|80% prediction range/);
  assert.ok(nodes(h.value).some(node => node.props.label === '21-day expected return'));
  assert.equal(nodes(h.value).find(node => node.type === 'Quality').props.results[0], result);
  h.unmount();
});

test('forecast navigation is within protected stacks, keeps five tabs, and leaves saved history/AI untouched', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const main = read('src/navigation/MainTabNavigator.tsx');
  assert.equal((main.match(/Screen name="Forecasting"/g) ?? []).length, 2);
  assert.equal((main.match(/<Tab.Screen/g) ?? []).length, 5);
  assert.match(main, /Back from Forecasting/); assert.match(main, /returnToHome/);
  assert.match(read('src/navigation/RootNavigator.tsx'), /authStatus === 'authenticated'[\s\S]*name="Main"/);
  for (const file of ['src/screens/settings/MoreScreen.tsx', 'src/screens/dashboard/DashboardScreen.tsx', 'src/screens/portfolios/PortfolioDetailScreen.tsx', 'src/screens/analytics/PortfolioAnalysisScreen.tsx', 'src/screens/watchlist/WatchlistScreen.tsx']) assert.match(read(file), /Forecasting/);
  for (const file of ['src/screens/reports/ReportDetailScreen.tsx', 'src/screens/simulations/SimulationResultScreen.tsx', 'src/screens/assistant/AssistantScreen.tsx']) assert.doesNotMatch(read(file), /useForecasting|getAssetOutlook|getPortfolioOutlook/);
});

test('themed forecast headers return to the source stack or Dashboard with safe root fallbacks', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const mocks = {
    react, '@expo/vector-icons': { Ionicons: 'Icon' },
    '@react-navigation/bottom-tabs': { createBottomTabNavigator: () => ({ Navigator: 'Tab', Screen: 'TabScreen' }) },
    '@react-navigation/native-stack': { createNativeStackNavigator: () => ({ Navigator: 'Stack', Screen: 'StackScreen' }) },
    '../theme/colors': { darkPalette: { text: '#F7FAFF' }, lightPalette: {} },
    '../preferences/usePreferences': { usePreferences: () => ({ themeMode: 'dark' }) },
    '../components/ui/HomeHeaderButton': { HomeHeaderButton: 'Home' }, '../components/ui/BackHeaderButton': { BackHeaderButton: 'Back' },
    './tabRootNavigation': { tabRootAction: () => null },
  };
  const source = ts.createSourceFile('navigator.tsx', fs.readFileSync(path.join(root, 'src/navigation/MainTabNavigator.tsx'), 'utf8'), ts.ScriptTarget.Latest, true);
  for (const node of source.statements) {
    if (ts.isImportDeclaration(node) && node.moduleSpecifier.text.startsWith('../screens/')) {
      mocks[node.moduleSpecifier.text] = Object.fromEntries(node.importClause.namedBindings.elements.map(binding => [binding.name.text, binding.name.text]));
    }
  }
  const { MainTabNavigator } = load('src/navigation/MainTabNavigator.tsx', mocks);
  const tree = MainTabNavigator(), destinations = [];
  let canBack = true;
  const navigation = {
    canGoBack: () => canBack, goBack: () => destinations.push('back'), navigate: value => destinations.push(value),
    getParent: () => ({ navigate: value => destinations.push(value) }),
  };
  const screen = tab => nodes(nodes(tree).find(n => n.props.name === tab).props.component()).find(n => n.props.name === 'Forecasting');
  const more = screen('MoreTab'), port = screen('Portfolio');
  const sourceBack = more.props.options({ navigation, route: { params: {} } }).headerLeft();
  assert.equal(sourceBack.props.color, '#F7FAFF'); sourceBack.props.onPress(); assert.equal(destinations.pop(), 'back');
  more.props.options({ navigation, route: { params: { returnToHome: true } } }).headerLeft().props.onPress();
  assert.equal(destinations.pop(), 'Home');
  port.props.options({ navigation }).headerLeft().props.onPress(); assert.equal(destinations.pop(), 'back');
  canBack = false;
  more.props.options({ navigation, route: {} }).headerLeft().props.onPress(); assert.equal(destinations.pop(), 'More');
  port.props.options({ navigation }).headerLeft().props.onPress(); assert.equal(destinations.pop(), 'Portfolios');
});

test('native money formatting preserves Decimal cents, rounding carries, scientific values and negative zero', () => {
  const cases = [
    ['1234567890123456.125', '$1,234,567,890,123,456.13'], ['-1.005', '-$1.01'],
    ['999.999', '$1,000.00'], ['2.345E+1', '$23.45'], ['0.005', '$0.01'], ['0.00005', '$0.00'],
    ['0E-12', '$0.00'], ['-0.0049', '$0.00'], ['-0', '$0.00'], ['00012.300', '$12.30'],
  ];
  for (const [value, expected] of cases) assert.equal(ui.forecastMoney(value, 'USD'), expected);
  assert.equal(ui.forecastMoney('250.125', 'THB', true), '+฿250.13');
  assert.equal(ui.forecastMoney('-250.125', 'THB', true), '-฿250.13');
  for (const invalid of ['NaN', 'Infinity', '1e999999', ' ', '1,000', 100, {}]) assert.equal(ui.forecastMoney(invalid, 'USD'), 'N/A');
  assert.equal(ui.negativeMoney('-0'), false); assert.equal(ui.negativeMoney('-1E-3'), true);
  assert.match(ui.compactForecastMoney(125000.125, 'USD', true), /^\+\$125K$/);
  assert.doesNotMatch(fs.readFileSync(path.join(root, 'src/forecasting/forecastingMoney.ts'), 'utf8'), /BigInt\(|\d+n\b/);
});

test('all native horizons require complete, consistent overall and holding monetary context', () => {
  for (const horizon of [7, 14, 21, 30]) {
    const source = horizon === 30 ? portfolio : weekly(portfolio, horizon);
    for (const kind of ['current', 'planned', 'legacy']) {
      for (const currency of kind === 'planned' ? ['USD', 'THB'] : ['USD']) {
        assert.equal(ui.validOutlookResponse(portfolioMode(source, kind, currency), 'portfolio', 'p', horizon), true);
      }
    }
    for (const patch of [null, undefined, { ...source.monetary_projection, baseline_amount: '0' },
      { ...source.monetary_projection, expected_change_amount: 250 },
      { ...source.monetary_projection, currency: 'THB', assumes_unchanged_fx: true },
      { ...source.monetary_projection, valuation_requested_date: '2026-02-30' },
      { ...source.monetary_projection, newest_price_as_of: '2026-10-08' },
      { ...source.monetary_projection, limitations: [42] },
    ]) assert.equal(ui.validOutlookResponse({ ...source, monetary_projection: patch }, 'portfolio', 'p', horizon), false);
    for (const patch of [null, { ...source.components[0].monetary_projection, currency: 'THB' },
      { ...source.components[0].monetary_projection, oldest_price_as_of: '2026-10-01' },
      { ...source.components[0].monetary_projection, valuation_requested_date: '2026-10-09' },
    ]) assert.equal(ui.validOutlookResponse({ ...source, components: [{ ...source.components[0], monetary_projection: patch }, source.components[1]] }, 'portfolio', 'p', horizon), false);
    assert.equal(ui.validOutlookResponse({ ...portfolioMode(source, 'legacy'), monetary_projection: source.monetary_projection }, 'portfolio', 'p', horizon), false);
    const planned = portfolioMode(source, 'planned', 'THB');
    assert.equal(ui.validOutlookResponse({ ...planned, monetary_projection: { ...planned.monetary_projection, assumes_unchanged_fx: false } }, 'portfolio', 'p', horizon), false);
  }
});

function moneyResultsHarness(initialResult, initialHidden = false) {
  const h = harness(); let result = initialResult, hidden = initialHidden;
  const destinations = [];
  const { ForecastingResults } = load('src/components/forecasting/ForecastingResults.tsx', {
    react: h.react, 'react-native': native, '../ui/Card': { Card: 'Card' }, '../ui/Button': { Button: 'Button' },
    './OutlookChart': { OutlookChart: 'Chart' }, './ForecastHorizonComparison': { ForecastQualityNotice: 'Quality' },
    '../../forecasting/forecastingUi': ui, '../../forecasting/forecastingStyles': { forecastingStyles: styles },
    '../../privacy/PortfolioPrivacy': { usePortfolioPrivacy: () => ({ hideValues: hidden }), usePrivateValue: () => value => hidden ? '••••' : value },
  });
  h.mount(() => ForecastingResults({ result, onAsset: symbol => destinations.push(symbol) }));
  return { h, destinations, change(next) { result = next; h.render(); }, hide(value) { hidden = value; h.render(); } };
}

test('native summary and holding cards copy own backend amounts at every horizon and retain standalone drill-down', () => {
  for (const horizon of [7, 14, 21, 30]) {
    const source = horizon === 30 ? portfolio : weekly(portfolio, horizon);
    const c = moneyResultsHarness(source);
    assert.match(text(c.h.value), /Portfolio amount outlook/);
    assert.match(text(c.h.value), /\$10,000.00/); assert.match(text(c.h.value), /\+\$250.00/);
    assert.match(text(c.h.value), /\$10,250.00/); assert.match(text(c.h.value), /not purchase cost/);
    source.components.forEach(item => {
      const card = nodes(c.h.value).find(node => node.type === 'Card' && node.props.key === item.symbol);
      const rows = nodes(card).filter(node => typeof node.type === 'function' && node.type.name === 'DataRow');
      assert.equal(rows.find(row => row.props.label === 'Current value (USD)').props.value, ui.forecastMoney(item.monetary_projection.baseline_amount, 'USD'));
      const change = rows.find(row => row.props.label === `${horizon}-day expected change (USD)`);
      assert.equal(change.props.value, ui.forecastMoney(item.monetary_projection.expected_change_amount, 'USD', true));
      assert.equal(change.props.negative, ui.negativeMoney(item.monetary_projection.expected_change_amount));
      assert.equal(rows.find(row => row.props.label === 'Estimated value (USD)').props.value, ui.forecastMoney(item.monetary_projection.estimated_ending_value, 'USD'));
      assert.equal(rows.find(row => row.props.label === 'Holding price as of').props.value, item.monetary_projection.oldest_price_as_of);
      assert.ok(text(change.type(change.props)).includes(change.props.value));
    });
    nodes(c.h.value).find(node => node.props.accessibilityLabel === 'Expected change (USD) chart').props.onPress(); c.h.render();
    const chart = nodes(c.h.value).find(node => node.type === 'Chart');
    assert.equal(chart.props.metric, 'change'); assert.equal(chart.props.points[0].estimate, 250); assert.equal(chart.props.points[0].interval, undefined);
    nodes(c.h.value).find(node => node.props.accessibilityLabel === 'View AAPL asset outlook').props.onPress();
    assert.deepEqual(c.destinations, ['AAPL']);
    nodes(c.h.value).find(node => node.props.accessibilityLabel === 'Model details and limitations').props.onPress(); c.h.render();
    assert.match(text(c.h.value), /Monetary assumptions/); assert.match(text(c.h.value), /not guaranteed balances/);
    c.h.unmount();
  }
});

test('native planned THB amounts are hypothetical, while legacy and standalone results never expose money controls', () => {
  const c = moneyResultsHarness(portfolioMode(weekly(portfolio, 14), 'planned', 'THB'));
  assert.match(text(c.h.value), /฿10,000.00/); assert.match(text(c.h.value), /unchanged exchange rates/);
  assert.match(text(c.h.value), /not assets you currently own/);
  assert.ok(nodes(c.h.value).some(node => node.props.label === 'Planned amount (THB)' && node.props.value === '฿4,000.00'));
  assert.ok(!nodes(c.h.value).some(node => node.props.label === 'Holding price as of'));
  assert.doesNotMatch(text(c.h.value), /Valuation requested/);
  nodes(c.h.value).find(node => node.props.accessibilityLabel === 'Expected change (THB) chart').props.onPress(); c.h.render();
  c.change(asset);
  assert.equal(nodes(c.h.value).find(node => node.type === 'Chart').props.metric, 'return');
  assert.doesNotMatch(text(c.h.value), /Portfolio amount outlook|Expected change \(|\$|฿/);
  assert.match(text(c.h.value), /80% prediction range/);
  c.change(portfolioMode(portfolio, 'legacy'));
  assert.match(text(c.h.value), /percentage-only/);
  assert.ok(!nodes(c.h.value).some(node => /Current value|Planned amount|Estimated value/.test(node.props.label ?? '')));
  assert.doesNotMatch(text(c.h.value), /\$|฿|Expected change \(/); c.h.unmount();
});

test('native privacy masks summary and holding values and immediately removes selected money chart data', () => {
  const c = moneyResultsHarness(portfolio);
  nodes(c.h.value).find(node => node.props.accessibilityLabel === 'Expected change (USD) chart').props.onPress(); c.h.render();
  c.hide(true);
  assert.match(text(c.h.value), /••••/); assert.doesNotMatch(text(c.h.value), /\$|฿|Expected change \(/);
  for (const row of nodes(c.h.value).filter(node => /Current value|expected change|Estimated value/.test(node.props.label ?? ''))) assert.equal(row.props.value, '••••');
  const chart = nodes(c.h.value).find(node => node.type === 'Chart');
  assert.equal(chart.props.metric, 'return');
  for (const point of chart.props.points) for (const key of ['amount', 'currency', 'baselineKey']) assert.equal(point[key], undefined);
  c.hide(false); assert.match(text(c.h.value), /\$10,000.00/);
  assert.equal(nodes(c.h.value).find(node => node.type === 'Chart').props.metric, 'change');
  c.h.unmount();
  const initiallyHidden = moneyResultsHarness(portfolio, true);
  assert.doesNotMatch(text(initiallyHidden.h.value), /\$|฿/);
  assert.ok(nodes(initiallyHidden.h.value).some(node => node.props.value === '••••')); initiallyHidden.h.unmount();
});

test('native monetary chart preserves full spoken amounts, compact labels, single-string ticks and baseline gaps', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { OutlookChart } = load('src/components/forecasting/OutlookChart.tsx', {
    react, 'react-native': native, 'react-native-svg': { __esModule: true, default: 'Svg', Circle: 'Circle', G: 'G', Line: 'Line', Polyline: 'Polyline', Text: 'SvgText' },
    '../../theme/theme': { colors: { primary: 'teal', warning: 'amber' } }, '../../forecasting/forecastingUi': ui,
    '../../forecasting/forecastingStyles': { forecastingStyles: styles },
  });
  const points = ui.comparisonPoints([weekly(portfolio, 7), weekly(portfolio, 14), weekly(portfolio, 21), portfolio], 'change');
  const tree = OutlookChart({ points, metric: 'change' });
  assert.equal(nodes(tree).filter(node => node.type === 'Polyline').length, 3);
  assert.equal(nodes(tree).filter(node => node.type === 'Line' && node.props.strokeWidth === 2).length, 0);
  assert.match(nodes(tree).find(node => node.props.accessibilityRole === 'image').props.accessibilityLabel, /Expected change \(USD\).*7 days: \+\$250.00/);
  assert.deepEqual(nodes(tree).filter(node => node.type === 'SvgText' && node.props.y === 191).map(node => node.children), [['7 days'], ['14 days'], ['21 days'], ['30 days']]);
  for (const key of ['baselineKey', 'currency', 'dataDate']) {
    const changed = points.map(point => ({ ...point })); changed[1][key] = 'different';
    assert.equal(nodes(OutlookChart({ points: changed, metric: 'change' })).filter(node => node.type === 'Polyline').length, 1);
  }
  const changedBaseline = { ...weekly(portfolio, 14), components: portfolio.components.map(item => ({ ...weekly(item, 14), monetary_projection: { ...item.monetary_projection, baseline_amount: '5000' } })) };
  assert.equal(nodes(OutlookChart({ points: ui.comparisonPoints([weekly(portfolio, 7), changedBaseline], 'change'), metric: 'change' })).filter(node => node.type === 'Polyline').length, 0);
  const large = OutlookChart({ points: [{ ...points[0], estimate: 125000.125, amount: '125000.125' }], metric: 'change' });
  assert.match(text(large), /\+\$125K/);
  assert.match(nodes(large).find(node => node.props.accessibilityRole === 'image').props.accessibilityLabel, /\+\$125,000.13/);
  for (const amount of ['1E+340', '1E+308', '-1E+308']) assert.equal(ui.forecastPoints({ ...portfolio, monetary_projection: { ...portfolio.monetary_projection, expected_change_amount: amount } }, 'change').length, 0);
  assert.equal(ui.forecastPoints(asset, 'change').length, 0);
  assert.equal(ui.forecastPoints(portfolioMode(portfolio, 'legacy'), 'change').length, 0);
});

test('native comparison amounts retain individual baselines, failures and privacy-safe charts', () => {
  const h = harness(); let hidden = false, results = [weekly(portfolio, 7), portfolio];
  const { ForecastHorizonComparison } = load('src/components/forecasting/ForecastHorizonComparison.tsx', {
    react: h.react, 'react-native': native, '../ui/Card': { Card: 'Card' }, './OutlookChart': { OutlookChart: 'Chart' },
    '../../forecasting/forecastingUi': ui, '../../forecasting/forecastingStyles': { forecastingStyles: styles },
    '../../privacy/PortfolioPrivacy': { usePortfolioPrivacy: () => ({ hideValues: hidden }), usePrivateValue: () => value => hidden ? '••••' : value },
  });
  h.mount(() => ForecastHorizonComparison({ results, loading: false, unavailable: [14, 21] }));
  assert.match(text(h.value), /Baseline amount:\s+\$10,000.00 USD/); assert.match(text(h.value), /Estimated value:\s+\$10,250.00/);
  assert.match(text(h.value), /14\s+days ·\s+Unavailable/);
  nodes(h.value).find(node => node.props.accessibilityLabel === 'Comparison Expected change (USD) chart').props.onPress(); h.render();
  assert.equal(nodes(h.value).find(node => node.type === 'Chart').props.metric, 'change');
  hidden = true; h.render();
  assert.doesNotMatch(text(h.value), /\$|฿|Expected change \(/); assert.match(text(h.value), /••••/);
  const chart = nodes(h.value).find(node => node.type === 'Chart'); assert.equal(chart.props.metric, 'return');
  assert.ok(chart.props.points.every(point => point.amount === undefined && point.baselineKey === undefined));
  hidden = false; results = [portfolioMode(weekly(portfolio, 7), 'planned', 'THB'), portfolioMode(portfolio, 'planned')]; h.render();
  assert.match(text(h.value), /฿10,000.00 THB/); assert.match(text(h.value), /\$10,000.00 USD/);
  assert.equal(nodes(h.value).find(node => node.type === 'Chart').props.metric, 'return');
  assert.ok(!nodes(h.value).some(node => /Comparison Expected change/.test(node.props.accessibilityLabel ?? ''))); h.unmount();
});

test('native loader rejects missing monetary context without stale values, fallback or additional valuation requests', async () => {
  const c = mountHook(); await c.h.settle();
  c.setOperation(async () => ({ ...portfolio, monetary_projection: null }));
  c.select('portfolio', 'p'); await c.h.settle(); assert.equal(c.h.value.result, null); assert.ok(c.h.value.error);
  c.setOperation(async () => portfolio); c.h.value.refresh(); await c.h.settle();
  assert.equal(c.h.value.result.monetary_projection.baseline_amount, '10000');
  c.setOperation(async () => ({ ...portfolio, components: [{ ...portfolio.components[0], monetary_projection: null }] }));
  c.h.value.refresh(); await c.h.settle(); assert.equal(c.h.value.result, null); assert.ok(c.h.value.error);
  assert.ok(c.calls.every(call => ['asset', 'portfolio'].includes(call[0]) && call[2].body === undefined)); c.h.unmount();
});
