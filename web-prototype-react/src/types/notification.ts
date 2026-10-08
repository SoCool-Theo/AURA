export type NotificationPreferences = {
  enabled: boolean;
  analysis_enabled: boolean;
  simulation_enabled: boolean;
};

export type NotificationItem = {
  id: string;
  kind: 'analysis' | 'simulation';
  title: string;
  message: string;
  portfolio_id: string;
  resource_id: string;
  created_at: string;
  read_at: string | null;
};

export type NotificationList = { items: NotificationItem[]; total: number; unread_count: number };
