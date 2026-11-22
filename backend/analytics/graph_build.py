"""Snapshot builder (FR-05, DR-01, DR-02; SPEC Section 6.1).

Builds the weighted undirected user graph from follows, likes and comments as
they exist at the cutoff (decision D-001), and records what was included and
what was excluded and why.
"""

import hashlib
import json
import math
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import igraph as ig
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from analytics.detectors import build_graph
from app.models import Comment, Follow, GraphSnapshot, Like, Post, User

DEFAULT_CONFIG_PATH = Path(__file__).with_name("config") / "default.yaml"
EXCLUSION_REASONS = ("deleted", "hidden", "blocked", "opted_out", "self", "outside_window")


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def config_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


@dataclass
class SnapshotGraph:
    snapshot: GraphSnapshot
    graph: ig.Graph  # vertex attribute `user_id`, edge attribute `weight`
    user_ids: list[uuid.UUID]


def _pair(a: uuid.UUID, b: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return (a, b) if str(a) < str(b) else (b, a)


def _user_reason(user: User, config: dict[str, Any]) -> str | None:
    """Why a user is not eligible, or None. Blocks and opt-out are enforced from M2."""
    if user.deleted_at is not None:
        return "deleted"
    if not config.get("include_synthetic", True) and user.is_synthetic:
        return "synthetic"
    return None


def compute_edges(
    db: Session, cutoff: datetime, config: dict[str, Any]
) -> tuple[dict[tuple[uuid.UUID, uuid.UUID], float], dict[str, int], dict[str, int]]:
    """Return {(u, v): weight}, included counts by type and excluded counts by reason."""
    users = {u.id: u for u in db.scalars(select(User))}
    ineligible = {uid: r for uid, u in users.items() if (r := _user_reason(u, config))}
    window_start = cutoff - timedelta(days=config["window_days"])
    decay = math.log(2) / config["half_life_days"]

    weights: dict[tuple[uuid.UUID, uuid.UUID], float] = defaultdict(float)
    included: Counter[str] = Counter({"follow": 0, "like": 0, "comment": 0})
    excluded: Counter[str] = Counter({reason: 0 for reason in EXCLUSION_REASONS})

    def exclusion(
        actor: uuid.UUID, owner: uuid.UUID, at: datetime, *content: Post | Comment
    ) -> str | None:
        """First matching reason, in a fixed order so each row is counted once."""
        for uid in (actor, owner):
            if uid in ineligible:
                return ineligible[uid]
        if any(c.deleted_at is not None for c in content):
            return "deleted"
        if any(c.hidden_at is not None for c in content):
            return "hidden"
        if actor == owner:
            return "self"
        if at < window_start:
            return "outside_window"
        return None

    for follow in db.scalars(select(Follow).where(Follow.created_at <= cutoff)):
        reason = next(
            (ineligible[u] for u in (follow.follower_id, follow.followee_id) if u in ineligible),
            None,
        )
        if reason:
            excluded[reason] += 1
            continue
        # Each follow direction adds alpha, so a mutual follow counts twice: s(u, v) = 2.
        weights[_pair(follow.follower_id, follow.followee_id)] += config["alpha_follow"]
        included["follow"] += 1

    def add_interaction(kind: str, actor: uuid.UUID, owner: uuid.UUID, at: datetime) -> None:
        age_days = (cutoff - at).total_seconds() / 86400
        weights[_pair(actor, owner)] += config["beta"][kind] * math.exp(-decay * age_days)
        included[kind] += 1

    likes = db.execute(
        select(Like, Post).join(Post, Post.id == Like.post_id).where(Like.created_at <= cutoff)
    )
    for like, post in likes:
        reason = exclusion(like.user_id, post.author_id, like.created_at, post)
        if reason:
            excluded[reason] += 1
        else:
            add_interaction("like", like.user_id, post.author_id, like.created_at)

    post_alias = aliased(Post)
    comments = db.execute(
        select(Comment, post_alias)
        .join(post_alias, post_alias.id == Comment.post_id)
        .where(Comment.created_at <= cutoff)
    )
    for comment, post in comments:
        reason = exclusion(comment.author_id, post.author_id, comment.created_at, post, comment)
        if reason:
            excluded[reason] += 1
        else:
            add_interaction("comment", comment.author_id, post.author_id, comment.created_at)

    return _normalise(dict(weights), config), dict(included), dict(excluded)


def _normalise(
    weights: dict[tuple[uuid.UUID, uuid.UUID], float], config: dict[str, Any]
) -> dict[tuple[uuid.UUID, uuid.UUID], float]:
    mode = config.get("normalization", "none")
    if mode == "none" or not weights:
        return weights
    if mode != "sqrt_strength":
        raise ValueError(f"Unknown normalization: {mode}")
    strength: dict[uuid.UUID, float] = defaultdict(float)
    for (u, v), w in weights.items():
        strength[u] += w
        strength[v] += w
    mean = sum(strength.values()) / len(strength)
    return {
        (u, v): w / (math.sqrt(strength[u] * strength[v]) / mean) for (u, v), w in weights.items()
    }


def build_snapshot(
    db: Session, cutoff: datetime, config: dict[str, Any] | None = None
) -> SnapshotGraph:
    """Build the graph and add its snapshot row to the session (the caller commits)."""
    config = config or load_config()
    weights, included, excluded = compute_edges(db, cutoff, config)

    # Users with no edges are not graph nodes; they get the empty state (DR-03).
    user_ids = sorted({u for pair in weights for u in pair}, key=str)
    index = {uid: i for i, uid in enumerate(user_ids)}
    pairs = sorted(weights, key=lambda p: (str(p[0]), str(p[1])))  # deterministic edge order
    graph = build_graph(
        len(user_ids), [(index[u], index[v]) for u, v in pairs], [weights[p] for p in pairs]
    )
    graph.vs["user_id"] = [str(uid) for uid in user_ids]

    snapshot = GraphSnapshot(
        id=uuid.uuid4(),
        cutoff_at=cutoff,
        config=config,
        config_hash=config_hash(config),
        node_count=graph.vcount(),
        edge_count=graph.ecount(),
        included_counts=included,
        excluded_counts=excluded,
    )
    db.add(snapshot)
    db.flush()
    return SnapshotGraph(snapshot=snapshot, graph=graph, user_ids=user_ids)
