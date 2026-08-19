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
      <p style={{ color: "var(--muted)", marginTop: 0 }}>
        Jede Einheit ist ein eigenes Gefäss: Inhalt und Dateien kannst du später löschen. Verlauf und
        Ergebnisse bleiben.
      </p>
      <p>
        <Link href="/units/new">+ Neue Einheit</Link>
      </p>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {units.map((u) => (
          <li
            key={u.id}
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "1rem",
              marginBottom: "0.75rem",
            }}
          >
            <strong>
              <Link href={`/units/${u.id}`} style={{ textDecoration: "none", color: "inherit" }}>
                {u.title}
              </Link>
            </strong>
            <p style={{ margin: "0.4rem 0 0", color: "var(--muted)", fontSize: "0.875rem" }}>
              {u.subject || "Thema offen"} · {u.language} · Stufe {u.difficulty} · {u.source_count}{" "}
              Quellen · {u.module_count} Blöcke
            </p>
            {u.brief && <p style={{ margin: "0.5rem 0 0" }}>{u.brief}</p>}
          </li>
        ))}
        {units.length === 0 && <p style={{ color: "var(--muted)" }}>Noch keine Einheiten.</p>}
      </ul>
    </main>
  );
}
