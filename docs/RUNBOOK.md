# LearnAI — Betrieb & Schnellreferenz (intern)

Stand: August 2026. Produktion: **CT 135** (`192.168.131.45`), öffentlich via **CT 108 nginx** → `https://learn.example.app`.

---

## Architektur (kurz)

```
Browser → CT 108 nginx (learn.example.app)
       → CT 135 :3000 Frontend / :8000 API (Docker)
       → PostgreSQL + Redis (nur Docker-Netz)
       → Ollama (z. B. 192.168.131.60:11434)
```

nginx auf CT 108 nutzt bereits `snippets/proxy-headers.conf` — **kein** separates LearnAI-Snippet nötig.

---

## Deploy (CT 135)

### Nur Python-Code (`backend/app/`) geändert

Volume-Mount — **kein** `pip install`, **kein** Image-Rebuild:

```bash
cd /opt/learnai
git pull origin feature/interactive-trainer-v1
docker compose restart api worker
curl -sS https://learn.example.app/api/v1/health
```

### `requirements.txt` oder `Dockerfile` geändert

Pakete werden **nur beim Image-Build** installiert (`backend/Dockerfile` → `pip install -r requirements.txt`).
`docker compose restart` reicht **nicht**.

```bash
cd /opt/learnai
git pull origin feature/interactive-trainer-v1
docker compose build api worker
docker compose up -d api worker
```

Bei Zweifeln (Cache): erzwingen ohne Layer-Cache:

```bash
docker compose build --no-cache api worker
docker compose up -d api worker
```

**Prüfen, ob die erwarteten Pakete im laufenden Container sind:**

```bash
docker compose exec api pip show pymupdf pymupdf-fonts | grep -E '^Name:|^Version:'
docker compose exec api python -c "import fitz; print('pymupdf', fitz.__doc__[:20]); print('ubuntu font', 'ubuntu' in fitz.fitz_fontdescriptors)"
```

Erwartung nach PDF-Fix: `pymupdf` ≥ 1.28, `pymupdf-fonts` 1.0.5, `ubuntu font True`.

### Frontend geändert

```bash
docker compose build frontend && docker compose up -d frontend
```

### Alles (empfohlen nach gemischten Änderungen)

```bash
bash scripts/deploy.sh
# = git pull + docker compose build + docker compose up -d
```

Vollständiger Rebuild aller Images:

```bash
docker compose build api worker frontend
docker compose up -d api worker frontend
```

Nach Compose-Änderungen an Ports:

```bash
# .env — nginx auf CT 108 muss CT 135 erreichen
PUBLISH_BIND=192.168.131.45
```

---

## .env prüfen (ohne Secrets)

```bash
cd /opt/learnai
bash scripts/check-env-safe.sh .env
```

**Produktion Pflicht:**

| Variable | Wert |
|----------|------|
| `APP_ENV` | `production` |
| `COOKIE_SECURE` | `true` |
| `CORS_ORIGINS` | `https://learn.example.app` |
| `PUBLISH_BIND` | `192.168.131.45` |
| `TRUSTED_PROXY_CIDRS` | `192.168.131.105/32` (nur CT 108) |
| `DATABASE_URL` | Host `db`, nicht `localhost` |

`DATABASE_URL` manuell maskiert prüfen:

```bash
grep ^DATABASE_URL= .env | sed -E 's#(://[^:]+:)[^@]+#\1***#'
```

---

## Ollama erreichbar?

```bash
# Vom API-Container (curl fehlt im Image — Python):
docker compose exec api python -c "
import urllib.request
url = 'http://192.168.131.60:11434/api/tags'  # oder host.docker.internal
print(urllib.request.urlopen(url, timeout=5).read()[:200].decode())
"
```

`.env` bei Bedarf:

```env
OLLAMA_URL=http://192.168.131.60:11434
WHISPER_URL=http://192.168.131.60:9000
```

`extra_hosts: host.docker.internal:host-gateway` ist in `docker-compose.yml` für api/worker gesetzt.

**Whisper (Audio-Quellen):** faster-whisper auf GMKtec (`gmk-evo`), Port 9000. LearnAI nutzt `WHISPER_URL` vor `OPENAI_API_KEY`.

```bash
# Von CT 135 (LearnAI):
curl -sS -m 10 http://192.168.131.60:9000/health
```

---

## Ports & Erreichbarkeit

```bash
ss -ltn | grep -E ':8000|:3000'
# Erwartung: 192.168.131.45:8000 und :3000

# Von CT 108:
curl -sS -m 3 http://192.168.131.45:8000/api/v1/health
```

---

## Logs

```bash
docker compose logs api --tail=50 -f
docker compose logs worker --tail=50 -f
docker compose logs frontend --tail=30
```

Login-IP-Diagnose (nach Login-Versuch):

```bash
docker compose logs api 2>&1 | grep login_ip_debug | tail -5
```

### Login-Sperren (Brute-Force, Redis)

Skripte liegen auf dem Host unter `./scripts/`, im API-Container unter **`/opt/scripts/`** (nicht `/app/scripts/`).

```bash
cd /opt/learnai
git pull   # Skripte müssen auf dem Host existieren (Volume-Mount)

docker compose exec -T api python /opt/scripts/list_login_blocks.py
docker compose exec -T api python /opt/scripts/list_login_blocks.py -v

# Entsperren (--email = Klartext beim Tippen, nicht aus DB; oder --email-hash aus list_login_blocks):
docker compose exec -T api python /opt/scripts/unlock_login.py --ip 203.0.113.10
docker compose exec -T api python /opt/scripts/unlock_login.py --email-hash <sha256-aus-liste>
docker compose exec -T api python /opt/scripts/unlock_login.py --email user@example.com
```

### Login-E-Mail nachziehen (Bestands-Accounts)

Neue Accounts speichern die Login-E-Mail automatisch. Für ältere Accounts:

```bash
docker compose exec -T api python /opt/scripts/backfill_login_email.py --email user@example.com
```

Oder in der Admin-UI unter **Benutzer** → «Login-E-Mail zuordnen».

---

## Datenbank

```bash
docker compose exec db psql -U learnai -d learnai -c '\dt'
docker compose exec api alembic upgrade head
bash scripts/backup-db.sh   # falls konfiguriert
```

---

## Häufige Fehler

| Symptom | Ursache | Fix |
|---------|---------|-----|
| **502** von nginx | API nur `127.0.0.1` gebunden | `PUBLISH_BIND=192.168.131.45`, `docker compose up -d` |
| Login ohne IP-Sperre | Proxy-IP nicht trusted | `TRUSTED_PROXY_CIDRS` = CT 108 `/32` |
| KI-Generate scheitert | Ollama nicht erreichbar | `OLLAMA_URL` auf LAN-IP setzen |
| Session weg nach Deploy | `SESSION_SECRET` geändert | Secret nicht rotieren ohne Plan |
| Upload abgelehnt | Magic-Byte-Check | Nur PDF/Bild/Audio (Quellen), Prüfung ohne Audio |

---

## Security-Checkliste (Rollout)

- [x] SSRF-Guard (`url_safety.py`)
- [x] XFF rechts-trusted (`client_ip.py`)
- [x] Magic-Byte-Uploads
- [x] `COOKIE_SECURE` + `APP_ENV=production`
- [x] DB nur localhost (`127.0.0.1:5433`)
- [x] API/Frontend an LAN-IP (`PUBLISH_BIND`)
- [x] `TRUSTED_PROXY_CIDRS` auf CT 108 `/32`
- [ ] Redis fail-closed bei Ausfall (offen)
- [ ] TOTP-Replay-Schutz (offen)
- [ ] OCR-Prompt-Delimiter (offen)

---

## Branch & Releases

Aktueller Feature-Branch: `feature/interactive-trainer-v1`  
Stand 22.08.2026: Lerntrainer v1, Fach-Schwerpunkte, Feld-Vorlagen, STT auf Eingabe-Karten.  
Siehe `docs/UNIT_CREATION.md`. Merge nach `main` wenn Trainer end-to-end stabil.
