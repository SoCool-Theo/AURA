// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { Card } from '../components/ui/Card';
import { Icon } from '../components/ui/Icon';
import { usePersistedState } from '../hooks/usePersistedState';
import { defaultPortfolios } from '../mocks/portfolios.mock';
import { reportsSeed } from '../mocks/reports.mock';
import { defaultSettings } from '../mocks/settings.mock';
import { watchlistSeed } from '../mocks/watchlist.mock';
import { AnalyticsPage } from '../pages/analytics/AnalyticsPage';
import { AssistantPage } from '../pages/assistant/AssistantPage';
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { LearnPage } from '../pages/learn/LearnPage';
import { CreatePortfolioPage } from '../pages/portfolios/CreatePortfolioPage';
import { PortfolioDetailPage } from '../pages/portfolios/PortfolioDetailPage';
import { PortfoliosPage } from '../pages/portfolios/PortfoliosPage';
import { ReportsPage } from '../pages/reports/ReportsPage';
import { SimulationsPage } from '../pages/simulations/SimulationsPage';
import { WatchlistPage } from '../pages/watchlist/WatchlistPage';
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
    case 'watchlist': content = <WatchlistPage watchlist={watchlist} setWatchlist={setWatchlist} />; break;
    case 'learn': content = <LearnPage />; break;
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
