"use client";

import { useMemo, useState } from "react";
import { GenericDiagramSvg } from "@/components/learn/GenericDiagramSvg";
import type { TrainerLabelDiagram } from "@/lib/api";

export type LabelDiagramSlotFeedback = {
  id: string;
  correct: boolean;
  expected_term?: string | null;
  user_term?: string | null;
};

type Props = {
  diagram: TrainerLabelDiagram;
  busy: boolean;
  result: {
    correct: boolean;
    label_slots?: LabelDiagramSlotFeedback[] | null;
  } | null;
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

function shortenLabel(text: string, layout: string): string {
  const limit = layout === "timeline" ? 14 : 10;
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 1)}…`;
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

  const slotFeedback = useMemo(() => {
    const map = new Map<string, LabelDiagramSlotFeedback>();
    for (const slot of result?.label_slots ?? []) {
      map.set(slot.id, slot);
    }
    return map;
  }, [result?.label_slots]);

  const usedTerms = new Set(Object.values(assignments));
  const allPlaced = hotspots.length > 0 && hotspots.every((hs) => assignments[hs.id]);
  const hasSemanticHints = hotspots.some((hs) => Boolean(displayHint(hs.hint)));
  const locked = Boolean(result?.correct);
  const showPartialFeedback = Boolean(result && !result.correct && slotFeedback.size > 0);

  const correctTerms = [...slotFeedback.values()].filter((s) => s.correct).map((s) => s.expected_term || s.user_term);
  const wrongTerms = [...slotFeedback.values()].filter((s) => !s.correct);

  function isHotspotLocked(hotspotId: string): boolean {
    if (locked) return true;
    return Boolean(slotFeedback.get(hotspotId)?.correct);
  }

  function placeOnHotspot(hotspotId: string) {
    if (isHotspotLocked(hotspotId) || !selectedTerm) return;
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
    if (isHotspotLocked(hotspotId)) return;
    setAssignments((prev) => {
      const next = { ...prev };
      delete next[hotspotId];
      return next;
    });
  }

  function handleSubmit() {
    if (!allPlaced || locked) return;
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
      <div className="label-diagram-stage" data-layout={layout}>
        <GenericDiagramSvg
          className="label-diagram-svg"
          layout={layout}
          slotCount={hotspots.length}
          showSlotNodes={false}
        />
        {hotspots.map((hs) => {
          const placed = assignments[hs.id];
          const feedback = slotFeedback.get(hs.id);
          const left = `${Math.round(hs.x * 100)}%`;
          const top = `${Math.round(hs.y * 100)}%`;
          const hoverHint = displayHint(hs.hint) || "Was gehört hierhin?";
          const row = hs.y < 0.56 ? "upper" : "lower";
          const hotspotLocked = isHotspotLocked(hs.id);
          return (
            <button
              key={hs.id}
              type="button"
              className={`label-diagram-hotspot${placed ? " filled" : ""}${selectedTerm && !placed && !hotspotLocked ? " ready" : ""}${displayHint(hs.hint) ? " has-hint" : ""}${feedback?.correct ? " slot-ok" : ""}${feedback && !feedback.correct ? " slot-bad" : ""}`}
              style={{ left, top }}
              data-row={layout === "timeline" ? row : undefined}
              disabled={busy || hotspotLocked}
              title={placed || undefined}
              aria-label={
                placed
                  ? feedback?.correct
                    ? `${placed} — richtig`
                    : feedback
                      ? `${placed} — noch nicht richtig`
                      : `${placed} zugeordnet`
                  : hoverHint
              }
              onClick={() => (placed && !hotspotLocked ? clearHotspot(hs.id) : placeOnHotspot(hs.id))}
            >
              {placed ? shortenLabel(placed, layout) : "?"}
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
              disabled={busy || locked || isUsed}
              onClick={() => setSelectedTerm(isSelected ? null : term)}
            >
              {term}
            </button>
          );
        })}
      </div>
      {!locked && (
        <div className="learn-actions">
          <button type="button" className="btn-primary" disabled={busy || !allPlaced} onClick={handleSubmit}>
            Antwort prüfen
          </button>
        </div>
      )}
      {result && (
        <div className={`label-diagram-feedback${result.correct ? " ok" : " bad"}`}>
          {result.correct ? (
            <p className="quiz-verdict ok">Richtig zugeordnet!</p>
          ) : (
            <>
              <p className="quiz-verdict bad">Noch nicht alles stimmt — korrigiere die markierten Stellen.</p>
              {showPartialFeedback && (
                <ul className="label-diagram-slot-summary">
                  {correctTerms.length > 0 && (
                    <li className="slot-summary-ok">
                      <strong>Richtig:</strong> {correctTerms.filter(Boolean).join(", ")}
                    </li>
                  )}
                  {wrongTerms.length > 0 && (
                    <li className="slot-summary-bad">
                      <strong>Noch prüfen:</strong>{" "}
                      {wrongTerms
                        .map((s) => s.user_term || s.expected_term)
                        .filter(Boolean)
                        .join(", ")}
                    </li>
                  )}
                </ul>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
