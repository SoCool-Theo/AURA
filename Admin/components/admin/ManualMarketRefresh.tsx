"use client";
import { useEffect, useRef, useState } from "react";
import { Database } from "lucide-react";
import { adminApi } from "@/lib/adminApi";
import type { MarketStatus } from "@/lib/adminContracts";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";

export function ManualMarketRefresh({ status, active, onUpdated }: { status?: MarketStatus; active: boolean; onUpdated: () => void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ error: boolean; text: string }>();
  const requestId = useRef<string | undefined>(undefined);
  const controller = useRef<AbortController | undefined>(undefined);
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function confirm() {
    if (controller.current) return;
    const abort = new AbortController(); controller.current = abort; setBusy(true); setMessage(undefined);
    requestId.current ??= crypto.randomUUID();
    try {
      const run = await adminApi.requestMarketRefresh(requestId.current, abort.signal);
      if (abort.signal.aborted) return;
      requestId.current = undefined;
      setMessage({ error: false, text: run.status === "queued" ? "Refresh request queued. The worker will process it shortly; check run history for the outcome." : "Refresh request confirmed. Check run history for the outcome." });
      setOpen(false); onUpdated();
    } catch (error) {
      if (!abort.signal.aborted) { setMessage({ error: true, text: error instanceof Error ? error.message : "Refresh request could not be confirmed. Check run history before retrying." }); onUpdated(); }
    } finally {
      controller.current = undefined;
      if (!abort.signal.aborted) setBusy(false);
    }
  }
  const unavailable = !status || status.worker_status !== "online";
  return <><AlertDialog open={open} onOpenChange={value => { if (!busy) setOpen(value); }}><AlertDialogTrigger asChild><Button ref={button} className="gradient-button" disabled={busy || unavailable || active || status?.last_run_status === "running"}><Database/>Update Market Data</Button></AlertDialogTrigger>
    <AlertDialogContent onCloseAutoFocus={event => { if (button.current && !button.current.disabled) { event.preventDefault(); button.current.focus(); } }}><AlertDialogHeader><AlertDialogTitle>Update market data?</AlertDialogTitle><AlertDialogDescription>Request daily historical prices for all required assets and exchange rates through yesterday UTC. The worker will validate and store available observations. Existing records for failed instruments are preserved, and the automatic schedule stays unchanged.</AlertDialogDescription></AlertDialogHeader>
      {message?.error && <p className="api-message" role="alert">{message.text}</p>}<AlertDialogFooter><AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel><AlertDialogAction disabled={busy} onClick={event => { event.preventDefault(); void confirm(); }}>{busy ? "Requesting…" : "Request update"}</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
    <p className="api-caption">{unavailable ? "Start the market-data worker to enable manual updates." : active || status?.last_run_status === "running" ? "A refresh is queued or running. Progress updates while this page is visible." : "Updates daily historical data; no streaming quotes."}</p>
    {message && !open && <p className="api-message" role={message.error ? "alert" : "status"}>{message.text}</p>}</>;
}
