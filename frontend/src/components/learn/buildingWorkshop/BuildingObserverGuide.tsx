"use client";

/** Draufsicht — Standorte für Vorne, Rechts, Von oben (RaumWerkstatt Kap. 3). */
export function BuildingObserverGuide() {
  return (
    <div className="building-views-guide">
      <b>Wo steht der Betrachter?</b>
      <svg viewBox="0 0 390 220" role="img" aria-label="Draufsicht mit Blickrichtungen">
        <defs>
          <marker id="bwg-arr-r" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 10 5 0 10z" fill="#d9474b" />
          </marker>
          <marker id="bwg-arr-b" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 10 5 0 10z" fill="#3c76e8" />
          </marker>
        </defs>
        <g stroke="#9fb0c2" fill="#fff">
          <rect x="115" y="28" width="150" height="150" rx="8" strokeWidth="2" />
          <text x="190" y="108" textAnchor="middle" fontSize="13" fontWeight="800" fill="#627083">
            GEBÄUDE
          </text>
        </g>
        <text x="190" y="205" textAnchor="middle" fontSize="12" fontWeight="800" fill="#d9474b">
          VORNE (Tiefe 1)
        </text>
        {/* Blick von unten nach oben ins Gebäude */}
        <line x1="190" y1="198" x2="190" y2="178" stroke="#d9474b" strokeWidth="3" markerEnd="url(#bwg-arr-r)" />
        <text x="318" y="108" fontSize="12" fontWeight="800" fill="#3c76e8">
          RECHTS
        </text>
        {/* Blick von rechts nach links ins Gebäude */}
        <line x1="298" y1="103" x2="268" y2="103" stroke="#3c76e8" strokeWidth="3" markerEnd="url(#bwg-arr-b)" />
        <text x="62" y="108" fontSize="12" fontWeight="800" fill="#8b4bb8">
          VON OBEN
        </text>
        <text x="62" y="128" fontSize="18" aria-hidden="true">👁</text>
      </svg>
      <p className="muted building-views-guide-note">
        Pfeile zeigen die <strong>Blickrichtung zum Gebäude</strong>. Vorne = Tiefe 1 (unten im Plan). Rechts = von der
        rechten Seite. Von oben = nur Belegung, keine Höhe.
      </p>
    </div>
  );
}
