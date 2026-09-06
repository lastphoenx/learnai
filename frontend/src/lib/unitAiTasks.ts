/** Spiegel von backend AI_TASK_FOR_UNIT + vision für Quellenanalyse. */
export const AI_TASK_FOR_UNIT: Record<string, string> = {
  mixed: "mixed",
  explain: "explain",
  quiz: "quiz",
  practice: "practice",
  math: "practice",
  workbook: "practice",
  review: "quiz",
  exam: "exam",
  vocab: "vocab",
  interactive: "mixed",
};

export function unitAiTaskKeys(taskType: string | undefined, sourceCount: number): string[] {
  const main = AI_TASK_FOR_UNIT[taskType || "mixed"] || "mixed";
  const keys = [main];
  if (sourceCount > 0) keys.push("vision");
  return [...new Set(keys)];
}

export function providerLabel(provider: string): string {
  if (provider === "ollama") return "Ollama";
  if (provider === "openai") return "OpenAI";
  if (provider === "anthropic") return "Anthropic";
  return provider;
}

export type AiSettingSource = "child" | "adult" | "catalog" | "env" | "unit";

export function aiSourceLabel(source: AiSettingSource | string | undefined): string {
  if (source === "child") return "Kind";
  if (source === "adult") return "Vererbt";
  if (source === "unit") return "Einheit";
  if (source === "env") return "Server";
  return "Katalog";
}

export function aiSourceBadgeClass(source: AiSettingSource | string | undefined): string {
  if (source === "child") return "unit-ai-source--child";
  if (source === "adult") return "unit-ai-source--adult";
  if (source === "unit") return "unit-ai-source--unit";
  if (source === "env") return "unit-ai-source--env";
  return "unit-ai-source--catalog";
}
