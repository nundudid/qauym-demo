import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,30}$")
MAX_INTERESTS = 10


def _normalise(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


def _check_email(value: str) -> str:
    if len(value) > 320 or not EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address")
    return value


def _check_username(value: str) -> str:
    if not USERNAME_RE.match(value):
        raise ValueError("Use 3–30 characters: a–z, 0–9 and underscore")
    return value


def _check_tag(value: str) -> str:
    if not 1 <= len(value) <= 30:
        raise ValueError("Each interest must be 1–30 characters")
    return value


Email = Annotated[str, BeforeValidator(_normalise), AfterValidator(_check_email)]
Username = Annotated[str, BeforeValidator(_normalise), AfterValidator(_check_username)]
Tag = Annotated[str, BeforeValidator(_normalise), AfterValidator(_check_tag)]


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


DisplayName = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=80)]


class MeOut(BaseModel):
    """The viewer's own profile, including private fields (FR-02)."""

    id: uuid.UUID
    email: str
    username: str
    display_name: str
    bio: str
    interests: list[str]
    role: str
    inference_opt_out: bool
    created_at: datetime


class UserBrief(BaseModel):
    """Permitted public fields only: never email, role or settings."""

    id: uuid.UUID
    username: str
    display_name: str


class UserListItem(UserBrief):
    bio: str
    is_following: bool
    is_self: bool


class ProfileOut(UserBrief):
    bio: str
    interests: list[str]
    follower_count: int
    following_count: int
    is_following: bool
    follows_you: bool
    is_self: bool
    created_at: datetime


class ProfileUpdate(BaseModel):
    display_name: DisplayName | None = None
    bio: Annotated[str, BeforeValidator(_strip), Field(max_length=280)] | None = None
    interests: Annotated[list[Tag], Field(max_length=MAX_INTERESTS)] | None = None
