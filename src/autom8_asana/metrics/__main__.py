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

Cache-freshness CLI surface (Batch-A, HANDOFF-thermia-to-10x-dev-2026-04-27;
PT-2 Option B refactor 2026-04-27 unifies force-warm with canonical surface):
    --force-warm        Trigger cache_warmer Lambda via canonical force_warm()
                        (autom8_asana.cache.integration.force_warm). Routes
                        through the app-shared DataFrameCache.coalescer per
                        LD-P3-2 (direct Lambda invoke FORBIDDEN).
    --force-warm --wait Sync mode (InvocationType=RequestResponse) + L1
                        MemoryTier invalidation per ADR-003 HYBRID.
    --sla-profile=X     Per-class staleness threshold (active=6h, warm=12h,
                        cold=24h, near-empty=7d) per P3 §2.2. Additive to
                        --strict (PRD C-2 backwards-compat preserved).

Force-warm requires the CACHE_WARMER_LAMBDA_ARN env var (fleet convention;
matches src/autom8_asana/api/routes/admin.py:211 and
src/autom8_asana/api/preload/progressive.py:548).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import TYPE_CHECKING

from autom8_asana.cache.integration.force_warm import (
    LAMBDA_ARN_ENV_VAR as _FORCE_WARM_REQUIRED_ENV,
)
from autom8_asana.cache.integration.force_warm import (
    ForceWarmError,
    force_warm,
)
from autom8_asana.metrics.cloudwatch_emit import emit_freshness_probe_metrics

if TYPE_CHECKING:
    from autom8_asana.metrics.freshness import FreshnessError, FreshnessReport

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
# Force-warm env var (PT-2 Option B refactor — fleet convention unification)
# Per ADR-005 + force_warm.py canonical surface: the cache_warmer Lambda
# ARN/name resolves from CACHE_WARMER_LAMBDA_ARN, matching the fleet
# convention at api/routes/admin.py:211 + api/preload/progressive.py:548.
# _FORCE_WARM_REQUIRED_ENV is bound to force_warm.LAMBDA_ARN_ENV_VAR at the
# top-of-module imports above so tests' `from autom8_asana.metrics.__main__
# import _FORCE_WARM_REQUIRED_ENV` continues to work — no duplication on
# the CLI side. The CLI preflight gates on the same var so missing-config
# emits a friendly stderr BEFORE coalescer/factory path is invoked.
# Discoverability: --help text names the var explicitly per AC-1
# friendly-error contract.
# ---------------------------------------------------------------------------


def _emit_force_warm_missing_env_error() -> None:
    """Write actionable stderr line for missing CACHE_WARMER_LAMBDA_ARN.

    Mirrors the _emit_preflight_error AC-1 'friendly stderr' shape, scoped to
    the force-warm path so the standard CLI does not inherit the requirement.
    Per PT-2 Option B refactor: env var unified to the fleet convention used
    at api/routes/admin.py:211 + api/preload/progressive.py:548.
    """
    msg = (
        f"ERROR: --force-warm requires the {_FORCE_WARM_REQUIRED_ENV} environment "
        "variable to resolve the cache_warmer Lambda function. Set it to the Lambda "
        "function ARN or name, then retry. (Fleet convention; see "
        "src/autom8_asana/api/routes/admin.py:211 and "
        "src/autom8_asana/api/preload/progressive.py:548.)"
    )
    print(msg, file=sys.stderr)


def _resolve_dataframe_cache_for_cli() -> object:
    """Return the app-shared DataFrameCache instance, initializing if needed.

    Per PT-2 Option B refactor: force-warm requests MUST share coalescer state
    with any in-process consumer. Two CLI invocations within the same Python
    process share the module-level singleton, so concurrent --force-warm calls
    against the same project_gid coalesce on the same DataFrameCacheCoalescer
    instance — which is precisely what LD-P3-2 thundering-herd protection
    requires.

    Returns:
        DataFrameCache instance (singleton) — guaranteed non-None or raises.

    Raises:
        ForceWarmError: kind="config" if S3 bucket is not configured (the
            factory returns None when the bucket env var is unset; we wrap as
            ForceWarmError so the CLI maps to the friendly-stderr exit-1 path).
    """
    from autom8_asana.cache.dataframe.factory import (
        get_dataframe_cache,
        initialize_dataframe_cache,
    )

    cache = get_dataframe_cache()
    if cache is None:
        cache = initialize_dataframe_cache()
    if cache is None:
        # Factory returns None when ASANA_CACHE_S3_BUCKET is unset. The CLI
        # bucket preflight (in main()) catches this case earlier with a more
        # specific message; this is a defensive fallback.
        raise ForceWarmError(
            ForceWarmError.KIND_CONFIG,
            "DataFrameCache cannot be initialized; ASANA_CACHE_S3_BUCKET is "
            "unset or factory returned None.",
        )
    return cache


def _safe_emit_freshness_probe_metrics(
    *,
    report: FreshnessReport,
    metric_name_dim: str,
    project_gid: str,
    section_coverage_delta: int,
    force_warm_latency_seconds: float | None,
) -> None:
    """Emit FLAG-1 freshness probe metrics; never crash the CLI on failure.

    Wraps ``cloudwatch_emit.emit_freshness_probe_metrics`` so that any
    transport, IAM, or boto3 import failure surfaces a single stderr line
    and the CLI continues per PRD C-2 backwards-compat (default-mode CLI
    MUST NOT change exit-code semantics from added observability emissions).

    The wrapped emit function already has its own per-call best-effort
    exception handler around ``put_metric_data``; this outer guard catches
    pre-call failures (e.g., boto3 import, AWS_REGION resolution, client
    construction) so the CLI's primary purpose — compute and print the
    metric — succeeds even when the observability path is broken.
    """
    try:
        emit_freshness_probe_metrics(
            report=report,
            metric_name_dim=metric_name_dim,
            project_gid=project_gid,
            section_coverage_delta=section_coverage_delta,
            force_warm_latency_seconds=force_warm_latency_seconds,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort observability emission
        sys.stderr.write(f"WARNING: freshness probe metric emission failed: {exc!r}\n")


def _resolve_section_coverage_delta(
    *,
    metric_entity_type: str | None,
    parquet_count: int,
) -> int:
    """Return classifier_active_section_count - parquet_count.

    SectionCoverageDelta is informational only (C-6 HARD CONSTRAINT — NO ALARM).
    When the classifier for ``metric_entity_type`` cannot be resolved (e.g.,
    --force-warm path with no metric name), returns 0 — the metric still emits
    so the dashboard cardinality is preserved across CLI shapes.
    """
    if metric_entity_type is None:
        return 0
    try:
        from autom8_asana.models.business.activity import CLASSIFIERS
    except Exception:  # noqa: BLE001 — observability path must not crash CLI
        return 0
    classifier = CLASSIFIERS.get(metric_entity_type)
    if classifier is None:
        return 0
    try:
        return len(classifier.active_sections()) - parquet_count
    except Exception:  # noqa: BLE001 — defensive
        return 0


def _execute_force_warm(
    project_gid: str,
    *,
    wait: bool,
    flag_parse_baseline: float | None = None,
    metric_name_dim: str = "force_warm",
    bucket: str | None = None,
    threshold_seconds: int | None = None,
    metric_entity_type: str | None = None,
) -> int:
    """Execute force-warm by delegating to the canonical force_warm() module.

    Per PT-2 Option B refactor (HANDOFF-thermia-to-10x-dev §3 LD-P3-2):
    the CLI does NOT construct its own coalescer or invoke boto3 directly.
    All Lambda invocation routes through the canonical surface at
    autom8_asana.cache.integration.force_warm, which inherits:

      - App-shared DataFrameCache.coalescer (NOT a fresh per-invocation
        instance) — two CLI --force-warm invocations within the same Python
        process share dedup state.
      - Coalescer key shape ``forcewarm:{project_gid}:{entity_types|*}``
        (Batch-C canonical; see force_warm.build_coalescer_key).
      - L1 MemoryTier invalidation on sync success per ADR-003 HYBRID.
      - CACHE_WARMER_LAMBDA_ARN env var resolution (fleet convention).

    FLAG-1 boundary (BLOCK-1 remediation): when ``flag_parse_baseline`` is
    supplied AND ``wait`` is True AND force_warm() succeeds, this method
    re-runs ``FreshnessReport.from_s3_listing`` to observe post-warm fresh
    state and emits the five-metric ``Autom8y/FreshnessProbe`` batch with
    ``ForceWarmLatencySeconds = monotonic_now - flag_parse_baseline``. The
    measured window includes argparse → coalescer wait → Lambda invoke →
    Lambda response → L1 invalidation → S3 list (recheck), satisfying the
    FLAG-1 boundary contract per P4 SLI-2.

    Default async path (``wait=False``) does NOT post-warm-recheck — the
    operator accepts SWR rebuild lag, so no end timestamp exists within a
    single CLI process. ForceWarmLatencySeconds is OMITTED on async per
    cloudwatch_emit.emit_freshness_probe_metrics contract.

    Args:
        project_gid: Project to warm. Forms the coalescer key together with
            entity_types=() (wildcard semantic).
        wait: If True, InvocationType=RequestResponse (sync) + L1 MemoryTier
            invalidation per ADR-003 HYBRID. If False, InvocationType=Event
            (async fire-and-forget); no L1 invalidation.
        flag_parse_baseline: time.monotonic() value captured immediately
            after parser.parse_args() in main(). Forms the FLAG-1 window
            start. When None, latency emission is suppressed.
        metric_name_dim: Dimension value identifying the CLI surface for
            cross-metric attribution. Defaults to "force_warm" for the
            force-warm CLI shape.
        bucket: S3 bucket for the post-warm freshness recheck. When None,
            falls back to ASANA_CACHE_S3_BUCKET. Recheck is suppressed if
            unresolvable.
        threshold_seconds: Threshold seconds passed into the recheck
            FreshnessReport. When None, recheck is suppressed (no defensible
            default at this altitude — caller passes the resolved threshold).
        metric_entity_type: Entity type for SectionCoverageDelta classifier
            resolution. None when force-warm runs without a metric name.

    Returns:
        Process exit code: 0 on success (sync ok / async accepted / coalesced
        wait succeeded), 1 on Lambda failure or transport error.
    """
    import asyncio

    try:
        cache = _resolve_dataframe_cache_for_cli()
    except ForceWarmError as fwe:
        if fwe.kind == ForceWarmError.KIND_CONFIG:
            print(f"ERROR: --force-warm config error: {fwe}", file=sys.stderr)
        else:
            print(f"ERROR: --force-warm setup failed: {fwe}", file=sys.stderr)
        return 1

    async def _delegate() -> int:
        try:
            result = await force_warm(
                cache=cache,  # type: ignore[arg-type]
                project_gid=project_gid,
                entity_types=(),
                wait=wait,
            )
        except ForceWarmError as fwe:
            # Sync mode failures (FunctionError, non-2xx, body.success=False)
            # surface here per force_warm.py:362-370.
            if fwe.kind == ForceWarmError.KIND_LAMBDA:
                print(
                    f"ERROR: force-warm Lambda reported failure: {fwe}",
                    file=sys.stderr,
                )
            elif fwe.kind == ForceWarmError.KIND_INVOKE:
                print(
                    f"ERROR: force-warm Lambda invoke failed: {fwe}",
                    file=sys.stderr,
                )
            elif fwe.kind == ForceWarmError.KIND_CONFIG:
                # Should be caught earlier by the CLI preflight; defensive.
                print(f"ERROR: force-warm config error: {fwe}", file=sys.stderr)
            else:
                print(
                    f"ERROR: force-warm failed ({fwe.kind}): {fwe}",
                    file=sys.stderr,
                )
            return 1

        # Map ForceWarmResult → CLI exit-code semantics + stderr lines.
        if result.deduped:
            if result.error:
                print(
                    f"ERROR: force-warm coalesced wait failed: {result.error}",
                    file=sys.stderr,
                )
                return 1
            print(
                "force-warm coalesced (another in-process invocation completed); "
                "no new Lambda invoke issued",
                file=sys.stderr,
            )
            return 0

        if not wait:
            # Async path — successful Event accept (2xx). Per FLAG-1 boundary,
            # default async path omits ForceWarmLatencySeconds (no end
            # timestamp available within a single CLI process).
            print(
                "force-warm invoked (async); monitor DMS metric "
                "Autom8y/AsanaCacheWarmer for completion",
                file=sys.stderr,
            )
            return 0

        # Sync path — force_warm() raises on Lambda failure, so reaching
        # here means success + L1 invalidation per ADR-003 HYBRID branch.
        print(
            "force-warm completed (sync); L1 invalidated per ADR-003 HYBRID",
            file=sys.stderr,
        )

        # FLAG-1 boundary: post-warm freshness recheck + latency emission.
        # Window = parse_args() → here (success of sync force_warm + L1
        # invalidation). Re-running from_s3_listing observes the post-warm
        # state so MaxParquetAgeSeconds/SectionCount/SectionAgeP95Seconds
        # reflect what the operator just refreshed.
        if flag_parse_baseline is not None and bucket is not None and threshold_seconds is not None:
            try:
                from autom8_asana.metrics.freshness import (
                    FreshnessError as _FE,
                )
                from autom8_asana.metrics.freshness import (
                    FreshnessReport as _FR,
                )

                prefix = f"dataframes/{project_gid}/sections/"
                try:
                    recheck = _FR.from_s3_listing(
                        bucket=bucket,
                        prefix=prefix,
                        threshold_seconds=threshold_seconds,
                    )
                except _FE as fe:
                    sys.stderr.write(
                        f"WARNING: post-warm freshness recheck failed: "
                        f"{fe.kind} s3://{fe.bucket}/{fe.prefix}\n"
                    )
                    return 0
                latency = time.monotonic() - flag_parse_baseline
                delta = _resolve_section_coverage_delta(
                    metric_entity_type=metric_entity_type,
                    parquet_count=recheck.parquet_count,
                )
                _safe_emit_freshness_probe_metrics(
                    report=recheck,
                    metric_name_dim=metric_name_dim,
                    project_gid=project_gid,
                    section_coverage_delta=delta,
                    force_warm_latency_seconds=latency,
                )
            except Exception as exc:  # noqa: BLE001
                # Top-level guard: any unexpected error in the observability
                # path surfaces a single stderr warning and leaves the
                # primary CLI exit semantics intact.
                sys.stderr.write(f"WARNING: post-warm observability emission failed: {exc!r}\n")

        return 0

    return asyncio.run(_delegate())


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
    # PT-2 Option B refactor: delegates to canonical force_warm() at
    # autom8_asana.cache.integration.force_warm. Env var unified to
    # CACHE_WARMER_LAMBDA_ARN (fleet convention).
    parser.add_argument(
        "--force-warm",
        action="store_true",
        dest="force_warm",
        help=(
            "Trigger cache_warmer Lambda via DataFrameCache coalescer. "
            "Coalescer-routed per LD-P3-2 (direct Lambda invoke FORBIDDEN). "
            f"Requires {_FORCE_WARM_REQUIRED_ENV} env var (fleet convention)."
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

    # FLAG-1 baseline (BLOCK-1 remediation): capture monotonic time IMMEDIATELY
    # after argparse so the force-warm latency window encompasses argparse →
    # coalescer wait → Lambda invoke → Lambda response → L1 invalidation →
    # post-warm S3 recheck. Per P4 SLI-2 ForceWarmLatencySeconds boundary.
    flag_parse_baseline: float = time.monotonic()

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

    # ----- Force-warm path (Work-Item 1; PT-2 Option B refactor) -----
    # Force-warm runs as an early branch — it does NOT require a metric name
    # (the warm cascade affects all entity types for the project_gid). Per AC-1,
    # exits 0 on Lambda success / 1 on Lambda failure / 1 with friendly stderr
    # on missing CACHE_WARMER_LAMBDA_ARN or missing ASANA_CACHE_S3_BUCKET
    # (preflight catches MINOR-OBS-2 bucket-typo case BEFORE Lambda invocation
    # per HANDOFF §1 work-item 1). Delegates to canonical force_warm() at
    # autom8_asana.cache.integration.force_warm.
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

        # 2. Validate CACHE_WARMER_LAMBDA_ARN (PT-2 Option B refactor: fleet
        #    convention env var; the canonical force_warm() resolves it via
        #    its own LAMBDA_ARN_ENV_VAR constant, but the CLI preflight
        #    surfaces missing-config friendly-stderr-style before the
        #    coalescer/factory path is invoked).
        function_arn = os.environ.get(_FORCE_WARM_REQUIRED_ENV)
        if not function_arn:
            _emit_force_warm_missing_env_error()
            sys.exit(1)

        # 3. Resolve project_gid for warm — use --project-gid if provided,
        #    else fall back to the metric's classifier (--metric-derived);
        #    if neither, surface a friendly stderr.
        warm_project_gid = args.project_gid
        warm_metric_name_dim = "force_warm"
        warm_metric_entity_type: str | None = None
        if args.metric:
            try:
                metric = registry.get_metric(args.metric)
                warm_metric_name_dim = metric.name
                warm_metric_entity_type = metric.scope.entity_type
                if warm_project_gid is None:
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

        # FLAG-1 boundary (BLOCK-1 remediation): pass flag_parse_baseline
        # captured immediately after parser.parse_args() so the post-warm
        # ForceWarmLatencySeconds spans argparse → coalescer wait → Lambda
        # invoke → Lambda response → L1 invalidation → S3 list (recheck).
        # Per P4 SLI-2 and ADR-006 §Decision (atomic emission timestamp).
        exit_code = _execute_force_warm(
            warm_project_gid,
            wait=args.wait,
            flag_parse_baseline=flag_parse_baseline,
            metric_name_dim=warm_metric_name_dim,
            bucket=bucket,
            threshold_seconds=threshold_seconds,
            metric_entity_type=warm_metric_entity_type,
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

    # ----- FLAG-1 baseline metric emission (BLOCK-1 remediation) -----
    # Default-mode CLI (no --force-warm) emits the four-metric baseline batch
    # so the operator's per-CLI-invocation observability surface is captured
    # regardless of which CLI shape ran. ForceWarmLatencySeconds is OMITTED
    # (no force-warm window exists on this path) per FLAG-1 contract.
    # SectionCoverageDelta is the difference between classifier active section
    # count and parquet count; informational only per C-6 HARD CONSTRAINT (NO ALARM).
    # Safe-emit wrapper absorbs any CW emission failure (PRD C-2 backwards-
    # compat: default-mode CLI exit-code semantics MUST NOT change from
    # added observability emissions).
    section_coverage_delta = _resolve_section_coverage_delta(
        metric_entity_type=metric.scope.entity_type,
        parquet_count=report.parquet_count,
    )
    _safe_emit_freshness_probe_metrics(
        report=report,
        metric_name_dim=metric.name,
        project_gid=project_gid,
        section_coverage_delta=section_coverage_delta,
        force_warm_latency_seconds=None,
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
