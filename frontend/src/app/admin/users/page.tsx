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
  updateChildGuardians,
  type AdminUser,
  type User,
} from "@/lib/api";
import { formatKiSummary } from "@/lib/kiSummary";

function parentLabel(users: AdminUser[], id: string) {
  const u = users.find((row) => row.id === id);
  return u?.display_name || id.slice(0, 8);
}

function ParentSelects({
  adults,
  parent1,
  parent2,
  onParent1,
  onParent2,
}: {
  adults: AdminUser[];
  parent1: string;
  parent2: string;
  onParent1: (id: string) => void;
  onParent2: (id: string) => void;
}) {
  return (
    <>
      <label>
        Elternteil 1
        <select required value={parent1} onChange={(e) => onParent1(e.target.value)}>
          <option value="" disabled>
            Elternteil wählen
          </option>
          {adults.map((u) => (
            <option key={u.id} value={u.id}>
              {u.display_name || u.id.slice(0, 8)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Elternteil 2 (optional)
        <select value={parent2} onChange={(e) => onParent2(e.target.value)}>
          <option value="">— kein zweiter Elternteil —</option>
          {adults
            .filter((u) => u.id !== parent1)
            .map((u) => (
              <option key={u.id} value={u.id}>
                {u.display_name || u.id.slice(0, 8)}
              </option>
            ))}
        </select>
      </label>
    </>
  );
}

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
  const [childParent1, setChildParent1] = useState("");
  const [childParent2, setChildParent2] = useState("");

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
    const parent_ids = [childParent1, childParent2].filter(Boolean);
    if (parent_ids.length === 0) {
      setError("Mindestens ein Elternteil wählen");
      return;
    }
    try {
      await createChildUser({
        email: childEmail.trim(),
        password: childPassword,
        display_name: childName.trim(),
        parent_ids,
      });
      setChildName("");
      setChildEmail("");
      setChildPassword("");
      setChildParent1("");
      setChildParent2("");
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
    <main className="shell shell-wide admin-page">
      <AppHeader user={user} title="Benutzer" />
      <p className="muted">
        Accounts für Login und 2FA. Lerner-Einstellungen (KI je Typ) unter Einstellungen →
        Lerner-Profil. Kinder können bis zu zwei Eltern haben.
      </p>
      {error && <p className="err">{error}</p>}

      <div className="admin-forms-grid">
      <form onSubmit={onCreate} className="card stack">
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
        <label className="checkbox-row">
          <input type="checkbox" checked={makeAdmin} onChange={(e) => setMakeAdmin(e.target.checked)} />
          Admin
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={totpRequired}
            onChange={(e) => setTotpRequired(e.target.checked)}
          />
          2FA Pflicht
        </label>
        <button type="submit">Benutzer anlegen</button>
      </form>

      <form onSubmit={onCreateChild} className="card stack">
        <h2>Kind anlegen</h2>
        <p className="muted">
          Kind-Account mit Lerner-Profil. Beide Eltern sehen Einheiten und Verlauf des Kindes und
          pflegen dessen KI-Einstellungen.
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
        <ParentSelects
          adults={adults}
          parent1={childParent1}
          parent2={childParent2}
          onParent1={(id) => {
            setChildParent1(id);
            if (id === childParent2) setChildParent2("");
          }}
          onParent2={setChildParent2}
        />
        <button type="submit">Kind anlegen</button>
      </form>
      </div>

      <ul className="admin-user-list">
        {users.map((u) => (
          <li key={u.id} className="admin-user-card">
            <InlineEditName
              value={u.display_name || ""}
              emptyLabel="ohne Namen"
              onSave={async (name) => {
                await updateAdminUser(u.id, { display_name: name });
                load();
              }}
            />
            <p className="admin-user-meta">
              {u.is_admin ? "Admin" : u.is_child ? "Kind" : "Benutzer"} · 2FA{" "}
              {u.totp_enabled ? "aktiv" : "nicht eingerichtet"}
              {u.ki_summary || formatKiSummary(u.by_task)
                ? ` · KI: ${u.ki_summary || formatKiSummary(u.by_task)}`
                : ""}
              {u.is_child && (u.parent_ids?.length || u.parent_id)
                ? ` · Eltern: ${(u.parent_ids?.length ? u.parent_ids : u.parent_id ? [u.parent_id] : [])
                    .map((id) => parentLabel(users, id))
                    .join(", ")}`
                : ""}
            </p>
            {u.is_child && (
              <ChildGuardianEditor user={u} adults={adults} onSaved={load} onError={setError} />
            )}
            <label className="checkbox-row">
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

function ChildGuardianEditor({
  user,
  adults,
  onSaved,
  onError,
}: {
  user: AdminUser;
  adults: AdminUser[];
  onSaved: () => void;
  onError: (msg: string | null) => void;
}) {
  const initial = user.parent_ids?.length ? user.parent_ids : user.parent_id ? [user.parent_id] : [];
  const [parent1, setParent1] = useState(initial[0] || "");
  const [parent2, setParent2] = useState(initial[1] || "");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const ids = user.parent_ids?.length ? user.parent_ids : user.parent_id ? [user.parent_id] : [];
    setParent1(ids[0] || "");
    setParent2(ids[1] || "");
  }, [user.parent_ids, user.parent_id]);

  async function save() {
    onError(null);
    const parent_ids = [parent1, parent2].filter(Boolean);
    if (parent_ids.length === 0) {
      onError("Mindestens ein Elternteil wählen");
      return;
    }
    try {
      await updateChildGuardians(user.id, parent_ids);
      setOpen(false);
      onSaved();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Eltern speichern fehlgeschlagen");
    }
  }

  if (!open) {
    return (
      <button type="button" className="ghost" style={{ marginBottom: "0.5rem" }} onClick={() => setOpen(true)}>
        Eltern bearbeiten
      </button>
    );
  }

  return (
    <div className="stack admin-guardian-edit">
      <ParentSelects
        adults={adults}
        parent1={parent1}
        parent2={parent2}
        onParent1={(id) => {
          setParent1(id);
          if (id === parent2) setParent2("");
        }}
        onParent2={setParent2}
      />
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button type="button" onClick={save}>
          Eltern speichern
        </button>
        <button type="button" className="ghost" onClick={() => setOpen(false)}>
          Abbrechen
        </button>
      </div>
    </div>
  );
}
