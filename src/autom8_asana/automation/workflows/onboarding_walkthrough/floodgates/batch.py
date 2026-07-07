"""Thin ACTIVE-enumeration batch loop + CLI over the single-office runner (TDD §2/§8).

The batch is deliberately thin: enumerate the ACTIVE PLAY tasks of the Calendar-Integrations
project (reusing ``resolve_section_gids`` — the SAME primitive the poster preflight uses), then
call ``run_office`` per office, aggregating a green/red report. The load-bearing property is
**per-office isolation**: one office's failure is recorded and the wave CONTINUES (never a
fleet halt), and a DONE office is skipped. ``--office`` scopes to ONE office (the isolation
door the operator points at a single misbehaving office during a wave).

CLI (design §2.2):

    # Phase-1: stage + SURFACE the reserved wrangler command, then HALT (no Asana writes).
    python -m ...floodgates.batch --phase produce --office <play_gid> --clinic "<Clinic Name>"

    # Phase-2: after the operator fires the CF deploy, post the three PLAY comments.
    python -m ...floodgates.batch --phase resume --office <play_gid> --execute

Default is dry-run (``--execute`` gates every Asana write). The CF ``wrangler`` deploy and the
client SEND are RESERVED operator levers — surfaced, never fired.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.automation.workflows.onboarding_walkthrough import constants
from autom8_asana.automation.workflows.onboarding_walkthrough.constants import (
    WALKTHROUGH_DECK_DEFAULT,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.office_runner import (
    OfficeRunResult,
    run_office,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.state import (
    Phase,
    StateStore,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play import PLAY_NAME_RE
from autom8_asana.automation.workflows.section_resolution import resolve_section_gids
from autom8_asana.client import AsanaClient

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)

__all__ = [
    "BatchReport",
    "OfficeReport",
    "enumerate_active_play_gids",
    "main",
    "run_batch",
]


@dataclass
class OfficeReport:
    """One office's line in the batch report."""

    play_gid: str
    status: str  # "ok" | "skipped_done" | "skipped_no_clinic" | "failed"
    outcome: str | None = None
    error: str | None = None
    result: OfficeRunResult | None = None


@dataclass
class BatchReport:
    """The aggregate outcome of a batch run (per-office isolation preserved)."""

    offices: list[OfficeReport] = field(default_factory=list)

    @property
    def ok(self) -> list[OfficeReport]:
        return [o for o in self.offices if o.status == "ok"]

    @property
    def failed(self) -> list[OfficeReport]:
        return [o for o in self.offices if o.status == "failed"]

    @property
    def skipped(self) -> list[OfficeReport]:
        return [o for o in self.offices if o.status.startswith("skipped")]


async def enumerate_active_play_gids(client: AsanaClient) -> list[str]:
    """Enumerate the ACTIVE-section PLAY task gids of the Calendar-Integrations project.

    Reuses ``resolve_section_gids`` (section-by-name, never a hardcoded section gid) — the
    SAME positive-selection primitive the poster preflight uses (link_on_play §5). Drops
    completed tasks and keeps only ``PLAY: Custom Calendar Integration`` names (belt+braces;
    the per-office runner's preflight re-validates). An empty resolution returns ``[]``.
    """
    resolved = await resolve_section_gids(
        client.sections,
        constants.CALENDAR_INTEGRATIONS_PROJECT_GID,
        constants.ACTIVE_SECTION_NAMES,
    )
    if not resolved:
        return []
    seen: set[str] = set()
    gids: list[str] = []
    for section_gid in resolved.values():
        tasks = await client.tasks.list_async(
            section=section_gid,
            opt_fields=["name", "completed"],
            completed_since="now",
        ).collect()
        for task in tasks:
            gid = task.gid
            if getattr(task, "completed", False) or gid in seen:
                continue
            name = getattr(task, "name", None)
            if not name or not PLAY_NAME_RE.search(name):
                continue
            seen.add(gid)
            gids.append(gid)
    return gids


async def run_batch(
    client: AsanaClient,
    *,
    phase: str,
    store: StateStore,
    deploy_base: Path,
    clinic_map: Mapping[str, str],
    office: str | None = None,
    producer_dir: Path | None = None,
    deck_template: str = WALKTHROUGH_DECK_DEFAULT,
    project_name: str | None = None,
    execute: bool = False,
) -> BatchReport:
    """Run the requested phase across ACTIVE offices (or a single ``--office``), isolating
    per-office failures.

    A DONE office is skipped; a ``produce`` office lacking an operator-confirmed clinic name
    is skipped (never freeze an un-named deck); any per-office exception is caught, recorded,
    and the wave CONTINUES (one office's failure never halts the batch).
    """
    play_gids = [office] if office is not None else await enumerate_active_play_gids(client)
    reports: list[OfficeReport] = []
    for gid in play_gids:
        existing = store.load(gid)
        if existing is not None and existing.phase is Phase.DONE:
            reports.append(OfficeReport(gid, "skipped_done", outcome="already_done"))
            continue
        clinic = clinic_map.get(gid) or (existing.clinic if existing is not None else None)
        if phase == "produce" and not clinic:
            reports.append(
                OfficeReport(gid, "skipped_no_clinic", error="no operator-confirmed clinic name")
            )
            continue
        try:
            result = await run_office(
                client,
                play_gid=gid,
                clinic=clinic or "",
                phase=phase,
                store=store,
                deploy_base=deploy_base,
                producer_dir=producer_dir,
                deck_template=deck_template,
                project_name=project_name,
                execute=execute,
            )
        except Exception as exc:  # noqa: BLE001 -- per-office isolation: one failure never halts the wave
            logger.warning("floodgates_office_failed", play_gid=gid, error=str(exc))
            reports.append(OfficeReport(gid, "failed", error=str(exc)))
            continue
        reports.append(OfficeReport(gid, "ok", outcome=result.outcome, result=result))
    return BatchReport(offices=reports)


# ------------------------------------------------------------------------------------ CLI


def _halt_banner(result: OfficeRunResult) -> str:
    """The Phase-1 HALT banner: surface the reserved CF deploy lever, never fire it."""
    return (
        f"\n[HALT — reserved operator lever] Deck staged for PLAY {result.play_gid} at "
        f"{result.deploy_root}\n"
        "  Fire the CF deploy in the CF-authed env (memory scar: direnv exec ~/life):\n"
        f"    {result.wrangler_command}\n"
        "  Then confirm the deck renders live and re-run Phase-2:\n"
        "    python -m autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.batch"
        f" --phase resume --office {result.play_gid} --execute\n"
    )


def _write_report(report: BatchReport, *, phase: str) -> None:
    for office in report.offices:
        line = f"[{office.status}] {office.play_gid} outcome={office.outcome}"
        if office.error:
            line += f" — {office.error}"
        sys.stdout.write(line + "\n")
        if (
            phase == "produce"
            and office.status == "ok"
            and office.result is not None
            and office.result.wrangler_command
        ):
            sys.stdout.write(_halt_banner(office.result))
    sys.stdout.write(
        f"\nsummary: {len(report.ok)} ok, {len(report.skipped)} skipped, "
        f"{len(report.failed)} failed\n"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Default = dry-run; ``--execute`` gates every Asana write.

    Phase-1 (``produce``) stages the deck(s) and SURFACES the reserved ``wrangler`` command per
    office, then HALTs. Phase-2 (``resume --execute``) posts the three PLAY comments after the
    operator has fired the CF deploy. Exit 0 when no office failed, else 1.
    """
    parser = argparse.ArgumentParser(
        prog="python -m autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.batch",
        description=(
            "Per-office floodgates batch seam: two-phase (produce/resume) orchestrator around "
            "the reserved Cloudflare deploy. The CF wrangler deploy and the client SEND are "
            "operator levers — surfaced, never fired."
        ),
    )
    parser.add_argument("--phase", required=True, choices=["produce", "resume"])
    parser.add_argument("--office", default=None, help="scope to ONE PLAY gid (isolation door).")
    parser.add_argument(
        "--clinic",
        default=None,
        help="operator-confirmed clinic name for --office (Phase-1 produce; personalization-gated).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="JSON object {play_gid: clinic} of operator-confirmed names for a full-wave produce.",
    )
    parser.add_argument("--state-dir", type=Path, default=Path(".sos/floodgates/state"))
    parser.add_argument("--deploy-base", type=Path, default=Path(".sos/floodgates/deploy"))
    parser.add_argument("--producer-dir", type=Path, default=None)
    parser.add_argument(
        "--project-name",
        default=None,
        help="Cloudflare Pages project name (surfaced into the wrangler command; operator-domain).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the Phase-2 PLAY-comment posts (the only mutating mode).",
    )
    args = parser.parse_args(argv)

    clinic_map: dict[str, str] = {}
    if args.manifest is not None:
        raw = json.loads(args.manifest.read_text(encoding="utf-8"))
        clinic_map.update({str(k): str(v) for k, v in raw.items()})
    if args.office is not None and args.clinic is not None:
        clinic_map[args.office] = args.clinic

    store = StateStore(args.state_dir)

    async def _run() -> BatchReport:
        async with AsanaClient() as client:
            return await run_batch(
                client,
                phase=args.phase,
                store=store,
                deploy_base=args.deploy_base,
                clinic_map=clinic_map,
                office=args.office,
                producer_dir=args.producer_dir,
                project_name=args.project_name,
                execute=args.execute,
            )

    report = asyncio.run(_run())
    _write_report(report, phase=args.phase)
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
