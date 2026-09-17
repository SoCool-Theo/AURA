import { useEffect, useRef, useState } from 'react';
import { explainPortfolio } from '../../api/agentApi';
import { listPortfolios } from '../../api/portfoliosApi';
import { go } from '../../app/routes';
import { AuraSelect } from '../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../components/ui/AuraSelect';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ApiErrorState';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import type { AgentExplainResponse, AgentSourceReference } from '../../types/agent';
import type { PortfolioSummaryResponse } from '../../types/portfolio';
import styles from './AssistantPage.module.css';
import { AnswerContent } from './components/AnswerContent';

function sourceLabel(source: AgentSourceReference): string {
  return source.type.charAt(0).toUpperCase() + source.type.slice(1);
}

interface AssistantPageProps {
  portfolioId?: string;
  reportId?: string;
  simulationId?: string;
}

export function AssistantPage({
  portfolioId: requestedPortfolioId,
  reportId,
  simulationId,
}: AssistantPageProps) {
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [portfolioId, setPortfolioId] = useState('');
  const [savedContext, setSavedContext] = useState<{ type: 'report' | 'simulation'; id: string } | null>(
    reportId ? { type: 'report', id: reportId } : simulationId ? { type: 'simulation', id: simulationId } : null,
  );
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState<AgentExplainResponse | null>(null);
  const [loadingPortfolios, setLoadingPortfolios] = useState(true);
  const [sending, setSending] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const sendingRef = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoadingPortfolios(true);
    setLoadError(null);
    void listPortfolios({ signal: controller.signal })
      .then(result => {
        if (controller.signal.aborted) return;
        setPortfolios(result.portfolios);
        const requestedExists = requestedPortfolioId
          ? result.portfolios.some(item => item.id === requestedPortfolioId)
          : false;
        if (requestedPortfolioId && !requestedExists) {
          setPortfolioId('');
          setSavedContext(null);
          setLoadError('Portfolio not found.');
          return;
        }
        setPortfolioId(current => requestedExists
          ? requestedPortfolioId ?? ''
          : current && result.portfolios.some(item => item.id === current)
            ? current
            : result.portfolios[0]?.id ?? '');
        setSavedContext(requestedExists
          ? reportId
            ? { type: 'report', id: reportId }
            : simulationId
              ? { type: 'simulation', id: simulationId }
              : null
          : null);
      })
      .catch(requestError => {
        if (!controller.signal.aborted) setLoadError(requestError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingPortfolios(false);
      });
    return () => controller.abort();
  }, [reloadKey, reportId, requestedPortfolioId, simulationId]);

  async function submit() {
    if (sendingRef.current) return;
    const normalizedMessage = message.trim();
    if (!portfolioId) {
      setSubmitError('Choose a portfolio before asking Aura a question.');
      return;
    }
    if (!normalizedMessage) {
      setSubmitError('Enter a question for Aura.');
      return;
    }
    sendingRef.current = true;
    setSending(true);
    setSubmitError(null);
    setResponse(null);
    try {
      setResponse(await explainPortfolio({
        portfolio_id: portfolioId,
        message: normalizedMessage,
        ...(savedContext?.type === 'report' ? { report_id: savedContext.id } : {}),
        ...(savedContext?.type === 'simulation' ? { simulation_id: savedContext.id } : {}),
      }));
    } catch (requestError) {
      setSubmitError(requestError);
    } finally {
      sendingRef.current = false;
      setSending(false);
    }
  }

  const portfolioOptions: AuraSelectOption<string>[] = [{
    value: '',
    label: loadingPortfolios ? 'Loading portfolios…' : portfolios.length ? 'Select a portfolio' : 'No portfolios available',
    description: 'Choose one of your saved portfolios', icon: 'wallet', tone: 'neutral', disabled: true,
  }, ...portfolios.map(portfolio => ({
    value: portfolio.id,
    label: portfolio.name,
    description: portfolio.portfolio_type === 'PLANNED'
      ? 'Planned allocation'
      : portfolio.portfolio_type === 'LEGACY'
        ? 'Legacy allocation'
        : 'Current holdings',
    icon: 'wallet',
    tone: 'teal' as const,
  }))];

  const selectedPortfolio = portfolios.find(portfolio => portfolio.id === portfolioId);
  const portfolioMode = selectedPortfolio?.portfolio_type ?? null;
  const modeTitle = portfolioMode === 'PLANNED'
    ? 'Planned portfolio context'
    : portfolioMode === 'LEGACY'
      ? 'Legacy allocation context'
      : 'Current portfolio context';
  const contextDescription = savedContext
    ? `Using this saved ${savedContext.type} snapshot. Later portfolio or market changes will not alter its context.`
    : portfolioMode === 'PLANNED'
      ? 'Aura will explain your proposed allocation as hypothetical—not as assets you already own.'
      : portfolioMode === 'LEGACY'
        ? 'Aura will explain the portfolio’s saved compatibility allocation.'
        : 'Aura will explain the current allocation derived from your saved holdings.';

  if (!loadingPortfolios && loadError) {
    return <div className={`page ${styles.page}`}><ScreenErrorState
      error={loadError}
      resourceName="Portfolio list"
      fallbackMessage="Aura could not load the portfolios available to the Assistant."
      onRetry={() => setReloadKey(key => key + 1)}
      onBack={() => go('dashboard')}
      backTitle="Back to Dashboard"
    /></div>;
  }

  return <div className={`page ${styles.page}`}>
    <header className={styles.header}>
      <div><span>GROUNDED PORTFOLIO EXPLANATIONS</span><h1>Ask Aura</h1><p>Aura explains your saved portfolio results. It does not calculate, predict, or recommend investments.</p></div>
      <div className={styles.safetyNote}><Icon name="shield" size={18} /><span>Educational explanations only</span></div>
    </header>
    <Card className={styles.askCard}>
      <div className={styles.field}><span>Portfolio</span><AuraSelect ariaLabel="Select portfolio for Aura explanation" value={portfolioId} options={portfolioOptions} onChange={nextPortfolioId => { setPortfolioId(nextPortfolioId); setSavedContext(null); setResponse(null); setSubmitError(null); }} disabled={loadingPortfolios || sending} /></div>
      {selectedPortfolio && <div className={[styles.contextCard, portfolioMode === 'PLANNED' ? styles.plannedContext : ''].join(' ')}><div><small>{savedContext ? 'IMMUTABLE SNAPSHOT' : 'LIVE PORTFOLIO'}</small><strong>{modeTitle}</strong></div><span>{contextDescription}</span></div>}
      <label className={styles.field}><span>Your question</span><textarea value={message} onChange={event => { setMessage(event.target.value); setSubmitError(null); }} placeholder={portfolioMode === 'PLANNED' ? 'For example: What are the main risks in this proposed allocation?' : 'For example: What are the main risk factors in this portfolio?'} maxLength={4000} disabled={sending} /></label>
      <div className={styles.actionRow}><small>{savedContext ? `Aura will use the selected saved ${savedContext.type} as context.` : 'Aura will use the selected portfolio as context.'}</small><button type="button" className="primary-btn" onClick={() => void submit()} disabled={loadingPortfolios || sending || !portfolioId || !message.trim()}><Icon name="spark" size={17} /> {sending ? 'Asking Aura…' : 'Ask Aura'}</button></div>
    </Card>
    {Boolean(submitError) && <InlineErrorCard error={submitError} resourceName="Assistant context" fallbackMessage="Aura could not prepare this explanation." onRetry={() => void submit()} />}
    {loadingPortfolios && <Card className={styles.stateCard}><h2>Loading portfolios</h2><p role="status">Retrieving your saved portfolios.</p></Card>}
    {!loadingPortfolios && !loadError && !portfolios.length && <Card className={styles.stateCard}><h2>No portfolios available</h2><p>Create a saved portfolio before asking Aura to explain its risk results.</p></Card>}
    {sending && <Card className={styles.stateCard}><h2>Aura is preparing an explanation</h2><p role="status">Aura is using your selected saved context.</p></Card>}
    {response && !sending && <section className={styles.responseSection} aria-live="polite">
      <Card className={styles.answerCard}><div className={styles.answerHeading}><span><Icon name="spark" size={19} /></span><div><small>AURA’S EXPLANATION</small><h2>Grounded response</h2></div></div><AnswerContent answer={response.answer} /></Card>
      <div className={styles.detailsGrid}>
        <Card className={styles.detailCard}><h2>Sources</h2>{response.sources.length ? <ul>{response.sources.map(source => <li key={`${source.type}-${source.id}`}><strong>{sourceLabel(source)}</strong><span>{source.id}</span></li>)}</ul> : <p>No source references were returned.</p>}</Card>
        <Card className={styles.detailCard}><h2>Limitations</h2>{response.limitations.length ? <ul>{response.limitations.map(limitation => <li key={limitation}>{limitation}</li>)}</ul> : <p>No additional limitations were returned.</p>}</Card>
      </div>
    </section>}
  </div>;
}
