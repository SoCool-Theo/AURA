const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '')
  .trim()
  .replace(/\/+$/, '');

export const environment = {
  apiBaseUrl,
} as const;
