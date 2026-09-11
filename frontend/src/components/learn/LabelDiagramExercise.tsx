"use client";

import { useMemo, useState } from "react";
import { GenericDiagramSvg } from "@/components/learn/GenericDiagramSvg";
import type { TrainerLabelDiagram } from "@/lib/api";

type Props = {
  diagram: TrainerLabelDiagram;
  busy: boolean;
  result: { correct: boolean; expected?: string | null } | null;
  onSubmit: (answer: string) => void;
};

const POSITION_HINTS = /^(oben|unten|links|rechts)/i;

function stableShuffle(items: string[], salt: string): string[] {
  return [...items].sort((a, b) => {
    const hash = (value: string) =>
      Array.from(`${salt}:${value}`).reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
    return hash(a) - hash(b);
  });
}

function displayHint(raw: string | null | undefined): string | null {
  const text = raw?.trim();
  if (!text || POSITION_HINTS.test(text)) return null;
  return text;
}

export function LabelDiagramExercise({ diagram, busy, result, onSubmit }: Props) {
  const hotspots = diagram.hotspots || [];
  const terms = useMemo(
    () => stableShuffle(diagram.terms || [], diagram.title || "diagram"),
    [diagram.terms, diagram.title],
  );
  const layout = diagram.layout || "radial";
  const [selectedTerm, setSelectedTerm] = useState<string | null>(null);
  const [assignments, setAssignments] = useState<Record<string, string>>({});

  const usedTerms = new Set(Object.values(assignments));
  const allPlaced = hotspots.length > 0 && hotspots.every((hs) => assignments[hs.id]);
  const hasSemanticHints = hotspots.some((hs) => Boolean(displayHint(hs.hint)));

  function placeOnHotspot(hotspotId: string) {
    if (result || !selectedTerm) return;
    setAssignments((prev) => {
      const next = { ...prev };
      for (const [key, value] of Object.entries(next)) {
        if (value === selectedTerm) delete next[key];
      }
      next[hotspotId] = selectedTerm;
      return next;
    });
    setSelectedTerm(null);
  }

  function clearHotspot(hotspotId: string) {
    if (result) return;
    setAssignments((prev) => {
      const next = { ...prev };
      delete next[hotspotId];
      return next;
    });
  }

  function handleSubmit() {
    if (!allPlaced || result) return;
    onSubmit(JSON.stringify(assignments));
  }

  return (
    <div className="label-diagram-exercise stack">
      {diagram.title && <h4 className="label-diagram-title">{diagram.title}</h4>}
      {diagram.instruction && (
        <p className="label-diagram-instruction">{diagram.instruction}</p>
      )}
      <p className="muted label-diagram-hint">
        {selectedTerm
          ? `«${selectedTerm}» — tippe die passende Stelle auf dem Schema.`
          : hasSemanticHints
            ? "Tippe einen Begriff, dann die passende Stelle. Über die Fragezeichen fährst du für Hinweise."
            : "Tippe einen Begriff, dann die passende Stelle auf dem Schema."}
      </p>
      <div className="label-diagram-stage">
        <GenericDiagramSvg
          className="label-diagram-svg"
          layout={layout}
          slotCount={hotspots.length}
        />
        {hotspots.map((hs) => {
          const placed = assignments[hs.id];
          const left = `${Math.round(hs.x * 100)}%`;
          const top = `${Math.round(hs.y * 100)}%`;
          const hoverHint = displayHint(hs.hint) || "Was gehört hierhin?";
          return (
            <button
              key={hs.id}
              type="button"
              className={`label-diagram-hotspot${placed ? " filled" : ""}${selectedTerm && !placed ? " ready" : ""}${displayHint(hs.hint) ? " has-hint" : ""}`}
              style={{ left, top }}
              disabled={busy || Boolean(result)}
              aria-label={placed ? `${placed} zugeordnet` : hoverHint}
              onClick={() => (placed ? clearHotspot(hs.id) : placeOnHotspot(hs.id))}
            >
              {placed ? (placed.length > 10 ? `${placed.slice(0, 9)}…` : placed) : "?"}
              {!placed && displayHint(hs.hint) && (
                <span className="label-diagram-hotspot-tooltip" role="tooltip">
                  {displayHint(hs.hint)}
                </span>
              )}
            </button>
          );
        })}
      </div>
      <div className="label-diagram-terms" role="listbox" aria-label="Fachbegriffe">
        {terms.map((term) => {
          const isUsed = usedTerms.has(term);
          const isSelected = selectedTerm === term;
          return (
            <button
              key={term}
              type="button"
              role="option"
              aria-selected={isSelected}
              className={`label-diagram-term${isSelected ? " selected" : ""}${isUsed ? " used" : ""}`}
              disabled={busy || Boolean(result) || isUsed}
              onClick={() => setSelectedTerm(isSelected ? null : term)}
            >
              {term}
            </button>
          );
        })}
      </div>
      {!result && (
        <div className="learn-actions">
          <button type="button" className="btn-primary" disabled={busy || !allPlaced} onClick={handleSubmit}>
            Antwort prüfen
          </button>
        </div>
      )}
      {result && (
        <p className={result.correct ? "quiz-verdict ok" : "quiz-verdict bad"}>
          {result.correct ? "Richtig zugeordnet!" : "Noch nicht alle Begriffe richtig — versuche es noch einmal."}
        </p>
      )}
    </div>
  );
}
