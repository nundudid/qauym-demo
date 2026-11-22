import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

ALGORITHMS = ("leiden", "louvain")
RUN_STATUSES = ("queued", "running", "succeeded", "failed", "published", "superseded")
RUN_TRIGGERS = ("manual", "schedule", "outbox")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class GraphSnapshot(Base):
    """The graph an analytics run was computed on. Never updated after creation."""

    __tablename__ = "graph_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    config_hash: Mapped[str] = mapped_column(String(64))
    node_count: Mapped[int] = mapped_column(Integer)
    edge_count: Mapped[int] = mapped_column(Integer)
    included_counts: Mapped[dict[str, Any]] = mapped_column(JSONB)
    excluded_counts: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalyticsRun(Base):
    __tablename__ = "analytics_runs"
    __table_args__ = (
        CheckConstraint(_in_list("algorithm", ALGORITHMS), name="algorithm_valid"),
        CheckConstraint(_in_list("status", RUN_STATUSES), name="status_valid"),
        CheckConstraint(_in_list("trigger", RUN_TRIGGERS), name="trigger_valid"),
        Index("ix_analytics_runs_started_at", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("graph_snapshots.id"))
    algorithm: Mapped[str] = mapped_column(String(20))
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    seed: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="queued", server_default="queued")
    trigger: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    job_key: Mapped[str] = mapped_column(String(100), unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float | None] = mapped_column(Float)
    peak_mem_mb: Mapped[float | None] = mapped_column(Float)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    code_revision: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)


class Community(Base):
    __tablename__ = "communities"
    __table_args__ = (UniqueConstraint("run_id", "label"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analytics_runs.id", ondelete="CASCADE"))
    label: Mapped[int] = mapped_column(Integer)
    size: Mapped[int] = mapped_column(Integer)
    # Top shared interests: only tags declared by at least 3 members (DR-04).
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        CheckConstraint("strength >= 0 AND strength <= 1", name="strength_range"),
        Index("ix_memberships_community_id", "community_id"),
        Index("ix_memberships_user_id", "user_id"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_runs.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    community_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE")
    )
    # Share of the user's edge weight that stays inside the community, 0-1.
    strength: Mapped[float] = mapped_column(Float)


class ActiveResult(Base):
    """slot = 'primary' points at the published Leiden run; changed only when publishing."""

    __tablename__ = "active_results"

    slot: Mapped[str] = mapped_column(String(20), primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analytics_runs.id"))
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
