# Aufgabentyp Golden Set

Eingefrorene Beispiel-Outputs der Generierungs-Pipeline (ein Fixture pro `task_type`).

## Grenze

Prüft **Struktur und Qualitätsregeln** am committed Beispiel — **nicht**, ob die aktuell laufende KI heute noch genauso gut generiert (kein Live-Aufruf in CI).

## Workflow

1. Gute echte Generierung exportieren oder `scripts/seed_task_type_golden_fixtures.ps1` als Startpunkt nutzen.
2. Fixture unter `backend/app/fixtures/task_type_golden/<task_type>.json` ablegen.
3. `_meta.task_type` und optional `subject_hint`, `min_cards` / `min_questions` (nur interactive) setzen.
4. `pytest tests/test_task_type_golden.py` muss grün sein.

## Abdeckung

Mindestens ein Fixture pro Aufgabentyp: mixed, explain, quiz, practice, math, workbook, review, exam, vocab, interactive.
