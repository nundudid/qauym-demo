"""FR-06, FR-07, NFR-05: validation, atomic publication, and one run per trigger."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from analytics.jobs import ADVISORY_LOCK_KEY, run_analytics
from analytics.validate import validate_run
from app.db import engine
from app.models import ActiveResult, AnalyticsRun, Community, GraphSnapshot, Membership
from tests.factories import follow, make_user, two_groups

# Cutoffs lie just ahead of the fixtures, which are created while each test runs.
NOW = datetime.now(UTC) + timedelta(hours=1)


def count(db: Session, model: type, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def active_run_id(db: Session):
    return db.scalar(select(ActiveResult.run_id).where(ActiveResult.slot == "primary"))


def by_algorithm(runs: list[AnalyticsRun]) -> dict[str, AnalyticsRun]:
    return {run.algorithm: run for run in runs}


def test_fr06_run_publishes_leiden_and_stores_louvain(db: Session) -> None:
    left, right = two_groups(db)
    outcome = run_analytics(db, cutoff=NOW)
    runs = by_algorithm(outcome.runs)

    assert outcome.started
    assert runs["leiden"].status == "published"
    assert runs["louvain"].status == "succeeded"  # stored for comparison, never shown
    assert active_run_id(db) == runs["leiden"].id
    for run in runs.values():
        assert run.seed == 42 and run.duration_ms is not None and run.peak_mem_mb > 0
        assert run.code_revision and run.finished_at is not None
        assert run.metrics["n_communities"] == 2
        assert {
            "modularity",
            "size_min",
            "size_median",
            "size_max",
            "singletons",
            "mean_conductance",
            "coverage",
            "disconnected_communities",
        } <= set(run.metrics)

    # Communities and memberships exist for the Leiden run only.
    assert count(db, Community, Community.run_id == runs["leiden"].id) == 2
    assert count(db, Membership, Membership.run_id == runs["leiden"].id) == 8
    assert count(db, Membership, Membership.run_id == runs["louvain"].id) == 0

    left_ids = {
        m.community_id for m in db.scalars(select(Membership)) if m.user_id in {u.id for u in left}
    }
    assert len(left_ids) == 1
    # left[0] has 6 units of weight inside its group and 1 crossing to the other group.
    strength = db.get(Membership, (runs["leiden"].id, left[0].id)).strength
    assert abs(strength - 6 / 7) < 1e-9
    assert db.get(Membership, (runs["leiden"].id, left[1].id)).strength == 1.0


def test_fr06_shared_interests_need_at_least_three_members(db: Session) -> None:
    left, _ = two_groups(db)
    make_user(db, "extra", interests=("rare",))
    db.commit()
    run = by_algorithm(run_analytics(db, cutoff=NOW).runs)["leiden"]
    membership = db.get(Membership, (run.id, left[0].id))
    summary = db.get(Community, membership.community_id).summary
    assert summary == {
        "top_interests": [{"tag": "chess", "members": 4}, {"tag": "hiking", "members": 4}]
    }


def test_fr07_injected_failure_keeps_the_previous_result_active(db: Session) -> None:
    left, right = two_groups(db)
    first = by_algorithm(run_analytics(db, cutoff=NOW).runs)["leiden"]
    memberships_before = count(db, Membership)

    # New activity, then a publish that fails after the memberships were inserted.
    newcomer = make_user(db, "newcomer")
    follow(db, newcomer, left[0])
    db.commit()

    def explode() -> None:
        raise RuntimeError("injected failure after the membership insert")

    outcome = run_analytics(db, cutoff=NOW + timedelta(minutes=5), publish_hook=explode)
    failed = by_algorithm(outcome.runs)["leiden"]

    assert failed.status == "failed"
    assert "injected failure" in failed.error_message
    # The previous run is still the active, published one.
    db.expire_all()
    assert active_run_id(db) == first.id
    assert db.get(AnalyticsRun, first.id).status == "published"
    # No partial result is visible anywhere.
    assert count(db, Membership, Membership.run_id == failed.id) == 0
    assert count(db, Community, Community.run_id == failed.id) == 0
    assert count(db, Membership) == memberships_before
    assert db.get(Membership, (first.id, newcomer.id)) is None

    # The next good run publishes and supersedes the old one.
    third = by_algorithm(run_analytics(db, cutoff=NOW + timedelta(minutes=10)).runs)["leiden"]
    db.expire_all()
    assert third.status == "published" and active_run_id(db) == third.id
    assert db.get(AnalyticsRun, first.id).status == "superseded"
    assert db.get(Membership, (third.id, newcomer.id)) is not None


def test_fr07_validation_rejects_bad_results(db: Session) -> None:
    two_groups(db)
    run = by_algorithm(run_analytics(db, cutoff=NOW).runs)["leiden"]
    snapshot = db.get(GraphSnapshot, run.snapshot_id)
    good = [0, 0, 0, 0, 1, 1, 1, 1]
    metrics = dict(run.metrics)

    assert validate_run(run, snapshot, 8, good, metrics) == []
    assert validate_run(run, snapshot, 8, good[:-1], metrics)  # a vertex without a membership
    assert validate_run(run, snapshot, 8, [0, 0, 0, 0, 2, 2, 2, 2], metrics)  # labels skip 1
    assert validate_run(run, snapshot, 8, good, {**metrics, "modularity": float("nan")})
    assert validate_run(run, snapshot, 8, good, {**metrics, "disconnected_communities": 1})
    run.code_revision = None
    assert validate_run(run, snapshot, 8, good, metrics) == ["missing code revision"]
    db.rollback()


def test_fr07_invalid_run_is_marked_failed_and_not_published(db: Session, monkeypatch) -> None:
    two_groups(db)
    monkeypatch.setattr("analytics.jobs.get_settings", lambda: type("S", (), {"git_sha": ""})())
    runs = by_algorithm(run_analytics(db, cutoff=NOW).runs)
    assert runs["leiden"].status == "failed"
    assert "missing code revision" in runs["leiden"].error_message
    assert active_run_id(db) is None
    assert count(db, Membership) == 0


def test_nfr05_double_trigger_creates_one_run(db: Session) -> None:
    two_groups(db)
    # A run is "in progress": another connection holds the advisory lock.
    with engine.connect() as other:
        other.execute(text("SELECT pg_advisory_lock(:k)"), {"k": ADVISORY_LOCK_KEY})
        blocked = run_analytics(db, cutoff=NOW)
        other.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": ADVISORY_LOCK_KEY})
        other.commit()
    assert not blocked.started
    assert count(db, AnalyticsRun) == 0

    first = run_analytics(db, cutoff=NOW)
    again = run_analytics(db, cutoff=NOW + timedelta(seconds=1))  # the same minute
    assert first.started and not again.started
    assert {r.id for r in again.runs} == {r.id for r in first.runs}
    assert count(db, AnalyticsRun) == 2  # one Leiden and one Louvain row
    assert count(db, GraphSnapshot) == 1


def test_fr06_empty_graph_publishes_an_empty_result(db: Session) -> None:
    make_user(db, "alone")
    db.commit()
    run = by_algorithm(run_analytics(db, cutoff=NOW).runs)["leiden"]
    assert run.status == "published"
    assert run.metrics["n_communities"] == 0
    assert count(db, Membership) == 0
