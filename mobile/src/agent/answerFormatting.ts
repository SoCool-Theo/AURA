export type AnswerInlinePart = {
  text: string;
  bold: boolean;
};

export type AnswerBlock =
  | { type: 'heading'; parts: AnswerInlinePart[] }
  | { type: 'paragraph'; parts: AnswerInlinePart[] }
  | { type: 'bullets'; items: AnswerInlinePart[][] };

function inlineParts(text: string): AnswerInlinePart[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .filter(Boolean)
    .map((part) => part.startsWith('**') && part.endsWith('**')
      ? { text: part.slice(2, -2), bold: true }
      : { text: part, bold: false });
}

export function formatAgentAnswer(answer: string): AnswerBlock[] {
  const lines = answer.replace(/\r\n/g, '\n').trim().split('\n');
  const blocks: AnswerBlock[] = [];
  let paragraph: string[] = [];
  let bullets: AnswerInlinePart[][] = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const text = paragraph.join(' ').trim();
    if (text) blocks.push({ type: 'paragraph', parts: inlineParts(text) });
    paragraph = [];
  };

  const flushBullets = () => {
    if (!bullets.length) return;
    blocks.push({ type: 'bullets', items: bullets });
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
      blocks.push({ type: 'heading', parts: inlineParts(heading[1]) });
      continue;
    }

    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      bullets.push(inlineParts(bullet[1]));
      continue;
    }

    const numbered = line.match(/^\d+[.)]\s+(.+)$/);
    if (numbered) {
      flushParagraph();
      bullets.push(inlineParts(numbered[1]));
      continue;
    }

    flushBullets();
    paragraph.push(line);
  }

  flushParagraph();
  flushBullets();
  return blocks;
}
