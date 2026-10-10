"use client";
import { useEffect, useState } from "react";

export function useAdminQuery<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{ load: typeof load; revision: number; data?: T; error?: string }>();
  useEffect(() => {
    const controller = new AbortController();
    Promise.resolve().then(() => load(controller.signal)).then(
      data => { if (!controller.signal.aborted) setResult({ load, revision, data }); },
      error => { if (!controller.signal.aborted) setResult({ load, revision, error: error instanceof Error ? error.message : "The request could not be completed." }); },
    );
    return () => controller.abort();
  }, [load, revision]);
  const current = result?.load === load && result.revision === revision ? result : undefined;
  return { data: current?.data, error: current?.error, loading: !current, retry: () => setRevision(value => value + 1) };
}
