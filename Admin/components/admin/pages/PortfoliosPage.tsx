"use client";
import { useCallback, useRef, useState } from "react";
import { Search } from "lucide-react";
import { adminApi } from "@/lib/adminApi";
import type { AdminPortfolio } from "@/lib/adminContracts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionCard } from "../SectionCard";
import { ApiState, Filter, Pagination, humanize, utc } from "../ApiState";
import { useAdminQuery } from "../useAdminQuery";

export function PortfoliosPage() {
  const [search, setSearch] = useState("");
  const [owner, setOwner] = useState("");
  const [filters, setFilters] = useState({ q: "", owner_id: "", portfolio_type: "", offset: 0 });
  const load = useCallback((signal: AbortSignal) => adminApi.portfolios({ ...filters, limit: 25 }, signal), [filters]);
  const query = useAdminQuery(load);
  const totals = useAdminQuery(adminApi.dashboard);
  const counts = totals.data?.portfolios;
  const [selected, setSelected] = useState<AdminPortfolio>();
  const action = useRef<HTMLButtonElement | null>(null);
  return <div className="page-stack">
    <SectionCard title="Investor Portfolios" description="Retained portfolios across all owners."><ApiState {...totals}/>{counts && <div className="data-pairs grid grid-cols-2 gap-3 sm:grid-cols-4">{(["total", "current", "planned", "legacy"] as const).map(key => <p key={key}><span>{humanize(key)}</span><b>{counts[key]}</b></p>)}</div>}</SectionCard>
    <form className="page-controls api-controls" onSubmit={event => { event.preventDefault(); setFilters(value => ({ ...value, q: search.trim(), owner_id: owner.trim(), offset: 0 })); }}>
      <label className="page-search"><Search/><Input value={search} maxLength={100} onChange={event => setSearch(event.target.value)} placeholder="Search portfolio or owner" aria-label="Search portfolios"/></label>
      <label className="api-filter">Owner ID<Input value={owner} onChange={event => setOwner(event.target.value)} placeholder="Optional account UUID" aria-label="Portfolio owner ID" pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"/></label>
      <Button type="submit" variant="outline">Search</Button>
      <Filter label="Portfolio type" value={filters.portfolio_type} options={["CURRENT", "PLANNED", "LEGACY"]} onChange={portfolio_type => setFilters(value => ({ ...value, portfolio_type, offset: 0 }))}/>
      <Button type="button" variant="outline" onClick={() => { setSearch(""); setOwner(""); setFilters({ q: "", owner_id: "", portfolio_type: "", offset: 0 }); }}>Clear filters</Button>
      <Button type="button" variant="outline" onClick={() => { query.retry(); totals.retry(); }}>Refresh</Button>
    </form>
    <SectionCard title="Portfolio Directory" description="Browse saved holding facts and retained result counts."><ApiState {...query}/>{query.data && <>
      <Table><TableHeader><TableRow>{["Portfolio / ID", "Owner / ID", "Type", "Holdings", "Reports", "Simulations", "Updated (UTC)", "Details"].map(label => <TableHead key={label}>{label}</TableHead>)}</TableRow></TableHeader><TableBody>{query.data.items.map(item => <TableRow key={item.id}>
        <TableCell className="whitespace-normal"><div className="min-w-40 max-w-60 break-words"><b>{item.name}</b><small className="block break-all text-muted-foreground">{item.id}</small></div></TableCell><TableCell className="whitespace-normal"><div className="min-w-40 max-w-60 break-words">{item.owner.display_name ?? item.owner.email ?? "Legacy account"}<small className="block break-all text-muted-foreground">{item.owner.email ?? "No registered email"}</small><small className="block break-all text-muted-foreground">{item.owner.id}</small>{item.owner.status === "SUSPENDED" && <span className="status-pill api-status-suspended">Suspended</span>}</div></TableCell>
        <TableCell>{humanize(item.portfolio_type)}{item.plan_currency && <small className="block text-muted-foreground">{item.plan_currency}</small>}</TableCell><TableCell>{item.holding_count}</TableCell><TableCell>{item.saved_report_count}</TableCell><TableCell>{item.saved_simulation_count}</TableCell><TableCell>{utc(item.updated_at)}</TableCell>
        <TableCell><Button size="sm" variant="outline" aria-label={`View ${item.name}`} onClick={event => { action.current = event.currentTarget; setSelected(item); }}>View details</Button></TableCell>
      </TableRow>)}</TableBody></Table>
      {query.data.items.length === 0 && <p className="api-message">No portfolios match these filters.</p>}<Pagination {...query.data} onChange={offset => setFilters(value => ({ ...value, offset }))}/>
    </>}</SectionCard>
    {selected && <PortfolioDetails key={selected.id} id={selected.id} onClose={() => setSelected(undefined)} restoreFocus={() => action.current?.focus()}/>}
  </div>;
}

function PortfolioDetails({ id, onClose, restoreFocus }: { id: string; onClose: () => void; restoreFocus: () => void }) {
  const load = useCallback((signal: AbortSignal) => adminApi.portfolio(id, signal), [id]);
  const query = useAdminQuery(load);
  const item = query.data;
  return <Dialog open onOpenChange={open => { if (!open) onClose(); }}><DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl" onCloseAutoFocus={event => { event.preventDefault(); restoreFocus(); }}>
    <DialogHeader><DialogTitle>{item?.name ?? "Portfolio details"}</DialogTitle><DialogDescription>Saved portfolio facts. Holdings are shown in their stored order.</DialogDescription></DialogHeader><ApiState {...query}/>
    {item && <><div className="data-pairs grid grid-cols-1 gap-x-6 break-words sm:grid-cols-2"><p><span>Portfolio ID</span><b>{item.id}</b></p><p><span>Owner</span><b>{item.owner.display_name ?? item.owner.email ?? "Legacy account"}</b></p><p><span>Owner ID</span><b>{item.owner.id}</b></p><p><span>Email</span><b>{item.owner.email ?? "No registered email"}</b></p><p><span>Account</span><b>{humanize(item.owner.account_type)} · {humanize(item.owner.status)}</b></p><p><span>Type</span><b>{humanize(item.portfolio_type)}{item.plan_currency && ` · ${item.plan_currency}`}</b></p><p><span>Created</span><b>{utc(item.created_at)}</b></p><p><span>Updated</span><b>{utc(item.updated_at)}</b></p><p><span>Saved reports / simulations</span><b>{item.saved_report_count} / {item.saved_simulation_count}</b></p>{item.source_plan_id && <p><span>Source plan ID</span><b>{item.source_plan_id}</b></p>}</div>
      <Table><TableHeader><TableRow><TableHead>Order</TableHead><TableHead>Symbol</TableHead>{item.portfolio_type === "CURRENT" ? <><TableHead>Shares</TableHead><TableHead>Recorded investment</TableHead><TableHead>Purchase date</TableHead></> : <TableHead>{item.portfolio_type === "PLANNED" ? `Proposed amount (${item.plan_currency})` : "Saved weight"}</TableHead>}</TableRow></TableHeader><TableBody>{item.holdings.map(holding => <TableRow key={holding.id}><TableCell>{holding.position + 1}</TableCell><TableCell>{holding.symbol}</TableCell>{item.portfolio_type === "CURRENT" ? <><TableCell>{holding.shares}</TableCell><TableCell>{holding.invested_amount ? `${holding.invested_amount} ${holding.invested_currency}` : "Not recorded"}</TableCell><TableCell>{holding.purchase_date ?? "Not recorded"}</TableCell></> : <TableCell>{item.portfolio_type === "PLANNED" ? holding.proposed_amount : new Intl.NumberFormat("en-GB", { style: "percent", maximumFractionDigits: 6 }).format(holding.weight ?? 0)}</TableCell>}</TableRow>)}</TableBody></Table>
      {item.holdings.length === 0 && <p className="api-message">This portfolio has no saved holdings.</p>}<p className="api-message">These are saved inputs. Current market values and risk results are not recalculated here.{item.portfolio_type === "PLANNED" && " Proposed amounts describe a hypothetical allocation."}</p>
    </>}
  </DialogContent></Dialog>;
}
