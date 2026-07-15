import { useState } from "react";
import type { CSSProperties, FormEvent, ReactNode } from "react";
import {
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  BriefcaseBusiness,
  Download,
  FileText,
  Gauge,
  GitBranch,
  GraduationCap,
  LineChart as LineIcon,
  MoreVertical,
  Plus,
  Send,
  Settings,
  Share2,
  Sparkles,
  Star,
  Trash2,
} from "lucide-react";
import { Link, NavLink, Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const performance = [
  { month: "Jun", portfolio: 100, benchmark: 100 },
  { month: "Jul", portfolio: 104, benchmark: 102 },
  { month: "Aug", portfolio: 102, benchmark: 101 },
  { month: "Sep", portfolio: 108, benchmark: 104 },
  { month: "Oct", portfolio: 107, benchmark: 105 },
  { month: "Nov", portfolio: 114, benchmark: 109 },
  { month: "Dec", portfolio: 112, benchmark: 108 },
  { month: "Jan", portfolio: 119, benchmark: 111 },
  { month: "Feb", portfolio: 121, benchmark: 113 },
  { month: "Mar", portfolio: 126, benchmark: 116 },
  { month: "Apr", portfolio: 124, benchmark: 118 },
  { month: "May", portfolio: 131, benchmark: 120 },
];

const simulation = [
  { month: "Oct '07", portfolio: 0, benchmark: 0 },
  { month: "Jan '08", portfolio: -3, benchmark: -2 },
  { month: "Apr '08", portfolio: -22, benchmark: -17 },
  { month: "Jul '08", portfolio: -34, benchmark: -25 },
  { month: "Oct '08", portfolio: -27, benchmark: -21 },
  { month: "Jan '09", portfolio: -37, benchmark: -29 },
  { month: "Mar '09", portfolio: -18, benchmark: -15 },
];

const portfolios = [
  ["Growth Portfolio", 63, "+12.45%", "May 14, 2026", "Moderate"],
  ["Conservative Income", 28, "+4.32%", "May 10, 2026", "Low"],
  ["Balanced Approach", 52, "+8.91%", "May 5, 2026", "Moderate"],
  ["Tech Focused", 72, "+15.21%", "Apr 28, 2026", "High"],
  ["Retirement Plan", 34, "+5.67%", "Apr 20, 2026", "Low"],
] as const;

type HoldingRow = {
  asset: string;
  type: string;
  allocation: number;
  amount: number;
};

const holdings: HoldingRow[] = [
  { asset: "AAPL · Apple Inc.", type: "Equity", allocation: 25, amount: 2500 },
  { asset: "MSFT · Microsoft Corp.", type: "Equity", allocation: 25, amount: 2500 },
  { asset: "VTI · Vanguard Total Stock Mkt", type: "ETF", allocation: 20, amount: 2000 },
  { asset: "AGG · iShares Core U.S. Aggregate Bond", type: "Bond", allocation: 20, amount: 2000 },
  { asset: "GLD · SPDR Gold Shares", type: "Commodity", allocation: 10, amount: 1000 },
];

const watchlist = [
  ["AAPL", "Apple Inc.", "$190.02", "+1.21%", "+24.32%"],
  ["MSFT", "Microsoft Corp.", "$415.37", "+0.85%", "+18.56%"],
  ["SPY", "SPDR S&P 500 ETF", "$535.16", "+0.46%", "+11.70%"],
  ["GLD", "SPDR Gold Shares", "$215.43", "-0.30%", "+13.11%"],
  ["AGG", "iShares Core U.S. Agg Bond", "$98.76", "-0.11%", "+3.34%"],
] as const;

const reports = [
  ["Growth Portfolio Risk Report", "Growth Portfolio", "May 14, 2026", "Risk Report"],
  ["2008 Crisis Simulation Report", "Growth Portfolio", "May 14, 2026", "Simulation"],
  ["Conservative Analysis Report", "Balanced Approach", "May 10, 2026", "Analysis"],
  ["Performance Summary Q1 2026", "Growth Portfolio", "May 1, 2026", "Performance"],
  ["What-if Analysis Report", "Conservative Income", "May 1, 2026", "Simulation"],
] as const;

function Brand() {
  return <Link className="brand" to="/"><span className="brandMark">A</span><span>AURA</span></Link>;
}

function ButtonLink({ to, children, secondary = false }: { to: string; children: ReactNode; secondary?: boolean }) {
  return <Link className={`button ${secondary ? "secondary" : "primary"}`} to={to}>{children}</Link>;
}

function Badge({ value }: { value: string }) {
  return <span className={`badge ${value.toLowerCase()}`}>{value}</span>;
}

function GaugeChart({ value = 63, dark = false }: { value?: number; dark?: boolean }) {
  return (
    <div className={`gauge ${dark ? "dark" : ""}`} style={{ "--score": `${value * 3.6}deg` } as CSSProperties}>
      <div><strong>{value}</strong><span>Moderate Risk</span></div>
    </div>
  );
}

function PageHeader({ title, subtitle, action }: { title: string; subtitle: string; action?: ReactNode }) {
  return <header className="pageHeader"><div><h1>{title}</h1><p>{subtitle}</p></div>{action}</header>;
}

function Sidebar() {
  const links = [
    ["Overview", "/dashboard", Gauge],
    ["My Portfolios", "/portfolios", BriefcaseBusiness],
    ["Simulator", "/simulator", LineIcon],
    ["AI Assistant", "/assistant", Bot],
    ["Reports", "/reports", FileText],
    ["Watchlist", "/watchlist", Star],
    ["Learn", "/learn", GraduationCap],
    ["Settings", "/settings", Settings],
  ] as const;
  return <aside className="sidebar">
    <Brand />
    <nav>{links.map(([label, path, Icon]) => <NavLink key={path} to={path} className={({ isActive }) => isActive ? "active" : ""}><Icon size={17}/><span>{label}</span></NavLink>)}</nav>
    <div className="upgrade"><BarChart3 size={20}/><strong>Upgrade to Pro</strong><p>Unlock advanced simulations, AI insights, and reports.</p><button>Upgrade Now</button></div>
  </aside>;
}

function Shell() {
  return <div className="shell"><Sidebar/><div className="content"><div className="topbar"><span>AURA workspace</span><div><button className="icon"><Bell size={17}/></button><span className="avatar">A</span></div></div><main><Outlet/></main></div></div>;
}

function Landing() {
  return <div className="landing">
    <header className="landingNav"><Brand/><nav><a href="#features">Features</a><a href="#works">How It Works</a><a href="#pricing">Pricing</a><a href="#about">About</a></nav><div><ButtonLink to="/login" secondary>Log In</ButtonLink><ButtonLink to="/signup">Get Started</ButtonLink></div></header>
    <section className="hero"><div className="heroCopy"><span className="eyebrow"><Sparkles size={14}/> AI-Powered · Explainable · Educational</span><h1>AI-Powered Portfolio Risk Intelligence</h1><p>Translating complex financial data into simple portfolio risk education.</p><div className="heroButtons"><ButtonLink to="/signup">Get Started Free</ButtonLink><ButtonLink to="/dashboard" secondary>View Demo</ButtonLink></div></div>
      <div className="heroCards">
        <article className="glass riskPreview"><small>Portfolio Risk Score</small><GaugeChart dark/></article>
        <article className="glass chartPreview"><small>Portfolio Performance (1Y)</small><strong className="positive">+12.45%</strong><ResponsiveContainer width="100%" height={180}><LineChart data={performance}><Line dataKey="portfolio" stroke="#55d8ff" strokeWidth={3} dot={false}/></LineChart></ResponsiveContainer></article>
        <article className="glass contributors"><small>Top Risk Contributors</small>{[["Technology",41],["Equities",28],["Bonds",19],["Commodities",12]].map(([n,v])=><div key={n}><span>{n}</span><i><b style={{width:`${v}%`}}/></i><strong>{v}%</strong></div>)}</article>
        <article className="glass allocation"><small>Asset Allocation</small><div className="donut"/><ul><li>Equities 60%</li><li>Bonds 20%</li><li>Gold 10%</li><li>Cash 10%</li></ul></article>
      </div>
    </section>
    <section id="features" className="featureStrip">{[
      { Icon: Bot, title: "Explainable AI", text: "Clear explanations grounded in calculated portfolio data." },
      { Icon: LineIcon, title: "Historical Simulation", text: "Explore how a portfolio behaved in past market periods." },
      { Icon: BookOpen, title: "Educational First", text: "Aura teaches risk and does not provide buy or sell advice." },
    ].map(({Icon,title,text})=><article key={title}><Icon size={24}/><div><h3>{title}</h3><p>{text}</p></div></article>)}</section>
  </div>;
}

function Dashboard() {
  const allocation = [{name:"Equities",value:60},{name:"Bonds",value:20},{name:"Gold",value:10},{name:"Cash",value:10}];
  return <><PageHeader title="Welcome back, Astrophage! 👋" subtitle="Here is your portfolio overview." action={<ButtonLink to="/portfolios/new"><Plus size={16}/> New Portfolio</ButtonLink>}/>
    <section className="metrics"><article><span>Portfolio Risk Score</span><GaugeChart value={63}/></article><article><span>1Y Performance</span><strong className="positive">+12.45%</strong><small>vs benchmark +8.32%</small></article><article><span>Sharpe Ratio</span><strong className="accent">1.24</strong><small className="positive">Good</small></article><article><span>Max Drawdown</span><strong className="negative">-18.32%</strong><small className="negative">High</small></article></section>
    <section className="dashboardGrid"><article className="panel wide"><h2>Performance (1 Year)</h2><ResponsiveContainer width="100%" height={280}><LineChart data={performance}><CartesianGrid strokeDasharray="3 3" stroke="#e8ebf6"/><XAxis dataKey="month"/><YAxis/><Tooltip/><Legend/><Line dataKey="portfolio" name="Your Portfolio" stroke="#3f51ff" strokeWidth={3} dot={false}/><Line dataKey="benchmark" name="Benchmark (SPY)" stroke="#aeb7d9" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer></article>
    <article className="panel"><h2>Asset Allocation</h2><ResponsiveContainer width="100%" height={260}><PieChart><Pie data={allocation} dataKey="value" nameKey="name" innerRadius={52} outerRadius={82}>{["#4b5cff","#2f7df6","#f7b84b","#d8ddff"].map(c=><Cell key={c} fill={c}/>)}</Pie><Tooltip/><Legend/></PieChart></ResponsiveContainer></article>
    <article className="panel"><h2>Recent Portfolios</h2>{portfolios.slice(0,3).map(p=><div className="listRow" key={p[0]}><div><strong>{p[0]}</strong><small>{p[3]}</small></div><span>{p[1]}</span><span className="positive">{p[2]}</span><Badge value={p[4]}/></div>)}</article>
    <article className="panel aiPanel"><span>AI</span><div><h2>AI Insight</h2><p>Your portfolio risk is moderate. Technology stocks contribute the most risk. Consider more bonds to improve stability.</p><ButtonLink to="/assistant">Ask AI Assistant</ButtonLink></div></article></section></>;
}

function Portfolios() {
  return <><PageHeader title="My Portfolios" subtitle="Create and manage your investment portfolios." action={<ButtonLink to="/portfolios/new"><Plus size={16}/> New Portfolio</ButtonLink>}/><article className="panel tablePanel"><table><thead><tr><th>Portfolio</th><th>Risk Score</th><th>1Y Performance</th><th>Last Updated</th><th>Status</th><th/></tr></thead><tbody>{portfolios.map(p=><tr key={p[0]}><td><strong>{p[0]}</strong></td><td>{p[1]}</td><td className="positive">{p[2]}</td><td>{p[3]}</td><td><Badge value={p[4]}/></td><td><button className="icon"><MoreVertical size={16}/></button></td></tr>)}</tbody></table></article><article className="panel createCta"><div><small>Create New Portfolio</small><h2>Start building a new portfolio from scratch.</h2><ButtonLink to="/portfolios/new"><Plus size={16}/> Create Portfolio</ButtonLink></div><div className="ctaArt"><span/><span/><span/></div></article></>;
}

function PortfolioEditor() {
  const navigate = useNavigate();
  const [rows,setRows] = useState<HoldingRow[]>(holdings);
  const totalAllocation=rows.reduce((s,r)=>s+Number(r.allocation),0); const totalAmount=rows.reduce((s,r)=>s+Number(r.amount),0);
  return <><PageHeader title="Create New Portfolio" subtitle="Add assets and set your investment allocation."/><article className="panel editor"><label>Portfolio Name<input defaultValue="My New Portfolio"/></label><div className="tablePanel"><table><thead><tr><th>Asset</th><th>Type</th><th>Allocation (%)</th><th>Amount (USD)</th><th/></tr></thead><tbody>{rows.map((r,i)=><tr key={i}><td><input value={r.asset} onChange={e=>setRows(rows.map((x,j)=>j===i?{...x,asset:e.target.value}:x))}/></td><td><select value={r.type} onChange={e=>setRows(rows.map((x,j)=>j===i?{...x,type:e.target.value}:x))}><option>Equity</option><option>ETF</option><option>Bond</option><option>Commodity</option><option>Cash</option></select></td><td><input type="number" value={r.allocation} onChange={e=>setRows(rows.map((x,j)=>j===i?{...x,allocation:Number(e.target.value)}:x))}/></td><td><input type="number" value={r.amount} onChange={e=>setRows(rows.map((x,j)=>j===i?{...x,amount:Number(e.target.value)}:x))}/></td><td><button className="icon" onClick={()=>setRows(rows.filter((_,j)=>j!==i))}><Trash2 size={16}/></button></td></tr>)}</tbody></table></div><button className="textButton" onClick={()=>setRows([...rows,{asset:"NEW · New Asset",type:"Equity",allocation:0,amount:0}])}><Plus size={15}/> Add Asset</button><footer><div><small>Total Allocation</small><strong className={totalAllocation===100?"positive":"negative"}>{totalAllocation}%</strong></div><div><small>Total Amount</small><strong>${totalAmount.toLocaleString()}</strong></div><button className="button primary" disabled={totalAllocation!==100} onClick={()=>navigate("/analysis")}>Analyze Portfolio</button></footer></article></>;
}

function Analysis() {
  return <><PageHeader title="Portfolio Analysis" subtitle="Growth Portfolio · Risk report based on weights and historical data." action={<div className="actions"><button className="button secondary"><Download size={16}/> Download Report</button><button className="button secondary"><Share2 size={16}/> Share</button></div>}/><div className="tabs">{["Overview","Risk Analysis","Performance","Correlation","Holdings"].map((t,i)=><button className={i===0?"active":""} key={t}>{t}</button>)}</div><section className="analysisGrid"><article className="panel centered"><h2>Risk Summary</h2><GaugeChart/><p>You are taking a moderate level of risk. The portfolio has meaningful growth potential but may decline during severe markets.</p></article><article className="panel"><h2>Key Metrics</h2>{[["Volatility (1Y)","14.32%"],["Sharpe Ratio","1.24"],["Maximum Drawdown","-18.32%"],["Diversification Level","0.72"],["Beta","1.12"]].map(x=><div className="definition" key={x[0]}><span>{x[0]}</span><strong className={x[0].includes("Drawdown")?"negative":""}>{x[1]}</strong></div>)}</article><article className="panel"><h2>Risk Contribution</h2>{[["Technology",41],["Equities",28],["Commodities",15],["Bonds",10],["Cash",6]].map(x=><div className="barRow" key={x[0]}><span>{x[0]}</span><i><b style={{width:`${x[1]}%`}}/></i><strong>{x[1]}%</strong></div>)}</article><article className="panel analysisChart"><h2>Performance (1 Year)</h2><ResponsiveContainer width="100%" height={280}><LineChart data={performance}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="month"/><YAxis/><Tooltip/><Legend/><Line dataKey="portfolio" name="Your Portfolio" stroke="#3f51ff" strokeWidth={3} dot={false}/><Line dataKey="benchmark" name="Benchmark" stroke="#aeb7d9" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer></article><article className="panel aiExplanation"><small>AI Explanation</small><h2>What is driving your risk?</h2><p>Technology stocks are the main contributor. They are more volatile, so downturns can produce larger losses. More bonds or gold could reduce overall risk.</p><ButtonLink to="/assistant">Ask AI Assistant</ButtonLink></article></section></>;
}

function Simulator() {
  return <><PageHeader title="Historical What-If Simulator" subtitle="Test your portfolio in different historical market periods."/><section className="simulatorGrid"><aside className="panel controls"><label>Select Portfolio<select><option>Growth Portfolio</option><option>Balanced Approach</option></select></label><label>Select Historical Period<select><option>2008 Financial Crisis</option><option>2020 COVID Crash</option></select></label><label>Initial Investment (USD)<input type="number" defaultValue={10000}/></label><button className="button primary">Run Simulation</button></aside><div><section className="metrics three"><article><span>Total Return</span><strong className="negative">-37.42%</strong></article><article><span>Max Drawdown</span><strong className="negative">-45.61%</strong></article><article><span>Volatility</span><strong>28.73%</strong></article></section><article className="panel"><ResponsiveContainer width="100%" height={350}><LineChart data={simulation}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="month"/><YAxis/><Tooltip/><Legend/><Line dataKey="portfolio" name="Your Portfolio" stroke="#3f51ff" strokeWidth={3} dot={false}/><Line dataKey="benchmark" name="Benchmark" stroke="#aeb7d9" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer></article><article className="panel insight"><strong>AI Insight</strong><p>During the 2008 crisis, high equity exposure increased losses. Adding more bonds could have reduced the drawdown.</p></article></div></section></>;
}

function Assistant() {
  const [messages,setMessages]=useState([{who:"ai",text:"Your portfolio has a moderate risk score, mainly because 60% is in equities."},{who:"user",text:"Which asset affects my risk the most?"},{who:"ai",text:"Technology stocks such as AAPL and MSFT contribute the most risk."}]); const [draft,setDraft]=useState("");
  const submit=(e:FormEvent)=>{e.preventDefault(); if(!draft.trim())return; setMessages([...messages,{who:"user",text:draft},{who:"ai",text:"This is a placeholder response. Later it will come from the Aura FastAPI AI-agent endpoint."}]); setDraft("");};
  return <><PageHeader title="AI Portfolio Assistant" subtitle="Ask questions about your portfolio risk." action={<button className="button secondary" onClick={()=>setMessages([])}><Trash2 size={16}/> Clear Chat</button>}/><article className="panel chat"><div className="messages">{messages.length===0?<div className="empty"><Sparkles/><h2>Start a new conversation</h2></div>:messages.map((m,i)=><div className={`message ${m.who}`} key={i}>{m.who==="ai"&&<span>AI</span>}<p>{m.text}</p></div>)}</div><div className="chips">{["Why is my risk high?","How can I diversify?","Explain max drawdown"].map(x=><button key={x} onClick={()=>setDraft(x)}>{x}</button>)}</div><form onSubmit={submit}><input value={draft} onChange={e=>setDraft(e.target.value)} placeholder="Ask about your portfolio..."/><button className="button primary"><Send size={18}/></button></form></article></>;
}

function Watchlist() { return <><PageHeader title="My Watchlist" subtitle="Track assets you are interested in." action={<button className="button primary"><Plus size={16}/> Add Asset</button>}/><article className="panel tablePanel"><table><thead><tr><th>Asset</th><th>Price</th><th>1D Change</th><th>1Y Change</th><th>Chart</th><th/></tr></thead><tbody>{watchlist.map((w,i)=><tr key={w[0]}><td><div className="asset"><span>{w[0][0]}</span><div><strong>{w[0]}</strong><small>{w[1]}</small></div></div></td><td><strong>{w[2]}</strong></td><td className={w[3].startsWith("+")?"positive":"negative"}>{w[3]}</td><td className="positive">{w[4]}</td><td><svg className="spark" viewBox="0 0 100 30"><polyline fill="none" stroke="#20b58e" strokeWidth="3" points={i%2?"0,20 18,12 33,16 50,9 65,12 82,5 100,7":"0,22 16,18 30,20 45,10 60,14 75,6 100,9"}/></svg></td><td><button className="icon"><MoreVertical size={16}/></button></td></tr>)}</tbody></table></article></> }

function Reports() { return <><PageHeader title="My Reports" subtitle="View and download generated reports." action={<button className="button primary"><Plus size={16}/> Generate New Report</button>}/><article className="panel tablePanel"><table><thead><tr><th>Report Name</th><th>Portfolio</th><th>Generated On</th><th>Type</th><th/></tr></thead><tbody>{reports.map(r=><tr key={r[0]}><td><strong>{r[0]}</strong></td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td><button className="icon"><Download size={16}/></button></td></tr>)}</tbody></table></article></> }

function Learn() { const lessons=[
  {Icon:BookOpen,title:"Modern Portfolio Theory",text:"Learn the foundation of portfolio construction."},
  {Icon:Gauge,title:"Risk Metrics Explained",text:"Understand volatility, Sharpe ratio, beta and drawdown."},
  {Icon:BriefcaseBusiness,title:"Asset Classes 101",text:"Understand stocks, bonds, cash and alternatives."},
  {Icon:LineIcon,title:"Market Cycles",text:"Learn what expansions, slowdowns and recessions mean."},
  {Icon:BarChart3,title:"Backtesting Basics",text:"Learn how historical periods can support education."},
  {Icon:Bot,title:"Explainable AI",text:"Understand how Aura explains calculated results."}
]; return <><PageHeader title="Learn" subtitle="Improve your financial knowledge."/><section className="lessonGrid">{lessons.map(({Icon,title,text})=><article className="lesson" key={title}><span><Icon size={24}/></span><h2>{title}</h2><p>{text}</p><button className="button secondary">Start Learning</button></article>)}</section></> }

function SettingsPage() { const [theme,setTheme]=useState("Light"); return <><PageHeader title="Settings" subtitle="Manage your account and preferences."/><article className="panel settingsPanel"><div className="tabs">{["Profile","Preferences","Notifications","Security"].map((x,i)=><button className={i===1?"active":""} key={x}>{x}</button>)}</div><div className="settingsGrid"><label>Display Currency<select><option>USD · US Dollar</option><option>THB · Thai Baht</option></select></label><label>Theme<div className="segment">{["Light","Dark"].map(x=><button className={theme===x?"active":""} onClick={()=>setTheme(x)} key={x}>{x}</button>)}</div></label><label>Time Zone<select><option>GMT+07:00 Bangkok</option><option>GMT+06:30 Yangon</option></select></label></div><footer><button className="button primary">Save Changes</button></footer></article></> }

function Login() { const nav=useNavigate(); return <div className="auth"><section className="authCard"><Brand/><h1>Welcome Back!</h1><p>Log in to your account.</p><form onSubmit={e=>{e.preventDefault();nav("/dashboard")}}><label>Email<input type="email" required placeholder="Enter your email"/></label><label>Password<input type="password" required placeholder="Enter your password"/></label><div className="authLine"><label><input type="checkbox"/> Remember me</label><a>Forgot password?</a></div><button className="button primary">Log In</button></form><div className="divider">or continue with</div><div className="social"><button>Google</button><button><GitBranch size={15}/> GitHub</button><button>Microsoft</button></div><small>Do not have an account? <Link to="/signup">Sign up</Link></small></section></div> }

function Signup() { const nav=useNavigate(); return <div className="auth signup"><section className="brandPanel"><Brand/><div className="largeA">A</div><h2>Understand risk. Build confidence.</h2></section><section className="authCard"><h1>Create Account</h1><p>Join Aura today.</p><form onSubmit={e=>{e.preventDefault();nav("/dashboard")}}><div className="twoCols"><label>Full Name<input required placeholder="Enter your full name"/></label><label>Email<input type="email" required placeholder="Enter your email"/></label><label>Password<input type="password" required placeholder="Create a password"/></label><label>Confirm Password<input type="password" required placeholder="Confirm password"/></label></div><label className="terms"><input type="checkbox" required/> I agree to the Terms of Service and Privacy Policy.</label><button className="button primary">Create Account</button></form><div className="divider">or continue with</div><div className="social"><button>Google</button><button><GitBranch size={15}/> GitHub</button><button>Microsoft</button></div><small>Already have an account? <Link to="/login">Log in</Link></small></section></div> }

function NotFound() { return <div className="notFound"><header><Brand/></header><main><div><strong>404</strong><h1>Page Not Found</h1><p>The page you are looking for does not exist or has been moved.</p><ButtonLink to="/dashboard">Go to Dashboard</ButtonLink></div><div className="astronaut"><span/><i/></div></main></div> }

export default function App() {
  return <Routes><Route path="/" element={<Landing/>}/><Route path="/login" element={<Login/>}/><Route path="/signup" element={<Signup/>}/><Route element={<Shell/>}><Route path="/dashboard" element={<Dashboard/>}/><Route path="/portfolios" element={<Portfolios/>}/><Route path="/portfolios/new" element={<PortfolioEditor/>}/><Route path="/analysis" element={<Analysis/>}/><Route path="/simulator" element={<Simulator/>}/><Route path="/assistant" element={<Assistant/>}/><Route path="/watchlist" element={<Watchlist/>}/><Route path="/reports" element={<Reports/>}/><Route path="/learn" element={<Learn/>}/><Route path="/settings" element={<SettingsPage/>}/></Route><Route path="/home" element={<Navigate to="/dashboard" replace/>}/><Route path="*" element={<NotFound/>}/></Routes>;
}
