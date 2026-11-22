# Qauym

A Nazarbayev University senior project: a social web app that detects communities in its user graph with Leiden (primary) and Louvain (baseline). The full specification is [docs/SPEC.md](docs/SPEC.md).

## Setup

You need Docker (with Compose) and `make`. On Windows: `winget install ezwinports.make`.

```sh
git clone https://github.com/nundudid/qauym-demo
cd qauym-demo
make up
```

Then open:

- Web app: http://localhost:5173
- API health: http://localhost:8000/api/v1/health
- API docs: http://localhost:8000/api/v1/docs

`make down` stops everything. Copy `.env.example` to `.env` only if you need to change a port or password.

## Demo

```sh
make seed            # synthetic demo users and activity
make analytics-run   # infer communities (or press "Run now" as the admin)
```

Then follow [docs/DEMO.md](docs/DEMO.md). It lists the demo accounts.

## Make targets

| Target | What it does |
| --- | --- |
| `make up` / `make down` | Start or stop all Docker Compose services |
| `make migrate` | Apply Alembic migrations |
| `make seed` | Load synthetic demo users and activity |
| `make analytics-run` | Trigger one analytics run (build, detect, validate, publish) |
| `make lint` | ruff, mypy, eslint, prettier check |
| `make test` | Backend tests with coverage, then frontend unit tests |
| `make e2e` | Playwright end-to-end tests against the running stack |
| `make data` | Download benchmark datasets and verify checksums |
| `make bench` | Run the Leiden and Louvain benchmark and write the results table |
| `make evidence` | Produce screenshots, benchmark table and test summary in `evidence/` |
| `make openapi` | Refresh `docs/openapi.json` |

Run one test suite at a time: the backend tests share one test database.

## Working on the project

Read [AGENTS.md](AGENTS.md). One task ID from SPEC Section 11 per branch, and `make lint test` before every pull request.
