# Pedagogy Golden Set

Repo-only Regression für `parse_pedagogy_extraction` (Didaktik-JSON nach Vision).

## Für Menschen (Admin)

- Nur **Lesen**: `/admin/golden-set` zeigt Ergebnis und kopierbaren Report.
- Kein Anlegen/Bearbeiten in der UI — Änderungen nur via Git.

## Für die KI (Pflicht bei Pedagogy-/Themen-Arbeit)

Wenn du ein **neues Fach**, einen **neuen Schwerpunkt** oder die **Pedagogy-Pipeline** änderst:

1. Lege (oder aktualisiere) ein Fixture unter `backend/app/fixtures/pedagogy_golden/<name>.json`.
2. `_meta` setzen:
   - `subject_group`: einer von `math`, `language`, `mgu`, `german`, `nature`
   - `subject_hint`: kurze Beschreibung
   - `min_method_labels`: meist `2`
3. Inhalt = repräsentatives Vision-JSON (keine echten Schülerfotos nötig).
4. `pytest tests/test_pedagogy_golden.py` muss grün sein.
5. Fixture **mit committen**.

Ziel: Jede Fachgruppe aus `subject_focus.py` hat mindestens ein Fixture. CI und Admin-UI melden Lücken.

**Nicht abgedeckt (bewusst offen):** Echte Foto-Regression durch Live-Vision.
