"use client";

import { useMemo, useState } from "react";
import { Plus, Search, UserCheck, UserX } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionCard } from "../SectionCard";
import type { UserRecord } from "../types";

export function UsersPage({ users, setUsers }: { users: UserRecord[]; setUsers: React.Dispatch<React.SetStateAction<UserRecord[]>> }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"Investor" | "Admin">("Investor");
  const filtered = useMemo(() => users.filter(u => `${u.name} ${u.email}`.toLowerCase().includes(query.toLowerCase())), [query, users]);

  function createUser() {
    if (!name.trim() || !email.includes("@")) { toast.error("Enter a name and valid email."); return; }
    setUsers(current => [...current, { id: Date.now(), name: name.trim(), email: email.trim(), role, status: "Active", portfolios: 0 }]);
    setName(""); setEmail(""); setRole("Investor"); setOpen(false); toast.success("User created.");
  }
  function toggleStatus(id: number) {
    setUsers(current => current.map(u => u.id === id ? { ...u, status: u.status === "Active" ? "Suspended" : "Active" } : u));
    toast.success("User status updated.");
  }

  return <div className="page-stack">
    <div className="page-controls"><label className="page-search"><Search/><Input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search by name or email"/></label>
      <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button className="gradient-button"><Plus/>Add New User</Button></DialogTrigger><DialogContent className="admin-dialog"><DialogHeader><DialogTitle>Create user</DialogTitle><DialogDescription>Add an investor or another administrator.</DialogDescription></DialogHeader><div className="form-grid"><label>Full name<Input value={name} onChange={e=>setName(e.target.value)} placeholder="Alex Morgan"/></label><label>Email address<Input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="alex@example.com"/></label><label>Role<Select value={role} onValueChange={v=>setRole(v as "Investor"|"Admin")}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent><SelectItem value="Investor">Investor</SelectItem><SelectItem value="Admin">Admin</SelectItem></SelectContent></Select></label></div><DialogFooter><Button variant="outline" onClick={()=>setOpen(false)}>Cancel</Button><Button onClick={createUser}>Create user</Button></DialogFooter></DialogContent></Dialog>
    </div>
    <SectionCard title="User Accounts" description={`${filtered.length} accounts shown`}><Table><TableHeader><TableRow><TableHead>User</TableHead><TableHead>Role</TableHead><TableHead>Portfolios</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Action</TableHead></TableRow></TableHeader><TableBody>{filtered.map(u=><TableRow key={u.id}><TableCell><div className="table-user"><span>{u.name.split(" ").map(x=>x[0]).join("").slice(0,2)}</span><div><b>{u.name}</b><small>{u.email}</small></div></div></TableCell><TableCell>{u.role}</TableCell><TableCell>{u.portfolios}</TableCell><TableCell><span className={`status-pill ${u.status.toLowerCase()}`}>{u.status}</span></TableCell><TableCell className="text-right"><Button variant="outline" size="sm" onClick={()=>toggleStatus(u.id)}>{u.status === "Active" ? <UserX/> : <UserCheck/>}{u.status === "Active" ? "Suspend" : "Activate"}</Button></TableCell></TableRow>)}</TableBody></Table></SectionCard>
  </div>;
}
