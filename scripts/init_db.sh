#!/usr/bin/env bash
# Erstmaliges Setup: .env (Passwort-Prompt) → Postgres → Schema → Smoke-Test
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> .env"
python3 scripts/init_env.py

mkdir -p uploads

echo "==> Postgres + Redis"
docker compose up -d db redis

echo "==> warte auf Postgres"
ok=0
for _ in $(seq 1 40); do
  if docker compose exec -T db pg_isready -U learnai -d learnai >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" -ne 1 ]]; then
  echo "Postgres nicht bereit." >&2
  docker compose logs --tail 40 db
  exit 1
fi

echo "==> Login-Test (SELECT)"
docker compose exec -T db psql -U learnai -d learnai -c \
  "SELECT current_user, current_database(), version();"

echo "==> API / Frontend / Worker"
docker compose up -d --build

echo "==> Alembic"
docker compose exec -T api alembic upgrade head

echo "==> Tabellen"
docker compose exec -T db psql -U learnai -d learnai -c '\dt'

echo "==> Health"
sleep 3
curl -fsS "http://127.0.0.1:3000/api/v1/health" || {
  echo ""
  docker compose logs --tail 40 api frontend
  exit 1
}
echo ""
echo "==> Fertig. Admin:"
echo "    docker compose exec -it api python /opt/scripts/bootstrap_admin.py --email DEINE@EMAIL"
