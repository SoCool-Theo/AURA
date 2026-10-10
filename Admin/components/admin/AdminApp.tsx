"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Toaster } from "@/components/ui/sonner";
import { adminApi } from "@/lib/adminApi";
import type { AdminIdentity } from "@/lib/adminContracts";
import { AdminSidebar } from "./AdminSidebar";
import { AdminTopbar } from "./AdminTopbar";
import { AdminSignIn } from "./AdminSignIn";
import { SectionCard } from "./SectionCard";
import { DashboardPage } from "./pages/DashboardPage";
import { UsersPage } from "./pages/UsersPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ActivityPage, AiOversightPage, HealthPage, MarketDataPage, PortfoliosPage, ReportsPage } from "./pages/OtherPages";
import type { AppearanceSettings, PageKey } from "./types";

const titles: Record<PageKey, string> = { dashboard: "Dashboard", users: "Users", portfolios: "Portfolios", market: "Market Data", reports: "Reports", health: "System Health", ai: "AI Monitoring", activity: "Activity Logs", settings: "Settings" };
const appearanceDefaults: AppearanceSettings = { appearance: "dark", compactSidebar: false };

export function AdminApp() {
  const [identity, setIdentity] = useState<AdminIdentity>();
  const [phase, setPhase] = useState<"checking" | "signedOut" | "signingIn" | "ready" | "unavailable">("checking");
  const [message, setMessage] = useState<string>();
  const [revision, setRevision] = useState(0);
  const loginRequest = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const unsubscribe = adminApi.subscribeAccessDenied(() => { loginRequest.current?.abort(); setIdentity(undefined); setPhase("signedOut"); setMessage("Your session ended or administrator access was removed. Sign in again."); });
    Promise.resolve().then(async () => {
      if (!adminApi.readToken()) { if (!controller.signal.aborted) setPhase("signedOut"); return; }
      try {
        const restored = await adminApi.me(controller.signal);
        if (!controller.signal.aborted) { setIdentity(restored); setPhase("ready"); }
      } catch (error) {
        if (!controller.signal.aborted) { setMessage(error instanceof Error ? error.message : "Unable to check your session."); setPhase(adminApi.readToken() ? "unavailable" : "signedOut"); }
      }
    });
    return () => { controller.abort(); loginRequest.current?.abort(); unsubscribe(); };
  }, [revision]);
  async function signIn(email: string, password: string) {
    loginRequest.current?.abort();
    const controller = new AbortController(); loginRequest.current = controller;
    setPhase("signingIn"); setMessage(undefined);
    try {
      const signedIn = await adminApi.login(email, password, controller.signal);
      if (!controller.signal.aborted) { setIdentity(signedIn); setPhase("ready"); }
    } catch (error) {
      if (!controller.signal.aborted) { setMessage(error instanceof Error ? error.message : "Unable to sign in."); setPhase("signedOut"); }
    }
  }
  function signOut() { loginRequest.current?.abort(); adminApi.clearToken(); setIdentity(undefined); setMessage(undefined); setPhase("signedOut"); }
  if (phase === "ready" && identity) return <AdminWorkspace key={identity.id} identity={identity} onSignOut={signOut}/>;
  if (phase === "checking" || phase === "unavailable") return <main className="admin-auth"><SectionCard title="AURA Admin"><p role={phase === "checking" ? "status" : "alert"}>{phase === "checking" ? "Checking administrator access…" : message}</p>{phase === "unavailable" && <div className="inline-actions"><Button onClick={() => { setPhase("checking"); setRevision(value => value + 1); }}>Retry</Button><Button variant="outline" onClick={signOut}>Sign out</Button></div>}</SectionCard></main>;
  return <AdminSignIn busy={phase === "signingIn"} message={message} onSignIn={signIn}/>;
}

function AdminWorkspace({ identity, onSignOut }: { identity: AdminIdentity; onSignOut: () => void }) {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [menuOpen, setMenuOpen] = useState(false);
  const settingsKey = `aura.admin.appearance.${identity.id}`;
  const [settings, setSettings] = useState(appearanceDefaults);
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      try {
        const saved = JSON.parse(localStorage.getItem(settingsKey) ?? "null");
        if (saved && ["dark", "light", "system"].includes(saved.appearance) && typeof saved.compactSidebar === "boolean") setSettings({ appearance: saved.appearance, compactSidebar: saved.compactSidebar });
      } catch { /* Use defaults when local preferences are unavailable. */ }
    });
    return () => cancelAnimationFrame(frame);
  }, [settingsKey]);
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: light)");
    const apply = () => { document.documentElement.dataset.auraTheme = settings.appearance === "light" || (settings.appearance === "system" && media.matches) ? "light" : "dark"; };
    apply(); media.addEventListener("change", apply);
    return () => { media.removeEventListener("change", apply); delete document.documentElement.dataset.auraTheme; };
  }, [settings.appearance]);
  function saveSettings(next: AppearanceSettings) { localStorage.setItem(settingsKey, JSON.stringify(next)); setSettings(next); }
  let content: React.ReactNode;
  if (page === "dashboard") content = <DashboardPage navigate={setPage}/>;
  else if (page === "users") content = <UsersPage identity={identity}/>;
  else if (page === "portfolios") content = <PortfoliosPage/>;
  else if (page === "market") content = <MarketDataPage/>;
  else if (page === "reports") content = <ReportsPage/>;
  else if (page === "health") content = <HealthPage/>;
  else if (page === "ai") content = <AiOversightPage/>;
  else if (page === "activity") content = <ActivityPage/>;
  else content = <SettingsPage identity={identity} settings={settings} onSave={saveSettings}/>;
  return <div className="admin-shell"><AdminSidebar current={page} onNavigate={setPage} open={menuOpen} onClose={() => setMenuOpen(false)} compact={settings.compactSidebar} identity={identity}/>{menuOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)}/>}<main className="admin-main"><AdminTopbar title={titles[page]} onOpenMenu={() => setMenuOpen(true)} onSignOut={onSignOut}/><div className="admin-content">{content}</div></main><Toaster position="top-right" richColors/></div>;
}
