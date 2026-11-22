import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

EVENT_TYPES = (
    "post_created",
    "post_deleted",
    "followed",
    "unfollowed",
    "liked",
    "unliked",
    "commented",
    "comment_deleted",
    "blocked",
    "unblocked",
)
OUTBOX_STATUSES = ("pending", "dispatched", "failed")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class InteractionEvent(Base):
    """Append-only log. Rows are written in the same transaction as the change (FR-04)."""

    __tablename__ = "interaction_events"
    __table_args__ = (
        CheckConstraint(_in_list("event_type", EVENT_TYPES), name="event_type_valid"),
        Index("ix_interaction_events_occurred_at", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    post_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("posts.id"))
    comment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("comments.id"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")


class Outbox(Base):
    __tablename__ = "outbox"
    __table_args__ = (
        CheckConstraint(_in_list("status", OUTBOX_STATUSES), name="status_valid"),
        Index("ix_outbox_status_available_at", "status", "available_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interaction_events.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(255))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[Any] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
