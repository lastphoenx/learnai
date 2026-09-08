import type { ReactNode } from "react";

/** Markierte Satzglieder (<mark>…</mark> oder […]) als Highlight statt Rohtext. */
const HIGHLIGHT_RE =
  /<mark>([\s\S]*?)<\/mark>|\[(?![A-D]\])([^\[\]]+)\]/gi;

export function renderCardQuestion(text: string): ReactNode {
  const src = text || "";
  HIGHLIGHT_RE.lastIndex = 0;
  if (!HIGHLIGHT_RE.test(src)) {
    return src;
  }

  HIGHLIGHT_RE.lastIndex = 0;
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  let match: RegExpExecArray | null;

  while ((match = HIGHLIGHT_RE.exec(src)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<span key={key++}>{src.slice(lastIndex, match.index)}</span>);
    }
    const inner = match[1] ?? match[2] ?? "";
    parts.push(
      <mark key={key++} className="card-marked-span">
        {inner}
      </mark>,
    );
    lastIndex = HIGHLIGHT_RE.lastIndex;
  }

  if (lastIndex < src.length) {
    parts.push(<span key={key++}>{src.slice(lastIndex)}</span>);
  }
  return parts;
}
