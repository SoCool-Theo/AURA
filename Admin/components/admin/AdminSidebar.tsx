"use client";

import { Activity, Bot, BriefcaseBusiness, ChartNoAxesCombined, Database, FileText, Gauge, HeartPulse, Settings, Users, X } from "lucide-react";
import type { PageKey } from "./types";
import type { AdminIdentity } from "@/lib/adminContracts";

const items: Array<{ key: PageKey; label: string; icon: typeof Gauge; badge?: string }> = [
  { key: "dashboard", label: "Dashboard", icon: Gauge },
  { key: "users", label: "Users", icon: Users },
  { key: "portfolios", label: "Portfolios", icon: BriefcaseBusiness },
  { key: "market", label: "Market Data", icon: ChartNoAxesCombined },
  { key: "reports", label: "Reports", icon: FileText },
  { key: "health", label: "System Health", icon: HeartPulse },
  { key: "ai", label: "AI Monitoring", icon: Bot },
  { key: "activity", label: "Activity Logs", icon: Activity },
  { key: "settings", label: "Settings", icon: Settings },
];

export function AdminSidebar({ current, onNavigate, open, onClose, compact, identity }: {
  current: PageKey; onNavigate: (page: PageKey) => void; open: boolean; onClose: () => void; compact: boolean;
  identity: AdminIdentity;
}) {
  const name = identity.display_name || identity.email;
  const initials = name.split(/\s+/).map(part => part[0]).join("").slice(0, 2).toUpperCase();
  return (
    <aside className={`admin-sidebar ${open ? "is-open" : ""} ${compact ? "is-compact" : ""}`}>
      <div className="brand-row">
        <div className="aura-mark">A</div>
        {!compact && <div><strong>AURA</strong><span>ADMIN PANEL</span></div>}
        <button className="mobile-close" aria-label="Close navigation" onClick={onClose}><X /></button>
      </div>
      <nav aria-label="Admin navigation">
        {items.map(({ key, label, icon: Icon, badge }) => (
          <button key={key} className={current === key ? "active" : ""} onClick={() => { onNavigate(key); onClose(); }} aria-current={current === key ? "page" : undefined} title={compact ? label : undefined}>
            <Icon />{!compact && <span>{label}</span>}{!compact && badge && <em>{badge}</em>}
          </button>
        ))}
      </nav>
      {!compact && (
        <div className="sidebar-bottom">
          <div className="admin-identity"><div className="avatar">{initials}</div><div><strong>{name}</strong><span>System Admin</span></div></div>
          <div className="quick-actions"><p>Quick actions</p><div>
            <button onClick={() => { onNavigate("market"); onClose(); }}><Database />View data</button>
            <button onClick={() => { onNavigate("users"); onClose(); }}><Users />View users</button>
          </div></div>
        </div>
      )}
    </aside>
  );
}
