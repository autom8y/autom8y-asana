"""Substrate-v2 — LIVE PARITY ARMING (WU-3 of RULING-potnia-s8-2-wave-entry-2026-08-03).

This module is the **in-repo operator tool** that ARMS the live-parity window (P5). It
is prod WIRING — not harness scaffolding, not a deployed service — that composes the
already-FROZEN seams into the minimal live-number path (G1: minimal path only; NO
general-purpose rebuild framework). It is deliberately kept OUT of
``substrate.__init__`` and is never imported by any deployed code path: it consumes the
cutover-gate harness (``tests.harness.substrate_gate``), which by the S7 design is the
parity substrate and lives under ``tests/`` — so this tool runs from the repo tree
(where the harness is importable), exactly as the WU-1 own-hands probe did. The FIRST
live Asana touch is WU-4 (window open); this module is proven DARK with injected fakes
at the HTTP boundary (CARDINAL P10 boundary: zero live Asana calls in build or test).

Five minimal units (each P7-gated):

* **3a** ``build_v1_offer_materialization`` — the CURRENT v1 offer plane (S3-read-only)
  as a harness ``Materialization``, with the RECEIPT-s8-0 torn-read guard (refuse loud,
  never a silent partial). Reads ``dataframes/{project}/offer/{dataframe.parquet,
  watermark.json}``; recomputes ``active_mrr`` over the three offer-lifecycle sections
  the O4 receipts pin ({ACTIVE, OPTIMIZE - Human Review, STAGED}).
* **3b** ``PacedOfferSectionFetcher`` + ``rebuild_offer_v2`` — the concrete
  ``PacedAsanaFetcher`` composing v1's G6 controllers (floor-gate admit -> AIMD slot ->
  retry -> bounded gather) around the Asana HTTP boundary, charging the hardened
  ``PerDayBudgetLedger`` per pagination-page ATTEMPT (429s + retries charge; reused/
  hash-CLEAN sections and S3 ops NEVER charge — pythia §5 counsel), threaded into a
  ``SubstrateRebuilder.rebuild()`` caller.
* **3c** ``build_parity_outbound`` / ``arm_process_parity_fetcher`` — the concrete armed
  ``outbound`` for ``PacedLiveParitySource`` (v1 from 3a, v2 from 3b), armed through the
  process singleton ``get_process_fetcher`` (never a second instance).
* **3d** ``ParityReceiptWriter`` — one durable JSON receipt per prod touch (P10 "leave a
  receipt"): ``FetchTelemetry`` + budget state + timestamps + outcome; a
  ``ParityBudgetExhausted`` is RECORDED as ``outcome=budget-halt`` and NEVER retried.

Seam discipline: this is seam-USE. No frozen seam (``rebuild.py`` /
``parity.py`` Protocols, ``RebuildOutcome`` / ``RebuildResult``) is changed — arming an
already-designed dark seam is seam-USE per the ruling's back-route.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

import polars as pl

from autom8_asana.config import BudgetAllocatorConfig
from autom8_asana.core.concurrency import gather_with_semaphore
from autom8_asana.core.retry import (
    BudgetConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    DefaultRetryPolicy,
    RetryBudget,
    RetryOrchestrator,
    RetryPolicyConfig,
    Subsystem,
)
from autom8_asana.core.types import EntityType
from autom8_asana.errors import RateLimitError
from autom8_asana.substrate.freshness import (
    FreshnessProof,
    fold_built_from_live_at,
    sla_seconds_for,
)
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.rebuild import (
    DefaultAcceptancePredicates,
    FetchedSections,
    FetchTelemetry,
    RebuildResult,
    SubstrateRebuilder,
)
from autom8_asana.transport.adaptive_semaphore import AIMDConfig, AsyncAdaptiveSemaphore
from autom8_asana.transport.budget_allocator import BudgetAllocator

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

    from tests.harness.substrate_gate.budget import PerDayBudgetLedger
    from tests.harness.substrate_gate.cases import Materialization
    from tests.harness.substrate_gate.parity import PacedLiveParitySource, ParityObservation

    from autom8_asana.substrate.rebuild import NowFn, SlaResolver
    from autom8_asana.substrate.store import S3ArtifactStore

# ---------------------------------------------------------------------------
# Shared offer-plane constants (pinned to the O4 receipts + exemplar #2)
# ---------------------------------------------------------------------------

# The offer project whose active_mrr the parity gate re-derives (DEFECT :20-23; O4).
OFFER_PROJECT_GID: str = "1143843662099250"

# active_mrr = Σ mrr over the THREE offer-lifecycle sections the O4 leg-1/leg-2 receipts
# pin (RECEIPT-s8-0-fixture-recapture L86-96 / L223-231; exemplar_two_materialization).
# The section name is a plain HYPHEN (U+002D) in prod bytes — NOT an en-dash. This is the
# receipted active_mrr definition for the substrate-v2 exemplar; it is deliberately
# NARROWER than metrics.freshness' 22-section classifier active-set (a different signal
# that shares the name) — the parity gate compares against the pinned exemplar, so the
# exemplar's definition is the one this constructor reproduces.
ACTIVE_MRR_SECTIONS: tuple[str, ...] = ("ACTIVE", "OPTIMIZE - Human Review", "STAGED")

_V1_OFFER_PLANE: str = "v1/offer"


class TornOfferPlaneRead(RuntimeError):
    """The v1 offer plane read is internally inconsistent — REFUSE loud, never a partial.

    Raised by ``materialize_v1_offer_plane`` when ``dataframe.parquet`` and
    ``watermark.json`` do not form an internally-consistent, non-torn set (a malformed
    watermark, a wrong-project watermark, a build instant that post-dates its own
    save, or a frame whose row count disagrees with the watermark — the two objects
    are then from different generations). Mirrors the RECEIPT-s8-0 torn-read guard:
    accept a snapshot ONLY when it is internally consistent; otherwise a human decides
    (refuse > wrong, charter P2). A charge is never levied — this is an S3 read.
    """


def _parse_aware(raw: object, label: str) -> datetime:
    """Parse an ISO-8601 instant to a tz-aware UTC datetime, or raise ``TornOfferPlaneRead``."""
    if not isinstance(raw, str):
        raise TornOfferPlaneRead(f"watermark {label} is not an ISO-8601 string: {raw!r}")
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise TornOfferPlaneRead(f"watermark {label} is not parseable: {raw!r} ({exc})") from exc
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise TornOfferPlaneRead(f"watermark {label} is not tz-aware: {raw!r}")
    return moment


def _composition_digest(composition: Mapping[str, tuple[int, float]]) -> str:
    """The O4 receipts' drift-tripwire digest: sha256 over sorted ``{section:[rows,value]}``.

    Same S3 bytes -> same aggregate -> same digest (RECEIPT L93-96). Reproduces the
    exemplar #2 ``content_digest`` exactly, so a determinism test can assert the
    constructor re-derives the pinned digest from the fixture bytes.
    """
    canonical = json.dumps(
        {section: list(cell) for section, cell in sorted(composition.items())},
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def materialize_v1_offer_plane(
    parquet_bytes: bytes,
    watermark_bytes: bytes,
    *,
    project_gid: str = OFFER_PROJECT_GID,
    active_sections: tuple[str, ...] = ACTIVE_MRR_SECTIONS,
    plane: str = _V1_OFFER_PLANE,
    sla_seconds: int | None = None,
) -> Materialization:
    """3a (pure): build a v1-side ``Materialization`` from raw offer-plane bytes.

    S3-read-only in prod (the bytes are a GET of ``dataframe.parquet`` + ``watermark.json``);
    this pure core takes the bytes so it is fully provable offline with fixture bytes (no
    I/O, no network — CARDINAL P10 boundary). Applies the RECEIPT-s8-0 torn-read guard,
    then recomputes ``active_mrr`` over ``active_sections`` and packages the coherent
    current state as a harness ``Materialization`` (``frame_digest == content_digest`` —
    a healthy, non-corrupt plane).

    Raises ``TornOfferPlaneRead`` on ANY inconsistency (never a silent partial).
    """
    # ---- watermark: parse + internal-consistency (torn-read) guard -------------
    try:
        watermark = json.loads(watermark_bytes)
    except json.JSONDecodeError as exc:
        raise TornOfferPlaneRead(f"watermark.json is not valid JSON: {exc}") from exc
    if not isinstance(watermark, dict):
        raise TornOfferPlaneRead(f"watermark.json is not a JSON object: {type(watermark).__name__}")

    wm_project = watermark.get("project_gid")
    if str(wm_project) != project_gid:
        raise TornOfferPlaneRead(
            f"watermark project_gid {wm_project!r} != requested {project_gid!r} — "
            "the parquet and watermark are not the same plane"
        )
    built_at = _parse_aware(watermark.get("watermark"), "watermark (build instant)")
    saved_at = _parse_aware(watermark.get("saved_at"), "saved_at")
    if built_at > saved_at:
        raise TornOfferPlaneRead(
            f"watermark build instant {built_at.isoformat()} post-dates its own save "
            f"{saved_at.isoformat()} — internally inconsistent (torn write)"
        )
    row_count = watermark.get("row_count")
    if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 0:
        raise TornOfferPlaneRead(f"watermark row_count is not a non-negative int: {row_count!r}")

    # ---- frame: parse + cross-check the row count against the watermark --------
    try:
        frame = pl.read_parquet(parquet_bytes)
    except Exception as exc:  # noqa: BLE001 — an unreadable parquet is a loud torn/corrupt read
        raise TornOfferPlaneRead(f"offer dataframe.parquet is unreadable: {exc!r}") from exc
    if frame.height != row_count:
        raise TornOfferPlaneRead(
            f"frame row count {frame.height} != watermark row_count {row_count} — "
            "the parquet and watermark are from different generations (torn read)"
        )
    for required in ("section", "mrr"):
        if required not in frame.columns:
            raise TornOfferPlaneRead(
                f"offer dataframe.parquet lacks required column {required!r} "
                f"(has {sorted(frame.columns)})"
            )

    resolved_sla = sla_seconds if sla_seconds is not None else sla_seconds_for(EntityType.OFFER)
    return offer_materialization_from_frame(
        plane=plane,
        frame=frame,
        built_from_live_at=built_at,
        sla_seconds=resolved_sla,
        active_sections=active_sections,
    )


def offer_materialization_from_frame(
    *,
    plane: str,
    frame: pl.DataFrame,
    built_from_live_at: datetime,
    sla_seconds: int,
    active_sections: tuple[str, ...] = ACTIVE_MRR_SECTIONS,
) -> Materialization:
    """Compose an offer ``Materialization`` (active_mrr) from an assembled frame.

    ONE source of truth for the active_mrr composition math, shared by the v1 S3 read
    (3a) and the v2 rebuild (3c) so both planes are apples-to-apples. Groups ``mrr`` by
    ``section`` over the pinned in-scope sections, mints the drift-tripwire composition
    digest, and packages a coherent (``frame_digest == content_digest``) plane.
    """
    from tests.harness.substrate_gate.cases import Materialization, SectionCell

    grouped = (
        frame.filter(pl.col("section").is_in(list(active_sections)))
        .group_by("section")
        .agg(pl.len().alias("rows"), pl.col("mrr").sum().alias("mrr"))
        .sort("section")
    )
    raw_cells: dict[str, tuple[int, float]] = {
        row["section"]: (int(row["rows"]), float(row["mrr"])) for row in grouped.to_dicts()
    }
    composition = {section: SectionCell(rows=r, value=v) for section, (r, v) in raw_cells.items()}
    served_value = round(sum(v for _r, v in raw_cells.values()), 6)
    digest = _composition_digest(raw_cells)
    return Materialization(
        plane=plane,
        proof=FreshnessProof(
            built_from_live_at=built_from_live_at, content_digest=digest, sla_seconds=sla_seconds
        ),
        served_value=served_value,
        composition=composition,
        frame_digest=digest,  # digest-consistent: coherent current state, NOT corrupt
    )


@dataclass(frozen=True, slots=True)
class S3OfferPlaneReader:
    """S3-read-only reader for the CURRENT v1 offer plane (``dataframes/{project}/offer/``).

    Mirrors the house lazy-boto3 + injectable-client pattern (``S3ArtifactStore``): a real
    ``boto3`` S3 client is built on first use; tests inject a fake/moto client. Reads the
    two objects the O4 receipt names — ``dataframe.parquet`` + ``watermark.json`` — and
    NOTHING else (no section fan, no write, no warm trigger). GET-only; never charges the
    Asana budget (S3 is not the 429-storm surface — pythia §5).
    """

    bucket: str
    region: str = "us-east-1"
    client: Any = None
    _prefix: str = field(default="dataframes", kw_only=True)

    def _s3(self) -> Any:
        if self.client is not None:
            return self.client
        import boto3

        return boto3.client("s3", region_name=self.region)

    def _key(self, project_gid: str, obj: str) -> str:
        return f"{self._prefix}/{project_gid}/offer/{obj}"

    def read(self, project_gid: str = OFFER_PROJECT_GID) -> tuple[bytes, bytes]:
        """GET ``(dataframe.parquet, watermark.json)`` bytes for the offer plane."""
        client = self._s3()
        parquet = client.get_object(
            Bucket=self.bucket, Key=self._key(project_gid, "dataframe.parquet")
        )["Body"].read()
        watermark = client.get_object(
            Bucket=self.bucket, Key=self._key(project_gid, "watermark.json")
        )["Body"].read()
        return parquet, watermark


def build_v1_offer_materialization(
    reader: S3OfferPlaneReader,
    *,
    project_gid: str = OFFER_PROJECT_GID,
) -> Materialization:
    """3a (prod): read the S3 offer plane via ``reader`` and materialize the v1 side."""
    parquet_bytes, watermark_bytes = reader.read(project_gid)
    return materialize_v1_offer_plane(parquet_bytes, watermark_bytes, project_gid=project_gid)


# ===========================================================================
# 3b — concrete PacedAsanaFetcher (real pacing composition) + rebuild caller
# ===========================================================================

# The Asana HTTP boundary: ONE call == ONE pagination page == ONE budget-charged attempt
# (aid, section_gid, cursor) -> (value_rows, next_cursor). In prod this is backed by the
# real Asana client (``AsanaHTTPClient.get_paginated`` mapped to value rows); in build/test
# it is a fake (CARDINAL P10 boundary: zero live Asana calls). A 429 raised here shrinks the
# AIMD window and charges the budget for that attempt (pythia §5: count attempts, not
# successes — a 429-storm is composed of FAILED attempts).
if TYPE_CHECKING:
    PageFetch = Callable[
        [ArtifactId, str, "str | None"], Awaitable[tuple[list[Mapping[str, Any]], "str | None"]]
    ]
    PlanFn = Callable[[ArtifactId], Awaitable["OfferSectionPlan"]]


class OfferSectionFetchError(RuntimeError):
    """A section's paced live fetch exhausted its retries — the rebuild will FETCH_REFUSED.

    Distinct from ``ParityBudgetExhausted`` (a per-day HALT that propagates) — this is a
    per-section failure the fetcher records in ``FetchedSections.failed_sections`` so C16
    completeness-by-construction refuses the partial rather than swapping it (rebuild.py
    ``_completeness_gap``). The incumbent is untouched (partial != corrupt, RC-E).
    """


@dataclass(frozen=True, slots=True)
class ReusedSection:
    """A hash-CLEAN section carried WITHOUT a live fetch (pythia §5: reuse never charges).

    ``instant`` is its PRIOR content-fetch instant (honestly drags the artifact's age back
    to its stalest section via the S2 MIN-fold); ``rows`` are its prior value rows, so the
    assembled frame is WHOLE (fetched ∪ reused) without a re-fetch or an S3-count proxy.
    """

    instant: datetime
    rows: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class OfferSectionPlan:
    """The minimal per-artifact fetch plan (G1: only what the ledger requires).

    ``refetch`` are the section gids to pull LIVE (each pagination page charges the budget);
    ``reuse`` are hash-CLEAN sections carried from the prior frame (never charge). The union
    is the C16 ``requested_sections``. In prod the plan comes from the staleness/hash-CLEAN
    probe + prior-frame read (S3, no charge — a WU-4 wiring); in build/test it is injected.
    """

    refetch: tuple[str, ...]
    reuse: Mapping[str, ReusedSection] = field(default_factory=dict)


@dataclass(slots=True)
class _TelemetryAccum:
    """Mutable per-fetch accountant folded into an immutable ``FetchTelemetry`` at the end.

    asyncio is single-threaded and every increment sits between awaits, so concurrent
    section tasks accumulate without a lock.
    """

    requests_issued: int = 0  # every HTTP page ATTEMPT at the boundary (success + 429)
    http_429_count: int = 0
    pages_succeeded: int = 0
    sections_refetched: int = 0
    sections_reused: int = 0

    def finalize(self) -> FetchTelemetry:
        # A retry is an attempt beyond the first success for a page: retries = attempts - pages.
        return FetchTelemetry(
            requests_issued=self.requests_issued,
            http_429_count=self.http_429_count,
            retries_issued=max(0, self.requests_issued - self.pages_succeeded),
            sections_refetched=self.sections_refetched,
            sections_reused=self.sections_reused,
        )


def _is_rate_limit_signal(exc: BaseException) -> bool:
    """True for a 429 the AIMD window must react to (mirrors ``parity._is_rate_limit_signal``)."""
    return isinstance(exc, RateLimitError) or getattr(exc, "status_code", None) == 429


def _build_retry_orchestrator(name: str) -> RetryOrchestrator:
    budget = RetryBudget(BudgetConfig())
    breaker = CircuitBreaker(CircuitBreakerConfig(name=name), budget=budget)
    policy = DefaultRetryPolicy(RetryPolicyConfig())
    return RetryOrchestrator(policy, budget, breaker, Subsystem.HTTP)


class PacedOfferSectionFetcher:
    """Concrete ``PacedAsanaFetcher`` (rebuild.py) — the REAL v1-G6 pacing composition.

    Per refetched section: ``floor_gate.admit()`` (advisory static floor) ->
    ``semaphore.acquire()`` (AIMD slot) -> per-page ``retry.execute_with_retry_async(...)``
    (resilience) around the injected HTTP boundary; sections fan out through
    ``gather_with_semaphore`` (bounded concurrency). Every page ATTEMPT charges the injected
    ``PerDayBudgetLedger`` BEFORE the call (a 429'd/retried attempt still spent its unit —
    pythia §5); reused/hash-CLEAN sections and the frame assembly touch no boundary and
    never charge. Structurally implements the frozen Protocol; imports NO ``AsanaClient``
    (RC-E-4) — the only Asana surface is the injected ``page_fetch``.
    """

    def __init__(
        self,
        *,
        page_fetch: PageFetch,
        plan: PlanFn,
        budget: PerDayBudgetLedger,
        concurrency: int = 5,
        aimd_ceiling: int = 10,
        now: NowFn | None = None,
        gate_clock: Callable[[], float] | None = None,
        gate_sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._page_fetch = page_fetch
        self._plan = plan
        self._budget = budget
        self._concurrency = concurrency
        self._semaphore = AsyncAdaptiveSemaphore(
            AIMDConfig(ceiling=aimd_ceiling), name="substrate_offer_fetch"
        )
        self._allocator = BudgetAllocator(BudgetAllocatorConfig())
        self._floor_gate = self._allocator.warmer_floor_gate(clock=gate_clock, sleep=gate_sleep)
        self._retry = _build_retry_orchestrator("substrate_offer_fetch")
        self._now: NowFn = now if now is not None else (lambda: datetime.now(UTC))

    def routes_through_paced_primitives(self) -> bool:
        """Structural self-check: genuinely wired through all four v1 primitives (RC-E-4)."""
        return (
            isinstance(self._semaphore, AsyncAdaptiveSemaphore)
            and self._floor_gate is not None
            and isinstance(self._retry, RetryOrchestrator)
        )

    async def _attempt_page(
        self,
        aid: ArtifactId,
        section_gid: str,
        cursor: str | None,
        slot: Any,
        telem: _TelemetryAccum,
    ) -> tuple[list[Mapping[str, Any]], str | None]:
        """ONE HTTP page attempt at the boundary (the budget-charge site). Mirrors parity.py.

        Charges the budget BEFORE the call (a 429'd/refused attempt still spent its unit —
        pythia §5); a 429 shrinks the AIMD window and is bridged across ``core.retry``'s
        botocore-shaped classifier via ``ParityOutboundError`` (a raw ``AsanaError.response``
        is an httpx ``Response`` / ``None``, never a botocore dict — feeding it raw
        ``AttributeError``s the classifier and masks the real failure).
        """
        from tests.harness.substrate_gate.parity import ParityOutboundError

        self._budget.consume()  # charge THIS attempt (before the call; 429'd counts)
        telem.requests_issued += 1
        try:
            page, next_cursor = await self._page_fetch(aid, section_gid, cursor)
        except Exception as exc:
            rate_limited = _is_rate_limit_signal(exc)
            if rate_limited:
                telem.http_429_count += 1
                slot.reject()  # AIMD: 429 shrinks the window BEFORE retry-handling
            raise ParityOutboundError(
                str(exc), status_code=getattr(exc, "status_code", None), rate_limited=rate_limited
            ) from exc
        telem.pages_succeeded += 1
        return page, next_cursor

    async def _fetch_section(
        self, aid: ArtifactId, section_gid: str, telem: _TelemetryAccum
    ) -> tuple[str, list[Mapping[str, Any]], datetime]:
        """Paginate one section live (paced): floor -> AIMD slot -> per-page retry."""
        await self._floor_gate.admit()  # advisory static floor
        async with await self._semaphore.acquire() as slot:  # AIMD concurrency slot
            rows: list[Mapping[str, Any]] = []
            cursor: str | None = None
            while True:
                page, cursor = await self._retry.execute_with_retry_async(  # resilience
                    partial(self._attempt_page, aid, section_gid, cursor, slot, telem),
                    operation_name="substrate_offer_page",
                )
                rows.extend(page)
                if cursor is None:
                    break
            slot.succeed()
            return section_gid, rows, self._now()

    async def fetch(self, aid: ArtifactId) -> FetchedSections:
        """``PacedAsanaFetcher`` conformance: paced live fetch -> a complete ``FetchedSections``."""
        plan = await self._plan(aid)
        telem = _TelemetryAccum(
            sections_refetched=len(plan.refetch), sections_reused=len(plan.reuse)
        )
        requested = frozenset(plan.refetch) | frozenset(plan.reuse)

        results = await gather_with_semaphore(
            [self._fetch_section(aid, gid, telem) for gid in plan.refetch],
            concurrency=self._concurrency,
            return_exceptions=True,
            label="substrate_offer_fetch",
        )

        all_rows: list[Mapping[str, Any]] = []
        instants: dict[str, datetime] = {}
        failed: set[str] = set()
        for gid, outcome in zip(plan.refetch, results, strict=True):
            if isinstance(outcome, BaseException):
                # Budget exhaustion is a HALT — propagate loud (never a per-section failure).
                _reraise_if_budget_halt(outcome)
                failed.add(gid)  # exhausted retries -> C16 FETCH_REFUSED, incumbent untouched
                continue
            _gid, section_rows, instant = outcome
            all_rows.extend(section_rows)
            instants[gid] = instant

        for gid, reused in plan.reuse.items():
            all_rows.extend(reused.rows)
            instants[gid] = reused.instant  # prior instant — the MIN-fold ages honestly

        frame = pl.DataFrame(list(all_rows)) if all_rows else pl.DataFrame()
        return FetchedSections(
            frame=frame,
            section_instants=instants,
            requested_sections=requested,
            failed_sections=frozenset(failed),
            telemetry=telem.finalize(),
        )


def _reraise_if_budget_halt(exc: BaseException) -> None:
    """Re-raise a per-day budget HALT (``ParityBudgetExhausted``); swallow other section errors."""
    from tests.harness.substrate_gate.budget import ParityBudgetExhausted

    if isinstance(exc, ParityBudgetExhausted):
        raise exc


class _CapturingFetcher:
    """Wraps a ``PacedAsanaFetcher`` to capture its single ``FetchedSections`` for the caller.

    ``SubstrateRebuilder`` calls ``fetch`` once (single-flight-coalesced), so the rebuild's
    fetched frame is captured for the v2 materialization WITHOUT a second live fetch (which
    would double-charge the budget).
    """

    def __init__(self, inner: PacedOfferSectionFetcher) -> None:
        self._inner = inner
        self.captured: FetchedSections | None = None

    async def fetch(self, aid: ArtifactId) -> FetchedSections:
        fetched = await self._inner.fetch(aid)
        self.captured = fetched
        return fetched


async def rebuild_offer_v2(
    aid: ArtifactId,
    *,
    fetcher: PacedOfferSectionFetcher,
    store: S3ArtifactStore,
    now: NowFn | None = None,
    sla_for: SlaResolver | None = None,
) -> tuple[RebuildResult, FetchedSections | None]:
    """3b (caller): drive ``SubstrateRebuilder.rebuild()`` for the offer plane.

    Composes the concrete paced fetcher with the frozen ``DefaultAcceptancePredicates`` and
    runs the stage-validate-swap. Returns the ``RebuildResult`` (its ``telemetry`` feeds the
    3d receipt) plus the captured ``FetchedSections`` (its frame is the v2 materialization
    source for 3c) — ``None`` when the fetch raised before returning one.
    """
    capturing = _CapturingFetcher(fetcher)
    rebuilder = SubstrateRebuilder(store, now=now, sla_for=sla_for)
    result = await rebuilder.rebuild(aid, capturing, DefaultAcceptancePredicates())
    return result, capturing.captured


# ===========================================================================
# 3d — per-touch receipt writer (P10 "every prod touch leaves a receipt")
# ===========================================================================

# Same durable parent as the ledger pin (survives park-per-day across the P5 window).
PARITY_RECEIPTS_ROOT: str = ".sos/wip/parity/receipts"


@dataclass(frozen=True, slots=True)
class ParityReceiptWriter:
    """Persists ONE dated JSON receipt per prod touch, consuming ``RebuildResult.telemetry``.

    Receipts land at ``{root}/{YYYY-MM-DD}/{entity}-{project}-{ts}-{uid}.json``. A
    ``ParityBudgetExhausted`` is RECORDED (``outcome=budget-halt``) and NEVER retried — it
    is non-transient by design and a charter L81 operator-interrupt trigger (budget
    exhaustion): the runner surfaces it, the writer records it.
    """

    root: Path
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))

    def _dir_for(self, at: datetime) -> Path:
        day = self.root / at.date().isoformat()
        day.mkdir(parents=True, exist_ok=True)
        return day

    def _persist(self, aid: ArtifactId, at: datetime, payload: dict[str, Any]) -> Path:
        stamp = at.strftime("%H%M%S%f")
        name = f"{aid.entity_type.value}-{aid.project_gid}-{stamp}-{uuid.uuid4().hex[:8]}.json"
        path = self._dir_for(at) / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    @staticmethod
    def _aid_block(aid: ArtifactId) -> dict[str, str]:
        return {"project_gid": aid.project_gid, "entity_type": aid.entity_type.value}

    @staticmethod
    def _telemetry_block(telemetry: FetchTelemetry | None) -> dict[str, int] | None:
        if telemetry is None:
            return None
        return {
            "requests_issued": telemetry.requests_issued,
            "http_429_count": telemetry.http_429_count,
            "retries_issued": telemetry.retries_issued,
            "sections_refetched": telemetry.sections_refetched,
            "sections_reused": telemetry.sections_reused,
        }

    def write(
        self, aid: ArtifactId, *, result: RebuildResult, ledger: PerDayBudgetLedger, at: datetime
    ) -> Path:
        """Record a completed prod touch (any ``RebuildOutcome``) + its budget state."""
        payload = {
            "aid": self._aid_block(aid),
            "touched_at": at.isoformat(),
            "outcome": result.outcome.value,
            "version_id": str(result.version_id) if result.version_id is not None else None,
            "built_from_live_at": (
                result.built_from_live_at.isoformat()
                if result.built_from_live_at is not None
                else None
            ),
            "detail": result.detail,
            "telemetry": self._telemetry_block(result.telemetry),
            "budget": {"count_today": ledger.count_today(), "cap": ledger.cap},
        }
        return self._persist(aid, at, payload)

    def write_budget_halt(
        self, aid: ArtifactId, *, ledger: PerDayBudgetLedger, at: datetime, detail: str
    ) -> Path:
        """Record a budget HALT (``outcome=budget-halt``). NEVER retried (charter L81)."""
        payload = {
            "aid": self._aid_block(aid),
            "touched_at": at.isoformat(),
            "outcome": "budget-halt",
            "version_id": None,
            "built_from_live_at": None,
            "detail": detail,
            "telemetry": None,
            "budget": {"count_today": ledger.count_today(), "cap": ledger.cap},
            "operator_interrupt": "budget-exhaustion (charter L81) — not retried",
        }
        return self._persist(aid, at, payload)


# ===========================================================================
# 3c — the concrete armed outbound for PacedLiveParitySource
# ===========================================================================


def _v2_materialization(fetched: FetchedSections | None, result: RebuildResult) -> Materialization:
    """Build the v2-side offer ``Materialization`` from the rebuild's captured frame.

    Uses the SAME active_mrr composition as v1 (apples-to-apples). ``built_from_live_at``
    is the rebuild's validated instant (``result``), falling back to the S2 MIN-fold of the
    fetched section instants.
    """
    if fetched is None:
        raise OfferSectionFetchError(
            f"v2 rebuild produced no frame (outcome={result.outcome.value}); "
            "cannot materialize the v2 parity side"
        )
    built = result.built_from_live_at or fold_built_from_live_at(fetched.section_instants)
    return offer_materialization_from_frame(
        plane="v2/offer",
        frame=fetched.frame,
        built_from_live_at=built,
        sla_seconds=sla_seconds_for(EntityType.OFFER),
    )


def build_parity_outbound(
    *,
    s3_reader: S3OfferPlaneReader,
    fetcher: PacedOfferSectionFetcher,
    store: S3ArtifactStore,
    receipt_writer: ParityReceiptWriter,
    budget: PerDayBudgetLedger,
    now: NowFn | None = None,
    sla_for: SlaResolver | None = None,
) -> Callable[[ArtifactId], Awaitable[ParityObservation]]:
    """3c: the concrete ``outbound`` — v1 (3a, S3) beside v2 (3b rebuild), receipted (3d).

    v1 is an S3 read (no charge); v2 is the paced live rebuild (budget charged at the HTTP
    boundary in 3b — the parity source itself is armed with ``budget=None`` so nothing is
    double-counted per-aid, per pythia §5). A ``ParityBudgetExhausted`` is recorded as a
    budget-halt receipt and re-raised (never retried — charter L81 operator interrupt).
    """
    clock: NowFn = now if now is not None else (lambda: datetime.now(UTC))

    async def _outbound(aid: ArtifactId) -> ParityObservation:
        from tests.harness.substrate_gate.budget import ParityBudgetExhausted
        from tests.harness.substrate_gate.parity import ParityObservation

        touched_at = clock()
        v1 = build_v1_offer_materialization(s3_reader, project_gid=aid.project_gid)
        try:
            result, fetched = await rebuild_offer_v2(
                aid, fetcher=fetcher, store=store, now=now, sla_for=sla_for
            )
        except ParityBudgetExhausted as exc:
            receipt_writer.write_budget_halt(aid, ledger=budget, at=touched_at, detail=str(exc))
            raise  # HALT — non-transient, never retried (charter L81 operator interrupt)
        v2 = _v2_materialization(fetched, result)
        receipt_writer.write(aid, result=result, ledger=budget, at=touched_at)
        return ParityObservation(aid=aid, v1=v1, v2=v2)

    return _outbound


def arm_process_parity_fetcher(
    outbound: Callable[[ArtifactId], Awaitable[ParityObservation]],
    *,
    concurrency: int = 5,
    aimd_ceiling: int = 10,
) -> PacedLiveParitySource:
    """Arm THE process-singleton ``PacedLiveParitySource`` with ``outbound`` (never a 2nd instance).

    Construction routes ``get_process_fetcher`` (the one process-wide instance / K>1 in-flight
    ceiling guard). ``budget`` is deliberately NOT wired into the parity source — the per-day
    P10 budget is charged at the Asana HTTP boundary inside the 3b fetcher (per pagination
    page), not once per parity observation (pythia §5). Verifies the RC-E-4 routing invariant
    post-wiring.
    """
    from tests.harness.substrate_gate.parity import get_process_fetcher

    source = get_process_fetcher(
        concurrency=concurrency, aimd_ceiling=aimd_ceiling, outbound=outbound, armed=True
    )
    if not source.routes_through_paced_primitives():  # RC-E-4: wired through all four v1 primitives
        raise RuntimeError(
            "armed parity source is not routed through the paced primitives (RC-E-4)"
        )
    return source


# ===========================================================================
# Window entry point (WU-4 opens the window by calling this)
# ===========================================================================

# Per-day P10 runaway cap: 2.0x headroom on the ~5,600/day midpoint of the UV-P-6
# instrumented HTTP-boundary fan-out (RECEIPT-s8-0 L317-345 / pythia §5). NOT the ~5,600
# section-proxy bound and NOT the Asana PAT ceiling (~2.16M/day) — a runaway guard for the
# 2026-07-27 429-storm, pinned from the instrumented count, not a guess.
DEFAULT_DAILY_BUDGET_CAP: int = 11_200


def default_ledger_path(*, year: int | None = None, repo_root: Path | None = None) -> Path:
    """Resolve the pinned per-day ledger path (``PINNED_LEDGER_PATH.format(year=...)``)."""
    from tests.harness.substrate_gate.budget import PINNED_LEDGER_PATH

    resolved_year = year if year is not None else datetime.now(UTC).year
    root = repo_root if repo_root is not None else Path.cwd()
    return root / PINNED_LEDGER_PATH.format(year=resolved_year)


@dataclass(frozen=True, slots=True)
class ArmedParityWindow:
    """The armed window handle WU-4 runs: the paced source + its budget/receipt collaborators."""

    source: PacedLiveParitySource
    ledger: PerDayBudgetLedger
    receipt_writer: ParityReceiptWriter
    fetcher: PacedOfferSectionFetcher


def arm_offer_parity_window(
    *,
    bucket: str,
    page_fetch: PageFetch,
    plan: PlanFn,
    store: S3ArtifactStore,
    region: str = "us-east-1",
    cap: int = DEFAULT_DAILY_BUDGET_CAP,
    ledger_path: Path | None = None,
    receipts_root: Path | None = None,
    now: NowFn | None = None,
    sla_for: SlaResolver | None = None,
) -> ArmedParityWindow:
    """Compose 3a-3d and ARM the process-singleton parity source for the offer plane.

    WU-4 opens the window by calling this then ``source.fetch_all_paced([offer_aid()])``.
    ``page_fetch`` + ``plan`` are the real Asana client call site + section planner WU-4
    injects; ``store`` is the v2 ``S3ArtifactStore``. Everything below the seam is proven
    DARK with fakes; this call performs NO Asana or S3 I/O by itself.
    """
    from tests.harness.substrate_gate.budget import PerDayBudgetLedger

    ledger = PerDayBudgetLedger(
        path=ledger_path if ledger_path is not None else default_ledger_path(), cap=cap
    )
    s3_reader = S3OfferPlaneReader(bucket=bucket, region=region)
    fetcher = PacedOfferSectionFetcher(page_fetch=page_fetch, plan=plan, budget=ledger, now=now)
    receipt_writer = ParityReceiptWriter(
        root=receipts_root if receipts_root is not None else Path.cwd() / PARITY_RECEIPTS_ROOT
    )
    outbound = build_parity_outbound(
        s3_reader=s3_reader,
        fetcher=fetcher,
        store=store,
        receipt_writer=receipt_writer,
        budget=ledger,
        now=now,
        sla_for=sla_for,
    )
    source = arm_process_parity_fetcher(outbound)
    return ArmedParityWindow(
        source=source, ledger=ledger, receipt_writer=receipt_writer, fetcher=fetcher
    )


def offer_aid() -> ArtifactId:
    """The offer-plane ``ArtifactId`` the window rebuilds/serves."""
    return ArtifactId(project_gid=OFFER_PROJECT_GID, entity_type=EntityType.OFFER)
