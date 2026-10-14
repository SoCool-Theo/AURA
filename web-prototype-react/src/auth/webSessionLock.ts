// Serialize cookie-changing requests within this tab and, where supported,
// across tabs. Refresh credentials remain exclusively in the HttpOnly cookie.
let operations: Promise<void> = Promise.resolve();

export function withWebSessionLock<T>(operation: () => Promise<T>): Promise<T> {
  const result = operations.then(async (): Promise<T> => {
    if (typeof navigator !== 'undefined' && navigator.locks) {
      return await navigator.locks.request('aura.web-session', operation);
    }
    return operation();
  });
  operations = result.then(() => undefined, () => undefined);
  return result;
}
