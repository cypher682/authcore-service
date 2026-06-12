# AuthCore Service

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
- Admin APIs for users, roles, permissions, RBAC checks, and audit log queries.
- Docker Compose stack with FastAPI, PostgreSQL, Redis, and Celery worker.
- Pytest suite with 85% coverage.
- GitHub Actions CI for lint, format, tests, Docker build, and Trivy CRITICAL scan.

## Tech Stack

| Area | Tools |
|---|---|
| API | FastAPI, Python 3.13, Pydantic v2 |
| Database | PostgreSQL, SQLAlchemy 2.0, Alembic |
| Cache / lockout | Redis |
| Async worker | Celery with Redis broker |
| Security | bcrypt, PyJWT, pyotp, SlowAPI |
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
| `POST` | `/api/v1/auth/login` | Login and issue tokens |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token |
| `POST` | `/api/v1/auth/mfa/setup` | Create/reuse pending TOTP setup |
| `POST` | `/api/v1/auth/mfa/verify` | Enable MFA with current TOTP code |
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
| CI validation notes | `docs/evidence/ci-evidence.md` |
| Postman collection | `docs/evidence/authcore.postman_collection.json` |

Current local validation:

- `10 passed`
- `85%` coverage
- Ruff passed
- Black check passed
- Docker runtime image build passed
- All Docker Compose services healthy at handoff

## CI/CD

Workflow file: `.github/workflows/ci.yml`

Jobs:

- `lint`: Ruff and Black.
- `test`: Docker Compose dependency startup, Alembic migration, pytest coverage.
- `docker-build`: runtime image build.
- `trivy`: CRITICAL vulnerability scan with SARIF upload.

## Security Notes

- Real `.env` files are ignored and must not be committed.
- Refresh token reuse revokes the token family.
- Failed login counters are tracked by account and IP in Redis.
- Superusers bypass named permission checks; normal users require assigned roles/permissions.
- Login currently still issues tokens when MFA is enabled; challenge-enforced login is intentionally left as a later refinement.

## Portfolio Status

Core implementation is complete. Remaining evidence work:

- GitHub Actions passing screenshot.
- Trivy SARIF artifact from remote CI run.
- Postman/Swagger UI demo screenshots.
- Live deployment URL after Render deployment.
