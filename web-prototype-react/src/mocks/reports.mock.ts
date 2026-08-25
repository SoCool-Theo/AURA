import type { ReportSummary } from '../types/report';

export const reportsSeed: ReportSummary[] = [
  { id: 1, name: 'Tech Portfolio Analysis', portfolio: 'Tech Portfolio', type: 'Analysis', date: 'May 11, 2026', riskScore: 72 },
  { id: 2, name: '2008 Financial Crisis Simulation', portfolio: 'Tech Portfolio', type: 'Simulation', date: 'May 11, 2026', riskScore: null },
  { id: 3, name: 'Allocation Change Simulation', portfolio: 'Tech Portfolio', type: 'Simulation', date: 'May 9, 2026', riskScore: null },
  { id: 4, name: 'Balanced Portfolio Analysis', portfolio: 'Balanced Portfolio', type: 'Analysis', date: 'May 7, 2026', riskScore: 48 },
  { id: 5, name: 'Tech vs Balanced Comparison', portfolio: 'Recommended', type: 'Comparison', date: 'May 6, 2026', riskScore: null },
  { id: 6, name: 'Retirement Fund Analysis', portfolio: 'Retirement Fund', type: 'Analysis', date: 'May 5, 2026', riskScore: 32 },
];
