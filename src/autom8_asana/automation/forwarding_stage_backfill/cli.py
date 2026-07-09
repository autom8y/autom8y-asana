"""CLI for the Forwarding-Stage backfill (S4).

Usage:
    # Dry-run PLAN (the DEFAULT posture; ZERO Asana writes)
    python -m autom8_asana.automation.forwarding_stage_backfill.cli plan
    python -m autom8_asana.automation.forwarding_stage_backfill.cli plan --lookback-days 21 --out plan.json

    # Apply (stamp the board; requires the S1 write config active)
    python -m autom8_asana.automation.forwarding_stage_backfill.cli apply

Exit codes:
    0: success
    1: error (uncalibrated config, denominator cap hit, apply-config inactive, etc.)

The ``plan`` subcommand is the default dry-run posture (operator's DRY-RUN-FIRST
ruling): it gathers evidence, derives stages, resolves CI tasks, runs the S1
validator, and emits a PLAN artifact -- but writes NOTHING to Asana. ``apply``
performs the same derivation and, for every ``stamp`` row, PUTs the custom field
with a per-task receipt; it REFUSES loudly if the S1 write config is inactive
(never a silent no-op).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime

from autom8y_log import get_logger

from autom8_asana.automation.forwarding_stage_backfill.backfill import (
    BackfillMode,
    BackfillPlan,
    BackfillWriteConfig,
    BackfillWriteConfigInactive,
    ForwardingStageBackfill,
)
from autom8_asana.automation.forwarding_stage_backfill.config import (
    BackfillConfig,
    UncalibratedBackfillConfig,
)
from autom8_asana.automation.forwarding_stage_backfill.evidence_source import (
    CloudWatchInsightsEvidenceSource,
    DenominatorCapError,
)
from autom8_asana.domain.forwarding_stage import StageDisposition

logger = get_logger(__name__)

__all__ = ["build_write_config", "main", "render_summary"]


def build_write_config() -> BackfillWriteConfig:
    """Build the write config from the S1 ``ApiSettings.forwarding_stage_*`` fields.

    Reuses the S1 config surface verbatim -- the ONLY place option GIDs / the
    field GID / the master switch live. A bad Inactive disposition string falls
    back to the safe PARKED default (never crash the CLI on a config typo).
    """
    from autom8_asana.api.config import get_settings

    settings = get_settings()
    raw_disp = (settings.forwarding_stage_disposition or {}).get(
        "Inactive", StageDisposition.PARKED.value
    )
    try:
        disposition = StageDisposition(raw_disp)
    except ValueError:
        logger.warning(
            "backfill_disposition_invalid",
            extra={"raw": raw_disp, "fallback": StageDisposition.PARKED.value},
        )
        disposition = StageDisposition.PARKED
    return BackfillWriteConfig(
        enabled=settings.forwarding_stage_write_enabled,
        field_gid=settings.forwarding_stage_field_gid,
        option_gids=dict(settings.forwarding_stage_option_gids or {}),
        inactive_disposition=disposition,
    )


def _company_id_field_gid() -> str:
    """The 'Company ID' custom-field definition GID (the resolution key).

    Reuses the SAME ``ApiSettings.company_id_field_gid`` field the receipts route
    consumes (api/config.py:81).
    """
    from autom8_asana.api.config import get_settings

    return get_settings().company_id_field_gid


async def _run(mode: BackfillMode, *, lookback_days: int, out_path: str | None) -> int:
    """Construct the live wiring and run the backfill; return an exit code."""
    from autom8_asana import AsanaClient
    from autom8_asana._defaults import NullCacheProvider

    backfill_cfg = BackfillConfig(lookback_days=lookback_days)
    write_cfg = build_write_config()

    try:
        evidence = CloudWatchInsightsEvidenceSource(backfill_cfg)
    except UncalibratedBackfillConfig as exc:
        print(f"Backfill config not calibrated: {exc}", file=sys.stderr)
        return 1

    # K2: the verify client reads CACHE-DISABLED (NullCacheProvider) so a
    # post-write re-read is never served the stale pre-write value. Confined to
    # the S4 verification posture -- the global SDK cache default is untouched.
    async with (
        AsanaClient() as client,
        AsanaClient(cache_provider=NullCacheProvider()) as verify_client,
    ):
        orchestrator = ForwardingStageBackfill(
            evidence_source=evidence,
            client=client,
            verify_client=verify_client,
            company_id_field_gid=_company_id_field_gid(),
            write_config=write_cfg,
            nudge_threshold_hours=backfill_cfg.nudge_threshold_hours,
        )
        try:
            plan = await orchestrator.run(mode=mode, window_days=lookback_days)
        except BackfillWriteConfigInactive as exc:
            print(f"APPLY REFUSED: {exc}", file=sys.stderr)
            return 1
        except DenominatorCapError as exc:
            print(f"DENOMINATOR CAP HIT (aborting; PLAN would be a lie): {exc}", file=sys.stderr)
            return 1

    _emit(plan, out_path=out_path)
    return 0


def _emit(plan: BackfillPlan, *, out_path: str | None) -> None:
    """Print the human summary + write the JSON PLAN/receipt artifact."""
    print(render_summary(plan))
    if out_path is None:
        out_path = _default_out_path(plan.mode)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(plan.to_dict(), fh, indent=2, sort_keys=True)
    print(f"\nArtifact written to: {out_path}")


def _default_out_path(mode: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    kind = "run-receipt" if mode == BackfillMode.APPLY.value else "plan"
    return f"forwarding-stage-backfill-{kind}-{stamp}.json"


def render_summary(plan: BackfillPlan) -> str:
    """Human-readable PLAN summary (denominator header + per-action counts)."""
    h = plan.header
    c = plan.counts
    lines = [
        f"Forwarding-Stage backfill [{plan.mode.upper()}]",
        "=" * 60,
        "DENOMINATOR (true, not the triage floor):",
        f"  window_days              : {h.window_days}",
        f"  distinct_clinics_observed: {h.distinct_clinics_observed}",
        f"  booking_mail_total       : {h.booking_mail_total}",
        f"  booking_clinics          : {h.booking_clinics}",
        f"  confirmation_clinics     : {h.confirmation_clinics}",
        f"  query_row_cap            : {h.query_row_cap}  (cap_hit={h.cap_hit})",
        f"  malformed_records        : booking={h.malformed_booking_records} "
        f"confirmation={h.malformed_confirmation_records}",
        "-" * 60,
        "ACTIONS:",
        f"  stamp-Flowing  : {c.get('stamp_Flowing', 0)}",
        f"  stamp-Stalled  : {c.get('stamp_Stalled', 0)}",
        f"  stamp-Verified : {c.get('stamp_Verified', 0)}",
        f"  stamp (total)  : {c.get('stamp', 0)}",
        f"  skip           : {c.get('skip', 0)}",
        f"  noop           : {c.get('noop', 0)}",
        f"  refuse         : {c.get('refuse', 0)}",
        f"  unresolved     : {c.get('unresolved', 0)}",
        "-" * 60,
    ]
    if plan.unresolved:
        lines.append("UNRESOLVED (operator triage -- malformed/ambiguous inbox, NEVER guessed):")
        for r in plan.unresolved:
            lines.append(
                f"  {r.inbox_uuid}  booking={r.booking_mail_count} "
                f"confirmation={r.forwarding_confirmation_seen} "
                f"derived={r.derived_stage} reason={r.reason}"
            )
        lines.append("-" * 60)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns an exit code (0 success / 1 error)."""
    from autom8_asana.core.logging import configure

    configure(level="WARNING")

    parser = argparse.ArgumentParser(
        prog="autom8_asana.automation.forwarding_stage_backfill.cli",
        description=(
            "Backfill each existing clinic's Forwarding Stage from monolith log "
            "evidence. `plan` (default) is a dry-run PLAN with ZERO writes; "
            "`apply` stamps the board (requires the S1 write config active)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        title="commands", dest="command", required=True, help="Available commands"
    )

    plan_parser = subparsers.add_parser(
        "plan",
        help="Dry-run: emit a PLAN artifact, ZERO Asana writes (DEFAULT posture)",
        description="Gather evidence, derive stages, resolve CI tasks, run the "
        "validator, emit a PLAN. Writes NOTHING to Asana.",
    )
    _add_common_args(plan_parser)

    apply_parser = subparsers.add_parser(
        "apply",
        help="Stamp the board with per-task receipts (requires active write config)",
        description="Same derivation as `plan`, but PUTs each `stamp` row and "
        "emits per-task receipts. REFUSES loudly if the write config is inactive.",
    )
    _add_common_args(apply_parser)

    args = parser.parse_args(argv)
    mode = BackfillMode.APPLY if args.command == "apply" else BackfillMode.PLAN

    try:
        return asyncio.run(_run(mode, lookback_days=args.lookback_days, out_path=args.out))
    except Exception as exc:  # BROAD-CATCH: boundary -- CLI entry point
        print(f"Backfill error: {exc}", file=sys.stderr)
        logger.exception("backfill_cli_failed")
        return 1


def _add_common_args(sub: argparse.ArgumentParser) -> None:
    from autom8_asana.automation.forwarding_stage_backfill.config import DEFAULT_LOOKBACK_DAYS

    sub.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help=f"Lookback window in days (default {DEFAULT_LOOKBACK_DAYS}; DD-2 knee).",
    )
    sub.add_argument(
        "--out",
        default=None,
        help="Path for the PLAN/run-receipt JSON artifact (default: cwd, timestamped).",
    )


if __name__ == "__main__":
    sys.exit(main())
