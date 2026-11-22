"""T1.1, DR-07: the seed is synthetic, fast, repeatable, and has recoverable planted groups."""

from datetime import UTC, datetime

from sklearn.metrics import normalized_mutual_info_score
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from analytics.detectors import run_leiden
from analytics.graph_build import build_snapshot
from app.models import InteractionEvent, Outbox, Post, User
from scripts.seed_demo import ADMIN_USER, DEMO_USER, GROUPS, ISOLATED_USER, seed
from tests.factories import make_user


def count(db: Session, model: type, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def test_t11_seed_is_synthetic_fast_and_recoverable(db: Session) -> None:
    real = make_user(db, "real_person")
    db.commit()

    summary = seed(db)
    assert summary.seconds < 60
    assert 280 <= summary.users <= 320
    assert len(GROUPS) == 8 and len(set(summary.planted.values())) == 8
    assert count(db, User, User.is_synthetic) == summary.users
    assert count(db, User, User.is_synthetic.is_(False)) == 1  # the real account is untouched
    assert count(db, InteractionEvent) == count(db, Outbox) > 0

    roles = dict(db.execute(select(User.username, User.role)).all())
    assert roles[ADMIN_USER] == "admin" and roles[DEMO_USER] == "user"
    newest, oldest = db.execute(select(func.max(Post.created_at), func.min(Post.created_at))).one()
    assert 50 <= (newest - oldest).days <= 60

    # Leiden on the seeded graph recovers the planted groups: NMI >= 0.7.
    built = build_snapshot(db, datetime.now(UTC))
    membership = run_leiden(built.graph, 42)
    truth = [summary.planted[uid] for uid in built.user_ids]
    assert normalized_mutual_info_score(truth, membership) >= 0.7

    in_graph = {str(uid) for uid in built.user_ids}
    isolated = db.scalars(select(User).where(User.username == ISOLATED_USER)).one()
    assert str(isolated.id) not in in_graph  # shows the empty state in the demo
    assert str(real.id) not in in_graph
    db.rollback()

    # Running it again replaces the synthetic data instead of adding to it.
    again = seed(db)
    assert again.users == summary.users
    assert count(db, User, User.is_synthetic) == summary.users
    assert count(db, User, User.id == real.id) == 1
