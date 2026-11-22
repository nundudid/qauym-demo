"""Post and comment listings, always filtered through the visibility module."""

import uuid

from sqlalchemy import ColumnElement, exists, func, select
from sqlalchemy.orm import Session, aliased

from app.models import Comment, Like, Post, User
from app.schemas.content import CommentOut, CommentPage, PostOut, PostPage
from app.schemas.user import UserBrief
from app.services import visibility
from app.services.pagination import before_cursor, encode_cursor


def brief(user: User) -> UserBrief:
    return UserBrief(id=user.id, username=user.username, display_name=user.display_name)


def visible_like_count(viewer: User):  # type: ignore[no-untyped-def]
    liker = aliased(User)
    return (
        select(func.count())
        .select_from(Like)
        .join(liker, liker.id == Like.user_id)
        .where(Like.post_id == Post.id, *visibility.user_conditions(viewer, liker))
        .correlate(Post)
        .scalar_subquery()
    )


def visible_comment_count(viewer: User):  # type: ignore[no-untyped-def]
    commenter = aliased(User)
    return (
        select(func.count())
        .select_from(Comment)
        .join(commenter, commenter.id == Comment.author_id)
        .where(
            Comment.post_id == Post.id,
            *visibility.comment_conditions(viewer, Comment, commenter),
        )
        .correlate(Post)
        .scalar_subquery()
    )


def list_posts(
    db: Session,
    viewer: User,
    *conditions: ColumnElement[bool],
    cursor: str | None = None,
    limit: int = 20,
) -> PostPage:
    liked = exists().where(Like.post_id == Post.id, Like.user_id == viewer.id)
    rows = db.execute(
        select(Post, User, visible_like_count(viewer), visible_comment_count(viewer), liked)
        .join(User, User.id == Post.author_id)
        .where(*visibility.post_conditions(viewer), *conditions, *before_cursor(Post, cursor))
        .order_by(Post.created_at.desc(), Post.id.desc())
        .limit(limit + 1)
    ).all()
    items = [
        PostOut(
            id=post.id,
            author=brief(author),
            body=post.body,
            created_at=post.created_at,
            like_count=likes,
            comment_count=comments,
            liked_by_me=liked_by_me,
            is_own=post.author_id == viewer.id,
        )
        for post, author, likes, comments, liked_by_me in rows[:limit]
    ]
    more = len(rows) > limit
    return PostPage(
        items=items,
        next_cursor=encode_cursor(items[-1].created_at, items[-1].id) if more else None,
    )


def get_post_out(db: Session, viewer: User, post_id: uuid.UUID) -> PostOut:
    return list_posts(db, viewer, Post.id == post_id, limit=1).items[0]


def list_comments(
    db: Session, viewer: User, post_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20
) -> CommentPage:
    rows = db.execute(
        select(Comment, User)
        .join(User, User.id == Comment.author_id)
        .where(
            Comment.post_id == post_id,
            *visibility.comment_conditions(viewer),
            *before_cursor(Comment, cursor),
        )
        .order_by(Comment.created_at.desc(), Comment.id.desc())
        .limit(limit + 1)
    ).all()
    items = [comment_out(comment, author, viewer) for comment, author in rows[:limit]]
    more = len(rows) > limit
    return CommentPage(
        items=items,
        next_cursor=encode_cursor(items[-1].created_at, items[-1].id) if more else None,
    )


def comment_out(comment: Comment, author: User, viewer: User) -> CommentOut:
    return CommentOut(
        id=comment.id,
        post_id=comment.post_id,
        author=brief(author),
        body=comment.body,
        created_at=comment.created_at,
        is_own=comment.author_id == viewer.id,
    )
