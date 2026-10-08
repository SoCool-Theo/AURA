export type Uuid = string;
export type IsoDate = string;
export type IsoDateTime = string;

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export type JsonObject = { [key: string]: JsonValue };

export type ApiHttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export type ApiCallOptions = {
  token?: string | null;
  signal?: AbortSignal;
};

export type ApiResponseMode = 'json' | 'none';

export type ApiRequestOptions<TBody = never> = Omit<
  RequestInit,
  'body' | 'headers' | 'method'
> & {
  method?: ApiHttpMethod;
  headers?: HeadersInit;
  token?: string | null;
  body?: TBody;
  responseMode?: ApiResponseMode;
};

export type ApiErrorKind =
  | 'configuration'
  | 'request'
  | 'network'
  | 'http'
  | 'authentication'
  | 'malformed-response';

export type FastApiValidationError = {
  loc: Array<string | number>;
  msg: string;
  type: string;
  input?: JsonValue;
  ctx?: JsonObject;
};

export type HealthResponse = {
  status: string;
  app_name: string;
  environment: string;
};
