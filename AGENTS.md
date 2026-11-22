# Qauym – rules for coding agents

Qauym is a Nazarbayev University senior project: a social web app that detects communities in its user graph with Leiden (primary) and Louvain (baseline). The full specification is docs/SPEC.md. Read it before changing code. If the spec and the code disagree, the spec wins. If the spec is silent or looks wrong, stop and ask instead of guessing.

## Stack (change only with an entry in docs/DECISIONS.md)
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (sync, psycopg 3), Alembic, PostgreSQL 16
- Jobs: Valkey 8 + RQ 2.x. Analytics: python-igraph, leidenalg, networkx, numpy, pandas, scikit-learn
- Frontend: React + Vite + TypeScript, React Router, TanStack Query, Tailwind CSS, Cytoscape.js
- Tests: pytest, pytest-cov, Playwright, Locust. Lint: ruff, mypy, eslint, prettier
- Everything runs with docker compose; use the Makefile targets

## How to work
1. Work on one task ID from SPEC Section 11 at a time, on a branch named t<id>-<short-name>.
2. Before coding, restate the task's "Done when" criteria and list the files you will touch.
3. Write or update tests first, named after the requirement IDs in the task (FR-xx, NFR-xx, DR-xx).
4. Keep pull requests small (aim for under 400 changed lines). Do not refactor unrelated code.
5. Run `make lint test` before saying a task is done, and report the real output. Never claim tests pass if you did not run them.
6. Record any decision the spec did not cover in docs/DECISIONS.md.

## Non-negotiable rules
- Every endpoint that returns users, posts, comments, communities, suggestions or graph data goes through app/services/visibility.py.
- Never show the viewer anything they could not already see, including inside explanations and graph views.
- Analytics results become visible only through the atomic publish step. A failed run leaves the previous result active.
- Passwords: Argon2id. Sessions: httpOnly cookies. No secrets in git (.env is gitignored; keep .env.example current).
- Never log passwords, tokens, cookies or post/comment bodies.
- Demo users have is_synthetic = true. Never scrape websites. Benchmark data comes only from bench/datasets.yaml.
- Only add dependencies with GPL-3.0-compatible licences (MIT, BSD, Apache-2.0, LGPL, GPL) and list them in docs/DEPENDENCIES.md.
- In the UI, call communities "inferred" and never give them sensitive names.
