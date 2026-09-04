"use client";

import { useState } from "react";
import { Bell, Database, LockKeyhole, MonitorCog, RotateCcw, Save, Send, ShieldCheck, UserRound } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SectionCard } from "../SectionCard";
import { defaultSettings } from "../mockData";
import type { AdminSettings } from "../types";

function SettingRow({ title, text, children }: { title: string; text: string; children: React.ReactNode }) {
  return <div className="setting-row"><div><b>{title}</b><p>{text}</p></div>{children}</div>;
}

export function SettingsPage({ settings, onSave }: { settings: AdminSettings; onSave: (settings: AdminSettings) => void }) {
  const [draft, setDraft] = useState(settings);
  const update = <K extends keyof AdminSettings>(key: K, value: AdminSettings[K]) => setDraft(s => ({ ...s, [key]: value }));
  const save = () => { onSave(draft); toast.success("Admin settings saved."); };
  const reset = () => { setDraft(defaultSettings); toast.info("Defaults restored. Save to apply them."); };

  return <div className="page-stack settings-page">
    <div className="settings-actions"><div><h2>Admin Settings</h2><p>Manage your admin profile, alerts, security and Aura system preferences.</p></div><div><Button variant="outline" onClick={reset}><RotateCcw/>Reset</Button><Button className="gradient-button" onClick={save}><Save/>Save Changes</Button></div></div>
    <Tabs defaultValue="profile" className="settings-tabs">
      <TabsList variant="line" className="settings-tab-list"><TabsTrigger value="profile"><UserRound/>Profile</TabsTrigger><TabsTrigger value="appearance"><MonitorCog/>Appearance</TabsTrigger><TabsTrigger value="notifications"><Bell/>Notifications</TabsTrigger><TabsTrigger value="security"><ShieldCheck/>Security</TabsTrigger><TabsTrigger value="system"><Database/>System</TabsTrigger></TabsList>

      <TabsContent value="profile"><SectionCard title="Administrator Profile" description="Shown in activity logs and admin account menus."><div className="settings-form"><label><Label htmlFor="adminName">Full name</Label><Input id="adminName" value={draft.adminName} onChange={e=>update("adminName", e.target.value)}/></label><label><Label htmlFor="adminEmail">Email address</Label><Input id="adminEmail" type="email" value={draft.email} onChange={e=>update("email", e.target.value)}/></label><label><Label htmlFor="roleLabel">Display role</Label><Input id="roleLabel" value={draft.roleLabel} onChange={e=>update("roleLabel", e.target.value)}/></label></div></SectionCard></TabsContent>

      <TabsContent value="appearance"><SectionCard title="Appearance" description="Choose how the admin workspace looks on this device."><SettingRow title="Color theme" text="Use the Aura dark theme, a bright workspace, or your system preference."><Select value={draft.appearance} onValueChange={v=>update("appearance", v as AdminSettings["appearance"])}><SelectTrigger className="setting-select"><SelectValue/></SelectTrigger><SelectContent><SelectItem value="dark">Dark</SelectItem><SelectItem value="light">Light</SelectItem><SelectItem value="system">System</SelectItem></SelectContent></Select></SettingRow><SettingRow title="Compact sidebar" text="Reduce navigation width to show icons only."><Switch checked={draft.compactSidebar} onCheckedChange={v=>update("compactSidebar", v)}/></SettingRow></SectionCard></TabsContent>

      <TabsContent value="notifications"><SectionCard title="Notification Preferences" description="Control which admin events should interrupt you."><SettingRow title="Email alerts" text="Send important system alerts to the admin email."><Switch checked={draft.emailAlerts} onCheckedChange={v=>update("emailAlerts", v)}/></SettingRow><SettingRow title="Security alerts" text="Notify admins about sign-ins and permission changes."><Switch checked={draft.securityAlerts} onCheckedChange={v=>update("securityAlerts", v)}/></SettingRow><SettingRow title="Failed market-data updates" text="Alert when the scheduler or provider update fails."><Switch checked={draft.failedUpdateAlerts} onCheckedChange={v=>update("failedUpdateAlerts", v)}/></SettingRow><SettingRow title="Weekly summary" text="Receive a summary of users, analyses and system health."><Switch checked={draft.weeklySummary} onCheckedChange={v=>update("weeklySummary", v)}/></SettingRow><Button variant="outline" onClick={()=>toast.success("Test notification sent.")}><Send/>Send Test Notification</Button></SectionCard></TabsContent>

      <TabsContent value="security"><div className="settings-grid"><SectionCard title="Authentication"><SettingRow title="Require MFA for admins" text="Require an additional verification step at sign-in."><Switch checked={draft.requireMfa} onCheckedChange={v=>update("requireMfa", v)}/></SettingRow><SettingRow title="Session timeout" text="Automatically end inactive admin sessions."><Select value={draft.sessionTimeout} onValueChange={v=>update("sessionTimeout", v)}><SelectTrigger className="setting-select"><SelectValue/></SelectTrigger><SelectContent><SelectItem value="15">15 minutes</SelectItem><SelectItem value="30">30 minutes</SelectItem><SelectItem value="60">1 hour</SelectItem><SelectItem value="240">4 hours</SelectItem></SelectContent></Select></SettingRow></SectionCard><SectionCard title="Active Sessions" description="Review and revoke other administrator sessions."><div className="session-card"><LockKeyhole/><div><b>Current session · Chrome on macOS</b><p>Bangkok, Thailand · Active now</p></div><span>Current</span></div><div className="session-card"><LockKeyhole/><div><b>Chrome on Windows</b><p>Last active 2 days ago</p></div><Button variant="outline" size="sm" onClick={()=>toast.success("Other session signed out.")}>Sign out</Button></div></SectionCard></div></TabsContent>

      <TabsContent value="system"><div className="settings-grid"><SectionCard title="Market Data Scheduler"><div className="settings-form"><label><Label>Daily update time</Label><Input type="time" value={draft.marketSchedule} onChange={e=>update("marketSchedule", e.target.value)}/></label><label><Label>Timezone</Label><Select value={draft.timezone} onValueChange={v=>update("timezone",v)}><SelectTrigger className="full-select"><SelectValue/></SelectTrigger><SelectContent><SelectItem value="UTC">UTC</SelectItem><SelectItem value="Asia/Bangkok">Asia/Bangkok</SelectItem><SelectItem value="America/New_York">America/New York</SelectItem></SelectContent></Select></label></div></SectionCard><SectionCard title="Platform Controls"><SettingRow title="Allow investor registration" text="Let new investors create their own Aura accounts."><Switch checked={draft.allowRegistration} onCheckedChange={v=>update("allowRegistration",v)}/></SettingRow><SettingRow title="Maintenance mode" text="Temporarily block investor access while admin work is performed."><Switch checked={draft.maintenanceMode} onCheckedChange={v=>update("maintenanceMode",v)}/></SettingRow></SectionCard></div></TabsContent>
    </Tabs>
    <div className="settings-save-bar"><span>{JSON.stringify(draft) === JSON.stringify(settings) ? "All changes saved" : "You have unsaved changes"}</span><Button onClick={save} disabled={JSON.stringify(draft) === JSON.stringify(settings)}><Save/>Save Changes</Button></div>
  </div>;
}
