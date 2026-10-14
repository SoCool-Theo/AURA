import assert from "node:assert/strict";
import test, { after } from "node:test";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const root = fileURLToPath(new URL("..", import.meta.url));
const vite = await createServer({ configFile: false, root, cacheDir: ".wrangler/admin-api-test-cache", appType: "custom", server: { middlewareMode: true, hmr: false, ws: false } });
after(() => vite.close());
const { createAdminApi, ADMIN_TOKEN_KEY, apiOrigin } = await vite.ssrLoadModule("/lib/adminApi.ts");
const contracts = await vite.ssrLoadModule("/lib/adminContracts.ts");

const portfolio = {
  id: "00000000-0000-4000-8000-000000000064", name: "Saved portfolio", portfolio_type: "CURRENT", plan_currency: null,
  created_at: "2026-10-14T00:00:00Z", updated_at: "2026-10-14T00:00:00Z",
  owner: { id: "00000000-0000-4000-8000-000000000002", email: null, display_name: null, account_type: "LEGACY", status: "ACTIVE" },
  holding_count: 1, saved_report_count: 8, saved_simulation_count: 3,
};
const portfolioDetails = { ...portfolio, source_plan_id: null, holdings: [{ id: "00000000-0000-4000-8000-0000000000c8", symbol: "AAPL", position: 0, weight: null, shares: "2.123456789012", invested_amount: null, invested_currency: null, purchase_date: null }] };

test("portfolio directory encodes server filters and strips private response fields", async () => {
  let called;
  const { api } = setup(async (url, init) => { called = [url, init]; return response({ items: [{ ...portfolio, result_snapshot: { private: true } }], total: 1, limit: 25, offset: 0 }); }, "token");
  const result = await api.portfolios({ q: "100%_\\", owner_id: portfolio.owner.id, portfolio_type: "CURRENT", limit: 25 });
  const query = new URL(called[0]);
  assert.equal(query.pathname, "/api/admin/portfolios"); assert.equal(query.searchParams.get("q"), "100%_\\");
  assert.equal(query.searchParams.get("owner_id"), portfolio.owner.id); assert.equal(called[1].method, "GET");
  assert.deepEqual(result.items[0], portfolio);
});
test("portfolio details keep exact decimal strings and reject mismatched identity or mode", async () => {
  const { api } = setup(async () => response(portfolioDetails), "token");
  assert.equal((await api.portfolio(portfolio.id)).holdings[0].shares, "2.123456789012");
  await assert.rejects(api.portfolio(portfolio.owner.id), /invalid portfolio details/);
  const planned = { ...portfolioDetails, portfolio_type: "PLANNED", plan_currency: "THB", holdings: [{ id: portfolioDetails.holdings[0].id, symbol: "AAPL", position: 0, weight: null, proposed_amount: "1234567890.123456789012" }] };
  assert.equal(contracts.portfolioDetailSchema.parse(planned).holdings[0].proposed_amount, "1234567890.123456789012");
  for (const invalid of [
    { ...planned, plan_currency: null }, { ...portfolioDetails, holding_count: 2 },
    { ...portfolioDetails, portfolio_type: "LEGACY" }, { ...portfolioDetails, source_plan_id: portfolio.id },
    { ...portfolioDetails, holdings: [{ ...portfolioDetails.holdings[0], shares: 2.123456789012 }] },
    { ...portfolioDetails, holdings: [{ ...portfolioDetails.holdings[0], invested_currency: "USD" }] },
    { ...portfolioDetails, holding_count: 2, holdings: [portfolioDetails.holdings[0], { ...portfolioDetails.holdings[0], symbol: "MSFT" }] },
  ]) assert.equal(contracts.portfolioDetailSchema.safeParse(invalid).success, false);
});
test("missing portfolios and read failures keep the admin session with safe feedback", async () => {
  for (const status of [404, 503]) {
    const { api } = setup(async () => response({ detail: "private credentials" }, status), "token");
    await assert.rejects(api.portfolio(portfolio.id), error => error.status === status && !error.message.includes("credentials") && (status !== 404 || error.message.includes("portfolio")));
    assert.equal(api.readToken(), "token");
  }
});
const identity = { id: "00000000-0000-4000-8000-000000000001", email: "admin@example.com", display_name: null, role: "ADMIN" };
function response(body, status = 200) { return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }); }
function setup(fetcher, token) {
  const values = new Map(token ? [[ADMIN_TOKEN_KEY, token]] : []);
  const storage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
  return { api: createAdminApi({ baseUrl: "http://127.0.0.1:8000", storage, fetcher }), values, storage };
}

test("uses shared login, checks persisted admin permission before saving its own token", async () => {
  const calls = [];
  const { api, values } = setup(async (url, init) => {
    calls.push([url, init]);
    assert.equal(values.size, 0);
    return calls.length === 1 ? response({ access_token: "synthetic-token", token_type: "bearer" }) : response(identity);
  });
  assert.deepEqual(await api.login(" admin@example.com ", "synthetic-password"), identity);
  assert.equal(values.get(ADMIN_TOKEN_KEY), "synthetic-token");
  assert.equal(calls[0][0], "http://127.0.0.1:8000/api/auth/login");
  assert.deepEqual(JSON.parse(calls[0][1].body), { email: identity.email, password: "synthetic-password" });
  assert.equal(calls[0][1].headers.Authorization, undefined);
  assert.equal(calls[1][0], "http://127.0.0.1:8000/api/admin/me");
  assert.equal(calls[1][1].headers.Authorization, "Bearer synthetic-token");
  for (const [, init] of calls) { assert.equal(init.credentials, "omit"); assert.equal(init.cache, "no-store"); assert.equal(init.redirect, "error"); }
});
test("refuses customer access without retaining its token or trusting role claims", async () => {
  let count = 0;
  const { api, values } = setup(async () => ++count === 1 ? response({ access_token: "customer-token", token_type: "bearer" }) : response({ detail: "private backend detail" }, 403));
  await assert.rejects(api.login("customer@example.com", "synthetic-password"), /Administrator access/);
  assert.equal(values.size, 0);
});
test("rejects a success response whose identity is not ADMIN", async () => {
  let count = 0;
  const { api, values } = setup(async () => ++count === 1 ? response({ access_token: "token", token_type: "bearer" }) : response({ ...identity, role: "CUSTOMER" }));
  await assert.rejects(api.login(identity.email, "synthetic-password"), /invalid response/);
  assert.equal(values.size, 0);
});
for (const status of [401, 403]) test(`${status} on a protected request removes the current session and notifies the guard`, async () => {
  const { api, values } = setup(async () => response({}, status), "old-token");
  let denied = 0; const unsubscribe = api.subscribeAccessDenied(() => denied++);
  await assert.rejects(api.dashboard());
  assert.equal(values.size, 0); assert.equal(denied, 1); unsubscribe();
});
test("a stale denial cannot remove a newer session", async () => {
  const { api, storage } = setup(async () => { storage.setItem(ADMIN_TOKEN_KEY, "new-token"); return response({}, 401); }, "old-token");
  let denied = 0; api.subscribeAccessDenied(() => denied++);
  await assert.rejects(api.me());
  assert.equal(api.readToken(), "new-token"); assert.equal(denied, 0);
});
test("503 is retryable, retains the session and hides backend exception details", async () => {
  const { api } = setup(async () => response({ detail: "database password should never be displayed" }, 503), "token");
  await assert.rejects(api.dashboard(), error => error.status === 503 && !error.message.includes("password"));
  assert.equal(api.readToken(), "token");
});
test("missing session makes no protected network request", async () => {
  const { api } = setup(async () => { throw new Error("should not fetch"); });
  await assert.rejects(api.dashboard(), error => error.status === 401);
});
test("directory filters use encoded server query and bounded page metadata", async () => {
  const { api } = setup(async url => {
    const query = new URL(url).searchParams;
    assert.equal(query.get("q"), "%_& person@example.com"); assert.equal(query.get("role"), "ADMIN"); assert.equal(query.get("account_type"), "REGISTERED"); assert.equal(query.get("offset"), "25");
    return response({ items: [], total: 27, limit: 25, offset: 25 });
  }, "token");
  assert.equal((await api.users({ q: "%_& person@example.com", role: "ADMIN", account_type: "REGISTERED", limit: 25, offset: 25 })).total, 27);
});
test("malformed payloads are rejected instead of generating fallback dashboard data", async () => {
  const { api } = setup(async () => response({ users: { total: 324 } }), "token");
  await assert.rejects(api.dashboard(), /invalid response/);
});
test("aborted login cannot save credentials after a late response", async () => {
  const controller = new AbortController(); let count = 0;
  const { api, values } = setup(async () => { if (++count === 1) return response({ access_token: "token", token_type: "bearer" }); controller.abort(); return response(identity); });
  await assert.rejects(api.login(identity.email, "synthetic-password", controller.signal), error => error.name === "AbortError");
  assert.equal(values.size, 0);
});
test("network failure does not expose raw exceptions", async () => {
  const { api } = setup(async () => { throw new Error("private endpoint or credential"); }, "token");
  await assert.rejects(api.me(), error => /Unable to reach/.test(error.message) && !error.message.includes("private"));
});
test("external cancellation remains cancellation, while timeouts become retryable errors", async () => {
  const fetcher = (_url, init) => new Promise((_resolve, reject) => init.signal.addEventListener("abort", () => reject(new DOMException("cancelled", "AbortError")), { once: true }));
  const { storage } = setup(fetcher, "token");
  const api = createAdminApi({ baseUrl: "http://127.0.0.1:8000", storage, fetcher, timeoutMs: 10 });
  await assert.rejects(api.me(), /timed out/);
  const controller = new AbortController(); const request = api.me(controller.signal); controller.abort();
  await assert.rejects(request, error => error.name === "AbortError");
});
test("configuration accepts origins and rejects embedded credentials and API paths", () => {
  assert.equal(apiOrigin(""), ""); assert.equal(apiOrigin("https://example.com/"), "https://example.com");
  for (const origin of ["https://user:password@example.com", "https://example.com/api", "javascript:alert(1)", "https://example.com?token=test"]) assert.throws(() => apiOrigin(origin));
});
test("decimal prices stay exact and metadata contracts strip unrecognized private fields", () => {
  const page = contracts.observationsSchema.parse({ items: [{ symbol: "AAPL", date: "2026-10-10", adjusted_close: "123.45678901", volume: null, source: "Synthetic" }], total: 1, limit: 25, offset: 0 });
  assert.equal(page.items[0].adjusted_close, "123.45678901");
  assert.deepEqual(contracts.identitySchema.parse({ ...identity, password_hash: "private" }), identity);
});

test("status actions use PATCH, carry the expected status and validate the server confirmation", async () => {
  const { api } = setup(async (url, init) => {
    assert.equal(url, `http://127.0.0.1:8000/api/admin/users/${identity.id}/status`);
    assert.equal(init.method, "PATCH");
    assert.equal(init.headers.Authorization, "Bearer token");
    assert.deepEqual(JSON.parse(init.body), { status: "SUSPENDED", expected_status: "ACTIVE" });
    return response({ id: identity.id, status: "SUSPENDED", updated_at: "2026-10-10T00:00:00Z" });
  }, "token");
  assert.equal((await api.setUserStatus(identity.id, "SUSPENDED", "ACTIVE")).status, "SUSPENDED");
  const wrong = setup(async () => response({ id: identity.id, status: "ACTIVE", updated_at: "2026-10-10T00:00:00Z" }), "token");
  await assert.rejects(wrong.api.setUserStatus(identity.id, "SUSPENDED", "ACTIVE"), /invalid status confirmation/);
});

test("status conflicts retain the session and only expose allowlisted safeguards", async () => {
  for (const detail of ["You cannot suspend your own account", "The last active administrator cannot be suspended", "private database password"]) {
    const { api } = setup(async () => response({ detail }, 409), "token");
    await assert.rejects(api.setUserStatus(identity.id, "SUSPENDED", "ACTIVE"), error => error.status === 409 && !error.message.includes("password"));
    assert.equal(api.readToken(), "token");
  }
});

test("audit schema accepts safe status changes and rejects mismatched events", () => {
  const event = { id: identity.id, created_at: "2026-10-10T00:00:00Z", actor_kind: "ADMIN", actor_user_id: identity.id,
    action: "USER_SUSPENDED", target_type: "USER", target_id: identity.id, details: { previous_status: "ACTIVE", new_status: "SUSPENDED" } };
  assert.equal(contracts.auditSchema.parse({ items: [event], total: 1, limit: 25, offset: 0 }).items[0].action, "USER_SUSPENDED");
  assert.throws(() => contracts.auditSchema.parse({ items: [{ ...event, details: { previous_status: "SUSPENDED", new_status: "ACTIVE" } }], total: 1, limit: 25, offset: 0 }));
});


const refreshRun = { id: identity.id, trigger: "ADMIN", requested_by: identity.id, status: "queued", requested_at: "2026-10-11T00:00:00Z", started_at: null, finished_at: null, attempt_count: 0, stored_count: 0, updated_symbols: [], failed_symbols: [], error_code: null };
test("manual refresh posts only a replayable request id and validates confirmation", async () => {
  const { api } = setup(async (url, init) => {
    assert.equal(url, "http://127.0.0.1:8000/api/admin/market-data/refresh");
    assert.equal(init.method, "POST");
    assert.deepEqual(JSON.parse(init.body), { request_id: identity.id });
    return response(refreshRun, 202);
  }, "token");
  assert.deepEqual(await api.requestMarketRefresh(identity.id), refreshRun);
  const wrong = setup(async () => response({ ...refreshRun, id: "00000000-0000-4000-8000-000000000002" }, 202), "token");
  await assert.rejects(wrong.api.requestMarketRefresh(identity.id), /invalid refresh confirmation/);
});
test("manual refresh conflicts are allowlisted and keep the administrator session", async () => {
  const { api } = setup(async () => response({ detail: "Market-data worker is offline" }, 409), "token");
  await assert.rejects(api.requestMarketRefresh(identity.id), /worker is offline/);
  assert.equal(api.readToken(), "token");
  const privateFailure = setup(async () => response({ detail: "private database details" }, 503), "token");
  await assert.rejects(privateFailure.api.requestMarketRefresh(identity.id), /currently unavailable/);
});
test("run history and audit reject invented states and non-daily refresh events", () => {
  assert.equal(contracts.marketRefreshRunSchema.safeParse({ ...refreshRun, status: "live" }).success, false);
  assert.equal(contracts.marketRefreshRunSchema.safeParse({ ...refreshRun, error_code: "private error" }).success, false);
  const event = { id: identity.id, created_at: refreshRun.requested_at, actor_kind: "ADMIN", actor_user_id: identity.id, target_type: "MARKET_REFRESH", target_id: identity.id, action: "MARKET_REFRESH_REQUESTED", details: { mode: "daily" } };
  assert.equal(contracts.auditSchema.safeParse({ items: [event], total: 1, limit: 25, offset: 0 }).success, true);
  assert.equal(contracts.auditSchema.safeParse({ items: [{ ...event, target_type: "USER" }], total: 1, limit: 25, offset: 0 }).success, false);
});


test("role changes send expected state and validate server confirmation", async () => {
  const result = { id: identity.id, role: "ADMIN", updated_at: "2026-10-13T00:00:00Z" };
  const { api } = setup(async (url, init) => {
    assert.equal(url, `http://127.0.0.1:8000/api/admin/users/${identity.id}/role`);
    assert.equal(init.method, "PATCH");
    assert.deepEqual(JSON.parse(init.body), { role: "ADMIN", expected_role: "CUSTOMER" });
    return response(result);
  }, "token");
  assert.deepEqual(await api.setUserRole(identity.id, "ADMIN", "CUSTOMER"), result);
  const wrongRole = setup(async () => response({ ...result, role: "CUSTOMER" }), "token");
  await assert.rejects(wrongRole.api.setUserRole(identity.id, "ADMIN", "CUSTOMER"), /invalid role confirmation/);
  const wrongId = setup(async () => response({ ...result, id: "00000000-0000-4000-8000-000000000002" }), "token");
  await assert.rejects(wrongId.api.setUserRole(identity.id, "ADMIN", "CUSTOMER"), /invalid role confirmation/);
});
test("role safeguards retain the actor session and expose only allowlisted detail", async () => {
  for (const detail of ["You cannot remove your own administrator access", "The last active administrator cannot be demoted", "Only registered accounts can become administrators", "Reactivate the account before granting administrator access"]) {
    const { api } = setup(async () => response({ detail }, 409), "token");
    await assert.rejects(api.setUserRole(identity.id, "ADMIN", "CUSTOMER"), error => error.message === detail + ".");
    assert.equal(api.readToken(), "token");
  }
  const failure = setup(async () => response({ detail: "private SQL credentials" }, 409), "token");
  await assert.rejects(failure.api.setUserRole(identity.id, "ADMIN", "CUSTOMER"), /Account role changed/);
});
test("role audit accepts both transitions and rejects unchanged roles or wrong actors", () => {
  const event = { id: identity.id, created_at: "2026-10-13T00:00:00Z", actor_kind: "ADMIN", actor_user_id: identity.id, target_type: "USER", target_id: identity.id, action: "USER_ROLE_CHANGED", details: { previous_role: "CUSTOMER", new_role: "ADMIN" } };
  const valid = value => contracts.auditSchema.safeParse({ items: [value], total: 1, limit: 25, offset: 0 }).success;
  assert.equal(valid(event), true);
  assert.equal(valid({ ...event, details: { previous_role: "ADMIN", new_role: "CUSTOMER" } }), true);
  assert.equal(valid({ ...event, details: { previous_role: "ADMIN", new_role: "ADMIN" } }), false);
  assert.equal(valid({ ...event, actor_kind: "OPERATOR", actor_user_id: null }), false);
});


test("account creation uses the admin endpoint, preserves password bytes and leaves actor session intact", async () => {
  const result = { id: identity.id, email: "created@example.com", display_name: "New User", role: "CUSTOMER", account_type: "REGISTERED", status: "ACTIVE", created_at: "2026-10-13T00:00:00Z", updated_at: "2026-10-13T00:00:00Z", portfolio_count: 0 };
  const { api } = setup(async (url, init) => {
    assert.equal(url, "http://127.0.0.1:8000/api/admin/users");
    assert.equal(init.method, "POST");
    assert.deepEqual(JSON.parse(init.body), { email: result.email, password: "  synthetic password  ", display_name: "New User" });
    return response(result, 201);
  }, "actor-token");
  assert.deepEqual(await api.createUser({ email: " created@example.com ", password: "  synthetic password  ", display_name: " New User " }), result);
  assert.equal(api.readToken(), "actor-token");
  const invalid = setup(async () => response({ ...result, role: "ADMIN" }, 201), "token");
  await assert.rejects(invalid.api.createUser({ email: result.email, password: "synthetic password" }), /invalid response/);
});
test("duplicate account feedback is safe and never clears the creating administrator session", async () => {
  const { api } = setup(async () => response({ detail: "Email already registered" }, 409), "token");
  await assert.rejects(api.createUser({ email: "created@example.com", password: "synthetic password" }), /already registered/);
  assert.equal(api.readToken(), "token");
});
test("account creation audit allows only registered customer metadata", () => {
  const event = { id: identity.id, created_at: "2026-10-13T00:00:00Z", actor_kind: "ADMIN", actor_user_id: identity.id, target_type: "USER", target_id: identity.id, action: "USER_CREATED", details: { role: "CUSTOMER", account_type: "REGISTERED" } };
  const valid = value => contracts.auditSchema.safeParse({ items: [value], total: 1, limit: 25, offset: 0 }).success;
  assert.equal(valid(event), true);
  assert.equal(valid({ ...event, details: { role: "ADMIN", account_type: "REGISTERED" } }), false);
  assert.equal(valid({ ...event, actor_kind: "OPERATOR", actor_user_id: null }), false);
});
