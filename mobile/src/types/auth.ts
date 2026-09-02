import type { IsoDateTime, Uuid } from './api';

export type RegistrationRequest = {
  email: string;
  password: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type AuthenticatedUserResponse = {
  id: Uuid;
  email: string;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
};

export type AccessTokenResponse = {
  access_token: string;
  token_type: 'bearer';
};
