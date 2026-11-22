"""The single owner of every rule about who can see what (SPEC Section 9, rule 1).

Every endpoint that returns users, posts, comments, communities, suggestions or
graph data must build its queries from these functions. M0 rules: deleted users
and deleted or hidden content are never returned. Blocks and opt-out (M2) are
added here, so no endpoint has to change. Every function takes the viewer for
that reason, even where M0 does not use it yet.
"""

import uuid
from typing import Any

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.orm import Session

from app.errors import not_found
from app.models import (
    ActiveResult,
    AnalyticsRun,
    Comment,
    Community,
    Follow,
    GraphSnapshot,
    Membership,
    Post,
    User,
)


def user_conditions(viewer: User, user: Any = User) -> list[ColumnElement[bool]]:
    """SQL conditions that keep only users the viewer may see."""
    return [user.deleted_at.is_(None)]


def post_conditions(
    viewer: User, post: Any = Post, author: Any = User
) -> list[ColumnElement[bool]]:
    """Conditions for posts; the query must join `author` on post.author_id."""
    return [post.deleted_at.is_(None), post.hidden_at.is_(None), *user_conditions(viewer, author)]


def comment_conditions(
    viewer: User, comment: Any = Comment, author: Any = User
) -> list[ColumnElement[bool]]:
    """Conditions for comments; the query must join `author` on comment.author_id."""
    return [
        comment.deleted_at.is_(None),
        comment.hidden_at.is_(None),
        *user_conditions(viewer, author),
    ]


def get_user(
    db: Session, viewer: User, *, user_id: uuid.UUID | None = None, username: str | None = None
) -> User:
    """Return a visible user or raise 404, never 403 (SPEC Section 5)."""
    query = select(User).where(*user_conditions(viewer))
    if user_id is not None:
        query = query.where(User.id == user_id)
    elif username is not None:
        query = query.where(User.username == username.lower())
    else:
        raise not_found("User")
    user = db.scalar(query)
    if user is None:
        raise not_found("User")
    return user


def get_post(db: Session, viewer: User, post_id: uuid.UUID) -> Post:
    post = db.scalar(
        select(Post)
        .join(User, User.id == Post.author_id)
        .where(Post.id == post_id, *post_conditions(viewer))
    )
    if post is None:
        raise not_found("Post")
    return post


def get_comment(db: Session, viewer: User, comment_id: uuid.UUID) -> Comment:
    comment = db.scalar(
        select(Comment)
        .join(User, User.id == Comment.author_id)
        .where(Comment.id == comment_id, *comment_conditions(viewer))
    )
    if comment is None:
        raise not_found("Comment")
    get_post(db, viewer, comment.post_id)  # a comment is only visible with its post
    return comment


# --- Inferred communities (M1) -------------------------------------------------


def active_run(db: Session) -> tuple[AnalyticsRun, GraphSnapshot] | None:
    """The published Leiden run and its snapshot, or None before the first run.

    Analytics results are only ever read through active_results, so a failed or
    half-written run can never be shown.
    """
    row = db.execute(
        select(AnalyticsRun, GraphSnapshot)
        .join(ActiveResult, ActiveResult.run_id == AnalyticsRun.id)
        .join(GraphSnapshot, GraphSnapshot.id == AnalyticsRun.snapshot_id)
        .where(ActiveResult.slot == "primary", AnalyticsRun.status == "published")
    ).first()
    return (row[0], row[1]) if row else None


def viewer_membership(db: Session, viewer: User, run: AnalyticsRun) -> Membership | None:
    return db.get(Membership, (run.id, viewer.id))


def get_viewer_community(db: Session, viewer: User, community_id: uuid.UUID) -> Community:
    """A community page is visible only to its own members, in the active run (D-014)."""
    active = active_run(db)
    if active is None:
        raise not_found("Community")
    membership = viewer_membership(db, viewer, active[0])
    if membership is None or membership.community_id != community_id:
        raise not_found("Community")
    community = db.get(Community, community_id)
    if community is None:
        raise not_found("Community")
    return community


def community_member_count(db: Session, viewer: User, community: Community) -> int:
    """Members the viewer may see; deleted users are not counted."""
    return (
        db.scalar(
            select(func.count())
            .select_from(Membership)
            .join(User, User.id == Membership.user_id)
            .where(Membership.community_id == community.id, *user_conditions(viewer))
        )
        or 0
    )


def known_community_members(db: Session, viewer: User, community: Community) -> list[User]:
    """Members the viewer follows or who follow the viewer. Everyone else is only counted,

    so the page never names someone the viewer could not already see a link to (DR-04).
    """
    follows_them = exists().where(Follow.follower_id == viewer.id, Follow.followee_id == User.id)
    follows_me = exists().where(Follow.follower_id == User.id, Follow.followee_id == viewer.id)
    return list(
        db.scalars(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.community_id == community.id,
                User.id != viewer.id,
                or_(follows_them, follows_me),
                *user_conditions(viewer),
            )
            .order_by(User.display_name, User.username)
        )
    )
