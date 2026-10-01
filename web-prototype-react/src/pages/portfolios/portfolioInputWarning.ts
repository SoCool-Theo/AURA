import { apiValidationIssues } from '../../api/apiErrorPresentation';
import type { HoldingValidationIssue } from './portfolioValidation';

export type PortfolioInputWarning = {
  elementId: string;
  message: string;
};

type HoldingInputIds = {
  emptyHoldings: string;
  rows: Array<{
    proposedAmount: string;
    shares: string;
    symbol: string;
  }>;
};

export function localHoldingInputWarning(
  issue: HoldingValidationIssue,
  ids: HoldingInputIds,
): PortfolioInputWarning {
  if (issue.index === null || issue.field === 'holdings') {
    return { elementId: ids.emptyHoldings, message: issue.message };
  }
  return {
    elementId: ids.rows[issue.index]?.[issue.field] ?? ids.emptyHoldings,
    message: issue.message,
  };
}

export function apiPortfolioInputWarning(
  error: unknown,
  ids: HoldingInputIds & { name?: string },
): PortfolioInputWarning | null {
  const issue = apiValidationIssues(error)[0];
  if (!issue) return null;
  if (ids.name && issue.path.endsWith('name')) {
    return { elementId: ids.name, message: issue.message };
  }

  const match = /holdings\.(\d+)\.(symbol|shares|proposed_amount)$/.exec(
    issue.path,
  );
  if (!match) return null;
  const row = ids.rows[Number(match[1])];
  if (!row) return null;
  const field = match[2] === 'proposed_amount' ? 'proposedAmount' : match[2];
  return {
    elementId: row[field as 'symbol' | 'shares' | 'proposedAmount'],
    message: issue.message,
  };
}

export function showPortfolioInputWarning(
  warning: PortfolioInputWarning,
): void {
  window.setTimeout(() => {
    const element = document.getElementById(warning.elementId);
    if (!(element instanceof HTMLElement)) return;
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    element.focus({ preventScroll: true });
  }, 0);
}
