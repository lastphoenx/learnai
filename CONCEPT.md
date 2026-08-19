# LearnAI — Konzept & Roadmap

Stand: ergänzt um Lückenanalyse (Prüfungen, Fehlermuster, Nacharbeit).

Siehe auch [README.md](README.md) (Ist-Stand) und [FOUNDATION.md](FOUNDATION.md) (technische Basis).

---

## Kernidee

| Begriff | Bedeutung |
|---------|-----------|
| **Lerneinheit** | Lebendes Gefäss: Quellen, KI-Blöcke, interaktives Lernen. Löschbar. |
| **Lernverlauf** | Bleibt dauerhaft: Titel, Zusammenfassung, Fortschritt, Rekonstruktionsdaten. |
| **Eltern/Lehrperson** | Sieht Kinder-Fortschritt, kann Einheiten anlegen und (künftig) echte Prüfungen auswerten. |

Lernen in der App (Quiz, Blöcke) ≠ echte Schulprüfung. Beides muss verbunden werden.

---

## Ist-Stand (implementiert)

- Lerneinheit anlegen (Modi, Mathe-Schwerpunkt, Quellen: Foto/PDF/Audio/URL)
- KI-Aufbereitung → Lernblöcke + Quiz
- Interaktiver Lernmodus mit Fortschritt, Pause, Wiederholung
- Verlauf + «ähnlich nochmal» / Wiederholungseinheit
- Eltern-Dashboard (Kinder-Übersicht)
- Zwei Eltern pro Kind
- Modus «Kurzprüfung» (nur KI-generierte Übungsprüfung in der App — **kein** Upload echter Schulprüfungen)

---

## Lücke: Echte Prüfung & Benotung (Priorität hoch)

Das fehlt noch vollständig — dein Eindruck ist richtig.

### Ziel

Pro Lerneinheit (oder pro Fach/Thema) soll eine **externe Prüfung** erfasst werden können:

1. **Upload** — Foto/PDF der korrigierten Prüfung (Handschrift, Rotstift, Punktabzüge)
2. **Metadaten** — Datum, Note/Punkte, max. Punkte, Prüfungstyp (Klassenarbeit, mündlich, …)
3. **Eingabe durch Lehrbeauftragte** — Eltern, Tutor oder später Lehrperson:
   - Gesamtnote / Prozent
   - optional pro Aufgabe: Punkte, Kommentar («Stellenwert verwechselt»)
4. **KI-Analyse** (Vision + Text):
   - Aufgaben erkennen und mit Lerneinheit/Thema verknüpfen
   - **Fehlermuster** clustern (z. B. Bruchrechnen: Nenner vergessen, falsch kürzen, Einheitenfehler)
   - Verständnislücken benennen (nicht nur «3/10 falsch»)
5. **Rückkopplung in Lernen**:
   - Kurzbericht für Eltern/Kind («Wo hakt es?»)
   - Vorschlag: neue **Nacharbeit-Einheit** (Modus Wiederholung + gezielter Mathe-Schwerpunkt)
   - Optional: ergänzende Erklärblöcke nur zu den erkannten Lücken
   - Tracking: gleiche Fehlerart beim nächsten Mal seltener?

### Vorgeschlagenes Datenmodell (noch nicht gebaut)

```
exam_result
  id, unit_id (nullable), profile_id, subject
  taken_at, grade_label, score, max_score
  uploaded_by_id, notes_encrypted
  source_file (wie unit_sources)
  analysis_encrypted  # KI: Fehlermuster, Aufgaben-Mapping
  status: uploaded | analyzed | action_created

exam_item (optional, manuell oder KI)
  exam_result_id, order_index
  prompt_text, points_earned, max_points
  error_tags[]  # z.B. fractions_denominator, unit_conversion
  teacher_comment_encrypted
```

Verknüpfung mit **Lernverlauf**: `learning_record.stats.exams[]` oder eigenes Event `exam_uploaded` / `exam_analyzed`.

### UI (Entwurf)

- Auf **Einheits-Detailseite**: Bereich «Schulprüfung» — Upload + Note eintragen
- Auf **Verlauf** / **Eltern-Dashboard**: Prüfungsergebnisse pro Kind, Trend (Note über Zeit)
- Nach Analyse: Button «Nacharbeit erstellen» → neue Einheit mit `task_type=review` + Brief aus Fehlermustern

### Rollen

| Rolle | Darf |
|-------|------|
| Kind | Prüfung hochladen (optional), Nacharbeit lernen |
| Eltern | Prüfung hochladen, benoten, Analyse lesen, Nacharbeit anlegen |
| Admin | alles |

---

## Weitere konzeptionelle Lücken

| Thema | Status | Anmerkung |
|-------|--------|-----------|
| Fehlermuster über mehrere Prüfungen | fehlt | Braucht `error_tags` + Auswertung über Zeit |
| Manuelle Korrektur der KI-Analyse | fehlt | Lehrperson korrigiert erkannte Aufgaben/Fehler |
| Vergleich App-Quiz vs. Schulprüfung | fehlt | «In der App 90 %, in der Prüfung 60 %» → Transferproblem |
| Spaced Repetition / Erinnerungsplan | fehlt | Wiederholung nach X Tagen automatisch vorschlagen |
| Offline / Druck | fehlt | Arbeitsblatt exportieren (PDF) |
| Mehrere Kinder gleiche Einheit | teilweise | Einheit pro Profil, kein «Vorlage duplizieren» |
| Benachrichtigungen | fehlt | «Kind hat Einheit abgeschlossen» |
| Datenschutz Prüfungsfotos | zu klären | Klassifizierung, Aufbewahrungsfrist, Löschen |

---

## Empfohlene Umsetzungsreihenfolge

### Phase A — Prüfung erfassen (MVP) ✅ *implementiert*
- Tabelle `exam_results` + Upload-API (`POST /units/{id}/exams`)
- UI auf Einheitsseite: Foto/PDF + Note/Punkte + Kommentar
- Speicherung im Lernverlauf (`exam_uploaded`-Event, `exam_count` im Verlauf)
- Datei abrufbar: `GET /units/{id}/exams/{exam_id}/file`
- Migration: `008_exam_results`

### Phase B — KI-Analyse ✅ *implementiert*
- `POST /units/{id}/exams/{exam_id}/analyze` — Vision/OCR + strukturiertes JSON
- Anzeige: Zusammenfassung, Lücken, Fehlermuster, Empfehlungen
- Migration: `009_exam_analysis` (`analysis_encrypted`)

### Phase C — Nacharbeit aus Fehlern ✅ *implementiert*
- `POST /units/{id}/exams/{exam_id}/remediation` — neue Einheit (Modus Wiederholung/Festigung)
- Brief aus Lücken, Fehlermustern und Empfehlungen; `math_focus` aus Analyse oder Ursprungseinheit
- Quellen der Ursprungseinheit werden mitkopiert; Schwierigkeit +1 (max. 5)
- Verknüpfung Exam ↔ Nacharbeit (`remediation_unit_id`, Status `action_created`)
- UI: «Nacharbeit erstellen» / «Zur Nacharbeit»
- Migration: `010_exam_remediation`
- KI-Einstellungen: neuer Aufgabentyp **«Schulprüfung analysieren»** (`exam_analysis`); OCR-Schritt nutzt **«Fotos / OCR»** (`vision`)

### Phase D — Langzeit
- Fehlertrend-Dashboard
- Erinnerungen / Spaced Repetition
- Export & Berichte für Elterngespräche

---

## Abgrenzung: «Kurzprüfung» (Modus) vs. «Schulprüfung» (Upload)

| | Kurzprüfung (Modus) | Schulprüfung (geplant) |
|--|---------------------|-------------------------|
| Quelle | KI generiert | Echtes Schulmaterial |
| Korrektur | Automatisch (Quiz) | Lehrperson / Rotstift auf Papier |
| Zweck | Üben in der App | Lernen aus echten Fehlern |
| Auswertung | sofort im Lernmodus | Analyse + Nacharbeit |

Beides soll nebeneinander existieren und im Verlauf des Kindes zusammenführbar sein.

---

## Nächster konkreter Schritt (wenn du willst)

**Phase A starten**: minimales `exam_results`-Modell + Upload auf der Einheitsseite, ohne KI — nur speichern und Note anzeigen. Danach Phase B (Analyse).
