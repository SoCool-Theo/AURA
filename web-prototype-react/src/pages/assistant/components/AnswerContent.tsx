import type { ReactNode } from 'react';
import styles from '../AssistantPage.module.css';

function inlineContent(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, index) => part.startsWith('**') && part.endsWith('**')
    ? <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>
    : <span key={`${part}-${index}`}>{part}</span>);
}

export function AnswerContent({ answer }: { answer: string }) {
  const lines = answer.replace(/\r\n/g, '\n').trim().split('\n');
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];
  let bullets: string[] = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const text = paragraph.join(' ').trim();
    if (text) blocks.push(<p key={`p-${blocks.length}`}>{inlineContent(text)}</p>);
    paragraph = [];
  };

  const flushBullets = () => {
    if (!bullets.length) return;
    blocks.push(<ul key={`ul-${blocks.length}`}>{bullets.map((item, index) => <li key={`${item}-${index}`}>{inlineContent(item)}</li>)}</ul>);
    bullets = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      flushBullets();
      continue;
    }

    const heading = line.match(/^#{1,3}\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushBullets();
      blocks.push(<h3 key={`h-${blocks.length}`}>{inlineContent(heading[1])}</h3>);
      continue;
    }

    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      bullets.push(bullet[1]);
      continue;
    }

    const numbered = line.match(/^\d+[.)]\s+(.+)$/);
    if (numbered) {
      flushParagraph();
      bullets.push(numbered[1]);
      continue;
    }

    flushBullets();
    paragraph.push(line);
  }

  flushParagraph();
  flushBullets();

  return <div className={styles.answerContent}>{blocks}</div>;
}
