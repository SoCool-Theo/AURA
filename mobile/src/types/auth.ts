import type { IsoDateTime, Uuid } from './api';

export type RegistrationRequest = {
  email: string;
  password: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type PreferredLanguage = 'en' | 'th';
export type ProfileTimezone = 'Asia/Bangkok' | 'Asia/Yangon';

export type AuthenticatedUserResponse = {
  id: Uuid;
  email: string;
  display_name: string | null;
  phone_number: string | null;
  preferred_language: PreferredLanguage;
  timezone: ProfileTimezone;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
};

export type ProfileUpdateRequest = {
  display_name?: string | null;
  email?: string;
  phone_number?: string | null;
  preferred_language?: PreferredLanguage;
  timezone?: ProfileTimezone;
  current_password?: string;
};

export type PasswordChangeRequest = {
  current_password: string;
  new_password: string;
};

export type AccountDeletionRequest = {
  current_password: string;
};

export type AccessTokenResponse = {
  access_token: string;
  token_type: 'bearer';
};
