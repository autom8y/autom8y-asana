#!/usr/bin/env python3
"""Analyze pytest-json-report outputs to identify slow tests and generate profiling report.

Usage:
    python scripts/analyze_test_timings.py [--profiling-dir .profiling] [--output docs/test-profiling-report.md]
"""

import argparse
import json
import os
import re
import statistics
from collections import defaultdict
from pathlib import Path


def load_runs(profiling_dir: str) -> list[dict]:
    """Load all run*.json files from the profiling directory."""
    runs = []
    for path in sorted(Path(profiling_dir).glob("run*.json")):
        with open(path) as f:
            runs.append(json.load(f))
    return runs


def extract_timings(runs: list[dict]) -> dict[str, list[float]]:
    """Extract per-test call durations across all runs."""
    timings: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        for test in run.get("tests", []):
            nodeid = test["nodeid"]
            call = test.get("call", {})
            if call.get("outcome") in ("passed", "failed") and "duration" in call:
                timings[nodeid].append(call["duration"])
    return dict(timings)


def categorize(nodeid: str) -> str:
    """Categorize test by directory."""
    parts = nodeid.split("/")
    if len(parts) >= 2:
        cat = parts[1]  # tests/<category>/...
        if cat in ("unit", "api", "validation", "benchmarks"):
            return cat
    return "other"


def compute_stats(durations: list[float]) -> dict:
    """Compute summary statistics for a list of durations."""
    if not durations:
        return {}
    s = sorted(durations)
    n = len(s)
    return {
        "mean": statistics.mean(s),
        "median": statistics.median(s),
        "std": statistics.stdev(s) if n > 1 else 0.0,
        "min": s[0],
        "max": s[-1],
        "p90": s[int(n * 0.90)] if n >= 10 else s[-1],
        "p95": s[int(n * 0.95)] if n >= 20 else s[-1],
        "p99": s[int(n * 0.99)] if n >= 100 else s[-1],
        "count": n,
    }


def detect_root_causes(nodeid: str, repo_root: str) -> list[str]:
    """Grep the test file for common slow-test patterns."""
    filepath = nodeid.split("::")[0]
    full_path = os.path.join(repo_root, filepath)
    causes = []

    if not os.path.exists(full_path):
        return causes

    try:
        with open(full_path) as f:
            content = f.read()
    except Exception:
        return causes

    if re.search(r"time\.sleep|asyncio\.sleep", content):
        causes.append("sleep")
    if re.search(r"ThreadPoolExecutor|threading\.(Thread|Lock|Event)", content):
        causes.append("concurrency")
    if re.search(r"@pytest\.fixture.*scope\s*=\s*['\"]session['\"]", content):
        causes.append("session-fixture")
    if re.search(r"pl\.(DataFrame|LazyFrame|read_|scan_)", content):
        causes.append("dataframe-ops")
    if re.search(r"subprocess\.|os\.system", content):
        causes.append("subprocess")
    if re.search(r"httpx\.|requests\.|aiohttp\.", content):
        causes.append("http-client")
    if re.search(r"moto|mock_aws|mock_s3", content, re.IGNORECASE):
        causes.append("aws-mock")

    return causes


def generate_report(
    timings: dict[str, list[float]],
    repo_root: str,
    slow_threshold_ms: float = 500.0,
) -> str:
    """Generate markdown profiling report."""
    lines = []
    lines.append("# Test Suite Profiling Report\n")

    # Per-test mean durations
    test_means: dict[str, float] = {}
    for nodeid, durs in timings.items():
        test_means[nodeid] = statistics.mean(durs)

    # Overall stats
    all_means = list(test_means.values())
    overall = compute_stats(all_means)
    total_duration = sum(all_means)

    lines.append("## Summary\n")
    lines.append(f"- **Total tests**: {len(all_means)}")
    lines.append(f"- **Total duration (sum of means)**: {total_duration:.1f}s")
    lines.append(f"- **Mean per test**: {overall['mean']*1000:.1f}ms")
    lines.append(f"- **Median per test**: {overall['median']*1000:.1f}ms")
    lines.append(f"- **P90**: {overall['p90']*1000:.1f}ms")
    lines.append(f"- **P95**: {overall['p95']*1000:.1f}ms")
    lines.append(f"- **P99**: {overall['p99']*1000:.1f}ms")
    lines.append(f"- **Std dev**: {overall['std']*1000:.1f}ms")
    lines.append(f"- **Slow threshold**: {slow_threshold_ms}ms")
    lines.append("")

    # By category
    by_cat: dict[str, list[float]] = defaultdict(list)
    for nodeid, mean_dur in test_means.items():
        by_cat[categorize(nodeid)].append(mean_dur)

    lines.append("## By Category\n")
    lines.append("| Category | Count | Sum (s) | Mean (ms) | Median (ms) | P95 (ms) | Max (ms) |")
    lines.append("|----------|-------|---------|-----------|-------------|----------|----------|")
    for cat in sorted(by_cat.keys()):
        durs = by_cat[cat]
        cs = compute_stats(durs)
        lines.append(
            f"| {cat} | {cs['count']} | {sum(durs):.1f} | "
            f"{cs['mean']*1000:.1f} | {cs['median']*1000:.1f} | "
            f"{cs['p95']*1000:.1f} | {cs['max']*1000:.1f} |"
        )
    lines.append("")

    # Top 30 slowest tests
    sorted_tests = sorted(test_means.items(), key=lambda x: x[1], reverse=True)
    top_n = 30

    lines.append(f"## Top {top_n} Slowest Tests\n")
    lines.append("| # | Mean (ms) | Std (ms) | Root Causes | Test |")
    lines.append("|---|-----------|----------|-------------|------|")
    for i, (nodeid, mean_dur) in enumerate(sorted_tests[:top_n], 1):
        durs = timings[nodeid]
        std = statistics.stdev(durs) if len(durs) > 1 else 0.0
        causes = detect_root_causes(nodeid, repo_root)
        cause_str = ", ".join(causes) if causes else "-"
        lines.append(f"| {i} | {mean_dur*1000:.0f} | {std*1000:.0f} | {cause_str} | `{nodeid}` |")
    lines.append("")

    # Root cause breakdown
    cause_counts: dict[str, int] = defaultdict(int)
    cause_duration: dict[str, float] = defaultdict(float)
    slow_tests = [(n, m) for n, m in test_means.items() if m * 1000 >= slow_threshold_ms]

    for nodeid, mean_dur in slow_tests:
        causes = detect_root_causes(nodeid, repo_root)
        for c in causes:
            cause_counts[c] += 1
            cause_duration[c] += mean_dur

    lines.append("## Root Cause Breakdown (slow tests)\n")
    lines.append(f"Tests above {slow_threshold_ms}ms threshold: **{len(slow_tests)}**\n")
    lines.append("| Root Cause | Count | Total Duration (s) |")
    lines.append("|------------|-------|-------------------|")
    for cause in sorted(cause_counts.keys(), key=lambda c: cause_duration[c], reverse=True):
        lines.append(f"| {cause} | {cause_counts[cause]} | {cause_duration[cause]:.1f} |")
    lines.append("")

    # Marker recommendations
    lines.append("## Marker Recommendations\n")
    lines.append(f"Tests to mark `@pytest.mark.slow` (>{slow_threshold_ms}ms mean):\n")
    lines.append("```")
    for nodeid, mean_dur in sorted(slow_tests, key=lambda x: x[1], reverse=True):
        lines.append(f"  {mean_dur*1000:7.0f}ms  {nodeid}")
    lines.append("```\n")

    # File-level recommendations (group by file for efficient marking)
    slow_by_file: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for nodeid, mean_dur in slow_tests:
        filepath = nodeid.split("::")[0]
        slow_by_file[filepath].append((nodeid, mean_dur))

    lines.append("### By File (for applying markers)\n")
    for filepath in sorted(slow_by_file.keys()):
        tests = slow_by_file[filepath]
        total = sum(d for _, d in tests)
        lines.append(f"**{filepath}** ({len(tests)} slow tests, {total:.1f}s total)")
        for nodeid, dur in sorted(tests, key=lambda x: x[1], reverse=True):
            test_name = nodeid.split("::")[-1]
            lines.append(f"  - `{test_name}` ({dur*1000:.0f}ms)")
        lines.append("")

    # Estimated fast suite impact
    fast_tests = [(n, m) for n, m in test_means.items() if m * 1000 < slow_threshold_ms]
    fast_duration = sum(m for _, m in fast_tests)
    lines.append("## Estimated Fast Suite Impact\n")
    lines.append(f"- **Fast tests**: {len(fast_tests)} ({len(fast_tests)/len(all_means)*100:.1f}%)")
    lines.append(f"- **Slow tests**: {len(slow_tests)} ({len(slow_tests)/len(all_means)*100:.1f}%)")
    lines.append(f"- **Fast suite duration (sum of means)**: {fast_duration:.1f}s")
    lines.append(f"- **Slow tests duration (sum of means)**: {sum(m for _, m in slow_tests):.1f}s")
    lines.append(f"- **Duration reduction**: {(1 - fast_duration/total_duration)*100:.1f}%")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze pytest timing data")
    parser.add_argument("--profiling-dir", default=".profiling", help="Directory with run*.json files")
    parser.add_argument("--output", default="docs/test-profiling-report.md", help="Output report path")
    parser.add_argument("--threshold", type=float, default=500.0, help="Slow test threshold in ms")
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)

    runs = load_runs(args.profiling_dir)
    if not runs:
        print(f"No run*.json files found in {args.profiling_dir}")
        return

    print(f"Loaded {len(runs)} profiling runs")
    timings = extract_timings(runs)
    print(f"Extracted timings for {len(timings)} tests")

    report = generate_report(timings, repo_root, args.threshold)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        f.write(report)
    print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
