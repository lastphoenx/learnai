"use client";

type Props = {
  className?: string;
  numbered?: boolean;
  slotCount?: number;
};

const SPOKE_ANGLES = [0, 60, 120, 180, 240, 300, 45, 135];

/** Neutrales Schema — nummerierte Plätze zum Zuordnen von Begriffen. */
export function GenericDiagramSvg({ className, numbered = false, slotCount = 5 }: Props) {
  const count = Math.max(3, Math.min(8, slotCount || 5));
  const nodeAngles = SPOKE_ANGLES.slice(0, count);

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
      </defs>
      <rect width="400" height="260" fill="url(#generic-diagram-bg)" rx="8" />
      <rect x="24" y="24" width="352" height="212" fill="none" stroke="#c5d3e3" strokeWidth="2" rx="12" />
      <circle cx="200" cy="130" r="28" fill="#dbeafe" stroke="#64748b" strokeWidth="2" />
      {numbered && (
        <text x="200" y="135" textAnchor="middle" fontSize="14" fontWeight="700" fill="#334155">
          ?
        </text>
      )}
      {nodeAngles.map((deg) => {
        const rad = (deg * Math.PI) / 180;
        const x2 = 200 + 110 * Math.cos(rad);
        const y2 = 130 + 72 * Math.sin(rad);
        return (
          <line
            key={`spoke-${deg}`}
            x1="200"
            y1="130"
            x2={x2}
            y2={y2}
            stroke="#94a3b8"
            strokeWidth="2"
            strokeDasharray="6 4"
          />
        );
      })}
      {nodeAngles.map((deg, index) => {
        const rad = (deg * Math.PI) / 180;
        const cx = 200 + 110 * Math.cos(rad);
        const cy = 130 + 72 * Math.sin(rad);
        return (
          <g key={`node-${deg}`}>
            <circle cx={cx} cy={cy} r="16" fill="#f8fafc" stroke="#64748b" strokeWidth="2" />
            {numbered && (
              <text x={cx} y={cy + 5} textAnchor="middle" fontSize="13" fontWeight="700" fill="#1e293b">
                {index + 1}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
