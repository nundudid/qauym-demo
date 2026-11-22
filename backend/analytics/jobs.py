"""One analytics run: build a snapshot, run Leiden and Louvain, validate, publish Leiden.

M1 runs this synchronously from `make analytics-run` and the admin endpoint
(SPEC Section 6.5). A PostgreSQL advisory lock stops two runs from overlapping.
"""

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from analytics.detectors import DETECTORS
from analytics.graph_build import SnapshotGraph, build_snapshot
from analytics.metrics import partition_metrics, peak_rss_mb
from analytics.publish import publish_run
from analytics.validate import validate_run
from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import AnalyticsRun

log = logging.getLogger(__name__)

ADVISORY_LOCK_KEY = 0x51415559  # "QAUY"
DEFAULT_SEED = 42
ALGORITHM_ORDER = ("leiden", "louvain")
LIVE_STATUSES = ("queued", "running", "succeeded", "published")


@dataclass
class RunOutcome:
    started: bool  # False when another run held the lock or this minute already has a run
    reason: str
    runs: list[AnalyticsRun] = field(default_factory=list)


def _job_key(db: Session, cutoff: datetime, algorithm: str) -> tuple[str, AnalyticsRun | None]:
    """Key per cutoff minute and algorithm, plus the live run that already holds it, if any."""
    base = f"analytics:{cutoff.strftime('%Y-%m-%dT%H:%M')}:{algorithm}"
    existing = db.scalars(select(AnalyticsRun).where(AnalyticsRun.job_key.like(f"{base}%"))).all()
    live = next((r for r in existing if r.status in LIVE_STATUSES), None)
    # Failed runs keep their key, so a retry in the same minute gets a suffixed one.
    key = base if not existing else f"{base}:retry{len(existing)}"
    return key, live


def _detect(run: AnalyticsRun, built: SnapshotGraph, seed: int) -> tuple[list[int], list[str]]:
    started = time.perf_counter()
    membership = DETECTORS[run.algorithm](built.graph, seed) if built.graph.vcount() else []
    run.duration_ms = (time.perf_counter() - started) * 1000
    run.peak_mem_mb = peak_rss_mb()
    run.metrics = partition_metrics(built.graph, membership)
    errors = validate_run(run, built.snapshot, built.graph.vcount(), membership, run.metrics)
    return membership, errors


def _fail(db: Session, run_id: uuid.UUID, message: str) -> None:
    run = db.get(AnalyticsRun, run_id)
    assert run is not None
    run.status = "failed"
    run.error_message = message[:2000]
    run.finished_at = datetime.now(UTC)
    db.commit()


def run_analytics(
    db: Session,
    *,
    trigger: str = "manual",
    requested_by: uuid.UUID | None = None,
    cutoff: datetime | None = None,
    seed: int = DEFAULT_SEED,
    config: dict[str, Any] | None = None,
    publish_hook: Callable[[], None] | None = None,
) -> RunOutcome:
    with engine.connect() as lock_conn:
        locked = lock_conn.execute(
            text("SELECT pg_try_advisory_lock(:k)"), {"k": ADVISORY_LOCK_KEY}
        ).scalar()
        if not locked:
            running = db.scalars(select(AnalyticsRun).where(AnalyticsRun.status == "running")).all()
            return RunOutcome(False, "An analytics run is already in progress.", list(running))
        try:
            return _run_locked(db, trigger, requested_by, cutoff, seed, config, publish_hook)
        finally:
            lock_conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": ADVISORY_LOCK_KEY})
            lock_conn.commit()


def _run_locked(
    db: Session,
    trigger: str,
    requested_by: uuid.UUID | None,
    cutoff: datetime | None,
    seed: int,
    config: dict[str, Any] | None,
    publish_hook: Callable[[], None] | None,
) -> RunOutcome:
    cutoff = cutoff or datetime.now(UTC)
    keys = {algorithm: _job_key(db, cutoff, algorithm) for algorithm in ALGORITHM_ORDER}
    duplicates = [live for _, live in keys.values() if live is not None]
    if duplicates:
        return RunOutcome(False, "A run for this minute already exists.", duplicates)

    built = build_snapshot(db, cutoff, config)
    runs = [
        AnalyticsRun(
            id=uuid.uuid4(),
            snapshot_id=built.snapshot.id,
            algorithm=algorithm,
            params={"objective": "modularity", "weights": "weight"},
            seed=seed,
            status="running",
            trigger=trigger,
            requested_by=requested_by,
            job_key=keys[algorithm][0],
            code_revision=get_settings().git_sha,
        )
        for algorithm in ALGORITHM_ORDER
    ]
    db.add_all(runs)
    db.commit()  # the snapshot and both runs are now visible on the admin page

    for run in runs:
        run_id = run.id
        try:
            membership, errors = _detect(run, built, seed)
            if errors:
                db.commit()  # keep the duration and metrics of the failed run
                _fail(db, run_id, "Validation failed: " + "; ".join(errors))
                continue
            run.finished_at = datetime.now(UTC)
            run.status = "succeeded"
            db.commit()
            # Only Leiden is ever published; Louvain is stored for comparison.
            if run.algorithm == "leiden":
                publish_run(db, run, built.graph, built.user_ids, membership, publish_hook)
        except Exception as exc:  # the previous result stays active
            db.rollback()
            log.exception("analytics run %s failed", run_id)
            _fail(db, run_id, f"{type(exc).__name__}: {exc}")
    for run in runs:
        db.refresh(run)
    return RunOutcome(True, "Run finished.", runs)


def main() -> int:
    with SessionLocal() as db:
        outcome = run_analytics(db, trigger="manual")
        print(outcome.reason)
        for run in outcome.runs:
            metrics = run.metrics or {}
            line = (
                f"  {run.algorithm:8s} {run.status:10s} "
                f"communities={metrics.get('n_communities', '-')} "
                f"modularity={metrics.get('modularity', float('nan')):.3f} "
                f"duration={run.duration_ms or 0:.0f} ms"
            )
            print(line + (f"  error: {run.error_message}" if run.error_message else ""))
        return 0 if all(r.status != "failed" for r in outcome.runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
