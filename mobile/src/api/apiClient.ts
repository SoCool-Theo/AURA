import { environment } from '../config/environment';
import { getToken } from '../auth/authStorage';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

type RequestOptions = RequestInit & { authenticated?: boolean };

export async function apiClient<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');

  if (options.authenticated !== false) {
    const token = await getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${environment.apiUrl}${path}`, { ...options, headers });
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;

  if (!response.ok) throw new ApiError(response.status, body?.detail ?? 'Request failed');
  return body as T;
}
