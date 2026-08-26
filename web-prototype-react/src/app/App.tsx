// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { LineChart } from '../components/charts/LineChart';
import { MiniLineChart } from '../components/charts/MiniLineChart';
import { PortfolioMetric } from '../components/portfolio/PortfolioMetric';
import { Card } from '../components/ui/Card';
import { Icon } from '../components/ui/Icon';
import { RiskPill } from '../components/ui/RiskPill';
import { SymbolBadge } from '../components/ui/SymbolBadge';
import { usePersistedState } from '../hooks/usePersistedState';
import { downturnA, downturnB, lineA, lineB } from '../mocks/dashboard.mock';
import { defaultPortfolios } from '../mocks/portfolios.mock';
import { reportsSeed } from '../mocks/reports.mock';
import { defaultSettings } from '../mocks/settings.mock';
import { scenarioOptions } from '../mocks/simulations.mock';
import { watchlistSeed } from '../mocks/watchlist.mock';
import { AnalyticsPage } from '../pages/analytics/AnalyticsPage';
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { CreatePortfolioPage } from '../pages/portfolios/CreatePortfolioPage';
import { PortfolioDetailPage } from '../pages/portfolios/PortfolioDetailPage';
import { PortfoliosPage } from '../pages/portfolios/PortfoliosPage';
import { money, pct } from '../utils/formatting';
import { slug } from '../utils/uiCalculations';
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
    case 'simulations': content = <Simulations portfolio={activePortfolio} {...shared} />; break;
    case 'assistant': content = <Assistant portfolio={activePortfolio} />; break;
    case 'reports': content = <Reports reports={reports} setReports={setReports} />; break;
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
