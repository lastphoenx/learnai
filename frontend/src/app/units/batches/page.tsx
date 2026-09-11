"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { fetchBatchImports, fetchMe, type BatchImportSummary, type User } from "@/lib/api";

function statusLabel(status?: string | null) {
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
    default:
      return { text: status || "—", className: "badge badge-neutral" };
  }
}

function formatWhen(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("de-CH", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function BatchHubPage() {
  const [user, setUser] = useState<User | null>(null);
  const [batches, setBatches] = useState<BatchImportSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
      })
      .catch(() => setError("Nicht angemeldet"));
    fetchBatchImports()
      .then((res) => setBatches(res.batches || []))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Batch-Liste konnte nicht geladen werden"),
      );
  }, []);

  const filtered = batches.filter((batch) => {
    const hay = `${batch.label || ""} ${batch.description || ""} ${batch.batch_id || ""} ${batch.subject || ""}`.toLowerCase();
    return hay.includes(query.trim().toLowerCase());
  });

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
      <AppHeader user={user} title="PDF-Batches" />
      <section className="card stack">
        <div className="section-head">
          <div>
            <h1 style={{ margin: 0, fontSize: "1.15rem" }}>Batch-Hub</h1>
            <p className="muted" style={{ margin: "0.35rem 0 0" }}>
              Alle PDF-Batch-Imports mit Posten-Liste und Sammel-Wartung — auch nach dem Import wieder auffindbar.
            </p>
          </div>
        </div>
        <div className="batch-wizard-actions">
          <Link className="btn btn-primary" href="/units/batch">
            Neuer Batch
          </Link>
          <Link className="btn ghost" href="/units">
            Alle Einheiten
          </Link>
        </div>
        <label className="stack" style={{ gap: "0.35rem" }}>
          <span className="muted">Suchen (Titel, Fach, Batch-ID)</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="z. B. NMG Schweizer Geschichte oder 3b6c2e13…"
          />
        </label>
        {error && user && <p className="err">{error}</p>}
      </section>

      <section className="card" style={{ padding: "0.75rem" }}>
        {filtered.length === 0 ? (
          <p className="muted" style={{ margin: 0 }}>
            {batches.length === 0
              ? "Noch keine Batches gespeichert. Starte einen PDF-Batch — er erscheint hier dauerhaft."
              : "Keine Treffer für die Suche."}
          </p>
        ) : (
          <ul className="unit-list">
            {filtered.map((batch) => {
              const badge = statusLabel(batch.status);
              return (
                <li key={batch.batch_id} className="unit-list-item card unit-list-card">
                  <Link href={`/units/batch/${batch.batch_id}`} className="unit-list-link">
                    <div className="unit-list-head">
                      <span className="unit-list-title">{batch.label || "Batch-Import"}</span>
                      <span className={badge.className}>{badge.text}</span>
                    </div>
                    <p className="muted" style={{ margin: "0.35rem 0 0", fontSize: "0.9rem" }}>
                      {batch.description || "—"}
                    </p>
                    <p className="muted" style={{ margin: "0.25rem 0 0", fontSize: "0.82rem" }}>
                      Batch-ID: <code>{batch.batch_id}</code>
                      {batch.updated_at ? ` · ${formatWhen(batch.updated_at)}` : ""}
                    </p>
                  </Link>
                  <div className="unit-list-actions">
                    <Link className="btn btn-primary btn-sm" href={`/units/batch/${batch.batch_id}`}>
                      Batch öffnen
                    </Link>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
