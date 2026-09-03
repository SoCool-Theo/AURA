import type { PortfolioHoldingInput } from '../types/portfolio';

export type HoldingDraft = {
  id: string;
  symbol: string;
  weightPercent: string;
};

export type HoldingValidationResult =
  | { holdings: PortfolioHoldingInput[]; error: null }
  | { holdings: null; error: string };

export function createHoldingDraft(
  symbol = '',
  weightPercent = ''
): HoldingDraft {
  return {
    id: `${Date.now()}-${Math.random()}`,
    symbol,
    weightPercent
  };
}

export function decimalWeightToPercent(weight: number): number {
  return weight * 100;
}

export function decimalWeightToInput(weight: number): string {
  return String(Number(decimalWeightToPercent(weight).toFixed(10)));
}

export function validateHoldingDrafts(
  drafts: HoldingDraft[]
): HoldingValidationResult {
  if (!drafts.length) {
    return { holdings: null, error: 'Add at least one holding.' };
  }

  const holdings: PortfolioHoldingInput[] = [];
  const seenSymbols = new Set<string>();
  let totalPercent = 0;

  for (let index = 0; index < drafts.length; index += 1) {
    const draft = drafts[index];
    const symbol = draft.symbol.trim().toUpperCase();
    if (!symbol) {
      return {
        holdings: null,
        error: `Holding ${index + 1} needs a symbol.`
      };
    }
    if (seenSymbols.has(symbol)) {
      return {
        holdings: null,
        error: `${symbol} appears more than once. Holding symbols must be unique.`
      };
    }

    const rawPercent = draft.weightPercent.trim();
    const weightPercent = Number(rawPercent);
    if (
      !rawPercent
      || !Number.isFinite(weightPercent)
      || weightPercent < 0
      || weightPercent > 100
    ) {
      return {
        holdings: null,
        error: `${symbol} needs a weight from 0% through 100%.`
      };
    }

    seenSymbols.add(symbol);
    totalPercent += weightPercent;
    holdings.push({ symbol, weight: weightPercent / 100 });
  }

  if (Math.abs(totalPercent - 100) > 1e-7) {
    return {
      holdings: null,
      error: `Total allocation must equal 100%. Current total: ${totalPercent.toFixed(2)}%.`
    };
  }

  return { holdings, error: null };
}
