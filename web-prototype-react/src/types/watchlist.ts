import type { IsoDate, IsoDateTime, Uuid } from './api';

export type WatchlistItemResponse = {
  id: Uuid;
  symbol: string;
  latest_price: number | null;
  latest_price_date: IsoDate | null;
  daily_change_percent: number | null;
  ytd_change_percent: number | null;
  created_at: IsoDateTime;
};

export type WatchlistListResponse = {
  items: WatchlistItemResponse[];
};

export type WatchlistCreateRequest = {
  symbol: string;
};
