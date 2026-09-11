"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import {
  batchImportCanResume,
  batchImportRowCanRetry,
  cancelBatchImport,
  fetchBatchImportQuality,
  fetchBatchImportStatus,
  fetchMe,
  resumeBatchImport,
  retryBatchImportUnits,
  type BatchImportJob,
  type BatchImportQualitySummary,
  type User,
} from "@/lib/api";

function statusLabel(status: string) {
  switch (status) {
    case "queued":
      return { text: "Warteschlange", className: "badge badge-neutral" };
    case "running":
      return { text: "Läuft", className: "badge badge-ready" };
    case "done":
      return { text: "Fertig", className: "badge badge-ready" };
    case "partial":
      return { text: "Teilweise", className: "badge badge-warn" };
    case "failed":
      return { text: "Fehlgeschlagen", className: "badge badge-draft" };
    case "cancelled":
      return { text: "Abgebrochen", className: "badge badge-neutral" };
    case "cancelling":
      return { text: "Abbruch…", className: "badge badge-warn" };
    default:
      return { text: status, className: "badge badge-neutral" };
  }
}

function unitStatusLabel(status?: string) {
  switch (status) {
    case "pending":
      return "Wartet";
    case "running":
      return "Generiert…";
    case "done":
      return "Fertig";
    case "failed":
      return "Fehler";
    default:
      return status || "—";
  }
}

function pedagogyLevelLabel(level?: string | null) {
  switch (level) {
    case "good":
      return "gut";
    case "partial":
      return "teilweise";
    case "low":
      return "gering";
    default:
      return level || "—";
  }
}

export default function BatchImportProgressPage() {
  const params = useParams();
  const batchId = String(params.jobId || "");
  const [user, setUser] = useState<User | null>(null);
  const [job, setJob] = useState<BatchImportJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [pollRev, setPollRev] = useState(0);
  const [selected, setSelected] = useState<Set<number>>(() => new Set());
  const [quality, setQuality] = useState<BatchImportQualitySummary | null>(null);

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
      })
      .catch(() => setError("Nicht angemeldet"));
  }, []);

  useEffect(() => {
    if (!batchId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const next = await fetchBatchImportStatus(batchId);
        if (cancelled) return;
        setJob(next);
        if (["done", "partial", "failed", "cancelled"].includes(next.status)) return;
        timer = setTimeout(poll, 3000);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Status konnte nicht geladen werden");
        }
      }
    }

    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [batchId, pollRev]);

  useEffect(() => {
    if (!batchId || !job) return;
    const finishedUnits = job.units?.filter((u) => u.generate_status === "done").length ?? 0;
    if (finishedUnits === 0 && !["done", "partial", "failed", "cancelled"].includes(job.status)) return;
    let cancelled = false;
    fetchBatchImportQuality(batchId)
      .then((summary) => {
        if (!cancelled) setQuality(summary);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [batchId, job]);

  function toggleSelected(index: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  async function onRetry(indices: number[]) {
    if (!batchId || retrying || indices.length === 0) return;
    setRetrying(true);
    setError(null);
    try {
      const next = await retryBatchImportUnits(batchId, indices);
      setJob(next);
      setSelected(new Set());
      if (["queued", "running", "cancelling"].includes(next.status)) {
        setPollRev((value) => value + 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erneut starten fehlgeschlagen");
    } finally {
      setRetrying(false);
    }
  }

  async function onCancel() {
    if (!batchId || cancelling) return;
    if (!window.confirm("Batch abbrechen? Fertige Einheiten bleiben erhalten.")) return;
    setCancelling(true);
    setError(null);
    try {
      const next = await cancelBatchImport(batchId);
      setJob(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Abbruch fehlgeschlagen");
    } finally {
      setCancelling(false);
    }
  }

  async function onResume() {
    if (!batchId || resuming) return;
    setResuming(true);
    setError(null);
    try {
      const next = await resumeBatchImport(batchId);
      setJob(next);
      if (["queued", "running", "cancelling"].includes(next.status)) {
        setPollRev((value) => value + 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fortsetzen fehlgeschlagen");
    } finally {
      setResuming(false);
    }
  }

  const badge = job ? statusLabel(job.status) : null;
  const doneCount =
    job?.units?.filter((u) => u.generate_status === "done").length ?? 0;
  const total = job?.total ?? job?.units?.length ?? 0;
  const active = job && ["queued", "running", "cancelling"].includes(job.status);
  const canResume = job && batchImportCanResume(job);
  const retryableSelected = [...selected].filter((index) => {
    const row = job?.units?.[index];
    return row && job && batchImportRowCanRetry(job, row);
  });
  const qualityByIndex = new Map((quality?.rows ?? []).map((row) => [row.index, row.quality]));

  if (error && !user) {
    return (
      <main className="shell">
        <p>{error}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main className="shell shell-wide">
      <AppHeader user={user} title="Batch-Import" />
      <section className="card stack">
        <div className="section-head">
          <h1 style={{ margin: 0, fontSize: "1.15rem" }}>Fortschritt</h1>
          {badge && <span className={badge.className}>{badge.text}</span>}
        </div>
        {job ? (
          <>
            <div className="generate-progress-compact">
              <div
                className="generate-progress-bar"
                role="progressbar"
                aria-valuenow={job.progress_pct ?? 0}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={job.message || "Batch-Fortschritt"}
              >
                <div
                  className="generate-progress-fill"
                  style={{ width: `${Math.min(100, Math.max(0, job.progress_pct ?? 0))}%` }}
                />
              </div>
              <span className="muted generate-progress-label">
                {doneCount}/{total} Einheiten
                {typeof job.progress_pct === "number" ? ` (${job.progress_pct}%)` : ""}
                {job.message ? ` — ${job.message}` : ""}
              </span>
            </div>
            {job.error && <p className="err">{job.error}</p>}
            {error && <p className="err">{error}</p>}
            {active && (
              <p className="muted" style={{ margin: 0 }}>
                Tab offen lassen — Generierung läuft seriell im Hintergrund.
              </p>
            )}
            {canResume && (
              <p className="muted" style={{ margin: 0 }}>
                Fertige Einheiten bleiben erhalten — «Fortsetzen» startet nur fehlende und fehlerhafte Posten erneut
                (gleiche PDF, kein Wizard).
              </p>
            )}
          </>
        ) : (
          <p className="muted">Status wird geladen…</p>
        )}
        <div className="batch-wizard-actions">
          <Link className="btn ghost" href="/units">
            Zu den Einheiten
          </Link>
          {active && (
            <button type="button" className="btn ghost" disabled={cancelling} onClick={() => void onCancel()}>
              {cancelling ? "Abbruch…" : "Batch abbrechen"}
            </button>
          )}
          {canResume && (
            <button type="button" className="btn btn-primary" disabled={resuming} onClick={() => void onResume()}>
              {resuming ? "Startet…" : "Fortsetzen"}
            </button>
          )}
          {!active && retryableSelected.length > 0 && (
            <button
              type="button"
              className="btn"
              disabled={retrying}
              onClick={() => void onRetry(retryableSelected)}
            >
              {retrying ? "Startet…" : `Auswahl erneut (${retryableSelected.length})`}
            </button>
          )}
          <Link className="btn" href="/units/batch">
            Neuer Batch
          </Link>
        </div>
      </section>

      {job?.units && job.units.length > 0 && (
        <section className="card" style={{ padding: "0.75rem" }}>
          <ul className="unit-list batch-progress-list">
            {job.units.map((row, index) => {
              const rowBadge = statusLabel(row.generate_status || "pending");
              const canRetryRow = job && batchImportRowCanRetry(job, row);
              const q = qualityByIndex.get(index);
              return (
                <li key={`${index}-${row.title}`} className="unit-list-item card unit-list-card batch-progress-row">
                  <div className="unit-list-link">
                    <div className="unit-list-head">
                      {canRetryRow && (
                        <label style={{ display: "flex", alignItems: "center", marginRight: 8 }}>
                          <input
                            type="checkbox"
                            checked={selected.has(index)}
                            onChange={() => toggleSelected(index)}
                            aria-label={`Zeile ${index + 1} für Erneut-Start auswählen`}
                          />
                        </label>
                      )}
                      <span className="unit-list-title">
                        {index + 1}. {row.title}
                        {row.posten ? ` (Posten ${row.posten})` : ""}
                        {row.is_review ? " — Review" : ""}
                      </span>
                      <span className={rowBadge.className}>{unitStatusLabel(row.generate_status)}</span>
                    </div>
                    <p className="muted" style={{ margin: "0.35rem 0 0", fontSize: "0.9rem" }}>
                      PDF S. {row.page_from}–{row.page_to}
                      {q?.reference_code ? ` · Ref. ${q.reference_code}` : ""}
                      {q?.card_count != null && q?.question_count != null
                        ? ` · ${q.card_count}/${q.trainer_target_cards ?? "?"} Karten, ${q.question_count}/${q.trainer_target_questions ?? "?"} Quiz`
                        : ""}
                      {q?.pedagogy_level ? ` · Didaktik ${pedagogyLevelLabel(q.pedagogy_level)}` : ""}
                    </p>
                    {row.error && <p className="err" style={{ margin: "0.35rem 0 0" }}>{row.error}</p>}
                  </div>
                  <div className="unit-list-actions" style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                    {canRetryRow && (
                      <button
                        type="button"
                        className="btn ghost btn-sm"
                        disabled={retrying}
                        onClick={() => void onRetry([index])}
                      >
                        Erneut
                      </button>
                    )}
                    {row.unit_id && row.generate_status === "done" && (
                      <>
                        <Link className="btn btn-primary btn-sm" href={`/units/${row.unit_id}`}>
                          Öffnen
                        </Link>
                        <Link className="btn ghost btn-sm" href={`/units/${row.unit_id}#didaktik`}>
                          Didaktik
                        </Link>
                        {user?.is_admin && q?.report_ref && (
                          <Link
                            className="btn ghost btn-sm"
                            href={`/admin/unit-report?ref=${encodeURIComponent(q.report_ref)}`}
                          >
                            Report
                          </Link>
                        )}
                      </>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {quality && (quality.done ?? 0) > 0 && (
        <section className="card stack">
          <h2 style={{ margin: 0, fontSize: "1.05rem" }}>Qualitätsübersicht</h2>
          <p className="muted" style={{ margin: 0 }}>
            {quality.done}/{quality.total} fertig
            {(quality.failed ?? 0) > 0 ? ` · ${quality.failed} Fehler` : ""}
            {(quality.pending ?? 0) > 0 ? ` · ${quality.pending} wartend` : ""}
          </p>
          <div style={{ overflowX: "auto" }}>
            <table className="batch-quality-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Titel</th>
                  <th>Ref.</th>
                  <th>Karten</th>
                  <th>Quiz</th>
                  <th>Didaktik</th>
                </tr>
              </thead>
              <tbody>
                {(quality.rows ?? [])
                  .filter((row) => row.quality)
                  .map((row) => (
                    <tr key={row.index}>
                      <td>{row.index + 1}</td>
                      <td>{row.title}</td>
                      <td>{row.quality?.reference_code || "—"}</td>
                      <td>
                        {row.quality?.card_count}/{row.quality?.trainer_target_cards ?? "?"}
                      </td>
                      <td>
                        {row.quality?.question_count}/{row.quality?.trainer_target_questions ?? "?"}
                      </td>
                      <td>{pedagogyLevelLabel(row.quality?.pedagogy_level)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}
