"use client";

import Link from "next/link";
import type { ExamResult } from "@/lib/api";

type Props = {
  unitId: string;
  exam: ExamResult;
};

export function ExamLearningEntry({ unitId, exam }: Props) {
  const analysis = exam.analysis;
  if (!analysis?.summary) {
    return null;
  }

  const wrongCount = (analysis.tasks || []).filter((t) => t.correct === false).length;
  const topGaps = (analysis.gaps || []).slice(0, 3);

  return (
    <section className="exam-learning-entry stack">
      <p className="learn-phase-kicker">Lern-Einstieg nach Prüfung</p>
      <h3>Dein Prüfungs-Feedback</h3>
      <p className="exam-learning-summary">{analysis.summary}</p>
      {topGaps.length > 0 && (
        <div>
          <strong>Priorität zum Üben</strong>
          <ul>
            {topGaps.map((gap, i) => (
              <li key={i}>{gap}</li>
            ))}
          </ul>
        </div>
      )}
      {wrongCount > 0 && (
        <p className="muted">
          {wrongCount} Aufgabe{wrongCount === 1 ? "" : "n"} in der Prüfung falsch — unten Nacharbeit oder Trainer
          starten.
        </p>
      )}
      <div className="learn-actions">
        <Link className="btn btn-primary" href={`/units/${unitId}/learn`}>
          In der App lernen
        </Link>
        {exam.remediation_unit_id && (
          <Link className="btn ghost" href={`/units/${exam.remediation_unit_id}`}>
            Zur Nacharbeit
          </Link>
        )}
        {exam.trainer_unit_id && (
          <Link className="btn ghost" href={`/units/${exam.trainer_unit_id}/learn`}>
            Zum Prüfungs-Trainer
          </Link>
        )}
      </div>
    </section>
  );
}
