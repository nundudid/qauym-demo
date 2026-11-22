from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import Problem
from app.models import Session as UserSession
from app.models import User
from app.security import hash_token

Db = Annotated[Session, Depends(get_db)]

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def csrf_guard(request: Request) -> None:
    """Mutating requests must carry `X-Qauym-Client: web` and, if they have a body, JSON."""
    if request.method not in MUTATING_METHODS:
        return
    if request.headers.get("x-qauym-client") != "web":
        raise Problem(403, "Forbidden", "Missing or invalid X-Qauym-Client header.")
    has_body = int(request.headers.get("content-length") or 0) > 0
    content_type = request.headers.get("content-type", "")
    if has_body and not content_type.startswith("application/json"):
        raise Problem(415, "Unsupported media type", "Request bodies must be JSON.")


def unauthenticated() -> Problem:
    return Problem(401, "Not authenticated", "Sign in to continue.")


def get_current_session(request: Request, db: Db) -> UserSession:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise unauthenticated()
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(UTC),
        )
    )
    if session is None:
        raise unauthenticated()
    return session


CurrentSession = Annotated[UserSession, Depends(get_current_session)]


def get_current_user(session: CurrentSession, db: Db) -> User:
    user = db.get(User, session.user_id)
    if user is None or user.deleted_at is not None:
        raise unauthenticated()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):  # type: ignore[no-untyped-def]
    def check(user: CurrentUser) -> User:
        # Hidden rather than forbidden, so the API does not confirm the route exists.
        if user.role not in roles:
            raise Problem(404, "Not found", "Resource not found.")
        return user

    return check
