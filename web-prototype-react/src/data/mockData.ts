export const defaultPortfolios = [
  {
    id: 'tech',
    name: 'Tech Portfolio',
    created: '2026-05-11',
    value: 18450,
    totalReturn: 12.45,
    riskScore: 72,
    riskLevel: 'Moderate Risk',
    cash: 0,
    holdings: [
      { symbol: 'NVDA', name: 'NVIDIA Corporation', type: 'Equity', weight: 57.1, value: 10542.1, dailyChange: 2.61, price: 181.63, shares: 58 },
      { symbol: 'TSLA', name: 'Tesla, Inc.', type: 'Equity', weight: 14.4, value: 2662.1, dailyChange: -1.12, price: 177.74, shares: 15 },
      { symbol: 'AAPL', name: 'Apple Inc.', type: 'Equity', weight: 10.4, value: 1914.5, dailyChange: 0.68, price: 191.45, shares: 10 },
      { symbol: 'BND', name: 'Vanguard Total Bond Market ETF', type: 'Bond', weight: 15.4, value: 2846.4, dailyChange: 0.12, price: 72.16, shares: 40 },
      { symbol: 'CASH', name: 'Cash', type: 'Cash', weight: 2.7, value: 484.9, dailyChange: 0, price: 1, shares: 484.9 }
    ]
  },
  {
    id: 'balanced',
    name: 'Balanced Portfolio',
    created: '2026-05-08',
    value: 12300,
    totalReturn: 7.84,
    riskScore: 48,
    riskLevel: 'Moderate Low',
    cash: 600,
    holdings: [
      { symbol: 'SPY', name: 'SPDR S&P 500 ETF Trust', type: 'Equity ETF', weight: 40, value: 4920, dailyChange: 0.65, price: 659.71, shares: 7.46 },
      { symbol: 'BND', name: 'Vanguard Total Bond Market ETF', type: 'Bond', weight: 30, value: 3690, dailyChange: 0.12, price: 72.16, shares: 51.14 },
      { symbol: 'GLD', name: 'SPDR Gold Shares', type: 'Commodity ETF', weight: 20, value: 2460, dailyChange: 0.37, price: 315.43, shares: 7.8 },
      { symbol: 'CASH', name: 'Cash', type: 'Cash', weight: 10, value: 1230, dailyChange: 0, price: 1, shares: 1230 }
    ]
  },
  {
    id: 'retirement',
    name: 'Retirement Fund',
    created: '2026-05-05',
    value: 40000,
    totalReturn: 9.21,
    riskScore: 32,
    riskLevel: 'Low',
    cash: 2000,
    holdings: [
      { symbol: 'VTI', name: 'Vanguard Total Stock Market ETF', type: 'Equity ETF', weight: 45, value: 18000, dailyChange: 0.52, price: 333.12, shares: 54.03 },
      { symbol: 'BND', name: 'Vanguard Total Bond Market ETF', type: 'Bond', weight: 35, value: 14000, dailyChange: 0.12, price: 72.16, shares: 194.01 },
      { symbol: 'GLD', name: 'SPDR Gold Shares', type: 'Commodity ETF', weight: 15, value: 6000, dailyChange: 0.37, price: 315.43, shares: 19.02 },
      { symbol: 'CASH', name: 'Cash', type: 'Cash', weight: 5, value: 2000, dailyChange: 0, price: 1, shares: 2000 }
    ]
  },
  {
    id: 'growth',
    name: 'Long Term Growth',
    created: '2026-05-01',
    value: 16750,
    totalReturn: 14.7,
    riskScore: 68,
    riskLevel: 'Moderate Risk',
    cash: 500,
    holdings: [
      { symbol: 'QQQ', name: 'Invesco QQQ Trust', type: 'Equity ETF', weight: 50, value: 8375, dailyChange: 1.12, price: 543.82, shares: 15.4 },
      { symbol: 'NVDA', name: 'NVIDIA Corporation', type: 'Equity', weight: 25, value: 4187.5, dailyChange: 2.61, price: 181.63, shares: 23.06 },
      { symbol: 'AAPL', name: 'Apple Inc.', type: 'Equity', weight: 20, value: 3350, dailyChange: 0.68, price: 191.45, shares: 17.5 },
      { symbol: 'CASH', name: 'Cash', type: 'Cash', weight: 5, value: 837.5, dailyChange: 0, price: 1, shares: 837.5 }
    ]
  }
];

export const watchlistSeed = [
  ['SPY', 'SPDR S&P 500 ETF Trust', 659.71, 0.65, 12.47, '549.2B'],
  ['QQQ', 'Invesco QQQ Trust', 543.82, 1.12, 15.31, '280.1B'],
  ['NVDA', 'NVIDIA Corporation', 181.63, 2.61, 100.21, '4.58T'],
  ['AAPL', 'Apple Inc.', 191.45, 0.68, 8.32, '2.97T'],
  ['TLT', 'iShares 20+ Year Treasury Bond ETF', 92.16, -0.21, -4.12, '45.3B'],
  ['GLD', 'SPDR Gold Shares', 315.43, 0.37, 19.47, '140.3B']
].map(([symbol, name, price, daily, yearly, cap]) => ({symbol, name, price, daily, yearly, cap}));

export const marketOverview = [
  { symbol: 'S&P 500', price: '5,297.10', change: 0.69 },
  { symbol: 'NASDAQ', price: '16,023.17', change: 1.24 },
  { symbol: 'VIX', price: '16.45', change: -2.31 }
];

export const reportsSeed = [
  { id: 1, name: 'Tech Portfolio Analysis', portfolio: 'Tech Portfolio', type: 'Analysis', date: 'May 11, 2026', riskScore: 72 },
  { id: 2, name: '2008 Financial Crisis Simulation', portfolio: 'Tech Portfolio', type: 'Simulation', date: 'May 11, 2026', riskScore: null },
  { id: 3, name: 'Allocation Change Simulation', portfolio: 'Tech Portfolio', type: 'Simulation', date: 'May 9, 2026', riskScore: null },
  { id: 4, name: 'Balanced Portfolio Analysis', portfolio: 'Balanced Portfolio', type: 'Analysis', date: 'May 7, 2026', riskScore: 48 },
  { id: 5, name: 'Tech vs Balanced Comparison', portfolio: 'Recommended', type: 'Comparison', date: 'May 6, 2026', riskScore: null },
  { id: 6, name: 'Retirement Fund Analysis', portfolio: 'Retirement Fund', type: 'Analysis', date: 'May 5, 2026', riskScore: 32 }
];

export const scenarioOptions = [
  { id: 'gfc', label: '2008 Financial Crisis', dates: 'Oct 1, 2007 – Mar 2009', returnPct: -37.42, drawdown: -45.61, volatility: 28.73, recovery: 16 },
  { id: 'covid', label: '2020 COVID Crash', dates: 'Feb 19, 2020 – Mar 23, 2020', returnPct: -22.65, drawdown: -30.18, volatility: 42.15, recovery: 5 },
  { id: 'dotcom', label: 'Dot-com Bust', dates: 'Mar 2000 – Oct 2002', returnPct: -41.25, drawdown: -48.34, volatility: 31.08, recovery: 31 },
  { id: 'growth', label: '2016–2019 Growth Period', dates: 'Jan 2016 – Dec 2019', returnPct: 44.2, drawdown: -13.8, volatility: 15.4, recovery: 3 }
];

export const correlation = [
  [1.00, 0.72, 0.48, -0.12, 0.25],
  [0.72, 1.00, 0.58, -0.06, 0.22],
  [0.48, 0.58, 1.00, -0.06, 0.30],
  [-0.12, -0.06, -0.06, 1.00, -0.25],
  [0.25, 0.22, 0.30, -0.25, 1.00]
];
