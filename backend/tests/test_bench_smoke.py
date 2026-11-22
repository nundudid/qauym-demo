"""FR-12: the benchmark harness runs end to end on a 200-node LFR graph in under 30 s."""

import json
import time
from pathlib import Path

import pytest

from bench.cli import main
from bench.report import COLUMNS

SMOKE_CONFIG = Path(__file__).resolve().parent.parent / "bench" / "configs" / "smoke.yaml"


def test_fr12_smoke_run_writes_the_results_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QAUYM_DATA_DIR", str(tmp_path / "data"))
    out = tmp_path / "bench"
    started = time.perf_counter()
    assert main(["run", "--config", str(SMOKE_CONFIG), "--out", str(out)]) == 0
    assert main(["report", str(out)]) == 0
    assert time.perf_counter() - started < 30

    runs = [json.loads(line) for line in (out / "runs.jsonl").read_text().splitlines()]
    assert {r["method"] for r in runs} == {"leiden", "louvain"}
    for run in runs:
        assert run["nodes"] == 200
        assert 0 <= run["nmi"] <= 1
        assert run["runtime_s"] > 0 and run["peak_mem_mb"] > 0
        assert run["dataset_meta"]["seed_used"] >= run["dataset_meta"]["seed_requested"]
    # On an easy graph (mu = 0.1) Leiden must recover the planted communities well.
    assert next(r for r in runs if r["method"] == "leiden")["nmi"] > 0.8

    header = (out / "results.md").read_text(encoding="utf-8").splitlines()[0]
    assert [c.strip() for c in header.strip("|").split("|")] == COLUMNS
    assert (out / "results.csv").exists()
    assert (out / "fig7_bench.png").stat().st_size > 10_000
    hardware = json.loads((out / "hardware.json").read_text())
    assert {
        "cpu_model",
        "cores_logical",
        "ram_gb",
        "os",
        "python",
        "igraph",
        "leidenalg",
        "networkx",
        "git_commit",
    } <= set(hardware)
