import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

interface ConversationListProps {
  onNewConversation: () => void;
  onSelectQuestion: (question: string) => void;
}

const TODAY_CONVERSATIONS = [
  ['Why is my risk high?', '11:23 PM'],
  ['How did I perform?', '9:14 PM'],
  ['Which asset affects risk?', '7:08 PM'],
];

const YESTERDAY_CONVERSATIONS = ['Explain correlation', 'How to reduce drawdown?'];

export function ConversationList({
  onNewConversation,
  onSelectQuestion,
}: ConversationListProps) {
  return (
    <Card className="conversation-list">
      <div className="conversation-heading">
        <div><h2>Conversations</h2><small>Your recent questions</small></div>
        <button aria-label="Search conversations"><Icon name="search" size={17} /></button>
      </div>
      <button className="primary-btn new-conversation-btn" onClick={onNewConversation}>
        <span>＋</span> New Conversation
      </button>
      <div className="conversation-group">
        <small>TODAY</small>
        {TODAY_CONVERSATIONS.map(([title, time], index) => (
          <button
            key={title}
            className={index === 0 ? 'active' : ''}
            onClick={() => onSelectQuestion(title)}
          >
            <span className="conversation-icon"><Icon name="assistant" size={15} /></span>
            <span><strong>{title}</strong><small>{time}</small></span>
            <i>›</i>
          </button>
        ))}
      </div>
      <div className="conversation-group">
        <small>YESTERDAY</small>
        {YESTERDAY_CONVERSATIONS.map(title => (
          <button key={title} onClick={() => onSelectQuestion(title)}>
            <span className="conversation-icon"><Icon name="assistant" size={15} /></span>
            <span><strong>{title}</strong><small>Yesterday</small></span>
            <i>›</i>
          </button>
        ))}
      </div>
      <div className="conversation-foot">
        <Icon name="shield" size={17} />
        <p>Your conversations use portfolio metrics from this educational prototype.</p>
      </div>
    </Card>
  );
}
