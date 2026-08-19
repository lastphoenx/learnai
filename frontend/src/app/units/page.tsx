"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { fetchMe, fetchUnits, type LearningUnit, type User } from "@/lib/api";

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
    <main className="shell">
      <AppHeader user={user} title="Lerneinheiten" />
      <div className="card stack">
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
          <ul className="list">
            {units.map((u) => (
              <li key={u.id} className="card" style={{ boxShadow: "none", padding: "1rem" }}>
                <strong>
                  <Link href={`/units/${u.id}`} style={{ textDecoration: "none", color: "inherit" }}>
                    {u.title}
                  </Link>
                </strong>
                <p className="muted" style={{ margin: "0.4rem 0 0", fontSize: "0.9rem" }}>
                  {u.subject || "Thema offen"} · {u.language} · Stufe {u.difficulty} · {u.source_count}{" "}
                  Quellen · {u.module_count} Blöcke
                </p>
                {u.brief && <p style={{ margin: "0.5rem 0 0" }}>{u.brief}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
