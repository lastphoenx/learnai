"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { InlineEditName } from "@/components/InlineEditName";
import { LearnerSettingsForm, type TaskRow } from "@/components/LearnerSettingsForm";
import { PasswordInput } from "@/components/PasswordInput";
import { TotpQr } from "@/components/TotpQr";
import { useChildPreview } from "@/lib/childPreview";
import {
  applyProfileRecommendations,
  changeMyPassword,
  confirm2fa,
  createChildUser,
  fetchAiStatus,
  fetchMe,
  fetchProfiles,
  setup2fa,
  updateMySettings,
  updateProfile,
  type AiModelCatalog,
  type LearnerProfile,
  type SttProvider,
  type SttStatus,
  type TaskCatalogItem,
  type User,
} from "@/lib/api";

const EMPTY_CATALOG: AiModelCatalog = {
  openai: { ok: false, configured: false, chat: [], vision: [], tts: [] },
  anthropic: { ok: false, configured: false, chat: [], vision: [] },
};

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [profiles, setProfiles] = useState<LearnerProfile[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [secret, setSecret] = useState<string | null>(null);
  const [uri, setUri] = useState<string | null>(null);
  const [recovery, setRecovery] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSecret, setShowSecret] = useState(false);
  const [childName, setChildName] = useState("");
  const [childEmail, setChildEmail] = useState("");
  const [childPassword, setChildPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPassword2, setNewPassword2] = useState("");
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [saved, setSaved] = useState(false);
  const [byTask, setByTask] = useState<Record<string, TaskRow>>({});
  const [llmProvider, setLlmProvider] = useState("default");
  const [llmModel, setLlmModel] = useState("");
  const [catalog, setCatalog] = useState<TaskCatalogItem[]>([]);
  const [modelCatalog, setModelCatalog] = useState<AiModelCatalog>(EMPTY_CATALOG);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [configured, setConfigured] = useState({ openai: false, anthropic: false, ollama: false });
  const [sttProvider, setSttProvider] = useState<SttProvider>("browser");
  const [sttStatus, setSttStatus] = useState<SttStatus | undefined>(undefined);

  const selected = profiles.find((p) => p.id === selectedId) ?? null;
  const { asChild } = useChildPreview(user);
  const readOnly = asChild;

  function loadProfileForm(profile: LearnerProfile) {
    setByTask(profile.by_task || {});
    setLlmProvider(profile.llm_provider || "default");
    setLlmModel(profile.llm_model || "");
    setSttProvider((profile.stt_provider as SttProvider) || "browser");
  }

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (!u.is_child) {
          fetchProfiles()
            .then((rows) => {
              setProfiles(rows);
              const initial = u.profile_id && rows.some((r) => r.id === u.profile_id)
                ? u.profile_id
                : rows[0]?.id || "";
              setSelectedId(initial);
              const profile = rows.find((p) => p.id === initial);
              if (profile) loadProfileForm(profile);
            })
            .catch((e: Error) => setError(e.message));
        }
      })
      .catch(() => setError("Nicht angemeldet"));
    fetchAiStatus()
      .then((s) => {
        setOllamaModels(s.ollama.models || []);
        setConfigured({
          openai: s.openai.configured,
          anthropic: s.anthropic.configured,
          ollama: Boolean(s.ollama.ok || s.ollama.configured),
        });
        setCatalog(s.task_catalog || []);
        setModelCatalog(s.models || EMPTY_CATALOG);
        setSttStatus(s.stt);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const profile = profiles.find((p) => p.id === selectedId);
    if (profile) loadProfileForm(profile);
  }, [selectedId, profiles]);

  async function onSetup(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await setup2fa(email);
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
      <main className="shell shell-wide">
        <p>{error}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main className="shell shell-wide">
      <AppHeader user={user} title="Einstellungen" />
      {user?.must_enroll_2fa && (
        <p className="warn">Für diesen Account ist 2FA Pflicht. Bitte jetzt einrichten.</p>
      )}

      <div className="card stack">
        <h2>Account</h2>
        <p className="muted">Name in der Kopfzeile beim Login — nicht der Lerner-Name.</p>
        <p>
          Login-E-Mail:{" "}
          <strong>{user?.login_email || "nicht hinterlegt"}</strong>
          {!user?.login_email && (
            <span className="muted"> — Admin kann sie unter Benutzer zuordnen.</span>
          )}
        </p>
        <InlineEditName
          value={user?.display_name || ""}
          placeholder="z.B. Max"
          onSave={async (name) => {
            const me = await updateMySettings({ display_name: name });
            setUser(me);
          }}
        />
        <form
          className="stack account-password-form"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            setPasswordSaved(false);
            if (newPassword !== newPassword2) {
              setError("Neue Passwörter stimmen nicht überein");
              return;
            }
            try {
              await changeMyPassword({
                current_password: currentPassword,
                new_password: newPassword,
              });
              setCurrentPassword("");
              setNewPassword("");
              setNewPassword2("");
              setPasswordSaved(true);
            } catch (err) {
              setError(err instanceof Error ? err.message : "Passwort ändern fehlgeschlagen");
            }
          }}
        >
          <h3>Passwort ändern</h3>
          <PasswordInput
            label="Aktuelles Passwort"
            required
            autoComplete="current-password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
          <PasswordInput
            label="Neues Passwort (min. 12 Zeichen)"
            required
            minLength={12}
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <PasswordInput
            label="Neues Passwort wiederholen"
            required
            minLength={12}
            autoComplete="new-password"
            value={newPassword2}
            onChange={(e) => setNewPassword2(e.target.value)}
          />
          <button type="submit">Passwort speichern</button>
          {passwordSaved && <p>Passwort geändert.</p>}
        </form>
      </div>

      <div className="card stack">
        <h2>Lerner-Einstellungen</h2>
        {readOnly ? (
          <p className="muted">Kinder-Accounts: dein Eltern-Account pflegt die KI-Einstellungen.</p>
        ) : profiles.length > 1 ? (
          <label>
            Lerner-Profil
            <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.display_name}
                  {p.id === user?.profile_id ? " (Du)" : ""}
                  {p.is_child_profile ? " (Kind)" : ""}
                </option>
              ))}
            </select>
          </label>
        ) : selected ? (
          <p>
            Profil: <strong>{selected.display_name}</strong>
            {selected.id === user?.profile_id && <span className="muted"> · Du</span>}
            {selected.is_child_profile && <span className="muted"> · Kind</span>}
          </p>
        ) : null}

        {!readOnly && selected && (
          <form
            className="stack"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              setSaved(false);
              try {
                const updated = await updateProfile(selected.id, {
                  llm_provider: llmProvider,
                  llm_model: llmModel,
                  by_task: byTask,
                  stt_provider: sttProvider,
                });
                setProfiles((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
                setSaved(true);
              } catch (err) {
                setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
              }
            }}
          >
            <InlineEditName
              value={selected.display_name}
              placeholder="Lerner-Name"
              onSave={async (name) => {
                const updated = await updateProfile(selected.id, { display_name: name });
                setProfiles((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
              }}
            />
            <LearnerSettingsForm
              catalog={catalog}
              configured={configured}
              ollamaModels={ollamaModels}
              modelCatalog={modelCatalog}
              byTask={byTask}
              llmProvider={llmProvider}
              llmModel={llmModel}
              onByTaskChange={setByTask}
              onFallbackChange={(provider, model) => {
                setLlmProvider(provider);
                setLlmModel(model);
              }}
              onApplyRecommendations={async () => {
                const updated = await applyProfileRecommendations(selected.id);
                setProfiles((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
                loadProfileForm(updated);
              }}
              sttProvider={sttProvider}
              sttStatus={sttStatus}
              onSttProviderChange={setSttProvider}
            />
            <button type="submit">Lerner-Einstellungen speichern</button>
            {saved && <p>Gespeichert.</p>}
          </form>
        )}
      </div>

      {!readOnly && !user?.is_admin && (
        <form
          className="card stack"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            try {
              await createChildUser({
                email: childEmail.trim(),
                password: childPassword,
                display_name: childName.trim(),
              });
              setChildName("");
              setChildEmail("");
              setChildPassword("");
              const rows = await fetchProfiles();
              setProfiles(rows);
            } catch (err) {
              setError(err instanceof Error ? err.message : "Kind anlegen fehlgeschlagen");
            }
          }}
        >
          <h2>Kind anlegen</h2>
          <p className="muted">Du wirst Elternteil und kannst Lerner-Einstellungen und Verlauf sehen.</p>
          <label>
            Lerner-Name
            <input required value={childName} onChange={(e) => setChildName(e.target.value)} />
          </label>
          <label>
            E-Mail (Login Kind)
            <input type="email" required value={childEmail} onChange={(e) => setChildEmail(e.target.value)} />
          </label>
          <PasswordInput
            label="Startpasswort"
            required
            minLength={12}
            value={childPassword}
            onChange={(e) => setChildPassword(e.target.value)}
          />
          <button type="submit">Kind anlegen</button>
        </form>
      )}

      <div className="card stack">
        <p>
          2FA: <strong>{user?.totp_enabled ? "aktiv" : "aus"}</strong> · Policy:{" "}
          {user?.totp_required ? "Pflicht" : "optional"}
        </p>
        {!user?.totp_enabled && !uri && (
          <form onSubmit={onSetup} className="stack">
            <label>
              E-Mail im Authenticator
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <button type="submit">QR-Code erzeugen</button>
          </form>
        )}
        {uri && !user?.totp_enabled && (
          <section className="stack">
            <div className="qr-wrap">
              <TotpQr uri={uri} />
            </div>
            <form onSubmit={onConfirm} className="stack">
              <label>
                Code
                <input value={code} onChange={(e) => setCode(e.target.value)} required />
              </label>
              <button type="submit">Code bestätigen</button>
            </form>
          </section>
        )}
        {recovery && (
          <ul>
            {recovery.map((c) => (
              <li key={c}>
                <code>{c}</code>
              </li>
            ))}
          </ul>
        )}
        {error && <p className="err">{error}</p>}
      </div>
    </main>
  );
}
