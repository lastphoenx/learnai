"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { clampWorkshopMode, type WorkshopModelUnlockResult } from "@/lib/workshop/workshopCapabilities";

type UseWorkshopFlowParams<TMode extends string, TUnlockCtx> = {
  hints: string[];
  initialMode: TMode;
  unlockContext: TUnlockCtx;
  resolveModelUnlock: (ctx: TUnlockCtx & { unlockedHintIds: string[] }) => WorkshopModelUnlockResult<TMode>;
  canUnlockHint?: (hintId: string) => boolean;
  onHintUnlocked?: (hintId: string) => void;
};

export function useWorkshopFlow<TMode extends string, TUnlockCtx>({
  hints,
  initialMode,
  unlockContext,
  resolveModelUnlock,
  canUnlockHint,
  onHintUnlocked,
}: UseWorkshopFlowParams<TMode, TUnlockCtx>) {
  const [unlockedHintCount, setUnlockedHintCount] = useState(0);
  const [modelMode, setModelMode] = useState<TMode>(initialMode);
  const [overlayActive, setOverlayActive] = useState(false);

  const unlockedHintIds = useMemo(
    () => hints.slice(0, Math.max(0, unlockedHintCount)),
    [hints, unlockedHintCount],
  );

  const modelUnlock = useMemo(
    () => resolveModelUnlock({ ...unlockContext, unlockedHintIds }),
    [resolveModelUnlock, unlockContext, unlockedHintIds],
  );

  useEffect(() => {
    const clamped = clampWorkshopMode(modelMode, modelUnlock.unlockedModes, initialMode);
    if (clamped !== modelMode) setModelMode(clamped);
  }, [modelMode, modelUnlock.unlockedModes, initialMode]);

  useEffect(() => {
    if (!modelUnlock.solutionOverlayAllowed && overlayActive) {
      setOverlayActive(false);
    }
  }, [modelUnlock.solutionOverlayAllowed, overlayActive]);

  const nextHintId = hints[unlockedHintCount];
  const nextHintAllowed = Boolean(nextHintId && (canUnlockHint?.(nextHintId) ?? true));

  const unlockNextHint = useCallback(() => {
    const id = hints[unlockedHintCount];
    if (!id || !(canUnlockHint?.(id) ?? true)) return;
    setUnlockedHintCount((n) => Math.min(n + 1, hints.length));
    onHintUnlocked?.(id);
  }, [hints, unlockedHintCount, canUnlockHint, onHintUnlocked]);

  return {
    unlockedHintCount,
    unlockedHintIds,
    modelMode,
    setModelMode,
    overlayActive,
    setOverlayActive,
    modelUnlock,
    nextHintId,
    nextHintAllowed,
    unlockNextHint,
  };
}
