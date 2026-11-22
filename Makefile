# Every target runs inside the Docker Compose services, so the only host
# requirements are Docker and make. Recipes are single commands so they work
# under both sh and cmd.exe.
DC := docker compose
API := $(DC) run --rm --no-deps api
API_DB := $(DC) run --rm api
WEB := $(DC) run --rm --no-deps web

GIT_SHA := $(shell git rev-parse --short HEAD)
BENCH := $(DC) run --rm --no-deps -e GIT_SHA=$(GIT_SHA) api python -m bench

.PHONY: up down migrate seed lint test e2e data bench bench-if-missing analytics-run evidence openapi

up:
	$(DC) up -d --build --wait db valkey
	$(API_DB) alembic upgrade head
	$(DC) up -d --build

down:
	$(DC) down

migrate:
	$(API_DB) alembic upgrade head

seed:
	$(API_DB) python -m scripts.seed_demo

analytics-run:
	$(DC) run --rm -e GIT_SHA=$(GIT_SHA) api python -m analytics.jobs

lint:
	$(API) ruff check .
	$(API) ruff format --check .
	$(API) mypy app analytics bench
	$(WEB) npm run lint
	$(WEB) npm run format:check
	$(WEB) npm run typecheck

test:
	$(API_DB) pytest --cov=app --cov=analytics --cov-report=term-missing
	$(WEB) npm test

e2e:
	$(DC) --profile e2e run --rm e2e npx playwright test --grep-invert @evidence

data:
	$(BENCH) data

# Benchmark configuration for the current milestone (M0).
bench: data
	$(BENCH) run --config bench/configs/m0.yaml --out /evidence/bench/
	$(BENCH) report /evidence/bench/

# Runs the benchmark only when its results table does not exist yet.
bench-if-missing:
	$(BENCH) ensure --config bench/configs/m0.yaml --out /evidence/bench/

# Report evidence pack (SPEC Section 10). A leading "-" keeps going after a failing
# suite, so tests.md and SUMMARY.md report the failure instead of not being written.
evidence:
	$(DC) up -d --wait db valkey
	$(DC) up -d
	$(API_DB) alembic upgrade head
	$(API_DB) python -m scripts.seed_demo
	-$(DC) run --rm -e GIT_SHA=$(GIT_SHA) api python -m analytics.jobs
	-$(API_DB) pytest -q --cov=app --cov=analytics --cov-report=json:/evidence/raw/backend-coverage.json --junitxml=/evidence/raw/backend-junit.xml
	-$(WEB) npx vitest run --reporter=json --outputFile=/evidence/raw/frontend-unit.json
	-$(DC) --profile e2e run --rm -e EVIDENCE_DIR=/evidence/screenshots -e PLAYWRIGHT_JSON_OUTPUT_NAME=/evidence/raw/e2e.json e2e npx playwright test --reporter=list,json
	$(BENCH) ensure --config bench/configs/m0.yaml --out /evidence/bench/
	$(DC) run --rm --no-deps -e GIT_SHA=$(GIT_SHA) api python -m scripts.evidence

# Copy of the API contract for the frontend and a future iOS client (SPEC Section 5).
openapi:
	$(API) python -m scripts.export_openapi > docs/openapi.json
