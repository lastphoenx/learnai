"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { fetchMe, fetchRecords, rebuildFromRecord, type LearningRecord, type User } from "@/lib/api";

export default function HistoryPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [records, setRecords] = useState<LearningRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
      })
      .catch(() => setError("Nicht angemeldet"));
    fetchRecords()
      .then(setRecords)
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
      <AppHeader user={user} title="Lernverlauf" />
      <p style={{ color: "var(--muted)" }}>
        Was du schon gemacht hast, bleibt – auch wenn die Einheit selbst gelöscht wurde.
      </p>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {records.map((r) => (
          <li
            key={r.id}
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "1rem",
              marginBottom: "0.75rem",
            }}
          >
            <strong>{r.title}</strong>
            <span style={{ marginLeft: 8, color: "var(--muted)", fontSize: "0.85rem" }}>
              {r.unit_alive ? "Einheit aktiv" : "Einheit gelöscht"}
            </span>
            <p style={{ margin: "0.4rem 0 0", color: "var(--muted)", fontSize: "0.875rem" }}>
              {r.subject || "–"} · {r.language} · Stufe {r.difficulty}
            </p>
            {r.summary && <p style={{ margin: "0.5rem 0 0" }}>{r.summary}</p>}
            <p style={{ margin: "0.75rem 0 0" }}>
              {r.unit_alive && r.unit_id ? (
                <Link href={`/units/${r.unit_id}`}>Öffnen</Link>
              ) : (
                <button
                  type="button"
                  onClick={async () => {
                    const nextDiff = Math.min(5, (r.difficulty || 1) + 1);
                    const unit = await rebuildFromRecord(r.id, nextDiff);
                    router.push(`/units/${unit.id}`);
                  }}
                >
                  Ähnliche Einheit, eine Stufe schwerer
                </button>
              )}
            </p>
          </li>
        ))}
        {records.length === 0 && <p style={{ color: "var(--muted)" }}>Noch kein Verlauf.</p>}
      </ul>
    </main>
  );
}
