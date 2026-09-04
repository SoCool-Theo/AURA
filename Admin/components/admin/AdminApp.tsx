"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";
import { AdminSidebar } from "./AdminSidebar";
import { AdminTopbar } from "./AdminTopbar";
import { DashboardPage } from "./pages/DashboardPage";
import { UsersPage } from "./pages/UsersPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ActivityPage, AiOversightPage, HealthPage, MarketDataPage, PortfoliosPage, ReportsPage } from "./pages/OtherPages";
import { defaultSettings, initialUsers } from "./mockData";
import type { AdminSettings, PageKey, UserRecord } from "./types";

const titles: Record<PageKey, string> = {
  dashboard: "Dashboard", users: "Users", portfolios: "Portfolios", market: "Market Data",
  reports: "Reports", health: "System Health", ai: "AI Oversight", activity: "Activity Logs", settings: "Settings",
};

export function AdminApp() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [menuOpen, setMenuOpen] = useState(false);
  const [users, setUsers] = useState<UserRecord[]>(initialUsers);
  const [records, setRecords] = useState(69449);
  const [lastUpdate, setLastUpdate] = useState("Sep 2, 2026 16:20");
  const [settings, setSettings] = useState<AdminSettings>(defaultSettings);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const saved = window.localStorage.getItem("aura-admin-settings");
      if (saved) { try { setSettings({ ...defaultSettings, ...JSON.parse(saved) }); } catch { /* ignore invalid local data */ } }
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    const isLight = settings.appearance === "light" || (settings.appearance === "system" && window.matchMedia("(prefers-color-scheme: light)").matches);
    document.documentElement.dataset.auraTheme = isLight ? "light" : "dark";
  }, [settings.appearance]);

  function saveSettings(next: AdminSettings) {
    setSettings(next);
    window.localStorage.setItem("aura-admin-settings", JSON.stringify(next));
  }

  function updateMarketData() {
    const id = toast.loading("Updating 17 market symbols…");
    window.setTimeout(() => {
      setRecords(value => value + 428);
      setLastUpdate("Sep 2, 2026 16:24");
      toast.success("Market data update completed.", { id });
    }, 850);
  }

  let content: React.ReactNode;
  if (page === "dashboard") content = <DashboardPage navigate={setPage} records={records} lastUpdate={lastUpdate} onUpdate={updateMarketData}/>;
  else if (page === "users") content = <UsersPage users={users} setUsers={setUsers}/>;
  else if (page === "portfolios") content = <PortfoliosPage/>;
  else if (page === "market") content = <MarketDataPage records={records} lastUpdate={lastUpdate} onUpdate={updateMarketData}/>;
  else if (page === "reports") content = <ReportsPage/>;
  else if (page === "health") content = <HealthPage/>;
  else if (page === "ai") content = <AiOversightPage/>;
  else if (page === "activity") content = <ActivityPage/>;
  else content = <SettingsPage settings={settings} onSave={saveSettings}/>;

  return (
    <div className="admin-shell">
      <AdminSidebar current={page} onNavigate={setPage} open={menuOpen} onClose={()=>setMenuOpen(false)} compact={settings.compactSidebar}/>
      {menuOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={()=>setMenuOpen(false)}/>} 
      <main className="admin-main"><AdminTopbar title={titles[page]} onOpenMenu={()=>setMenuOpen(true)}/><div className="admin-content">{content}</div></main>
      <Toaster position="top-right" richColors />
    </div>
  );
}
