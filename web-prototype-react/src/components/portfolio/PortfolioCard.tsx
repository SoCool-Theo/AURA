import type { PortfolioSummaryResponse } from '../../types/portfolio';
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
          <small>Created</small>
          <strong>{new Date(portfolio.created_at).toLocaleDateString()}</strong>
        </div>
        <div>
          <small>Last Updated</small>
          <strong>{new Date(portfolio.updated_at).toLocaleDateString()}</strong>
        </div>
        <div>
          <small>Portfolio ID</small>
          <strong>{portfolio.id.slice(0, 8)}<span>…</span></strong>
        </div>
      </div>
      <div className="portfolio-card-actions">
        <button className="primary-btn" onClick={onOpenPortfolio} disabled={busy}>
          Open Portfolio <span>→</span>
        </button>
      </div>
    </Card>
  );
}
