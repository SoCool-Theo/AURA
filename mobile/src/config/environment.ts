import Constants from 'expo-constants';

const DEVELOPMENT_API_PORT = '8000';

function resolveDevelopmentApiBaseUrl(): string {
  if (!__DEV__) return '';

  const hostUri = Constants.expoConfig?.hostUri?.trim();
  if (!hostUri) return '';

  try {
    const metroUrl = new URL(
      hostUri.includes('://') ? hostUri : `http://${hostUri}`
    );
    metroUrl.protocol = 'http:';
    metroUrl.port = DEVELOPMENT_API_PORT;
    metroUrl.pathname = '';
    metroUrl.search = '';
    metroUrl.hash = '';
    return metroUrl.origin;
  } catch {
    return '';
  }
}

const configuredApiBaseUrl = process.env.EXPO_PUBLIC_API_URL?.trim() ?? '';

export const environment = Object.freeze({
  apiBaseUrl: configuredApiBaseUrl || resolveDevelopmentApiBaseUrl()
});
