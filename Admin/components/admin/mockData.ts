import type { AdminSettings, UserRecord } from "./types";

export const initialUsers: UserRecord[] = [
  { id: 1, name: "Alex Morgan", email: "alex@example.com", role: "Investor", status: "Active", portfolios: 3 },
  { id: 2, name: "Sarah Lee", email: "sarah@example.com", role: "Investor", status: "Active", portfolios: 2 },
  { id: 3, name: "John Smith", email: "john@example.com", role: "Investor", status: "Suspended", portfolios: 1 },
  { id: 4, name: "Maya Chen", email: "maya@example.com", role: "Investor", status: "Active", portfolios: 4 },
];

export const defaultSettings: AdminSettings = {
  adminName: "Yan Lin Oo",
  email: "admin@aura.local",
  roleLabel: "System Admin",
  appearance: "dark",
  compactSidebar: false,
  emailAlerts: true,
  securityAlerts: true,
  failedUpdateAlerts: true,
  weeklySummary: false,
  requireMfa: false,
  sessionTimeout: "30",
  marketSchedule: "02:00",
  timezone: "UTC",
  maintenanceMode: false,
  allowRegistration: true,
};

export const activities = [
  ["Market data update completed", "17 symbols · 69,449 records", "2 min ago"],
  ["Settings updated", "Notification preferences changed", "43 min ago"],
  ["User account created", "alex@example.com", "1 hr ago"],
  ["System health viewed", "All services operational", "2 hrs ago"],
];
