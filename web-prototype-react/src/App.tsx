// @ts-nocheck
import React, { useEffect, useState } from 'react';
import {
  correlation,
  defaultPortfolios,
  reportsSeed,
  scenarioOptions,
  watchlistSeed
} from './data/mockData';
const navItems = [
  ['dashboard', 'dashboard', 'Dashboard'],
  ['portfolios', 'portfolios', 'Portfolios'],
  ['analytics', 'analytics', 'Analytics'],
  ['simulations', 'simulations', 'Simulations'],
  ['assistant', 'assistant', 'AI Assistant'],
  ['reports', 'reports', 'Reports']
];

const lineA = [18, 16, 20, 17, 24, 25, 29, 33, 31, 36, 39, 43, 40, 45, 49, 44, 50, 54, 58, 55, 61, 64, 67, 73, 69, 76, 81, 78, 85, 91];
const lineB = [12, 11, 13, 10, 14, 17, 16, 20, 22, 24, 22, 27, 29, 26, 31, 30, 34, 37, 35, 39, 41, 40, 44, 48, 47, 51, 53, 55, 57, 60];
const downturnA = [5, 0, -3, -8, -12, -16, -19, -22, -24, -27, -31, -35, -37, -34, -40, -43, -39, -36, -34, -37, -33, -31, -28, -30];
const downturnB = [5, 3, -1, -4, -7, -10, -12, -15, -18, -19, -21, -24, -25, -23, -28, -31, -29, -26, -24, -22, -20, -18, -16, -15];

function money(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);
}

function pct(value, digits = 2) {
  return `${value >= 0 ? '+' : ''}${Number(value).toFixed(digits)}%`;
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function slug(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function routeFromHash() {
  const raw = window.location.hash.replace(/^#\/?/, '') || 'dashboard';
  const [page, id] = raw.split('/');
  return { page, id };
}

function go(path) {
  window.location.hash = `#/${path}`;
}

function usePersistedState(key, seed) {
  const [value, setValue] = useState(() => {
    try {
      const found = localStorage.getItem(key);
      return found ? JSON.parse(found) : seed;
    } catch {
      return seed;
    }
  });
  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);
  return [value, setValue];
}

function App() {
  const [route, setRoute] = useState(routeFromHash());
  const [portfolios, setPortfolios] = usePersistedState('aura-portfolios', defaultPortfolios);
  const [reports, setReports] = usePersistedState('aura-reports', reportsSeed);
  const [watchlist, setWatchlist] = usePersistedState('aura-watchlist', watchlistSeed);
  const [settings, setSettings] = usePersistedState('aura-settings', {
    name: 'Yan Lin Oo', email: 'yan@example.com', phone: '+1 (888) 123-4567', language: 'English', timezone: 'UTC+06:30 Yangon'
  });

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
          {navItems.map(([key, icon, label]) => (
            <button key={key} className={`nav-item ${isActive(key) ? 'active' : ''}`} onClick={() => go(key)}>
              <span className="nav-icon"><Icon name={icon} size={18}/></span><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="top-nav-actions">
          <button className="nav-action" aria-label="Search"><Icon name="search" size={21}/></button>
          <button className="nav-action notification-button" aria-label="Notifications">
            <Icon name="bell" size={21}/><span className="notification-dot" />
          </button>
          <div className="profile-menu-wrap">
            <button className="profile-trigger" onClick={() => setOpen(value => !value)} aria-expanded={open} aria-haspopup="menu">
              <span className="avatar">{initials}</span><span className="chevron"><Icon name="chevron-down" size={17}/></span>
            </button>
            {open && <div className="profile-menu" role="menu">
              <strong>{settings?.name || 'Aura User'}</strong>
              <small>{settings?.email || 'Portfolio owner'}</small>
              <button onClick={() => { setOpen(false); go('settings'); }}>Settings</button>
              <button onClick={() => { setOpen(false); go('watchlist'); }}>Watchlist</button>
              <button onClick={() => { setOpen(false); go('learn'); }}>Learn</button>
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
          <button className="dashboard-selector date-selector"><Icon name="calendar" size={19}/><span>May 11, 2026</span><span className="selector-chevron"><Icon name="chevron-down" size={17}/></span></button>
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

    <nav className="detail-tabs" aria-label="Portfolio sections">{['Overview','Holdings','Performance','Activity'].map(item=><button className={tab===item?'active':''} onClick={()=>setTab(item)} key={item}>{item}{item==='Holdings'&&<span>{portfolio.holdings.length}</span>}</button>)}</nav>

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

  function run() {
    if (mode!=='Historical Scenario' && Math.abs(totalAllocation-100)>0.01) return alert('Allocation must total 100%.');
    setRan(true);
  }
  function save() {
    setReports(prev=>[{id:Date.now(),name:`${scenario.label} ${mode}`,portfolio:portfolio.name,type:'Simulation',date:new Date().toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}),riskScore:null},...prev]);
    alert('Simulation saved to Reports.');
  }

  return <div className="page">
    <PageHeader title="Simulations" subtitle="Test your portfolio in different historical market scenarios." actions={<button className="secondary-btn" onClick={()=>go('reports')}>Simulation History</button>} />
    <div className="tabs simulation-tabs">{['Historical Scenario','Allocation Change','Combined Simulation'].map(t=><button key={t} className={mode===t?'active':''} onClick={()=>{setMode(t);setRan(false)}}>{t}</button>)}</div>
    <Card className="simulation-controls"><div><label>Select Portfolio</label><select value={portfolio.id} onChange={e=>go(`simulations/${e.target.value}`)}><option value={portfolio.id}>{portfolio.name}</option></select></div><div><label>Select Scenario</label><select value={scenarioId} onChange={e=>{setScenarioId(e.target.value);setRan(false)}}>{scenarioOptions.map(s=><option value={s.id} key={s.id}>{s.label} ({s.dates})</option>)}</select></div><button className="primary-btn" onClick={run}>Run Simulation</button></Card>
    {mode!=='Historical Scenario' && <Card><CardTitle title={mode==='Allocation Change'?'Test a Different Allocation':'Modified Allocation for Same Scenario'} right={<span className={Math.abs(totalAllocation-100)<.01?'green-text':'red-text'}>Total: {totalAllocation.toFixed(1)}%</span>} /><div className="allocation-editor">{portfolio.holdings.map(h=><label key={h.symbol}><span>{h.symbol}</span><input type="number" min="0" max="100" step="0.1" value={allocation[h.symbol]} onChange={e=>{setAllocation({...allocation,[h.symbol]:Number(e.target.value)});setRan(false)}}/><span>%</span></label>)}</div></Card>}
    {ran && <>
      <div className="stat-grid four"><StatCard label="Total Return" value={pct(simulatedReturn)} sub={scenario.label} tone={simulatedReturn<0?'red':'green'} spark={simulatedReturn<0?downturnA:lineA}/><StatCard label="Max Drawdown" value={`${(scenario.drawdown + allocationEffect*0.7).toFixed(2)}%`} sub="Peak-to-trough decline" tone="red" spark={downturnB}/><StatCard label="Volatility" value={`${Math.max(8,scenario.volatility-allocationEffect*0.25).toFixed(2)}%`} sub="Annualized"/><StatCard label="Recovery Time" value={`${Math.max(1,Math.round(scenario.recovery-allocationEffect*0.1))} months`} sub="Estimated historical recovery"/></div>
      <div className="simulation-grid"><Card><CardTitle title="Portfolio Value Over Time" right={<div className="chart-legend"><span className="p-dot"/>Your Portfolio <span className="b-dot"/>Benchmark</div>} /><LineChart primary={scenario.returnPct<0?downturnA:lineA} secondary={scenario.returnPct<0?downturnB:lineB} negative={scenario.returnPct<0} /></Card><Card><CardTitle title="Scenario Details" /><div className="scenario-details"><p>This simulation shows how the selected portfolio would have behaved using historical price movements during <strong>{scenario.label}</strong>.</p><dl><div><dt>Start / Event period</dt><dd>{scenario.dates}</dd></div><div><dt>Simulation mode</dt><dd>{mode}</dd></div><div><dt>Data basis</dt><dd>Historical market prices</dd></div></dl><button className="secondary-btn wide" onClick={save}>Save Simulation</button><button className="primary-btn wide" onClick={()=>go('assistant')}>Ask AI About This Scenario</button></div></Card></div>
      {mode==='Combined Simulation' && <Card><CardTitle title="Original vs Modified Allocation" /><div className="comparison-cards"><div><small>Original</small><strong>{pct(scenario.returnPct)}</strong><span>Historical return</span></div><div><small>Modified</small><strong className={simulatedReturn>scenario.returnPct?'green-text':'red-text'}>{pct(simulatedReturn)}</strong><span>Historical return</span></div><div><small>Difference</small><strong>{pct(simulatedReturn-scenario.returnPct)}</strong><span>Allocation effect</span></div></div></Card>}
    </>}
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
  return <div className="page assistant-page"><PageHeader title="AI Assistant" subtitle="Ask anything about your portfolio." />
    <div className="assistant-layout"><Card className="conversation-list"><button className="primary-btn wide" onClick={()=>setMessages([{role:'assistant',text:'New conversation started. What would you like to understand?'}])}>＋ New Conversation</button><small>Today</small>{['Why is my risk high?','How did I perform?','Which asset affects...'].map((t,i)=><button key={i} onClick={()=>send(t)}>{t}<span>{23-i*2}</span></button>)}<small>Yesterday</small>{['Explain correlation','How to reduce drawdown?'].map(t=><button key={t} onClick={()=>send(t)}>{t}</button>)}</Card>
    <Card className="chat-card"><div className="chat-head"><strong>Ask Aura about your portfolio.</strong><span className="online-dot"/> Portfolio-aware demo</div><div className="messages">{messages.map((m,i)=><div key={i} className={`message ${m.role}`}><span className="message-avatar">{m.role==='assistant'?'A':'Y'}</span><p>{m.text}</p></div>)}</div><div className="prompt-chips">{prompts.map(p=><button key={p} onClick={()=>send(p)}>{p}</button>)}</div><div className="chat-input"><input value={text} onChange={e=>setText(e.target.value)} onKeyDown={e=>e.key==='Enter'&&send()} placeholder="Ask follow-up question..."/><button onClick={()=>send()}>➜</button></div><p className="ai-disclaimer">Aura explains calculated and historical portfolio risk; it does not provide buy/sell advice.</p></Card>
    <Card className="context-card"><CardTitle title="Portfolio Context" /><div className="context-portfolio"><SymbolBadge symbol="TP"/><div><strong>{portfolio.name}</strong><small>{money(portfolio.value)}</small></div></div><dl><div><dt>Risk Score</dt><dd>{portfolio.riskScore}</dd></div><div><dt>Volatility</dt><dd>15.32%</dd></div><div><dt>Max Drawdown</dt><dd className="red-text">-21.45%</dd></div><div><dt>Sharpe Ratio</dt><dd>1.24</dd></div></dl><button className="secondary-btn wide" onClick={()=>go(`analytics/${portfolio.id}`)}>View Full Analysis</button></Card></div>
  </div>;
}

function Reports({ reports, setReports }) {
  const [query,setQuery]=useState('');
  const [type,setType]=useState('All Types');
  const visible=reports.filter(r=>(type==='All Types'||r.type===type)&&r.name.toLowerCase().includes(query.toLowerCase()));
  function download(r) {
    const body = `AURA REPORT\n\n${r.name}\nPortfolio: ${r.portfolio}\nType: ${r.type}\nDate: ${r.date}\nRisk Score: ${r.riskScore ?? 'N/A'}\n\nEducational portfolio risk report prototype.`;
    const blob = new Blob([body], {type:'text/plain'});
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`${slug(r.name)}.txt`;a.click();URL.revokeObjectURL(a.href);
  }
  return <div className="page"><PageHeader title="Reports" subtitle="View and manage your analysis reports." /><Card className="reports-card"><div className="report-filters"><input placeholder="Search reports..." value={query} onChange={e=>setQuery(e.target.value)}/><select><option>All Portfolios</option></select><select value={type} onChange={e=>setType(e.target.value)}><option>All Types</option><option>Analysis</option><option>Simulation</option><option>Comparison</option></select></div><div className="table-scroll"><table><thead><tr><th>Report</th><th>Portfolio</th><th>Type</th><th>Date</th><th>Risk Score</th><th>Action</th></tr></thead><tbody>{visible.map(r=><tr key={r.id}><td><strong>{r.name}</strong></td><td>{r.portfolio}</td><td>{r.type}</td><td>{r.date}</td><td>{r.riskScore?<RiskPill score={r.riskScore}/>:<span>—</span>}</td><td><button className="table-action" onClick={()=>download(r)}>⇩</button><button className="table-action" onClick={()=>setReports(prev=>prev.filter(x=>x.id!==r.id))}>⋮</button></td></tr>)}</tbody></table></div><div className="table-footer">Showing {visible.length} of {reports.length} reports <div><button>‹</button><button className="active">1</button><button>›</button></div></div></Card></div>;
}

function Watchlist({ watchlist, setWatchlist }) {
  const [query,setQuery]=useState('');
  const [add,setAdd]=useState(false);
  const visible=watchlist.filter(x=>x.symbol.toLowerCase().includes(query.toLowerCase())||x.name.toLowerCase().includes(query.toLowerCase()));
  function addAsset() {
    const symbol=prompt('Symbol (e.g. AMZN)'); if(!symbol) return;
    const clean=symbol.trim().toUpperCase();
    if(watchlist.some(x=>x.symbol===clean)) return alert('Already in watchlist.');
    setWatchlist(prev=>[...prev,{symbol:clean,name:`${clean} demo asset`,price:100,daily:0,yearly:0,cap:'—'}]);
  }
  return <div className="page"><PageHeader title="Watchlist" subtitle="Track assets you're interested in." actions={<button className="primary-btn" onClick={addAsset}>＋ Add Asset</button>} /><Card><div className="report-filters"><input placeholder="Search watchlist..." value={query} onChange={e=>setQuery(e.target.value)}/></div><div className="table-scroll"><table><thead><tr><th>Asset</th><th>Price</th><th>Daily Change</th><th>YTD Change</th><th>Market Cap</th><th>Action</th></tr></thead><tbody>{visible.map(a=><tr key={a.symbol}><td><div className="asset-cell"><SymbolBadge symbol={a.symbol}/><div><strong>{a.symbol}</strong><small>{a.name}</small></div></div></td><td>{money(a.price)}</td><td className={a.daily>=0?'green-text':'red-text'}>{pct(a.daily)}</td><td className={a.yearly>=0?'green-text':'red-text'}>{pct(a.yearly)}</td><td>{a.cap}</td><td><button className="table-action" onClick={()=>setWatchlist(prev=>prev.filter(x=>x.symbol!==a.symbol))}>×</button></td></tr>)}</tbody></table></div></Card></div>;
}

function Learn() {
  const lessons=[['Understanding Risk Score','How Aura combines volatility, drawdown, concentration, and diversification.'],['Volatility','Learn what historical price fluctuations mean for a portfolio.'],['Maximum Drawdown','Understand the largest peak-to-trough decline.'],['Sharpe Ratio','Learn about return relative to historical volatility.'],['Correlation','See why assets moving together can increase concentration risk.'],['Historical What-If','Learn how scenario simulations use past market periods.']];
  return <div className="page"><PageHeader title="Learn" subtitle="Beginner-friendly portfolio risk education." /><div className="lesson-grid">{lessons.map(([title,text],i)=><Card key={title} className="lesson-card"><span>{['◉','〽','↓','↗','⌘','◫'][i]}</span><h3>{title}</h3><p>{text}</p><button onClick={()=>alert(`${title}\n\n${text}\n\nThis learning module can later be connected to your course content or Aura knowledge base.`)}>Open lesson →</button></Card>)}</div></div>;
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
  return <div className="page"><PageHeader title="Settings" subtitle="Manage your account and preferences." /><div className="tabs">{['Profile','Preferences','Notifications','Security','Billing'].map(t=><button key={t} className={tab===t?'active':''} onClick={()=>setTab(t)}>{t}</button>)}</div>{tab==='Profile'?<Card className="settings-card"><div className="profile-panel"><div className="profile-photo">YL</div><strong>{form.name}</strong><small>{form.email}</small><button className="secondary-btn">Edit Profile</button></div><div className="settings-form"><label>Full Name<input value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Email<input value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></label><label>Phone<input value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})}/></label><label>Language<select value={form.language} onChange={e=>setForm({...form,language:e.target.value})}><option>English</option><option>Thai</option></select></label><label>Timezone<select value={form.timezone} onChange={e=>setForm({...form,timezone:e.target.value})}><option>UTC+06:30 Yangon</option><option>UTC+07:00 Bangkok</option></select></label><button className="primary-btn settings-save" onClick={save}>Save Changes</button></div></Card>:<Card className="empty-settings"><h2>{tab}</h2><p>This prototype includes the page state and navigation. Connect this section to authentication and account services when those backend features are added.</p></Card>}</div>;
}

function Timeline({ items }) {return <div className="timeline">{items.map((x,i)=><div key={x}><span>{i+1}</span><div><strong>{x}</strong><small>{i===0?'Today':`${i} day${i>1?'s':''} ago`}</small></div></div>)}</div>}

export default App;
