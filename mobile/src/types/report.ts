import type { PortfolioAnalysis } from './analytics';

export type ReportSnapshot = {
  id: string;
  portfolioId: string;
  portfolioName: string;
  createdAt: string;
  analysis: PortfolioAnalysis;
};
