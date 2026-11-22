# Qauym MVP – Statement of Work and Build Prompt


This document is the single source of truth for building the Qauym MVP with an AI coding agent such as Claude Code, Cursor or Codex. It turns the requirements baseline (the UR, FR, NFR and DR IDs in the Requirements and Design document and the final report) into fixed technical decisions, so the agent builds what the report describes instead of guessing.

## 1. How to use this document

1. **Put it in the repository.** Export this doc as Markdown (Export menu) and commit it as `docs/SPEC.md`. Copy the rules block in Section 12.1 into `AGENTS.md` at the repository root, and into `CLAUDE.md` too if you use Claude Code.
2. **Start every session the same way.** Paste the session prompt (12.2), then the prompt for the current milestone (12.3 to 12.5).
3. **One task per session and branch.** Use the task IDs from Section 11 (for example T0.3) in branch names and pull-request titles.
4. **Review every pull request yourselves.** Run `make lint test`, click through the feature, and tick the task's acceptance criteria. Do not merge code that nobody on the team can explain: you will defend it in the demo and the final report.
5. **Fix the spec before re-prompting.** When the agent hits a gap or a wrong assumption, change this doc first, re-export it, then re-prompt. Record decisions the spec did not cover in `docs/DECISIONS.md`.
6. **Keep the evidence.** `make evidence` (Section 10) produces the screenshots, benchmark table and test numbers that fill the report's placeholders.

## 2. Scope and milestones

The report, the presentation and a working prototype are all due on Friday 27 November 2026, so the whole Fall build is one five-day sprint. M0 is what must exist by Thursday's code freeze. M1, the end-to-end slice, starts only if M0 is done by Wednesday 18:00; otherwise it is the first work after the winter break. Each milestone must leave the app runnable from a fresh clone with `make up`.

| Milestone | Deadline | Goal | Must include | Done when |
| --- | --- | --- | --- | --- |
| M0: Fall sprint | Thu 26 Nov 2026, 18:00 code freeze | A working prototype to show in the report and the presentation | Repository, Docker Compose and CI; accounts and profiles (FR-01, FR-02); posts, follows, likes, comments (FR-03); event log with outbox and idempotency (FR-04); feed UI; benchmark harness with Leiden and Louvain on LFR and SNAP email-Eu-core (FR-06 offline, FR-12) | An end-to-end test (register, post, follow, like, comment) passes; `make bench` writes the results table; `make evidence` writes Figures 5–7 |
| M1: vertical slice | Stretch goal for Thu 26 Nov; otherwise Fri 15 Jan 2027 | User activity becomes a visible inferred community | Synthetic demo data; snapshot builder (FR-05); analytics run with validation and atomic publication, started by `make analytics-run` or the admin button (FR-06, FR-07); My communities page (FR-08); admin runs page | The demo script in `docs/DEMO.md` runs in under 10 minutes on a fresh clone; the forced-failure test keeps the previous result active |
| Submission | Fri 27 Nov 2026, 23:59 | Report with its Turnitin report, and the presentation | – | – |
| Winter break | 28 Nov 2026 – 10 Jan 2027 | No planned work | – | – |
| M2: MVP complete | Fri 5 Feb 2027 | Every Fall-tagged requirement met | Explained suggestions with cold start (FR-09); bounded graph view with text summary (FR-10); blocking, reporting and moderation (FR-11); read-time privacy filter; analytics on the RQ worker with outbox-driven and nightly runs; inference opt-out; NFR-01 to NFR-08 | All acceptance tests pass in CI; backend coverage at least 75%; load test and scale benchmark reported; iOS go/no-go memo written |

**Five-day plan (23–27 November).** Everyone is blocked until T0.1 lands, so it comes first on Monday morning. The M1 decision is made on Wednesday at 18:00: start it only if the core-flow test passes and the benchmark table exists.

| Day | Amankeldi (backend) | Islam (frontend) | Nurdaulet (algorithms) | Yernur (DevOps, data) | Nurbek (product, docs) |
| --- | --- | --- | --- | --- | --- |
| Mon 23 Nov | T0.2 models and migration, once T0.1 lands | T0.5 screens against a mock API | T0.6 LFR loader, detectors, metrics | T0.1 scaffold by noon, then CI | Presentation outline; tests list from FR IDs |
| Tue 24 Nov | T0.3 auth; start T0.4 | Connect screens to the real API | email-Eu-core; child-process runs; first results table | T0.7 datasets; CI with PostgreSQL | Write FR-01 to FR-04 tests with Amankeldi |
| Wed 25 Nov | Finish T0.4; if M1 starts, T1.4 | Core-flow e2e test; if M1 starts, T1.5 | `fig7_bench.png`; if M1 starts, T1.2 | T0.8 evidence spec; if M1 starts, T1.1 | M1 go/no-go at 18:00; slide draft |
| Thu 26 Nov | Bug fixes; T1.3 if M1 started | Polish; check at 375 px | Final benchmark on one fixed machine | `make evidence` on a clean clone after the 18:00 freeze | Send evidence to Claude; fill the report; finish slides |
| Fri 27 Nov | Demo rehearsal | Demo rehearsal | Demo rehearsal | Generate the Turnitin report in Moodle | Export the report; upload report and Turnitin report to Drive by 23:59 |

**Out of scope for this SoW:** overlapping and temporal methods (FR-13), the recommendation evaluation study (FR-14), the user study, the iOS client, graph neural networks, public production hosting, images and media uploads, direct messages, notifications, email verification and password reset by email. These belong to Spring 2027 or later.

**Definition of done for every task:** code and tests merged, CI green, a teammate has reviewed it, its acceptance criteria are ticked, and any new decision is written in `docs/DECISIONS.md`.

## 3. Fixed technology decisions and repository layout

These choices are fixed so the agent never picks a framework on its own. Changing one needs an entry in `docs/DECISIONS.md` and a teammate's approval.

| Concern | Decision | Reason |
| --- | --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x (synchronous, psycopg 3 driver), Alembic migrations, uvicorn | Matches the report; sync SQLAlchemy is simpler to debug than async |
| Database | PostgreSQL 16 | Single source of truth for app data, events, snapshots and results |
| Authentication | Server-side sessions: random token (`secrets.token_urlsafe(32)`), stored as a SHA-256 hash, sent as an httpOnly, SameSite=Lax cookie (Secure outside local dev); 14-day expiry; passwords hashed with Argon2id (`argon2-cffi`) | Logout truly invalidates the session (FR-01); salted hashing (NFR-03) |
| CSRF protection | Every mutating request must send JSON and the header `X-Qauym-Client: web`; reject otherwise | Simple protection that works with cookie sessions |
| Job queue | Valkey 8 with RQ 2.x; RQ's built-in cron scheduling for nightly runs (M2) | BSD-licensed, chosen over Redis 8 to avoid source-available terms |
| Analytics | python-igraph, leidenalg, networkx (LFR generator), numpy, pandas, scikit-learn (NMI, ARI), psutil, matplotlib | Same stack for the app worker and the benchmark harness |
| Frontend | React with Vite and TypeScript, React Router, TanStack Query, Tailwind CSS; Cytoscape.js for the graph view (M2) | Plain single-page app; no server-side rendering needed |
| Testing | pytest, pytest-cov, FastAPI TestClient against a real PostgreSQL, Playwright (end-to-end and screenshots), Locust (M2) | Requirement-derived tests and automatic report evidence |
| Code quality | ruff (lint and format), mypy (non-strict), eslint, prettier | Run in CI on every pull request |
| Runtime | Docker Compose services: `db`, `valkey`, `api`, `worker`, `web`; Node.js 22 LTS or newer for the frontend build | One command to start everything |
| Configuration | Environment variables via pydantic-settings; `.env.example` committed, `.env` gitignored | No secrets in git |
| Licence | GPL-3.0-or-later, pending the advisor's confirmation (leidenalg is GPL-3.0-or-later) | Only add dependencies with GPL-compatible licences |

**Repository layout**

```text
qauym/
├── AGENTS.md                 # rules for coding agents (Section 12.1)
├── README.md                 # setup in 5 commands
├── Makefile
├── docker-compose.yml
├── .env.example
├── .github/workflows/ci.yml
├── docs/
│   ├── SPEC.md               # this document
│   ├── DECISIONS.md
│   ├── DEPENDENCIES.md       # every dependency and its licence
│   └── DEMO.md               # demo script (M1)
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   ├── app/
│   │   ├── main.py  config.py  db.py  security.py
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── api/              # routers: auth, users, posts, social, communities,
│   │   │                     # suggestions, graph, moderation, admin
│   │   └── services/         # visibility.py, events.py, idempotency.py, ...
│   ├── analytics/            # graph_build.py, detectors.py, metrics.py,
│   │                         # validate.py, publish.py, jobs.py, suggest.py
│   ├── bench/                # cli.py, datasets.py, report.py,
│   │                         # datasets.yaml, configs/*.yaml
│   ├── scripts/seed_demo.py
│   └── tests/
├── frontend/
│   ├── src/                  # pages/, components/, api/, hooks/
│   └── e2e/                  # Playwright tests, evidence.spec.ts
├── data/                     # gitignored downloads; provenance in bench/datasets.yaml
└── evidence/                 # generated by `make evidence`
```

**Makefile targets**

| Target | What it does |
| --- | --- |
| `make up` / `make down` | Start or stop all Docker Compose services |
| `make migrate` | Apply Alembic migrations |
| `make seed` | Load synthetic demo users and activity (M1) |
| `make lint` | ruff, mypy, eslint, prettier check |
| `make test` | Backend tests with coverage, then frontend unit tests |
| `make e2e` | Playwright end-to-end tests against the running stack |
| `make data` | Download benchmark datasets and verify checksums |
| `make bench` | Run the benchmark configuration for the current milestone |
| `make analytics-run` | Trigger one analytics run (build, detect, validate, publish) |
| `make evidence` | Produce screenshots, benchmark table and test summary in `evidence/` |

## 4. Data model

All primary keys are UUIDs unless stated, all timestamps are `timestamptz` in UTC, and deletes of user content are soft deletes (`deleted_at`). One Alembic migration per task.

| Table | Key columns | Constraints and notes | Milestone |
| --- | --- | --- | --- |
| `users` | id, email, username, password\_hash, display\_name, bio, role, is\_synthetic, inference\_opt\_out, created\_at, deleted\_at | email unique and lower-cased; username unique, 3–30 chars `[a-z0-9_]`; bio ≤ 280 chars; role in {user, moderator, admin}; `is_synthetic` marks demo accounts (DR-07); `inference_opt_out` default false (used from M2) | M0 |
| `user_interests` | user\_id, tag | PK (user\_id, tag); tag lower-case, ≤ 30 chars, at most 10 per user | M0 |
| `sessions` | id, user\_id, token\_hash, created\_at, expires\_at, revoked\_at | token\_hash unique; logout sets revoked\_at | M0 |
| `posts` | id, author\_id, body, created\_at, deleted\_at, hidden\_at, hidden\_by | body 1–1000 chars, text only | M0 |
| `comments` | id, post\_id, author\_id, body, created\_at, deleted\_at, hidden\_at, hidden\_by | body 1–500 chars | M0 |
| `follows` | follower\_id, followee\_id, created\_at | PK (follower\_id, followee\_id); CHECK follower ≠ followee | M0 |
| `likes` | user\_id, post\_id, created\_at | PK (user\_id, post\_id) | M0 |
| `interaction_events` | id, event\_type, actor\_id, target\_user\_id, post\_id, comment\_id, occurred\_at, payload | Append-only log; event\_type in {post\_created, post\_deleted, followed, unfollowed, liked, unliked, commented, comment\_deleted, blocked, unblocked}; written in the same transaction as the change it records (FR-04) | M0 |
| `outbox` | id, event\_id, status, attempts, available\_at, dispatched\_at, last\_error | event\_id unique; status in {pending, dispatched, failed}; written with the event; dispatched from M2 | M0 |
| `idempotency_keys` | user\_id, key, method, path, request\_hash, response\_status, response\_body, created\_at | PK (user\_id, key); same key and same body returns the stored response; same key with a different body returns 409 | M0 |
| `graph_snapshots` | id, cutoff\_at, config, config\_hash, node\_count, edge\_count, included\_counts, excluded\_counts, created\_at | config and counts as JSONB; never updated after creation | M1 |
| `analytics_runs` | id, snapshot\_id, algorithm, params, seed, status, trigger, requested\_by, job\_key, started\_at, finished\_at, duration\_ms, peak\_mem\_mb, metrics, code\_revision, error\_message | algorithm in {leiden, louvain}; status in {queued, running, succeeded, failed, published, superseded}; trigger in {manual, schedule, outbox}; job\_key unique (deduplication) | M1 |
| `communities` | id, run\_id, label, size, summary | Unique (run\_id, label); summary JSONB holds top shared interests (only tags declared by at least 3 members) | M1 |
| `memberships` | run\_id, user\_id, community\_id, strength | PK (run\_id, user\_id); strength = share of the user's edge weight inside the community, 0–1 | M1 |
| `active_results` | slot, run\_id, activated\_at | slot = 'primary' points at the published Leiden run; changed only inside the publish transaction | M1 |
| `blocks` | blocker\_id, blocked\_id, created\_at | PK (blocker\_id, blocked\_id); CHECK blocker ≠ blocked | M2 |
| `reports` | id, reporter\_id, target\_type, target\_id, reason, details, status, resolved\_by, resolved\_at, resolution\_note, created\_at | target\_type in {post, comment, user}; status in {open, actioned, dismissed}; one open report per reporter and target | M2 |

**Decision: build the graph from current state, keep events as the log.** The snapshot builder reads `follows`, `likes` and `comments` as they exist at the cutoff, filtered by eligibility. The `interaction_events` table stays the append-only record that guarantees idempotency, feeds the outbox and supports auditing. This keeps unlike, unfollow and delete semantics correct without replaying compensating events. Record this in `docs/DECISIONS.md` as D-001.

## 5. API contract

The API is REST over JSON under `/api/v1`, authenticated by the session cookie. It is client-neutral so a later iOS client can use it unchanged.

**Conventions**

- **Errors** use RFC 9457 problem details: `{type, title, status, detail}`. Authentication failures never reveal whether an email exists.
- **Objects the viewer may not see** return 404, not 403, so the API does not confirm they exist.
- **Pagination** is cursor-based on (created\_at, id), newest first, `limit` at most 50.
- **Idempotency.** Every POST that creates content or a relationship requires an `Idempotency-Key` header (UUID). Repeating a key returns the stored response without a second row or event (FR-03, FR-04).
- **Analytics responses** always include `run_id`, `snapshot_cutoff_at` and `inferred: true`.

| Method and path | Purpose | Access | Milestone | Req. |
| --- | --- | --- | --- | --- |
| `GET /health` | Liveness and database check | Public | M0 | – |
| `POST /auth/register` | Create account; returns 201 and sets the session cookie | Public | M0 | FR-01 |
| `POST /auth/login` | Sign in; generic error on bad credentials; rate-limited | Public | M0 | FR-01 |
| `POST /auth/logout` | Revoke the current session | User | M0 | FR-01 |
| `GET /me`, `PATCH /me` | Own profile with private fields; edit display name, bio, interests | User | M0 | FR-02 |
| `GET /users?query=` | Search users by username or display name (People page) | User | M0 | – |
| `GET /users/{username}` | Public profile: permitted fields only, follower and following counts | User | M0 | FR-02 |
| `POST /posts`, `DELETE /posts/{id}` | Create a post; soft-delete own post | User / owner | M0 | FR-03 |
| `GET /feed` | Reverse-chronological own and followed users' posts; no ranking, so it is non-profiled | User | M0 | FR-03 |
| `POST` / `DELETE /users/{id}/follow` | Follow, unfollow | User | M0 | FR-03 |
| `POST` / `DELETE /posts/{id}/like` | Like, unlike | User | M0 | FR-03 |
| `GET` / `POST /posts/{id}/comments`, `DELETE /comments/{id}` | Read, add, soft-delete own comment | User / owner | M0 | FR-03 |
| `GET /communities/me` | Viewer's inferred community from the active run, snapshot time, explicit empty state | User | M1 | FR-08 |
| `GET /communities/{id}` | Size, shared interests, and only members the viewer follows or who follow the viewer (others counted, not named) | User | M1 | FR-08 |
| `POST /admin/analytics/runs` | Queue a run (build, Leiden and Louvain, validate, publish) | Admin | M1 | FR-05–07 |
| `GET /admin/analytics/runs` | List runs with status, duration and metrics | Admin | M1 | FR-06 |
| `GET /suggestions?limit=10` | Ranked people suggestions, each with one reason and its run\_id | User | M2 | FR-09 |
| `GET /graph/neighbourhood` | Bounded ego graph (at most 41 nodes) plus `text_summary` | User | M2 | FR-10 |
| `POST` / `DELETE /users/{id}/block` | Block, unblock; takes effect on the next request | User | M2 | FR-11 |
| `POST /reports` | Report a post, comment or user with a reason | User | M2 | FR-11 |
| `GET /moderation/reports`, `POST /moderation/reports/{id}/resolve` | Review queue; resolve with hide or dismiss and a note | Moderator | M2 | FR-11 |
| `PATCH /me/privacy`, `DELETE /me` | Inference opt-out; account deletion (anonymise and exclude from snapshots) | User | M2 | Law 94-V |

FastAPI generates the OpenAPI schema at `/api/v1/openapi.json`; commit a copy to `docs/openapi.json` at each milestone so the frontend and a future iOS client share one contract.

## 6. Graph build, analytics worker and publication

One analytics run builds a snapshot, runs Leiden and Louvain on it, validates both, and publishes the Leiden result atomically. Louvain is stored for comparison and is never shown to users.

### 6.1 Snapshot builder (FR-05, DR-01, DR-02)

The default configuration lives in `backend/analytics/config/default.yaml` and is copied, with its SHA-256 hash, into every snapshot:

```yaml
version: 1
window_days: 180          # ignore likes/comments older than this
half_life_days: 30        # exponential decay half-life h
alpha_follow: 1.0         # weight per follow direction
beta:
  like: 0.5
  comment: 1.0
normalization: none       # none | sqrt_strength
include_synthetic: true   # demo environment only
```

Edge weight between users u and v at cutoff T:

```text
w(u,v) = ( alpha * s(u,v) + sum over interactions e between u and v of beta[type(e)] * exp(-lambda * (T - t_e)) ) / N(u,v)
lambda = ln(2) / half_life_days
s(u,v) = number of follow directions between u and v (0, 1 or 2)
N(u,v) = 1                                   if normalization = none
N(u,v) = sqrt(S_u * S_v) / mean(S)           if normalization = sqrt_strength,
         where S_x is x's total un-normalised edge weight
```

An interaction is a like by u on v's post or a comment by u on v's post, counted in both directions into one undirected edge. **Eligibility:** both users active, not deleted, not opted out (from M2), no block in either direction (from M2); post and comment not deleted or hidden; interaction created at or before T and within `window_days`; self-interactions excluded. Users with no edges are not graph nodes; they get the empty state (DR-03). The builder records included counts by type and excluded counts by reason (deleted, hidden, blocked, opted\_out, self, outside\_window).

### 6.2 Detectors (FR-06)

Build an undirected weighted `igraph.Graph` with a `user_id` vertex attribute and a `weight` edge attribute, then:

```python
import random, igraph as ig, leidenalg as la

def run_leiden(g: ig.Graph, seed: int) -> list[int]:
    part = la.find_partition(g, la.ModularityVertexPartition,
                             weights="weight", n_iterations=-1, seed=seed)
    return part.membership

def run_louvain(g: ig.Graph, seed: int) -> list[int]:
    random.seed(seed)
    ig.set_random_number_generator(random)   # makes multilevel reproducible
    return g.community_multilevel(weights="weight").membership
```

Each run records: algorithm, parameters, seed (default 42 in the app), duration, peak memory, and metrics: modularity, number of communities, community-size min/median/max, singleton count, mean conductance, coverage (share of edge weight inside communities) and the number of internally disconnected communities.

### 6.3 Validation before publication (FR-07)

A run is published only if every check passes; otherwise its status is `failed` with the reason:

1. Every vertex in the snapshot graph has exactly one membership.
2. The membership count equals the snapshot's node count, and labels are contiguous from 0.
3. No metric is NaN or infinite.
4. The Leiden result has zero internally disconnected communities.
5. Snapshot ID, code revision (`GIT_SHA` environment variable), config hash, seed and duration are all present.

### 6.4 Atomic publication

In one database transaction: insert communities and memberships for the Leiden run, set its status to `published`, point `active_results.primary` at it, and set the previously published run to `superseded`. Any exception rolls the transaction back, marks the run `failed` and leaves the previous result active. A test injects an exception after the membership insert and asserts that the old run is still active and that no partial memberships are visible.

### 6.5 Jobs and scheduling (NFR-05)

- **M1:** `make analytics-run` and `POST /admin/analytics/runs` call `analytics.jobs.run_analytics` synchronously; no queue yet, to save time. A PostgreSQL advisory lock stops two runs from overlapping, so a double click creates one run.
- **M2:** move the job onto RQ (`rq worker analytics` in the `worker` container) with `job_id = "analytics:" + cutoff truncated to the minute`. A dispatcher loop marks pending outbox rows as dispatched every 10 seconds and enqueues at most one debounced run per 15 minutes when graph-relevant events arrived. RQ cron adds a nightly run at 22:00 UTC (03:00 in Kazakhstan). Jobs retry up to 3 times with back-off; a retry reuses the same snapshot, so input is never counted twice.

### 6.6 Suggestions with explanations (M2, FR-09)

1. **Candidates:** members of the viewer's community plus friends of friends through follows.
2. **Filter:** remove the viewer, people already followed, blocked in either direction, deleted and opted-out users.
3. **Score:** 0.5 × same community + 0.3 × common neighbours (scaled 0–1) + 0.2 × Jaccard similarity of interests. Keep the weights in config.
4. **Reason:** take the largest visible component: "You both follow 4 people", "Active in your community", or for cold start "Shares your interests: hiking, chess" with the label "Based on your profile". A reason may count or name only people the viewer can already see.
5. **No membership (new or isolated user):** return interest-based suggestions, labelled; if the user has no interests, return recently active users, labelled "Not personalised". Opted-out users always get the non-personalised list.

### 6.7 Graph neighbourhood (M2, FR-10)

Nodes are the viewer plus up to 40 users connected to the viewer in the active snapshot, ranked by edge weight, after the visibility filter. Edges are drawn only between returned nodes. Each node carries its community label. `text_summary` states the same facts in sentences, for example: "You are in Community 3 (42 members). Your strongest connections are Aru and Dias (Community 3) and Timur (Community 7)."

## 7. Benchmark harness and datasets (FR-12, DR-07)

The harness reuses `analytics/detectors.py` and `analytics/metrics.py`, so the numbers in the report come from the same code the app runs.

**Commands**

- `python -m bench run --config bench/configs/m0.yaml --out evidence/bench/` runs every (dataset, method, seed) combination.
- `python -m bench report evidence/bench/` writes `results.md`, `results.csv`, `hardware.json` and `fig7_bench.png`.

**Measurement rules**

- Run each (dataset, method, seed) in a fresh child process (`multiprocessing` with the `spawn` start method) and read the child's peak resident memory with `resource.getrusage(RUSAGE_SELF).ru_maxrss`. igraph allocates in C, so `tracemalloc` alone would under-report.
- Time only the detection call with `time.perf_counter()`; graph loading is timed separately.
- Use detector seeds 1–5 and report mean ± standard deviation.
- NMI and ARI come from `sklearn.metrics.normalized_mutual_info_score` and `adjusted_rand_score`, and only where ground truth exists.

**M0 configuration (`bench/configs/m0.yaml`)**

| Dataset | How it is produced | Ground truth | Notes |
| --- | --- | --- | --- |
| LFR, mixing μ = 0.1, 0.3, 0.5 | `networkx.LFR_benchmark_graph(n=1000, tau1=3, tau2=1.5, mu=μ, average_degree=15, max_degree=50, min_community=20, max_community=100, seed=42)` | Planted communities (node attribute `community`) | The generator sometimes fails to converge: retry with seed + 1, up to 10 times, and record the seed actually used |
| SNAP email-Eu-core | `email-Eu-core.txt.gz` and `email-Eu-core-department-labels.txt.gz` from snap.stanford.edu/data | 42 departments, one per member | 1,005 nodes and 25,571 directed edges; convert to undirected and drop self-loops before running |

Later configurations: `m1.yaml` adds a resolution sweep for Leiden (RBConfigurationVertexPartition, resolution 0.5–2.0) and LFR μ up to 0.7; `m2.yaml` adds a scale run on LFR with 100,000 nodes for NFR-02 and one larger SNAP network with ground-truth communities (com-Amazon or com-DBLP, top 5,000 communities).

**Outputs**

- `results.md` uses exactly the columns of the report's Table 4.2: Dataset, Nodes, Edges, Method, Modularity, NMI, ARI, Runtime (s), Peak memory (MB).
- `hardware.json` records CPU model, cores, RAM, operating system, and the versions of Python, igraph, leidenalg and networkx, plus the git commit.
- `fig7_bench.png` is a grouped bar chart of NMI by LFR μ for Leiden and Louvain, with email-Eu-core alongside.

**Dataset provenance (DR-07).** `bench/datasets.yaml` lists each dataset's name, source URL, SHA-256, terms of use, citation and preprocessing steps. `make data` downloads into `data/raw/` and verifies checksums; if the network blocks the download, place the files there by hand. Datasets are never committed to git, and benchmark data never mixes with app users.

## 8. Frontend screens and accessibility rules

The web client is a single-page React app served by the `web` container and talking only to `/api/v1`. Every screen must work at 1280 px and 375 px wide.

| Screen | Route | Milestone | Must show | Req. |
| --- | --- | --- | --- | --- |
| Sign in, register | `/login`, `/register` | M0 | Labelled fields, inline validation, errors announced with `aria-live` | FR-01 |
| Feed | `/` | M0 | Post composer with character count; own and followed users' posts, newest first; like and unlike; comment thread; delete own post | FR-03 |
| Profile | `/u/:username` | M0 | Display name, bio, interests, follower counts, follow button, posts | FR-02, FR-03 |
| Edit profile | `/settings/profile` | M0 | Display name, bio, up to 10 interest tags | FR-02 |
| People | `/people` | M0 | Search and follow users (needed to build a graph during demos) | FR-03 |
| My communities | `/communities` | M1 | "Inferred by Qauym on {snapshot time}" label; community card with size, shared interests and people you know in it; a friendly empty state for new or isolated users | FR-08, DR-03, DR-04 |
| Community detail | `/communities/:id` | M1 | Size, shared interests, members the viewer already knows; others only counted | FR-08 |
| Analytics runs (admin) | `/admin/runs` | M1 | Runs table (algorithm, status, duration, modularity, communities, error) and a "Run now" button | FR-05–07 |
| Discover | `/discover` | M2 | Suggestion cards with the reason text, a "Why am I seeing this?" disclosure, follow button, labels for profile-based and non-personalised suggestions | FR-09 |
| Graph view | `/communities/graph` | M2 | Cytoscape.js ego graph (at most 41 nodes) with zoom, pan and select; a keyboard-focusable node list; the text summary beside it | FR-10, NFR-06 |
| Report and block | Dialogs on posts, comments, profiles | M2 | Reason picker and confirmation; blocked users' content disappears at once | FR-11 |
| Moderation queue | `/moderation` | M2 | Open reports with content preview; hide or dismiss with a note | FR-11 |
| Privacy settings | `/settings/privacy` | M2 | Toggle "Use my activity for community inference"; delete account | Law 94-V, Law 18-VIII Art. 12 |

**Accessibility (NFR-06).** Use semantic HTML and real `<button>` and `<label>` elements; keep a visible focus ring; make every action reachable by keyboard; never use colour as the only signal; give every image and icon button an accessible name; announce async errors with `aria-live="polite"`.

**Wording rules (DR-04).** Always say "inferred community". Name communities "Community {n}" followed by up to three shared interests declared by at least 3 members. Never derive names or labels from sensitive traits, and never call a community a group the user joined.

## 9. Privacy, security and moderation rules

These rules are not negotiable. The report's ethics and legal section (6.1–6.3) promises them, so the code must enforce them and tests must prove it.

1. **One visibility module.** `app/services/visibility.py` owns every rule about who can see what. Every endpoint that returns users, posts, comments, communities, suggestions or graph data calls it. A test walks the router list and fails if a data-returning endpoint skips it.
2. **Blocks win immediately (DR-09).** A block in either direction hides the two users' posts, comments and profiles from each other (404), removes them from each other's suggestions, community pages and graph views, and applies on the very next request, whatever analytics version is active.
3. **Hidden and deleted content** is never returned to non-moderators. Deleted users never appear anywhere.
4. **Opt-out (from M2).** Opted-out users are excluded from new snapshots, their old memberships are ignored at read time, their community page explains why it is empty, and they get only non-personalised suggestions.
5. **No leaks through explanations (DR-04).** Reasons, community pages and graph views may show only people and facts the viewer could already see.
6. **Authentication.** Argon2id password hashes; session token rotated at login and revoked at logout; login and register rate-limited to 10 requests per minute per IP (Valkey counter).
7. **Authorisation.** Object-level checks on every mutation: only the owner, or a moderator where the spec allows it. Roles are checked on the server, never trusted from the client.
8. **Secrets and logs (NFR-08).** No secrets in git. Logs never contain passwords, tokens, cookies or post and comment bodies.
9. **Data separation (DR-07).** Demo accounts have `is_synthetic = true`. Benchmark datasets never enter the app database. No scraping of any website.
10. **Account deletion (M2).** Soft-delete the user, blank the profile fields, revoke sessions, and exclude the user from all future snapshots.
11. **Hosting.** The MVP runs locally or on a university server. If real (non-team) users are ever invited, their data must be stored on servers in Kazakhstan, as the report's legal section requires.

## 10. Testing, CI and the report evidence pack

Tests are written from requirement IDs, so the report can say which test verifies which requirement.

**Required tests**

| Requirement | Test file | What it proves | Milestone |
| --- | --- | --- | --- |
| FR-01 | `tests/test_auth.py` | Duplicate account rejected; wrong password gives a generic error; requests after logout get 401 | M0 |
| FR-02 | `tests/test_profile_privacy.py` | Users edit only their own profile; public responses omit email and other private fields | M0 |
| FR-03 | `tests/test_social_uniqueness.py` | Double follow or like creates one row; delete only own content | M0 |
| FR-04 | `tests/test_idempotency.py` | Same Idempotency-Key twice gives one row, one event, one outbox entry and the same response; different body gives 409 | M0 |
| FR-06, FR-12 | `tests/test_detectors.py`, `tests/test_bench_smoke.py` | Same seed gives the same membership; a 200-node LFR run finishes in CI in under 30 s | M0 |
| FR-05 | `tests/test_snapshot_builder.py` | A hand-made fixture gives the expected edge weights and excluded counts | M1 |
| FR-07, NFR-05 | `tests/test_publication_failure.py` | An injected failure leaves the previous run active and no partial memberships | M1 |
| FR-08 | `tests/test_communities_me.py` | Ordinary member, isolated user (empty state), stale snapshot (timestamp shown), no run yet | M1 |
| FR-09 | `tests/test_suggestions_privacy.py` | Self, followed, blocked and opted-out users never suggested; reasons mention only visible people | M2 |
| FR-10 | `tests/test_graph_bounds.py` | At most 41 nodes; blocked users absent; text summary names the same nodes | M2 |
| FR-11, NFR-04 | `tests/test_moderation.py`, `tests/test_stale_snapshot_privacy.py` | Hidden content disappears; a block applied after a snapshot still filters that snapshot's results | M2 |
| NFR-03 | `tests/test_authz.py` | Cross-user writes return 404; non-moderators cannot moderate; unauthenticated requests get 401 | M0–M2 |
| Core flow | `frontend/e2e/core-flow.spec.ts` | Register, post, follow, like, comment in a real browser | M0 |

**Continuous integration** (`.github/workflows/ci.yml`, on every pull request): ruff and mypy; pytest with PostgreSQL 16 and Valkey service containers; a coverage report (report-only until M1, then failing below 75% for `backend/app` and `backend/analytics` from M2); frontend lint, type check and build; Playwright against `docker compose up` from M1.

**Evidence pack.** `make evidence` seeds demo data, runs the tests and benchmark if their outputs are missing, and writes:

| File | Report use | Milestone |
| --- | --- | --- |
| `evidence/screenshots/fig5_login.png` | Figure 5 | M0 |
| `evidence/screenshots/fig6_feed.png` | Figure 6 | M0 |
| `evidence/bench/fig7_bench.png`, `results.md`, `results.csv`, `hardware.json` | Figure 7 and Table 4.2 | M0 |
| `evidence/screenshots/communities.png`, `admin_runs.png` | Demo and Spring report | M1 |
| `evidence/screenshots/discover.png`, `graph.png`, `moderation.png` | Spring report | M2 |
| `evidence/tests.md` | Number of tests, pass rate, coverage, CI link | M0–M2 |
| `evidence/SUMMARY.md` | Generated summary: commit, date, what exists, open issues | M0–M2 |

Screenshots come from `frontend/e2e/evidence.spec.ts`, which logs in as a synthetic demo user and captures each screen at 1280 × 800 (and the feed again at 375 × 812). When M0 is done, send the `evidence/` folder (or `SUMMARY.md`, `results.md`, `tests.md` and the PNGs) back to Claude to fill the report's bold placeholders.

## 11. Task breakdown by milestone and owner

Owners follow the roles in the report; the owner drives the agent session and a second member reviews. Tasks inside a milestone can run in parallel unless a dependency is listed.

### M0: Fall sprint (23–26 November 2026, code freeze Thursday 18:00)

| ID | Task | Owner | Req. | Done when |
| --- | --- | --- | --- | --- |
| T0.1 | Repository scaffold: Docker Compose (`db`, `valkey`, `api`, `web`), Makefile, `.env.example`, README, AGENTS.md, CI skeleton | Yernur | NFR-07 | `make up` serves `/api/v1/health` and the web app; CI green |
| T0.2 | Models and first migration: users, user\_interests, sessions, posts, comments, follows, likes, interaction\_events, outbox, idempotency\_keys | Amankeldi | FR-01–04 | Migration applies on an empty database and rolls back cleanly |
| T0.3 | Auth: register, login, logout, me; Argon2id; sessions; rate limit (needs T0.2) | Amankeldi | FR-01, NFR-03 | `test_auth.py` passes |
| T0.4 | Profiles, posts, feed, follows, likes, comments, people search; idempotency; event and outbox in the same transaction (needs T0.3) | Amankeldi, tests by Nurbek | FR-02–04 | `test_profile_privacy`, `test_social_uniqueness`, `test_idempotency` pass |
| T0.5 | Frontend: login, register, feed, profile, edit profile, people (needs API from T0.4; start against a mock) | Islam | FR-01–03, NFR-06 | `core-flow.spec.ts` passes |
| T0.6 | Benchmark harness: LFR and email-Eu-core loaders, Leiden and Louvain in child processes, metrics, `results.md`, `hardware.json`, `fig7_bench.png` | Nurdaulet | FR-06, FR-12 | `make bench` finishes in under 10 minutes on a laptop and writes the table |
| T0.7 | `bench/datasets.yaml` provenance register and `make data` with checksums | Yernur | DR-07 | Fresh clone plus `make data` gets both SNAP files and verifies them |
| T0.8 | Evidence pack v0: `evidence.spec.ts` creates a demo user and a few posts through the API, captures Figures 5–6; `tests.md`; `SUMMARY.md` | Nurbek | Report 4.2 | `make evidence` writes all M0 files from the evidence table |

### M1: vertical slice (Fall stretch from Wednesday 25 November; otherwise 11–15 January 2027)

| ID | Task | Owner | Req. | Done when |
| --- | --- | --- | --- | --- |
| T1.1 | `make seed`: about 300 synthetic users in about 8 planted interest groups, 60 days of timestamped posts, likes, comments and follows, `is_synthetic = true` | Yernur, Nurdaulet | DR-07 | Seed runs in under a minute; Leiden on the seeded graph reaches NMI ≥ 0.7 against the planted groups |
| T1.2 | Snapshot builder with config, eligibility and counts | Nurdaulet | FR-05, DR-01, DR-02 | `test_snapshot_builder.py` passes |
| T1.3 | Analytics job: build, detect, validate and publish atomically; run synchronously by `make analytics-run` and the admin endpoint; advisory-lock deduplication (RQ comes in M2) | Amankeldi | FR-06, FR-07, NFR-05 | `test_publication_failure.py` passes; a double trigger creates one run |
| T1.4 | `GET /communities/me` and `GET /communities/{id}` through the visibility module | Amankeldi | FR-08 | `test_communities_me.py` passes |
| T1.5 | Frontend: My communities, community detail, admin runs page | Islam | FR-08, DR-04 | Screens show the inferred label, snapshot time and empty state |
| T1.6 | Playwright in CI; coverage report | Yernur | NFR-07 | CI runs all tests on every pull request |
| T1.7 | `docs/DEMO.md` script, `openapi.json` copy, evidence pack v1 | Nurbek | – | A teammate who did not build it runs the demo from a fresh clone |

### M2: MVP complete (18 January – 5 February 2027)

| ID | Task | Owner | Req. | Done when |
| --- | --- | --- | --- | --- |
| T2.1 | Blocks, reports, moderation queue and hiding; visibility module enforced everywhere | Nurbek, Amankeldi | FR-11, NFR-04, DR-09 | `test_moderation.py` and `test_stale_snapshot_privacy.py` pass |
| T2.2 | Suggestions with reasons and cold start | Nurdaulet, Amankeldi | FR-09, DR-03 | `test_suggestions_privacy.py` passes |
| T2.3 | Graph neighbourhood endpoint, Cytoscape view, node list and text summary | Islam | FR-10, NFR-06 | `test_graph_bounds.py` passes; keyboard-only walkthrough works |
| T2.4 | Analytics runs on the RQ worker; outbox dispatcher, debounced runs, nightly RQ cron run, retries | Amankeldi | FR-05, NFR-05 | Killing the worker mid-run leaves the last result active; retry succeeds |
| T2.5 | Privacy settings: inference opt-out and account deletion | Nurbek | Law 94-V, Law 18-VIII | Opted-out user absent from the next snapshot and from all results |
| T2.6 | Test hardening: authorisation tests, coverage at least 75% | Yernur | NFR-03, NFR-07 | CI enforces the coverage threshold |
| T2.7 | Locust load test (100 users, p95 and error rate), LFR 100,000-node scale run, backup and restore rehearsal | Yernur, Nurdaulet | NFR-01, NFR-02, NFR-05 | Results written to `evidence/perf/` |
| T2.8 | Accessibility pass at 375 px and keyboard-only | Islam, Nurbek | NFR-06 | Checklist in `docs/ACCESSIBILITY.md` complete |
| T2.9 | Written iOS go/no-go memo against the kickoff criteria | Nurbek with the iOS-experienced member | UR-09 | Memo in `docs/IOS_DECISION.md` |
| T2.10 | Evidence pack v2 and updated `openapi.json` | Nurbek | – | All evidence files regenerated from the M2 commit |

## 12. Copy-paste prompts for the coding agent

Replace the parts in angle brackets before sending. Keep prompts short and let the agent read `docs/SPEC.md` for detail.

### 12.1 Repository rules (save as AGENTS.md and CLAUDE.md)

```markdown
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
```

### 12.2 Session start (every session)

```text
Read AGENTS.md and docs/SPEC.md. Current milestone: <M0 | M1 | M2>. Today is <date>.
1. In at most 10 lines, say what this milestone must deliver.
2. Inspect the repository and list the milestone's tasks from SPEC Section 11 as done, partly done or missing, with evidence (files, tests, make targets).
3. Propose the next task and a step-by-step plan for it, including the tests you will write first.
Wait for my "go" before changing any files.
```

### 12.3 Milestone M0 (Fall sprint, starting from an empty repository)

```text
Milestone M0: Fall sprint. Code freeze Thursday 26 November 2026, 18:00; the report and presentation are due Friday 27 November. The repository is empty. Follow the five-day plan in SPEC Section 2.

Goal: `make up` starts the stack; in the browser a user can register, edit their profile, post, follow, like and comment; each such action writes an interaction_events row and an outbox row in the same transaction; `make bench` compares Leiden and Louvain on LFR (mu = 0.1, 0.3, 0.5) and SNAP email-Eu-core; `make evidence` writes the M0 files listed in SPEC Section 10.

Order: T0.1 -> T0.2 -> T0.3 -> T0.4, with T0.6 and T0.7 in a separate session, then T0.5, then T0.8.
Constraints: text-only posts; no email sending or password reset; reverse-chronological feed with no ranking; Idempotency-Key required on POSTs that create content or relationships; benchmark runs each (dataset, method, seed) in a fresh process with seeds 1-5 and writes results.md with the exact columns of SPEC Section 7.
Start with T0.1: show the plan and the file tree you will create, then wait for "go".
```

### 12.4 Milestone M1 (vertical slice: Fall stretch goal or first week of January)

```text
Milestone M1: vertical slice. Stretch goal before the code freeze on Thursday 26 November 2026, 18:00; otherwise due Friday 15 January 2027. M0 is merged.

Goal: a seeded demo where an admin presses "Run now" (or runs make analytics-run), the job builds a snapshot from current follows, likes and comments (SPEC 6.1, decision D-001), runs Leiden and Louvain, validates (SPEC 6.3) and publishes Leiden atomically (SPEC 6.4); then a user opens My communities and sees their inferred community with the snapshot time, while an isolated user sees the empty state.

Order: T1.1 and T1.2 in parallel, then T1.3, T1.4, T1.5, T1.6, T1.7.
Must-have tests: test_snapshot_builder.py, test_publication_failure.py, test_communities_me.py, and the seeded NMI check (>= 0.7 against planted groups).
Start by restating SPEC 6.1-6.5 in your own words and listing any ambiguity before writing code.
```

### 12.5 Milestone M2 (after the winter break)

```text
Milestone M2: MVP complete. Deadline Friday 5 February 2027. Work resumes 11 January; finish M1 first if the Fall sprint did not reach it. Move analytics runs onto the RQ worker as part of T2.4.

Goal: every Fall-tagged requirement is met: suggestions with privacy-safe reasons and cold start (SPEC 6.6), bounded graph view with text summary (SPEC 6.7), blocking, reporting and moderation, the visibility module enforced on every data endpoint (SPEC 9), outbox-driven and nightly scheduled runs, inference opt-out and account deletion, coverage >= 75%, load test and scale benchmark.

Begin with T2.1, because every later task depends on the visibility module. For each task, write the privacy tests from SPEC Section 10 before the feature code.
```

### 12.6 Pull-request review (run on every PR, ideally in a fresh session)

```text
Review branch <branch> for task <ID> against docs/SPEC.md and AGENTS.md. Do not rewrite code. Check and report by severity, with file and line:
- Are the task's "Done when" criteria met, and are the required tests present and meaningful?
- Does any data-returning endpoint bypass app/services/visibility.py, or can an explanation, community page or graph view reveal something the viewer could not see?
- Is authorisation checked on every mutation? Are secrets or post bodies logged?
- Do migrations apply and roll back? Would `make up` still work on a fresh clone?
- Any new dependency, and is its licence GPL-compatible?
```
