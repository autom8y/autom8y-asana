"""Substrate-v2 — WU-4 WINDOW ENTRY RUNNER (opens the P5 live-parity window).

The in-repo operator tool that OPENS the window: one paced parity sweep per invocation,
then the PROV-2 in-process sweep (so ``EvaluatorHeartbeat`` emits), a one-screen JSON summary
for the session, and an exit code distinguishing {served, refusal, budget-halt, error}. It
wires the FINAL real seams onto the WU-3 arming (``substrate.live``) under the qa gate's seven
consolidated WU-4 entry conditions (QA-s8-2 receipt §5, PR #305 delta-gate):

  1. M-1 (BINDING) planner coverage — ``ManifestSectionPlanner`` derives ``covered_section_names``
     from the LIVE offer manifest actually fetched, gid->name reconciled; declared == actual by
     construction (a lying plan is unconstructable).
  2. ``min_build_instant`` (F-305-4) — scanned from the last SERVED receipt's build instant
     (fallback: the leg-2 baseline), threaded per touch.
  3. Arming via ``live.arm_offer_parity_window`` ONLY — fresh process, cap 11,200 pinned,
     ``{year}`` ledger path resolved at arming, single pinned charger.
  4. Real Asana call site as ``page_fetch`` — ``build_live_offer_page_fetch`` wraps the SAME
     client v1 uses (``AsanaHTTPClient.get_paginated("/tasks", section=gid)``), one page = one
     attempt = one budget charge; S3 reads / hash-CLEAN never route here (pythia §5).
  5. Interrupt classes — ``ParityBudgetExhausted`` / ``ParityLegRefused`` TERMINATE the sweep,
     recorded (the outbound receipts on every path), NEVER retried in-process.
  6. Dual-leg receipts are the daily HANDOFF substrate — LEG A ``served_active_mrr`` is the gate
     anchor; LEG B ``exemplar_aggregate`` is corpus-continuity ONLY.
  7. Torn-read residual — the equal-rowcount swap is guarded by monotonicity (#2); the S3-LIST
     cross-check is optional hardening (pythia-noted residual, not a blocker).

CARDINAL P10 boundary: ``run_window_sweep`` is fully injectable and its tests use fakes — ZERO
live Asana calls in tests. The FIRST live touch happens only when ``main()`` runs this in the
repo against real seams (WU-4 proper). Not imported by any deployed path; not in
``substrate.__init__``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from autom8_asana.substrate import live
from autom8_asana.substrate.observe import (
    SUBSTRATE_PROVABILITY_NAMESPACE,
    CloudWatchDataQualityEmitter,
)
from autom8_asana.substrate.prov_sweep import (
    PROV_ENVIRONMENT,
    build_prov_sweep_evaluator,
    run_prov_sweep,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

    from autom8_asana.dataframes.section_persistence import SectionInfo, SectionManifest
    from autom8_asana.substrate.identity import ArtifactId
    from autom8_asana.substrate.observe import ExpectedSetSource
    from autom8_asana.substrate.rebuild import NowFn, SlaResolver
    from autom8_asana.substrate.store import ArtifactStore, S3ArtifactStore

__all__ = [
    "LEG2_BASELINE_BUILD_INSTANT",
    "ManifestSectionPlanner",
    "NoOfferManifestError",
    "SectionPersistenceManifestSource",
    "SweepExit",
    "SweepSummary",
    "build_live_offer_page_fetch",
    "run_window_sweep",
    "scan_last_served_build_instant",
]

# Fallback generation floor when NO served receipt yet exists (the O4 leg-2 baseline build
# instant, RECEIPT-s8-0-fixture-recapture L189). Monotonicity (§F-305-4) starts here.
LEG2_BASELINE_BUILD_INSTANT: datetime = datetime(2026, 8, 3, 16, 12, 41, 349255, tzinfo=UTC)


class SweepExit(IntEnum):
    """Process exit code — the session distinguishes sweep outcomes without parsing text."""

    SERVED = 0  # a served ParityObservation (both legs computed)
    REFUSAL = 10  # ParityLegRefused (fetch-refused / staged-rejected / coverage) — first-class
    BUDGET_HALT = 20  # ParityBudgetExhausted — charter L81 operator interrupt
    ERROR = 30  # any other failure (torn-read, column-missing, unexpected)


_EXIT_BY_OUTCOME: dict[str, SweepExit] = {
    "served": SweepExit.SERVED,
    "budget-halt": SweepExit.BUDGET_HALT,
    "error": SweepExit.ERROR,
}


def _exit_for_outcome(outcome: str) -> SweepExit:
    if outcome.startswith("refused-"):
        return SweepExit.REFUSAL
    return _EXIT_BY_OUTCOME.get(outcome, SweepExit.ERROR)


# ===========================================================================
# M-1 (BINDING) — the manifest-derived planner: declared coverage == actually fetched
# ===========================================================================


class NoOfferManifestError(RuntimeError):
    """No live offer manifest exists — coverage is unprovable, so REFUSE (never a static list).

    The M-1 contract makes ``covered_section_names`` derive from the live listing; with NO
    listing there is nothing to reconcile, and declaring coverage would be the exact static-
    declaration the ruling forbids. Fail loud rather than fabricate a coverage claim.
    """


class ManifestSource(Protocol):
    """Where the runner reads the LIVE offer section listing (S3-read; NO Asana charge)."""

    async def get_offer_manifest(self, project_gid: str) -> SectionManifest | None:
        """The offer plane's ``SectionManifest`` (``dataframes/{project}/offer/manifest.json``)."""
        ...


@dataclass(frozen=True, slots=True)
class SectionPersistenceManifestSource:
    """Prod ``ManifestSource``: the offer manifest the v1 pipeline itself maintains.

    Reuses ``SectionPersistence.get_manifest_async(project, "offer")`` — the SAME machinery the
    v1 warmer writes — so the runner's listing IS the pipeline's listing (no parallel source of
    truth). S3 GET only; never touches Asana.
    """

    persistence: Any  # dataframes.section_persistence.SectionPersistence

    async def get_offer_manifest(self, project_gid: str) -> SectionManifest | None:
        manifest: SectionManifest | None = await self.persistence.get_manifest_async(
            project_gid, entity_type="offer"
        )
        return manifest


# (gid, info) -> True to FETCH this section, False to SKIP it entirely. Default fetches every
# listed section (complete + safe). Injectable for tests (the M-1 two-sided proof) and a future
# hash-CLEAN reuse optimization (a skipped section is neither fetched NOR declared covered).
if TYPE_CHECKING:
    SectionFetchDecider = Callable[[str, SectionInfo], bool]


def _fetch_all(_gid: str, _info: SectionInfo) -> bool:
    return True


@dataclass(frozen=True, slots=True)
class ManifestSectionPlanner:
    """M-1 (BINDING): derive the ``OfferSectionPlan`` from the LIVE offer manifest.

    **Derivation chain** (own-hands, S3-read, ZERO Asana charge):
    ``SectionPersistence.get_manifest_async(project, "offer")`` ->
    ``SectionManifest.sections {gid: SectionInfo(name, ...)}`` (the v1 pipeline's own listing) ->
    ONE pass: for every gid the decider FETCHES, add ``info.name.lower()`` to
    ``covered_section_names`` AND its gid to ``refetch`` ->
    ``OfferSectionPlan(refetch, reuse={}, covered_section_names=covered)``.

    **Why this closes the M-1 declared-vs-actual gap by construction:** ``covered`` and
    ``refetch`` are built in the SAME iteration from the SAME manifest — a section can be
    declared covered ONLY by having its gid put into the fetch plan in the same step. A lying
    plan (declares coverage of a section it does not fetch) is therefore unconstructable. A
    classifier-active section ABSENT from the manifest, or null-named, is not in ``covered`` ->
    ``live.assert_plan_covers_active_set`` (called in the fetcher BEFORE any charge) refuses
    loudly. Post-cutover, coverage moves to the serve-time provability predicate (PT-03/S9).
    """

    source: ManifestSource
    decider: Any = _fetch_all  # SectionFetchDecider

    async def plan(self, aid: ArtifactId) -> live.OfferSectionPlan:
        manifest = await self.source.get_offer_manifest(aid.project_gid)
        if manifest is None:
            raise NoOfferManifestError(
                f"no offer manifest for project {aid.project_gid} — coverage is unprovable; "
                "refusing to declare a static coverage claim (M-1)"
            )
        covered: set[str] = set()
        refetch: list[str] = []
        for gid, info in manifest.sections.items():
            if not self.decider(gid, info):
                continue  # SKIP: neither fetched nor declared covered (M-1 fail-closed)
            refetch.append(gid)
            if info.name:  # null-named -> fetched but NOT attributable -> not in covered
                covered.add(info.name.lower())
        return live.OfferSectionPlan(
            refetch=tuple(refetch), reuse={}, covered_section_names=frozenset(covered)
        )


# ===========================================================================
# min_build_instant — the generation-monotonicity floor from the last served receipt (F-305-4)
# ===========================================================================


def scan_last_served_build_instant(
    receipts_root: Path, *, fallback: datetime = LEG2_BASELINE_BUILD_INSTANT
) -> datetime:
    """The build instant of the most-recent SERVED receipt (or ``fallback`` if none).

    Scans ``{receipts_root}/**/*.json`` for ``outcome == "served"`` and returns the greatest
    ``built_from_live_at`` seen — the monotonicity floor the next capture must not regress below
    (an equal-rowcount generation swap is thereby refused, §F-305-4). Only SERVED receipts count
    (a refusal/error/budget-halt did not advance the served generation). Malformed receipts are
    skipped, not fatal.
    """
    latest: datetime | None = None
    if receipts_root.exists():
        for path in receipts_root.rglob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if payload.get("outcome") != "served":
                continue
            raw = payload.get("built_from_live_at")
            if not isinstance(raw, str):
                continue
            try:
                instant = datetime.fromisoformat(raw)
            except ValueError:
                continue
            if instant.tzinfo is not None and (latest is None or instant > latest):
                latest = instant
    return latest if latest is not None else fallback


# ===========================================================================
# Real Asana page adapter (condition 4) — one get_paginated per page = one budget charge
# ===========================================================================


class PaginatedHttp(Protocol):
    """The paginated GET surface of the SAME Asana client the v1 pipeline uses."""

    async def get_paginated(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        """One page: ``(tasks, next_offset)`` — the v1 idiom (clients/tasks.py:614-627)."""
        ...


def build_live_offer_page_fetch(
    http: PaginatedHttp,
    *,
    to_offer_row: Callable[[Mapping[str, Any]], dict[str, Any]],
    opt_fields: str,
) -> Callable[[ArtifactId, str, str | None], Awaitable[tuple[list[Mapping[str, Any]], str | None]]]:
    """The REAL Asana call site (condition 4): ONE ``get_paginated`` per pagination page.

    Wraps ``http.get_paginated("/tasks", params={"section": gid, "offset": cursor, "opt_fields":
    ...})`` — the SAME client + endpoint the v1 warmer uses. The 3b fetcher charges the budget
    once per invocation of this callable, so each pagination page is exactly one attempt (429s
    and retried pages each charge; hash-CLEAN verifies and S3 reads never route here, so they
    never charge — pythia §5). ``to_offer_row`` maps each Asana task to the offer row schema
    ``(section, mrr, office_phone, vertical, cost, offer_id, weekly_ad_spend)`` — the v1 builder
    transform WU-4 supplies (its live fidelity is exercised on the first window run, not in
    tests).
    """

    async def _page_fetch(
        aid: ArtifactId, section_gid: str, cursor: str | None
    ) -> tuple[list[Mapping[str, Any]], str | None]:
        params: dict[str, Any] = {"section": section_gid, "opt_fields": opt_fields}
        if cursor is not None:
            params["offset"] = cursor
        tasks, next_cursor = await http.get_paginated("/tasks", params=params)
        rows: list[Mapping[str, Any]] = [to_offer_row(task) for task in tasks]
        return rows, next_cursor

    return _page_fetch


# ===========================================================================
# The sweep — one paced parity sweep + the PROV-2 sweep + a JSON summary (conditions 5/6/7)
# ===========================================================================


@dataclass(frozen=True, slots=True)
class SweepSummary:
    """The one-screen sweep result the session consumes + appends to the daily HANDOFF."""

    outcome: str
    exit_code: int
    parity: dict[str, Any]
    prov: dict[str, Any]
    budget: dict[str, Any]
    receipts_written: list[str] = field(default_factory=list)
    min_build_instant: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "outcome": self.outcome,
                "exit_code": self.exit_code,
                "min_build_instant": self.min_build_instant,
                "parity": self.parity,
                "prov": self.prov,
                "budget": self.budget,
                "receipts_written": self.receipts_written,
            },
            indent=2,
            sort_keys=True,
        )


def _receipt_paths(receipts_root: Path) -> set[Path]:
    return set(receipts_root.rglob("*.json")) if receipts_root.exists() else set()


async def run_window_sweep(
    *,
    bucket: str,
    page_fetch: Callable[
        [ArtifactId, str, str | None], Awaitable[tuple[list[Mapping[str, Any]], str | None]]
    ],
    manifest_source: ManifestSource,
    v2_store: S3ArtifactStore,
    expected_set: ExpectedSetSource,
    prov_store: ArtifactStore | None = None,
    cw_client: Any = None,
    region: str = "us-east-1",
    cap: int = live.DEFAULT_DAILY_BUDGET_CAP,
    ledger_path: Path | None = None,
    receipts_root: Path | None = None,
    decider: Any = _fetch_all,
    now: NowFn | None = None,
    sla_for: SlaResolver | None = None,
) -> SweepSummary:
    """Run ONE paced parity sweep then the PROV-2 sweep; return the JSON-able summary.

    Fully injectable (fakes in tests; ZERO live network). ``main()`` supplies the real seams.
    The parity outcome is read from the receipt the outbound writes on EVERY path (condition 6),
    so refusal/budget-halt/error are first-class recorded outcomes, never in-process retried
    (condition 5). Runs the PROV sweep regardless (PROV-2's clear depends on the heartbeat).
    """
    from tests.harness.substrate_gate.parity import reset_process_fetcher

    resolved_receipts_root = (
        receipts_root if receipts_root is not None else Path.cwd() / live.PARITY_RECEIPTS_ROOT
    )
    min_build = scan_last_served_build_instant(resolved_receipts_root)
    planner = ManifestSectionPlanner(source=manifest_source, decider=decider)

    reset_process_fetcher()  # fresh-process semantics: this invocation owns the singleton
    window = live.arm_offer_parity_window(
        bucket=bucket,
        page_fetch=page_fetch,
        plan=planner.plan,
        store=v2_store,
        region=region,
        cap=cap,
        ledger_path=ledger_path,
        receipts_root=resolved_receipts_root,
        now=now,
        sla_for=sla_for,
        min_build_instant=min_build,
        # PROV-7 sink for the tiered floor's warn tier — the SAME injected ``cw_client``
        # the PROV sweep uses, so a fake client keeps the whole sweep network-free.
        data_quality_emitter=CloudWatchDataQualityEmitter(
            environment=PROV_ENVIRONMENT, cw_client=cw_client
        ),
    )

    parity, exit_code, new_receipts = await _run_parity(window, resolved_receipts_root)
    prov = await _run_prov(
        prov_store if prov_store is not None else v2_store, expected_set, cw_client, now
    )

    return SweepSummary(
        outcome=parity["outcome"],
        exit_code=int(exit_code),
        parity=parity,
        prov=prov,
        budget={"count_today": window.ledger.count_today(), "cap": window.ledger.cap},
        receipts_written=new_receipts,
        min_build_instant=min_build.isoformat(),
    )


async def _run_parity(
    window: live.ArmedParityWindow, receipts_root: Path
) -> tuple[dict[str, Any], SweepExit, list[str]]:
    """Drive the paced sweep; classify from the receipt written this sweep (condition 6)."""
    before = _receipt_paths(receipts_root)
    served_obs = None
    try:
        results = await window.source.fetch_all_paced([live.offer_aid()])
        served_obs = results[0] if results else None
    except Exception:  # noqa: BLE001 — interrupts terminate the sweep; the outbound already receipted
        served_obs = None

    new_paths = sorted(_receipt_paths(receipts_root) - before)
    new_names = [p.name for p in new_paths]
    if not new_paths:
        return (
            {"outcome": "error", "detail": "no receipt written for the touch (unexpected)"},
            SweepExit.ERROR,
            new_names,
        )

    payload = json.loads(new_paths[-1].read_text(encoding="utf-8"))
    outcome = str(payload.get("outcome", "error"))
    parity: dict[str, Any] = {
        "outcome": outcome,
        "receipt": new_paths[-1].name,
        "legs": payload.get("legs"),
        "detail": payload.get("detail", ""),
        # Per-offer demoted-column nulls (digest item 2) — carried onto the one-screen
        # summary so the daily HANDOFF digest names each wounded offer, not just a count.
        "data_quality_warnings": payload.get("data_quality_warnings"),
    }
    if served_obs is not None:
        parity["observation"] = {
            "v1_plane": served_obs.v1.plane,
            "v1_served_active_mrr": served_obs.v1.served_value,
            "v2_plane": served_obs.v2.plane,
            "v2_served_active_mrr": served_obs.v2.served_value,
        }
    return parity, _exit_for_outcome(outcome), new_names


async def _run_prov(
    store: ArtifactStore, expected_set: ExpectedSetSource, cw_client: Any, now: NowFn | None
) -> dict[str, Any]:
    """Drive the PROV-2 in-process sweep so ``EvaluatorHeartbeat`` emits (PROV-2 clear)."""
    evaluator = build_prov_sweep_evaluator(
        store=store, expected_set=expected_set, cw_client=cw_client
    )
    run = await run_prov_sweep(evaluator, now=now() if now is not None else None)
    return {
        "run_id": run.run_id,
        "namespace": SUBSTRATE_PROVABILITY_NAMESPACE,
        "environment": PROV_ENVIRONMENT,
        "heartbeat_emitted": True,
        "expected_count": run.expected_count,
        "evaluated_count": run.evaluated_count,
        "unprovable_count": run.unprovable_count,
        "completeness": run.completeness,
        "expected_set_mismatch_count": run.expected_set_mismatch_count,
    }


# ===========================================================================
# CLI entry (the WU-4 live invocation shell — real-seam assembly is operator-supplied)
# ===========================================================================


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - live wiring, exercised at WU-4
    r"""CLI shell for the WU-4 window run — refuses until the runbook supplies the real seams.

    ``run_window_sweep`` above IS the tested WU-4 composition point (all seams injected). The
    WU-4 daily-window runbook calls it with the real seams, e.g.::

        v1_storage = S3DataFrameStorage(location=S3LocationConfig(bucket="autom8-s3"))
        summary = await run_window_sweep(
            bucket="autom8-s3",
            manifest_source=SectionPersistenceManifestSource(SectionPersistence(v1_storage)),
            page_fetch=build_live_offer_page_fetch(real_asana_http_client,
                                                   to_offer_row=v1_task_to_offer_row,
                                                   opt_fields=OFFER_OPT_FIELDS),
            v2_store=S3ArtifactStore("<v2-bucket>"),
            expected_set=registry_targets_union_dataframes_v2_enumeration,
        )
        print(summary.to_json()); raise SystemExit(summary.exit_code)

    The three operator-supplied live-fidelity hooks — the real Asana client, the task->offer-row
    transform (v1 builder), and the PROV expected-set (entity registry union dataframes-v2/
    enumeration) — carry live customer PII and Asana credentials, so they are assembled in the
    runbook (never fabricated here). A wiring gap fails LOUDLY (M-1 refuses coverage; the served
    leg refuses) — never a silent wrong-serve.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Open the substrate-v2 live-parity window (one sweep). See the main() runbook."
    )
    parser.parse_args(argv)
    raise NotImplementedError(
        "the WU-4 live seams (Asana client + task->offer-row transform + PROV expected-set) are "
        "assembled per the daily window runbook (main() docstring); run_window_sweep is the "
        "tested composition point the runbook calls with those real seams"
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
