# Test summary

Commit `6cfd543`, generated 2026-11-22 16:24 UTC by `make evidence`.

| Suite | Tests | Passed | Failed | Pass rate |
| --- | --- | --- | --- | --- |
| Backend (pytest, real PostgreSQL) | 78 | 78 | 0 | 100% |
| Frontend unit (vitest) | 7 | 7 | 0 | 100% |
| End to end (Playwright, Chromium) | 5 | 5 | 0 | 100% |

## Backend coverage

| Package | Line coverage |
| --- | --- |
| `backend/analytics` | 95.4% |
| `backend/app` | 98.0% |
| **Total** | **97.4%** |

## Requirement to test file

| Requirement | Test file | Tests | Passed |
| --- | --- | --- | --- |
| FR-01 | `tests/test_auth.py` | 11 | 11 |
| FR-02 | `tests/test_profile_privacy.py` | 7 | 7 |
| FR-03 | `tests/test_social_uniqueness.py` | 12 | 12 |
| FR-04 | `tests/test_idempotency.py` | 7 | 7 |
| FR-05 | `tests/test_snapshot_builder.py` | 7 | 7 |
| FR-06, FR-12 | `tests/test_detectors.py` | 9 | 9 |
| FR-12 | `tests/test_bench_smoke.py` | 1 | 1 |
| FR-07, NFR-05 | `tests/test_publication_failure.py` | 7 | 7 |
| FR-08 | `tests/test_communities_me.py` | 7 | 7 |
| DR-07 (seed) | `tests/test_seed_demo.py` | 1 | 1 |
| Core flow | `frontend/e2e/core-flow.spec.ts` | see end-to-end row | |

CI: `.github/workflows/ci.yml` runs the same suites on every pull request. Add the link to the latest CI run here once the branch is pushed.
