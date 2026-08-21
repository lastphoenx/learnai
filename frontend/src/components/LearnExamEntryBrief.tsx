"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { ExamLearnEntry } from "@/lib/api";

type Props = {
  unitId: string;
  entry: ExamLearnEntry;
};

export function LearnExamEntryBrief({ unitId, entry }: Props) {
  const storageKey = `learn-exam-entry-dismissed-${unitId}-${entry.exam_id}`;
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem(storageKey) !== "1") {
      setVisible(true);
    }
  }, [storageKey]);

  if (!visible || !entry.summary) {
    return null;
  }

  function dismiss() {
    sessionStorage.setItem(storageKey, "1");
    setVisible(false);
  }

  const title =
    entry.match === "same_unit"
      ? "Dein Prüfungs-Feedback zu dieser Einheit"
      : entry.source_unit_title
        ? `Prüfungs-Feedback (${entry.source_unit_title})`
        : "Prüfungs-Feedback als Einstieg";

  return (
    <section className="card exam-learning-entry stack">
      <p className="learn-phase-kicker">Kurzbericht · Lern-Einstieg</p>
      <h2>{title}</h2>
      <p className="exam-learning-summary">{entry.summary}</p>
      {(entry.gaps || []).length > 0 && (
        <div>
          <strong>Priorität zum Üben</strong>
          <ul>
            {(entry.gaps || []).slice(0, 3).map((gap, i) => (
              <li key={i}>{gap}</li>
            ))}
          </ul>
        </div>
      )}
      {(entry.error_tags || []).length > 0 && (
        <div className="badge-row">
          {(entry.error_tags || []).slice(0, 5).map((tag) => (
            <span key={tag.tag} className="badge badge-neutral" title={tag.tag}>
              {tag.label}
            </span>
          ))}
        </div>
      )}
      <div className="learn-actions">
        {entry.remediation_unit_id && (
          <Link className="btn ghost" href={`/units/${entry.remediation_unit_id}`}>
            Zur Prüfungs-Nacharbeit
          </Link>
        )}
        {entry.trainer_unit_id && (
          <Link className="btn ghost" href={`/units/${entry.trainer_unit_id}/learn`}>
            Zum Prüfungs-Trainer
          </Link>
        )}
        <button type="button" className="btn ghost" onClick={dismiss}>
          Verstanden, weiter lernen
        </button>
      </div>
    </section>
  );
}
