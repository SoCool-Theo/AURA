export type PageKey = "dashboard" | "users" | "portfolios" | "market" | "reports" | "health" | "ai" | "activity" | "settings";

export type UserRecord = {
  id: number;
  name: string;
  email: string;
  role: "Investor" | "Admin";
  status: "Active" | "Suspended";
  portfolios: number;
};

export type AdminSettings = {
  adminName: string;
  email: string;
  roleLabel: string;
  appearance: "dark" | "light" | "system";
  compactSidebar: boolean;
  emailAlerts: boolean;
  securityAlerts: boolean;
  failedUpdateAlerts: boolean;
  weeklySummary: boolean;
  requireMfa: boolean;
  sessionTimeout: string;
  marketSchedule: string;
  timezone: string;
  maintenanceMode: boolean;
  allowRegistration: boolean;
};
