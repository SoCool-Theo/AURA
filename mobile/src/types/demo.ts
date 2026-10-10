/**
 * Temporary view models for the unmigrated local mobile demo.
 *
 * These are not FastAPI contracts and must never be used by production API
 * modules. Feature phases will remove them as each screen becomes API-backed.
 */
export type DemoAuraUser = {
  id: string;
  email: string;
  name: string;
};

export type DemoAuthResult = {
  accessToken: string;
  user: DemoAuraUser;
};

export type DemoHolding = {
  symbol: string;
  name: string;
  weight: number;
  value: number;
  risk: 'Low' | 'Medium' | 'High';
};

export type DemoPortfolio = {
  id: string;
  name: string;
  totalValue: number;
  riskScore: number;
  riskLevel: 'Low' | 'Moderate' | 'High';
  annualizedReturn: number;
  maxDrawdown: number;
  holdings: DemoHolding[];
};

export type DemoRiskDriver = {
  symbol: string;
  level: 'Low' | 'Medium' | 'High';
  explanation: string;
};

export type DemoPortfolioAnalysis = {
  riskScore: number;
  riskLevel: string;
  volatility: number;
  annualizedReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  diversification: string;
  topRiskDrivers: DemoRiskDriver[];
};

export type DemoReportSnapshot = {
  id: string;
  portfolioId: string;
  portfolioName: string;
  createdAt: string;
  analysis: DemoPortfolioAnalysis;
};

export type DemoSimulationMode =
  | 'Historical Scenario'
  | 'Allocation Change'
  | 'Combined';

export type DemoSimulationMetrics = {
  cumulativeReturn: number;
  annualizedVolatility: number;
  maxDrawdown: number;
  sharpeRatio: number | null;
  endingValue: number;
};

export type DemoSimulationRecord = {
  id: string;
  portfolioId: string;
  portfolioName: string;
  mode: DemoSimulationMode;
  title: string;
  createdAt: string;
  scenarioId?: string;
  original: DemoSimulationMetrics;
  modified?: DemoSimulationMetrics;
  comparison?: {
    returnDelta: number;
    volatilityDelta: number;
    drawdownDelta: number;
  };
};
