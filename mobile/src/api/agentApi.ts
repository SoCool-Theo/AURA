import type { ApiCallOptions } from '../types/api';
import type {
  AgentExplainRequest,
  AgentExplainResponse,
  AgentSourceReference
} from '../types/agent';
import { ApiError, apiRequest } from './apiClient';

const SOURCE_TYPES = new Set<AgentSourceReference['type']>([
  'portfolio',
  'report',
  'simulation'
]);
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isSource(value: unknown): value is AgentSourceReference {
  return isRecord(value)
    && typeof value.type === 'string'
    && SOURCE_TYPES.has(value.type as AgentSourceReference['type'])
    && typeof value.id === 'string'
    && UUID_PATTERN.test(value.id);
}

function parseResponse(value: unknown): AgentExplainResponse {
  if (
    !isRecord(value)
    || typeof value.answer !== 'string'
    || !value.answer.trim()
    || !Array.isArray(value.sources)
    || !value.sources.every(isSource)
    || !Array.isArray(value.limitations)
    || !value.limitations.every(
      (item) => typeof item === 'string' && Boolean(item.trim())
    )
  ) {
    throw new ApiError({
      kind: 'malformed-response',
      message: 'Aura API returned a malformed or unexpected AI response.'
    });
  }

  return {
    answer: value.answer,
    sources: value.sources,
    limitations: value.limitations
  };
}

export const agentApi = {
  async explain(
    request: AgentExplainRequest,
    options: ApiCallOptions = {}
  ): Promise<AgentExplainResponse> {
    const response = await apiRequest<unknown, AgentExplainRequest>(
      '/api/agent/explain',
      { ...options, method: 'POST', body: request }
    );
    return parseResponse(response);
  }
};
