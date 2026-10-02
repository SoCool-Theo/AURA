// Node-only orchestration checks using the installed TypeScript compiler.
// The minimal hook harness is not a React Native renderer or device E2E test.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const supportedAssetSymbols = [
  'AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'GOOGL', 'META', 'SPY', 'QQQ',
  'DIA', 'VTI', 'GLD', 'SLV', 'BND', 'TLT', 'BTC-USD', 'ETH-USD'
];

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

test('mobile Settings sign out confirms, cancels safely, retries failures, and blocks duplicate taps', async () => {
  const harness = hookHarness();
  const user = { email: 'user@example.com' };
  harness.react.createElement = (type, props, ...children) => ({ type, props: props ?? {}, children });
  let signOuts = 0, fail = true, pending;
  const { SettingsScreen } = load('src/screens/settings/SettingsScreen.tsx', {
    react: harness.react,
    'react-native': { Alert: { alert: () => assert.fail('Sign out must use the themed dialog') }, KeyboardAvoidingView: 'Avoid', Modal: 'Modal', Platform: { OS: 'android' }, Pressable: 'Pressable', ScrollView: 'Scroll', Text: 'Text', TextInput: 'Input', View: 'View', StyleSheet: { create: value => value } },
    'react-native-safe-area-context': { SafeAreaView: 'Safe' }, '@expo/vector-icons': { Ionicons: 'Icon' },
    '../../components/ui/Button': { Button: 'Button' },
    '../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
    './DeleteAccountSection': { DeleteAccountSection: 'DeleteAccount' },
    '../../components/ui/Card': { Card: 'Card' }, '../../components/ui/PageTitle': { PageTitle: 'Title' },
    '../../api/authApi': { authApi: {} }, '../../api/apiErrorPresentation': {}, '../../api/apiClient': { ApiError: Error },
    '../../auth/accountIdentity': { accountDisplayName: () => 'Aura User', accountInitials: () => 'AU' },
    '../../auth/useAuth': { useAuth: () => ({ user, setCurrentUser: () => {}, signOut: async () => {
      signOuts++; if (fail) throw Error('storage failed'); await pending.promise;
    } }) },
    '../../hooks/useAppData': { useAppData: () => ({ resetLocalData: () => assert.fail('Sign out must not reset data') }) },
    '../../preferences/usePreferences': { usePreferences: () => ({ themeMode: 'dark', setThemeMode: () => {}, resetPreferences: () => assert.fail('Sign out must not reset preferences') }) },
    '../../theme/theme': { colors: {}, spacing: {} },
  });
  harness.mount(() => SettingsScreen()); await harness.settle();
  const nodes = () => {
    const all = [];
    function visit(node) { if (!node || typeof node !== 'object') return; all.push(node); node.children?.forEach(visit); }
    visit(harness.value); return all;
  };
  const button = () => nodes().find(node => node.type === 'Button' && ['Sign out', 'Please wait…'].includes(node.props.title));
  const dialog = () => nodes().find(node => node.type === 'Dialog');
  assert.equal(dialog().props.visible, false);
  button().props.onPress(); await harness.settle();
  assert.equal(dialog().props.visible, true); assert.equal(signOuts, 0);
  assert.equal(dialog().props.tone, 'danger'); assert.equal(dialog().props.iconName, 'log-out-outline');
  assert.match(dialog().props.description, /will not be deleted/);
  const staleConfirm = dialog().props.onConfirm;
  dialog().props.onCancel(); await harness.settle(); staleConfirm(); await harness.settle();
  assert.equal(signOuts, 0); assert.equal(dialog().props.visible, false);
  button().props.onPress(); await harness.settle(); dialog().props.onConfirm(); await harness.settle();
  assert.equal(signOuts, 1); assert.match(dialog().props.errorMessage, /retry sign out/);
  fail = false; pending = deferred();
  dialog().props.onConfirm(); dialog().props.onConfirm(); await harness.settle();
  assert.equal(signOuts, 2); assert.equal(dialog().props.busy, true); assert.equal(button().props.disabled, true);
  dialog().props.onCancel(); await harness.settle(); assert.equal(dialog().props.visible, true);
  pending.resolve(); await harness.settle(); assert.equal(dialog().props.visible, false);
});

test('mobile saved-session Sign Out also confirms and retains its retry flow', async () => {
  const harness = hookHarness();
  harness.react.createElement = (type, props, ...children) => ({ type, props: props ?? {}, children });
  let signOuts = 0, retries = 0, fail = true, pending;
  const { SessionRestoreScreen } = load('src/screens/auth/SessionRestoreScreen.tsx', {
    react: harness.react, 'react-native': { StyleSheet: { create: value => value } },
    'react-native-safe-area-context': { SafeAreaView: 'Safe' }, '../../theme/theme': { colors: {} },
    '../../components/ui/ErrorState': { ScreenErrorState: 'Error' },
    '../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
  });
  harness.mount(() => SessionRestoreScreen({ message: 'Session unavailable', error: Error('offline'), onRetry: async () => { retries++; }, onSignOut: async () => {
    signOuts++; if (fail) throw Error('storage failed'); await pending.promise;
  } }));
  const screen = () => harness.value.children[0]; const dialog = () => harness.value.children[1];
  screen().props.onRetry(); await harness.settle(); assert.equal(retries, 1); assert.equal(signOuts, 0);
  screen().props.onBack(); await harness.settle(); assert.equal(dialog().props.visible, true); assert.equal(signOuts, 0);
  dialog().props.onCancel(); await harness.settle(); assert.equal(signOuts, 0);
  screen().props.onBack(); await harness.settle(); dialog().props.onConfirm(); await harness.settle();
  assert.equal(signOuts, 1); assert.match(dialog().props.errorMessage, /Please retry/);
  fail = false; pending = deferred();
  dialog().props.onConfirm(); dialog().props.onConfirm(); await harness.settle(); assert.equal(signOuts, 2);
  dialog().props.onCancel(); screen().props.onRetry(); await harness.settle();
  assert.equal(dialog().props.visible, true); assert.equal(retries, 1);
  pending.resolve(); await harness.settle(); assert.equal(dialog().props.visible, false);
});

test('danger confirmation Close and Cancel use red without changing default dialogs or busy guards', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const colors = { text: '#fff', danger: '#FF6B7A', surfaceAlt: '#14213A', negativeBackground: '#2C171E', dangerBorder: '#5B2631' };
  const { ConfirmationDialog } = load('src/components/ui/ConfirmationDialog.tsx', {
    react,
    '@expo/vector-icons': { Ionicons: 'Icon' },
    'react-native': { Modal: 'Modal', KeyboardAvoidingView: 'AvoidingView', ScrollView: 'Scroll', Pressable: 'Pressable', Text: 'Text', View: 'View', Platform: { OS: 'android' }, StyleSheet: { create: styles => styles } },
    '../../theme/theme': { colors, spacing: {} },
    './Button': { Button: 'Button' },
  });
  for (const tone of [undefined, 'danger']) {
    for (const busy of [false, true]) {
      let cancelled = 0;
      const tree = ConfirmationDialog({ visible: true, title: 'Delete account?', description: 'Permanent', subject: 'user@example.com', subjectLabel: 'Account', confirmLabel: 'Delete Account', tone, busy, onCancel: () => { cancelled++; }, onConfirm: () => {} });
      const nodes = [];
      function visit(node) {
        if (!node || typeof node !== 'object') return;
        nodes.push(node); node.children?.forEach(visit);
      }
      visit(tree);
      const close = nodes.find(node => node.type === 'Pressable');
      const cancel = nodes.find(node => node.type === 'Button' && node.props.title === 'Cancel');
      const closeStyle = Object.assign({}, ...close.props.style.filter(Boolean));
      assert.equal(close.children[0].props.color, tone === 'danger' ? colors.danger : colors.text);
      assert.equal(closeStyle.backgroundColor, tone === 'danger' ? colors.negativeBackground : colors.surfaceAlt);
      if (tone === 'danger') assert.equal(closeStyle.borderColor, colors.dangerBorder);
      assert.equal(cancel.props.variant, tone === 'danger' ? 'danger' : 'secondary');
      assert.equal(close.props.disabled, busy);
      assert.equal(cancel.props.disabled, busy);
      tree.props.onRequestClose(); assert.equal(cancelled, busy ? 0 : 1);
      if (!busy) { close.props.onPress(); cancel.props.onPress(); assert.equal(cancelled, 3); }
    }
  }
});

test('bottom-tab presses return nested stacks to their roots, including cold deep links', () => {
  let key = 0;
  const routerPath = 'node_modules/@react-navigation/routers/src/';
  const nanoid = { nanoid: () => String(++key) };
  const CommonActions = load(`${routerPath}CommonActions.tsx`);
  const BaseRouter = load(`${routerPath}BaseRouter.tsx`, { 'nanoid/non-secure': nanoid });
  const createParamsFromAction = load(`${routerPath}createParamsFromAction.tsx`);
  const createRouteFromAction = load(`${routerPath}createRouteFromAction.tsx`, {
    'nanoid/non-secure': nanoid, './createParamsFromAction': createParamsFromAction
  });
  const routerMocks = {
    'nanoid/non-secure': nanoid, './BaseRouter': BaseRouter,
    './createParamsFromAction': createParamsFromAction, './createRouteFromAction': createRouteFromAction
  };
  const { StackRouter } = load(`${routerPath}StackRouter.tsx`, routerMocks);
  const SwitchRouter = load(`${routerPath}SwitchRouter.tsx`, routerMocks);
  const { TabRouter } = load(`${routerPath}TabRouter.tsx`, { './SwitchRouter': SwitchRouter });
  const tabRoots = load('src/navigation/tabRootNavigation.ts', {
    '@react-navigation/native': { CommonActions }
  });
  const mocks = {
    react: { createElement: (type, props, ...children) => ({ type, props, children }) },
    '@expo/vector-icons': { Ionicons: 'Icon' },
    '@react-navigation/bottom-tabs': { createBottomTabNavigator: () => ({ Navigator: 'TabNavigator', Screen: 'TabScreen' }) },
    '@react-navigation/native-stack': { createNativeStackNavigator: () => ({ Navigator: 'StackNavigator', Screen: 'StackScreen' }) },
    '../theme/colors': { darkPalette: {}, lightPalette: {} },
    '../preferences/usePreferences': { usePreferences: () => ({ themeMode: 'dark' }) },
    '../components/ui/HomeHeaderButton': { HomeHeaderButton: 'HomeHeaderButton' },
    '../components/ui/BackHeaderButton': { BackHeaderButton: 'BackHeaderButton' },
    './tabRootNavigation': tabRoots
  };
  // Screens are irrelevant to this navigator listener test; stub their named exports.
  const source = ts.createSourceFile('navigator.tsx', fs.readFileSync(path.join(root, 'src/navigation/MainTabNavigator.tsx'), 'utf8'), ts.ScriptTarget.Latest, true);
  for (const node of source.statements) {
    if (!ts.isImportDeclaration(node) || !node.moduleSpecifier.text.startsWith('../screens/')) continue;
    mocks[node.moduleSpecifier.text] = Object.fromEntries(
      node.importClause.namedBindings.elements.map(binding => [binding.name.text, binding.name.text])
    );
  }
  const { MainTabNavigator } = load('src/navigation/MainTabNavigator.tsx', mocks);
  const listeners = MainTabNavigator().props.screenListeners;
  const tabOptions = {
    routeNames: ['Home', 'Portfolio', 'Simulate', 'AI', 'MoreTab'], routeParamList: {}, routeGetIdList: {}
  };
  const cases = [
    ['Portfolio', 'Portfolios', 'PortfolioDetail'],
    ['Simulate', 'Simulations', 'SimulationResult'],
    ['MoreTab', 'More', 'Reports'],
    ['MoreTab', 'More', 'LearnDetail'],
    ['MoreTab', 'More', 'Settings']
  ];
  for (const [tab, rootScreen, detail] of cases) {
    for (const focused of [false, true]) {
      for (const coldDeepLink of [false, true]) {
        const tabs = TabRouter({});
        let state = tabs.getInitialState(tabOptions);
        const tabIndex = state.routes.findIndex(route => route.name === tab);
        const stack = StackRouter({ initialRouteName: rootScreen });
        const stackOptions = { routeNames: [rootScreen, detail], routeParamList: {}, routeGetIdList: {} };
        const child = stack.getRehydratedState({
          index: coldDeepLink ? 0 : 1,
          routes: [...(coldDeepLink ? [] : [{ name: rootScreen }]), {
            name: detail, params: { portfolioId: 'portfolio-1', simulationId: 'run-1', lessonId: 'volatility' }
          }]
        }, stackOptions);
        state.routes[tabIndex] = { ...state.routes[tabIndex], state: child, params: { screen: detail, params: child.routes.at(-1).params } };
        if (focused) state = tabs.getStateForRouteFocus(state, state.routes[tabIndex].key);
        const previousState = state;
        let prevented = false;
        listeners({
          route: state.routes[tabIndex],
          navigation: { dispatch: action => { state = tabs.getStateForAction(state, action, tabOptions); } }
        }).tabPress({ preventDefault: () => { prevented = true; } });
        assert.ok(prevented);
        assert.equal(state.index, tabIndex);
        const params = state.routes[tabIndex].params;
        assert.equal(params.screen, undefined, 'stale detail screen params are replaced');
        // React Navigation applies nested params.state as a reset to the child router.
        const reset = stack.getStateForAction(child, CommonActions.reset(params.state), stackOptions);
        const result = stack.getRehydratedState(reset, stackOptions);
        assert.deepEqual(Array.from(result.routes, route => route.name), [rootScreen]);
        assert.equal(result.index, 0);
        assert.equal(result.routes[0].params, undefined);
        assert.equal(stack.getStateForAction(result, CommonActions.goBack(), stackOptions), null);
        state.routes.forEach((route, index) => {
          if (index !== tabIndex) assert.equal(route, previousState.routes[index], 'other tabs and AI context remain untouched');
        });
      }
    }
  }
  for (const name of ['Home', 'AI']) {
    listeners({ route: { name }, navigation: { dispatch: () => assert.fail('Keep leaf-tab navigation native') } })
      .tabPress({ preventDefault: () => assert.fail('Keep leaf-tab navigation native') });
  }
});

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

test('account deletion uses authenticated DELETE with a password body and empty 204', async () => {
  const calls = [];
  const transport = load('src/api/apiClient.ts', {
    '../auth/authStorage': { getToken: async () => 'token' },
    '../config/environment': { environment: { apiBaseUrl: 'http://example.invalid' } }
  }, { fetch: async (url, options) => {
    calls.push({ url, options }); return { status: 204, ok: true, text: async () => '' };
  } });
  const { authApi } = load('src/api/authApi.ts', { './apiClient': transport });
  assert.equal(await authApi.deleteAccount({ current_password: 'current-password' }), undefined);
  assert.equal(calls[0].url, 'http://example.invalid/api/auth/me');
  assert.equal(calls[0].options.method, 'DELETE');
  assert.equal(calls[0].options.headers.get('Authorization'), 'Bearer token');
  assert.deepEqual(JSON.parse(calls[0].options.body), { current_password: 'current-password' });
});

test('mobile account deletion is above sign out and requires password confirmation before deletion', async () => {
  for (const logoutThrows of [false, true]) {
    const harness = hookHarness();
    harness.react.createElement = (type, props, ...children) => ({ type, props: props ?? {}, children });
    const calls = [], busyChanges = []; let fail = true, signedOut = 0, pending;
    class ApiError extends Error { constructor() { super('Wrong password'); this.status = 403; } }
    const { DeleteAccountSection } = load('src/screens/settings/DeleteAccountSection.tsx', {
      react: harness.react,
      'react-native': { View: 'View', Text: 'Text', TextInput: 'Input', StyleSheet: { create: value => value } },
      '../../api/authApi': { authApi: { deleteAccount: async request => {
        calls.push(JSON.parse(JSON.stringify(request))); if (fail) throw new ApiError(); await pending.promise;
      } } },
      '../../api/apiClient': { ApiError },
      '../../api/apiErrorPresentation': { apiErrorPresentation: () => ({ message: 'Unable to delete account.' }) },
      '../../auth/useAuth': { useAuth: () => ({ user: { email: 'user@example.com' }, signOut: async () => {
        signedOut++; if (logoutThrows) throw Error('storage unavailable');
      } }) },
      '../../components/ui/Button': { Button: 'Button' },
      '../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
      '../../theme/theme': { colors: {}, spacing: {} },
    });
    harness.mount(() => DeleteAccountSection({ onBusyChange: value => busyChanges.push(value) }));
    const button = () => harness.value.children[2];
    const dialog = () => harness.value.children[3];
    const password = value => dialog().children[1].props.onChangeText(value);
    assert.equal(button().props.variant, 'danger'); assert.equal(calls.length, 0);
    button().props.onPress(); await harness.settle();
    assert.equal(dialog().props.tone, 'danger');
    assert.equal(dialog().props.confirmDisabled, true);
    dialog().props.onConfirm(); await harness.settle(); assert.equal(calls.length, 0);
    password('current-password'); await harness.settle();
    dialog().props.onCancel(); await harness.settle(); assert.equal(calls.length, 0);
    button().props.onPress(); await harness.settle();
    assert.equal(dialog().props.confirmDisabled, true);
    password('current-password'); await harness.settle();
    dialog().props.onConfirm(); await harness.settle();
    assert.equal(dialog().props.errorMessage, 'The current password is incorrect.'); assert.equal(signedOut, 0);
    fail = false; pending = deferred();
    dialog().props.onConfirm(); dialog().props.onConfirm(); await harness.settle();
    assert.equal(calls.length, 2); assert.equal(dialog().props.busy, true);
    dialog().props.onCancel(); await harness.settle(); assert.equal(dialog().props.visible, true);
    pending.resolve(); await harness.settle();
    assert.equal(signedOut, 1); assert.equal(dialog().props.visible, false); assert.equal(button().props.disabled, true);
    assert.deepEqual(busyChanges, [true, false, true, false]);
    assert.deepEqual(calls[1], { current_password: 'current-password' });
  }
  const settings = fs.readFileSync(path.join(root, 'src/screens/settings/SettingsScreen.tsx'), 'utf8');
  assert.ok(settings.indexOf('<DeleteAccountSection') > settings.indexOf('Data & support'));
  assert.ok(settings.indexOf('<DeleteAccountSection') < settings.indexOf("title={pending ? 'Please wait…' : 'Sign out'}"));
  assert.match(settings, /disabled={pending \|\| accountDeleting}/);
});

test('simulation delete transport accepts an empty 204 and encodes both IDs', async () => {
  const calls = [];
  const transport = load('src/api/apiClient.ts', {
    '../auth/authStorage': { getToken: async () => 'token' },
    '../config/environment': { environment: { apiBaseUrl: 'http://example.invalid' } }
  }, { fetch: async (url, options) => {
    calls.push({ url, options });
    return { status: 204, ok: true, text: async () => '' };
  } });
  const { simulationsApi } = load('src/api/simulationsApi.ts', { './apiClient': transport });
  assert.equal(await simulationsApi.deleteHistory('portfolio/a', 'simulation/b'), undefined);
  assert.equal(calls[0].url, 'http://example.invalid/api/portfolios/portfolio%2Fa/simulations/simulation%2Fb');
  assert.equal(calls[0].options.method, 'DELETE');
  assert.equal(calls[0].options.headers.get('Authorization'), 'Bearer token');
});

test('simulation deletion removes only its row, retains failed deletes, and prevents stale resurrection', async () => {
  const harness = hookHarness();
  const old = { id: 'old', portfolio_id: 'a', created_at: '2026-01-01' };
  const recent = { id: 'recent', portfolio_id: 'a', created_at: '2026-02-01' };
  let pending, failDelete = true;
  const api = {
    listHistoricalScenarios: async () => ({ scenarios: [] }),
    history: async () => pending ? pending.promise : { simulations: [old, recent] },
    deleteHistory: async () => { if (failDelete) throw Error('offline'); }
  };
  const { SimulationProvider } = load('src/simulation/SimulationProvider.tsx', {
    react: harness.react, '../api/simulationsApi': { simulationsApi: api },
    '../auth/useAuth': { useAuth: () => ({ status: 'authenticated', user: { id: 'user' } }) }
  });
  harness.mount(() => SimulationProvider({})); await harness.settle();
  await harness.value.refreshHistory([{ id: 'a', name: 'A' }]); await harness.settle();
  await assert.rejects(harness.value.deleteSimulation('a', 'recent'));
  assert.equal(harness.value.history.length, 2);
  pending = deferred();
  const refresh = harness.value.refreshHistory([{ id: 'a', name: 'A' }]);
  failDelete = false;
  await harness.value.deleteSimulation('a', 'recent'); await harness.settle();
  assert.equal(harness.value.history.map(row => row.id).join(), 'old');
  pending.resolve({ simulations: [old, recent] }); await refresh; await harness.settle();
  assert.equal(harness.value.history.map(row => row.id).join(), 'old');
});

test('mobile simulation deletion requires confirmation, supports cancel/retry, and blocks duplicate submissions', async () => {
  const harness = hookHarness();
  harness.react.createElement = (type, props, ...children) => ({ type, props: props ?? {}, children });
  const calls = []; let fail = true, deleted = 0, pending;
  const { DeleteSimulationButton } = load('src/components/simulations/DeleteSimulationButton.tsx', {
    react: harness.react,
    '../ui/Button': { Button: 'Button' }, '../ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
    '../../simulation/useSimulations': { useSimulations: () => ({ deleteSimulation: async (...ids) => {
      calls.push(ids); if (fail) throw Error('offline'); await pending.promise;
    } }) },
    '../../simulation/simulationErrors': { simulationErrorMessage: error => error.message }
  });
  harness.mount(() => DeleteSimulationButton({ portfolioId: 'a', simulationId: 'b', subject: 'snapshot b', onDeleted: () => { deleted++; } }));
  const button = () => harness.value.children[0];
  const dialog = () => harness.value.children[1];
  assert.equal(dialog().props.visible, false); assert.equal(calls.length, 0);
  button().props.onPress(); await harness.settle();
  dialog().props.onCancel(); await harness.settle(); assert.equal(calls.length, 0);
  button().props.onPress(); await harness.settle(); dialog().props.onConfirm(); await harness.settle();
  assert.equal(dialog().props.errorMessage, 'offline'); assert.equal(dialog().props.visible, true); assert.equal(deleted, 0);
  fail = false; pending = deferred();
  dialog().props.onConfirm(); dialog().props.onConfirm(); await harness.settle();
  assert.equal(calls.length, 2); assert.equal(dialog().props.busy, true);
  dialog().props.onCancel(); await harness.settle(); assert.equal(dialog().props.visible, true);
  pending.resolve(); await harness.settle(); assert.equal(deleted, 1);
  assert.equal(dialog().props.visible, false); assert.equal(calls[1].join(), 'a,b');
  for (const file of ['SimulationHistoryScreen', 'SimulationsScreen', 'SimulationResultScreen']) {
    assert.match(fs.readFileSync(path.join(root, `src/screens/simulations/${file}.tsx`), 'utf8'), /<DeleteSimulationButton/);
  }
});

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
  const portfolioFormatting = load('src/portfolio/portfolioFormatting.ts');
  const dashboard = load('src/dashboard/dashboardPresentation.ts', { '../report/reportFormatting': formatting });
  assert.equal(dashboard.dashboardPercent(null), 'N/A');
  assert.equal(dashboard.dashboardPercent(undefined), 'N/A');
  assert.equal(dashboard.dashboardPercent(-0.25), '-25.00%');
  assert.equal(dashboard.dashboardPercent(0), '0.00%');
  assert.equal(portfolioFormatting.formatSignedPortfolioMoney('820', 'USD'), '+$820.00');
  assert.equal(portfolioFormatting.formatSignedPortfolioMoney('-2380', 'USD'), '−$2,380.00');
  assert.equal(portfolioFormatting.formatSignedPortfolioMoney('0', 'THB'), '฿0.00');
  assert.equal(portfolioFormatting.formatPortfolioQuantity('10.125'), '10.13');
  assert.equal(portfolioFormatting.formatPortfolioQuantity('10'), '10.00');
  assert.equal(portfolioFormatting.formatHoldingDecimalInput('1000.000000000000'), '1000.00');
  const points = [{ date: '2026-02-01', return: -0.2 }, { date: '2026-04-01', return: 0.1 }];
  const filtered = dashboard.filterDashboardReturns(points, '1M');
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0], points[1]);
  assert.equal(points.length, 2);
  assert.deepEqual(
    JSON.parse(JSON.stringify(dashboard.RETURN_VIEW_RANGES)),
    ['1M', '3M', '6M', '1Y', 'ALL']
  );
  assert.equal(dashboard.filterReturnPoints(points, 'ALL').length, 2);
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

test('Welcome uses the two-card preview and unboxed feature icons', () => {
  const welcome = fs.readFileSync(
    path.join(root, 'src/screens/welcome/WelcomeScreen.tsx'),
    'utf8'
  );
  const featureIconStyle = welcome.match(/featureIcon:\s*\{([\s\S]*?)\n\s*\},/);

  assert.ok(featureIconStyle, 'Welcome feature icon style should exist');
  assert.doesNotMatch(featureIconStyle[1], /border(?:Radius|Width|Color)|backgroundColor/);
  assert.match(welcome, /Understand risk clearly/);
  assert.match(welcome, /styles\.chartCard/);
  assert.match(welcome, /styles\.reportCard/);
  assert.doesNotMatch(welcome, /styles\.previewFooter/);
});

test('real holding contracts preserve precision, order, modes, and valuation allocations', () => {
  const validation = load('src/portfolio/portfolioValidation.ts', {
    './supportedAssetSymbols': { supportedAssetSymbols }
  });
  const portfolioTypes = load('src/types/portfolio.ts');
  const simulation = load('src/simulation/simulationValidation.ts');

  const result = validation.validateRealHoldingDrafts([
    { id: 'first', symbol: ' msft ', shares: '10.12' },
    { id: 'second', symbol: 'AAPL', shares: '4.5' }
  ]);
  assert.equal(result.error, null);
  assert.deepEqual(JSON.parse(JSON.stringify(result.holdings)), [
    { symbol: 'MSFT', shares: '10.12' },
    { symbol: 'AAPL', shares: '4.5' }
  ]);
  assert.match(
    validation.validateRealHoldingDrafts([
      { id: 'a', symbol: 'AAPL', shares: '0' }
    ]).error,
    /positive quantity owned/i
  );
  const invalid = validation.validateRealHoldingDrafts([
    { id: 'a', symbol: 'AAPL', shares: '0' }
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(invalid.issue)), {
    index: 0,
    field: 'shares',
    message: invalid.error
  });

  const legacy = { symbol: 'AAPL', weight: 1, invested_amount: null, invested_currency: null, shares: null, purchase_date: null, position: 0 };
  const real = { symbol: 'MSFT', weight: null, invested_amount: null, invested_currency: null, shares: '1', purchase_date: null, position: 0 };
  const planned = { symbol: 'NVDA', weight: null, invested_amount: null, proposed_amount: '2500', invested_currency: null, shares: null, purchase_date: null, position: 0 };
  assert.equal(portfolioTypes.portfolioHoldingMode([]), 'empty');
  assert.equal(portfolioTypes.portfolioHoldingMode([legacy]), 'legacy');
  assert.equal(portfolioTypes.portfolioHoldingMode([real]), 'real');
  assert.equal(portfolioTypes.portfolioHoldingMode([planned]), 'planned');
  assert.equal(portfolioTypes.portfolioHoldingMode([legacy, real]), 'mixed');

  const inputs = simulation.allocationInputsFromValuation({ holdings: [
    { symbol: 'MSFT', current_allocation: '0.625' },
    { symbol: 'AAPL', current_allocation: '0.375' }
  ] });
  assert.deepEqual(JSON.parse(JSON.stringify(inputs)), { MSFT: '62.50', AAPL: '37.50' });
  assert.deepEqual(
    JSON.parse(JSON.stringify(simulation.allocationInputsFromValuation({ holdings: [
      { symbol: 'AAPL', current_allocation: '0.3333333333' },
      { symbol: 'MSFT', current_allocation: '0.3333333333' },
      { symbol: 'NVDA', current_allocation: '0.3333333334' }
    ] }))),
    { AAPL: '33.33', MSFT: '33.33', NVDA: '33.34' }
  );
  assert.equal(simulation.isAllocationPercentInput('12.23'), true);
  assert.equal(simulation.isAllocationPercentInput('12.234'), false);
  const roundedThirds = { AAPL: '33.33', MSFT: '33.33', NVDA: '33.34' };
  const roundedPortfolio = {
    holdings: [
      { symbol: 'AAPL' },
      { symbol: 'MSFT' },
      { symbol: 'NVDA' }
    ]
  };
  assert.equal(simulation.validateModifiedAllocation(roundedPortfolio, roundedThirds).error, null);
  assert.deepEqual(roundedThirds, { AAPL: '33.33', MSFT: '33.33', NVDA: '33.34' });

  const initialAllocation = { AAPL: '40.00', MSFT: '35.00', NVDA: '25.00' };
  const rebalanced = simulation.rebalanceAllocationInputs(
    initialAllocation,
    ['AAPL', 'MSFT'],
    'AAPL',
    '50'
  );
  assert.deepEqual(JSON.parse(JSON.stringify(rebalanced)), {
    AAPL: '50',
    MSFT: '25.00',
    NVDA: '25.00'
  });
  assert.equal(Object.values(rebalanced).reduce((total, value) => total + Number(value), 0), 100);
  assert.deepEqual(initialAllocation, { AAPL: '40.00', MSFT: '35.00', NVDA: '25.00' });
  assert.deepEqual(
    JSON.parse(JSON.stringify(simulation.rebalanceAllocationInputs(
      rebalanced,
      ['AAPL', 'MSFT'],
      'AAPL',
      '20.00'
    ))),
    { AAPL: '20.00', MSFT: '55.00', NVDA: '25.00' }
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(simulation.rebalanceAllocationInputs(
      { AAPL: '100.00', MSFT: '0.00', NVDA: '0.00' },
      ['AAPL', 'MSFT'],
      'AAPL',
      '40.00'
    ))),
    { AAPL: '40.00', MSFT: '60.00', NVDA: '0.00' }
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(simulation.rebalanceAllocationInputs(
      { AAPL: '39.95', MSFT: '54.31', GOOG: '5.74' },
      ['MSFT', 'GOOG'],
      'MSFT',
      '55.00'
    ))),
    { AAPL: '39.95', MSFT: '55.00', GOOG: '5.05' }
  );
  assert.match(
    simulation.validateModifiedAllocation(roundedPortfolio, {
      AAPL: '33.333',
      MSFT: '33.333',
      NVDA: '33.334'
    }).error,
    /needs a weight/
  );
});

test('allocation and combined mobile screens use the two-target allocation editor', () => {
  const allocation = fs.readFileSync(path.join(root, 'src/screens/simulations/AllocationChangeScreen.tsx'), 'utf8');
  const combined = fs.readFileSync(path.join(root, 'src/screens/simulations/CombinedSimulationScreen.tsx'), 'utf8');
  const editor = fs.readFileSync(path.join(root, 'src/components/simulations/AllocationEditor.tsx'), 'utf8');
  const results = fs.readFileSync(path.join(root, 'src/components/simulations/SimulationResults.tsx'), 'utf8');
  assert.match(allocation, /rebalanceAllocationInputs/);
  assert.match(combined, /rebalanceAllocationInputs/);
  assert.match(editor, /percent\.toFixed\(2\)/);
  assert.match(editor, /onBlur/);
  assert.match(editor, /Select exactly two assets/);
  assert.match(editor, /accessibilityRole="checkbox"/);
  assert.match(editor, /editable=\{!disabled && selected && selectedSymbols\.length === 2\}/);
  assert.match(editor, /onPress=\{\(\) => toggleTarget\(holding\.symbol\)\}/);
  assert.match(editor, /onPressIn=\{\(event\) => event\.stopPropagation\(\)\}/);
  assert.match(allocation, /getPortfolioReportHistory\(selectedPortfolioSummary\)/);
  assert.match(allocation, /getReport\(selectedPortfolioSummary\.id, newest\.id\)/);
  assert.match(allocation, /screen: 'ReportDetail'/);
  assert.match(combined, /getPortfolioReportHistory\(selectedPortfolioSummary\)/);
  assert.match(combined, /getReport\(selectedPortfolioSummary\.id, newest\.id\)/);
  assert.match(combined, /screen: 'ReportDetail'/);
  assert.match(results, /Latest saved portfolio analysis/);
  assert.match(results, /Latest portfolio analysis vs new combined simulation/);
  assert.match(results, /metrics=\{response\.modified\.metrics\}/);
  assert.match(results, /points: response\.modified\.trajectory/);
  assert.match(results, /label: 'New combined result'/);
  assert.match(results, /backend original and modified results over the same requested period/);
  assert.match(results, /View latest analysis details/);
});

test('portfolio input warnings identify, reveal, and focus the first invalid mobile field', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const warning = read('src/portfolio/portfolioInputWarning.ts');
  const create = read('src/screens/portfolios/CreatePortfolioScreen.tsx');
  const editor = read('src/components/portfolio/HoldingsEditor.tsx');
  const dialog = read('src/components/portfolio/PortfolioInputWarningDialog.tsx');
  const input = read('src/components/ui/Input.tsx');
  const validation = load('src/portfolio/portfolioValidation.ts', {
    './supportedAssetSymbols': { supportedAssetSymbols }
  });

  assert.doesNotMatch(warning, /Alert\.alert\(/);
  assert.match(warning, /revealField\(warning\.fieldKey\)/);
  assert.match(warning, /apiValidationIssues\(error\)/);
  assert.match(create, /presentInputWarning\(localHoldingInputWarning/);
  assert.match(editor, /presentInputWarning\(localHoldingInputWarning/);
  assert.match(create, /fieldRefs\.current\.get\(fieldKey\)\?\.focus\(\)/);
  assert.match(input, /forwardRef<TextInput, InputProps>/);
  assert.match(dialog, /<Modal/);
  assert.match(dialog, /Check your information/);
  assert.match(dialog, /Show input/);
  assert.match(create, /<PortfolioInputWarningDialog/);
  assert.match(editor, /<PortfolioInputWarningDialog/);
  assert.match(create, /placeholder="10\.50"/);
  assert.match(editor, /placeholder="10\.50"/);
  assert.match(validation.validateRealHoldingDrafts([{
    id: 'one',
    symbol: 'AAPL',
    shares: '10.125'
  }]).error, /up to 2 decimal places/);
  assert.match(validation.validateRealHoldingDrafts([{
    id: 'two',
    symbol: 'ASDF',
    shares: '10.50'
  }]).error, /ASDF is not supported/);
});

test('planned mobile contracts preserve amount authority and consume backend target weights', async () => {
  const validation = load('src/portfolio/portfolioValidation.ts', {
    './supportedAssetSymbols': { supportedAssetSymbols }
  });
  const simulation = load('src/simulation/simulationValidation.ts');
  const calls = [];
  const { portfoliosApi } = load('src/api/portfoliosApi.ts', {
    './apiClient': { apiRequest: async (path, options = {}) => {
      calls.push({ path, options });
      return {};
    } }
  });
  const portfolioId = 'e6518442-58cb-408f-af47-fb00b5550000';
  const holdings = [
    { id: 'a', symbol: ' aapl ', proposedAmount: '4000.00' },
    { id: 'b', symbol: 'NVDA', proposedAmount: '6000' }
  ];
  const result = validation.validatePlannedHoldingDrafts(holdings);
  assert.equal(result.error, null);
  assert.deepEqual(JSON.parse(JSON.stringify(result.holdings)), [
    { symbol: 'AAPL', proposed_amount: '4000.00' },
    { symbol: 'NVDA', proposed_amount: '6000' }
  ]);
  assert.match(validation.validatePlannedHoldingDrafts([
    { id: 'a', symbol: 'AAPL', proposedAmount: '0' }
  ]).error, /positive proposed amount/i);
  assert.match(validation.validatePlannedHoldingDrafts([
    { id: 'a', symbol: 'ASDF', proposedAmount: '1000.00' }
  ]).error, /ASDF is not supported/);

  const allocation = {
    portfolio_id: portfolioId,
    portfolio_type: 'PLANNED',
    plan_currency: 'USD',
    total_proposed_amount: '10000',
    holdings: [
      { id: 'a', symbol: 'AAPL', proposed_amount: '4000', target_allocation: '0.4', position: 0 },
      { id: 'b', symbol: 'NVDA', proposed_amount: '6000', target_allocation: '0.6', position: 1 }
    ]
  };
  assert.deepEqual(
    JSON.parse(JSON.stringify(simulation.allocationInputsFromPlannedAllocation(allocation))),
    { AAPL: '40.00', NVDA: '60.00' }
  );

  await portfoliosApi.create({ name: 'Plan', portfolio_type: 'PLANNED', plan_currency: 'USD' });
  await portfoliosApi.replacePlannedHoldings(portfolioId, result.holdings);
  await portfoliosApi.getPlannedAllocation(portfolioId);
  await portfoliosApi.getPlannedPreview(portfolioId);
  assert.deepEqual(calls[0].options.body, { name: 'Plan', portfolio_type: 'PLANNED', plan_currency: 'USD' });
  assert.deepEqual(
    JSON.parse(JSON.stringify(calls[1].options.body)),
    { holdings: JSON.parse(JSON.stringify(result.holdings)) }
  );
  assert.equal(calls[2].path, `/api/portfolios/${portfolioId}/planned-allocation`);
  assert.equal(calls[3].path, `/api/portfolios/${portfolioId}/planned-preview`);
});

test('mobile Watchlist uses the authenticated backend contract and backend metrics', async () => {
  const calls = [];
  const { watchlistApi } = load('src/api/watchlistApi.ts', {
    './apiClient': { apiRequest: async (requestPath, options = {}) => {
      calls.push({ path: requestPath, options });
      return requestPath === '/api/watchlist' && options.method === 'POST'
        ? { symbol: options.body.symbol }
        : { items: [] };
    } }
  });

  await watchlistApi.list();
  await watchlistApi.add('ETH-USD');
  await watchlistApi.remove('ETH-USD');

  assert.equal(calls[0].path, '/api/watchlist');
  assert.equal(calls[1].path, '/api/watchlist');
  assert.equal(calls[1].options.method, 'POST');
  assert.deepEqual(JSON.parse(JSON.stringify(calls[1].options.body)), { symbol: 'ETH-USD' });
  assert.equal(calls[2].path, '/api/watchlist/ETH-USD');
  assert.equal(calls[2].options.method, 'DELETE');
  assert.equal(calls[2].options.responseMode, 'none');

  class ApiError extends Error {
    constructor(options) {
      super(options.message ?? 'Request failed');
      Object.assign(this, options);
    }
  }
  const ui = load('src/watchlist/watchlistUi.ts', {
    '../api/apiClient': { ApiError }
  });
  assert.equal(ui.formatWatchlistPrice(null), '—');
  assert.equal(ui.formatWatchlistPercent(null), '—');
  assert.equal(ui.formatWatchlistPercent(-1.236), '-1.24%');
  assert.match(ui.watchlistErrorMessage(new ApiError({ status: 404 }), 'remove'), /no longer in/i);
  assert.match(ui.watchlistErrorMessage(new ApiError({ status: 409 }), 'add'), /already in/i);
  assert.doesNotMatch(ui.watchlistErrorMessage(new ApiError({ status: 500, message: 'database secret' }), 'remove'), /database|secret/i);
});

test('mobile Watchlist stays under More and has no mock or local-storage authority', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const screen = read('src/screens/watchlist/WatchlistScreen.tsx');
  const navigator = read('src/navigation/MainTabNavigator.tsx');
  const more = read('src/screens/settings/MoreScreen.tsx');

  assert.match(screen, /watchlistApi\.list/);
  assert.match(screen, /watchlistApi\.add/);
  assert.match(screen, /watchlistApi\.remove/);
  assert.match(screen, /supportedAssets\.filter/);
  assert.match(screen, /Loading your Watchlist/);
  assert.match(screen, /Your Watchlist is empty/);
  assert.match(screen, /latest_price/);
  assert.match(screen, /latest_price_date/);
  assert.match(screen, /daily_change_percent/);
  assert.match(screen, /ytd_change_percent/);
  assert.match(navigator, /MoreStack\.Screen name="Watchlist"/);
  assert.match(more, /Follow supported assets/);
  assert.ok(!/Watchlist.*Unavailable|coming later/i.test(`${screen}\n${more}`));
  assert.ok(!/AsyncStorage|SecureStore|watchlistCatalog|watchlist\.mock/i.test(screen));
  assert.ok(!/fetch\(['"]https?:|OPENAI_API_KEY|ALPHA_VANTAGE|YAHOO/i.test(screen));
});

test('planned mobile presentation keeps estimates display-only and supports V3 history', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const create = read('src/screens/portfolios/CreatePortfolioScreen.tsx');
  const editor = read('src/components/portfolio/HoldingsEditor.tsx');
  const detail = read('src/screens/portfolios/PortfolioDetailScreen.tsx');
  const analysis = read('src/components/analytics/AnalysisResults.tsx');
  const metricDetails = read('src/report/reportMetricDetails.ts');
  const simulation = read('src/components/simulations/SimulationResults.tsx');
  const history = read('src/screens/simulations/SimulationResultScreen.tsx');

  assert.match(create, /A Planned Portfolio/);
  assert.match(create, /<HoldingDecimalInput/);
  assert.match(create, /Proposed Amount/);
  assert.match(editor, /<HoldingDecimalInput/);
  assert.match(editor, /replacePlannedHoldings/);
  assert.match(detail, /getPlannedPreview/);
  assert.match(detail, /Estimated shares are display-only/);
  assert.match(analysis, /SAVED PLANNED ALLOCATION/);
  assert.match(analysis, /Estimated shares are for display only/);
  assert.match(analysis, /MetricAmountSheet/);
  assert.match(analysis, /Tap for amount/);
  assert.match(analysis, /setSelectedMetric\('endingValue'\)/);
  assert.match(analysis, /Estimated Value at End of Period/);
  assert.match(analysis, /monetary\.estimated_ending_value/);
  assert.match(analysis, /Historical Portfolio Return/);
  assert.match(analysis, /analysis\.historical_value_context/);
  assert.match(analysis, /Same shares at historical prices/);
  assert.match(analysis, /RETURN_VIEW_RANGES\.map/);
  assert.match(analysis, /setReturnViewRange\(range\)/);
  assert.match(analysis, /accessibilityRole="tab"/);
  assert.match(analysis, /PortfolioReturnsChart points=\{visibleReturns\}/);
  assert.match(metricDetails, /cumulative_return_amount/);
  assert.match(metricDetails, /annualized_return_amount/);
  assert.match(metricDetails, /maximum_drawdown_amount/);
  assert.match(metricDetails, /estimated_ending_value/);
  assert.match(metricDetails, /not a prediction of future value/);
  assert.match(metricDetails, /fixed-shares-historical-value/);
  assert.match(metricDetails, /not your actual profit or loss/);
  assert.ok(!/reference_amount\s*\*/.test(`${analysis}\n${metricDetails}`));
  assert.match(simulation, /Saved planned allocation/);
  assert.match(history, /isSimulationHistoryV3/);
  assert.ok(!/proposedAmount\s*\/|proposed_amount\s*\//.test(`${create}\n${editor}\n${detail}`));
});

test('mobile historical scenarios compare the latest saved analysis with the event result', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const screen = read('src/screens/simulations/HistoricalScenarioScreen.tsx');
  const results = read('src/components/simulations/SimulationResults.tsx');
  const chart = read('src/components/charts/SimulationTrajectoryChart.tsx');

  assert.match(screen, /originalAllocation=\{originalAllocation\}/);
  assert.match(screen, /Number\(holding\.current_allocation\)/);
  assert.match(screen, /Number\(holding\.target_allocation\)/);
  assert.match(screen, /getPortfolioReportHistory\(selectedPortfolioSummary\)/);
  assert.match(screen, /getReport\(selectedPortfolioSummary\.id, newest\.id\)/);
  assert.match(screen, /screen: 'ReportDetail'/);
  assert.match(results, /Latest portfolio analysis vs historical scenario/);
  assert.match(results, /reference\.portfolio_metrics\.cumulative_return/);
  assert.match(results, /reference\.max_drawdown\.max_drawdown/);
  assert.match(results, /View latest analysis details/);
  assert.match(results, /Allocation used by this scenario run/);
  assert.match(results, /savedAnalysisTrajectory\(latestAnalysis\.analysis\)/);
  assert.match(chart, /accessibilityLabel="Choose trajectory lines"/);
  assert.match(chart, /accessibilityRole="radio"/);
  assert.match(chart, /selectedSeries === 'all' \? null/);
  assert.match(chart, />Date<\/SvgText>/);
  assert.doesNotMatch(results, /no-movement comparison line/);
  assert.doesNotMatch(results, /normalized_ending_value\s*[-+*/]/);
});

test('mobile reconstructs a normalized display path from saved backend return observations', () => {
  const simulation = load('src/simulation/simulationFormatting.ts');
  const analysis = {
    start_date: '2026-01-01',
    portfolio_returns: [
      { date: '2026-01-02', portfolio_return: 0.1 },
      { date: '2026-01-03', portfolio_return: -0.1 }
    ]
  };
  assert.deepEqual(JSON.parse(JSON.stringify(simulation.savedAnalysisTrajectory(analysis))), [
    { date: '2026-01-01', normalized_value: 1 },
    { date: '2026-01-02', normalized_value: 1.1 },
    { date: '2026-01-03', normalized_value: 0.9900000000000001 }
  ]);
  assert.deepEqual(analysis.portfolio_returns, [
    { date: '2026-01-02', portfolio_return: 0.1 },
    { date: '2026-01-03', portfolio_return: -0.1 }
  ]);
});

test('mobile destructive actions and portfolio naming use Aura-themed dialogs', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const confirmation = read('src/components/ui/ConfirmationDialog.tsx');
  const portfolio = read('src/screens/portfolios/PortfolioDetailScreen.tsx');
  const reports = read('src/screens/reports/ReportsScreen.tsx');
  const reportDetail = read('src/screens/reports/ReportDetailScreen.tsx');
  const watchlist = read('src/screens/watchlist/WatchlistScreen.tsx');
  const create = read('src/screens/portfolios/CreatePortfolioScreen.tsx');
  const editor = read('src/components/portfolio/HoldingsEditor.tsx');

  assert.match(confirmation, /<Modal/);
  assert.match(confirmation, /colors\.surface/);
  assert.match(confirmation, /variant="danger"/);
  assert.match(portfolio, /visible=\{nameAction !== null\}/);
  assert.match(portfolio, /<ConfirmationDialog/);
  assert.match(reports, /<ConfirmationDialog/);
  assert.match(reportDetail, /<ConfirmationDialog/);
  assert.match(watchlist, /<ConfirmationDialog/);
  assert.match(create, /<ConfirmationDialog/);
  assert.match(editor, /<ConfirmationDialog/);
  assert.doesNotMatch(`${portfolio}\n${reports}\n${reportDetail}\n${watchlist}`, /Alert\.alert/);
});

test('mobile asset picker shows full names while preserving symbol values', () => {
  const catalog = load('src/portfolio/supportedAssetSymbols.ts');
  const field = fs.readFileSync(
    path.join(root, 'src/components/portfolio/AssetSymbolField.tsx'),
    'utf8'
  );

  assert.equal(catalog.supportedAssets.length, 17);
  assert.deepEqual(
    JSON.parse(JSON.stringify(catalog.supportedAssetSymbols)),
    JSON.parse(JSON.stringify(catalog.supportedAssets.map(asset => asset.symbol)))
  );
  assert.ok(catalog.supportedAssets.every(asset => asset.symbol && asset.name));
  assert.match(field, /supportedAssets\.map/);
  assert.match(field, /asset\.name/);
  assert.match(field, /chooseSymbol\(asset\.symbol\)/);
});

test('Home report-backed return cards reuse saved monetary metric details', () => {
  const dashboard = fs.readFileSync(
    path.join(root, 'src/screens/dashboard/DashboardScreen.tsx'),
    'utf8'
  );
  const details = fs.readFileSync(
    path.join(root, 'src/report/reportMetricDetails.ts'),
    'utf8'
  );

  assert.match(dashboard, /reportMonetaryMetrics\(report\)/);
  assert.match(dashboard, /setSelectedMetric\('annualized'\)/);
  assert.match(dashboard, /setSelectedMetric\('drawdown'\)/);
  assert.match(dashboard, /<MetricAmountSheet/);
  assert.match(dashboard, /Tap for amount/);
  assert.match(details, /annualized_return_amount/);
  assert.match(details, /maximum_drawdown_amount/);
  assert.ok(!/reference_amount\s*\*/.test(`${dashboard}\n${details}`));
});

test('purchase-date helper remains reusable while current forms require only quantity', () => {
  const purchaseDates = load('src/portfolio/purchaseDate.ts');
  const now = new Date();
  const maximumDate = purchaseDates.maximumPurchaseDate(now);
  const today = now.toISOString().slice(0, 10);
  const yesterday = new Date(now.getTime() - 86_400_000).toISOString().slice(0, 10);

  assert.equal(purchaseDates.formatPurchaseDate(maximumDate), today);
  assert.equal(
    purchaseDates.formatPurchaseDate(
      purchaseDates.purchaseDatePickerValue(yesterday, maximumDate)
    ),
    yesterday
  );

  const create = fs.readFileSync(path.join(root, 'src/screens/portfolios/CreatePortfolioScreen.tsx'), 'utf8');
  const edit = fs.readFileSync(path.join(root, 'src/components/portfolio/HoldingsEditor.tsx'), 'utf8');
  assert.match(create, /Quantity Owned/);
  assert.match(edit, /Quantity Owned/);
  assert.doesNotMatch(create, /<PurchaseDateField|Invested Amount|Shares Owned/);
  assert.doesNotMatch(edit, /<PurchaseDateField|Invested Amount|Shares Owned/);
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

test('saved simulation opens Assistant with exact immutable simulation grounding', () => {
  const simulationDetail = fs.readFileSync(
    path.join(root, 'src/screens/simulations/SimulationResultScreen.tsx'),
    'utf8'
  );
  const assistant = fs.readFileSync(
    path.join(root, 'src/screens/assistant/AssistantScreen.tsx'),
    'utf8'
  );
  const navigationTypes = fs.readFileSync(
    path.join(root, 'src/navigation/navigationTypes.ts'),
    'utf8'
  );

  assert.match(simulationDetail, /Ask Aura about this saved simulation/);
  assert.match(simulationDetail, /navigate\('AI', \{ portfolioId, simulationId \}\)/);
  assert.match(navigationTypes, /AI: \{ portfolioId\?: string; simulationId\?: string \}/);
  assert.match(assistant, /requestedSimulationId/);
  assert.match(assistant, /simulation_id: selectedSimulationId/);
  assert.match(assistant, /IMMUTABLE SIMULATION/);
  assert.match(assistant, /exact immutable saved simulation/);
  assert.match(assistant, /Use live portfolio context/);
});

test('More report detail exposes an accessible back action to Reports', () => {
  const navigation = fs.readFileSync(
    path.join(root, 'src/navigation/MainTabNavigator.tsx'),
    'utf8'
  );
  const backButton = fs.readFileSync(
    path.join(root, 'src/components/ui/BackHeaderButton.tsx'),
    'utf8'
  );

  assert.match(navigation, /MoreStack\.Screen[\s\S]*name="ReportDetail"[\s\S]*BackHeaderButton/);
  assert.match(navigation, /label="Back to Reports"/);
  assert.match(navigation, /navigation\.navigate\('Reports'\)/);
  assert.match(backButton, /accessibilityRole="button"/);
  assert.match(backButton, /name="arrow-back"/);
});

test('mobile Reports back action returns directly to More', () => {
  const navigation = fs.readFileSync(
    path.join(root, 'src/navigation/MainTabNavigator.tsx'),
    'utf8'
  );

  assert.match(navigation, /MoreStack\.Screen[\s\S]*name="Reports"[\s\S]*headerBackVisible: false/);
  assert.match(navigation, /name="Reports"[\s\S]*label="Back to More"[\s\S]*navigation\.popTo\('More'\)/);
});

test('mobile Analytics exposes an explicit back action in both navigation stacks', () => {
  const navigation = fs.readFileSync(
    path.join(root, 'src/navigation/MainTabNavigator.tsx'),
    'utf8'
  );

  assert.match(navigation, /PortfolioStack\.Screen[\s\S]*name="PortfolioAnalysis"[\s\S]*label="Back from Analytics"/);
  assert.match(navigation, /navigation\.navigate\('Portfolios'\)/);
  assert.match(navigation, /MoreStack\.Screen[\s\S]*name="Analytics"[\s\S]*label="Back to More"/);
  assert.match(navigation, /onPress=\{\(\) => navigation\.navigate\('More'\)\}/);
  assert.match(navigation, /navigation\.canGoBack\(\) \? navigation\.goBack\(\)/);
});

test('Portfolio detail exposes a back action when opened directly from Home', () => {
  const navigation = fs.readFileSync(
    path.join(root, 'src/navigation/MainTabNavigator.tsx'),
    'utf8'
  );

  assert.match(navigation, /PortfolioStack\.Screen[\s\S]*name="PortfolioDetail"[\s\S]*label="Back from Portfolio"/);
  assert.match(navigation, /navigation\.canGoBack\(\)[\s\S]*navigation\.goBack\(\)[\s\S]*navigation\.getParent\(\)\?\.navigate\('Home'\)/);
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
  const holdings = [{ symbol: 'AAPL', shares: '5' }];

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
  assert.match(source, /Quantity Owned/);
  assert.doesNotMatch(source, /Invested Amount|Shares Owned|<PurchaseDateField/);
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
  assert.match(editor, /Quantity Owned/);
  assert.doesNotMatch(editor, /Invested Amount|Shares Owned|<PurchaseDateField/);
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
  assert.match(analysis, /SAVED PORTFOLIO VALUATION/);
  assert.match(reportDetail, /Later[\s\S]*portfolio or market changes do not alter them/);
  assert.match(allocation, /allocationInputsFromValuation/);
  assert.match(combined, /allocationInputsFromValuation/);
  assert.match(allocation, /<AllocationEditor/);
  assert.match(combined, /<AllocationEditor/);
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
  const request = {
    portfolio_id: portfolioId,
    message: 'Why is this risky?',
    history: [
      { role: 'user', content: 'What is my portfolio?' },
      { role: 'assistant', content: 'Your portfolio contains saved holdings.' }
    ]
  };
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
  assert.match(agentErrorMessage(new ApiError({ kind: 'network' })), /check your connection/i);
  assert.match(agentErrorMessage(new ApiError({ kind: 'configuration' })), /not configured/i);
  assert.match(agentErrorMessage(new ApiError({ kind: 'malformed-response' })), /unexpected AI response/i);
});

test('mobile Assistant has no direct provider access or synthetic conversation authority', () => {
  const api = fs.readFileSync(path.join(root, 'src/api/agentApi.ts'), 'utf8');
  const screen = fs.readFileSync(path.join(root, 'src/screens/assistant/AssistantScreen.tsx'), 'utf8');
  const answerContent = fs.readFileSync(path.join(root, 'src/components/assistant/AnswerContent.tsx'), 'utf8');
  const answerFormatting = load('src/agent/answerFormatting.ts');

  assert.match(api, /apiRequest/);
  assert.match(api, /\/api\/agent\/explain/);
  assert.match(screen, /usePortfolios/);
  assert.match(screen, /AbortController/);
  assert.match(screen, /newest saved report/);
  assert.match(screen, /messages\.slice\(-8\)/);
  assert.match(screen, /history/);
  assert.match(screen, /Start a conversation/);
  assert.match(screen, /FOLLOW-UP IDEAS/);
  assert.match(screen, /item\.id === latestAssistantMessageId && !sending/);
  assert.match(screen, /style=\{styles\.assistantMessageColumn\}/);
  assert.doesNotMatch(screen, /followUpsExpanded|See more|See less/);
  assert.match(screen, /accessibilityLabel="Hide message composer"/);
  assert.match(screen, /accessibilityLabel="Show message composer"/);
  assert.match(screen, /name="chevron-down"/);
  assert.match(screen, /name="chevron-up"/);
  assert.match(screen, /Grounding details/);
  assert.match(screen, /title="New chat"/);
  assert.match(screen, /style=\{styles\.userBubble\}/);
  assert.match(screen, /style=\{styles\.assistantBubble\}/);
  assert.match(screen, /<Card style=\{styles\.composerCard\}>/);
  assert.doesNotMatch(screen, /<View style=\{styles\.composerCard\}>/);
  assert.match(screen, /footer=\{composer\}/);
  assert.match(screen, /style=\{\[styles\.composerDock, composerHidden && styles\.composerDockHidden\]\}/);
  const composerDockStyle = screen.match(/composerDock:\s*\{([\s\S]*?)\r?\n\s*\},\r?\n\s*composerDockHidden:/)?.[1] ?? '';
  assert.doesNotMatch(composerDockStyle, /backgroundColor|borderTop/);
  assert.match(composerDockStyle, /position: 'absolute'/);
  assert.match(screen, /paddingBottom: composerHeight \+ spacing\.lg/);
  assert.match(screen, /setComposerHeight\(nativeEvent\.layout\.height\)/);
  assert.doesNotMatch(screen, /shadowOpacity: 0\.24|elevation: 10/);
  assert.match(screen, /<AnswerContent answer=\{item\.content\}/);
  assert.match(answerContent, /formatAgentAnswer/);
  const formatted = answerFormatting.formatAgentAnswer(
    '## Main risk\n\nYour **largest holding** matters.\n\n- Concentration\n2. Drawdown'
  );
  assert.deepEqual(JSON.parse(JSON.stringify(formatted)), [
    { type: 'heading', parts: [{ text: 'Main risk', bold: false }] },
    {
      type: 'paragraph',
      parts: [
        { text: 'Your ', bold: false },
        { text: 'largest holding', bold: true },
        { text: ' matters.', bold: false }
      ]
    },
    {
      type: 'bullets',
      items: [
        [{ text: 'Concentration', bold: false }],
        [{ text: 'Drawdown', bold: false }]
      ]
    }
  ]);
  assert.ok(!/OPENAI_API_KEY|GROQ_API_KEY|api\.openai|api\.groq/i.test(`${api}\n${screen}`));
  assert.ok(!/AsyncStorage|SecureStore|conversationHistory|chatHistory/.test(screen));
});

test('mobile current-value failures explain the data refresh and retry valuation', () => {
  const dashboard = fs.readFileSync(path.join(root, 'src/screens/dashboard/DashboardScreen.tsx'), 'utf8');
  const detail = fs.readFileSync(path.join(root, 'src/screens/portfolios/PortfolioDetailScreen.tsx'), 'utf8');
  const errors = fs.readFileSync(path.join(root, 'src/portfolio/portfolioErrors.ts'), 'utf8');
  const reportErrors = fs.readFileSync(path.join(root, 'src/report/reportErrors.ts'), 'utf8');
  const errorState = fs.readFileSync(path.join(root, 'src/components/ui/ErrorState.tsx'), 'utf8');

  assert.match(dashboard, /retryTitle=\{holdingMode === 'real' \? 'Retry Current Value' : 'Retry allocation'\}/);
  assert.match(dashboard, /onRetry=\{dashboard\.retryDetails\}/);
  assert.doesNotMatch(dashboard, /Analyze Portfolio Again/);
  assert.match(dashboard, /compactAction=\{holdingMode === 'real'\}/);
  assert.match(detail, /retryTitle="Retry Current Value"/);
  assert.match(detail, /PORTFOLIO_MARKET_DATA_RECOVERY_MESSAGE/);
  assert.match(errors, /New analysis is unavailable until market data is refreshed/);
  assert.match(reportErrors, /Analysis will be available after the market data refresh completes/);
  assert.match(errorState, /compactAction: \{ flexGrow: 0, flexBasis: 'auto', alignSelf: 'flex-start' \}/);
});

test('mobile asset-risk detail is report-backed, navigable, and never recalculates risk', () => {
  const read = file => fs.readFileSync(path.join(root, file), 'utf8');
  const results = read('src/components/analytics/AnalysisResults.tsx');
  const reportDetail = read('src/screens/reports/ReportDetailScreen.tsx');
  const analysis = read('src/screens/analytics/PortfolioAnalysisScreen.tsx');
  const detail = read('src/screens/reports/AssetRiskDetailScreen.tsx');
  const navigator = read('src/navigation/MainTabNavigator.tsx');
  const metricDetails = read('src/report/reportMetricDetails.ts');
  const reportTypes = read('src/types/report.ts');
  const dashboard = read('src/screens/dashboard/DashboardScreen.tsx');

  assert.match(results, /onOpenAsset/);
  assert.match(results, /onPress=\{\(\) => onOpenAsset\?\.\(asset\.symbol\)\}/);
  assert.match(reportDetail, /navigation\.navigate\('AssetRiskDetail'/);
  assert.match(analysis, /navigation\.navigate\('AssetRiskDetail'/);
  assert.match(dashboard, /screen: 'AssetRiskDetail'/);
  assert.match(dashboard, /params: \{ portfolioId: report\.portfolio_id, reportId: report\.id, assetSymbol \}/);
  assert.match(dashboard, /onPress=\{\(\) => openAssetRisk\(driver\.symbol\)\}/);
  assert.match(dashboard, /Open \$\{driver\.symbol\} asset risk details/);
  assert.match(navigator, /name="AssetRiskDetail"/);
  assert.match(detail, /getReport\(portfolioId, reportId/);
  assert.match(detail, /navigation\.popTo\('ReportDetail'/);
  assert.match(detail, /focusAssetSection: true/);
  assert.doesNotMatch(detail, /Back to per-asset valuation and risk|backButtonText/);
  assert.match(reportDetail, /ref=\{scrollRef\}/);
  assert.match(reportDetail, /onAssetSectionLayout/);
  assert.match(results, /nativeID="per-asset-analysis"/);
  assert.match(detail, /asset\.risk_classification/);
  assert.match(detail, /report\.analysis\.asset_returns/);
  assert.match(detail, /filterReturnPoints\(series\?\.points \?\? \[\], range\)/);
  assert.match(reportTypes, /asset_monetary_metrics\?: PortfolioReportAssetMonetaryMetrics\[\]/);
  assert.match(detail, /assetReportMonetaryMetrics\(report, assetSymbol\)/);
  assert.match(detail, /setSelectedMetric\('cumulative'\)/);
  assert.match(detail, /setSelectedMetric\('annualized'\)/);
  assert.match(detail, /setSelectedMetric\('drawdown'\)/);
  assert.match(detail, /<MetricAmountSheet/);
  assert.match(metricDetails, /monetary\.cumulative_return_amount/);
  assert.match(metricDetails, /monetary\.annualized_return_amount/);
  assert.match(metricDetails, /monetary\.maximum_drawdown_amount/);
  assert.doesNotMatch(metricDetails, /reference_amount\s*\*/);
  assert.doesNotMatch(detail, /Math\.(sqrt|pow)|annualized_volatility\s*[*/+-]|max_drawdown\s*[*/+-]/);
});

test('mobile settings use the authenticated Backend Profile V1 contract', async () => {
  const calls = [];
  const { authApi } = load('src/api/authApi.ts', {
    './apiClient': {
      apiRequest: async (requestPath, options = {}) => {
        calls.push({ path: requestPath, options });
        return requestPath.endsWith('/password') ? undefined : { id: 'user' };
      }
    }
  });
  await authApi.updateProfile({ display_name: 'Aura User' });
  await authApi.changePassword({
    current_password: 'current-pass',
    new_password: 'different-pass'
  });
  assert.equal(calls[0].path, '/api/auth/me');
  assert.equal(calls[0].options.method, 'PATCH');
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0].options.body)), { display_name: 'Aura User' });
  assert.equal(calls[1].path, '/api/auth/me/password');
  assert.equal(calls[1].options.method, 'PUT');
  assert.equal(calls[1].options.responseMode, 'none');

  const settings = fs.readFileSync(path.join(root, 'src/screens/settings/SettingsScreen.tsx'), 'utf8');
  const context = fs.readFileSync(path.join(root, 'src/auth/AuthProvider.tsx'), 'utf8');
  const types = fs.readFileSync(path.join(root, 'src/types/auth.ts'), 'utf8');
  assert.match(settings, /authApi\.updateProfile\(request\)/);
  assert.match(settings, /authApi\.changePassword/);
  assert.match(settings, /request\.current_password = profileDraft\.currentPassword/);
  assert.match(settings, /emailChanged \?/);
  assert.match(settings, /setCurrentUser\(updatedUser\)/);
  assert.match(settings, /UTC\+07:00 Bangkok/);
  assert.doesNotMatch(settings, /Yangon|UTC\+06:30/);
  assert.doesNotMatch(settings, /setDisplayName|stored only on this device/);
  assert.match(context, /setCurrentUser: setUser/);
  assert.match(types, /preferred_language: PreferredLanguage/);
  assert.match(types, /timezone: ProfileTimezone/);
});

test('mobile account identity prefers the saved name and safely falls back to email', () => {
  const identity = load('src/auth/accountIdentity.ts');
  const unnamed = { email: 'sherlockthiha2003@gmail.com', display_name: null };
  const named = { email: 'sherlockthiha2003@gmail.com', display_name: 'Sherlock Thiha' };
  assert.equal(identity.accountDisplayName(unnamed), 'sherlockthiha2003@gmail.com');
  assert.equal(identity.accountDisplayName(named), 'Sherlock Thiha');
  assert.equal(identity.accountInitials(unnamed), 'SH');
  assert.equal(identity.accountInitials(named), 'ST');

  const dashboard = fs.readFileSync(path.join(root, 'src/screens/dashboard/DashboardScreen.tsx'), 'utf8');
  const settings = fs.readFileSync(path.join(root, 'src/screens/settings/SettingsScreen.tsx'), 'utf8');
  const preferences = fs.readFileSync(path.join(root, 'src/preferences/PreferencesProvider.tsx'), 'utf8');
  assert.match(dashboard, /const displayName = accountDisplayName\(user\)/);
  assert.match(dashboard, /title=\{`Welcome back, \$\{displayName\}`\}/);
  assert.doesNotMatch(dashboard, /usePreferences|\.split\(' '\)\[0\]/);
  assert.match(settings, /const resolvedName = accountDisplayName\(user\)/);
  assert.match(settings, /numberOfLines=\{user\?\.display_name \? 1 : 2\}/);
  assert.match(settings, /\{user\?\.display_name \? \(/);
  assert.doesNotMatch(preferences, /displayName|setDisplayName/);
});
