import type {
  PortfolioCurrency,
  PortfolioPlannedHoldingResponse,
  PortfolioPlannedHoldingInput,
  PortfolioRealHoldingResponse,
  PortfolioRealHoldingInput,
} from '../../types/portfolio';

export type RealHoldingDraft = {
  id: number;
  symbol: string;
  shares: string;
};

export type PlannedHoldingDraft = {
  id: number;
  symbol: string;
  proposedAmount: string;
};

export type HoldingValidationIssue = {
  index: number | null;
  field: 'holdings' | 'symbol' | 'shares' | 'proposedAmount';
  message: string;
};

export type HoldingValidationResult<T> =
  | { holdings: T[]; error: null; issue: null }
  | { holdings: null; error: string; issue: HoldingValidationIssue };

function invalidHolding(
  message: string,
  field: HoldingValidationIssue['field'],
  index: number | null,
): { holdings: null; error: string; issue: HoldingValidationIssue } {
  return { holdings: null, error: message, issue: { field, index, message } };
}

export function createRealHoldingDraft(id: number): RealHoldingDraft {
  return {
    id,
    symbol: '',
    shares: '',
  };
}

export function createPlannedHoldingDraft(id: number): PlannedHoldingDraft {
  return {
    id,
    symbol: '',
    proposedAmount: '',
  };
}

export function realHoldingToDraft(
  id: number,
  holding: PortfolioRealHoldingResponse,
): RealHoldingDraft {
  return {
    id,
    symbol: holding.symbol,
    shares: holding.shares,
  };
}

export function plannedHoldingToDraft(
  id: number,
  holding: PortfolioPlannedHoldingResponse,
): PlannedHoldingDraft {
  return {
    id,
    symbol: holding.symbol,
    proposedAmount: holding.proposed_amount,
  };
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

function normalizedUniqueSymbol(
  value: string,
  index: number,
  seenSymbols: Set<string>,
): { symbol: string; error: null } | { symbol: null; error: string } {
  const symbol = value.trim().toUpperCase();
  if (!symbol) {
    return { symbol: null, error: `Holding ${index + 1} needs a symbol.` };
  }
  if (seenSymbols.has(symbol)) {
    return {
      symbol: null,
      error: `${symbol} appears more than once. Holding symbols must be unique.`,
    };
  }
  seenSymbols.add(symbol);
  return { symbol, error: null };
}

export function validateRealHoldingDrafts(
  drafts: RealHoldingDraft[],
): HoldingValidationResult<PortfolioRealHoldingInput> {
  if (!drafts.length) {
    return invalidHolding('Add at least one holding.', 'holdings', null);
  }

  const holdings: PortfolioRealHoldingInput[] = [];
  const seenSymbols = new Set<string>();
  for (let index = 0; index < drafts.length; index += 1) {
    const draft = drafts[index];
    const normalizedSymbol = normalizedUniqueSymbol(draft.symbol, index, seenSymbols);
    if (!normalizedSymbol.symbol) {
      return invalidHolding(
        normalizedSymbol.error ?? `Holding ${index + 1} needs a symbol.`,
        'symbol',
        index,
      );
    }

    const shares = positiveDecimal(draft.shares);
    if (!shares) {
      return invalidHolding(
        `${normalizedSymbol.symbol} needs a positive quantity owned with up to 12 decimal places.`,
        'shares',
        index,
      );
    }

    holdings.push({
      symbol: normalizedSymbol.symbol,
      shares,
    });
  }

  return { holdings, error: null, issue: null };
}

export function validatePlannedHoldingDrafts(
  drafts: PlannedHoldingDraft[],
): HoldingValidationResult<PortfolioPlannedHoldingInput> {
  if (!drafts.length) {
    return invalidHolding(
      'Add at least one planned holding.',
      'holdings',
      null,
    );
  }

  const holdings: PortfolioPlannedHoldingInput[] = [];
  const seenSymbols = new Set<string>();
  for (let index = 0; index < drafts.length; index += 1) {
    const draft = drafts[index];
    const normalizedSymbol = normalizedUniqueSymbol(draft.symbol, index, seenSymbols);
    if (!normalizedSymbol.symbol) {
      return invalidHolding(
        normalizedSymbol.error ?? `Holding ${index + 1} needs a symbol.`,
        'symbol',
        index,
      );
    }

    const proposedAmount = positiveDecimal(draft.proposedAmount);
    if (!proposedAmount) {
      return invalidHolding(
        `${normalizedSymbol.symbol} needs a positive proposed amount with up to 12 decimal places.`,
        'proposedAmount',
        index,
      );
    }

    holdings.push({
      symbol: normalizedSymbol.symbol,
      proposed_amount: proposedAmount,
    });
  }

  return { holdings, error: null, issue: null };
}
