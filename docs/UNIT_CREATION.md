# Lerneinheit anlegen — Aufgabentypen & Schwerpunkte

Stand: 23. August 2026.

---

## UI-Flow (`/units/new`)

Felder mit **kontextuellen Vorlagen**: leere Felder zeigen Placeholder-Templates; darunter kurze Tipps (verschwinden beim Ausfüllen). Vorlagen passen sich an **Aufgabentyp** und **Schwerpunkt** an.

Implementierung: `frontend/src/lib/unitFieldHints.ts`, `frontend/src/components/UnitFieldGuide.tsx`.

### Empfohlene Reihenfolge

1. Titel
2. Aufgabentyp (`select_label` im Dropdown erklärt den Modus)
3. Schwerpunkt (wenn sichtbar)
4. Fach / Thema
5. Beschreibung / Auftrag an die KI
6. Sprache, Zielalter, Kinder, Schwierigkeit

---

## Aufgabentypen

Definiert in `backend/app/ai/task_types.py`. API: `GET /api/v1/units/task-types`.

| Key | Label (Badge) | Select-Label (Dropdown) |
|-----|---------------|-------------------------|
| `mixed` | Gemischt | Lerntext lesen → Quiz, Block für Block |
| `interactive` | Lerntrainer | Karten, Check, Eingabe-Übungen, Wissens-Hub |
| `math` | Rechnen | Mathe-Aufgaben mit Lösungsweg |
| `vocab` | Vokabeln | Fremdsprache: Wort, Bedeutung, Beispiel |
| … | … | … |

---

## Fach-Schwerpunkte

Definiert in `backend/app/ai/subject_focus.py`. Gespeichert im Rekonstruktions-JSON als `math_focus` (historischer Name, gilt für alle Fächer).

API liefert `focus_groups`:

```json
{
  "id": "language",
  "label": "Sprachen",
  "options": [{ "key": "lang_tenses_perf", "label": "Zeitformen: Perfekt / Passé composé" }]
}
```

### Gruppen

| ID | Fach-Erkennung (subject) | Optionen (Auszug) |
|----|--------------------------|-------------------|
| `math` | mathe, math, rechnen | decimals, fractions, geometry, … |
| `language` | franz, engl, sprach, vocab-Aufgabentyp | lang_vocab, lang_verbs, lang_tenses_* , … |
| `nmg` | nmg, mensch, gesellschaft, umwelt, mgu (legacy) | nmg_health, nmg_history, nmg_geography, … |
| `german` | deutsch | de_spelling, de_grammar, de_reading, … |
| `nature` | natur, biologie, physik | nt_biology, nt_physics, … |

`detect_focus_group(subject, task_type)` wählt die Gruppe. Frontend: `frontend/src/lib/subjectFocus.ts`.

Bei gesetztem Schwerpunkt hängt `augment_brief()` einen Hinweis an den Auftrag (`backend/app/ai/task_types.py`).

---

## Interaktiver Lerntrainer (`interactive`)

Nach «Mit KI aufbereiten»:

- **~50 Lernkarten** + **~50 Check-Fragen** (Zielwerte in `trainer_options`, Default 50/50)
- Karten: 30 % Merk, 30 % Kopf, 40 % Eingabe (`_split_card_kinds` in `generate_interactive.py`)
- UI-Tabs: Einstieg · Verstehen · Üben · **Check** (Quiz)
- Eingabe-Karten: STT via `SpeechInputButton` + Profil-`stt_provider` (Whisper lokal oder Browser)
- **Navigation:** Sprungleiste (eine Zeile, ‹ ›), keine Zurück/Weiter-Zeile. Offen = grau, richtig = Grün, falsch = Rot. **Später** schiebt ohne Bewertung ans Ende.
- Inhaltsspalte ~36rem (Tablet voll, grosse Monitore nicht strecken)
- Quiz-Varianten = Ableitungen mit Gleichungen (Badges «Aus dem Heft» / «Alternativer Weg»)
- Admin: Kopfzeile **Kind-Ansicht** simuliert Kinder-Navigation (sessionStorage)

Bestehende Einheiten ohne Neu-Generierung: keine `kind` auf Karten → alle = Kopf.

Implementierung: `frontend/src/components/learn/InteractiveTrainer.tsx`, `JumpStrip.tsx`, `CardInputExercise.tsx`, `frontend/src/lib/childPreview.ts`.

---

## Tests

- `backend/tests/test_quiz_explanation.py`
- `backend/tests/test_content_analysis.py`
- `backend/tests/test_quiz_numeric.py`

---

## Siehe auch

- [RUNBOOK.md](RUNBOOK.md) — Deploy
- [../CONCEPT.md](../CONCEPT.md) — Fachmodell
