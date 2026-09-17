import type { PortfolioReportResponse } from '../../../types/report';
import { DateRangeSelector } from './DateRangeSelector';

interface Props { firstName: string; report: PortfolioReportResponse | null }

export function DashboardHeader({ firstName, report }: Props) {
  return <section className="dashboard-hero"><svg className="dashboard-wave" viewBox="0 0 900 120" preserveAspectRatio="none" aria-hidden="true"><path d="M0 77 C80 31 125 105 205 60 S330 28 395 68 510 96 580 48 690 28 760 58 900 35" /><path className="wave-dots" d="M0 92 C95 45 145 116 230 72 S360 42 430 79 555 105 630 62 740 45 900 57" /></svg><div className="dashboard-greeting"><h1>Welcome, {firstName}! <span aria-hidden="true">👋</span></h1><p>Review current holdings, planned allocations, and saved risk reports.</p></div><div className="dashboard-selectors"><DateRangeSelector startDate={report?.analysis.start_date} endDate={report?.analysis.end_date} /></div></section>;
}
