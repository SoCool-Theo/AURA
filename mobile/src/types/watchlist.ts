export type WatchlistItem = {
  symbol: string;
  name: string;
  price: number;
  changePercent: number;
  category: 'Stock' | 'ETF' | 'Bond' | 'Metal' | 'Crypto';
};
