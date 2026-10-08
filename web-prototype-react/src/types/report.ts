import type {
  AnalysisPeriod,
  AssetMetrics,
  PortfolioAnalysisResponse,
  RiskDriverEntry,
} from './analytics';
import type { IsoDate, IsoDateTime, Uuid } from './api';
import type {
  DecimalString,
  PlannedPortfolioBaselineContext,
  PortfolioCurrency,
  PortfolioHoldingValuationResponse,
  PortfolioValuationFxResponse,
} from './portfolio';

type PortfolioReportEnvelope = {
  id: Uuid;
  portfolio_id: Uuid;
  created_at: IsoDateTime;
};

export type PortfolioReportMonetaryMetrics = {
  currency: PortfolioCurrency;
  basis:
    | 'fixed-shares-historical-value'
    | 'saved-current-valuation'
    | 'planned-proposed-amount';
  reference_amount: DecimalString;
  cumulative_return_amount: DecimalString;
  annualized_return_amount: DecimalString;
  maximum_drawdown_amount: DecimalString | null;
  estimated_ending_value?: DecimalString | null;
};

export type PortfolioReportAssetMonetaryMetrics = {
  symbol: string;
  currency: PortfolioCurrency;
  basis: 'saved-current-value' | 'planned-proposed-amount';
  reference_amount: DecimalString;
  cumulative_return_amount: DecimalString;
  annualized_return_amount: DecimalString;
  maximum_drawdown_amount: DecimalString | null;
};

export type PortfolioReportV1Response = PortfolioReportEnvelope & {
  analysis: PortfolioAnalysisResponse;
};

export type PortfolioReportV2ValuationContext = {
  valuation_currency: PortfolioCurrency;
  requested_date: IsoDate;
  oldest_price_as_of: IsoDate;
  newest_price_as_of: IsoDate;
  total_current_value_usd: DecimalString;
  total_current_value: DecimalString;
  fx: PortfolioValuationFxResponse | null;
};

export type PortfolioReportV2Holding = PortfolioHoldingValuationResponse & {
  asset_metrics: AssetMetrics;
  risk_driver: RiskDriverEntry;
};

export type PortfolioReportV2Response = PortfolioReportEnvelope & {
  schema_version: 'portfolio-analysis-response-v2';
  analysis: PortfolioAnalysisResponse;
  valuation: PortfolioReportV2ValuationContext;
  holdings: PortfolioReportV2Holding[];
  monetary_metrics?: PortfolioReportMonetaryMetrics | null;
  asset_monetary_metrics?: PortfolioReportAssetMonetaryMetrics[];
};

export type PortfolioReportV3Response = PortfolioReportEnvelope & {
  schema_version: 'portfolio-analysis-response-v3';
  analysis: PortfolioAnalysisResponse;
  baseline: PlannedPortfolioBaselineContext;
  currency_conversion?: {
    requested_date: IsoDate;
    fx: PortfolioValuationFxResponse;
  } | null;
  monetary_metrics?: PortfolioReportMonetaryMetrics | null;
  asset_monetary_metrics?: PortfolioReportAssetMonetaryMetrics[];
  currency_views?: PortfolioReportV3CurrencyView[];
};

export type PortfolioReportV3CurrencyView = {
  currency: PortfolioCurrency;
  total_proposed_amount: DecimalString;
  holdings: Array<{
    symbol: string;
    proposed_amount: DecimalString;
  }>;
  monetary_metrics: PortfolioReportMonetaryMetrics;
  asset_monetary_metrics: PortfolioReportAssetMonetaryMetrics[];
};

export type PortfolioReportResponse =
  | PortfolioReportV1Response
  | PortfolioReportV2Response
  | PortfolioReportV3Response;

export function isPortfolioReportV2(
  report: PortfolioReportResponse,
): report is PortfolioReportV2Response {
  return 'schema_version' in report
    && report.schema_version === 'portfolio-analysis-response-v2';
}

export function isPortfolioReportV3(
  report: PortfolioReportResponse,
): report is PortfolioReportV3Response {
  return 'schema_version' in report
    && report.schema_version === 'portfolio-analysis-response-v3';
}

export type PortfolioReportSummary = AnalysisPeriod & {
  id: Uuid;
  portfolio_id: Uuid;
  created_at: IsoDateTime;
};

export type PortfolioReportListResponse = {
  reports: PortfolioReportSummary[];
};

export type PortfolioReportHistoryItem = PortfolioReportSummary & {
  portfolio_name: string;
};

// Legacy prototype view models retained only for deferred mock-backed
// simulation/demo code. Production Analytics and Reports use the API types.
export type ReportSummary = {
  id: number;
  portfolioId: string;
  name: string;
  portfolio: string;
  type: 'Analysis' | 'Simulation' | 'Comparison';
  date: string;
  riskScore: number | null;
};

export type ReportRiskLevel = 'Low' | 'Moderate' | 'High';

export type ReportMetric = {
  label: string;
  value: number;
  format: 'currency' | 'percentage' | 'decimal' | 'score';
  detail: string;
  tone: 'teal' | 'amber' | 'red' | 'blue';
  icon: string;
};

export type ReportPerformanceSnapshot = {
  periodLabel: string;
  startValue: number;
  endValue: number;
  periodReturn: number;
  annualizedReturn: number;
  values: ReadonlyArray<number>;
  labels: ReadonlyArray<string>;
};

export type ReportRiskDriver = {
  rank: number;
  symbol: string;
  name: string;
  weight: number;
  riskContribution: number;
  impactScore: number;
  explanation: string;
};

export type ReportAssetDetail = {
  symbol: string;
  name: string;
  assetType: string;
  weight: number;
  value: number;
  annualizedReturn: number;
  annualizedVolatility: number;
  maxDrawdown: number;
  riskScore: number;
};

export type CorrelationTone =
  | 'self'
  | 'positive-strong'
  | 'positive-medium'
  | 'positive-weak'
  | 'negative-weak';

export type ReportCorrelationCell = {
  value: number;
  tone: CorrelationTone;
};

export type ReportCorrelationSnapshot = {
  symbols: ReadonlyArray<string>;
  matrix: ReadonlyArray<ReadonlyArray<ReportCorrelationCell>>;
  averageCorrelation: number;
  note: string;
};

export type ReportDetail = {
  id: number;
  portfolioId: string;
  title: string;
  reportType: 'Portfolio Analysis';
  portfolioName: string;
  createdAt: string;
  analysisPeriod: string;
  version: string;
  status: 'Complete';
  riskScore: number;
  riskLevel: ReportRiskLevel;
  summary: string;
  metrics: ReadonlyArray<ReportMetric>;
  performance: ReportPerformanceSnapshot;
  riskDrivers: ReadonlyArray<ReportRiskDriver>;
  assets: ReadonlyArray<ReportAssetDetail>;
  correlation: ReportCorrelationSnapshot;
};
