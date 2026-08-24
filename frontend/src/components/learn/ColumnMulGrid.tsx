"use client";

import type { ColumnMulLayout } from "@/lib/quizOption";

function padLeft(cells: string[], width: number): string[] {
  return [...Array(Math.max(0, width - cells.length)).fill(""), ...cells];
}

function Row({
  op,
  cells,
  className,
}: {
  op?: string;
  cells: string[];
  className?: string;
}) {
  return (
    <>
      <span className="mul-column-op">{op || ""}</span>
      {cells.map((ch, i) => (
        <span key={`${className || "d"}-${i}`} className={className}>
          {ch}
        </span>
      ))}
    </>
  );
}

export function ColumnMulGrid({ layout }: { layout: ColumnMulLayout }) {
  const digitWidth = Math.max(
    layout.top.length,
    layout.bottom.length,
    layout.total.length,
    ...(layout.partials || []).map((p) => p.length),
    (layout.carries || []).length,
  );
  const carries = padLeft(
    (layout.carries || []).map((c) => c || ""),
    digitWidth,
  );
  const top = padLeft(layout.top.split(""), digitWidth);
  const bottom = padLeft(layout.bottom.split(""), digitWidth);
  const total = padLeft(layout.total.split(""), digitWidth);
  const partials = (layout.partials || []).map((p) => padLeft(p.split(""), digitWidth));
  const cols = digitWidth + 1;

  return (
    <div className="mul-column-wrap">
      <div className="mul-column" style={{ gridTemplateColumns: `1.25em repeat(${digitWidth}, 1.15em)` }}>
        <Row op="" cells={carries} className="mul-column-carry" />
        <Row op="" cells={top} className="mul-column-digit" />
        <Row op="×" cells={bottom} className="mul-column-digit" />
        <span className="mul-column-rule" style={{ gridColumn: `1 / span ${cols}` }} />
        {partials.length > 1
          ? partials.map((row, i) => (
              <Row key={`p-${i}`} op={i === 0 ? "" : "+"} cells={row} className="mul-column-digit" />
            ))
          : null}
        {partials.length > 1 ? (
          <span className="mul-column-rule" style={{ gridColumn: `1 / span ${cols}` }} />
        ) : null}
        <Row op="" cells={total} className="mul-column-digit mul-column-total" />
      </div>
    </div>
  );
}
