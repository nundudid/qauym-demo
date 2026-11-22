"""Atomic publication of a validated Leiden run (SPEC Section 6.4)."""

import uuid
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import igraph as ig
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import ActiveResult, AnalyticsRun, Community, Membership, UserInterest

PRIMARY_SLOT = "primary"
MIN_MEMBERS_PER_INTEREST = 3  # a tag is shown only if at least 3 members declared it (DR-04)
MAX_INTERESTS = 3


def membership_strengths(graph: ig.Graph, membership: list[int]) -> list[float]:
    """For each vertex, the share of its edge weight that stays inside its community."""
    inside = [0.0] * graph.vcount()
    total = [0.0] * graph.vcount()
    for (u, v), w in zip(graph.get_edgelist(), graph.es["weight"], strict=True):
        total[u] += w
        total[v] += w
        if membership[u] == membership[v]:
            inside[u] += w
            inside[v] += w
    return [min(1.0, i / t) if t > 0 else 0.0 for i, t in zip(inside, total, strict=True)]


def community_summary(db: Session, member_ids: list[uuid.UUID]) -> dict[str, Any]:
    tags = db.scalars(select(UserInterest.tag).where(UserInterest.user_id.in_(member_ids)))
    counts = Counter(tags)
    shared = [
        {"tag": tag, "members": n}
        for tag, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        if n >= MIN_MEMBERS_PER_INTEREST
    ]
    return {"top_interests": shared[:MAX_INTERESTS]}


def publish_run(
    db: Session,
    run: AnalyticsRun,
    graph: ig.Graph,
    user_ids: list[uuid.UUID],
    membership: list[int],
    after_memberships: Callable[[], None] | None = None,
) -> None:
    """Make `run` the active result in one transaction, or change nothing.

    Inserts communities and memberships, marks the run published, repoints
    active_results.primary and supersedes the previous run. Any exception rolls
    all of that back; the caller then marks the run failed and the previous
    result stays active. `after_memberships` lets a test inject a failure.
    The caller must have committed its own work first.
    """
    try:
        strengths = membership_strengths(graph, membership)
        members: dict[int, list[int]] = {}
        for vertex, label in enumerate(membership):
            members.setdefault(label, []).append(vertex)

        community_ids: dict[int, uuid.UUID] = {}
        for label, vertices in sorted(members.items()):
            community_ids[label] = uuid.uuid4()
            db.add(
                Community(
                    id=community_ids[label],
                    run_id=run.id,
                    label=label,
                    size=len(vertices),
                    summary=community_summary(db, [user_ids[v] for v in vertices]),
                )
            )
        db.flush()
        if membership:
            db.execute(
                insert(Membership),
                [
                    {
                        "run_id": run.id,
                        "user_id": user_ids[vertex],
                        "community_id": community_ids[label],
                        "strength": strengths[vertex],
                    }
                    for vertex, label in enumerate(membership)
                ],
            )
        if after_memberships is not None:
            after_memberships()

        now = datetime.now(UTC)
        db.execute(
            update(AnalyticsRun)
            .where(AnalyticsRun.status == "published", AnalyticsRun.id != run.id)
            .values(status="superseded")
        )
        db.execute(update(AnalyticsRun).where(AnalyticsRun.id == run.id).values(status="published"))
        db.execute(
            insert(ActiveResult)
            .values(slot=PRIMARY_SLOT, run_id=run.id, activated_at=now)
            .on_conflict_do_update(
                index_elements=[ActiveResult.slot], set_={"run_id": run.id, "activated_at": now}
            )
        )
        db.commit()
    except BaseException:
        db.rollback()
        raise
    db.refresh(run)
