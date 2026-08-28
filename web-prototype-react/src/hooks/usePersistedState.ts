import { useEffect, useState, type Dispatch, type SetStateAction } from 'react';

export function usePersistedState<T>(
  key: string,
  seed: T,
): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => {
    try {
      const storedValue = localStorage.getItem(key);
      return storedValue ? (JSON.parse(storedValue) as T) : seed;
    } catch {
      return seed;
    }
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue];
}
