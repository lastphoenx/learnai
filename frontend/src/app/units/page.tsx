"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { fetchMe, fetchUnits, type LearningUnit, type User } from "@/lib/api";
import { languageLabel, taskTypeLabel } from "@/lib/taskTypes";

function statusBadge(status: string) {
  if (status === "ready") return { label: "Bereit", className: "badge badge-ready" };
  if (status === "draft") return { label: "Entwurf", className: "badge badge-draft" };
  return { label: status, className: "badge badge-neutral" };
}

export default function UnitsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [units, setUnits] = useState<LearningUnit[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
      })
      .catch(() => setError("Nicht angemeldet"));
    fetchUnits()
      .then(setUnits)
      .catch(() => {});
  }, []);

  if (error && !user) {
    return (
      <main className="shell">
        <p>{error}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main className="shell shell-wide unit-page">
      <AppHeader user={user} title="Lerneinheiten" />
      <section className="card stack">
        <p className="muted" style={{ margin: 0 }}>
          Jede Einheit ist ein eigenes Gefäss: Inhalt und Dateien kannst du später löschen. Verlauf
          und Ergebnisse bleiben.
        </p>
        <p>
          <Link className="btn btn-primary" href="/units/new">
            Neue Einheit
          </Link>
        </p>
        {units.length === 0 ? (
          <p className="muted">Noch keine Einheiten — starte mit der ersten aus deinen Unterlagen.</p>
        ) : (
          <ul className="unit-list">
            {units.map((u) => {
              const badge = statusBadge(u.status);
              return (
                <li key={u.id} className="unit-list-item card">
                  <div className="unit-list-head">
                    <Link href={`/units/${u.id}`} className="unit-list-title">
                      {u.title}
                    </Link>
                    <span className={badge.className}>{badge.label}</span>
                  </div>
                  <div className="badge-row" style={{ marginTop: "0.55rem" }}>
                    {u.learner_name && <span className="badge badge-neutral">{u.learner_name}</span>}
                    <span className="badge badge-subject">{u.subject || "Ohne Fach"}</span>
                    <span className="badge badge-mode">{taskTypeLabel(u.task_type || "mixed")}</span>
                    <span className="badge badge-neutral">{languageLabel(u.language)}</span>
                    <span className="badge badge-neutral">Stufe {u.difficulty}</span>
                    <span className="badge badge-neutral">{u.source_count} Quellen</span>
                    <span className="badge badge-neutral">{u.module_count} Blöcke</span>
                    {u.learn_progress?.status === "completed" && (
                      <span className="badge badge-ready">Abgeschlossen</span>
                    )}
                    {u.learn_progress?.status === "in_progress" && u.learn_progress.percent > 0 && (
                      <span className="badge badge-neutral">{u.learn_progress.percent}% gelernt</span>
                    )}
                  </div>
                  {u.brief && <p className="unit-list-brief">{u.brief}</p>}
                  {u.module_count > 0 && (
                    <div className="unit-list-actions">
                      <Link className="btn btn-primary" href={`/units/${u.id}/learn`}>
                        {u.learn_progress?.status === "in_progress"
                          ? "Weiterlernen"
                          : u.learn_progress?.status === "completed"
                            ? "Nochmal"
                            : "Lernen"}
                      </Link>
                      <Link className="btn ghost" href={`/units/${u.id}`}>
                        Bearbeiten
                      </Link>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
