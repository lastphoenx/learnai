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
