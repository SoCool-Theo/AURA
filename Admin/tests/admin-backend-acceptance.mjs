// Opt-in integration check against serve-backend-fixture.py on port 8019.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const root = fileURLToPath(new URL("..", import.meta.url));
const credentials = JSON.parse(await readFile(new URL("../.wrangler/admin-fixture-credentials.json", import.meta.url), "utf8"));
const baseUrl = process.argv[2] ?? "http://127.0.0.1:8019";
assert.ok(["http://127.0.0.1:8019", "http://127.0.0.1:5191", "http://127.0.0.1:5192"].includes(baseUrl), "Use only the documented localhost fixture/preview ports");
const vite = await createServer({ root, configFile: false, cacheDir: ".wrangler/admin-acceptance-cache", appType: "custom", server: { middlewareMode: true, hmr: false, ws: false } });
try {
  const { createAdminApi } = await vite.ssrLoadModule("/lib/adminApi.ts");
  const values = new Map();
  const storage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
  const api = createAdminApi({ baseUrl, storage });
  await assert.rejects(api.login(credentials.customer, credentials.password), error => error.status === 403);
  assert.equal(values.size, 0);
  assert.equal((await api.login(credentials.admin, credentials.password)).role, "ADMIN");
  for (const [name, load] of [
    ["identity", () => api.me()], ["dashboard", () => api.dashboard()],
    ["users", () => api.users({ limit: 25 })], ["inventory", () => api.inventory()],
    ["refresh status", () => api.marketStatus()], ["observations", () => api.observations({ symbol: "AAPL", limit: 25 })],
    ["health", () => api.health()], ["AI summary", () => api.aiSummary()],
    ["AI requests", () => api.aiRequests({ outcome: "REFUSED", limit: 25 })],
    ["audit", () => api.audit({ action: "ADMIN_BOOTSTRAPPED", limit: 25 })],
  ]) { await load(); console.log(`PASS real router + client contract: ${name}`); }
  for (let round = 0; round < 3; round++) {
    await Promise.all([api.dashboard(), api.inventory(), api.marketStatus(), api.health(), api.audit({ limit: 4 })]);
  }
  console.log("PASS concurrent dashboard reads across three rounds");
  assert.equal((await api.users({ limit: 25, offset: 25 })).items.length, 7);
  assert.equal((await api.users({ q: "customer00@example.com", limit: 25 })).total, 1);
  assert.equal((await api.users({ q: "doesnotexist", limit: 25 })).total, 0);
  assert.equal((await api.users({ role: "ADMIN", limit: 25 })).total, 1);
  assert.equal((await api.users({ account_type: "LEGACY", limit: 25 })).total, 1);
  assert.equal((await api.aiRequests({ outcome: "COMPLETED", limit: 25 })).total, 0);
  api.clearToken(); await assert.rejects(api.dashboard(), error => error.status === 401);
  console.log("PASS customer denial, pagination, server filters, empty results, and cleared session");
} finally { await vite.close(); }
