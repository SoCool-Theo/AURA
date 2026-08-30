import type { IsoDateTime, Uuid } from './api';

export type PortfolioHoldingInput = {
  symbol: string;
  weight: number;
};

export type PortfolioCreateRequest = {
  name: string;
};

export type PortfolioUpdateRequest = {
  name: string;
};

export type PortfolioDuplicateRequest = {
  name: string;
};

export type PortfolioHoldingsReplaceRequest = {
  holdings: PortfolioHoldingInput[];
};

export type PortfolioHoldingResponse = PortfolioHoldingInput & {
  position: number;
};

export type PortfolioResponse = {
  id: Uuid;
  name: string;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  holdings: PortfolioHoldingResponse[];
};

export type PortfolioSummaryResponse = {
  id: Uuid;
  name: string;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
};

export type PortfolioListResponse = {
  portfolios: PortfolioSummaryResponse[];
};

// Legacy prototype view models retained for deferred, mock-backed feature
// pages. Production portfolio routes use the backend response types above.
export type Holding = {
  symbol: string;
  name: string;
  type: string;
  weight: number;
  value: number;
  dailyChange: number;
  price: number;
  shares: number;
};

export type Portfolio = {
  id: string;
  name: string;
  created: string;
  value: number;
  totalReturn: number;
  annualizedReturn?: number;
  riskScore: number;
  riskLevel: string;
  cash: number;
  holdings: Holding[];
};
