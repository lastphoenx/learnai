"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { login, verify2fa } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [needs2fa, setNeeds2fa] = useState(false);
  const [totpCode, setTotpCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function afterLogin(mustEnroll?: boolean) {
    router.push(mustEnroll ? "/settings" : "/units");
  }

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await login(email, password);
      if (res.requires_2fa) {
        setNeeds2fa(true);
      } else {
        afterLogin(res.must_enroll_2fa);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  }

  async function on2fa(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await verify2fa(totpCode);
      afterLogin(res.must_enroll_2fa);
    } catch (err) {
      setError(err instanceof Error ? err.message : "2FA fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell" style={{ maxWidth: 28rem }}>
      <header className="app-header">
        <h1>Anmelden</h1>
        <ThemeToggle />
      </header>

      <section className="card">
        {!needs2fa ? (
          <form onSubmit={onLogin} className="stack">
            <label>
              E-Mail
              <input
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label>
              Passwort
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {error && <p className="err">{error}</p>}
            <button type="submit" disabled={loading}>
              {loading ? "…" : "Login"}
            </button>
          </form>
        ) : (
          <form onSubmit={on2fa} className="stack">
            <p className="muted">6-stelliger Code aus der Authenticator-App:</p>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              placeholder="123456"
            />
            {error && <p className="err">{error}</p>}
            <button type="submit" disabled={loading}>
              {loading ? "…" : "Bestätigen"}
            </button>
          </form>
        )}
      </section>
    </main>
  );
}
