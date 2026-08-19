# Foundation (Phase 1–3)

Einfrierbarer Stand für **neue Secure-Apps** auf eigenen CTs.

Scaffold: [`scripts/scaffold-new-app.sh`](scripts/scaffold-new-app.sh)  
Proxmox-CT-Basis: `doku/pve2/host/grund_ct_debian_docker.md`

Git-Tag (nach Freeze): `foundation-phase3`

---

## Enthalten

| Bereich | Umsetzung |
|---------|-----------|
| Stack | FastAPI + Next.js 15 + PostgreSQL 18 (Docker Compose) |
| Crypto | AES-256-GCM, Master-Key; PBKDF2-SHA256 600k für User-Daten |
| Passwörter | Argon2id |
| Klassifizierung | `classification` 0–3 auf Tabellen |
| Multi-Tenant | `tenants` + Default-Tenant |
| Auth | Login (Email-Hash), Session-Cookies, 2FA TOTP + Recovery |
| Bootstrap | `scripts/bootstrap_admin.py` |
| Domain-Demo | Projekte + Tasks (verschlüsselt) |
| RBAC | viewer → member → manager → owner |
| Locking | `core/locking.py`, 15-Min-Lease |
| Frontend | Login, Projekte, Projekt-Detail/Tasks, Theme-Toggle |
| Ops | `deploy.sh`, `backup-db.sh`, Dependabot, `/api`-Proxy via Next rewrites |

## Nicht enthalten (pro App später)

- Domain-Modelle jenseits Projects/Tasks
- UI-Design / Branding
- nginx-vHost, Domain, Prod-CORS
- WebSockets, SaaS-Billing, …

---

## Neues Projekt

```bash
# Lokal oder auf dem CT — Tag foundation-phase3 muss existieren (oder --from-tree)
./scripts/scaffold-new-app.sh meine-app ../
cd ../meine-app
# .env ist vorbereitet → docker compose up -d && alembic upgrade head
```

Die Demo-Domain (Projekte/Tasks) bleibt als **funktionierendes Gerüst**. Umbenennen/ersetzen, wenn die Fachlichkeit klar ist — `core/crypto`, `core/auth`, Sessions, RBAC-Muster bleiben.
