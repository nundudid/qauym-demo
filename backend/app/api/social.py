import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.api.deps import CurrentUser, Db
from app.errors import Problem, not_found
from app.models import Comment, Follow, Like, Post
from app.schemas.content import CommentCreate, CommentOut, CommentPage, FollowOut, LikeOut
from app.services import visibility
from app.services.events import record_event
from app.services.idempotency import IdemKey, run_idempotent
from app.services.pagination import Cursor, Limit
from app.services.posts import comment_out, list_comments, visible_like_count

router = APIRouter(tags=["social"])


@router.post("/users/{user_id}/follow", response_model=FollowOut)
def follow(
    user_id: uuid.UUID, request: Request, key: IdemKey, user: CurrentUser, db: Db
) -> JSONResponse:
    def handler() -> tuple[int, FollowOut]:
        target = visibility.get_user(db, user, user_id=user_id)
        if target.id == user.id:
            raise Problem(422, "Validation failed", "You cannot follow yourself.")
        created = db.execute(
            insert(Follow)
            .values(follower_id=user.id, followee_id=target.id)
            .on_conflict_do_nothing()
            .returning(Follow.follower_id)
        ).first()
        if created is None:  # already following: no second row, no second event
            return 200, FollowOut(following=True)
        record_event(db, "followed", user.id, target_user_id=target.id)
        return 201, FollowOut(following=True)

    return run_idempotent(db, user, request, key, None, handler)


@router.delete("/users/{user_id}/follow", response_model=FollowOut)
def unfollow(user_id: uuid.UUID, user: CurrentUser, db: Db) -> FollowOut:
    removed = db.execute(
        delete(Follow)
        .where(Follow.follower_id == user.id, Follow.followee_id == user_id)
        .returning(Follow.followee_id)
    ).first()
    if removed is not None:
        record_event(db, "unfollowed", user.id, target_user_id=user_id)
    db.commit()
    return FollowOut(following=False)


def _like_out(db: Db, user: CurrentUser, post: Post, liked: bool) -> LikeOut:
    count = db.scalar(select(visible_like_count(user)).where(Post.id == post.id)) or 0
    return LikeOut(liked=liked, like_count=count)


@router.post("/posts/{post_id}/like", response_model=LikeOut)
def like(
    post_id: uuid.UUID, request: Request, key: IdemKey, user: CurrentUser, db: Db
) -> JSONResponse:
    def handler() -> tuple[int, LikeOut]:
        post = visibility.get_post(db, user, post_id)
        created = db.execute(
            insert(Like)
            .values(user_id=user.id, post_id=post.id)
            .on_conflict_do_nothing()
            .returning(Like.user_id)
        ).first()
        if created is not None:
            record_event(db, "liked", user.id, target_user_id=post.author_id, post_id=post.id)
        return (201 if created is not None else 200), _like_out(db, user, post, True)

    return run_idempotent(db, user, request, key, None, handler)


@router.delete("/posts/{post_id}/like", response_model=LikeOut)
def unlike(post_id: uuid.UUID, user: CurrentUser, db: Db) -> LikeOut:
    post = visibility.get_post(db, user, post_id)
    removed = db.execute(
        delete(Like).where(Like.user_id == user.id, Like.post_id == post.id).returning(Like.post_id)
    ).first()
    if removed is not None:
        record_event(db, "unliked", user.id, target_user_id=post.author_id, post_id=post.id)
    db.commit()
    return _like_out(db, user, post, False)


@router.get("/posts/{post_id}/comments", response_model=CommentPage)
def read_comments(
    post_id: uuid.UUID, user: CurrentUser, db: Db, cursor: Cursor = None, limit: Limit = 20
) -> CommentPage:
    post = visibility.get_post(db, user, post_id)
    return list_comments(db, user, post.id, cursor=cursor, limit=limit)


@router.post("/posts/{post_id}/comments", status_code=201, response_model=CommentOut)
def add_comment(
    post_id: uuid.UUID,
    body: CommentCreate,
    request: Request,
    key: IdemKey,
    user: CurrentUser,
    db: Db,
) -> JSONResponse:
    def handler() -> tuple[int, CommentOut]:
        post = visibility.get_post(db, user, post_id)
        comment = Comment(id=uuid.uuid4(), post_id=post.id, author_id=user.id, body=body.body)
        db.add(comment)
        db.flush()
        record_event(
            db,
            "commented",
            user.id,
            target_user_id=post.author_id,
            post_id=post.id,
            comment_id=comment.id,
        )
        return 201, comment_out(comment, user, user)

    return run_idempotent(db, user, request, key, body, handler)


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: uuid.UUID, user: CurrentUser, db: Db) -> None:
    comment = visibility.get_comment(db, user, comment_id)
    if comment.author_id != user.id:
        raise not_found("Comment")
    comment.deleted_at = datetime.now(UTC)
    record_event(db, "comment_deleted", user.id, post_id=comment.post_id, comment_id=comment.id)
    db.commit()
