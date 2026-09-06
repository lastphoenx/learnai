"use client";

import { useEffect, useState } from "react";
import { patchUnitLearnerRelease, type LearningUnit } from "@/lib/api";

export type LearnerReleaseInfo = NonNullable<LearningUnit["learner_release"]>;

export function learnerReleaseBadge(release: LearningUnit["learner_release"]) {
  if (!release?.targets_child) return null;
  if (release.released) {
    return { label: "Kind: freigegeben", className: "badge badge-ready" };
  }
  return { label: "Kind: gesperrt", className: "badge badge-fail" };
}

type Props = {
  unitId: string;
  release: LearnerReleaseInfo;
  compact?: boolean;
  disabled?: boolean;
  onUpdated?: (unit: LearningUnit) => void;
  onError?: (message: string) => void;
};

export function LearnerReleaseToggle({
  unitId,
  release,
  compact = false,
  disabled = false,
  onUpdated,
  onError,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [released, setReleased] = useState(release.released);

  useEffect(() => {
    setReleased(release.released);
  }, [release.released]);

  if (!release.targets_child) return null;

  async function onToggle(next: boolean) {
    if (busy || disabled) return;
    setBusy(true);
    try {
      const updated = await patchUnitLearnerRelease(unitId, next);
      const value = updated.learner_release?.released ?? next;
      setReleased(value);
      onUpdated?.(updated);
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Freigabe fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  return (
    <label
      className={`learner-release-toggle${compact ? " learner-release-toggle--compact" : ""}${busy ? " is-busy" : ""}`}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <span className="learner-release-toggle-text">
        {compact ? "Kind freigeben" : "Für Kind freigeben"}
      </span>
      <span className={`slide-switch${released ? " on" : ""}`} aria-hidden="true">
        <span className="slide-switch-knob" />
      </span>
      <input
        type="checkbox"
        role="switch"
        checked={released}
        disabled={busy || disabled}
        onChange={(e) => onToggle(e.target.checked)}
        aria-label={released ? "Für Kind freigegeben" : "Für Kind gesperrt"}
      />
      <span className={`learner-release-toggle-status${released ? " is-on" : ""}`}>
        {released ? "Freigegeben" : "Gesperrt"}
      </span>
    </label>
  );
}
