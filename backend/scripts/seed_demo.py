"""`make seed`: synthetic demo users and activity (T1.1, DR-07).

About 300 users in 8 planted interest groups with 60 days of timestamped posts,
likes, comments and follows. Every account has is_synthetic = true. Nothing is
scraped and no benchmark data is used. Running it again replaces the synthetic
data and leaves real accounts alone.
"""

import os
import random
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Comment,
    Follow,
    InteractionEvent,
    Like,
    Outbox,
    Post,
    User,
    UserInterest,
)
from app.security import hash_password

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo-password")
EMAIL_DOMAIN = "demo.qauym.test"
DAYS = 60

GROUPS: list[tuple[str, ...]] = [
    ("hiking", "camping", "climbing"),
    ("chess", "boardgames", "puzzles"),
    ("football", "running", "cycling"),
    ("cooking", "baking", "coffee"),
    ("photography", "film", "design"),
    ("python", "robotics", "linux"),
    ("music", "guitar", "concerts"),
    ("books", "poetry", "history"),
]
FIRST_NAMES = [
    "Aru", "Dias", "Timur", "Aigerim", "Madina", "Nurlan", "Dana", "Yerlan", "Aliya", "Sanzhar",
    "Kamila", "Arman", "Zhanna", "Daniyar", "Saule", "Bekzat", "Aisha", "Ruslan", "Dinara",
    "Alibek", "Gulnaz", "Marat", "Asel", "Yerzhan", "Togzhan", "Adil", "Zarina", "Kairat",
    "Ainur", "Olzhas", "Laura", "Miras", "Samal", "Azamat", "Aida", "Bauyrzhan", "Meruert",
]  # fmt: skip
POST_TEMPLATES = [
    "Spent the weekend on {a}. Anyone else into it?",
    "Looking for people on campus who like {a} and {b}.",
    "Small win today: finally made progress with {a}.",
    "What got you started with {a}?",
    "Planning a {a} meetup next week. Who is in?",
    "Hot take: {a} is better with friends.",
]
COMMENT_TEMPLATES = ["Count me in!", "Nice one.", "Same here.", "Tell me more?", "Love this."]

# The demo script signs in with these (see docs/DEMO.md).
DEMO_USER = "demo"
ADMIN_USER = "admin"
ISOLATED_USER = "newcomer"


@dataclass
class SeedSummary:
    users: int
    posts: int
    follows: int
    likes: int
    comments: int
    seconds: float
    planted: dict[uuid.UUID, int]  # user id -> planted group, for the NMI check


def wipe_synthetic(db: Session) -> None:
    """Remove every synthetic account and everything attached to one."""
    syn = "(SELECT id FROM users WHERE is_synthetic)"
    posts = f"(SELECT id FROM posts WHERE author_id IN {syn})"
    comments = f"(SELECT id FROM comments WHERE author_id IN {syn} OR post_id IN {posts})"
    events = (
        "(SELECT id FROM interaction_events WHERE "
        f"actor_id IN {syn} OR target_user_id IN {syn} OR post_id IN {posts} "
        f"OR comment_id IN {comments})"
    )
    statements = [
        f"DELETE FROM outbox WHERE event_id IN {events}",
        f"DELETE FROM interaction_events WHERE id IN {events}",
        f"DELETE FROM memberships WHERE user_id IN {syn}",
        f"UPDATE analytics_runs SET requested_by = NULL WHERE requested_by IN {syn}",
        f"DELETE FROM likes WHERE user_id IN {syn} OR post_id IN {posts}",
        f"DELETE FROM comments WHERE id IN {comments}",
        f"DELETE FROM posts WHERE author_id IN {syn}",
        f"DELETE FROM follows WHERE follower_id IN {syn} OR followee_id IN {syn}",
        "DELETE FROM users WHERE is_synthetic",  # sessions, interests, idempotency keys cascade
    ]
    for statement in statements:
        db.execute(text(statement))


def seed(db: Session, *, rng_seed: int = 7, users_per_group: int = 37) -> SeedSummary:
    started = time.perf_counter()
    rng = random.Random(rng_seed)
    now = datetime.now(UTC)
    wipe_synthetic(db)

    def moment(max_days_ago: float = DAYS) -> datetime:
        return now - timedelta(seconds=rng.uniform(600, max_days_ago * 86400))

    password_hash = hash_password(DEMO_PASSWORD)  # one hash: these are throwaway demo accounts
    users: list[dict[str, Any]] = []
    interests: list[dict[str, Any]] = []
    group_of: dict[uuid.UUID, int] = {}
    members: list[list[uuid.UUID]] = [[] for _ in GROUPS]
    all_tags = [tag for group in GROUPS for tag in group]

    def add_user(
        username: str, display: str, group: int | None, role: str = "user", bio: str = ""
    ) -> uuid.UUID:
        uid = uuid.UUID(int=rng.getrandbits(128), version=4)
        users.append(
            {
                "id": uid,
                "email": f"{username}@{EMAIL_DOMAIN}",
                "username": username,
                "password_hash": password_hash,
                "display_name": display,
                "bio": bio,
                "role": role,
                "is_synthetic": True,
                "created_at": now - timedelta(days=DAYS + rng.uniform(1, 30)),
            }
        )
        if group is not None:
            group_of[uid] = group
            members[group].append(uid)
            tags = set(rng.sample(GROUPS[group], k=rng.choice([2, 3])))
            if rng.random() < 0.25:
                tags.add(rng.choice(all_tags))
            interests.extend({"user_id": uid, "tag": tag} for tag in sorted(tags))
            if not bio:
                users[-1]["bio"] = f"Into {' and '.join(sorted(tags)[:2])}."
        return uid

    add_user(DEMO_USER, "Demo User", 0, bio="The account used in the Qauym demo.")
    for group in range(len(GROUPS)):
        for i in range(users_per_group - (1 if group == 0 else 0)):
            name = FIRST_NAMES[(group * 7 + i) % len(FIRST_NAMES)]
            add_user(f"{name.lower()}_{group + 1}{i:02d}", name, group)
    add_user(ADMIN_USER, "Demo Admin", None, role="admin", bio="Runs the analytics.")
    isolated = add_user(ISOLATED_USER, "New Comer", None, bio="Just joined.")
    interests.append({"user_id": isolated, "tag": "hiking"})

    grouped = list(group_of)

    def pick_other(uid: uuid.UUID, same_group: float) -> uuid.UUID:
        """Mostly someone from the same planted group, sometimes anyone else."""
        while True:
            pool = members[group_of[uid]] if rng.random() < same_group else grouped
            other = rng.choice(pool)
            if other != uid:
                return other

    follows: dict[tuple[uuid.UUID, uuid.UUID], datetime] = {}
    for uid in grouped:
        for _ in range(rng.randint(5, 8)):
            follows.setdefault((uid, pick_other(uid, 0.9)), moment())

    posts: list[dict[str, Any]] = []
    posts_by_author: dict[uuid.UUID, list[dict[str, Any]]] = {uid: [] for uid in grouped}
    for uid in grouped:
        for _ in range(rng.randint(2, 4)):
            a, b = rng.sample(GROUPS[group_of[uid]], k=2)
            post: dict[str, Any] = {
                "id": uuid.UUID(int=rng.getrandbits(128), version=4),
                "author_id": uid,
                "body": rng.choice(POST_TEMPLATES).format(a=a, b=b),
                "created_at": moment(),
            }
            posts.append(post)
            posts_by_author[uid].append(post)

    def later(than: datetime) -> datetime:
        return than + (now - than) * rng.uniform(0.02, 1.0)

    likes: dict[tuple[uuid.UUID, uuid.UUID], dict[str, Any]] = {}
    comments: list[dict[str, Any]] = []
    for uid in grouped:
        for _ in range(rng.randint(8, 12)):
            post = rng.choice(posts_by_author[pick_other(uid, 0.85)])
            likes.setdefault(
                (uid, post["id"]),
                {"user_id": uid, "post_id": post["id"], "created_at": later(post["created_at"])},
            )
        for _ in range(rng.randint(3, 5)):
            post = rng.choice(posts_by_author[pick_other(uid, 0.85)])
            comments.append(
                {
                    "id": uuid.UUID(int=rng.getrandbits(128), version=4),
                    "post_id": post["id"],
                    "author_id": uid,
                    "body": rng.choice(COMMENT_TEMPLATES),
                    "created_at": later(post["created_at"]),
                }
            )

    follow_rows: list[dict[str, Any]] = [
        {"follower_id": a, "followee_id": b, "created_at": at} for (a, b), at in follows.items()
    ]
    author_of = {post["id"]: post["author_id"] for post in posts}

    # The same event log the API writes, so the demo data looks like real activity (FR-04).
    events: list[dict[str, Any]] = []

    def event(kind: str, actor: uuid.UUID, at: datetime, **refs: Any) -> None:
        events.append(
            {
                "id": uuid.UUID(int=rng.getrandbits(128), version=4),
                "event_type": kind,
                "actor_id": actor,
                "target_user_id": refs.get("target"),
                "post_id": refs.get("post"),
                "comment_id": refs.get("comment"),
                "occurred_at": at,
                "payload": {"seeded": True},
            }
        )

    for post in posts:
        event("post_created", post["author_id"], post["created_at"], post=post["id"])
    for row in follow_rows:
        event("followed", row["follower_id"], row["created_at"], target=row["followee_id"])
    for like in likes.values():
        post_id = like["post_id"]
        event("liked", like["user_id"], like["created_at"], target=author_of[post_id], post=post_id)
    for comment in comments:
        event(
            "commented",
            comment["author_id"],
            comment["created_at"],
            target=author_of[comment["post_id"]],
            post=comment["post_id"],
            comment=comment["id"],
        )

    for model, rows in (
        (User, users),
        (UserInterest, interests),
        (Follow, follow_rows),
        (Post, posts),
        (Like, list(likes.values())),
        (Comment, comments),
        (InteractionEvent, events),
        (Outbox, [{"id": uuid.uuid4(), "event_id": e["id"]} for e in events]),
    ):
        db.execute(insert(model), rows)
    db.commit()

    return SeedSummary(
        users=len(users),
        posts=len(posts),
        follows=len(follow_rows),
        likes=len(likes),
        comments=len(comments),
        seconds=time.perf_counter() - started,
        planted=group_of,
    )


def main() -> int:
    with SessionLocal() as db:
        summary = seed(db)
    print(
        f"Seeded {summary.users} synthetic users in {len(GROUPS)} planted groups: "
        f"{summary.posts} posts, {summary.follows} follows, {summary.likes} likes, "
        f"{summary.comments} comments in {summary.seconds:.1f}s."
    )
    print(
        f"Sign in as {DEMO_USER}@{EMAIL_DOMAIN}, {ADMIN_USER}@{EMAIL_DOMAIN} (admin) or "
        f"{ISOLATED_USER}@{EMAIL_DOMAIN} (no connections) with the password "
        f"'{DEMO_PASSWORD}'."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
