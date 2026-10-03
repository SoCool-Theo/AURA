export type AnswerInlinePart = {
  text: string;
  bold: boolean;
};
export type AnswerCellAlignment = 'left' | 'center' | 'right';
export type AnswerBlock =
  | { type: 'heading'; parts: AnswerInlinePart[] }
  | { type: 'paragraph'; parts: AnswerInlinePart[] }
  | { type: 'bullets'; items: AnswerInlinePart[][] }
  | { type: 'table'; headers: AnswerInlinePart[][]; rows: AnswerInlinePart[][][]; alignments: AnswerCellAlignment[] };

function inlineParts(text: string): AnswerInlinePart[] {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map(part =>
    part.startsWith('**') && part.endsWith('**')
      ? { text: part.slice(2, -2), bold: true }
      : { text: part, bold: false });
}

// Split only actual column separators, not escaped pipes or pipes inside code spans.
function tableCells(line: string): string[] | null {
  const text = line.trim();
  const cells: string[] = [];
  let cell = '', codeTicks = 0, separators = 0, endedWithSeparator = false;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    endedWithSeparator = false;
    if (char === '\\' && i + 1 < text.length) {
      const next = text[++i];
      cell += next === '|' || next === '\\' ? next : '\\' + next;
      continue;
    }
    if (char === '`') {
      let run = 1;
      while (text[i + run] === '`') run++;
      if (codeTicks === 0) codeTicks = run;
      else if (codeTicks === run) codeTicks = 0;
      cell += '`'.repeat(run); i += run - 1;
      continue;
    }
    if (char === '|' && codeTicks === 0) {
      cells.push(cell.trim()); cell = ''; separators++; endedWithSeparator = true;
    } else cell += char;
  }
  if (!separators) return null;
  cells.push(cell.trim());
  if (text.startsWith('|')) cells.shift();
  if (endedWithSeparator) cells.pop();
  return cells.length ? cells : null;
}

function tableAt(lines: string[], start: number): { block: Extract<AnswerBlock, { type: 'table' }>; end: number } | null {
  const headers = tableCells(lines[start]);
  const delimiters = tableCells(lines[start + 1] ?? '');
  if (!headers || !delimiters || headers.length !== delimiters.length
    || !delimiters.every(cell => /^:?-{3,}:?$/.test(cell))) return null;
  const alignments: AnswerCellAlignment[] = delimiters.map(cell =>
    cell.startsWith(':') && cell.endsWith(':') ? 'center' : cell.endsWith(':') ? 'right' : 'left');
  const rows: AnswerInlinePart[][][] = [];
  let end = start + 2;
  while (end < lines.length) {
    const cells = tableCells(lines[end]);
    // Preserve malformed rows as text; never silently drop or shift financial values.
    if (!cells || cells.length !== headers.length) break;
    rows.push(cells.map(inlineParts)); end++;
  }
  return { block: { type: 'table', headers: headers.map(inlineParts), rows, alignments }, end };
}

export function formatAgentAnswer(answer: string): AnswerBlock[] {
  const lines = answer.replace(/\r\n?/g, '\n').trim().split('\n');
  const blocks: AnswerBlock[] = [];
  let paragraph: string[] = [], bullets: AnswerInlinePart[][] = [];
  let fence: { char: string; length: number } | null = null;
  const flushParagraph = () => {
    if (!paragraph.length) return;
    const text = paragraph.join(' ').trim();
    if (text) blocks.push({ type: 'paragraph', parts: inlineParts(text) });
    paragraph = [];
  };
  const flushBullets = () => {
    if (!bullets.length) return;
    blocks.push({ type: 'bullets', items: bullets }); bullets = [];
  };
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index].trim();
    const marker = line.match(/^(`{3,}|~{3,})(.*)$/);
    if (fence || marker) {
      flushBullets(); paragraph.push(line);
      if (fence) {
        if (marker && marker[1][0] === fence.char && marker[1].length >= fence.length && !marker[2].trim()) fence = null;
      } else if (marker) fence = { char: marker[1][0], length: marker[1].length };
      continue;
    }
    if (!line) { flushParagraph(); flushBullets(); continue; }
    const table = tableAt(lines, index);
    if (table) {
      flushParagraph(); flushBullets(); blocks.push(table.block); index = table.end - 1; continue;
    }
    const heading = line.match(/^#{1,3}\s+(.+)$/);
    if (heading) { flushParagraph(); flushBullets(); blocks.push({ type: 'heading', parts: inlineParts(heading[1]) }); continue; }
    const bullet = line.match(/^(?:[-*]|\d+[.)])\s+(.+)$/);
    if (bullet) { flushParagraph(); bullets.push(inlineParts(bullet[1])); continue; }
    flushBullets(); paragraph.push(line);
  }
  flushParagraph(); flushBullets();
  return blocks;
}
