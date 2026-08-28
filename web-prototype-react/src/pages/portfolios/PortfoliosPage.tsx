import { useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { Portfolio } from '../../types/portfolio';
import { go } from '../../app/routes';
import { PortfolioCard } from '../../components/portfolio/PortfolioCard';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { AuraSelect } from '../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../components/ui/AuraSelect';
import { money, pct } from '../../utils/formatting';
import { slug } from '../../utils/uiCalculations';

interface PortfoliosPageProps {
  portfolios: Portfolio[];
  setPortfolios: Dispatch<SetStateAction<Portfolio[]>>;
}

interface PortfolioSummaryProps {
  label: string;
  value: string | number;
  detail: string;
  icon: string;
  tone: string;
}

const riskFilterOptions: ReadonlyArray<AuraSelectOption<string>> = [
  { value: 'all', label: 'All risk levels', description: 'Show every portfolio risk level', icon: 'shield', tone: 'teal' },
  { value: 'low', label: 'Low risk', description: 'Lower historical volatility and risk', icon: 'shield', tone: 'green' },
  { value: 'moderate', label: 'Moderate risk', description: 'Balanced historical risk and return', icon: 'shield', tone: 'amber' },
  { value: 'high', label: 'High risk', description: 'Higher historical volatility and risk', icon: 'shield', tone: 'red' },
];

const sortOptions: ReadonlyArray<AuraSelectOption<string>> = [
  { value: 'recent', label: 'Recently created', description: 'Newest portfolios appear first', icon: 'calendar', tone: 'teal' },
  { value: 'value', label: 'Highest value', description: 'Largest saved portfolio value first', icon: 'wallet', tone: 'blue' },
  { value: 'return', label: 'Highest return', description: 'Strongest historical return first', icon: 'trend', tone: 'green' },
  { value: 'risk', label: 'Highest risk', description: 'Largest saved risk score first', icon: 'shield', tone: 'red' },
];

function PortfolioSummary({ label, value, detail, icon, tone }: PortfolioSummaryProps) {
  return (
    <Card className={`portfolio-summary-card ${tone}`}>
      <span className="summary-icon"><Icon name={icon} size={21} /></span>
      <div><small>{label}</small><strong>{value}</strong><span>{detail}</span></div>
    </Card>
  );
}

export function PortfoliosPage({ portfolios, setPortfolios }: PortfoliosPageProps) {
  const [query, setQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [sortBy, setSortBy] = useState('recent');
  const [editing, setEditing] = useState<string | null>(null);
  const riskLevel = (portfolio: Portfolio) => portfolio.riskScore >= 70
    ? 'high'
    : portfolio.riskScore >= 55
      ? 'moderate'
      : 'low';
  const visible = portfolios
    .filter(portfolio => portfolio.name.toLowerCase().includes(query.toLowerCase()))
    .filter(portfolio => riskFilter === 'all' || riskLevel(portfolio) === riskFilter)
    .sort((left, right) => {
      if (sortBy === 'value') return right.value - left.value;
      if (sortBy === 'risk') return right.riskScore - left.riskScore;
      if (sortBy === 'return') return right.totalReturn - left.totalReturn;
      return new Date(right.created).getTime() - new Date(left.created).getTime();
    });
  const combinedValue = portfolios.reduce((sum, portfolio) => sum + portfolio.value, 0);
  const averageReturn = portfolios.length
    ? portfolios.reduce((sum, portfolio) => sum + portfolio.totalReturn, 0) / portfolios.length
    : 0;
  const averageRisk = portfolios.length
    ? Math.round(portfolios.reduce((sum, portfolio) => sum + portfolio.riskScore, 0) / portfolios.length)
    : 0;
  const trackedAssets = new Set(
    portfolios.flatMap(portfolio => portfolio.holdings.map(holding => holding.symbol)),
  ).size;

  function duplicate(portfolio: Portfolio) {
    const copy = {
      ...portfolio,
      id: `${slug(portfolio.name)}-${Date.now()}`,
      name: `${portfolio.name} Copy`,
      created: new Date().toISOString().slice(0, 10),
      holdings: portfolio.holdings.map(holding => ({ ...holding })),
    };
    setPortfolios(previous => [...previous, copy]);
  }

  function remove(portfolio: Portfolio) {
    if (confirm(`Delete ${portfolio.name}?`)) {
      setPortfolios(previous => previous.filter(item => item.id !== portfolio.id));
    }
  }

  function rename(portfolio: Portfolio) {
    const name = prompt('New portfolio name', portfolio.name);
    if (name?.trim()) {
      setPortfolios(previous => previous.map(item => (
        item.id === portfolio.id ? { ...item, name: name.trim() } : item
      )));
    }
  }

  return (
    <div className="page portfolios-page">
      <section className="portfolios-hero">
        <div>
          <h1>Portfolios</h1>
          <p>Create, organize, and monitor the portfolios you use for risk analysis.</p>
        </div>
        <button className="primary-btn new-portfolio-btn" onClick={() => go('create')}>
          <span>＋</span> New Portfolio
        </button>
      </section>

      <div className="portfolio-summary-grid">
        <PortfolioSummary label="Total Portfolios" value={portfolios.length} detail="Active portfolios" icon="portfolios" tone="purple" />
        <PortfolioSummary label="Combined Value" value={money(combinedValue)} detail="Across all portfolios" icon="wallet" tone="blue" />
        <PortfolioSummary label="Average Return" value={pct(averageReturn)} detail="Historical annualized" icon="trend" tone="green" />
        <PortfolioSummary label="Average Risk" value={`${averageRisk}/100`} detail={`${trackedAssets} unique assets tracked`} icon="shield" tone="amber" />
      </div>

      <Card className="portfolio-toolbar">
        <label className="portfolio-search">
          <Icon name="search" size={19} />
          <span className="sr-only">Search portfolios</span>
          <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search portfolios..." />
        </label>
        <div className="portfolio-toolbar-controls">
          <AuraSelect className="portfolio-filter" ariaLabel="Filter by risk" value={riskFilter} options={riskFilterOptions} onChange={setRiskFilter} />
          <AuraSelect className="portfolio-filter" ariaLabel="Sort portfolios" value={sortBy} options={sortOptions} onChange={setSortBy} />
        </div>
      </Card>

      <div className="portfolio-section-heading">
        <div><h2>Your Portfolios</h2><p>{visible.length} of {portfolios.length} portfolios</p></div>
      </div>
      {visible.length ? (
        <div className="portfolio-grid">
          {visible.map(portfolio => (
            <PortfolioCard
              key={portfolio.id}
              portfolio={portfolio}
              menuOpen={editing === portfolio.id}
              onToggleMenu={() => setEditing(editing === portfolio.id ? null : portfolio.id)}
              onRename={() => { rename(portfolio); setEditing(null); }}
              onDuplicate={() => { duplicate(portfolio); setEditing(null); }}
              onDelete={() => { remove(portfolio); setEditing(null); }}
              onOpenPortfolio={() => go(`portfolio/${portfolio.id}`)}
              onViewAnalysis={() => go(`analytics/${portfolio.id}`)}
            />
          ))}
        </div>
      ) : (
        <Card className="portfolio-empty-state">
          <span><Icon name="search" size={25} /></span>
          <h3>No portfolios found</h3>
          <p>Try a different search term or risk filter.</p>
          <button className="secondary-btn" onClick={() => { setQuery(''); setRiskFilter('all'); }}>
            Clear filters
          </button>
        </Card>
      )}
    </div>
  );
}
