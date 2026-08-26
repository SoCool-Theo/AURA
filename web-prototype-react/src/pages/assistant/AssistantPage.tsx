import { useState } from 'react';
import type { Portfolio } from '../../types/portfolio';
import type { AssistantMessage } from '../../types/assistant';
import { ChatWorkspace } from './components/ChatWorkspace';
import { ConversationList } from './components/ConversationList';
import { PortfolioContext } from './components/PortfolioContext';

interface AssistantPageProps {
  portfolio: Portfolio;
}

const PROMPTS = [
  'Why is my portfolio risk score 72?',
  'How can I reduce risk?',
  'What is diversification?',
  'Why is correlation important?',
];

export function AssistantPage({ portfolio }: AssistantPageProps) {
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      role: 'assistant',
      text: `Hi! I can explain ${portfolio.name} in simple language. What would you like to know?`,
    },
  ]);
  const [text, setText] = useState('');

  function answer(question: string) {
    const lower = question.toLowerCase();
    if (lower.includes('why') && lower.includes('risk')) {
      return `Your portfolio is around ${portfolio.riskScore}/100 mainly because the biggest positions are concentrated in technology assets. NVDA and TSLA also have relatively high volatility, so large moves in those holdings can affect the whole portfolio more strongly.`;
    }
    if (lower.includes('reduce')) {
      return 'Historically, risk could be reduced by lowering concentration in the largest volatile holdings and increasing the share of assets that behave differently, such as broad bond exposure. Aura is explaining historical risk patterns, not telling you what to buy or sell.';
    }
    if (lower.includes('divers')) {
      return 'Diversification means spreading exposure so the portfolio is not controlled by one asset, sector, or type of market behavior. Aura looks at both weights and how assets historically moved together.';
    }
    if (lower.includes('correlation')) {
      return 'Correlation measures how closely two assets moved together historically. Values near +1 mean they often moved in the same direction, while lower or negative values can provide more diversification.';
    }
    if (lower.includes('drawdown')) {
      return 'Maximum drawdown is the largest historical drop from a portfolio peak to a later trough before a new high. It helps show how severe a past decline was.';
    }
    return `For ${portfolio.name}, Aura focuses on calculated metrics such as volatility, maximum drawdown, Sharpe ratio, concentration, diversification, and risk drivers. Ask me about one of those and I’ll explain it in simpler terms.`;
  }

  function send(question = text) {
    const clean = question.trim();
    if (!clean) return;
    setMessages(previous => [
      ...previous,
      { role: 'user', text: clean },
      { role: 'assistant', text: answer(clean) },
    ]);
    setText('');
  }

  function startNewConversation() {
    setMessages([
      {
        role: 'assistant',
        text: 'New conversation started. What would you like to understand?',
      },
    ]);
  }

  return (
    <div className="page assistant-page">
      <header className="assistant-header">
        <div>
          <span>PORTFOLIO INTELLIGENCE</span>
          <h1>AI Assistant</h1>
          <p>Understand your portfolio risk through clear, educational explanations.</p>
        </div>
        <div className="assistant-header-status">
          <i />
          <span><strong>Aura is ready</strong><small>Using {portfolio.name} context</small></span>
        </div>
      </header>
      <div className="assistant-layout">
        <ConversationList
          onNewConversation={startNewConversation}
          onSelectQuestion={send}
        />
        <ChatWorkspace
          portfolioName={portfolio.name}
          messages={messages}
          text={text}
          prompts={PROMPTS}
          onTextChange={setText}
          onSend={send}
        />
        <PortfolioContext portfolio={portfolio} onAsk={send} />
      </div>
    </div>
  );
}
