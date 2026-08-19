"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { confirm2fa, fetchMe, setup2fa, type User } from "@/lib/api";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [secret, setSecret] = useState<string | null>(null);
  const [uri, setUri] = useState<string | null>(null);
  const [recovery, setRecovery] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch(() => setError("Nicht angemeldet"));
  }, []);

  async function onSetup(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await setup2fa(email, password);
      setSecret(res.secret);
      setUri(res.provisioning_uri);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Setup fehlgeschlagen");
    }
  }

  async function onConfirm(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await confirm2fa(code, email);
      setRecovery(res.recovery_codes);
      const me = await fetchMe();
      setUser(me);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bestätigung fehlgeschlagen");
    }
  }

  if (error && !user) {
    return (
      <main style={{ maxWidth: 640, margin: "3rem auto", padding: "0 1.5rem" }}>
        <p>{error}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 640, margin: "3rem auto", padding: "0 1.5rem" }}>
      <AppHeader user={user} title="Einstellungen" />
      {user?.must_enroll_2fa && (
        <p style={{ color: "#b45309" }}>
          Für diesen Account ist 2FA Pflicht. Bitte jetzt einrichten, danach geht es weiter.
        </p>
      )}
      <p>
        2FA: {user?.totp_enabled ? "aktiv" : "aus"} · Policy:{" "}
        {user?.totp_required ? "Pflicht" : "optional"}
      </p>
      {!user?.totp_enabled && (
        <>
          <form onSubmit={onSetup} style={{ display: "grid", gap: "0.75rem", marginTop: "1.5rem" }}>
            <label>
              E-Mail
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
              />
            </label>
            <label>
              Passwort
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
              />
            </label>
            <button type="submit">2FA starten</button>
          </form>
          {uri && (
            <section style={{ marginTop: "1.5rem" }}>
              <p>Secret in die Authenticator-App übernehmen:</p>
              <code style={{ display: "block", wordBreak: "break-all" }}>{secret}</code>
              <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>{uri}</p>
              <form onSubmit={onConfirm} style={{ display: "grid", gap: 8, marginTop: 12 }}>
                <input
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="123456"
                  required
                  style={{ padding: 8 }}
                />
                <button type="submit">Code bestätigen</button>
              </form>
            </section>
          )}
        </>
      )}
      {recovery && (
        <section style={{ marginTop: "1.5rem" }}>
          <p>Recovery-Codes – einmalig notieren und offline aufbewahren:</p>
          <ul>
            {recovery.map((c) => (
              <li key={c}>
                <code>{c}</code>
              </li>
            ))}
          </ul>
        </section>
      )}
      {error && <p style={{ color: "#ef4444" }}>{error}</p>}
    </main>
  );
}
