"use client";
import { useCallback, useState } from "react";
import { Plus, Search } from "lucide-react";
import { adminApi } from "@/lib/adminApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionCard } from "../SectionCard";
import { ApiState, Filter, Pagination, humanize, utc } from "../ApiState";
import { useAdminQuery } from "../useAdminQuery";

export function UsersPage() {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ q: "", role: "", account_type: "", offset: 0 });
  const load = useCallback((signal: AbortSignal) => adminApi.users({ ...filters, limit: 25 }, signal), [filters]);
  const query = useAdminQuery(load);
  return <div className="page-stack"><form className="page-controls api-controls" onSubmit={event => { event.preventDefault(); setFilters(value => ({ ...value, q: search.trim(), offset: 0 })); }}><label className="page-search"><Search/><Input value={search} maxLength={100} onChange={event => setSearch(event.target.value)} placeholder="Search by name or email" aria-label="Search users"/></label><Button type="submit" variant="outline">Search</Button><Filter label="Role" value={filters.role} options={["CUSTOMER", "ADMIN"]} onChange={role => setFilters(value => ({ ...value, role, offset: 0 }))}/><Filter label="Account type" value={filters.account_type} options={["REGISTERED", "LEGACY"]} onChange={account_type => setFilters(value => ({ ...value, account_type, offset: 0 }))}/><Button type="button" className="gradient-button" disabled title="User creation is not supported by the admin API"><Plus/>Add New User</Button></form><SectionCard title="User Accounts" description="Read-only account directory. Creation and suspension are not available."><ApiState {...query}/>{query.data && <><Table><TableHeader><TableRow><TableHead>User</TableHead><TableHead>Role</TableHead><TableHead>Portfolios</TableHead><TableHead>Account type</TableHead><TableHead>Created (UTC)</TableHead></TableRow></TableHeader><TableBody>{query.data.items.map(user => <TableRow key={user.id}><TableCell><div className="table-user"><span>{(user.display_name || user.email || "Legacy").slice(0, 2).toUpperCase()}</span><div><b>{user.display_name || "Unnamed account"}</b><small>{user.email || "No email · legacy account"}</small></div></div></TableCell><TableCell>{humanize(user.role)}</TableCell><TableCell>{user.portfolio_count}</TableCell><TableCell>{humanize(user.account_type)}</TableCell><TableCell>{utc(user.created_at)}</TableCell></TableRow>)}</TableBody></Table>{query.data.items.length === 0 && <p className="api-message">No accounts match these filters.</p>}<Pagination {...query.data} onChange={offset => setFilters(value => ({ ...value, offset }))}/></>}</SectionCard></div>;
}
