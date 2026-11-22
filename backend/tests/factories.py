"""Direct database fixtures for analytics tests (no API round trip, no rate limit)."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Comment, Follow, Like, Post, User, UserInterest


def days_ago(days: float, now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) - timedelta(days=days)


def make_user(db: Session, username: str, *, interests: tuple[str, ...] = (), **fields) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{username}@example.com",
        username=username,
        password_hash="not-a-real-hash",
        display_name=username.capitalize(),
        **fields,
    )
    db.add(user)
    db.flush()
    db.add_all(UserInterest(user_id=user.id, tag=tag) for tag in interests)
    db.flush()
    return user


def follow(db: Session, follower: User, followee: User, at: datetime | None = None) -> None:
    db.add(
        Follow(follower_id=follower.id, followee_id=followee.id, created_at=at or datetime.now(UTC))
    )
    db.flush()


def make_post(db: Session, author: User, at: datetime | None = None, **fields) -> Post:
    post = Post(
        id=uuid.uuid4(),
        author_id=author.id,
        body="post",
        created_at=at or datetime.now(UTC),
        **fields,
    )
    db.add(post)
    db.flush()
    return post


def like(db: Session, user: User, post: Post, at: datetime | None = None) -> None:
    db.add(Like(user_id=user.id, post_id=post.id, created_at=at or datetime.now(UTC)))
    db.flush()


def comment(db: Session, user: User, post: Post, at: datetime | None = None, **fields) -> Comment:
    row = Comment(
        id=uuid.uuid4(),
        post_id=post.id,
        author_id=user.id,
        body="comment",
        created_at=at or datetime.now(UTC),
        **fields,
    )
    db.add(row)
    db.flush()
    return row


def two_groups(db: Session, size: int = 4) -> tuple[list[User], list[User]]:
    """Two fully connected follow groups joined by one follow: two obvious communities."""
    left = [make_user(db, f"left{i}", interests=("hiking", "chess")) for i in range(size)]
    right = [make_user(db, f"right{i}", interests=("cooking",)) for i in range(size)]
    for group in (left, right):
        for a in group:
            for b in group:
                if a is not b:
                    follow(db, a, b)
    follow(db, left[0], right[0])
    db.commit()
    return left, right
