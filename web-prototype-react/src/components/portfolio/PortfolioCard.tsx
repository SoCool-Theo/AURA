import type { PortfolioSummaryResponse } from '../../types/portfolio';
import { portfolioTypeLabel } from '../../pages/portfolios/portfolioUi';
import { Card } from '../ui/Card';
import { SymbolBadge } from '../ui/SymbolBadge';

interface PortfolioCardProps {
  portfolio: PortfolioSummaryResponse;
  busy: boolean;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onRename: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onOpenPortfolio: () => void;
  onOpenLatestReport?: () => void;
}

export function PortfolioCard({
  portfolio,
  busy,
  menuOpen,
  onToggleMenu,
  onRename,
  onDuplicate,
  onDelete,
  onOpenPortfolio,
  onOpenLatestReport,
}: PortfolioCardProps) {
  return (
    <Card className="portfolio-card">
      <div className="portfolio-card-head">
        <div className="portfolio-identity">
          <SymbolBadge symbol={portfolio.name.slice(0, 2).toUpperCase()} />
          <div>
            <h3>{portfolio.name}</h3>
            <small>Created {new Date(portfolio.created_at).toLocaleDateString()}</small>
          </div>
        </div>
        <div className="portfolio-card-head-actions">
          <span className={`portfolio-mode-pill ${portfolio.portfolio_type.toLowerCase()}`}>
            {portfolioTypeLabel(portfolio.portfolio_type)}
          </span>
          <button
            className="portfolio-menu-button"
            aria-label={`Actions for ${portfolio.name}`}
            onClick={onToggleMenu}
            disabled={busy}
          >
            •••
          </button>
        </div>
        {menuOpen && (
          <div className="menu-pop portfolio-menu">
            <button onClick={onRename} disabled={busy}>Rename</button>
            <button onClick={onDuplicate} disabled={busy}>Duplicate</button>
            <button className="danger" onClick={onDelete} disabled={busy}>Delete</button>
          </div>
        )}
      </div>
      <div className="portfolio-card-metrics">
        <div>
          <small>Portfolio Type</small>
          <strong>{portfolio.portfolio_type === 'PLANNED' ? 'Planned' : portfolio.portfolio_type === 'LEGACY' ? 'Legacy' : 'Current'}</strong>
        </div>
        <div>
          <small>Updated</small>
          <strong>{new Date(portfolio.updated_at).toLocaleDateString()}</strong>
        </div>
        <div>
          <small>{portfolio.portfolio_type === 'PLANNED' ? 'Plan Currency' : 'Status'}</small>
          <strong>{portfolio.portfolio_type === 'PLANNED'
            ? portfolio.plan_currency
            : portfolio.portfolio_type === 'LEGACY'
              ? 'Saved weights'
              : 'Actual holdings'}</strong>
        </div>
      </div>
      <div className={`portfolio-card-actions ${onOpenLatestReport ? '' : 'single-action'}`}>
        <button className="primary-btn" onClick={onOpenPortfolio} disabled={busy}>
          Open Portfolio <span>→</span>
        </button>
        {onOpenLatestReport && (
          <button className="secondary-btn" onClick={onOpenLatestReport} disabled={busy}>
            View Latest Report
          </button>
        )}
      </div>
    </Card>
  );
}
