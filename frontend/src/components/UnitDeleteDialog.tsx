"use client";

type Props = {
  open: boolean;
  unitTitle: string;
  learnerName?: string | null;
  busy?: boolean;
  onClose: () => void;
  onDelete: (purgeHistory: boolean) => void;
};

export function UnitDeleteDialog({
  open,
  unitTitle,
  learnerName,
  busy = false,
  onClose,
  onDelete,
}: Props) {
  if (!open) return null;

  const childHint = learnerName ? ` für ${learnerName}` : "";

  return (
    <div className="dialog-backdrop" role="presentation" onClick={busy ? undefined : onClose}>
      <div
        className="dialog card stack unit-delete-dialog"
        role="dialog"
        aria-labelledby="unit-delete-title"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="dialog-header">
          <h2 id="unit-delete-title">Einheit löschen</h2>
          <button type="button" className="icon-btn" onClick={onClose} disabled={busy} aria-label="Schließen">
            ✕
          </button>
        </div>

        <p>
          <strong>{unitTitle}</strong>
          {childHint}
        </p>

        <p className="muted">
          LearnAI speichert Lernfortschritt und Prüfungen getrennt von der Einheit. Wähle, ob der Verlauf
          erhalten bleiben oder mit gelöscht werden soll.
        </p>

        <div className="unit-delete-options stack">
          <button
            type="button"
            className="btn unit-delete-option"
            disabled={busy}
            onClick={() => onDelete(false)}
          >
            <strong>Nur diese Einheit löschen</strong>
            <span className="muted">
              Lernverlauf, Quiz-Ergebnisse und Prüfungen bleiben unter «Verlauf» sichtbar (empfohlen für
              Berichte).
            </span>
          </button>
          <button
            type="button"
            className="btn unit-delete-option unit-delete-option-danger"
            disabled={busy}
            onClick={() => onDelete(true)}
          >
            <strong>Komplett löschen</strong>
            <span className="muted">
              Einheit, zugehöriger Lernverlauf, Statistik, Events und Prüfungseinträge zu dieser Einheit
              unwiderruflich entfernen.
            </span>
          </button>
        </div>

        <div className="dialog-actions">
          <button type="button" className="ghost" onClick={onClose} disabled={busy}>
            Abbrechen
          </button>
        </div>
      </div>
    </div>
  );
}
