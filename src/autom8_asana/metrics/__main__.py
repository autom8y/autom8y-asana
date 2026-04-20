"""CLI entry point for metrics computation.

Usage:
    python -m autom8_asana.metrics active_mrr
    python -m autom8_asana.metrics active_mrr --verbose
    python -m autom8_asana.metrics --list
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

# ---------------------------------------------------------------------------
# CLI preflight — Alternative C (TDD-0001-cli-preflight-contract, CFG-006)
# Subprocess-first (secretspec check --profile cli) with inline fallback when
# the binary is absent. Called inside main() immediately before load_project_dataframe.
# Exit code 2 distinguishes preflight contract violations from runtime errors (exit 1).
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

# Variables declared required=true under [profiles.cli] in secretspec.toml (ADR-0001).
# Keep in sync with secretspec.toml:[profiles.cli]. A companion test asserts parity.
_CLI_REQUIRED = ("ASANA_CACHE_S3_BUCKET", "ASANA_CACHE_S3_REGION")


def _emit_preflight_error(missing: list[str]) -> None:
    """Write the structured actionable error to stderr. Does not exit."""
    root = _REPO_ROOT
    missing_lines = "\n".join(f"  - {v}" for v in missing)
    msg = f"""\
ERROR: CLI preflight failed — [profiles.cli] contract in secretspec.toml requires the following env var(s) but they are unset or empty:
{missing_lines}

This CLI entrypoint (python -m autom8_asana.metrics) runs under the 'cli' profile of secretspec.toml,
which is strict about S3 cache configuration. See:

  1. .env/defaults                (committed, Layer 3) — set committed project defaults here
     path: {root}/.env/defaults
  2. .env/local.example → .env/local  (example committed; .env/local is gitignored, Layer 5)
     path: {root}/.env/local.example
     copy: cp .env/local.example .env/local   # then edit .env/local with real values
  3. secretspec.toml              (the contract itself — declares which vars are required under --profile cli)
     path: {root}/secretspec.toml
     validate: secretspec check --config secretspec.toml --provider env --profile cli

Typical fix: ensure .env/defaults contains ASANA_CACHE_S3_BUCKET and ASANA_CACHE_S3_REGION,
then re-run 'direnv allow' (or source the env manually) and retry."""
    print(msg, file=sys.stderr)


def _preflight_inline_fallback() -> None:
    """Inline fallback when secretspec binary is absent. Checks _CLI_REQUIRED vars."""
    missing = [v for v in _CLI_REQUIRED if not os.environ.get(v)]
    if missing:
        _emit_preflight_error(missing)
        sys.exit(2)


def _preflight_cli_profile() -> None:
    """Run secretspec check --profile cli; fall back to inline check if binary missing.

    Silent on success. Writes actionable error to stderr and exits 2 on failure.
    See TDD-0001-cli-preflight-contract.md for the full behavioral specification.
    """
    secretspec_cmd = [
        "secretspec",
        "check",
        "--config",
        str(_REPO_ROOT / "secretspec.toml"),
        "--provider",
        "env",
        "--profile",
        "cli",
    ]
    try:
        result = subprocess.run(
            secretspec_cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, PermissionError):
        # secretspec binary unavailable — announce fallback and run inline check.
        print(
            "WARNING: secretspec binary not found; using inline preflight check.",
            file=sys.stderr,
        )
        _preflight_inline_fallback()
        return
    except subprocess.TimeoutExpired:
        # Treat timeout as binary unavailable; fall back rather than block startup.
        print(
            "WARNING: secretspec timed out; using inline preflight check.",
            file=sys.stderr,
        )
        _preflight_inline_fallback()
        return

    if result.returncode != 0:
        # secretspec reported a violation — extract missing var names from its stderr.
        # Fall back to the inline tuple if parsing produces an empty list.
        import re

        raw = result.stderr or ""
        found = re.findall(r"\b(ASANA_\w+|AUTOM8\w*)\b", raw)
        missing = found if found else list(_CLI_REQUIRED)
        _emit_preflight_error(missing)
        sys.exit(2)


def main() -> None:
    from autom8_asana.dataframes.offline import load_project_dataframe
    from autom8_asana.metrics.compute import compute_metric
    from autom8_asana.metrics.registry import MetricRegistry
    from autom8_asana.models.business.activity import CLASSIFIERS

    registry = MetricRegistry()

    parser = argparse.ArgumentParser(
        description="Compute metrics from cached Asana section data",
    )
    parser.add_argument(
        "metric",
        nargs="?",
        help="Metric name to compute (e.g., active_mrr, active_ad_spend)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show per-row breakdown",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_metrics",
        help="List all available metrics",
    )
    parser.add_argument(
        "--project-gid",
        help="Override project GID (default: resolved from metric entity type)",
    )
    args = parser.parse_args()

    # --list mode
    if args.list_metrics:
        names = registry.list_metrics()
        print("Available metrics:")
        for name in names:
            metric = registry.get_metric(name)
            print(f"  {name:25s} {metric.description}")
        return

    # Require metric name
    if not args.metric:
        parser.error("metric name is required (or use --list)")

    # Look up metric
    try:
        metric = registry.get_metric(args.metric)
    except KeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve project GID
    project_gid = args.project_gid
    if project_gid is None:
        classifier = CLASSIFIERS.get(metric.scope.entity_type)
        if classifier is None:
            print(
                f"ERROR: Cannot resolve project GID for entity type '{metric.scope.entity_type}'",
                file=sys.stderr,
            )
            sys.exit(1)
        project_gid = classifier.project_gid

    # CLI preflight — TDD-0001-cli-preflight-contract, CFG-006
    # Runs here: after arg parsing + cheap prerequisite checks, before any S3 call.
    # --list path is already gone (early return above); GID is resolved.
    _preflight_cli_profile()

    # Load data
    try:
        df = load_project_dataframe(project_gid)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(df)} rows from project {project_gid}")

    # Compute
    result = compute_metric(metric, df, verbose=args.verbose)

    # Aggregate
    agg_fn = getattr(result[metric.expr.column], metric.expr.agg)
    total = agg_fn()

    # Guard None: mean/min/max on empty DataFrame returns None
    if total is None:
        formatted = "N/A (no data)"
    elif metric.expr.agg == "count":
        formatted = f"{int(total):,}"
    else:
        # sum, mean, min, max on financial columns
        formatted = f"${total:,.2f}"

    if metric.scope.dedup_keys:
        dedup_desc = ", ".join(metric.scope.dedup_keys)
        print(f"Unique ({dedup_desc}) combos: {len(result)}")

    print(f"\n  {metric.name}: {formatted}")


if __name__ == "__main__":
    main()
