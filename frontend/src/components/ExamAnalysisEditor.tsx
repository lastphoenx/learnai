"use client";

import { FormEvent, useEffect, useState } from "react";
import { EXAM_ERROR_TAG_OPTIONS, labelForErrorTag } from "@/lib/examErrorTags";
import type { ExamAnalysis } from "@/lib/api";

type Props = {
  analysis: ExamAnalysis;
  onSave: (analysis: ExamAnalysis) => Promise<void>;
  onCancel: () => void;
  busy?: boolean;
};

function cloneAnalysis(a: ExamAnalysis): ExamAnalysis {
  return JSON.parse(JSON.stringify(a)) as ExamAnalysis;
}

export function ExamAnalysisEditor({ analysis, onSave, onCancel, busy }: Props) {
  const [draft, setDraft] = useState<ExamAnalysis>(() => cloneAnalysis(analysis));

  useEffect(() => {
    setDraft(cloneAnalysis(analysis));
  }, [analysis]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await onSave(draft);
  }

  function updateTask(index: number, patch: Partial<NonNullable<ExamAnalysis["tasks"]>[number]>) {
    setDraft((d) => {
      const tasks = [...(d.tasks || [])];
      tasks[index] = { ...tasks[index], ...patch };
      return { ...d, tasks };
    });
  }

  function setTaskTags(index: number, raw: string) {
    const tags = raw
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);
    updateTask(index, { error_tags: tags });
  }

  return (
    <form onSubmit={onSubmit} className="exam-analysis-editor stack">
      <p className="muted section-lead" style={{ margin: 0 }}>
        KI-Analyse manuell korrigieren — Änderungen werden für Nacharbeit und Trends verwendet.
      </p>

      <label>
        Zusammenfassung
        <textarea
          rows={3}
          value={draft.summary || ""}
          onChange={(e) => setDraft({ ...draft, summary: e.target.value })}
        />
      </label>

      <label>
        Verständnislücken (eine pro Zeile)
        <textarea
          rows={3}
          value={(draft.gaps || []).join("\n")}
          onChange={(e) =>
            setDraft({
              ...draft,
              gaps: e.target.value.split("\n").map((l) => l.trim()).filter(Boolean),
            })
          }
        />
      </label>

      <label>
        Empfehlungen (eine pro Zeile)
        <textarea
          rows={3}
          value={(draft.recommendations || []).join("\n")}
          onChange={(e) =>
            setDraft({
              ...draft,
              recommendations: e.target.value.split("\n").map((l) => l.trim()).filter(Boolean),
            })
          }
        />
      </label>

      <div>
        <strong>Aufgaben</strong>
        <ul className="exam-task-edit-list">
          {(draft.tasks || []).map((task, i) => (
            <li key={i} className="card exam-task-edit-item">
              <div className="form-row">
                <label>
                  Nr.
                  <input
                    type="number"
                    min={1}
                    value={task.index ?? i + 1}
                    onChange={(e) => updateTask(i, { index: Number(e.target.value) || i + 1 })}
                  />
                </label>
                <label className="exam-task-correct-label">
                  <input
                    type="checkbox"
                    checked={task.correct === true}
                    onChange={(e) => updateTask(i, { correct: e.target.checked })}
                  />
                  Korrekt
                </label>
                <label>
                  Pkt. erreicht
                  <input
                    type="number"
                    min={0}
                    value={task.points_earned ?? ""}
                    onChange={(e) =>
                      updateTask(i, {
                        points_earned: e.target.value === "" ? undefined : Number(e.target.value),
                      })
                    }
                  />
                </label>
                <label>
                  Max. Pkt.
                  <input
                    type="number"
                    min={0}
                    value={task.max_points ?? ""}
                    onChange={(e) =>
                      updateTask(i, {
                        max_points: e.target.value === "" ? undefined : Number(e.target.value),
                      })
                    }
                  />
                </label>
              </div>
              <label>
                Beschreibung
                <input
                  value={task.description || ""}
                  onChange={(e) => updateTask(i, { description: e.target.value })}
                />
              </label>
              <label>
                Fehler-Tags (kommagetrennt)
                <input
                  list={`exam-tags-${i}`}
                  value={(task.error_tags || []).join(", ")}
                  onChange={(e) => setTaskTags(i, e.target.value)}
                  placeholder="z.B. fractions_denominator, unit_conversion"
                />
                <datalist id={`exam-tags-${i}`}>
                  {EXAM_ERROR_TAG_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </datalist>
              </label>
              {(task.error_tags || []).length > 0 && (
                <p className="exam-task-tags">
                  {(task.error_tags || []).map((tag) => (
                    <span key={tag} className="badge badge-math">
                      {labelForErrorTag(tag)}
                    </span>
                  ))}
                </p>
              )}
              <label>
                Fehlerhinweis
                <input
                  value={(task.errors || [])[0] || ""}
                  onChange={(e) =>
                    updateTask(i, { errors: e.target.value.trim() ? [e.target.value.trim()] : [] })
                  }
                />
              </label>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="btn-sm ghost"
          onClick={() =>
            setDraft((d) => ({
              ...d,
              tasks: [
                ...(d.tasks || []),
                { index: (d.tasks?.length || 0) + 1, description: "", correct: false, error_tags: [] },
              ],
            }))
          }
        >
          + Aufgabe
        </button>
      </div>

      <div className="filter-row">
        <button type="submit" className="btn-sm btn-primary" disabled={busy}>
          {busy ? "Speichern…" : "Analyse speichern"}
        </button>
        <button type="button" className="btn-sm ghost" onClick={onCancel} disabled={busy}>
          Abbrechen
        </button>
      </div>
    </form>
  );
}
