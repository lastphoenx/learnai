"use client";

import { useMemo, useState } from "react";
import type { AiModelCatalog } from "@/lib/api";

type Props = {
  provider: string;
  taskKey: string;
  value: string;
  onChange: (model: string) => void;
  ollamaModels: string[];
  catalog: AiModelCatalog;
  hints?: string[];
  allowEmpty?: boolean;
  emptyLabel?: string;
};

function pickHintMatches(hints: string[], available: string[]): string[] {
  const picked: string[] = [];
  // Bereits aufgelöste exakte Modellnamen (vom API-Katalog)
  for (const hint of hints) {
    if (picked.length >= 3) break;
    const exact = available.find((m) => m === hint);
    if (exact && !picked.includes(exact)) picked.push(exact);
  }
  if (picked.length >= 3) return picked;
  for (const hint of hints) {
    if (picked.length >= 3) break;
    const token = hint.split(":")[0].toLowerCase();
    const match = available.find((model) => {
      if (picked.includes(model)) return false;
      const lower = model.toLowerCase();
      if (lower === hint.toLowerCase()) return true;
      if (hint.includes(":")) return false;
      return lower.startsWith(`${token}:`) || lower.startsWith(`${token}-`);
    });
    if (match) picked.push(match);
  }
  return picked;
}

export function ModelSelect({
  provider,
  taskKey,
  value,
  onChange,
  ollamaModels,
  catalog,
  hints = [],
  allowEmpty = true,
  emptyLabel = "Empfehlung (automatisch)",
}: Props) {
  const [showAll, setShowAll] = useState(false);
  const name = provider.toLowerCase();

  const allModels = useMemo(() => {
    if (name === "ollama") return ollamaModels;
    if (name === "openai") {
      const block = catalog.openai;
      if (taskKey === "tts") return block.tts;
      if (taskKey === "vision") return block.vision.length ? block.vision : block.chat;
      return block.chat;
    }
    if (name === "anthropic") {
      const block = catalog.anthropic;
      return block.chat.length ? block.chat : block.vision;
    }
    return [];
  }, [name, taskKey, ollamaModels, catalog]);

  const recommended = useMemo(
    () => pickHintMatches(hints, allModels).slice(0, 3),
    [hints, allModels],
  );

  if (name === "ollama") {
    if (ollamaModels.length === 0) {
      return <span className="muted">Ollama nicht erreichbar</span>;
    }
  } else if (name === "openai") {
    const block = catalog.openai;
    if (!block.ok || allModels.length === 0) {
      return (
        <span className="muted">
          OpenAI-Modelle nicht geladen{block.error ? `: ${block.error}` : ""}
        </span>
      );
    }
  } else if (name === "anthropic") {
    const block = catalog.anthropic;
    if (!block.ok || allModels.length === 0) {
      return (
        <span className="muted">
          Anthropic-Modelle nicht geladen{block.error ? `: ${block.error}` : ""}
        </span>
      );
    }
  } else {
    return <span className="muted">Provider wählen</span>;
  }

  const extras = allModels.filter((m) => !recommended.includes(m));
  const showExtras = showAll || (value && !recommended.includes(value) && !extras.includes(value));

  return (
    <div className="model-select-wrap">
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {allowEmpty && <option value="">{emptyLabel}</option>}
        {recommended.map((m, index) => (
          <option key={m} value={m}>
            {index + 1}. {m}
            {index === 0 ? " (beste Wahl)" : ""}
          </option>
        ))}
        {value && !recommended.includes(value) && (
          <option value={value}>Aktuell: {value}</option>
        )}
        {showExtras &&
          extras
            .filter((m) => m !== value)
            .map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
      </select>
      {!showAll && extras.length > 0 && (
        <button type="button" className="ghost model-select-more" onClick={() => setShowAll(true)}>
          Alle {allModels.length} Modelle…
        </button>
      )}
    </div>
  );
}
