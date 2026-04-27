"""CLI entry point for metrics computation.

Usage:
    python -m autom8_asana.metrics active_mrr
    python -m autom8_asana.metrics active_mrr --verbose
    python -m autom8_asana.metrics active_mrr --strict --staleness-threshold 6h
    python -m autom8_asana.metrics active_mrr --strict --sla-profile=warm
    python -m autom8_asana.metrics --force-warm
    python -m autom8_asana.metrics --force-warm --wait
    python -m autom8_asana.metrics active_mrr --json
    python -m autom8_asana.metrics --list

Cache-freshness CLI surface (Batch-A, HANDOFF-thermia-to-10x-dev-2026-04-27):
    --force-warm        Trigger cache_warmer Lambda via DataFrameCache coalescer
                        (LD-P3-2: direct Lambda invoke FORBIDDEN).
    --force-warm --wait Sync mode (InvocationType=RequestResponse) + L1
                        MemoryTier invalidation per ADR-003 HYBRID.
    --sla-profile=X     Per-class staleness threshold (active=6h, warm=12h,
                        cold=24h, near-empty=7d) per P3 §2.2. Additive to
                        --strict (PRD C-2 backwards-compat preserved).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.metrics.freshness import FreshnessError

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


# ---------------------------------------------------------------------------
# SLA profile classes (Work-Item 2 — PRD NG8 / FLAG-2 / LD-P2-1)
# Per P3 §2.2 and HANDOFF §3 LD-P2-1 resolution table:
#   active     -> 21600s (6h)   — direct contributor to financial aggregate
#   warm       -> 43200s (12h)  — informational; relaxed threshold acceptable
#   cold       -> 86400s (24h)  — slow-moving sections
#   near-empty -> 604800s (7d)  — presumably-inactive sections
# Default profile when --sla-profile is absent: 'active' (strictest), preserving
# PRD G2 6h behavior + PRD C-2 backwards-compat.
# ---------------------------------------------------------------------------
_SLA_PROFILE_THRESHOLDS: dict[str, int] = {
    "active": 21600,
    "warm": 43200,
    "cold": 86400,
    "near-empty": 604800,
}

# ---------------------------------------------------------------------------
# Force-warm preflight env var (Work-Item 1 — LD-P2-2 disposition)
# Disposition: Option A — env-var preflight check (NOT settings field).
# Rationale: matches the existing _CLI_REQUIRED tuple pattern used for the
# 'cli' profile. The var is gated only on --force-warm invocation paths so
# that default-mode CLI invocations (no force-warm) preserve PRD C-2 behavior
# verbatim — adding a settings field would couple the var to all CLI paths.
# Discoverability: --help text names the var; missing-var stderr names it
# explicitly per the AC-1 friendly-error contract.
# ---------------------------------------------------------------------------
_FORCE_WARM_REQUIRED_ENV = "CACHE_WARMER_LAMBDA_FUNCTION_NAME"


def _coalescer_key_for_force_warm(project_gid: str) -> str:
    """Return the coalescer key for cross-entity-type force-warm coordination.

    Force-warm warms ALL entity types in a single Lambda invocation
    (cache_warmer.py cascade). The coalescer key uses a sentinel entity_type
    'force_warm' to coordinate that the cascade is in progress without
    blocking individual entity_type get_async() calls that target the same
    project.
    """
    return f"force_warm:{project_gid}"


def _emit_force_warm_missing_env_error() -> None:
    """Write actionable stderr line for missing CACHE_WARMER_LAMBDA_FUNCTION_NAME.

    Mirrors the _emit_preflight_error AC-1 'friendly stderr' shape, scoped to
    the force-warm path so the standard CLI does not inherit the requirement.
    """
    msg = (
        f"ERROR: --force-warm requires the {_FORCE_WARM_REQUIRED_ENV} environment "
        "variable to resolve the cache_warmer Lambda function. Set it to the Lambda "
        "function name or ARN, then retry. (Per HANDOFF §5 LD-P2-2 disposition: "
        "preflight env var contract.)"
    )
    print(msg, file=sys.stderr)


def _execute_force_warm(
    project_gid: str,
    *,
    wait: bool,
    function_name: str,
) -> int:
    """Execute force-warm via DataFrameCache coalescer-protected path (LD-P3-2).

    Per HANDOFF §3 LD-P2 resolution: force-warm MUST route through
    DataFrameCache (coalescer-protected). Direct Lambda invoke is FORBIDDEN.
    The coalescer's try_acquire_async() gates the boto3.client('lambda').invoke()
    call so concurrent --force-warm invocations from multiple operators do not
    issue simultaneous cascade warms.

    Args:
        project_gid: Project to warm. Used as the coalescer key.
        wait: If True, InvocationType=RequestResponse (sync) + L1 MemoryTier
            invalidation per ADR-003 HYBRID. If False, InvocationType=Event
            (async fire-and-forget); no L1 invalidation (operator accepts SWR
            rebuild lag).
        function_name: Lambda function name or ARN, resolved upstream from
            CACHE_WARMER_LAMBDA_FUNCTION_NAME.

    Returns:
        Process exit code: 0 on success (sync ok or async accepted), 1 on
        Lambda failure or transport error.
    """
    import asyncio

    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    # Coalescer-routed path per LD-P3-2.
    # Build a minimal coalescer for cross-process gating; the in-process
    # coalescer state is bounded to this CLI invocation (single process), but
    # the gating-before-invoke discipline is preserved per the architecture
    # contract. P3 §5.1 stampede protection layers the Lambda idempotency-key
    # window (5-min) on top for cross-process dedup.
    from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer

    coalescer = DataFrameCacheCoalescer()
    coalescer_key = _coalescer_key_for_force_warm(project_gid)

    async def _invoke_through_coalescer() -> int:
        acquired = await coalescer.try_acquire_async(coalescer_key)
        if not acquired:
            # Another in-process force-warm holds the lock; wait then bail.
            await coalescer.wait_async(coalescer_key, timeout_seconds=coalescer.max_wait_seconds)
            print(
                "force-warm coalesced (another in-process invocation completed); "
                "no new Lambda invoke issued",
                file=sys.stderr,
            )
            return 0

        # We hold the lock — perform the Lambda invoke.
        # boto3 picks up AWS credentials from the caller's execution context
        # per P2 §4 'IAM-bound via the invoker's execution context' decision.
        try:
            lambda_client = boto3.client("lambda")
            invocation_type = "RequestResponse" if wait else "Event"
            payload = json.dumps({"project_gid": project_gid}).encode("utf-8")
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType=invocation_type,
                Payload=payload,
            )

            if not wait:
                # Async path — Lambda returns 202 on accept.
                status = response.get("StatusCode", 0)
                if status == 202:
                    print(
                        "force-warm invoked (async); monitor DMS metric "
                        "Autom8y/AsanaCacheWarmer for completion",
                        file=sys.stderr,
                    )
                    await coalescer.release_async(coalescer_key, success=True)
                    return 0
                print(
                    f"ERROR: force-warm Lambda invoke returned StatusCode={status} "
                    "(expected 202 for async)",
                    file=sys.stderr,
                )
                await coalescer.release_async(coalescer_key, success=False)
                return 1

            # Sync path — parse Lambda response body.
            payload_bytes = response.get("Payload")
            body_text = ""
            if payload_bytes is not None:
                body_text = payload_bytes.read().decode("utf-8", errors="replace")
            function_error = response.get("FunctionError")
            if function_error:
                print(
                    f"ERROR: force-warm Lambda reported FunctionError={function_error}: "
                    f"{body_text}",
                    file=sys.stderr,
                )
                await coalescer.release_async(coalescer_key, success=False)
                return 1

            # Lambda success. ADR-003 HYBRID: invalidate L1 MemoryTier so the
            # next read does not serve a stale L1 entry against a fresh L2.
            try:
                _invalidate_memory_tier_for_force_warm(project_gid)
            except Exception as inval_err:  # noqa: BLE001 — best-effort
                # Invalidation failure does NOT fail the force-warm; operator
                # gets a fresh L2 + an SWR rebuild on next read worst case.
                print(
                    f"WARNING: force-warm succeeded but MemoryTier invalidation "
                    f"failed: {inval_err!r}",
                    file=sys.stderr,
                )
            print(
                "force-warm completed (sync); L1 invalidated per ADR-003 HYBRID",
                file=sys.stderr,
            )
            await coalescer.release_async(coalescer_key, success=True)
            return 0
        except ClientError as ce:
            code = (ce.response or {}).get("Error", {}).get("Code", "unknown")
            print(
                f"ERROR: force-warm Lambda invoke failed (ClientError {code}): {ce}",
                file=sys.stderr,
            )
            await coalescer.release_async(coalescer_key, success=False)
            return 1
        except BotoCoreError as be:
            print(
                f"ERROR: force-warm Lambda invoke failed (transport): {be}",
                file=sys.stderr,
            )
            await coalescer.release_async(coalescer_key, success=False)
            return 1

    return asyncio.run(_invoke_through_coalescer())


def _invalidate_memory_tier_for_force_warm(project_gid: str) -> None:
    """Invalidate L1 MemoryTier entries for the project per ADR-003 HYBRID.

    Called on --force-warm --wait success. Default async --force-warm does NOT
    call this (operator accepts SWR rebuild lag).

    Implementation note: a fresh DataFrameCache instance does not share L1
    state with any other process's cache, so this is a no-op for the standalone
    CLI process. The invalidation is meaningful when the CLI is invoked
    in-process from a longer-running consumer (e.g., a batch job that imports
    the metrics module). The HYBRID contract is preserved either way; the
    no-op shape on a fresh process is the architecturally-correct behavior.
    """
    from autom8_asana.cache.integration.dataframe_cache import (
        DataFrameCache,
    )

    # If a singleton/factory exposes a process-shared cache, invalidate it.
    # We use getattr so this remains a no-op when the factory has no
    # cached singleton — the contract is "best effort L1 invalidation."
    factory_module = sys.modules.get("autom8_asana.cache.dataframe.factory")
    if factory_module is None:
        return
    get_singleton = getattr(factory_module, "get_dataframe_cache", None)
    if get_singleton is None:
        return
    try:
        cache = get_singleton()
    except Exception:  # noqa: BLE001 — factory may require runtime context
        return
    if isinstance(cache, DataFrameCache):
        cache.invalidate_project(project_gid)


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
    # ----- Force-warm CLI affordance (Work-Item 1, PRD NG4, P2 §4) -----
    parser.add_argument(
        "--force-warm",
        action="store_true",
        dest="force_warm",
        help=(
            "Trigger cache_warmer Lambda via DataFrameCache coalescer. "
            "Coalescer-routed per LD-P3-2 (direct Lambda invoke FORBIDDEN). "
            f"Requires {_FORCE_WARM_REQUIRED_ENV} env var."
        ),
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help=(
            "Compose with --force-warm: invoke Lambda synchronously "
            "(InvocationType=RequestResponse) and invalidate L1 MemoryTier "
            "on success per ADR-003 HYBRID. Default async without --wait."
        ),
    )
    # ----- SLA profile (Work-Item 2, PRD NG8, P3 §2.2 / FLAG-2) -----
    parser.add_argument(
        "--sla-profile",
        choices=sorted(_SLA_PROFILE_THRESHOLDS.keys()),
        default=None,
        dest="sla_profile",
        help=(
            "Per-class staleness threshold: active=6h, warm=12h, cold=24h, "
            "near-empty=7d (P3 §2.2). Composes with --strict; additive to "
            "--staleness-threshold. When both --sla-profile and "
            "--staleness-threshold are passed, --staleness-threshold wins "
            "(numeric override beats named profile per AC-2)."
        ),
    )
    args = parser.parse_args()

    # ----- Threshold resolution (Work-Item 2, AC-2) -----
    # Resolution precedence per AC-2 + HANDOFF §3 LD-P2-1:
    #   1. --staleness-threshold (numeric override) wins when explicitly set
    #      (defaults to "6h" so a literal "6h" is the implicit default).
    #   2. --sla-profile maps to per-class threshold seconds.
    #   3. Default: 6h (active class equivalent — preserves PRD G2 + PRD C-2).
    # Detection of "explicit --staleness-threshold": when the value differs
    # from the default "6h" string, the operator passed it explicitly.
    sla_profile_default = "active"  # implicit default per LD-P2-1
    explicit_staleness = args.staleness_threshold != "6h"
    try:
        if explicit_staleness:
            threshold_seconds = parse_duration_spec(args.staleness_threshold)
        elif args.sla_profile is not None:
            threshold_seconds = _SLA_PROFILE_THRESHOLDS[args.sla_profile]
        else:
            # Default 6h preserves PRD G2 + PRD C-2 backwards-compat.
            threshold_seconds = _SLA_PROFILE_THRESHOLDS[sla_profile_default]
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

    # ----- Force-warm path (Work-Item 1) -----
    # Force-warm runs as an early branch — it does NOT require a metric name
    # (the warm cascade affects all entity types for the project_gid). Per AC-1,
    # exits 0 on Lambda success / 1 on Lambda failure / 1 with friendly stderr
    # on missing CACHE_WARMER_LAMBDA_FUNCTION_NAME or missing
    # ASANA_CACHE_S3_BUCKET (preflight catches MINOR-OBS-2 bucket-typo case
    # BEFORE Lambda invocation per HANDOFF §1 work-item 1).
    if args.force_warm:
        # 1. Validate ASANA_CACHE_S3_BUCKET (catches MINOR-OBS-2 case before
        #    we get anywhere near the warmer Lambda).
        bucket = os.environ.get("ASANA_CACHE_S3_BUCKET")
        if not bucket:
            print(
                "ERROR: --force-warm requires ASANA_CACHE_S3_BUCKET to be set "
                "to a non-empty bucket name. Set it, then retry.",
                file=sys.stderr,
            )
            sys.exit(1)

        # 2. Validate CACHE_WARMER_LAMBDA_FUNCTION_NAME (LD-P2-2 disposition).
        function_name = os.environ.get(_FORCE_WARM_REQUIRED_ENV)
        if not function_name:
            _emit_force_warm_missing_env_error()
            sys.exit(1)

        # 3. Resolve project_gid for warm — use --project-gid if provided,
        #    else fall back to the metric's classifier (--metric-derived);
        #    if neither, use a sentinel that surfaces in stderr.
        warm_project_gid = args.project_gid
        if warm_project_gid is None and args.metric:
            try:
                metric = registry.get_metric(args.metric)
                classifier = CLASSIFIERS.get(metric.scope.entity_type)
                if classifier is not None:
                    warm_project_gid = classifier.project_gid
            except KeyError:
                pass
        if warm_project_gid is None:
            print(
                "ERROR: --force-warm requires --project-gid or a metric name "
                "whose entity type resolves to a classifier with project_gid",
                file=sys.stderr,
            )
            sys.exit(1)

        exit_code = _execute_force_warm(
            warm_project_gid,
            wait=args.wait,
            function_name=function_name,
        )
        sys.exit(exit_code)

    # Require metric name (force-warm path returned above)
    if not args.metric:
        parser.error("metric name is required (or use --list, or --force-warm)")

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
    # MINOR-OBS-2 fix (Work-Item 8): catch botocore.exceptions.ClientError for
    # the NoSuchBucket case so we emit an AC-4.2-shaped friendly stderr line
    # rather than a raw botocore traceback. Mirrors the IO-error mapping at
    # freshness.py:158-182. ClientError is a base class — we map known error
    # codes (NoSuchBucket, NoSuchKey, AccessDenied, etc.) to friendly messages
    # and re-emit the raw representation for unknown codes.
    import botocore.exceptions as _botocore_exceptions

    try:
        df = load_project_dataframe(project_gid)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except _botocore_exceptions.ClientError as ce:
        # Mirror the FreshnessError.KIND_NOT_FOUND mapping (freshness.py:169-170)
        # for the bucket-typo case; emit AC-4.2-style friendly stderr (no raw
        # traceback). Other ClientError codes get a generic friendly line so we
        # never leak a botocore traceback regardless of code.
        bucket = os.environ.get("ASANA_CACHE_S3_BUCKET", "<unset>")
        prefix = f"dataframes/{project_gid}/sections/"
        code = (ce.response or {}).get("Error", {}).get("Code", "")
        if code in {"NoSuchBucket", "NoSuchKey", "404"}:
            print(
                f"ERROR: bucket or prefix not found — s3://{bucket}/{prefix}",
                file=sys.stderr,
            )
        elif code in {
            "AccessDenied",
            "403",
            "InvalidAccessKeyId",
            "SignatureDoesNotMatch",
        }:
            print(
                f"ERROR: S3 access denied — s3://{bucket}/{prefix} (code: {code})",
                file=sys.stderr,
            )
        else:
            print(
                f"ERROR: S3 ClientError ({code or 'unknown'}) — s3://{bucket}/{prefix}",
                file=sys.stderr,
            )
        sys.exit(1)
    except _botocore_exceptions.NoCredentialsError as nce:
        bucket = os.environ.get("ASANA_CACHE_S3_BUCKET", "<unset>")
        print(
            f"ERROR: S3 credentials unavailable — bucket s3://{bucket} (detail: {nce})",
            file=sys.stderr,
        )
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
