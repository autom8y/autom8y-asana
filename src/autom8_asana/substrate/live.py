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

The active_mrr referent is the PRODUCTION-SERVED number per
RULING-pythia-f305-1-active-mrr-referent-2026-08-04 — a DUAL-LEG ledger: LEG A (the gate
anchor) is the served-definition active_mrr (22-section classifier + dedup(office_phone,
vertical) + mrr>0 + Float64 sum, via the real ``compute_metric`` machinery, computed
identically on v1 and v2); LEG B (a tripwire, NOT the gate) is the 3-section raw exemplar
aggregate. Nine capture-mechanics conditions (ruling §6) bind, the fail-closed fetch-plan
coverage assertion being the anti-RC-C keystone.

* **3a** ``materialize_v1_offer_plane`` / ``build_v1_offer_materialization`` — the CURRENT v1
  offer plane (S3-read-only) as a served-definition (LEG A) ``Materialization`` with the
  RECEIPT-s8-0 torn-read guard (+ §F-305-4 generation-monotonicity); ``exemplar_aggregate_value``
  is LEG B.
* **3b** ``PacedOfferSectionFetcher`` + ``rebuild_offer_v2`` — the concrete ``PacedAsanaFetcher``
  composing v1's G6 controllers (floor-gate admit -> AIMD slot -> retry -> bounded gather) around
  the Asana HTTP boundary, charging the hardened ``PerDayBudgetLedger`` per pagination-page
  ATTEMPT (a 429 charges; reused/hash-CLEAN sections and S3 ops NEVER charge — pythia §5), with
  the §6 #2 coverage assertion fail-closed BEFORE any charge; threaded into a
  ``SubstrateRebuilder.rebuild()`` caller.
* **3c** ``build_parity_outbound`` / ``arm_process_parity_fetcher`` — the concrete armed
  ``outbound``: a DUAL-LEG record, a ``ParityObservation`` ONLY on a SWAPPED coverage-clean v2,
  refusal + error as first-class recorded outcomes; armed through the process singleton
  ``get_process_fetcher`` (never a second instance).
* **3d** ``ParityReceiptWriter`` — one durable JSON receipt per prod touch on ALL paths
  (served / refused / error / budget-halt): dual-leg PII-safe scalars + digests + ``FetchTelemetry``
  + budget state; a charged raise still receipts (F-305-3); budget-halt NEVER retried.

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
from functools import lru_cache, partial
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
from autom8_asana.metrics.compute import compute_metric
from autom8_asana.metrics.registry import MetricRegistry
from autom8_asana.models.business.activity import CLASSIFIERS, AccountActivity
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
    RebuildOutcome,
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
# Shared offer-plane constants + the DUAL-LEG active_mrr referent (F-305-1)
# ---------------------------------------------------------------------------
# Per RULING-pythia-f305-1-active-mrr-referent-2026-08-04: active_mrr DENOTES the
# PRODUCTION-SERVED number. LEG A (the gate anchor, the leg PT-03 Q1 + the auto-flip hang
# on) is the served-definition active_mrr — the 22-section classifier active set
# (activity.py:181-208) + dedup by (office_phone, vertical) keep="first" + mrr>0 filter +
# Float64 sum (offer.py:20-43 / compute.py:66-116) — computed IDENTICALLY on v1 and v2 via
# the REAL ``compute_metric`` machinery (§6 #1-7 satisfied by construction: the section set
# comes FROM THE CLASSIFIER, never a hardcoded list — a hardcoded subset is the RC-C drift
# vector that produced the defect). LEG B (a corpus-continuity / byte-determinism TRIPWIRE,
# NOT the gate) is the 3-section raw exemplar aggregate — RETAINED per ruling §4, re-labeled
# "exemplar aggregate" (never "served_value"; the O4 "served_value" label was a misnomer).

# The offer project whose active_mrr the parity gate re-derives (DEFECT :20-23; O4).
OFFER_PROJECT_GID: str = "1143843662099250"

# LEG B tripwire sections (3-section raw; plain HYPHEN U+002D in prod bytes). This is the
# exemplar/corpus aggregate — a strict subset of the 22-section classifier active set, raw
# (no dedup, no mrr>0 filter). It is NOT active_mrr (ruling §4 label correction).
EXEMPLAR_AGGREGATE_SECTIONS: tuple[str, ...] = ("ACTIVE", "OPTIMIZE - Human Review", "STAGED")

# The columns the served leg REQUIRES present + typed on BOTH sides — section, mrr, and the
# (office_phone, vertical) dedup keys (§6 #3/#8; offer.py:19/28 confirm the offer schema
# declares them). A missing one is a FINDING (ActiveMrrColumnMissing), not a silent partial.
_SERVED_REQUIRED_COLUMNS: tuple[str, ...] = ("section", "mrr", "office_phone", "vertical")

_V1_OFFER_PLANE: str = "v1/offer"


class ActiveMrrColumnMissing(RuntimeError):
    """The served-definition columns (section, mrr, office_phone, vertical) are not all present.

    The ruling's explicit "verify the served definition's columns are present + identically
    typed on both sides; a missing dedup-key column is a FINDING to report, not to paper
    over." Raised loudly rather than silently computing a wrong/partial number.
    """


class ActiveMrrRefused(RuntimeError):
    """The served leg REFUSES — a first-class outcome, never coerced to zero/skipped (§6 #2/#9).

    Fires when v2's fetch plan omits a classifier-active section (the anti-RC-C keystone: a
    partial sum is the $14,360 silent-loss shape of the founding wound), or when any
    classifier-active section is not present-and-fresh-and-torn-read-clean. In the parity
    comparison this is preserved distinct from a served number (over-refusal W2 vs correct
    refusal is a downstream pythia call).
    """


@lru_cache(maxsize=1)
def _offer_active_metric() -> Any:
    """The registered ``active_mrr`` Metric — the single authoritative served definition."""
    return MetricRegistry().get_metric("active_mrr")


@lru_cache(maxsize=1)
def classifier_active_sections() -> frozenset[str]:
    """The 22-section OFFER active set FROM THE CLASSIFIER (§6 #1 — never hardcoded).

    Lowercased, exactly as ``compute.py:78`` derives + matches it, so the fetch-plan coverage
    assertion keys off the same set the served metric filters on.
    """
    classifier = CLASSIFIERS.get("offer")
    if classifier is None:  # pragma: no cover - the offer classifier is a module constant
        raise ActiveMrrColumnMissing("no OFFER classifier registered; cannot resolve active set")
    return frozenset(classifier.sections_for(AccountActivity("active")))


def assert_plan_covers_active_set(covered_section_names: frozenset[str]) -> None:
    """§6 #2 fail-closed coverage: the plan MUST be a superset of the classifier active set.

    Any classifier-active section absent from the fetch plan → ``ActiveMrrRefused`` (never a
    partial sum). Case-insensitive (both sides lowercased), mirroring the served metric's
    ``.str.to_lowercase()`` match. This is what makes the silent-loss shape unconstructable.
    """
    covered = {name.lower() for name in covered_section_names}
    missing = classifier_active_sections() - covered
    if missing:
        raise ActiveMrrRefused(
            f"fetch plan omits {len(missing)} classifier-active section(s) {sorted(missing)} — "
            "refusing a partial active_mrr (§6 #2 anti-RC-C keystone; the silent-loss shape of "
            "the founding wound is unconstructable here)"
        )


def served_active_mrr(frame: pl.DataFrame) -> tuple[float, int]:
    """LEG A: the served-definition active_mrr, via the REAL ``active_mrr`` metric machinery.

    Reuses ``compute_metric`` (classifier 22-section filter → mrr>0 → dedup(office_phone,
    vertical) → Float64 sum), so v1 and v2 are computed IDENTICALLY and conditions §6 #1-7 hold
    by construction. Returns ``(active_mrr, deduped_row_count)``. Raises ``ActiveMrrColumnMissing``
    if a served-definition column is absent (the ruling's "report, don't paper over").
    """
    missing = [c for c in _SERVED_REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ActiveMrrColumnMissing(
            f"served active_mrr requires columns {list(_SERVED_REQUIRED_COLUMNS)} present + typed; "
            f"frame is missing {missing} (has {sorted(frame.columns)}) — reporting, not papering over"
        )
    metric = _offer_active_metric()
    result = compute_metric(metric, frame)
    total = result[metric.expr.column].sum()
    return round(float(total if total is not None else 0.0), 6), result.height


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
    """PII-safe drift-tripwire digest: sha256 over sorted ``{label:[rows,value]}`` (§6 #8).

    Digests ONLY the per-classification (leg A) / per-section (leg B) scalar aggregates —
    the PII dedup keys (``office_phone``) NEVER enter it. Same frame bytes -> same aggregate
    -> same digest, so a determinism test can pin it.
    """
    canonical = json.dumps(
        {label: list(cell) for label, cell in sorted(composition.items())},
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def materialize_v1_offer_plane(
    parquet_bytes: bytes,
    watermark_bytes: bytes,
    *,
    project_gid: str = OFFER_PROJECT_GID,
    plane: str = _V1_OFFER_PLANE,
    sla_seconds: int | None = None,
    min_build_instant: datetime | None = None,
) -> Materialization:
    """3a (pure): build the v1-side served-definition (LEG A) ``Materialization`` from raw bytes.

    S3-read-only in prod (the bytes are a GET of ``dataframe.parquet`` + ``watermark.json``);
    this pure core takes the bytes so it is fully provable offline (no I/O — CARDINAL P10
    boundary). Applies the RECEIPT-s8-0 torn-read guard, then computes the SERVED active_mrr
    (LEG A, §6 #1-7) via ``offer_materialization_from_frame``.

    ``min_build_instant`` (§F-305-4, optional): the build instant of the LAST accepted capture.
    The bare row_count cross-check is blind to an equal-rowcount GENERATION SWAP (two distinct
    generations that happen to share a row count); a build instant that has regressed below the
    last accepted one is that swap and is REFUSED. WU-4 threads the prior receipt's build instant.

    Raises ``TornOfferPlaneRead`` on inconsistency; ``ActiveMrrColumnMissing`` if the served
    columns (section, mrr, office_phone, vertical) are absent (never a silent partial).
    """
    frame, built_at = guarded_v1_offer_frame(
        parquet_bytes, watermark_bytes, project_gid=project_gid, min_build_instant=min_build_instant
    )
    resolved_sla = sla_seconds if sla_seconds is not None else sla_seconds_for(EntityType.OFFER)
    return offer_materialization_from_frame(
        plane=plane, frame=frame, built_from_live_at=built_at, sla_seconds=resolved_sla
    )


def guarded_v1_offer_frame(
    parquet_bytes: bytes,
    watermark_bytes: bytes,
    *,
    project_gid: str = OFFER_PROJECT_GID,
    min_build_instant: datetime | None = None,
) -> tuple[pl.DataFrame, datetime]:
    """Parse + apply the RECEIPT-s8-0 torn-read guard ONCE; return ``(frame, build_instant)``.

    Shared by the LEG-A materialization and the LEG-B exemplar aggregate so ONE parse feeds
    both legs (no double read). Raises ``TornOfferPlaneRead`` on any inconsistency.
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
    if min_build_instant is not None and built_at < min_build_instant:
        raise TornOfferPlaneRead(
            f"watermark build instant {built_at.isoformat()} regressed below the last accepted "
            f"capture {min_build_instant.isoformat()} — an equal-rowcount generation swap the "
            "row_count cross-check is blind to (§F-305-4)"
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
    return frame, built_at


def offer_materialization_from_frame(
    *,
    plane: str,
    frame: pl.DataFrame,
    built_from_live_at: datetime,
    sla_seconds: int,
) -> Materialization:
    """Compose the served-definition (LEG A) offer ``Materialization`` — IDENTICAL v1/v2 (§6 #1-7).

    ONE source of truth for the served number, called on BOTH the v1 S3 frame and the v2
    rebuild frame, via the REAL ``active_mrr`` metric machinery. ``served_value`` is the served
    active_mrr; the composition is the PII-safe per-classification cell ``{"active":
    (deduped_rows, active_mrr)}`` (§6 #8 — no dedup key ever enters it); the digest is over that.
    """
    from tests.harness.substrate_gate.cases import Materialization, SectionCell

    active_mrr, deduped_rows = served_active_mrr(frame)
    cells: dict[str, tuple[int, float]] = {"active": (deduped_rows, active_mrr)}
    digest = _composition_digest(cells)
    return Materialization(
        plane=plane,
        proof=FreshnessProof(
            built_from_live_at=built_from_live_at, content_digest=digest, sla_seconds=sla_seconds
        ),
        served_value=active_mrr,
        composition={"active": SectionCell(rows=deduped_rows, value=active_mrr)},
        frame_digest=digest,  # digest-consistent: coherent served state, NOT corrupt
    )


def exemplar_aggregate_value(
    frame: pl.DataFrame, *, sections: tuple[str, ...] = EXEMPLAR_AGGREGATE_SECTIONS
) -> tuple[float, dict[str, tuple[int, float]]]:
    """LEG B (a TRIPWIRE, NOT the gate): the 3-section RAW exemplar aggregate (ruling §4).

    No dedup, no ``mrr>0`` filter — the corpus-continuity / byte-determinism number the O4
    receipts track. Re-labeled "exemplar aggregate" per the ruling §4 label correction; it is
    NEVER ``active_mrr`` / ``served_value``. Returns ``(aggregate, {section: (rows, value)})``.
    """
    grouped = (
        frame.filter(pl.col("section").is_in(list(sections)))
        .group_by("section")
        .agg(pl.len().alias("rows"), pl.col("mrr").sum().alias("mrr"))
        .sort("section")
    )
    cells: dict[str, tuple[int, float]] = {
        row["section"]: (int(row["rows"]), float(row["mrr"])) for row in grouped.to_dicts()
    }
    total = round(sum(v for _r, v in cells.values()), 6)
    return total, cells


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

    ``covered_section_names`` are the section NAMES this plan guarantees it fetched-or-reused —
    the coverage set the served leg checks against the classifier active set (§6 #2 fail-closed).
    Section NAMES (not gids) because the classifier active set is by name; a classifier-active
    section absent here means the plan would produce a partial served sum → REFUSE.
    """

    refetch: tuple[str, ...]
    reuse: Mapping[str, ReusedSection] = field(default_factory=dict)
    covered_section_names: frozenset[str] = frozenset()


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
        # There is NO in-sweep retry: a boundary error is wrapped in ParityOutboundError, which
        # core.retry classifies non-transient, so the orchestrator re-raises immediately (I-5).
        # ``retries_issued`` therefore counts FAILED attempts (a 429 charges, shrinks AIMD, and
        # fails this sweep's observation; the NEXT paced sweep is the retry) = attempts - pages.
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
    ``semaphore.acquire()`` (AIMD slot) -> ``retry.execute_with_retry_async(...)`` around the
    injected HTTP boundary; sections fan out through ``gather_with_semaphore`` (bounded
    concurrency). Every page ATTEMPT charges the injected ``PerDayBudgetLedger`` BEFORE the call
    (a 429'd attempt still spent its unit — pythia §5); reused/hash-CLEAN sections and the frame
    assembly touch no boundary and never charge.

    NO in-sweep retry actually fires: a boundary error is bridged as a non-transient
    ``ParityOutboundError`` (a raw ``AsanaError`` would crash core.retry's botocore-shaped
    classifier), so the orchestrator re-raises immediately. A 429 charges, shrinks the AIMD
    window, and FAILS this section's fetch (→ C16 FETCH_REFUSED); the NEXT paced sweep is the
    retry. Structurally implements the frozen Protocol; imports NO ``AsanaClient`` (RC-E-4) —
    the only Asana surface is the injected ``page_fetch``.
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
        """Paginate one section live (paced): floor -> AIMD slot -> per-page boundary attempt."""
        await self._floor_gate.admit()  # advisory static floor
        async with await self._semaphore.acquire() as slot:  # AIMD concurrency slot
            rows: list[Mapping[str, Any]] = []
            cursor: str | None = None
            while True:
                (
                    page,
                    cursor,
                ) = await self._retry.execute_with_retry_async(  # non-transient: no retry fires
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
        # §6 #2 fail-closed coverage — BEFORE any HTTP charge: if the plan omits a
        # classifier-active section, REFUSE LOUDLY (never spend budget on a partial sum whose
        # served number would silently lose value — the anti-RC-C keystone).
        assert_plan_covers_active_set(plan.covered_section_names)
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
# 3d — per-touch DUAL-LEG receipt writer (P10 "every prod touch leaves a receipt")
# ===========================================================================

# Same durable parent as the ledger pin (survives park-per-day across the P5 window).
PARITY_RECEIPTS_ROOT: str = ".sos/wip/parity/receipts"


class ParityLegRefused(RuntimeError):
    """The v2 parity side REFUSED (first-class outcome, §6 #9) — no ``ParityObservation`` is made.

    Raised by the outbound when the v2 rebuild did not SWAP (FETCH_REFUSED / STAGED_REJECTED)
    or the served leg refused coverage (``ActiveMrrRefused``). The refusal is RECORDED (3d) as a
    first-class outcome, never coerced to a zero-valued observation; the runner surfaces it and
    pythia classifies over-refusal (W2) vs correct-refusal downstream.
    """


@dataclass(frozen=True, slots=True)
class ParityLegs:
    """The F-305-1 dual-leg ledger row — PII-safe scalars + digests ONLY (§6 #8).

    LEG A ``served_*`` is the served-definition active_mrr (the gate anchor PT-03 Q1 hangs on);
    LEG B ``exemplar_*`` is the 3-section raw exemplar aggregate (a corpus-continuity tripwire,
    NEVER the served number). Dedup keys (``office_phone``) NEVER appear here.
    """

    served_v1: float | None = None
    served_v2: float | None = None
    served_digest: str | None = None
    exemplar_v1: float | None = None
    exemplar_v2: float | None = None
    exemplar_digest: str | None = None

    def as_block(self) -> dict[str, Any]:
        return {
            "served_active_mrr": {
                "v1": self.served_v1,
                "v2": self.served_v2,
                "digest": self.served_digest,
                "note": "LEG A — the gate anchor (22-section classifier + dedup + mrr>0)",
            },
            "exemplar_aggregate": {
                "v1": self.exemplar_v1,
                "v2": self.exemplar_v2,
                "digest": self.exemplar_digest,
                "note": "LEG B — 3-section raw tripwire, NOT active_mrr (ruling §4)",
            },
        }


@dataclass(frozen=True, slots=True)
class ParityReceiptWriter:
    """Persists ONE dated JSON receipt per prod touch — a DUAL-LEG ledger row, on ALL paths.

    Receipts land at ``{root}/{YYYY-MM-DD}/{entity}-{project}-{ts}-{uid}.json``. Every CHARGED
    touch leaves a receipt on EVERY path (served / refused / error / budget-halt) — F-305-3: a
    raise path that charged the budget MUST still receipt (P10). A ``ParityBudgetExhausted`` is
    ``outcome=budget-halt`` and NEVER retried (charter L81 operator interrupt).
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

    def _base(
        self,
        aid: ArtifactId,
        *,
        outcome: str,
        ledger: PerDayBudgetLedger,
        at: datetime,
        result: RebuildResult | None,
        legs: ParityLegs | None,
        detail: str,
    ) -> dict[str, Any]:
        return {
            "aid": self._aid_block(aid),
            "touched_at": at.isoformat(),
            "outcome": outcome,
            "version_id": (
                str(result.version_id)
                if result is not None and result.version_id is not None
                else None
            ),
            "built_from_live_at": (
                result.built_from_live_at.isoformat()
                if result is not None and result.built_from_live_at is not None
                else None
            ),
            "detail": detail or (result.detail if result is not None else ""),
            "telemetry": self._telemetry_block(result.telemetry if result is not None else None),
            "budget": {"count_today": ledger.count_today(), "cap": ledger.cap},
            "legs": legs.as_block() if legs is not None else None,
        }

    def write_served(
        self,
        aid: ArtifactId,
        *,
        result: RebuildResult,
        legs: ParityLegs,
        ledger: PerDayBudgetLedger,
        at: datetime,
    ) -> Path:
        """Record a SERVED touch (SWAPPED + coverage-ok): both legs, both sides."""
        return self._persist(
            aid,
            at,
            self._base(
                aid, outcome="served", ledger=ledger, at=at, result=result, legs=legs, detail=""
            ),
        )

    def write_refusal(
        self,
        aid: ArtifactId,
        *,
        outcome: str,
        ledger: PerDayBudgetLedger,
        at: datetime,
        legs: ParityLegs | None = None,
        result: RebuildResult | None = None,
        detail: str = "",
    ) -> Path:
        """Record a first-class REFUSAL (§6 #9): v2 refused; v1's served number is preserved."""
        return self._persist(
            aid,
            at,
            self._base(
                aid, outcome=outcome, ledger=ledger, at=at, result=result, legs=legs, detail=detail
            ),
        )

    def write_error(
        self,
        aid: ArtifactId,
        *,
        error: BaseException,
        ledger: PerDayBudgetLedger,
        at: datetime,
        legs: ParityLegs | None = None,
        result: RebuildResult | None = None,
    ) -> Path:
        """F-305-3: a charged touch that RAISED still leaves a receipt (outcome=error, class named)."""
        payload = self._base(
            aid, outcome="error", ledger=ledger, at=at, result=result, legs=legs, detail=str(error)
        )
        payload["error"] = {"type": type(error).__name__, "message": str(error)}
        return self._persist(aid, at, payload)

    def write_budget_halt(
        self, aid: ArtifactId, *, ledger: PerDayBudgetLedger, at: datetime, detail: str
    ) -> Path:
        """Record a budget HALT (``outcome=budget-halt``). NEVER retried (charter L81)."""
        payload = self._base(
            aid, outcome="budget-halt", ledger=ledger, at=at, result=None, legs=None, detail=detail
        )
        payload["operator_interrupt"] = "budget-exhaustion (charter L81) — not retried"
        return self._persist(aid, at, payload)


# ===========================================================================
# 3c — the concrete armed outbound for PacedLiveParitySource (dual-leg, F-305-1/2/3)
# ===========================================================================


def _v2_materialization(fetched: FetchedSections | None, result: RebuildResult) -> Materialization:
    """Build the v2-side served-definition (LEG A) ``Materialization`` from the rebuilt frame.

    Uses the SAME ``offer_materialization_from_frame`` as v1 (identical served computation,
    §6 #1-7). ``built_from_live_at`` is the rebuild's validated instant, falling back to the
    S2 MIN-fold of the fetched section instants.
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
    min_build_instant: datetime | None = None,
) -> Callable[[ArtifactId], Awaitable[ParityObservation]]:
    """3c: the concrete ``outbound`` — a DUAL-LEG parity record (F-305-1) with first-class refusal.

    LEG A (gate anchor): the SERVED active_mrr computed IDENTICALLY on the v1 S3 frame and the
    v2 rebuild frame (§6). LEG B (tripwire): the 3-section exemplar aggregate on each side. v1 is
    an S3 read (no charge); v2 is the paced live rebuild (budget charged at the HTTP boundary in
    3b; the parity source is armed ``budget=None`` so nothing double-counts per-aid).

    A ``ParityObservation`` is constructed ONLY on a SWAPPED, coverage-clean v2 (F-305-2). A
    ``ParityBudgetExhausted`` → budget-halt receipt + re-raise (never retried). A non-SWAPPED
    rebuild or a coverage ``ActiveMrrRefused`` → refusal receipt + ``ParityLegRefused`` (first
    class, §6 #9). Any other exception on a (possibly charged) touch → error receipt + re-raise
    (F-305-3). No raise path escapes without a receipt.
    """
    from tests.harness.substrate_gate.budget import ParityBudgetExhausted

    clock: NowFn = now if now is not None else (lambda: datetime.now(UTC))
    v1_sla = sla_for(EntityType.OFFER) if sla_for is not None else sla_seconds_for(EntityType.OFFER)

    async def _outbound(aid: ArtifactId) -> ParityObservation:
        from tests.harness.substrate_gate.parity import ParityObservation

        touched_at = clock()
        v1_served: float | None = None
        v1_exemplar: float | None = None
        v1_digest: str | None = None
        try:
            # --- LEG A + LEG B on the v1 S3 plane (one guarded parse; no charge) -------------
            parquet_bytes, watermark_bytes = s3_reader.read(aid.project_gid)
            v1_frame, v1_built = guarded_v1_offer_frame(
                parquet_bytes,
                watermark_bytes,
                project_gid=aid.project_gid,
                min_build_instant=min_build_instant,
            )
            v1_mat = offer_materialization_from_frame(
                plane="v1/offer", frame=v1_frame, built_from_live_at=v1_built, sla_seconds=v1_sla
            )
            v1_served, v1_digest = v1_mat.served_value, v1_mat.frame_digest
            v1_exemplar = exemplar_aggregate_value(v1_frame)[0]
            # --- LEG A + LEG B on the v2 rebuild (paced live; budget at the HTTP boundary) ----
            result, fetched = await rebuild_offer_v2(
                aid, fetcher=fetcher, store=store, now=now, sla_for=sla_for
            )
        except ParityBudgetExhausted as exc:
            receipt_writer.write_budget_halt(aid, ledger=budget, at=touched_at, detail=str(exc))
            raise  # HALT — non-transient, never retried (charter L81 operator interrupt)
        except ActiveMrrRefused as exc:
            # §6 #2 coverage refusal (raised in fetch BEFORE any charge) — first-class, recorded.
            receipt_writer.write_refusal(
                aid,
                outcome="refused-coverage",
                ledger=budget,
                at=touched_at,
                legs=ParityLegs(
                    served_v1=v1_served, served_digest=v1_digest, exemplar_v1=v1_exemplar
                ),
                detail=str(exc),
            )
            raise ParityLegRefused(f"served leg refused coverage: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 — F-305-3: a (possibly charged) raise must receipt
            receipt_writer.write_error(
                aid,
                error=exc,
                ledger=budget,
                at=touched_at,
                legs=ParityLegs(
                    served_v1=v1_served, served_digest=v1_digest, exemplar_v1=v1_exemplar
                ),
            )
            raise

        # F-305-2: a ParityObservation is constructed ONLY on SWAPPED. Non-SWAPPED is a
        # first-class refusal in the record, never a normal (coherent-looking) observation.
        if result.outcome is not RebuildOutcome.SWAPPED:
            receipt_writer.write_refusal(
                aid,
                outcome=f"refused-{result.outcome.value}",
                result=result,
                ledger=budget,
                at=touched_at,
                legs=ParityLegs(
                    served_v1=v1_served, served_digest=v1_digest, exemplar_v1=v1_exemplar
                ),
                detail=result.detail,
            )
            raise ParityLegRefused(f"v2 rebuild {result.outcome.value}: {result.detail}")

        try:
            v2_mat = _v2_materialization(fetched, result)
            v2_exemplar, v2_ex_cells = (
                exemplar_aggregate_value(fetched.frame) if fetched is not None else (None, {})
            )
        except Exception as exc:  # noqa: BLE001 — F-305-3: the charged rebuild must still receipt
            receipt_writer.write_error(
                aid,
                error=exc,
                result=result,
                ledger=budget,
                at=touched_at,
                legs=ParityLegs(
                    served_v1=v1_served, served_digest=v1_digest, exemplar_v1=v1_exemplar
                ),
            )
            raise

        legs = ParityLegs(
            served_v1=v1_served,
            served_v2=v2_mat.served_value,
            served_digest=v2_mat.frame_digest,  # LEG A PII-safe per-classification digest
            exemplar_v1=v1_exemplar,
            exemplar_v2=v2_exemplar,
            exemplar_digest=_composition_digest(v2_ex_cells) if v2_ex_cells else None,
        )
        receipt_writer.write_served(aid, result=result, legs=legs, ledger=budget, at=touched_at)
        return ParityObservation(aid=aid, v1=v1_mat, v2=v2_mat)

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
    min_build_instant: datetime | None = None,
) -> ArmedParityWindow:
    """Compose 3a-3d and ARM the process-singleton parity source for the offer plane.

    WU-4 opens the window by calling this then ``source.fetch_all_paced([offer_aid()])``.
    ``page_fetch`` + ``plan`` are the real Asana client call site + section planner WU-4
    injects; ``store`` is the v2 ``S3ArtifactStore``; ``min_build_instant`` (F-305-4) is the
    prior served receipt's build instant (generation-monotonicity floor). Everything below the
    seam is proven DARK with fakes; this call performs NO Asana or S3 I/O by itself.
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
        min_build_instant=min_build_instant,
    )
    source = arm_process_parity_fetcher(outbound)
    return ArmedParityWindow(
        source=source, ledger=ledger, receipt_writer=receipt_writer, fetcher=fetcher
    )


def offer_aid() -> ArtifactId:
    """The offer-plane ``ArtifactId`` the window rebuilds/serves."""
    return ArtifactId(project_gid=OFFER_PROJECT_GID, entity_type=EntityType.OFFER)
