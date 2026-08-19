"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import {
  analyzeExam,
  createRemediationFromExam,
  deleteExam,
  examFileUrl,
  patchExam,
  uploadExam,
  type ExamResult,
  type ExamPatchBody,
} from "@/lib/api";

const EXAM_TYPE_LABELS: Record<string, string> = {
  klassenarbeit: "Klassenarbeit",
  test: "Test / Lernzielkontrolle",
  muendlich: "Mündliche Prüfung",
  sonstiges: "Sonstiges",
};

function formatExamGrade(exam: ExamResult) {
  if (exam.grade_label) return exam.grade_label;
  if (exam.score != null && exam.max_score != null) return `${exam.score}/${exam.max_score}`;
  if (exam.score != null) return `${exam.score} Pkt.`;
  return "—";
}

function formatDate(iso: string | null) {
  if (!iso) return "Datum unbekannt";
  try {
    return new Date(iso).toLocaleDateString("de-CH");
  } catch {
    return iso.slice(0, 10);
  }
}

type Props = {
  unitId: string;
  exams: ExamResult[];
  onChange: () => void;
  disabled?: boolean;
};

export function UnitExamSection({ unitId, exams, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [takenAt, setTakenAt] = useState("");
  const [examType, setExamType] = useState("klassenarbeit");
  const [gradeLabel, setGradeLabel] = useState("");
  const [score, setScore] = useState("");
  const [maxScore, setMaxScore] = useState("");
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editGrade, setEditGrade] = useState("");
  const [editNotes, setEditNotes] = useState("");

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Bitte eine Datei wählen (Foto oder PDF der korrigierten Prüfung).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await uploadExam(unitId, file, {
        taken_at: takenAt || undefined,
        exam_type: examType,
        grade_label: gradeLabel.trim() || undefined,
        score: score ? Number(score) : undefined,
        max_score: maxScore ? Number(maxScore) : undefined,
        notes: notes.trim() || undefined,
      });
      setFile(null);
      setGradeLabel("");
      setScore("");
      setMaxScore("");
      setNotes("");
      setOpen(false);
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function startEdit(exam: ExamResult) {
    setEditingId(exam.id);
    setEditGrade(exam.grade_label || "");
    setEditNotes(exam.notes || "");
  }

  async function saveEdit(examId: string) {
    setBusy(true);
    setError(null);
    try {
      const body: ExamPatchBody = {
        grade_label: editGrade.trim() || null,
        notes: editNotes.trim() || null,
      };
      await patchExam(unitId, examId, body);
      setEditingId(null);
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card unit-section">
      <div className="section-head">
        <h2>Schulprüfung</h2>
        <span className="badge badge-neutral">{exams.length}</span>
      </div>
      <p className="muted section-lead">
        Korrigierte Prüfung hochladen, Note eintragen und per KI Fehlermuster erkennen lassen.
      </p>

      {exams.length > 0 && (
        <ul className="source-list" style={{ marginBottom: "1rem" }}>
          {exams.map((exam) => (
            <li key={exam.id} className="source-item exam-item">
              <div className="source-meta">
                <span className="badge badge-exam">{EXAM_TYPE_LABELS[exam.exam_type] || exam.exam_type}</span>
                <strong>{formatExamGrade(exam)}</strong>
                <span className="muted">{formatDate(exam.taken_at)}</span>
                {exam.status === "analyzed" && <span className="badge badge-ready">Analysiert</span>}
                {exam.status === "action_created" && <span className="badge badge-ready">Nacharbeit</span>}
                {exam.original_name && <span className="muted source-flags">{exam.original_name}</span>}
              </div>
              {editingId === exam.id ? (
                <div className="exam-edit stack" style={{ width: "100%", marginTop: "0.5rem" }}>
                  <label>
                    Note
                    <input value={editGrade} onChange={(e) => setEditGrade(e.target.value)} placeholder="z.B. 5 oder 4+" />
                  </label>
                  <label>
                    Kommentar
                    <textarea value={editNotes} onChange={(e) => setEditNotes(e.target.value)} rows={2} />
                  </label>
                  <div className="filter-row">
                    <button type="button" className="btn-sm btn-primary" onClick={() => saveEdit(exam.id)} disabled={busy}>
                      Speichern
                    </button>
                    <button type="button" className="btn-sm ghost" onClick={() => setEditingId(null)}>
                      Abbrechen
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {exam.notes && <p className="exam-notes muted">{exam.notes}</p>}
                  {exam.analysis && (
                    <div className="exam-analysis">
                      {exam.analysis.summary && <p>{exam.analysis.summary}</p>}
                      {(exam.analysis.gaps || []).length > 0 && (
                        <div>
                          <strong>Verständnislücken</strong>
                          <ul>
                            {(exam.analysis.gaps || []).map((g, i) => (
                              <li key={i}>{g}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {(exam.analysis.error_patterns || []).length > 0 && (
                        <div>
                          <strong>Fehlermuster</strong>
                          <ul className="exam-pattern-list">
                            {(exam.analysis.error_patterns || []).map((p, i) => (
                              <li key={i}>
                                <span className="badge badge-math">{p.label || p.tag}</span>
                                {p.count ? ` · ${p.count}×` : ""}
                                {(p.examples || []).length > 0 && (
                                  <span className="muted"> — {p.examples?.[0]}</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {(exam.analysis.recommendations || []).length > 0 && (
                        <div>
                          <strong>Empfehlungen</strong>
                          <ul>
                            {(exam.analysis.recommendations || []).map((r, i) => (
                              <li key={i}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {(exam.analysis.tasks || []).length > 0 && (
                        <div>
                          <strong>Aufgaben</strong>
                          <ul className="exam-task-list">
                            {(exam.analysis.tasks || []).map((t, i) => (
                              <li key={i} className={t.correct ? "exam-task-ok" : "exam-task-fail"}>
                                <span>
                                  {t.index != null ? `Aufgabe ${t.index}: ` : ""}
                                  {t.description || "—"}
                                  {t.max_points != null
                                    ? ` (${t.points_earned ?? "?"}/${t.max_points} Pkt.)`
                                    : ""}
                                </span>
                                {(t.error_tags || []).length > 0 && (
                                  <span className="exam-task-tags">
                                    {(t.error_tags || []).map((tag) => (
                                      <span key={tag} className="badge badge-math">
                                        {tag.replace(/_/g, " ")}
                                      </span>
                                    ))}
                                  </span>
                                )}
                                {(t.errors || []).length > 0 && (
                                  <span className="muted"> — {(t.errors || [])[0]}</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="source-actions">
                    {exam.has_file && (
                      <a className="btn-sm ghost" href={examFileUrl(unitId, exam.id)} target="_blank" rel="noreferrer">
                        Ansehen
                      </a>
                    )}
                    {exam.has_file && exam.status !== "analyzed" && (
                      <button
                        type="button"
                        className="btn-sm btn-primary"
                        disabled={busy}
                        onClick={async () => {
                          setBusy(true);
                          setError(null);
                          try {
                            await analyzeExam(unitId, exam.id);
                            onChange();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Analyse fehlgeschlagen");
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        KI-Analyse
                      </button>
                    )}
                    {exam.has_file && exam.status === "analyzed" && (
                      <button
                        type="button"
                        className="btn-sm ghost"
                        disabled={busy}
                        onClick={async () => {
                          setBusy(true);
                          try {
                            await analyzeExam(unitId, exam.id);
                            onChange();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Analyse fehlgeschlagen");
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        Analyse neu
                      </button>
                    )}
                    {exam.analysis && !exam.remediation_unit_id && (
                      <button
                        type="button"
                        className="btn-sm btn-primary"
                        disabled={busy}
                        onClick={async () => {
                          setBusy(true);
                          setError(null);
                          try {
                            const res = await createRemediationFromExam(unitId, exam.id);
                            onChange();
                            if (res.unit?.id) {
                              window.location.href = `/units/${res.unit.id}`;
                            }
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Nacharbeit fehlgeschlagen");
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        Nacharbeit erstellen
                      </button>
                    )}
                    {exam.remediation_unit_id && (
                      <Link className="btn-sm ghost" href={`/units/${exam.remediation_unit_id}`}>
                        Zur Nacharbeit
                      </Link>
                    )}
                    <button type="button" className="btn-sm ghost" onClick={() => startEdit(exam)} disabled={busy}>
                      ✎
                    </button>
                    <button
                      type="button"
                      className="btn-sm ghost danger-text"
                      disabled={busy}
                      onClick={async () => {
                        if (!confirm("Prüfungseintrag inkl. Datei löschen?")) return;
                        setBusy(true);
                        try {
                          await deleteExam(unitId, exam.id);
                          onChange();
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Löschen fehlgeschlagen");
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      Löschen
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {!open ? (
        <button type="button" className="btn" onClick={() => setOpen(true)} disabled={disabled || busy}>
          Prüfung erfassen
        </button>
      ) : (
        <form onSubmit={onUpload} className="card stack exam-upload-form">
          <h3 style={{ margin: 0, fontSize: "1rem" }}>Neue Schulprüfung</h3>
          <div className="form-row">
            <label>
              Prüfungsdatum
              <input type="date" value={takenAt} onChange={(e) => setTakenAt(e.target.value)} />
            </label>
            <label>
              Art
              <select value={examType} onChange={(e) => setExamType(e.target.value)}>
                {Object.entries(EXAM_TYPE_LABELS).map(([k, label]) => (
                  <option key={k} value={k}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="form-row">
            <label>
              Note (Schulnote)
              <input value={gradeLabel} onChange={(e) => setGradeLabel(e.target.value)} placeholder="z.B. 5 oder 4+" />
            </label>
            <label>
              Punkte erreicht
              <input type="number" min={0} value={score} onChange={(e) => setScore(e.target.value)} />
            </label>
            <label>
              Max. Punkte
              <input type="number" min={1} value={maxScore} onChange={(e) => setMaxScore(e.target.value)} />
            </label>
          </div>
          <label>
            Kommentar (Korrekturen, Auffälligkeiten)
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="z.B. häufige Fehler bei Bruchrechnung, Nachkommastellen …"
            />
          </label>
          <label className="file-drop">
            <span className="btn">Prüfung wählen</span>
            <input
              type="file"
              accept="image/*,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              hidden
              required
            />
            <span className="muted">{file ? file.name : "Foto oder PDF der korrigierten Prüfung"}</span>
          </label>
          {error && <p className="err">{error}</p>}
          <div className="filter-row">
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Speichern…" : "Hochladen"}
            </button>
            <button type="button" className="ghost" onClick={() => setOpen(false)} disabled={busy}>
              Abbrechen
            </button>
          </div>
        </form>
      )}
      {error && !open && <p className="err">{error}</p>}
    </section>
  );
}
