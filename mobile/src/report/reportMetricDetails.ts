import {
  formatPortfolioMoney,
  formatSignedPortfolioMoney
} from '../portfolio/portfolioFormatting';
import type { MetricAmountSheetContent } from '../components/analytics/MetricAmountSheet';
import { formatRatioPercent } from './reportFormatting';
import {
  isPortfolioReportV2,
  isPortfolioReportV3,
  type PortfolioReportAssetMonetaryMetrics,
  type PortfolioReportMonetaryMetrics,
  type PortfolioReportResponse
} from '../types/report';

export type ReportMonetaryMetricKey = 'endingValue' | 'cumulative' | 'annualized' | 'drawdown';

export function reportMonetaryMetrics(
  report: PortfolioReportResponse | null | undefined
): PortfolioReportMonetaryMetrics | null {
  if (!report || (!isPortfolioReportV2(report) && !isPortfolioReportV3(report))) {
    return null;
  }
  return report.monetary_metrics ?? null;
}

export function assetReportMonetaryMetrics(
  report: PortfolioReportResponse | null | undefined,
  symbol: string
): PortfolioReportAssetMonetaryMetrics | null {
  if (!report || (!isPortfolioReportV2(report) && !isPortfolioReportV3(report))) {
    return null;
  }
  return report.asset_monetary_metrics?.find(
    (metric) => metric.symbol === symbol
  ) ?? null;
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

  if (key === 'endingValue') {
    if (
      monetary.basis !== 'planned-proposed-amount'
      || monetary.estimated_ending_value == null
    ) return null;
    return {
      title: 'Estimated Value at End of Period',
      percentage: formatPortfolioMoney(monetary.estimated_ending_value, monetary.currency),
      amount: formatSignedPortfolioMoney(monetary.cumulative_return_amount, monetary.currency),
      amountLabel: 'Estimated change during this historical period',
      reference,
      explanation: `This shows how much the planned investment would have been worth at the end of the historical period from ${report.analysis.start_date} to ${report.analysis.end_date}. It is based on past performance and is not a prediction of future value.`,
      tone: metrics.cumulative_return < 0 ? 'danger' : 'success'
    };
  }

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

export function assetReportMetricAmountContent(
  key: ReportMonetaryMetricKey | null,
  report: PortfolioReportResponse | null | undefined,
  symbol: string
): MetricAmountSheetContent | null {
  const monetary = assetReportMonetaryMetrics(report, symbol);
  const asset = report?.analysis.asset_metrics.find(
    (metric) => metric.symbol === symbol
  );
  if (!key || !report || !monetary || !asset) return null;

  const reference = monetary.basis === 'planned-proposed-amount'
    ? `Based on the hypothetical ${formatPortfolioMoney(monetary.reference_amount, monetary.currency)} proposed for ${symbol} in this saved plan.`
    : `Based on the ${formatPortfolioMoney(monetary.reference_amount, monetary.currency)} current value saved for ${symbol} in this report.`;

  if (key === 'cumulative') {
    return {
      title: `${symbol} Cumulative Return`,
      percentage: formatRatioPercent(asset.cumulative_return),
      amount: formatSignedPortfolioMoney(monetary.cumulative_return_amount, monetary.currency),
      amountLabel: 'Estimated change over this analysis period',
      reference,
      explanation: `This applies ${symbol}'s historical cumulative return from ${report.analysis.start_date} to ${report.analysis.end_date} to its saved reference amount. It is not actual profit or a forecast.`,
      tone: asset.cumulative_return < 0 ? 'danger' : 'success'
    };
  }

  if (key === 'annualized') {
    return {
      title: `${symbol} Annualized Return`,
      percentage: formatRatioPercent(asset.annualized_return),
      amount: formatSignedPortfolioMoney(monetary.annualized_return_amount, monetary.currency),
      amountLabel: 'Estimated annual equivalent',
      reference,
      explanation: `This converts ${symbol}'s saved historical annualized rate into a one-year money equivalent. It is not guaranteed profit, actual account performance, or a forecast.`,
      tone: asset.annualized_return < 0 ? 'danger' : 'success'
    };
  }

  if (monetary.maximum_drawdown_amount === null) return null;
  return {
    title: `${symbol} Maximum Drawdown`,
    percentage: formatRatioPercent(asset.max_drawdown),
    amount: formatSignedPortfolioMoney(monetary.maximum_drawdown_amount, monetary.currency),
    amountLabel: 'Estimated peak-to-trough decline',
    reference,
    explanation: `This uses ${symbol}'s exact saved historical peak-to-trough return path. It is not a prediction of future loss.`,
    tone: 'danger'
  };
}
