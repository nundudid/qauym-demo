"""Idempotency-Key handling for POSTs that create content or relationships (FR-03, FR-04)."""

import hashlib
import json
import uuid
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import Problem
from app.models import IdempotencyKey, User


def require_idempotency_key(
    idempotency_key: Annotated[str | None, Header(description="A UUID, unique per action")] = None,
) -> str:
    try:
        return str(uuid.UUID(idempotency_key or ""))
    except ValueError:
        raise Problem(
            400, "Idempotency key required", "Send an Idempotency-Key header containing a UUID."
        ) from None


IdemKey = Annotated[str, Depends(require_idempotency_key)]


def _request_hash(request: Request, payload: Any) -> str:
    canonical = json.dumps(
        [request.method, request.url.path, jsonable_encoder(payload)], sort_keys=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _replay(stored: IdempotencyKey, request_hash: str) -> JSONResponse:
    if stored.request_hash != request_hash:
        raise Problem(
            409,
            "Idempotency key reused",
            "This Idempotency-Key was already used with a different request.",
        )
    return JSONResponse(stored.response_body, status_code=stored.response_status)


def run_idempotent(
    db: Session,
    user: User,
    request: Request,
    key: str,
    payload: Any,
    handler: Callable[[], tuple[int, Any]],
) -> JSONResponse:
    """Run `handler` at most once per (user, key) and commit.

    `handler` makes its changes in the open transaction and returns (status, body).
    The stored response is written in that same transaction, so a repeated key
    returns it without a second row or event.
    """
    request_hash = _request_hash(request, payload)
    stored = db.get(IdempotencyKey, (user.id, key))
    if stored is not None:
        return _replay(stored, request_hash)

    status, body = handler()
    encoded = jsonable_encoder(body)
    db.add(
        IdempotencyKey(
            user_id=user.id,
            key=key,
            method=request.method,
            path=request.url.path,
            request_hash=request_hash,
            response_status=status,
            response_body=encoded,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        # A concurrent request with the same key won; return what it stored.
        db.rollback()
        stored = db.get(IdempotencyKey, (user.id, key))
        if stored is None:
            raise
        return _replay(stored, request_hash)
    return JSONResponse(encoded, status_code=status)
