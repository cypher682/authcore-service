# Evidence Capture Guide

Capture these before writing the Dev.to, LinkedIn, and X content. Use clean browser windows, readable zoom, and avoid showing tokens, passwords, MFA secrets, or raw `.env` values.

## Folder Naming

Recommended local folder:

```text
docs/evidence/screenshots/
```

Recommended filenames:

```text
01-github-actions-green.png
02-ci-test-coverage.png
03-trivy-scan.png
04-docker-containers-healthy.png
05-swagger-overview.png
06-register-login-postman.png
07-refresh-rotation.png
08-mfa-setup-verify.png
09-sessions-list-revoke.png
10-rbac-admin-flow.png
11-audit-logs.png
12-lockout-rate-limit.png
13-live-health-url.png
```

## Required Screenshots

### 1. GitHub Actions Green Run

- Page: `https://github.com/cypher682/authcore-service/actions/workflows/ci.yml`
- Capture the latest successful `AuthCore CI` run.
- Show all jobs if possible: `lint`, `test`, `docker-build`, and `trivy`.

### 2. CI Test Coverage

- Page: the successful Actions run logs.
- Open `Test with coverage`.
- Capture the coverage table showing `10 passed` and at least `80%` coverage.

### 3. Trivy Scan Proof

- Page: the successful Actions run logs.
- Open `Trivy critical scan`.
- Capture the scan completion or SARIF upload step.
- The point is to show the image scan ran and blocked on CRITICAL severity.

### 4. Docker Stack Health

Run locally:

```bash
docker ps --filter "name=authcore"
```

Capture `authcore_app`, `authcore_celery`, `authcore_postgres`, and `authcore_redis` as healthy/running.

### 5. Swagger / OpenAPI Overview

- Page: `http://localhost:8000/docs`
- Capture the route groups for `Auth`, `Users`, and `Admin`.
- Also capture `GET /health` executed successfully if possible.

### 6. Register + Login Flow

Use Postman collection:

```text
docs/evidence/authcore.postman_collection.json
```

Capture:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- Response status and token type only.
- Blur or crop tokens.

### 7. Refresh Token Rotation

Capture:

- `POST /api/v1/auth/refresh` succeeds with the latest refresh token.
- Reusing an older refresh token returns `401`.
- Blur all token values.

### 8. MFA Setup + Verify

Capture:

- `POST /api/v1/auth/mfa/setup`
- `POST /api/v1/auth/mfa/verify`
- Response showing `is_enabled: true`.
- Do not expose the TOTP secret or QR/provisioning URI publicly.

### 9. Sessions

Capture:

- `GET /api/v1/users/me/sessions`
- `DELETE /api/v1/users/me/sessions/{session_id}`
- Show session count before/after if practical.

### 10. RBAC Admin Flow

Capture:

- Admin creates a permission.
- Admin creates a role.
- Admin attaches permission to role.
- Admin assigns role to user.
- User passes `GET /api/v1/admin/rbac/permission-check`.

### 11. Audit Logs

Capture:

- `GET /api/v1/admin/audit-logs?limit=10`
- Show event types such as `auth.login.success`, `rbac.role.created`, `rbac.permission.created`, or `session.revoked`.

### 12. Brute Force / Lockout

Capture:

- Multiple failed login attempts.
- Final lockout response: `423`.
- Optional: route rate limit response: `429`.

### 13. Live Deployment URL

After Render deployment:

- Capture the live `/health` endpoint.
- Capture live `/docs`.
- Add the live URL to `README.md` and this evidence pack.

## Commands To Reproduce Evidence

Start stack:

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
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

Check containers:

```bash
docker ps --filter "name=authcore"
```

## What Not To Show

- Raw access tokens.
- Raw refresh tokens.
- MFA secret or provisioning URI.
- Real `.env` values.
- Personal email inboxes.
- Database passwords.

## After Capturing

Update:

- `docs/evidence/README.md` with screenshot filenames.
- `README.md` with live URL after deployment.
- Dev.to draft with selected screenshots.
- LinkedIn post with GitHub, live URL, and one strong architecture screenshot.
