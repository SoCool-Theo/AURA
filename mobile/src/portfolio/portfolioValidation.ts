import type {
  PortfolioCurrency,
  PortfolioPlannedHoldingInput,
  PortfolioPlannedHoldingResponse,
  PortfolioRealHoldingInput,
  PortfolioRealHoldingResponse
} from '../types/portfolio';

export type RealHoldingDraft = {
  id: string;
  symbol: string;
  investedAmount: string;
  investedCurrency: PortfolioCurrency;
  shares: string;
  purchaseDate: string;
};

export type RealHoldingValidationResult =
  | { holdings: PortfolioRealHoldingInput[]; error: null }
  | { holdings: null; error: string };

export type PlannedHoldingDraft = {
  id: string;
  symbol: string;
  proposedAmount: string;
};

export type PlannedHoldingValidationResult =
  | { holdings: PortfolioPlannedHoldingInput[]; error: null }
  | { holdings: null; error: string };

function draftId(): string {
  return `${Date.now()}-${Math.random()}`;
}

export function createRealHoldingDraft(
  values: Partial<Omit<RealHoldingDraft, 'id'>> = {}
): RealHoldingDraft {
  return {
    id: draftId(),
    symbol: values.symbol ?? '',
    investedAmount: values.investedAmount ?? '',
    investedCurrency: values.investedCurrency ?? 'USD',
    shares: values.shares ?? '',
    purchaseDate: values.purchaseDate ?? ''
  };
}

export function realHoldingToDraft(
  holding: PortfolioRealHoldingResponse
): RealHoldingDraft {
  return createRealHoldingDraft({
    symbol: holding.symbol,
    investedAmount: holding.invested_amount,
    investedCurrency: holding.invested_currency,
    shares: holding.shares,
    purchaseDate: holding.purchase_date
  });
}

export function createPlannedHoldingDraft(
  values: Partial<Omit<PlannedHoldingDraft, 'id'>> = {}
): PlannedHoldingDraft {
  return {
    id: draftId(),
    symbol: values.symbol ?? '',
    proposedAmount: values.proposedAmount ?? ''
  };
}

export function plannedHoldingToDraft(
  holding: PortfolioPlannedHoldingResponse
): PlannedHoldingDraft {
  return createPlannedHoldingDraft({
    symbol: holding.symbol,
    proposedAmount: holding.proposed_amount
  });
}

function positiveDecimal(value: string): string | null {
  const normalized = value.trim();
  const match = /^(\d+)(?:\.(\d+))?$/.exec(normalized);
  if (!match || !/[1-9]/.test(normalized)) return null;

  const integerDigits = match[1].replace(/^0+/, '').length || 1;
  const decimalDigits = match[2]?.length ?? 0;
  if (integerDigits > 16 || decimalDigits > 12) return null;
  return normalized;
}

function isValidPurchaseDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  if (
    parsed.getUTCFullYear() !== year
    || parsed.getUTCMonth() !== month - 1
    || parsed.getUTCDate() !== day
  ) {
    return false;
  }

  const now = new Date();
  const today = Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate()
  );
  return parsed.getTime() <= today;
}

export function validateRealHoldingDrafts(
  drafts: RealHoldingDraft[]
): RealHoldingValidationResult {
  if (!drafts.length) {
    return { holdings: null, error: 'Add at least one holding.' };
  }

  const holdings: PortfolioRealHoldingInput[] = [];
  const seenSymbols = new Set<string>();

  for (let index = 0; index < drafts.length; index += 1) {
    const draft = drafts[index];
    const symbol = draft.symbol.trim().toUpperCase();
    if (!symbol) {
      return { holdings: null, error: `Holding ${index + 1} needs a symbol.` };
    }
    if (seenSymbols.has(symbol)) {
      return {
        holdings: null,
        error: `${symbol} appears more than once. Holding symbols must be unique.`
      };
    }

    const investedAmount = positiveDecimal(draft.investedAmount);
    if (!investedAmount) {
      return {
        holdings: null,
        error: `${symbol} needs a positive invested amount with up to 12 decimal places.`
      };
    }

    if (draft.investedCurrency !== 'USD' && draft.investedCurrency !== 'THB') {
      return {
        holdings: null,
        error: `${symbol} needs an invested currency of USD or THB.`
      };
    }

    const shares = positiveDecimal(draft.shares);
    if (!shares) {
      return {
        holdings: null,
        error: `${symbol} needs positive shares with up to 12 decimal places.`
      };
    }

    const purchaseDate = draft.purchaseDate.trim();
    if (!isValidPurchaseDate(purchaseDate)) {
      return {
        holdings: null,
        error: `${symbol} needs a valid purchase date that is not in the future.`
      };
    }

    seenSymbols.add(symbol);
    holdings.push({
      symbol,
      invested_amount: investedAmount,
      invested_currency: draft.investedCurrency,
      shares,
      purchase_date: purchaseDate
    });
  }

  return { holdings, error: null };
}

export function validatePlannedHoldingDrafts(
  drafts: PlannedHoldingDraft[]
): PlannedHoldingValidationResult {
  if (!drafts.length) {
    return { holdings: null, error: 'Add at least one planned holding.' };
  }

  const holdings: PortfolioPlannedHoldingInput[] = [];
  const seenSymbols = new Set<string>();
  for (let index = 0; index < drafts.length; index += 1) {
    const draft = drafts[index];
    const symbol = draft.symbol.trim().toUpperCase();
    if (!symbol) {
      return { holdings: null, error: `Holding ${index + 1} needs a symbol.` };
    }
    if (seenSymbols.has(symbol)) {
      return { holdings: null, error: `${symbol} appears more than once. Holding symbols must be unique.` };
    }
    const proposedAmount = positiveDecimal(draft.proposedAmount);
    if (!proposedAmount) {
      return { holdings: null, error: `${symbol} needs a positive proposed amount with up to 12 decimal places.` };
    }
    seenSymbols.add(symbol);
    holdings.push({ symbol, proposed_amount: proposedAmount });
  }
  return { holdings, error: null };
}

export function decimalWeightToPercent(weight: number): number {
  return weight * 100;
}
