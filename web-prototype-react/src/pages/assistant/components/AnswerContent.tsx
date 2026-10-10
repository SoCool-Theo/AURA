import type { ReactNode } from 'react';
import { formatAgentAnswer, type AnswerInlinePart } from '../answerFormatting';
import styles from '../AssistantPage.module.css';

function inlineContent(parts: AnswerInlinePart[]): ReactNode[] {
  return parts.map((part, index) => part.bold
    ? <strong key={index}>{part.text}</strong>
    : <span key={index}>{part.text}</span>);
}

export function AnswerContent({ answer }: { answer: string }) {
  return <div className={styles.answerContent}>
    {formatAgentAnswer(answer).map((block, index) => {
      if (block.type === 'heading') return <h3 key={index}>{inlineContent(block.parts)}</h3>;
      if (block.type === 'paragraph') return <p key={index}>{inlineContent(block.parts)}</p>;
      if (block.type === 'table') return <div key={index} className={styles.answerTableWrap}
        role="region" aria-label="Aura answer table" tabIndex={0}>
        <table className={styles.answerTable}>
          <caption className="sr-only">Aura answer table</caption>
          <thead><tr>{block.headers.map((parts, column) =>
            <th key={column} scope="col" style={{ textAlign: block.alignments[column] }}>{inlineContent(parts)}</th>)}</tr></thead>
          <tbody>{block.rows.map((row, rowIndex) => <tr key={rowIndex}>
            {row.map((parts, column) => <td key={column} style={{ textAlign: block.alignments[column] }}>{inlineContent(parts)}</td>)}
          </tr>)}</tbody>
        </table>
      </div>;
      return <ul key={index}>{block.items.map((parts, itemIndex) => <li key={itemIndex}>{inlineContent(parts)}</li>)}</ul>;
    })}
  </div>;
}
