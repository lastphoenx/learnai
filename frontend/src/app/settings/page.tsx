"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { TotpQr } from "@/components/TotpQr";
import {
  confirm2fa,
  fetchAiStatus,
  fetchMe,
  setup2fa,
  updateMySettings,
  type TaskCatalogItem,
  type User,
} from "@/lib/api";

type TaskRow = { provider: string; model: string };

function pickLocal(recs: string[], pulled: string[]): string {
  const lower = pulled.map((p) => p.toLowerCase());
  for (const rec of recs) {
    const r = rec.toLowerCase();
    const idx = lower.findIndex((p) => p === r || p.startsWith(r) || p.includes(r.split(":")[0]));
    if (idx >= 0) return pulled[idx];
  }
  return "";
}

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
  const [byTask, setByTask] = useState<Record<string, TaskRow>>({});
  const [catalog, setCatalog] = useState<TaskCatalogItem[]>([]);
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
        setByTask(u.by_task || {});
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
      })
      .catch(() => undefined);
  }, []);

  function setRow(key: string, patch: Partial<TaskRow>) {
    setByTask((prev) => {
      const current = prev[key] || { provider: "", model: "" };
      return { ...prev, [key]: { ...current, ...patch } };
    });
  }

  function applyRecommended() {
    const next: Record<string, TaskRow> = {};
    for (const item of catalog) {
      next[item.key] = {
        provider: item.default_provider,
        model:
          item.default_provider === "ollama"
            ? pickLocal(item.local, ollamaModels)
            : item.external[0] || "",
      };
    }
    setByTask(next);
  }

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
                by_task: byTask,
              });
              setUser(me);
              setByTask(me.by_task || {});
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
              placeholder="z.B. Thomas, Lena, Klasse 4a"
            />
          </label>
          <p className="muted">
            Pro Aufgabentyp ein Modell. Lokal wo Qualität und Datenschutz passen; Vorlesen und
            Sprache über OpenAI/Anthropic. Keys bleiben in der Server-.env.
          </p>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button type="button" className="ghost" onClick={applyRecommended}>
              Empfehlungen übernehmen
            </button>
          </div>
          {catalog.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table className="task-ai">
                <thead>
                  <tr>
                    <th>Typ</th>
                    <th>Provider</th>
                    <th>Modell</th>
                  </tr>
                </thead>
                <tbody>
                  {catalog.map((item) => {
                    const row = byTask[item.key] || { provider: "", model: "" };
                    const provider = row.provider || "";
                    const isTts = item.key === "tts";
                    return (
                      <tr key={item.key}>
                        <td>
                          <strong>{item.label}</strong>
                          <p className="why">{item.why}</p>
                          <p className="why">
                            Lokal: {item.local.map((m, i) => `${i + 1}. ${m}`).join(" · ")}
                            <br />
                            Extern: {item.external.map((m, i) => `${i + 1}. ${m}`).join(" · ")}
                          </p>
                        </td>
                        <td>
                          <select
                            value={provider}
                            onChange={(e) =>
                              setRow(item.key, { provider: e.target.value, model: "" })
                            }
                          >
                            <option value="">Empfehlung ({item.default_provider})</option>
                            {!isTts && configured.ollama && (
                              <option value="ollama">Ollama (lokal)</option>
                            )}
                            {configured.openai && <option value="openai">OpenAI</option>}
                            {!isTts && configured.anthropic && (
                              <option value="anthropic">Anthropic</option>
                            )}
                          </select>
                        </td>
                        <td>
                          <ModelField
                            item={item}
                            provider={provider || item.default_provider}
                            model={row.model}
                            ollamaModels={ollamaModels}
                            onChange={(model) => setRow(item.key, { model })}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <details>
            <summary className="muted">Fallback für Text-Typen ohne eigene Zeile</summary>
            <div className="stack" style={{ marginTop: "0.75rem" }}>
              <label>
                KI-Provider
                <select value={llmProvider} onChange={(e) => setLlmProvider(e.target.value)}>
                  <option value="default">Standard (Empfehlung je Typ)</option>
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
                    placeholder="leer = Server-Default"
                  />
                )}
              </label>
            </div>
          </details>
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

function ModelField({
  item,
  provider,
  model,
  ollamaModels,
  onChange,
}: {
  item: TaskCatalogItem;
  provider: string;
  model: string;
  ollamaModels: string[];
  onChange: (model: string) => void;
}) {
  if (item.key === "tts") {
    return (
      <select value={model} onChange={(e) => onChange(e.target.value)}>
        <option value="">1. tts-1-hd</option>
        <option value="tts-1-hd">1. tts-1-hd</option>
        <option value="gpt-4o-mini-tts">2. gpt-4o-mini-tts</option>
        <option value="tts-1">3. tts-1</option>
      </select>
    );
  }
  if (provider === "ollama" && ollamaModels.length > 0) {
    return (
      <select value={model} onChange={(e) => onChange(e.target.value)}>
        <option value="">auto / Server</option>
        {ollamaModels.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    );
  }
  const hints = provider === "ollama" ? item.local : item.external;
  return (
    <>
      <input
        value={model}
        onChange={(e) => onChange(e.target.value)}
        placeholder={hints[0] || "leer = Default"}
        list={`models-${item.key}`}
      />
      <datalist id={`models-${item.key}`}>
        {hints.map((h) => (
          <option key={h} value={h} />
        ))}
      </datalist>
    </>
  );
}
