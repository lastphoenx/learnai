"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { fetchMe, fetchParentDashboard, type ChildDashboardStats, type User } from "@/lib/api";

export default function ParentDashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [children, setChildren] = useState<ChildDashboardStats[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.is_child) {
          setError("Nur für Eltern-Accounts");
          return;
        }
        return fetchParentDashboard().then((d) => setChildren(d.children));
      })
      .catch((e: Error) => setError(e.message));
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
    <main className="shell">
      <AppHeader user={user} title="Kinder-Übersicht" />
      <p className="muted">
        Lernfortschritt deiner Kinder — Einheiten, Quiz-Ergebnisse und letzte Aktivität.
      </p>
      {error && <p className="err">{error}</p>}

      {children.length === 0 ? (
        <p className="muted">
          Noch keine Kinder verknüpft. Unter{" "}
          <Link href="/settings">Einstellungen</Link> oder Admin → Benutzer kannst du Kind-Accounts
          anlegen.
        </p>
      ) : (
        <div className="stack">
          {children.map((child) => (
            <section key={child.user_id} className="card stack">
              <h2 style={{ margin: 0 }}>{child.display_name}</h2>
              <p className="muted" style={{ margin: 0 }}>
                {child.active_units} aktive Einheit{child.active_units !== 1 ? "en" : ""} ·{" "}
                {child.completed} abgeschlossen · {child.in_progress} in Bearbeitung
                {child.quiz_total > 0
                  ? ` · Quiz ${child.quiz_correct}/${child.quiz_total} (${child.quiz_percent}%)`
                  : ""}
              </p>
              {child.recent.length > 0 && (
                <ul className="list" style={{ margin: 0 }}>
                  {child.recent.map((r) => (
                    <li key={r.record_id} className="card" style={{ boxShadow: "none", padding: "0.75rem" }}>
                      <strong>{r.title}</strong>
                      <span className="muted" style={{ marginLeft: 8, fontSize: "0.85rem" }}>
                        {r.status === "completed"
                          ? "abgeschlossen"
                          : r.status === "in_progress"
                            ? "in Bearbeitung"
                            : "nicht gestartet"}
                        {r.quiz_total > 0 ? ` · Quiz ${r.quiz_correct}/${r.quiz_total}` : ""}
                      </span>
                      <p style={{ margin: "0.5rem 0 0", display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {r.unit_id && (
                          <>
                            <Link className="btn btn-primary" href={`/units/${r.unit_id}/learn`}>
                              {r.status === "in_progress" ? "Weiterlernen" : "Lernen"}
                            </Link>
                            <Link className="btn" href={`/units/${r.unit_id}`}>
                              Einheit
                            </Link>
                          </>
                        )}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
