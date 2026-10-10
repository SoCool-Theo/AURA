import assert from "node:assert/strict";
import test, { after } from "node:test";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const root = fileURLToPath(new URL("..", import.meta.url));
const vite = await createServer({ configFile: false, root, cacheDir: ".wrangler/admin-api-test-cache", appType: "custom", server: { middlewareMode: true, hmr: false, ws: false } });
after(() => vite.close());
const { createAdminApi, ADMIN_TOKEN_KEY, apiOrigin } = await vite.ssrLoadModule("/lib/adminApi.ts");
const contracts = await vite.ssrLoadModule("/lib/adminContracts.ts");
const identity = { id: "00000000-0000-4000-8000-000000000001", email: "admin@example.com", display_name: null, role: "ADMIN" };
const response = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
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
