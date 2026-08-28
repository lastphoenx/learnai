# LearnAI — Hinweise für KI-Assistenten (Cursor, Copilot, …)

## Git & Branches (Pflicht — immer gleicher Ablauf)

Quelle der Wahrheit: `doku/pve2/vm/135-learnai/betrieb.md`

| Was | Branch | CT 135 |
|-----|--------|--------|
| **Produktion / Live-Bug** | **direkt `main`** | `git pull origin main` — **nie** Feature-Branches pullen |
| **Unfertiges Feature** (Golden Set, …) | `feature/task-type-golden` | erst mergen, wenn live |

**Keine einmaligen `fix/…`-Branches** für kleine Live-Fixes. Commit + Push auf `main`. Einen `fix/…`-Branch nur, wenn der Nutzer ihn ausdrücklich will oder die Änderung unsicher/reviewbedürftig ist — **nach Merge auf `main` sofort löschen** (`git push origin --delete <branch>` und `git branch -d <branch>`).

### Live-Fix — Checkliste (direkt auf main)

```powershell
cd learnai
git fetch origin
git checkout -f main
git pull origin main
# … ändern …
git add …
git commit -m "fix: …"
git push origin main
```

Wenn gerade auf `feature/task-type-golden` weitergearbeitet wird: `main` danach dort einmergen (nicht umgekehrt auf CT deployen).

**Nicht:** `git push origin <sha>:main` (Refspec-Hack), Merge ohne vorher `git pull`, Feature-Branch auf CT deployen, gemergte `fix/…`-Branches stehen lassen.

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

Lokales Repo nach Prod-Fix: auf `main` bleiben, ausser der Nutzer arbeitet am Feature-Branch.

## Pedagogy Golden Set (Pflicht)

Bei Arbeit an **Didaktik**, **source_pedagogy**, **Pedagogy-Prompts**, **neuen Fach-Schwerpunkten** oder **interaktivem Trainer**:

1. Prüfe `backend/app/fixtures/pedagogy_golden/` — jede Fachgruppe braucht mindestens ein Fixture:
   - `math`, `language`, `nmg`, `german`, `nature` (siehe `app/ai/subject_focus.py`)
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
