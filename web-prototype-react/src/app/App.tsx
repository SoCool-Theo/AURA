// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { usePersistedState } from '../hooks/usePersistedState';
import { correlation } from '../mocks/analytics.mock';
import { downturnA, downturnB, lineA, lineB } from '../mocks/dashboard.mock';
import { defaultPortfolios } from '../mocks/portfolios.mock';
import { reportsSeed } from '../mocks/reports.mock';
import { defaultSettings } from '../mocks/settings.mock';
import { scenarioOptions } from '../mocks/simulations.mock';
import { watchlistSeed } from '../mocks/watchlist.mock';
import { money, pct } from '../utils/formatting';
import { clamp, slug } from '../utils/uiCalculations';
import { navItems } from './navigation';
import { go, routeFromHash } from './routes';

function App() {
  const [route, setRoute] = useState(routeFromHash());
  const [portfolios, setPortfolios] = usePersistedState('aura-portfolios', defaultPortfolios);
  const [reports, setReports] = usePersistedState('aura-reports', reportsSeed);
  const [watchlist, setWatchlist] = usePersistedState('aura-watchlist', watchlistSeed);
  const [settings, setSettings] = usePersistedState('aura-settings', defaultSettings);

  useEffect(() => {
    const handler = () => setRoute(routeFromHash());
    window.addEventListener('hashchange', handler);
    if (!window.location.hash) go('dashboard');
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const activePortfolio = portfolios.find(p => p.id === (route.id || 'tech')) || portfolios[0];
  const shared = { portfolios, setPortfolios, reports, setReports, watchlist, setWatchlist, settings, setSettings };

  let content;
  switch (route.page) {
    case 'dashboard': content = <Dashboard {...shared} />; break;
    case 'portfolios': content = <Portfolios {...shared} />; break;
    case 'portfolio': content = <PortfolioDetail portfolio={activePortfolio} {...shared} />; break;
    case 'analytics': content = <Analytics portfolio={activePortfolio} {...shared} />; break;
    case 'simulations': content = <Simulations portfolio={activePortfolio} {...shared} />; break;
    case 'assistant': content = <Assistant portfolio={activePortfolio} />; break;
    case 'reports': content = <Reports reports={reports} setReports={setReports} />; break;
    case 'watchlist': content = <Watchlist watchlist={watchlist} setWatchlist={setWatchlist} />; break;
    case 'learn': content = <Learn />; break;
    case 'create': content = <CreatePortfolio portfolios={portfolios} setPortfolios={setPortfolios} />; break;
    case 'settings': content = <Settings settings={settings} setSettings={setSettings} />; break;
    default: content = <Dashboard {...shared} />;
  }

  return (
    <div className="app-shell">
      <TopNavigation route={route} settings={settings} />
      <main className="main-area">
        {content}
      </main>
    </div>
  );
}

function Icon({ name, size = 20 }) {
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true
  };

  switch (name) {
    case 'dashboard': return <svg {...common}><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5M9 21v-7h6v7"/></svg>;
    case 'portfolios': return <svg {...common}><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/></svg>;
    case 'analytics': return <svg {...common}><path d="m12 3 9 9-9 9-9-9 9-9Z"/><circle cx="12" cy="12" r="3"/></svg>;
    case 'simulations': return <svg {...common}><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16M15 4v16"/></svg>;
    case 'assistant': return <svg {...common}><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3"/></svg>;
    case 'reports': return <svg {...common}><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h8"/></svg>;
    case 'search': return <svg {...common}><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>;
    case 'bell': return <svg {...common}><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>;
    case 'chevron-down': return <svg {...common}><path d="m7 9.5 5 5 5-5"/></svg>;
    case 'wallet': return <svg {...common}><path d="M4 7h16v12H4zM7 7V4h9v3M16 12h4"/></svg>;
    case 'calendar': return <svg {...common}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></svg>;
    case 'trend': return <svg {...common}><path d="m3 17 6-6 4 4 8-9"/><path d="M15 6h6v6"/></svg>;
    case 'shield': return <svg {...common}><path d="M12 3 4.5 6v5c0 5 3.2 8.3 7.5 10 4.3-1.7 7.5-5 7.5-10V6L12 3Z"/><path d="m9 12 2 2 4-5"/></svg>;
    case 'drawdown': return <svg {...common}><path d="m3 7 6 6 4-4 8 8"/><path d="M15 17h6v-6"/></svg>;
    case 'spark': return <svg {...common}><path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z"/></svg>;
    case 'analysis': return <svg {...common}><circle cx="12" cy="12" r="7"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/><circle cx="12" cy="12" r="2"/></svg>;
    default: return null;
  }
}

function TopNavigation({ route, settings }) {
  const [open, setOpen] = useState(false);
  const initials = settings?.name?.split(/\s+/).map(part => part[0]).slice(0, 2).join('').toUpperCase() || 'YL';
  const isActive = key => route.page === key || (key === 'portfolios' && ['portfolio', 'create'].includes(route.page));

  return (
    <header className="top-nav">
      <div className="top-nav-inner">
        <button className="brand" onClick={() => go('dashboard')} aria-label="Go to dashboard">
          <span className="brand-mark">A</span><span>AURA</span>
        </button>
        <nav className="nav-list" aria-label="Primary navigation">
          {navItems.map(([key, icon, label]) => {
            const active = isActive(key);
            return <button key={key} className={`nav-item ${active ? 'active' : ''}`} aria-current={active?'page':undefined} onClick={() => go(key)}>
              <span className="nav-icon"><Icon name={icon} size={18}/></span><span>{label}</span>
            </button>;
          })}
        </nav>
        <div className="top-nav-actions">
          <button className="nav-action" aria-label="Search"><Icon name="search" size={21}/></button>
          <button className="nav-action notification-button" aria-label="Notifications">
            <Icon name="bell" size={21}/><span className="notification-dot" aria-hidden="true" />
          </button>
          <div className="profile-menu-wrap">
            <button className="profile-trigger" onClick={() => setOpen(value => !value)} aria-label="Open user menu" aria-expanded={open} aria-haspopup="menu">
              <span className="avatar">{initials}</span><span className="chevron"><Icon name="chevron-down" size={17}/></span>
            </button>
            {open && <div className="profile-menu" role="menu">
              <strong>{settings?.name || 'Aura User'}</strong>
              <small>{settings?.email || 'Portfolio owner'}</small>
              <button role="menuitem" onClick={() => { setOpen(false); go('settings'); }}>Settings</button>
              <button role="menuitem" onClick={() => { setOpen(false); go('watchlist'); }}>Watchlist</button>
              <button role="menuitem" onClick={() => { setOpen(false); go('learn'); }}>Learn</button>
            </div>}
          </div>
        </div>
      </div>
    </header>
  );
}

function PageHeader({ title, subtitle, actions }) {
  return <header className="page-header"><div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div><div className="header-actions">{actions}</div></header>;
}

function Card({ children, className = '' }) {
  return <section className={`card ${className}`}>{children}</section>;
}

function StatCard({ label, value, sub, tone = 'purple', spark = lineA.slice(0, 12) }) {
  return <Card className="stat-card"><small>{label}</small><strong>{value}</strong><span className={`stat-sub ${tone}`}>{sub}</span><MiniLine values={spark} /></Card>;
}

function MiniLine({ values }) {
  const points = svgPoints(values, 160, 36, 4);
  return <svg className="mini-line" viewBox="0 0 160 36" preserveAspectRatio="none"><polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" /></svg>;
}

function svgPoints(values, width, height, pad = 8) {
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  return values.map((v, i) => {
    const x = pad + (i / Math.max(1, values.length - 1)) * (width - pad * 2);
    const y = height - pad - ((v - min) / span) * (height - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
}

function LineChart({ primary = lineA, secondary, labels = ['Jan 21', 'Nov 21', 'Sep 22', 'Jul 23', 'May 24', 'May 26'], height = 210, negative = false, area = false }) {
  const all = secondary ? [...primary, ...secondary] : primary;
  const min = Math.min(...all, negative ? -50 : 0), max = Math.max(...all, 10);
  const normalized = arr => arr.map((v, i) => {
    const x = 14 + (i / Math.max(1, arr.length - 1)) * 672;
    const y = 14 + ((max - v) / (max - min || 1)) * (height - 42);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 700 ${height}`} className="line-chart" preserveAspectRatio="none">
        {area && <defs><linearGradient id="performance-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#765CFF" stopOpacity=".34"/><stop offset="100%" stopColor="#765CFF" stopOpacity=".02"/></linearGradient></defs>}
        {[0.25, 0.5, 0.75].map(n => <line key={n} x1="14" y1={height*n} x2="686" y2={height*n} className="grid-line" />)}
        {negative && <line x1="14" y1={14 + (max / (max - min)) * (height - 42)} x2="686" y2={14 + (max / (max - min)) * (height - 42)} className="zero-line" />}
        {area && <polygon points={`14,${height - 28} ${normalized(primary)} 686,${height - 28}`} fill="url(#performance-area)" />}
        {secondary && <polyline points={normalized(secondary)} fill="none" className="secondary-line" strokeWidth="2.2" vectorEffect="non-scaling-stroke" />}
        <polyline points={normalized(primary)} fill="none" className="primary-line" strokeWidth="3" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="chart-labels">{labels.map(l => <span key={l}>{l}</span>)}</div>
    </div>
  );
}

function RiskGauge({ score = 65, label = 'Moderate' }) {
  const deg = clamp(score, 0, 100) * 1.8;
  return <div className="gauge-block"><div className="gauge" style={{'--score-deg': `${deg}deg`}}><div className="gauge-inner"><strong>{score}</strong><small>{label}</small></div></div></div>;
}

function Donut({ holdings }) {
  const colors = ['#5844E5', '#1160F8', '#11B89D', '#F2A121', '#A855F7', '#3B82F6'];
  let offset = 0;
  const circles = holdings.slice(0, 6).map((h, i) => {
    const dash = `${h.weight} ${100 - h.weight}`;
    const node = <circle key={h.symbol} cx="50" cy="50" r="34" fill="none" stroke={colors[i % colors.length]} strokeWidth="15" strokeDasharray={dash} strokeDashoffset={-offset} pathLength="100" />;
    offset += h.weight;
    return node;
  });
  return <svg className="donut" viewBox="0 0 100 100" transform="rotate(-90)">{circles}<circle cx="50" cy="50" r="24" fill="var(--bg-card)" /></svg>;
}

function RiskPill({ score }) {
  const level = score >= 70 ? 'high' : score >= 55 ? 'moderate' : 'low';
  return <span className={`pill ${level}`}>{score} · {level === 'high' ? 'High' : level === 'moderate' ? 'Moderate' : 'Low'}</span>;
}

function Dashboard({ portfolios, settings }) {
  const [selectedId, setSelectedId] = useState(portfolios[0]?.id || '');
  const portfolio = portfolios.find(item => item.id === selectedId) || portfolios[0];
  if (!portfolio) return null;

  const firstName = settings?.name?.split(/\s+/)[0] || 'Yan';
  const annualizedReturn = Number(portfolio.annualizedReturn ?? portfolio.totalReturn ?? 0);
  const riskLabel = String(portfolio.riskLevel || 'Moderate').replace(/\s+Risk$/i, '');
  const riskDrivers = portfolio.holdings.filter(item => item.symbol !== 'CASH').slice(0, 3);
  const allocation = Object.values(portfolio.holdings.reduce((groups, holding) => {
    const label = holding.type === 'Cash' ? 'Cash' : holding.type.includes('Bond') ? 'Bonds' : holding.type.includes('Crypto') ? 'Crypto' : 'Equity';
    groups[label] = groups[label] || { symbol: label, type: label, weight: 0 };
    groups[label].weight += Number(holding.weight || 0);
    return groups;
  }, {}));

  return (
    <div className="page dashboard-page">
      <section className="dashboard-hero">
        <svg className="dashboard-wave" viewBox="0 0 900 120" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 77 C80 31 125 105 205 60 S330 28 395 68 510 96 580 48 690 28 760 58 900 35" />
          <path className="wave-dots" d="M0 92 C95 45 145 116 230 72 S360 42 430 79 555 105 630 62 740 45 900 57" />
        </svg>
        <div className="dashboard-greeting">
          <h1>Good evening, {firstName}! <span aria-hidden="true">👋</span></h1>
          <p>Here's your portfolio overview and key insights.</p>
        </div>
        <div className="dashboard-selectors">
          <label className="dashboard-selector">
            <Icon name="wallet" size={19}/>
            <span className="sr-only">Portfolio</span>
            <select value={portfolio.id} onChange={event => setSelectedId(event.target.value)}>
              {portfolios.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <span className="selector-chevron"><Icon name="chevron-down" size={17}/></span>
          </label>
          <button className="dashboard-selector date-selector" aria-label="Selected date: May 11, 2026"><Icon name="calendar" size={19}/><span>May 11, 2026</span><span className="selector-chevron"><Icon name="chevron-down" size={17}/></span></button>
        </div>
      </section>

      <div className="dashboard-kpis">
        <DashboardKpi title="Total Portfolio Value" icon="wallet" tone="purple" visual={<MiniLine values={lineA.slice(12)} />}>
          <strong>{money(portfolio.value)}</strong>
          <span className="metric-change positive">▲ {money(portfolio.value * .064)} (6.4%)</span>
        </DashboardKpi>
        <DashboardKpi title="Risk Score" icon="shield" tone="amber" visual={<RiskGauge score={portfolio.riskScore} label="" />}>
          <strong>{portfolio.riskScore}</strong>
          <span className="metric-change warning">{riskLabel}</span>
        </DashboardKpi>
        <DashboardKpi title="Annualized Return" icon="trend" tone="purple" visual={<MiniLine values={lineA.slice(8)} />}>
          <strong>{pct(annualizedReturn)}</strong>
          <span className="metric-change purple-text">Annualized</span>
        </DashboardKpi>
        <DashboardKpi title="Maximum Drawdown" icon="drawdown" tone="red" visual={<MiniLine values={downturnA.slice(6)} />}>
          <strong>-21.45%</strong>
          <span className="metric-change negative">Mar 2020</span>
        </DashboardKpi>
      </div>

      <div className="dashboard-primary-grid">
        <Card className="dashboard-performance-card">
          <div className="dashboard-card-header performance-header">
            <div className="dashboard-card-title"><span className="title-icon"><Icon name="trend" size={22}/></span><h2>Portfolio Performance</h2></div>
            <div className="range-tabs"><button>1M</button><button>6M</button><button>1Y</button><button>3Y</button><button className="active">All</button></div>
            <div className="performance-return"><strong>{pct(annualizedReturn)}</strong><small>Annualized Return</small></div>
          </div>
          <div className="dashboard-chart-axis"><span>$120K</span><span>$100K</span><span>$80K</span><span>$60K</span><span>$40K</span></div>
          <LineChart primary={lineA} height={245} area />
        </Card>

        <Card className="dashboard-risk-card">
          <div className="dashboard-card-header"><div className="dashboard-card-title"><h2>Top Risk Drivers</h2></div><button className="text-btn" onClick={() => go(`analytics/${portfolio.id}`)}>View all</button></div>
          <div className="dashboard-risk-list">
            {riskDrivers.map((holding, index) => <div key={holding.symbol}>
              <SymbolBadge symbol={holding.symbol}/>
              <div><strong>{holding.name}</strong><small>{holding.symbol}</small></div>
              <b>{holding.weight}%</b>
              <span className={`mini-risk ${index < 2 ? 'high' : 'moderate'}`}>{index < 2 ? 'High' : 'Medium'}</span>
            </div>)}
          </div>
        </Card>
      </div>

      <div className="dashboard-bottom-grid">
        <Card className="dashboard-allocation-card">
          <div className="dashboard-card-header"><div className="dashboard-card-title"><span className="title-icon allocation-icon">◔</span><h2>Portfolio Allocation</h2></div></div>
          <div className="dashboard-allocation-body">
            <Donut holdings={allocation}/>
            <div className="dashboard-legend">{allocation.map((item, index) => <div key={item.symbol}><span className={`legend-dot c${index}`}/><span>{item.type}</span><strong>{item.weight.toFixed(1)}%</strong></div>)}</div>
          </div>
        </Card>

        <Card className="dashboard-insight-card">
          <div className="dashboard-card-header"><div className="dashboard-card-title"><span className="title-icon"><Icon name="spark" size={21}/></span><h2>AI Insight</h2></div></div>
          <p>Your portfolio risk score is <strong>{portfolio.riskScore} ({riskLabel})</strong>. Concentration in the largest holdings increases historical drawdown risk. Broader diversification may improve long-term resilience.</p>
          <button className="primary-btn insight-action" onClick={() => go('assistant')}>Ask Aura <span>→</span></button>
        </Card>

        <Card className="dashboard-analysis-card">
          <div className="dashboard-card-header"><div className="dashboard-card-title"><span className="title-icon"><Icon name="analysis" size={22}/></span><h2>Portfolio Analysis</h2></div></div>
          <div className="analysis-status"><p>Last analyzed: May 11, 2026</p><p>Risk score: <strong>{portfolio.riskScore}</strong><span>•</span><b>{riskLabel}</b></p></div>
          <div className="analysis-card-actions">
            <button className="primary-btn" onClick={() => go(`analytics/${portfolio.id}`)}>View Analysis <span>→</span></button>
            <button className="secondary-btn" onClick={() => go(`analytics/${portfolio.id}`)}>Re-analyze <span>↻</span></button>
          </div>
        </Card>
      </div>
    </div>
  );
}

function DashboardKpi({ title, icon, tone, visual, children }) {
  return <Card className={`dashboard-kpi ${tone}`}>
    <div className="metric-heading"><span className="metric-icon"><Icon name={icon} size={21}/></span><span>{title}</span></div>
    <div className="metric-body"><div className="metric-copy">{children}</div><div className="metric-visual">{visual}</div></div>
  </Card>;
}

function CardTitle({ title, right }) {
  return <div className="card-title"><h3>{title}</h3>{right}</div>;
}

function FeatureCard({ icon, title, text, button, onClick, tone = 'purple' }) {
  return <Card className={`feature-card ${tone}`}><div className="feature-icon">{icon}</div><div><h3>{title}</h3><p>{text}</p><button onClick={onClick}>{button}</button></div></Card>;
}

function SymbolBadge({ symbol }) {
  return <span className={`symbol-badge s-${symbol.replace(/[^a-zA-Z]/g,'').slice(0,3).toLowerCase()}`}>{symbol.slice(0,4)}</span>;
}

function Portfolios({ portfolios, setPortfolios }) {
  const [query, setQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [sortBy, setSortBy] = useState('recent');
  const [editing, setEditing] = useState(null);
  const riskLevel = portfolio => portfolio.riskScore >= 70 ? 'high' : portfolio.riskScore >= 55 ? 'moderate' : 'low';
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
  const averageReturn = portfolios.length ? portfolios.reduce((sum, portfolio) => sum + portfolio.totalReturn, 0) / portfolios.length : 0;
  const averageRisk = portfolios.length ? Math.round(portfolios.reduce((sum, portfolio) => sum + portfolio.riskScore, 0) / portfolios.length) : 0;
  const trackedAssets = new Set(portfolios.flatMap(portfolio => portfolio.holdings.map(holding => holding.symbol))).size;

  function duplicate(p) {
    const copy = { ...p, id: `${slug(p.name)}-${Date.now()}`, name: `${p.name} Copy`, created: new Date().toISOString().slice(0,10), holdings: p.holdings.map(h=>({...h})) };
    setPortfolios(prev => [...prev, copy]);
  }
  function remove(p) {
    if (confirm(`Delete ${p.name}?`)) setPortfolios(prev => prev.filter(x=>x.id!==p.id));
  }
  function rename(p) {
    const name = prompt('New portfolio name', p.name);
    if (name?.trim()) setPortfolios(prev=>prev.map(x=>x.id===p.id?{...x,name:name.trim()}:x));
  }

  return <div className="page portfolios-page">
    <section className="portfolios-hero">
      <div><h1>Portfolios</h1><p>Create, organize, and monitor the portfolios you use for risk analysis.</p></div>
      <button className="primary-btn new-portfolio-btn" onClick={()=>go('create')}><span>＋</span> New Portfolio</button>
    </section>

    <div className="portfolio-summary-grid">
      <PortfolioSummary label="Total Portfolios" value={portfolios.length} detail="Active portfolios" icon="portfolios" tone="purple" />
      <PortfolioSummary label="Combined Value" value={money(combinedValue)} detail="Across all portfolios" icon="wallet" tone="blue" />
      <PortfolioSummary label="Average Return" value={pct(averageReturn)} detail="Historical annualized" icon="trend" tone="green" />
      <PortfolioSummary label="Average Risk" value={`${averageRisk}/100`} detail={`${trackedAssets} unique assets tracked`} icon="shield" tone="amber" />
    </div>

    <Card className="portfolio-toolbar">
      <label className="portfolio-search"><Icon name="search" size={19}/><span className="sr-only">Search portfolios</span><input value={query} onChange={event=>setQuery(event.target.value)} placeholder="Search portfolios..."/></label>
      <div className="portfolio-toolbar-controls">
        <label className="portfolio-filter"><span className="sr-only">Filter by risk</span><select value={riskFilter} onChange={event=>setRiskFilter(event.target.value)}><option value="all">All risk levels</option><option value="low">Low risk</option><option value="moderate">Moderate risk</option><option value="high">High risk</option></select><Icon name="chevron-down" size={16}/></label>
        <label className="portfolio-filter"><span className="sr-only">Sort portfolios</span><select value={sortBy} onChange={event=>setSortBy(event.target.value)}><option value="recent">Recently created</option><option value="value">Highest value</option><option value="return">Highest return</option><option value="risk">Highest risk</option></select><Icon name="chevron-down" size={16}/></label>
      </div>
    </Card>

    <div className="portfolio-section-heading"><div><h2>Your Portfolios</h2><p>{visible.length} of {portfolios.length} portfolios</p></div></div>
    {visible.length ? <div className="portfolio-grid">{visible.map(portfolio=><Card key={portfolio.id} className="portfolio-card">
      <div className="portfolio-card-head">
        <div className="portfolio-identity"><SymbolBadge symbol={portfolio.name.slice(0,2).toUpperCase()} /><div><h3>{portfolio.name}</h3><small>Created {new Date(portfolio.created).toLocaleDateString()}</small></div></div>
        <div className="portfolio-card-head-actions"><RiskPill score={portfolio.riskScore}/><button className="portfolio-menu-button" aria-label={`Actions for ${portfolio.name}`} onClick={()=>setEditing(editing===portfolio.id?null:portfolio.id)}>•••</button></div>
        {editing===portfolio.id&&<div className="menu-pop portfolio-menu"><button onClick={()=>{rename(portfolio);setEditing(null)}}>Rename</button><button onClick={()=>{duplicate(portfolio);setEditing(null)}}>Duplicate</button><button className="danger" onClick={()=>{remove(portfolio);setEditing(null)}}>Delete</button></div>}
      </div>
      <div className="portfolio-card-metrics"><div><small>Portfolio Value</small><strong>{money(portfolio.value)}</strong></div><div><small>Annualized Return</small><strong className="green-text">{pct(portfolio.totalReturn)}</strong></div><div><small>Risk Score</small><strong>{portfolio.riskScore}<span>/100</span></strong></div></div>
      <div className="portfolio-allocation-heading"><span>Allocation</span><small>{portfolio.holdings.length} holdings</small></div>
      <div className="portfolio-card-allocation">{portfolio.holdings.slice(0,5).map(holding=><span key={holding.symbol} style={{width:`${holding.weight}%`}} title={`${holding.symbol} ${holding.weight}%`}/>)}</div>
      <div className="holding-chips">{portfolio.holdings.slice(0,4).map(holding=><span key={holding.symbol}><b>{holding.symbol}</b>{holding.weight}%</span>)}{portfolio.holdings.length>4&&<span className="more-holdings">+{portfolio.holdings.length-4} more</span>}</div>
      <div className="portfolio-card-actions"><button className="secondary-btn" onClick={()=>go(`portfolio/${portfolio.id}`)}>Open Portfolio <span>→</span></button><button className="primary-btn" onClick={()=>go(`analytics/${portfolio.id}`)}>View Analysis</button></div>
    </Card>)}</div> : <Card className="portfolio-empty-state"><span><Icon name="search" size={25}/></span><h3>No portfolios found</h3><p>Try a different search term or risk filter.</p><button className="secondary-btn" onClick={()=>{setQuery('');setRiskFilter('all')}}>Clear filters</button></Card>}
  </div>;
}

function PortfolioSummary({ label, value, detail, icon, tone }) {
  return <Card className={`portfolio-summary-card ${tone}`}><span className="summary-icon"><Icon name={icon} size={21}/></span><div><small>{label}</small><strong>{value}</strong><span>{detail}</span></div></Card>;
}

function PortfolioDetail({ portfolio, setPortfolios }) {
  const [tab, setTab] = useState('Overview');
  const [menu, setMenu] = useState(false);
  if (!portfolio) return null;
  const totalWeight = portfolio.holdings.reduce((sum, holding) => sum + Number(holding.weight || 0), 0);
  const riskLabel = String(portfolio.riskLevel || 'Moderate').replace(/\s+Risk$/i, '');
  const cashPercentage = ((portfolio.cash / portfolio.value) * 100 || 0).toFixed(1);

  function rename() {
    const name = prompt('New portfolio name', portfolio.name);
    if (name?.trim()) setPortfolios(prev=>prev.map(x=>x.id===portfolio.id?{...x,name:name.trim()}:x));
  }
  function updateWeight(symbol, next) {
    const n = clamp(Number(next)||0,0,100);
    setPortfolios(prev=>prev.map(p=>p.id!==portfolio.id?p:{...p,holdings:p.holdings.map(h=>h.symbol===symbol?{...h,weight:n}:h)}));
  }
  return <div className="page portfolio-detail-page">
    <button className="detail-back-link" onClick={()=>go('portfolios')}>← Back to Portfolios</button>
    <section className="portfolio-detail-header">
      <div className="detail-identity"><SymbolBadge symbol={portfolio.name.slice(0,2).toUpperCase()}/><div><div className="detail-title-row"><h1>{portfolio.name}</h1><button aria-label="Rename portfolio" onClick={rename}>✎</button><RiskPill score={portfolio.riskScore}/></div><p>Created {new Date(portfolio.created).toLocaleDateString()} <span>•</span> Last analyzed May 11, 2026</p></div></div>
      <div className="detail-header-actions"><button className="primary-btn" onClick={()=>go(`analytics/${portfolio.id}`)}>View Analysis <span>→</span></button><div className="relative"><button className="secondary-btn detail-more-btn" onClick={()=>setMenu(!menu)} aria-expanded={menu}>More <Icon name="chevron-down" size={16}/></button>{menu&&<div className="menu-pop detail-menu"><button onClick={()=>{rename();setMenu(false)}}>Rename portfolio</button><button onClick={()=>go(`simulations/${portfolio.id}`)}>Run simulation</button><button onClick={()=>go('reports')}>View reports</button></div>}</div></div>
    </section>

    <nav className="detail-tabs" aria-label="Portfolio sections" role="tablist">{['Overview','Holdings','Performance','Activity'].map(item=><button role="tab" aria-selected={tab===item} className={tab===item?'active':''} onClick={()=>setTab(item)} key={item}>{item}{item==='Holdings'&&<span>{portfolio.holdings.length}</span>}</button>)}</nav>

    {tab==='Overview' && <div className="detail-tab-panel">
      <div className="detail-metric-grid">
        <PortfolioMetric label="Total Value" value={money(portfolio.value)} detail="Current portfolio value" icon="wallet" tone="purple" />
        <PortfolioMetric label="Annualized Return" value={pct(portfolio.totalReturn)} detail="Historical annualized" icon="trend" tone="green" />
        <PortfolioMetric label="Risk Score" value={`${portfolio.riskScore}/100`} detail={riskLabel} icon="shield" tone="amber" />
        <PortfolioMetric label="Cash Position" value={money(portfolio.cash)} detail={`${cashPercentage}% of portfolio`} icon="wallet" tone="blue" />
      </div>
      <div className="detail-overview-grid">
        <HoldingsTable portfolio={portfolio} onViewAll={()=>setTab('Holdings')}/>
        <Card className="detail-performance-card"><div className="detail-card-heading"><div><h2>Portfolio Performance</h2><p>Cumulative historical return</p></div><div className="range-tabs"><button>1M</button><button>6M</button><button>1Y</button><button>3Y</button><button className="active">All</button></div></div><div className="detail-chart-legend"><span className="p-dot"/>Your Portfolio <span className="b-dot"/>S&amp;P 500</div><LineChart primary={lineA} secondary={lineB} height={235} area/><div className="detail-performance-kpis"><div><small>Best Month</small><strong className="green-text">+8.32%</strong><span>Apr 2023</span></div><div><small>Worst Month</small><strong className="red-text">-6.91%</strong><span>Mar 2020</span></div><div><small>Positive Months</small><strong>62%</strong><span>Historical</span></div><div><small>Beta</small><strong>1.08</strong><span>vs S&amp;P 500</span></div></div></Card>
      </div>
    </div>}

    {tab==='Holdings' && <div className="detail-tab-panel"><Card className="detail-section-card"><div className="detail-section-header"><div><h2>Portfolio Holdings</h2><p>Review assets and adjust their prototype allocation weights.</p></div><div className={`allocation-total-badge ${Math.abs(totalWeight-100)<.2?'valid':'invalid'}`}><small>Total allocation</small><strong>{totalWeight.toFixed(1)}%</strong></div></div><div className="detail-edit-holdings"><div className="edit-holdings-head"><span>Asset</span><span>Type</span><span>Weight</span><span>Market Value</span></div>{portfolio.holdings.map(holding=><div className="edit-holding-row" key={holding.symbol}><div className="asset-cell"><SymbolBadge symbol={holding.symbol}/><div><strong>{holding.symbol}</strong><small>{holding.name}</small></div></div><span className="asset-type">{holding.type}</span><label><span className="sr-only">{holding.symbol} weight</span><input type="number" min="0" max="100" value={holding.weight} onChange={event=>updateWeight(holding.symbol,event.target.value)}/><b>%</b></label><strong>{money(holding.value)}</strong></div>)}</div><div className="detail-section-footer"><p>Changing weights updates this frontend prototype only. Portfolio calculations will use backend data after API integration.</p><button className="primary-btn" onClick={()=>go(`analytics/${portfolio.id}`)}>Analyze Allocation</button></div></Card></div>}

    {tab==='Performance' && <div className="detail-tab-panel performance-tab-layout"><Card className="historical-performance-card"><div className="detail-card-heading"><div><h2>Historical Performance</h2><p>Portfolio performance compared with the S&amp;P 500 benchmark.</p></div><div className="range-tabs"><button>1Y</button><button>3Y</button><button className="active">All</button></div></div><div className="detail-chart-legend"><span className="p-dot"/>Your Portfolio <span className="b-dot"/>S&amp;P 500</div><LineChart primary={lineA} secondary={lineB} height={330} area/></Card><Card className="performance-summary-card"><div className="detail-card-heading"><div><h2>Performance Summary</h2><p>Historical risk and return</p></div></div><dl><div><dt>Annualized return</dt><dd className="green-text">{pct(portfolio.totalReturn)}</dd></div><div><dt>Annualized volatility</dt><dd>15.32%</dd></div><div><dt>Maximum drawdown</dt><dd className="red-text">-21.45%</dd></div><div><dt>Sharpe ratio</dt><dd>1.24</dd></div><div><dt>Beta</dt><dd>1.08</dd></div></dl><p>This prototype uses deterministic demo series. Final values will come from Aura's analytics API.</p></Card></div>}

    {tab==='Activity' && <div className="detail-tab-panel activity-tab-layout"><Card className="detail-activity-card"><div className="detail-card-heading"><div><h2>Recent Activity</h2><p>Portfolio changes, analyses, and simulations.</p></div></div><Timeline items={['Portfolio analyzed — risk score 72','2008 Financial Crisis simulation completed','Holding weight updated for NVDA','Portfolio created']} /></Card><Card className="activity-summary-card"><div className="detail-card-heading"><div><h2>Portfolio History</h2><p>Current record summary</p></div></div><dl><div><dt>Created</dt><dd>{new Date(portfolio.created).toLocaleDateString()}</dd></div><div><dt>Last analyzed</dt><dd>May 11, 2026</dd></div><div><dt>Saved reports</dt><dd>2</dd></div><div><dt>Simulations</dt><dd>1</dd></div></dl><button className="secondary-btn" onClick={()=>go('reports')}>View Reports <span>→</span></button></Card></div>}
  </div>;
}

function HoldingsTable({ portfolio, onViewAll }) {
  return <Card className="detail-holdings-card"><div className="detail-card-heading"><div><h2>Holdings</h2><p>{portfolio.holdings.length} assets in this portfolio</p></div>{onViewAll&&<button onClick={onViewAll}>View all</button>}</div><div className="table-scroll"><table className="detail-holdings-table"><thead><tr><th>Asset</th><th>Weight</th><th>Value</th><th>Daily Change</th></tr></thead><tbody>{portfolio.holdings.map(holding=><tr key={holding.symbol}><td><div className="asset-cell"><SymbolBadge symbol={holding.symbol}/><div><strong>{holding.symbol}</strong><small>{holding.name}</small></div></div></td><td><strong>{holding.weight}%</strong></td><td>{money(holding.value)}</td><td className={holding.dailyChange>0?'green-text':holding.dailyChange<0?'red-text':''}>{holding.dailyChange===0?'—':pct(holding.dailyChange)}</td></tr>)}</tbody><tfoot><tr><td>Total</td><td>{portfolio.holdings.reduce((sum,holding)=>sum+Number(holding.weight||0),0).toFixed(1)}%</td><td>{money(portfolio.value)}</td><td/></tr></tfoot></table></div></Card>;
}

function PortfolioMetric({ label, value, detail, icon, tone }) {
  return <Card className={`detail-metric-card ${tone}`}><span className="detail-metric-icon"><Icon name={icon} size={20}/></span><div><small>{label}</small><strong>{value}</strong><span>{detail}</span></div></Card>;
}

function Analytics({ portfolio, setReports }) {
  const riskDrivers = portfolio.holdings.filter(holding=>holding.symbol!=='CASH').map((holding,index)=>({ ...holding, contribution: Math.max(2, (holding.weight*(index===0?1.1:index===1?0.9:0.55))).toFixed(1), level: index<2?'High':index===2?'Moderate':'Low' }));
  const riskLabel = String(portfolio.riskLevel || 'Moderate').replace(/\s+Risk$/i, '');
  function saveReport() {
    const report = {id:Date.now(),name:`${portfolio.name} Analysis`,portfolio:portfolio.name,type:'Analysis',date:new Date().toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}),riskScore:portfolio.riskScore};
    setReports(prev=>[report,...prev]);
    alert('Analysis snapshot saved to Reports.');
  }
  return <div className="page analytics-page">
    <button className="analytics-back-link" onClick={()=>go(`portfolio/${portfolio.id}`)}>← Back to {portfolio.name}</button>
    <header className="analytics-header"><div><h1>Portfolio Analysis</h1><p>Historical risk report for <strong>{portfolio.name}</strong>.</p></div><div><button className="secondary-btn" onClick={()=>go('assistant')}><Icon name="spark" size={17}/> Ask Aura</button><button className="primary-btn" onClick={saveReport}>Save Report <span>↓</span></button></div></header>

    <Card className="analysis-summary-hero">
      <div className="analysis-summary-copy"><span className="analysis-eyebrow"><Icon name="analysis" size={15}/> OVERALL RISK SUMMARY</span><div className="analysis-score-line"><strong>{portfolio.riskScore}<small>/100</small></strong><span>{riskLabel}</span></div><h2>Your portfolio has a {riskLabel.toLowerCase()} historical risk profile.</h2><p>The largest risk comes from concentrated exposure to high-volatility assets and positive correlation between the largest positions. These observations explain historical behavior and are not investment recommendations.</p><div className="analysis-summary-actions"><button className="primary-btn" onClick={()=>go('assistant')}>Ask Aura About This <span>→</span></button><button className="secondary-btn" onClick={()=>go(`simulations/${portfolio.id}`)}>Run What-If Simulation</button></div></div>
      <div className="analysis-gauge-panel"><RiskGauge score={portfolio.riskScore} label={riskLabel}/><div><span>Last analyzed</span><strong>May 11, 2026</strong></div><small>Based on historical portfolio data</small></div>
    </Card>

    <div className="analytics-metric-grid">
      <PortfolioMetric label="Annualized Volatility" value="15.32%" detail="Moderate historical variation" icon="trend" tone="purple" />
      <PortfolioMetric label="Maximum Drawdown" value="-21.45%" detail="Historical peak-to-trough" icon="drawdown" tone="red" />
      <PortfolioMetric label="Sharpe Ratio" value="1.24" detail="Good risk-adjusted return" icon="trend" tone="green" />
      <PortfolioMetric label="Diversification" value="56/100" detail="Moderate diversification" icon="shield" tone="amber" />
    </div>

    <div className="analytics-content-grid">
      <Card className="risk-drivers-card"><div className="analytics-card-heading"><div><h2>Main Risk Drivers</h2><p>Assets contributing most to historical portfolio risk.</p></div><span>{riskDrivers.length} assets</span></div><div className="analytics-driver-table"><div className="analytics-driver-head"><span>Asset</span><span>Weight</span><span>Risk contribution</span><span>Level</span></div>{riskDrivers.map(driver=><div className="analytics-driver-row" key={driver.symbol}><div className="asset-cell"><SymbolBadge symbol={driver.symbol}/><div><strong>{driver.symbol}</strong><small>{driver.name}</small></div></div><b>{driver.weight}%</b><div className="driver-contribution"><div><span style={{width:`${Math.min(100,Number(driver.contribution))}%`}}/></div><small>{driver.contribution}%</small></div><span className={`mini-risk ${driver.level.toLowerCase()}`}>{driver.level}</span></div>)}</div></Card>
      <Card className="correlation-card"><div className="analytics-card-heading"><div><h2>Asset Relationships</h2><p>Historical return correlation</p></div><span className="correlation-scale"><i/> Lower <i/> Higher</span></div><Heatmap/><div className="correlation-note"><Icon name="analysis" size={17}/><p>Higher positive values mean assets historically moved together. Lower or negative relationships may improve diversification.</p></div></Card>
    </div>

    <section className="asset-analysis-section"><div className="asset-analysis-heading"><div><h2>Individual Asset Analysis</h2><p>Historical risk and performance details for each invested asset.</p></div><button className="secondary-btn" onClick={()=>go(`portfolio/${portfolio.id}`)}>View Holdings</button></div><div className="asset-analysis-grid">{portfolio.holdings.filter(holding=>holding.symbol!=='CASH').map((holding,index)=><Card key={holding.symbol} className="asset-analysis-card"><div className="asset-analysis-card-head"><div className="asset-cell"><SymbolBadge symbol={holding.symbol}/><div><strong>{holding.symbol}</strong><small>{holding.name}</small></div></div><RiskPill score={Math.max(25,portfolio.riskScore-index*9)}/></div><div className="asset-weight-row"><span>Portfolio weight</span><strong>{holding.weight}%</strong></div><div className="asset-weight-bar"><span style={{width:`${holding.weight}%`}}/></div><dl><div><dt>Annualized return</dt><dd className="green-text">{pct(8+index*2.1)}</dd></div><div><dt>Volatility</dt><dd>{(14+index*4.2).toFixed(1)}%</dd></div><div><dt>Maximum drawdown</dt><dd className="red-text">-{(18+index*7.3).toFixed(1)}%</dd></div><div><dt>Sharpe ratio</dt><dd>{(1.4-index*0.17).toFixed(2)}</dd></div></dl></Card>)}</div></section>
  </div>;
}

function Heatmap({ compact=false }) {
  const labels = ['NVDA','TSLA','AAPL','BND','GLD'];
  return <div className={`heatmap ${compact?'compact':''}`}><div className="heat-empty" />{labels.map(l=><b key={l}>{l}</b>)}{labels.map((row,ri)=><React.Fragment key={row}><b>{row}</b>{correlation[ri].map((v,ci)=><span key={`${ri}-${ci}`} style={{'--heat':Math.abs(v)}} className={v<0?'negative':''}>{v.toFixed(2)}</span>)}</React.Fragment>)}</div>;
}

function Simulations({ portfolio, setReports }) {
  const [mode, setMode] = useState('Historical Scenario');
  const [scenarioId, setScenarioId] = useState('gfc');
  const [ran, setRan] = useState(true);
  const [allocation, setAllocation] = useState(() => Object.fromEntries(portfolio.holdings.map(h=>[h.symbol,h.weight])));
  const scenario = scenarioOptions.find(s=>s.id===scenarioId);
  const totalAllocation = Object.values(allocation).reduce((s,n)=>s+Number(n||0),0);
  const allocationEffect = (100-totalAllocation)*0.02 + (Number(allocation.BND||0)-15)*0.18 - (Number(allocation.NVDA||0)-57)*0.12;
  const simulatedReturn = scenario.returnPct + (mode==='Historical Scenario'?0:allocationEffect);
  const modes = [
    ['Historical Scenario','reports','Replay a historical market event'],
    ['Allocation Change','trend','Test a different asset allocation'],
    ['Combined Simulation','simulations','Change allocation within a scenario']
  ];

  function run() {
    if (mode!=='Historical Scenario' && Math.abs(totalAllocation-100)>0.01) return alert('Allocation must total 100%.');
    setRan(true);
  }
  function save() {
    setReports(prev=>[{id:Date.now(),name:`${scenario.label} ${mode}`,portfolio:portfolio.name,type:'Simulation',date:new Date().toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}),riskScore:null},...prev]);
    alert('Simulation saved to Reports.');
  }
  function resetAllocation() {
    setAllocation(Object.fromEntries(portfolio.holdings.map(holding=>[holding.symbol,holding.weight])));
    setRan(false);
  }

  return <div className="page simulations-page">
    <header className="simulations-header"><div><h1>Simulations</h1><p>Explore how your portfolio might have behaved during historical market conditions.</p></div><button className="secondary-btn" onClick={()=>go('reports')}><Icon name="reports" size={17}/> Simulation History</button></header>

    <Card className="simulation-mode-card"><div className="simulation-mode-heading"><h2>Choose a simulation type</h2><p>Select what you want to test before configuring the scenario.</p></div><div className="simulation-mode-options">{modes.map(([label,icon,description])=><button key={label} aria-pressed={mode===label} className={mode===label?'active':''} onClick={()=>{setMode(label);setRan(false)}}><span className="simulation-mode-icon"><Icon name={icon} size={20}/></span><span><strong>{label}</strong><small>{description}</small></span><i>{mode===label?'✓':''}</i></button>)}</div></Card>

    <Card className="simulation-setup-card"><div className="simulation-setup-heading"><div><span>SIMULATION SETUP</span><h2>Configure your test</h2></div><small>Historical results are educational, not predictive.</small></div><div className="simulation-controls-grid"><label><span>Portfolio</span><small>Portfolio to simulate</small><span className="simulation-select"><Icon name="wallet" size={18}/><select value={portfolio.id} onChange={event=>go(`simulations/${event.target.value}`)}><option value={portfolio.id}>{portfolio.name}</option></select><Icon name="chevron-down" size={16}/></span></label><label><span>Historical scenario</span><small>Market period to replay</small><span className="simulation-select"><Icon name="calendar" size={18}/><select value={scenarioId} onChange={event=>{setScenarioId(event.target.value);setRan(false)}}>{scenarioOptions.map(option=><option value={option.id} key={option.id}>{option.label} — {option.dates}</option>)}</select><Icon name="chevron-down" size={16}/></span></label><button className="primary-btn run-simulation-btn" onClick={run}><span>▶</span> Run Simulation</button></div></Card>

    {mode!=='Historical Scenario' && <Card className="simulation-allocation-card"><div className="simulation-allocation-header"><div><h2>{mode==='Allocation Change'?'Test a Different Allocation':'Modified Allocation for This Scenario'}</h2><p>Adjust weights while keeping the total allocation at 100%.</p></div><div><button onClick={resetAllocation}>Reset</button><span className={Math.abs(totalAllocation-100)<.01?'valid':'invalid'}><small>Total</small><strong>{totalAllocation.toFixed(1)}%</strong></span></div></div><div className="simulation-allocation-grid">{portfolio.holdings.map(holding=><label key={holding.symbol}><span className="allocation-asset"><SymbolBadge symbol={holding.symbol}/><span><strong>{holding.symbol}</strong><small>{holding.type}</small></span></span><span className="allocation-input"><input type="number" min="0" max="100" step="0.1" value={allocation[holding.symbol]} onChange={event=>{setAllocation({...allocation,[holding.symbol]:Number(event.target.value)});setRan(false)}}/><b>%</b></span></label>)}</div><div className="simulation-allocation-progress"><span><i style={{width:`${Math.min(100,totalAllocation)}%`}}/></span><p className={Math.abs(totalAllocation-100)<.01?'green-text':'orange-text'}>{Math.abs(totalAllocation-100)<.01?'Allocation is ready to simulate.':'Allocation must total 100% before running.'}</p></div></Card>}

    {!ran&&<Card className="simulation-ready-state"><span><Icon name="simulations" size={27}/></span><div><h2>Ready to run {mode.toLowerCase()}</h2><p>Review the setup above, then run the simulation to generate historical results.</p></div><button className="primary-btn" onClick={run}>Run Simulation <span>→</span></button></Card>}

    {ran && <section className="simulation-results">
      <div className="simulation-results-heading"><div><span>SIMULATION RESULTS</span><h2>{scenario.label}</h2><p>{mode} · {portfolio.name}</p></div><span className="results-status"><i/> Completed</span></div>
      <div className="simulation-metric-grid"><PortfolioMetric label="Total Return" value={pct(simulatedReturn)} detail={scenario.label} icon="trend" tone={simulatedReturn<0?'red':'green'}/><PortfolioMetric label="Maximum Drawdown" value={`${(scenario.drawdown+allocationEffect*0.7).toFixed(2)}%`} detail="Peak-to-trough decline" icon="drawdown" tone="red"/><PortfolioMetric label="Annualized Volatility" value={`${Math.max(8,scenario.volatility-allocationEffect*0.25).toFixed(2)}%`} detail="Historical variation" icon="trend" tone="purple"/><PortfolioMetric label="Recovery Time" value={`${Math.max(1,Math.round(scenario.recovery-allocationEffect*0.1))} months`} detail="Estimated historical recovery" icon="calendar" tone="blue"/></div>
      <div className="simulation-results-grid"><Card className="simulation-chart-card"><div className="simulation-card-heading"><div><h2>Portfolio Value Over Time</h2><p>Historical portfolio and benchmark paths</p></div><div className="detail-chart-legend"><span className="p-dot"/>Your Portfolio <span className="b-dot"/>Benchmark</div></div><LineChart primary={scenario.returnPct<0?downturnA:lineA} secondary={scenario.returnPct<0?downturnB:lineB} negative={scenario.returnPct<0} height={285} area/></Card><Card className="simulation-scenario-card"><div className="simulation-card-heading"><div><h2>Scenario Details</h2><p>Inputs used for this result</p></div></div><div className="scenario-summary-icon"><Icon name="reports" size={22}/></div><p>This simulation applies historical market movements from <strong>{scenario.label}</strong> to the selected portfolio.</p><dl><div><dt>Event period</dt><dd>{scenario.dates}</dd></div><div><dt>Simulation mode</dt><dd>{mode}</dd></div><div><dt>Data basis</dt><dd>Historical prices</dd></div></dl><div className="scenario-actions"><button className="secondary-btn" onClick={save}>Save Result</button><button className="primary-btn" onClick={()=>go('assistant')}>Ask Aura <span>→</span></button></div></Card></div>
      {mode==='Combined Simulation' && <Card className="simulation-comparison-card"><div className="simulation-card-heading"><div><h2>Original vs Modified Allocation</h2><p>How the allocation adjustment changed the historical result.</p></div></div><div className="simulation-comparison-grid"><div><small>Original allocation</small><strong>{pct(scenario.returnPct)}</strong><span>Historical return</span></div><span className="comparison-arrow">→</span><div className="highlight"><small>Modified allocation</small><strong className={simulatedReturn>scenario.returnPct?'green-text':'red-text'}>{pct(simulatedReturn)}</strong><span>Historical return</span></div><div><small>Difference</small><strong className={simulatedReturn-scenario.returnPct>=0?'green-text':'red-text'}>{pct(simulatedReturn-scenario.returnPct)}</strong><span>Allocation effect</span></div></div></Card>}
    </section>}
  </div>;
}

function Assistant({ portfolio }) {
  const [messages, setMessages] = useState([
    {role:'assistant',text:`Hi! I can explain ${portfolio.name} in simple language. What would you like to know?`}
  ]);
  const [text, setText] = useState('');
  const prompts = ['Why is my portfolio risk score 72?','How can I reduce risk?','What is diversification?','Why is correlation important?'];
  function answer(q) {
    const lower=q.toLowerCase();
    if (lower.includes('why') && lower.includes('risk')) return `Your portfolio is around ${portfolio.riskScore}/100 mainly because the biggest positions are concentrated in technology assets. NVDA and TSLA also have relatively high volatility, so large moves in those holdings can affect the whole portfolio more strongly.`;
    if (lower.includes('reduce')) return `Historically, risk could be reduced by lowering concentration in the largest volatile holdings and increasing the share of assets that behave differently, such as broad bond exposure. Aura is explaining historical risk patterns, not telling you what to buy or sell.`;
    if (lower.includes('divers')) return `Diversification means spreading exposure so the portfolio is not controlled by one asset, sector, or type of market behavior. Aura looks at both weights and how assets historically moved together.`;
    if (lower.includes('correlation')) return `Correlation measures how closely two assets moved together historically. Values near +1 mean they often moved in the same direction, while lower or negative values can provide more diversification.`;
    if (lower.includes('drawdown')) return `Maximum drawdown is the largest historical drop from a portfolio peak to a later trough before a new high. It helps show how severe a past decline was.`;
    return `For ${portfolio.name}, Aura focuses on calculated metrics such as volatility, maximum drawdown, Sharpe ratio, concentration, diversification, and risk drivers. Ask me about one of those and I’ll explain it in simpler terms.`;
  }
  function send(q=text) {
    const clean=q.trim(); if(!clean) return;
    setMessages(prev=>[...prev,{role:'user',text:clean},{role:'assistant',text:answer(clean)}]);
    setText('');
  }
  const conversations = [
    ['Why is my risk high?','11:23 PM'],
    ['How did I perform?','9:14 PM'],
    ['Which asset affects risk?','7:08 PM']
  ];
  return <div className="page assistant-page">
    <header className="assistant-header"><div><span>PORTFOLIO INTELLIGENCE</span><h1>AI Assistant</h1><p>Understand your portfolio risk through clear, educational explanations.</p></div><div className="assistant-header-status"><i/><span><strong>Aura is ready</strong><small>Using {portfolio.name} context</small></span></div></header>
    <div className="assistant-layout">
      <Card className="conversation-list">
        <div className="conversation-heading"><div><h2>Conversations</h2><small>Your recent questions</small></div><button aria-label="Search conversations"><Icon name="search" size={17}/></button></div>
        <button className="primary-btn new-conversation-btn" onClick={()=>setMessages([{role:'assistant',text:'New conversation started. What would you like to understand?'}])}><span>＋</span> New Conversation</button>
        <div className="conversation-group"><small>TODAY</small>{conversations.map(([title,time],i)=><button key={title} className={i===0?'active':''} onClick={()=>send(title)}><span className="conversation-icon"><Icon name="assistant" size={15}/></span><span><strong>{title}</strong><small>{time}</small></span><i>›</i></button>)}</div>
        <div className="conversation-group"><small>YESTERDAY</small>{['Explain correlation','How to reduce drawdown?'].map(title=><button key={title} onClick={()=>send(title)}><span className="conversation-icon"><Icon name="assistant" size={15}/></span><span><strong>{title}</strong><small>Yesterday</small></span><i>›</i></button>)}</div>
        <div className="conversation-foot"><Icon name="shield" size={17}/><p>Your conversations use portfolio metrics from this educational prototype.</p></div>
      </Card>

      <Card className="chat-card">
        <div className="chat-head"><div className="aura-chat-identity"><span><Icon name="spark" size={20}/></span><div><strong>Aura</strong><small><i className="online-dot"/> Portfolio risk assistant</small></div></div><div className="chat-context-pill"><Icon name="wallet" size={15}/><span>{portfolio.name}</span><Icon name="chevron-down" size={14}/></div></div>
        <div className="messages" aria-live="polite">{messages.map((message,index)=><div key={index} className={`message ${message.role}`}><span className="message-avatar">{message.role==='assistant'?<Icon name="spark" size={15}/>: 'Y'}</span><div className="message-content"><small>{message.role==='assistant'?'Aura':'You'}</small><p>{message.text}</p><time>{message.role==='assistant'?'Now':'Just now'}</time></div></div>)}</div>
        <div className="assistant-suggestions"><span>Suggested questions</span><div className="prompt-chips">{prompts.map(prompt=><button key={prompt} onClick={()=>send(prompt)}><Icon name="spark" size={12}/>{prompt}</button>)}</div></div>
        <div className="chat-composer"><div className="chat-input"><button className="composer-add" aria-label="Add context">＋</button><input value={text} onChange={event=>setText(event.target.value)} onKeyDown={event=>event.key==='Enter'&&send()} placeholder="Ask Aura about risk, performance, or diversification..."/><button className="composer-send" onClick={()=>send()} aria-label="Send message">↑</button></div><div className="composer-meta"><span>Press Enter to send</span><span><Icon name="shield" size={12}/> Educational explanations only</span></div></div>
      </Card>

      <aside className="assistant-context-column">
        <Card className="context-card"><div className="context-card-heading"><div><span>PORTFOLIO CONTEXT</span><h2>Currently analyzing</h2></div><Icon name="wallet" size={19}/></div><div className="context-portfolio"><SymbolBadge symbol="TP"/><div><strong>{portfolio.name}</strong><small>{money(portfolio.value)} total value</small></div></div><div className="context-risk"><div><span>Risk Score</span><strong>{portfolio.riskScore}<small>/100</small></strong><b>Moderate</b></div><div className="context-risk-ring" style={{'--risk-score':`${portfolio.riskScore*3.6}deg`}}><span>{portfolio.riskScore}</span></div></div><dl><div><dt>Annualized return</dt><dd className="green-text">+12.45%</dd></div><div><dt>Volatility</dt><dd>15.32%</dd></div><div><dt>Max drawdown</dt><dd className="red-text">-21.45%</dd></div><div><dt>Sharpe ratio</dt><dd>1.24</dd></div></dl><button className="secondary-btn context-analysis-btn" onClick={()=>go(`analytics/${portfolio.id}`)}>View Full Analysis <span>→</span></button></Card>
        <Card className="assistant-drivers-card"><div className="context-card-heading"><div><span>TOP RISK DRIVERS</span><h2>What Aura can explain</h2></div></div><div className="assistant-driver"><SymbolBadge symbol="NVDA"/><span><strong>NVIDIA</strong><small>57.1% concentration</small></span><b className="high">High</b></div><div className="assistant-driver"><SymbolBadge symbol="TSLA"/><span><strong>Tesla</strong><small>14.4% concentration</small></span><b className="high">High</b></div><button onClick={()=>send('Which asset affects my risk the most?')}>Ask about risk drivers <span>→</span></button></Card>
        <Card className="assistant-safety-card"><Icon name="shield" size={20}/><div><strong>Educational guidance</strong><p>Aura explains historical metrics and does not provide investment recommendations.</p></div></Card>
      </aside>
    </div>
  </div>;
}

function Reports({ reports, setReports }) {
  const [query,setQuery]=useState('');
  const [type,setType]=useState('All Types');
  const visible=reports.filter(r=>(type==='All Types'||r.type===type)&&r.name.toLowerCase().includes(query.toLowerCase()));
  const reportCounts = {
    analysis: reports.filter(report=>report.type==='Analysis').length,
    simulation: reports.filter(report=>report.type==='Simulation').length,
    comparison: reports.filter(report=>report.type==='Comparison').length
  };
  const reportIcon = report => report.type==='Simulation'?'simulations':report.type==='Comparison'?'analytics':'reports';
  function download(r) {
    const body = `AURA REPORT\n\n${r.name}\nPortfolio: ${r.portfolio}\nType: ${r.type}\nDate: ${r.date}\nRisk Score: ${r.riskScore ?? 'N/A'}\n\nEducational portfolio risk report prototype.`;
    const blob = new Blob([body], {type:'text/plain'});
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`${slug(r.name)}.txt`;a.click();URL.revokeObjectURL(a.href);
  }
  return <div className="page reports-page">
    <header className="reports-header"><div><span>PORTFOLIO DOCUMENTS</span><h1>Reports</h1><p>Review, filter, and download your saved portfolio analyses and simulations.</p></div><button className="primary-btn" onClick={()=>go('analytics')}><Icon name="analysis" size={17}/> Create New Analysis</button></header>

    <div className="report-summary-grid">
      <Card className="report-summary-card purple"><span><Icon name="reports" size={19}/></span><div><small>Total Reports</small><strong>{reports.length}</strong><p>Saved in your library</p></div></Card>
      <Card className="report-summary-card blue"><span><Icon name="analysis" size={19}/></span><div><small>Portfolio Analyses</small><strong>{reportCounts.analysis}</strong><p>Risk analysis reports</p></div></Card>
      <Card className="report-summary-card amber"><span><Icon name="simulations" size={19}/></span><div><small>Simulations</small><strong>{reportCounts.simulation}</strong><p>Historical scenario results</p></div></Card>
      <Card className="report-summary-card green"><span><Icon name="analytics" size={19}/></span><div><small>Comparisons</small><strong>{reportCounts.comparison}</strong><p>Portfolio comparisons</p></div></Card>
    </div>

    <Card className="reports-library-card">
      <div className="reports-library-heading"><div><h2>Report Library</h2><p>All generated reports are stored here for future reference.</p></div><span>{visible.length} {visible.length===1?'report':'reports'}</span></div>
      <div className="report-filters"><label className="report-search"><Icon name="search" size={17}/><input placeholder="Search by report name..." value={query} onChange={event=>setQuery(event.target.value)}/>{query&&<button onClick={()=>setQuery('')} aria-label="Clear search">×</button>}</label><label className="report-select"><Icon name="wallet" size={16}/><select aria-label="Filter by portfolio"><option>All Portfolios</option></select><Icon name="chevron-down" size={14}/></label><label className="report-select"><Icon name="reports" size={16}/><select value={type} onChange={event=>setType(event.target.value)} aria-label="Filter by report type"><option>All Types</option><option>Analysis</option><option>Simulation</option><option>Comparison</option></select><Icon name="chevron-down" size={14}/></label>{(query||type!=='All Types')&&<button className="clear-report-filters" onClick={()=>{setQuery('');setType('All Types')}}>Clear filters</button>}</div>

      {visible.length>0?<div className="reports-table-wrap" role="region" aria-label="Saved reports" tabIndex={0}><table className="reports-table"><thead><tr><th>Report</th><th>Portfolio</th><th>Type</th><th>Created</th><th>Risk Score</th><th aria-label="Actions"/></tr></thead><tbody>{visible.map(report=><tr key={report.id}><td><div className={`report-name-cell ${report.type.toLowerCase()}`}><span><Icon name={reportIcon(report)} size={18}/></span><div><strong>{report.name}</strong><small>Educational portfolio risk report</small></div></div></td><td><div className="report-portfolio-cell"><span>{report.portfolio.slice(0,2).toUpperCase()}</span><strong>{report.portfolio}</strong></div></td><td><span className={`report-type-badge ${report.type.toLowerCase()}`}>{report.type}</span></td><td><div className="report-date-cell"><Icon name="calendar" size={15}/><span>{report.date}</span></div></td><td>{report.riskScore?<div className="report-risk-score"><strong>{report.riskScore}</strong><RiskPill score={report.riskScore}/></div>:<span className="not-applicable">Not applicable</span>}</td><td><div className="report-row-actions"><button onClick={()=>download(report)} aria-label={`Download ${report.name}`} title="Download report"><span>↓</span></button><button className="delete" onClick={()=>setReports(previous=>previous.filter(item=>item.id!==report.id))} aria-label={`Delete ${report.name}`} title="Delete report">×</button></div></td></tr>)}</tbody></table></div>:<div className="reports-empty-state"><span><Icon name="reports" size={28}/></span><h3>No reports found</h3><p>Try changing your search or report-type filter.</p><button className="secondary-btn" onClick={()=>{setQuery('');setType('All Types')}}>Reset Filters</button></div>}

      <div className="table-footer"><span>Showing <strong>{visible.length}</strong> of <strong>{reports.length}</strong> reports</span><div><button aria-label="Previous page">‹</button><button className="active">1</button><button aria-label="Next page">›</button></div></div>
    </Card>
    <div className="reports-education-note"><Icon name="shield" size={16}/><p>Reports summarize calculated and historical portfolio risk for educational use. They are not investment recommendations.</p></div>
  </div>;
}

function Watchlist({ watchlist, setWatchlist }) {
  const [query,setQuery]=useState('');
  const visible=watchlist.filter(x=>x.symbol.toLowerCase().includes(query.toLowerCase())||x.name.toLowerCase().includes(query.toLowerCase()));
  const positiveCount=watchlist.filter(asset=>asset.daily>0).length;
  const averageDaily=watchlist.length?watchlist.reduce((sum,asset)=>sum+Number(asset.daily),0)/watchlist.length:0;
  const topMover=watchlist.length?[...watchlist].sort((a,b)=>b.daily-a.daily)[0]:null;
  function addAsset() {
    const symbol=prompt('Symbol (e.g. AMZN)'); if(!symbol) return;
    const clean=symbol.trim().toUpperCase();
    if(watchlist.some(x=>x.symbol===clean)) return alert('Already in watchlist.');
    setWatchlist(prev=>[...prev,{symbol:clean,name:`${clean} demo asset`,price:100,daily:0,yearly:0,cap:'—'}]);
  }
  return <div className="page watchlist-page">
    <header className="watchlist-header"><div><span>MARKET MONITOR</span><h1>Watchlist</h1><p>Track assets you are interested in and review their recent market movement.</p></div><button className="primary-btn" onClick={addAsset}><span>＋</span> Add Asset</button></header>

    <div className="watchlist-summary-grid">
      <Card className="watchlist-summary-card"><span className="purple"><Icon name="wallet" size={19}/></span><div><small>Tracked Assets</small><strong>{watchlist.length}</strong><p>Saved to your watchlist</p></div></Card>
      <Card className="watchlist-summary-card"><span className="green"><Icon name="trend" size={19}/></span><div><small>Positive Today</small><strong>{positiveCount}</strong><p>{watchlist.length?`${Math.round(positiveCount/watchlist.length*100)}% of tracked assets`:'No tracked assets'}</p></div></Card>
      <Card className="watchlist-summary-card"><span className={averageDaily>=0?'blue':'red'}><Icon name={averageDaily>=0?'trend':'drawdown'} size={19}/></span><div><small>Average Daily Move</small><strong className={averageDaily>=0?'green-text':'red-text'}>{pct(averageDaily)}</strong><p>Across the current list</p></div></Card>
      <Card className="watchlist-summary-card"><span className="amber"><Icon name="spark" size={19}/></span><div><small>Top Daily Mover</small><strong>{topMover?.symbol||'—'}</strong><p className={topMover?.daily>=0?'green-text':'red-text'}>{topMover?pct(topMover.daily):'No market data'}</p></div></Card>
    </div>

    <Card className="watchlist-library-card">
      <div className="watchlist-library-heading"><div><h2>Tracked Assets</h2><p>Market values shown here are prototype data for portfolio-risk education.</p></div><div className="market-status"><i/><span>Market data available</span></div></div>
      <div className="watchlist-toolbar"><label><Icon name="search" size={17}/><input placeholder="Search by symbol or company name..." value={query} onChange={event=>setQuery(event.target.value)}/>{query&&<button onClick={()=>setQuery('')} aria-label="Clear search">×</button>}</label><div className="watchlist-view-controls"><button className="active"><Icon name="reports" size={15}/> List</button><span>Last updated May 11, 2026</span></div></div>

      {visible.length?<div className="watchlist-table-wrap" role="region" aria-label="Tracked assets" tabIndex={0}><table className="watchlist-table"><thead><tr><th>Asset</th><th>Price</th><th>Daily Change</th><th>YTD Change</th><th>Market Cap</th><th>Trend</th><th aria-label="Actions"/></tr></thead><tbody>{visible.map((asset,index)=><tr key={asset.symbol}><td><div className="watchlist-asset-cell"><SymbolBadge symbol={asset.symbol}/><div><strong>{asset.symbol}</strong><small>{asset.name}</small></div></div></td><td><div className="watchlist-price"><strong>{money(asset.price)}</strong><small>USD</small></div></td><td><span className={`watchlist-change ${asset.daily>=0?'positive':'negative'}`}>{asset.daily>=0?'↑':'↓'} {pct(asset.daily)}</span></td><td><span className={asset.yearly>=0?'green-text':'red-text'}>{pct(asset.yearly)}</span></td><td><strong className="watchlist-cap">{asset.cap}</strong></td><td><div className={`watchlist-spark ${asset.daily>=0?'positive':'negative'}`}><MiniLine values={(asset.daily>=0?lineA:downturnA).slice(index,index+10)}/></div></td><td><button className="watchlist-remove" onClick={()=>setWatchlist(previous=>previous.filter(item=>item.symbol!==asset.symbol))} aria-label={`Remove ${asset.symbol} from watchlist`} title="Remove from watchlist">×</button></td></tr>)}</tbody></table></div>:<div className="watchlist-empty-state"><span><Icon name="search" size={27}/></span><h3>{watchlist.length?'No matching assets':'Your watchlist is empty'}</h3><p>{watchlist.length?'Try a different symbol or company name.':'Add an asset to begin tracking market movements.'}</p><button className="secondary-btn" onClick={watchlist.length?()=>setQuery(''):addAsset}>{watchlist.length?'Clear Search':'Add Your First Asset'}</button></div>}
      <div className="watchlist-footer"><span>Showing <strong>{visible.length}</strong> of <strong>{watchlist.length}</strong> tracked assets</span><button onClick={addAsset}>＋ Add another asset</button></div>
    </Card>
    <div className="watchlist-education-note"><Icon name="shield" size={16}/><p>Watchlist performance is historical market information for education and does not represent a recommendation to buy or sell.</p></div>
  </div>;
}

function Learn() {
  const lessons=[
    {title:'Understanding Risk Score',text:'How Aura combines volatility, drawdown, concentration, and diversification.',icon:'shield',topic:'Risk basics',time:'5 min',level:'Beginner'},
    {title:'Volatility',text:'Learn what historical price fluctuations mean for a portfolio.',icon:'trend',topic:'Market behavior',time:'4 min',level:'Beginner'},
    {title:'Maximum Drawdown',text:'Understand the largest peak-to-trough decline.',icon:'drawdown',topic:'Loss awareness',time:'6 min',level:'Beginner'},
    {title:'Sharpe Ratio',text:'Learn about return relative to historical volatility.',icon:'analytics',topic:'Risk-adjusted return',time:'7 min',level:'Intermediate'},
    {title:'Correlation',text:'See why assets moving together can increase concentration risk.',icon:'analysis',topic:'Diversification',time:'6 min',level:'Intermediate'},
    {title:'Historical What-If',text:'Learn how scenario simulations use past market periods.',icon:'simulations',topic:'Scenarios',time:'8 min',level:'Intermediate'}
  ];
  function openLesson(lesson) {
    alert(`${lesson.title}\n\n${lesson.text}\n\nThis learning module can later be connected to your course content or Aura knowledge base.`);
  }
  return <div className="page learn-page">
    <header className="learn-header"><div><span>AURA LEARNING CENTER</span><h1>Learn Portfolio Risk</h1><p>Build confidence with clear, beginner-friendly lessons about portfolio behavior.</p></div><div className="learn-progress-pill"><span><Icon name="reports" size={18}/></span><div><strong>{lessons.length} lessons</strong><small>About 36 minutes total</small></div></div></header>

    <div className="learn-feature-grid">
      <Card className="learn-feature-card"><div className="learn-feature-copy"><span className="learn-feature-label"><Icon name="spark" size={13}/> RECOMMENDED START</span><h2>Understand what your risk score is really telling you</h2><p>Learn how Aura brings several historical risk measures together without turning them into investment advice.</p><div className="learn-feature-meta"><span><Icon name="calendar" size={14}/> 5 minutes</span><span><Icon name="shield" size={14}/> Beginner</span></div><button className="primary-btn" onClick={()=>openLesson(lessons[0])}>Start First Lesson <span>→</span></button></div><div className="learn-feature-visual"><div className="learning-orbit"><span><Icon name="shield" size={32}/></span><i className="orbit-one"><Icon name="trend" size={16}/></i><i className="orbit-two"><Icon name="drawdown" size={16}/></i><i className="orbit-three"><Icon name="analysis" size={16}/></i></div><small>Risk is more than one number</small></div></Card>
      <Card className="learning-path-card"><div className="learning-path-heading"><span>YOUR LEARNING PATH</span><h2>From foundations to scenarios</h2><p>Follow the modules in order or explore any topic.</p></div><div className="learning-path-steps"><div className="active"><span>1</span><div><strong>Risk Foundations</strong><small>Score, volatility, and drawdown</small></div><b>3 lessons</b></div><div><span>2</span><div><strong>Portfolio Relationships</strong><small>Return, correlation, diversification</small></div><b>2 lessons</b></div><div><span>3</span><div><strong>Historical Scenarios</strong><small>Understand what-if simulations</small></div><b>1 lesson</b></div></div></Card>
    </div>

    <section className="learning-library"><div className="learning-library-heading"><div><span>LEARNING LIBRARY</span><h2>Explore all lessons</h2><p>Short explanations designed to make portfolio-risk metrics easier to understand.</p></div><span className="lesson-count">{lessons.length} modules</span></div><div className="lesson-grid">{lessons.map((lesson,index)=><Card key={lesson.title} className={`lesson-card lesson-tone-${index%3}`}><div className="lesson-card-top"><span><Icon name={lesson.icon} size={21}/></span><b>{String(index+1).padStart(2,'0')}</b></div><span className="lesson-topic">{lesson.topic}</span><h3>{lesson.title}</h3><p>{lesson.text}</p><div className="lesson-meta"><span><Icon name="calendar" size={13}/>{lesson.time}</span><span><Icon name="analysis" size={13}/>{lesson.level}</span></div><button onClick={()=>openLesson(lesson)}>Open Lesson <span>→</span></button></Card>)}</div></section>

    <Card className="learn-aura-card"><span><Icon name="spark" size={22}/></span><div><h2>Have a question while learning?</h2><p>Ask Aura to explain a portfolio-risk concept using the context of your current portfolio.</p></div><button className="secondary-btn" onClick={()=>go('assistant')}>Ask AI Assistant <span>→</span></button></Card>
    <div className="learn-education-note"><Icon name="shield" size={16}/><p>Learning content explains historical portfolio-risk concepts and is not financial or investment advice.</p></div>
  </div>;
}

function CreatePortfolio({ portfolios, setPortfolios }) {
  const [step,setStep]=useState(1);
  const [name,setName]=useState('My New Portfolio');
  const [description,setDescription]=useState('My long term investment portfolio.');
  const [holdings,setHoldings]=useState([
    {symbol:'NVDA',name:'NVIDIA Corporation',type:'Equity',price:181.63,shares:58,weight:57.1},
    {symbol:'TSLA',name:'Tesla, Inc.',type:'Equity',price:177.74,shares:15,weight:14.4},
    {symbol:'AAPL',name:'Apple Inc.',type:'Equity',price:191.45,shares:10,weight:10.4},
    {symbol:'BND',name:'Vanguard Total Bond Market ETF',type:'Bond',price:72.16,shares:40,weight:15.4},
    {symbol:'CASH',name:'Cash',type:'Cash',price:1,shares:484.9,weight:2.7}
  ]);
  const total=holdings.reduce((s,h)=>s+h.price*h.shares,0);
  const totalWeight=holdings.reduce((s,h)=>s+Number(h.weight),0);
  const steps=[['1','Basic Info','Name and preferences'],['2','Add Holdings','Build your allocation'],['3','Review','Confirm and create']];
  const currentStep=steps[step-1];
  function addHolding() {
    const symbol=prompt('Asset symbol'); if(!symbol)return;
    const amount=Number(prompt('Amount invested in USD','1000'))||1000;
    const price=100;
    const newH={symbol:symbol.toUpperCase(),name:`${symbol.toUpperCase()} Asset`,type:'Equity',price,shares:amount/price,weight:0};
    const next=[...holdings,newH]; const nextTotal=next.reduce((s,h)=>s+h.price*h.shares,0);
    setHoldings(next.map(h=>({...h,weight:Number(((h.price*h.shares/nextTotal)*100).toFixed(1))})));
  }
  function removeHolding(symbol){const next=holdings.filter(h=>h.symbol!==symbol);const t=next.reduce((s,h)=>s+h.price*h.shares,0);setHoldings(next.map(h=>({...h,weight:Number(((h.price*h.shares/t)*100).toFixed(1))})));}
  function create() {
    if(!name.trim()) return alert('Please enter a portfolio name.');
    if(!holdings.length) return alert('Add at least one holding.');
    const id=`${slug(name)}-${Date.now()}`;
    const value=holdings.reduce((s,h)=>s+h.price*h.shares,0);
    const p={id,name:name.trim(),created:new Date().toISOString().slice(0,10),value,totalReturn:0,riskScore:55,riskLevel:'Moderate',cash:holdings.find(h=>h.symbol==='CASH')?.price*holdings.find(h=>h.symbol==='CASH')?.shares||0,holdings:holdings.map(h=>({...h,value:h.price*h.shares,dailyChange:0}))};
    setPortfolios([...portfolios,p]);go(`portfolio/${id}`);
  }
  return <div className="page create-page">
    <button className="create-back-link" onClick={()=>go('portfolios')}>← Back to Portfolios</button>
    <section className="create-header"><div><h1>Create New Portfolio</h1><p>Build a portfolio to explore its historical performance and risk.</p></div><span>Step {step} of {steps.length}</span></section>

    <Card className="create-stepper">{steps.map(([number,label,detail],index)=><React.Fragment key={number}>
      <button className={`${step===Number(number)?'active':''} ${step>Number(number)?'complete':''}`} onClick={()=>setStep(Number(number))} aria-current={step===Number(number)?'step':undefined}>
        <span className="step-number">{step>Number(number)?'✓':number}</span><span className="step-copy"><strong>{label}</strong><small>{detail}</small></span>
      </button>{index<steps.length-1&&<span className={`step-connector ${step>index+1?'complete':''}`}/>}
    </React.Fragment>)}</Card>

    <div className="create-workspace">
      <Card className="wizard-main">
        <div className="wizard-section-header"><span>STEP {currentStep[0]}</span><h2>{step===1?'Portfolio Information':step===2?'Add Your Holdings':'Review Your Portfolio'}</h2><p>{step===1?'Give this portfolio a clear name and description.':step===2?'Add the assets and amounts you want Aura to analyze.':'Check the portfolio details before creating it.'}</p></div>

        {step===1&&<div className="wizard-step-content basic-info-step">
          <div className="wizard-form-grid">
            <label className="wizard-field"><span>Portfolio Name</span><small>Use a name that helps you recognize this portfolio.</small><input value={name} onChange={event=>setName(event.target.value)} placeholder="e.g. Long-Term Growth"/></label>
            <label className="wizard-field"><span>Currency</span><small>Values and reports will use this currency.</small><span className="wizard-select"><select><option>USD - US Dollar</option></select><Icon name="chevron-down" size={16}/></span></label>
            <label className="wizard-field full"><span>Description <em>Optional</em></span><small>Add a short note about the portfolio's purpose.</small><textarea rows="5" value={description} onChange={event=>setDescription(event.target.value)} placeholder="Describe your investment goal..."/></label>
          </div>
        </div>}

        {step===2&&<div className="wizard-step-content holdings-step">
          <div className="wizard-title-row"><label className="asset-search"><Icon name="search" size={18}/><span className="sr-only">Search assets</span><input placeholder="Search assets by symbol or company name..."/></label><button className="primary-btn" onClick={addHolding}>＋ Add Manually</button></div>
          <div className="wizard-holdings-table table-scroll"><table><thead><tr><th>Asset</th><th>Type</th><th>Price</th><th>Shares / Amount</th><th>Allocation</th><th><span className="sr-only">Action</span></th></tr></thead><tbody>{holdings.map(holding=><tr key={holding.symbol}><td><div className="asset-cell"><SymbolBadge symbol={holding.symbol}/><div><strong>{holding.symbol}</strong><small>{holding.name}</small></div></div></td><td><span className="asset-type">{holding.type}</span></td><td>{money(holding.price)}</td><td><input className="table-input" aria-label={`${holding.symbol} shares`} type="number" value={holding.shares} onChange={event=>setHoldings(holdings.map(item=>item.symbol===holding.symbol?{...item,shares:Number(event.target.value)}:item))}/></td><td><strong>{holding.weight}%</strong></td><td><button className="remove-holding" aria-label={`Remove ${holding.symbol}`} onClick={()=>removeHolding(holding.symbol)}>×</button></td></tr>)}</tbody></table></div>
          <div className="allocation-status"><div><span>Total allocation</span><small>Portfolio weights should total 100%.</small></div><div className="allocation-progress"><span style={{width:`${Math.min(100,totalWeight)}%`}}/><b className={Math.abs(totalWeight-100)<.2?'green-text':'orange-text'}>{totalWeight.toFixed(1)}%</b></div></div>
        </div>}

        {step===3&&<div className="wizard-step-content review-step">
          <div className="review-summary"><div><small>Portfolio Name</small><strong>{name}</strong></div><div><small>Total Value</small><strong>{money(total)}</strong></div><div><small>Holdings</small><strong>{holdings.length}</strong></div><div><small>Allocation</small><strong className={Math.abs(totalWeight-100)<.2?'green-text':'orange-text'}>{totalWeight.toFixed(1)}%</strong></div></div>
          <div className="review-holdings-card"><div className="review-holdings-title"><h3>Holdings</h3><button onClick={()=>setStep(2)}>Edit holdings</button></div><HoldingsReview holdings={holdings}/></div>
          <div className="educational-notice"><Icon name="shield" size={19}/><p>Aura analyzes historical portfolio risk for educational purposes. It does not provide buy or sell recommendations.</p></div>
        </div>}

        <div className="wizard-footer"><button className="secondary-btn" onClick={()=>step===1?go('portfolios'):setStep(step-1)}>{step===1?'Cancel':'← Back'}</button>{step<3?<button className="primary-btn" onClick={()=>setStep(step+1)}>{step===1?'Continue to Holdings':'Review Portfolio'} <span>→</span></button>:<button className="primary-btn create-confirm-btn" onClick={create}>Create Portfolio <span>✓</span></button>}</div>
      </Card>

      <aside className="create-sidebar">
        <Card className="portfolio-preview-card"><div className="preview-icon"><Icon name="portfolios" size={22}/></div><small>PORTFOLIO PREVIEW</small><h3>{name.trim()||'Untitled Portfolio'}</h3><p>{description.trim()||'No description added.'}</p><dl><div><dt>Estimated value</dt><dd>{money(total)}</dd></div><div><dt>Holdings</dt><dd>{holdings.length}</dd></div><div><dt>Allocation</dt><dd className={Math.abs(totalWeight-100)<.2?'green-text':'orange-text'}>{totalWeight.toFixed(1)}%</dd></div></dl></Card>
        <Card className="after-create-card"><h3>What happens next?</h3><div><span>1</span><p><strong>Create portfolio</strong><small>Save these holdings in your Aura workspace.</small></p></div><div><span>2</span><p><strong>Run analysis</strong><small>Calculate historical risk and performance metrics.</small></p></div><div><span>3</span><p><strong>Explore insights</strong><small>Understand the results in beginner-friendly language.</small></p></div></Card>
      </aside>
    </div>
  </div>;
}

function HoldingsReview({ holdings }) {return <div className="holding-review">{holdings.map(h=><div key={h.symbol}><div className="asset-cell"><SymbolBadge symbol={h.symbol}/><div><strong>{h.symbol}</strong><small>{h.name}</small></div></div><strong>{h.weight}%</strong><span>{money(h.price*h.shares)}</span></div>)}</div>}

function Settings({ settings, setSettings }) {
  const [form,setForm]=useState(settings); const [tab,setTab]=useState('Profile');
  function save(){setSettings(form);alert('Settings saved.');}
  const initials=form.name.split(/\s+/).filter(Boolean).map(part=>part[0]).slice(0,2).join('').toUpperCase()||'YL';
  const sections=[['Profile','assistant','Personal details'],['Preferences','analytics','Language and region'],['Notifications','bell','Updates and alerts'],['Security','shield','Account protection'],['Billing','reports','Plan and invoices']];
  const activeSection=sections.find(([name])=>name===tab);
  return <div className="page settings-page">
    <header className="settings-header"><div><span>ACCOUNT CENTER</span><h1>Settings</h1><p>Manage your Aura profile, preferences, and account configuration.</p></div><div className="settings-saved-status"><i/><span><strong>Local profile</strong><small>Saved in this browser</small></span></div></header>
    <div className="settings-layout">
      <Card className="settings-navigation"><div className="settings-nav-profile"><div className="settings-nav-avatar">{initials}</div><div><strong>{form.name}</strong><small>{form.email}</small></div></div><nav aria-label="Settings sections">{sections.map(([name,icon,description])=><button key={name} aria-current={tab===name?'page':undefined} className={tab===name?'active':''} onClick={()=>setTab(name)}><span><Icon name={icon} size={17}/></span><span><strong>{name}</strong><small>{description}</small></span><i>›</i></button>)}</nav><div className="settings-nav-note"><Icon name="shield" size={17}/><p>Prototype profile data remains in your browser's local storage.</p></div></Card>

      <div className="settings-content">
        {tab==='Profile'?<>
          <Card className="settings-profile-card"><div className="settings-section-heading"><div><span>PROFILE INFORMATION</span><h2>Your account details</h2><p>Update the information displayed throughout the Aura prototype.</p></div><span className="settings-profile-badge"><Icon name="assistant" size={15}/> Portfolio owner</span></div><div className="settings-profile-hero"><div className="profile-photo">{initials}<span><Icon name="spark" size={12}/></span></div><div><strong>{form.name}</strong><small>{form.email}</small><p>Your initials appear in the navigation and account menu.</p></div><button className="secondary-btn">Change Photo</button></div></Card>
          <Card className="settings-form-card"><div className="settings-form-heading"><h2>Personal Information</h2><p>Keep your contact details and regional preferences up to date.</p></div><div className="settings-form"><label><span>Full Name</span><small>Name shown across your Aura workspace</small><span className="settings-field"><Icon name="assistant" size={16}/><input value={form.name} onChange={event=>setForm({...form,name:event.target.value})} placeholder="Enter your full name"/></span></label><label><span>Email Address</span><small>Primary account contact</small><span className="settings-field"><span className="field-symbol">@</span><input type="email" value={form.email} onChange={event=>setForm({...form,email:event.target.value})} placeholder="name@example.com"/></span></label><label><span>Phone Number</span><small>Optional contact information</small><span className="settings-field"><span className="field-symbol">＋</span><input value={form.phone} onChange={event=>setForm({...form,phone:event.target.value})} placeholder="Enter your phone number"/></span></label><label><span>Language</span><small>Interface language preference</small><span className="settings-field settings-select-field"><Icon name="reports" size={16}/><select value={form.language} onChange={event=>setForm({...form,language:event.target.value})}><option>English</option><option>Thai</option></select><Icon name="chevron-down" size={14}/></span></label><label className="timezone-field"><span>Timezone</span><small>Used for dates and report timestamps</small><span className="settings-field settings-select-field"><Icon name="calendar" size={16}/><select value={form.timezone} onChange={event=>setForm({...form,timezone:event.target.value})}><option>UTC+06:30 Yangon</option><option>UTC+07:00 Bangkok</option></select><Icon name="chevron-down" size={14}/></span></label></div><div className="settings-form-footer"><div><Icon name="shield" size={15}/><span>Changes are stored only in this frontend prototype.</span></div><div><button className="secondary-btn" onClick={()=>setForm(settings)}>Discard Changes</button><button className="primary-btn settings-save" onClick={save}>Save Changes <span>→</span></button></div></div></Card>
        </>:<Card className="empty-settings"><div className="empty-settings-icon"><Icon name={activeSection?.[1]||'settings'} size={27}/></div><span>ACCOUNT SETTINGS</span><h2>{tab}</h2><p>This prototype includes the section navigation and visual state. Connect {tab.toLowerCase()} to authentication and account services when those backend capabilities are introduced.</p><div className="empty-settings-preview"><div><span><Icon name={activeSection?.[1]||'settings'} size={16}/></span><div><strong>{activeSection?.[2]}</strong><small>Backend integration required</small></div></div><b>Coming later</b></div><div className="empty-settings-boundary"><Icon name="shield" size={16}/><p>No account-service functionality has been added during this design phase.</p></div></Card>}
      </div>
    </div>
  </div>;
}

function Timeline({ items }) {return <div className="timeline">{items.map((x,i)=><div key={x}><span>{i+1}</span><div><strong>{x}</strong><small>{i===0?'Today':`${i} day${i>1?'s':''} ago`}</small></div></div>)}</div>}

export default App;
