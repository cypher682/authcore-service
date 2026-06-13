# Evidence Capture Guide

Capture these before writing the Dev.to, LinkedIn, and X content. Use clean browser windows, readable zoom, and avoid showing tokens, passwords, MFA secrets, or raw `.env` values.

If Postman or CLI testing is slow, open `docs/demo/index.html` in your browser and click through the panels from top to bottom. The local demo calls the same API endpoints and masks sensitive fields in the response cards.

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

## Postman API Test Workflow

You can use either Postman or the local browser demo for this workflow. The endpoint order is the same.

Use this workflow to personally test each endpoint and capture evidence responses.

### 0. Start Local Stack

From `F2/authcore-service`:

```bash
docker compose up -d
docker compose exec app alembic upgrade head
docker ps --filter "name=authcore"
```

Expected:

- `authcore_app` is healthy.
- `authcore_postgres` is healthy.
- `authcore_redis` is healthy.
- `authcore_celery` is running/healthy.

### 1. Import Collection

Import:

```text
docs/evidence/authcore.postman_collection.json
```

Set these collection variables:

| Variable | Example |
|---|---|
| `base_url` | `http://localhost:8000` |
| `email` | `demo-user-001@example.com` |
| `admin_email` | `demo-admin-001@example.com` |
| `password` | `Str0ngDemoPass!` |
| `access_token` | blank initially |
| `refresh_token` | blank initially |
| `old_refresh_token` | blank initially |
| `mfa_code` | blank initially |
| `user_id` | blank initially |
| `admin_access_token` | blank initially |
| `role_id` | blank initially |
| `permission_id` | blank initially |
| `session_id` | blank initially |

Use a new email each time you rerun the full flow.

### 2. Health Check

Request:

```http
GET {{base_url}}/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "authcore-service"
}
```

Screenshot:

- Capture status `200`.
- Capture `status: healthy`.

### 3. OpenAPI Schema

Request:

```http
GET {{base_url}}/openapi.json
```

Expected:

- Status `200`.
- JSON includes `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/admin/audit-logs`.

Screenshot:

- Better screenshot from browser: `{{base_url}}/docs`.
- Show `Auth`, `Users`, and `Admin` route groups.

### 4. Register Normal User

Request:

```http
POST {{base_url}}/api/v1/auth/register
Content-Type: application/json
```

Body:

```json
{
  "email": "{{email}}",
  "password": "{{password}}"
}
```

Expected:

- Status `201`.
- Response includes `access_token`, `refresh_token`, `token_type`, and `user`.

Postman Tests tab:

```javascript
const body = pm.response.json();
pm.collectionVariables.set("access_token", body.access_token);
pm.collectionVariables.set("refresh_token", body.refresh_token);
pm.collectionVariables.set("old_refresh_token", body.refresh_token);
pm.collectionVariables.set("user_id", body.user.id);
```

Screenshot:

- Capture status `201`.
- Capture `token_type: bearer`.
- Capture user email or ID.
- Hide or blur token values.

### 5. Login Normal User

Request:

```http
POST {{base_url}}/api/v1/auth/login
Content-Type: application/json
```

Body:

```json
{
  "email": "{{email}}",
  "password": "{{password}}"
}
```

Expected:

- Status `200`.
- New token pair returned.

Postman Tests tab:

```javascript
const body = pm.response.json();
pm.collectionVariables.set("access_token", body.access_token);
pm.collectionVariables.set("refresh_token", body.refresh_token);
```

Screenshot:

- Capture successful login.
- Hide tokens.

### 6. Refresh Token Rotation

First refresh with current token.

Request:

```http
POST {{base_url}}/api/v1/auth/refresh
Content-Type: application/json
```

Body:

```json
{
  "refresh_token": "{{refresh_token}}"
}
```

Expected:

- Status `200`.
- New `access_token` and `refresh_token`.

Postman Tests tab:

```javascript
const body = pm.response.json();
pm.collectionVariables.set("access_token", body.access_token);
pm.collectionVariables.set("refresh_token", body.refresh_token);
```

Now prove reuse detection by sending the old refresh token.

Request:

```http
POST {{base_url}}/api/v1/auth/refresh
Content-Type: application/json
```

Body:

```json
{
  "refresh_token": "{{old_refresh_token}}"
}
```

Expected:

- Status `401`.
- Token family reuse is rejected.

Screenshot:

- Capture the successful refresh response first.
- Capture the `401` reuse rejection.
- Hide all token values.

### 7. MFA Setup

Request:

```http
POST {{base_url}}/api/v1/auth/mfa/setup
Authorization: Bearer {{access_token}}
```

Expected:

- Status `200`.
- Response includes `secret`, `provisioning_uri`, and `is_enabled: false`.

Do not screenshot the raw secret publicly. For testing, copy the secret locally.

Generate the current TOTP code in the app container:

```bash
docker compose exec app python -c "import pyotp; print(pyotp.TOTP('PASTE_SECRET_HERE').now())"
```

Set Postman variable:

```text
mfa_code=<generated 6 digit code>
```

### 8. MFA Verify

Request:

```http
POST {{base_url}}/api/v1/auth/mfa/verify
Authorization: Bearer {{access_token}}
Content-Type: application/json
```

Body:

```json
{
  "code": "{{mfa_code}}"
}
```

Expected:

- Status `200`.
- Response:

```json
{
  "is_enabled": true
}
```

Screenshot:

- Capture `is_enabled: true`.
- Do not show the secret or provisioning URI.

### 9. List Sessions

Request:

```http
GET {{base_url}}/api/v1/users/me/sessions
Authorization: Bearer {{access_token}}
```

Expected:

- Status `200`.
- Array of sessions.

Postman Tests tab:

```javascript
const body = pm.response.json();
if (body.length > 0) {
  pm.collectionVariables.set("session_id", body[0].id);
}
```

Screenshot:

- Capture session fields: `id`, `device_fingerprint`, `ip_address`, `last_active`.
- Hide anything you consider sensitive.

### 10. Revoke Session

Request:

```http
DELETE {{base_url}}/api/v1/users/me/sessions/{{session_id}}
Authorization: Bearer {{access_token}}
```

Expected:

- Status `204`.
- No response body.

Screenshot:

- Capture status `204`.

### 11. Register Admin User

Request:

```http
POST {{base_url}}/api/v1/auth/register
Content-Type: application/json
```

Body:

```json
{
  "email": "{{admin_email}}",
  "password": "{{password}}"
}
```

Expected:

- Status `201`.

Promote this user to superuser locally:

```bash
docker compose exec postgres psql -U authcore -d authcore_db -c "UPDATE users SET is_superuser = true WHERE email = 'demo-admin-001@example.com';"
```

Replace `demo-admin-001@example.com` with your actual `admin_email` variable.

### 12. Login Admin User

Request:

```http
POST {{base_url}}/api/v1/auth/login
Content-Type: application/json
```

Body:

```json
{
  "email": "{{admin_email}}",
  "password": "{{password}}"
}
```

Expected:

- Status `200`.
- Admin token pair returned.

Postman Tests tab:

```javascript
const body = pm.response.json();
pm.collectionVariables.set("admin_access_token", body.access_token);
```

Screenshot:

- Capture successful admin login.
- Hide tokens.

### 13. Create `admin:manage` Permission

First check whether it already exists.

Request:

```http
GET {{base_url}}/api/v1/admin/permissions
Authorization: Bearer {{admin_access_token}}
```

If `admin:manage` exists, copy its `id` into `permission_id`.

If it does not exist, create it:

```http
POST {{base_url}}/api/v1/admin/permissions
Authorization: Bearer {{admin_access_token}}
Content-Type: application/json
```

Body:

```json
{
  "name": "admin:manage",
  "resource": "admin",
  "action": "manage",
  "description": "Allows access to protected admin manage route"
}
```

Expected:

- Status `201`.

Postman Tests tab:

```javascript
const body = pm.response.json();
pm.collectionVariables.set("permission_id", body.id);
```

Screenshot:

- Capture created/listed permission.

### 14. Create Role

Request:

```http
POST {{base_url}}/api/v1/admin/roles
Authorization: Bearer {{admin_access_token}}
Content-Type: application/json
```

Body:

```json
{
  "name": "portfolio-admin-demo",
  "description": "Portfolio evidence role for admin manage permission"
}
```

Expected:

- Status `201`.

Postman Tests tab:

```javascript
const body = pm.response.json();
pm.collectionVariables.set("role_id", body.id);
```

If the role already exists, use `GET /api/v1/admin/roles` and copy the existing role ID into `role_id`.

### 15. Attach Permission To Role

Request:

```http
POST {{base_url}}/api/v1/admin/roles/{{role_id}}/permissions
Authorization: Bearer {{admin_access_token}}
Content-Type: application/json
```

Body:

```json
{
  "permission_id": "{{permission_id}}"
}
```

Expected:

- Status `204`.

Screenshot:

- Capture `204`.

### 16. Assign Role To Normal User

Request:

```http
POST {{base_url}}/api/v1/admin/users/roles
Authorization: Bearer {{admin_access_token}}
Content-Type: application/json
```

Body:

```json
{
  "user_id": "{{user_id}}",
  "role_id": "{{role_id}}"
}
```

Expected:

- Status `204`.

Screenshot:

- Capture `204`.

### 17. Verify RBAC Permission Check

Use the normal user's access token.

Request:

```http
GET {{base_url}}/api/v1/admin/rbac/permission-check
Authorization: Bearer {{access_token}}
```

Expected:

- Status `200`.
- Response includes:

```json
{
  "status": "allowed",
  "permission": "admin:manage"
}
```

Screenshot:

- Capture the allowed response.

### 18. Query Audit Logs

Use the admin token.

Request:

```http
GET {{base_url}}/api/v1/admin/audit-logs?limit=10
Authorization: Bearer {{admin_access_token}}
```

Expected:

- Status `200`.
- Events include auth, MFA, RBAC, or session actions.

Screenshot:

- Capture event types such as `auth.login.success`, `rbac.role.created`, `rbac.permission.created`, `rbac.user_role.assigned`, or `session.revoked`.

### 19. Failed Login Lockout

Use the normal user's email and a wrong password.

Request:

```http
POST {{base_url}}/api/v1/auth/login
Content-Type: application/json
```

Body:

```json
{
  "email": "{{email}}",
  "password": "WrongPassword123!"
}
```

Run this repeatedly.

Expected:

- First failed attempts return `401`.
- After the configured threshold, response returns `423`.

Screenshot:

- Capture one `401`.
- Capture final `423` lockout response.

If you need to reset lockout counters locally:

```bash
docker compose exec redis redis-cli --scan --pattern "authcore:login:*" | ForEach-Object { docker compose exec redis redis-cli DEL $_ }
```

On Git Bash/WSL:

```bash
docker compose exec redis sh -c 'redis-cli --scan --pattern "authcore:login:*" | xargs -r redis-cli DEL'
```

### 20. Rate Limit Evidence

The auth route limit is `10/minute`.

Use any auth endpoint repeatedly, for example bad refresh:

```http
POST {{base_url}}/api/v1/auth/refresh
Content-Type: application/json
```

Body:

```json
{
  "refresh_token": "bad-token"
}
```

Expected:

- After repeated requests in the same minute, response returns `429`.

Screenshot:

- Capture the `429` response.

## Quick Screenshot Checklist

Use this as a final checklist after completing the Postman workflow.

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
- Capture Render deploy logs showing startup.
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
