#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
  alembic upgrade head
fi

# --proxy-headers makes request.client.host the real client IP from X-Forwarded-For.
# Behind Caddy that is required, or per-IP lockout and rate limiting key on the proxy address
# and every client shares one bucket. FORWARDED_ALLOW_IPS is set to the proxy's network by the
# deployment ("*" only where the app is unreachable except through that proxy).
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
