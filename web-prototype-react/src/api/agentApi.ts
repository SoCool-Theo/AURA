import type { ApiCallOptions } from '../types/api';
import type { AgentExplainRequest, AgentExplainResponse } from '../types/agent';
import { apiRequest } from './apiClient';

export function explainPortfolio(
  request: AgentExplainRequest,
  options: ApiCallOptions = {},
): Promise<AgentExplainResponse> {
  return apiRequest<AgentExplainResponse, AgentExplainRequest>(
    '/api/agent/explain',
    { ...options, method: 'POST', body: request },
  );
}
