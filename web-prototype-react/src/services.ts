const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export type ApiRequestOptions = RequestInit & {
  headers?: Record<string, string>;
};

export async function apiRequest<T = unknown>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T | null> {
  if (!API_BASE) {
    throw new Error(
      'No API base URL configured. Aura is running with frontend demo data.',
    );
  }

  const response = await fetch(`${API_BASE}${path}`, {
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

export const backendReady = Boolean(API_BASE);
