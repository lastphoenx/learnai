# LearnAI

Self-hosted KI-Lernplattform für Kinder und Eltern — Lerneinheiten aus Schulmaterial, interaktives Lernen, echte Prüfungen auswerten, gezielte Nacharbeit.

Login + 2FA in der App (kein externer Identity-Provider nötig).

## Features

- **Lerneinheiten** — Foto, PDF, Audio, URL; **KI-Aufbereitung asynchron** (alle Aufgabentypen, Celery + Fortschritt); Modi inkl. **Lerntrainer**; Fach-Schwerpunkte; Auftrags-Vorlagen
- **Quiz-Erklärungen** — Laufzeit-Herleitung für Multiplikation, Addition, Subtraktion, Division (Spaltenrechnung, Kopfwege)
- **Lernmodus** — Fortschritt, Pause, TTS, Übungsaufgaben, didaktische Phasen (Einstieg → Verstehen → Üben → Check); Sprungleiste im Trainer
- **Adaptive Nacharbeit** — Quiz-Schwächen und Prüfungs-`error_tags` fließen in Nacharbeit und Trainer-Einheiten
- **Kinder & Eltern** — Lernprofile, Zuweisung an mehrere Kinder (inkl. Vorlagen-Kopie mit Blöcken), Eltern-Dashboard
- **Schulprüfungen** — Upload, KI-Analyse (Fehlermuster, Tags), Kurzbericht als Lern-Einstieg, Langzeit-Trends
- **Sicherheit** — Argon2id, AES-256-GCM, TOTP-2FA, Redis Brute-Force-Schutz, SSRF-Guard, Upload-Magic-Bytes, Security-Headers

## Schnellstart (lokal)

```bash
cp .env.example .env
# Secrets setzen (siehe scripts/generate_keys.py)
bash scripts/init_db.sh
docker compose exec -it api python /opt/scripts/bootstrap_admin.py --email admin@example.local
```

Frontend: http://localhost:3000 · API-Docs: http://localhost:8000/api/docs

Lokal: `APP_ENV=development`, `COOKIE_SECURE=false`, `PUBLISH_BIND=127.0.0.1` (Default in `.env.example`).

## Dokumentation

| Datei | Inhalt |
|-------|--------|
| [DEVELOPER.md](DEVELOPER.md) | Architektur, API, Auth, Entwicklung |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Betrieb, Deploy, Schnellbefehle (intern) |
| [docs/UNIT_CREATION.md](docs/UNIT_CREATION.md) | Aufgabentypen, Schwerpunkte, Lerntrainer |
| [CONCEPT.md](CONCEPT.md) | Fachmodell, Lernkreislauf, Roadmap |
| [AGENTS.md](AGENTS.md) | Git-Workflow, Golden Sets, Regeln für KI-Assistenten |
| [FOUNDATION.md](FOUNDATION.md) | Technische Basis (Scaffold) |
| `deploy/` | nginx-Beispiele, `proxy-headers.conf` |
| `scripts/check-env-safe.sh` | `.env` anzeigen ohne Secrets |

## Stack

FastAPI · Next.js 15 · PostgreSQL 18 · Redis · Celery · Docker Compose · Ollama (optional OpenAI/Anthropic)
