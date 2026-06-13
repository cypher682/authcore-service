# AuthCore Local Demo UI

This is a static browser UI for capturing portfolio evidence without fighting Postman or CLI quoting.

## Run

1. Start the API stack:

```bash
docker compose up -d
docker compose exec app alembic upgrade head
```

2. Open:

```text
docs/demo/index.html
```

3. Click the panels in order:

- Setup / Health
- User Auth
- MFA
- Sessions
- Admin Bootstrap
- RBAC + Audit
- Abuse Protection

## Screenshot Guidance

Screenshot the response cards. The UI masks:

- Access tokens
- Refresh tokens
- MFA secrets
- Provisioning URIs

## Admin Bootstrap

The browser cannot promote a user to superuser directly. After clicking `Register Admin`, click `Show Promote Command`, copy the command, and run it from `F2/authcore-service`.

Then return to the browser and click `Login Admin`.

## Notes

- This is a local evidence tool, not a production frontend.
- It uses `fetch()` against `http://localhost:8000` by default.
- It works because local `.env` runs the app with `APP_DEBUG=true`, which allows browser CORS for local evidence capture.
