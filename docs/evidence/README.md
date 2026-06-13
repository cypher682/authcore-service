# AuthCore Evidence Pack

Captured on 2026-06-12 for the F2 `authcore-service` build.

## Available Evidence

- `api-smoke-evidence.json` contains redacted API smoke proof from the running Docker stack. It stores IDs, status values, counts, and event names only; it does not store access tokens, refresh tokens, MFA secrets, or passwords.
- `ci-evidence.md` documents the local CI-equivalent checks run before handing off Step 14.
- `evidence-capture-guide.md` lists the screenshots and artifacts to capture before drafting portfolio content.
- `authcore.postman_collection.json` is a Postman collection for the portfolio demo flow.

## Verified Capabilities

- Docker stack health: `app`, `celery_worker`, `postgres`, and `redis` were healthy.
- Public API surface: `/health` and `/openapi.json`.
- Auth flow: register, login, bearer token response, refresh-compatible token issuance.
- Session tracking: user session listing after register/login.
- MFA: setup and TOTP verification enabled MFA for the evidence user.
- Admin/RBAC: superuser admin created a permission and role, attached permission to role, and assigned role to user.
- Audit logging: recent audit log sample included RBAC assignment, role/permission creation, and login success events.

## Evidence Still Best Captured Manually

- GitHub Actions run screenshot from the passing workflow.
- Trivy SARIF artifact or scan output from the GitHub Actions `trivy` job.
- Postman or Insomnia demo screenshots for portfolio presentation.
- Live deployment URL once hosting is configured.

Use `evidence-capture-guide.md` as the capture checklist.
