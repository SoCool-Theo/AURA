import { z } from "zod";

const count = z.number().int().nonnegative();
const timestamp = z.string().datetime({ offset: true });
const date = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const nullableTime = timestamp.nullable();
const role = z.enum(["CUSTOMER", "ADMIN"]);
const accountStatus = z.enum(["ACTIVE", "SUSPENDED"]);
export type AdminAccountStatus = z.infer<typeof accountStatus>;
const healthStatus = z.enum(["healthy", "degraded", "unavailable", "unknown", "not_checked"]);
const outcome = z.enum(["COMPLETED", "REFUSED", "ERROR"]);
const provider = z.enum(["openai", "groq", "custom"]);
const price = z.string().regex(/^\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/);

export const tokenSchema = z.object({ access_token: z.string().trim().min(1), token_type: z.literal("bearer") });
export const identitySchema = z.object({ id: z.string().uuid(), email: z.string().email(), display_name: z.string().nullable(), role: z.literal("ADMIN") });
export type AdminIdentity = z.infer<typeof identitySchema>;

export function pageSchema<T extends z.ZodTypeAny>(item: T) {
  return z.object({ items: z.array(item), total: count, limit: count.min(1).max(100), offset: count.max(10000) });
}
export type Page<T> = { items: T[]; total: number; limit: number; offset: number };

const savedCounts = z.object({ total: count, today: count, yesterday: count, last_7_days: count });
export const dashboardSchema = z.object({
  generated_at: timestamp, timezone: z.literal("UTC"), window_start: date, window_end: date,
  users: z.object({ total: count, customers: count, admins: count, registered: count, legacy: count, new_last_7_days: count }),
  portfolios: z.object({ total: count, current: count, planned: count, legacy: count, new_last_7_days: count }),
  saved_reports: savedCounts, saved_simulations: savedCounts,
  daily: z.array(z.object({ date, new_users: count, new_portfolios: count, saved_reports: count, saved_simulations: count })),
});
export type Dashboard = z.infer<typeof dashboardSchema>;
export const usersSchema = pageSchema(z.object({
  id: z.string().uuid(), email: z.string().email().nullable(), display_name: z.string().nullable(), role,
  account_type: z.enum(["REGISTERED", "LEGACY"]), status: accountStatus, created_at: timestamp, updated_at: timestamp, portfolio_count: count,
}));
export type AdminUser = z.infer<typeof usersSchema>["items"][number];
export const userStatusSchema = z.object({ id: z.string().uuid(), status: accountStatus, updated_at: timestamp });

export const inventorySchema = z.object({
  checked_at: timestamp, total_records: count, stored_symbols: count, required_symbols: count,
  present_required_symbols: count, current_required_symbols: count, stale_required_symbols: count,
  missing_required_symbols: count, unexpected_symbols: count,
  instruments: z.array(z.object({
    symbol: z.string(), required_for_refresh: z.boolean(), kind: z.enum(["asset", "fx", "unknown"]),
    quote_currency: z.string().nullable(), base_currency: z.string().nullable(), total_records: count,
    first_price_date: date.nullable(), latest_price_date: date.nullable(), latest_adjusted_close: price.nullable(),
    latest_volume: count.nullable(), latest_source: z.string().nullable(), age_days: count.nullable(),
    freshness: z.enum(["current", "stale", "missing", "unknown"]),
  })),
});
export type Inventory = z.infer<typeof inventorySchema>;
export const observationsSchema = pageSchema(z.object({ symbol: z.string(), date, adjusted_close: price, volume: count.nullable(), source: z.string() }));
export const marketStatusSchema = z.object({
  mode: z.literal("daily"), checked_at: timestamp, update_time_utc: z.string(), next_scheduled_at: timestamp,
  worker_status: z.enum(["unknown", "online", "offline"]), worker_last_seen_at: nullableTime,
  last_run_status: z.enum(["never", "running", "success", "partial", "failed"]),
  last_attempt_at: nullableTime, last_finished_at: nullableTime, last_complete_at: nullableTime,
  attempt_count: count, stored_count: count, updated_symbols: z.array(z.string()), failed_symbols: z.array(z.string()),
  error_code: z.enum(["provider_unavailable", "database_unavailable", "validation_failed", "update_failed", "lock_lost", "incomplete_coverage"]).nullable(),
  data_status: z.enum(["current", "stale", "missing"]),
  observations: z.array(z.object({ symbol: z.string(), kind: z.enum(["asset", "fx"]), latest_price_date: date.nullable(), age_days: count.nullable(), is_current: z.boolean() })),
});
export type MarketStatus = z.infer<typeof marketStatusSchema>;
export const healthSchema = z.object({
  checked_at: timestamp, status: z.enum(["healthy", "degraded", "unavailable", "unknown"]), coverage: z.literal("partial"),
  checks: z.array(z.object({
    component: z.enum(["api", "authentication", "database", "market_data_worker", "market_data", "market_data_refresh", "market_data_provider", "analytics"]),
    status: healthStatus, reason: z.string(), latency_ms: z.number().finite().nonnegative().nullable(),
  })), market_data: marketStatusSchema.nullable(),
});
export type Health = z.infer<typeof healthSchema>;

const auditFields = {
  id: z.string().uuid(), created_at: timestamp, actor_kind: z.enum(["OPERATOR", "ADMIN"]), actor_user_id: z.string().uuid().nullable(),
  target_type: z.literal("USER"), target_id: z.string().uuid(),
};
export const auditSchema = pageSchema(z.discriminatedUnion("action", [
  z.object({ ...auditFields, actor_kind: z.literal("OPERATOR"), actor_user_id: z.null(), action: z.literal("ADMIN_BOOTSTRAPPED"), details: z.object({ previous_role: z.literal("CUSTOMER"), new_role: z.literal("ADMIN") }) }),
  z.object({ ...auditFields, actor_kind: z.literal("ADMIN"), actor_user_id: z.string().uuid(), action: z.literal("USER_SUSPENDED"), details: z.object({ previous_status: z.literal("ACTIVE"), new_status: z.literal("SUSPENDED") }) }),
  z.object({ ...auditFields, actor_kind: z.literal("ADMIN"), actor_user_id: z.string().uuid(), action: z.literal("USER_REACTIVATED"), details: z.object({ previous_status: z.literal("SUSPENDED"), new_status: z.literal("ACTIVE") }) }),
]));
export type AuditEvent = z.infer<typeof auditSchema>["items"][number];

export const aiSummarySchema = z.object({
  checked_at: timestamp, total: count, completed: count, refused: count, errors: count, provider_calls: count,
  input_refusals: count, output_refusals: count, average_duration_ms: z.number().finite().nonnegative().nullable(),
  first_recorded_at: nullableTime, last_recorded_at: nullableTime,
  configuration: z.object({
    configured_provider: z.enum(["openai", "groq"]).nullable(), model_configured: z.boolean(), credential_configured: z.boolean(),
    ready: z.boolean(), connectivity: z.literal("not_checked"), telemetry_mode: z.literal("best_effort_metadata"), advice_guard_enabled: z.literal(true),
  }),
});
export const aiRequestsSchema = pageSchema(z.object({
  id: z.string().uuid(), created_at: timestamp, started_at: timestamp, duration_ms: z.number().finite().nonnegative(),
  outcome, http_status: z.union([z.literal(200), z.literal(404), z.literal(409), z.literal(500), z.literal(502), z.literal(503)]),
  provider_kind: provider.nullable(), provider_called: z.boolean(), refusal_stage: z.enum(["INPUT", "OUTPUT"]).nullable(),
  guardrail_reason: z.enum(["empty_message", "investment_advice", "invalid_output", "output_too_long", "system_leakage", "planned_ownership_claim"]).nullable(),
  error_code: z.enum(["CONTEXT_UNAVAILABLE", "REPORT_UNAVAILABLE", "SIMULATION_UNAVAILABLE", "MARKET_DATA_UNAVAILABLE", "HOLDING_STATE_INVALID", "PROVIDER_UNAVAILABLE", "PROVIDER_TIMEOUT", "INVALID_PROVIDER_RESPONSE", "UNSAFE_PROVIDER_OUTPUT", "INTERNAL_ERROR"]).nullable(),
  has_portfolio_source: z.boolean(), has_report_source: z.boolean(), has_simulation_source: z.boolean(), limitation_count: count.max(10),
}));
