import type { WatchlistAsset } from '../types/market';

export const watchlistSeed: WatchlistAsset[] = [
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF Trust', price: 659.71, daily: 0.65, yearly: 12.47, cap: '549.2B' },
  { symbol: 'QQQ', name: 'Invesco QQQ Trust', price: 543.82, daily: 1.12, yearly: 15.31, cap: '280.1B' },
  { symbol: 'NVDA', name: 'NVIDIA Corporation', price: 181.63, daily: 2.61, yearly: 100.21, cap: '4.58T' },
  { symbol: 'AAPL', name: 'Apple Inc.', price: 191.45, daily: 0.68, yearly: 8.32, cap: '2.97T' },
  { symbol: 'TLT', name: 'iShares 20+ Year Treasury Bond ETF', price: 92.16, daily: -0.21, yearly: -4.12, cap: '45.3B' },
  { symbol: 'GLD', name: 'SPDR Gold Shares', price: 315.43, daily: 0.37, yearly: 19.47, cap: '140.3B' },
];
