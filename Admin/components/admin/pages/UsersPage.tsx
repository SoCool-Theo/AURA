"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Plus, Search } from "lucide-react";
import { adminApi } from "@/lib/adminApi";
import type { AdminIdentity, AdminUser } from "@/lib/adminContracts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionCard } from "../SectionCard";
import { ApiState, Filter, Pagination, humanize, utc } from "../ApiState";
import { useAdminQuery } from "../useAdminQuery";

export function UsersPage({ identity }: { identity: AdminIdentity }) {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ q: "", role: "", account_type: "", status: "", offset: 0 });
  const load = useCallback((signal: AbortSignal) => adminApi.users({ ...filters, limit: 25 }, signal), [filters]);
  const query = useAdminQuery(load);
  const [selected, setSelected] = useState<AdminUser>();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [actionKind, setActionKind] = useState<"status" | "role">("status");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [notice, setNotice] = useState<string>();
  const inFlight = useRef<AbortController | null>(null);
  const actionButton = useRef<HTMLButtonElement | null>(null);
  const searchInput = useRef<HTMLInputElement | null>(null);
  useEffect(() => () => inFlight.current?.abort(), []);
  const suspending = selected?.status === "ACTIVE";
  const changingRole = actionKind === "role";
  const granting = selected?.role === "CUSTOMER";
  const action = changingRole ? granting ? "Grant administrator access" : "Remove administrator access" : suspending ? "Suspend" : "Reactivate";
  const destructive = changingRole ? !granting : suspending;

  async function confirm() {
    if (!dialogOpen || !selected || inFlight.current) return;
    const controller = new AbortController();
    inFlight.current = controller;
    setBusy(true); setError(undefined); setNotice(undefined);
    try {
      if (changingRole) {
        await adminApi.setUserRole(selected.id, granting ? "ADMIN" : "CUSTOMER", selected.role, controller.signal);
      } else {
        await adminApi.setUserStatus(selected.id, suspending ? "SUSPENDED" : "ACTIVE", selected.status, controller.signal);
      }
      if (!controller.signal.aborted) {
        setNotice(changingRole ? `${granting ? "Administrator access granted" : "Administrator access removed"}. Existing sessions have ended; the user must sign in again.` : suspending ? "Account suspended. Existing sessions are invalidated." : "Account reactivated. The user can sign in again.");
        setDialogOpen(false);
        query.retry();
      }
    } catch (failure) {
      if (!controller.signal.aborted) {
        setError(`${failure instanceof Error ? failure.message : "Unable to confirm the update."} Refresh the directory before trying again if the result is uncertain.`);
        query.retry();
      }
    } finally {
      if (!controller.signal.aborted) { inFlight.current = null; setBusy(false); }
    }
  }

  return <div className="page-stack">
    <form className="page-controls api-controls" onSubmit={event => { event.preventDefault(); setFilters(value => ({ ...value, q: search.trim(), offset: 0 })); }}>
      <label className="page-search"><Search/><Input ref={searchInput} value={search} maxLength={100} onChange={event => setSearch(event.target.value)} placeholder="Search by name or email" aria-label="Search users"/></label>
      <Button type="submit" variant="outline">Search</Button>
      <Filter label="Role" value={filters.role} options={["CUSTOMER", "ADMIN"]} onChange={role => setFilters(value => ({ ...value, role, offset: 0 }))}/>
      <Filter label="Account type" value={filters.account_type} options={["REGISTERED", "LEGACY"]} onChange={account_type => setFilters(value => ({ ...value, account_type, offset: 0 }))}/>
      <Filter label="Status" value={filters.status} options={["ACTIVE", "SUSPENDED"]} onChange={status => setFilters(value => ({ ...value, status, offset: 0 }))}/>
      <Button type="button" className="gradient-button" disabled title="User creation is not supported by the admin API"><Plus/>Add New User</Button>
    </form>
    {notice && <p role="status" className="api-message">{notice}</p>}
    <SectionCard title="User Accounts" description="Manage account access and administrator roles while preserving portfolios and saved records.">
      <ApiState {...query}/>
      {query.data && <>
        <Table><TableHeader><TableRow><TableHead>User</TableHead><TableHead>Role</TableHead><TableHead>Portfolios</TableHead><TableHead>Account type</TableHead><TableHead>Status</TableHead><TableHead>Created (UTC)</TableHead><TableHead>Actions</TableHead></TableRow></TableHeader>
          <TableBody>{query.data.items.map(user => <TableRow key={user.id}>
            <TableCell><div className="table-user"><span>{(user.display_name || user.email || "Legacy").slice(0, 2).toUpperCase()}</span><div><b>{user.display_name || "Unnamed account"}</b><small>{user.email || "No email · legacy account"}</small></div></div></TableCell>
            <TableCell>{humanize(user.role)}</TableCell><TableCell>{user.portfolio_count}</TableCell><TableCell>{humanize(user.account_type)}</TableCell>
            <TableCell><span className={`status-pill ${user.status === "ACTIVE" ? "api-status-healthy" : "api-status-degraded"}`}>{humanize(user.status)}</span></TableCell><TableCell>{utc(user.created_at)}</TableCell>
            <TableCell><div className="inline-actions"><Button variant="outline" size="sm" disabled={busy || user.id === identity.id} title={user.id === identity.id ? "You cannot suspend your own account" : undefined} aria-label={`${user.status === "ACTIVE" ? "Suspend" : "Reactivate"} ${user.email || user.display_name || user.id}`} onClick={event => { actionButton.current = event.currentTarget; setActionKind("status"); setSelected(user); setDialogOpen(true); setError(undefined); setNotice(undefined); }}>{user.status === "ACTIVE" ? "Suspend" : "Reactivate"}</Button>
              <Button variant="outline" size="sm" disabled={busy || user.id === identity.id || user.role === "CUSTOMER" && (user.account_type !== "REGISTERED" || user.status !== "ACTIVE")} title={user.id === identity.id ? "You cannot remove your own administrator access" : user.role === "CUSTOMER" && user.account_type !== "REGISTERED" ? "Only registered accounts can become administrators" : user.role === "CUSTOMER" && user.status !== "ACTIVE" ? "Reactivate this account before granting administrator access" : undefined} aria-label={`${user.role === "CUSTOMER" ? "Grant administrator access to" : "Remove administrator access from"} ${user.email || user.display_name || user.id}`} onClick={event => { actionButton.current = event.currentTarget; setActionKind("role"); setSelected(user); setDialogOpen(true); setError(undefined); setNotice(undefined); }}>{user.role === "CUSTOMER" ? "Grant admin access" : "Remove admin access"}</Button></div></TableCell>
          </TableRow>)}</TableBody>
        </Table>
        {query.data.items.length === 0 && <p className="api-message">No accounts match these filters.</p>}
        <Pagination {...query.data} onChange={offset => setFilters(value => ({ ...value, offset }))}/>
      </>}
    </SectionCard>
    <AlertDialog open={dialogOpen} onOpenChange={open => { if (!inFlight.current) setDialogOpen(open); }}>
      <AlertDialogContent onCloseAutoFocus={event => { event.preventDefault(); (actionButton.current?.isConnected && !actionButton.current.disabled ? actionButton.current : searchInput.current)?.focus(); }}><AlertDialogHeader><AlertDialogTitle>{action}{changingRole ? "" : " account"}?</AlertDialogTitle>
        <AlertDialogDescription>{selected?.email || selected?.display_name || selected?.id}. {changingRole ? granting ? "This account will gain access to the admin dashboard and administrator actions. Existing sessions will end, and the user must sign in again." : "This account will lose administrator permission and retain customer access, portfolios, and saved records. Existing sessions will end, and the user must sign in again. Suspended accounts remain suspended." : suspending ? "This account will lose access immediately. Existing sessions will end. Portfolios and saved records will be preserved." : "This account will regain access and must sign in again. Previous sessions will remain invalid."}</AlertDialogDescription>
      </AlertDialogHeader>
      {error && <p role="alert" className="api-message">{error}</p>}
      <AlertDialogFooter><AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel><AlertDialogAction variant={destructive ? "destructive" : "default"} disabled={busy} onClick={event => { event.preventDefault(); void confirm(); }}>{busy ? "Updating…" : `${action}${changingRole ? "" : " account"}`}</AlertDialogAction></AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </div>;
}
