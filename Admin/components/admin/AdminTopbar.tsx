"use client";
import { Bell, CalendarDays, LogOut, Menu, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function AdminTopbar({ title, onOpenMenu, onSignOut }: { title: string; onOpenMenu: () => void; onSignOut: () => void }) {
  return <header className="admin-topbar"><div className="title-cluster"><Button className="menu-button" variant="ghost" size="icon" onClick={onOpenMenu} aria-label="Open navigation"><Menu/></Button><div><h1>{title}</h1><p>Monitor Aura with verified administrator access.</p></div></div><div className="top-actions"><label className="top-search" title="Global search is not available yet"><Search/><Input placeholder="Search admin panel" disabled aria-label="Global search unavailable"/></label><span className="date-button"><CalendarDays/>{new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" }).format(new Date())} UTC</span><Button variant="outline" size="icon" disabled aria-label="Notifications unavailable" title="Notifications are not supported yet"><Bell/></Button><Button variant="outline" onClick={onSignOut}><LogOut/>Sign out</Button></div></header>;
}
