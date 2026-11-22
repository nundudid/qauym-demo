import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, Db
from app.errors import not_found
from app.models import Follow, Post
from app.schemas.content import PostCreate, PostOut, PostPage
from app.services import visibility
from app.services.events import record_event
from app.services.idempotency import IdemKey, run_idempotent
from app.services.pagination import Cursor, Limit
from app.services.posts import get_post_out, list_posts

router = APIRouter(tags=["posts"])


@router.post("/posts", status_code=201, response_model=PostOut)
def create_post(
    body: PostCreate, request: Request, key: IdemKey, user: CurrentUser, db: Db
) -> JSONResponse:
    def handler() -> tuple[int, PostOut]:
        post = Post(id=uuid.uuid4(), author_id=user.id, body=body.body)
        db.add(post)
        db.flush()
        record_event(db, "post_created", user.id, post_id=post.id)
        return 201, get_post_out(db, user, post.id)

    return run_idempotent(db, user, request, key, body, handler)


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: uuid.UUID, user: CurrentUser, db: Db) -> None:
    post = visibility.get_post(db, user, post_id)
    if post.author_id != user.id:
        raise not_found("Post")  # cross-user writes look like a missing object (NFR-03)
    post.deleted_at = datetime.now(UTC)
    record_event(db, "post_deleted", user.id, post_id=post.id)
    db.commit()


@router.get("/feed", response_model=PostPage)
def read_feed(user: CurrentUser, db: Db, cursor: Cursor = None, limit: Limit = 20) -> PostPage:
    """Own and followed users' posts, newest first. No ranking, so it is non-profiled."""
    followed = select(Follow.followee_id).where(Follow.follower_id == user.id)
    return list_posts(
        db,
        user,
        or_(Post.author_id == user.id, Post.author_id.in_(followed)),
        cursor=cursor,
        limit=limit,
    )
