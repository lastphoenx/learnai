# LearnAI — Entwickler-Dokumentation

Stand: August 2026.

---

## Architektur

```
Browser
  → Reverse Proxy (TLS)
       ├─ /api/*  → App-Host :8000 (FastAPI, Client-IP via X-Real-IP)
       └─ /*      → App-Host :3000 (Next.js)
                         └─ SSR; /api nur Fallback (Middleware)
  → api:8000 → PostgreSQL + Redis + Celery Worker
  → Ollama / OpenAI / Anthropic (konfigurierbar)
```

| Service | Port | Rolle |
|---------|------|-------|
| `frontend` | 3000 | Next.js App Router, Theme, Login-UI |
| `api` | 8000 | FastAPI REST, Auth, KI-Orchestrierung |
| `worker` | — | Celery (async Jobs, falls konfiguriert) |
| `db` | 5433→5432 | PostgreSQL 18 |
| `redis` | 6379 | Brute-Force-Zähler, Celery-Broker |

**Wichtig:** In Produktion sollte der Reverse Proxy `/api/` **direkt** an FastAPI routen (siehe `deploy/nginx.example.conf`). Nur so kommt die echte Client-IP per `X-Real-IP` an — nicht ausschliesslich über den Next.js-Rewrite.

---

## Projektstruktur

```
learnai/
├── backend/
│   ├── app/
│   │   ├── api/          # routes, units, dashboard, profiles, health
│   │   ├── ai/           # generate, extract, exam_analyze, providers, task_types
│   │   ├── core/auth/    # sessions, bruteforce, client_ip, dependencies
│   │   ├── models/       # SQLAlchemy
│   │   ├── services/     # unit, learn, exam, exam_insights, dashboard, profile
│   │   └── main.py
│   ├── alembic/versions/ # 001 … 010
│   └── tests/
├── frontend/src/
│   ├── app/              # login, units, parent, admin, settings, history
│   ├── components/
│   └── lib/api.ts        # API-Client
├── deploy/               # Generische nginx-Beispiele
├── scripts/              # init_db.sh, deploy.sh, backup-db.sh, bootstrap_admin.py
└── docker-compose.yml
```

---

## Fachmodell

| Begriff | Tabelle / Ort | Beschreibung |
|---------|---------------|--------------|
| **Lerneinheit** | `learning_units` | Lebendes Gefäss: Quellen, KI-Blöcke, Schwierigkeit, Modus |
| **Lernverlauf** | `learning_records` | Bleibt dauerhaft; Fingerprint für «ähnlich nochmal» |
| **Lernprofil** | `learning_profiles` | Kind mit KI-Einstellungen (Provider, Modell je Aufgabentyp) |
| **Prüfungsergebnis** | `exam_results` | Upload, Note, `analysis_encrypted` (JSON), `remediation_unit_id` |
| **Benutzer** | `users` | Login, 2FA, Rollen (admin, child, parent) |

Quellen (`unit_sources`): Foto, PDF, Audio, URL — optional Auto-Purge nach OCR.

---

## Auth & Sicherheit

### Login-Flow

1. `POST /api/v1/auth/login` — Passwort prüfen
2. Bei 2FA: `requires_2fa: true` + Challenge-Cookie → `POST /api/v1/auth/2fa/verify`
3. Session-Cookie `learn_session` (HttpOnly, `COOKIE_SECURE` in Prod)

### 2FA

- TOTP (Authenticator-App) + einmalige Recovery Codes (gehasht)
- Policy pro Account: `totp_required` (Admin unter `/admin/users`)
- `must_enroll_2fa` blockiert App bis Einrichtung unter `/settings`

### Brute-Force (`core/auth/bruteforce.py`)

Redis-basiert. Konfiguration in `.env` / `config.py`:

| Setting | Default | Bedeutung |
|---------|---------|-----------|
| `LOGIN_ALLOWLIST_ONLY` | `true` | Unbekannte E-Mails → dauerhafte Sperre (+ IP) |
| `LOGIN_RATE_LIMIT_PER_IP` | 15/min | Rate-Limit Login |
| `LOGIN_MAX_FAILURES_PER_EMAIL` | 5 | E-Mail-Sperre nach Fehlversuchen |
| `LOGIN_MAX_FAILURES_PER_IP` | 8 | IP-Sperre nach Fehlversuchen |
| `TRUSTED_PROXY_CIDRS` | private ranges | Nur von diesen Peers `X-Real-IP` vertrauen |

### Client-IP (`core/auth/client_ip.py`)

- Hinter vertrauenswürdigem Proxy: `X-Real-IP` / `X-Forwarded-For`
- Private LAN-IPs werden für Rate-Limits genutzt; öffentliche IPs für IP-Sperren
- Diagnose: `login_ip_debug` INFO-Log bei Login

### Verschlüsselung

- `ENCRYPTION_MASTER_KEY` (32 Byte Base64) — AES-256-GCM für sensible Felder
- Passwörter: Argon2id; E-Mail-Hash für Lookup

---

## Schulprüfungs-Pipeline

### Phase A — Erfassen
- `POST /units/{id}/exams` — Upload + Metadaten (Note, Punkte, Kommentar)
- `GET /units/{id}/exams/{exam_id}/file` — Datei abrufen

### Phase B — KI-Analyse
- `POST /units/{id}/exams/{exam_id}/analyze` — Vision/OCR → strukturiertes JSON
- Aufgaben in `analysis.tasks[]` mit `error_tags[]` (siehe `ai/error_tags.py`)

### Phase C — Nacharbeit
- `POST /units/{id}/exams/{exam_id}/remediation` — neue Einheit (Modus `review`)

### Phase D — Langzeit
- `GET /dashboard/parent/exam-insights` — Fehlertrends pro Kind
- `GET /dashboard/parent/report/{profile_id}` — Markdown-Bericht
- `GET /dashboard/parent/report/{profile_id}/pdf` — Elternbericht als PDF
- `GET /units/{id}/worksheet.pdf` — Arbeitsblatt (Lernblöcke + Fragen, ohne Lösungen)

---

## KI

Provider: `LLM_PROVIDER=ollama|openai|anthropic`. Pro Lernprofil überschreibbar (Einstellungen).

Endpoints: `GET /api/v1/ai/status`, `GET /api/v1/ai/effective`, `POST /api/v1/ai/complete`, `POST /units/{id}/generate`.

---

## API-Übersicht

Präfix: `/api/v1`. OpenAPI: `/api/docs`.

| Bereich | Endpunkte |
|---------|-----------|
| Auth | `/auth/login`, `/logout`, `/me`, `/2fa/*` |
| Users (Admin) | `/users`, `/users/children`, `/users/{id}/totp-policy`, `/guardians` |
| Units | CRUD, sources, generate, learn/*, exams/* |
| Profiles | CRUD, `apply-recommendations` |
| Dashboard | `/dashboard/parent`, `/exam-insights`, `/report/{id}` |
| Health | `/health` |

---

## Umgebungsvariablen

Siehe `.env.example`. Wichtig für Produktion:

```env
CORS_ORIGINS=https://your-domain.example
COOKIE_SECURE=true
LOGIN_ALLOWLIST_ONLY=true
LLM_PROVIDER=ollama
OLLAMA_URL=http://ollama-host:11434
# OLLAMA_MODEL / OLLAMA_VISION_MODEL optional — leer = Katalog + installierte Ollama-Modelle
```

---

## Datenbank-Migrationen

```bash
docker compose exec api alembic upgrade head
```

Alembic läuft auch beim Container-Start (`docker-entrypoint.sh`).

---

## Lokale Entwicklung

```bash
bash scripts/init_db.sh
docker compose up -d
docker compose logs -f api
```

API-Code ist per Volume gemountet (`./backend/app` → `restart api` reicht).

Tests:

```bash
cd backend && python -m pytest tests/ -q
```

---

## Deploy

```bash
git pull
docker compose restart api          # nur Python-Änderungen (Volume)
./scripts/deploy.sh                 # Build + alle Services
```

Produktionsspezifische nginx-Konfiguration und Infrastruktur-Doku gehören **nicht** ins öffentliche Repo — nur in private Betriebsdoku pflegen.

Generisches Muster: `deploy/nginx.example.conf` — `/api/` an `:8000`, Rest an `:3000`, `proxy-headers` mit `X-Real-IP`.

Optional: `deploy/nginx-auth-limit.example.conf` — zusätzliches Rate-Limit auf nginx-Ebene.

---

## Roadmap (offen)

Siehe [CONCEPT.md](CONCEPT.md).
