"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { UnitEditDialog } from "@/components/UnitEditDialog";
import { UnitExamSection } from "@/components/UnitExamSection";
import {
  addSourceUrl,
  createReviewUnit,
  deleteSource,
  deleteUnit,
  fetchMe,
  fetchUnit,
  fetchUnitTaskTypes,
  generateUnit,
  patchUnit,
  purgeSource,
  speak,
  uploadSource,
  type LearningUnit,
  type User,
} from "@/lib/api";
import {
  languageLabel,
  mathFocusLabel,
  taskTypeLabel,
  type UnitTaskType,
} from "@/lib/taskTypes";

function statusBadge(status: string) {
  if (status === "ready") return { label: "Bereit", className: "badge badge-ready" };
  if (status === "draft") return { label: "Entwurf", className: "badge badge-draft" };
  return { label: status, className: "badge" };
}

function sourceKindLabel(kind: string) {
  const map: Record<string, string> = {
    image: "Foto",
    pdf: "PDF",
    audio: "Audio",
    url: "Link",
    text: "Text",
  };
  return map[kind] || kind;
}

export default function UnitDetailPage() {
  const params = useParams();
  const router = useRouter();
  const unitId = params.id as string;
  const [user, setUser] = useState<User | null>(null);
  const [unit, setUnit] = useState<LearningUnit | null>(null);
  const [taskTypes, setTaskTypes] = useState<UnitTaskType[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sourceUrl, setSourceUrl] = useState("");
  const [editOpen, setEditOpen] = useState(false);

  function reload() {
    fetchUnit(unitId).then(setUnit).catch(() => setError("Einheit nicht gefunden"));
  }

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
      })
      .catch(() => setError("Nicht angemeldet"));
    fetchUnitTaskTypes()
      .then((d) => setTaskTypes(d.task_types || []))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (unitId) reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unitId]);

  async function onFiles(e: ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files?.length) return;
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        await uploadSource(unitId, file);
      }
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload fehlgeschlagen");
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  async function onAddUrl(e: FormEvent) {
    e.preventDefault();
    if (!sourceUrl.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await addSourceUrl(unitId, sourceUrl.trim());
      setSourceUrl("");
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Link hinzufügen fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteUnit() {
    if (
      !confirm(
        "Lerneinheit inkl. Dateien löschen? Verlauf, Ergebnisse und die Kurzbeschreibung bleiben für Berichte und für «ähnlich nochmal» erhalten."
      )
    ) {
      return;
    }
    await deleteUnit(unitId);
    router.push("/history");
  }

  async function onSpeak() {
    if (!unit?.title) return;
    try {
      const blob = await speak(`${unit.title}. ${unit.brief || ""}`, unit.language);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Vorlesen nicht möglich");
    }
  }

  async function onGenerate() {
    setBusy(true);
    setError(null);
    try {
      const next = await generateUnit(unitId);
      setUnit(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "KI-Aufbereitung fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  if (error && !unit) {
    return (
      <main className="shell">
        <AppHeader user={user} />
        <p className="err">{error}</p>
        <Link href="/units">Zurück zu Einheiten</Link>
      </main>
    );
  }

  const badge = unit ? statusBadge(unit.status) : null;
  const moduleCount = unit?.modules?.length ?? 0;
  const sourceCount = unit?.sources?.length ?? 0;

  return (
    <main className="shell shell-wide unit-page">
      <AppHeader user={user} />
      {error && <p className="err">{error}</p>}

      {unit && (
        <>
          <nav className="breadcrumb" aria-label="Brotkrumen">
            <Link href="/units">Einheiten</Link>
            <span aria-hidden="true">›</span>
            <span>{unit.title}</span>
          </nav>

          <section className="unit-hero card">
            <div className="unit-hero-top">
              <div>
                <p className="hero-kicker">Lerneinheit</p>
                <h1 className="unit-title">{unit.title}</h1>
              </div>
              <button
                type="button"
                className="icon-btn edit-btn"
                onClick={() => setEditOpen(true)}
                aria-label="Einheit bearbeiten"
                title="Bearbeiten"
              >
                ✎
              </button>
            </div>

            <div className="badge-row">
              {badge && <span className={badge.className}>{badge.label}</span>}
              <span className="badge badge-subject">{unit.subject || "Ohne Fach"}</span>
              <span className="badge badge-mode">{taskTypeLabel(unit.task_type || "mixed", taskTypes)}</span>
              {unit.math_focus && (
                <span className="badge badge-math">{mathFocusLabel(unit.math_focus)}</span>
              )}
              <span className="badge badge-neutral">{languageLabel(unit.language)}</span>
              <span className="badge badge-neutral">Stufe {unit.difficulty}</span>
              {unit.target_age && <span className="badge badge-neutral">{unit.target_age} J.</span>}
              {unit.learner_name && <span className="badge badge-neutral">{unit.learner_name}</span>}
            </div>

            {unit.brief ? (
              <p className="unit-brief">{unit.brief}</p>
            ) : (
              <p className="muted unit-brief-empty">Keine Beschreibung — Stift klicken zum Ergänzen.</p>
            )}
          </section>

          <section className="card unit-section">
            <h2>Aktionen</h2>
            <div className="action-grid">
              {(unit.modules || []).length > 0 && (
                <Link className="btn btn-primary action-tile" href={`/units/${unit.id}/learn`}>
                  <strong>
                    {unit.learn_progress?.status === "in_progress"
                      ? "Weiterlernen"
                      : unit.learn_progress?.status === "completed"
                        ? "Nochmal lernen"
                        : "Lernen starten"}
                  </strong>
                  <span className="muted">
                    {unit.learn_progress?.percent
                      ? `${unit.learn_progress.percent}% Fortschritt`
                      : `${moduleCount} Lernblock${moduleCount === 1 ? "" : "e"}`}
                  </span>
                </Link>
              )}
              <button type="button" className="action-tile" onClick={onGenerate} disabled={busy}>
                <strong>{busy ? "KI arbeitet…" : "Mit KI aufbereiten"}</strong>
                <span className="muted">
                  {sourceCount > 0 ? `${sourceCount} Quelle(n)` : "Aus Titel & Auftrag"}
                </span>
              </button>
              <button
                type="button"
                className="action-tile"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError(null);
                  try {
                    const review = await createReviewUnit(unitId);
                    router.push(`/units/${review.id}`);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Wiederholung konnte nicht erstellt werden");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <strong>Wiederholung</strong>
                <span className="muted">Festigung mit gleichen Quellen</span>
              </button>
              <button type="button" className="action-tile" onClick={onSpeak} disabled={busy}>
                <strong>Vorlesen</strong>
                <span className="muted">OpenAI TTS</span>
              </button>
            </div>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={unit.auto_purge_sources}
                onChange={async (e) => {
                  const next = await patchUnit(unit.id, { auto_purge_sources: e.target.checked });
                  setUnit(next);
                }}
              />
              <span>Fotos nach OCR automatisch löschen (Metadaten bleiben)</span>
            </label>
          </section>

          <section className="card unit-section">
            <div className="section-head">
              <h2>Quellen</h2>
              <span className="badge badge-neutral">{sourceCount}</span>
            </div>
            <p className="muted section-lead">Fotos, PDF, Audio oder Links — Grundlage für die KI-Aufbereitung.</p>
            <label className="file-drop">
              <span className="btn">Dateien wählen</span>
              <input type="file" multiple accept="image/*,.pdf,audio/*" onChange={onFiles} disabled={busy} hidden />
              <span className="muted">Bilder, PDF oder Audio</span>
            </label>
            <form onSubmit={onAddUrl} className="inline-form">
              <input
                type="url"
                placeholder="https://… Link als Quelle"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                disabled={busy}
              />
              <button type="submit" className="btn-primary" disabled={busy || !sourceUrl.trim()}>
                Link hinzufügen
              </button>
            </form>
            {(unit.sources || []).length === 0 ? (
              <p className="muted empty-hint">Noch keine Quellen hochgeladen.</p>
            ) : (
              <ul className="source-list">
                {(unit.sources || []).map((s) => (
                  <li key={s.id} className="source-item">
                    <div className="source-meta">
                      <span className="badge badge-source">{sourceKindLabel(s.kind)}</span>
                      <strong>{s.original_name || "Unbenannt"}</strong>
                      <span className="muted source-flags">
                        {!s.has_file && "Datei entfernt · "}
                        {s.has_extracted_text ? "Text extrahiert" : "Kein Text"}
                      </span>
                    </div>
                    <div className="source-actions">
                      {s.has_file && (
                        <button type="button" className="btn-sm ghost" onClick={() => purgeSource(unit.id, s.id).then(reload)}>
                          Datei löschen
                        </button>
                      )}
                      <button type="button" className="btn-sm ghost danger-text" onClick={() => deleteSource(unit.id, s.id).then(reload)}>
                        Entfernen
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <UnitExamSection
            unitId={unitId}
            exams={unit.exams || []}
            onChange={reload}
            disabled={busy}
          />

          <section className="card unit-section">
            <div className="section-head">
              <h2>Lernblöcke</h2>
              <span className="badge badge-neutral">{moduleCount}</span>
            </div>
            {moduleCount === 0 ? (
              <p className="muted empty-hint">
                Noch keine Blöcke — Quellen hochladen und «Mit KI aufbereiten». Ohne Quellen nutzt die KI Titel
                und Auftrag.
              </p>
            ) : (
              <ol className="module-list">
                {(unit.modules || []).map((m, idx) => {
                  const content = m.content as { text?: string } | null;
                  const quiz = m.quiz as { questions?: { q: string; options?: string[]; answer?: number }[] } | null;
                  const qCount = quiz?.questions?.length ?? 0;
                  return (
                    <li key={m.id} className="module-card">
                      <div className="module-head">
                        <span className="module-num">{idx + 1}</span>
                        <h3>{m.title}</h3>
                        {qCount > 0 && <span className="badge badge-quiz">{qCount} Fragen</span>}
                      </div>
                      {content?.text && <div className="module-body">{content.text}</div>}
                      {qCount > 0 && (
                        <details className="module-quiz">
                          <summary>Quiz anzeigen</summary>
                          <ol>
                            {(quiz?.questions || []).map((q, i) => (
                              <li key={i}>
                                {q.q}
                                <ul className="quiz-options">
                                  {(q.options || []).map((opt, j) => (
                                    <li key={j} className={j === q.answer ? "quiz-correct" : undefined}>
                                      {opt}
                                      {j === q.answer ? " ✓" : ""}
                                    </li>
                                  ))}
                                </ul>
                              </li>
                            ))}
                          </ol>
                        </details>
                      )}
                    </li>
                  );
                })}
              </ol>
            )}
          </section>

          <section className="unit-danger-zone">
            <button type="button" className="btn-sm ghost danger-text" onClick={onDeleteUnit}>
              Ganze Einheit löschen (Verlauf bleibt)
            </button>
          </section>

          <UnitEditDialog
            unit={unit}
            open={editOpen}
            onClose={() => setEditOpen(false)}
            onSaved={(next) => setUnit(next)}
          />
        </>
      )}
    </main>
  );
}
