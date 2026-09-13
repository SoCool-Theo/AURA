import type { PortfolioSummaryResponse } from '../../../types/portfolio';
import type { PortfolioReportResponse } from '../../../types/report';
import { DateRangeSelector } from './DateRangeSelector';
import { PortfolioSelector } from './PortfolioSelector';

interface Props { firstName: string; portfolios: PortfolioSummaryResponse[]; selectedId: string; report: PortfolioReportResponse | null; onSelectPortfolio: (id: string) => void }

export function DashboardHeader({ firstName, portfolios, selectedId, report, onSelectPortfolio }: Props) {
  return <section className="dashboard-hero"><svg className="dashboard-wave" viewBox="0 0 900 120" preserveAspectRatio="none" aria-hidden="true"><path d="M0 77 C80 31 125 105 205 60 S330 28 395 68 510 96 580 48 690 28 760 58 900 35" /><path className="wave-dots" d="M0 92 C95 45 145 116 230 72 S360 42 430 79 555 105 630 62 740 45 900 57" /></svg><div className="dashboard-greeting"><h1>Welcome, {firstName}! <span aria-hidden="true">👋</span></h1><p>Review current holdings, planned allocations, and saved risk reports.</p></div><div className="dashboard-selectors"><PortfolioSelector portfolios={portfolios} selectedId={selectedId} onSelect={onSelectPortfolio} /><DateRangeSelector startDate={report?.analysis.start_date} endDate={report?.analysis.end_date} /></div></section>;
}
