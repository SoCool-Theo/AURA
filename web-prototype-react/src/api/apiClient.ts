import { environment } from '../config/environment';
import type { ApiRequestOptions } from '../types/api';

export async function apiRequest<T = unknown>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T | null> {
  if (!environment.apiBaseUrl) {
    throw new Error(
      'No API base URL configured. Aura is running with frontend demo data.',
    );
  }

  const response = await fetch(`${environment.apiBaseUrl}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }

  if (response.status === 204) return null;
  return (await response.json()) as T;
}

export const backendReady = Boolean(environment.apiBaseUrl);
