import type { Portfolio } from '../types/portfolio';

export const portfoliosMock: Portfolio[] = [
  {
    id: 'tech-growth',
    name: 'Tech Growth',
    totalValue: 10000,
    riskScore: 72,
    riskLevel: 'Moderate',
    annualizedReturn: 15.34,
    maxDrawdown: -18.62,
    holdings: [
      { symbol: 'AAPL', name: 'Apple Inc.', weight: 30, value: 3000, risk: 'Medium' },
      { symbol: 'TSLA', name: 'Tesla Inc.', weight: 25, value: 2500, risk: 'High' },
      { symbol: 'NVDA', name: 'NVIDIA Corp.', weight: 20, value: 2000, risk: 'High' },
      { symbol: 'BND', name: 'Vanguard Total Bond', weight: 15, value: 1500, risk: 'Low' },
      { symbol: 'CASH', name: 'Cash Balance', weight: 10, value: 1000, risk: 'Low' }
    ]
  },
  {
    id: 'balanced',
    name: 'Balanced Core',
    totalValue: 24500,
    riskScore: 48,
    riskLevel: 'Moderate',
    annualizedReturn: 9.10,
    maxDrawdown: -10.30,
    holdings: [
      { symbol: 'VTI', name: 'Vanguard Total Stock Market', weight: 45, value: 11025, risk: 'Medium' },
      { symbol: 'BND', name: 'Vanguard Total Bond', weight: 35, value: 8575, risk: 'Low' },
      { symbol: 'GLD', name: 'SPDR Gold Shares', weight: 20, value: 4900, risk: 'Low' }
    ]
  }
];
