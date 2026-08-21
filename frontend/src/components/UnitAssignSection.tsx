"use client";

import { useState } from "react";
import { assignUnitToProfiles, type LearnerProfile } from "@/lib/api";
import { LearnerMultiSelect } from "@/components/LearnerMultiSelect";

type Props = {
  unitId: string;
  currentProfileId: string | null | undefined;
  profiles: LearnerProfile[];
  onAssigned: () => void;
};

export function UnitAssignSection({ unitId, currentProfileId, profiles, onAssigned }: Props) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const available = profiles.filter(
    (p) => p.is_child_profile && p.id !== currentProfileId,
  );
  if (available.length === 0) return null;

  async function onAssign() {
    const ids = selected.filter((id) => id !== currentProfileId);
    if (!ids.length) {
      setError("Bitte mindestens ein Kind wählen.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await assignUnitToProfiles(unitId, ids);
      const withBlocks = (res.units || []).filter((u) => (u.module_count || 0) > 0).length;
      const blockHint =
        withBlocks > 0
          ? ` — ${withBlocks} mit Lernblöcken, sofort lernbereit`
          : "";
      setMessage(`${res.created_count} Kopie(n) erstellt${blockHint}.`);
      setOpen(false);
      setSelected([]);
      onAssigned();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Zuweisung fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card unit-section">
      <h2>Weitere Kinder zuweisen</h2>
      <p className="muted section-lead">
        Erstellt eine vollständige Kopie für andere Kinder: Quellen, Lernblöcke und Trainer-Inhalte —
        ohne erneute KI-Generierung. Jedes Kind hat eigenen Lernfortschritt.
      </p>
      {message && <p className="muted">{message}</p>}
      {!open ? (
        <button type="button" className="btn" onClick={() => setOpen(true)}>
          Anderen Kindern zuweisen
        </button>
      ) : (
        <div className="stack">
          <LearnerMultiSelect
            profiles={available}
            selectedIds={selected}
            onChange={setSelected}
            label="Kinder auswählen"
          />
          {error && <p className="err">{error}</p>}
          <div className="filter-row">
            <button type="button" className="btn-primary" onClick={onAssign} disabled={busy}>
              {busy ? "Erstelle…" : "Kopien erstellen"}
            </button>
            <button type="button" className="ghost" onClick={() => setOpen(false)} disabled={busy}>
              Abbrechen
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
