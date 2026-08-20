// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react';
import {
  correlation,
  defaultPortfolios,
  marketOverview,
  reportsSeed,
  scenarioOptions,
  watchlistSeed
} from './data/mockData';
import { backendReady } from './services';

const navItems = [
  ['dashboard', '⌂', 'Dashboard'],
  ['portfolios', '▣', 'Portfolios'],
  ['analytics', '◈', 'Analytics'],
  ['simulations', '◫', 'Simulations'],
  ['assistant', '◎', 'AI Assistant'],
  ['reports', '▤', 'Reports'],
  ['watchlist', '☆', 'Watchlist'],
  ['learn', '▥', 'Learn']
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
      <Sidebar route={route} />
      <main className="main-area">
        <div className="top-strip">
          <div className="demo-badge">{backendReady ? 'API connected' : 'Interactive frontend demo'}</div>
          <button className="icon-btn" aria-label="notifications">🔔<span className="notification-dot" /></button>
        </div>
        {content}
      </main>
    </div>
  );
}

function Sidebar({ route }) {
  return (
    <aside className="sidebar">
      <button className="brand" onClick={() => go('dashboard')}><span className="brand-mark">A</span><span>AURA</span></button>
      <nav className="nav-list">
        {navItems.map(([key, icon, label]) => (
          <button key={key} className={`nav-item ${route.page === key || (key === 'portfolios' && route.page === 'portfolio') ? 'active' : ''}`} onClick={() => go(key)}>
            <span>{icon}</span><span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-spacer" />
      <div className="quick-actions">
        <div className="quick-title">QUICK ACTIONS</div>
        <button onClick={() => go('create')}>＋ New Portfolio</button>
        <button onClick={() => go('simulations')}>▶ Run Simulation</button>
        <button onClick={() => go('assistant')}>✦ Ask AI Assistant</button>
      </div>
      <button className="user-card" onClick={() => go('settings')}>
        <div className="avatar">YL</div>
        <div><strong>Yan Lin Oo</strong><small>Premium Plan</small></div>
        <span>⌃</span>
      </button>
    </aside>
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

function LineChart({ primary = lineA, secondary, labels = ['Jan 21', 'Nov 21', 'Sep 22', 'Jul 23', 'May 24', 'May 26'], height = 210, negative = false }) {
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
        {[0.25, 0.5, 0.75].map(n => <line key={n} x1="14" y1={height*n} x2="686" y2={height*n} className="grid-line" />)}
        {negative && <line x1="14" y1={14 + (max / (max - min)) * (height - 42)} x2="686" y2={14 + (max / (max - min)) * (height - 42)} className="zero-line" />}
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
  const colors = ['#633cff', '#1f73ff', '#14b8a6', '#ff9f1c', '#f04fb3', '#8b5cf6'];
  let offset = 0;
  const circles = holdings.slice(0, 6).map((h, i) => {
    const dash = `${h.weight} ${100 - h.weight}`;
    const node = <circle key={h.symbol} cx="50" cy="50" r="34" fill="none" stroke={colors[i % colors.length]} strokeWidth="15" strokeDasharray={dash} strokeDashoffset={-offset} pathLength="100" />;
    offset += h.weight;
    return node;
  });
  return <svg className="donut" viewBox="0 0 100 100" transform="rotate(-90)">{circles}<circle cx="50" cy="50" r="24" fill="white" /></svg>;
}

function RiskPill({ score }) {
  const level = score >= 70 ? 'high' : score >= 55 ? 'moderate' : 'low';
  return <span className={`pill ${level}`}>{score} · {level === 'high' ? 'High' : level === 'moderate' ? 'Moderate' : 'Low'}</span>;
}

function Dashboard({ portfolios }) {
  const total = portfolios.reduce((s, p) => s + p.value, 0);
  const tech = portfolios.find(p => p.id === 'tech') || portfolios[0];
  return (
    <div className="page dashboard-page">
      <PageHeader title="Good evening, Yan! 👋" subtitle="Here's what's happening with your portfolios today." actions={<button className="select-btn">Jan 1, 2021 - May 11, 2026⌄</button>} />
      <div className="stat-grid five">
        <StatCard label="Total Portfolio Value" value={money(total)} sub="▲ $14,200 (6.4%)" tone="green" />
        <Card className="stat-card risk-stat"><small>Overall Risk Score</small><div className="risk-inline"><div><strong>65</strong><span className="stat-sub orange">Moderate</span></div><RiskGauge score={65} label="" /></div></Card>
        <StatCard label="Daily Volatility" value="15.32%" sub="Annualized" />
        <StatCard label="Max Drawdown" value="-21.45%" sub="Mar 2020" tone="red" spark={downturnA.slice(0, 12)} />
        <StatCard label="Sharpe Ratio" value="1.24" sub="Good" tone="blue" spark={lineB.slice(0, 12)} />
      </div>

      <div className="dashboard-grid top">
        <Card className="allocation-card"><CardTitle title="Portfolio Allocation" /><div className="allocation-body"><Donut holdings={tech.holdings} /><div className="legend">{tech.holdings.slice(0,4).map((h,i)=><div key={h.symbol}><span className={`legend-dot c${i}`}/><strong>{h.type}</strong><b>{h.weight}%</b><small>{money(h.value)}</small></div>)}</div></div></Card>
        <Card className="value-card"><CardTitle title="Portfolio Value Over Time" right={<div className="range-tabs"><button>1M</button><button>6M</button><button>1Y</button><button>3Y</button><button className="active">All</button></div>} /><LineChart primary={lineA} height={205}/></Card>
        <Card><CardTitle title="Top Risk Drivers" right={<button className="text-btn" onClick={() => go('analytics')}>View all</button>} /><div className="risk-list">{tech.holdings.slice(0,4).map((h,i)=><div key={h.symbol}><SymbolBadge symbol={h.symbol}/><div><strong>{h.name}</strong><small>{h.symbol}</small></div><b>{h.weight}%</b><span className={`mini-risk ${i < 2 ? 'high' : i === 2 ? 'moderate' : 'low'}`}>{i<2?'High':i===2?'Medium':'Low'}</span></div>)}</div></Card>
      </div>

      <div className="feature-strip">
        <FeatureCard icon="◉" title="Analyze Portfolio" text="Get comprehensive risk analysis and performance metrics." button="Analyze Now →" onClick={()=>go('analytics')} />
        <FeatureCard icon="◫" title="What-If Simulator" text="Test your portfolio in historical market scenarios." button="Run Simulation →" onClick={()=>go('simulations')} tone="blue" />
        <FeatureCard icon="••" title="AI Assistant" text="Ask questions and get simple explanations about your portfolio." button="Ask AI →" onClick={()=>go('assistant')} tone="pink" />
        <FeatureCard icon="▤" title="View Reports" text="Review your previous analysis reports and export data." button="View Reports →" onClick={()=>go('reports')} tone="green" />
        <FeatureCard icon="◷" title="Recent Simulation" text="See your recent what-if simulations and results." button="View All →" onClick={()=>go('simulations')} tone="orange" />
      </div>

      <div className="dashboard-grid bottom">
        <Card><CardTitle title="Recent Portfolios" right={<button className="text-btn" onClick={()=>go('portfolios')}>View all</button>} /><div className="portfolio-list">{portfolios.slice(0,4).map(p=><button key={p.id} onClick={()=>go(`portfolio/${p.id}`)}><SymbolBadge symbol={p.name.slice(0,2).toUpperCase()} /><div><strong>{p.name}</strong><small>{new Date(p.created).toLocaleDateString()}</small></div><b>{money(p.value)}</b><RiskPill score={p.riskScore}/></button>)}</div></Card>
        <Card><CardTitle title="Market Overview" right={<button className="text-btn" onClick={()=>go('watchlist')}>View more</button>} /><div className="market-list">{marketOverview.map((m,i)=><div key={m.symbol}><div><strong>{m.symbol}</strong><small>{m.price}</small></div><MiniLine values={i===2?downturnA.slice(0,10):lineB.slice(i, i+10)} /><span className={m.change>=0?'green-text':'red-text'}>{pct(m.change)}</span></div>)}</div></Card>
        <Card><CardTitle title="Asset Correlation (Heatmap)" right={<button className="text-btn" onClick={()=>go('analytics')}>View full</button>} /><Heatmap compact /></Card>
        <Card className="insight-card"><CardTitle title="✦ AI Insight" right={<button className="text-btn" onClick={()=>go('assistant')}>View all</button>} /><p>Your portfolio risk score is <strong>72 (Moderate)</strong>, mainly because NVDA and TSLA have a high combined weight and move together often.</p><p>Adding more bonds or defensive assets may reduce historical volatility.</p><button className="primary-btn wide" onClick={()=>go('assistant')}>Ask AI for details →</button></Card>
      </div>
    </div>
  );
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
  const [editing, setEditing] = useState(null);
  const visible = portfolios.filter(p => p.name.toLowerCase().includes(query.toLowerCase()));

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

  return <div className="page">
    <PageHeader title="Portfolios" subtitle="Create and manage your investment portfolios." actions={<button className="primary-btn" onClick={()=>go('create')}>＋ New Portfolio</button>} />
    <Card className="toolbar"><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search portfolios..."/><select><option>All risk levels</option><option>Low</option><option>Moderate</option><option>High</option></select></Card>
    <div className="portfolio-grid">{visible.map(p=><Card key={p.id} className="portfolio-card"><div className="portfolio-card-head"><div><SymbolBadge symbol={p.name.slice(0,2).toUpperCase()} /><div><h3>{p.name}</h3><small>Created {new Date(p.created).toLocaleDateString()}</small></div></div><button onClick={()=>setEditing(editing===p.id?null:p.id)}>•••</button>{editing===p.id&&<div className="menu-pop"><button onClick={()=>rename(p)}>Rename</button><button onClick={()=>duplicate(p)}>Duplicate</button><button className="danger" onClick={()=>remove(p)}>Delete</button></div>}</div><div className="portfolio-card-metrics"><div><small>Portfolio Value</small><strong>{money(p.value)}</strong></div><div><small>Total Return</small><strong className="green-text">{pct(p.totalReturn)}</strong></div><div><small>Risk Score</small><strong>{p.riskScore}</strong></div></div><div className="portfolio-card-allocation">{p.holdings.slice(0,5).map(h=><span key={h.symbol} style={{width:`${h.weight}%`}} title={`${h.symbol} ${h.weight}%`}/>)}</div><div className="holding-chips">{p.holdings.slice(0,4).map(h=><span key={h.symbol}>{h.symbol} {h.weight}%</span>)}</div><div className="portfolio-card-actions"><button className="secondary-btn" onClick={()=>go(`portfolio/${p.id}`)}>Open Portfolio</button><button className="primary-btn" onClick={()=>go(`analytics/${p.id}`)}>Analyze</button></div></Card>)}</div>
  </div>;
}

function PortfolioDetail({ portfolio, setPortfolios }) {
  const [tab, setTab] = useState('Overview');
  const [menu, setMenu] = useState(false);
  if (!portfolio) return null;

  function rename() {
    const name = prompt('New portfolio name', portfolio.name);
    if (name?.trim()) setPortfolios(prev=>prev.map(x=>x.id===portfolio.id?{...x,name:name.trim()}:x));
  }
  function updateWeight(symbol, next) {
    const n = clamp(Number(next)||0,0,100);
    setPortfolios(prev=>prev.map(p=>p.id!==portfolio.id?p:{...p,holdings:p.holdings.map(h=>h.symbol===symbol?{...h,weight:n}:h)}));
  }
  return <div className="page">
    <button className="back-link" onClick={()=>go('portfolios')}>← Back to Portfolios</button>
    <PageHeader title={<>{portfolio.name} <button className="tiny-icon" onClick={rename}>✎</button></>} subtitle={`Created on ${new Date(portfolio.created).toLocaleDateString()}  •  Last analyzed May 11, 2026`} actions={<><button className="primary-btn" onClick={()=>go(`analytics/${portfolio.id}`)}>Analyze Again</button><div className="relative"><button className="secondary-btn" onClick={()=>setMenu(!menu)}>More •••</button>{menu&&<div className="menu-pop header-menu"><button onClick={rename}>Rename</button><button onClick={()=>go(`simulations/${portfolio.id}`)}>Run Simulation</button><button onClick={()=>go('reports')}>View Reports</button></div>}</div></>} />
    <div className="tabs">{['Overview','Holdings','Performance','Activity'].map(t=><button className={tab===t?'active':''} onClick={()=>setTab(t)} key={t}>{t}</button>)}</div>
    {tab==='Overview' && <>
      <div className="stat-grid four"><StatCard label="Total Value" value={money(portfolio.value)} sub="Current portfolio"/><StatCard label="Total Return (Ann.)" value={pct(portfolio.totalReturn)} sub="Historical annualized" tone="green"/><Card className="stat-card"><small>Risk Score</small><div className="risk-inline"><div><strong>{portfolio.riskScore}</strong><span className="stat-sub orange">{portfolio.riskLevel}</span></div><RiskGauge score={portfolio.riskScore}/></div></Card><StatCard label="Cash" value={money(portfolio.cash)} sub={`${((portfolio.cash/portfolio.value)*100||0).toFixed(1)}% of portfolio`}/></div>
      <div className="portfolio-overview-grid"><HoldingsTable portfolio={portfolio}/><Card><CardTitle title="Performance (Cumulative)" right={<div className="range-tabs"><button>1M</button><button>6M</button><button>1Y</button><button>3Y</button><button className="active">All</button></div>} /><div className="chart-legend"><span className="p-dot"/>Your Portfolio <span className="b-dot"/>Benchmark (S&P 500)</div><LineChart primary={lineA} secondary={lineB}/><div className="performance-kpis"><div><strong className="green-text">+8.32%</strong><small>Best Month<br/>Apr 2023</small></div><div><strong className="red-text">-6.91%</strong><small>Worst Month<br/>Mar 2020</small></div><div><strong>62%</strong><small>Positive Months</small></div><div><strong>1.08</strong><small>Beta</small></div></div></Card></div>
    </>}
    {tab==='Holdings' && <Card><CardTitle title="Edit Holdings" right={<span className="subtle">Weights are editable for prototype testing</span>} /><div className="edit-holdings">{portfolio.holdings.map(h=><div key={h.symbol}><SymbolBadge symbol={h.symbol}/><div><strong>{h.symbol}</strong><small>{h.name}</small></div><input type="number" min="0" max="100" value={h.weight} onChange={e=>updateWeight(h.symbol,e.target.value)}/><span>%</span><strong>{money(h.value)}</strong></div>)}</div></Card>}
    {tab==='Performance' && <Card><CardTitle title="Historical Performance" /><LineChart primary={lineA} secondary={lineB} height={300}/><p className="note">This prototype uses deterministic demo series. Connect the page to Aura's analysis API when the backend service and routes are ready.</p></Card>}
    {tab==='Activity' && <Card><CardTitle title="Recent Activity" /><Timeline items={['Portfolio analyzed — risk score 72','2008 Financial Crisis simulation completed','Holding weight updated for NVDA','Portfolio created']} /></Card>}
  </div>;
}

function HoldingsTable({ portfolio }) {
  return <Card><CardTitle title="Holdings" /><div className="table-scroll"><table><thead><tr><th>Asset</th><th>Weight</th><th>Value</th><th>Daily Change</th></tr></thead><tbody>{portfolio.holdings.map(h=><tr key={h.symbol}><td><div className="asset-cell"><SymbolBadge symbol={h.symbol}/><div><strong>{h.symbol}</strong><small>{h.name}</small></div></div></td><td>{h.weight}%</td><td>{money(h.value)}</td><td className={h.dailyChange>0?'green-text':h.dailyChange<0?'red-text':''}>{h.dailyChange===0?'—':pct(h.dailyChange)}</td></tr>)}</tbody><tfoot><tr><td>Total</td><td>100%</td><td>{money(portfolio.value)}</td><td/></tr></tfoot></table></div></Card>;
}

function Analytics({ portfolio, setReports }) {
  const riskDrivers = portfolio.holdings.map((h,i)=>({ ...h, contribution: Math.max(2, (h.weight*(i===0?1.1:i===1?0.9:0.55))).toFixed(1), level: i<2?'High':i===2?'Moderate':'Low' }));
  function saveReport() {
    const report = {id:Date.now(),name:`${portfolio.name} Analysis`,portfolio:portfolio.name,type:'Analysis',date:new Date().toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}),riskScore:portfolio.riskScore};
    setReports(prev=>[report,...prev]);
    alert('Analysis snapshot saved to Reports.');
  }
  return <div className="page">
    <PageHeader title="Portfolio Analysis" subtitle={`Risk report for ${portfolio.name}.`} actions={<><button className="secondary-btn" onClick={()=>go('assistant')}>✦ Ask AI</button><button className="primary-btn" onClick={saveReport}>Save Report</button></>} />
    <Card className="analysis-hero"><div><span className="eyebrow">OVERALL RISK SUMMARY</span><h2>{portfolio.riskScore}/100 · {portfolio.riskLevel}</h2><p>Your portfolio has a moderate risk profile. The largest risk comes from concentrated exposure to high-volatility technology assets and positive correlation between the biggest positions.</p><div className="analysis-actions"><button className="primary-btn" onClick={()=>go('assistant')}>Ask AI About This</button><button className="secondary-btn" onClick={()=>go(`simulations/${portfolio.id}`)}>Run What-If Simulation</button></div></div><RiskGauge score={portfolio.riskScore} label="Moderate" /></Card>
    <div className="stat-grid four"><StatCard label="Volatility (Annualized)" value="15.32%" sub="Moderate"/><StatCard label="Maximum Drawdown" value="-21.45%" sub="Historical peak-to-trough" tone="red"/><StatCard label="Sharpe Ratio" value="1.24" sub="Good risk-adjusted return" tone="green"/><StatCard label="Diversification" value="56/100" sub="Moderate" tone="orange"/></div>
    <div className="analytics-grid"><Card><CardTitle title="Main Risk Drivers" /><div className="driver-table"><div className="driver-head"><span>Asset</span><span>Portfolio Weight</span><span>Risk Contribution</span><span>Level</span></div>{riskDrivers.map(r=><div className="driver-row" key={r.symbol}><div className="asset-cell"><SymbolBadge symbol={r.symbol}/><div><strong>{r.symbol}</strong><small>{r.name}</small></div></div><b>{r.weight}%</b><div className="bar-meter"><span style={{width:`${Math.min(100,Number(r.contribution))}%`}}/></div><span className={`mini-risk ${r.level.toLowerCase()}`}>{r.level}</span></div>)}</div></Card><Card><CardTitle title="Asset Relationships" /><Heatmap /><p className="note">Higher positive values mean two assets historically moved more closely together. Negative values can support diversification.</p></Card></div>
    <Card><CardTitle title="Individual Asset Details" /><div className="asset-detail-grid">{portfolio.holdings.filter(h=>h.symbol!=='CASH').map((h,i)=><div key={h.symbol} className="asset-detail"><div className="asset-cell"><SymbolBadge symbol={h.symbol}/><div><strong>{h.symbol}</strong><small>{h.name}</small></div></div><dl><div><dt>Weight</dt><dd>{h.weight}%</dd></div><div><dt>Annualized return</dt><dd>{pct(8+i*2.1)}</dd></div><div><dt>Volatility</dt><dd>{(14+i*4.2).toFixed(1)}%</dd></div><div><dt>Max drawdown</dt><dd className="red-text">-{(18+i*7.3).toFixed(1)}%</dd></div><div><dt>Sharpe</dt><dd>{(1.4-i*0.17).toFixed(2)}</dd></div></dl></div>)}</div></Card>
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
  return <div className="page create-page"><PageHeader title="Create New Portfolio" subtitle="Set up your portfolio details." /><div className="wizard-layout"><Card className="wizard-steps">{[['1','Basic Info'],['2','Add Holdings'],['3','Review']].map(([n,label])=><button key={n} className={step===Number(n)?'active':''} onClick={()=>setStep(Number(n))}><span>{n}</span>{label}</button>)}</Card><Card className="wizard-main">{step===1&&<><h2>Basic Info</h2><label>Portfolio Name<input value={name} onChange={e=>setName(e.target.value)}/></label><label>Description (optional)<textarea rows="4" value={description} onChange={e=>setDescription(e.target.value)}/></label><label>Currency<select><option>USD - US Dollar</option></select></label><div className="wizard-art"><div className="fake-pie">◔</div><span>Build a portfolio, then analyze its historical risk.</span></div><div className="wizard-footer"><span/><button className="primary-btn" onClick={()=>setStep(2)}>Next: Add Holdings →</button></div></>}{step===2&&<><div className="wizard-title-row"><h2>Add Holdings</h2><button className="primary-btn" onClick={addHolding}>Add Manually</button></div><input className="asset-search" placeholder="Search assets (e.g., AAPL, Microsoft, etc.)"/><div className="table-scroll"><table><thead><tr><th>Asset</th><th>Type</th><th>Price</th><th>Shares / Amount</th><th>Allocation</th><th>Action</th></tr></thead><tbody>{holdings.map(h=><tr key={h.symbol}><td><div className="asset-cell"><SymbolBadge symbol={h.symbol}/><div><strong>{h.symbol}</strong><small>{h.name}</small></div></div></td><td>{h.type}</td><td>{money(h.price)}</td><td><input className="table-input" type="number" value={h.shares} onChange={e=>setHoldings(holdings.map(x=>x.symbol===h.symbol?{...x,shares:Number(e.target.value)}:x))}/></td><td>{h.weight}%</td><td><button className="table-action" onClick={()=>removeHolding(h.symbol)}>×</button></td></tr>)}</tbody></table></div><div className="allocation-total">Total Allocation <strong className={Math.abs(totalWeight-100)<.2?'green-text':'orange-text'}>{totalWeight.toFixed(1)}%</strong></div><div className="wizard-footer"><button className="secondary-btn" onClick={()=>setStep(1)}>← Back</button><button className="primary-btn" onClick={()=>setStep(3)}>Next: Review →</button></div></>}{step===3&&<><h2>Review Portfolio</h2><div className="review-summary"><div><small>Name</small><strong>{name}</strong></div><div><small>Total Value</small><strong>{money(total)}</strong></div><div><small>Holdings</small><strong>{holdings.length}</strong></div><div><small>Allocation</small><strong>{totalWeight.toFixed(1)}%</strong></div></div><HoldingsReview holdings={holdings}/><p className="note">After creation, Aura can analyze the portfolio once the frontend is connected to the backend analysis service.</p><div className="wizard-footer"><button className="secondary-btn" onClick={()=>setStep(2)}>← Back</button><button className="primary-btn" onClick={create}>Create Portfolio ✓</button></div></>}</Card></div></div>;
}

function HoldingsReview({ holdings }) {return <div className="holding-review">{holdings.map(h=><div key={h.symbol}><div className="asset-cell"><SymbolBadge symbol={h.symbol}/><div><strong>{h.symbol}</strong><small>{h.name}</small></div></div><strong>{h.weight}%</strong><span>{money(h.price*h.shares)}</span></div>)}</div>}

function Settings({ settings, setSettings }) {
  const [form,setForm]=useState(settings); const [tab,setTab]=useState('Profile');
  function save(){setSettings(form);alert('Settings saved.');}
  return <div className="page"><PageHeader title="Settings" subtitle="Manage your account and preferences." /><div className="tabs">{['Profile','Preferences','Notifications','Security','Billing'].map(t=><button key={t} className={tab===t?'active':''} onClick={()=>setTab(t)}>{t}</button>)}</div>{tab==='Profile'?<Card className="settings-card"><div className="profile-panel"><div className="profile-photo">YL</div><strong>{form.name}</strong><small>{form.email}</small><button className="secondary-btn">Edit Profile</button></div><div className="settings-form"><label>Full Name<input value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Email<input value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></label><label>Phone<input value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})}/></label><label>Language<select value={form.language} onChange={e=>setForm({...form,language:e.target.value})}><option>English</option><option>Thai</option></select></label><label>Timezone<select value={form.timezone} onChange={e=>setForm({...form,timezone:e.target.value})}><option>UTC+06:30 Yangon</option><option>UTC+07:00 Bangkok</option></select></label><button className="primary-btn settings-save" onClick={save}>Save Changes</button></div></Card>:<Card className="empty-settings"><h2>{tab}</h2><p>This prototype includes the page state and navigation. Connect this section to authentication and account services when those backend features are added.</p></Card>}</div>;
}

function Timeline({ items }) {return <div className="timeline">{items.map((x,i)=><div key={x}><span>{i+1}</span><div><strong>{x}</strong><small>{i===0?'Today':`${i} day${i>1?'s':''} ago`}</small></div></div>)}</div>}

export default App;
