import type { AnalysisPeriod, PortfolioAnalysisResponse } from './analytics';
import type { IsoDateTime, Uuid } from './api';

export type PortfolioReportResponse = {
  id: Uuid;
  portfolio_id: Uuid;
  created_at: IsoDateTime;
  analysis: PortfolioAnalysisResponse;
};

export type PortfolioReportSummary = AnalysisPeriod & {
  id: Uuid;
  portfolio_id: Uuid;
  created_at: IsoDateTime;
};

export type PortfolioReportListResponse = {
  reports: PortfolioReportSummary[];
};
