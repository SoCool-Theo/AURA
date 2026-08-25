export type WatchlistAsset = {
  symbol: string;
  name: string;
  price: number;
  daily: number;
  yearly: number;
  cap: string;
};

export type MarketOverviewItem = {
  symbol: string;
  price: string;
  change: number;
};
