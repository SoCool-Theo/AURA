import { useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { Portfolio } from '../../types/portfolio';
import { go } from '../../app/routes';
import { Icon } from '../../components/ui/Icon';
import { RiskPill } from '../../components/ui/RiskPill';
import { SymbolBadge } from '../../components/ui/SymbolBadge';
import { clamp } from '../../utils/uiCalculations';
import { ActivityTab } from './components/ActivityTab';
import { HoldingsTab } from './components/HoldingsTab';
import { PerformanceTab } from './components/PerformanceTab';
import { PortfolioOverviewTab } from './components/PortfolioOverviewTab';

interface PortfolioDetailPageProps {
  portfolio?: Portfolio;
  setPortfolios: Dispatch<SetStateAction<Portfolio[]>>;
}

type PortfolioTab = 'Overview' | 'Holdings' | 'Performance' | 'Activity';

const PORTFOLIO_TABS: PortfolioTab[] = ['Overview', 'Holdings', 'Performance', 'Activity'];

export function PortfolioDetailPage({ portfolio, setPortfolios }: PortfolioDetailPageProps) {
  const [tab, setTab] = useState<PortfolioTab>('Overview');
  const [menu, setMenu] = useState(false);

  if (!portfolio) return null;
  const currentPortfolio = portfolio;

  function rename() {
    const name = prompt('New portfolio name', currentPortfolio.name);
    if (name?.trim()) {
      setPortfolios(previous => previous.map(item => (
        item.id === currentPortfolio.id ? { ...item, name: name.trim() } : item
      )));
    }
  }

  function updateWeight(symbol: string, next: string) {
    const weight = clamp(Number(next) || 0, 0, 100);
    setPortfolios(previous => previous.map(item => (
      item.id !== currentPortfolio.id
        ? item
        : {
          ...item,
          holdings: item.holdings.map(holding => (
            holding.symbol === symbol ? { ...holding, weight } : holding
          )),
        }
    )));
  }

  return (
    <div className="page portfolio-detail-page">
      <button className="detail-back-link" onClick={() => go('portfolios')}>← Back to Portfolios</button>
      <section className="portfolio-detail-header">
        <div className="detail-identity">
          <SymbolBadge symbol={portfolio.name.slice(0, 2).toUpperCase()} />
          <div>
            <div className="detail-title-row">
              <h1>{portfolio.name}</h1>
              <button aria-label="Rename portfolio" onClick={rename}>✎</button>
              <RiskPill score={portfolio.riskScore} />
            </div>
            <p>Created {new Date(portfolio.created).toLocaleDateString()} <span>•</span> Last analyzed May 11, 2026</p>
          </div>
        </div>
        <div className="detail-header-actions">
          <button className="primary-btn" onClick={() => go(`analytics/${portfolio.id}`)}>View Analysis <span>→</span></button>
          <div className="relative">
            <button className="secondary-btn detail-more-btn" onClick={() => setMenu(!menu)} aria-expanded={menu}>
              More <Icon name="chevron-down" size={16} />
            </button>
            {menu && (
              <div className="menu-pop detail-menu">
                <button onClick={() => { rename(); setMenu(false); }}>Rename portfolio</button>
                <button onClick={() => go(`simulations/${portfolio.id}`)}>Run simulation</button>
                <button onClick={() => go('reports')}>View reports</button>
              </div>
            )}
          </div>
        </div>
      </section>

      <nav className="detail-tabs" aria-label="Portfolio sections" role="tablist">
        {PORTFOLIO_TABS.map(item => (
          <button
            role="tab"
            aria-selected={tab === item}
            className={tab === item ? 'active' : ''}
            onClick={() => setTab(item)}
            key={item}
          >
            {item}{item === 'Holdings' && <span>{portfolio.holdings.length}</span>}
          </button>
        ))}
      </nav>

      {tab === 'Overview' && <PortfolioOverviewTab portfolio={portfolio} onViewHoldings={() => setTab('Holdings')} />}
      {tab === 'Holdings' && <HoldingsTab portfolio={portfolio} onUpdateWeight={updateWeight} />}
      {tab === 'Performance' && <PerformanceTab portfolio={portfolio} />}
      {tab === 'Activity' && <ActivityTab portfolio={portfolio} />}
    </div>
  );
}
