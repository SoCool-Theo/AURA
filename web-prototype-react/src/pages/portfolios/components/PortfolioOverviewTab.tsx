import { HoldingsTable } from '../../../components/portfolio/HoldingsTable';
import type { PortfolioResponse } from '../../../types/portfolio';

type PortfolioOverviewTabProps = {
  portfolio: PortfolioResponse;
  onViewHoldings: () => void;
};

export function PortfolioOverviewTab({
  portfolio,
  onViewHoldings,
}: PortfolioOverviewTabProps) {
  return (
    <div className="detail-tab-panel">
      <HoldingsTable portfolio={portfolio} onViewAll={onViewHoldings} />
    </div>
  );
}
