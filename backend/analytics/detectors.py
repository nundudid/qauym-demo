"""Community detectors shared by the app's analytics job and the benchmark harness (FR-06)."""

import random
from collections.abc import Callable

import igraph as ig
import leidenalg as la


def run_leiden(g: ig.Graph, seed: int) -> list[int]:
    part = la.find_partition(
        g, la.ModularityVertexPartition, weights="weight", n_iterations=-1, seed=seed
    )
    return list(part.membership)


def run_louvain(g: ig.Graph, seed: int) -> list[int]:
    random.seed(seed)
    ig.set_random_number_generator(random)  # makes multilevel reproducible
    return list(g.community_multilevel(weights="weight").membership)


DETECTORS: dict[str, Callable[[ig.Graph, int], list[int]]] = {
    "leiden": run_leiden,
    "louvain": run_louvain,
}


def build_graph(
    n: int, edges: list[tuple[int, int]], weights: list[float] | None = None
) -> ig.Graph:
    """Undirected weighted graph; unweighted inputs get weight 1.0 so one code path serves both."""
    g = ig.Graph(n=n, edges=edges, directed=False)
    g.es["weight"] = weights if weights is not None else [1.0] * len(edges)
    return g
