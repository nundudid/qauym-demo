from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.jobs import run_analytics
from app.api.deps import Db, require_role
from app.models import ActiveResult, AnalyticsRun, GraphSnapshot, User
from app.schemas.analytics import RunList, RunOut, RunTriggerOut

router = APIRouter(tags=["admin"])

# The role is read from the database for the session's user, never from the client.
Admin = Annotated[User, Depends(require_role("admin"))]


def run_rows(db: Session, run_ids: list | None = None, limit: int = 50) -> list[RunOut]:
    active_id = db.scalar(select(ActiveResult.run_id).where(ActiveResult.slot == "primary"))
    query = (
        select(AnalyticsRun, GraphSnapshot)
        .outerjoin(GraphSnapshot, GraphSnapshot.id == AnalyticsRun.snapshot_id)
        .order_by(AnalyticsRun.started_at.desc(), AnalyticsRun.algorithm)
        .limit(limit)
    )
    if run_ids is not None:
        query = query.where(AnalyticsRun.id.in_(run_ids))
    out = []
    for run, snapshot in db.execute(query):
        metrics = run.metrics or {}
        out.append(
            RunOut(
                id=run.id,
                algorithm=run.algorithm,
                status=run.status,
                trigger=run.trigger,
                seed=run.seed,
                started_at=run.started_at,
                finished_at=run.finished_at,
                duration_ms=run.duration_ms,
                peak_mem_mb=run.peak_mem_mb,
                modularity=metrics.get("modularity"),
                n_communities=metrics.get("n_communities"),
                metrics=run.metrics,
                code_revision=run.code_revision,
                error_message=run.error_message,
                snapshot_id=run.snapshot_id,
                snapshot_cutoff_at=snapshot.cutoff_at if snapshot else None,
                node_count=snapshot.node_count if snapshot else None,
                edge_count=snapshot.edge_count if snapshot else None,
                is_active=run.id == active_id,
            )
        )
    return out


@router.post("/admin/analytics/runs", response_model=RunTriggerOut, status_code=201)
def trigger_run(admin: Admin, db: Db, response: Response) -> RunTriggerOut:
    """Build a snapshot, run Leiden and Louvain, validate, and publish Leiden.

    Synchronous in M1. If a run is already in progress, or one already exists for
    this minute, nothing new starts and the existing runs are returned with 200.
    """
    outcome = run_analytics(db, trigger="manual", requested_by=admin.id)
    if not outcome.started:
        response.status_code = 200
    return RunTriggerOut(
        started=outcome.started,
        reason=outcome.reason,
        runs=run_rows(db, [run.id for run in outcome.runs]),
    )


@router.get("/admin/analytics/runs", response_model=RunList)
def list_runs(admin: Admin, db: Db) -> RunList:
    return RunList(items=run_rows(db))
