import { useEffect, useId, useRef, useState } from 'react';
import { Icon } from '../../components/ui/Icon';
import styles from './WelcomePage.module.css';

const SECTIONS = [
  ['features', 'Features'], ['how-it-works', 'How it works'],
  ['learn', 'Learn'], ['about', 'About'],
] as const;

const STEPS = [
  ['portfolios', 'Build your portfolio', 'Record your current shares or explore a planned allocation.'],
  ['analytics', 'See the whole picture', 'Understand historical returns, concentration, drawdown, and risk drivers.'],
  ['simulations', 'Explore a what-if', 'Compare allocations and see how they behave through a past market event.'],
  ['assistant', 'Make sense of it', 'Ask Aura to explain your results in everyday language.'],
] as const;

const LESSONS = [
  ['pulse', 'Volatility', 'How much did it move?', 'A portfolio with larger ups and downs has higher historical volatility, even if its average return is similar to a steadier portfolio.'],
  ['drawdown', 'Drawdown', 'How far did it fall?', 'A fall from a $10,000 peak to $8,000 is a 20% drawdown. It takes a 25% gain from $8,000 to recover to that peak.'],
  ['diversification', 'Diversification', 'What moves together?', 'Five technology stocks can still share the same risks. Spreading weights matters, and so does how the assets move together.'],
  ['stats-chart', 'Sharpe ratio', 'How much return for the risk?', 'The Sharpe ratio compares excess return with volatility. Read it alongside other metrics to understand the historical experience.'],
] as const;

function Brand({ onBackToTop }: { onBackToTop: () => void }) {
  return <a href="#/welcome" className={styles.brand} aria-label="Aura welcome page" onClick={event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onBackToTop();
  }}><span aria-hidden="true" />AURA</a>;
}

function StartLink({ label = 'Get started' }: { label?: string }) {
  return <a href="#/signup" className={styles.primaryLink}>{label}<Icon name="chevron-right" size={18} /></a>;
}

// These paths are illustrations for the public product tour, never portfolio results.
function PreviewChart({ comparison = false, line = 'all' }: { comparison?: boolean; line?: string }) {
  const gradientId = useId();
  return <svg className={styles.chart} viewBox="0 0 600 220" role="img" aria-label={comparison ? `Illustrative comparison chart showing ${line === 'all' ? 'both lines' : line}. These are sample paths, not calculated results.` : 'Illustrative portfolio chart. These are sample observations, not calculated results.'}>
    <defs><linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#31D6CF" stopOpacity=".22" /><stop offset="100%" stopColor="#31D6CF" stopOpacity="0" /></linearGradient></defs>
    {[40, 100, 160].map((y, index) => <g key={y}><line x1="42" x2="575" y1={y} y2={y} stroke="#233149" strokeDasharray={index === 1 ? '4 5' : undefined} /><text x="5" y={y + 4} fill="#A7B2C7" fontSize="11">{120 - index * 20}</text></g>)}
    {!comparison && <path d="M42 100 80 90 118 104 155 72 192 86 229 61 266 85 304 60 341 68 378 42 415 60 452 28 489 45 526 31 575 18V180H42Z" fill={`url(#${gradientId})`} />}
    {(!comparison || line !== 'modified') && <polyline points={comparison ? '42,100 80,91 118,110 155,136 192,126 229,153 266,145 304,126 341,144 378,128 415,107 452,120 489,106 526,95 575,82' : '42,100 80,90 118,104 155,72 192,86 229,61 266,85 304,60 341,68 378,42 415,60 452,28 489,45 526,31 575,18'} fill="none" stroke={comparison ? '#4C8DFF' : '#76E5E0'} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />}
    {comparison && line !== 'original' && <polyline points="42,100 80,94 118,101 155,111 192,99 229,117 266,106 304,87 341,98 378,79 415,66 452,71 489,51 526,55 575,37" fill="none" stroke="#76E5E0" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />}
    <text x="42" y="205" fill="#A7B2C7" fontSize="11">Start of sample period</text><text x="575" y="205" textAnchor="end" fill="#A7B2C7" fontSize="11">End of sample period</text>
  </svg>;
}

function DashboardPreview({ compact = false }: { compact?: boolean }) {
  const [mode, setMode] = useState<'current' | 'planned'>('current');
  return <div className={`${styles.dashboardPreview} ${compact ? styles.compactPreview : ''}`}>
    <div className={styles.previewBar}><span className={styles.previewBrand}><span aria-hidden="true" /> AURA</span><span>Portfolio overview</span><span className={styles.sampleBadge}>Sample data</span></div>
    <div className={styles.previewBody}>
      <div className={styles.previewHeading}><div><small>YOUR PORTFOLIO, EXPLAINED</small><h3>My Sample Portfolio</h3></div><Icon name="portfolios" size={28} /></div>
      {!compact && <div className={styles.modeTabs} role="group" aria-label="Sample portfolio type">{(['current', 'planned'] as const).map(item => <button key={item} aria-pressed={mode === item} onClick={() => setMode(item)}>{item === 'current' ? 'Current holdings' : 'Planned allocation'}</button>)}</div>}
      <div className={styles.previewMetrics}>
        <div><Icon name="wallet" size={18} /><small>{mode === 'current' ? 'Current value' : 'Proposed amount'}</small><strong>$10,000</strong><span>{mode === 'current' ? 'Sample owned holdings' : 'Hypothetical allocation'}</span></div>
        <div><Icon name="speedometer" size={18} /><small>Risk score</small><strong className={styles.amber}>42.0<em>/100</em></strong><span className={styles.amber}>Moderate · sample score</span></div>
        <div><Icon name="drawdown" size={18} /><small>Max drawdown</small><strong className={styles.red}>−18.5%</strong><span>Sample historical decline</span></div>
      </div>
      <div className={styles.previewChart}><div><h4>Historical portfolio journey</h4><span>Illustrative · normalized to 100</span></div><PreviewChart /></div>
      {!compact && <div className={styles.previewBottom}><div><h4>Top risk drivers</h4>{[['AAPL', '52%'], ['MSFT', '38%'], ['BND', '10%']].map(([symbol, contribution]) => <div className={styles.driver} key={symbol}><b>{symbol}</b><span>Sample contribution</span><strong>{contribution}</strong></div>)}</div><div className={styles.previewInsight}><Icon name="assistant" size={22} /><h4>A clearer view of your risk.</h4><p>See which holdings drive your portfolio’s fluctuations, then ask Aura to explain why.</p></div></div>}
    </div>
  </div>;
}

export function WelcomePage() {
  const pageRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedLine, setSelectedLine] = useState('all');

  useEffect(() => {
    window.scrollTo(0, 0);
    const root = pageRef.current;
    if (!root || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add(styles.visible);
          observer.unobserve(entry.target);
        }
      }
    }, { threshold: .08 });
    root.classList.add(styles.revealEnabled);
    root.querySelectorAll('[data-reveal]').forEach(element => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  function scrollToSection(id: string) {
    setMenuOpen(false);
    const section = document.getElementById(`welcome-${id}`);
    section?.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    section?.focus({ preventScroll: true });
  }

  function scrollToTop() {
    setMenuOpen(false);
    window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    document.getElementById('welcome-main')?.focus({ preventScroll: true });
  }

  return <div ref={pageRef} className={styles.page}>
    <a className={styles.skipLink} href="#/welcome" onClick={event => { event.preventDefault(); scrollToSection('main'); }}>Skip to content</a>
    <header className={styles.header} onKeyDown={event => {
      if (event.key === 'Escape' && menuOpen) {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    }}>
      <div className={styles.headerInner}>
        <Brand onBackToTop={scrollToTop} />
        <nav id="welcome-navigation" className={`${styles.navigation} ${menuOpen ? styles.navigationOpen : ''}`} aria-label="Welcome navigation">{SECTIONS.map(([id, label]) => <button key={id} onClick={() => scrollToSection(id)}>{label}</button>)}</nav>
        <div className={styles.headerActions}><a href="#/login" className={styles.signIn}>Sign in</a><StartLink /><button ref={menuButtonRef} className={styles.menuButton} aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="welcome-navigation" onClick={() => setMenuOpen(value => !value)}><Icon name={menuOpen ? 'chevron-up' : 'chevron-down'} size={22} /></button></div>
      </div>
    </header>

    <main id="welcome-main" tabIndex={-1}>
      <section className={styles.hero} aria-labelledby="welcome-title">
        <div className={styles.heroGlow} aria-hidden="true" />
        <div className={styles.heroCopy}>
          <span className={styles.eyebrow}><span className={styles.statusDot} /> PORTFOLIO RISK, MADE CLEAR</span>
          <h1 id="welcome-title">Understand the risk<br />behind <span>your portfolio.</span></h1>
          <p>See the bigger picture. Explore historical risk, test what-if scenarios, and turn complex numbers into understanding.</p>
          <div className={styles.heroActions}><StartLink label="Explore with Aura" /><button className={styles.secondaryLink} onClick={() => scrollToSection('how-it-works')}>See how it works<Icon name="chevron-down" size={18} /></button></div>
          <div className={styles.heroNote}><Icon name="shield" size={16} /> Built for learning. Designed for clarity.</div>
        </div>
        <div className={styles.heroProduct}>
          <div className={styles.deviceFrame}><DashboardPreview /></div>
          <div className={styles.floatingCard}><span><Icon name="assistant" size={22} /></span><div><strong>Less guesswork. More understanding.</strong><p>Meet your portfolio’s AI explainer.</p></div></div>
        </div>
        <p className={styles.sampleCaption}>Product preview with illustrative sample data. Your results depend on your holdings and analysis period.</p>
      </section>

      <div className={styles.capabilityStrip}>{[['analytics', 'Historical analytics'], ['compare', 'What-if simulations'], ['assistant', 'AI explanations'], ['reports', 'Saved reports']].map(([icon, label]) => <span key={label}><Icon name={icon} size={20} />{label}</span>)}</div>

      <section className={`${styles.section} ${styles.problemSection}`} data-reveal aria-labelledby="problem-title">
        <div className={styles.sectionCopy}><span className={styles.eyebrow}>LOOK BENEATH THE RETURNS</span><h2 id="problem-title">More assets.<br />Not always <span>less risk.</span></h2><p>A portfolio can look balanced and still move as one. Aura helps you see concentration, shared market movements, and the holdings that contribute most to risk.</p><p className={styles.quietCopy}>The number of assets is just the beginning. Understanding how they work together is what matters.</p></div>
        <div className={styles.allocationStory}>
          <div className={styles.allocationRing} role="img" aria-label="Illustrative allocation: AAPL 40 percent, MSFT 35 percent, BND 25 percent"><div><small>SAMPLE PORTFOLIO</small><strong>3 assets</strong><span>One connected picture</span></div></div>
          <div className={styles.allocationLegend}><span><i />AAPL <b>40%</b></span><span><i />MSFT <b>35%</b></span><span><i />BND <b>25%</b></span></div>
          <div className={styles.storyNote}><Icon name="diversification" size={22} /><p>Different names can share similar risks.<br /><strong>Explore weights and correlations together.</strong></p></div>
        </div>
      </section>

      <section id="welcome-how-it-works" tabIndex={-1} className={`${styles.section} ${styles.workflowSection}`} data-reveal aria-labelledby="workflow-title">
        <div className={styles.centerHeading}><span className={styles.eyebrow}>FROM HOLDINGS TO UNDERSTANDING</span><h2 id="workflow-title">Your portfolio.<br /><span>A clearer perspective.</span></h2><p>Four steps to explore the story behind your numbers.</p></div>
        <div className={styles.steps}>{STEPS.map(([icon, title, description], index) => <article key={title}><span className={styles.stepNumber}>0{index + 1}</span><Icon name={icon} size={28} /><h3>{title}</h3><p>{description}</p></article>)}</div>
      </section>

      <section id="welcome-features" tabIndex={-1} className={`${styles.section} ${styles.featuresSection}`} data-reveal aria-labelledby="features-title">
        <div className={styles.sectionCopy}><span className={styles.eyebrow}>THE WHOLE PICTURE, IN ONE PLACE</span><h2 id="features-title">Numbers that<br /><span>mean something.</span></h2><p>Start with an overview. Look closer at the details. Connect each result to the historical experience of your portfolio.</p><div className={styles.featureRows}>{[['speedometer', 'Risk, explained', 'A risk score with reasons and detailed metrics behind it.'], ['drawdown', 'The downside experience', 'See historical fluctuations and the largest peak-to-trough decline.'], ['assets', 'Every holding has a story', 'Explore asset risk, allocation, and contributions to portfolio volatility.'], ['reports', 'A record you can revisit', 'Save analysis snapshots and return to the same results later.']].map(([icon, title, text]) => <div key={title}><span><Icon name={icon} size={22} /></span><div><h3>{title}</h3><p>{text}</p></div></div>)}</div></div>
        <div className={styles.analysisVisual}><div className={styles.visualHeading}><Icon name="analytics" size={21} /><strong>Inside your portfolio analysis</strong><span className={styles.sampleBadge}>Sample</span></div><div className={styles.riskVisual}><div className={styles.gauge}><strong>42.0<small>Moderate risk · sample</small></strong></div><p>One score. A deeper explanation.</p></div><div className={styles.analysisTiles}>{[['Volatility', 'How widely returns fluctuated', 'pulse'], ['Drawdown', 'The largest historical decline', 'drawdown'], ['Diversification', 'How exposure is distributed', 'diversification'], ['Risk drivers', 'Which holdings contributed most', 'trend']].map(([label, text, icon]) => <div key={label}><Icon name={icon} size={21} /><h3>{label}</h3><p>{text}</p></div>)}</div></div>
      </section>

      <section className={styles.simulationBand}>
        <div className={styles.section} data-reveal>
          <div className={styles.centerHeading}><span className={styles.eyebrow}>EXPLORE THE WHAT-IFS</span><h2>What if your portfolio<br /><span>had taken a different path?</span></h2><p>Replay a past event. Adjust an allocation. Combine both.<br />Compare the historical experience before making sense of the difference.</p></div>
          <div className={styles.simulationPreview}>
            <div className={styles.simulationHeading}><div><span className={styles.eyebrow}>HISTORICAL SCENARIO PREVIEW</span><h3>Two allocations. One historical window.</h3></div><span className={styles.sampleBadge}>Illustrative paths</span></div>
            <div className={styles.lineControls} role="group" aria-label="Choose sample comparison lines">{[['all', 'Both lines'], ['original', 'Original allocation'], ['modified', 'Modified allocation']].map(([value, label]) => <button key={value} aria-pressed={selectedLine === value} onClick={() => setSelectedLine(value)}>{value !== 'all' && <i className={value === 'original' ? styles.originalDot : styles.modifiedDot} />}{label}</button>)}</div>
            <PreviewChart comparison line={selectedLine} />
            <p className={styles.chartNote}>Normalized illustration · both paths start at 100. Changing a line changes this preview only.</p>
          </div>
          <div className={styles.simulationModes}>{[['calendar', 'Historical scenario', 'Explore an unchanged allocation during a past market event.'], ['compare', 'Allocation change', 'Compare an original and modified allocation over the same period.'], ['simulations', 'Combined simulation', 'Explore a modified allocation within a historical scenario.']].map(([icon, title, text]) => <div key={title}><Icon name={icon} size={23} /><h3>{title}</h3><p>{text}</p></div>)}</div>
          <p className={styles.sampleCaption}>Historical simulations explain past behavior. They do not predict the next market event.</p>
        </div>
      </section>

      <section className={`${styles.section} ${styles.assistantSection}`} data-reveal aria-labelledby="assistant-title">
        <div className={styles.conversation}><div className={styles.visualHeading}><Icon name="assistant" size={22} /><strong>Ask Aura</strong><span className={styles.sampleBadge}>Example conversation</span></div><div className={styles.question}>Why does concentration matter?</div><div className={styles.answer}><span className={styles.answerIcon}><Icon name="assistant" size={21} /></span><div><strong>A smaller number of holdings can have a bigger influence.</strong><p>In this example, two stocks account for most of the portfolio. If they move in the same direction, their changes can strongly affect the whole portfolio.</p><p>You can look at the asset weights and risk contributions together to understand that exposure.</p><span><Icon name="reports" size={14} /> Illustrative explanation</span></div></div><div className={styles.followUp}>Your question is where understanding begins.<Icon name="spark" size={18} /></div></div>
        <div className={styles.sectionCopy}><span className={styles.eyebrow}>MEET YOUR AI EXPLAINER</span><h2 id="assistant-title">Ask why.<br /><span>Understand more.</span></h2><p>A risk score is a starting point. Ask follow-up questions about your portfolio, saved analysis, or simulation and get explanations grounded in Aura’s results.</p><div className={styles.assistantBenefits}><span><Icon name="reports" size={18} /> Connected to your analysis</span><span><Icon name="assistant" size={18} /> Plain-language explanations</span><span><Icon name="school" size={18} /> Built around learning</span></div><StartLink label="Start exploring" /></div>
      </section>

      <section id="welcome-learn" tabIndex={-1} className={`${styles.section} ${styles.learnSection}`} data-reveal aria-labelledby="learn-title">
        <div className={styles.learnHeading}><div><span className={styles.eyebrow}>BUILD YOUR FINANCIAL VOCABULARY</span><h2 id="learn-title">Little lessons.<br /><span>Lasting understanding.</span></h2></div><p>Get comfortable with the concepts behind your results. Open a topic for a quick introduction, then explore Aura Learn after signing in.</p></div>
        <div className={styles.lessonCards}>{LESSONS.map(([icon, title, subtitle, explanation]) => <details key={title}><summary><Icon name={icon} size={26} /><span>{title}</span><small>{subtitle}</small><span className={styles.lessonAction}>Quick introduction<Icon name="chevron-down" size={17} /></span></summary><p>{explanation}</p></details>)}</div>
        <div className={styles.learnAction}><StartLink label="Explore Aura Learn" /><span>Lessons, simple examples, and related videos.</span></div>
      </section>

      <section className={`${styles.section} ${styles.platformSection}`} data-reveal aria-labelledby="platform-title">
        <div className={styles.centerHeading}><span className={styles.eyebrow}>AURA ON WEB AND MOBILE</span><h2 id="platform-title">The bigger picture.<br /><span>Wherever you are.</span></h2><p>Explore in depth on your desktop. Review your portfolio on mobile.<br />Your account brings your saved portfolios and results together.</p></div>
        <div className={styles.platformDevices}><div className={styles.laptop}><DashboardPreview compact /><span className={styles.laptopBase} aria-hidden="true" /></div><div className={styles.phone}><span className={styles.phoneNotch} aria-hidden="true" /><div className={styles.phoneHeading}><span className={styles.phoneMark} /> AURA <small>Sample</small></div><small className={styles.phoneOverline}>YOUR PORTFOLIO</small><h3>A clearer view.</h3><div className={styles.phoneValue}><Icon name="wallet" size={19} /><span>Current value</span><strong>$10,000</strong><small>Illustrative portfolio</small></div><div className={styles.phoneRisk}><Icon name="speedometer" size={20} /><span>Risk score</span><strong>42.0</strong><small>Moderate · sample</small></div><PreviewChart /><div className={styles.phoneTabs}><Icon name="dashboard" /><Icon name="portfolios" /><Icon name="simulations" /><Icon name="assistant" /></div></div></div>
      </section>

      <section id="welcome-about" tabIndex={-1} className={`${styles.section} ${styles.aboutSection}`} data-reveal aria-labelledby="about-title">
        <div className={styles.centerHeading}><span className={styles.eyebrow}>UNDERSTANDING COMES FIRST</span><h2 id="about-title">Built to explain.<br /><span>Designed to help you learn.</span></h2><p>Aura is a portfolio risk education project. It helps you understand the historical risks in your holdings and explore alternatives thoughtfully.</p></div>
        <div className={styles.principles}>{[['analytics', 'Calculations you can trace', 'Risk metrics come from Aura’s analytics. The Assistant helps explain those results.'], ['reports', 'A moment, preserved', 'Saved reports and simulations keep a snapshot of the results from when they were created.'], ['school', 'Education at the center', 'Explore risk concepts and historical scenarios. Aura does not place trades or provide buy or sell recommendations.']].map(([icon, title, text]) => <article key={title}><Icon name={icon} size={26} /><h3>{title}</h3><p>{text}</p></article>)}</div>
        <div className={styles.faq}><h3>A few things worth knowing.</h3>{[['Can I use a portfolio I am planning?', 'Yes. Aura supports current holdings and planned allocations. A planned portfolio uses proposed amounts so you can explore a hypothetical allocation before owning those assets.'], ['Does a historical simulation predict my future returns?', 'No. Historical scenarios describe how an allocation behaved during a selected past period. Future market conditions and results can be different.'], ['Do I need an account?', 'You can explore this page without signing in. Create an account to save portfolios, run analysis and simulations, and use the AI Assistant.'], ['What information do I enter?', 'For current holdings, enter supported asset symbols and share quantities. For a planned allocation, enter proposed amounts. Aura does not ask you to connect a brokerage account.']].map(([question, answer]) => <details key={question}><summary>{question}<Icon name="chevron-down" size={18} /></summary><p>{answer}</p></details>)}</div>
      </section>

      <section className={styles.finalCta} data-reveal><span className={styles.ctaMark} aria-hidden="true" /><span className={styles.eyebrow}>YOUR NEXT STEP STARTS WITH CLARITY</span><h2>Get to know<br /><span>your portfolio.</span></h2><p>Discover the story behind your numbers with Aura.</p><StartLink label="Create your Aura account" /><a href="#/login" className={styles.finalSignIn}>Already have an account? <span>Sign in →</span></a></section>
    </main>

    <footer className={styles.footer}><div className={styles.footerTop}><div><Brand onBackToTop={scrollToTop} /><p>Portfolio risk education.<br />A clearer perspective on your holdings.</p></div><nav aria-label="Footer navigation">{SECTIONS.map(([id, label]) => <button key={id} onClick={() => scrollToSection(id)}>{label}</button>)}<a href="#/login">Sign in</a></nav></div><div className={styles.footerBottom}><span>Aura · Portfolio risk education</span><p>Educational purposes only. Historical performance does not guarantee future results. Not financial or investment advice.</p></div></footer>
  </div>;
}
