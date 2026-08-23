"use client";

import { useCallback, useSyncExternalStore } from "react";
import type { User } from "@/lib/api";

const KEY = "learnai.previewChildUi";
const EVENT = "learnai-child-preview";

function emit() {
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(onStoreChange: () => void) {
  window.addEventListener(EVENT, onStoreChange);
  return () => window.removeEventListener(EVENT, onStoreChange);
}

function getSnapshot() {
  return sessionStorage.getItem(KEY) === "1";
}

function getServerSnapshot() {
  return false;
}

/** Admin-only: Seitenaufbau wie ein Kinder-Account (Navigation, ausgeblendete Blöcke). */
export function useChildPreview(user: User | null | undefined) {
  const stored = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const canPreview = Boolean(user?.is_admin) && !user?.is_child;
  const preview = canPreview && stored;
  const asChild = Boolean(user?.is_child) || preview;

  const togglePreview = useCallback(() => {
    sessionStorage.setItem(KEY, stored ? "0" : "1");
    emit();
  }, [stored]);

  return { asChild, canPreview, preview, togglePreview };
}
