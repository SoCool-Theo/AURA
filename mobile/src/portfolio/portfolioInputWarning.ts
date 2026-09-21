import { apiValidationIssues } from '../api/apiErrorPresentation';
import type { HoldingValidationIssue } from './portfolioValidation';

export type PortfolioInputWarning = {
  fieldKey: string;
  message: string;
};

type HoldingFieldKeys = {
  emptyHoldings: string;
  rows: Array<{
    proposedAmount: string;
    shares: string;
    symbol: string;
  }>;
};

export function localHoldingInputWarning(
  issue: HoldingValidationIssue,
  keys: HoldingFieldKeys
): PortfolioInputWarning {
  if (issue.index === null || issue.field === 'holdings') {
    return { fieldKey: keys.emptyHoldings, message: issue.message };
  }
  return {
    fieldKey: keys.rows[issue.index]?.[issue.field] ?? keys.emptyHoldings,
    message: issue.message
  };
}

export function apiPortfolioInputWarning(
  error: unknown,
  keys: HoldingFieldKeys & { name?: string }
): PortfolioInputWarning | null {
  const issue = apiValidationIssues(error)[0];
  if (!issue) return null;
  if (keys.name && issue.path.endsWith('name')) {
    return { fieldKey: keys.name, message: issue.message };
  }

  const match = /holdings\.(\d+)\.(symbol|shares|proposed_amount)$/.exec(
    issue.path
  );
  if (!match) return null;
  const row = keys.rows[Number(match[1])];
  if (!row) return null;
  const field = match[2] === 'proposed_amount' ? 'proposedAmount' : match[2];
  return {
    fieldKey: row[field as 'symbol' | 'shares' | 'proposedAmount'],
    message: issue.message
  };
}

export function showPortfolioInputWarning(
  warning: PortfolioInputWarning,
  revealField: (fieldKey: string) => void
): void {
  setTimeout(() => revealField(warning.fieldKey), 120);
}
