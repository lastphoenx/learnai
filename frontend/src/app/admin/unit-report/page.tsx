"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { fetchMe, fetchUnitQualityReport, type UnitQualityReport, type User } from "@/lib/api";

export default function AdminUnitReportPage() {
  const [user, setUser] = useState<User | null>(null);
  const [ref, setRef] = useState("");
  const [result, setResult] = useState<UnitQualityReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (!u.is_admin) setError("Nur Admins");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Fehler"));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const code = ref.trim();
    if (!code) return;
    setBusy(true);
    setError(null);
    setCopied(false);
    try {
      const res = await fetchUnitQualityReport(code);
      setResult(res);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Report fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onCopy() {
    if (!result?.report) return;
    await navigator.clipboard.writeText(result.report);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <main className="shell shell-wide admin-page">
      <AppHeader user={user} title="Qualitätsreport" />
      {error && <p className="err">{error}</p>}

      <section className="card unit-section">
        <h2>Lerneinheit per Referenz</h2>
        <p className="muted section-lead">
          <strong>0001</strong> = ganze Einheits-Familie (Quiz/Lösungsvarianten der Vorlage).
          <br />
          <strong>0001.0001</strong> = eine Instanz (z. B. Giulia) inkl. Lernfortschritt.
          <br />
          Den Report kopieren und der KI zur Analyse geben.
        </p>
        <form className="inline-form" onSubmit={onSubmit}>
          <input
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            placeholder="0001 oder 0001.0001"
            pattern="\d{4}(\.\d{4})?"
            disabled={!user?.is_admin || busy}
            required
          />
          <button type="submit" className="btn-primary" disabled={!user?.is_admin || busy}>
            {busy ? "Erstelle…" : "Report erstellen"}
          </button>
        </form>
        <p className="muted empty-hint">
          CLI auf dem Server:{" "}
          <code>docker compose exec -T api python /opt/scripts/unit_quality_report.py 0001.0001</code>
        </p>
      </section>

      {result && (
        <section className="card unit-section">
          <div className="filter-row">
            <h3 style={{ margin: 0 }}>
              Report — {result.ref}
              <span className="muted" style={{ fontWeight: 400, marginLeft: "0.5rem" }}>
                ({result.scope === "instance" ? "Instanz" : "Familie"} · {result.unit_count} Einheit
                {result.unit_count === 1 ? "" : "en"})
              </span>
            </h3>
            <button type="button" className="btn" onClick={onCopy}>
              {copied ? "Kopiert" : "Report kopieren"}
            </button>
          </div>
          <pre className="admin-golden-report">{result.report}</pre>
        </section>
      )}

      <p className="muted">
        <Link href="/admin/golden-set">Golden Set</Link>
        {" · "}
        <Link href="/admin/users">Benutzer</Link>
      </p>
    </main>
  );
}
