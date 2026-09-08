import type { ReactNode } from "react";

/** Markierte Satzglieder (<mark>…) als Highlight statt Rohtext anzeigen. */
export function renderCardQuestion(text: string): ReactNode {
  const src = text || "";
  if (!src.includes("<mark")) {
    return src;
  }
  const parts = src.split(/(<mark>[\s\S]*?<\/mark>)/gi);
  return parts.map((part, index) => {
    const match = part.match(/^<mark>([\s\S]*?)<\/mark>$/i);
    if (!match) {
      return <span key={index}>{part}</span>;
    }
    return (
      <mark key={index} className="card-marked-span">
        {match[1]}
      </mark>
    );
  });
}
