import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.schemas.user import UserBrief, UserListItem, _strip

PostBody = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=1000)]
CommentBody = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=500)]


class PostCreate(BaseModel):
    body: PostBody


class PostOut(BaseModel):
    id: uuid.UUID
    author: UserBrief
    body: str
    created_at: datetime
    like_count: int
    comment_count: int
    liked_by_me: bool
    is_own: bool


class CommentCreate(BaseModel):
    body: CommentBody


class CommentOut(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    author: UserBrief
    body: str
    created_at: datetime
    is_own: bool


class FollowOut(BaseModel):
    following: bool


class LikeOut(BaseModel):
    liked: bool
    like_count: int


class PostPage(BaseModel):
    items: list[PostOut]
    next_cursor: str | None


class CommentPage(BaseModel):
    items: list[CommentOut]
    next_cursor: str | None


class UserPage(BaseModel):
    items: list[UserListItem]
