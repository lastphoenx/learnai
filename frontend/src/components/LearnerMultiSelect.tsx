"use client";

import type { LearnerProfile } from "@/lib/api";

type Props = {
  profiles: LearnerProfile[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  label?: string;
};

export function LearnerMultiSelect({ profiles, selectedIds, onChange, label }: Props) {
  const childProfiles = profiles.filter((p) => p.is_child_profile);
  const targets = childProfiles.length > 0 ? childProfiles : profiles;
  const allSelected = targets.length > 0 && targets.every((p) => selectedIds.includes(p.id));

  function toggleAll() {
    if (allSelected) {
      onChange([]);
    } else {
      onChange(targets.map((p) => p.id));
    }
  }

  function toggleOne(id: string) {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((x) => x !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  }

  if (targets.length === 0) return null;

  return (
    <div className="learner-multi-select">
      <span className="learner-multi-label">{label || "Zuweisen an"}</span>
      <div className="learner-multi-options">
        {targets.length > 1 && (
          <label className="learner-check-row">
            <input type="checkbox" checked={allSelected} onChange={toggleAll} />
            <span>Alle Kinder</span>
          </label>
        )}
        {targets.map((p) => (
          <label key={p.id} className="learner-check-row">
            <input
              type="checkbox"
              checked={selectedIds.includes(p.id)}
              onChange={() => toggleOne(p.id)}
            />
            <span>
              {p.display_name}
              {p.is_child_profile ? "" : " (Profil)"}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
