"use client";

import { Bell, CalendarDays, Menu, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

export function AdminTopbar({ title, onOpenMenu }: { title: string; onOpenMenu: () => void }) {
  return (
    <header className="admin-topbar">
      <div className="title-cluster">
        <Button className="menu-button" variant="ghost" size="icon" onClick={onOpenMenu} aria-label="Open navigation"><Menu /></Button>
        <div><h1>{title}</h1><p>{title === "Dashboard" ? "Good evening, Admin! 👋" : "Manage Aura with clear, controlled actions."}</p></div>
      </div>
      <div className="top-actions">
        <label className="top-search"><Search /><Input placeholder="Search admin panel" /></label>
        <Button variant="outline" className="date-button"><CalendarDays /> Sep 2, 2026</Button>
        <Popover>
          <PopoverTrigger asChild><Button variant="outline" size="icon" aria-label="Notifications" className="notify-button"><Bell /><span>3</span></Button></PopoverTrigger>
          <PopoverContent align="end" className="notifications-panel">
            <h3>Notifications</h3>
            <p><b>Market data</b><span>Two symbols need review.</span></p>
            <p><b>Security</b><span>New admin sign-in detected.</span></p>
            <p><b>Reports</b><span>43 analyses completed today.</span></p>
          </PopoverContent>
        </Popover>
      </div>
    </header>
  );
}
