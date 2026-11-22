"""Append-only interaction log plus outbox (FR-04)."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import InteractionEvent, Outbox


def record_event(
    db: Session,
    event_type: str,
    actor_id: uuid.UUID,
    *,
    target_user_id: uuid.UUID | None = None,
    post_id: uuid.UUID | None = None,
    comment_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> InteractionEvent:
    """Add the event and its outbox row to the caller's open transaction.

    The caller commits, so the change, its event and its outbox entry succeed or
    fail together. Payloads must never contain post or comment bodies.
    """
    event = InteractionEvent(
        id=uuid.uuid4(),
        event_type=event_type,
        actor_id=actor_id,
        target_user_id=target_user_id,
        post_id=post_id,
        comment_id=comment_id,
        payload=payload or {},
    )
    db.add(event)
    db.flush()
    db.add(Outbox(event_id=event.id))
    return event
