import { environment } from '../config/environment';
import type {
  ApiErrorKind,
  ApiRequestOptions,
  JsonValue,
} from '../types/api';

type ParsedResponseBody = JsonValue | string | null;

type ApiAuthentication = {
  getAccessToken: () => string | null;
  onUnauthorized: (rejectedToken: string) => void;
};

let apiAuthentication: ApiAuthentication | null = null;

export function configureApiAuthentication(
  authentication: ApiAuthentication,
): () => void {
  apiAuthentication = authentication;
  return () => {
    if (apiAuthentication === authentication) apiAuthentication = null;
  };
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly detail: JsonValue | null;
  readonly responseBody: ParsedResponseBody;

  constructor({
    kind,
    message,
    status = null,
    detail = null,
    responseBody = null,
    cause,
  }: {
    kind: ApiErrorKind;
    message: string;
    status?: number | null;
    detail?: JsonValue | null;
    responseBody?: ParsedResponseBody;
    cause?: unknown;
  }) {
    super(message, cause === undefined ? undefined : { cause });
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.detail = detail;
    this.responseBody = responseBody;
  }
}

function buildApiUrl(path: string): string {
  if (!environment.apiBaseUrl) {
    throw new ApiError({
      kind: 'configuration',
      message: 'VITE_API_BASE_URL is not configured.',
    });
  }

  let baseUrl: URL;
  try {
    baseUrl = new URL(environment.apiBaseUrl);
  } catch (cause) {
    throw new ApiError({
      kind: 'configuration',
      message: 'VITE_API_BASE_URL must be a valid absolute URL.',
      cause,
    });
  }

  if (
    (baseUrl.pathname !== '' && baseUrl.pathname !== '/')
    || baseUrl.search
    || baseUrl.hash
  ) {
    throw new ApiError({
      kind: 'configuration',
      message: 'VITE_API_BASE_URL must contain only the API origin, without /api or another path.',
    });
  }

  const normalizedPath = `/${path.replace(/^\/+/, '')}`;
  if (normalizedPath !== '/api' && !normalizedPath.startsWith('/api/')) {
    throw new ApiError({
      kind: 'configuration',
      message: 'Aura API request paths must begin with /api.',
    });
  }

  return new URL(normalizedPath, `${baseUrl.origin}/`).toString();
}

async function parseResponseBody(response: Response): Promise<ParsedResponseBody> {
  const text = await response.text();
  if (!text) return null;

  try {
    return JSON.parse(text) as JsonValue;
  } catch {
    return text;
  }
}

function extractDetail(body: ParsedResponseBody): JsonValue | null {
  if (
    body !== null
    && typeof body === 'object'
    && !Array.isArray(body)
    && 'detail' in body
  ) {
    return body.detail;
  }
  return null;
}

function httpErrorMessage(
  response: Response,
  detail: JsonValue | null,
): string {
  if (typeof detail === 'string' && detail) return detail;
  return `Request failed with HTTP ${response.status}`;
}

export async function apiRequest<TResponse, TBody = never>(
  path: string,
  options: ApiRequestOptions<TBody> = {},
): Promise<TResponse> {
  const { body, headers: suppliedHeaders, token, ...requestOptions } = options;
  const accessToken = token === undefined
    ? apiAuthentication?.getAccessToken() ?? null
    : token;
  const headers = new Headers(suppliedHeaders);
  headers.set('Accept', 'application/json');

  if (body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);

  let response: Response;
  try {
    response = await fetch(buildApiUrl(path), {
      ...requestOptions,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (cause) {
    if (cause instanceof ApiError) throw cause;
    throw new ApiError({
      kind: 'network',
      message: 'Unable to reach the Aura API.',
      cause,
    });
  }

  if (response.status === 204) return undefined as TResponse;

  const responseBody = await parseResponseBody(response);

  if (!response.ok) {
    const detail = extractDetail(responseBody);
    if (response.status === 401 && accessToken) {
      apiAuthentication?.onUnauthorized(accessToken);
    }
    throw new ApiError({
      kind: 'http',
      message: httpErrorMessage(response, detail),
      status: response.status,
      detail,
      responseBody,
    });
  }

  return responseBody as TResponse;
}

export const backendReady = Boolean(environment.apiBaseUrl);
