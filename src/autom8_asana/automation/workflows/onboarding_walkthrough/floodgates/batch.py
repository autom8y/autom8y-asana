"""Thin ACTIVE-enumeration batch loop + CLI over the single-office runner (TDD §2/§8).

The batch is deliberately thin: enumerate the ACTIVE PLAY tasks of the Calendar-Integrations
project (reusing ``resolve_section_gids`` — the SAME primitive the poster preflight uses), then
call ``run_office`` per office, aggregating a green/red report. The load-bearing property is
**per-office isolation**: one office's failure is recorded and the wave CONTINUES (never a
fleet halt), and a DONE office is skipped. ``--office`` scopes to ONE office (the isolation
door the operator points at a single misbehaving office during a wave).

Produce waves stage every office into ONE wave-shared ``--deploy-base`` root (TDD §8:
point it at the deck-host checkout's ``public/`` for cross-wave accumulation) and surface
a SINGLE wave-level ``wrangler pages deploy`` command — only after the fail-closed
deploy-root guard (root-hygiene allowlist, ``_headers`` byte-parity, no-orphan
manifest-superset predicate) passes. A guard refusal is LOUD and surfaces NO command.

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
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.automation.workflows.onboarding_walkthrough import constants
from autom8_asana.automation.workflows.onboarding_walkthrough.constants import (
    WALKTHROUGH_DECK_DEFAULT,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.deploy_root_guard import (
    DeployRootRefused,
    assert_deploy_root_ready,
    assert_wave_slugs_staged,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.name_match import (
    ClinicNameMismatch,
    clinic_from_play_name,
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
from autom8_asana.automation.workflows.onboarding_walkthrough.render_check import (
    RenderCheckRefused,
)
from autom8_asana.automation.workflows.section_resolution import resolve_section_gids
from autom8_asana.client import AsanaClient

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)

# Operator-environment defaults (absolute paths recommended), so a recipe or shell profile
# pins ONE state dir and ONE deploy root for every run instead of per-command flags.
STATE_DIR_ENV = "AUTOM8_FLOODGATES_STATE_DIR"
DEPLOY_BASE_ENV = "AUTOM8_FLOODGATES_DEPLOY_BASE"

__all__ = [
    "BatchReport",
    "OfficeReport",
    "clinic_from_play_name",
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
    """The aggregate outcome of a batch run (per-office isolation preserved).

    ``wrangler_command`` is the ONE wave-level reserved-lever command (produce phase,
    surfaced only after the fail-closed deploy-root guard passes). ``deploy_refusal``
    carries the guard's LOUD refusal when it does not — in that case NO wrangler command
    is surfaced anywhere (per-office copies are stripped too).
    """

    offices: list[OfficeReport] = field(default_factory=list)
    wrangler_command: str | None = None
    deploy_refusal: str | None = None

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
    deck_manifest: Path | None = None,
    execute: bool = False,
) -> BatchReport:
    """Run the requested phase across ACTIVE offices (or a single ``--office``), isolating
    per-office failures.

    A DONE office is skipped; a ``produce`` office lacking an operator-confirmed clinic name
    is skipped (never freeze an un-named deck); any per-office exception is caught, recorded,
    and the wave CONTINUES (one office's failure never halts the batch).

    Produce phase surfaces ONE wave-level ``wrangler`` command (all offices stage into the
    SHARED ``deploy_base``), and only after ``assert_deploy_root_ready`` passes — root
    hygiene (recursive-exact), ``_headers`` byte-parity, and the no-orphan predicate
    against the committed deck-host ledger (``deck_manifest`` overrides the default
    ``<deploy_base>/../config/deck-manifest.json``) — plus the wave-slug cross-check
    (every staged-ok office's pinned slug dir present in the root). Any guard refusal is
    recorded LOUDLY on the report and NO wrangler command is surfaced (fail-closed).
    """
    if phase == "produce":
        # PRE-FLIGHT the shared root BEFORE any office freezes or mints. Running the guard
        # only after produce let a wrong ``--deploy-base`` persist PRODUCED state whose slug
        # dir lives in the wrong root; every re-run then returned ``already_produced`` and
        # the wave stayed refused. A refused root now produces NOTHING (no mint, no state).
        try:
            assert_deploy_root_ready(Path(deploy_base), manifest_path=deck_manifest)
        except DeployRootRefused as exc:
            logger.error(
                "floodgates_wave_preflight_refused", deploy_base=str(deploy_base), error=str(exc)
            )
            return BatchReport(offices=[], deploy_refusal=str(exc))

    play_gids = [office] if office is not None else await enumerate_active_play_gids(client)
    reports: list[OfficeReport] = []
    for gid in play_gids:
        # ``store.load`` is INSIDE the try: a corrupt / hand-edited manifest raises on
        # deserialize, and per-office isolation demands one office's corruption never poison
        # the wave (state.py invariant) — record it as ``failed`` and CONTINUE, never abort.
        try:
            existing = store.load(gid)
            if existing is not None and existing.phase is Phase.DONE:
                reports.append(OfficeReport(gid, "skipped_done", outcome="already_done"))
                continue
            clinic = clinic_map.get(gid) or (existing.clinic if existing is not None else None)
            if phase == "produce" and not clinic:
                reports.append(
                    OfficeReport(
                        gid, "skipped_no_clinic", error="no operator-confirmed clinic name"
                    )
                )
                continue
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
        except Exception as exc:  # noqa: BLE001 -- per-office isolation: one failure (incl. a corrupt-manifest load) never halts the wave
            # A D9 refusal carries clinic names, and a D10(b) refusal can (clinic_missing):
            # they go to the [failed] stdout line only, never into the structured log (which
            # gets the gid and the error type, plus the reason code for a render refusal).
            if isinstance(exc, ClinicNameMismatch):
                log_error = "ClinicNameMismatch"
            elif isinstance(exc, RenderCheckRefused):
                log_error = f"{type(exc).__name__}[{exc.reason}]"
            else:
                log_error = str(exc)
            logger.warning("floodgates_office_failed", play_gid=gid, error=log_error)
            reports.append(OfficeReport(gid, "failed", error=str(exc)))
            continue
        reports.append(OfficeReport(gid, "ok", outcome=result.outcome, result=result))

    report = BatchReport(offices=reports)
    if phase == "produce":
        _gate_wave_deploy_command(report, deploy_base=deploy_base, deck_manifest=deck_manifest)
    return report


def _gate_wave_deploy_command(
    report: BatchReport, *, deploy_base: Path, deck_manifest: Path | None
) -> None:
    """Surface the ONE wave-level wrangler command iff the deploy-root guard passes.

    The guard (root-hygiene allowlist + ``_headers`` byte-parity + manifest-superset
    no-orphan predicate + wave-slug cross-check) runs BEFORE any command is surfaced. The
    wave-slug cross-check closes the ledger-blind ``already_produced`` window: every
    staged-ok office's PINNED slug dir must be present in the shared root (an office at
    ``PRODUCED`` re-surfaces the command without re-staging, and a slug not yet in the
    committed ledger is invisible to the no-orphan predicate). On refusal the report
    carries ``deploy_refusal``, every per-office ``wrangler_command`` is stripped
    (fail-closed: no copy of the lever survives a refused wave), and the CLI exits red.
    """
    staged = [
        o
        for o in report.offices
        if o.status == "ok" and o.result is not None and getattr(o.result, "wrangler_command", None)
    ]
    if not staged:
        return  # nothing staged this wave -> nothing to surface, nothing to guard.
    staged_slugs: dict[str, str] = {}
    for o in staged:
        slug = getattr(o.result, "slug", None)
        if isinstance(slug, str) and slug:
            staged_slugs[o.play_gid] = slug
    try:
        assert_deploy_root_ready(Path(deploy_base), manifest_path=deck_manifest)
        assert_wave_slugs_staged(Path(deploy_base), staged_slugs)
    except DeployRootRefused as exc:
        logger.error("floodgates_wave_deploy_refused", deploy_base=str(deploy_base), error=str(exc))
        report.deploy_refusal = str(exc)
        for o in staged:
            if o.result is not None:
                o.result.wrangler_command = None
        return
    # All offices of a wave share the root, so their surfaced commands are identical;
    # the wave-level command is that single command, surfaced exactly ONCE.
    report.wrangler_command = staged[0].result.wrangler_command if staged[0].result else None


# ------------------------------------------------------------------------------------ CLI


def _wave_halt_banner(report: BatchReport, *, deploy_base: Path) -> str:
    """The Phase-1 HALT banner: ONE reserved CF deploy lever for the WHOLE wave."""
    staged = [o.play_gid for o in report.ok if o.result is not None]
    return (
        f"\n[HALT — reserved operator lever] {len(staged)} deck(s) staged into the wave-shared "
        f"root {deploy_base}\n"
        "  Fire ONE CF deploy for the whole wave in the CF-authed env "
        "(memory scar: direnv exec ~/life):\n"
        f"    {report.wrangler_command}\n"
        "  Then confirm the decks render live and re-run Phase-2 per office:\n"
        "    python -m autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.batch"
        " --phase resume --office <play_gid> --execute\n"
    )


def _wave_refusal_banner(report: BatchReport, *, deploy_base: Path) -> str:
    """The LOUD fail-closed banner: the deploy-root guard refused; NO command is surfaced."""
    return (
        f"\n[REFUSED — no deploy command surfaced] wave-shared root {deploy_base} failed the "
        "fail-closed deploy-root guard:\n"
        f"  {report.deploy_refusal}\n"
        "  Reconcile the deploy root / deck-host ledger, then re-run --phase produce.\n"
    )


def _write_report(report: BatchReport, *, phase: str, deploy_base: Path) -> None:
    for office in report.offices:
        line = f"[{office.status}] {office.play_gid} outcome={office.outcome}"
        if office.error:
            line += f" — {office.error}"
        sys.stdout.write(line + "\n")
    if phase == "resume":
        for office in report.ok:
            previews = getattr(office.result, "previews", None) or {}
            if office.outcome == "dry_run" and previews:
                for name in ("link", "template", "card"):
                    sys.stdout.write(
                        f"\n--- {office.play_gid} {name} (exactly what --execute would post) ---\n"
                        f"{previews.get(name, '')}\n"
                    )
    if phase == "produce":
        # D10(b) receipts: which browser rendered each staged deck, and the outcome.
        for office in report.ok:
            receipt = getattr(office.result, "render_receipt", None)
            if receipt is not None:
                sys.stdout.write(f"[render] {office.play_gid} {receipt.line()}\n")
        if report.wrangler_command:
            sys.stdout.write(_wave_halt_banner(report, deploy_base=deploy_base))
        elif report.deploy_refusal:
            sys.stdout.write(_wave_refusal_banner(report, deploy_base=deploy_base))
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
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path(os.environ.get(STATE_DIR_ENV, ".sos/floodgates/state")),
        help=f"per-office state directory (env {STATE_DIR_ENV}); resolved to an absolute path.",
    )
    parser.add_argument(
        "--deploy-base",
        type=Path,
        default=Path(os.environ.get(DEPLOY_BASE_ENV, ".sos/floodgates/deploy")),
        help=(
            f"(env {DEPLOY_BASE_ENV}) the WAVE-SHARED accumulating deploy root — point it at the deck-host checkout's "
            "public/ for cross-wave accumulation (TDD §8). The wave-level wrangler command is "
            "surfaced only after the fail-closed deploy-root guard passes."
        ),
    )
    parser.add_argument(
        "--deck-manifest",
        type=Path,
        default=None,
        help=(
            "explicit deck-host ledger path for the no-orphan predicate; default "
            "<deploy-base>/../config/deck-manifest.json. A missing/unreadable ledger REFUSES "
            "the deploy surface (fail-closed)."
        ),
    )
    parser.add_argument("--producer-dir", type=Path, default=None)
    parser.add_argument(
        "--project-name",
        default=None,
        help="Cloudflare Pages project name (surfaced into the wrangler command; operator-domain).",
    )
    parser.add_argument(
        "--suggest-clinic",
        action="store_true",
        help=(
            "read-only: print the clinic name suggested by --office's PLAY title, then exit "
            "(no produce, no writes). Confirm it, then pass it to --clinic."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the Phase-2 PLAY-comment posts (the only mutating mode).",
    )
    args = parser.parse_args(argv)
    # Absolute paths: a relative default resolved against whatever cwd the operator ran from
    # silently forked state across directories (a second run minted a second deck).
    args.state_dir = args.state_dir.expanduser().resolve()
    args.deploy_base = args.deploy_base.expanduser().resolve()
    sys.stdout.write(f"state-dir: {args.state_dir}\ndeploy-base: {args.deploy_base}\n")

    clinic_map: dict[str, str] = {}
    if args.manifest is not None:
        raw = json.loads(args.manifest.read_text(encoding="utf-8"))
        clinic_map.update({str(k): str(v) for k, v in raw.items()})
    if args.office is not None and args.clinic is not None:
        clinic_map[args.office] = args.clinic

    if args.suggest_clinic:
        return _suggest_clinic(args.office)

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
                deck_manifest=args.deck_manifest,
                execute=args.execute,
            )

    report = asyncio.run(_run())
    _write_report(report, phase=args.phase, deploy_base=args.deploy_base)
    incomplete = _incomplete_offices(report, phase=args.phase, execute=args.execute)
    for gid, why in incomplete:
        sys.stdout.write(f"[INCOMPLETE] {gid} — {why}\n")
    skipped_scoped = bool(
        args.office is not None and any(o.status == "skipped_no_clinic" for o in report.skipped)
    )
    # RED when anything did not do what was asked: a failure, a refused wave, a skip of the
    # ONE office the operator named, or a "done" office with no contact card posted.
    return 1 if (report.failed or report.deploy_refusal or skipped_scoped or incomplete) else 0


def _suggest_clinic(office: str | None) -> int:
    """Print the PLAY title's suggested clinic name for ONE office (read-only)."""
    if office is None:
        sys.stdout.write("--suggest-clinic needs --office <play_gid>\n")
        return 2

    async def _name() -> str | None:
        async with AsanaClient() as client:
            task = await client.tasks.get_async(office, opt_fields=["name"])
            return getattr(task, "name", None)

    suggestion = clinic_from_play_name(asyncio.run(_name()))
    if suggestion is None:
        sys.stdout.write(f"{office}: no suggestion (title is not a PLAY with a clinic part)\n")
        return 1
    sys.stdout.write(f"{office}: suggested clinic: {suggestion}\n")
    return 0


def _incomplete_offices(report: BatchReport, *, phase: str, execute: bool) -> list[tuple[str, str]]:
    """Offices an executed resume left without a contact-card story (no holder/contacts)."""
    if phase != "resume" or not execute:
        return []
    out: list[tuple[str, str]] = []
    for office in report.ok:
        posts = getattr(office.result, "posts", None) or {}
        if not posts.get("card"):
            out.append(
                (office.play_gid, "no contact card posted (no holder or no usable contacts)")
            )
    return out


if __name__ == "__main__":
    sys.exit(main())
