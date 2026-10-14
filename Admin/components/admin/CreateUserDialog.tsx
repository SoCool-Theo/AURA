"use client";
import { useEffect, useRef, useState } from "react";
import { Plus } from "lucide-react";
import { AdminApiError, adminApi } from "@/lib/adminApi";
import type { AdminUser } from "@/lib/adminContracts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export function CreateUserDialog({ disabled, onStart, onCreated, onUncertain }: { disabled: boolean; onStart: () => void; onCreated: (user: AdminUser) => void; onUncertain: () => void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string>();
  const inFlight = useRef<AbortController | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => () => inFlight.current?.abort(), []);
  function changeOpen(value: boolean) {
    if (inFlight.current) return;
    setOpen(value); setError(undefined);
    if (value) onStart();
    if (!value) { setEmail(""); setName(""); setPassword(""); setConfirmation(""); }
  }
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    event.stopPropagation();
    if (inFlight.current) return;
    if ([...password].length < 8) { setError("Use an initial password with at least 8 characters."); return; }
    if (password !== confirmation) { setError("The password confirmation does not match."); return; }
    const controller = new AbortController(); inFlight.current = controller;
    setBusy(true); setError(undefined);
    try {
      const user = await adminApi.createUser({ email, password, display_name: name }, controller.signal);
      if (!controller.signal.aborted) { setOpen(false); setEmail(""); setName(""); onCreated(user); }
    } catch (failure) {
      if (!controller.signal.aborted) {
        const message = failure instanceof Error ? failure.message : "Account creation could not be confirmed.";
        setError(failure instanceof AdminApiError && failure.status === 409 ? message : `${message} Check the Users directory if the result is uncertain.`);
        onUncertain();
      }
    } finally {
      if (!controller.signal.aborted) { inFlight.current = null; setBusy(false); setPassword(""); setConfirmation(""); }
    }
  }
  return <Dialog open={open} onOpenChange={changeOpen}><DialogTrigger asChild><Button ref={trigger} type="button" className="gradient-button" disabled={disabled || busy}><Plus/>Add New User</Button></DialogTrigger>
    <DialogContent className="max-h-[90vh] overflow-y-auto" showCloseButton={!busy} onCloseAutoFocus={event => { event.preventDefault(); trigger.current?.focus(); }}>
      <DialogHeader><DialogTitle>Create user account</DialogTitle><DialogDescription>New accounts start with customer access. Grant administrator access separately after creation. The user can sign in with these credentials and change their password in account settings.</DialogDescription></DialogHeader>
      <form onSubmit={event => { void submit(event); }}><div className="settings-form">
        <label>Full name (optional)<Input value={name} maxLength={100} autoComplete="off" disabled={busy} onChange={event => setName(event.target.value)}/></label>
        <label>Email address<Input type="email" required value={email} autoComplete="off" disabled={busy} onChange={event => setEmail(event.target.value)}/></label>
        <label>Initial password<Input type="password" required minLength={8} value={password} autoComplete="new-password" disabled={busy} onChange={event => setPassword(event.target.value)}/></label>
        <label>Confirm initial password<Input type="password" required minLength={8} value={confirmation} autoComplete="new-password" disabled={busy} onChange={event => setConfirmation(event.target.value)}/></label>
      </div>{error && <p className="api-message" role="alert">{error}</p>}<DialogFooter><Button type="button" variant="outline" disabled={busy} onClick={() => changeOpen(false)}>Cancel</Button><Button type="submit" className="gradient-button" disabled={busy}>{busy ? "Creating…" : "Create account"}</Button></DialogFooter></form>
    </DialogContent>
  </Dialog>;
}
