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
    <main style={{ maxWidth: 400, margin: "4rem auto", padding: "0 1.5rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", marginBottom: "2rem" }}>
        <h1 style={{ margin: 0 }}>Anmelden</h1>
        <ThemeToggle />
      </header>

      {!needs2fa ? (
        <form onSubmit={onLogin} style={{ display: "grid", gap: "1rem" }}>
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
          {error && <p style={{ color: "#ef4444", margin: 0 }}>{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? "…" : "Login"}
          </button>
        </form>
      ) : (
        <form onSubmit={on2fa} style={{ display: "grid", gap: "1rem" }}>
          <p style={{ color: "var(--muted)" }}>2FA-Code aus der Authenticator-App:</p>
          <input
            type="text"
            inputMode="numeric"
            required
            value={totpCode}
            onChange={(e) => setTotpCode(e.target.value)}
            placeholder="123456"
            style={{ padding: 8 }}
          />
          {error && <p style={{ color: "#ef4444", margin: 0 }}>{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? "…" : "Bestätigen"}
          </button>
        </form>
      )}
    </main>
  );
}
