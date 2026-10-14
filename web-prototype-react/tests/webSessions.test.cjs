const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const access = value => {
  const account = value.startsWith('account-') ? value.slice(-1) : 'user';
  return 'header.' + Buffer.from(JSON.stringify({ sub: account, sid: 'session-' + account, nonce: value })).toString('base64url') + '.signature';
};
const tick = () => new Promise(resolve => setImmediate(resolve));
const reply = (status, body) => new Response(body === undefined ? null : JSON.stringify(body), { status });
function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

function harness(fetch, extra = {}) {
  const modules = new Map(), storage = new Map(), slots = [], effects = [];
  let cursor = 0, failRemoval = false;
  const react = {
    createContext: () => ({ Provider: 'Provider' }),
    createElement: (_type, props) => props.value,
    useState(initial) {
      const i = cursor++;
      if (!(i in slots)) slots[i] = initial;
      return [slots[i], value => { slots[i] = typeof value === 'function' ? value(slots[i]) : value; }];
    },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useCallback: fn => fn,
    useMemo: fn => fn(),
    useEffect: fn => effects.push(fn),
  };
  function load(file) {
    if (modules.has(file)) return modules.get(file).exports;
    const module = { exports: {} };
    modules.set(file, module);
    const code = ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React },
    }).outputText;
    vm.runInNewContext(code, {
      module, exports: module.exports, URL, Headers, Promise, atob, React: react, fetch,
      window: { sessionStorage: {
        getItem: key => storage.get(key) ?? null,
        setItem: (key, value) => storage.set(key, value),
        removeItem: key => { if (failRemoval) throw Error('storage unavailable'); storage.delete(key); },
      } },
      require(name) {
        if (name === 'react') return react;
        if (name.endsWith('/config/environment')) return { environment: { apiBaseUrl: 'https://api.aura.example' } };
        const base = path.posix.normalize(path.posix.join(path.posix.dirname(file), name));
        return load(fs.existsSync(path.join(root, base + '.ts')) ? base + '.ts' : base + '.tsx');
      },
      ...extra,
    }, { filename: file });
    return module.exports;
  }
  const api = load('src/api/apiClient.ts'), auth = load('src/api/authApi.ts');
  let provider;
  return {
    api, auth, storage, load,
    failRemoval: () => { failRemoval = true; },
    render() {
      provider ??= load('src/auth/AuthContext.tsx').AuthProvider;
      cursor = 0; effects.length = 0;
      return provider({});
    },
    configure() { effects[0](); },
    startup() { effects.forEach(fn => fn()); },
  };
}

test('web auth uses credentialed cookie endpoints without exposing refresh secrets in bodies', async () => {
  const calls = [];
  const h = harness(async (url, options) => {
    calls.push({ url, options });
    return url.endsWith('/logout') ? reply(204) : reply(200, { access_token: 'access', token_type: 'bearer' });
  });
  await h.auth.loginUser({ email: 'web@example.com', password: 'test-password' });
  await h.auth.refreshWebSession();
  await h.auth.logoutWebSession();
  assert.deepEqual(calls.map(call => new URL(call.url).pathname), ['/api/auth/web/login', '/api/auth/web/refresh', '/api/auth/web/logout']);
  for (const { options } of calls) {
    assert.equal(options.credentials, 'include');
    assert.equal(options.headers.get('X-Aura-Web-Session'), '1');
    assert.equal(options.headers.has('Authorization'), false);
    assert.doesNotMatch(options.body ?? '', /refresh_token/);
  }
});

test('an expired bearer request renews and retries once preserving its body', async () => {
  const calls = [], rejected = [];
  const h = harness(async (url, options) => {
    calls.push({ url, options });
    return options.headers.get('Authorization') === 'Bearer ' + access('old') ? reply(401, { detail: 'Expired' }) : reply(200, { saved: true });
  });
  let refreshes = 0;
  h.api.configureApiAuthentication({ getAccessToken: () => access('old'), onUnauthorized: token => rejected.push(token),
    refreshAccessToken: async () => { refreshes++; return access('new'); } });
  const result = await h.api.apiRequest('/api/portfolios', { method: 'POST', body: { name: 'Portfolio' } });
  assert.equal(result.saved, true); assert.equal(refreshes, 1); assert.equal(calls.length, 2);
  assert.equal(calls[0].options.body, calls[1].options.body);
  assert.equal(calls[1].options.headers.get('Authorization'), 'Bearer ' + access('new'));
  assert.deepEqual(rejected, []);
});

test('a second unauthorized response ends renewal without a retry loop', async () => {
  let requests = 0, renewals = 0; const rejected = [];
  const h = harness(async () => { requests++; return reply(401, { detail: 'Invalid' }); });
  h.api.configureApiAuthentication({ getAccessToken: () => access('old'), onUnauthorized: token => rejected.push(token),
    refreshAccessToken: async () => { renewals++; return access('new'); } });
  await assert.rejects(() => h.api.apiRequest('/api/auth/me'), error => error.status === 401);
  assert.equal(requests, 2); assert.equal(renewals, 1); assert.deepEqual(rejected, [access('new')]);
});

test('refresh connection failures retain authentication and public requests never renew', async () => {
  const h = harness(async () => reply(401, { detail: 'Invalid' }));
  const rejected = []; let renewals = 0;
  h.api.configureApiAuthentication({ getAccessToken: () => access('old'), onUnauthorized: token => rejected.push(token),
    refreshAccessToken: async () => { renewals++; throw new h.api.ApiError({ kind: 'network', message: 'Offline' }); } });
  await assert.rejects(() => h.api.apiRequest('/api/auth/me'), error => error.kind === 'network');
  await assert.rejects(() => h.api.apiRequest('/api/auth/register', { token: null }), error => error.status === 401);
  assert.equal(renewals, 1); assert.deepEqual(rejected, []);
});

test('an expired refresh session invalidates the rejected access token', async () => {
  const h = harness(async () => reply(401, { detail: 'Invalid' })), rejected = [];
  h.api.configureApiAuthentication({ getAccessToken: () => access('old'), onUnauthorized: token => rejected.push(token),
    refreshAccessToken: async () => { throw new h.api.ApiError({ kind: 'http', status: 401, message: 'Expired' }); } });
  await assert.rejects(() => h.api.apiRequest('/api/auth/me'), error => error.status === 401);
  assert.deepEqual(rejected, [access('old')]);
});

test('aborted requests do not replay after renewal', async () => {
  let requests = 0; const controller = new AbortController();
  const h = harness(async () => { requests++; controller.abort(); return reply(401); });
  h.api.configureApiAuthentication({ getAccessToken: () => access('old'), onUnauthorized: () => {}, refreshAccessToken: async () => access('new') });
  await assert.rejects(() => h.api.apiRequest('/api/auth/me', { signal: controller.signal }));
  assert.equal(requests, 1);
});

test('startup restores a session after the tab access-token storage was cleared', async () => {
  const calls = [];
  const h = harness(async (url, options) => {
    calls.push({ url, options });
    return url.endsWith('/refresh') ? reply(200, { access_token: access('restored') }) : reply(200, { id: 'user', email: 'web@example.com' });
  });
  h.render(); h.startup(); await tick(); await tick();
  const state = h.render();
  assert.equal(state.status, 'authenticated'); assert.equal(state.user.id, 'user');
  assert.equal(h.storage.get('aura.auth.accessToken'), access('restored'));
  assert.equal(calls[1].options.headers.get('Authorization'), 'Bearer ' + access('restored'));
});

test('startup treats a missing or expired refresh cookie as signed out', async () => {
  const h = harness(async () => reply(401, { detail: 'Expired' }));
  h.render(); h.startup(); await tick(); await tick();
  assert.equal(h.render().status, 'unauthenticated'); assert.equal(h.storage.size, 0);
});

test('a network failure during restoration is retryable without clearing the session', async () => {
  let offline = true;
  const h = harness(async url => {
    if (offline) throw Error('offline');
    return url.endsWith('/refresh') ? reply(200, { access_token: access('renewed') }) : reply(200, { id: 'user' });
  });
  h.storage.set('aura.auth.accessToken', access('old')); h.render(); h.startup(); await tick(); await tick();
  assert.equal(h.render().status, 'error'); assert.equal(h.storage.get('aura.auth.accessToken'), access('old'));
  offline = false; await h.render().retrySessionRestore();
  assert.equal(h.render().status, 'authenticated');
});

test('simultaneous expired API calls share one provider renewal', async () => {
  const renewal = deferred(); let refreshes = 0;
  const h = harness(async (url, options) => {
    if (url.endsWith('/login')) return reply(200, { access_token: access('old') });
    if (url.endsWith('/refresh')) { refreshes++; return renewal.promise; }
    if (url.endsWith('/auth/me')) return reply(200, { id: 'user' });
    return options.headers.get('Authorization') === 'Bearer ' + access('old') ? reply(401) : reply(200, { ok: true });
  });
  const state = h.render(); h.configure(); await state.login({ email: 'web@example.com', password: 'test-password' });
  const first = h.api.apiRequest('/api/portfolios'), second = h.api.apiRequest('/api/watchlist');
  await tick(); assert.equal(refreshes, 1);
  renewal.resolve(reply(200, { access_token: access('new') }));
  assert.equal((await first).ok, true); assert.equal((await second).ok, true);
  assert.equal(h.storage.get('aura.auth.accessToken'), access('new')); assert.equal(h.render().status, 'authenticated');
});

test('a late restoration response cannot restore a session after sign out', async () => {
  const renewal = deferred(); let profileRequests = 0;
  const h = harness(async url => {
    if (url.endsWith('/refresh')) return renewal.promise;
    if (url.endsWith('/logout')) return reply(204);
    profileRequests++; return reply(200, { id: 'user' });
  });
  h.storage.set('aura.auth.accessToken', access('old'));
  const state = h.render(); h.configure(); const restoration = state.retrySessionRestore();
  await tick(); const logout = state.logout(); renewal.resolve(reply(200, { access_token: access('late') }));
  await Promise.all([restoration, logout]);
  assert.equal(h.render().status, 'unauthenticated'); assert.equal(h.storage.size, 0); assert.equal(profileRequests, 0);
});

test('an old account request cannot renew or invalidate a newer sign-in', async () => {
  const oldRequest = deferred(); let loginCount = 0, refreshes = 0;
  const h = harness(async url => {
    if (url.endsWith('/login')) return reply(200, { access_token: ++loginCount === 1 ? access('account-a') : access('account-b') });
    if (url.endsWith('/portfolios')) return oldRequest.promise;
    if (url.endsWith('/refresh')) { refreshes++; return reply(401); }
    return reply(200, { id: loginCount === 1 ? 'a' : 'b' });
  });
  const state = h.render(); h.configure(); await state.login({});
  const old = h.api.apiRequest('/api/portfolios');
  await state.login({}); oldRequest.resolve(reply(401));
  await assert.rejects(() => old, error => error.status === 401);
  assert.equal(refreshes, 0); assert.equal(h.storage.get('aura.auth.accessToken'), access('account-b'));
  assert.equal(h.render().user.id, 'b');
});

test('failed server logout remains visible and does not pretend the cookie was revoked', async () => {
  const h = harness(async url => {
    if (url.endsWith('/logout')) throw Error('offline');
    return url.endsWith('/login') ? reply(200, { access_token: access('old') }) : reply(200, { id: 'user' });
  });
  const state = h.render(); h.configure(); await state.login({});
  await assert.rejects(() => state.logout(), error => error.kind === 'network');
  assert.equal(h.render().status, 'authenticated'); assert.equal(h.storage.get('aura.auth.accessToken'), access('old'));
});

test('a shared cookie for another tab sign-in cannot silently replace the current account', async () => {
  const calls = [];
  const h = harness(async url => {
    calls.push(url);
    if (url.endsWith('/login')) return reply(200, { access_token: access('account-a') });
    if (url.endsWith('/refresh')) return reply(200, { access_token: access('account-b') });
    if (url.endsWith('/auth/me')) return reply(200, { id: 'a' });
    return reply(401);
  });
  const state = h.render(); h.configure(); await state.login({});
  await assert.rejects(() => h.api.apiRequest('/api/portfolios'), error => error.status === 401);
  assert.equal(h.render().status, 'unauthenticated'); assert.equal(h.render().user, null);
  assert.equal(h.storage.size, 0);
  assert.equal(calls.filter(url => url.endsWith('/portfolios')).length, 1);
  assert.equal(calls.some(url => url.endsWith('/logout')), false, 'the other tab session remains valid');
});

test('successful server logout clears authenticated UI even if storage removal fails', async () => {
  const h = harness(async url => url.endsWith('/logout') ? reply(204) : url.endsWith('/login')
    ? reply(200, { access_token: access('old') }) : reply(200, { id: 'user' }));
  const state = h.render(); h.configure(); await state.login({}); h.failRemoval();
  await assert.rejects(() => state.logout(), /storage unavailable/);
  assert.equal(h.render().status, 'unauthenticated'); assert.equal(h.render().user, null);
});

test('logout identifies the local session before clearing a shared browser cookie', async () => {
  let logoutHeaders;
  const h = harness(async (url, options) => {
    if (url.endsWith('/logout')) { logoutHeaders = options.headers; return reply(204); }
    return url.endsWith('/login') ? reply(200, { access_token: access('account-a') }) : reply(200, { id: 'a' });
  });
  const state = h.render(); h.configure(); await state.login({}); await state.logout();
  assert.equal(logoutHeaders.get('X-Aura-Web-Session-Id'), 'session-a');
  assert.equal(h.render().status, 'unauthenticated');
});

test('an older API call sharing a restoration cannot retry under a different session identity', async () => {
  const renewal = deferred(); let portfolioCalls = 0;
  const h = harness(async url => {
    if (url.endsWith('/refresh')) return renewal.promise;
    if (url.endsWith('/portfolios')) { portfolioCalls++; return reply(401); }
    return reply(200, { id: 'b' });
  });
  h.storage.set('aura.auth.accessToken', access('account-a'));
  const state = h.render(); h.configure(); const restoration = state.retrySessionRestore();
  const request = h.api.apiRequest('/api/portfolios'); await tick();
  renewal.resolve(reply(200, { access_token: access('account-b') }));
  await assert.rejects(() => request, error => error.status === 401); await restoration;
  assert.equal(portfolioCalls, 1); assert.equal(h.render().user.id, 'b');
});

test('password changes and account deletion clear local authentication after successful 204', async () => {
  for (const operation of ['password', 'delete']) {
    const h = harness(async (url, options) => {
      if (options.method === 'PUT' || options.method === 'DELETE') return reply(204);
      return url.endsWith('/login') ? reply(200, { access_token: access('old') }) : reply(200, { id: 'user' });
    });
    const state = h.render(); h.configure(); await state.login({});
    if (operation === 'password') await h.auth.changeCurrentUserPassword({ current_password: 'old-password', new_password: 'new-password' });
    else await h.auth.deleteCurrentUserAccount({ current_password: 'old-password' });
    assert.equal(h.render().status, 'unauthenticated'); assert.equal(h.storage.size, 0);
  }
});

test('cookie operations serialize across tabs through Web Locks and release after failures', async () => {
  const first = deferred(), calls = []; let queue = Promise.resolve();
  const navigator = { locks: { request(name, operation) {
    assert.equal(name, 'aura.web-session');
    const result = queue.then(operation); queue = result.then(() => {}, () => {}); return result;
  } } };
  const a = harness(async url => { calls.push(['a', url]); return first.promise; }, { navigator });
  const b = harness(async url => { calls.push(['b', url]); return reply(204); }, { navigator });
  const exchange = a.auth.refreshWebSession(); await tick();
  const logout = b.auth.logoutWebSession(); await tick(); assert.equal(calls.length, 1);
  first.resolve(reply(500, { detail: 'Temporary failure' }));
  await assert.rejects(() => exchange, error => error.status === 500); await logout;
  assert.equal(calls.length, 2); assert.equal(calls[1][0], 'b');
});

test('a recent concurrent rotation retries once with the updated cookie', async () => {
  let calls = 0;
  const h = harness(async () => ++calls === 1 ? reply(409) : reply(200, { access_token: access('new') }));
  assert.equal((await h.auth.refreshWebSession()).access_token, access('new')); assert.equal(calls, 2);
  const repeated = harness(async () => reply(409));
  await assert.rejects(() => repeated.auth.refreshWebSession(), error => error.status === 409);
});
