# LearnAI

Self-hosted KI-Lernplattform. Foundation (Auth, 2FA, Crypto) aus dem Projektmanagement-Scaffold.

Öffentlich: `https://learn.santinel.li` hinter nginx CT 108 — **ohne Authentik**, Login + 2FA in der App.

## Fachmodell

- **Lerneinheit** = lebendes Gefäss (Inhalt, Fotos, Blöcke). Kann im UI komplett gelöscht werden.
- **Lernverlauf** = bleibt. Ergebnisse, Kurzbeschreibung, Fingerprint zum Neuaufbau («ähnlich, eine Stufe schwerer»).
- Quellenfotos können einzeln weg, oder nach OCR nur die Datei (Text bleibt). Optional Auto-Purge nach Vision.
- **2FA pro Account:** Pflicht oder optional (Admin). Einmal eingerichtet, gilt sie beim Login immer.

Ausführliches Konzept, Lücken und Roadmap (u. a. **Schulprüfungen hochladen & Fehlermuster**): **[CONCEPT.md](CONCEPT.md)**

## Schnellstart

```bash
bash scripts/init_db.sh
# Prompt: DB-Passwort, Produktion ja/nein, Keys falls leer
docker compose exec -it api python /opt/scripts/bootstrap_admin.py --email admin@example.local
```

`init_db.sh` schreibt `.env`, startet Postgres, prüft Login (`SELECT`), fährt Alembic, testet `/api/v1/health`.

Frontend: http://localhost:3000

## KI

| Dienst | Default |
|--------|---------|
| Chat / Aufbereitung | Ollama auf EVO (`LLM_PROVIDER=ollama`, `192.168.131.60:11434`) |
| Vision (Fotos) | Ollama-Vision-Modell, sonst OpenAI/Claude je nach Provider |
| Fallback | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — im UI oder `provider` im API |
| TTS | OpenAI (`TTS_PROVIDER=openai`) |

Test (eingeloggt, Cookie): `GET /api/v1/ai/status`, `POST /api/v1/ai/complete`. Lerneinheit: «Mit KI aufbereiten».

## Deploy

Produktions-Doku (CT, nginx, Firewall, Backup): **`doku/pve2/vm/135-learnai/`**

- CT 135, `192.168.131.45`, `https://learn.santinel.li`
- nginx CT 108 ohne Authentik, Proxy auf `:3000`
- Grund-CT: `doku/pve2/host/grund_ct_debian_docker.md`
