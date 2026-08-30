import type { HealthResponse } from '../types/api';
import { apiRequest } from './apiClient';

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/api/health', { signal });
}
