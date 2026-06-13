# Render Deployment Guide

This guide deploys `authcore-service` as a Docker-backed Render web service. Use it after the GitHub repo and CI are green.

## Current Repo

- GitHub: `https://github.com/cypher682/authcore-service`
- Blueprint file: `render.yaml`
- Dockerfile: `Dockerfile`
- Health check: `/health`

## What Render Needs

AuthCore requires:

- A web service built from the Dockerfile.
- A PostgreSQL database URL in SQLAlchemy async format.
- A Redis-compatible URL for rate limiting, lockout counters, and Celery broker/backend.
- A non-default `APP_SECRET_KEY`.

The app image now includes `alembic/` and `alembic.ini`, so production migrations can run at container startup when `RUN_MIGRATIONS_ON_START=true`.

## Environment Variables

Set these in Render before first deploy:

| Key | Required | Example / Note |
|---|---:|---|
| `APP_ENV` | Yes | `production` |
| `APP_DEBUG` | Yes | `false` |
| `APP_SECRET_KEY` | Yes | Generate a long random value; never use `.env.example` default |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB` |
| `REDIS_URL` | Yes | Redis URL for app counters, usually DB `0` |
| `CELERY_BROKER_URL` | Yes | Redis URL for broker, usually DB `1` if provider supports DB selection |
| `CELERY_RESULT_BACKEND` | Yes | Redis URL for results, usually DB `2` if provider supports DB selection |
| `RUN_MIGRATIONS_ON_START` | Yes | `true` for first deploy and normal deploys |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` |
| `RATE_LIMIT_AUTH` | No | `10/minute` |
| `RATE_LIMIT_SENSITIVE` | No | `5/minute` |
| `MAX_FAILED_ATTEMPTS` | No | `5` |
| `LOCKOUT_TTL_SECONDS` | No | `900` |
| `SENTRY_DSN` | No | Optional |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAILS_FROM` | No | Optional until email features are completed |

## Important URL Format

The app uses SQLAlchemy async with `asyncpg`, so the database URL must start with:

```text
postgresql+asyncpg://
```

If your provider gives:

```text
postgres://USER:PASSWORD@HOST:PORT/DB
```

convert it to:

```text
postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB
```

## Deploy Steps

1. Open Render dashboard.
2. Create a new Blueprint or Docker Web Service from `cypher682/authcore-service`.
3. If using Blueprint, select `render.yaml`.
4. Add the required secret environment variables.
5. Deploy.
6. Watch logs for:

```text
Running upgrade
authcore-service starting
```

7. Verify:

```text
https://YOUR-RENDER-SERVICE.onrender.com/health
https://YOUR-RENDER-SERVICE.onrender.com/docs
```

## Evidence To Capture

After deployment, capture:

- Render service dashboard showing successful deploy.
- Render logs showing migration + startup.
- Live `/health` response.
- Live `/docs` page.
- One live API request from Postman.

Add the live URL and screenshots to:

- `README.md`
- `docs/evidence/README.md`
- `docs/evidence/evidence-capture-guide.md`

## Celery Worker Note

The current Render blueprint deploys the API web service only. The Celery worker is healthy in Docker Compose and can be deployed later as a Render background worker if async email/background processing becomes part of the live demo.

For the current portfolio demo, the web API evidence is enough because auth, MFA, RBAC, sessions, audit logs, rate limiting, and lockout are all handled by the FastAPI service plus PostgreSQL/Redis.
