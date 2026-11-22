# Decisions

Decisions the specification did not cover, or that change a fixed choice in SPEC Section 3.

## D-001: Build the graph from current state, keep events as the log

From SPEC Section 4. The snapshot builder reads `follows`, `likes` and `comments` as they exist at the cutoff, filtered by eligibility. `interaction_events` stays the append-only record that guarantees idempotency, feeds the outbox and supports auditing. This keeps unlike, unfollow and delete semantics correct without replaying compensating events.

## D-002: Every Makefile target runs inside Docker Compose (T0.1)

`make lint` and `make test` run in the `api` and `web` containers rather than on the host, so the only host requirements are Docker and make, and every machine uses Python 3.12 and Node 22 whatever is installed locally. Recipes are single commands so they work under both `sh` and Windows `cmd.exe`.

## D-003: Tests use a separate `qauym_test` database (T0.1)

SPEC Section 3 requires tests against a real PostgreSQL. They run against `qauym_test` in the same `db` container, created by `docker/initdb/01-test-db.sh`, so a test run never touches app or demo data.

## D-004: The `web` container runs the Vite dev server (T0.1)

Vite serves the app on port 5173 and proxies `/api` to the `api` container, so the browser sees one origin and the session cookie needs no CORS setup. A production build served by a static server is deferred until hosting is decided (SPEC Section 9, rule 11).

## D-005: `uv` installs backend dependencies (T0.1)

`uv pip install -r pyproject.toml` keeps `pyproject.toml` the single dependency list for Docker and CI. uv is a build tool only (MIT / Apache-2.0).

## D-006: The rate limiter fails open (T0.3)

Login and register are limited to 10 requests per minute per IP with a Valkey counter (SPEC Section 9, rule 6). If Valkey is unreachable the request is allowed and a warning is logged, so a cache outage does not lock everyone out. The limit is configurable with `AUTH_RATE_LIMIT_PER_MINUTE`.

## D-007: `GET /users/{username}/posts` (T0.4)

The profile screen must show the user's posts (SPEC Section 8), but Section 5 lists no endpoint for them. This endpoint returns them with the same shape and pagination as `GET /feed`, through the visibility module.

## D-008: Duplicate registration returns one generic 409 (T0.3)

FR-01 requires duplicate accounts to be rejected. The response is the same whether the email or the username is taken, so it reveals as little as a registration form can.

## D-009: Follow and like return 201 when created and 200 when already present (T0.4)

A repeated follow or like with a new Idempotency-Key creates no second row or event and returns 200 with the same body. Unfollow and unlike are idempotent and return the resulting state.

## D-010: Comments are returned newest first (T0.4)

`GET /posts/{id}/comments` follows the pagination convention in SPEC Section 5 (newest first). The web client reverses each thread so it reads oldest first.

## D-011: Playwright runs in its official container (T0.5)

`make e2e` starts the `e2e` Compose service (`mcr.microsoft.com/playwright`, same version as `@playwright/test`), which reaches the app at `http://web:5173`. No browser has to be installed on the host. The `web` entrypoint reinstalls `node_modules` when `package-lock.json` changes, because that folder lives in a named volume that outlives image rebuilds.

## D-012: Benchmark measurement details (T0.6)

- Each dataset is prepared once into `data/cache/*.npz`; every (dataset, method, seed) child process loads that file, so LFR generation is never part of a timed run.
- Peak memory is read from `VmHWM` in `/proc/self/status`, not `resource.getrusage` as SPEC Section 7 says. Linux carries `ru_maxrss` across exec, so a spawned child starts at the parent's size: with getrusage every run reported the parent's 165 MB. `VmHWM` is the child's own peak; getrusage remains the fallback where `/proc` is missing.
- The child reads its peak resident memory right after detection. NMI and ARI are computed with scikit-learn in the parent process, so scikit-learn's own memory is not counted against the detector.
- The benchmark runs in the `api` container, so `hardware.json` describes the container's view of the machine (it records `in_container: true`).

## D-013: SNAP checksums were pinned on first download (T0.7)

The SHA-256 values in `bench/datasets.yaml` were computed from the files downloaded from snap.stanford.edu on 22 November 2026; SNAP does not publish checksums. Both files matched the documented sizes (25,571 directed edges, 1,005 labelled nodes).

## D-014: A community page is visible only to its own members (T1.4)

SPEC Section 5 does not say who may open `GET /communities/{id}`. Membership is inferred data about a person, so the endpoint returns 404 unless the viewer is a member of that community in the active run. The size shown counts only members the viewer may see, so deleted users are not counted.

## D-015: One migration for the M1 analytics tables (T1.2, T1.3)

`graph_snapshots`, `analytics_runs`, `communities`, `memberships` and `active_results` are created together in migration `0002`, not one migration per task, because the tasks were built in one session and the tables reference each other.

## D-016: Run deduplication in M1 (T1.3)

- A PostgreSQL advisory lock is held for the whole job. A trigger that arrives while it is held starts nothing and returns the runs in progress.
- `job_key` is `analytics:<cutoff minute>:<algorithm>`. A second trigger in the same minute returns the existing runs. If the earlier run in that minute failed, a retry is allowed and gets the key suffix `:retryN`.
- One trigger writes two `analytics_runs` rows that share a snapshot: Leiden (published) and Louvain (succeeded, never published).
- `POST /admin/analytics/runs` returns 201 when a run started and 200 when it did not. It needs no Idempotency-Key because the lock and `job_key` already deduplicate it.

## D-017: Admin endpoints return 404 to non-admins (T1.3)

Following "404, not 403" in SPEC Section 5, a signed-in user without the admin role gets 404 from `/admin/*`, so the API does not confirm the routes exist. The role is read from the database for the session's user.

## D-018: Demo seed details (T1.1)

- `make seed` inserts directly into the database and writes matching `interaction_events` and `outbox` rows, so seeded activity has the same log as activity made through the API.
- All synthetic accounts share one password, `demo-password` (override with `DEMO_PASSWORD`), and use the reserved domain `demo.qauym.test`. They exist only for local demos.
- Running the seed again deletes every synthetic account and its activity first; accounts registered through the app are kept.

## D-019: Evidence pack (T0.8, T1.7)

`make evidence` seeds the demo data and runs the analytics, then runs every test suite even if one fails, so `evidence/tests.md` and `evidence/SUMMARY.md` report failures instead of not being written. Raw test output goes to `evidence/raw/` (gitignored). A suite with no output is reported as "not run". The screenshots use the seeded demo accounts rather than accounts created through the API, so Figure 6 shows a realistic feed.
