"use client";
import { Activity, BriefcaseBusiness, Database, FileText, HeartPulse, Users } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { adminApi } from "@/lib/adminApi";
import { SectionCard } from "../SectionCard";
import { ApiState, humanize, utc } from "../ApiState";
import { useAdminQuery } from "../useAdminQuery";
import type { PageKey } from "../types";

const loadRecentActivity = (signal: AbortSignal) => adminApi.audit({ limit: 4 }, signal);
export function DashboardPage({ navigate }: { navigate: (page: PageKey) => void }) {
  const overview = useAdminQuery(adminApi.dashboard);
  const inventory = useAdminQuery(adminApi.inventory);
  const market = useAdminQuery(adminApi.marketStatus);
  const health = useAdminQuery(adminApi.health);
  const activity = useAdminQuery(loadRecentActivity);
  const data = overview.data;
  if (!data) return <SectionCard title="Dashboard"><ApiState {...overview}/></SectionCard>;
  const stats = [
    ["Total Users", data.users.total.toLocaleString(), `${data.users.new_last_7_days} new in 7 days`, Users, "cyan"],
    ["Total Portfolios", data.portfolios.total.toLocaleString(), `${data.portfolios.new_last_7_days} new in 7 days`, BriefcaseBusiness, "purple"],
    ["Reports Saved Today", data.saved_reports.today.toLocaleString(), `${data.saved_reports.yesterday} yesterday · UTC`, Activity, "cyan"],
    ["Saved Reports", data.saved_reports.total.toLocaleString(), `${data.saved_reports.last_7_days} retained from last 7 days`, FileText, "orange"],
    ["System Health", health.data ? humanize(health.data.status) : health.error ? "Unavailable" : "Checking", "Partial check coverage", HeartPulse, health.data?.status === "healthy" ? "green" : "orange"],
  ] as const;
  const lastSeven = data.daily.slice(-7);
  return <div className="page-stack"><p className="api-caption">Snapshot {utc(data.generated_at)} · Counts describe retained records.</p><div className="stat-grid">{stats.map(([label, value, change, Icon, tone]) => <article className={`stat-card ${tone}`} key={label}><div className="stat-icon"><Icon/></div><div><span>{label}</span><strong>{value}</strong><small>{change}</small></div></article>)}</div>
    <div className="dashboard-grid"><SectionCard title="Market Data Health" action={<Button variant="outline" size="sm" onClick={() => navigate("market")}>View details</Button>}><ApiState {...inventory}/><ApiState {...market}/>{inventory.data && market.data && <><div className="market-summary"><div className="data-pairs"><p><span>Data status</span><b>{humanize(market.data.data_status)}</b></p><p><span>Last complete refresh</span><b>{utc(market.data.last_complete_at)}</b></p><p><span>Stored / required symbols</span><b>{inventory.data.stored_symbols} / {inventory.data.required_symbols}</b></p><p><span>Total records</span><b>{inventory.data.total_records.toLocaleString()}</b></p></div><div className="orbit"><Database/><i/><i/><i/></div></div><Button className="gradient-button" disabled title="A manual refresh API is not available"><Database/>Update Market Data</Button></>}</SectionCard>
    <SectionCard title="Attention Required"><ApiState {...health}/>{health.data && <div className="attention-list">{health.data.checks.filter(check => check.status !== "healthy").map(check => <button key={check.component} onClick={() => navigate("health")}><HeartPulse/><span><b>{humanize(check.component)} · {humanize(check.status)}</b><small>{humanize(check.reason)}</small></span></button>)}{health.data.checks.every(check => check.status === "healthy") && <p>All reported checks are healthy. Coverage is partial.</p>}</div>}</SectionCard>
    <SectionCard title="Saved Reports Overview" description="Last 7 UTC days"><div className="chart-number"><strong>{data.saved_reports.last_7_days}</strong><span>retained reports</span></div><div className="chart-box small"><ResponsiveContainer width="100%" height="100%"><BarChart data={lastSeven}><CartesianGrid stroke="var(--border)" vertical={false}/><XAxis dataKey="date" stroke="var(--muted-foreground)" fontSize={12} tickFormatter={value => String(value).slice(5)}/><YAxis stroke="var(--muted-foreground)" fontSize={12} allowDecimals={false}/><Tooltip/><Bar dataKey="saved_reports" name="Saved reports" fill="var(--primary)" radius={[5, 5, 0, 0]}/></BarChart></ResponsiveContainer></div></SectionCard></div>
    <div className="dashboard-grid lower"><SectionCard title="Retained Analysis Records" action={<Button variant="ghost" size="sm" onClick={() => navigate("reports")}>View totals</Button>}><div className="data-pairs"><p><span>Reports saved today</span><b>{data.saved_reports.today}</b></p><p><span>Simulations saved today</span><b>{data.saved_simulations.today}</b></p><p><span>Total saved simulations</span><b>{data.saved_simulations.total}</b></p></div><p className="api-caption">Individual report browsing is not available to administrators yet.</p></SectionCard>
    <SectionCard title="Required Instrument Coverage" description="Stored observations; historical gaps are not assessed."><ApiState {...inventory}/>{inventory.data && <div className="data-pairs"><p><span>Current</span><b>{inventory.data.current_required_symbols}</b></p><p><span>Stale</span><b>{inventory.data.stale_required_symbols}</b></p><p><span>Missing</span><b>{inventory.data.missing_required_symbols}</b></p></div>}</SectionCard>
    <SectionCard title="Recent Admin Activity" action={<Button variant="ghost" size="sm" onClick={() => navigate("activity")}>View all</Button>}><ApiState {...activity}/>{activity.data && <div className="activity-mini">{activity.data.items.map(event => <p key={event.id}><span><Users/></span><b>{humanize(event.action)}</b><small>{utc(event.created_at)}</small></p>)}{activity.data.items.length === 0 && <p>No retained audit events.</p>}</div>}</SectionCard></div>
    <SectionCard title="Saved Records Trend" description={`${data.window_start} to ${data.window_end} · UTC`}><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.daily}><defs><linearGradient id="reports-gradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--primary)" stopOpacity=".5"/><stop offset="1" stopColor="var(--primary)" stopOpacity="0"/></linearGradient></defs><CartesianGrid stroke="var(--border)" vertical={false}/><XAxis dataKey="date" stroke="var(--muted-foreground)" tickFormatter={value => String(value).slice(5)}/><YAxis stroke="var(--muted-foreground)" allowDecimals={false}/><Tooltip/><Area type="monotone" dataKey="saved_reports" name="Saved reports" stroke="var(--primary)" fill="url(#reports-gradient)" strokeWidth={3}/><Area type="monotone" dataKey="saved_simulations" name="Saved simulations" stroke="var(--blue)" fill="transparent" strokeWidth={3}/></AreaChart></ResponsiveContainer></div></SectionCard>
  </div>;
}
