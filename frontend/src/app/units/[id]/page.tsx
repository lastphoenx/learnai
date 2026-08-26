"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { UnitAssignSection } from "@/components/UnitAssignSection";
import { UnitDeleteDialog } from "@/components/UnitDeleteDialog";
import { UnitEditDialog } from "@/components/UnitEditDialog";
import { UnitExamSection } from "@/components/UnitExamSection";
import { SourcePreviewModal } from "@/components/SourcePreviewModal";
import { useChildPreview } from "@/lib/childPreview";
import {
  addSourceUrl,
  createReviewUnit,
  createTestCopyUnit,
  reviewUnitHref,
  deleteSource,
  deleteUnit,
  fetchMe,
  fetchProfiles,
  fetchUnit,
  fetchUnitTaskTypes,
  generateUnit,
  fetchGenerateStatus,
  waitForGenerateJob,
  fetchQuizWeaknesses,
  patchUnit,
  purgeSource,
  sourceFileUrl,
  speak,
  unitWorksheetPdfUrl,
  unitTrainerExportUrl,
  extractUnitPedagogy,
  fetchUnitPedagogy,
  uploadSource,
  type GenerateJobStatus,
  type LearningUnit,
  type LearnerProfile,
  type QuizWeaknesses,
  type UnitModule,
  type UnitPedagogy,
  type UnitSource,
  type User,
} from "@/lib/api";
import { QuizWeaknessPanel } from "@/components/QuizWeaknessPanel";
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
  const searchParams = useSearchParams();
  const unitId = params.id as string;
  const [user, setUser] = useState<User | null>(null);
  const { asChild } = useChildPreview(user);
  const [unit, setUnit] = useState<LearningUnit | null>(null);
  const [taskTypes, setTaskTypes] = useState<UnitTaskType[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sourceUrl, setSourceUrl] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [generateJob, setGenerateJob] = useState<GenerateJobStatus | null>(null);
  const [profiles, setProfiles] = useState<LearnerProfile[]>([]);
  const [quizWeaknesses, setQuizWeaknesses] = useState<QuizWeaknesses | null>(null);
  const [pedagogy, setPedagogy] = useState<UnitPedagogy | null>(null);
  const [pedagogyBusy, setPedagogyBusy] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [previewSource, setPreviewSource] = useState<UnitSource | null>(null);
  const autogenStarted = useRef(false);

  function reload() {
    return fetchUnit(unitId).then(setUnit).catch(() => setError("Einheit nicht gefunden"));
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
    fetchProfiles()
      .then(setProfiles)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (unitId) reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unitId]);

  useEffect(() => {
    if (!unitId || !unit?.source_count) {
      setPedagogy(null);
      return;
    }
    fetchUnitPedagogy(unitId)
      .then(setPedagogy)
      .catch(() => setPedagogy(null));
  }, [unitId, unit?.source_count, unit?.updated_at]);

  async function onExtractPedagogy() {
    setPedagogyBusy(true);
    try {
      const data = await extractUnitPedagogy(unitId);
      setPedagogy(data);
      reload();
    } catch {
      setError("Didaktik konnte nicht aus den Quellen gelesen werden.");
    } finally {
      setPedagogyBusy(false);
    }
  }

  useEffect(() => {
    if (!unitId || !unit?.module_count) {
      setQuizWeaknesses(null);
      return;
    }
    fetchQuizWeaknesses(unitId)
      .then(setQuizWeaknesses)
      .catch(() => setQuizWeaknesses(null));
  }, [unitId, unit?.module_count, unit?.learn_progress?.quiz_total, unit?.learn_progress?.status]);

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

  async function onDeleteUnit(purgeHistory: boolean) {
    setDeleteBusy(true);
    try {
      await deleteUnit(unitId, { purgeHistory });
      router.push(purgeHistory ? "/units" : "/history");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Löschen fehlgeschlagen");
      setDeleteBusy(false);
      setDeleteOpen(false);
    }
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
    setGenerateJob({ status: "queued", message: "Starte…", progress_pct: 0 });
    try {
      const started = await generateUnit(unitId, unit?.trainer_options?.llm_provider || undefined);
      if (started.mode === "sync") {
        setUnit(started.unit);
        return;
      }
      setGenerateJob(started.job);
      const next = await waitForGenerateJob(unitId, setGenerateJob);
      setUnit(next);
      setGenerateJob(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "KI-Aufbereitung fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!unit || unit.task_type !== "interactive" || (unit.modules || []).length > 0 || busy) return;
    let cancelled = false;
    fetchGenerateStatus(unitId)
      .then((res) => {
        if (cancelled) return;
        if (res.job.status === "queued" || res.job.status === "running") {
          setBusy(true);
          setGenerateJob(res.job);
          return waitForGenerateJob(unitId, setGenerateJob)
            .then((next) => {
              if (!cancelled) setUnit(next);
            })
            .catch((err) => {
              if (!cancelled) {
                setError(err instanceof Error ? err.message : "KI-Aufbereitung fehlgeschlagen");
              }
            })
            .finally(() => {
              if (!cancelled) {
                setBusy(false);
                setGenerateJob(null);
              }
            });
        }
      })
      .catch((err) => {
        if (!cancelled && err instanceof Error && err.message !== "Kein laufender Generierungsjob") {
          setError(err.message);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unit?.id, unit?.task_type, unit?.modules?.length]);

  useEffect(() => {
    if (searchParams.get("autogen") !== "1" || !unit || busy || autogenStarted.current) return;
    router.replace(`/units/${unitId}`);
    if ((unit.modules || []).length > 0) return;
    autogenStarted.current = true;
    void onGenerate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unit?.id, unit?.modules?.length, searchParams, busy]);

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
        <div className="unit-page-layout">
          <div className="unit-page-main">
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
              {unit.reference_code && (
                <span className="badge badge-neutral unit-ref-badge" title="Referenz-Code für Support und Qualitätsreport">
                  Ref {unit.reference_code}
                </span>
              )}
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

          {user && !asChild && unit && (
            <UnitAssignSection
              unitId={unitId}
              currentUnit={unit}
              currentProfileId={unit.profile_id}
              learnerName={unit.learner_name}
              profiles={profiles}
              onAssigned={reload}
            />
          )}

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
                {(unit.sources || []).map((s: UnitSource) => {
                  const isImage = s.kind === "image" || (s.content_type || "").startsWith("image/");
                  return (
                  <li key={s.id} className="source-item">
                    {s.has_file && isImage ? (
                      <button
                        type="button"
                        className="source-thumb-btn"
                        onClick={() => setPreviewSource(s)}
                        aria-label={`${s.original_name || "Quelle"} anzeigen`}
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          className="source-thumb"
                          src={sourceFileUrl(unit.id, s.id)}
                          alt=""
                          loading="lazy"
                        />
                      </button>
                    ) : s.has_file ? (
                      <button
                        type="button"
                        className="source-thumb-btn source-thumb-placeholder"
                        onClick={() => setPreviewSource(s)}
                        aria-label={`${s.original_name || "Quelle"} anzeigen`}
                      >
                        {sourceKindLabel(s.kind)}
                      </button>
                    ) : (
                      <div className="source-thumb-btn source-thumb-placeholder source-thumb-missing" aria-hidden>
                        —
                      </div>
                    )}
                    <div className="source-meta">
                      <span className="badge badge-source">{sourceKindLabel(s.kind)}</span>
                      <button type="button" className="source-name-btn" onClick={() => setPreviewSource(s)}>
                        <strong>{s.original_name || "Unbenannt"}</strong>
                      </button>
                      <span className="muted source-flags">
                        {!s.has_file && "Datei entfernt · "}
                        {s.has_extracted_text ? "Text extrahiert" : "Kein Text"}
                      </span>
                    </div>
                    <div className="source-actions">
                      {s.has_file && (
                        <button
                          type="button"
                          className="btn-sm ghost"
                          title="Datei von der Platte entfernen — extrahierter Text bleibt für die KI"
                          onClick={() => purgeSource(unit.id, s.id).then(reload)}
                        >
                          Datei löschen
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn-sm ghost danger-text"
                        title="Quelle vollständig entfernen (Datei + Text)"
                        onClick={() => deleteSource(unit.id, s.id).then(reload)}
                      >
                        Quelle entfernen
                      </button>
                    </div>
                  </li>
                  );
                })}
              </ul>
            )}
          </section>

          {sourceCount > 0 && unit.task_type === "interactive" && (
            <details className="card unit-section unit-pedagogy-section unit-pedagogy-collapsible" open={!pedagogy?.has_pedagogy}>
              <summary className="unit-pedagogy-summary">
                <span className="section-head unit-pedagogy-summary-head">
                  <h2>Didaktik aus Quellen</h2>
                  {pedagogy?.has_pedagogy ? (
                    <span className="badge badge-ready">Erkannt</span>
                  ) : (
                    <span className="badge badge-neutral">Noch nicht gelesen</span>
                  )}
                </span>
                <span className="muted section-lead unit-pedagogy-summary-lead">
                  Lösungswege und Aufgabentypen aus dem Heft — Grundlage für Verstehen, Üben und Check.
                  {pedagogy?.has_pedagogy && pedagogy.quality ? (
                    <>
                      {" "}
                      ({pedagogy.quality.method_count} Strategien
                      {pedagogy.quality.worked_with_steps != null
                        ? `, ${pedagogy.quality.worked_with_steps} Beispiele`
                        : ""}
                      )
                    </>
                  ) : null}
                </span>
              </summary>
              <div className="unit-pedagogy-body">
              {pedagogy?.has_pedagogy ? (
                <>
                  {pedagogy.profile?.methods && pedagogy.profile.methods.length > 0 && (
                    <ul className="unit-pedagogy-methods">
                      {pedagogy.profile.methods.map((method, index) => (
                        <li key={`${method.label}-${index}`} className="unit-pedagogy-method">
                          <strong>{method.label}</strong>
                          {method.when ? <span className="muted"> — {method.when}</span> : null}
                        </li>
                      ))}
                    </ul>
                  )}
                  {pedagogy.profile?.exercise_patterns && pedagogy.profile.exercise_patterns.length > 0 && (
                    <div className="unit-pedagogy-patterns">
                      <span className="muted">Aufgabentypen:</span>{" "}
                      {pedagogy.profile.exercise_patterns.join(" · ")}
                    </div>
                  )}
                  {pedagogy.profile?.worked_examples && pedagogy.profile.worked_examples.length > 0 && (
                    <ul className="unit-pedagogy-examples">
                      {pedagogy.profile.worked_examples.slice(0, 4).map((example, index) => (
                        <li key={`${example.problem}-${index}`}>
                          <strong>{example.problem}</strong>
                          {example.method_label ? ` (${example.method_label})` : ""}
                          {example.steps?.length ? `: ${example.steps.slice(0, 3).join(" → ")}` : ""}
                        </li>
                      ))}
                    </ul>
                  )}
                  {pedagogy.quality ? (
                    <p className="muted unit-pedagogy-quality">
                      Qualität: {pedagogy.quality.level === "good"
                        ? "gut strukturiert"
                        : pedagogy.quality.level === "partial"
                          ? "teilweise erkannt"
                          : "wenig erkannt"}
                      {" "}
                      ({pedagogy.quality.method_count} Strategien
                      {pedagogy.quality.methods_with_when != null
                        ? `, ${pedagogy.quality.methods_with_when} mit Anwendungs-Hinweis`
                        : ""}
                      , {pedagogy.quality.worked_with_steps} Beispiele mit Schritten)
                    </p>
                  ) : null}
                  <pre className="unit-pedagogy-digest">{pedagogy.digest}</pre>
                </>
              ) : (
                <p className="muted empty-hint">
                  Noch keine strukturierte Didaktik. Lies die Quellen ein, bevor du generierst — oder starte
                  «Mit KI aufbereiten» (extrahiert automatisch).
                </p>
              )}
              <div className="unit-pedagogy-actions">
                <button
                  type="button"
                  className="btn"
                  onClick={onExtractPedagogy}
                  disabled={busy || pedagogyBusy}
                >
                  {pedagogyBusy ? "Lese Quellen…" : pedagogy?.has_pedagogy ? "Didaktik aktualisieren" : "Didaktik einlesen"}
                </button>
              </div>
              </div>
            </details>
          )}

          <UnitExamSection
            unitId={unitId}
            exams={unit.exams || []}
            onChange={reload}
            disabled={busy}
          />

          {moduleCount === 0 && (
            <p className="muted empty-hint card unit-section">
              Noch keine Lernblöcke — Quellen hochladen und «Mit KI aufbereiten» in der Seitenleiste. Ohne Quellen
              nutzt die KI Titel und Auftrag.
            </p>
          )}

          <section className="unit-danger-zone">
            <h2 className="danger-text" style={{ margin: 0, fontSize: "1rem" }}>
              Gefahrenzone
            </h2>
            <p className="muted section-lead">
              Diese Lerneinheit unwiderruflich entfernen (getrennt von der Kind-Zuordnung oben).
            </p>
            <button type="button" className="btn-sm ghost danger-text" onClick={() => setDeleteOpen(true)}>
              Einheit löschen…
            </button>
          </section>
          </div>

          <aside className="card unit-section unit-page-aside">
            <h2>Aktionen</h2>

            {moduleCount > 0 && (
              <section className="unit-aside-learn" aria-labelledby="aside-learn-heading">
                <h3 id="aside-learn-heading" className="aside-subhead">
                  Lernen
                  <span className="badge badge-neutral">{moduleCount}</span>
                </h3>
                <Link className="btn btn-primary action-tile unit-learn-cta" href={`/units/${unit.id}/learn`}>
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
                <ol className="module-compact-list">
                  {(unit.modules || []).map((m: UnitModule, idx: number) => {
                    const content = m.content as { cards?: unknown[] } | null;
                    const quiz = m.quiz as { questions?: unknown[] } | null;
                    const qCount = quiz?.questions?.length ?? 0;
                    const cardCount = Array.isArray(content?.cards) ? content.cards.length : 0;
                    const isInteractive = unit.task_type === "interactive";
                    const metaParts: string[] = [];
                    if (isInteractive && cardCount > 0) metaParts.push(`${cardCount} Karten`);
                    if (qCount > 0) metaParts.push(`${qCount} Fragen`);
                    return (
                      <li key={m.id}>
                        <Link href={`/units/${unit.id}/learn?module=${idx}`} className="module-compact-link">
                          <span className="module-num">{idx + 1}</span>
                          <span className="module-compact-body">
                            <strong>{m.title}</strong>
                            {metaParts.length > 0 && (
                              <span className="muted module-compact-meta">{metaParts.join(" · ")}</span>
                            )}
                          </span>
                          <span className="module-compact-go" aria-hidden="true">
                            ›
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                </ol>
                {unit.task_type === "interactive" && (
                  <p className="muted aside-hint">Im Lerntrainer: Wissen, Karten und Quiz — alle Blöcke nacheinander.</p>
                )}
              </section>
            )}

            {quizWeaknesses && (
              <QuizWeaknessPanel
                unitId={unitId}
                data={quizWeaknesses}
                compact
                onCreated={() => {
                  reload();
                  fetchQuizWeaknesses(unitId).then(setQuizWeaknesses).catch(() => undefined);
                }}
              />
            )}

            <h3 className="aside-subhead">Einheit</h3>
            <div className="action-grid action-grid-aside">
              {(unit.modules || []).length > 0 && (
                <a
                  className="action-tile"
                  href={unitWorksheetPdfUrl(unit.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <strong>
                    {unit.task_type === "interactive" ? "Trainer-Arbeitsblatt (PDF)" : "Arbeitsblatt (PDF)"}
                  </strong>
                  <span className="muted">
                    {unit.task_type === "interactive"
                      ? "Kernwissen, Lernkarten, Quiz + Lösungen"
                      : "Zum Ausdrucken — ohne Lösungen"}
                  </span>
                </a>
              )}
              {(unit.modules || []).length > 0 && unit.task_type === "interactive" && (
                <a className="action-tile" href={unitTrainerExportUrl(unit.id)}>
                  <strong>Offline-Export (JSON)</strong>
                  <span className="muted">LearnAI + Bio-Ranger Format</span>
                </a>
              )}
              <button
                type="button"
                className={`action-tile${busy ? " action-tile-busy" : ""}`}
                onClick={onGenerate}
                disabled={busy}
                aria-busy={busy}
              >
                <strong>{busy ? "KI arbeitet…" : "Mit KI aufbereiten"}</strong>
                {unit.task_type === "interactive" && sourceCount > 0 && !pedagogy?.has_pedagogy && !busy && (
                  <span className="muted" style={{ display: "block", marginTop: "0.35rem" }}>
                    Tipp: Zuerst «Didaktik einlesen» — dann siehst du die erkannten Lösungswege.
                  </span>
                )}
                {busy ? (
                  <div className="generate-progress-compact">
                    <div
                      className="generate-progress-bar"
                      role="progressbar"
                      aria-valuenow={generateJob?.progress_pct ?? 0}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={generateJob?.message || "KI-Generierung"}
                    >
                      <div
                        className="generate-progress-fill"
                        style={{
                          width: `${Math.min(100, Math.max(0, generateJob?.progress_pct ?? 0))}%`,
                        }}
                      />
                    </div>
                    <span className="muted generate-progress-label">
                      {generateJob?.message || "Bitte Tab offen lassen…"}
                      {typeof generateJob?.progress_pct === "number" ? ` (${generateJob.progress_pct}%)` : ""}
                    </span>
                  </div>
                ) : (
                  <span className="muted">
                    {unit.task_type === "interactive" && sourceCount > 0
                      ? `${sourceCount} Quelle(n) — Tab offen lassen`
                      : sourceCount > 0
                        ? `${sourceCount} Quelle(n)`
                        : "Aus Titel & Auftrag"}
                  </span>
                )}
              </button>
              {user && !asChild && (
              <button
                type="button"
                className="action-tile"
                disabled={busy}
                onClick={async () => {
                  if (
                    !confirm(
                      "Es wird eine Testkopie ohne Kind-Zuordnung erstellt — gleiche Quellen und Lernblöcke, aber kein Lernfortschritt des Kindes. Fortfahren?"
                    )
                  ) {
                    return;
                  }
                  setBusy(true);
                  setError(null);
                  try {
                    const copy = await createTestCopyUnit(unitId);
                    router.push(`/units/${copy.id}`);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Testkopie konnte nicht erstellt werden");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <strong>Testkopie erstellen</strong>
                <span className="muted">
                  Für Geräte- und Layout-Tests — Fortschritt des Kindes bleibt unberührt
                </span>
              </button>
              )}
              <button
                type="button"
                className="action-tile"
                disabled={busy}
                onClick={async () => {
                  if (
                    !confirm(
                      "Es wird eine neue Wiederholungs-Einheit angelegt — diese Einheit bleibt unverändert. Die KI erstellt danach neue Aufgaben (dauert einige Minuten). Fortfahren?"
                    )
                  ) {
                    return;
                  }
                  setBusy(true);
                  setError(null);
                  try {
                    const review = await createReviewUnit(unitId);
                    router.push(reviewUnitHref(review));
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Wiederholung konnte nicht erstellt werden");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <strong>Wiederholung</strong>
                <span className="muted">
                  Bei Quiz-Fehlern: Trainer · sonst neue Einheit mit gleichen Quellen
                </span>
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
          </aside>

          <UnitEditDialog
            unit={unit}
            open={editOpen}
            onClose={() => setEditOpen(false)}
            onSaved={(next) => setUnit(next)}
          />

          <UnitDeleteDialog
            open={deleteOpen}
            unitTitle={unit.title}
            learnerName={unit.learner_name}
            busy={deleteBusy}
            onClose={() => setDeleteOpen(false)}
            onDelete={onDeleteUnit}
          />

          {previewSource && (
            <SourcePreviewModal
              unitId={unitId}
              source={previewSource}
              onClose={() => setPreviewSource(null)}
            />
          )}
        </div>
      )}
    </main>
  );
}