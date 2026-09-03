import { useEffect, useRef, useState } from 'react';
import { explainPortfolio } from '../../api/agentApi';
import { ApiError } from '../../api/apiClient';
import { listPortfolios } from '../../api/portfoliosApi';
import { AuraSelect } from '../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../components/ui/AuraSelect';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import type { AgentExplainResponse, AgentSourceReference } from '../../types/agent';
import type { PortfolioSummaryResponse } from '../../types/portfolio';
import styles from './AssistantPage.module.css';

function assistantErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Unable to contact Aura right now. Please try again.';
  switch (error.status) {
    case 401: return 'Your session has ended. Please sign in again.';
    case 404: return 'The requested portfolio, report, or simulation could not be found.';
    case 422: return 'Aura could not process that request. Check your selected portfolio and question.';
    case 502: return 'Aura received an invalid AI explanation. Please try again.';
    case 503: return 'Aura’s AI service is temporarily unavailable. Please try again later.';
    default: return error.kind === 'configuration'
      ? 'Aura is not configured to reach the API.'
      : 'Unable to contact Aura right now. Please try again.';
  }
}

function sourceLabel(source: AgentSourceReference): string {
  return source.type.charAt(0).toUpperCase() + source.type.slice(1);
}

export function AssistantPage() {
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [portfolioId, setPortfolioId] = useState('');
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState<AgentExplainResponse | null>(null);
  const [loadingPortfolios, setLoadingPortfolios] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const sendingRef = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoadingPortfolios(true);
    setError(null);
    void listPortfolios({ signal: controller.signal })
      .then(result => {
        if (controller.signal.aborted) return;
        setPortfolios(result.portfolios);
        setPortfolioId(current => current && result.portfolios.some(item => item.id === current)
          ? current : result.portfolios[0]?.id ?? '');
      })
      .catch(requestError => {
        if (!controller.signal.aborted) setError(assistantErrorMessage(requestError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingPortfolios(false);
      });
    return () => controller.abort();
  }, [reloadKey]);

  async function submit() {
    if (sendingRef.current) return;
    const normalizedMessage = message.trim();
    if (!portfolioId) {
      setError('Choose a portfolio before asking Aura a question.');
      return;
    }
    if (!normalizedMessage) {
      setError('Enter a question for Aura.');
      return;
    }
    sendingRef.current = true;
    setSending(true);
    setError(null);
    setResponse(null);
    try {
      setResponse(await explainPortfolio({ portfolio_id: portfolioId, message: normalizedMessage }));
    } catch (requestError) {
      setError(assistantErrorMessage(requestError));
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
    value: portfolio.id, label: portfolio.name, description: 'Saved portfolio', icon: 'wallet', tone: 'teal' as const,
  }))];

  return <div className={`page ${styles.page}`}>
    <header className={styles.header}>
      <div><span>GROUNDED PORTFOLIO EXPLANATIONS</span><h1>Ask Aura</h1><p>Aura explains your saved portfolio results. It does not calculate, predict, or recommend investments.</p></div>
      <div className={styles.safetyNote}><Icon name="shield" size={18} /><span>Educational explanations only</span></div>
    </header>
    <Card className={styles.askCard}>
      <div className={styles.field}><span>Portfolio</span><AuraSelect ariaLabel="Select portfolio for Aura explanation" value={portfolioId} options={portfolioOptions} onChange={nextPortfolioId => { setPortfolioId(nextPortfolioId); setResponse(null); setError(null); }} disabled={loadingPortfolios || sending} /></div>
      <label className={styles.field}><span>Your question</span><textarea value={message} onChange={event => { setMessage(event.target.value); setError(null); }} placeholder="For example: What are the main risk factors in this portfolio?" maxLength={4000} disabled={sending} /></label>
      <div className={styles.actionRow}><small>Only the selected portfolio and your question are sent for this explanation.</small><button type="button" className="primary-btn" onClick={() => void submit()} disabled={loadingPortfolios || sending || !portfolioId || !message.trim()}><Icon name="spark" size={17} /> {sending ? 'Asking Aura…' : 'Ask Aura'}</button></div>
    </Card>
    {error && <p className={styles.error} role="alert">{error}</p>}
    {loadingPortfolios && <Card className={styles.stateCard}><h2>Loading portfolios</h2><p role="status">Retrieving your saved portfolios.</p></Card>}
    {!loadingPortfolios && error && !portfolios.length && <Card className={styles.stateCard}><h2>Portfolios unavailable</h2><p>Aura needs an available portfolio before it can provide a grounded explanation.</p><button className="primary-btn" onClick={() => setReloadKey(key => key + 1)}>Try again</button></Card>}
    {!loadingPortfolios && !error && !portfolios.length && <Card className={styles.stateCard}><h2>No portfolios available</h2><p>Create a saved portfolio before asking Aura to explain its risk results.</p></Card>}
    {sending && <Card className={styles.stateCard}><h2>Aura is preparing an explanation</h2><p role="status">Aura is using backend-calculated portfolio context.</p></Card>}
    {response && !sending && <section className={styles.responseSection} aria-live="polite">
      <Card className={styles.answerCard}><div className={styles.answerHeading}><span><Icon name="spark" size={19} /></span><div><small>AURA’S EXPLANATION</small><h2>Grounded response</h2></div></div><p className={styles.answer}>{response.answer}</p></Card>
      <div className={styles.detailsGrid}>
        <Card className={styles.detailCard}><h2>Sources</h2>{response.sources.length ? <ul>{response.sources.map(source => <li key={`${source.type}-${source.id}`}><strong>{sourceLabel(source)}</strong><span>{source.id}</span></li>)}</ul> : <p>No source references were returned.</p>}</Card>
        <Card className={styles.detailCard}><h2>Limitations</h2>{response.limitations.length ? <ul>{response.limitations.map(limitation => <li key={limitation}>{limitation}</li>)}</ul> : <p>No additional limitations were returned.</p>}</Card>
      </div>
    </section>}
  </div>;
}
