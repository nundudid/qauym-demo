"""FR-06: detectors are reproducible and the metrics are correct on a known graph."""

import math
import random

import igraph as ig
import pytest

from analytics.detectors import DETECTORS, build_graph, run_leiden, run_louvain
from analytics.metrics import all_finite, partition_metrics


def two_cliques() -> ig.Graph:
    """Two 5-cliques joined by one edge: the obvious partition has two communities."""
    edges = [
        (a, b) for base in (0, 5) for a in range(base, base + 5) for b in range(a + 1, base + 5)
    ]
    return build_graph(10, [*edges, (4, 5)])


def planted(seed: int = 3) -> ig.Graph:
    """Six planted groups of 50: dense inside (p = 0.2), sparse between (p = 0.01)."""
    rng = random.Random(seed)
    edges = [
        (a, b)
        for a in range(300)
        for b in range(a + 1, 300)
        if rng.random() < (0.2 if a // 50 == b // 50 else 0.01)
    ]
    return build_graph(300, edges)


@pytest.mark.parametrize("method", ["leiden", "louvain"])
def test_fr06_same_seed_gives_the_same_membership(method: str) -> None:
    g = planted()
    first = DETECTORS[method](g, 42)
    assert first == DETECTORS[method](g, 42)
    assert len(first) == g.vcount()
    assert sorted(set(first)) == list(range(max(first) + 1))  # labels contiguous from 0


@pytest.mark.parametrize("detector", [run_leiden, run_louvain])
def test_fr06_detectors_split_two_cliques(detector) -> None:  # type: ignore[no-untyped-def]
    membership = detector(two_cliques(), 1)
    assert len(set(membership)) == 2
    assert len(set(membership[:5])) == len(set(membership[5:])) == 1


def test_fr06_detectors_use_edge_weights() -> None:
    # A path a-b-c-d whose middle edge is far heavier: weights must pull b and c together.
    g = build_graph(4, [(0, 1), (1, 2), (2, 3)], [0.1, 10.0, 0.1])
    membership = run_leiden(g, 1)
    assert membership[1] == membership[2]


def test_fr06_metrics_on_two_cliques() -> None:
    g = two_cliques()
    metrics = partition_metrics(g, [0] * 5 + [1] * 5)
    assert metrics["n_communities"] == 2
    assert (metrics["size_min"], metrics["size_median"], metrics["size_max"]) == (5, 5.0, 5)
    assert metrics["singletons"] == 0
    assert metrics["coverage"] == pytest.approx(20 / 21)
    assert metrics["mean_conductance"] == pytest.approx(1 / 21)  # cut 1, volume 21 each side
    assert metrics["modularity"] == pytest.approx(g.modularity([0] * 5 + [1] * 5))
    assert metrics["disconnected_communities"] == 0
    assert all_finite(metrics)


def test_fr06_metrics_count_disconnected_communities_and_singletons() -> None:
    g = two_cliques()
    # Community 0 holds one node from each clique plus nothing linking them inside it.
    metrics = partition_metrics(g, [0, 1, 1, 1, 1, 2, 2, 2, 2, 0])
    assert metrics["disconnected_communities"] == 1
    lonely = partition_metrics(g, [0, 0, 0, 0, 0, 1, 1, 1, 1, 2])
    assert lonely["singletons"] == 1


def test_fr06_leiden_communities_are_internally_connected() -> None:
    g = planted()
    assert partition_metrics(g, run_leiden(g, 42))["disconnected_communities"] == 0


def test_fr06_all_finite_rejects_nan() -> None:
    assert not all_finite({"modularity": math.nan})
    assert not all_finite({"modularity": math.inf})
