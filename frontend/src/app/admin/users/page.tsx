"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { createUser, fetchMe, fetchUsers, setTotpPolicy, type AdminUser, type User } from "@/lib/api";

export default function AdminUsersPage() {
  const [user, setUser] = useState<User | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [makeAdmin, setMakeAdmin] = useState(false);
  const [totpRequired, setTotpRequired] = useState(false);

  function load() {
    fetchUsers().then(setUsers).catch((e: Error) => setError(e.message));
  }

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (!u.is_admin) setError("Nur Admins");
        else load();
      })
      .catch(() => setError("Nicht angemeldet"));
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createUser({
        email: email.trim(),
        password,
        display_name: displayName.trim(),
        is_admin: makeAdmin,
        totp_required: totpRequired,
      });
      setEmail("");
      setPassword("");
      setDisplayName("");
      setMakeAdmin(false);
      setTotpRequired(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Anlegen fehlgeschlagen");
    }
  }

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
      <AppHeader user={user} title="Benutzer" />
      <p className="muted">
        2FA ist pro Account steuerbar: Pflicht oder optional. Wenn sie einmal eingerichtet ist, gilt
        sie beim Login immer.
      </p>
      {error && <p className="err">{error}</p>}

      <form onSubmit={onCreate} className="card stack" style={{ marginBottom: "1.5rem" }}>
        <h2>Neuen Benutzer anlegen</h2>
        <label>
          Anzeigename
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="z.B. Lena"
          />
        </label>
        <label>
          E-Mail (Login)
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Startpasswort (min. 12 Zeichen)
          <input
            type="password"
            required
            minLength={12}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input type="checkbox" checked={makeAdmin} onChange={(e) => setMakeAdmin(e.target.checked)} />
          Admin
        </label>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={totpRequired}
            onChange={(e) => setTotpRequired(e.target.checked)}
          />
          2FA Pflicht
        </label>
        <button type="submit">Benutzer anlegen</button>
      </form>

      <ul style={{ listStyle: "none", padding: 0 }}>
        {users.map((u) => (
          <li
            key={u.id}
            style={{
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "1rem",
              marginBottom: 8,
            }}
          >
            <strong>{u.display_name || "ohne Namen"}</strong>
            <p style={{ margin: "0.4rem 0" }}>
              {u.is_admin ? "Admin" : "Benutzer"} · 2FA {u.totp_enabled ? "aktiv" : "nicht eingerichtet"}
              {u.llm_provider ? ` · KI: ${u.llm_provider}` : ""}
            </p>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={u.totp_required}
                onChange={async (e) => {
                  await setTotpPolicy(u.id, e.target.checked);
                  load();
                }}
              />
              2FA Pflicht
            </label>
          </li>
        ))}
      </ul>
    </main>
  );
}
