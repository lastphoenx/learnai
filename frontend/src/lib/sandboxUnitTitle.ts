import type { LearningUnit } from "@/lib/api";

export function sandboxUnitTitle(
  unit: Pick<LearningUnit, "title" | "is_sandbox_copy">,
): string {
  const title = (unit.title || "").trim();
  if (!unit.is_sandbox_copy) return title;
  if (/^test-kopie\s*:/i.test(title)) {
    return title.replace(/^test-kopie\s*:/i, "Test-Kopie:");
  }
  if (/^test\s*:/i.test(title)) {
    const rest = title.replace(/^test\s*:/i, "");
    return `Test-Kopie:${rest.startsWith(" ") || rest === "" ? rest : ` ${rest}`}`;
  }
  return `Test-Kopie: ${title}`;
}
