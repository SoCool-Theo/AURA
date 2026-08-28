import type { KeyboardEvent } from 'react';
import type { AssistantMessage } from '../../../types/assistant';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface ChatWorkspaceProps {
  portfolioName: string;
  messages: AssistantMessage[];
  text: string;
  prompts: string[];
  onTextChange: (text: string) => void;
  onSend: (question?: string) => void;
}

export function ChatWorkspace({
  portfolioName,
  messages,
  text,
  prompts,
  onTextChange,
  onSend,
}: ChatWorkspaceProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') onSend();
  }

  return (
    <Card className="chat-card">
      <div className="chat-head">
        <div className="aura-chat-identity">
          <span><Icon name="spark" size={20} /></span>
          <div><strong>Aura</strong><small><i className="online-dot" /> Portfolio risk assistant</small></div>
        </div>
        <div className="chat-context-pill">
          <Icon name="wallet" size={15} />
          <span>{portfolioName}</span>
          <Icon name="chevron-down" size={14} />
        </div>
      </div>
      <div className="messages" aria-live="polite">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <span className="message-avatar">
              {message.role === 'assistant' ? <Icon name="spark" size={15} /> : 'Y'}
            </span>
            <div className="message-content">
              <small>{message.role === 'assistant' ? 'Aura' : 'You'}</small>
              <p>{message.text}</p>
              <time>{message.role === 'assistant' ? 'Now' : 'Just now'}</time>
            </div>
          </div>
        ))}
      </div>
      <div className="assistant-suggestions">
        <span>Suggested questions</span>
        <div className="prompt-chips">
          {prompts.map(prompt => (
            <button key={prompt} onClick={() => onSend(prompt)}>
              <Icon name="spark" size={12} />{prompt}
            </button>
          ))}
        </div>
      </div>
      <div className="chat-composer">
        <div className="chat-input">
          <button className="composer-add" aria-label="Add context">＋</button>
          <input
            value={text}
            onChange={event => onTextChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Aura about risk, performance, or diversification..."
          />
          <button className="composer-send" onClick={() => onSend()} aria-label="Send message">↑</button>
        </div>
        <div className="composer-meta">
          <span>Press Enter to send</span>
          <span><Icon name="shield" size={12} /> Educational explanations only</span>
        </div>
      </div>
    </Card>
  );
}
