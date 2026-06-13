# AuthCore Evidence Pack

Captured during the F2 `authcore-service` build.

## Available Evidence

- `api-smoke-evidence.json` contains redacted API smoke proof from the running Docker stack. It stores IDs, status values, counts, and event names only; it does not store access tokens, refresh tokens, MFA secrets, or passwords.
- `ci-evidence.md` documents the local CI-equivalent checks run before handing off Step 14.
- `evidence-capture-guide.md` lists the screenshots and artifacts to capture before drafting portfolio content.
- `../demo/index.html` is a local browser UI for screenshot-friendly API testing without Postman.
- `authcore.postman_collection.json` is a Postman collection for the portfolio demo flow.
- `../deployment/render.md` documents the Render deployment steps and required environment variables.

## Screenshot Evidence

- `screenshots/01-github-actions-green.png` shows the passing GitHub Actions workflow.
- `screenshots/02-ci-test-coverage.png` shows local pytest coverage output.
- `screenshots/03-trivy-scan.png` shows the Trivy scan job output.
- `screenshots/04-docker-containers-healthy.png` shows Docker Compose services running healthy.
- `screenshots/05-swagger-overview.png` shows the Swagger/OpenAPI auth surface.
- `screenshots/06-register-login.png` shows the masked register/login response.
- `screenshots/07-refresh-rotation.png` shows refresh token rotation evidence.
- `screenshots/08-mfa-setup-verify.png` shows masked MFA setup/verify evidence.
- `screenshots/09-sessions-list-revoke.png` shows session list/revoke evidence.
- `screenshots/10-rbac-admins-list.png` shows admin/RBAC evidence.
- `screenshots/11-audit-logs.png` shows audit log evidence.
- `screenshots/12-lockout-rate-limit.png` shows lockout/rate-limit evidence.
- `screenshots/13-live-health-url.png` shows the local health response.

## Verified Capabilities

- Docker stack health: `app`, `celery_worker`, `postgres`, and `redis` were healthy.
- Public API surface: `/health` and `/openapi.json`.
- Auth flow: register, login, bearer token response, refresh-compatible token issuance.
- Account recovery: email verification and password reset token flows are implemented with hashed stored tokens.
- Session tracking: user session listing after register/login.
- MFA: setup and TOTP verification enabled MFA for the evidence user.
- Admin/RBAC: superuser admin created a permission and role, attached permission to role, and assigned role to user.
- Audit logging: recent audit log sample included RBAC assignment, role/permission creation, and login success events.

## Evidence Still Best Captured Manually

- Live deployment URL once hosting is configured.
- Render dashboard and startup log screenshots after the first successful live deploy.

Use `evidence-capture-guide.md` as the capture checklist.
