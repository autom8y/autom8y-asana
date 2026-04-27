"""CLI entry point for metrics computation.

Usage:
    python -m autom8_asana.metrics active_mrr
    python -m autom8_asana.metrics active_mrr --verbose
    python -m autom8_asana.metrics active_mrr --strict --staleness-threshold 6h
    python -m autom8_asana.metrics active_mrr --json
    python -m autom8_asana.metrics --list
"""

from __future__ import annotations

import argparse
import json
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
# Keep in sync with secretspec.toml:[profiles.cli]. See tests/unit/metrics/test_main.py::TestPreflightParity::test_inline_and_secretspec_enforce_same_required_vars.
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
    from autom8_asana.metrics.freshness import (
        FreshnessError,
        FreshnessReport,
        format_human_lines,
        format_json_envelope,
        format_warning,
        parse_duration_spec,
    )
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
    # ----- Freshness signal flags (PRD verify-active-mrr-provenance, ADR-001) -----
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Promote stale-threshold/IO/zero-result warnings to non-zero exit "
            "(PRD AC-2.3, AC-4.4, AC-5.2)."
        ),
    )
    parser.add_argument(
        "--staleness-threshold",
        default="6h",
        help=(
            "Maximum acceptable parquet age before WARNING fires. "
            "Duration spec: Ns/Nm/Nh/Nd. Default: 6h."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",  # 'json' is a stdlib module name; avoid attribute shadow
        help=(
            "Emit a single structured JSON envelope to stdout instead of "
            "human-readable lines (warnings still stderr)."
        ),
    )
    args = parser.parse_args()

    # Validate --staleness-threshold spec BEFORE any S3 work (TDD §3.2 step 1).
    try:
        threshold_seconds = parse_duration_spec(args.staleness_threshold)
    except ValueError as ve:
        print(f"ERROR: {ve}", file=sys.stderr)
        sys.exit(1)

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

    if not args.json_mode:
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

    if metric.scope.dedup_keys and not args.json_mode:
        dedup_desc = ", ".join(metric.scope.dedup_keys)
        print(f"Unique ({dedup_desc}) combos: {len(result)}")

    # Existing dollar-figure emission (preserved byte-for-byte under default mode
    # per PRD C-2 / SM-6). Suppressed under --json per AC-3.2.
    if not args.json_mode:
        print(f"\n  {metric.name}: {formatted}")

    # ----- Freshness signal (PRD verify-active-mrr-provenance, ADR-001) -----
    bucket = os.environ.get("ASANA_CACHE_S3_BUCKET")
    prefix = f"dataframes/{project_gid}/sections/"

    # Build the FreshnessReport. Map FreshnessError to AC-4.x stderr lines.
    try:
        # bucket may be None here only if the upstream load_project_dataframe
        # was satisfied through some other path (parameter override). The
        # preflight guarantees the env var is set for the standard CLI path.
        if not bucket:
            raise FreshnessError(
                FreshnessError.KIND_UNKNOWN,
                "<unset>",
                prefix,
                ValueError("ASANA_CACHE_S3_BUCKET unset at freshness probe time"),
            )
        report = FreshnessReport.from_s3_listing(
            bucket=bucket,
            prefix=prefix,
            threshold_seconds=threshold_seconds,
        )
    except FreshnessError as fe:
        _emit_freshness_io_error(fe)
        sys.exit(1)

    # Empty-prefix check: parquet_count == 0 is structurally an IO-layer failure.
    # Always exit 1 regardless of --strict (TDD §3.4).
    if report.parquet_count == 0:
        print(
            f"ERROR: no parquets found at s3://{report.bucket}/{report.prefix}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Detect zero-result-set: parquets present but compute pipeline yielded
    # zero rows. Distinct from empty-prefix per TDD §3.4 + latent #5.
    zero_result = len(result) == 0

    # ----- Output emission -----
    if args.json_mode:
        # JSON mode: single envelope to stdout; warnings/errors still stderr.
        # `value` is the computed metric float when the aggregation succeeded;
        # falls back to None for the "N/A (no data)" case.
        envelope_value: float | None = None if total is None else float(total)
        envelope = format_json_envelope(
            report=report,
            value=envelope_value,
            metric_name=metric.name,
            currency="USD",
            env="production",
            bucket_evidence="stakeholder-affirmation-2026-04-27",
        )
        print(json.dumps(envelope, sort_keys=True, indent=2))
    else:
        # Default mode: emit additive freshness lines per AC-1.2.
        for line in format_human_lines(report):
            print(line)

    # WARNING line (stderr) for stale data — both default and JSON modes.
    if report.stale:
        print(format_warning(report), file=sys.stderr)

    # Zero-result-set warning (stderr) — both default and JSON modes.
    if zero_result:
        print(
            f"WARNING: zero rows after filter+dedup for metric '{metric.name}'",
            file=sys.stderr,
        )

    # Exit code resolution per TDD §3.5 matrix.
    if args.strict and (report.stale or zero_result):
        sys.exit(1)


def _emit_freshness_io_error(fe: FreshnessError) -> None:  # noqa: F821
    """Map FreshnessError.kind to AC-4.1/4.2/4.3 stderr lines."""
    if fe.kind == "auth":
        msg = (
            f"ERROR: S3 freshness probe failed (auth): "
            f"could not authenticate against s3://{fe.bucket}/{fe.prefix} — {fe.underlying!r}"
        )
    elif fe.kind == "not-found":
        msg = (
            f"ERROR: S3 freshness probe failed (not-found): "
            f"s3://{fe.bucket}/{fe.prefix} does not exist — {fe.underlying!r}"
        )
    elif fe.kind == "network":
        msg = (
            f"ERROR: S3 freshness probe failed (network): "
            f"could not reach s3://{fe.bucket}/{fe.prefix} — {fe.underlying!r}"
        )
    else:
        msg = (
            f"ERROR: S3 freshness probe failed (unknown): "
            f"s3://{fe.bucket}/{fe.prefix} — {fe.underlying!r}"
        )
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()
