"use client";

import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main style={{ maxWidth: 640, margin: "4rem auto", padding: "0 1.5rem" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "2rem",
        }}
      >
        <h1 style={{ margin: 0, fontSize: "1.75rem" }}>LearnAI</h1>
        <ThemeToggle />
      </header>

      <section
        style={{
          background: "var(--card)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: "1.5rem",
        }}
      >
        <h2 style={{ marginTop: 0, fontSize: "1rem", color: "var(--muted)" }}>API-Status</h2>
        {error && <p style={{ color: "#ef4444" }}>Fehler: {error}</p>}
        {health && (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, lineHeight: 1.8 }}>
            <li>
              Status: <strong>{health.status}</strong>
            </li>
            <li>
              Tenant: <strong>{health.tenant}</strong>
            </li>
          </ul>
        )}
        {!health && !error && <p style={{ color: "var(--muted)" }}>Verbinde…</p>}
        <p style={{ marginTop: "1.5rem" }}>
          <a href="/login">Login</a> · <a href="/units">Lerneinheiten</a>
        </p>
      </section>
    </main>
  );
}
