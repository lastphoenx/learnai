#!/usr/bin/env bash
# LearnAI — .env anzeigen ohne Secrets (für Support/Debug).
# Nutzung: ./scripts/check-env-safe.sh [pfad/zur/.env]
set -euo pipefail

ENV_FILE="${1:-.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Datei nicht gefunden: $ENV_FILE" >&2
  exit 1
fi

awk -F= '
function mask_db_url(val,    p, q, userpass) {
  if (val !~ /^postgresql/) return val
  p = index(val, "://")
  q = index(val, "@")
  if (p == 0 || q == 0 || q <= p) return val
  userpass = substr(val, p + 3, q - p - 3)
  sub(/:[^:]*$/, ":***", userpass)
  return substr(val, 1, p + 2) userpass substr(val, q)
}

function mask(key, val) {
  if (key ~ /(PASSWORD|SECRET|KEY|TOKEN)/) {
    if (length(val) > 0) return "[gesetzt, " length(val) " Zeichen]"
    return "[LEER]"
  }
  if (key == "DATABASE_URL" || key == "REDIS_URL") {
    return mask_db_url(val)
  }
  return val
}

/^[[:space:]]*#/ { print; next }
/^[[:space:]]*$/ { print; next }
{
  key = $1
  sub(/^[^=]+=/, "", $0)
  val = $0
  gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
  gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
  print key "=" mask(key, val)
}' "$ENV_FILE"
