// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { MiniLineChart } from '../components/charts/MiniLineChart';
import { Card } from '../components/ui/Card';
import { Icon } from '../components/ui/Icon';
import { SymbolBadge } from '../components/ui/SymbolBadge';
import { usePersistedState } from '../hooks/usePersistedState';
import { downturnA, lineA } from '../mocks/dashboard.mock';
import { defaultPortfolios } from '../mocks/portfolios.mock';
import { reportsSeed } from '../mocks/reports.mock';
import { defaultSettings } from '../mocks/settings.mock';
import { watchlistSeed } from '../mocks/watchlist.mock';
import { AnalyticsPage } from '../pages/analytics/AnalyticsPage';
import { AssistantPage } from '../pages/assistant/AssistantPage';
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { CreatePortfolioPage } from '../pages/portfolios/CreatePortfolioPage';
import { PortfolioDetailPage } from '../pages/portfolios/PortfolioDetailPage';
import { PortfoliosPage } from '../pages/portfolios/PortfoliosPage';
import { ReportsPage } from '../pages/reports/ReportsPage';
import { SimulationsPage } from '../pages/simulations/SimulationsPage';
import { money, pct } from '../utils/formatting';
import { AppLayout } from './AppLayout';
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
    case 'dashboard': content = <DashboardPage portfolios={portfolios} settings={settings} />; break;
    case 'portfolios': content = <PortfoliosPage portfolios={portfolios} setPortfolios={setPortfolios} />; break;
    case 'portfolio': content = <PortfolioDetailPage portfolio={activePortfolio} setPortfolios={setPortfolios} />; break;
    case 'analytics': content = <AnalyticsPage portfolio={activePortfolio} setReports={setReports} />; break;
    case 'simulations': content = <SimulationsPage portfolio={activePortfolio} setReports={setReports} />; break;
    case 'assistant': content = <AssistantPage portfolio={activePortfolio} />; break;
    case 'reports': content = <ReportsPage reports={reports} setReports={setReports} />; break;
    case 'watchlist': content = <Watchlist watchlist={watchlist} setWatchlist={setWatchlist} />; break;
    case 'learn': content = <Learn />; break;
    case 'create': content = <CreatePortfolioPage portfolios={portfolios} setPortfolios={setPortfolios} />; break;
    case 'settings': content = <Settings settings={settings} setSettings={setSettings} />; break;
    default: content = <DashboardPage portfolios={portfolios} settings={settings} />;
  }

  return <AppLayout route={route} settings={settings}>{content}</AppLayout>;
}

function CardTitle({ title, right }) {
  return <div className="card-title"><h3>{title}</h3>{right}</div>;
}

function FeatureCard({ icon, title, text, button, onClick, tone = 'purple' }) {
  return <Card className={`feature-card ${tone}`}><div className="feature-icon">{icon}</div><div><h3>{title}</h3><p>{text}</p><button onClick={onClick}>{button}</button></div></Card>;
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

      {visible.length?<div className="watchlist-table-wrap" role="region" aria-label="Tracked assets" tabIndex={0}><table className="watchlist-table"><thead><tr><th>Asset</th><th>Price</th><th>Daily Change</th><th>YTD Change</th><th>Market Cap</th><th>Trend</th><th aria-label="Actions"/></tr></thead><tbody>{visible.map((asset,index)=><tr key={asset.symbol}><td><div className="watchlist-asset-cell"><SymbolBadge symbol={asset.symbol}/><div><strong>{asset.symbol}</strong><small>{asset.name}</small></div></div></td><td><div className="watchlist-price"><strong>{money(asset.price)}</strong><small>USD</small></div></td><td><span className={`watchlist-change ${asset.daily>=0?'positive':'negative'}`}>{asset.daily>=0?'↑':'↓'} {pct(asset.daily)}</span></td><td><span className={asset.yearly>=0?'green-text':'red-text'}>{pct(asset.yearly)}</span></td><td><strong className="watchlist-cap">{asset.cap}</strong></td><td><div className={`watchlist-spark ${asset.daily>=0?'positive':'negative'}`}><MiniLineChart values={(asset.daily>=0?lineA:downturnA).slice(index,index+10)}/></div></td><td><button className="watchlist-remove" onClick={()=>setWatchlist(previous=>previous.filter(item=>item.symbol!==asset.symbol))} aria-label={`Remove ${asset.symbol} from watchlist`} title="Remove from watchlist">×</button></td></tr>)}</tbody></table></div>:<div className="watchlist-empty-state"><span><Icon name="search" size={27}/></span><h3>{watchlist.length?'No matching assets':'Your watchlist is empty'}</h3><p>{watchlist.length?'Try a different symbol or company name.':'Add an asset to begin tracking market movements.'}</p><button className="secondary-btn" onClick={watchlist.length?()=>setQuery(''):addAsset}>{watchlist.length?'Clear Search':'Add Your First Asset'}</button></div>}
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

export default App;
