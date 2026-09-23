import type { LearningUnit } from "@/lib/api";

export function templateRootId(unit: Pick<LearningUnit, "id" | "template_root_id">): string {
  return unit.template_root_id || unit.id;
}

export function sameTemplateFamily(
  a: Pick<LearningUnit, "id" | "template_root_id">,
  b: Pick<LearningUnit, "id" | "template_root_id">,
): boolean {
  return templateRootId(a) === templateRootId(b);
}

export function siblingCopyForProfile(
  units: LearningUnit[],
  opts: { currentUnit: LearningUnit; profileId: string },
): LearningUnit | undefined {
  return units.find(
    (unit) =>
      unit.id !== opts.currentUnit.id &&
      unit.profile_id === opts.profileId &&
      sameTemplateFamily(unit, opts.currentUnit) &&
      !unit.is_sandbox_copy,
  );
}

/** Vorlage zum Kopieren / Link «Original» — auch wenn sandbox_copy_of in alten Daten fehlt. */
export function familyContentSourceUnit(
  units: LearningUnit[],
  current: LearningUnit,
): LearningUnit | undefined {
  const fromSandbox = current.sandbox_copy_of;
  if (fromSandbox) {
    const hit = units.find((u) => u.id === fromSandbox);
    if (hit) return hit;
  }
  const templateId = current.template_unit_id;
  if (templateId && templateId !== current.id) {
    const hit = units.find((u) => u.id === templateId);
    if (hit) return hit;
  }
  return units.find(
    (u) =>
      u.id !== current.id &&
      sameTemplateFamily(u, current) &&
      !u.is_sandbox_copy &&
      !String(u.title || "")
        .toLowerCase()
        .startsWith("test-kopie:"),
  );
}

export function unitIdForChildCopySource(units: LearningUnit[], current: LearningUnit): string {
  return familyContentSourceUnit(units, current)?.id ?? current.id;
}
