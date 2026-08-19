#!/usr/bin/env bash
# Neues Secure-App-Repo aus Foundation Phase 1–3 erzeugen.
#
# Usage:
#   ./scripts/scaffold-new-app.sh <app-slug> [ziel-elternverzeichnis]
#   ./scripts/scaffold-new-app.sh inventar ~/dev
#   ./scripts/scaffold-new-app.sh inventar ~/dev --from-tree
#
# Empfohlen: Git-Tag foundation-phase3. Sonst --from-tree / Fallback.

set -euo pipefail

FOUNDATION_TAG="${FOUNDATION_TAG:-foundation-phase3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  echo "Usage: $0 <app-slug> [ziel-elternverzeichnis] [--from-tree]" >&2
  echo "  app-slug: kleinbuchstaben, ziffern, bindestriche (z.B. inventar)" >&2
  exit 1
}

FROM_TREE=0
SLUG=""
PARENT=""

for arg in "$@"; do
  case "$arg" in
    --from-tree) FROM_TREE=1 ;;
    -h|--help) usage ;;
    *)
      if [[ -z "$SLUG" ]]; then SLUG="$arg"
      elif [[ -z "$PARENT" ]]; then PARENT="$arg"
      else usage
      fi
      ;;
  esac
done

[[ -n "$SLUG" ]] || usage
PARENT="${PARENT:-$(dirname "$SOURCE_REPO")}"

if [[ ! "$SLUG" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "FEHLER: app-slug ungültig (erwartet: ^[a-z][a-z0-9-]*$)" >&2
  exit 1
fi

TARGET="$PARENT/$SLUG"
if [[ -e "$TARGET" ]]; then
  echo "FEHLER: Ziel existiert bereits: $TARGET" >&2
  exit 1
fi

DB_NAME="${SLUG//-/_}"
TITLE="$(python3 -c "
s='$SLUG'.split('-')
print(' '.join(w[:1].upper()+w[1:] for w in s if w))
")"

echo "==> Quelle: $SOURCE_REPO"
echo "==> Ziel:   $TARGET"
echo "==> Slug:   $SLUG  | DB: $DB_NAME  | Titel: $TITLE"

mkdir -p "$PARENT"

copy_from_tag() {
  if ! git -C "$SOURCE_REPO" rev-parse --verify "$FOUNDATION_TAG^{commit}" >/dev/null 2>&1; then
    return 1
  fi
  echo "==> git archive $FOUNDATION_TAG"
  mkdir -p "$TARGET"
  git -C "$SOURCE_REPO" archive --format=tar "$FOUNDATION_TAG" | tar -x -C "$TARGET"
}

copy_from_tree() {
  echo "==> rsync Arbeitsbaum (ohne .git / Build-Artefakte)"
  mkdir -p "$TARGET"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude '.git/' \
      --exclude '.venv/' \
      --exclude 'node_modules/' \
      --exclude '.next/' \
      --exclude '__pycache__/' \
      --exclude '.pytest_cache/' \
      --exclude '.env' \
      --exclude '*.pyc' \
      --exclude 'backend/.venv/' \
      "$SOURCE_REPO/" "$TARGET/"
  else
    # Fallback ohne rsync (z.B. Git Bash minimal)
    git -C "$SOURCE_REPO" archive --format=tar HEAD | tar -x -C "$TARGET"
  fi
}

if [[ "$FROM_TREE" -eq 1 ]]; then
  copy_from_tree
elif ! copy_from_tag; then
  echo "WARNUNG: Tag '$FOUNDATION_TAG' fehlt — Fallback Arbeitsbaum" >&2
  echo "         Freeze: git tag -a $FOUNDATION_TAG -m 'Foundation Phase 1-3'" >&2
  copy_from_tree
fi

replace_in_files() {
  local old="$1" new="$2"
  find "$TARGET" -type f \
    ! -path '*/.git/*' \
    ! -path '*/node_modules/*' \
    ! -path '*/.venv/*' \
    ! -path '*/.next/*' \
    ! -name '*.png' ! -name '*.jpg' ! -name '*.ico' ! -name '*.woff*' \
    -print0 | while IFS= read -r -d '' f; do
      if grep -qF "$old" "$f" 2>/dev/null; then
        python3 -c "
from pathlib import Path
p = Path(r'''$f''')
old, new = '''$old''', '''$new'''
t = p.read_text(encoding='utf-8')
if old in t:
    p.write_text(t.replace(old, new), encoding='utf-8')
"
      fi
    done
}

echo "==> Umbenennen"
replace_in_files "learnai" "$SLUG"
replace_in_files "LearnAI" "$TITLE"

python3 - "$TARGET" "$DB_NAME" "$SLUG" "$TITLE" <<'PY'
from pathlib import Path
import re, sys

root = Path(sys.argv[1])
db, slug, title = sys.argv[2], sys.argv[3], sys.argv[4]

env_ex = root / ".env.example"
if env_ex.exists():
    text = env_ex.read_text(encoding="utf-8")
    text = re.sub(r"^POSTGRES_DB=.*$", f"POSTGRES_DB={db}", text, flags=re.M)
    text = re.sub(
        r"^DATABASE_URL=postgresql\+psycopg://.*$",
        f"DATABASE_URL=postgresql+psycopg://pm:change-me-strong-password@db:5432/{db}",
        text,
        flags=re.M,
    )
    # Prod-Domain-Hinweis neutralisieren
    text = text.replace("your-domain.example", "app.example.local")
    env_ex.write_text(text, encoding="utf-8")

for rel in ("scripts/deploy.sh", "scripts/backup-db.sh"):
    p = root / rel
    if p.exists():
        t = p.read_text(encoding="utf-8")
        t = t.replace("CT 129", "App-CT")
        t = re.sub(r"129-\S+", "dienst-doku", t)
        p.write_text(t, encoding="utf-8")

readme = root / "README.md"
readme.write_text(
    f"""# {title}

Secure-App aus Foundation Phase 1–3 (`scaffold-new-app.sh`, Slug `{slug}`).

Startdomain: **Projekte / Tasks** (Demo). Fachmodelle später ersetzen;
`core/crypto`, `core/auth`, Sessions, RBAC und Locking beibehalten.

Siehe [FOUNDATION.md](FOUNDATION.md).

## Schnellstart

```bash
# .env ist vom Scaffold mit Keys vorausgefüllt — POSTGRES_PASSWORD anpassen
docker compose up -d
docker compose exec api alembic upgrade head
python scripts/bootstrap_admin.py --email admin@example.local
```

Frontend: http://localhost:3000 — API-Health: http://localhost:3000/api/v1/health

## Deploy

App nach `/opt/{slug}`, dann `./scripts/deploy.sh`. Infrastruktur-Doku separat (nicht im öffentlichen Repo).
""",
    encoding="utf-8",
)
PY

echo "==> .env erzeugen"
cp "$TARGET/.env.example" "$TARGET/.env"
MASTER="$(python3 -c 'import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())')"
SESSION="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"
python3 - "$TARGET/.env" "$MASTER" "$SESSION" "$DB_NAME" <<'PY'
from pathlib import Path
import re, sys
p = Path(sys.argv[1])
master, session, db = sys.argv[2], sys.argv[3], sys.argv[4]
text = p.read_text(encoding="utf-8")
text = re.sub(r"^ENCRYPTION_MASTER_KEY=.*$", f"ENCRYPTION_MASTER_KEY={master}", text, flags=re.M)
text = re.sub(r"^SESSION_SECRET=.*$", f"SESSION_SECRET={session}", text, flags=re.M)
text = re.sub(r"^POSTGRES_DB=.*$", f"POSTGRES_DB={db}", text, flags=re.M)
text = re.sub(r"(@db:5432/)[^\s#]+", rf"\g<1>{db}", text)
p.write_text(text, encoding="utf-8")
PY

echo "==> git init"
rm -rf "$TARGET/.git"
git -C "$TARGET" init -b main
(
  cd "$TARGET"
  git update-index --chmod=+x scripts/*.sh 2>/dev/null || true
  git add -A
  # chmod erneut nach add (Windows)
  git update-index --chmod=+x scripts/deploy.sh scripts/backup-db.sh scripts/scaffold-new-app.sh 2>/dev/null || true
  git -c user.email="scaffold@local" -c user.name="scaffold" commit -m "Initial: Secure-App Foundation (Phase 1-3) as $SLUG"
)

echo ""
echo "==> Fertig: $TARGET"
echo ""
echo "Nächste Schritte:"
echo "  1. cd $TARGET"
echo "  2. POSTGRES_PASSWORD (+ DATABASE_URL) in .env setzen"
echo "  3. docker compose up -d && docker compose exec api alembic upgrade head"
echo "  4. python scripts/bootstrap_admin.py --email …"
echo "  5. GitHub-Repo + auf CT nach /opt/$SLUG"
echo ""
echo "Domain ist noch Projekte/Tasks — core/* behalten, Fachlichkeit austauschen."
