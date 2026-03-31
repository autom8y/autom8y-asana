#!/usr/bin/env python3
"""Aegis CI threshold enforcement.

Parses aegis-report.json and exits non-zero if any of:
  - memory.regressions is non-empty
  - total RSS growth exceeds budget_mb (200 MB)
  - any operation has outcome == "FAILED"

Designed to run as a standalone script with zero additional dependencies
(stdlib only).

Usage:
    python scripts/aegis-check.py [path/to/aegis-report.json]

Exit codes:
    0  All checks pass
    1  One or more checks failed
    2  Report file missing or malformed
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def load_report(path: Path) -> dict:
    """Load and minimally validate the aegis report."""
    if not path.exists():
        print(f"ERROR: Report not found at {path}", file=sys.stderr)
        sys.exit(2)
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Could not parse report: {exc}", file=sys.stderr)
        sys.exit(2)

    for required in ("coverage", "memory", "total_operations"):
        if required not in data:
            print(f"ERROR: Report missing required key '{required}'", file=sys.stderr)
            sys.exit(2)

    return data


def check_report(report: dict) -> tuple[bool, list[str]]:
    """Run all checks against the report.

    Returns (passed, details) where details contains human-readable
    failure descriptions when passed is False.
    """
    failures: list[str] = []

    # --- Check 1: regressions ---
    memory = report["memory"]
    regressions = memory.get("regressions", [])
    if regressions:
        for reg in regressions:
            endpoint = reg.get("endpoint", "unknown")
            reason = reg.get("reason", "no reason given")
            failures.append(f"{endpoint}: {reason}")

    # --- Check 2: total RSS growth vs budget ---
    total_growth = memory.get("total_growth_mb", 0.0)
    # The conftest emits "budget_mb"; older reports may use "max_rss_growth_mb"
    budget = memory.get("budget_mb") or memory.get("max_rss_growth_mb") or 200
    if total_growth > budget:
        failures.append(
            f"Total RSS growth {total_growth:.1f}MB exceeds {budget}MB budget"
        )

    # --- Check 3: any FAILED operations ---
    coverage = report["coverage"]
    failed_count = coverage.get("failed", 0)
    if failed_count > 0:
        failed_ops = [
            op for op in report.get("operations", [])
            if op.get("outcome") == "FAILED"
        ]
        for op in failed_ops:
            method = op.get("method", "?")
            path = op.get("path", "?")
            status = op.get("status", "?")
            failures.append(f"{method} {path} returned {status}")

    return (len(failures) == 0, failures)


def format_summary(report: dict, passed: bool, failures: list[str]) -> str:
    """Format the human-readable summary for CI logs."""
    coverage = report["coverage"]
    memory = report["memory"]
    schema = report.get("schema_validation", {})
    total_ops = report.get("total_operations", 0)
    budget = memory.get("budget_mb") or memory.get("max_rss_growth_mb") or 200

    lines = [
        "Aegis Synthetic Coverage Report",
        "=" * 40,
        (
            f"Operations: {total_ops} total, "
            f"{coverage.get('passed', 0)} PASSED, "
            f"{coverage.get('expected_5xx', 0)} EXPECTED-5xx, "
            f"{coverage.get('failed', 0)} FAILED"
        ),
        f"Coverage:   {coverage.get('active_coverage_pct', 0)}% active",
        (
            f"Memory:     Total RSS growth: "
            f"{memory.get('total_growth_mb', 0):.1f}MB / {budget}MB budget"
        ),
        (
            f"Regressions: "
            f"{len(memory.get('regressions', []))} endpoints above threshold"
        ),
        (
            f"Schema:     "
            f"{schema.get('checked', 0)} validated, "
            f"{schema.get('invalid', 0)} invalid (spec drift)"
        ),
        "",
    ]

    if passed:
        lines.append("RESULT: PASS")
    else:
        lines.append("RESULT: FAIL")
        for detail in failures:
            lines.append(f"  - {detail}")

    return "\n".join(lines)


def format_step_summary(report: dict, passed: bool, failures: list[str]) -> str:
    """Format GitHub Actions job summary (markdown)."""
    coverage = report["coverage"]
    memory = report["memory"]
    schema = report.get("schema_validation", {})
    total_ops = report.get("total_operations", 0)
    budget = memory.get("budget_mb") or memory.get("max_rss_growth_mb") or 200
    regressions = memory.get("regressions", [])

    status_icon = "PASS" if passed else "FAIL"

    lines = [
        f"## Aegis Synthetic Coverage Report -- {status_icon}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Operations | {total_ops} |",
        f"| Active Coverage | {coverage.get('active_coverage_pct', 0)}% |",
        f"| PASSED | {coverage.get('passed', 0)} |",
        f"| EXPECTED-5xx | {coverage.get('expected_5xx', 0)} |",
        f"| FAILED | {coverage.get('failed', 0)} |",
        f"| RSS Growth | {memory.get('total_growth_mb', 0):.1f}MB / {budget}MB |",
        f"| Regressions | {len(regressions)} |",
        f"| Schema Checked | {schema.get('checked', 0)} |",
        f"| Schema Invalid | {schema.get('invalid', 0)} |",
        "",
    ]

    # Per-category breakdown
    per_category = memory.get("per_category", {})
    if per_category:
        lines.append("<details>")
        lines.append("<summary>Per-category breakdown</summary>")
        lines.append("")
        lines.append("| Category | Ops | RSS Delta |")
        lines.append("|----------|-----|-----------|")
        for cat, info in sorted(per_category.items()):
            lines.append(
                f"| {cat} | {info.get('operations', 0)} | "
                f"{info.get('delta_mb', 0):.1f}MB |"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if not passed:
        lines.append("> **BLOCKED**: Aegis regression detected. Details:")
        lines.append(">")
        for detail in failures:
            lines.append(f"> - {detail}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("aegis-report.json")
    report = load_report(report_path)

    passed, failures = check_report(report)

    # Print human-readable summary to stdout (visible in CI logs)
    print(format_summary(report, passed, failures))

    # Write GitHub Actions step summary if running in CI
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(format_step_summary(report, passed, failures))

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
