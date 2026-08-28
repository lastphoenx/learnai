"use client";

type Props = {
  className?: string;
};

/** Neutrales Schema — Hotspots liegen relativ (0–1) darüber, ohne thematische Silhouette. */
export function GenericDiagramSvg({ className }: Props) {
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
      {[0, 60, 120, 180, 240, 300].map((deg) => {
        const rad = (deg * Math.PI) / 180;
        const x2 = 200 + 110 * Math.cos(rad);
        const y2 = 130 + 72 * Math.sin(rad);
        return (
          <line
            key={deg}
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
      {[0, 72, 144, 216, 288].map((deg) => {
        const rad = (deg * Math.PI) / 180;
        const cx = 200 + 110 * Math.cos(rad);
        const cy = 130 + 72 * Math.sin(rad);
        return <circle key={`node-${deg}`} cx={cx} cy={cy} r="14" fill="#f1f5f9" stroke="#64748b" strokeWidth="2" />;
      })}
    </svg>
  );
}
