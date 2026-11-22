"""Dataset download, verification and preparation (FR-12, DR-07).

Every dataset is prepared once into a compressed .npz (edge list plus ground
truth) so each benchmark child process only has to load it.
"""

import gzip
import hashlib
import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import yaml

REGISTRY_PATH = Path(__file__).with_name("datasets.yaml")
LFR_MAX_RETRIES = 10


def data_dir() -> Path:
    configured = os.environ.get("QAUYM_DATA_DIR")
    if configured:
        return Path(configured)
    mounted = Path("/data")
    return mounted if mounted.is_dir() else Path(__file__).resolve().parents[2] / "data"


def load_registry() -> list[dict[str, Any]]:
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))["datasets"]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DatasetError(RuntimeError):
    pass


def ensure_files(download: bool = True) -> list[Path]:
    """Download missing files into data/raw/ and verify every checksum."""
    raw = data_dir() / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    paths = []
    for dataset in load_registry():
        for spec in dataset["files"]:
            path = raw / spec["filename"]
            if not path.exists():
                if not download:
                    raise DatasetError(f"{path} is missing. Run `make data`.")
                print(f"downloading {spec['url']}")
                try:
                    request = urllib.request.Request(spec["url"], headers={"User-Agent": "qauym"})
                    with urllib.request.urlopen(request, timeout=60) as res:
                        path.write_bytes(res.read())
                except OSError as exc:
                    raise DatasetError(
                        f"Could not download {spec['url']} ({exc}). "
                        f"Download it by hand and place it at {path}."
                    ) from exc
            actual = sha256_of(path)
            if actual != spec["sha256"]:
                raise DatasetError(
                    f"Checksum mismatch for {path}: expected {spec['sha256']}, got {actual}. "
                    "Delete the file and run `make data` again."
                )
            print(f"verified {spec['filename']} sha256={actual[:16]}...")
            paths.append(path)
    return paths


@dataclass
class Prepared:
    name: str
    path: Path
    nodes: int
    edges: int
    has_truth: bool
    meta: dict[str, Any]


def _save(
    name: str, cache: Path, n: int, edges: np.ndarray, truth: np.ndarray, meta: dict
) -> Prepared:
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, n=n, edges=edges, truth=truth, meta=json.dumps(meta))
    return Prepared(name, cache, n, len(edges), True, meta)


def _load_cached(name: str, cache: Path) -> Prepared:
    with np.load(cache) as z:
        return Prepared(name, cache, int(z["n"]), len(z["edges"]), True, json.loads(str(z["meta"])))


def prepare_lfr(name: str, params: dict[str, Any]) -> Prepared:
    key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
    cache = data_dir() / "cache" / f"lfr_{key}.npz"
    if cache.exists():
        return _load_cached(name, cache)

    args = dict(params)
    requested_seed = args.pop("seed")
    graph = None
    for attempt in range(LFR_MAX_RETRIES + 1):
        seed = requested_seed + attempt
        try:
            graph = nx.LFR_benchmark_graph(seed=seed, **args)
            break
        except nx.ExceededMaxIterations:
            continue
    if graph is None:
        raise DatasetError(f"LFR generation did not converge for {params}")

    graph.remove_edges_from(list(nx.selfloop_edges(graph)))
    n = graph.number_of_nodes()
    # Each node's `community` attribute is the set of its members; label by smallest member.
    labels = {v: min(graph.nodes[v]["community"]) for v in graph}
    remap = {label: i for i, label in enumerate(sorted(set(labels.values())))}
    truth = np.array([remap[labels[v]] for v in range(n)], dtype=np.int64)
    edges = np.array(sorted((min(u, v), max(u, v)) for u, v in graph.edges()), dtype=np.int64)
    meta = {"kind": "lfr", "params": params, "seed_requested": requested_seed, "seed_used": seed}
    return _save(name, cache, n, edges, truth, meta)


def prepare_email_eu_core(name: str) -> Prepared:
    cache = data_dir() / "cache" / "email_eu_core.npz"
    if cache.exists():
        return _load_cached(name, cache)
    ensure_files(download=False)
    raw = data_dir() / "raw"
    with gzip.open(raw / "email-Eu-core.txt.gz", "rt") as fh:
        directed = np.loadtxt(fh, dtype=np.int64)
    with gzip.open(raw / "email-Eu-core-department-labels.txt.gz", "rt") as fh:
        labels = np.loadtxt(fh, dtype=np.int64)

    n = int(labels[:, 0].max()) + 1
    truth = np.zeros(n, dtype=np.int64)
    truth[labels[:, 0]] = labels[:, 1]
    no_loops = directed[directed[:, 0] != directed[:, 1]]
    undirected = np.unique(np.sort(no_loops, axis=1), axis=0)
    meta = {
        "kind": "email_eu_core",
        "directed_edges": int(len(directed)),
        "self_loops_dropped": int(len(directed) - len(no_loops)),
        "departments": int(len(np.unique(truth))),
    }
    return _save(name, cache, n, undirected, truth, meta)


def prepare(spec: dict[str, Any]) -> Prepared:
    if spec["kind"] == "lfr":
        return prepare_lfr(spec["name"], spec["params"])
    if spec["kind"] == "email_eu_core":
        return prepare_email_eu_core(spec["name"])
    raise DatasetError(f"Unknown dataset kind: {spec['kind']}")
