"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { TotpQr } from "@/components/TotpQr";
import { confirm2fa, fetchAiStatus, fetchMe, setup2fa, updateMySettings, type User } from "@/lib/api";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [secret, setSecret] = useState<string | null>(null);
  const [uri, setUri] = useState<string | null>(null);
  const [recovery, setRecovery] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSecret, setShowSecret] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [llmProvider, setLlmProvider] = useState("default");
  const [llmModel, setLlmModel] = useState("");
  const [saved, setSaved] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [configured, setConfigured] = useState({ openai: false, anthropic: false, ollama: false });

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        setDisplayName(u.display_name || "");
        setLlmProvider(u.llm_provider || "default");
        setLlmModel(u.llm_model || "");
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
      })
      .catch(() => undefined);
  }, []);

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
      <main className="shell">
        <p>{error}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main className="shell">
      <AppHeader user={user} title="Einstellungen" />
      {user?.must_enroll_2fa && (
        <p className="warn">Für diesen Account ist 2FA Pflicht. Bitte jetzt einrichten.</p>
      )}
      <div className="card stack">
        <h2>Profil</h2>
        <form
          className="stack"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            setSaved(false);
            try {
              const me = await updateMySettings({
                display_name: displayName,
                llm_provider: llmProvider,
                llm_model: llmModel,
              });
              setUser(me);
              setSaved(true);
            } catch (err) {
              setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
            }
          }}
        >
          <label>
            Anzeigename
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="z.B. Papa, Lena, Klasse 4a"
            />
          </label>
          <label>
            KI-Provider
            <select value={llmProvider} onChange={(e) => setLlmProvider(e.target.value)}>
              <option value="default">Standard (Server)</option>
              {configured.ollama && <option value="ollama">Ollama (lokal)</option>}
              {configured.openai && <option value="openai">OpenAI</option>}
              {configured.anthropic && <option value="anthropic">Anthropic / Claude</option>}
            </select>
          </label>
          <label>
            Modell
            {llmProvider === "ollama" && ollamaModels.length > 0 ? (
              <select value={llmModel} onChange={(e) => setLlmModel(e.target.value)}>
                <option value="">Standard</option>
                {ollamaModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <input
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                placeholder={
                  llmProvider === "openai"
                    ? "z.B. gpt-4o-mini"
                    : llmProvider === "anthropic"
                      ? "z.B. claude-sonnet-4-0"
                      : "leer = Server-Default"
                }
              />
            )}
          </label>
          <p className="muted">
            API-Keys bleiben in der Server-.env. Hier wählst du nur, womit deine Einheiten
            aufbereitet werden.
          </p>
          <button type="submit">Einstellungen speichern</button>
          {saved && <p>Gespeichert.</p>}
        </form>
      </div>
      <div className="card stack">
        <p>
          2FA: <strong>{user?.totp_enabled ? "aktiv" : "aus"}</strong> · Policy:{" "}
          {user?.totp_required ? "Pflicht" : "optional"}
        </p>
        {!user?.totp_enabled && !uri && (
          <form onSubmit={onSetup} className="stack">
            <p className="muted">
              Die E-Mail erscheint als Name in der Authenticator-App. Du bist bereits angemeldet —
              kein Passwort nötig.
            </p>
            <label>
              E-Mail im Authenticator
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <button type="submit">QR-Code erzeugen</button>
          </form>
        )}
        {uri && !user?.totp_enabled && (
          <section className="stack">
            <h2>Authenticator scannen</h2>
            <p className="muted">
              Aegis, Google Authenticator oder Authy: QR scannen, danach den 6-stelligen Code
              eintragen.
            </p>
            <div className="qr-wrap">
              <TotpQr uri={uri} />
            </div>
            <details>
              <summary>Kein Scan möglich? Secret manuell</summary>
              <button type="button" onClick={() => setShowSecret((v) => !v)}>
                {showSecret ? "Secret verbergen" : "Secret zeigen"}
              </button>
              {showSecret && <code className="secret">{secret}</code>}
            </details>
            <form onSubmit={onConfirm} className="stack">
              <label>
                Code aus der App
                <input
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="123456"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                />
              </label>
              <button type="submit">Code bestätigen</button>
            </form>
          </section>
        )}
        {recovery && (
          <section className="stack">
            <h2>Recovery-Codes</h2>
            <p className="warn">
              Einmalig notieren und offline aufbewahren. Jeder Code gilt nur einmal.
            </p>
            <ul>
              {recovery.map((c) => (
                <li key={c}>
                  <code>{c}</code>
                </li>
              ))}
            </ul>
          </section>
        )}
        {error && <p className="err">{error}</p>}
      </div>
    </main>
  );
}
