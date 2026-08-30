import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import styles from '../DeferredFeature.module.css';

export function AssistantPage() {
  return <div className={`page ${styles.page}`}><header className={styles.header}><span>FUTURE AI EXPERIENCE</span><h1>AI Assistant</h1><p>The interface is reserved for Aura’s future educational explanation service.</p></header><Card className={styles.card}><span className={styles.icon}><Icon name="spark" size={28} /></span><span className={styles.badge}>Backend AI not connected</span><h2>AI explanations are not available yet</h2><p>Aura does not currently have an AI Agent endpoint. Sending messages, generated portfolio explanations, conversation history, and portfolio-aware AI responses are disabled until that backend capability exists.</p><div className={styles.facts}><div><strong>Available now</strong><small>Deterministic portfolio analytics, reports, and historical simulations.</small></div><div><strong>Deferred</strong><small>Generated explanations and conversational portfolio guidance.</small></div></div></Card></div>;
}
