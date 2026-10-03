import type { ApiCallOptions } from '../types/api';
import type { NotificationList, NotificationPreferences } from '../types/notification';
import { apiRequest } from './apiClient';

const listeners = new Set<() => void>();
export function subscribeNotifications(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}
export function notificationsChanged() { listeners.forEach(listener => listener()); }

export const notificationsApi = {
  list(offset = 0, limit = 25, options: ApiCallOptions = {}) {
    return apiRequest<NotificationList>(`/api/notifications?limit=${limit}&offset=${offset}`, options);
  },
  preferences(options: ApiCallOptions = {}) {
    return apiRequest<NotificationPreferences>('/api/notifications/preferences', options);
  },
  savePreferences(body: NotificationPreferences, options: ApiCallOptions = {}) {
    return apiRequest<NotificationPreferences, NotificationPreferences>('/api/notifications/preferences', { ...options, method: 'PUT', body });
  },
  markRead(id: string, options: ApiCallOptions = {}) {
    return apiRequest<void>(`/api/notifications/${encodeURIComponent(id)}/read`, { ...options, method: 'POST' });
  },
  markAllRead(options: ApiCallOptions = {}) {
    return apiRequest<void>('/api/notifications/read-all', { ...options, method: 'POST' });
  },
};
