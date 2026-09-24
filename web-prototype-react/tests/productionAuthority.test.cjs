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
  assert.match(reportDetail, /getElementById\('per-asset-analysis'\)\?\.scrollIntoView/);
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
