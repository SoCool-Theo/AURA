import type { MarketOverviewItem } from '../types/market';

export const lineA = [18, 16, 20, 17, 24, 25, 29, 33, 31, 36, 39, 43, 40, 45, 49, 44, 50, 54, 58, 55, 61, 64, 67, 73, 69, 76, 81, 78, 85, 91];
export const lineB = [12, 11, 13, 10, 14, 17, 16, 20, 22, 24, 22, 27, 29, 26, 31, 30, 34, 37, 35, 39, 41, 40, 44, 48, 47, 51, 53, 55, 57, 60];
export const downturnA = [5, 0, -3, -8, -12, -16, -19, -22, -24, -27, -31, -35, -37, -34, -40, -43, -39, -36, -34, -37, -33, -31, -28, -30];
export const downturnB = [5, 3, -1, -4, -7, -10, -12, -15, -18, -19, -21, -24, -25, -23, -28, -31, -29, -26, -24, -22, -20, -18, -16, -15];

export const marketOverview: MarketOverviewItem[] = [
  { symbol: 'S&P 500', price: '5,297.10', change: 0.69 },
  { symbol: 'NASDAQ', price: '16,023.17', change: 1.24 },
  { symbol: 'VIX', price: '16.45', change: -2.31 },
];
