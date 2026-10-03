const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const supportedAssetSymbols = [
  'AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'GOOGL', 'META', 'SPY', 'QQQ',
  'DIA', 'VTI', 'GLD', 'SLV', 'BND', 'TLT', 'BTC-USD', 'ETH-USD',
];

function load(file, mocks = {}, globals = {}) {
  const module = { exports: {} };
  const source = fs.readFileSync(path.join(root, file), 'utf8');
  const code = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.React,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  }).outputText;
  vm.runInNewContext(code, {
    module,
    exports: module.exports,
    URL,
    Headers,
    Date,
    require: name => {
      if (!(name in mocks) && name.endsWith('/privacy/PortfolioPrivacy')) return {
        usePortfolioPrivacy: () => ({ hideValues: false, ready: true, storageError: null, setHideValues: () => {} }),
        usePrivateValue: () => value => value, usePrivateText: () => value => value,
      };
      assert.ok(name in mocks, `Unmocked module ${name} in ${file}`);
      return mocks[name];
    },
    ...globals,
  }, { filename: file });
  return module.exports;
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

test('web Top Risk Drivers opens the exact saved report section, retaining setup when no report exists', () => {
  const routes = [], react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { RiskDrivers } = load('src/pages/dashboard/components/RiskDrivers.tsx', {
    '../../../app/routes': { go: route => routes.push(route) }, '../../../components/ui/Card': { Card: 'Card' },
    '../../../components/ui/SymbolBadge': { SymbolBadge: 'Symbol' }, '../dashboardUi': { formatPercent: value => `${value * 100}%` }, '../DashboardIntegration.module.css': {},
  }, { React: react });
  const render = (reportId, loading = false) => localWebNodes(RiskDrivers({ portfolioId: 'portfolio', reportId, drivers: [], loading, failed: false })).find(node => node.type === 'button');
  render('saved-report').props.onClick(); assert.deepEqual(routes, ['reports/portfolio/saved-report/risk-drivers']);
  render(null).props.onClick(); assert.equal(routes[1], 'analytics/portfolio');
  assert.equal(render('saved-report', true).props.disabled, true);
  const app = fs.readFileSync(path.join(root, 'src/app/App.tsx'), 'utf8');
  const results = fs.readFileSync(path.join(root, 'src/pages/analytics/components/AnalysisResults.tsx'), 'utf8');
  assert.match(app, /focusRiskDrivers=\{route.contextId === 'risk-drivers'\}/);
  assert.match(results, /id="risk-drivers"[^\n]*<RiskDriverTable/);
});

test('web report detail waits for the saved snapshot before jumping to Risk Drivers or the existing asset section', async () => {
  for (const [options, expected] of [[{ focusRiskDrivers: true }, 'risk-drivers'], [{ focusAssetSection: true }, 'per-asset-analysis'], [{}, null]]) {
    for (const navigationHeight of [76, 108.5, null]) {
    const slots = []; let cursor = 0, effects = [], resolve;
    const pending = new Promise(done => { resolve = done; }), requests = [], frames = [], scrolled = [];
    const react = {
      createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
      useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial; return [slots[i], value => { slots[i] = value; }]; },
      useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
      useEffect(fn) { effects.push(fn); },
    };
    const { ReportDetailPage } = load('src/pages/reports/ReportDetailPage.tsx', {
      react, '../../api/reportsApi': { getPortfolioReport: (portfolioId, reportId) => { requests.push([portfolioId, reportId]); return pending; } },
      '../../app/routes': { go() {} }, '../../components/ui/ApiErrorState': { InlineErrorCard: 'Error', ScreenErrorState: 'Error' },
      '../../components/ui/Icon': { Icon: 'Icon' }, '../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
      '../../types/report': { isPortfolioReportV2: () => false, isPortfolioReportV3: () => false },
      '../analytics/analyticsUi': { formatReportTimestamp: value => value }, '../analytics/components/AnalysisResults': { AnalysisResults: 'Analysis' }, './ReportDetailPage.module.css': {},
    }, { React: react, AbortController, window: { requestAnimationFrame: fn => { frames.push(fn); return 1; }, cancelAnimationFrame() {} },
      document: {
        querySelector: selector => { assert.equal(selector, '.top-nav'); return navigationHeight == null ? null : { getBoundingClientRect: () => ({ height: navigationHeight }) }; },
        getElementById: id => ({ style: { scrollMarginTop: '18px' }, scrollIntoView(options) { scrolled.push([id, options.block, this.style.scrollMarginTop]); } }),
      } });
    const render = () => { cursor = 0; effects = []; return ReportDetailPage({ portfolioId: 'p', reportId: 'exact', ...options }); };
    render(); effects[0](); effects[1](); assert.equal(frames.length, 0, 'no premature scroll while loading');
    resolve({ id: 'exact', portfolio_id: 'p', created_at: 'today', analysis: { portfolio_name: 'Saved portfolio' } });
    await new Promise(done => setImmediate(done)); render(); effects[1]();
    frames.forEach(fn => fn()); assert.deepEqual(scrolled, expected ? [[expected, 'start', `${Math.ceil(navigationHeight ?? 0) + 18}px`]] : []);
    assert.deepEqual(requests, [['p', 'exact']]);
    }
  }
});

test('web saved risk levels color both asset labels and scores without reclassifying backend numbers', () => {
  const ui = load('src/pages/analytics/analyticsUi.ts', { '../../api/apiClient': { ApiError: Error } });
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { AssetAnalysisCard } = load('src/pages/analytics/components/AssetAnalysisCard.tsx', {
    '../../../components/ui/Icon': { Icon: 'Icon' }, '../../../components/ui/SymbolBadge': { SymbolBadge: 'Symbol' },
    '../analyticsUi': ui, '../AnalyticsIntegration.module.css': { assetRiskLevel: 'risk' },
  }, { React: react });
  const { AnalysisSummary } = load('src/pages/analytics/components/AnalysisSummary.tsx', {
    '../../../components/ui/Card': { Card: 'Card' }, '../../../components/ui/Icon': { Icon: 'Icon' },
    '../analyticsUi': ui, '../AnalyticsIntegration.module.css': {},
  }, { React: react });
  const levels = [['Low', 'var(--green-primary)'], ['Moderate', 'var(--amber-primary)'], ['High', 'var(--red-bright)'], ['Very High', 'var(--red-bright)']];
  for (const [level, color] of levels) {
    // The same number intentionally receives each saved label: colors must not calculate severity.
    const risk = { risk_score: 50, risk_level: level, reasons: [] };
    assert.equal(ui.riskColor(level), color);
    const asset = { symbol: 'AAPL', weight: .5, cumulative_return: .1, annualized_return: .1, annualized_volatility: .2, max_drawdown: -.1, sharpe_ratio: 1, risk_classification: risk };
    const paragraph = localWebNodes(AssetAnalysisCard({ asset, onOpen() {} })).find(node => node.type === 'p');
    assert.equal(paragraph.props.style.color, color); assert.equal(paragraph.children.join(''), `50.0 · ${level} risk`);
    const summary = localWebNodes(AnalysisSummary({ analysis: { risk_classification: risk, metadata: {} } }));
    const score = summary.find(node => node.type === 'strong'), label = summary.find(node => node.type === 'span' && node.props.style);
    assert.equal(score.props.style.color, color); assert.equal(label.props.style.color, color);
    assert.equal(score.children.join(''), '50.0');
  }
  assert.equal(ui.riskColor(undefined), 'var(--text-muted)');
  const legacy = AssetAnalysisCard({ asset: { symbol: 'OLD', weight: 1, cumulative_return: 0, annualized_return: 0, annualized_volatility: 0, max_drawdown: 0, sharpe_ratio: null }, onOpen() {} });
  assert.ok(!localWebNodes(legacy).some(node => node.type === 'p'));
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const detail = read('src/pages/reports/AssetRiskDetailPage.tsx');
  assert.match(detail, /<strong style=\{\{ color: riskColor\(risk\?\.risk_level\) \}\}/);
  assert.match(detail, /<span style=\{\{ color: riskColor\(risk\?\.risk_level\) \}\}/);
  const dashboard = read('src/pages/dashboard/components/DashboardKpiGrid.tsx');
  assert.match(dashboard, /<strong style=\{\{ color: riskColor\(risk\?\.risk_level\) \}\}/);
  assert.match(dashboard, /className=\{`metric-change \$\{riskLabelTone\}`\} style=\{\{ color: riskColor\(risk\?\.risk_level\) \}\}/);
});

test('web gauge score accepts risk color while keeping legacy callers unchanged', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { GaugeChart } = load('src/components/charts/GaugeChart.tsx', { '../../utils/uiCalculations': { clamp: (value, min, max) => Math.max(min, Math.min(max, value)) } }, { React: react });
  const colored = localWebNodes(GaugeChart({ score: 83.3, color: 'var(--red-bright)' })).find(node => node.type === 'strong');
  assert.equal(colored.props.style.color, 'var(--red-bright)'); assert.equal(colored.children[0], 83.3);
  assert.equal(localWebNodes(GaugeChart({ score: 30 })).find(node => node.type === 'strong').props.style, undefined);
});

function mountWebPrivacy(accountId, storage) {
  const slots = []; let cursor = 0, wrapper, tree;
  const react = {
    createContext: value => ({ Provider: 'PrivacyProvider', initial: value }),
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useContext: () => tree.props.value,
    useState: initial => {
      const i = cursor++;
      if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial;
      return [slots[i], next => { slots[i] = typeof next === 'function' ? next(slots[i]) : next; render(); }];
    },
  };
  const privacy = load('src/privacy/PortfolioPrivacy.tsx', {
    react, '../auth/useAuth': { useAuth: () => ({ user: accountId ? { id: accountId } : null }) },
  }, { React: react, localStorage: storage });
  wrapper = privacy.PortfolioPrivacyProvider({ children: 'content' });
  function render() { cursor = 0; tree = accountId ? wrapper.type(wrapper.props) : wrapper; }
  render();
  return { privacy, get value() { return tree.props.value; }, key: wrapper.props.key };
}

test('web portfolio privacy defaults Off per account/browser and survives logout/login with both choices', () => {
  const saved = new Map(), writes = [];
  const storage = { getItem: key => saved.get(key) ?? null, setItem: (key, value) => { writes.push(key); saved.set(key, value); } };
  const first = mountWebPrivacy('account-a', storage);
  assert.equal(first.value.hideValues, false); assert.equal(first.value.ready, true);
  first.value.setHideValues(true); assert.equal(first.value.hideValues, true);
  assert.equal(first.privacy.usePrivateValue()('$12,345.67'), '••••');
  assert.equal(first.privacy.usePrivateText()('Based on ฿12,345.67; USD 987.65. Return +12.34%.'), 'Based on ••••; ••••. Return +12.34%.');
  assert.equal(mountWebPrivacy(null, storage).value.hideValues, false);
  assert.equal(writes.length, 1, 'logout must not overwrite the account preference');
  assert.equal(mountWebPrivacy('account-b', storage).value.hideValues, false);
  const restored = mountWebPrivacy('account-a', storage);
  assert.equal(restored.key, 'account-a'); assert.equal(restored.value.hideValues, true);
  restored.value.setHideValues(false);
  assert.equal(restored.privacy.usePrivateValue()('$12,345.67'), '$12,345.67');
  assert.equal(mountWebPrivacy('account-a', storage).value.hideValues, false);
  first.value.setHideValues(true);
  assert.equal(mountWebPrivacy('account-a', { getItem: () => null }).value.hideValues, false, 'another browser starts Off');
  assert.notEqual(first.privacy.privacyStorageKey('account-a'), first.privacy.privacyStorageKey('account-b'));
});

test('web portfolio privacy fails closed for unreadable/malformed storage and reports save failures with retry', () => {
  for (const raw of ['bad-json', '{}', '"true"']) {
    const state = mountWebPrivacy('account-a', { getItem: () => raw });
    assert.equal(state.value.hideValues, true); assert.match(state.value.storageError, /could not be loaded/);
  }
  let fail = true; const saved = new Map();
  const state = mountWebPrivacy('account-a', {
    getItem: () => { throw Error('blocked'); },
    setItem: (key, value) => { if (fail) throw Error('blocked'); saved.set(key, value); },
  });
  assert.equal(state.value.hideValues, true);
  state.value.setHideValues(false); assert.equal(state.value.hideValues, false);
  assert.match(state.value.storageError, /could not be saved/);
  fail = false; state.value.setHideValues(false); assert.equal(state.value.storageError, null);
  assert.equal(saved.get(state.privacy.privacyStorageKey('account-a')), 'false');
});

test('web real/planned holdings mask personal values and quantities without altering allocation or data', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const types = load('src/types/portfolio.ts');
  const formatting = load('src/pages/portfolios/portfolioUi.ts', { '../../api/apiClient': { ApiError: Error } });
  let hidden = true;
  const { HoldingsTable } = load('src/components/portfolio/HoldingsTable.tsx', {
    '../../privacy/PortfolioPrivacy': { usePrivateValue: () => value => hidden ? '••••' : value },
    '../../types/portfolio': types, '../../pages/portfolios/portfolioUi': formatting,
    '../ui/Card': { Card: 'Card' }, '../ui/SymbolBadge': { SymbolBadge: 'SymbolBadge' },
  }, { React: react });
  const portfolio = { portfolio_type: 'CURRENT', holdings: [{ position: 0, symbol: 'AAPL', shares: '123.45', weight: null }] };
  const valuation = { valuation_currency: 'USD', total_current_value: '24690.00', holdings: [{ symbol: 'AAPL', current_value: '24690.00', current_allocation: '1' }] };
  const original = JSON.stringify({ portfolio, valuation });
  let tree = JSON.stringify(HoldingsTable({ portfolio, valuation }));
  assert.match(tree, /••••/); assert.match(tree, /100.00%/); assert.match(tree, /AAPL/);
  assert.doesNotMatch(tree, /123.45|24,690/);
  hidden = false; tree = JSON.stringify(HoldingsTable({ portfolio, valuation }));
  assert.match(tree, /123.45/); assert.match(tree, /24,690/);
  hidden = true;
  const planned = { portfolio_type: 'PLANNED', plan_currency: 'THB', holdings: [{ position: 0, symbol: 'AAPL', proposed_amount: '54321.00', weight: null }] };
  const plannedPreview = { plan_currency: 'THB', total_proposed_amount: '54321.00', holdings: [{ symbol: 'AAPL', estimate_status: 'AVAILABLE', estimated_shares: '77.77', target_allocation: '1' }] };
  tree = JSON.stringify(HoldingsTable({ portfolio: planned, plannedPreview }));
  assert.match(tree, /••••/); assert.doesNotMatch(tree, /54,321|77.77/); assert.match(tree, /100.00%/);
  assert.equal(JSON.stringify({ portfolio, valuation }), original);
});

test('web metric details and holding inputs do not render personal amounts or editable hidden values', () => {
  let hidden = true;
  const state = mountWebPrivacy('account-a', { getItem: () => 'true' });
  const privacy = { usePrivateValue: state.privacy.usePrivateValue, usePrivateText: state.privacy.usePrivateText,
    usePortfolioPrivacy: () => ({ hideValues: hidden }) };
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useRef: value => ({ current: value }), useEffect: () => {},
    useState: initial => [typeof initial === 'function' ? initial() : initial, () => {}],
  };
  const { MetricAmountDialog } = load('src/pages/analytics/components/MetricAmountDialog.tsx', {
    react, '../../../privacy/PortfolioPrivacy': privacy, '../AnalyticsIntegration.module.css': {},
  }, { React: react });
  const content = { title: 'Return', percentage: '+12.34%', amount: '+$1,523.70', amountLabel: 'Change', reference: 'Based on $12,345.67.', explanation: 'Historical results.', tone: 'positive' };
  let tree = JSON.stringify(MetricAmountDialog({ content, onClose: () => {} }));
  assert.match(tree, /\+12.34%/); assert.match(tree, /••••/); assert.doesNotMatch(tree, /1,523|12,345/);
  content.percentage = '฿54,321.00'; tree = JSON.stringify(MetricAmountDialog({ content, onClose: () => {} }));
  assert.doesNotMatch(tree, /54,321/);
  const { HoldingDecimalInput } = load('src/pages/portfolios/components/HoldingDecimalInput.tsx', {
    react, '../../../privacy/PortfolioPrivacy': privacy,
    '../portfolioUi': { formatHoldingDecimalInput: value => Number(value).toFixed(2) }, '../PortfolioIntegration.module.css': {},
  }, { React: react });
  let edits = 0;
  let input = HoldingDecimalInput({ value: '12345.67', onValueChange: () => { edits++; } }).children[0];
  assert.equal(input.props.value, ''); assert.equal(input.props.placeholder, '••••'); assert.equal(input.props.disabled, true);
  assert.doesNotMatch(JSON.stringify(input), /12345/);
  input.props.onChange({ target: { value: '222.22' } }); assert.equal(edits, 0);
  hidden = false; input = HoldingDecimalInput({ value: '12345.67', onValueChange: () => { edits++; } }).children[0];
  assert.equal(input.props.value, '12345.67'); input.props.onChange({ target: { value: '222.22' } }); assert.equal(edits, 1);
});

test('web privacy covers result surfaces without masking public prices, FX, or normalized charts', () => {
  const files = [
    'src/components/portfolio/HoldingsTable.tsx', 'src/pages/dashboard/components/DashboardKpiGrid.tsx',
    'src/pages/portfolios/PortfolioDetailView.tsx', 'src/pages/analytics/components/AnalysisResults.tsx',
    'src/pages/reports/AssetRiskDetailPage.tsx', 'src/pages/simulations/components/SimulationResults.tsx',
  ];
  let masked = 0, publicPrices = 0;
  for (const file of files) {
    const source = fs.readFileSync(path.join(root, file), 'utf8');
    assert.match(source, /usePrivateValue/);
    const ast = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    function visit(node) {
      if (ts.isCallExpression(node) && node.expression.getText(ast) === 'formatPortfolioMoney') {
        const publicPrice = node.arguments[0].getText(ast).includes('asset_price');
        const wrapped = ts.isCallExpression(node.parent) && node.parent.expression.getText(ast) === 'privateValue';
        assert.equal(wrapped, !publicPrice, `${file}: ${node.getText(ast)}`);
        if (publicPrice) publicPrices++; else masked++;
      }
      ts.forEachChild(node, visit);
    }
    visit(ast);
  }
  assert.ok(masked > 15); assert.ok(publicPrices > 0);
  const chart = fs.readFileSync(path.join(root, 'src/pages/simulations/components/SimulationTrajectoryChart.tsx'), 'utf8');
  assert.match(chart, /normalized_value/); assert.doesNotMatch(chart, /formatPortfolioMoney/);
  const main = fs.readFileSync(path.join(root, 'src/main.tsx'), 'utf8'); assert.match(main, /<PortfolioPrivacyProvider><LearnProgressProvider><App \/><\/LearnProgressProvider><\/PortfolioPrivacyProvider>/);
  const assistant = fs.readFileSync(path.join(root, 'src/pages/assistant/AssistantPage.tsx'), 'utf8');
  assert.match(assistant, /if \(sendingRef.current \|\| hideValues\) return/);
  assert.ok(assistant.indexOf('if (hideValues) return') < assistant.indexOf('{messages.map'));
  assert.match(assistant, /AI chat hidden for privacy/);
});

test('web profile Sign Out prompts first and only confirmed logout navigates to sign in', async () => {
  const slots = []; let cursor = 0, dirty, tree, logouts = 0, fail = true;
  const navigations = [];
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useState: initial => {
      const i = cursor++; if (!(i in slots)) slots[i] = initial;
      return [slots[i], value => { slots[i] = typeof value === 'function' ? value(slots[i]) : value; dirty = true; }];
    },
    useRef: initial => { const i = cursor++; return slots[i] ??= { current: initial }; },
  };
  const { ProfileMenu } = load('src/components/navigation/ProfileMenu.tsx', {
    react,
    '../../app/routes': { go: route => navigations.push(route) },
    '../../auth/accountIdentity': { accountDisplayName: () => 'Aura User', accountInitials: () => 'AU' },
    '../../auth/useAuth': { useAuth: () => ({ user: { email: 'user@example.com' }, logout: () => {
      logouts++; if (fail) throw Error('storage failed');
    } }) },
    '../ui/Icon': { Icon: 'Icon' }, '../ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
  }, { React: react });
  const render = () => { cursor = 0; dirty = false; tree = ProfileMenu(); };
  const settle = async () => { await new Promise(done => setImmediate(done)); if (dirty) render(); };
  const request = async () => {
    tree.children[0].props.onClick(); await settle();
    tree.children[1].children.at(-1).props.onClick(); await settle();
  };
  const dialog = () => tree.children[2];
  render(); await request();
  assert.equal(logouts, 0); assert.deepEqual(navigations, []);
  assert.equal(tree.children[1], false, 'menu closes when confirmation opens');
  assert.equal(dialog().props.title, 'Sign out?');
  assert.equal(dialog().props.tone, 'danger'); assert.equal(dialog().props.iconName, 'logout');
  assert.equal(dialog().props.subject, 'user@example.com');
  assert.match(dialog().props.description, /will not be deleted/);
  const staleConfirm = dialog().props.onConfirm;
  dialog().props.onCancel(); await settle(); staleConfirm(); await settle();
  assert.equal(logouts, 0); assert.equal(dialog(), false);
  await request(); dialog().props.onConfirm(); await settle();
  assert.equal(logouts, 1); assert.ok(dialog().props.error); assert.deepEqual(navigations, []);
  fail = false;
  dialog().props.onConfirm(); dialog().props.onConfirm(); await settle();
  assert.equal(logouts, 2); assert.deepEqual(navigations, ['login']); assert.equal(dialog(), false);
});

test('web red dialogs have red Close/Cancel text and a centered accessible SVG close icon', () => {
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useEffect: () => {}, useRef: value => ({ current: value }),
  };
  const { ConfirmationDialog } = load('src/components/ui/ConfirmationDialog.tsx', {
    react, 'react-dom': { createPortal: node => node },
    './ApiErrorState': { FormErrorSummary: 'Error' }, './Icon': { Icon: 'Icon' },
    './ConfirmationDialog.module.css': { close: 'close', cancel: 'cancel', dangerTheme: 'dangerTheme' },
  }, { React: react, document: { body: {} } });
  for (const busy of [false, true]) {
    let cancelled = 0;
    const tree = ConfirmationDialog({ title: 'Delete account?', description: 'Permanent', subject: 'user@example.com', subjectLabel: 'Account', confirmLabel: 'Delete Account', tone: 'danger', busy, onCancel: () => { cancelled++; }, onConfirm: () => {} });
    const nodes = [];
    function visit(node) { if (!node || typeof node !== 'object') return; nodes.push(node); node.children?.forEach(visit); }
    visit(tree);
    const close = nodes.find(node => node.type === 'button' && node.props.className === 'close');
    const cancel = nodes.find(node => node.type === 'button' && node.children[0] === 'Cancel');
    assert.equal(close.props['aria-label'], 'Close delete account?');
    assert.equal(close.children[0].props.name, 'close');
    assert.equal(close.children[0].props.size, 18);
    assert.equal(close.props.disabled, busy); assert.equal(cancel.props.disabled, busy);
    if (!busy) { close.props.onClick(); cancel.props.onClick(); assert.equal(cancelled, 2); }
  }
  const styles = fs.readFileSync(path.join(root, 'src/components/ui/ConfirmationDialog.module.css'), 'utf8');
  assert.match(styles, /\.close \{[^}]*display: grid; place-items: center; padding: 0;/);
  assert.match(styles, /\.dangerTheme \.close, \.dangerTheme \.cancel \{ color: var\(--red-bright\)/);
  assert.match(styles, /\.dangerTheme \.close:hover, \.dangerTheme \.close:focus-visible, \.dangerTheme \.cancel:hover, \.dangerTheme \.cancel:focus-visible \{ color: var\(--red-bright\)/);
  const { Icon } = load('src/components/ui/Icon.tsx', {}, { React: react });
  assert.equal(Icon({ name: 'close' }).children[0].props.d, 'm6 6 12 12M18 6 6 18');
});

test('account deletion password field matches mobile dark red without changing other settings fields', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const section = read('src/pages/settings/components/DeleteAccountSection.tsx');
  const styles = read('src/pages/settings/SettingsPage.module.css');
  const mobile = read('../mobile/src/screens/settings/DeleteAccountSection.tsx');
  assert.match(section, /styles\.passwordFields} \$\{styles\.deletePassword/);
  assert.match(mobile, /backgroundColor: '#150a10'/);
  assert.match(styles, /\.passwordFields\.deletePassword input \{ background: #150a10; border-color: rgba\(255, 107, 122, \.4\)/);
  assert.match(styles, /\.passwordFields\.deletePassword input:focus \{ background: #150a10; border-color: var\(--red-primary\)/);
  assert.match(styles, /\.passwordFields\.deletePassword input:focus-visible \{ outline: 3px solid rgba\(255, 107, 122, \.4\); outline-offset: 2px;/);
  assert.match(styles, /\.passwordFields\.deletePassword input::selection \{ background: rgba\(255, 107, 122, \.35\)/);
  assert.doesNotMatch(read('src/pages/settings/SettingsPage.tsx'), /deletePassword/);
});

test('web sign out clears authenticated state even when token storage removal fails', () => {
  const updates = [];
  const react = {
    createContext: () => ({ Provider: 'Provider' }),
    createElement: (_type, props) => props.value,
    useState: initial => [initial, value => updates.push(value)],
    useRef: initial => ({ current: initial }),
    useCallback: fn => fn,
    useMemo: fn => fn(),
    useEffect: () => {},
  };
  const { AuthProvider } = load('src/auth/AuthContext.tsx', {
    react,
    '../api/authApi': {},
    '../api/apiClient': { ApiError: Error, configureApiAuthentication: () => {} },
    './authStorage': { clearAccessToken: () => { throw Error('storage unavailable'); } },
  }, { React: react });
  assert.throws(() => AuthProvider({}).logout(), /storage unavailable/);
  assert.deepEqual(updates, [null, null, 'unauthenticated']);
});

test('web account deletion uses authenticated DELETE and accepts an empty 204', async () => {
  const calls = [];
  const transport = load('src/api/apiClient.ts', {
    '../config/environment': { environment: { apiBaseUrl: 'http://example.invalid' } },
  }, { fetch: async (url, options) => {
    calls.push({ url, options }); return { status: 204, ok: true, text: async () => '' };
  } });
  const api = load('src/api/authApi.ts', { './apiClient': transport });
  assert.equal(await api.deleteCurrentUserAccount({ current_password: 'current-password' }, { token: 'token' }), undefined);
  assert.equal(calls[0].url, 'http://example.invalid/api/auth/me');
  assert.equal(calls[0].options.method, 'DELETE');
  assert.equal(calls[0].options.headers.get('Authorization'), 'Bearer token');
  assert.deepEqual(JSON.parse(calls[0].options.body), { current_password: 'current-password' });
});

test('web account deletion confirms password, supports cancel/retry, blocks duplicates, and signs out after success', async () => {
  for (const logoutThrows of [false, true]) {
    const slots = []; let cursor = 0, dirty, tree;
    const react = {
      createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
      useState: initial => {
        const i = cursor++; if (!(i in slots)) slots[i] = initial;
        return [slots[i], value => { slots[i] = value; dirty = true; }];
      },
      useRef: initial => { const i = cursor++; return slots[i] ??= { current: initial }; },
    };
    const calls = []; let fail = true, signedOut = 0, resolve;
    const { DeleteAccountSection } = load('src/pages/settings/components/DeleteAccountSection.tsx', {
      react,
      '../../../api/authApi': { deleteCurrentUserAccount: async request => {
        calls.push(plain(request)); if (fail) throw Error('wrong password'); await new Promise(done => { resolve = done; });
      } },
      '../../../auth/useAuth': { useAuth: () => ({ user: { email: 'user@example.com' }, logout: () => {
        signedOut++; if (logoutThrows) throw Error('storage unavailable');
      } }) },
      '../../../components/ui/Card': { Card: 'Card' },
      '../../../components/ui/Icon': { Icon: 'Icon' },
      '../../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
      '../SettingsPage.module.css': {},
    }, { React: react });
    const render = () => { cursor = 0; dirty = false; tree = DeleteAccountSection({}); };
    const settle = async () => { for (let i = 0; i < 5; i++) { await new Promise(done => setImmediate(done)); if (dirty) render(); } };
    const button = () => tree.children[0].children[1];
    const dialog = () => tree.children[1];
    const password = value => dialog().children[0].children[0].children[1].props.onChange({ target: { value } });
    render(); assert.equal(calls.length, 0);
    button().props.onClick(); await settle();
    assert.equal(dialog().props.tone, 'danger');
    assert.equal(dialog().props.confirmDisabled, true);
    dialog().props.onConfirm(); await settle(); assert.equal(calls.length, 0);
    password('current-password'); await settle();
    dialog().props.onCancel(); await settle(); assert.equal(calls.length, 0);
    button().props.onClick(); await settle();
    assert.equal(dialog().props.confirmDisabled, true, 'cancel clears the secret');
    password('current-password'); await settle();
    dialog().props.onConfirm(); await settle();
    assert.equal(dialog().props.error.message, 'wrong password'); assert.equal(signedOut, 0);
    fail = false;
    dialog().props.onConfirm(); dialog().props.onConfirm(); await settle();
    assert.equal(calls.length, 2); assert.equal(dialog().props.busy, true);
    dialog().props.onCancel(); await settle(); assert.ok(dialog());
    resolve(); await settle();
    assert.equal(signedOut, 1); assert.equal(dialog(), false); assert.equal(button().props.disabled, true);
    assert.deepEqual(calls[1], { current_password: 'current-password' });
  }
  const settings = fs.readFileSync(path.join(root, 'src/pages/settings/SettingsPage.tsx'), 'utf8');
  assert.ok(settings.indexOf('<DeleteAccountSection') > settings.indexOf('<DeferredSettingsSections'));
});

test('web simulation deletion requires confirmation and only updates history after success', async () => {
  const slots = []; let cursor = 0, dirty, tree;
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useState: initial => {
      const i = cursor++; if (!(i in slots)) slots[i] = initial;
      return [slots[i], value => { slots[i] = value; dirty = true; }];
    },
    useRef: initial => { const i = cursor++; return slots[i] ??= { current: initial }; },
    useEffect: () => {}
  };
  const calls = []; let fail = true, deleted = 0, resolve;
  const { DeleteSimulationButton } = load('src/pages/simulations/components/DeleteSimulationButton.tsx', {
    react,
    '../../../api/simulationsApi': { deleteSimulationHistory: async (...ids) => {
      calls.push(ids); if (fail) throw Error('offline'); await new Promise(done => { resolve = done; });
    } },
    '../../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
    '../SimulationIntegration.module.css': {}
  }, { React: react });
  const render = () => { cursor = 0; dirty = false; tree = DeleteSimulationButton({ portfolioId: 'a', simulationId: 'b', subject: 'snapshot b', onDeleted: () => { deleted++; } }); };
  const settle = async () => { for (let i = 0; i < 5; i++) { await new Promise(done => setImmediate(done)); if (dirty) render(); } };
  render(); assert.equal(tree.children[1], false); assert.equal(calls.length, 0);
  tree.children[0].props.onClick(); await settle();
  assert.equal(tree.children[1].props.tone, 'danger');
  tree.children[1].props.onCancel(); await settle(); assert.equal(calls.length, 0);
  tree.children[0].props.onClick(); await settle(); tree.children[1].props.onConfirm(); await settle();
  assert.equal(tree.children[1].props.error.message, 'offline'); assert.equal(deleted, 0);
  fail = false;
  tree.children[1].props.onConfirm(); tree.children[1].props.onConfirm(); await settle();
  assert.equal(calls.length, 2); assert.equal(tree.children[1].props.busy, true);
  tree.children[1].props.onCancel(); await settle(); assert.ok(tree.children[1]);
  resolve(); await settle(); assert.equal(deleted, 1); assert.equal(tree.children[1], false);
  assert.deepEqual(plain(calls[1]), ['a', 'b']);
  for (const file of ['components/SimulationHistory.tsx', 'SimulationHistoryDetailPage.tsx']) {
    assert.match(fs.readFileSync(path.join(root, `src/pages/simulations/${file}`), 'utf8'), /<DeleteSimulationButton/);
  }
});

test('web simulation delete uses the authenticated transport and handles 204', async () => {
  const calls = [];
  const transport = load('src/api/apiClient.ts', {
    '../config/environment': { environment: { apiBaseUrl: 'http://example.invalid' } },
  }, { fetch: async (url, options) => {
    calls.push({ url, options }); return { status: 204, ok: true, text: async () => '' };
  } });
  const api = load('src/api/simulationsApi.ts', { './apiClient': transport });
  assert.equal(await api.deleteSimulationHistory('a/b', 'c/d', { token: 'token' }), undefined);
  assert.ok(calls[0].url.endsWith('/api/portfolios/a%2Fb/simulations/c%2Fd'));
  assert.equal(calls[0].options.method, 'DELETE');
  assert.equal(calls[0].options.headers.get('Authorization'), 'Bearer token');
});

test('simulation deletion uses a red-only dialog and right-aligned history actions', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const dialog = read('src/components/ui/ConfirmationDialog.module.css');
  const history = read('src/pages/simulations/SimulationIntegration.module.css');
  assert.match(dialog, /\.dangerTheme \.accent \{ background: var\(--red-bright\);/);
  assert.match(dialog, /\.dangerTheme button:focus-visible \{ outline: 3px solid rgba\(255, 89, 100, \.5\)/);
  assert.match(dialog, /\.dangerTheme \.danger \{[^}]*background: var\(--red-bright\)/);
  assert.match(history, /\.historyTable th:last-child \{ text-align: right;/);
  assert.match(history, /\.historyTable td:last-child \{ width: 1%; white-space: nowrap;/);
  assert.match(history, /\.historyTable \.historyActions \{ justify-content: flex-end; flex-wrap: nowrap;/);
  assert.match(read('src/pages/simulations/components/SimulationHistory.tsx'), /styles\.historyTable/);
});

test('both welcome brand links return to the top without hash navigation', () => {
  for (const reducedMotion of [false, true]) {
    const scrolls = [];
    const focusCalls = [];
    const stateUpdates = [];
    const WelcomePage = load('src/pages/welcome/WelcomePage.tsx', {
      react: {
        useEffect: () => {},
        useRef: () => ({ current: null }),
        useState: initial => [initial, value => stateUpdates.push(value)],
      },
      '../../components/ui/Icon': { Icon: 'Icon' },
      './WelcomePage.module.css': {},
    }, {
      React: { createElement: (type, props, ...children) => ({ type, props, children }) },
      window: {
        matchMedia: () => ({ matches: reducedMotion }),
        scrollTo: options => scrolls.push(plain(options)),
      },
      document: { getElementById: id => id === 'welcome-main'
        ? { focus: options => focusCalls.push(plain(options)) } : null },
    }).WelcomePage;
    const brandLinks = [];
    function collect(node) {
      if (Array.isArray(node)) return node.forEach(collect);
      if (!node || typeof node !== 'object') return;
      if (typeof node.type === 'function' && node.type.name === 'Brand') {
        brandLinks.push(node.type(node.props));
      }
      node.children?.forEach(collect);
    }
    collect(WelcomePage());
    assert.equal(brandLinks.length, 2);
    for (const link of brandLinks) {
      let prevented = false;
      link.props.onClick({ preventDefault: () => { prevented = true; } });
      assert.ok(prevented);
      assert.deepEqual(scrolls.at(-1), { top: 0, behavior: reducedMotion ? 'instant' : 'smooth' });
      assert.deepEqual(focusCalls.at(-1), { preventScroll: true });
      assert.equal(stateUpdates.at(-1), false);
    }
    const previousScrollCount = scrolls.length;
    brandLinks[0].props.onClick({ ctrlKey: true, preventDefault: () => assert.fail('Preserve modified link clicks') });
    assert.equal(scrolls.length, previousScrollCount);
    assert.equal(brandLinks[0].props.href, '#/welcome');
  }
});

test('public entry defaults to welcome and preserves saved-result deep links', () => {
  const location = { hash: '' };
  const routes = load('src/app/routes.ts', {}, { window: { location } });
  assert.equal(routes.routeFromHash().page, 'welcome');
  location.hash = '#/';
  assert.equal(routes.routeFromHash().page, 'welcome');
  location.hash = '#/assistant/portfolio-1/simulation/run-2';
  assert.deepEqual(plain(routes.routeFromHash()), {
    page: 'assistant', id: 'portfolio-1', reportId: 'simulation', contextId: 'run-2',
  });
  routes.go('signup');
  assert.equal(routes.routeFromHash().page, 'signup');
  routes.go('login');
  assert.equal(routes.routeFromHash().page, 'login');
});

test('welcome is public only after session restoration and protected pages remain protected', () => {
  let route = { page: 'welcome' };
  let status = 'unauthenticated';
  let effects = [];
  const redirects = [];
  const mocks = {
    react: { useEffect: effect => effects.push(effect) },
    '../auth/useAuth': { useAuth: () => ({ status }) },
    '../hooks/useHashRoute': { useHashRoute: () => route },
    './routes': { go: destination => redirects.push(destination) },
  };
  const components = {
    '../auth/ProtectedRoute': 'ProtectedRoute', './AppLayout': 'AppLayout',
    '../pages/analytics/AnalyticsPage': 'AnalyticsPage',
    '../pages/assistant/AssistantPage': 'AssistantPage',
    '../pages/auth/LoginPage': 'LoginPage', '../pages/auth/RegisterPage': 'RegisterPage',
    '../pages/dashboard/DashboardPage': 'DashboardPage', '../pages/learn/LearnPage': 'LearnPage',
    '../pages/not-found/NotFoundPage': 'NotFoundPage',
    '../pages/portfolios/CreatePortfolioPage': 'CreatePortfolioPage',
    '../pages/portfolios/PortfolioDetailPage': 'PortfolioDetailPage',
    '../pages/portfolios/PortfoliosPage': 'PortfoliosPage',
    '../pages/reports/ReportsPage': 'ReportsPage', '../pages/reports/ReportDetailPage': 'ReportDetailPage',
    '../pages/reports/AssetRiskDetailPage': 'AssetRiskDetailPage',
    '../pages/settings/SettingsPage': 'SettingsPage', '../pages/simulations/SimulationsPage': 'SimulationsPage',
    '../pages/help/HelpSupportPage': 'HelpSupportPage',
    '../pages/notifications/NotificationsPage': 'NotificationsPage',
    '../pages/simulations/SimulationHistoryDetailPage': 'SimulationHistoryDetailPage',
    '../pages/watchlist/WatchlistPage': 'WatchlistPage', '../pages/welcome/WelcomePage': 'WelcomePage',
  };
  for (const [moduleName, component] of Object.entries(components)) {
    mocks[moduleName] = { [component]: component };
  }
  const App = load('src/app/App.tsx', mocks, {
    React: { createElement: (type, props, ...children) => ({ type, props, children }) },
  }).default;
  const render = () => {
    effects = [];
    const output = App();
    effects.forEach(effect => effect());
    return output;
  };
  assert.equal(render().type, 'WelcomePage');
  status = 'initializing';
  assert.equal(render().type, 'ProtectedRoute');
  assert.deepEqual(redirects, []);
  status = 'authenticated';
  for (const page of ['welcome', 'login', 'signup']) {
    route = { page };
    assert.equal(render(), null);
    assert.equal(redirects.at(-1), 'dashboard');
  }
  status = 'unauthenticated';
  route = { page: 'login' };
  assert.equal(render().type, 'LoginPage');
  route = { page: 'signup' };
  assert.equal(render().type, 'RegisterPage');
  route = { page: 'reports', id: 'portfolio-1', reportId: 'report-2' };
  const protectedResult = render();
  assert.equal(protectedResult.type, 'ProtectedRoute');
  assert.equal(protectedResult.children[0].type, 'AppLayout');
  const report = protectedResult.children[0].children[0];
  assert.equal(report.type, 'ReportDetailPage');
  assert.equal(report.props.portfolioId, 'portfolio-1');
  assert.equal(report.props.reportId, 'report-2');
  route = { page: 'help' };
  const help = render();
  assert.equal(help.type, 'ProtectedRoute');
  assert.equal(help.children[0].type, 'AppLayout');
  assert.equal(help.children[0].children[0].type, 'HelpSupportPage');
});

test('current and planned holding validation preserves facts and never creates weights', () => {
  const validation = load('src/pages/portfolios/portfolioValidation.ts', {
    './supportedAssetSymbols': { supportedAssetSymbols },
  });
  const current = validation.validateRealHoldingDrafts([{
    id: 1,
    symbol: ' aapl ',
    shares: '5.5',
  }]);
  assert.equal(current.error, null);
  assert.deepEqual(plain(current.holdings), [{
    symbol: 'AAPL',
    shares: '5.5',
  }]);
  assert.ok(!('weight' in current.holdings[0]));

  const planned = validation.validatePlannedHoldingDrafts([
    { id: 1, symbol: ' aapl ', proposedAmount: '4000' },
    { id: 2, symbol: 'NVDA', proposedAmount: '6000.00' },
  ]);
  assert.equal(planned.error, null);
  assert.deepEqual(plain(planned.holdings), [
    { symbol: 'AAPL', proposed_amount: '4000' },
    { symbol: 'NVDA', proposed_amount: '6000.00' },
  ]);
  assert.ok(planned.holdings.every(holding => !('weight' in holding) && !('shares' in holding)));

  const invalid = validation.validateRealHoldingDrafts([{
    id: 3,
    symbol: 'AAPL',
    shares: '0',
  }]);
  assert.deepEqual(plain(invalid.issue), {
    index: 0,
    field: 'shares',
    message: invalid.error,
  });

  const excessSharePrecision = validation.validateRealHoldingDrafts([{
    id: 4,
    symbol: 'AAPL',
    shares: '10.125',
  }]);
  assert.match(excessSharePrecision.error, /up to 2 decimal places/);
  const unsupported = validation.validateRealHoldingDrafts([{
    id: 5,
    symbol: 'ASDF',
    shares: '10.50',
  }]);
  assert.deepEqual(plain(unsupported.issue), {
    index: 0,
    field: 'symbol',
    message: `ASDF is not supported. Choose one of Aura's 17 available assets.`,
  });
  assert.match(validation.validatePlannedHoldingDrafts([{
    id: 6,
    symbol: 'ASDF',
    proposedAmount: '1000.00',
  }]).error, /ASDF is not supported/);
});

test('portfolio input warnings identify, reveal, and focus the first invalid web field', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const warning = read('src/pages/portfolios/portfolioInputWarning.ts');
  const create = read('src/pages/portfolios/PortfolioCreateFlow.tsx');
  const editor = read('src/pages/portfolios/components/PortfolioHoldingsEditor.tsx');
  const symbol = read('src/pages/portfolios/components/AssetSymbolField.tsx');
  const dialog = read('src/pages/portfolios/components/PortfolioInputWarningDialog.tsx');
  const styles = read('src/pages/portfolios/PortfolioIntegration.module.css');

  assert.doesNotMatch(warning, /window\.alert/);
  assert.match(warning, /scrollIntoView\(\{ behavior: 'smooth', block: 'center' \}\)/);
  assert.match(warning, /element\.focus\(\{ preventScroll: true \}\)/);
  assert.match(warning, /apiValidationIssues\(error\)/);
  assert.match(create, /presentInputWarning\(localHoldingInputWarning/);
  assert.match(editor, /presentInputWarning\(localHoldingInputWarning/);
  assert.match(symbol, /aria-invalid=\{Boolean\(error\)\}/);
  assert.match(dialog, /createPortal/);
  assert.match(dialog, /role="alertdialog"/);
  assert.match(dialog, /Check your information/);
  assert.match(dialog, /Show input/);
  assert.match(create, /<PortfolioInputWarningDialog/);
  assert.match(editor, /<PortfolioInputWarningDialog/);
  assert.match(create, /placeholder="10\.50"/);
  assert.match(editor, /placeholder="10\.50"/);
  const pickerButtonStyles = styles.match(
    /\.assetSymbolPickerButton\s*\{[\s\S]*?\}/,
  )?.[0] ?? '';
  assert.match(pickerButtonStyles, /height:\s*34px/);
  assert.doesNotMatch(pickerButtonStyles, /bottom:/);
});

test('current, planned, and legacy allocation displays consume their authoritative source', () => {
  class ApiError extends Error {}
  const portfolioUi = load('src/pages/portfolios/portfolioUi.ts', {
    '../../api/apiClient': { ApiError },
  });
  const base = { id: 'portfolio', name: 'Test', plan_currency: null, source_plan_id: null, created_at: '', updated_at: '' };
  const current = { ...base, portfolio_type: 'CURRENT', holdings: [] };
  const planned = { ...base, portfolio_type: 'PLANNED', plan_currency: 'USD', holdings: [] };
  const legacy = { ...base, portfolio_type: 'LEGACY', holdings: [{ symbol: 'BND', weight: 1 }] };

  assert.deepEqual(plain(portfolioUi.resolvedPortfolioAllocation(current, {
    holdings: [{ symbol: 'AAPL', current_allocation: '0.625' }],
  }, null)), [{ symbol: 'AAPL', weight: 0.625 }]);
  assert.deepEqual(plain(portfolioUi.resolvedPortfolioAllocation(planned, null, {
    holdings: [{ symbol: 'NVDA', target_allocation: '0.4' }],
  })), [{ symbol: 'NVDA', weight: 0.4 }]);
  assert.deepEqual(plain(portfolioUi.resolvedPortfolioAllocation(legacy, null, null)), [{ symbol: 'BND', weight: 1 }]);
  assert.equal(portfolioUi.formatPortfolioQuantity('10.125'), '10.13');
  assert.equal(portfolioUi.formatPortfolioQuantity('10'), '10.00');
  assert.equal(portfolioUi.formatHoldingDecimalInput('1000.000000000000'), '1000.00');
});

test('simulation editors initialize from backend current and planned weights in saved order', () => {
  class ApiError extends Error {}
  const simulation = load('src/pages/simulations/simulationUi.ts', {
    '../../api/apiClient': { ApiError },
  });
  assert.deepEqual(plain(simulation.allocationInputsFromValuation({ holdings: [
    { symbol: 'MSFT', current_allocation: '0.625' },
    { symbol: 'AAPL', current_allocation: '0.375' },
  ] })), { MSFT: '62.50', AAPL: '37.50' });
  assert.deepEqual(plain(simulation.allocationInputsFromPlannedAllocation({ holdings: [
    { symbol: 'AAPL', target_allocation: '0.4' },
    { symbol: 'NVDA', target_allocation: '0.6' },
  ] })), { AAPL: '40.00', NVDA: '60.00' });
  assert.deepEqual(plain(simulation.allocationInputsFromValuation({ holdings: [
    { symbol: 'AAPL', current_allocation: '0.3333333333' },
    { symbol: 'MSFT', current_allocation: '0.3333333333' },
    { symbol: 'NVDA', current_allocation: '0.3333333334' },
  ] })), { AAPL: '33.33', MSFT: '33.33', NVDA: '33.34' });

  const initial = { AAPL: '40.00', MSFT: '35.00', NVDA: '25.00' };
  const rebalanced = simulation.rebalanceAllocationInputs(
    initial,
    ['AAPL', 'MSFT'],
    'AAPL',
    '50',
  );
  assert.deepEqual(plain(rebalanced), {
    AAPL: '50',
    MSFT: '25.00',
    NVDA: '25.00',
  });
  assert.equal(Object.values(rebalanced).reduce((total, value) => total + Number(value), 0), 100);
  assert.deepEqual(initial, { AAPL: '40.00', MSFT: '35.00', NVDA: '25.00' });
  assert.deepEqual(plain(simulation.rebalanceAllocationInputs(
    rebalanced,
    ['AAPL', 'MSFT'],
    'AAPL',
    '20.00',
  )), { AAPL: '20.00', MSFT: '55.00', NVDA: '25.00' });
  assert.deepEqual(plain(simulation.rebalanceAllocationInputs(
    { AAPL: '100.00', MSFT: '0.00', NVDA: '0.00' },
    ['AAPL', 'MSFT'],
    'AAPL',
    '40.00',
  )), { AAPL: '40.00', MSFT: '60.00', NVDA: '0.00' });
  assert.deepEqual(plain(simulation.rebalanceAllocationInputs(
    { AAPL: '39.95', MSFT: '54.31', GOOG: '5.74' },
    ['MSFT', 'GOOG'],
    'MSFT',
    '55.00',
  )), { AAPL: '39.95', MSFT: '55.00', GOOG: '5.05' });

  const portfolio = { holdings: [{ symbol: 'BND' }, { symbol: 'AAPL' }] };
  const result = simulation.validateModifiedAllocation(portfolio, { AAPL: '75', BND: '25' });
  assert.equal(result.error, null);
  assert.deepEqual(plain(result.allocation), [
    { symbol: 'BND', weight: 0.25 },
    { symbol: 'AAPL', weight: 0.75 },
  ]);
  assert.match(
    simulation.validateModifiedAllocation(portfolio, { AAPL: '75.001', BND: '24.999' }).error,
    /needs an allocation/,
  );
});

test('allocation and combined web modes use the two-target allocation editor', () => {
  const page = fs.readFileSync(path.join(root, 'src/pages/simulations/SimulationsPage.tsx'), 'utf8');
  const editor = fs.readFileSync(path.join(root, 'src/pages/simulations/components/AllocationEditor.tsx'), 'utf8');
  const results = fs.readFileSync(path.join(root, 'src/pages/simulations/components/SimulationResults.tsx'), 'utf8');
  assert.match(page, /rebalanceAllocationInputs/);
  assert.match(page, /mode !== 'historical-scenario'/);
  assert.match(editor, /step="0\.01"/);
  assert.match(editor, /percent\.toFixed\(2\)/);
  assert.match(editor, /Select exactly two assets/);
  assert.match(editor, /selectedSymbols\.length >= 2/);
  assert.match(editor, /disabled=\{disabled \|\| !selected/);
  assert.match(editor, /role="checkbox"/);
  assert.match(editor, /onClick=\{\(\) => \{ if \(!selectionDisabled\) toggleTarget/);
  assert.match(editor, /onClick=\{event => event\.stopPropagation\(\)\}/);
  assert.match(results, /Latest Saved Portfolio Analysis/);
  assert.match(results, /result\.type === 'allocation'/);
  assert.match(results, /backend original and modified results over the same requested period/);
  assert.match(results, /View latest analysis details/);
  assert.match(results, /Latest Portfolio Analysis vs New Combined Simulation/);
  assert.match(results, /metrics=\{response\.modified\.metrics\}/);
  assert.match(results, /combined=\{response\.modified\.trajectory\}/);
  assert.match(results, /label: 'New combined result'/);
});

test('web historical scenarios compare the latest saved analysis with the event result', () => {
  const page = fs.readFileSync(path.join(root, 'src/pages/simulations/SimulationsPage.tsx'), 'utf8');
  const results = fs.readFileSync(path.join(root, 'src/pages/simulations/components/SimulationResults.tsx'), 'utf8');

  assert.match(page, /setOriginalAllocation\(savedAllocation\)/);
  assert.match(page, /listPortfolioReports\(selectedPortfolioId/);
  assert.match(page, /getPortfolioReport\(selectedPortfolioId, newest\.id/);
  assert.match(page, /latestAnalysis=\{latestAnalysis\}/);
  assert.match(results, /Latest Portfolio Analysis vs Historical Scenario/);
  assert.match(results, /reference\.portfolio_metrics\.cumulative_return/);
  assert.match(results, /reference\.max_drawdown\.max_drawdown/);
  assert.match(results, /View latest analysis details/);
  assert.match(results, /Allocation used by this scenario run/);
  assert.match(results, /savedAnalysisTrajectory\(latestAnalysis\.analysis\)/);
  assert.doesNotMatch(results, /no-movement comparison line/);
  assert.doesNotMatch(results, /normalized_ending_value\s*[-+*/]/);
});

test('web reconstructs a normalized display path from saved backend return observations', () => {
  class ApiError extends Error {}
  const simulation = load('src/pages/simulations/simulationUi.ts', {
    '../../api/apiClient': { ApiError },
  });
  const analysis = {
    start_date: '2026-01-01',
    portfolio_returns: [
      { date: '2026-01-02', portfolio_return: 0.1 },
      { date: '2026-01-03', portfolio_return: -0.1 },
    ],
  };
  assert.deepEqual(plain(simulation.savedAnalysisTrajectory(analysis)), [
    { date: '2026-01-01', normalized_value: 1 },
    { date: '2026-01-02', normalized_value: 1.1 },
    { date: '2026-01-03', normalized_value: 0.9900000000000001 },
  ]);
  assert.deepEqual(analysis.portfolio_returns, [
    { date: '2026-01-02', portfolio_return: 0.1 },
    { date: '2026-01-03', portfolio_return: -0.1 },
  ]);
});

test('portfolio API sends typed payloads and uses planned allocation endpoints', async () => {
  const calls = [];
  const api = load('src/api/portfoliosApi.ts', {
    './apiClient': {
      apiRequest: async (requestPath, options = {}) => {
        calls.push({ path: requestPath, options });
        return {};
      },
    },
  });
  const id = '10000000-0000-0000-0000-000000000001';
  await api.createPortfolio({ name: 'Plan', portfolio_type: 'PLANNED', plan_currency: 'THB' });
  await api.replacePlannedPortfolioHoldings(id, [{ symbol: 'AAPL', proposed_amount: '10000' }]);
  await api.getPlannedPortfolioAllocation(id);
  await api.getPlannedPortfolioPreview(id);

  assert.deepEqual(plain(calls[0].options.body), { name: 'Plan', portfolio_type: 'PLANNED', plan_currency: 'THB' });
  assert.deepEqual(plain(calls[1].options.body), { holdings: [{ symbol: 'AAPL', proposed_amount: '10000' }] });
  assert.equal(calls[2].path, `/api/portfolios/${id}/planned-allocation`);
  assert.equal(calls[3].path, `/api/portfolios/${id}/planned-preview`);
});

test('web Watchlist uses the authenticated backend contract and backend metrics', async () => {
  const calls = [];
  const api = load('src/api/watchlistApi.ts', {
    './apiClient': {
      apiRequest: async (requestPath, options = {}) => {
        calls.push({ path: requestPath, options });
        return requestPath === '/api/watchlist' && options.method === 'POST'
          ? { symbol: options.body.symbol }
          : { items: [] };
      },
    },
  });

  await api.listWatchlist();
  await api.addWatchlistItem('BTC-USD');
  await api.deleteWatchlistItem('BTC-USD');

  assert.equal(calls[0].path, '/api/watchlist');
  assert.equal(calls[1].path, '/api/watchlist');
  assert.equal(calls[1].options.method, 'POST');
  assert.deepEqual(plain(calls[1].options.body), { symbol: 'BTC-USD' });
  assert.equal(calls[2].path, '/api/watchlist/BTC-USD');
  assert.equal(calls[2].options.method, 'DELETE');

  class ApiError extends Error {
    constructor(options) {
      super(options.message ?? 'Request failed');
      Object.assign(this, options);
    }
  }
  const ui = load('src/pages/watchlist/watchlistUi.ts', {
    '../../api/apiClient': { ApiError },
  });
  assert.equal(ui.formatWatchlistPrice(null), '—');
  assert.equal(ui.formatWatchlistPercent(null), '—');
  assert.equal(ui.formatWatchlistPercent(2.345), '+2.35%');
  assert.match(ui.watchlistErrorMessage(new ApiError({ status: 409 }), 'add'), /already in/i);
  assert.match(ui.watchlistErrorMessage(new ApiError({ status: 422 }), 'add'), /supported assets/i);
  assert.doesNotMatch(ui.watchlistErrorMessage(new ApiError({ status: 500, message: 'database secret' }), 'add'), /database|secret/i);
});

test('web Watchlist has real states, supported-asset search, and no mock authority', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const page = read('src/pages/watchlist/WatchlistPage.tsx');
  const table = read('src/pages/watchlist/components/WatchlistTable.tsx');
  const toolbar = read('src/pages/watchlist/components/WatchlistToolbar.tsx');

  assert.match(page, /listWatchlist/);
  assert.match(page, /addWatchlistItem/);
  assert.match(page, /deleteWatchlistItem/);
  assert.match(page, /supportedAssets\.filter/);
  assert.match(page, /Loading your Watchlist/);
  assert.match(table, /Your watchlist is empty/);
  assert.match(table, /latest_price/);
  assert.match(table, /latest_price_date/);
  assert.match(table, /daily_change_percent/);
  assert.match(table, /ytd_change_percent/);
  assert.match(toolbar, /Updated dates are shown per asset/);
  assert.match(page, /setViewMode/);
  assert.match(toolbar, /onViewChange\('list'\)/);
  assert.match(toolbar, /onViewChange\('grid'\)/);
  assert.match(toolbar, /aria-pressed/);
  assert.match(table, /viewMode === 'list'/);
  assert.match(table, /watchlist-grid-card/);
  assert.ok(!/watchlistSeed|watchlist\.mock|market cap|spark/i.test(`${page}\n${table}`));
  assert.ok(!/fetch\(['"]https?:|OPENAI_API_KEY|ALPHA_VANTAGE|YAHOO/i.test(`${page}\n${table}`));
});

test('error presentation distinguishes required statuses and sanitizes server failures', () => {
  class ApiError extends Error {
    constructor(options) {
      super(options.message ?? 'Request failed');
      Object.assign(this, options);
    }
  }
  const errors = load('src/api/apiErrorPresentation.ts', {
    './apiClient': { ApiError },
  });
  const classify = options => errors.apiErrorPresentation(new ApiError(options), { resourceName: 'Portfolio' });

  assert.deepEqual([
    classify({ kind: 'http', status: 401 }).code,
    classify({ kind: 'http', status: 404 }).code,
    classify({ kind: 'http', status: 422, detail: [] }).code,
    classify({ kind: 'http', status: 500, message: 'secret database failure' }).code,
    classify({ kind: 'network', status: null }).code,
  ], ['401', '404', '422', '500', 'NETWORK']);
  assert.equal(classify({ kind: 'http', status: 404 }).retryable, false);
  assert.equal(classify({ kind: 'http', status: 500 }).retryable, true);
  assert.ok(!classify({ kind: 'http', status: 500, message: 'secret database failure' }).message.includes('database'));

  const issues = errors.apiValidationIssues(new ApiError({
    kind: 'http',
    status: 422,
    detail: [{ loc: ['body', 'holdings', 0, 'shares'], msg: 'Must be positive' }],
  }));
  assert.deepEqual(plain(issues), [{ path: 'holdings.0.shares', message: 'Must be positive' }]);
});

test('saved report and simulation links preserve exact Ask Aura context', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const report = read('src/pages/reports/ReportDetailPage.tsx');
  const simulation = read('src/pages/simulations/SimulationHistoryDetailPage.tsx');
  const dashboardAi = read('src/pages/dashboard/components/AiInsight.tsx');
  const assistant = read('src/pages/assistant/AssistantPage.tsx');
  const app = read('src/app/App.tsx');

  assert.match(report, /assistant\/\$\{report\.portfolio_id\}\/report\/\$\{report\.id\}/);
  assert.match(simulation, /assistant\/\$\{portfolioId\}\/simulation\/\$\{simulationId\}/);
  assert.match(dashboardAi, /assistant\/\$\{report\.portfolio_id\}\/report\/\$\{report\.id\}/);
  assert.match(dashboardAi, /assistant\/\$\{portfolioId\}/);
  assert.match(dashboardAi, /Ask Aura<\/button>/);
  assert.match(assistant, /report_id: savedContext\.id/);
  assert.match(assistant, /simulation_id: savedContext\.id/);
  assert.match(assistant, /setLoadError\('Portfolio not found\.'\)/);
  assert.match(app, /route\.reportId === 'report'/);
  assert.match(app, /route\.reportId === 'simulation'/);
  assert.match(report, /className="primary-btn".*Run New Analysis<\/button>/);
});

test('web Assistant composer collapses and restores like the mobile composer', () => {
  const assistant = fs.readFileSync(path.join(root, 'src/pages/assistant/AssistantPage.tsx'), 'utf8');
  const icons = fs.readFileSync(path.join(root, 'src/components/ui/Icon.tsx'), 'utf8');
  const styles = fs.readFileSync(path.join(root, 'src/pages/assistant/AssistantComposer.module.css'), 'utf8');

  assert.match(assistant, /const \[composerHidden, setComposerHidden\] = useState\(false\)/);
  assert.match(assistant, /aria-label="Hide message composer"/);
  assert.match(assistant, /setComposerHidden\(true\)/);
  assert.match(assistant, /aria-label="Show message composer"/);
  assert.match(assistant, /setComposerHidden\(false\)/);
  assert.match(assistant, /name="chevron-down"/);
  assert.match(assistant, /name="chevron-up"/);
  assert.match(icons, /case 'chevron-up'/);
  assert.match(styles, /\.collapsedComposer/);
  assert.match(styles, /\.hideComposerButton/);
  assert.match(styles, /\.showComposerButton/);
});

test('web theme uses the mobile palette while preserving gradients and dark action text', () => {
  const styles = fs.readFileSync(path.join(root, 'src/styles.css'), 'utf8');
  const authStyles = fs.readFileSync(path.join(root, 'src/pages/auth/AuthPage.module.css'), 'utf8');
  const simulationResults = fs.readFileSync(path.join(root, 'src/pages/simulations/components/SimulationResults.tsx'), 'utf8');

  for (const token of [
    '--bg-app:#07111F',
    '--bg-card:#101A2C',
    '--purple-primary:#31D6CF',
    '--purple-hover:#2EC5E6',
    '--text-primary:#F7FAFF',
    '--text-secondary:#A7B2C7',
    '--border-card:#233149',
    '--green-primary:#33D18F',
    '--on-primary:#031614',
    '--positive-background:#0D2C27',
    '--negative-background:#2C171E',
    '--purple-background:#21163D',
    '--cyan-background:#0C2B35',
    '--blue-background:#12264A',
    '--warning-background:#312611',
  ]) assert.ok(styles.includes(token), `Missing mobile theme token: ${token}`);

  assert.match(styles, /\.card\{background:linear-gradient\(145deg,rgba\(16,26,44,\.96\),rgba\(10,21,38,\.96\)\)/);
  assert.match(styles, /\.primary-btn\{[^}]*background:linear-gradient\(135deg,var\(--purple-primary\),var\(--purple-hover\)\);color:var\(--on-primary\)/);
  assert.match(styles, /\.composer-send\{[^}]*color:var\(--on-primary\)!important/);
  assert.match(authStyles, /\.submitButton[\s\S]*?color: var\(--on-primary\);/);
  assert.match(simulationResults, /color: '#31D6CF'/);
  assert.match(simulationResults, /color: '#8B5CF6'/);
});

test('auth inputs keep the Aura field surface when the browser autofills saved credentials', () => {
  const authStyles = fs.readFileSync(path.join(root, 'src/pages/auth/AuthPage.module.css'), 'utf8');

  assert.match(authStyles, /input:-webkit-autofill/);
  assert.match(authStyles, /-webkit-background-clip: text/);
  assert.match(authStyles, /-webkit-text-fill-color: var\(--text-primary\)/);
  assert.match(authStyles, /box-shadow: 0 0 0 1000px transparent inset/);
  assert.match(authStyles, /input:autofill/);
});

test('web feature icons follow the mobile semantic icon mappings', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const icons = read('src/components/ui/Icon.tsx');
  const dashboard = read('src/pages/dashboard/components/DashboardKpiGrid.tsx');
  const analytics = read('src/pages/analytics/components/AnalysisResults.tsx');
  const simulationModes = read('src/pages/simulations/components/SimulationModeSelector.tsx');
  const simulationResults = read('src/pages/simulations/components/SimulationResults.tsx');

  for (const icon of ['speedometer', 'pulse', 'stats-chart', 'pie-chart', 'compare', 'diversification', 'assets', 'eye', 'school', 'settings']) {
    assert.ok(icons.includes(`case '${icon}'`), `Missing web icon: ${icon}`);
  }
  assert.match(dashboard, /title="Risk Score" icon="speedometer"/);
  assert.match(dashboard, /title=\{valueTitle\} icon="wallet" tone="blue"/);
  assert.match(dashboard, /tone=\{riskKpiTone\}/);
  assert.match(dashboard, /tone=\{returnKpiTone\}/);
  assert.match(dashboard, /title="Annualized Return" icon="trend"/);
  assert.match(dashboard, /title="Maximum Drawdown" icon="drawdown"/);
  assert.match(analytics, /MetricLabel icon="analytics" label="Annualized Return" tone=/);
  assert.match(analytics, /MetricLabel icon="pulse" label="Annualized Volatility" tone="warning"/);
  assert.match(simulationModes, /'historical-scenario', 'Historical Scenario', 'time', 'purple'/);
  assert.match(simulationModes, /'allocation', 'Allocation Change', 'pie-chart', 'cyan'/);
  assert.match(simulationModes, /'combined', 'Combined Simulation', 'compare', 'blue'/);
  assert.match(simulationResults, /MetricLabel icon="drawdown" label="Maximum Drawdown" tone="danger"/);
});

test('web return metrics expose saved money equivalents with side chevrons', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const dashboard = read('src/pages/dashboard/components/DashboardKpiGrid.tsx');
  const analysis = read('src/pages/analytics/components/AnalysisResults.tsx');
  const reportDetails = read('src/pages/analytics/reportMetricDetails.ts');
  const reportPage = read('src/pages/reports/ReportDetailPage.tsx');
  const icons = read('src/components/ui/Icon.tsx');

  assert.match(dashboard, /setSelectedMetric\('annualized'\)/);
  assert.match(dashboard, /setSelectedMetric\('drawdown'\)/);
  assert.match(dashboard, /<MetricAmountDialog/);
  assert.match(dashboard, /name="chevron-right"/);
  assert.match(analysis, /setSelectedMetric\('annualized'\)/);
  assert.match(analysis, /setSelectedMetric\('drawdown'\)/);
  assert.match(analysis, /setSelectedMetric\('endingValue'\)/);
  assert.match(analysis, /Estimated Value at End of Period/);
  assert.match(analysis, /monetary\.estimated_ending_value/);
  assert.match(analysis, /Historical Portfolio Return/);
  assert.match(analysis, /analysis\.historical_value_context/);
  assert.match(analysis, /Same shares at historical prices/);
  assert.match(analysis, /name="chevron-right"/);
  assert.match(reportPage, /<AnalysisResults report=\{report\} \/>/);
  assert.match(icons, /case 'chevron-right'/);
  assert.match(reportDetails, /monetary\.annualized_return_amount/);
  assert.match(reportDetails, /monetary\.maximum_drawdown_amount/);
  assert.match(reportDetails, /monetary\.estimated_ending_value/);
  assert.match(reportDetails, /not a prediction of future value/);
  assert.match(reportDetails, /fixed-shares-historical-value/);
  assert.match(reportDetails, /not your actual profit or loss/);
  assert.match(reportDetails, /monetary\.reference_amount/);
  assert.doesNotMatch(reportDetails, /reference_amount\s*\*/);
});

test('web risk levels use their semantic colors and report returns stay compact', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const summary = read('src/pages/analytics/components/AnalysisSummary.tsx');
  const results = read('src/pages/analytics/components/AnalysisResults.tsx');
  const dashboard = read('src/pages/dashboard/components/DashboardKpiGrid.tsx');
  const analyticsStyles = read('src/pages/analytics/AnalyticsIntegration.module.css');
  const returnRanges = load('src/pages/analytics/returnSeriesRange.ts');

  assert.match(summary, /risk_level === 'Low'[\s\S]*successScore[\s\S]*risk_level === 'Moderate'[\s\S]*warningScore[\s\S]*dangerScore/);
  assert.match(analyticsStyles, /\.score\.successScore>svg,\.score\.successScore span\{color:var\(--green-primary\)\}/);
  assert.match(analyticsStyles, /\.score\.warningScore>svg,\.score\.warningScore span\{color:var\(--amber-primary\)\}/);
  assert.match(analyticsStyles, /\.score\.dangerScore>svg,\.score\.dangerScore span\{color:var\(--red-bright\)\}/);
  assert.match(dashboard, /riskLabelTone = !risk \? 'purple-text' : risk\.risk_level === 'Low' \? 'positive' : risk\.risk_level === 'Moderate' \? 'warning' : 'negative'/);

  const chartIndex = results.indexOf('<PortfolioReturnChart');
  const tableIndex = results.indexOf('<table className={styles.dataTable}>');
  assert.ok(chartIndex >= 0 && chartIndex < tableIndex, 'Return graph must appear before the return table');
  assert.match(results, /returnSeriesScroll/);
  assert.match(results, /Scrollable portfolio return observations/);
  assert.match(results, /RETURN_VIEW_RANGES\.map/);
  assert.match(results, /setReturnViewRange\(range\)/);
  assert.match(results, /Portfolio return graph range/);
  assert.match(analyticsStyles, /\.returnSeriesScroll\{max-height:360px/);
  assert.match(analyticsStyles, /\.returnSeriesScroll thead\{position:sticky/);
  assert.deepEqual(plain(returnRanges.RETURN_VIEW_RANGES), ['1M', '3M', '6M', '1Y', 'ALL']);
  const points = [
    { date: '2025-09-30', portfolio_return: 0.01 },
    { date: '2026-08-29', portfolio_return: 0.02 },
    { date: '2026-08-30', portfolio_return: 0.03 },
    { date: '2026-09-30', portfolio_return: 0.04 },
  ];
  assert.deepEqual(
    plain(returnRanges.visibleReturnPoints(points, '1M').map(point => point.date)),
    ['2026-08-30', '2026-09-30'],
  );
  assert.equal(returnRanges.visibleReturnPoints(points, '1Y').length, 4);
  assert.equal(returnRanges.visibleReturnPoints(points, 'ALL').length, 4);
});

test('web current-value failures explain the data refresh and retry valuation', () => {
  const dashboard = fs.readFileSync(path.join(root, 'src/pages/dashboard/DashboardPage.tsx'), 'utf8');
  const detail = fs.readFileSync(path.join(root, 'src/pages/portfolios/PortfolioDetailView.tsx'), 'utf8');
  const portfolioUi = fs.readFileSync(path.join(root, 'src/pages/portfolios/portfolioUi.ts'), 'utf8');
  const analytics = fs.readFileSync(path.join(root, 'src/pages/analytics/AnalyticsPage.tsx'), 'utf8');
  const analyticsUi = fs.readFileSync(path.join(root, 'src/pages/analytics/analyticsUi.ts'), 'utf8');
  const errorStyles = fs.readFileSync(path.join(root, 'src/components/ui/ApiErrorState.module.css'), 'utf8');

  assert.match(dashboard, /retryTitle=\{portfolio\.portfolio_type === 'CURRENT' \? 'Retry Current Value' : 'Retry allocation'\}/);
  assert.match(dashboard, /onRetry=\{\(\) => setContextReloadKey/);
  assert.doesNotMatch(dashboard, /Analyze Portfolio Again/);
  assert.match(dashboard, /compactAction=\{portfolio\.portfolio_type === 'CURRENT'\}/);
  assert.match(detail, /retryTitle=\{portfolio\.portfolio_type === 'CURRENT' \? 'Retry Current Value' : 'Retry preview'\}/);
  assert.match(detail, /PORTFOLIO_MARKET_DATA_RECOVERY_MESSAGE/);
  assert.match(portfolioUi, /New analysis is unavailable until market data is refreshed/);
  assert.match(analytics, /analysisErrorMessage\(actionError/);
  assert.match(analyticsUi, /Analysis will be available after the market data refresh completes/);
  assert.match(errorStyles, /\.actions \.compactAction\{min-width:0;width:auto\}/);
});

test('web dashboard exposes mobile-style visible portfolio choices', () => {
  const dashboard = fs.readFileSync(path.join(root, 'src/pages/dashboard/DashboardPage.tsx'), 'utf8');
  const header = fs.readFileSync(path.join(root, 'src/pages/dashboard/components/DashboardHeader.tsx'), 'utf8');
  const selector = fs.readFileSync(path.join(root, 'src/pages/dashboard/components/PortfolioSelector.tsx'), 'utf8');
  const dashboardStyles = fs.readFileSync(path.join(root, 'src/pages/dashboard/DashboardIntegration.module.css'), 'utf8');
  const styles = fs.readFileSync(path.join(root, 'src/styles.css'), 'utf8');

  assert.match(selector, /role="radiogroup"/);
  assert.match(selector, /role="radio"/);
  assert.match(selector, /aria-checked=\{selected\}/);
  assert.match(selector, /onClick=\{\(\) => onSelect\(portfolio\.id\)\}/);
  assert.match(dashboard, /portfolioContextBar[\s\S]*<PortfolioSelector[\s\S]*currencyControl/);
  assert.doesNotMatch(header, /PortfolioSelector/);
  assert.match(dashboardStyles, /portfolioContextBar :global\(\.dashboard-portfolio-picker\)/);
  assert.match(styles, /\.dashboard-portfolio-options\{[^}]*overflow-x:auto/);
  assert.match(styles, /\.dashboard-portfolio-option\.active\{/);
});

test('web portfolio cards and dashboard visuals use balanced formatted layouts', () => {
  class ApiError extends Error {}
  const dashboardUi = load('src/pages/dashboard/dashboardUi.ts', {
    '../../api/apiClient': { ApiError },
  });
  const styles = fs.readFileSync(path.join(root, 'src/styles.css'), 'utf8');
  const dashboardStyles = fs.readFileSync(
    path.join(root, 'src/pages/dashboard/DashboardIntegration.module.css'),
    'utf8',
  );
  const riskDrivers = fs.readFileSync(
    path.join(root, 'src/pages/dashboard/components/RiskDrivers.tsx'),
    'utf8',
  );
  const dashboard = fs.readFileSync(
    path.join(root, 'src/pages/dashboard/DashboardPage.tsx'),
    'utf8',
  );

  const ticks = dashboardUi.portfolioReturnAxisTicks(-0.026, 0.023);
  const labels = ticks.map(tick => dashboardUi.formatPortfolioReturnTick(tick, 0.049));
  assert.equal(ticks.length, 5);
  assert.ok(ticks.includes(0));
  assert.equal(new Set(labels).size, labels.length);
  assert.equal(dashboardUi.formatPortfolioReturnTick(-0.0004, 0.05), '0.0%');
  assert.match(styles, /\.portfolios-page \.portfolio-card\{[^}]*display:flex[^}]*justify-content:center/);
  assert.match(styles, /\.portfolios-page \.portfolio-card-actions\{[^}]*margin-top:0/);
  assert.match(riskDrivers, /styles\.driverTrack/);
  assert.match(riskDrivers, /Math\.min\(100, Math\.abs/);
  assert.match(riskDrivers, /go\(`asset\/\$\{portfolioId\}\/\$\{reportId\}\/\$\{encodeURIComponent\(driver\.symbol\)\}`\)/);
  assert.match(riskDrivers, /aria-label=\{`Open \$\{driver\.symbol\} asset risk details`\}/);
  assert.match(dashboard, /reportId=\{report\?\.id \?\? null\}/);
  assert.match(dashboardStyles, /dashboard-risk-list[\s\S]*justify-content: flex-start/);
  assert.match(dashboardStyles, /\.driverTrack/);
});

test('web holding forms expose the complete mobile-supported asset catalog', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const catalog = load('src/pages/portfolios/supportedAssetSymbols.ts');
  const mobileCatalog = load('../mobile/src/portfolio/supportedAssetSymbols.ts');
  const field = read('src/pages/portfolios/components/AssetSymbolField.tsx');
  const create = read('src/pages/portfolios/PortfolioCreateFlow.tsx');
  const editor = read('src/pages/portfolios/components/PortfolioHoldingsEditor.tsx');
  const decimalInput = read('src/pages/portfolios/components/HoldingDecimalInput.tsx');
  const detail = read('src/pages/portfolios/PortfolioDetailView.tsx');
  const allocation = read('src/components/portfolio/AllocationLegend.tsx');

  assert.deepEqual(plain(catalog.supportedAssets), plain(mobileCatalog.supportedAssets));
  assert.deepEqual(plain(catalog.supportedAssetSymbols), plain(mobileCatalog.supportedAssetSymbols));
  assert.equal(catalog.supportedAssetSymbols.length, 17);
  assert.ok(catalog.supportedAssets.every(asset => asset.symbol && asset.name));
  assert.ok(!catalog.supportedAssetSymbols.includes('THB=X'));
  assert.match(field, /role="dialog"/);
  assert.match(field, /createPortal/);
  assert.match(field, /supportedAssets\.map/);
  assert.match(field, /asset\.name/);
  assert.match(field, /chooseSymbol\(asset\.symbol\)/);
  assert.match(field, /role="radiogroup"/);
  assert.match(field, /role="radio"/);
  assert.match(field, /event\.target\.value\.toUpperCase\(\)/);
  const styles = read('src/pages/portfolios/PortfolioIntegration.module.css');
  assert.match(styles, /\.assetPickerOptions[\s\S]*?max-height: 310px/);
  assert.match(styles, /\.assetPickerOptions[\s\S]*?overflow-y: auto/);
  assert.match(create, /<AssetSymbolField/);
  assert.match(editor, /<AssetSymbolField/);
  assert.match(create, /<HoldingDecimalInput/);
  assert.match(editor, /<HoldingDecimalInput/);
  assert.match(decimalInput, /TWO_DECIMAL_INPUT/);
  assert.match(detail, /styles\.allocationCard/);
  assert.match(detail, /styles\.recordGrid/);
  assert.match(allocation, /toFixed\(2\)/);
  assert.match(styles, /\.allocationCard/);
  assert.match(styles, /\.recordGrid > div:nth-child\(n \+ 4\)/);
});

test('web portfolio actions use accessible Aura dialogs and one purchase-date icon', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const detail = read('src/pages/portfolios/PortfolioDetailView.tsx');
  const dialog = read('src/pages/portfolios/components/PortfolioActionDialog.tsx');
  const styles = read('src/pages/portfolios/PortfolioIntegration.module.css');

  assert.doesNotMatch(detail, /\bprompt\s*\(/);
  assert.doesNotMatch(detail, /\bconfirm\s*\(/);
  assert.match(detail, /openActionDialog\('rename'\)/);
  assert.match(detail, /openActionDialog\('duplicate'\)/);
  assert.match(detail, /openActionDialog\('delete'\)/);
  assert.match(dialog, /createPortal/);
  assert.match(dialog, /role="dialog"/);
  assert.match(dialog, /aria-modal="true"/);
  assert.match(dialog, /event\.key === 'Escape'/);
  assert.match(dialog, /event\.key !== 'Tab'/);
  assert.match(styles, /\.dateField input::\-webkit-calendar-picker-indicator[\s\S]*?opacity: 0/);
  assert.match(styles, /\.dateField svg[\s\S]*?color: var\(--purple-light\)/);
});

test('web portfolio detail exposes the newest saved report only after analysis exists', () => {
  const detail = fs.readFileSync(
    path.join(root, 'src/pages/portfolios/PortfolioDetailView.tsx'),
    'utf8',
  );

  assert.match(detail, /listPortfolioReports\(portfolioId/);
  assert.match(detail, /setLatestReport\(response\.reports\[0\] \?\? null\)/);
  assert.match(detail, /\{latestReport && <button[\s\S]*?>View Latest Report<\/button>\}/);
  assert.match(detail, /go\(`reports\/\$\{portfolio\.id\}\/\$\{latestReport\.id\}`\)/);
});

test('web asset-risk detail is report-backed, navigable, and never recalculates risk', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const results = read('src/pages/analytics/components/AnalysisResults.tsx');
  const card = read('src/pages/analytics/components/AssetAnalysisCard.tsx');
  const detail = read('src/pages/reports/AssetRiskDetailPage.tsx');
  const metricDetails = read('src/pages/analytics/reportMetricDetails.ts');
  const reportTypes = read('src/types/report.ts');
  const reportDetail = read('src/pages/reports/ReportDetailPage.tsx');
  const app = read('src/app/App.tsx');

  assert.match(results, /replace\(`reports\/\$\{report\.portfolio_id\}\/\$\{report\.id\}\/assets`\)/);
  assert.match(results, /go\(`asset\/\$\{report\.portfolio_id\}\/\$\{report\.id\}\/\$\{encodeURIComponent\(symbol\)\}`\)/);
  assert.match(card, /onClick=\{onOpen\}/);
  assert.match(app, /case 'asset':/);
  assert.match(app, /focusAssetSection=\{route\.contextId === 'assets'\}/);
  assert.match(detail, /go\(`reports\/\$\{portfolioId\}\/\$\{reportId\}\/assets`\)/);
  assert.match(reportDetail, /getElementById\(focusRiskDrivers \? 'risk-drivers' : 'per-asset-analysis'\)/);
  assert.match(reportDetail, /section\?\.scrollIntoView/);
  assert.match(detail, /getPortfolioReport\(portfolioId, reportId/);
  assert.match(detail, /asset\.risk_classification/);
  assert.match(detail, /report\.analysis\.asset_returns/);
  assert.match(detail, /visibleReturnPoints\(series\?\.points \?\? \[\], range\)/);
  assert.match(reportTypes, /asset_monetary_metrics\?: PortfolioReportAssetMonetaryMetrics\[\]/);
  assert.match(detail, /assetReportMonetaryMetrics\(report, symbol\)/);
  assert.match(detail, /setSelectedMetric\('cumulative'\)/);
  assert.match(detail, /setSelectedMetric\('annualized'\)/);
  assert.match(detail, /setSelectedMetric\('drawdown'\)/);
  assert.match(detail, /<MetricAmountDialog/);
  assert.match(metricDetails, /monetary\.cumulative_return_amount/);
  assert.match(metricDetails, /monetary\.annualized_return_amount/);
  assert.match(metricDetails, /monetary\.maximum_drawdown_amount/);
  assert.doesNotMatch(metricDetails, /reference_amount\s*\*/);
  assert.doesNotMatch(detail, /Math\.(sqrt|pow)|annualized_volatility\s*[*/+-]|max_drawdown\s*[*/+-]/);
});

test('web destructive actions and portfolio naming use Aura-themed dialogs', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const confirmation = read('src/components/ui/ConfirmationDialog.tsx');
  const portfolios = read('src/pages/portfolios/PortfoliosPage.tsx');
  const portfolioDialog = read('src/pages/portfolios/components/PortfolioActionDialog.tsx');
  const reports = read('src/pages/reports/ReportsPage.tsx');
  const reportDetail = read('src/pages/reports/ReportDetailPage.tsx');
  const watchlist = read('src/pages/watchlist/WatchlistPage.tsx');
  const create = read('src/pages/portfolios/PortfolioCreateFlow.tsx');
  const editor = read('src/pages/portfolios/components/PortfolioHoldingsEditor.tsx');

  assert.match(confirmation, /role="dialog"/);
  assert.match(confirmation, /aria-modal="true"/);
  assert.match(confirmation, /createPortal/);
  assert.match(portfolios, /<PortfolioActionDialog/);
  assert.match(portfolios, /openActionDialog\('rename'/);
  assert.match(portfolios, /openActionDialog\('duplicate'/);
  assert.match(portfolios, /openActionDialog\('delete'/);
  assert.match(portfolioDialog, /actionDialogOverlay/);
  assert.match(reports, /<ConfirmationDialog/);
  assert.match(reportDetail, /<ConfirmationDialog/);
  assert.match(watchlist, /<ConfirmationDialog/);
  assert.match(create, /<ConfirmationDialog/);
  assert.match(editor, /<ConfirmationDialog/);
  assert.doesNotMatch(`${portfolios}\n${reports}\n${reportDetail}\n${watchlist}`, /\b(?:prompt|confirm)\s*\(/);
});

test('web and mobile Learn surfaces share nine example-based lessons and scoped videos', () => {
  const webLearn = fs.readFileSync(path.join(root, 'src/pages/learn/LearnPage.tsx'), 'utf8');
  const webDialog = fs.readFileSync(path.join(root, 'src/pages/learn/components/LessonDialog.tsx'), 'utf8');
  const mobileLearn = fs.readFileSync(path.join(root, '../mobile/src/mocks/learn.mock.ts'), 'utf8');
  const mobileDetail = fs.readFileSync(path.join(root, '../mobile/src/screens/learn/LearnDetailScreen.tsx'), 'utf8');
  const mobileLibrary = fs.readFileSync(path.join(root, '../mobile/src/screens/learn/LearnScreen.tsx'), 'utf8');
  const lessonIds = [
    'risk-score',
    'volatility',
    'drawdown',
    'sharpe',
    'diversification',
    'historical-scenario',
    'allocation-change',
    'combined',
    'ai-explanation',
  ];

  for (const lessonId of lessonIds) {
    assert.match(webLearn, new RegExp(`id: '${lessonId}'`));
    assert.match(mobileLearn, new RegExp(`id: '${lessonId}'`));
  }
  assert.equal((webLearn.match(/Example:/g) ?? []).length, 9);
  assert.equal((mobileLearn.match(/Example:/g) ?? []).length, 9);
  assert.equal((webLearn.match(/youtube\.com\/watch/g) ?? []).length, 5);
  assert.equal((mobileLearn.match(/youtube\.com\/watch/g) ?? []).length, 5);
  assert.doesNotMatch(webLearn.slice(webLearn.indexOf("id: 'historical-scenario'")), /youtube\.com\/watch/);
  assert.doesNotMatch(mobileLearn.slice(mobileLearn.indexOf("id: 'historical-scenario'")), /youtube\.com\/watch/);
  assert.doesNotMatch(webLearn, /\balert\s*\(/);
  assert.match(webDialog, /role="dialog"/);
  assert.match(webDialog, /aria-modal="true"/);
  assert.match(webDialog, /event\.key === 'Escape'/);
  assert.match(webDialog, /target="_blank" rel="noreferrer"/);
  assert.match(mobileDetail, /Linking\.openURL\(lesson\.video!\.url\)/);
  assert.match(webLearn, /Open AI Assistant/);
  assert.match(mobileLibrary, /Ask Aura about your results/);
  assert.match(mobileLibrary, /navigation\.getParent\(\)\?\.navigate\('AI'\)/);
  assert.match(mobileLibrary, /not financial or investment advice/);
  const webLibrary = fs.readFileSync(path.join(root, 'src/pages/learn/components/LessonLibrary.tsx'), 'utf8');
  assert.match(webLibrary, /placeholder="Search lessons by topic or concept…"/);
  assert.match(webLibrary, /lesson\.title,[\s\S]*lesson\.topic,[\s\S]*lesson\.text,[\s\S]*\.\.\.lesson\.body/);
  assert.match(webLibrary, /filteredLessons\.length === 0/);
  assert.match(webLibrary, /Clear search/);
});

test('historical scenario results compare the latest analysis and use selection-aware axes', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const results = read('src/pages/simulations/components/SimulationResults.tsx');
  const chart = read('src/pages/simulations/components/SimulationTrajectoryChart.tsx');
  const mobileResults = read('../mobile/src/components/simulations/SimulationResults.tsx');
  const mobileChart = read('../mobile/src/components/charts/SimulationTrajectoryChart.tsx');

  assert.match(results, /Latest Portfolio Analysis vs Historical Scenario/);
  assert.match(results, /savedAnalysisTrajectory\(latestAnalysis\.analysis\)/);
  assert.match(results, /label: 'Historical scenario'/);
  assert.match(chart, /All lines/);
  assert.match(chart, /aria-label="Choose trajectory lines"/);
  assert.match(chart, /setSelectedSeries\(item\.label\)/);
  assert.match(chart, /selectedSeries === 'all' \? null/);
  assert.match(chart, />Date<\/text>/);
  assert.match(mobileResults, /Latest portfolio analysis vs historical scenario/);
  assert.match(mobileResults, /savedAnalysisTrajectory\(latestAnalysis\.analysis\)/);
  assert.match(mobileChart, /accessibilityLabel="Choose trajectory lines"/);
  assert.match(mobileChart, /accessibilityRole="radio"/);
  assert.match(mobileChart, /selectedSeries === 'all' \? null/);
  assert.match(mobileChart, />Date<\/SvgText>/);
});

test('production web source has no direct market, database, or LLM provider authority', () => {
  const sourceRoot = path.join(root, 'src');
  const files = [];
  const collect = directory => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const target = path.join(directory, entry.name);
      if (entry.isDirectory()) collect(target);
      else if (/\.(ts|tsx)$/.test(entry.name)) files.push(target);
    }
  };
  collect(sourceRoot);

  for (const file of files) {
    const source = fs.readFileSync(file, 'utf8');
    if (/\bfetch\s*\(/.test(source)) assert.ok(file.endsWith('apiClient.ts'));
    assert.ok(!/OPENAI_API_KEY|GROQ_API_KEY|SUPABASE_SERVICE_ROLE|DATABASE_URL/.test(source));
  }

  const create = fs.readFileSync(path.join(root, 'src/pages/portfolios/PortfolioCreateFlow.tsx'), 'utf8');
  const editor = fs.readFileSync(path.join(root, 'src/pages/portfolios/components/PortfolioHoldingsEditor.tsx'), 'utf8');
  const detail = fs.readFileSync(path.join(root, 'src/pages/portfolios/PortfolioDetailView.tsx'), 'utf8');
  assert.ok(!/Weight %|TOTAL ALLOCATION|weightPercent/.test(`${create}\n${editor}`));
  assert.ok(!/proposedAmount\s*\/|proposed_amount\s*\//.test(`${create}\n${editor}\n${detail}`));
  assert.match(detail, /Estimated shares are display-only/);
});

test('web settings use the authenticated Backend Profile V1 contract', async () => {
  const calls = [];
  const auth = load('src/api/authApi.ts', {
    './apiClient': {
      apiRequest: async (requestPath, options = {}) => {
        calls.push({ path: requestPath, options });
        return requestPath.endsWith('/password') ? undefined : { id: 'user' };
      },
    },
  });
  await auth.updateCurrentUserProfile({ display_name: 'Aura User' });
  await auth.changeCurrentUserPassword({
    current_password: 'current-pass',
    new_password: 'different-pass',
  });
  assert.equal(calls[0].path, '/api/auth/me');
  assert.equal(calls[0].options.method, 'PATCH');
  assert.deepEqual(plain(calls[0].options.body), { display_name: 'Aura User' });
  assert.equal(calls[1].path, '/api/auth/me/password');
  assert.equal(calls[1].options.method, 'PUT');

  const settings = fs.readFileSync(path.join(root, 'src/pages/settings/SettingsPage.tsx'), 'utf8');
  const context = fs.readFileSync(path.join(root, 'src/auth/AuthContext.tsx'), 'utf8');
  const types = fs.readFileSync(path.join(root, 'src/types/auth.ts'), 'utf8');
  assert.match(settings, /updateCurrentUserProfile\(request\)/);
  assert.match(settings, /changeCurrentUserPassword/);
  assert.match(settings, /request\.current_password = profile\.currentPassword/);
  assert.match(settings, /emailChanged &&/);
  assert.match(settings, /setCurrentUser\(updatedUser\)/);
  assert.match(settings, /value="UTC\+07:00 Bangkok" readOnly/);
  assert.doesNotMatch(settings, /Yangon|UTC\+06:30/);
  assert.doesNotMatch(settings, /usePersistedState|localStorage/);
  assert.match(context, /setCurrentUser: setUser/);
  assert.match(types, /preferred_language: PreferredLanguage/);
  assert.match(types, /timezone: ProfileTimezone/);
});

test('web account identity prefers the saved name and safely falls back to email', () => {
  const identity = load('src/auth/accountIdentity.ts');
  const unnamed = { email: 'sherlockthiha2003@gmail.com', display_name: null };
  const named = { email: 'sherlockthiha2003@gmail.com', display_name: 'Sherlock Thiha' };
  assert.equal(identity.accountDisplayName(unnamed), 'sherlockthiha2003@gmail.com');
  assert.equal(identity.accountDisplayName(named), 'Sherlock Thiha');
  assert.equal(identity.accountInitials(unnamed), 'SH');
  assert.equal(identity.accountInitials(named), 'ST');

  const dashboard = fs.readFileSync(path.join(root, 'src/pages/dashboard/DashboardPage.tsx'), 'utf8');
  const profileMenu = fs.readFileSync(path.join(root, 'src/components/navigation/ProfileMenu.tsx'), 'utf8');
  const styles = fs.readFileSync(path.join(root, 'src/styles.css'), 'utf8');
  assert.match(dashboard, /accountDisplayName\(user\)/);
  assert.doesNotMatch(dashboard, /email\.split\('@'\)/);
  assert.match(profileMenu, /<strong title=\{displayName\}>\{displayName\}<\/strong>/);
  assert.match(profileMenu, /user\?\.display_name \? user\.email : 'Authenticated Aura account'/);
  assert.match(styles, /\.profile-menu\{[^}]*max-width:calc\(100vw - 24px\)/);
  assert.match(styles, /\.profile-menu strong\{[^}]*overflow-wrap:anywhere/);
  assert.match(styles, /\.dashboard-greeting h1\{[^}]*overflow-wrap:anywhere/);
});

test('web session restoration uses the focused Aura loading screen', () => {
  const route = fs.readFileSync(path.join(root, 'src/auth/ProtectedRoute.tsx'), 'utf8');
  const styles = fs.readFileSync(path.join(root, 'src/auth/ProtectedRoute.module.css'), 'utf8');

  assert.match(route, /status === 'initializing'/);
  assert.match(route, /aria-busy="true"/);
  assert.match(route, /Welcome back/);
  assert.match(route, /Restoring your Aura session…/);
  assert.match(route, /Secure session/);
  assert.match(route, /Portfolio risk education/);
  assert.match(route, /role="status"/);
  assert.match(styles, /\.loadingBoundary/);
  assert.match(styles, /\.loadingHeaderInner/);
  assert.match(styles, /linear-gradient\(180deg, rgba\(11, 22, 40, \.98\), rgba\(7, 17, 31, \.94\)\)/);
  assert.match(styles, /max-width: 1680px/);
  assert.match(styles, /\.secureIcon/);
  assert.match(styles, /url\('\.\.\/assets\/aura-market-background\.png'\)/);
  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)/);
});

test('web settings enable privacy, local reset, help, About Aura and account notification settings', () => {
  let cursor = 0; const slots = [];
  const navigations = [];
  let hiddenValues = false;
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useState: initial => { const i = cursor++; if (!(i in slots)) slots[i] = initial; return [slots[i], value => { slots[i] = value; }]; },
    useRef: initial => { const i = cursor++; return slots[i] ??= { current: initial }; },
  };
  const { DeferredSettingsSections } = load('src/pages/settings/components/DeferredSettingsSections.tsx', {
    react, './AboutAuraDialog': { AboutAuraDialog: 'AboutDialog' },
    '../../../app/routes': { go: route => navigations.push(route) },
    '../../../learn/LearnProgress': { useLearnProgress: () => ({ resetLocalData: async () => {} }) },
    '../../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
    '../../../components/ui/Card': { Card: 'Card' },
    '../../../components/ui/Icon': { Icon: 'Icon' },
    '../SettingsPage.module.css': {},
    '../../../privacy/PortfolioPrivacy': { usePortfolioPrivacy: () => ({
      hideValues: hiddenValues, ready: true, storageError: null, setHideValues: value => { hiddenValues = value; },
    }) },
  }, { React: react });
  const render = () => { cursor = 0; return DeferredSettingsSections(); };
  const buttons = [], headings = [], text = [];
  function visit(node) {
    if (Array.isArray(node)) return node.forEach(visit);
    if (typeof node === 'string') { text.push(node); return; }
    if (!node || typeof node !== 'object') return;
    if (node.type === 'button') buttons.push(node);
    if (node.type === 'h2') headings.push(node.children.join(''));
    node.children?.forEach(visit);
  }
  visit(render());
  assert.deepEqual(headings, ['Privacy & alerts', 'Data & support']);
  const labels = ['Hide portfolio values', 'App notifications', 'Reset local data', 'Help & Support', 'About Aura'];
  assert.deepEqual(buttons.map(button => button.props['aria-label'] ?? button.children.join('')), labels);
  for (const button of buttons) {
    const enabled = ['About Aura', 'Hide portfolio values', 'Reset local data', 'Help & Support', 'App notifications'].includes(button.props['aria-label']);
    assert.equal(Boolean(button.props.disabled), !enabled);
    if (!enabled) assert.equal(button.props.onClick, undefined);
    assert.equal(button.props.type, 'button');
    assert.ok(button.props['aria-describedby']);
  }
  assert.equal(text.filter(value => value === 'Not available yet').length, 0);
  assert.equal(buttons[0].props.role, 'switch');
  assert.equal(buttons[0].props['aria-checked'], false);
  const help = buttons.find(button => button.props['aria-label'] === 'Help & Support');
  assert.equal(help.props['aria-haspopup'], undefined);
  assert.equal(help.children.at(-1).props.name, 'chevron-right');
  help.props.onClick(); assert.deepEqual(navigations, ['help']);
  buttons[1].props.onClick(); assert.equal(navigations.at(-1), 'notification-settings');
  buttons[0].props.onClick(); assert.equal(hiddenValues, true);
  const about = buttons.at(-1);
  assert.equal(about.props['aria-haspopup'], 'dialog');
  assert.equal(about.children[0].children[0].props.name, 'shield');
  assert.equal(about.children[1].children[0].children[0], 'About Aura');
  assert.equal(about.children[1].children[1].children[0], 'Learn about Aura and its current features.');
  assert.equal(about.children[2].type, 'Icon');
  assert.equal(about.children[2].props.name, 'chevron-right');
  assert.ok(about.children.every(child => child.type !== 'button'));
  assert.equal(render().children[2], false);
  about.props.onClick();
  assert.equal(render().children[2].type, 'AboutDialog');
  render().children[2].props.onClose();
  assert.equal(render().children[2], false);
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const mobile = fs.readFileSync(path.join(root, '../mobile/src/screens/settings/SettingsScreen.tsx'), 'utf8');
  for (const label of labels) assert.ok(mobile.includes(label));
  assert.match(read('src/pages/settings/SettingsPage.tsx'), /<DeferredSettingsSections \/>/);
  const preview = read('src/pages/settings/components/DeferredSettingsSections.tsx');
  assert.doesNotMatch(preview, /localStorage|sessionStorage|authApi/);
  assert.match(preview, /await resetLocalData\(\)/);
  const styles = read('src/pages/settings/SettingsPage.module.css');
  assert.match(styles, /\.availableRow \{ width: 100%/);
  assert.doesNotMatch(styles, /\.availableRow:hover/);
  assert.match(styles, /\.availableRow:focus-visible \{ outline: 2px solid var\(--teal-primary\)/);
  assert.match(styles, /\.availableRow \{ flex-wrap: nowrap; \}/);
});

test('Aura product copy and guidance use professional educational-platform branding', () => {
  const academicLabel = new RegExp(['senior', 'project'].join('\\s+'), 'i');
  const files = [
    '../AGENTS.md', '../PROJECT_CONTEXT.md', '../CURRENT_STATUS.md',
    '../mobile/src/screens/settings/AboutAuraDialog.tsx',
    'src/pages/settings/components/AboutAuraDialog.tsx', 'src/pages/welcome/WelcomePage.tsx',
  ];
  for (const file of files) assert.doesNotMatch(fs.readFileSync(path.join(root, file), 'utf8'), academicLabel, file);
  const guidance = fs.readFileSync(path.join(root, '../AGENTS.md'), 'utf8');
  assert.match(guidance, /Use professional product wording in UI, documentation, and future features/);
  const welcome = fs.readFileSync(path.join(root, 'src/pages/welcome/WelcomePage.tsx'), 'utf8');
  assert.match(welcome, /Aura · Portfolio risk education/);
});

test('web About Aura uses themed content, keyboard dismissal/focus trapping, and returns focus', () => {
  const focused = [], effects = [], listeners = {};
  class Element {
    constructor(name) { this.name = name; this.isConnected = true; }
    focus(options) { focused.push({ name: this.name, options }); }
  }
  const trigger = new Element('about-trigger'), close = new Element('close'), done = new Element('done');
  const document = { body: { style: { overflow: 'auto' } }, activeElement: trigger };
  const refs = [{ querySelectorAll: () => [close, done] }, close]; let refIndex = 0, closed = 0;
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useRef: initial => ({ current: refIndex < refs.length ? refs[refIndex++] : initial }),
    useEffect: callback => effects.push(callback),
  };
  const { AboutAuraDialog } = load('src/pages/settings/components/AboutAuraDialog.tsx', {
    react, 'react-dom': { createPortal: node => node }, '../../../components/ui/Icon': { Icon: 'Icon' },
    './AboutAuraDialog.module.css': {},
  }, { React: react, HTMLElement: Element, document, window: {
    addEventListener: (name, handler) => { listeners[name] = handler; },
    removeEventListener: name => { delete listeners[name]; },
  } });
  const nodes = [], text = [];
  function visit(node) {
    if (Array.isArray(node)) return node.forEach(visit);
    if (typeof node === 'string') { text.push(node); return; }
    if (!node || typeof node !== 'object') return; nodes.push(node); node.children?.forEach(visit);
  }
  visit(AboutAuraDialog({ onClose: () => { closed++; } }));
  assert.ok(nodes.some(node => node.props.role === 'dialog' && node.props['aria-modal'] === 'true'));
  const titles = nodes.filter(node => node.type === 'h3').map(node => node.children.join(''));
  assert.deepEqual(titles, ['Portfolios & risk', 'What-if simulations', 'AI Assistant', 'Watchlist & Learn']);
  assert.match(text.join(' '), /not live quotes/); assert.match(text.join(' '), /not a trading platform or financial advisor/);
  assert.match(text.join(' '), /Historical results do not guarantee future performance/);
  for (const button of nodes.filter(node => node.type === 'button')) button.props.onClick();
  assert.equal(closed, 3);
  const cleanup = effects[0](); assert.equal(document.body.style.overflow, 'hidden');
  assert.equal(focused.at(-1).name, 'close');
  listeners.keydown({ key: 'Escape' }); assert.equal(closed, 4);
  let prevented = 0;
  document.activeElement = done; listeners.keydown({ key: 'Tab', preventDefault: () => { prevented++; } });
  assert.equal(focused.at(-1).name, 'close');
  document.activeElement = close; listeners.keydown({ key: 'Tab', shiftKey: true, preventDefault: () => { prevented++; } });
  assert.equal(focused.at(-1).name, 'done'); assert.equal(prevented, 2);
  cleanup(); assert.equal(document.body.style.overflow, 'auto'); assert.equal(listeners.keydown, undefined);
  assert.equal(focused.at(-1).name, 'about-trigger');
  const styles = fs.readFileSync(path.join(root, 'src/pages/settings/components/AboutAuraDialog.module.css'), 'utf8');
  assert.match(styles, /background: var\(--bg-card\)/); assert.match(styles, /var\(--teal-primary\)/);
  assert.match(styles, /overflow-y: auto/); assert.match(styles, /100dvh/);
});
// Small hook harness for local UI workflows, not a browser E2E renderer.
function localWebHarness() {
  const slots = []; let cursor = 0, tree, component;
  const react = {
    createContext: () => ({ Provider: 'Provider' }),
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useContext: () => tree.props.value,
    useState: initial => {
      const i = cursor++;
      if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial;
      return [slots[i], next => { slots[i] = typeof next === 'function' ? next(slots[i]) : next; }];
    },
    useRef: initial => { const i = cursor++; return slots[i] ??= { current: initial }; },
    useMemo: fn => fn(), useEffect: () => {},
  };
  return { react, mount(fn) { component = fn; this.render(); }, render() { cursor = 0; tree = component(); }, get tree() { return tree; } };
}
function localWebNodes(tree) {
  if (Array.isArray(tree)) return tree.flatMap(localWebNodes);
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...(tree.children ?? []).flatMap(localWebNodes)];
}
function mountWebProgress(accountId, storage) {
  const h = localWebHarness();
  const api = load('src/learn/LearnProgress.tsx', {
    react: h.react, '../auth/useAuth': { useAuth: () => ({ user: accountId ? { id: accountId } : null }) },
  }, { React: h.react, localStorage: storage });
  const wrapper = api.LearnProgressProvider({ children: 'content' });
  h.mount(() => accountId ? wrapper.type(wrapper.props) : wrapper);
  return { h, api, get value() { return h.tree.props.value; }, key: wrapper.props.key };
}

test('web Learn completion persists per account, supports undo, survives login and resets only its own key', async () => {
  const saved = new Map([['session', 'token'], ['reports', 'saved-report']]);
  const storage = { getItem: key => saved.get(key) ?? null, setItem: (key, value) => saved.set(key, value), removeItem: key => saved.delete(key) };
  const first = mountWebProgress('a', storage);
  assert.deepEqual(plain(first.value.learnProgress), {});
  first.value.toggleLessonComplete('risk-score'); first.h.render();
  assert.equal(first.value.learnProgress['risk-score'], true);
  first.value.toggleLessonComplete('risk-score'); first.h.render();
  assert.equal(first.value.learnProgress['risk-score'], false);
  first.value.toggleLessonComplete('volatility'); first.h.render();
  assert.equal(mountWebProgress(null, storage).value.learnProgress.volatility, undefined);
  assert.equal(mountWebProgress('a', storage).value.learnProgress.volatility, true);
  const other = mountWebProgress('b', storage);
  assert.deepEqual(plain(other.value.learnProgress), {});
  other.value.toggleLessonComplete('drawdown'); other.h.render();
  await first.value.resetLocalData(); first.h.render();
  assert.deepEqual(plain(first.value.learnProgress), {});
  assert.equal(mountWebProgress('a', storage).value.learnProgress.volatility, undefined);
  assert.equal(mountWebProgress('b', storage).value.learnProgress.drawdown, true);
  assert.equal(saved.get('session'), 'token'); assert.equal(saved.get('reports'), 'saved-report');
});

test('web Learn handles corrupt, blocked and failed-save storage without false completion', async () => {
  for (const raw of ['null', '[]', 'bad-json', '{"risk-score":1}']) {
    const state = mountWebProgress('a', { getItem: () => raw });
    assert.ok(state.value.localError); assert.deepEqual(plain(state.value.learnProgress), {});
  }
  let failRead = true, failWrite = true, failReset = true;
  const saved = new Map();
  const state = mountWebProgress('a', {
    getItem: key => { if (failRead) throw Error('blocked'); return saved.get(key) ?? null; },
    setItem: (key, value) => { if (failWrite) throw Error('quota'); saved.set(key, value); },
    removeItem: key => { if (failReset) throw Error('blocked'); saved.delete(key); },
  });
  assert.ok(state.value.localError);
  failRead = false; state.value.retryLocalData(); state.h.render();
  assert.equal(state.value.localError, null);
  state.value.toggleLessonComplete('risk-score'); state.h.render();
  assert.equal(state.value.learnProgress['risk-score'], undefined); assert.match(state.value.localError, /could not be saved/);
  failWrite = false; state.value.retryLocalData(); state.h.render();
  state.value.toggleLessonComplete('risk-score'); state.h.render();
  await assert.rejects(() => state.value.resetLocalData()); state.h.render();
  assert.equal(state.value.learnProgress['risk-score'], true);
  failReset = false; await state.value.resetLocalData(); state.h.render();
  assert.deepEqual(plain(state.value.learnProgress), {});
});

test('web Learn opens without auto-completion, explicitly marks/undoes and shows actual total/path progress', () => {
  const state = mountWebProgress('a', { getItem: () => null, setItem: () => {} });
  const h = localWebHarness();
  const progress = { useLearnProgress: () => state.value };
  const { LearnPage } = load('src/pages/learn/LearnPage.tsx', {
    react: h.react, '../../learn/LearnProgress': progress,
    '../../app/routes': { go: () => {} }, '../../components/ui/Card': { Card: 'Card' }, '../../components/ui/Icon': { Icon: 'Icon' },
    './components/LearningFeature': { LearningFeature: 'Feature' }, './components/LearningPath': { LearningPath: 'Path' },
    './components/LessonLibrary': { LessonLibrary: 'Library' }, './components/LessonDialog': { LessonDialog: 'Dialog' },
  }, { React: h.react });
  h.mount(() => LearnPage());
  const library = () => localWebNodes(h.tree).find(node => node.type === 'Library');
  const bar = () => localWebNodes(h.tree).find(node => node.props.role === 'progressbar');
  const lessons = library().props.lessons;
  assert.equal(bar().props['aria-valuenow'], 0);
  library().props.onOpen(lessons[0]); h.render();
  assert.equal(state.value.learnProgress[lessons[0].id], undefined);
  const dialogHarness = localWebHarness();
  const { LessonDialog } = load('src/pages/learn/components/LessonDialog.tsx', {
    react: dialogHarness.react, '../../../learn/LearnProgress': progress,
    'react-dom': { createPortal: node => node }, '../../../components/ui/Icon': { Icon: 'Icon' },
  }, { React: dialogHarness.react, document: { body: {} } });
  dialogHarness.mount(() => LessonDialog({ lesson: lessons[0], onClose: () => {} }));
  const complete = () => localWebNodes(dialogHarness.tree).find(node => node.type === 'button' && /Mark/.test(node.children[0]));
  assert.equal(state.value.learnProgress[lessons[0].id], undefined);
  complete().props.onClick(); state.h.render(); dialogHarness.render(); h.render();
  assert.equal(bar().props['aria-valuenow'], 1);
  assert.equal(complete().children[0], 'Mark as not completed');
  complete().props.onClick(); state.h.render(); h.render();
  assert.equal(bar().props['aria-valuenow'], 0);
  for (const lesson of lessons) { state.value.toggleLessonComplete(lesson.id); state.h.render(); }
  state.value.toggleLessonComplete('unknown-lesson'); state.h.render(); h.render();
  assert.equal(bar().props['aria-valuenow'], 9); assert.equal(bar().props['aria-valuemax'], 9);
  const { LearningPath } = load('src/pages/learn/components/LearningPath.tsx', { '../../../components/ui/Card': { Card: 'Card' } }, { React: h.react });
  const pathTree = LearningPath({ learnProgress: state.value.learnProgress });
  assert.deepEqual(localWebNodes(pathTree).filter(node => node.type === 'b').map(node => node.children.join('')), ['4/4 completed', '1/1 completed', '4/4 completed']);
});

test('web Reset local data confirms/cancels, blocks duplicates, retries failure and preserves unrelated data', async () => {
  const h = localWebHarness(); let clears = 0, privacyResets = 0, fail = true, release;
  const { DeferredSettingsSections } = load('src/pages/settings/components/DeferredSettingsSections.tsx', {
    '../../../app/routes': { go: () => {} },
    react: h.react, '../../../components/ui/Card': { Card: 'Card' }, '../../../components/ui/Icon': { Icon: 'Icon' },
    '../../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' }, './AboutAuraDialog': { AboutAuraDialog: 'AboutDialog' }, '../SettingsPage.module.css': {},
    '../../../privacy/PortfolioPrivacy': { usePortfolioPrivacy: () => ({ hideValues: true, ready: true, setHideValues: () => {}, resetPrivacy: async () => { privacyResets++; } }) },
    '../../../learn/LearnProgress': { useLearnProgress: () => ({ resetLocalData: async () => { clears++; if (fail) throw Error('blocked'); await new Promise(resolve => { release = resolve; }); } }) },
  }, { React: h.react });
  h.mount(() => DeferredSettingsSections());
  const button = () => localWebNodes(h.tree).find(node => node.props['aria-label'] === 'Reset local data');
  const dialog = () => localWebNodes(h.tree).find(node => node.type === 'Dialog');
  button().props.onClick(); h.render(); assert.equal(clears, 0);
  assert.equal(dialog().props.tone, 'danger'); assert.match(dialog().props.description, /turns Hide portfolio values off/);
  assert.match(dialog().props.description, /session stay unchanged/);
  const staleConfirm = dialog().props.onConfirm;
  dialog().props.onCancel(); h.render(); staleConfirm();
  assert.equal(clears, 0); assert.equal(dialog(), undefined);
  button().props.onClick(); h.render(); dialog().props.onConfirm();
  await new Promise(resolve => setImmediate(resolve)); h.render();
  assert.equal(clears, 1); assert.equal(privacyResets, 0); assert.match(JSON.stringify(dialog()), /Local reset incomplete/);
  fail = false; dialog().props.onConfirm(); dialog().props.onConfirm(); h.render();
  assert.equal(clears, 2); assert.equal(dialog().props.busy, true); assert.equal(button().props.disabled, true);
  dialog().props.onCancel(); h.render(); assert.ok(dialog());
  release(); await new Promise(resolve => setImmediate(resolve)); h.render();
  assert.equal(privacyResets, 1); assert.equal(dialog(), undefined);
  assert.match(JSON.stringify(h.tree), /Local data reset/);
});

test('web strict privacy reset persists before unmasking and retains other account preferences', async () => {
  let fail = true;
  const saved = new Map([['aura_portfolio_privacy_v1:a', 'true'], ['aura_portfolio_privacy_v1:b', 'true']]);
  const state = mountWebPrivacy('a', { getItem: key => saved.get(key), setItem: (key, value) => { if (fail) throw Error('blocked'); saved.set(key, value); } });
  await assert.rejects(() => state.value.resetPrivacy());
  assert.equal(state.value.hideValues, true); assert.match(state.value.storageError, /could not be reset/);
  fail = false; await state.value.resetPrivacy();
  assert.equal(state.value.hideValues, false); assert.equal(saved.get('aura_portfolio_privacy_v1:a'), 'false');
  assert.equal(saved.get('aura_portfolio_privacy_v1:b'), 'true');
});
test('web/mobile Help content is identical, searchable by answer/category, and truthful about local data and support', () => {
  const api = load('src/pages/help/helpContent.ts');
  const mobileContent = fs.readFileSync(path.join(root, '../mobile/src/screens/settings/helpContent.ts'), 'utf8');
  assert.equal(mobileContent, fs.readFileSync(path.join(root, 'src/pages/help/helpContent.ts'), 'utf8'));
  const original = JSON.stringify(api.helpSections);
  assert.equal(api.helpSections.length, 7);
  const articles = api.helpSections.flatMap(section => section.articles);
  assert.equal(articles.length, 20); assert.equal(new Set(articles.map(article => article.id)).size, 20);
  assert.equal(api.filterHelpSections('   ').length, 7);
  assert.equal(api.filterHelpSections(' PORTFOLIO TYPES ').flatMap(section => section.articles).length, 2);
  assert.equal(api.filterHelpSections('Sharpe ratio')[0].articles[0].id, 'risk-metrics');
  assert.equal(api.filterHelpSections('authentication tokens').flatMap(section => section.articles).length > 0, true);
  assert.equal(api.filterHelpSections('qzx-no-article').length, 0);
  assert.equal(JSON.stringify(api.helpSections), original, 'search never mutates content');
  const answer = id => articles.find(article => article.id === id).answer.join(' ');
  assert.match(answer('reset-local-data'), /turns Hide portfolio values Off/);
  assert.match(answer('reset-local-data'), /does not delete your account/);
  assert.match(answer('reset-local-data'), /Other accounts/);
  assert.match(answer('assistant-context'), /specific simulation/);
  assert.match(answer('assistant-context'), /does not automatically analyze every past report/);
  assert.match(answer('original-comparison'), /latest saved analysis/);
  assert.match(answer('contact-support'), /not available yet/);
  assert.doesNotMatch(original, /mailto:|https?:\/\/|buy this|guaranteed return/i);
});

test('web Help uses native expandable questions, searches answers, clears empty results and returns to Settings', () => {
  const h = localWebHarness(), navigations = [];
  const { HelpSupportPage } = load('src/pages/help/HelpSupportPage.tsx', {
    react: h.react, '../../app/routes': { go: route => navigations.push(route) },
    '../../components/ui/Card': { Card: 'Card' }, '../../components/ui/Icon': { Icon: 'Icon' },
    './helpContent': load('src/pages/help/helpContent.ts'), './HelpSupportPage.module.css': {},
  }, { React: h.react });
  h.mount(() => HelpSupportPage());
  const nodes = () => localWebNodes(h.tree);
  const search = value => { nodes().find(node => node.type === 'input').props.onChange({ target: { value } }); h.render(); };
  assert.equal(nodes().filter(node => node.type === 'details').length, 20);
  assert.equal(nodes().filter(node => node.type === 'summary').length, 20);
  assert.ok(nodes().filter(node => node.type === 'details').every(node => node.props.open === undefined), 'collapsed until native activation');
  search(' Sharpe ratio ');
  assert.equal(nodes().filter(node => node.type === 'details').length, 1);
  assert.equal(nodes().find(node => node.type === 'summary').children[0], 'How should I read the risk metrics?');
  search('qzx-no-article'); assert.equal(nodes().filter(node => node.type === 'details').length, 0);
  assert.match(JSON.stringify(h.tree), /No matching help articles/);
  nodes().find(node => node.type === 'button' && node.children[0] === 'Clear search').props.onClick(); h.render();
  assert.equal(nodes().filter(node => node.type === 'details').length, 20);
  nodes().find(node => node.type === 'button' && node.children.includes(' Back to Settings')).props.onClick();
  assert.deepEqual(navigations, ['settings']);
  const source = fs.readFileSync(path.join(root, 'src/pages/help/HelpSupportPage.tsx'), 'utf8');
  assert.doesNotMatch(source, /fetch\(|localStorage|sessionStorage|authApi|resetLocalData/);
  const css = fs.readFileSync(path.join(root, 'src/pages/help/HelpSupportPage.module.css'), 'utf8');
  assert.match(css, /summary:focus-visible/); assert.match(css, /var\(--teal-primary\)/);
  assert.match(css, /@media \(max-width: 600px\)/);
});
test('web/mobile answer parsers recognize real Markdown tables without dropping values or parsing literal pipes', () => {
  const web = load('src/pages/assistant/answerFormatting.ts');
  const mobile = load('../mobile/src/agent/answerFormatting.ts');
  assert.equal(fs.readFileSync(path.join(root, 'src/pages/assistant/answerFormatting.ts'), 'utf8'), fs.readFileSync(path.join(root, '../mobile/src/agent/answerFormatting.ts'), 'utf8'));
  const samples = [
    '## Comparison\r\n\r\nBefore.\r\n| Metric | Original | Modified |\r\n| :--- | :---: | ---: |\r\n| **Return** | -2.50% | 0 |\r\n| Sharpe | Unavailable | 1.20 |\r\n\r\n- After.',
    'Name | Value\n--- | ---:\nAlpha | -$1,234.56\nBeta | N/A',
    '| Label | Value |\n| --- | --- |\n| A \\| B | `x|y` |\n| C |  |',
    '| A | B |\n| --- | --- |\n| 1 | 2 |\n\nOther text\n\n| C | D |\n| --- | --- |\n| 3 | 4 |',
    '| One column |\n| --- |\n| unchanged |',
    '```markdown\n| Literal | Example |\n| --- | --- |\n| a | b |\n```',
    '|asda|asdf|\nNot a complete table.',
    '| A | B |\n| --- | not-a-separator |\n| 10 | 20 |',
    '| A | B |\n| --- | --- |\n| 10 | 20 | 30 |',
  ];
  for (const input of samples) assert.deepEqual(plain(web.formatAgentAnswer(input)), plain(mobile.formatAgentAnswer(input)));
  const blocks = web.formatAgentAnswer(samples[0]);
  assert.deepEqual(plain(blocks.map(block => block.type)), ['heading', 'paragraph', 'table', 'bullets']);
  const table = blocks[2];
  assert.deepEqual(plain(table.alignments), ['left', 'center', 'right']);
  assert.equal(table.rows[0][0][0].bold, true);
  assert.equal(table.rows[0][1][0].text, '-2.50%'); assert.equal(table.rows[0][2][0].text, '0');
  assert.equal(table.rows[1][1][0].text, 'Unavailable');
  const escaped = web.formatAgentAnswer(samples[2])[0];
  assert.equal(escaped.rows[0][0][0].text, 'A | B'); assert.equal(escaped.rows[0][1][0].text, '`x|y`');
  assert.deepEqual(plain(escaped.rows[1][1]), []);
  assert.equal(web.formatAgentAnswer(samples[3]).filter(block => block.type === 'table').length, 2);
  assert.equal(web.formatAgentAnswer(samples[4])[0].headers.length, 1);
  for (const input of samples.slice(5, 8)) assert.ok(web.formatAgentAnswer(input).every(block => block.type !== 'table'));
  assert.match(JSON.stringify(web.formatAgentAnswer(samples[8])), /30/, 'malformed extra cells are preserved as text, not truncated');
});

test('web AI answer tables use semantic headers, keyboard scrolling, escaped text and keep existing formatting', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { AnswerContent } = load('src/pages/assistant/components/AnswerContent.tsx', {
    '../answerFormatting': load('src/pages/assistant/answerFormatting.ts'), '../AssistantPage.module.css': { answerTable: 'answerTable' },
  }, { React: react });
  const answer = '## Results\n\n| Metric | Value |\n| --- | ---: |\n| **Return** | -2.50% |\n| <img src=x onerror=alert(1)> | 0 |\n\n- Preserved bullet\n\nAfter the table.';
  const tree = AnswerContent({ answer });
  const nodes = localWebNodes(tree);
  assert.equal(nodes.filter(node => node.type === 'table').length, 1);
  assert.equal(nodes.filter(node => node.type === 'th' && node.props.scope === 'col').length, 2);
  assert.equal(nodes.find(node => node.props.role === 'region').props.tabIndex, 0);
  assert.equal(nodes.find(node => node.type === 'td' && node.props.style.textAlign === 'right').children[0][0].children[0], '-2.50%');
  assert.ok(nodes.some(node => node.type === 'strong' && node.children[0] === 'Return'));
  assert.ok(nodes.some(node => node.type === 'span' && node.children[0] === '<img src=x onerror=alert(1)>'));
  assert.equal(nodes.filter(node => node.type === 'img').length, 0);
  assert.equal(nodes.filter(node => node.type === 'h3').length, 1); assert.equal(nodes.filter(node => node.type === 'ul').length, 1);
  assert.equal(answer.includes('-2.50%'), true, 'formatting never mutates the source answer');
  const source = fs.readFileSync(path.join(root, 'src/pages/assistant/components/AnswerContent.tsx'), 'utf8');
  assert.doesNotMatch(source, /dangerouslySetInnerHTML|eval\(|fetch\(/);
  const css = fs.readFileSync(path.join(root, 'src/pages/assistant/AssistantPage.module.css'), 'utf8');
  assert.match(css, /overflow-x: auto/); assert.match(css, /answerTableWrap:focus-visible/);
});
