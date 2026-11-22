"""`python -m bench data | run | report` (SPEC Section 7)."""

import argparse
import json
import multiprocessing as mp
import os
import platform
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

# Heavy libraries (pandas, networkx, scikit-learn, matplotlib) are imported inside the
# functions that need them: a spawned child re-imports this module, and it should load
# only numpy, igraph and leidenalg so its start-up time and peak memory stay small.
CHILD_TIMEOUT_S = 600


def _child(conn: Any, npz_path: str, method: str, seed: int) -> None:
    """One (dataset, method, seed) in a fresh process, so peak memory is its own."""
    import numpy as np

    from analytics.detectors import DETECTORS, build_graph
    from analytics.metrics import partition_metrics, peak_rss_mb

    t0 = time.perf_counter()
    with np.load(npz_path) as z:
        n, edges = int(z["n"]), z["edges"]
    g = build_graph(n, edges.tolist())
    load_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    membership = DETECTORS[method](g, seed)
    runtime_s = time.perf_counter() - t0  # only the detection call is timed

    peak_mb = peak_rss_mb()  # read straight after detection

    metrics = partition_metrics(g, membership)
    conn.send(
        {
            "load_s": load_s,
            "runtime_s": runtime_s,
            "peak_mem_mb": peak_mb,
            "modularity": metrics["modularity"],
            "n_communities": metrics["n_communities"],
            "disconnected_communities": metrics["disconnected_communities"],
            "membership": membership,
        }
    )
    conn.close()


def run_one(npz_path: Path, method: str, seed: int) -> dict[str, Any]:
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_child, args=(child, str(npz_path), method, seed))
    proc.start()
    child.close()
    try:
        if not parent.poll(CHILD_TIMEOUT_S):
            raise RuntimeError(f"{method} seed {seed} timed out")
        return parent.recv()
    except EOFError:
        raise RuntimeError(f"{method} seed {seed} crashed (exit {proc.exitcode})") from None
    finally:
        proc.join(5)
        if proc.is_alive():
            proc.kill()


def hardware() -> dict[str, Any]:
    import psutil

    cpu = platform.processor()
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {
        "cpu_model": cpu,
        "cores_physical": psutil.cpu_count(logical=False),
        "cores_logical": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / 2**30, 1),
        "os": platform.platform(),
        "in_container": Path("/.dockerenv").exists(),
        "python": platform.python_version(),
        "igraph": version("igraph"),
        "leidenalg": version("leidenalg"),
        "networkx": version("networkx"),
        "git_commit": os.environ.get("GIT_SHA", "unknown"),
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def cmd_run(config_path: Path, out: Path) -> int:
    import numpy as np
    import yaml
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    from bench import datasets

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    for spec in config["datasets"]:
        t0 = time.perf_counter()
        prepared = datasets.prepare(spec)
        print(
            f"{prepared.name}: {prepared.nodes} nodes, {prepared.edges} edges "
            f"(prepared in {time.perf_counter() - t0:.1f}s)",
            flush=True,
        )
        with np.load(prepared.path) as z:
            truth = z["truth"]
        for method in config["methods"]:
            for seed in config["seeds"]:
                result = run_one(prepared.path, method, seed)
                membership = result.pop("membership")
                result["nmi"] = float(normalized_mutual_info_score(truth, membership))
                result["ari"] = float(adjusted_rand_score(truth, membership))
                rows.append(
                    {
                        "dataset": prepared.name,
                        "nodes": prepared.nodes,
                        "edges": prepared.edges,
                        "method": method,
                        "seed": seed,
                        "dataset_meta": prepared.meta,
                        **result,
                    }
                )
            done = [r for r in rows if r["dataset"] == prepared.name and r["method"] == method]
            print(
                f"  {method}: NMI {sum(r['nmi'] for r in done) / len(done):.3f}, "
                f"{sum(r['runtime_s'] for r in done) / len(done) * 1000:.1f} ms/run",
                flush=True,
            )
    (out / "runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    info = hardware()
    info["config"] = str(config_path)
    info["total_wall_s"] = round(time.perf_counter() - started, 1)
    (out / "hardware.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} runs to {out} in {info['total_wall_s']}s")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bench")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("data", help="download datasets into data/raw/ and verify checksums")
    run = sub.add_parser("run", help="run every (dataset, method, seed) combination")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--out", type=Path, required=True)
    ensure = sub.add_parser("ensure", help="run and report only if results.md is missing")
    ensure.add_argument("--config", type=Path, required=True)
    ensure.add_argument("--out", type=Path, required=True)
    report = sub.add_parser("report", help="write results.md, results.csv and fig7_bench.png")
    report.add_argument("out", type=Path)
    args = parser.parse_args(argv)

    from bench import datasets

    try:
        if args.command == "data":
            datasets.ensure_files()
            return 0
        if args.command == "ensure":
            from bench.report import write_report

            if (args.out / "results.md").exists():
                print(f"{args.out / 'results.md'} exists; skipping the benchmark")
                return 0
            datasets.ensure_files()
            cmd_run(args.config, args.out)
            write_report(args.out)
            return 0
        if args.command == "run":
            return cmd_run(args.config, args.out)
        from bench.report import write_report

        write_report(args.out)
        return 0
    except datasets.DatasetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
