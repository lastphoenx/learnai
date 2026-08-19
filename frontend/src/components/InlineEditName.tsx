"use client";

import { FormEvent, useState } from "react";

type Props = {
  value: string;
  placeholder?: string;
  emptyLabel?: string;
  onSave: (name: string) => Promise<void>;
  disabled?: boolean;
};

export function InlineEditName({
  value,
  placeholder = "Name",
  emptyLabel = "ohne Namen",
  onSave,
  disabled,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEdit() {
    if (disabled) return;
    setDraft(value);
    setError(null);
    setEditing(true);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSave(draft.trim());
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  if (editing) {
    return (
      <form className="inline-name-form" onSubmit={submit}>
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={placeholder}
          disabled={busy}
        />
        <button type="submit" disabled={busy}>
          OK
        </button>
        <button type="button" className="ghost" disabled={busy} onClick={() => setEditing(false)}>
          Abbrechen
        </button>
        {error && <span className="err">{error}</span>}
      </form>
    );
  }

  return (
    <span className="inline-name">
      <strong>{value.trim() || emptyLabel}</strong>
      {!disabled && (
        <button
          type="button"
          className="icon-btn"
          title="Name bearbeiten"
          aria-label="Name bearbeiten"
          onClick={startEdit}
        >
          ✎
        </button>
      )}
    </span>
  );
}
