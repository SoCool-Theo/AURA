import type { ReportDetail, ReportSummary } from '../types/report';

export const reportsSeed: ReportSummary[] = [
  { id: 1, portfolioId: 'tech', name: 'Tech Portfolio Analysis', portfolio: 'Tech Portfolio', type: 'Analysis', date: 'May 11, 2026', riskScore: 72 },
  { id: 2, portfolioId: 'tech', name: '2008 Financial Crisis Simulation', portfolio: 'Tech Portfolio', type: 'Simulation', date: 'May 11, 2026', riskScore: null },
  { id: 3, portfolioId: 'tech', name: 'Allocation Change Simulation', portfolio: 'Tech Portfolio', type: 'Simulation', date: 'May 9, 2026', riskScore: null },
  { id: 4, portfolioId: 'balanced', name: 'Balanced Portfolio Analysis', portfolio: 'Balanced Portfolio', type: 'Analysis', date: 'May 7, 2026', riskScore: 48 },
  { id: 5, portfolioId: 'tech', name: 'Tech vs Balanced Comparison', portfolio: 'Recommended', type: 'Comparison', date: 'May 6, 2026', riskScore: null },
  { id: 6, portfolioId: 'retirement', name: 'Retirement Fund Analysis', portfolio: 'Retirement Fund', type: 'Analysis', date: 'May 5, 2026', riskScore: 32 },
];

const reportDetails: ReadonlyArray<ReportDetail> = [
  {
    id: 1,
    portfolioId: 'tech',
    title: 'Tech Portfolio Analysis',
    reportType: 'Portfolio Analysis',
    portfolioName: 'Tech Portfolio',
    createdAt: 'May 11, 2026 at 4:32 PM',
    analysisPeriod: 'Jan 21, 2021 – May 11, 2026',
    version: '1.0',
    status: 'Complete',
    riskScore: 72,
    riskLevel: 'High',
    summary: 'The portfolio delivered strong historical growth, but its risk remains concentrated in a small number of technology holdings. NVIDIA is the largest source of both return and portfolio-level volatility.',
    metrics: [
      { label: 'Total Portfolio Value', value: 18450, format: 'currency', detail: 'Saved market value', tone: 'teal', icon: 'wallet' },
      { label: 'Annualized Return', value: 12.45, format: 'percentage', detail: 'Historical annual rate', tone: 'teal', icon: 'trend' },
      { label: 'Annualized Volatility', value: 15.32, format: 'percentage', detail: 'Historical price variation', tone: 'amber', icon: 'analytics' },
      { label: 'Maximum Drawdown', value: -21.45, format: 'percentage', detail: 'Largest peak-to-trough decline', tone: 'red', icon: 'drawdown' },
      { label: 'Sharpe Ratio', value: 1.24, format: 'decimal', detail: 'Risk-adjusted return', tone: 'blue', icon: 'trend' },
      { label: 'Diversification Score', value: 56, format: 'score', detail: 'Moderate diversification', tone: 'amber', icon: 'shield' },
    ],
    performance: {
      periodLabel: 'ALL',
      startValue: 9850,
      endValue: 18450,
      periodReturn: 87.31,
      annualizedReturn: 12.45,
      values: [9850, 10240, 10110, 10880, 11270, 11140, 11860, 12320, 12100, 12890, 13340, 13620, 14280, 13920, 14650, 15110, 14960, 15740, 16320, 16080, 16940, 17430, 17810, 18450],
      labels: ['Jan 21', 'Nov 21', 'Sep 22', 'Jul 23', 'May 24', 'May 26'],
    },
    riskDrivers: [
      { rank: 1, symbol: 'NVDA', name: 'NVIDIA Corporation', weight: 57.1, riskContribution: 48.2, impactScore: 86, explanation: 'The portfolio is highly concentrated in NVIDIA, so changes in the stock have an outsized effect on total portfolio risk.' },
      { rank: 2, symbol: 'TSLA', name: 'Tesla, Inc.', weight: 14.4, riskContribution: 22.4, impactScore: 78, explanation: 'Tesla adds meaningful volatility and tends to amplify large movements in the equity allocation.' },
      { rank: 3, symbol: 'AAPL', name: 'Apple Inc.', weight: 10.4, riskContribution: 11.6, impactScore: 61, explanation: 'Apple increases technology-sector concentration, though its contribution is lower than the two largest drivers.' },
      { rank: 4, symbol: 'BND', name: 'Vanguard Total Bond Market ETF', weight: 15.4, riskContribution: 4.8, impactScore: 29, explanation: 'The bond allocation contributes relatively little risk and provides some balance against equity movements.' },
    ],
    assets: [
      { symbol: 'NVDA', name: 'NVIDIA Corporation', assetType: 'Equity', weight: 57.1, value: 10542.1, annualizedReturn: 28.42, annualizedVolatility: 31.8, maxDrawdown: -37.2, riskScore: 86 },
      { symbol: 'TSLA', name: 'Tesla, Inc.', assetType: 'Equity', weight: 14.4, value: 2662.1, annualizedReturn: 16.74, annualizedVolatility: 42.6, maxDrawdown: -48.3, riskScore: 78 },
      { symbol: 'AAPL', name: 'Apple Inc.', assetType: 'Equity', weight: 10.4, value: 1914.5, annualizedReturn: 18.15, annualizedVolatility: 24.1, maxDrawdown: -29.4, riskScore: 61 },
      { symbol: 'BND', name: 'Vanguard Total Bond Market ETF', assetType: 'Bond ETF', weight: 15.4, value: 2846.4, annualizedReturn: 2.36, annualizedVolatility: 6.7, maxDrawdown: -12.1, riskScore: 29 },
      { symbol: 'CASH', name: 'Cash', assetType: 'Cash', weight: 2.7, value: 484.9, annualizedReturn: 0, annualizedVolatility: 0, maxDrawdown: 0, riskScore: 4 },
    ],
    correlation: {
      symbols: ['NVDA', 'TSLA', 'AAPL', 'BND'],
      matrix: [
        [{ value: 1, tone: 'self' }, { value: 0.54, tone: 'positive-medium' }, { value: 0.68, tone: 'positive-strong' }, { value: -0.08, tone: 'negative-weak' }],
        [{ value: 0.54, tone: 'positive-medium' }, { value: 1, tone: 'self' }, { value: 0.47, tone: 'positive-medium' }, { value: -0.12, tone: 'negative-weak' }],
        [{ value: 0.68, tone: 'positive-strong' }, { value: 0.47, tone: 'positive-medium' }, { value: 1, tone: 'self' }, { value: 0.03, tone: 'positive-weak' }],
        [{ value: -0.08, tone: 'negative-weak' }, { value: -0.12, tone: 'negative-weak' }, { value: 0.03, tone: 'positive-weak' }, { value: 1, tone: 'self' }],
      ],
      averageCorrelation: 0.32,
      note: 'The three equity holdings move together more often than the bond allocation. This reduces the diversification benefit inside the equity portion of the portfolio.',
    },
  },
];

export async function loadReportDetailSnapshot(
  portfolioId: string,
  reportId: string,
): Promise<ReportDetail | null> {
  await new Promise(resolve => setTimeout(resolve, 180));

  return reportDetails.find(report => (
    report.portfolioId === portfolioId && String(report.id) === reportId
  )) ?? null;
}
