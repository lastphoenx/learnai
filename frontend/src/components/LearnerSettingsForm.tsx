"use client";

import { useState } from "react";
import { ModelSelect } from "@/components/ModelSelect";
import type { AiModelCatalog, SttProvider, SttStatus, TaskCatalogItem } from "@/lib/api";
import { isReasoningModel, REASONING_EFFORT_OPTIONS } from "@/lib/reasoningModels";

export type TaskRow = { provider: string; model: string; reasoning_effort?: string };

function modelHints(item: TaskCatalogItem, effectiveProvider: string): string[] {
  if (effectiveProvider === "ollama") {
    return item.local_resolved?.length ? item.local_resolved : item.local;
  }
  return item.external_resolved?.length ? item.external_resolved : item.external;
}

type Props = {
  catalog: TaskCatalogItem[];
  configured: { openai: boolean; anthropic: boolean; ollama: boolean };
  ollamaModels: string[];
  modelCatalog: AiModelCatalog;
  byTask: Record<string, TaskRow>;
  llmProvider: string;
  llmModel: string;
  llmReasoningEffort: string;
  onByTaskChange: (next: Record<string, TaskRow>) => void;
  onFallbackChange: (provider: string, model: string) => void;
  onReasoningEffortChange: (effort: string) => void;
  onApplyRecommendations: () => void;
  sttProvider?: SttProvider;
  sttStatus?: SttStatus;
  onSttProviderChange?: (provider: SttProvider) => void;
  readOnly?: boolean;
};

export function LearnerSettingsForm({
  catalog,
  configured,
  ollamaModels,
  modelCatalog,
  byTask,
  llmProvider,
  llmModel,
  llmReasoningEffort,
  onByTaskChange,
  onFallbackChange,
  onReasoningEffortChange,
  onApplyRecommendations,
  sttProvider = "browser",
  sttStatus,
  onSttProviderChange,
  readOnly,
}: Props) {
  function setRow(key: string, patch: Partial<TaskRow>) {
    const current = byTask[key] || { provider: "", model: "" };
    onByTaskChange({ ...byTask, [key]: { ...current, ...patch } });
  }

  return (
    <>
      <p className="muted">
        Pro Zeile: Provider wählen, dann eine der 1–3 Empfehlungen — oder leer lassen für
        automatische Wahl. «Empfehlungen übernehmen» setzt alles auf einmal.
      </p>
      {!readOnly && (
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button type="button" className="ghost" onClick={onApplyRecommendations}>
            Empfehlungen übernehmen
          </button>
        </div>
      )}
      {catalog.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table className="task-ai">
            <thead>
              <tr>
                <th>Typ</th>
                <th>Provider</th>
                <th>Modell</th>
                <th>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {catalog.map((item) => {
                const row = byTask[item.key] || { provider: "", model: "" };
                const provider = row.provider || "";
                const isTts = item.key === "tts";
                const isMixed = item.key === "mixed";
                const effectiveProvider = provider || item.default_provider;
                const showReasoning =
                  effectiveProvider === "openai" && isReasoningModel(row.model);
                return (
                  <tr key={item.key}>
                    <td>
                      <strong>{item.label}</strong>
                      <p className="why">{item.why}</p>
                      {isMixed ? (
                        <p className="why muted" style={{ marginTop: "0.35rem" }}>
                          Posten-Einheiten mit Fotos (Preset «posten_compact»): dieses Modell sieht die
                          Originalbilder direkt in einem Call — «Fotos / OCR» wird dafür nicht
                          verwendet. Vision-fähiges Gemischt-Modell nötig (z. B. gpt-4o, qwen2.5vl).
                        </p>
                      ) : null}
                    </td>
                    <td>
                      {readOnly ? (
                        effectiveProvider
                      ) : (
                        <select
                          value={provider}
                          onChange={(e) => setRow(item.key, { provider: e.target.value, model: "" })}
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
                      )}
                    </td>
                    <td>
                      {readOnly ? (
                        row.model || "Default"
                      ) : (
                        <ModelSelect
                          provider={effectiveProvider}
                          taskKey={item.key}
                          value={row.model}
                          onChange={(model) => setRow(item.key, { model })}
                          ollamaModels={ollamaModels}
                          catalog={modelCatalog}
                          hints={modelHints(item, effectiveProvider)}
                          emptyLabel={
                            item.key === "tts" ? "Standard (tts-1-hd)" : "Empfehlung (automatisch)"
                          }
                        />
                      )}
                    </td>
                    <td>
                      {showReasoning ? (
                        readOnly ? (
                          row.reasoning_effort || "API-Standard"
                        ) : (
                          <select
                            value={row.reasoning_effort || ""}
                            onChange={(e) =>
                              setRow(item.key, { reasoning_effort: e.target.value || undefined })
                            }
                            title="OpenAI reasoning_effort (GPT-5 / o-Serie)"
                          >
                            {REASONING_EFFORT_OPTIONS.map((opt) => (
                              <option key={opt.value || "default"} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        )
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <div className="stack" style={{ marginTop: "1rem" }}>
        <h3 style={{ margin: 0 }}>Sprache zu Text (Diktat)</h3>
        <p className="muted" style={{ margin: 0 }}>
          Für Mikrofon-Buttons beim Anlegen von Einheiten und bei Eingabe-Karten im Üben. «Lokal» nutzt den
          Whisper-Dienst auf dem GMKtec (privat). «Browser» nutzt Chrome/Edge-Spracherkennung.
        </p>
        <label>
          STT-Engine
          {readOnly ? (
            <span>{sttProvider}</span>
          ) : (
            <select
              value={sttProvider}
              onChange={(e) => onSttProviderChange?.(e.target.value as SttProvider)}
            >
              <option value="browser">Browser (Chrome/Edge)</option>
              <option value="local" disabled={Boolean(sttStatus && !sttStatus.local.configured)}>
                Lokal (Whisper){sttStatus && !sttStatus.local.configured ? " — nicht konfiguriert" : ""}
              </option>
              <option value="openai" disabled={Boolean(sttStatus && !sttStatus.openai.configured)}>
                OpenAI Whisper{sttStatus && !sttStatus.openai.configured ? " — kein API-Key" : ""}
              </option>
              <option value="anthropic" disabled>
                Anthropic — nicht verfügbar
              </option>
            </select>
          )}
        </label>
      </div>
      <details>
        <summary className="muted">Fallback für Text-Typen ohne eigene Zeile</summary>
        <div className="stack" style={{ marginTop: "0.75rem" }}>
          <label>
            KI-Provider
            {readOnly ? (
              <span>{llmProvider || "Empfehlung je Typ"}</span>
            ) : (
              <select
                value={llmProvider}
                onChange={(e) => onFallbackChange(e.target.value, llmModel)}
              >
                <option value="default">Standard (Empfehlung je Typ)</option>
                {configured.ollama && <option value="ollama">Ollama (lokal)</option>}
                {configured.openai && <option value="openai">OpenAI</option>}
                {configured.anthropic && <option value="anthropic">Anthropic</option>}
              </select>
            )}
          </label>
          <label>
            Modell
            {readOnly || llmProvider === "default" ? (
              <span>{llmModel || "Default"}</span>
            ) : (
              <ModelSelect
                provider={llmProvider}
                taskKey="mixed"
                value={llmModel}
                onChange={(model) => onFallbackChange(llmProvider, model)}
                ollamaModels={ollamaModels}
                catalog={modelCatalog}
                hints={modelHints(
                  catalog.find((c) => c.key === "mixed") || {
                    key: "mixed",
                    label: "",
                    why: "",
                    default_provider: "ollama",
                    local: [],
                    external: [],
                  },
                  llmProvider,
                )}
              />
            )}
          </label>
          {llmProvider === "openai" && isReasoningModel(llmModel) && (
            <label>
              Reasoning-Aufwand (Fallback)
              {readOnly ? (
                <span>{llmReasoningEffort || "API-Standard"}</span>
              ) : (
                <select
                  value={llmReasoningEffort}
                  onChange={(e) => onReasoningEffortChange(e.target.value)}
                >
                  {REASONING_EFFORT_OPTIONS.map((opt) => (
                    <option key={opt.value || "default"} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}
              <span className="muted why">
                Für GPT-5/o-Modelle ohne eigene Zeile in der Tabelle (z. B. Gemischt bei Posten
                kompakt).
              </span>
            </label>
          )}
        </div>
      </details>
    </>
  );
}
