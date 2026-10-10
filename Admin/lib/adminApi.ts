import type { z } from "zod";
import * as contracts from "./adminContracts";

export const ADMIN_TOKEN_KEY = "aura.admin.accessToken";
export class AdminApiError extends Error {
  constructor(message: string, public readonly status: number | null = null) { super(message); this.name = "AdminApiError"; }
}
export function apiOrigin(value: string): string {
  if (!value.trim()) return ""; // Same-origin reverse proxy; no token transfer between websites.
  let url: URL;
  try { url = new URL(value.trim()); } catch { throw new AdminApiError("The admin API origin is invalid."); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new AdminApiError("Configure only the HTTP(S) API origin, without credentials or /api.");
  }
  return url.origin;
}

type Query = Record<string, string | number | undefined>;
type ApiOptions = { baseUrl?: string; fetcher?: typeof fetch; storage?: Storage; timeoutMs?: number };
export function createAdminApi(options: ApiOptions = {}) {
  const listeners = new Set<() => void>();
  const storage = () => options.storage ?? (typeof window === "undefined" ? undefined : window.sessionStorage);
  const readToken = () => { try { return storage()?.getItem(ADMIN_TOKEN_KEY)?.trim() || null; } catch { return null; } };
  const clearToken = () => { try { storage()?.removeItem(ADMIN_TOKEN_KEY); } catch { /* Clear in-memory access even if storage is denied. */ } };
  function deny(token: string) {
    if (readToken() !== token) return; // An old response cannot invalidate a newer login.
    clearToken(); listeners.forEach(listener => listener());
  }
  async function request<T>(path: string, schema: z.ZodType<T>, token: string | null, signal?: AbortSignal, body?: { email: string; password: string }) {
    if (path !== "/api/auth/login" && !path.startsWith("/api/admin/")) throw new AdminApiError("Unsupported admin request.");
    if (path !== "/api/auth/login" && !token) throw new AdminApiError("Sign in to continue.", 401);
    const controller = new AbortController();
    const abort = () => controller.abort();
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) controller.abort();
    const timer = setTimeout(abort, options.timeoutMs ?? 15000);
    try {
      const origin = apiOrigin(options.baseUrl ?? (import.meta.env.DEV ? "" : import.meta.env.VITE_API_BASE_URL ?? ""));
      const response = await (options.fetcher ?? fetch)(origin + path, {
        method: body ? "POST" : "GET", credentials: "omit", cache: "no-store", redirect: "error", signal: controller.signal,
        headers: { Accept: "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body ? { "Content-Type": "application/json" } : {}) },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      if (!response.ok) {
        if (token && (response.status === 401 || response.status === 403)) deny(token);
        const messages: Record<number, string> = {
          401: body ? "Email or password is incorrect." : "Your session has expired. Sign in again.",
          403: "Administrator access is required for this account.", 422: "Check the supplied filters or sign-in fields.",
          503: "This service is currently unavailable. Try again shortly.",
        };
        throw new AdminApiError(messages[response.status] ?? "The admin request could not be completed.", response.status);
      }
      let data: unknown;
      try { data = await response.json(); } catch { throw new AdminApiError("The API returned an invalid response."); }
      const parsed = schema.safeParse(data);
      if (!parsed.success) throw new AdminApiError("The API returned an invalid response.");
      return parsed.data;
    } catch (error) {
      if (signal?.aborted) throw new DOMException("Request cancelled", "AbortError");
      if (error instanceof AdminApiError) throw error;
      throw new AdminApiError(controller.signal.aborted ? "The API request timed out. Try again." : "Unable to reach the Aura API. Check the connection and try again.");
    } finally { clearTimeout(timer); signal?.removeEventListener("abort", abort); }
  }
  function get<T>(path: string, schema: z.ZodType<T>, signal?: AbortSignal, query: Query = {}) {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => { if (value !== undefined && value !== "") params.set(key, String(value)); });
    return request(path + (params.size ? `?${params}` : ""), schema, readToken(), signal);
  }
  return {
    readToken, clearToken,
    subscribeAccessDenied(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    async login(email: string, password: string, signal?: AbortSignal) {
      const result = await request("/api/auth/login", contracts.tokenSchema, null, signal, { email: email.trim(), password });
      const identity = await request("/api/admin/me", contracts.identitySchema, result.access_token, signal);
      if (signal?.aborted) throw new DOMException("Request cancelled", "AbortError");
      try { const target = storage(); if (!target) throw new Error(); target.setItem(ADMIN_TOKEN_KEY, result.access_token); }
      catch { throw new AdminApiError("Browser session storage is unavailable. Allow it and try again."); }
      return identity;
    },
    me: (signal?: AbortSignal) => get("/api/admin/me", contracts.identitySchema, signal),
    dashboard: (signal?: AbortSignal) => get("/api/admin/dashboard", contracts.dashboardSchema, signal),
    users: (query: Query, signal?: AbortSignal) => get("/api/admin/users", contracts.usersSchema, signal, query),
    inventory: (signal?: AbortSignal) => get("/api/admin/market-data", contracts.inventorySchema, signal),
    marketStatus: (signal?: AbortSignal) => get("/api/admin/market-data/status", contracts.marketStatusSchema, signal),
    observations: (query: Query, signal?: AbortSignal) => get("/api/admin/market-data/observations", contracts.observationsSchema, signal, query),
    health: (signal?: AbortSignal) => get("/api/admin/system-health", contracts.healthSchema, signal),
    audit: (query: Query, signal?: AbortSignal) => get("/api/admin/audit-logs", contracts.auditSchema, signal, query),
    aiSummary: (signal?: AbortSignal) => get("/api/admin/ai-monitoring", contracts.aiSummarySchema, signal),
    aiRequests: (query: Query, signal?: AbortSignal) => get("/api/admin/ai-monitoring/requests", contracts.aiRequestsSchema, signal, query),
  };
}
export const adminApi = createAdminApi();
