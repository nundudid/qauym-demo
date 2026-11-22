"""Partition quality metrics recorded for every run (SPEC Section 6.2)."""

import math
from pathlib import Path
from typing import Any

import igraph as ig
import numpy as np


def partition_metrics(g: ig.Graph, membership: list[int]) -> dict[str, Any]:
    m = np.asarray(membership, dtype=np.int64)
    k = int(m.max()) + 1 if m.size else 0
    sizes = np.bincount(m, minlength=k)

    edges = np.asarray(g.get_edgelist(), dtype=np.int64).reshape(-1, 2)
    w = np.asarray(g.es["weight"], dtype=float) if g.ecount() else np.zeros(0)
    cu, cv = m[edges[:, 0]], m[edges[:, 1]]
    internal = cu == cv
    total = float(w.sum())

    # Conductance of S = cut(S) / min(vol(S), vol(V \ S)), averaged over communities.
    volume = np.bincount(cu, weights=w, minlength=k) + np.bincount(cv, weights=w, minlength=k)
    cross = ~internal
    cut = np.bincount(cu[cross], weights=w[cross], minlength=k) + np.bincount(
        cv[cross], weights=w[cross], minlength=k
    )
    denom = np.minimum(volume, 2 * total - volume)
    conductance = np.divide(cut, denom, out=np.zeros(k), where=denom > 0)

    return {
        "modularity": float(g.modularity(membership, weights="weight")) if g.ecount() else 0.0,
        "n_communities": k,
        "size_min": int(sizes.min()) if k else 0,
        "size_median": float(np.median(sizes)) if k else 0.0,
        "size_max": int(sizes.max()) if k else 0,
        "singletons": int((sizes == 1).sum()),
        "mean_conductance": float(conductance.mean()) if k else 0.0,
        "coverage": float(w[internal].sum() / total) if total > 0 else 0.0,
        "disconnected_communities": count_disconnected(g, m, np.flatnonzero(cross)),
    }


def count_disconnected(g: ig.Graph, membership: np.ndarray, cross_edge_ids: np.ndarray) -> int:
    """Communities whose members are not all reachable from each other inside the community."""
    inside = g.copy()
    inside.delete_edges(cross_edge_ids.tolist())
    components = np.asarray(inside.connected_components().membership, dtype=np.int64)
    pairs = np.unique(np.stack([membership, components], axis=1), axis=0)
    parts_per_community = np.bincount(pairs[:, 0])
    return int((parts_per_community > 1).sum())


def all_finite(metrics: dict[str, Any]) -> bool:
    return all(math.isfinite(v) for v in metrics.values() if isinstance(v, int | float))


def peak_rss_mb() -> float:
    """Peak resident memory of this process in MiB.

    Linux carries `ru_maxrss` across exec, so in a spawned child it starts at the
    parent's size and over-reports. VmHWM belongs to the new address space and is
    this process's own peak, so prefer it and fall back to getrusage (D-012).
    """
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) / 1024  # reported in KiB
    except OSError:
        pass
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
