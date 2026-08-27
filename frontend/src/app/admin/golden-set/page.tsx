"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import {
  fetchMe,
  fetchPedagogyGoldenStatus,
  fetchTaskTypeGoldenStatus,
  runPedagogyGoldenSuite,
  runTaskTypeGoldenSuite,
  type PedagogyGoldenStatus,
  type TaskTypeGoldenStatus,
  type User,
} from "@/lib/api";

type GoldenSuiteProps<T extends { ok: boolean; report: string; passed: number; total: number; coverage_complete: boolean }> = {
  title: string;
  lead: string;
  coverageTitle: string;
  coverageRows: { id: string; label: string; ok: boolean; detail: string }[];
  fixtures: { name: string; ok: boolean; meta: string; error?: string }[];
  status: T | null;
  busy: boolean;
  onRun: () => void;
  report: string | null;
  onCopy: () => void;
  copied: boolean;
};

function GoldenSuiteSection<T extends { ok: boolean; report: string; passed: number; total: number; coverage_complete: boolean }>({
  title,
  lead,
  coverageTitle,
  coverageRows,
  fixtures,
  status,
  busy,
  onRun,
  report,
  onCopy,
  copied,
}: GoldenSuiteProps<T>) {
  return (
    <>
      <section className="card unit-section">
        <h2>{title}</h2>
        <p className="muted section-lead">{lead}</p>
        <div className="filter-row">
          <button type="button" className="btn-primary" onClick={onRun} disabled={busy}>
            {busy ? "Läuft…" : "Tests jetzt ausführen"}
          </button>
          {report ? (
            <button type="button" className="btn" onClick={onCopy}>
              {copied ? "Kopiert" : "Report kopieren"}
            </button>
          ) : null}
        </div>
        {status && (
          <p className="muted">
            {status.passed}/{status.total} Fixtures OK
            {status.coverage_complete ? " · alle Gruppen abgedeckt" : " · Abdeckung unvollständig"}
          </p>
        )}
      </section>

      <section className="card unit-section">
        <h3>{coverageTitle}</h3>
        <ul className="admin-golden-coverage">
          {coverageRows.map((row) => (
            <li key={row.id} className="admin-golden-coverage-row">
              <span className={`badge ${row.ok ? "badge-ready" : "badge-neutral"}`}>{row.ok ? "OK" : "fehlt"}</span>
              <strong>{row.label}</strong>
              <span className="muted">{row.detail}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card unit-section">
        <h3>Fixtures ({fixtures.length})</h3>
        <ul className="admin-golden-list">
          {fixtures.map((row) => (
            <li key={row.name} className="admin-golden-result-row">
              <div className="admin-golden-result-head">
                <strong>{row.name}</strong>
                <span className={`badge ${row.ok ? "badge-ready" : "badge-neutral"}`}>{row.ok ? "OK" : "Fehler"}</span>
              </div>
              <p className="muted admin-golden-result-meta">{row.meta}</p>
              {row.error ? <p className="err admin-golden-result-error">{row.error}</p> : null}
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

export default function AdminGoldenSetPage() {
  const [user, setUser] = useState<User | null>(null);
  const [pedagogyStatus, setPedagogyStatus] = useState<PedagogyGoldenStatus | null>(null);
  const [taskTypeStatus, setTaskTypeStatus] = useState<TaskTypeGoldenStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busyPedagogy, setBusyPedagogy] = useState(false);
  const [busyTaskType, setBusyTaskType] = useState(false);
  const [copiedReport, setCopiedReport] = useState<string | null>(null);

  async function reload() {
    const [pedagogy, taskType] = await Promise.all([
      fetchPedagogyGoldenStatus(),
      fetchTaskTypeGoldenStatus(),
    ]);
    setPedagogyStatus(pedagogy);
    setTaskTypeStatus(taskType);
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

  async function onRunPedagogy() {
    setBusyPedagogy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await runPedagogyGoldenSuite();
      setPedagogyStatus(res);
      setMessage(res.ok ? "Pedagogy-Set: alle Tests bestanden." : "Pedagogy-Set: Fehler — Report kopieren.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suite fehlgeschlagen");
    } finally {
      setBusyPedagogy(false);
    }
  }

  async function onRunTaskType() {
    setBusyTaskType(true);
    setError(null);
    setMessage(null);
    try {
      const res = await runTaskTypeGoldenSuite();
      setTaskTypeStatus(res);
      setMessage(res.ok ? "Aufgabentyp-Set: alle Tests bestanden." : "Aufgabentyp-Set: Fehler — Report kopieren.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suite fehlgeschlagen");
    } finally {
      setBusyTaskType(false);
    }
  }

  async function onCopyReport(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedReport(text);
      window.setTimeout(() => setCopiedReport(null), 2000);
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

  const pedagogyCoverage = pedagogyStatus?.coverage;
  const taskTypeCoverage = taskTypeStatus?.coverage;

  return (
    <main className="shell shell-wide admin-page">
      <AppHeader user={user} title="Golden Set" />
      {error && <p className="err">{error}</p>}
      {message && <p className="muted">{message}</p>}

      <GoldenSuiteSection
        title="Pedagogy Golden Set"
        lead="Didaktik-Pipeline (JSON nach Vision). Fixtures nur im Git — Ergebnis lesen, Report für die KI kopieren."
        coverageTitle="Fachgruppen-Abdeckung"
        coverageRows={(pedagogyCoverage?.expected_groups || []).map((group) => {
          const covered = pedagogyCoverage?.covered.find((row) => row.id === group.id);
          const missing = pedagogyCoverage?.missing.some((row) => row.id === group.id);
          return {
            id: group.id,
            label: group.label,
            ok: !missing,
            detail: covered?.fixtures?.length
              ? covered.fixtures.join(", ")
              : "kein Fixture in backend/app/fixtures/pedagogy_golden/",
          };
        })}
        fixtures={(pedagogyStatus?.fixtures || []).map((row) => ({
          name: row.name,
          ok: !!row.ok,
          meta: [
            row.subject_group_label || row.subject_group || "—",
            row.subject_hint || "",
            row.method_count != null ? `${row.method_count} Strategien` : "",
          ]
            .filter(Boolean)
            .join(" · "),
          error: row.error,
        }))}
        status={pedagogyStatus}
        busy={busyPedagogy || !user?.is_admin}
        onRun={onRunPedagogy}
        report={pedagogyStatus?.report || null}
        onCopy={() => pedagogyStatus?.report && onCopyReport(pedagogyStatus.report)}
        copied={copiedReport === pedagogyStatus?.report}
      />

      <GoldenSuiteSection
        title="Aufgabentyp Golden Set"
        lead="Generierte Lerneinheiten (modules-JSON pro Aufgabentyp). Prüft Struktur und Qualitätsregeln — keine Live-KI-Regression."
        coverageTitle="Aufgabentyp-Abdeckung"
        coverageRows={(taskTypeCoverage?.expected_types || []).map((group) => {
          const covered = taskTypeCoverage?.covered.find((row) => row.id === group.id);
          const missing = taskTypeCoverage?.missing.some((row) => row.id === group.id);
          return {
            id: group.id,
            label: group.label,
            ok: !missing,
            detail: covered?.fixtures?.length
              ? covered.fixtures.join(", ")
              : "kein Fixture in backend/app/fixtures/task_type_golden/",
          };
        })}
        fixtures={(taskTypeStatus?.fixtures || []).map((row) => ({
          name: row.name,
          ok: !!row.ok,
          meta: [
            row.task_type_label || row.task_type || "—",
            row.subject_hint || "",
            row.module_count != null ? `${row.module_count} Module` : "",
            row.question_count != null ? `${row.question_count} Fragen` : "",
          ]
            .filter(Boolean)
            .join(" · "),
          error: row.error,
        }))}
        status={taskTypeStatus}
        busy={busyTaskType || !user?.is_admin}
        onRun={onRunTaskType}
        report={taskTypeStatus?.report || null}
        onCopy={() => taskTypeStatus?.report && onCopyReport(taskTypeStatus.report)}
        copied={copiedReport === taskTypeStatus?.report}
      />

      {(pedagogyStatus?.report || taskTypeStatus?.report) && (
        <section className="card unit-section">
          <h3>Reports (für KI)</h3>
          {pedagogyStatus?.report ? (
            <>
              <h4>Pedagogy</h4>
              <pre className="admin-golden-report">{pedagogyStatus.report}</pre>
            </>
          ) : null}
          {taskTypeStatus?.report ? (
            <>
              <h4>Aufgabentypen</h4>
              <pre className="admin-golden-report">{taskTypeStatus.report}</pre>
            </>
          ) : null}
        </section>
      )}

      <p className="muted">
        <Link href="/admin/users">← Benutzer-Verwaltung</Link>
      </p>
    </main>
  );
}
