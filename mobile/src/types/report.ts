import type {
  AnalysisPeriod,
  AssetMetrics,
  PortfolioAnalysisResponse,
  RiskDriverEntry
} from './analytics';
import type { IsoDate, IsoDateTime, Uuid } from './api';
import type {
  DecimalString,
  PortfolioCurrency,
  PortfolioHoldingValuationResponse,
  PortfolioValuationFxResponse
} from './portfolio';

type PortfolioReportEnvelope = {
  id: Uuid;
  portfolio_id: Uuid;
  created_at: IsoDateTime;
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
};

export type PortfolioReportResponse =
  | PortfolioReportV1Response
  | PortfolioReportV2Response;

export function isPortfolioReportV2(
  report: PortfolioReportResponse
): report is PortfolioReportV2Response {
  return 'schema_version' in report
    && report.schema_version === 'portfolio-analysis-response-v2';
}

export type PortfolioReportSummary = AnalysisPeriod & {
  id: Uuid;
  portfolio_id: Uuid;
  created_at: IsoDateTime;
};

export type PortfolioReportListResponse = {
  reports: PortfolioReportSummary[];
};
