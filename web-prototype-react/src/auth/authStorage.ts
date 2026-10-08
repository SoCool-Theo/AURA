const ACCESS_TOKEN_KEY = 'aura.auth.accessToken';

function getSessionStorage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function readAccessToken(): string | null {
  const storage = getSessionStorage();
  const token = storage?.getItem(ACCESS_TOKEN_KEY)?.trim();

  if (!token) {
    storage?.removeItem(ACCESS_TOKEN_KEY);
    return null;
  }

  return token;
}

export function storeAccessToken(token: string): void {
  const normalizedToken = token.trim();
  if (!normalizedToken) throw new Error('Aura received an empty access token.');

  const storage = getSessionStorage();
  if (!storage) throw new Error('Browser session storage is unavailable.');

  storage.setItem(ACCESS_TOKEN_KEY, normalizedToken);
}

export function clearAccessToken(): void {
  getSessionStorage()?.removeItem(ACCESS_TOKEN_KEY);
}
