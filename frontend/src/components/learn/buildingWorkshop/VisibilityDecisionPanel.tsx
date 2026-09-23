"use client";

import type { ReactNode } from "react";
import type { SpatialSequenceAnswer } from "@/lib/spatialSequence";

type Expected = SpatialSequenceAnswer["visibility"];

type Props = {
  value: Expected | null;
  expected: Expected | undefined;
  disabled?: boolean;
  onPick: (v: Expected) => void;
  onContinue?: () => void;
  showContinue?: boolean;
};

export function VisibilityDecisionPanel({
  value,
  expected,
  disabled,
  onPick,
  onContinue,
  showContinue,
}: Props) {
  const picked = value;
  let decisionNote: ReactNode = null;
  if (picked && expected) {
    const correct = picked === expected;
    if (correct) {
      decisionNote =
        picked === "one_view_sufficient" ? (
          <>
            <b>Richtig:</b> Die entscheidenden Höhen bleiben in dieser Aufgabe aus der ersten Sicht erkennbar.
          </>
        ) : (
          <>
            <b>Richtig:</b> Die erste Sicht lässt verdeckte Stellen offen. Nutze die zweite Schrägansicht.
          </>
        );
    } else {
      decisionNote = (
        <>
          <b>Noch einmal prüfen:</b> Verfolge jede Spalte von vorne nach hinten — gibt es vollständig verdeckte Säulen?
        </>
      );
    }
  }

  function btnClass(choice: Expected) {
    if (!picked || picked !== choice) return "btn secondary building-views-choice";
    if (!expected) return "btn building-views-choice building-views-choice--on";
    const correct = choice === expected;
    return `btn building-views-choice building-views-choice--on${correct ? " building-views-choice--ok" : " building-views-choice--bad"}`;
  }

  return (
    <div className="building-views-question">
      <b>Reicht die erste Schrägansicht aus, um alle nötigen Informationen eindeutig zu erkennen?</b>
      <div className="btnrow building-views-question-buttons">
        <button
          type="button"
          className={btnClass("one_view_sufficient")}
          disabled={disabled}
          onClick={() => onPick("one_view_sufficient")}
        >
          Ja, sie reicht
        </button>
        <button
          type="button"
          className={btnClass("second_view_required")}
          disabled={disabled}
          onClick={() => onPick("second_view_required")}
        >
          Nein, weitere Sicht nötig
        </button>
      </div>
      {decisionNote ? <p className="building-views-decision-note">{decisionNote}</p> : null}
      {showContinue && picked && onContinue ? (
        <button type="button" className="btn-primary" style={{ marginTop: "0.65rem" }} onClick={onContinue}>
          Weiter zu den Ansichten
        </button>
      ) : null}
    </div>
  );
}
