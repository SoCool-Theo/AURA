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
const ui = load('src/forecasting/forecastingUi.ts', { '../api/apiClient': { ApiError } });
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
function mountHook(options = {}) {
  const h = harness(), calls = [], timers = new Map();
  let focused = true;
  let account = 'a', scope = 'asset', selection = 'AAPL', operation = options.operation ?? (async (kind, id) => kind === 'asset' ? { ...asset, symbol: id } : { ...portfolio, portfolio_id: id });
  const auth = { useAuth: () => ({ status: account ? 'authenticated' : 'unauthenticated', user: account ? { id: account } : null }) };
  const api = { getAssetOutlook: (id, opts) => { calls.push(['asset', id, opts]); return operation('asset', id); }, getPortfolioOutlook: (id, opts) => { calls.push(['portfolio', id, opts]); return operation('portfolio', id); } };
  const { useForecasting } = load('src/forecasting/useForecasting.ts', { react: h.react, '@react-navigation/native': { useFocusEffect: cb => h.react.useEffect(() => focused ? cb() : undefined, [cb, focused]) }, '../auth/useAuth': auth, '../api/forecastingApi': api, './forecastingUi': ui },
    { setTimeout: (fn, delay) => { assert.equal(delay, 60000); const key = Symbol(); timers.set(key, fn); return key; }, clearTimeout: key => timers.delete(key) });
  h.mount(() => useForecasting(scope, selection));
  return { h, calls, timers, auth, useForecasting, setOperation(value) { operation = value; },
    focus(value) { focused = value; h.render(); },
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
});
test('native results retain planned baseline, negative shares, ranges, metadata and asset drill-down', async () => {
  const h = harness(), destinations = [];
  const { ForecastingResults } = load('src/components/forecasting/ForecastingResults.tsx', {
    react: h.react, 'react-native': native, '../ui/Card': { Card: 'Card' }, '../ui/Button': { Button: 'Button' },
    './OutlookChart': { OutlookChart: 'Chart' }, '../../forecasting/forecastingUi': ui,
    '../../forecasting/forecastingStyles': { forecastingStyles: styles },
  });
  let result = { ...portfolio, baseline_kind: 'planned' };
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
  const h = harness(), selections = [], destinations = [];
  let refreshed = 0;
  const forecast = { result: null, error: null, loading: false, refresh: () => refreshed++ };
  const { AccountForecasting } = load('src/screens/forecasting/ForecastingScreen.tsx', {
    react: h.react, '@react-navigation/native': { useFocusEffect: cb => h.react.useEffect(cb, [cb]) },
    'react-native': native, 'react-native-safe-area-context': { SafeAreaView: 'Safe' },
    '../../theme/theme': { colors: {} }, '../../auth/useAuth': { useAuth: () => ({ status: 'authenticated', user: { id: 'a' } }) },
    '../../api/portfoliosApi': { portfoliosApi: { list: operation } },
    '../../components/ui/Button': { Button: 'Button' }, '../../components/ui/Card': { Card: 'Card' },
    '../../components/ui/PageTitle': { PageTitle: 'Title' }, '../../components/ui/ErrorState': { InlineErrorCard: 'ErrorCard' },
    '../../components/simulations/PortfolioSelector': { PortfolioSelector: 'PortfolioSelector' },
    '../../components/forecasting/ForecastingResults': { ForecastingResults: 'Results' },
    '../../forecasting/useForecasting': { useForecasting: (scope, selection) => { selections.push([scope, selection]); return forecast; } },
    '../../forecasting/forecastingUi': ui, '../../forecasting/forecastingStyles': { forecastingStyles: styles },
    '../../portfolio/supportedAssetSymbols': { supportedAssets: [{ symbol: 'AAPL', name: 'Apple' }, { symbol: 'MSFT', name: 'Microsoft' }] },
  });
  const navigation = {
    navigate: (...args) => destinations.push(args), push: (...args) => destinations.push(args),
    getState: () => ({ routeNames: ['More', 'Analytics', 'Forecasting'] }),
    getParent: () => ({ navigate: (...args) => destinations.push(args) }),
  };
  h.mount(() => AccountForecasting({ route: { params }, navigation }));
  return { h, selections, forecast, destinations, get refreshed() { return refreshed; } };
}
test('mobile screen offers asset access without portfolios, keeps search selection and disables weekly horizons', async () => {
  const c = mountScreen(); await c.h.settle();
  assert.match(text(c.h.value), /No portfolios yet/);
  const horizons = nodes(c.h.value).filter(n => /calendar days/.test(n.props.accessibilityLabel ?? ''));
  assert.deepEqual(horizons.map(n => n.props.disabled), [true, true, true, false]);
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
