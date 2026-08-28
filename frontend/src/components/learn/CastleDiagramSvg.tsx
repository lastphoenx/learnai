"use client";

type Props = {
  className?: string;
};

/** Vereinfachte Burgsilhouette — Hotspots liegen relativ (0–1) darüber. */
export function CastleDiagramSvg({ className }: Props) {
  return (
    <svg
      viewBox="0 0 400 260"
      className={className}
      role="img"
      aria-label="Burg-Skizze zum Beschriften"
    >
      <defs>
        <linearGradient id="castle-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#b8d4f0" />
          <stop offset="100%" stopColor="#e8f0fa" />
        </linearGradient>
        <linearGradient id="castle-hill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#8fbc8f" />
          <stop offset="100%" stopColor="#6b9b6b" />
        </linearGradient>
      </defs>
      <rect width="400" height="260" fill="url(#castle-sky)" />
      <ellipse cx="200" cy="230" rx="220" ry="55" fill="url(#castle-hill)" />
      <path d="M0 210 Q80 195 160 205 T320 200 T400 215 L400 260 L0 260 Z" fill="#5a8f5a" />
      <path d="M30 215 Q120 200 200 208 T370 212 L370 260 L30 260 Z" fill="#4a90e2" opacity="0.55" />
      {/* Bergfried */}
      <rect x="278" y="28" width="44" height="120" fill="#9a8b7a" stroke="#5c5348" strokeWidth="2" />
      <polygon points="278,28 300,8 322,28" fill="#7a6b5a" stroke="#5c5348" strokeWidth="2" />
      <rect x="292" y="55" width="16" height="22" fill="#c9dde8" stroke="#5c5348" />
      {/* Hauptmauer */}
      <rect x="118" y="88" width="168" height="72" fill="#a89a88" stroke="#5c5348" strokeWidth="2" />
      <polygon points="118,88 202,62 286,88" fill="#8a7d6c" stroke="#5c5348" strokeWidth="2" />
      {[138, 168, 198, 228, 258].map((x) => (
        <rect key={x} x={x} y="98" width="12" height="18" fill="#c9dde8" stroke="#5c5348" strokeWidth="1" />
      ))}
      {/* Seitenturm links */}
      <rect x="88" y="72" width="36" height="88" fill="#9a8b7a" stroke="#5c5348" strokeWidth="2" />
      <polygon points="88,72 106,52 124,72" fill="#7a6b5a" stroke="#5c5348" strokeWidth="2" />
      {/* Tor */}
      <rect x="178" y="118" width="44" height="42" fill="#4a3f36" stroke="#5c5348" strokeWidth="2" />
      <path d="M178 160 Q200 138 222 160" fill="none" stroke="#3a3028" strokeWidth="3" />
      {/* Brücke */}
      <rect x="148" y="152" width="104" height="8" fill="#8b7355" stroke="#5c5348" strokeWidth="1" />
      <rect x="142" y="158" width="8" height="28" fill="#6b5a45" />
      <rect x="250" y="158" width="8" height="28" fill="#6b5a45" />
    </svg>
  );
}
