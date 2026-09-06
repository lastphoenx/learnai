"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import {
  fetchAdminAiOverview,
  fetchMe,
  type AdminAiOverviewUnit,
  type User,
} from "@/lib/api";
import { aiSourceBadgeClass, formatAiTasksCompact, providerLabel } from "@/lib/unitAiTasks";

function formatCurrentAi(row: AdminAiOverviewUnit): string {
  const bits = Object.entries(row.current_ai || {}).map(([key, task]) => {
    const prov = task.provider ? providerLabel(task.provider) : "—";
    const model = task.model || "(auto)";
    return `${key}: ${prov} ${model}`;
  });
  return bits.length ? bits.join(" · ") : "—";
}

function formatWhen(iso: string | undefined): string | null {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function AdminAiOverviewPage() {
  const [user, setUser] = useState<User | null>(null);
  const [rows, setRows] = useState<AdminAiOverviewUnit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (!u.is_admin) {
          setError("Nur Admins");
          setBusy(false);
          return;
        }
        return fetchAdminAiOverview();
      })
      .then((data) => {
        if (data) setRows(data.units || []);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Fehler"))
      .finally(() => setBusy(false));
  }, []);

  const sorted = useMemo(
    () => [...rows].sort((a, b) => (a.reference_code || "").localeCompare(b.reference_code || "")),
    [rows],
  );

  return (
    <main className="shell shell-wide admin-page">
      <AppHeader user={user} title="KI-Übersicht" />
      {error && <p className="err">{error}</p>}

      <section className="card unit-section">
        <h2>Lerneinheiten — aktuelle &amp; zuletzt genutzte KI</h2>
        <p className="muted section-lead">
          Pro Einheit: effektive Generierungs-Modelle (Profil/Vererbung) und der Snapshot des letzten
          Aufbereitens. Detail pro Referenz im{" "}
          <Link href="/admin/unit-report">Qualitätsreport</Link>.
        </p>
        {busy ? (
          <p className="muted">Lade…</p>
        ) : sorted.length === 0 ? (
          <p className="muted empty-hint">Keine Einheiten gefunden.</p>
        ) : (
          <div className="admin-ai-table-wrap">
            <table className="admin-ai-table">
              <thead>
                <tr>
                  <th>Ref</th>
                  <th>Titel</th>
                  <th>Lerner</th>
                  <th>Status</th>
                  <th>Aktuelle KI</th>
                  <th>Zuletzt generiert</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((row) => {
                  const lastWhen = formatWhen(row.last_ai_run?.finished_at);
                  const primary = Object.values(row.current_ai || {})[0];
                  return (
                    <tr key={row.unit_id}>
                      <td>
                        <code>{row.reference_code || "—"}</code>
                      </td>
                      <td>{row.title}</td>
                      <td>{row.learner}</td>
                      <td>
                        {row.status}
                        {row.module_count > 0 ? ` · ${row.module_count} Mod.` : ""}
                      </td>
                      <td className="admin-ai-models">
                        {formatCurrentAi(row)}
                        {primary?.source ? (
                          <span
                            className={`unit-ai-source-badge ${aiSourceBadgeClass(primary.source)}`}
                            style={{ marginLeft: "0.35rem" }}
                          >
                            {primary.source_label || primary.source}
                          </span>
                        ) : null}
                      </td>
                      <td className="admin-ai-models">
                        {lastWhen ? (
                          <>
                            <span className="muted">{lastWhen}</span>
                            {row.last_ai_summary ? (
                              <>
                                <br />
                                {formatAiTasksCompact(row.last_ai_run?.tasks || null) ||
                                  row.last_ai_summary}
                              </>
                            ) : null}
                          </>
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                      <td>
                        <Link href={`/units/${row.unit_id}`}>Einheit</Link>
                        {row.reference_code ? (
                          <>
                            {" · "}
                            <Link href={`/admin/unit-report?ref=${encodeURIComponent(row.reference_code)}`}>
                              Report
                            </Link>
                          </>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="muted">
        <Link href="/admin/unit-report">Qualitätsreport</Link>
        {" · "}
        <Link href="/admin/users">Benutzer</Link>
        {" · "}
        <Link href="/admin/golden-set">Golden Set</Link>
      </p>
    </main>
  );
}
