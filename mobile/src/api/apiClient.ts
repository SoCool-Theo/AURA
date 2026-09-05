import { getToken } from '../auth/authStorage';
import { environment } from '../config/environment';
import type {
  ApiErrorKind,
  ApiRequestOptions,
  JsonValue
} from '../types/api';

type ParsedResponseBody = JsonValue | string | null;

type ApiAuthentication = {
  getAccessToken: () => Promise<string | null>;
  onAuthenticationRejected: (
    rejectedToken: string | null
  ) => void | Promise<void>;
};

const defaultAuthentication: ApiAuthentication = {
  getAccessToken: getToken,
  onAuthenticationRejected: () => undefined
};

let apiAuthentication = defaultAuthentication;

export function configureApiAuthentication(
  authentication: ApiAuthentication
): () => void {
  apiAuthentication = authentication;
  return () => {
    if (apiAuthentication === authentication) {
      apiAuthentication = defaultAuthentication;
    }
  };
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly detail: JsonValue | null;
  readonly responseBody: ParsedResponseBody;
  readonly causeValue: unknown;

  constructor({
    kind,
    message,
    status = null,
    detail = null,
    responseBody = null,
    cause
  }: {
    kind: ApiErrorKind;
    message: string;
    status?: number | null;
    detail?: JsonValue | null;
    responseBody?: ParsedResponseBody;
    cause?: unknown;
  }) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.detail = detail;
    this.responseBody = responseBody;
    this.causeValue = cause;
  }
}

function buildApiUrl(path: string): string {
  if (!environment.apiBaseUrl) {
    throw new ApiError({
      kind: 'configuration',
      message: 'EXPO_PUBLIC_API_URL is not configured.'
    });
  }

  let baseUrl: URL;
  try {
    baseUrl = new URL(environment.apiBaseUrl);
  } catch (cause) {
    throw new ApiError({
      kind: 'configuration',
      message: 'EXPO_PUBLIC_API_URL must be a valid absolute URL.',
      cause
    });
  }

  if (
    !['http:', 'https:'].includes(baseUrl.protocol)
    || baseUrl.username
    || baseUrl.password
    || (baseUrl.pathname !== '' && baseUrl.pathname !== '/')
    || baseUrl.search
    || baseUrl.hash
  ) {
    throw new ApiError({
      kind: 'configuration',
      message: 'EXPO_PUBLIC_API_URL must be an HTTP(S) origin without credentials, a path, query, or fragment.'
    });
  }

  const normalizedPath = `/${path.replace(/^\/+/, '')}`;
  if (normalizedPath !== '/api' && !normalizedPath.startsWith('/api/')) {
    throw new ApiError({
      kind: 'configuration',
      message: 'Aura API request paths must begin with /api.'
    });
  }

  return new URL(normalizedPath, `${baseUrl.origin}/`).toString();
}

function parseJson(text: string): {
  parsed: boolean;
  body: ParsedResponseBody;
} {
  if (!text) return { parsed: true, body: null };
  try {
    return { parsed: true, body: JSON.parse(text) as JsonValue };
  } catch {
    return { parsed: false, body: text };
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

function httpErrorMessage(status: number, detail: JsonValue | null): string {
  if (status >= 500) return `Aura API is unavailable (HTTP ${status}). Please try again.`;
  if (typeof detail === 'string' && detail.trim()) return detail;
  return `Request failed with HTTP ${status}.`;
}

async function resolveAccessToken(
  suppliedToken: string | null | undefined
): Promise<string | null> {
  if (suppliedToken !== undefined) return suppliedToken;
  try {
    return await apiAuthentication.getAccessToken();
  } catch (cause) {
    throw new ApiError({
      kind: 'configuration',
      message: 'Aura could not access secure authentication storage.',
      cause
    });
  }
}

export async function apiRequest<TResponse, TBody = never>(
  path: string,
  options: ApiRequestOptions<TBody> = {}
): Promise<TResponse> {
  const {
    body,
    headers: suppliedHeaders,
    token: suppliedToken,
    responseMode = 'json',
    ...requestOptions
  } = options;
  const url = buildApiUrl(path);
  const accessToken = await resolveAccessToken(suppliedToken);
  const headers = new Headers(suppliedHeaders);
  headers.set('Accept', 'application/json');

  let requestBody: string | undefined;
  if (body !== undefined) {
    headers.set('Content-Type', 'application/json');
    try {
      requestBody = JSON.stringify(body);
    } catch (cause) {
      throw new ApiError({
        kind: 'request',
        message: 'Aura could not serialize the API request body.',
        cause
      });
    }
  }

  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);

  let response: Response;
  try {
    response = await fetch(url, {
      ...requestOptions,
      headers,
      body: requestBody
    });
  } catch (cause) {
    throw new ApiError({
      kind: 'network',
      message: 'Unable to reach the Aura API.',
      cause
    });
  }

  // Status alone is authoritative, even if reading a 401 response body fails.
  if (response.status === 401) {
    try { await apiAuthentication.onAuthenticationRejected(accessToken); }
    catch { /* AuthProvider exposes any secure-storage cleanup failure. */ }
  }

  let responseText: string;
  try {
    responseText = await response.text();
  } catch (cause) {
    throw new ApiError({
      kind: 'network',
      message: 'Aura lost the API response before it could be read.',
      status: response.status,
      cause
    });
  }
  const { parsed, body: responseBody } = parseJson(responseText);

  if (!response.ok) {
    const detail = parsed && response.status < 500 ? extractDetail(responseBody) : null;
    const kind: ApiErrorKind = response.status === 401
      ? 'authentication'
      : 'http';

    throw new ApiError({
      kind,
      message: httpErrorMessage(response.status, detail),
      status: response.status,
      detail,
      responseBody
    });
  }

  if (responseMode === 'none') {
    return undefined as TResponse;
  }

  if (!responseText || !parsed || responseBody === null || typeof responseBody !== 'object' || Array.isArray(responseBody)) {
    throw new ApiError({
      kind: 'malformed-response',
      message: !responseText
        ? 'Aura API returned an unexpected empty response.'
        : 'Aura API returned a malformed or unexpected response.',
      status: response.status,
      responseBody
    });
  }

  return responseBody as TResponse;
}
