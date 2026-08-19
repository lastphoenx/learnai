#!/usr/bin/env bash
# PostgreSQL-Backup des Docker-Volumes (CT 135)
#
# Cron-Beispiel (täglich 03:00):
#   0 3 * * * /opt/learnai/scripts/backup-db.sh >> /var/log/learnai-backup.log 2>&1

set -euo pipefail

REPO_DIR="/opt/learnai"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/learnai}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

cd "$REPO_DIR"

if [[ ! -f .env ]]; then
  echo "FEHLER: .env fehlt" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/learnai-db-${STAMP}.sql.gz"

echo "==> Backup nach $OUT"
docker compose exec -T db pg_dump -U learnai learnai | gzip > "$OUT"

echo "==> Alte Backups (> ${RETENTION_DAYS} Tage) löschen"
find "$BACKUP_DIR" -name 'learnai-db-*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete

ls -lh "$OUT"
echo "==> Fertig."
