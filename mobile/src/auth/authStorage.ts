import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'aura_access_token';

export async function saveToken(token: string): Promise<void> {
  const normalizedToken = token.trim();
  if (!normalizedToken) {
    throw new Error('Aura received an empty access token.');
  }
  await SecureStore.setItemAsync(TOKEN_KEY, normalizedToken);
}

export async function getToken(): Promise<string | null> {
  const token = await SecureStore.getItemAsync(TOKEN_KEY);
  return token?.trim() || null;
}

export function clearToken(): Promise<void> {
  return SecureStore.deleteItemAsync(TOKEN_KEY);
}
