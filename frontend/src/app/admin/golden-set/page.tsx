"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import {
  fetchMe,
  fetchPedagogyGoldenStatus,
  runPedagogyGoldenSuite,
  type PedagogyGoldenStatus,
  type User,
} from "@/lib/api";

export default function AdminGoldenSetPage() {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<PedagogyGoldenStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function reload() {
    const res = await fetchPedagogyGoldenStatus();
    setStatus(res);
  }

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (!u.is_admin) setError("Nur Admins");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Fehler"));
  }, []);

  useEffect(() => {
    if (!user?.is_admin) return;
    reload().catch((err) => setError(err instanceof Error ? err.message : "Fehler"));
  }, [user?.is_admin]);

  async function onRunSuite() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await runPedagogyGoldenSuite();
      setStatus(res);
      setMessage(res.ok ? "Alle Tests bestanden." : "Es gibt Fehler — Report unten kopieren und der KI geben.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suite fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onCopyReport() {
    if (!status?.report) return;
    try {
      await navigator.clipboard.writeText(status.report);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Kopieren fehlgeschlagen — Report manuell markieren.");
    }
  }

  if (error && !user) {
    return (
      <main className="shell">
        <AppHeader />
        <p className="err">{error}</p>
      </main>
    );
  }

  const coverage = status?.coverage;

  return (
    <main className="shell shell-wide admin-page">
      <AppHeader user={user} title="Golden Set" />
      {error && <p className="err">{error}</p>}
      {message && <p className={status?.ok ? "muted" : "err"}>{message}</p>}

      <section className="card unit-section">
        <h2>Pedagogy Golden Set</h2>
        <p className="muted section-lead">
          Automatische Qualitätsprüfung der Didaktik-Pipeline (JSON nach Vision). Fixtures liegen nur im Git —
          hier siehst du Ergebnisse und kannst den Report für die KI kopieren. Kein Bearbeiten nötig.
        </p>
        <div className="filter-row">
          <button type="button" className="btn-primary" onClick={onRunSuite} disabled={busy || !user?.is_admin}>
            {busy ? "Läuft…" : "Tests jetzt ausführen"}
          </button>
          {status?.report ? (
            <button type="button" className="btn" onClick={onCopyReport}>
              {copied ? "Kopiert" : "Report kopieren"}
            </button>
          ) : null}
        </div>
        {status && (
          <p className="muted">
            {status.passed}/{status.total} Fixtures OK
            {status.coverage_complete ? " · alle Fachgruppen abgedeckt" : " · Fachgruppen fehlen"}
          </p>
        )}
      </section>

      {coverage && (
        <section className="card unit-section">
          <h3>Fachgruppen-Abdeckung</h3>
          <ul className="admin-golden-coverage">
            {coverage.expected_groups.map((group) => {
              const covered = coverage.covered.find((row) => row.id === group.id);
              const missing = coverage.missing.some((row) => row.id === group.id);
              return (
                <li key={group.id} className="admin-golden-coverage-row">
                  <span className={`badge ${missing ? "badge-neutral" : "badge-ready"}`}>
                    {missing ? "fehlt" : "OK"}
                  </span>
                  <strong>{group.label}</strong>
                  <span className="muted">
                    {covered?.fixtures?.length
                      ? covered.fixtures.join(", ")
                      : "kein Fixture in backend/app/fixtures/pedagogy_golden/"}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <section className="card unit-section">
        <h3>Fixtures ({status?.fixtures.length ?? 0})</h3>
        <ul className="admin-golden-list">
          {(status?.fixtures || []).map((row) => (
            <li key={row.name} className="admin-golden-result-row">
              <div className="admin-golden-result-head">
                <strong>{row.name}</strong>
                <span className={`badge ${row.ok ? "badge-ready" : "badge-neutral"}`}>
                  {row.ok ? "OK" : "Fehler"}
                </span>
              </div>
              <p className="muted admin-golden-result-meta">
                {row.subject_group_label || row.subject_group || "—"}
                {row.subject_hint ? ` · ${row.subject_hint}` : ""}
                {row.method_count != null ? ` · ${row.method_count} Strategien` : ""}
              </p>
              {row.error ? <p className="err admin-golden-result-error">{row.error}</p> : null}
            </li>
          ))}
        </ul>
      </section>

      {status?.report && (
        <section className="card unit-section">
          <h3>Report (für KI)</h3>
          <pre className="admin-golden-report">{status.report}</pre>
        </section>
      )}

      <p className="muted">
        <Link href="/admin/users">← Benutzer-Verwaltung</Link>
      </p>
    </main>
  );
}
