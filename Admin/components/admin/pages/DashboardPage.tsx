"use client";

import { Activity, ArrowUpRight, BriefcaseBusiness, ChartNoAxesCombined, Check, Database, FileText, HeartPulse, ShieldCheck, TriangleAlert, Users } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SectionCard } from "../SectionCard";
import type { PageKey } from "../types";

const bars = [
  { day: "Mon", analyses: 40 }, { day: "Tue", analyses: 53 }, { day: "Wed", analyses: 69 },
  { day: "Thu", analyses: 82 }, { day: "Fri", analyses: 95 }, { day: "Sat", analyses: 114 },
];
const trend = [
  { day: "Aug 5", analyses: 36, reports: 12 }, { day: "Aug 10", analyses: 57, reports: 23 },
  { day: "Aug 15", analyses: 45, reports: 18 }, { day: "Aug 20", analyses: 75, reports: 31 },
  { day: "Aug 25", analyses: 61, reports: 27 }, { day: "Sep 2", analyses: 98, reports: 55 },
];

export function DashboardPage({ navigate, records, lastUpdate, onUpdate }: {
  navigate: (page: PageKey) => void; records: number; lastUpdate: string; onUpdate: () => void;
}) {
  const stats = [
    ["Total Users", "324", "+8 this week", Users, "cyan"],
    ["Total Portfolios", "587", "+14 this week", BriefcaseBusiness, "purple"],
    ["Analyses Today", "43", "+12 vs yesterday", ChartNoAxesCombined, "cyan"],
    ["Reports", "1,203", "+56 this week", FileText, "orange"],
    ["System Health", "Healthy", "All systems operational", HeartPulse, "green"],
  ] as const;
  return (
    <div className="page-stack">
      <div className="stat-grid">
        {stats.map(([label, value, change, Icon, tone]) => (
          <article className={`stat-card ${tone}`} key={label}><div className="stat-icon"><Icon /></div><div><span>{label}</span><strong>{value}</strong><small>{change}</small></div></article>
        ))}
      </div>

      <div className="dashboard-grid">
        <SectionCard title="Market Data Health" action={<Button variant="outline" size="sm" onClick={() => navigate("market")}>View details</Button>}>
          <div className="market-summary">
            <div className="data-pairs"><p><span>Data source</span><b>Yahoo Finance <Badge>Connected</Badge></b></p><p><span>Last successful update</span><b>{lastUpdate}</b></p><p><span>Tracked symbols</span><b>17</b></p><p><span>Total records</span><b>{records.toLocaleString()}</b></p></div>
            <div className="orbit"><Database /><i /><i /><i /></div>
          </div>
          <Button className="gradient-button" onClick={onUpdate}><Database /> Update Market Data <ArrowUpRight /></Button>
        </SectionCard>

        <SectionCard title="Attention Required">
          <div className="attention-list"><button onClick={() => navigate("market")}><TriangleAlert /><span><b>Market data may be outdated</b><small>Last successful update was several hours ago.</small></span></button><button onClick={() => navigate("market")}><TriangleAlert /><span><b>2 symbols have missing data</b><small>BTC-USD and GLD have data gaps.</small></span></button><div><Check /><span><b>0 failed updates</b><small>All scheduled jobs completed.</small></span></div></div>
        </SectionCard>

        <SectionCard title="Analyses Overview" description="Last 7 days">
          <div className="chart-number"><strong>285</strong><span>↑ 12.5%</span></div>
          <div className="chart-box small"><ResponsiveContainer width="100%" height="100%"><BarChart data={bars}><CartesianGrid stroke="var(--border)" vertical={false} /><XAxis dataKey="day" stroke="var(--muted-foreground)" fontSize={12} /><YAxis stroke="var(--muted-foreground)" fontSize={12} /><Tooltip /><Bar dataKey="analyses" fill="var(--primary)" radius={[5,5,0,0]} /></BarChart></ResponsiveContainer></div>
        </SectionCard>
      </div>

      <div className="dashboard-grid lower">
        <SectionCard title="Recent Analyses" action={<Button variant="ghost" size="sm" onClick={() => navigate("reports")}>View all</Button>}>
          <div className="row-list">{[["Tech Portfolio","Yan Lin Oo","72"],["Balanced Portfolio","Alex Morgan","48"],["Retirement Fund","Sarah Lee","32"],["Long Term Growth","John Smith","68"]].map(x => <button key={x[0]} onClick={() => navigate("reports")}><Activity /><span><b>{x[0]}</b><small>{x[1]}</small></span><strong className={Number(x[2]) > 65 ? "risk-high" : "risk-low"}>{x[2]}</strong></button>)}</div>
        </SectionCard>
        <SectionCard title="Most Analyzed Assets" description="Last 7 days"><div className="asset-list">{[["NVDA",87],["AAPL",76],["TSLA",63],["SPY",59],["MSFT",52]].map(([name,count], i) => <p key={String(name)}><i style={{background:["var(--primary)","var(--blue)","var(--purple)","var(--warning)","var(--primary-hover)"][i]}}/><b>{name}</b><span>{count} analyses</span></p>)}</div></SectionCard>
        <SectionCard title="Recent Admin Activity" action={<Button variant="ghost" size="sm" onClick={() => navigate("activity")}>View all</Button>}><div className="activity-mini">{["Market data update completed","Viewed system health report","User account created","Settings updated"].map((x,i)=><p key={x}><span>{i === 0 ? <Database /> : i === 1 ? <ShieldCheck /> : i === 2 ? <Users /> : <Activity />}</span><b>{x}</b><small>{i+1}h</small></p>)}</div></SectionCard>
      </div>

      <SectionCard title="Analyses Trend" description="Last 30 days"><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend}><defs><linearGradient id="purple" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--primary)" stopOpacity=".5"/><stop offset="1" stopColor="var(--primary)" stopOpacity="0"/></linearGradient></defs><CartesianGrid stroke="var(--border)" vertical={false}/><XAxis dataKey="day" stroke="var(--muted-foreground)"/><YAxis stroke="var(--muted-foreground)"/><Tooltip/><Area type="monotone" dataKey="analyses" stroke="var(--primary)" fill="url(#purple)" strokeWidth={3}/><Area type="monotone" dataKey="reports" stroke="var(--blue)" fill="transparent" strokeWidth={3}/></AreaChart></ResponsiveContainer></div></SectionCard>
    </div>
  );
}
