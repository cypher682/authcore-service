# AuthCore Service

[![AuthCore CI](https://github.com/cypher682/authcore-service/actions/workflows/ci.yml/badge.svg)](https://github.com/cypher682/authcore-service/actions/workflows/ci.yml)

Production-grade Identity and Access Management API built with FastAPI, PostgreSQL, Redis, Celery, Docker, and GitHub Actions.

This is the first flagship project in the Cypher portfolio build. It targets backend engineering depth while also showing DevOps delivery practices: Docker-first development, automated tests, CI gates, image scanning, and evidence-driven documentation.

## Highlights

- JWT access tokens and refresh token rotation.
- Refresh token family tracking with reuse detection.
- TOTP MFA setup, verification, and disable flow.
- Session management with device fingerprints and concurrent session pruning.
- Dynamic RBAC with roles, permissions, user-role assignment, and route-level checks.
- Structured audit logs for auth, MFA, RBAC, and session events.
- Redis-backed rate limiting and account/IP brute-force lockout.
- Password strength policy with optional HaveIBeenPwned k-anonymity breach checking.
- Email verification and password reset token flows using Celery email tasks.
- Admin APIs for users, roles, permissions, RBAC checks, and audit log queries.
- Docker Compose stack with FastAPI, PostgreSQL, Redis, and Celery worker.
- Pytest suite with 81% coverage.
- GitHub Actions CI for lint, format, tests, Docker build, and Trivy CRITICAL scan.

## Tech Stack

| Area | Tools |
|---|---|
| API | FastAPI, Python 3.13, Pydantic v2 |
| Database | PostgreSQL, SQLAlchemy 2.0, Alembic |
| Cache / lockout | Redis |
| Async worker | Celery with Redis broker |
| Security | bcrypt, PyJWT, pyotp, SlowAPI |
| Password checks | Local strength rules, optional HaveIBeenPwned range API |
| Testing | pytest, pytest-asyncio, pytest-cov, httpx, Factory Boy |
| Delivery | Docker, Docker Compose, GitHub Actions, Trivy |

## Architecture

```text
Client
  |
  v
FastAPI app
  |-- Auth routes: register, login, refresh, MFA
  |-- User routes: session listing and revocation
  |-- Admin routes: users, RBAC, audit logs
  |
  |-- PostgreSQL: users, roles, permissions, sessions, MFA configs, audit logs
  |-- Redis: rate limits, failed-login counters, Celery broker/backend
  |-- Celery worker: async task foundation
```

## API Surface

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Service health |
| `POST` | `/api/v1/auth/register` | Register user and issue tokens |
| `POST` | `/api/v1/auth/verify-email` | Verify an email address with a token |
| `POST` | `/api/v1/auth/verify-email/resend` | Resend verification token for an unverified account |
| `POST` | `/api/v1/auth/login` | Login and issue tokens |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token |
| `POST` | `/api/v1/auth/password/forgot` | Request password reset email |
| `POST` | `/api/v1/auth/password/reset` | Reset password with a valid token |
| `POST` | `/api/v1/auth/mfa/setup` | Create/reuse pending TOTP setup |
| `POST` | `/api/v1/auth/mfa/verify` | Enable MFA with current TOTP code |
| `POST` | `/api/v1/auth/mfa/challenge/verify` | Exchange MFA challenge and TOTP code for tokens |
| `POST` | `/api/v1/auth/mfa/disable` | Disable MFA with current TOTP code |
| `GET` | `/api/v1/users/me/sessions` | List current user's sessions |
| `DELETE` | `/api/v1/users/me/sessions/{session_id}` | Revoke a user session |
| `GET` | `/api/v1/admin/users` | List users as superuser |
| `GET` | `/api/v1/admin/audit-logs` | Query audit logs as superuser |
| `POST` | `/api/v1/admin/roles` | Create role |
| `POST` | `/api/v1/admin/permissions` | Create permission |
| `POST` | `/api/v1/admin/roles/{role_id}/permissions` | Attach permission to role |
| `POST` | `/api/v1/admin/users/roles` | Assign role to user |
| `GET` | `/api/v1/admin/rbac/permission-check` | Verify dynamic permission access |

## Local Development

Create a local `.env` from `.env.example`, then run:

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
```

Open:

```text
http://localhost:8000/docs
```

Run tests:

```bash
docker compose exec -e COVERAGE_FILE=/tmp/.coverage app pytest --cov=app --cov-report=term-missing --cov-fail-under=80 -q
```

Run quality gates:

```bash
docker compose exec -e RUFF_CACHE_DIR=/tmp/ruff_cache app ruff check app tests alembic
docker compose exec app black --check app tests alembic
```

## Evidence

Evidence lives in `docs/evidence/`.

| Evidence | File |
|---|---|
| Evidence index | `docs/evidence/README.md` |
| Redacted API smoke proof | `docs/evidence/api-smoke-evidence.json` |
| Local browser demo | `docs/demo/index.html` |
| Postman collection | `docs/evidence/authcore.postman_collection.json` |

Deployment guide:

- Render deployment: `docs/deployment/render.md`
- Render blueprint: `render.yaml`

Current validation:

- `18 passed`
- `81%` coverage
- Ruff passed
- Black check passed
- Docker runtime image build passed
- GitHub Actions CI passed on `main`
- All Docker Compose services healthy at handoff

## CI/CD

Workflow file: `.github/workflows/ci.yml`

Jobs:

- `lint`: Ruff and Black.
- `test`: Docker Compose dependency startup, Alembic migration, pytest coverage.
- `docker-build`: runtime image build.
- `trivy`: CRITICAL vulnerability scan with SARIF upload.

## Local Evidence Demo

If Postman is slow, use the static browser demo:

```text
docs/demo/index.html
```

Recommended flow:

1. Start the Docker stack.
2. Open `docs/demo/index.html` in a browser.
3. Click through the panels from top to bottom.
4. Screenshot the response cards.

The demo masks tokens, refresh tokens, MFA secrets, and provisioning URIs automatically.

## Deployment

Render deployment is prepared but the live URL is not added yet.

- Docker startup honors Render's `PORT` environment variable.
- Alembic migration assets are included in the runtime image.
- `RUN_MIGRATIONS_ON_START=true` runs `alembic upgrade head` before Uvicorn.
- Use `postgresql+asyncpg://...` for `DATABASE_URL` on Render.
- Use the same managed Redis URL for `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` unless separate Redis DB indexes are available.
- The current Render blueprint deploys the API web service only; real external email-provider delivery and cloud Celery worker deployment are deferred.
- Deployment guide: `docs/deployment/render.md`

## Security Notes

- Real `.env` files are ignored and must not be committed.
- Refresh token reuse revokes the token family.
- Failed login counters are tracked by account and IP in Redis.
- Superusers bypass named permission checks; normal users require assigned roles/permissions.
- When MFA is enabled, login returns an MFA challenge token instead of bearer tokens. The client must verify the challenge with a current TOTP code before tokens are issued.
- Registration enforces password strength rules. Optional HaveIBeenPwned range checks can be enabled with `PASSWORD_BREACH_CHECK_ENABLED=true`.
- Email verification and password reset tokens are stored hashed in PostgreSQL. Password reset revokes existing refresh token families.

## Portfolio Status

Core implementation is complete. Remaining evidence work:

- GitHub Actions passing screenshot from the latest green run.
- Trivy SARIF artifact or scan proof from the `trivy` job.
- Postman/Swagger UI demo screenshots listed in `docs/evidence/README.md`.
- Live deployment URL after Render deployment.
- Render dashboard/log screenshots after first successful deploy.
