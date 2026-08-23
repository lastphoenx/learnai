# LearnAI — Hinweise für KI-Assistenten (Cursor, Copilot, …)

## Pedagogy Golden Set (Pflicht)

Bei Arbeit an **Didaktik**, **source_pedagogy**, **Pedagogy-Prompts**, **neuen Fach-Schwerpunkten** oder **interaktivem Trainer**:

1. Prüfe `backend/app/fixtures/pedagogy_golden/` — jede Fachgruppe braucht mindestens ein Fixture:
   - `math`, `language`, `mgu`, `german`, `nature` (siehe `app/ai/subject_focus.py`)
2. Neues/angepasstes Thema → Fixture anlegen oder aktualisieren (`<thema>.json`).
3. Jedes Fixture enthält `_meta`:
   ```json
   "_meta": {
     "subject_group": "math",
     "subject_hint": "Kurzbeschreibung",
     "min_method_labels": 2
   }
   ```
4. Inhalt = realistisches Didaktik-JSON (nach Vision-Extraktion), **keine Schema-Platzhalter**.
5. Tests laufen lassen: `pytest backend/tests/test_pedagogy_golden.py backend/tests/test_pedagogy_golden_service.py`
6. **Immer mit committen** — der Nutzer bearbeitet kein JSON manuell.

Admin-UI (`/admin/golden-set`) ist **read-only**: zeigt nur Testergebnis + kopierbaren Report für die KI.

## Referenz-Codes & Qualitätsreport

Jede Lerneinheit erhält lesbare Codes in `reconstruction_encrypted`:

- `reference_family` / `0001` — Familie (Vorlage + alle Kinder-Kopien)
- `reference_code` / `0001.0001` — Instanz (z. B. Giulia)

Bei neuen Einheiten/Kopien automatisch vergeben; bestehende beim ersten Laden nachgezogen.

- Anzeige: Badge **Ref 0001.0001** auf der Einheitsseite (Admin + Schüler)
- Report: `/admin/unit-report` oder `python scripts/unit_quality_report.py 0001.0001`
- `0001` = Quiz/Lösungsvarianten der Familie; `0001.0001` = plus Lernfortschritt

**Bewusst nicht Teil des Golden Sets:** Live-Foto-Regression (Vision End-to-End) — separates späteres Thema.

## Deploy-Hinweis

- Nur `backend/app/` geändert → `docker compose restart api worker`
- `requirements.txt` / Dockerfile → `docker compose build api worker` + `up -d`
- Frontend → `docker compose build frontend` + `up -d frontend`

Siehe `docs/RUNBOOK.md`.

## Trainer-UI

- Check, Lernkarten und Übungsaufgaben teilen die **Sprungleiste** (`JumpStrip.tsx`). Keine extra Zurück/Weiter-Zeile wieder einbauen.
- Offene Nummern **neutral/grau**, nicht Akzentgrün. Grün/Rot nur nach Bewertung.
- Inhalt (Frage, Optionen, Eingabe) in ~36rem, nicht auf 27" strecken.
- Admin-Vorschau Kinder-Navigation: `frontend/src/lib/childPreview.ts` (Kopfzeile «Kind-Ansicht»).
