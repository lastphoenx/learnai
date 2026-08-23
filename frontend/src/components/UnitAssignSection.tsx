"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  assignUnitToProfiles,
  fetchUnits,
  patchUnitProfile,
  type LearnerProfile,
  type LearningUnit,
} from "@/lib/api";
import { LearnerMultiSelect } from "@/components/LearnerMultiSelect";
import { siblingCopyForProfile } from "@/lib/unitTemplateFamily";

type Props = {
  unitId: string;
  currentUnit: Pick<
    LearningUnit,
    "id" | "template_root_id" | "is_sandbox_copy" | "sandbox_copy_of" | "title"
  >;
  currentProfileId: string | null | undefined;
  learnerName?: string | null;
  profiles: LearnerProfile[];
  onAssigned: () => void;
};

export function UnitAssignSection({
  unitId,
  currentUnit,
  currentProfileId,
  learnerName,
  profiles,
  onAssigned,
}: Props) {
  const [allUnits, setAllUnits] = useState<LearningUnit[]>([]);
  const [copyOpen, setCopyOpen] = useState(false);
  const [selectedCopyIds, setSelectedCopyIds] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const isSandbox = Boolean(currentUnit.is_sandbox_copy);

  const children = useMemo(
    () => profiles.filter((p) => p.is_child_profile),
    [profiles],
  );

  const adults = useMemo(
    () => profiles.filter((p) => !p.is_child_profile),
    [profiles],
  );

  useEffect(() => {
    fetchUnits()
      .then(setAllUnits)
      .catch(() => setAllUnits([]));
  }, [unitId, message, currentProfileId]);

  const unitForMatch = useMemo(() => {
    const fetched = allUnits.find((u) => u.id === unitId);
    if (!fetched) {
      return { ...currentUnit, id: unitId } as LearningUnit;
    }
    return { ...fetched, ...currentUnit, id: unitId };
  }, [allUnits, currentUnit, unitId]);

  const assignableCopyIds = useMemo(() => {
    if (isSandbox) return [];
    return children
      .filter((child) => {
        if (child.id === currentProfileId) return false;
        return !siblingCopyForProfile(allUnits, {
          currentUnit: unitForMatch,
          profileId: child.id,
        });
      })
      .map((child) => child.id);
  }, [allUnits, children, currentProfileId, isSandbox, unitForMatch]);

  async function onUnassign() {
    setBusy(true);
    setError(null);
    try {
      await patchUnitProfile(unitId, null);
      setMessage(
        isSandbox
          ? "Test-Zuordnung aufgehoben."
          : "Zuordnung aufgehoben — Einheit ist keinem Kind mehr zugewiesen.",
      );
      onAssigned();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Zuordnung konnte nicht aufgehoben werden");
    } finally {
      setBusy(false);
    }
  }

  async function onAssignTo(profileId: string) {
    setBusy(true);
    setError(null);
    try {
      await patchUnitProfile(unitId, profileId);
      const profile = profiles.find((p) => p.id === profileId);
      setMessage(
        profile
          ? isSandbox
            ? `Test-Kopie zugewiesen an ${profile.display_name}.`
            : `Zugewiesen an ${profile.display_name}.`
          : "Profil zugewiesen.",
      );
      onAssigned();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Zuweisung fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onCreateCopies() {
    const ids = selectedCopyIds.filter((id) => assignableCopyIds.includes(id));
    if (!ids.length) {
      setError("Bitte mindestens ein Kind ohne Kopie wählen.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await assignUnitToProfiles(unitId, ids);
      setMessage(`${res.created_count} Kopie(n) für weitere Kinder erstellt.`);
      setCopyOpen(false);
      setSelectedCopyIds([]);
      onAssigned();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kopien konnten nicht erstellt werden");
    } finally {
      setBusy(false);
    }
  }

  const originalId = currentUnit.sandbox_copy_of;

  return (
    <section className="card unit-section unit-assign-section">
      <h2>{isSandbox ? "Test-Kopie & Zuweisung" : "Kinder & Zuweisung"}</h2>
      {isSandbox ? (
        <p className="muted section-lead">
          Sandbox-Kopie mit eigenem Fortschritt — zum Testen ohne den Fortschritt eines Kindes zu
          verändern. Zuweisung an Eltern/Admin oder Lernen ohne Zuweisung (mit deinem Profil).
        </p>
      ) : (
        <p className="muted section-lead">
          Diese Einheit kann genau einem Kind zugeordnet sein — oder vorübergehend keinem. Für ein
          zweites Kind wird eine Kopie erstellt (eigener Fortschritt).
        </p>
      )}

      {isSandbox && originalId && (
        <p className="unit-assign-original-link">
          <Link className="btn btn-sm" href={`/units/${originalId}`}>
            Original öffnen
          </Link>
        </p>
      )}

      {currentProfileId ? (
        <p className="unit-assign-current">
          <span className="badge badge-ready">Zugewiesen</span>
          <strong>{learnerName || "Profil"}</strong>
          <button type="button" className="btn btn-sm ghost" onClick={onUnassign} disabled={busy}>
            Zuordnung aufheben
          </button>
        </p>
      ) : (
        <p className="unit-assign-current">
          <span className="badge badge-neutral">Nicht zugewiesen</span>
          <span className="muted">
            {isSandbox ? "Zum Testen unten zuweisen oder direkt lernen" : "Kein Kind — unten zuweisen"}
          </span>
        </p>
      )}

      {isSandbox && adults.length > 0 && (
        <>
          <h3 className="unit-assign-subhead">Zum Testen zuweisen</h3>
          <ul className="unit-assign-children">
            {adults.map((adult) => {
              const isCurrent = adult.id === currentProfileId;
              return (
                <li key={adult.id} className="unit-assign-child-row">
                  <span>{adult.display_name}</span>
                  <div className="unit-assign-child-actions">
                    {isCurrent ? (
                      <span className="badge badge-ready">diese Test-Kopie</span>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-sm btn-primary"
                        onClick={() => onAssignTo(adult.id)}
                        disabled={busy}
                      >
                        Zum Testen zuweisen
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}

      {children.length === 0 ? (
        !isSandbox && (
          <p className="muted empty-hint">
            Noch keine Kinder-Profile. Unter <Link href="/settings">Einstellungen</Link>{" "}
            Kind-Accounts anlegen.
          </p>
        )
      ) : (
        <>
          {!isSandbox && <h3 className="unit-assign-subhead">Kinder</h3>}
          {isSandbox && children.length > 0 && (
            <h3 className="unit-assign-subhead">Kinder-Einheiten in dieser Familie</h3>
          )}
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
                      <span className="badge badge-ready">diese Einheit</span>
                    ) : sibling ? (
                      <Link className="btn btn-sm" href={`/units/${sibling.id}`}>
                        {isSandbox ? `${child.display_name}: Einheit öffnen` : "Kopie öffnen"}
                      </Link>
                    ) : !currentProfileId && !isSandbox ? (
                      <button
                        type="button"
                        className="btn btn-sm btn-primary"
                        onClick={() => onAssignTo(child.id)}
                        disabled={busy}
                      >
                        Zuweisen
                      </button>
                    ) : isSandbox ? (
                      <span className="muted">keine Kopie</span>
                    ) : (
                      <span className="muted">noch keine Kopie</span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}

      {message && <p className="muted">{message}</p>}
      {error && <p className="err">{error}</p>}

      {!isSandbox && currentProfileId && children.length > 1 && assignableCopyIds.length > 0 && (
        <>
          {!copyOpen ? (
            <button type="button" className="btn" onClick={() => setCopyOpen(true)} disabled={busy}>
              Kopie für weiteres Kind erstellen
            </button>
          ) : (
            <div className="stack">
              <LearnerMultiSelect
                profiles={children.filter((c) => assignableCopyIds.includes(c.id))}
                selectedIds={selectedCopyIds}
                onChange={setSelectedCopyIds}
                label="Kinder ohne Kopie"
              />
              <div className="filter-row">
                <button type="button" className="btn-primary" onClick={onCreateCopies} disabled={busy}>
                  {busy ? "Erstelle…" : "Kopien erstellen"}
                </button>
                <button type="button" className="ghost" onClick={() => setCopyOpen(false)} disabled={busy}>
                  Abbrechen
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {!isSandbox &&
        currentProfileId &&
        children.length > 1 &&
        assignableCopyIds.length === 0 &&
        !message && (
          <p className="muted empty-hint">Alle anderen Kinder haben bereits eine Kopie.</p>
        )}
    </section>
  );
}
