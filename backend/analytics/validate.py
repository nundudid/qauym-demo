"""Checks a run must pass before it may be published (FR-07; SPEC Section 6.3)."""

from typing import Any

from analytics.metrics import all_finite
from app.models import AnalyticsRun, GraphSnapshot


def validate_run(
    run: AnalyticsRun,
    snapshot: GraphSnapshot,
    vertex_count: int,
    membership: list[int],
    metrics: dict[str, Any],
) -> list[str]:
    """Return the reasons the run is invalid; an empty list means it may be published."""
    errors: list[str] = []

    # 1. Every vertex in the snapshot graph has exactly one membership.
    if len(membership) != vertex_count or any(label is None for label in membership):
        errors.append(f"{len(membership)} memberships for {vertex_count} graph vertices")

    # 2. The membership count equals the snapshot's node count; labels are contiguous from 0.
    if len(membership) != snapshot.node_count:
        errors.append(
            f"{len(membership)} memberships but the snapshot has {snapshot.node_count} nodes"
        )
    labels = sorted({label for label in membership if label is not None})
    if labels != list(range(len(labels))):
        errors.append("community labels are not contiguous from 0")

    # 3. No metric is NaN or infinite.
    if not all_finite(metrics):
        errors.append("a metric is NaN or infinite")

    # 4. The Leiden result has zero internally disconnected communities.
    if run.algorithm == "leiden" and metrics.get("disconnected_communities", 0) != 0:
        errors.append(f"{metrics['disconnected_communities']} internally disconnected communities")

    # 5. Provenance is complete.
    provenance = {
        "snapshot id": run.snapshot_id,
        "code revision": run.code_revision,
        "config hash": snapshot.config_hash,
        "seed": run.seed,
        "duration": run.duration_ms,
    }
    errors.extend(f"missing {name}" for name, value in provenance.items() if value in (None, ""))
    return errors
