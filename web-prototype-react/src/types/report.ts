export type ReportSummary = {
  id: number;
  portfolioId: string;
  name: string;
  portfolio: string;
  type: 'Analysis' | 'Simulation' | 'Comparison';
  date: string;
  riskScore: number | null;
};

export type ReportRiskLevel = 'Low' | 'Moderate' | 'High';

export type ReportMetric = {
  label: string;
  value: number;
  format: 'currency' | 'percentage' | 'decimal' | 'score';
  detail: string;
  tone: 'teal' | 'amber' | 'red' | 'blue';
  icon: string;
};

export type ReportPerformanceSnapshot = {
  periodLabel: string;
  startValue: number;
  endValue: number;
  periodReturn: number;
  annualizedReturn: number;
  values: ReadonlyArray<number>;
  labels: ReadonlyArray<string>;
};

export type ReportRiskDriver = {
  rank: number;
  symbol: string;
  name: string;
  weight: number;
  riskContribution: number;
  impactScore: number;
  explanation: string;
};

export type ReportAssetDetail = {
  symbol: string;
  name: string;
  assetType: string;
  weight: number;
  value: number;
  annualizedReturn: number;
  annualizedVolatility: number;
  maxDrawdown: number;
  riskScore: number;
};

export type CorrelationTone =
  | 'self'
  | 'positive-strong'
  | 'positive-medium'
  | 'positive-weak'
  | 'negative-weak';

export type ReportCorrelationCell = {
  value: number;
  tone: CorrelationTone;
};

export type ReportCorrelationSnapshot = {
  symbols: ReadonlyArray<string>;
  matrix: ReadonlyArray<ReadonlyArray<ReportCorrelationCell>>;
  averageCorrelation: number;
  note: string;
};

export type ReportDetail = {
  id: number;
  portfolioId: string;
  title: string;
  reportType: 'Portfolio Analysis';
  portfolioName: string;
  createdAt: string;
  analysisPeriod: string;
  version: string;
  status: 'Complete';
  riskScore: number;
  riskLevel: ReportRiskLevel;
  summary: string;
  metrics: ReadonlyArray<ReportMetric>;
  performance: ReportPerformanceSnapshot;
  riskDrivers: ReadonlyArray<ReportRiskDriver>;
  assets: ReadonlyArray<ReportAssetDetail>;
  correlation: ReportCorrelationSnapshot;
};
