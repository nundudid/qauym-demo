from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request, Response
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import CurrentSession, CurrentUser, Db
from app.config import get_settings
from app.errors import Problem
from app.models import Session as UserSession
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn
from app.schemas.user import MeOut
from app.security import hash_password, hash_token, new_session_token, verify_password
from app.services.rate_limit import enforce_auth_rate_limit

router = APIRouter(tags=["auth"])


def me_out(user: User) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        interests=[i.tag for i in user.interests],
        role=user.role,
        inference_opt_out=user.inference_opt_out,
        created_at=user.created_at,
    )


def start_session(db: Session, user: User, response: Response) -> None:
    settings = get_settings()
    token = new_session_token()
    lifetime = timedelta(days=settings.session_days)
    db.add(
        UserSession(
            user_id=user.id, token_hash=hash_token(token), expires_at=datetime.now(UTC) + lifetime
        )
    )
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=not settings.is_local,
        path="/",
    )


def revoke_presented_session(db: Session, request: Request) -> None:
    token = request.cookies.get(get_settings().session_cookie_name)
    if token:
        db.execute(
            update(UserSession)
            .where(UserSession.token_hash == hash_token(token), UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )


def account_exists() -> Problem:
    return Problem(
        409, "Account already exists", "An account with this email or username already exists."
    )


@router.post("/auth/register", status_code=201, response_model=MeOut)
def register(body: RegisterIn, request: Request, response: Response, db: Db) -> MeOut:
    enforce_auth_rate_limit(request, "register")
    taken = db.scalar(
        select(User.id).where(or_(User.email == body.email, User.username == body.username))
    )
    if taken is not None:
        raise account_exists()
    user = User(
        email=body.email,
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.username,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # lost a race with an identical registration
        db.rollback()
        raise account_exists() from None
    start_session(db, user, response)
    db.commit()
    return me_out(user)


@router.post("/auth/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response, db: Db) -> MeOut:
    enforce_auth_rate_limit(request, "login")
    user = db.scalar(select(User).where(User.email == body.email, User.deleted_at.is_(None)))
    if not verify_password(body.password, user.password_hash if user else None) or user is None:
        # Same response whether the email is unknown or the password is wrong.
        raise Problem(401, "Sign-in failed", "Invalid email or password.")
    revoke_presented_session(db, request)  # rotate: an older session cookie stops working
    start_session(db, user, response)
    db.commit()
    return me_out(user)


@router.post("/auth/logout", status_code=204)
def logout(session: CurrentSession, response: Response, db: Db) -> None:
    session.revoked_at = datetime.now(UTC)
    db.commit()
    response.delete_cookie(get_settings().session_cookie_name, path="/")


@router.get("/me", response_model=MeOut, tags=["profile"])
def read_me(user: CurrentUser) -> MeOut:
    return me_out(user)
