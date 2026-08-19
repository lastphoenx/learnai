"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { fetchMe, fetchUsers, setTotpPolicy, type AdminUser, type User } from "@/lib/api";

export default function AdminUsersPage() {
  const [user, setUser] = useState<User | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState<string | null>(null);

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

  if (error && !user) {
    return (
      <main style={{ maxWidth: 720, margin: "3rem auto", padding: "0 1.5rem" }}>
        <p>{error}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 800, margin: "3rem auto", padding: "0 1.5rem" }}>
      <AppHeader user={user} title="Benutzer / 2FA-Policy" />
      <p style={{ color: "var(--muted)" }}>
        2FA ist pro Account steuerbar: Pflicht oder optional. Wenn sie einmal eingerichtet ist, gilt
        sie beim Login immer.
      </p>
      {error && <p style={{ color: "#ef4444" }}>{error}</p>}
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
            <code>{u.id}</code>
            <p style={{ margin: "0.4rem 0" }}>
              {u.is_admin ? "Admin" : "Benutzer"} · 2FA {u.totp_enabled ? "aktiv" : "nicht eingerichtet"}
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
