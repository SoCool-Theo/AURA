import { useEffect, useRef, useState } from 'react';
import { usePortfolioPrivacy } from '../../privacy/PortfolioPrivacy';
import { explainPortfolio } from '../../api/agentApi';
import { listPortfolios } from '../../api/portfoliosApi';
import { go } from '../../app/routes';
import { AuraSelect } from '../../components/ui/AuraSelect';
import type { AuraSelectOption } from '../../components/ui/AuraSelect';
import { InlineErrorCard, ScreenErrorState } from '../../components/ui/ApiErrorState';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import type { AgentConversationMessage, AgentExplainResponse, AgentSourceReference } from '../../types/agent';
import type { PortfolioSummaryResponse } from '../../types/portfolio';
import styles from './AssistantPage.module.css';
import composerStyles from './AssistantComposer.module.css';
import { AnswerContent } from './components/AnswerContent';

function sourceLabel(source: AgentSourceReference): string {
  return source.type.charAt(0).toUpperCase() + source.type.slice(1);
}

type ChatMessage =
  | { id: number; role: 'user'; content: string }
  | { id: number; role: 'assistant'; content: string; response: AgentExplainResponse };

interface AssistantPageProps {
  portfolioId?: string;
  reportId?: string;
  simulationId?: string;
}

const CURRENT_STARTER_QUESTIONS = [
  'What is my portfolio?',
  'Explain my portfolio risk simply.',
  'What are the main risks?',
  'What are the advantages and disadvantages?',
] as const;

const PLANNED_STARTER_QUESTIONS = [
  'What does this planned portfolio look like?',
  'Explain this planned allocation simply.',
  'What are the main risks of this plan?',
  'Why is this planned allocation concentrated?',
] as const;

const REPORT_STARTER_QUESTIONS = [
  'Summarize this report simply.',
  'What are the main risk drivers?',
  'What does maximum drawdown mean here?',
  'What should I understand first from this report?',
] as const;

const SIMULATION_STARTER_QUESTIONS = [
  'Explain this simulation result simply.',
  'What caused the biggest change?',
  'What does this result say about my portfolio risk?',
  'Summarize the key takeaway from this simulation.',
] as const;

const FOLLOW_UP_QUESTIONS = [
  'Explain that more simply.',
  'Why does that matter?',
  'Which number should I pay attention to most?',
] as const;

export function AssistantPage({
  portfolioId: requestedPortfolioId,
  reportId,
  simulationId,
}: AssistantPageProps) {
  const { hideValues } = usePortfolioPrivacy();
  const [portfolios, setPortfolios] = useState<PortfolioSummaryResponse[]>([]);
  const [portfolioId, setPortfolioId] = useState('');
  const [savedContext, setSavedContext] = useState<{ type: 'report' | 'simulation'; id: string } | null>(
    reportId ? { type: 'report', id: reportId } : simulationId ? { type: 'simulation', id: simulationId } : null,
  );
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [composerHidden, setComposerHidden] = useState(false);
  const [loadingPortfolios, setLoadingPortfolios] = useState(true);
  const [sending, setSending] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const sendingRef = useRef(false);
  const nextMessageIdRef = useRef(1);
  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

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
          setMessages([]);
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

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, sending]);

  async function submit() {
    if (sendingRef.current || hideValues) return;
    const normalizedMessage = message.trim();
    if (!portfolioId) {
      setSubmitError('Choose a portfolio before asking Aura a question.');
      return;
    }
    if (!normalizedMessage) {
      setSubmitError('Enter a question for Aura.');
      return;
    }

    const history: AgentConversationMessage[] = messages.slice(-8).map(item => ({
      role: item.role,
      content: item.content,
    }));
    const userMessage: ChatMessage = {
      id: nextMessageIdRef.current++,
      role: 'user',
      content: normalizedMessage,
    };

    sendingRef.current = true;
    setSending(true);
    setSubmitError(null);
    setMessages(current => [...current, userMessage]);
    setMessage('');

    try {
      const result = await explainPortfolio({
        portfolio_id: portfolioId,
        message: normalizedMessage,
        history,
        ...(savedContext?.type === 'report' ? { report_id: savedContext.id } : {}),
        ...(savedContext?.type === 'simulation' ? { simulation_id: savedContext.id } : {}),
      });
      const assistantMessage: ChatMessage = {
        id: nextMessageIdRef.current++,
        role: 'assistant',
        content: result.answer,
        response: result,
      };
      setMessages(current => [...current, assistantMessage]);
    } catch (requestError) {
      setMessages(current => current.filter(item => item.id !== userMessage.id));
      setMessage(normalizedMessage);
      setSubmitError(requestError);
    } finally {
      sendingRef.current = false;
      setSending(false);
    }
  }

  function startNewChat() {
    if (sending) return;
    setMessages([]);
    setMessage('');
    setSubmitError(null);
  }

  function chooseExampleQuestion(question: string) {
    if (sending || !portfolioId) return;
    setMessage(question);
    setSubmitError(null);
    window.requestAnimationFrame(() => textareaRef.current?.focus());
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
  const starterQuestions = savedContext?.type === 'report'
    ? REPORT_STARTER_QUESTIONS
    : savedContext?.type === 'simulation'
      ? SIMULATION_STARTER_QUESTIONS
      : portfolioMode === 'PLANNED'
        ? PLANNED_STARTER_QUESTIONS
        : CURRENT_STARTER_QUESTIONS;

  if (hideValues) return <div className={`page ${styles.page}`}><Card className={styles.stateCard}>
    <h1>AI chat hidden for privacy</h1>
    <p>Questions and replies can contain personal amounts. Turn off Hide portfolio values in Settings to view your chat or send a message.</p>
    <button type="button" className="primary-btn" onClick={() => go('settings')}>Open Settings</button>
  </Card></div>;

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
      <div><span>GROUNDED PORTFOLIO EXPLANATIONS</span><h1>Ask Aura</h1><p>Ask follow-up questions in the same conversation. Aura keeps a short in-session chat context while grounding every answer in backend-owned portfolio data.</p></div>
      <div className={styles.safetyNote}><Icon name="shield" size={18} /><span>Educational explanations only</span></div>
    </header>

    <Card className={styles.contextPanel}>
      <div className={styles.field}><span>Portfolio</span><AuraSelect ariaLabel="Select portfolio for Aura explanation" value={portfolioId} options={portfolioOptions} onChange={nextPortfolioId => { setPortfolioId(nextPortfolioId); setSavedContext(null); setMessages([]); setMessage(''); setSubmitError(null); }} disabled={loadingPortfolios || sending} /></div>
      {selectedPortfolio && <div className={[styles.contextCard, portfolioMode === 'PLANNED' ? styles.plannedContext : ''].join(' ')}><div><small>{savedContext ? 'IMMUTABLE SNAPSHOT' : 'LIVE PORTFOLIO'}</small><strong>{modeTitle}</strong></div><span>{contextDescription}</span></div>}
    </Card>

    {loadingPortfolios && <Card className={styles.stateCard}><h2>Loading portfolios</h2><p role="status">Retrieving your saved portfolios.</p></Card>}
    {!loadingPortfolios && !loadError && !portfolios.length && <Card className={styles.stateCard}><h2>No portfolios available</h2><p>Create a saved portfolio before asking Aura to explain its risk results.</p></Card>}

    {!loadingPortfolios && portfolios.length > 0 && <section className={styles.chatSection} aria-live="polite">
      {!messages.length && !sending && <Card className={styles.emptyChat}>
        <span><Icon name="spark" size={20} /></span>
        <div className={styles.emptyChatContent}>
          <h2>Start a conversation</h2>
          <p>Ask about your holdings, risk, historical performance, or a saved simulation. Choose an example below or write your own question.</p>
          <div className={styles.exampleQuestions} aria-label="Example questions">
            <small>TRY ASKING</small>
            <div className={styles.questionChips}>
              {starterQuestions.map(question => <button type="button" key={question} className={styles.questionChip} onClick={() => chooseExampleQuestion(question)}>{question}</button>)}
            </div>
          </div>
        </div>
      </Card>}

      {messages.map(item => item.role === 'user'
        ? <div className={styles.userRow} key={item.id}><div className={styles.userBubble}><small>YOU</small><p>{item.content}</p></div></div>
        : <div className={styles.assistantRow} key={item.id}>
          <div className={styles.assistantAvatar}><Icon name="spark" size={17} /></div>
          <Card className={styles.assistantBubble}>
            <small>AURA</small>
            <AnswerContent answer={item.content} />
            {(item.response.sources.length > 0 || item.response.limitations.length > 0) && <details className={styles.groundingDetails}>
              <summary>Grounding details</summary>
              {item.response.sources.length > 0 && <div><strong>Sources</strong><ul>{item.response.sources.map(source => <li key={`${item.id}-${source.type}-${source.id}`}>{sourceLabel(source)} · {source.id}</li>)}</ul></div>}
              {item.response.limitations.length > 0 && <div><strong>Limitations</strong><ul>{item.response.limitations.map(limitation => <li key={`${item.id}-${limitation}`}>{limitation}</li>)}</ul></div>}
            </details>}
          </Card>
        </div>)}

      {sending && <div className={styles.assistantRow}><div className={styles.assistantAvatar}><Icon name="spark" size={17} /></div><Card className={`${styles.assistantBubble} ${styles.typingBubble}`}><small>AURA</small><p role="status">Thinking about your portfolio context…</p></Card></div>}
      <div ref={conversationEndRef} />
    </section>}

    {Boolean(submitError) && <InlineErrorCard error={submitError} resourceName="Assistant context" fallbackMessage="Aura could not prepare this explanation." onRetry={() => void submit()} />}

    {!loadingPortfolios && portfolios.length > 0 && composerHidden && <div className={composerStyles.collapsedComposer}>
      <button
        type="button"
        className={composerStyles.showComposerButton}
        aria-label="Show message composer"
        onClick={() => setComposerHidden(false)}
      >
        <Icon name="chevron-up" size={22} />
      </button>
    </div>}

    {!loadingPortfolios && portfolios.length > 0 && !composerHidden && <Card className={styles.composerCard}>
      {messages.length > 0 && !sending && <div className={styles.followUpSuggestions}>
        <small>FOLLOW-UP IDEAS</small>
        <div className={styles.followUpChips}>{FOLLOW_UP_QUESTIONS.map(question => <button type="button" key={question} className={styles.followUpChip} onClick={() => chooseExampleQuestion(question)}>{question}</button>)}</div>
      </div>}
      <div className={styles.field}>
        <div className={composerStyles.questionHeader}>
          <label htmlFor="aura-question">Your question</label>
          <div className={composerStyles.questionHeaderActions}>
            <span className={composerStyles.characterCount}>{message.length}/4000</span>
            <button
              type="button"
              className={composerStyles.hideComposerButton}
              aria-label="Hide message composer"
              onClick={() => setComposerHidden(true)}
            >
              <Icon name="chevron-down" size={20} />
            </button>
          </div>
        </div>
        <textarea id="aura-question" ref={textareaRef} value={message} onChange={event => { setMessage(event.target.value); setSubmitError(null); }} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void submit(); } }} placeholder={portfolioMode === 'PLANNED' ? 'Ask about this proposed allocation…' : 'Ask about this portfolio…'} maxLength={4000} disabled={sending || !portfolioId} />
      </div>
      <div className={styles.actionRow}>
        <div className={styles.composerHints}><small>Enter to send · Shift+Enter for a new line</small>{messages.length > 0 && <button type="button" className={styles.newChatButton} onClick={startNewChat} disabled={sending}>New chat</button>}</div>
        <button type="button" className="primary-btn" onClick={() => void submit()} disabled={sending || !portfolioId || !message.trim()}><Icon name="spark" size={17} /> {sending ? 'Asking Aura…' : 'Send'}</button>
      </div>
    </Card>}
  </div>;
}
