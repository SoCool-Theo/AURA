export type ReportSummary = {
  id: number;
  name: string;
  portfolio: string;
  type: 'Analysis' | 'Simulation' | 'Comparison';
  date: string;
  riskScore: number | null;
};
