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
      sameTemplateFamily(unit, opts.currentUnit),
  );
}
