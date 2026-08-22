"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { assignUnitToProfiles, fetchUnits, type LearnerProfile, type LearningUnit } from "@/lib/api";
import { LearnerMultiSelect } from "@/components/LearnerMultiSelect";
import { siblingCopyForProfile } from "@/lib/unitTemplateFamily";

type Props = {
  unitId: string;
  currentUnit: Pick<LearningUnit, "id" | "template_root_id">;
  currentProfileId: string | null | undefined;
  learnerName?: string | null;
  profiles: LearnerProfile[];
  onAssigned: () => void;
  onRequestRemove?: () => void;
};

export function UnitAssignSection({
  unitId,
  currentUnit,
  currentProfileId,
  learnerName,
  profiles,
  onAssigned,
  onRequestRemove,
}: Props) {
  const [allUnits, setAllUnits] = useState<LearningUnit[]>([]);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const children = useMemo(
    () => profiles.filter((p) => p.is_child_profile),
    [profiles],
  );

  useEffect(() => {
    fetchUnits()
      .then(setAllUnits)
      .catch(() => setAllUnits([]));
  }, [unitId, message]);

  const unitForMatch = useMemo(
    () => allUnits.find((u) => u.id === unitId) || ({ ...currentUnit, id: unitId } as LearningUnit),
    [allUnits, currentUnit, unitId],
  );

  const assignableIds = useMemo(() => {
    return children
      .filter((child) => {
        if (child.id === currentProfileId) return false;
        return !siblingCopyForProfile(allUnits, {
          currentUnit: unitForMatch,
          profileId: child.id,
        });
      })
      .map((child) => child.id);
  }, [allUnits, children, currentProfileId, unitForMatch]);

  async function onAssign() {
    const ids = selected.filter((id) => assignableIds.includes(id));
    if (!ids.length) {
      setError("Bitte mindestens ein Kind ohne Kopie wählen.");
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
    <section className="card unit-section unit-assign-section">
      <h2>Kinder & Kopien</h2>
      <p className="muted section-lead">
        Jede Lerneinheit gehört genau einem Kind. Für weitere Kinder wird eine vollständige Kopie erstellt
        (eigener Fortschritt, gleiche Inhalte). Die Zuordnung aufheben = diese Kopie löschen.
      </p>

      {children.length === 1 && (
        <p className="muted empty-hint">
          Nur ein Kind im Haushalt. Um Kopien für Geschwister anzulegen, zuerst ein weiteres Kind unter{" "}
          <Link href="/settings">Einstellungen</Link> anlegen.
        </p>
      )}

      {currentProfileId ? (
        <p className="unit-assign-current">
          <span className="badge badge-neutral">Diese Kopie</span>
          <strong>{learnerName || "Zugewiesenes Kind"}</strong>
        </p>
      ) : (
        <p className="muted">Kein Kind zugewiesen — beim Erstellen oder per Kopie zuweisen.</p>
      )}

      {children.length === 0 ? (
        <p className="muted empty-hint">
          Noch keine Kinder-Profile. Unter <Link href="/settings">Einstellungen</Link> oder Admin → Benutzer
          Kind-Accounts anlegen.
        </p>
      ) : (
        <ul className="unit-assign-children">
          {children.map((child) => {
            const isCurrent = child.id === currentProfileId;
            const sibling = siblingCopyForProfile(allUnits, {
              currentUnit: unitForMatch,
              profileId: child.id,
            });
            return (
              <li key={child.id} className="unit-assign-child-row">
                <span>{child.display_name}</span>
                <div className="unit-assign-child-actions">
                  {isCurrent ? (
                    <>
                      <span className="badge badge-ready">aktuelle Einheit</span>
                      {onRequestRemove ? (
                        <button type="button" className="btn btn-sm ghost danger-text" onClick={onRequestRemove}>
                          Zuordnung aufheben…
                        </button>
                      ) : null}
                    </>
                  ) : sibling ? (
                    <Link className="btn btn-sm" href={`/units/${sibling.id}`}>
                      Kopie öffnen
                    </Link>
                  ) : (
                    <span className="muted">noch keine Kopie</span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {message && <p className="muted">{message}</p>}

      {children.length > 1 && assignableIds.length > 0 && (
        <>
          {!open ? (
            <button type="button" className="btn btn-primary" onClick={() => setOpen(true)}>
              Kopie für weiteres Kind erstellen
            </button>
          ) : (
            <div className="stack">
              <LearnerMultiSelect
                profiles={children.filter((c) => assignableIds.includes(c.id))}
                selectedIds={selected}
                onChange={setSelected}
                label="Kinder ohne Kopie"
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
        </>
      )}

      {children.length > 1 && assignableIds.length === 0 && !message && (
        <p className="muted empty-hint">Alle Kinder haben bereits eine Kopie dieser Einheit.</p>
      )}
    </section>
  );
}
