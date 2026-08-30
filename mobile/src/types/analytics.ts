export type RiskDriver = { symbol: string; level: 'Low' | 'Medium' | 'High'; explanation: string };
export type PortfolioAnalysis = {
  riskScore: number;
  riskLevel: string;
  volatility: number;
  annualizedReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  diversification: string;
  topRiskDrivers: RiskDriver[];
};
