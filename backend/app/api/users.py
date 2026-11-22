from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.api.auth import me_out
from app.api.deps import CurrentUser, Db
from app.models import Follow, Post, User, UserInterest
from app.schemas.content import PostPage, UserPage
from app.schemas.user import MeOut, ProfileOut, ProfileUpdate, UserListItem
from app.services import visibility
from app.services.pagination import Cursor, Limit
from app.services.posts import list_posts

router = APIRouter(tags=["profile"])


@router.patch("/me", response_model=MeOut)
def update_me(body: ProfileUpdate, user: CurrentUser, db: Db) -> MeOut:
    """Users edit only their own profile: the target is always the session's user (FR-02)."""
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.bio is not None:
        user.bio = body.bio
    if body.interests is not None:
        tags = sorted(set(body.interests))
        user.interests = [UserInterest(user_id=user.id, tag=tag) for tag in tags]
    db.commit()
    db.refresh(user)
    return me_out(user)


def _follows(follower_id, followee_id):  # type: ignore[no-untyped-def]
    return exists().where(Follow.follower_id == follower_id, Follow.followee_id == followee_id)


@router.get("/users", response_model=UserPage)
def search_users(
    user: CurrentUser,
    db: Db,
    query: Annotated[str, Query(max_length=80)] = "",
    limit: Limit = 20,
) -> UserPage:
    """Search by username or display name; an empty query lists the newest users."""
    stmt = select(User, _follows(user.id, User.id)).where(*visibility.user_conditions(user))
    term = query.strip().lower()
    if term:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        stmt = stmt.where(
            or_(User.username.like(pattern), func.lower(User.display_name).like(pattern))
        )
    rows = db.execute(stmt.order_by(User.created_at.desc(), User.id.desc()).limit(limit)).all()
    return UserPage(
        items=[
            UserListItem(
                id=u.id,
                username=u.username,
                display_name=u.display_name,
                bio=u.bio,
                is_following=following,
                is_self=u.id == user.id,
            )
            for u, following in rows
        ]
    )


def _count_follows(db: Session, viewer: User, *, of: User, followers: bool) -> int:
    """Count only followers or followees the viewer may see."""
    other = aliased(User)
    mine, theirs = (
        (Follow.followee_id, Follow.follower_id)
        if followers
        else (Follow.follower_id, Follow.followee_id)
    )
    return (
        db.scalar(
            select(func.count())
            .select_from(Follow)
            .join(other, other.id == theirs)
            .where(mine == of.id, *visibility.user_conditions(viewer, other))
        )
        or 0
    )


@router.get("/users/{username}", response_model=ProfileOut)
def read_profile(username: str, user: CurrentUser, db: Db) -> ProfileOut:
    """Public profile: permitted fields only, never email or settings (FR-02)."""
    target = visibility.get_user(db, user, username=username)
    return ProfileOut(
        id=target.id,
        username=target.username,
        display_name=target.display_name,
        bio=target.bio,
        interests=[i.tag for i in target.interests],
        follower_count=_count_follows(db, user, of=target, followers=True),
        following_count=_count_follows(db, user, of=target, followers=False),
        is_following=bool(db.scalar(select(_follows(user.id, target.id)))),
        follows_you=bool(db.scalar(select(_follows(target.id, user.id)))),
        is_self=target.id == user.id,
        created_at=target.created_at,
    )


@router.get("/users/{username}/posts", response_model=PostPage)
def read_user_posts(
    username: str, user: CurrentUser, db: Db, cursor: Cursor = None, limit: Limit = 20
) -> PostPage:
    """Posts for the profile screen (D-007)."""
    target = visibility.get_user(db, user, username=username)
    return list_posts(db, user, Post.author_id == target.id, cursor=cursor, limit=limit)
