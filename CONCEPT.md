# LearnAI — Konzept & Roadmap

Stand: August 2026 (Phasen A–D der Prüfungs-Pipeline abgeschlossen).

Siehe auch [README.md](README.md), [DEVELOPER.md](DEVELOPER.md) (technisch) und [FOUNDATION.md](FOUNDATION.md) (Scaffold-Basis).

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

### Lernen
- Lerneinheit anlegen (Modi, Mathe-Schwerpunkt, Quellen: Foto/PDF/Audio/URL)
- KI-Aufbereitung → Lernblöcke + Quiz (Aufgabentypen: mixed, explain, quiz, practice, math, workbook, review, exam)
- Interaktiver Lernmodus mit Fortschritt, Pause, TTS, Wiederholung
- Verlauf + «ähnlich nochmal» / Wiederholungseinheit
- Einheiten mehreren Lernprofilen zuweisen

### Rollen & Profile
- Eltern-Dashboard (Kinder-Übersicht, Prüfungstrends, Markdown-Bericht)
- Zwei Eltern pro Kind (`child_guardians`)
- Lernprofile mit KI-Einstellungen je Aufgabentyp (Provider/Modell)
- Modus «Kurzprüfung» (KI-generierte Übungsprüfung in der App)

### Schulprüfungen (Phasen A–D) ✅
- **A:** Upload korrigierter Prüfung + Note/Punkte/Kommentar (`exam_results`)
- **B:** KI-Analyse (Vision/OCR) — Aufgaben, Lücken, Fehlermuster, `error_tags` pro Aufgabe
- **C:** Nacharbeit-Einheit aus Analyse (Modus Wiederholung, Quellen kopiert, Schwierigkeit +1)
- **D:** Langzeit-Trends (`error_tags` aggregiert), Wiederholungs-Erinnerungen, Eltern-Bericht-Export

### Sicherheit
- Login + TOTP-2FA + Recovery Codes; 2FA-Pflicht pro Account (Admin)
- Redis Brute-Force-Schutz (Rate-Limits, E-Mail-/IP-Sperren, Allowlist-only)
- Client-IP hinter nginx (X-Real-IP); Login-IP-Debug-Logging

---

## Abgeschlossen: Echte Prüfung & Benotung

*Ursprüngliche Lücke — jetzt umgesetzt (siehe Phasen A–D oben).*

## Weitere konzeptionelle Lücken

| Thema | Status | Anmerkung |
|-------|--------|-----------|
| Fehlermuster über mehrere Prüfungen | ✅ | Aggregation im Eltern-Dashboard (Phase D) |
| Manuelle Korrektur der KI-Analyse | ✅ | PATCH analysis + UI «Analyse bearbeiten» |
| Vergleich App-Quiz vs. Schulprüfung | ✅ | `transfer` pro Prüfung (Einheit + Eltern-Dashboard) |
| Spaced Repetition / Erinnerungsplan | teilweise | Wiederholungs-Hinweis nach 7 Tagen (Kinder-Übersicht) |
| Offline / Druck | fehlt | Arbeitsblatt exportieren (PDF) |
| Mehrere Kinder gleiche Einheit | teilweise | Zuweisung an Profile; kein «Vorlage duplizieren» |
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

### Phase D — Langzeit ✅ *implementiert*
- Fehlertrend-Dashboard auf **Kinder-Übersicht** (`GET /dashboard/parent/exam-insights`)
- Aggregation von `error_tags` über alle Prüfungen pro Kind
- Wiederholungs-Erinnerungen (7 Tage nach Abschluss einer Einheit)
- Export Markdown-Bericht für Elterngespräche (`GET /dashboard/parent/report/{profile_id}`)

### Phase E — Analyse editieren ✅ *implementiert*
- `PATCH /units/{id}/exams/{exam_id}/analysis` — manuelle Korrektur (Aufgaben, Tags, Lücken)
- UI: «Analyse bearbeiten» auf Einheitsseite; Flag `analysis_edited`

### Phase F — Transfer App vs. Prüfung ✅ *implementiert*
- Vergleich Quiz-% vs. Prüfungs-% pro Einheit (`transfer` in Exam-API)
- Anzeige auf Einheitsseite und Eltern-Prüfungsverlauf
- Signale: `transfer_gap` (≥15 % App besser), `aligned`, `exam_better`

### exam_item / error_tags (Stand)
- **Keine eigene `exam_items`-Tabelle** — Aufgaben liegen in `analysis.tasks[]` (JSON, Phase B)
- Pro Aufgabe: `error_tags[]` (z. B. `fractions_denominator`, `unit_conversion`) via KI-Analyse
- Aggregierte Muster zusätzlich in `analysis.error_patterns[]`
- Anzeige pro Aufgabe auf der Einheitsseite; Trends im Eltern-Dashboard

---

## Abgrenzung: «Kurzprüfung» (Modus) vs. «Schulprüfung» (Upload)

| | Kurzprüfung (Modus) | Schulprüfung (Upload) |
|--|---------------------|------------------------|
| Quelle | KI generiert | Echtes Schulmaterial |
| Korrektur | Automatisch (Quiz) | Lehrperson / Rotstift auf Papier |
| Zweck | Üben in der App | Lernen aus echten Fehlern |
| Auswertung | sofort im Lernmodus | Analyse + Nacharbeit + Langzeit-Trends |

Beides existiert nebeneinander und wird im Verlauf des Kindes zusammengeführt.

---

## Nächste Schritte (optional)

1. **PDF-Export** — Elternbericht und Arbeitsblatt drucken
2. **Benachrichtigungen** — E-Mail/Push bei Abschluss oder Prüfungserinnerung
3. **Datenschutz Prüfungsfotos** — Aufbewahrungsfrist formalisieren
