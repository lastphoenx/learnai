"use client";

import type { AiModelCatalog } from "@/lib/api";

type Props = {
  provider: string;
  taskKey: string;
  value: string;
  onChange: (model: string) => void;
  ollamaModels: string[];
  catalog: AiModelCatalog;
  allowEmpty?: boolean;
  emptyLabel?: string;
};

export function ModelSelect({
  provider,
  taskKey,
  value,
  onChange,
  ollamaModels,
  catalog,
  allowEmpty = true,
  emptyLabel = "Server-Default",
}: Props) {
  const name = provider.toLowerCase();

  if (name === "ollama") {
    if (ollamaModels.length === 0) {
      return <span className="muted">Ollama nicht erreichbar</span>;
    }
    return (
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {allowEmpty && <option value="">{emptyLabel}</option>}
        {ollamaModels.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    );
  }

  if (name === "openai") {
    const block = catalog.openai;
    const models =
      taskKey === "tts"
        ? block.tts
        : taskKey === "vision"
          ? block.vision.length
            ? block.vision
            : block.chat
          : block.chat;
    if (!block.ok || models.length === 0) {
      return (
        <span className="muted">
          OpenAI-Modelle nicht geladen{block.error ? `: ${block.error}` : ""}
        </span>
      );
    }
    return (
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {allowEmpty && <option value="">{emptyLabel}</option>}
        {models.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    );
  }

  if (name === "anthropic") {
    const block = catalog.anthropic;
    const models = block.chat.length ? block.chat : block.vision;
    if (!block.ok || models.length === 0) {
      return (
        <span className="muted">
          Anthropic-Modelle nicht geladen{block.error ? `: ${block.error}` : ""}
        </span>
      );
    }
    return (
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {allowEmpty && <option value="">{emptyLabel}</option>}
        {models.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    );
  }

  return <span className="muted">Provider wählen</span>;
}
