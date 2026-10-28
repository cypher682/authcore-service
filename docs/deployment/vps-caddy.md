# Deploying authcore-service to the Oracle VM

Target: `https://authcore.141-148-69-94.sslip.io` on the Oracle Cloud Ampere ARM VM, behind the
Caddy container that already serves `whoami`.

```
GitHub Actions          GHCR                    Oracle VM (arm64)                     Internet
──────────────          ────                    ─────────────────                     ────────
push to main
  └ AuthCore CI ──ok──► build linux/arm64 ──► pull ──► authcore-app:8000 ──► Caddy :443 ──► TLS
      │                 push :<sha> :latest         authcore-worker              │
      └ Deploy ──────────── ssh ──────────────────►  authcore-postgres (internal) ─┘
                                                     authcore-redis    (internal)
```

Nothing is built on the server. The image is built in CI, pushed to GHCR, pulled by tag, and the
host only runs `docker compose pull && docker compose up -d`.

---

## 1. GitHub repository secrets — this is the whole list

Only **deployment plumbing** goes into GitHub. Application settings (DB password, JWT secret,
SMTP) stay in `/opt/apps/authcore/.env` on the server, so a compromised workflow cannot leak them
and rotating them never means touching the repo.

| Secret | Required | Value |
|---|---|---|
| `DEPLOY_HOST` | yes | `141.148.69.94` |
| `DEPLOY_USER` | yes | `deploy` (the non-root user with docker access) |
| `DEPLOY_SSH_KEY` | yes | Private key of the deploy keypair, full PEM including header/footer lines |
| `DEPLOY_PORT` | no | `22` if omitted |
| `GHCR_USER` | only if the package is private | `cypher682` |
| `GHCR_TOKEN` | only if the package is private | Classic PAT with `read:packages` scope |

`GITHUB_TOKEN` is provided by Actions automatically — it pushes the image (`packages: write` is
already declared in the workflow). Nothing else is needed, no Docker Hub account.

**Public or private package?** Public is the simpler default: the compose file is public, the
source is public, and `docker compose pull` then needs no credentials on the host. Push once, open
the package page under the repo's *Packages*, and set visibility to public if it was created
private. If you prefer private, add `GHCR_USER` + `GHCR_TOKEN` and the workflow logs in on the
server before pulling; no file changes.

---

## 2. One-time server preparation

All as the `deploy` user over SSH (or root with `sudo`), from the server itself.

```bash
# The deploy user must be able to talk to the Docker socket.
id deploy | grep -q docker || sudo usermod -aG docker deploy   # then log out and back in

# Deploy directory — owned by deploy so the pipeline never needs sudo.
sudo mkdir -p /opt/apps/authcore
sudo chown deploy:deploy /opt/apps/authcore

# The shared network Caddy already publishes on.
docker network ls --format '{{.Name}}' | grep -qx web || docker network create web
```

Generate the deploy keypair **on your laptop** and install the public half:

```bash
ssh-keygen -t ed25519 -C "github-actions-authcore" -f ~/.ssh/authcore_deploy -N ""
ssh-copy-id -i ~/.ssh/authcore_deploy.pub deploy@141.148.69.94
cat ~/.ssh/authcore_deploy            # paste this into DEPLOY_SSH_KEY
```

Check the `deploy` account's SSH is sane before blaming the pipeline:

```bash
ssh -i ~/.ssh/authcore_deploy deploy@141.148.69.94 'whoami && docker ps'
```

`whoami` must print `deploy` and `docker ps` must not ask for sudo. If it does, the group change
has not taken effect for that session.

---

## 3. The application `.env`

```bash
cd /opt/apps/authcore
install -m 600 /dev/null .env
cat > .env <<EOF
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_USER=authcore
POSTGRES_PASSWORD=$(openssl rand -hex 24)
POSTGRES_DB=authcore_db
RUN_MIGRATIONS_ON_START=true
EMAILS_FROM=noreply@authcore.example
PASSWORD_BREACH_CHECK_ENABLED=false
EOF
chmod 600 .env
```

Both generated values are hex on purpose: `POSTGRES_PASSWORD` is interpolated into the
`DATABASE_URL`, so `@ : /` would corrupt the connection string. `deploy/.env.prod.example` lists
every optional setting (JWT lifetimes, rate limits, lockout) with the production values.

The compose file supplies `DATABASE_URL`, `REDIS_URL` and the Celery URLs itself, pointing at the
container names — do not put `localhost` URLs here.

---

## 4. The Caddy block

Add `deploy/Caddyfile.snippet` to `/opt/caddy/Caddyfile`, validate, then reload. Validate before
reload so a typo cannot take `whoami` down with it:

```bash
sudo cp /opt/caddy/Caddyfile /opt/caddy/Caddyfile.bak
sudo tee -a /opt/caddy/Caddyfile >/dev/null <<'EOF'

authcore.141-148-69-94.sslip.io {
	encode zstd gzip
	reverse_proxy authcore-app:8000
}
EOF

sudo docker exec caddy caddy validate --config /etc/caddy/Caddyfile
sudo docker exec caddy caddy reload  --config /etc/caddy/Caddyfile
```

No DNS record: `authcore.<ip-with-dashes>.sslip.io` resolves to `141.148.69.94` by construction,
and Caddy obtains the certificate on the first request. Until the app container exists, that
request returns `502` — expected before the first deploy.

---

## 5. First deploy

```bash
git push origin main        # or: Actions -> Deploy -> Run workflow
```

Watch the `Deploy` run: *Build and push image* (arm64, ~4–6 min under QEMU) → *Deploy to Oracle VM*
→ *Verify the public endpoint*. The last step polls `https://…/health` for 90 s, which also covers
first-time certificate issuance.

Verify by hand:

```bash
curl -s https://authcore.141-148-69-94.sslip.io/health
curl -sI https://authcore.141-148-69-94.sslip.io/docs | head -n1
ssh deploy@141.148.69.94 'cd /opt/apps/authcore && docker compose ps'
```

`/health` returns the service name, version and `"env":"production"`; `/docs` returns Swagger UI.

---

## 6. What happens on a normal push

1. `AuthCore CI` runs lint, tests with the 80% coverage gate, image build, Trivy scan.
2. If CI succeeded on `main`, `Deploy` builds `linux/arm64` and pushes `:<sha>` **and** `:latest`.
3. The runner `scp`s `deploy/docker-compose.prod.yml` to `/opt/apps/authcore/docker-compose.yml` —
   the repo is the source of truth for the stack definition.
4. It runs `docker compose pull` and `up -d --wait --wait-timeout 180`. The app container runs
   `alembic upgrade head` before uvicorn, so schema changes land before traffic does.
5. It polls the public `/health` and fails the run if the URL is not serving.

A red `Deploy` therefore means the site is actually down — not just "step finished strangely".

**Rollback** — every push keeps an immutable sha tag:

```bash
ssh deploy@141.148.69.94
cd /opt/apps/authcore
IMAGE_TAG=<previous-sha> docker compose up -d
```

The host keeps a week of previous sha images; GHCR keeps every tag, so an older `IMAGE_TAG` still
pulls even after the local copy is pruned.

---

## 7. When it breaks

| Symptom | Cause |
|---|---|
| `permission denied (publickey)` | `DEPLOY_USER`/key mismatch, or `~/.ssh` on the server is group-writable |
| `docker: command not found` / permission denied on socket | `deploy` not in the `docker` group in that session |
| `compose up` exits non-zero | Health wait timed out; the run prints `docker compose ps` and the last 100 log lines |
| `Error: pull access denied` | Package is private and `GHCR_*` secrets are missing |
| `502` from Caddy, container healthy | App not on the `web` network, or the upstream name differs from `container_name` |
| `exec format error` | Image built for the wrong platform — the VM is arm64 |
| Cert not issued | Port 80 unreachable; Caddy needs it for the ACME HTTP challenge |

Logs live on the host, not in Actions:

```bash
cd /opt/apps/authcore && docker compose logs --tail 100 app
sudo docker logs caddy --tail 50
```

---

## 8. Two things that will bite later

**The hostname is tied to the IP.** `141-148-69-94` is part of the URL. If the instance's public IP
changes, every URL in the docs breaks. Add a wildcard `*.yourdomain.dev` A record to the IP and the
only edit is the hostname in `Caddyfile` and the `PUBLIC_URL` env in `deploy.yml`.

**The server is €250-credit-shaped right now.** After 18 November the credit is gone; the instance
must be inside the Always Free shape (2 OCPU / 12 GB) or the stack quietly starts costing money.
Resize in place — do not terminate and recreate, or the free-tier allowance may not come back.
