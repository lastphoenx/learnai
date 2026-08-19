#!/bin/sh
set -e
case "$1" in
  uvicorn)
    echo "Running database migrations..."
    alembic upgrade head
    ;;
esac
exec "$@"
