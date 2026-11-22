"""Cursor pagination on (created_at, id), newest first (SPEC Section 5)."""

import base64
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import Query
from sqlalchemy import ColumnElement, tuple_

from app.errors import Problem

Limit = Annotated[int, Query(ge=1, le=50)]
Cursor = Annotated[str | None, Query(description="next_cursor from the previous page")]


def encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{created_at.isoformat()}|{row_id}".encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        stamp, row_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(stamp), uuid.UUID(row_id)
    except (ValueError, UnicodeDecodeError):
        raise Problem(400, "Invalid cursor", "The cursor is not valid.") from None


def before_cursor(model: Any, cursor: str | None) -> list[ColumnElement[bool]]:
    if cursor is None:
        return []
    stamp, row_id = decode_cursor(cursor)
    return [tuple_(model.created_at, model.id) < (stamp, row_id)]
