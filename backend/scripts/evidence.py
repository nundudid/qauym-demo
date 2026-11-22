"""Write evidence/tests.md and evidence/SUMMARY.md from the raw test outputs (SPEC Section 10).

`make evidence` runs the test suites first; they leave machine-readable results
in evidence/raw/. This script only reads those files and reports what they say:
a suite whose output is missing is reported as "not run", never as passed.
"""

import json
import os
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EVIDENCE = Path(os.environ.get("EVIDENCE_DIR", "/evidence"))
RAW = EVIDENCE / "raw"

EXPECTED_FILES = {
    "screenshots/fig5_login.png": "Figure 5 (M0)",
    "screenshots/fig6_feed.png": "Figure 6 (M0)",
    "screenshots/fig6_feed_mobile.png": "Figure 6 at 375 px (M0)",
    "bench/fig7_bench.png": "Figure 7 (M0)",
    "bench/results.md": "Table 4.2 (M0)",
    "bench/results.csv": "Table 4.2 data (M0)",
    "bench/hardware.json": "Benchmark hardware (M0)",
    "screenshots/communities.png": "My communities (M1)",
    "screenshots/community_detail.png": "Community detail (M1)",
    "screenshots/communities_empty.png": "Empty state (M1)",
    "screenshots/admin_runs.png": "Admin runs (M1)",
    "tests.md": "Test summary",
}


def backend_results() -> dict[str, Any] | None:
    path = RAW / "backend-junit.xml"
    if not path.exists():
        return None
    suite = ET.parse(path).getroot()
    suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
    assert suite is not None
    total = int(suite.get("tests", 0))
    failed = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
    skipped = int(suite.get("skipped", 0))
    by_file: dict[str, list[int]] = {}
    for case in suite.iter("testcase"):
        name = case.get("classname", "").split(".")[-1]
        bad = case.find("failure") is not None or case.find("error") is not None
        entry = by_file.setdefault(name, [0, 0])
        entry[0] += 1
        entry[1] += 0 if bad else 1
    return {
        "total": total,
        "failed": failed,
        "skipped": skipped,
        "passed": total - failed - skipped,
        "seconds": float(suite.get("time", 0)),
        "by_file": by_file,
    }


def coverage() -> dict[str, float] | None:
    path = RAW / "backend-coverage.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    packages: dict[str, list[int]] = {}
    for filename, info in data["files"].items():
        package = filename.split("/")[0]
        entry = packages.setdefault(package, [0, 0])
        entry[0] += info["summary"]["covered_lines"]
        entry[1] += info["summary"]["num_statements"]
    out = {name: 100 * c / n for name, (c, n) in packages.items() if n}
    out["total"] = data["totals"]["percent_covered"]
    return out


def vitest_results() -> dict[str, int] | None:
    path = RAW / "frontend-unit.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return {
        "total": data["numTotalTests"],
        "passed": data["numPassedTests"],
        "failed": data["numFailedTests"],
    }


def playwright_results() -> dict[str, Any] | None:
    path = RAW / "e2e.json"
    if not path.exists():
        return None
    stats = json.loads(path.read_text())["stats"]
    passed, failed = stats["expected"], stats["unexpected"] + stats.get("flaky", 0)
    return {"total": passed + failed + stats["skipped"], "passed": passed, "failed": failed}


def row(name: str, result: dict[str, Any] | None) -> str:
    if result is None:
        return f"| {name} | not run | – | – | – |"
    rate = 100 * result["passed"] / result["total"] if result["total"] else 0
    return f"| {name} | {result['total']} | {result['passed']} | {result['failed']} | {rate:.0f}% |"


REQUIREMENT_TESTS = [
    ("FR-01", "test_auth"),
    ("FR-02", "test_profile_privacy"),
    ("FR-03", "test_social_uniqueness"),
    ("FR-04", "test_idempotency"),
    ("FR-05", "test_snapshot_builder"),
    ("FR-06, FR-12", "test_detectors"),
    ("FR-12", "test_bench_smoke"),
    ("FR-07, NFR-05", "test_publication_failure"),
    ("FR-08", "test_communities_me"),
    ("DR-07 (seed)", "test_seed_demo"),
]


def tests_markdown(commit: str, when: str) -> str:
    backend, unit, e2e, cov = backend_results(), vitest_results(), playwright_results(), coverage()
    lines = [
        "# Test summary",
        "",
        f"Commit `{commit}`, generated {when} by `make evidence`.",
        "",
        "| Suite | Tests | Passed | Failed | Pass rate |",
        "| --- | --- | --- | --- | --- |",
        row("Backend (pytest, real PostgreSQL)", backend),
        row("Frontend unit (vitest)", unit),
        row("End to end (Playwright, Chromium)", e2e),
        "",
        "## Backend coverage",
        "",
    ]
    if cov is None:
        lines.append("Not measured in this run.")
    else:
        lines += ["| Package | Line coverage |", "| --- | --- |"]
        lines += [
            f"| `backend/{name}` | {pct:.1f}% |"
            for name, pct in sorted(cov.items())
            if name != "total"
        ]
        lines.append(f"| **Total** | **{cov['total']:.1f}%** |")
    lines += ["", "## Requirement to test file", ""]
    if backend is None:
        lines.append("Backend tests were not run.")
    else:
        lines += ["| Requirement | Test file | Tests | Passed |", "| --- | --- | --- | --- |"]
        for requirement, name in REQUIREMENT_TESTS:
            total, passed = backend["by_file"].get(name, [0, 0])
            lines.append(f"| {requirement} | `tests/{name}.py` | {total} | {passed} |")
        lines.append("| Core flow | `frontend/e2e/core-flow.spec.ts` | see end-to-end row | |")
    lines += [
        "",
        "CI: `.github/workflows/ci.yml` runs the same suites on every pull request. "
        "Add the link to the latest CI run here once the branch is pushed.",
        "",
    ]
    return "\n".join(lines)


def summary_markdown(commit: str, when: str) -> str:
    backend, unit, e2e = backend_results(), vitest_results(), playwright_results()
    lines = [
        "# Evidence summary",
        "",
        f"- Commit: `{commit}`",
        f"- Generated: {when}",
        "- Data: synthetic demo accounts only (`is_synthetic = true`); benchmark datasets are "
        "listed in `backend/bench/datasets.yaml` and never enter the app database.",
        "",
        "## Files",
        "",
        "| File | Report use | Present |",
        "| --- | --- | --- |",
    ]
    missing = []
    for name, use in EXPECTED_FILES.items():
        present = (EVIDENCE / name).exists() or name == "tests.md"
        if not present:
            missing.append(name)
        lines.append(f"| `evidence/{name}` | {use} | {'yes' if present else '**missing**'} |")

    lines += ["", "## Open issues", ""]
    issues = [f"`evidence/{name}` was not produced." for name in missing]
    for label, result in (("Backend", backend), ("Frontend unit", unit), ("End-to-end", e2e)):
        if result is None:
            issues.append(f"{label} tests were not run.")
        elif result["failed"]:
            issues.append(f"{label} tests: {result['failed']} of {result['total']} failed.")
    if commit in ("dev", "unknown", ""):
        issues.append("The commit is not recorded: run `make evidence` from a git checkout.")
    lines += [f"- {issue}" for issue in issues] or ["- None found by this run."]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    commit = os.environ.get("GIT_SHA", "unknown")
    when = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "tests.md").write_text(tests_markdown(commit, when), encoding="utf-8")
    (EVIDENCE / "SUMMARY.md").write_text(summary_markdown(commit, when), encoding="utf-8")
    print(f"wrote {EVIDENCE / 'tests.md'} and {EVIDENCE / 'SUMMARY.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
