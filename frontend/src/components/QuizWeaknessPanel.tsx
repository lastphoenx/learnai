"use client";

import Link from "next/link";
import { useState } from "react";
import {
  createInteractiveTrainerFromQuiz,
  createRemediationFromQuiz,
  type QuizWeaknesses,
} from "@/lib/api";
import { QuizExplanation } from "@/components/learn/QuizExplanation";

type Props = {
  unitId: string;
  data: QuizWeaknesses;
  compact?: boolean;
  onCreated?: () => void;
};

export function QuizWeaknessPanel({ unitId, data, compact = false, onCreated }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!data.can_remediate || data.wrong_count === 0) {
    return null;
  }

  const preview = data.weaknesses.slice(0, compact ? 3 : 6);

  async function onRemediation() {
    setBusy(true);
    setError(null);
    try {
      const res = await createRemediationFromQuiz(unitId);
      onCreated?.();
      if (res.unit?.id) {
        window.location.href = `/units/${res.unit.id}?autogen=1`;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nacharbeit fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onTrainer() {
    if (
      !confirm(
        "Neue Trainer-Einheit aus Quiz-Schwächen anlegen und KI-Generierung starten?"
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await createInteractiveTrainerFromQuiz(unitId);
      onCreated?.();
      if (res.unit?.id) {
        window.location.href = `/units/${res.unit.id}?autogen=1`;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trainer fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={`quiz-weakness-panel${compact ? " quiz-weakness-panel-compact" : ""}`}>
      <div className="section-head">
        <h3>Quiz-Schwächen</h3>
        <span className="badge badge-quiz">
          {data.wrong_count} falsch · {data.quiz_correct}/{data.quiz_total} richtig
        </span>
      </div>
      <p className="muted section-lead">
        Die KI kann gezielt Nacharbeit und einen Trainer zu genau diesen Fehlern erstellen.
      </p>
      {(data.error_tags || []).length > 0 && (
        <div className="badge-row quiz-weakness-tags">
          {(data.error_tags || []).slice(0, 5).map((t) => (
            <span key={t.key || t.tag} className="badge badge-neutral" title={t.label}>
              {t.label} ({t.count})
            </span>
          ))}
        </div>
      )}
      <ul className="quiz-weakness-list">
        {preview.map((w) => (
          <li key={`${w.module_id}-${w.question_index}`}>
            <span className="badge badge-neutral">{w.module_title}</span>
            <strong>{w.question}</strong>
            {w.explanation && <QuizExplanation text={w.explanation} />}
          </li>
        ))}
      </ul>
      {data.wrong_count > preview.length && (
        <p className="muted">… und {data.wrong_count - preview.length} weitere Fehler</p>
      )}
      {error && <p className="err">{error}</p>}
      <div className="learn-actions">
        {data.remediation_unit_id ? (
          <Link className="btn btn-primary" href={`/units/${data.remediation_unit_id}`}>
            Zur Nacharbeit
          </Link>
        ) : (
          <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void onRemediation()}>
            Nacharbeit aus Schwächen
          </button>
        )}
        {data.trainer_unit_id ? (
          <Link className="btn ghost" href={`/units/${data.trainer_unit_id}/learn`}>
            Zum Schwächen-Trainer
          </Link>
        ) : (
          <button type="button" className="btn ghost" disabled={busy} onClick={() => void onTrainer()}>
            Trainer aus Schwächen
          </button>
        )}
      </div>
    </section>
  );
}
