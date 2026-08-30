import type { WatchlistItem } from '../types/watchlist';

export const watchlistCatalog: WatchlistItem[] = [
  { symbol: 'AAPL', name: 'Apple Inc.', price: 238.42, changePercent: 1.24, category: 'Stock' },
  { symbol: 'MSFT', name: 'Microsoft Corp.', price: 518.63, changePercent: 0.71, category: 'Stock' },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', price: 181.91, changePercent: 2.08, category: 'Stock' },
  { symbol: 'TSLA', name: 'Tesla Inc.', price: 411.18, changePercent: -1.36, category: 'Stock' },
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF', price: 651.33, changePercent: 0.43, category: 'ETF' },
  { symbol: 'QQQ', name: 'Invesco QQQ', price: 591.27, changePercent: 0.56, category: 'ETF' },
  { symbol: 'VTI', name: 'Vanguard Total Stock Market', price: 324.84, changePercent: 0.35, category: 'ETF' },
  { symbol: 'BND', name: 'Vanguard Total Bond Market', price: 74.91, changePercent: 0.11, category: 'Bond' },
  { symbol: 'TLT', name: 'iShares 20+ Year Treasury', price: 88.74, changePercent: -0.22, category: 'Bond' },
  { symbol: 'GLD', name: 'SPDR Gold Shares', price: 311.12, changePercent: 0.82, category: 'Metal' },
  { symbol: 'BTC-USD', name: 'Bitcoin', price: 118540, changePercent: 1.92, category: 'Crypto' },
  { symbol: 'ETH-USD', name: 'Ethereum', price: 4784, changePercent: 2.41, category: 'Crypto' }
];
