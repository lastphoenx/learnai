# LearnAI — Hinweise für KI-Assistenten (Cursor, Copilot, …)

## Git & Branches (Pflicht — immer gleicher Ablauf)

Quelle der Wahrheit: `doku/pve2/vm/135-learnai/betrieb.md`

| Was | Branch | CT 135 |
|-----|--------|--------|
| **Produktion / Live-Bug** | `main` (oder kurzer `fix/…` **von** `main`) | `git pull origin main` — **nie** Feature-Branches pullen |
| **Unfertiges Feature** (aktuell: Golden Set) | `feature/task-type-golden` | erst mergen, wenn live |
| **Konzept, noch nicht begonnen** (Eltern-KI/BYOK) | frischer `feature/parent-ai-access` **von** `main`, wenn es losgeht | — |

### Live-Fix — Checkliste (jedes Mal, in dieser Reihenfolge)

```powershell
cd learnai
git fetch origin
git checkout -f main
git pull origin main
git checkout -b fix/kurzbeschreibung
# … ändern …
git add …
git commit -m "fix: …"
git push -u origin fix/kurzbeschreibung
git checkout main
git merge --ff-only fix/kurzbeschreibung
git push origin main
git push origin --delete fix/kurzbeschreibung
```

**Branch nach jedem Merge löschen** (`git push origin --delete <branch>` im selben Atemzug wie der Merge auf `main`). Ein Branch pro Thema — kein `fix/…` auf einem Feature-Branch weiterbauen.

**Nicht:** `git push origin <sha>:main` (Refspec-Hack), Merge ohne vorher `git pull`, Feature-Branch auf CT deployen, `main` vergessen nachzuziehen, gemergte Branches liegen lassen.

### Windows: Checkout blockiert durch `scripts/generate_keys.py`

Index ist **LF** (`git ls-files --eol` → `i/lf`). Phantom-«modified» kommt von Editor/Checkout, nicht vom Repo — **nicht committen.**

```powershell
git checkout -f -B <branch> origin/<branch>
```

Abdeckung wie SlitProjektHub: `.gitattributes` (`*.py text eol=lf`) + `.editorconfig` (`end_of_line = lf`). Kein `core.autocrlf` anfassen.

### Deploy CT 135 (nach `main`-Push)

```bash
cd /opt/learnai && git pull origin main && bash scripts/deploy.sh
```

Lokales Repo nach Prod-Fix: `git checkout feature/task-type-golden` (oder anderen aktiven Feature-Branch) und `git merge origin/main`.

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

## Aufgabentyp Golden Set (Pflicht)

Bei Arbeit an **Generierung**, **Aufgabentypen**, **Modul-Validierung** oder **Trainer-Output**:

1. Prüfe `backend/app/fixtures/task_type_golden/` — jeder Aufgabentyp braucht mindestens ein Fixture (`mixed`, `explain`, `quiz`, `practice`, `math`, `workbook`, `review`, `exam`, `vocab`, `interactive`).
2. Fixture = eingefrorener `modules`-JSON-Output (nicht verschlüsselte DB-Unit).
3. `_meta` enthält mindestens `task_type` und `subject_hint`; für `interactive` optional `min_cards` / `min_questions`.
4. Validierung nutzt die bestehenden Produktions-Checks (`_validate_modules`, `validate_interactive_modules`, `explanation_has_derivation`, typ-spezifische Regeln für `exam`/`vocab`).
5. Tests: `pytest backend/tests/test_task_type_golden.py`
6. **Grenze:** Struktur/Regeln am Fixture — keine Live-KI-Regression (wie beim Pedagogy-Set).

Seed-Skripte: `backend/scripts/seed_task_type_golden_fixtures.py` (Python) oder `.ps1` (Windows ohne Python).

## Referenz-Codes & Qualitätsreport

Jede Lerneinheit erhält lesbare Codes in `reconstruction_encrypted`:

- `reference_family` / `0001` — Familie (Vorlage + alle Kinder-Kopien)
- `reference_code` / `0001.0001` — Instanz (z. B. Giulia)

Bei neuen Einheiten/Kopien automatisch vergeben; bestehende beim ersten Laden nachgezogen.

- Anzeige: Badge **Ref 0001.0001** auf der Einheitsseite (Admin + Schüler)
- Report: `/admin/unit-report` oder `python scripts/unit_quality_report.py 0001.0001`
- `0001` = Quiz/Lösungsvarianten der Familie; `0001.0001` = plus Lernfortschritt

**Bewusst nicht Teil des Golden Sets:** Live-Foto-Regression (Vision End-to-End) — separates späteres Thema.

## Tests (Pflicht — aber nicht auf Windows raten)

**Lokal Windows:** Kein Python/pytest verfügbar (nur Microsoft-Store-Alias). **Nicht** wiederholt `python`/`py` probieren.

**Stattdessen:**
1. **GitHub CI** nach Push (`/.github/workflows/ci.yml`) — Ergebnis abwarten oder im PR prüfen.
2. **CT 135 (Prod-VM):** `cd /opt/learnai && docker compose exec -T api python -m pytest tests/test_units.py tests/test_unit_reference.py -q`

Vollständiger Lauf lokal nur mit echtem Python oder Docker: `cd backend && python -m pytest tests/ -q` (siehe `DEVELOPER.md`).

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
