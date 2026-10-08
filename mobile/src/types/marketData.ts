export type MarketObservationStatus = {
  symbol: string;
  kind: 'asset' | 'fx';
  latest_price_date: string | null;
  age_days: number | null;
  is_current: boolean;
};

export type MarketDataStatusResponse = {
  mode: 'daily';
  checked_at: string;
  update_time_utc: string;
  next_scheduled_at: string;
  worker_status: 'unknown' | 'online' | 'offline';
  worker_last_seen_at: string | null;
  last_run_status: 'never' | 'running' | 'success' | 'partial' | 'failed';
  last_attempt_at: string | null;
  last_finished_at: string | null;
  last_complete_at: string | null;
  attempt_count: number;
  stored_count: number;
  updated_symbols: string[];
  failed_symbols: string[];
  error_code: 'provider_unavailable' | 'database_unavailable' | 'validation_failed' | 'update_failed' | 'lock_lost' | 'incomplete_coverage' | null;
  data_status: 'current' | 'stale' | 'missing';
  observations: MarketObservationStatus[];
};
