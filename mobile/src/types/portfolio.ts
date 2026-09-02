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
