const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');

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
  const validation = load('src/pages/portfolios/portfolioValidation.ts');
  const today = new Date();
  const date = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, '0'),
    String(today.getDate()).padStart(2, '0'),
  ].join('-');

  const current = validation.validateRealHoldingDrafts([{
    id: 1,
    symbol: ' aapl ',
    investedAmount: '1000.25',
    investedCurrency: 'USD',
    shares: '5.5',
    purchaseDate: date,
  }]);
  assert.equal(current.error, null);
  assert.deepEqual(plain(current.holdings), [{
    symbol: 'AAPL',
    invested_amount: '1000.25',
    invested_currency: 'USD',
    shares: '5.5',
    purchase_date: date,
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
});

test('simulation editors initialize from backend current and planned weights in saved order', () => {
  class ApiError extends Error {}
  const simulation = load('src/pages/simulations/simulationUi.ts', {
    '../../api/apiClient': { ApiError },
  });
  assert.deepEqual(plain(simulation.allocationInputsFromValuation({ holdings: [
    { symbol: 'MSFT', current_allocation: '0.625' },
    { symbol: 'AAPL', current_allocation: '0.375' },
  ] })), { MSFT: '62.5', AAPL: '37.5' });
  assert.deepEqual(plain(simulation.allocationInputsFromPlannedAllocation({ holdings: [
    { symbol: 'AAPL', target_allocation: '0.4' },
    { symbol: 'NVDA', target_allocation: '0.6' },
  ] })), { AAPL: '40', NVDA: '60' });

  const portfolio = { holdings: [{ symbol: 'BND' }, { symbol: 'AAPL' }] };
  const result = simulation.validateModifiedAllocation(portfolio, { AAPL: '75', BND: '25' });
  assert.equal(result.error, null);
  assert.deepEqual(plain(result.allocation), [
    { symbol: 'BND', weight: 0.25 },
    { symbol: 'AAPL', weight: 0.75 },
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
  const assistant = read('src/pages/assistant/AssistantPage.tsx');
  const app = read('src/app/App.tsx');

  assert.match(report, /assistant\/\$\{report\.portfolio_id\}\/report\/\$\{report\.id\}/);
  assert.match(simulation, /assistant\/\$\{portfolioId\}\/simulation\/\$\{simulationId\}/);
  assert.match(assistant, /report_id: savedContext\.id/);
  assert.match(assistant, /simulation_id: savedContext\.id/);
  assert.match(assistant, /setLoadError\('Portfolio not found\.'\)/);
  assert.match(app, /route\.reportId === 'report'/);
  assert.match(app, /route\.reportId === 'simulation'/);
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

test('web current-value failures offer compact portfolio reanalysis recovery', () => {
  const dashboard = fs.readFileSync(path.join(root, 'src/pages/dashboard/DashboardPage.tsx'), 'utf8');
  const errorStyles = fs.readFileSync(path.join(root, 'src/components/ui/ApiErrorState.module.css'), 'utf8');

  assert.match(dashboard, /retryTitle=\{portfolio\.portfolio_type === 'CURRENT' \? 'Analyze Portfolio Again' : 'Retry allocation'\}/);
  assert.match(dashboard, /\? \(\) => go\(`analytics\/\$\{portfolio\.id\}`\)/);
  assert.match(dashboard, /Any existing analysis may be out of date/);
  assert.match(dashboard, /compactAction=\{portfolio\.portfolio_type === 'CURRENT'\}/);
  assert.match(errorStyles, /\.actions \.compactAction\{min-width:0;width:auto\}/);
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
