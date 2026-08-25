import type { Portfolio } from '../../types/portfolio';
import { money, pct } from '../../utils/formatting';
import { Card } from '../ui/Card';
import { RiskPill } from '../ui/RiskPill';
import { SymbolBadge } from '../ui/SymbolBadge';
import { AllocationLegend } from './AllocationLegend';

interface PortfolioCardProps {
  portfolio: Portfolio;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onRename: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onOpenPortfolio: () => void;
  onViewAnalysis: () => void;
}

export function PortfolioCard({
  portfolio,
  menuOpen,
  onToggleMenu,
  onRename,
  onDuplicate,
  onDelete,
  onOpenPortfolio,
  onViewAnalysis,
}: PortfolioCardProps) {
  return (
    <Card className="portfolio-card">
      <div className="portfolio-card-head">
        <div className="portfolio-identity">
          <SymbolBadge symbol={portfolio.name.slice(0, 2).toUpperCase()} />
          <div>
            <h3>{portfolio.name}</h3>
            <small>Created {new Date(portfolio.created).toLocaleDateString()}</small>
          </div>
        </div>
        <div className="portfolio-card-head-actions">
          <RiskPill score={portfolio.riskScore} />
          <button
            className="portfolio-menu-button"
            aria-label={`Actions for ${portfolio.name}`}
            onClick={onToggleMenu}
          >
            •••
          </button>
        </div>
        {menuOpen && (
          <div className="menu-pop portfolio-menu">
            <button onClick={onRename}>Rename</button>
            <button onClick={onDuplicate}>Duplicate</button>
            <button className="danger" onClick={onDelete}>Delete</button>
          </div>
        )}
      </div>
      <div className="portfolio-card-metrics">
        <div>
          <small>Portfolio Value</small>
          <strong>{money(portfolio.value)}</strong>
        </div>
        <div>
          <small>Annualized Return</small>
          <strong className="green-text">{pct(portfolio.totalReturn)}</strong>
        </div>
        <div>
          <small>Risk Score</small>
          <strong>{portfolio.riskScore}<span>/100</span></strong>
        </div>
      </div>
      <AllocationLegend holdings={portfolio.holdings} />
      <div className="portfolio-card-actions">
        <button className="secondary-btn" onClick={onOpenPortfolio}>
          Open Portfolio <span>→</span>
        </button>
        <button className="primary-btn" onClick={onViewAnalysis}>View Analysis</button>
      </div>
    </Card>
  );
}
