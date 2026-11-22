import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.user import UserBrief


class CommunityOut(BaseModel):
    id: uuid.UUID
    name: str  # "Community {n}": never derived from a trait (DR-04)
    shared_interests: list[str]  # tags declared by at least 3 members
    size: int
    known_members: list[UserBrief]  # people the viewer follows or who follow the viewer
    other_member_count: int  # everyone else is counted, not named
    strength: float | None = None


class CommunitiesMeOut(BaseModel):
    """`state` tells the client which explicit state to show (FR-08, DR-03)."""

    state: Literal["member", "not_in_graph", "no_run"]
    message: str
    inferred: Literal[True] = True
    run_id: uuid.UUID | None
    snapshot_cutoff_at: datetime | None
    community: CommunityOut | None


class CommunityDetailOut(BaseModel):
    inferred: Literal[True] = True
    run_id: uuid.UUID
    snapshot_cutoff_at: datetime
    community: CommunityOut


class RunOut(BaseModel):
    id: uuid.UUID
    algorithm: str
    status: str
    trigger: str
    seed: int | None
    started_at: datetime
    finished_at: datetime | None
    duration_ms: float | None
    peak_mem_mb: float | None
    modularity: float | None
    n_communities: int | None
    metrics: dict[str, Any] | None
    code_revision: str | None
    error_message: str | None
    snapshot_id: uuid.UUID | None
    snapshot_cutoff_at: datetime | None
    node_count: int | None
    edge_count: int | None
    is_active: bool


class RunList(BaseModel):
    items: list[RunOut]


class RunTriggerOut(BaseModel):
    started: bool
    reason: str
    runs: list[RunOut]
