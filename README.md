# LearnAI

Self-hosted KI-Lernplattform für Kinder und Eltern — Lerneinheiten aus Schulmaterial, interaktives Lernen, echte Prüfungen auswerten, Nacharbeit generieren.

Login + 2FA in der App (kein externer Identity-Provider nötig).

## Features

- **Lerneinheiten** — Foto, PDF, Audio, URL; KI-Aufbereitung zu Blöcken und Quiz; Modi (Erklären, Üben, Mathe, Heft, Wiederholung, Kurzprüfung)
- **Lernmodus** — Fortschritt, Pause, TTS, Wiederholung; Verlauf bleibt nach Löschen der Einheit
- **Kinder & Eltern** — Lernprofile, zwei Eltern pro Kind, Zuweisung von Einheiten, Eltern-Dashboard
- **Schulprüfungen** — Upload korrigierter Prüfungen, KI-Analyse (Fehlermuster, `error_tags`), Nacharbeit-Einheit, Langzeit-Trends
- **Sicherheit** — Argon2id, AES-256-GCM, TOTP-2FA (+ Recovery), Redis Brute-Force-Schutz, Allowlist-Login
- **KI** — Ollama für Chat/Vision, optional OpenAI/Anthropic; TTS via OpenAI

## Schnellstart (lokal)

```bash
bash scripts/init_db.sh
docker compose exec -it api python /opt/scripts/bootstrap_admin.py --email admin@example.local
```

Frontend: http://localhost:3000 · API-Docs: http://localhost:8000/api/docs

## Dokumentation

| Datei | Inhalt |
|-------|--------|
| [DEVELOPER.md](DEVELOPER.md) | Architektur, API, Auth, Deploy, Entwicklung |
| [CONCEPT.md](CONCEPT.md) | Fachmodell, Prüfungs-Pipeline, Roadmap |
| [FOUNDATION.md](FOUNDATION.md) | Technische Basis (Scaffold Phase 1–3) |
| `deploy/` | Generische nginx-Beispiele (ohne produktionsspezifische Werte) |

## Stack

FastAPI · Next.js 15 · PostgreSQL 18 · Redis · Celery · Docker Compose
