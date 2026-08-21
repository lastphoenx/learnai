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
- Lerneinheit anlegen (Modi mit Dropdown-Erklärung, **Fach-Schwerpunkte**, Feld-Vorlagen für KI-Auftrag, Quellen)
- KI-Aufbereitung → Lernblöcke + Quiz (Aufgabentypen: mixed, explain, quiz, practice, math, workbook, review, exam, **interactive** / Lerntrainer)
- **Lerntrainer:** Karten (Merk/Kopf/Eingabe), Check (~50 Fragen), Wissens-Hub, Inhalts-Analyse; STT auf Eingabe-Karten (Whisper/Browser)
- **Quiz-Schwächen** → Nacharbeit / Trainer-Einheit (manuell + Auto-Schwelle)
- **Wiederholung** bei Quiz-Fehlern → Trainer-Pfad statt generischer Neugenerierung
- **Prüfungs-Kurzbericht** als Lern-Einstieg (`exam_entry` beim Start)
- Verlauf + Wiederholungseinheit; Zuweisung inkl. **Vorlagen-Kopie** (Quellen + Lernblöcke)

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
- Client-IP hinter nginx (X-Real-IP, XFF rechts-trusted); `TRUSTED_PROXY_CIDRS`
- SSRF-Guard für URL-Quellen; Magic-Byte-Validierung bei Uploads
- `APP_ENV=production` + `COOKIE_SECURE`; Security-Header in FastAPI

---

## Abgeschlossen: Echte Prüfung & Benotung

*Ursprüngliche Lücke — jetzt umgesetzt (siehe Phasen A–D oben).*

## Weitere konzeptionelle Lücken

| Thema | Status | Anmerkung |
|-------|--------|-----------|
| Fehlermuster über mehrere Prüfungen | ✅ | Aggregation im Eltern-Dashboard (Phase D) |
| Manuelle Korrektur der KI-Analyse | ✅ | PATCH analysis + UI «Analyse bearbeiten» |
| Vergleich App-Quiz vs. Schulprüfung | ✅ | `transfer` pro Prüfung (Einheit + Eltern-Dashboard) |
| Spaced Repetition / Erinnerungsplan | teilweise | Lernkarten im Trainer; 7-Tage-Hinweis Eltern-Dashboard |
| Offline / Druck | ✅ | Arbeitsblatt-PDF; Trainer-Export JSON |
| Mehrere Kinder gleiche Einheit | ✅ | Zuweisung kopiert Quellen + Lernblöcke |
| App-Quiz → adaptive Nacharbeit | ✅ | `error_tags`, Nacharbeit/Trainer, Auto-Trainer |
| Benachrichtigungen | fehlt | «Kind hat Einheit abgeschlossen» |
| Datenschutz Prüfungsfotos | zu klären | Klassifizierung, Aufbewahrungsfrist, Löschen |
| Redis fail-closed / TOTP-Replay | offen | Security-Härtung mittlere Priorität |

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

### Phase G — Bericht-PDF ✅ *implementiert*
- `GET /dashboard/parent/report/{profile_id}/pdf` — Elternbericht inkl. Prüfungen, Fehlermuster, Transfer
- Markdown-Export bleibt unter `/report/{profile_id}`

### Phase H — Arbeitsblatt-PDF ✅ *implementiert*
- `GET /units/{unit_id}/worksheet.pdf` — Lernblöcke + Quizfragen (ohne Lösungen), Antwortzeilen
- UI: «Arbeitsblatt (PDF)» auf Einheitsseite (wenn Lernblöcke vorhanden)

## Nächste Schritte (optional)

1. **Benachrichtigungen** — E-Mail/Push bei Abschluss oder Prüfungserinnerung
2. **Datenschutz Prüfungsfotos** — Aufbewahrungsfrist formalisieren
