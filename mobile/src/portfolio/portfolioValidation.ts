import type {
  PortfolioPlannedHoldingInput,
  PortfolioPlannedHoldingResponse,
  PortfolioRealHoldingInput,
  PortfolioRealHoldingResponse
} from '../types/portfolio';

export type RealHoldingDraft = {
  id: string;
  symbol: string;
  shares: string;
};

export type HoldingValidationIssue = {
  index: number | null;
  field: 'holdings' | 'symbol' | 'shares' | 'proposedAmount';
  message: string;
};

export type RealHoldingValidationResult =
  | { holdings: PortfolioRealHoldingInput[]; error: null; issue: null }
  | { holdings: null; error: string; issue: HoldingValidationIssue };

export type PlannedHoldingDraft = {
  id: string;
  symbol: string;
  proposedAmount: string;
};

export type PlannedHoldingValidationResult =
  | { holdings: PortfolioPlannedHoldingInput[]; error: null; issue: null }
  | { holdings: null; error: string; issue: HoldingValidationIssue };

function invalidHolding(
  message: string,
  field: HoldingValidationIssue['field'],
  index: number | null
): { holdings: null; error: string; issue: HoldingValidationIssue } {
  return { holdings: null, error: message, issue: { field, index, message } };
}

function draftId(): string {
  return `${Date.now()}-${Math.random()}`;
}

export function createRealHoldingDraft(
  values: Partial<Omit<RealHoldingDraft, 'id'>> = {}
): RealHoldingDraft {
  return {
    id: draftId(),
    symbol: values.symbol ?? '',
    shares: values.shares ?? ''
  };
}

export function realHoldingToDraft(
  holding: PortfolioRealHoldingResponse
): RealHoldingDraft {
  return createRealHoldingDraft({
    symbol: holding.symbol,
    shares: holding.shares
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

export function validateRealHoldingDrafts(
  drafts: RealHoldingDraft[]
): RealHoldingValidationResult {
  if (!drafts.length) {
    return invalidHolding('Add at least one holding.', 'holdings', null);
  }

  const holdings: PortfolioRealHoldingInput[] = [];
  const seenSymbols = new Set<string>();

  for (let index = 0; index < drafts.length; index += 1) {
    const draft = drafts[index];
    const symbol = draft.symbol.trim().toUpperCase();
    if (!symbol) {
      return invalidHolding(
        `Holding ${index + 1} needs a symbol.`,
        'symbol',
        index
      );
    }
    if (seenSymbols.has(symbol)) {
      return invalidHolding(
        `${symbol} appears more than once. Holding symbols must be unique.`,
        'symbol',
        index
      );
    }

    const shares = positiveDecimal(draft.shares);
    if (!shares) {
      return invalidHolding(
        `${symbol} needs a positive quantity owned with up to 12 decimal places.`,
        'shares',
        index
      );
    }

    seenSymbols.add(symbol);
    holdings.push({ symbol, shares });
  }

  return { holdings, error: null, issue: null };
}

export function validatePlannedHoldingDrafts(
  drafts: PlannedHoldingDraft[]
): PlannedHoldingValidationResult {
  if (!drafts.length) {
    return invalidHolding(
      'Add at least one planned holding.',
      'holdings',
      null
    );
  }

  const holdings: PortfolioPlannedHoldingInput[] = [];
  const seenSymbols = new Set<string>();
  for (let index = 0; index < drafts.length; index += 1) {
    const draft = drafts[index];
    const symbol = draft.symbol.trim().toUpperCase();
    if (!symbol) {
      return invalidHolding(
        `Holding ${index + 1} needs a symbol.`,
        'symbol',
        index
      );
    }
    if (seenSymbols.has(symbol)) {
      return invalidHolding(
        `${symbol} appears more than once. Holding symbols must be unique.`,
        'symbol',
        index
      );
    }
    const proposedAmount = positiveDecimal(draft.proposedAmount);
    if (!proposedAmount) {
      return invalidHolding(
        `${symbol} needs a positive proposed amount with up to 12 decimal places.`,
        'proposedAmount',
        index
      );
    }
    seenSymbols.add(symbol);
    holdings.push({ symbol, proposed_amount: proposedAmount });
  }
  return { holdings, error: null, issue: null };
}

export function decimalWeightToPercent(weight: number): number {
  return weight * 100;
}
