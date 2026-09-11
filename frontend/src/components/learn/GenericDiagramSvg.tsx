"use client";

type Layout = "radial" | "timeline" | "pyramid";

type Props = {
  className?: string;
  layout?: Layout | string;
  slotCount?: number;
  /** Wenn false: nur Hintergrund/Linien — Hotspots liegen als HTML darüber. */
  showSlotNodes?: boolean;
};

function radialCoords(index: number, count: number): { x: number; y: number; deg: number } {
  const deg = (360 * index) / Math.max(1, count) - 90;
  const rad = (deg * Math.PI) / 180;
  return {
    x: 200 + 110 * Math.cos(rad),
    y: 130 + 72 * Math.sin(rad),
    deg,
  };
}

function timelineCoords(index: number, count: number): { x: number; y: number } {
  const x = count <= 1 ? 200 : 56 + (288 * index) / (count - 1);
  return { x, y: 130 };
}

function pyramidCoords(index: number, count: number): { x: number; y: number } {
  const rows = Math.max(1, Math.ceil(Math.sqrt(count)));
  const row = Math.floor(index / rows);
  const col = index % rows;
  const rowCount = Math.min(rows, count - row * rows) || 1;
  const x = 200 + (col - (rowCount - 1) / 2) * 72;
  const y = 48 + row * 44;
  return { x, y };
}

/** Neutrales Schema — Fragezeichen-Plätze zum Zuordnen von Begriffen. */
export function GenericDiagramSvg({
  className,
  layout = "radial",
  slotCount = 5,
  showSlotNodes = true,
}: Props) {
  const count = Math.max(3, Math.min(12, slotCount || 5));
  const layoutName: Layout =
    layout === "timeline" || layout === "pyramid" ? layout : "radial";

  const nodes = Array.from({ length: count }, (_, index) => {
    if (layoutName === "timeline") {
      const { x, y } = timelineCoords(index, count);
      return { x, y, deg: 0 };
    }
    if (layoutName === "pyramid") {
      const { x, y } = pyramidCoords(index, count);
      return { x, y, deg: 0 };
    }
    return radialCoords(index, count);
  });

  return (
    <svg
      viewBox="0 0 400 260"
      className={className}
      role="img"
      aria-label="Schema zum Beschriften"
    >
      <defs>
        <linearGradient id="generic-diagram-bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#eef4fb" />
          <stop offset="100%" stopColor="#f8fafc" />
        </linearGradient>
        <marker
          id="generic-diagram-arrow"
          markerWidth="8"
          markerHeight="8"
          refX="6"
          refY="3"
          orient="auto"
        >
          <path d="M0,0 L6,3 L0,6 Z" fill="#64748b" />
        </marker>
      </defs>
      <rect width="400" height="260" fill="url(#generic-diagram-bg)" rx="8" />
      <rect x="24" y="24" width="352" height="212" fill="none" stroke="#c5d3e3" strokeWidth="2" rx="12" />

      {layoutName === "radial" && (
        <>
          <circle cx="200" cy="130" r="28" fill="#dbeafe" stroke="#64748b" strokeWidth="2" />
          <text x="200" y="135" textAnchor="middle" fontSize="16" fontWeight="700" fill="#334155">
            ?
          </text>
          {nodes.map((node, index) => (
            <line
              key={`spoke-${index}`}
              x1="200"
              y1="130"
              x2={node.x}
              y2={node.y}
              stroke="#94a3b8"
              strokeWidth="2"
              strokeDasharray="6 4"
            />
          ))}
        </>
      )}

      {layoutName === "timeline" && (
        <>
          <line x1="48" y1="130" x2="352" y2="130" stroke="#94a3b8" strokeWidth="2" />
          {nodes.slice(0, -1).map((node, index) => {
            const next = nodes[index + 1];
            const span = next.x - node.x;
            const inset = Math.min(14, Math.max(4, span * 0.22));
            let x1 = node.x + inset;
            let x2 = next.x - inset;
            if (x2 <= x1) {
              x1 = node.x + 2;
              x2 = next.x - 2;
            }
            if (x2 <= x1) return null;
            return (
              <line
                key={`timeline-arrow-${index}`}
                x1={x1}
                y1={130}
                x2={x2}
                y2={130}
                stroke="#64748b"
                strokeWidth="2"
                markerEnd="url(#generic-diagram-arrow)"
              />
            );
          })}
          <line
            x1="352"
            y1="130"
            x2="368"
            y2="130"
            stroke="#64748b"
            strokeWidth="2"
            markerEnd="url(#generic-diagram-arrow)"
          />
        </>
      )}

      {layoutName === "pyramid" && (
        <>
          {nodes.slice(0, -1).map((node, index) => {
            const next = nodes[index + 1];
            if (Math.abs(node.y - next.y) > 8) return null;
            return (
              <line
                key={`pyramid-link-${index}`}
                x1={node.x + 16}
                y1={node.y}
                x2={next.x - 16}
                y2={next.y}
                stroke="#94a3b8"
                strokeWidth="1.5"
              />
            );
          })}
        </>
      )}

      {showSlotNodes &&
        nodes.map((node, index) => (
          <g key={`node-${index}`}>
            <circle cx={node.x} cy={node.y} r="16" fill="#f8fafc" stroke="#64748b" strokeWidth="2" />
            <text x={node.x} y={node.y + 5} textAnchor="middle" fontSize="14" fontWeight="700" fill="#1e293b">
              ?
            </text>
          </g>
        ))}
    </svg>
  );
}
