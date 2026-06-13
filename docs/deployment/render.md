# Render Deployment Guide

This guide deploys `authcore-service` as a Docker-backed Render web service. Use it after the GitHub repo and CI are green.

Status before deployment:

- Core backend is complete.
- GitHub Actions CI is green on `main`.
- Render deployment is prepared but the live URL is not added yet.
- The blueprint deploys the FastAPI web API only; the Celery worker is not deployed in the current blueprint.

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

Recommended Render resources:

- One Docker Web Service for the API.
- One Render PostgreSQL database.
- One Render Redis instance.

Use the repository root as the service root. This repo is already `authcore-service`, so there is no nested `F2/` path inside GitHub.

## Environment Variables

Set these in Render before first deploy:

| Key | Required | Example / Note |
|---|---:|---|
| `APP_ENV` | Yes | `production` |
| `APP_DEBUG` | Yes | `false` |
| `APP_SECRET_KEY` | Yes | Generate a long random value; never use `.env.example` default |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB` |
| `REDIS_URL` | Yes | Redis URL for app counters |
| `CELERY_BROKER_URL` | Yes | Use the same Redis URL for now unless the provider supports separate DB indexes |
| `CELERY_RESULT_BACKEND` | Yes | Use the same Redis URL for now unless the provider supports separate DB indexes |
| `RUN_MIGRATIONS_ON_START` | Yes | `true` for first deploy and normal deploys |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` |
| `RATE_LIMIT_AUTH` | No | `10/minute` |
| `RATE_LIMIT_SENSITIVE` | No | `5/minute` |
| `MAX_FAILED_ATTEMPTS` | No | `5` |
| `LOCKOUT_TTL_SECONDS` | No | `900` |
| `PASSWORD_BREACH_CHECK_ENABLED` | No | `false` by default; set `true` to call HaveIBeenPwned range API |
| `PASSWORD_BREACH_CHECK_FAIL_CLOSED` | No | `false`; if `true`, registration fails when breach check is unavailable |
| `HIBP_TIMEOUT_SECONDS` | No | `2.0` |
| `SENTRY_DSN` | No | Optional |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAILS_FROM` | No | Reserved for future real email-provider delivery |

## Redis URL Note

Local Docker uses separate Redis DB indexes:

```text
redis://redis:6379/0
redis://redis:6379/1
redis://redis:6379/2
```

Some managed Redis providers do not allow selecting separate DB indexes. If Render gives one Redis URL, use the same URL for:

- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

That is acceptable for the current deployment because the blueprint only runs the API web service.

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

1. Open the Render dashboard.
2. Create a PostgreSQL database.
3. Create a Redis instance.
4. Create a new Blueprint or Docker Web Service from `cypher682/authcore-service`.
5. If using Blueprint, select `render.yaml`.
6. Add the required secret environment variables.
7. Convert the PostgreSQL URL to `postgresql+asyncpg://...` before saving `DATABASE_URL`.
8. Deploy.
9. Watch logs for:

```text
Running upgrade
authcore-service starting
```

10. Verify:

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
- One live API request from Postman, Swagger UI, or browser.

Add the live URL and screenshots to:

- `README.md`
- `docs/evidence/README.md`
- `docs/evidence/evidence-capture-guide.md`

## Celery Worker Note

The current Render blueprint deploys the API web service only. The Celery worker is healthy in Docker Compose and can be deployed later as a Render background worker if async email/background processing becomes part of the live demo.

Email verification and password reset API flows are implemented, and their tokens are stored hashed in PostgreSQL. Real external email-provider delivery is not implemented yet. For the current portfolio demo, focus live evidence on health, OpenAPI docs, registration/login, MFA, sessions, RBAC/admin, audit logs, rate limiting, and lockout.
