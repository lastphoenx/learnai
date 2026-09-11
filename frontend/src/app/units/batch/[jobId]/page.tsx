"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import {
  batchImportCanResume,
  cancelBatchImport,
  fetchBatchImportStatus,
  fetchMe,
  resumeBatchImport,
  type BatchImportJob,
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

export default function BatchImportProgressPage() {
  const params = useParams();
  const batchId = String(params.jobId || "");
  const [user, setUser] = useState<User | null>(null);
  const [job, setJob] = useState<BatchImportJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [pollRev, setPollRev] = useState(0);

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
              return (
                <li key={`${index}-${row.title}`} className="unit-list-item card unit-list-card batch-progress-row">
                  <div className="unit-list-link">
                    <div className="unit-list-head">
                      <span className="unit-list-title">
                        {index + 1}. {row.title}
                        {row.posten ? ` (Posten ${row.posten})` : ""}
                        {row.is_review ? " — Review" : ""}
                      </span>
                      <span className={rowBadge.className}>{unitStatusLabel(row.generate_status)}</span>
                    </div>
                    <p className="muted" style={{ margin: "0.35rem 0 0", fontSize: "0.9rem" }}>
                      PDF S. {row.page_from}–{row.page_to}
                    </p>
                    {row.error && <p className="err" style={{ margin: "0.35rem 0 0" }}>{row.error}</p>}
                  </div>
                  {row.unit_id && row.generate_status === "done" && (
                    <div className="unit-list-actions">
                      <Link className="btn btn-primary" href={`/units/${row.unit_id}`}>
                        Öffnen
                      </Link>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </main>
  );
}
