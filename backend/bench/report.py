"""Turn runs.jsonl into results.md, results.csv and fig7_bench.png (report Table 4.2, Figure 7)."""

import json
from pathlib import Path

import pandas as pd

COLUMNS = [
    "Dataset",
    "Nodes",
    "Edges",
    "Method",
    "Modularity",
    "NMI",
    "ARI",
    "Runtime (s)",
    "Peak memory (MB)",
]
METHOD_LABEL = {"leiden": "Leiden", "louvain": "Louvain"}
# Fixed categorical order: Leiden is always blue, Louvain always orange.
METHOD_COLOR = {"leiden": "#2a78d6", "louvain": "#eb6834"}
SURFACE, TEXT, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"


def load_runs(out: Path) -> pd.DataFrame:
    rows = [json.loads(line) for line in (out / "runs.jsonl").read_text().splitlines() if line]
    return pd.DataFrame(rows)


def summarise(runs: pd.DataFrame) -> pd.DataFrame:
    order = {name: i for i, name in enumerate(runs["dataset"].drop_duplicates())}
    grouped = runs.groupby(["dataset", "nodes", "edges", "method"], sort=False)
    summary = grouped.agg(
        seeds=("seed", "count"),
        modularity_mean=("modularity", "mean"),
        modularity_std=("modularity", "std"),
        nmi_mean=("nmi", "mean"),
        nmi_std=("nmi", "std"),
        ari_mean=("ari", "mean"),
        ari_std=("ari", "std"),
        runtime_s_mean=("runtime_s", "mean"),
        runtime_s_std=("runtime_s", "std"),
        peak_mem_mb_mean=("peak_mem_mb", "mean"),
        peak_mem_mb_std=("peak_mem_mb", "std"),
    ).reset_index()
    summary = summary.fillna(0.0)  # std of a single seed
    summary["_order"] = summary["dataset"].map(order)
    return summary.sort_values(["_order", "method"]).drop(columns="_order").reset_index(drop=True)


def _pm(mean: float, std: float, digits: int) -> str:
    return f"{mean:.{digits}f} ± {std:.{digits}f}"


def results_markdown(summary: pd.DataFrame) -> str:
    lines = ["| " + " | ".join(COLUMNS) + " |", "| " + " | ".join("---" for _ in COLUMNS) + " |"]
    for r in summary.itertuples():
        cells = [
            r.dataset,
            f"{r.nodes:,}",
            f"{r.edges:,}",
            METHOD_LABEL.get(r.method, r.method),
            _pm(r.modularity_mean, r.modularity_std, 3),
            _pm(r.nmi_mean, r.nmi_std, 3),
            _pm(r.ari_mean, r.ari_std, 3),
            _pm(r.runtime_s_mean, r.runtime_s_std, 4),
            _pm(r.peak_mem_mb_mean, r.peak_mem_mb_std, 1),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    seeds = int(summary["seeds"].max())
    note = (
        f"\nMean ± standard deviation over {seeds} detector seed(s). Runtime covers the "
        "detection call only. Peak memory is the child process's peak resident set size "
        "after loading the graph and running detection.\n"
    )
    return "\n".join(lines) + "\n" + note


def write_figure(summary: pd.DataFrame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(summary["dataset"].drop_duplicates())
    methods = [m for m in METHOD_LABEL if m in set(summary["method"])]
    width = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for i, method in enumerate(methods):
        rows = summary[summary["method"] == method].set_index("dataset").reindex(names)
        xs = [x + (i - (len(methods) - 1) / 2) * (width + 0.03) for x in range(len(names))]
        bars = ax.bar(
            xs,
            rows["nmi_mean"],
            width,
            yerr=rows["nmi_std"],
            color=METHOD_COLOR[method],
            label=METHOD_LABEL[method],
            error_kw={"ecolor": MUTED, "elinewidth": 1, "capsize": 3},
            zorder=3,
        )
        for bar, mean, std in zip(bars, rows["nmi_mean"], rows["nmi_std"], strict=True):
            ax.annotate(
                f"{mean:.2f}",
                (bar.get_x() + bar.get_width() / 2, mean + std),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                color=TEXT,
            )
    ax.set_xticks(range(len(names)), [n.replace("mu=", "μ = ") for n in names])
    ax.set_ylim(0, 1.12)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("NMI against ground truth", color=MUTED)
    ax.set_title(
        "Agreement with ground-truth communities: Leiden vs Louvain",
        loc="left",
        fontsize=12,
        color=TEXT,
        pad=24,
    )
    seeds = int(summary["seeds"].max())
    ax.text(
        0,
        1.035,
        f"Normalised mutual information, mean of {seeds} seeds; error bars show ± 1 SD",
        transform=ax.transAxes,
        fontsize=9,
        color=MUTED,
    )
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(colors=MUTED, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.98), labelcolor=TEXT)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def write_report(out: Path) -> None:
    summary = summarise(load_runs(out))
    (out / "results.md").write_text(results_markdown(summary), encoding="utf-8")
    summary.to_csv(out / "results.csv", index=False, float_format="%.6f")
    write_figure(summary, out / "fig7_bench.png")
    print(f"wrote results.md, results.csv and fig7_bench.png to {out}")
