# LearnAI

Self-hosted KI-Lernplattform. Foundation (Auth, 2FA, Crypto) aus dem Projektmanagement-Scaffold.

Öffentlich: `https://learn.santinel.li` hinter nginx CT 108 — **ohne Authentik**, Login + 2FA in der App.

## Fachmodell

- **Lerneinheit** = lebendes Gefäss (Inhalt, Fotos, Blöcke). Kann im UI komplett gelöscht werden.
- **Lernverlauf** = bleibt. Ergebnisse, Kurzbeschreibung, Fingerprint zum Neuaufbau («ähnlich, eine Stufe schwerer»).
- Quellenfotos können einzeln weg, oder nach OCR nur die Datei (Text bleibt). Optional Auto-Purge nach Vision.
- **2FA pro Account:** Pflicht oder optional (Admin). Einmal eingerichtet, gilt sie beim Login immer.

## Schnellstart

```bash
cp .env.example .env
# ENCRYPTION_MASTER_KEY, SESSION_SECRET, POSTGRES_PASSWORD setzen

docker compose up -d
docker compose exec api alembic upgrade head
python scripts/bootstrap_admin.py --email admin@example.local
```

Frontend: http://localhost:3000

## KI

| Dienst | Default |
|--------|---------|
| TTS | OpenAI (`TTS_PROVIDER=openai`) |
| Vision / Kurse | folgt, lokal Ollama `192.168.131.60:11434` |
| Chat | Ollama / OpenAI / Anthropic |

Sprachkurse in Slice 1: **Fotos aus dem Lernmittel**, noch kein Kamera-Objekt-Modus.

## Deploy

Produktions-Doku (CT, nginx, Firewall, Backup): **`doku/pve2/vm/135-learnai/`**

- CT 135, `192.168.131.45`, `https://learn.santinel.li`
- nginx CT 108 ohne Authentik, Proxy auf `:3000`
- Grund-CT: `doku/pve2/host/grund_ct_debian_docker.md`
