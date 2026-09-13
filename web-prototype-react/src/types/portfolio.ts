import type { IsoDate, IsoDateTime, Uuid } from './api';

export type PortfolioCurrency = 'USD' | 'THB';
export type PortfolioType = 'CURRENT' | 'PLANNED' | 'LEGACY';

/** Decimal values are serialized as strings to preserve backend precision. */
export type DecimalString = string;

// Percentage allocation input remains valid for simulations and legacy
// compatibility. Current and planned portfolio CRUD use the typed inputs below.
export type PortfolioHoldingInput = {
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

export type PortfolioPlannedHoldingInput = {
  symbol: string;
  proposed_amount: DecimalString;
};

export type PortfolioCreateRequest =
  | {
    name: string;
    portfolio_type?: 'CURRENT';
    plan_currency?: never;
  }
  | {
    name: string;
    portfolio_type: 'PLANNED';
    plan_currency: PortfolioCurrency;
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

export type PortfolioPlannedHoldingsReplaceRequest = {
  holdings: PortfolioPlannedHoldingInput[];
};

// Kept only while the existing legacy percentage editor is migrated in place.
export type PortfolioLegacyHoldingsReplaceRequest = {
  holdings: PortfolioHoldingInput[];
};

type PortfolioHoldingResponseBase = {
  id: Uuid;
  symbol: string;
  position: number;
};

export type PortfolioLegacyHoldingResponse = PortfolioHoldingResponseBase & {
  weight: number;
  invested_amount: null;
  proposed_amount: null;
  invested_currency: null;
  shares: null;
  purchase_date: null;
};

export type PortfolioRealHoldingResponse = PortfolioHoldingResponseBase & {
  weight: null;
  invested_amount: DecimalString;
  proposed_amount: null;
  invested_currency: PortfolioCurrency;
  shares: DecimalString;
  purchase_date: IsoDate;
};

export type PortfolioPlannedHoldingResponse = PortfolioHoldingResponseBase & {
  weight: null;
  invested_amount: null;
  proposed_amount: DecimalString;
  invested_currency: null;
  shares: null;
  purchase_date: null;
};

export type PortfolioHoldingResponse =
  | PortfolioLegacyHoldingResponse
  | PortfolioRealHoldingResponse
  | PortfolioPlannedHoldingResponse;

export type PortfolioHoldingMode =
  | 'empty'
  | 'legacy'
  | 'real'
  | 'planned'
  | 'mixed';

export function isLegacyPortfolioHolding(
  holding: PortfolioHoldingResponse,
): holding is PortfolioLegacyHoldingResponse {
  return holding.weight != null;
}

export function isRealPortfolioHolding(
  holding: PortfolioHoldingResponse,
): holding is PortfolioRealHoldingResponse {
  return holding.invested_amount != null;
}

export function isPlannedPortfolioHolding(
  holding: PortfolioHoldingResponse,
): holding is PortfolioPlannedHoldingResponse {
  return holding.proposed_amount != null;
}

export function portfolioHoldingMode(
  holdings: PortfolioHoldingResponse[],
): PortfolioHoldingMode {
  if (!holdings.length) return 'empty';

  const modes = new Set(holdings.map((holding) => (
    isLegacyPortfolioHolding(holding)
      ? 'legacy'
      : isRealPortfolioHolding(holding)
        ? 'real'
        : isPlannedPortfolioHolding(holding)
          ? 'planned'
          : 'mixed'
  )));

  if (modes.size !== 1 || modes.has('mixed')) return 'mixed';
  return modes.values().next().value as Exclude<PortfolioHoldingMode, 'empty' | 'mixed'>;
}

export type PortfolioResponse = {
  id: Uuid;
  name: string;
  portfolio_type: PortfolioType;
  plan_currency: PortfolioCurrency | null;
  source_plan_id: Uuid | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  holdings: PortfolioHoldingResponse[];
};

export type PortfolioSummaryResponse = {
  id: Uuid;
  name: string;
  portfolio_type: PortfolioType;
  plan_currency: PortfolioCurrency | null;
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

export type PortfolioPlannedAllocationHoldingResponse = {
  id: Uuid;
  symbol: string;
  proposed_amount: DecimalString;
  target_allocation: DecimalString;
  position: number;
};

export type PortfolioPlannedAllocationResponse = {
  portfolio_id: Uuid;
  portfolio_type: 'PLANNED';
  plan_currency: PortfolioCurrency;
  total_proposed_amount: DecimalString;
  holdings: PortfolioPlannedAllocationHoldingResponse[];
};

export type PlannedEstimateStatus =
  | 'AVAILABLE'
  | 'PRICE_UNAVAILABLE'
  | 'FX_UNAVAILABLE';

export type PortfolioPlannedPreviewHoldingResponse =
  PortfolioPlannedAllocationHoldingResponse & {
    estimate_status: PlannedEstimateStatus;
    estimated_shares: DecimalString | null;
    asset_price: DecimalString | null;
    asset_quote_currency: 'USD' | null;
    price_as_of: IsoDate | null;
  };

export type PortfolioPlannedPreviewResponse = {
  portfolio_id: Uuid;
  portfolio_type: 'PLANNED';
  plan_currency: PortfolioCurrency;
  requested_date: IsoDate;
  total_proposed_amount: DecimalString;
  fx: PortfolioValuationFxResponse | null;
  holdings: PortfolioPlannedPreviewHoldingResponse[];
};

export type PlannedPortfolioBaselineContext = {
  portfolio_type: 'PLANNED';
  baseline_source: 'proposed-amount-target-allocation';
  plan_currency: PortfolioCurrency;
  total_proposed_amount: DecimalString;
  hypothetical_notice: string;
  holdings: PortfolioPlannedAllocationHoldingResponse[];
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
