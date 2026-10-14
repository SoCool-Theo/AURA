import { z } from "zod";

const count = z.number().int().nonnegative();
const finite = z.number().finite();
const unit = finite.min(0).max(1);
const date = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const time = z.string().datetime({ offset: true });
const uuid = z.string().uuid();
const currency = z.enum(["USD", "THB"]);
const decimal = z.string().regex(/^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/);
const positive = decimal.refine(value => !value.startsWith("-") && /[1-9]/.test(value.split(/[eE]/)[0]));
const versionNames = { V1: "portfolio-analysis-response-v1", V2: "portfolio-analysis-response-v2", V3: "portfolio-analysis-response-v3" } as const;
const metadata = z.object({
  id: uuid, portfolio_id: uuid, portfolio_name: z.string(), start_date: date, end_date: date, created_at: time,
  schema_version: z.string(), report_version: z.enum(["V1", "V2", "V3", "OTHER"]),
  owner: z.object({ id: uuid, email: z.string().email().nullable(), display_name: z.string().nullable(), account_type: z.enum(["REGISTERED", "LEGACY"]), status: z.enum(["ACTIVE", "SUSPENDED"]) }),
});
const validMetadata = (item: z.infer<typeof metadata>) => item.start_date <= item.end_date && (item.report_version === "OTHER" ? !Object.values<string>(versionNames).includes(item.schema_version) : versionNames[item.report_version] === item.schema_version);
export const reportsSchema = z.object({ items: z.array(metadata.refine(validMetadata)), total: count, limit: count.min(1).max(100), offset: count.max(10000) });
export type AdminReport = z.infer<typeof metadata>;
const risk = z.object({ risk_score: finite.min(0).max(100), risk_level: z.enum(["Low", "Moderate", "High", "Very High"]), reasons: z.array(z.string()).min(1) });
const analysis = z.object({
  portfolio_name: z.string(), start_date: date, end_date: date,
  metadata: z.object({ analysis_start: date, analysis_end: date, price_observation_count: count, return_observation_count: count, asset_count: count.min(1) }),
  portfolio_metrics: z.object({ cumulative_return: finite, annualized_return: finite, annualized_volatility: finite.nonnegative(), sharpe_ratio: finite }),
  max_drawdown: z.object({ max_drawdown: finite.min(-1).max(0), peak_date: date.nullable(), trough_date: date.nullable() }),
  concentration: z.object({ largest_weight: unit, top_n_weight: unit, hhi: unit, effective_number_of_assets: finite.positive() }),
  diversification: z.object({ overall_score: finite.min(0).max(100).nullable(), level: z.enum(["Weak", "Moderate", "Strong", "Unavailable"]) }),
  risk_classification: risk,
  asset_metrics: z.array(z.object({ symbol: z.string().min(1), weight: unit, cumulative_return: finite, annualized_return: finite, annualized_volatility: finite.nonnegative(), max_drawdown: finite.min(-1).max(0), sharpe_ratio: finite.nullable() })).min(1),
  risk_drivers: z.object({ top_driver: z.string().min(1), entries: z.array(z.object({ rank: count.min(1), symbol: z.string().min(1), weight: unit, percentage_volatility_contribution: finite })).min(1) }),
  correlation_matrix: z.object({ symbols: z.array(z.string()).min(1), values: z.array(z.array(finite.min(-1).max(1).nullable())) }),
}).refine(item => item.start_date <= item.end_date && item.metadata.asset_count === item.asset_metrics.length &&
  item.correlation_matrix.values.length === item.correlation_matrix.symbols.length && item.correlation_matrix.values.every(row => row.length === item.correlation_matrix.symbols.length));
const monetary = z.object({ currency, basis: z.enum(["fixed-shares-historical-value", "saved-current-valuation", "planned-proposed-amount"]), reference_amount: positive, cumulative_return_amount: decimal, annualized_return_amount: decimal, maximum_drawdown_amount: decimal.nullable(), estimated_ending_value: positive.nullable().optional() });
const envelope = { id: uuid, portfolio_id: uuid, created_at: time, analysis };
const legacy = z.object({ ...envelope, schema_version: z.literal(versionNames.V1).optional() });
const current = z.object({ ...envelope, schema_version: z.literal(versionNames.V2),
  valuation: z.object({ valuation_currency: currency, requested_date: date, oldest_price_as_of: date, newest_price_as_of: date, total_current_value: positive, total_current_value_usd: positive }),
  holdings: z.array(z.object({ id: uuid, symbol: z.string(), shares: positive, position: count, current_value: positive, current_allocation: positive, price_as_of: date })),
  monetary_metrics: monetary.nullable().optional(),
});
const planned = z.object({ ...envelope, schema_version: z.literal(versionNames.V3),
  baseline: z.object({ portfolio_type: z.literal("PLANNED"), baseline_source: z.literal("proposed-amount-target-allocation"), plan_currency: currency, total_proposed_amount: positive, hypothetical_notice: z.string().min(1),
    holdings: z.array(z.object({ id: uuid, symbol: z.string(), proposed_amount: positive, target_allocation: positive, position: count })).min(1) }),
  monetary_metrics: monetary.nullable().optional(),
});
export const reportDetailSchema = metadata.extend({ report: z.union([planned, current, legacy]) }).refine(item => validMetadata(item) &&
  item.report.id === item.id && item.report.portfolio_id === item.portfolio_id && Date.parse(item.created_at) === Date.parse(item.report.created_at) &&
  item.report.analysis.start_date === item.start_date && item.report.analysis.end_date === item.end_date &&
  (item.report.schema_version ?? versionNames.V1) === item.schema_version);
export type AdminReportDetail = z.infer<typeof reportDetailSchema>;
