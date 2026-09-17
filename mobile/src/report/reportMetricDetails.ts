import {
  formatPortfolioMoney,
  formatSignedPortfolioMoney
} from '../portfolio/portfolioFormatting';
import type { MetricAmountSheetContent } from '../components/analytics/MetricAmountSheet';
import { formatRatioPercent } from './reportFormatting';
import {
  isPortfolioReportV2,
  isPortfolioReportV3,
  type PortfolioReportMonetaryMetrics,
  type PortfolioReportResponse
} from '../types/report';

export type ReportMonetaryMetricKey = 'cumulative' | 'annualized' | 'drawdown';

export function reportMonetaryMetrics(
  report: PortfolioReportResponse | null | undefined
): PortfolioReportMonetaryMetrics | null {
  if (!report || (!isPortfolioReportV2(report) && !isPortfolioReportV3(report))) {
    return null;
  }
  return report.monetary_metrics ?? null;
}

export function reportMetricAmountContent(
  key: ReportMonetaryMetricKey | null,
  report: PortfolioReportResponse | null | undefined
): MetricAmountSheetContent | null {
  const monetary = reportMonetaryMetrics(report);
  if (!key || !report || !monetary) return null;

  const metrics = report.analysis.portfolio_metrics;
  const drawdown = report.analysis.max_drawdown;
  const reference = monetary.basis === 'planned-proposed-amount'
    ? `Based on your hypothetical ${formatPortfolioMoney(monetary.reference_amount, monetary.currency)} planned investment.`
    : `Based on the ${formatPortfolioMoney(monetary.reference_amount, monetary.currency)} portfolio valuation saved with this report.`;

  if (key === 'cumulative') {
    return {
      title: 'Cumulative Return',
      percentage: formatRatioPercent(metrics.cumulative_return),
      amount: formatSignedPortfolioMoney(monetary.cumulative_return_amount, monetary.currency),
      amountLabel: 'Estimated change over this analysis period',
      reference,
      explanation: `This applies the historical cumulative return from ${report.analysis.start_date} to ${report.analysis.end_date} to the saved reference amount. It is not actual profit or a forecast.`,
      tone: metrics.cumulative_return < 0 ? 'danger' : 'success'
    };
  }

  if (key === 'annualized') {
    return {
      title: 'Annualized Return',
      percentage: formatRatioPercent(metrics.annualized_return),
      amount: formatSignedPortfolioMoney(monetary.annualized_return_amount, monetary.currency),
      amountLabel: 'Estimated annual equivalent',
      reference,
      explanation: 'This converts the historical annualized rate into a one-year money equivalent. It is not guaranteed profit, actual account performance, or a forecast.',
      tone: metrics.annualized_return < 0 ? 'danger' : 'success'
    };
  }

  if (monetary.maximum_drawdown_amount === null) return null;
  const period = drawdown.peak_date && drawdown.trough_date
    ? ` from ${drawdown.peak_date} to ${drawdown.trough_date}`
    : '';
  return {
    title: 'Maximum Drawdown',
    percentage: formatRatioPercent(drawdown.max_drawdown),
    amount: formatSignedPortfolioMoney(monetary.maximum_drawdown_amount, monetary.currency),
    amountLabel: 'Estimated peak-to-trough decline',
    reference,
    explanation: `This is the money equivalent of the same largest historical decline${period}. It is not a prediction of future loss.`,
    tone: 'danger'
  };
}
