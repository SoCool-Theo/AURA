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
      if (!(name in mocks) && name.endsWith('/privacy/PortfolioPrivacy')) return {
        usePortfolioPrivacy: () => ({ hideValues: false, ready: true, storageError: null, setHideValues: () => {} }),
        usePrivateValue: () => value => value, usePrivateText: () => value => value,
      };
      assert.ok(name in mocks, `Unmocked module ${name} in ${file}`);
      return mocks[name];
    }
  }, { filename: file });
  return module.exports;
}

test('mobile Settings sign out confirms, cancels safely, retries failures, and blocks duplicate taps', async () => {
  const harness = hookHarness();
  const navigations = [];
  const user = { email: 'user@example.com' };
  harness.react.createElement = (type, props, ...children) => ({ type, props: props ?? {}, children });
  let signOuts = 0, fail = true, pending;
  let hiddenValues = false;
  const { SettingsScreen } = load('src/screens/settings/SettingsScreen.tsx', {
    react: harness.react,
    'react-native': { Alert: { alert: () => assert.fail('Sign out must use the themed dialog') }, KeyboardAvoidingView: 'Avoid', Modal: 'Modal', Platform: { OS: 'android' }, Pressable: 'Pressable', ScrollView: 'Scroll', Switch: 'Switch', Text: 'Text', TextInput: 'Input', View: 'View', StyleSheet: { create: value => value } },
    'react-native-safe-area-context': { SafeAreaView: 'Safe' }, '@expo/vector-icons': { Ionicons: 'Icon' },
    '../../components/ui/Button': { Button: 'Button' },
    '../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
    './DeleteAccountSection': { DeleteAccountSection: 'DeleteAccount' },
    './AboutAuraDialog': { AboutAuraDialog: 'AboutDialog' },
    '../../components/ui/Card': { Card: 'Card' }, '../../components/ui/PageTitle': { PageTitle: 'Title' },
    '../../api/authApi': { authApi: {} }, '../../api/apiErrorPresentation': {}, '../../api/apiClient': { ApiError: Error },
    '../../auth/accountIdentity': { accountDisplayName: () => 'Aura User', accountInitials: () => 'AU' },
    '../../auth/useAuth': { useAuth: () => ({ user, setCurrentUser: () => {}, signOut: async () => {
      signOuts++; if (fail) throw Error('storage failed'); await pending.promise;
    } }) },
    '../../hooks/useAppData': { useAppData: () => ({ resetLocalData: () => assert.fail('Sign out must not reset data') }) },
    '../../preferences/usePreferences': { usePreferences: () => ({ themeMode: 'dark', setThemeMode: () => {}, resetPreferences: () => assert.fail('Sign out must not reset preferences') }) },
    '../../privacy/PortfolioPrivacy': { usePortfolioPrivacy: () => ({ hideValues: hiddenValues, ready: true, storageError: null, setHideValues: value => { hiddenValues = value; } }) },
    '../../theme/theme': { colors: {}, spacing: {} },
  });
  harness.mount(() => SettingsScreen({ navigation: { navigate: route => navigations.push(route) } })); await harness.settle();
  const nodes = () => {
    const all = [];
    function visit(node) { if (!node || typeof node !== 'object') return; all.push(node); node.children?.forEach(visit); }
    visit(harness.value); return all;
  };
  const button = () => nodes().find(node => node.type === 'Button' && ['Sign out', 'Please wait…'].includes(node.props.title));
  const dialog = () => nodes().find(node => node.type === 'Dialog');
  const about = () => nodes().find(node => node.type === 'AboutDialog');
  const help = nodes().find(node => node.type === 'Pressable' && node.props.accessibilityLabel === 'Help and support');
  assert.equal(help.props.accessibilityRole, 'button');
  assert.equal(help.children.at(-1).props.name, 'chevron-forward');
  help.props.onPress(); assert.deepEqual(navigations, ['HelpSupport']); assert.equal(signOuts, 0);
  assert.equal(about().props.visible, false);
  const aboutRow = nodes().find(node => node.type === 'Pressable' && node.props.accessibilityLabel === 'About Aura');
  assert.equal(aboutRow.props.accessibilityRole, 'button');
  assert.equal(aboutRow.children.at(-1).type, 'Icon');
  assert.equal(aboutRow.children.at(-1).props.name, 'chevron-forward');
  aboutRow.props.onPress();
  await harness.settle(); assert.equal(about().props.visible, true); assert.equal(signOuts, 0);
  about().props.onClose(); await harness.settle(); assert.equal(about().props.visible, false);
  const privacySwitch = nodes().find(node => node.type === 'Switch' && node.props.accessibilityLabel === 'Hide portfolio values');
  assert.equal(privacySwitch.props.disabled, false); assert.equal(privacySwitch.props.value, false);
  privacySwitch.props.onValueChange(true); assert.equal(hiddenValues, true); assert.equal(signOuts, 0);
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

test('mobile About Aura matches web content and uses themed modal/backdrop/close/Done dismissal', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const colors = { surface: '#101A2C', primary: '#31D6CF' };
  const { AboutAuraDialog } = load('src/screens/settings/AboutAuraDialog.tsx', {
    react, '@expo/vector-icons': { Ionicons: 'Icon' },
    'react-native': { Modal: 'Modal', Pressable: 'Pressable', ScrollView: 'Scroll', Text: 'Text', View: 'View', StyleSheet: { create: value => value, absoluteFill: {} } },
    '../../components/ui/Button': { Button: 'Button' }, '../../theme/theme': { colors, spacing: {} },
  });
  let closed = 0; const tree = AboutAuraDialog({ visible: true, onClose: () => { closed++; } });
  assert.equal(tree.props.visible, true); tree.props.onRequestClose();
  const nodes = [], text = [];
  function visit(node) {
    if (Array.isArray(node)) return node.forEach(visit);
    if (typeof node === 'string') { text.push(node); return; }
    if (!node || typeof node !== 'object') return; nodes.push(node); node.children?.forEach(visit);
  }
  visit(tree);
  assert.ok(nodes.some(node => node.props.accessibilityViewIsModal && node.props.style.backgroundColor === colors.surface));
  assert.ok(nodes.some(node => node.type === 'Scroll'));
  for (const control of nodes.filter(node => node.type === 'Pressable' || node.type === 'Button')) control.props.onPress();
  assert.equal(closed, 4);
  const web = fs.readFileSync(path.join(root, '../web-prototype-react/src/pages/settings/components/AboutAuraDialog.tsx'), 'utf8');
  for (const value of text) assert.ok(web.includes(value), `Web/mobile content differs: ${value}`);
  assert.ok(nodes.some(node => node.type === 'Icon' && node.props.name === 'close' && node.props.color === colors.primary));
  const source = fs.readFileSync(path.join(root, 'src/screens/settings/SettingsScreen.tsx'), 'utf8');
  assert.doesNotMatch(source, /Alert\.alert\(\s*'About Aura'/);
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
    ['MoreTab', 'More', 'Settings'],
    ['MoreTab', 'More', 'HelpSupport']
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
    unmount() { for (const slot of slots) slot?.cleanup?.(); },
    get value() { return value; }
  };
}
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

function mountMobilePrivacy(accountId, storage) {
  const harness = hookHarness();
  harness.react.createElement = (type, props, ...children) => ({ type, props: props ?? {}, children });
  harness.react.useContext = () => harness.value.props.value;
  const privacy = load('src/privacy/PortfolioPrivacy.tsx', {
    react: harness.react, '@react-native-async-storage/async-storage': storage,
    '../auth/useAuth': { useAuth: () => ({ user: accountId ? { id: accountId } : null }) },
  });
  const wrapper = privacy.PortfolioPrivacyProvider({ children: 'content' });
  harness.mount(() => accountId ? wrapper.type(wrapper.props) : wrapper);
  return { harness, privacy, get value() { return harness.value.props.value; }, key: wrapper.props.key };
}

test('mobile local privacy is account-isolated, remembered after login, and hides while preferences load', async () => {
  const saved = new Map(), writes = [];
  const storage = { getItem: async key => saved.get(key) ?? null, setItem: async (key, value) => { writes.push(key); saved.set(key, value); } };
  const first = mountMobilePrivacy('account-a', storage);
  assert.equal(first.value.hideValues, true); assert.equal(first.value.ready, false);
  first.value.setHideValues(false); assert.equal(writes.length, 0, 'toggle is disabled during restoration');
  await first.harness.settle(); assert.equal(first.value.hideValues, false);
  first.value.setHideValues(true); await first.harness.settle(); assert.equal(first.value.hideValues, true);
  assert.equal(first.privacy.usePrivateValue()('123.45'), '••••');
  assert.equal(first.privacy.usePrivateText()('฿12,345.67 and −$987.65; +12.34%'), '•••• and ••••; +12.34%');
  first.harness.unmount(); assert.equal(mountMobilePrivacy(null, storage).value.hideValues, false);
  assert.equal(writes.length, 1);
  const other = mountMobilePrivacy('account-b', storage); await other.harness.settle();
  assert.equal(other.value.hideValues, false); assert.notEqual(other.key, first.key);
  const restored = mountMobilePrivacy('account-a', storage); await restored.harness.settle();
  assert.equal(restored.value.hideValues, true);
  restored.value.setHideValues(false); await restored.harness.settle(); restored.harness.unmount();
  const off = mountMobilePrivacy('account-a', storage); await off.harness.settle(); assert.equal(off.value.hideValues, false);
  assert.equal(off.privacy.usePrivateValue()('123.45'), '123.45');
  const anotherDevice = mountMobilePrivacy('account-a', { getItem: async () => null });
  await anotherDevice.harness.settle(); assert.equal(anotherDevice.value.hideValues, false);
});

test('mobile privacy serializes rapid toggles, retries failures, and ignores stale account restoration', async () => {
  const saved = new Map(), calls = []; const pendingWrite = deferred(); let firstWrite = true, fail = false;
  const storage = { getItem: async key => saved.get(key) ?? null, setItem: async (key, value) => {
    calls.push(value); if (firstWrite) { firstWrite = false; await pendingWrite.promise; }
    if (fail) throw Error('blocked'); saved.set(key, value);
  } };
  const state = mountMobilePrivacy('account-a', storage); await state.harness.settle();
  state.value.setHideValues(true); state.value.setHideValues(false); await state.harness.settle();
  assert.deepEqual(calls, ['true']); assert.equal(state.value.hideValues, false);
  pendingWrite.resolve(); await state.harness.settle(); assert.deepEqual(calls, ['true', 'false']);
  assert.equal(saved.get(state.privacy.privacyStorageKey('account-a')), 'false');
  fail = true; state.value.setHideValues(true); await state.harness.settle();
  assert.equal(state.value.hideValues, true); assert.match(state.value.storageError, /could not be saved/);
  fail = false; state.value.setHideValues(true); await state.harness.settle(); assert.equal(state.value.storageError, null);
  const pendingRead = deferred();
  const stale = mountMobilePrivacy('account-a', { getItem: () => pendingRead.promise });
  stale.harness.unmount();
  const next = mountMobilePrivacy('account-b', storage); await next.harness.settle(); assert.equal(next.value.hideValues, false);
  pendingRead.resolve('true'); await stale.harness.settle(); assert.equal(stale.value.ready, false);
  assert.equal(next.value.hideValues, false);
  for (const raw of ['broken', '{}', '"true"']) {
    const bad = mountMobilePrivacy('account-a', { getItem: async () => raw }); await bad.harness.settle();
    assert.equal(bad.value.hideValues, true); assert.equal(bad.value.ready, true); assert.match(bad.value.storageError, /could not be loaded/);
  }
  const blocked = mountMobilePrivacy('account-a', { getItem: async () => { throw Error('blocked'); } });
  await blocked.harness.settle(); assert.equal(blocked.value.hideValues, true); assert.match(blocked.value.storageError, /could not be loaded/);
});

test('mobile real/planned asset rows mask personal amounts and shares while keeping allocations and data', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  let hidden = true;
  const { AssetRow } = load('src/components/portfolio/AssetRow.tsx', {
    react, 'react-native': { StyleSheet: { create: value => value }, Text: 'Text', View: 'View' },
    '../../privacy/PortfolioPrivacy': { usePrivateValue: () => value => hidden ? '••••' : value },
    '../../types/portfolio': load('src/types/portfolio.ts'),
    '../../portfolio/portfolioFormatting': load('src/portfolio/portfolioFormatting.ts'),
    '../../portfolio/portfolioValidation': { decimalWeightToPercent: value => value * 100 },
    '../../theme/theme': { colors: {}, spacing: {} },
  });
  const holding = { symbol: 'AAPL', shares: '123.45', invested_amount: '9876.54', invested_currency: 'USD', position: 0, weight: null };
  const valuation = { current_value: '24690.00', current_allocation: '1' };
  const original = JSON.stringify({ holding, valuation });
  let tree = JSON.stringify(AssetRow({ holding, valuation }));
  assert.match(tree, /••••/); assert.match(tree, /100.00%/); assert.doesNotMatch(tree, /123.45|9,876|24,690/);
  hidden = false; tree = JSON.stringify(AssetRow({ holding, valuation })); assert.match(tree, /123.45/); assert.match(tree, /24,690/);
  hidden = true; tree = JSON.stringify(AssetRow({ holding: { symbol: 'AAPL', proposed_amount: '54321.00', weight: null }, valuationCurrency: 'THB', plannedPreview: { estimate_status: 'AVAILABLE', estimated_shares: '77.77', target_allocation: '1' } }));
  assert.match(tree, /••••/); assert.doesNotMatch(tree, /54,321|77.77/); assert.match(tree, /100.00%/);
  assert.equal(JSON.stringify({ holding, valuation }), original);
});

test('mobile metric sheets and decimal inputs hide amounts without changing percentages or stored input data', async () => {
  const state = mountMobilePrivacy('account-a', { getItem: async () => 'true' }); await state.harness.settle();
  let hidden = true;
  const privacy = { usePrivateValue: state.privacy.usePrivateValue, usePrivateText: state.privacy.usePrivateText,
    usePortfolioPrivacy: () => ({ hideValues: hidden }) };
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
    useState: initial => [typeof initial === 'function' ? initial() : initial, () => {}],
    useRef: value => ({ current: value }), useEffect: () => {}, forwardRef: fn => fn,
  };
  const { MetricAmountSheet } = load('src/components/analytics/MetricAmountSheet.tsx', {
    react, '../../privacy/PortfolioPrivacy': privacy,
    'react-native': { Modal: 'Modal', Pressable: 'Pressable', Text: 'Text', View: 'View', StyleSheet: { create: value => value, absoluteFill: {} } },
    '@expo/vector-icons': { Ionicons: 'Icon' }, '../../theme/theme': { colors: {}, spacing: {} }, '../ui/Button': { Button: 'Button' },
  });
  const content = { title: 'Return', percentage: '+12.34%', amount: '−฿1,523.70', amountLabel: 'Change', reference: 'Based on $12,345.67.', explanation: 'Historical results.', tone: 'danger' };
  let tree = JSON.stringify(MetricAmountSheet({ content, onClose: () => {} }));
  assert.match(tree, /\+12.34%/); assert.match(tree, /••••/); assert.doesNotMatch(tree, /1,523|12,345/);
  content.percentage = '$54,321.00'; tree = JSON.stringify(MetricAmountSheet({ content, onClose: () => {} })); assert.doesNotMatch(tree, /54,321/);
  const { HoldingDecimalInput } = load('src/components/portfolio/HoldingDecimalInput.tsx', {
    react, '../../privacy/PortfolioPrivacy': privacy, '../ui/Input': { Input: 'Input' },
    'react-native': { Text: 'Text' }, '../../theme/theme': { colors: {} },
    '../../portfolio/portfolioFormatting': load('src/portfolio/portfolioFormatting.ts'),
  });
  let edits = 0;
  let input = HoldingDecimalInput({ label: 'Amount', value: '12345.67', onValueChange: () => { edits++; } }, null).children[0];
  assert.equal(input.props.value, ''); assert.equal(input.props.placeholder, '••••'); assert.equal(input.props.editable, false);
  assert.doesNotMatch(JSON.stringify(input), /12345/);
  input.props.onChangeText('222.22'); assert.equal(edits, 0);
  hidden = false; input = HoldingDecimalInput({ label: 'Amount', value: '12345.67', onValueChange: () => { edits++; } }, null).children[0];
  assert.equal(input.props.value, '12345.67'); input.props.onChangeText('222.22'); assert.equal(edits, 1);
});

test('mobile privacy covers result surfaces while preserving public prices, FX, and normalized charts', () => {
  const files = ['src/components/portfolio/AssetRow.tsx', 'src/screens/dashboard/DashboardScreen.tsx',
    'src/screens/portfolios/PortfolioDetailScreen.tsx', 'src/components/analytics/AnalysisResults.tsx',
    'src/screens/reports/AssetRiskDetailScreen.tsx', 'src/components/simulations/SimulationResults.tsx'];
  let masked = 0, publicPrices = 0;
  for (const file of files) {
    const source = fs.readFileSync(path.join(root, file), 'utf8'); assert.match(source, /usePrivateValue/);
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
  const chart = fs.readFileSync(path.join(root, 'src/components/charts/SimulationTrajectoryChart.tsx'), 'utf8');
  assert.match(chart, /normalized_value/); assert.doesNotMatch(chart, /formatPortfolioMoney/);
  const providers = fs.readFileSync(path.join(root, 'src/app/AppProviders.tsx'), 'utf8');
  assert.ok(providers.indexOf('<AuthProvider>') < providers.indexOf('<PortfolioPrivacyProvider>'));
  const settings = fs.readFileSync(path.join(root, 'src/screens/settings/SettingsScreen.tsx'), 'utf8');
  assert.match(settings, /<Switch accessibilityLabel="Hide portfolio values"/);
  assert.match(settings, /disabled=\{!privacy.ready \|\| pending \|\| accountDeleting\}/);
  assert.match(settings, /onValueChange=\{privacy.setHideValues\}/);
  const assistant = fs.readFileSync(path.join(root, 'src/screens/assistant/AssistantScreen.tsx'), 'utf8');
  assert.match(assistant, /if \(sendingRef.current \|\| hideValues\) return/);
  assert.ok(assistant.indexOf('if (hideValues) return') < assistant.indexOf('{messages.map'));
  assert.match(assistant, /AI chat hidden for privacy/);
});

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
  assert.equal(Object.keys(await api.loadLearnProgress('account-a')).length, 0);
  for (const invalid of ['null', '[]', 'invalid', '{"lesson":42}']) {
    raw = invalid; await assert.rejects(() => api.loadLearnProgress('account-a'));
  }
  raw = '{"lesson":true}'; assert.equal((await api.loadLearnProgress('account-a')).lesson, true);
  await api.saveLearnProgress('account-a', { lesson: true });
  assert.equal(new Set(reads).size, 1);
  assert.equal(writes[0][0], reads[0]);
  await api.clearLocalAuraData('account-a');
  assert.ok(removed.includes(reads[0]));
  assert.ok(!removed.some(key => /token|auth/i.test(key)));
  assert.ok(!removed.includes(api.learnProgressStorageKey('account-b')));
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
function localMobileNodes(tree) {
  if (Array.isArray(tree)) return tree.flatMap(localMobileNodes);
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...(tree.children ?? []).flatMap(localMobileNodes)];
}
function plain(value) { return JSON.parse(JSON.stringify(value)); }
function mountMobileProgress(accountId, storage) {
  const h = hookHarness();
  h.react.createElement = (type, props, ...children) => ({ type, props: props ?? {}, children });
  const api = load('src/storage/appStorage.ts', { '@react-native-async-storage/async-storage': storage });
  const { AppDataProvider } = load('src/storage/AppDataProvider.tsx', {
    react: h.react, './appStorage': api, '../auth/useAuth': { useAuth: () => ({ user: accountId ? { id: accountId } : null }) },
  });
  const wrapper = AppDataProvider({});
  h.mount(() => wrapper.type(wrapper.props));
  return { h, api, get value() { return h.value.props.value; } };
}

test('mobile Learn progress persists per account, supports undo and resets only current account/obsolete local keys', async () => {
  const saved = new Map([['auth-token', 'session'], ['report', 'saved-report'], ['aura_portfolio_privacy_v1:b', 'true']]);
  const storage = { getItem: async key => saved.get(key) ?? null, setItem: async (key, value) => saved.set(key, value), multiRemove: async keys => keys.forEach(key => saved.delete(key)) };
  const first = mountMobileProgress('a', storage);
  assert.equal(first.value.loading, true); await first.h.settle();
  await first.value.toggleLessonComplete('risk-score'); await first.h.settle();
  assert.equal(first.value.learnProgress['risk-score'], true);
  await first.value.toggleLessonComplete('risk-score'); await first.h.settle();
  assert.equal(first.value.learnProgress['risk-score'], false);
  await first.value.toggleLessonComplete('drawdown'); await first.h.settle(); first.h.unmount();
  const signedOut = mountMobileProgress(null, storage); await signedOut.h.settle();
  assert.deepEqual(plain(signedOut.value.learnProgress), {});
  const restored = mountMobileProgress('a', storage); await restored.h.settle();
  assert.equal(restored.value.learnProgress.drawdown, true);
  const other = mountMobileProgress('b', storage); await other.h.settle();
  assert.deepEqual(plain(other.value.learnProgress), {});
  await other.value.toggleLessonComplete('volatility'); await other.h.settle();
  await restored.value.resetLocalData(); await restored.h.settle();
  assert.deepEqual(plain(restored.value.learnProgress), {});
  const refreshed = mountMobileProgress('a', storage); await refreshed.h.settle();
  assert.deepEqual(plain(refreshed.value.learnProgress), {});
  assert.equal(JSON.parse(saved.get(first.api.learnProgressStorageKey('b'))).volatility, true);
  assert.equal(saved.get('auth-token'), 'session'); assert.equal(saved.get('report'), 'saved-report');
  assert.equal(saved.get('aura_portfolio_privacy_v1:b'), 'true');
});

test('mobile Learn saves only on success, rejects reset during writes, and ignores pre-reset reads', async () => {
  let failWrite = true, pendingWrite;
  const saved = new Map();
  const storage = {
    getItem: async key => saved.get(key) ?? null,
    setItem: async (key, value) => { if (failWrite) throw Error('quota'); if (pendingWrite) await pendingWrite.promise; saved.set(key, value); },
    multiRemove: async keys => keys.forEach(key => saved.delete(key)),
  };
  const state = mountMobileProgress('a', storage); await state.h.settle();
  await state.value.toggleLessonComplete('risk-score'); await state.h.settle();
  assert.equal(state.value.learnProgress['risk-score'], undefined); assert.match(state.value.localError, /Could not save/);
  failWrite = false; await state.value.retryLocalData(); await state.h.settle();
  pendingWrite = deferred();
  const save = state.value.toggleLessonComplete('risk-score');
  await state.value.toggleLessonComplete('risk-score');
  await assert.rejects(() => state.value.resetLocalData());
  pendingWrite.resolve(); await save; await state.h.settle();
  assert.equal(state.value.learnProgress['risk-score'], true);
  const pendingRead = deferred();
  const delayed = mountMobileProgress('a', { ...storage, getItem: () => pendingRead.promise });
  await delayed.value.resetLocalData(); await delayed.h.settle();
  pendingRead.resolve('{"drawdown":true}'); await delayed.h.settle();
  assert.deepEqual(plain(delayed.value.learnProgress), {}); assert.equal(delayed.value.loading, false);
});

test('mobile strict privacy reset queues after toggles, stays hidden on failure, and does not touch other accounts', async () => {
  const saved = new Map([['aura_portfolio_privacy_v1:a', 'true'], ['aura_portfolio_privacy_v1:b', 'true']]);
  let fail = true, pending;
  const state = mountMobilePrivacy('a', {
    getItem: async key => saved.get(key) ?? null,
    setItem: async (key, value) => { if (fail) throw Error('blocked'); if (pending) await pending.promise; saved.set(key, value); },
  });
  await state.harness.settle(); await assert.rejects(() => state.value.resetPrivacy()); await state.harness.settle();
  assert.equal(state.value.hideValues, true); assert.match(state.value.storageError, /could not be reset/);
  fail = false; pending = deferred(); state.value.setHideValues(true);
  const resetting = state.value.resetPrivacy(); await state.harness.settle();
  assert.equal(state.value.hideValues, true);
  pending.resolve(); await resetting; await state.harness.settle();
  assert.equal(state.value.hideValues, false); assert.equal(saved.get('aura_portfolio_privacy_v1:a'), 'false');
  assert.equal(saved.get('aura_portfolio_privacy_v1:b'), 'true');
});

test('mobile Reset uses themed confirmation, cancel/duplicate guards and partial failure retry without signing out', async () => {
  const h = hookHarness(); h.react.createElement = (type, props, ...children) => ({ type, props: props ?? {}, children });
  const user = { id: 'a', email: 'a@example.com' };
  let clears = 0, preferences = 0, privacy = 0, fail = true, pending;
  const { SettingsScreen } = load('src/screens/settings/SettingsScreen.tsx', {
    react: h.react,
    'react-native': { Alert: { alert: () => assert.fail('Reset must use Aura themed confirmation') }, KeyboardAvoidingView: 'Avoid', Modal: 'Modal', Platform: { OS: 'android' }, Pressable: 'Pressable', ScrollView: 'Scroll', Switch: 'Switch', Text: 'Text', TextInput: 'Input', View: 'View', StyleSheet: { create: value => value } },
    'react-native-safe-area-context': { SafeAreaView: 'Safe' }, '@expo/vector-icons': { Ionicons: 'Icon' },
    '../../components/ui/Button': { Button: 'Button' }, '../../components/ui/ConfirmationDialog': { ConfirmationDialog: 'Dialog' },
    './DeleteAccountSection': { DeleteAccountSection: 'Delete' }, './AboutAuraDialog': { AboutAuraDialog: 'About' },
    '../../components/ui/Card': { Card: 'Card' }, '../../components/ui/PageTitle': { PageTitle: 'Title' },
    '../../api/authApi': { authApi: {} }, '../../api/apiErrorPresentation': {}, '../../api/apiClient': { ApiError: Error },
    '../../auth/accountIdentity': { accountDisplayName: () => 'Aura User', accountInitials: () => 'AU' },
    '../../auth/useAuth': { useAuth: () => ({ user, signOut: () => assert.fail('Reset must not sign out') }) },
    '../../hooks/useAppData': { useAppData: () => ({ loading: false, localPending: false, resetLocalData: async () => { clears++; if (fail) throw Error('blocked'); await pending.promise; } }) },
    '../../preferences/usePreferences': { usePreferences: () => ({ themeMode: 'dark', ready: true, resetPreferences: async () => { preferences++; } }) },
    '../../privacy/PortfolioPrivacy': { usePortfolioPrivacy: () => ({ hideValues: true, ready: true, resetPrivacy: async () => { privacy++; } }) },
    '../../theme/theme': { colors: {}, spacing: {} },
  });
  h.mount(() => SettingsScreen()); await h.settle();
  const button = () => localMobileNodes(h.value).find(node => node.props.accessibilityLabel === 'Reset local data');
  const dialog = () => localMobileNodes(h.value).find(node => node.type === 'Dialog' && node.props.title === 'Reset local data?');
  button().props.onPress(); await h.settle(); assert.equal(clears, 0); assert.equal(dialog().props.visible, true);
  assert.equal(dialog().props.tone, 'danger'); assert.match(dialog().props.description, /turns Hide portfolio values off/);
  const staleConfirm = dialog().props.onConfirm;
  dialog().props.onCancel(); await h.settle(); staleConfirm(); await h.settle(); assert.equal(clears, 0);
  button().props.onPress(); await h.settle(); dialog().props.onConfirm(); await h.settle();
  assert.match(dialog().props.errorMessage, /Local reset incomplete/); assert.equal(privacy, 0); assert.equal(preferences, 0);
  fail = false; pending = deferred(); dialog().props.onConfirm(); dialog().props.onConfirm(); await h.settle();
  assert.equal(clears, 2); assert.equal(dialog().props.busy, true); assert.equal(button().props.disabled, true);
  dialog().props.onCancel(); await h.settle(); assert.equal(dialog().props.visible, true);
  pending.resolve(); await h.settle(); assert.equal(dialog().props.visible, false);
  assert.equal(preferences, 1); assert.equal(privacy, 1); assert.match(JSON.stringify(h.value), /Local data reset/);
});

test('mobile appearance reset waits for earlier writes and persists defaults last', async () => {
  const h = hookHarness(); let pending, saved, fail = false;
  const { PreferencesProvider } = load('src/preferences/PreferencesProvider.tsx', {
    react: h.react, 'react-native': { Appearance: { setColorScheme: () => {} } },
    '@react-native-async-storage/async-storage': { getItem: async () => null, setItem: async (_key, value) => { if (pending) await pending.promise; if (fail) throw Error('blocked'); saved = value; } },
  });
  h.mount(() => PreferencesProvider({})); await h.settle();
  pending = deferred(); h.value.setThemeMode('light');
  const reset = h.value.resetPreferences(); await h.settle();
  pending.resolve(); await reset; await h.settle();
  assert.equal(h.value.themeMode, 'dark'); assert.deepEqual(JSON.parse(saved), { themeMode: 'dark' });
  fail = true; await assert.rejects(() => h.value.resetPreferences());
});
test('mobile lesson opening does not auto-complete; explicit completion/undo updates actual progress counts', async () => {
  const saved = new Map();
  const state = mountMobileProgress('a', { getItem: async key => saved.get(key) ?? null, setItem: async (key, value) => saved.set(key, value), multiRemove: async () => {} });
  const lessons = load('src/mocks/learn.mock.ts');
  const h = hookHarness(); h.react.createElement = (type, props, ...children) => ({ type, props: props ?? {}, children });
  const common = {
    react: h.react, 'react-native': { Linking: { openURL: () => {} }, Pressable: 'Pressable', ScrollView: 'Scroll', View: 'View', Text: 'Text', StyleSheet: { create: value => value } },
    'react-native-safe-area-context': { SafeAreaView: 'Safe' }, '@expo/vector-icons': { Ionicons: 'Icon' },
    '../../components/ui/Button': { Button: 'Button' }, '../../components/ui/Card': { Card: 'Card' },
    '../../components/ui/Input': { Input: 'Input' }, '../../components/ui/PageTitle': { PageTitle: 'Title' },
    '../../components/ui/Tag': { Tag: 'Tag' }, '../../components/ui/EmptyState': { EmptyState: 'Empty' },
    '../../components/ui/KeyboardAwareScrollView': { KeyboardAwareScrollView: 'Scroll' },
    '../../mocks/learn.mock': lessons, '../../hooks/useAppData': { useAppData: () => state.value },
    '../../theme/theme': { colors: {}, spacing: {}, typography: {} },
  };
  const { LearnDetailScreen } = load('src/screens/learn/LearnDetailScreen.tsx', common);
  const { LearnScreen } = load('src/screens/learn/LearnScreen.tsx', common);
  const lesson = lessons.learnLessons[0];
  h.mount(() => LearnDetailScreen({ route: { params: { lessonId: lesson.id } } }));
  const complete = () => localMobileNodes(h.value).find(node => node.type === 'Button' && /progress|completed/.test(node.props.title));
  assert.equal(complete().props.disabled, true);
  await state.h.settle(); h.render();
  assert.equal(state.value.learnProgress[lesson.id], undefined, 'reading is not completion');
  await complete().props.onPress(); await state.h.settle(); h.render();
  assert.equal(complete().props.title, 'Mark as not completed');
  await complete().props.onPress(); await state.h.settle(); h.render();
  assert.equal(complete().props.title, 'Mark lesson completed');
  for (const item of lessons.learnLessons) { await state.value.toggleLessonComplete(item.id); await state.h.settle(); }
  await state.value.toggleLessonComplete('unknown-lesson'); await state.h.settle();
  h.mount(() => LearnScreen({ navigation: { navigate: () => {} } }));
  const bar = localMobileNodes(h.value).find(node => node.props.accessibilityRole === 'progressbar');
  assert.equal(bar.props.accessibilityValue.now, 9); assert.equal(bar.props.accessibilityValue.max, 9);
  const completedCards = localMobileNodes(h.value).filter(node => node.type === 'Pressable' && /, completed$/.test(node.props.accessibilityLabel));
  assert.equal(completedCards.length, 9);
});
test('mobile Help expands/collapses answers, filters body text, clears empty results and keeps local data untouched', async () => {
  const h = hookHarness(); h.react.createElement = (type, props, ...children) => ({ type, props: props ?? {}, children });
  const api = load('src/screens/settings/helpContent.ts');
  const original = JSON.stringify(api.helpSections);
  const { HelpSupportScreen } = load('src/screens/settings/HelpSupportScreen.tsx', {
    react: h.react, 'react-native': { Pressable: 'Pressable', StyleSheet: { create: value => value }, Text: 'Text', View: 'View' },
    'react-native-safe-area-context': { SafeAreaView: 'Safe' }, '@expo/vector-icons': { Ionicons: 'Icon' },
    '../../components/ui/Button': { Button: 'Button' }, '../../components/ui/Card': { Card: 'Card' },
    '../../components/ui/Input': { Input: 'Input' }, '../../components/ui/KeyboardAwareScrollView': { KeyboardAwareScrollView: 'Scroll' },
    '../../components/ui/PageTitle': { PageTitle: 'Title' }, '../../theme/theme': { colors: {}, spacing: {} }, './helpContent': api,
  });
  h.mount(() => HelpSupportScreen()); await h.settle();
  const nodes = () => localMobileNodes(h.value);
  const questions = () => nodes().filter(node => node.type === 'Pressable');
  assert.equal(questions().length, 20);
  assert.ok(questions().every(node => node.props.accessibilityState.expanded === false));
  const question = api.helpSections[0].articles[0];
  assert.doesNotMatch(JSON.stringify(h.value), /enter the shares you actually own/);
  questions()[0].props.onPress(); await h.settle();
  assert.equal(questions()[0].props.accessibilityState.expanded, true);
  assert.match(JSON.stringify(h.value), /enter the shares you actually own/);
  questions()[0].props.onPress(); await h.settle();
  assert.equal(questions()[0].props.accessibilityState.expanded, false);
  const search = async value => { nodes().find(node => node.type === 'Input').props.onChangeText(value); await h.settle(); };
  await search(' Sharpe ratio '); assert.equal(questions().length, 1);
  assert.equal(questions()[0].props.accessibilityLabel, 'How should I read the risk metrics?');
  await search('qzx-no-article'); assert.equal(questions().length, 0);
  assert.match(JSON.stringify(h.value), /No matching help articles/);
  nodes().find(node => node.type === 'Button' && node.props.title === 'Clear search').props.onPress(); await h.settle();
  assert.equal(questions().length, 20); assert.equal(questions()[0].props.accessibilityLabel, question.question);
  assert.equal(JSON.stringify(api.helpSections), original);
  const source = fs.readFileSync(path.join(root, 'src/screens/settings/HelpSupportScreen.tsx'), 'utf8');
  assert.doesNotMatch(source, /AsyncStorage|authApi|fetch\(|resetLocalData/);
  assert.match(source, /colors\.background/); assert.match(source, /colors\.primary/);
});

test('mobile Help registers in More stack and its themed header returns directly to Settings', () => {
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
  const more = localMobileNodes(MainTabNavigator()).find(node => node.props.name === 'MoreTab');
  const help = localMobileNodes(more.props.component()).find(node => node.props.name === 'HelpSupport');
  assert.equal(help.props.component, 'HelpSupportScreen');
  const popped = [];
  const options = help.props.options({ navigation: { popTo: route => popped.push(route) } });
  assert.equal(options.headerBackVisible, false);
  const back = options.headerLeft(); assert.equal(back.props.label, 'Back to Settings');
  assert.equal(back.props.color, '#F7FAFF'); back.props.onPress(); assert.deepEqual(popped, ['Settings']);
  assert.match(fs.readFileSync(path.join(root, 'src/navigation/navigationTypes.ts'), 'utf8'), /HelpSupport: undefined/);
});
test('mobile answer formatting preserves aligned Markdown tables, escaped pipes, missing values and surrounding text', () => {
  const { formatAgentAnswer } = load('src/agent/answerFormatting.ts');
  const blocks = formatAgentAnswer('Before.\r\n\r\n| Metric | Value |\r\n| :--- | ---: |\r\n| **Drawdown** | -18.50% |\r\n| A \\| B | N/A |\r\n| Empty | |\r\n\r\n- After.');
  assert.deepEqual(plain(blocks.map(block => block.type)), ['paragraph', 'table', 'bullets']);
  const table = blocks[1];
  assert.deepEqual(plain(table.alignments), ['left', 'right']);
  assert.equal(table.rows[0][0][0].bold, true); assert.equal(table.rows[0][1][0].text, '-18.50%');
  assert.equal(table.rows[1][0][0].text, 'A | B'); assert.equal(table.rows[1][1][0].text, 'N/A');
  assert.deepEqual(plain(table.rows[2][1]), []);
  assert.equal(formatAgentAnswer('|asda|asdf|')[0].type, 'paragraph');
  assert.ok(formatAgentAnswer('~~~\n| A | B |\n| --- | --- |\n~~~').every(block => block.type !== 'table'));
});

test('mobile AI answer tables use themed horizontal scrolling and accessible column labels without raw HTML', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }) };
  const { AnswerContent } = load('src/components/assistant/AnswerContent.tsx', {
    react, 'react-native': { StyleSheet: { create: value => value }, ScrollView: 'Scroll', Text: 'Text', View: 'View' },
    '../../agent/answerFormatting': load('src/agent/answerFormatting.ts'), '../../theme/theme': { colors: { primary: 'teal' }, spacing: {} },
  });
  const nodes = localMobileNodes(AnswerContent({ answer: '| Metric | Value |\n| --- | ---: |\n| **Return** | -2.50% |\n| Literal | <script>alert(1)</script> |' }));
  const scroll = nodes.find(node => node.type === 'Scroll');
  assert.equal(scroll.props.horizontal, true); assert.equal(scroll.props.accessibilityLabel, 'Aura answer table');
  assert.equal(nodes.filter(node => node.props.accessibilityRole === 'header').length, 2);
  assert.ok(nodes.some(node => node.props.accessibilityLabel === 'Value: -2.50%'));
  assert.ok(nodes.some(node => node.props.parts?.some(part => part.text === '<script>alert(1)</script>')));
  assert.ok(nodes.some(node => node.props.parts?.some(part => part.text === 'Return' && part.bold)));
  assert.ok(nodes.some(node => node.props.style?.textAlign === 'right'));
  assert.equal(nodes.filter(node => node.type === 'WebView').length, 0);
});
