import type { DemoPortfolioAnalysis as PortfolioAnalysis } from '../types/demo';

export const analyticsMock: PortfolioAnalysis = {
  riskScore: 72,
  riskLevel: 'Moderate Risk',
  volatility: 12.45,
  annualizedReturn: 15.34,
  maxDrawdown: -18.62,
  sharpeRatio: 1.28,
  diversification: 'Weak',
  topRiskDrivers: [
    { symbol: 'TSLA', level: 'High', explanation: 'High volatility and a large portfolio weight.' },
    { symbol: 'NVDA', level: 'High', explanation: 'Concentrated technology exposure increases portfolio sensitivity.' },
    { symbol: 'AAPL', level: 'Medium', explanation: 'Large portfolio weight contributes meaningfully to total risk.' }
  ]
};
