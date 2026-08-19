"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { InlineEditName } from "@/components/InlineEditName";
import {
  createChildUser,
  createUser,
  fetchMe,
  fetchUsers,
  setTotpPolicy,
  updateAdminUser,
  type AdminUser,
  type User,
} from "@/lib/api";
import { formatKiSummary } from "@/lib/kiSummary";

export default function AdminUsersPage() {
  const [user, setUser] = useState<User | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [makeAdmin, setMakeAdmin] = useState(false);
  const [totpRequired, setTotpRequired] = useState(false);
  const [childName, setChildName] = useState("");
  const [childEmail, setChildEmail] = useState("");
  const [childPassword, setChildPassword] = useState("");
  const [childParentId, setChildParentId] = useState("");

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

  async function onCreateChild(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createChildUser({
        email: childEmail.trim(),
        password: childPassword,
        display_name: childName.trim(),
        parent_id: childParentId || undefined,
      });
      setChildName("");
      setChildEmail("");
      setChildPassword("");
      setChildParentId("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kind anlegen fehlgeschlagen");
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

  const adults = users.filter((u) => !u.is_child);

  return (
    <main className="shell">
      <AppHeader user={user} title="Benutzer" />
      <p className="muted">
        Accounts für Login und 2FA. Lerner-Einstellungen (KI je Typ) unter Einstellungen →
        Lerner-Profil.
      </p>
      {error && <p className="err">{error}</p>}

      <form onSubmit={onCreate} className="card stack" style={{ marginBottom: "1.5rem" }}>
        <h2>Neuen Benutzer anlegen</h2>
        <label>
          Anzeigename
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="z.B. Lena" />
        </label>
        <label>
          E-Mail (Login)
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
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

      <form onSubmit={onCreateChild} className="card stack" style={{ marginBottom: "1.5rem" }}>
        <h2>Kind anlegen</h2>
        <p className="muted">
          Kind-Account mit Lerner-Profil. Eltern sehen Einheiten und Verlauf des Kindes und pflegen
          dessen KI-Einstellungen.
        </p>
        <label>
          Lerner-Name
          <input required value={childName} onChange={(e) => setChildName(e.target.value)} />
        </label>
        <label>
          E-Mail (Login für Kind, optional synthetisch)
          <input type="email" required value={childEmail} onChange={(e) => setChildEmail(e.target.value)} />
        </label>
        <label>
          Startpasswort
          <input
            type="password"
            required
            minLength={12}
            value={childPassword}
            onChange={(e) => setChildPassword(e.target.value)}
          />
        </label>
        <label>
          Eltern-Account
          <select value={childParentId} onChange={(e) => setChildParentId(e.target.value)}>
            <option value="">Ich bin der Elternteil</option>
            {adults.map((u) => (
              <option key={u.id} value={u.id}>
                {u.display_name || u.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </label>
        <button type="submit">Kind anlegen</button>
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
            <InlineEditName
              value={u.display_name || ""}
              emptyLabel="ohne Namen"
              onSave={async (name) => {
                await updateAdminUser(u.id, { display_name: name });
                load();
              }}
            />
            <p style={{ margin: "0.4rem 0" }}>
              {u.is_admin ? "Admin" : u.is_child ? "Kind" : "Benutzer"} · 2FA{" "}
              {u.totp_enabled ? "aktiv" : "nicht eingerichtet"}
              {u.ki_summary || formatKiSummary(u.by_task)
                ? ` · KI: ${u.ki_summary || formatKiSummary(u.by_task)}`
                : ""}
              {u.parent_id ? " · hat Eltern" : ""}
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
