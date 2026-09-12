import type { IsoDate, IsoDateTime, Uuid } from './api';

export type PortfolioCurrency = 'USD' | 'THB';

/** Decimal values are serialized as strings by the backend to preserve precision. */
export type DecimalString = string;

export type PortfolioAllocationInput = {
  symbol: string;
  weight: number;
};

export type PortfolioRealHoldingInput = {
  symbol: string;
  invested_amount: DecimalString;
  invested_currency: PortfolioCurrency;
  shares: DecimalString;
  purchase_date: IsoDate;
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
  holdings: PortfolioRealHoldingInput[];
};

type PortfolioHoldingResponseBase = {
  id: Uuid;
  symbol: string;
  position: number;
};

export type PortfolioLegacyHoldingResponse = PortfolioHoldingResponseBase & {
  weight: number;
  invested_amount: null;
  invested_currency: null;
  shares: null;
  purchase_date: null;
};

export type PortfolioRealHoldingResponse = PortfolioHoldingResponseBase & {
  weight: null;
  invested_amount: DecimalString;
  invested_currency: PortfolioCurrency;
  shares: DecimalString;
  purchase_date: IsoDate;
};

export type PortfolioHoldingResponse =
  | PortfolioLegacyHoldingResponse
  | PortfolioRealHoldingResponse;

export type PortfolioHoldingMode = 'empty' | 'legacy' | 'real' | 'mixed';

export function isLegacyPortfolioHolding(
  holding: PortfolioHoldingResponse
): holding is PortfolioLegacyHoldingResponse {
  return holding.weight !== null;
}

export function isRealPortfolioHolding(
  holding: PortfolioHoldingResponse
): holding is PortfolioRealHoldingResponse {
  return holding.weight === null;
}

export function portfolioHoldingMode(
  holdings: PortfolioHoldingResponse[]
): PortfolioHoldingMode {
  if (!holdings.length) return 'empty';
  const hasLegacy = holdings.some(isLegacyPortfolioHolding);
  const hasReal = holdings.some(isRealPortfolioHolding);
  if (hasLegacy && hasReal) return 'mixed';
  return hasReal ? 'real' : 'legacy';
}

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

export type PortfolioValuationFxResponse = {
  pair: 'USD/THB';
  provider_symbol: 'THB=X';
  rate: DecimalString;
  as_of: IsoDate;
};

export type PortfolioHoldingValuationResponse = {
  id: Uuid;
  symbol: string;
  invested_amount: DecimalString;
  invested_currency: PortfolioCurrency;
  shares: DecimalString;
  purchase_date: IsoDate;
  position: number;
  asset_price: DecimalString;
  asset_quote_currency: 'USD';
  price_as_of: IsoDate;
  current_value_usd: DecimalString;
  current_value: DecimalString;
  current_allocation: DecimalString;
};

export type PortfolioValuationResponse = {
  portfolio_id: Uuid;
  valuation_currency: PortfolioCurrency;
  requested_date: IsoDate;
  oldest_price_as_of: IsoDate;
  newest_price_as_of: IsoDate;
  total_current_value_usd: DecimalString;
  total_current_value: DecimalString;
  fx: PortfolioValuationFxResponse | null;
  holdings: PortfolioHoldingValuationResponse[];
};
