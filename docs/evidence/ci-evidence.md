# CI Evidence

Captured on 2026-06-12 after adding the service workflow at `.github/workflows/ci.yml`.

## Workflow Gates

- Ruff lint: `ruff check app tests alembic`
- Black format check: `black --check app tests alembic`
- Docker-first tests: `pytest --cov=app --cov-report=term-missing --cov-fail-under=80 -q`
- Docker build: `docker build --target runtime`
- Trivy critical image scan: GitHub Actions job blocks on `CRITICAL` severity findings and uploads SARIF.

## Remote CI

- Repository: `https://github.com/cypher682/authcore-service`
- Workflow: `https://github.com/cypher682/authcore-service/actions/workflows/ci.yml`
- Passing run: `https://github.com/cypher682/authcore-service/actions/runs/27447084549`
- Final green commit: `96d4423 Stabilize CI test and scan jobs`

## Local Validation

- `docker compose config` passed.
- `docker compose exec -e RUFF_CACHE_DIR=/tmp/ruff_cache app ruff check app tests alembic` passed.
- `docker compose exec app black --check app tests alembic` passed.
- `docker compose exec -e COVERAGE_FILE=/tmp/.coverage app pytest --cov=app --cov-report=term-missing --cov-fail-under=80 -q` returned `18 passed` with 81% coverage.
- `docker build --target runtime -t authcore-service:ci-check .` passed.

## Known Warning

- `pytest-asyncio` warns about the custom session-scoped `event_loop` fixture in `tests/conftest.py`. This is tracked from Step 12 and does not fail the current CI gate.
