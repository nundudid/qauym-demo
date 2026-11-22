"""FR-05, DR-01, DR-02: a hand-made fixture gives the expected edge weights and counts."""

import math
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from analytics.graph_build import build_snapshot, compute_edges, config_hash, load_config
from tests.factories import comment, follow, like, make_post, make_user

T = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def ago(days: float) -> datetime:
    return T - timedelta(days=days)


@pytest.fixture
def world(db: Session) -> dict:
    a, b, c = (make_user(db, name) for name in ("aaa", "bbb", "ccc"))
    gone = make_user(db, "gone", deleted_at=ago(1))
    loner = make_user(db, "loner")

    follow(db, a, b, ago(50))
    follow(db, b, a, ago(40))  # mutual: s(a, b) = 2
    follow(db, a, c, ago(30))
    follow(db, gone, a, ago(30))  # excluded: deleted user

    a_post = make_post(db, a, ago(100))
    b_post = make_post(db, b, ago(100))
    deleted_post = make_post(db, b, ago(100), deleted_at=ago(5))

    like(db, a, b_post, ago(30))  # one half-life old: 0.5 * 0.5
    comment(db, c, a_post, ago(60))  # two half-lives old: 1.0 * 0.25
    like(db, a, a_post, ago(10))  # excluded: self
    like(db, b, a_post, ago(200))  # excluded: outside the 180-day window
    like(db, c, deleted_post, ago(10))  # excluded: deleted post
    comment(db, b, a_post, ago(10), hidden_at=ago(9))  # excluded: hidden comment
    like(db, c, b_post, T + timedelta(days=1))  # after the cutoff: not part of this snapshot
    db.commit()
    return {"a": a, "b": b, "c": c, "gone": gone, "loner": loner}


def pair(x, y) -> tuple:
    return (x.id, y.id) if str(x.id) < str(y.id) else (y.id, x.id)


def test_fr05_edge_weights_match_the_formula(db: Session, world: dict) -> None:
    weights, _, _ = compute_edges(db, T, load_config())
    a, b, c = world["a"], world["b"], world["c"]
    assert set(weights) == {pair(a, b), pair(a, c)}
    assert weights[pair(a, b)] == pytest.approx(2 * 1.0 + 0.5 * 0.5)
    assert weights[pair(a, c)] == pytest.approx(1 * 1.0 + 1.0 * 0.25)


def test_fr05_included_and_excluded_counts(db: Session, world: dict) -> None:
    _, included, excluded = compute_edges(db, T, load_config())
    assert included == {"follow": 3, "like": 1, "comment": 1}
    assert excluded == {
        "deleted": 2,  # the deleted user's follow and the like on a deleted post
        "hidden": 1,
        "blocked": 0,  # enforced from M2
        "opted_out": 0,  # enforced from M2
        "self": 1,
        "outside_window": 1,
    }


def test_fr05_snapshot_row_and_graph(db: Session, world: dict) -> None:
    config = load_config()
    built = build_snapshot(db, T, config)
    db.commit()
    snapshot = built.snapshot

    assert snapshot.cutoff_at == T
    assert snapshot.config == config
    assert snapshot.config_hash == config_hash(config) and len(snapshot.config_hash) == 64
    assert (snapshot.node_count, snapshot.edge_count) == (3, 2)
    assert snapshot.included_counts["follow"] == 3
    assert snapshot.excluded_counts["self"] == 1

    # Users with no edges, and deleted users, are not graph nodes (DR-03).
    in_graph = set(built.graph.vs["user_id"])
    assert in_graph == {str(world[k].id) for k in "abc"}
    assert not built.graph.is_directed()
    assert sorted(built.graph.es["weight"]) == pytest.approx([1.25, 2.25])


def test_fr05_same_input_gives_the_same_graph(db: Session, world: dict) -> None:
    first, second = build_snapshot(db, T), build_snapshot(db, T)
    assert first.user_ids == second.user_ids
    assert first.graph.get_edgelist() == second.graph.get_edgelist()
    assert first.graph.es["weight"] == second.graph.es["weight"]


def test_dr02_decay_and_window_come_from_the_config(db: Session, world: dict) -> None:
    config = {**load_config(), "half_life_days": 60, "window_days": 365}
    weights, included, excluded = compute_edges(db, T, config)
    a, b = world["a"], world["b"]
    # The 30-day-old like now decays by 2^-0.5 and the 200-day-old like is inside the window.
    expected = (
        2.0 + 0.5 * math.exp(-math.log(2) / 60 * 30) + 0.5 * math.exp(-math.log(2) / 60 * 200)
    )
    assert weights[pair(a, b)] == pytest.approx(expected)
    assert included["like"] == 2 and excluded["outside_window"] == 0


def test_dr02_sqrt_strength_normalisation(db: Session, world: dict) -> None:
    weights, _, _ = compute_edges(db, T, {**load_config(), "normalization": "sqrt_strength"})
    a, b, c = world["a"], world["b"], world["c"]
    strength = {"a": 3.5, "b": 2.25, "c": 1.25}
    mean = sum(strength.values()) / 3
    assert weights[pair(a, b)] == pytest.approx(2.25 / (math.sqrt(3.5 * 2.25) / mean))
    assert weights[pair(a, c)] == pytest.approx(1.25 / (math.sqrt(3.5 * 1.25) / mean))


def test_dr07_synthetic_users_can_be_left_out(db: Session) -> None:
    real, demo = make_user(db, "real"), make_user(db, "demo", is_synthetic=True)
    follow(db, real, demo, ago(1))
    db.commit()
    assert len(compute_edges(db, T, load_config())[0]) == 1
    weights, _, excluded = compute_edges(db, T, {**load_config(), "include_synthetic": False})
    assert weights == {} and excluded["synthetic"] == 1
