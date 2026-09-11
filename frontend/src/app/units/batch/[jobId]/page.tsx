"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import {
  batchImportCanResume,
  batchImportNeedsDraftLink,
  batchImportRowCanRepair,
  batchImportRowCanRetry,
  batchImportRowHasDraft,
  cancelBatchImport,
  fetchBatchImportQuality,
  fetchBatchImportStatus,
  fetchBatchMaintenanceStatus,
  fetchMe,
  linkBatchImportDrafts,
  rederiveBatchPractice,
  repairBatchImportUnits,
  resumeBatchImport,
  retryBatchImportUnits,
  type BatchImportJob,
  type BatchImportQualitySummary,
  type BatchMaintenanceStatus,
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
    case "repair_pending":
      return "Reparatur…";
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
  const [repairing, setRepairing] = useState(false);
  const [linkingDrafts, setLinkingDrafts] = useState(false);
  const [pollRev, setPollRev] = useState(0);
  const [selected, setSelected] = useState<Set<number>>(() => new Set());
  const [quality, setQuality] = useState<BatchImportQualitySummary | null>(null);
  const [maintenance, setMaintenance] = useState<BatchMaintenanceStatus | null>(null);
  const [rederiving, setRederiving] = useState(false);
  const [maintSelected, setMaintSelected] = useState<Set<number>>(() => new Set());

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

  useEffect(() => {
    if (!batchId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function pollMaintenance() {
      try {
        const next = await fetchBatchMaintenanceStatus(batchId);
        if (cancelled) return;
        setMaintenance(next.status === "idle" ? null : next);
        if (next.status === "running" || next.status === "queued") {
          timer = setTimeout(pollMaintenance, 3000);
        }
      } catch {
        if (!cancelled) setMaintenance(null);
      }
    }

    void pollMaintenance();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [batchId, pollRev, rederiving]);

  function toggleMaintSelected(index: number) {
    setMaintSelected((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  async function onRederivePractice(indices?: number[]) {
    if (!batchId || rederiving) return;
    const count =
      indices?.length ??
      (job?.units || []).filter((row) => row.generate_status === "done" && row.unit_id).length;
    if (
      !window.confirm(
        `Übungsaufgaben für ${count} Einheit(en) neu ableiten? Pro Modul wird Basiswissen aktualisiert (KI, einige Minuten).`,
      )
    ) {
      return;
    }
    setRederiving(true);
    setError(null);
    try {
      await rederiveBatchPractice(batchId, indices);
      setPollRev((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Übungsaufgaben neu ableiten fehlgeschlagen");
    } finally {
      setRederiving(false);
    }
  }

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

  async function onLinkDrafts() {
    if (!batchId || linkingDrafts) return;
    setLinkingDrafts(true);
    setError(null);
    try {
      const result = await linkBatchImportDrafts(batchId);
      setJob(result.job);
      if (result.linked <= 0) {
        setError("Keine passenden Entwürfe gefunden — ggf. «Neu generieren».");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Entwürfe verknüpfen fehlgeschlagen");
    } finally {
      setLinkingDrafts(false);
    }
  }

  async function onRepair(indices: number[]) {
    if (!batchId || repairing || indices.length === 0) return;
    setRepairing(true);
    setError(null);
    try {
      const next = await repairBatchImportUnits(batchId, indices);
      setJob(next);
      setSelected(new Set());
      if (["queued", "running", "cancelling"].includes(next.status)) {
        setPollRev((value) => value + 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reparatur fehlgeschlagen");
    } finally {
      setRepairing(false);
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
  const repairableSelected = [...selected].filter((index) => {
    const row = job?.units?.[index];
    return row && batchImportRowCanRepair(row);
  });
  const doneMaintIndices = (job?.units || [])
    .map((row, index) => ({ row, index }))
    .filter(({ row }) => row.generate_status === "done" && row.unit_id)
    .map(({ index }) => index);
  const maintSelectedDone = [...maintSelected].filter((index) => doneMaintIndices.includes(index));
  const qualityByIndex = new Map((quality?.rows ?? []).map((row) => [row.index, row.quality]));

  const needsDraftLink = job && batchImportNeedsDraftLink(job);

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
      <AppHeader user={user} title="Batch-Hub" />
      <section className="card stack">
        <div className="section-head">
          <div>
            <h1 style={{ margin: 0, fontSize: "1.15rem" }}>{job?.label || "Batch-Import"}</h1>
            {job?.description && (
              <p className="muted" style={{ margin: "0.35rem 0 0" }}>
                {job.description}
              </p>
            )}
            <p className="muted" style={{ margin: "0.25rem 0 0", fontSize: "0.82rem" }}>
              Batch-ID: <code>{batchId}</code>
              {job?.from_manifest ? " · aus Archiv (Redis abgelaufen)" : ""}
            </p>
          </div>
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
          <Link className="btn ghost" href="/units/batches">
            Alle Batches
          </Link>
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
          {!active && needsDraftLink && (
            <button
              type="button"
              className="btn btn-primary"
              disabled={linkingDrafts}
              onClick={() => void onLinkDrafts()}
            >
              {linkingDrafts ? "Verknüpft…" : "Entwürfe verknüpfen"}
            </button>
          )}
          {!active && retryableSelected.length > 0 && (
            <button
              type="button"
              className="btn"
              disabled={retrying || repairing}
              onClick={() => void onRetry(retryableSelected)}
            >
              {retrying ? "Startet…" : `Neu generieren (${retryableSelected.length})`}
            </button>
          )}
          {!active && repairableSelected.length > 0 && (
            <button
              type="button"
              className="btn btn-primary"
              disabled={repairing || retrying}
              onClick={() => void onRepair(repairableSelected)}
            >
              {repairing ? "Repariert…" : `Reparieren (${repairableSelected.length})`}
            </button>
          )}
          <Link className="btn" href="/units/batch">
            Neuer Batch
          </Link>
        </div>
      </section>

      {job && doneMaintIndices.length > 0 && !active && (
        <section className="card stack">
          <h2 style={{ margin: 0, fontSize: "1.05rem" }}>Batch-Wartung</h2>
          <p className="muted" style={{ margin: 0 }}>
            Sammelaktionen für fertige Posten — ohne jeden Posten einzeln in der Einheit zu öffnen.
          </p>
          {maintenance && maintenance.status !== "idle" && (
            <div className="generate-progress-compact">
              <div className="generate-progress-bar" role="progressbar" aria-valuenow={maintenance.current ?? 0}>
                <div
                  className="generate-progress-fill"
                  style={{
                    width: `${
                      maintenance.total && maintenance.current
                        ? Math.min(100, Math.round((100 * maintenance.current) / maintenance.total))
                        : maintenance.status === "running"
                          ? 12
                          : 100
                    }%`,
                  }}
                />
              </div>
              <span className="muted generate-progress-label">
                {maintenance.message ||
                  (maintenance.status === "running"
                    ? `${maintenance.current ?? 0}/${maintenance.total ?? "?"}`
                    : maintenance.status)}
              </span>
            </div>
          )}
          {maintenance?.results && maintenance.results.length > 0 && maintenance.status !== "running" && (
            <ul className="muted" style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.9rem" }}>
              {maintenance.results
                .filter((row) => !row.ok)
                .slice(0, 8)
                .map((row) => (
                  <li key={`${row.index}-${row.unit_id}`}>
                    {row.title || row.unit_id}: {row.error || "Fehler"}
                  </li>
                ))}
            </ul>
          )}
          <div className="batch-wizard-actions">
            <button
              type="button"
              className="btn btn-primary"
              disabled={rederiving || maintenance?.status === "running"}
              onClick={() => void onRederivePractice()}
            >
              {rederiving || maintenance?.status === "running"
                ? "Läuft…"
                : `Übungsaufgaben neu ableiten (${doneMaintIndices.length})`}
            </button>
            {maintSelectedDone.length > 0 && (
              <button
                type="button"
                className="btn"
                disabled={rederiving || maintenance?.status === "running"}
                onClick={() => void onRederivePractice(maintSelectedDone)}
              >
                Auswahl ({maintSelectedDone.length})
              </button>
            )}
          </div>
        </section>
      )}

      {job?.units && job.units.length > 0 && (
        <section className="card" style={{ padding: "0.75rem" }}>
          <ul className="unit-list batch-progress-list">
            {job.units.map((row, index) => {
              const rowBadge = statusLabel(row.generate_status || "pending");
              const canRetryRow = job && batchImportRowCanRetry(job, row);
              const canRepairRow = batchImportRowCanRepair(row);
              const hasDraft = batchImportRowHasDraft(row);
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
                      {row.generate_status === "done" && row.unit_id && !active && (
                        <label style={{ display: "flex", alignItems: "center", marginRight: 8 }}>
                          <input
                            type="checkbox"
                            checked={maintSelected.has(index)}
                            onChange={() => toggleMaintSelected(index)}
                            aria-label={`Posten ${index + 1} für Wartung auswählen`}
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
                    {hasDraft && (
                      <Link className="btn ghost btn-sm" href={`/units/${row.unit_id}`}>
                        Entwurf öffnen
                      </Link>
                    )}
                    {canRepairRow && (
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        disabled={repairing || retrying}
                        onClick={() => void onRepair([index])}
                      >
                        Reparieren
                      </button>
                    )}
                    {canRetryRow && (
                      <button
                        type="button"
                        className="btn ghost btn-sm"
                        disabled={retrying || repairing}
                        onClick={() => void onRetry([index])}
                        title="Vision und alle Bereiche neu generieren"
                      >
                        Neu generieren
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
