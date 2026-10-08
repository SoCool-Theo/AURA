import type { AuthenticatedUserResponse } from '../types/auth';

export function accountDisplayName(
  user: AuthenticatedUserResponse | null,
): string {
  return user?.display_name?.trim() || user?.email || 'Investor';
}

export function accountInitials(
  user: AuthenticatedUserResponse | null,
): string {
  const source = accountDisplayName(user);
  const parts = source.split(/\s+/).filter(Boolean);
  return (
    parts.length > 1
      ? `${parts[0][0]}${parts.at(-1)?.[0] ?? ''}`
      : source.slice(0, 2)
  ).toUpperCase();
}
