"""T0.2: the migration applies on an empty database and rolls back cleanly."""

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.db import Base, engine

M0_TABLES = {
    "users",
    "user_interests",
    "sessions",
    "posts",
    "comments",
    "follows",
    "likes",
    "interaction_events",
    "outbox",
    "idempotency_keys",
}


def table_names() -> set[str]:
    return set(inspect(engine).get_table_names())


def test_migration_rolls_back_and_reapplies(alembic_cfg: Config) -> None:
    assert M0_TABLES <= table_names()

    command.downgrade(alembic_cfg, "base")
    assert table_names() == {"alembic_version"}

    command.upgrade(alembic_cfg, "head")
    assert M0_TABLES <= table_names()


def test_models_match_the_migrated_schema() -> None:
    assert {t.name for t in Base.metadata.sorted_tables} <= table_names()


USER_SQL = (
    "INSERT INTO users (id, email, username, password_hash, display_name) "
    "VALUES (gen_random_uuid(), :email, :username, 'x', 'X') RETURNING id"
)


@pytest.mark.parametrize(
    ("email", "username"),
    [("Upper@example.com", "valid_name"), ("ok@example.com", "No"), ("ok@example.com", "Bad-Name")],
)
def test_user_constraints_reject_bad_rows(db: Session, email: str, username: str) -> None:
    with pytest.raises(IntegrityError):
        db.execute(text(USER_SQL), {"email": email, "username": username})


def test_follow_constraints(db: Session) -> None:
    a = db.execute(text(USER_SQL), {"email": "a@example.com", "username": "aaa"}).scalar_one()
    b = db.execute(text(USER_SQL), {"email": "b@example.com", "username": "bbb"}).scalar_one()
    follow = text("INSERT INTO follows (follower_id, followee_id) VALUES (:f, :t)")
    db.execute(follow, {"f": a, "t": b})
    db.commit()

    with pytest.raises(IntegrityError):  # self-follow
        db.execute(follow, {"f": a, "t": a})
    db.rollback()
    with pytest.raises(IntegrityError):  # duplicate
        db.execute(follow, {"f": a, "t": b})
