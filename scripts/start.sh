#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
  alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
