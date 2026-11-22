# Dependencies and licences

Every direct dependency must have a GPL-3.0-compatible licence (AGENTS.md). Add a row when you add a dependency.

## Backend (`backend/pyproject.toml`)

| Package | Licence | Used for |
| --- | --- | --- |
| fastapi | MIT | API framework |
| uvicorn | BSD-3-Clause | ASGI server |
| pydantic, pydantic-settings | MIT | Schemas and configuration |
| sqlalchemy | MIT | ORM |
| psycopg | LGPL-3.0 | PostgreSQL driver |
| alembic | MIT | Migrations |
| argon2-cffi | MIT | Argon2id password hashing |
| redis | MIT | Client for Valkey (rate limiting; RQ from M2) |
| python-igraph | GPL-2.0-or-later | Graphs and Louvain (multilevel) |
| leidenalg | GPL-3.0-or-later | Leiden |
| networkx | BSD-3-Clause | LFR benchmark generator |
| numpy | BSD-3-Clause | Arrays |
| pandas | BSD-3-Clause | Benchmark tables |
| scikit-learn | BSD-3-Clause | NMI and ARI |
| psutil | BSD-3-Clause | Hardware description |
| matplotlib | PSF-based (BSD-compatible) | Benchmark figure |
| pyyaml | MIT | Benchmark and analytics configuration |
| pytest, pytest-cov | MIT | Tests and coverage (dev) |
| httpx | BSD-3-Clause | FastAPI TestClient transport (dev) |
| ruff | MIT | Lint and format (dev) |
| mypy | MIT | Type checking (dev) |
| uv | MIT / Apache-2.0 | Dependency installer (build only) |

## Frontend (`frontend/package.json`)

| Package | Licence | Used for |
| --- | --- | --- |
| react, react-dom | MIT | UI |
| react-router-dom | MIT | Routing |
| @tanstack/react-query | MIT | Server state |
| tailwindcss, @tailwindcss/vite | MIT | Styling |
| vite, @vitejs/plugin-react | MIT | Build and dev server |
| typescript | Apache-2.0 | Type checking |
| vitest | MIT | Unit tests |
| @testing-library/react, @testing-library/jest-dom | MIT | Component tests |
| jsdom | MIT | Test DOM |
| eslint, @eslint/js, typescript-eslint, eslint-plugin-react-hooks, globals | MIT | Lint |
| prettier | MIT | Formatting |
| @playwright/test | Apache-2.0 | End-to-end tests and screenshots |

## Services

| Image | Licence |
| --- | --- |
| postgres:16 | PostgreSQL Licence |
| valkey/valkey:8 | BSD-3-Clause |
| mcr.microsoft.com/playwright | Apache-2.0 (test runner only) |
