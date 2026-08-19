"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return (
    <main className="shell">
      <header className="app-header">
        <div>
          <p className="hero-kicker">Self-hosted</p>
          <h1 className="brand">LearnAI</h1>
        </div>
        <ThemeToggle />
      </header>

      <section className="card stack">
        <h2>Lernplattform hinter deiner eigenen Tür</h2>
        <p className="muted">
          Lerneinheiten aus deinen Unterlagen, Verlauf bleibt — auch wenn eine Einheit gelöscht
          wird. Login und 2FA laufen in der App, nicht über Authentik.
        </p>
        <p>
          <Link className="btn btn-primary" href="/login">
            Anmelden
          </Link>
          {"  "}
          <Link href="/units">Zu den Einheiten</Link>
        </p>
        <p className="muted">
          API: {health ? health.status : "…"} · Mandant {health?.tenant ?? "—"}
        </p>
      </section>
    </main>
  );
}
