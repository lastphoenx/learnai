#!/usr/bin/env bash
# git pull + Docker neu bauen/starten (auf dem App-Host)

set -euo pipefail

REPO_DIR="/opt/learnai"
cd "$REPO_DIR"

if [[ ! -f .env ]]; then
  echo "FEHLER: .env fehlt. Einmalig: bash scripts/init_db.sh" >&2
  exit 1
fi

if [[ -d .git ]]; then
  echo "==> git pull"
  git pull
else
  echo "WARNUNG: kein git-Repo — manueller Stand, kein pull" >&2
fi

echo "==> Build & start"
docker compose build
docker compose up -d

HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:3000/api/v1/health}"
echo "==> Health (über Frontend-Proxy): ${HEALTH_URL}"
sleep 3
if ! curl -fsS "${HEALTH_URL}"; then
  echo ""
  echo "==> Container-Logs:"
  docker compose logs --tail 30
  exit 1
fi
echo ""

echo "==> Fertig."
