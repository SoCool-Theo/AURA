import { Card } from '../../../components/ui/Card';
import type { PortfolioResponse } from '../../../types/portfolio';
import { formatPortfolioDate } from '../portfolioUi';

export function ActivityTab({ portfolio }: { portfolio: PortfolioResponse }) {
  return (
    <div className="detail-tab-panel">
      <Card className="detail-section-card">
        <div className="detail-section-header">
          <div>
            <h2>Portfolio Record</h2>
            <p>Aura currently records when this portfolio was created and last updated.</p>
          </div>
        </div>
        <dl>
          <div><dt>Created</dt><dd>{formatPortfolioDate(portfolio.created_at)}</dd></div>
          <div><dt>Updated</dt><dd>{formatPortfolioDate(portfolio.updated_at)}</dd></div>
        </dl>
      </Card>
    </div>
  );
}
