"""Substrate-v2 Seam 4 — SERVING (core policy + thin adapters). RC-C(serve) / P2.

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 4. Value objects +
the single public read Protocol; the per-read gate and adapter bodies are owned
by S4. The cross-process WIRE contract is the operator's DP-3 ruling — this seam
is wire-stable (the ``Refused`` FIELDS hold under any ratified status class).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, assert_never

from autom8y_log import get_logger

from autom8_asana.substrate.freshness import Provability
from autom8_asana.substrate.store import ArtifactMissing, PointerCorrupt

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from autom8_asana.substrate.freshness import FreshnessProof
    from autom8_asana.substrate.identity import ArtifactId
    from autom8_asana.substrate.store import ArtifactStore

logger = get_logger(__name__)


class RefuseReason(Enum):
    """CLOSED refusal taxonomy ([H14]): {STALE, CORRUPT, MISSING, DIVERGENT}."""

    STALE = "stale"
    CORRUPT = "corrupt"
    MISSING = "missing"
    DIVERGENT = "divergent"


@dataclass(frozen=True, slots=True)
class SunsetBreach:
    """C13 field-level sunset marker (TDD §11 C13 — architect ruling 2026-07-29).

    The additive payload observable that keeps a *surface-lifecycle* sunset breach
    machine-distinguishable from an ordinary *age* staleness at the payload level.
    The CLOSED ``RefuseReason`` grammar STANDS: a runtime sunset breach maps to
    ``RefuseReason.STALE`` (no ``EXPIRED`` member — the rot-trigger for minting one
    is recorded in C13); this named marker is the ORTHOGONAL surface-governance axis
    riding the payload, separated from the consumer-facing reason *by altitude, not
    fused* (contrast the ``ai_cloud`` anti-pattern). Field names/types mirror the S7
    harness's anticipatory ``cases.SunsetBreach`` so a future migration is a drop-in.

    Security: carries the logical serving-plane label + two instants only — no S3
    key, bucket, version_id, or internal path (refusal bodies leak no topology).
    """

    surface: str  # which bridge/transitional surface breached (the logical serving plane)
    sunset_after: datetime  # the declared sunset instant (tz-aware UTC)
    observed_at: datetime  # the serving instant at which the breach was observed (tz-aware UTC)


@dataclass(frozen=True, slots=True)
class RefusePayload:
    """OQ-1 frozen observable ([H14] — do NOT narrow): the RC-A-2 explanation surface.

    Seam 4, FROZEN v1.0. The wire FORMAT is DP-3; the FIELDS below are the seam.
    Every dimension the design mandates is present and un-narrowed — the
    ``of each`` / ``per-section`` multiplicities are preserved as mappings, not
    collapsed into a single opaque message.

    C13 ADDITIVE field (``sunset_breach``): the frozen FOUR fields above are
    untouched; a FIFTH optional field with a ``None`` default is added per the TDD
    §11 C13 architect ruling (an additive payload-observable extension inside the
    OQ-1 "rich, do-NOT-narrow" mandate — NOT a reason-enum change, NOT a signature
    change, NO version bump). Landing it on the seam type retires the S7 harness's
    anticipatory ``HarnessRefusePayload`` subclass placeholder (which stays valid: a
    slotted subclass that redefines this now-inherited slot resolves to empty own
    slots, so the harness corpus is unbroken — verified by ``tests/harness``).
    """

    plane: str  # which copy / plane the refusal concerns
    absolute_age: Mapping[str, float]  # absolute age (seconds) of EACH copy/plane
    magnitude: float  # divergence magnitude between copies
    per_section_delta: Mapping[str, float]  # per-section composition delta
    # C13 additive (default None): populated ONLY on a sunset-breach refusal, which
    # still carries ``RefuseReason.STALE`` — the marker is what makes it distinguishable.
    sunset_breach: SunsetBreach | None = None


@dataclass(frozen=True, slots=True)
class Provable:
    """A provable served number: value bytes + their freshness proof. Seam 4, FROZEN v1.0."""

    frame: bytes
    proof: FreshnessProof


@dataclass(frozen=True, slots=True)
class Refused:
    """A loud refusal: closed reason + the OQ-1 observable payload. Seam 4, FROZEN v1.0."""

    reason: RefuseReason
    detail: RefusePayload


# PEP 695 alias — valid on 3.12 (PE G3). A bare value is unobtainable without
# handling Refused.
type ServedNumber = Provable | Refused


class SubstrateReader(Protocol):
    """The single public read path → Provable | Refused (never a bare value). Seam 4, FROZEN v1.0."""

    async def read(self, aid: ArtifactId) -> ServedNumber:
        """postcondition: store.read_current → is_provable(proof, canonical_digest(parsed frame), now) → Provable | Refused; NEVER a bare value.

        The gate binds per-read; caching a Provable/ServedNumber result above the
        gate is FORBIDDEN (C2). Owned by S4.
        """
        ...


# ===========================================================================
# S5 IMPLEMENTATION — gated choke-point reader + refusal payload builders +
# serve-side refusal SLI / future-dated anomaly emission (RC-C(serve) / P2 / DP-3).
#
# SEAM-0 froze the contract ABOVE; S5 fills the reader body here (mirroring how S6
# filled substrate.observe below its frozen Protocol). The frozen surface is
# untouched — RefuseReason members, Provable/Refused, ServedNumber, SubstrateReader,
# and RefusePayload's FOUR fields all stand; only the sanctioned C13 `sunset_breach`
# is additive. These symbols import from `substrate.serve`, NOT the package root:
# the frozen `__all__` (guarded at 24 by test_seam_contracts) is unchanged (S6 fan
# precedent). No asyncio.to_thread offload site is introduced (the concurrency guard
# stays green); emission is synchronous best-effort like S6.
# ===========================================================================

# Injected collaborators ([H19] shared predicate): the reader consumes the SAME
# is_provable Seam-1 predicate serving + observability share, INJECTED as a callable,
# plus a digest-of-bytes derivation (parse + canonical_digest) whose concrete frame
# serialization is S4-owned and wired at S8 — the SAME injection S6's evaluator uses,
# so neither serve nor observe hardcodes the not-yet-frozen S4 codec. PEP 695 lazy
# aliases keep the annotation-only names off the runtime import graph.
type IsProvable = Callable[[FreshnessProof, str, datetime], Provability]
type DigestOfFrame = Callable[[bytes], str]
type Clock = Callable[[], datetime]


# --------------------------------------------------------- refusal payloads ---
# Builders that keep the frozen FOUR fields well-formed and multiplicity-preserving
# for every reason (mirrors the S7 harness reference builders, so a sunset case is
# constructed identically on both sides).


def missing_payload() -> RefusePayload:
    """Well-formed payload for a MISSING refusal — no copy exists, so no age.

    Security (enumeration-oracle safe): a MISSING refusal reveals nothing beyond
    "not currently provable" — an empty plane label and an empty age map, IDENTICAL
    whether the artifact was never built or was reaped. Missing-vs-unknown are the
    SAME shape, so the 424 surface is not an existence oracle (a non-servable
    entity_type never reaches serving — it is refused at ArtifactId construction).
    """
    return RefusePayload(plane="", absolute_age={}, magnitude=0.0, per_section_delta={})


def single_copy_payload(plane: str, age_seconds: float) -> RefusePayload:
    """Well-formed payload for a single-copy STALE/CORRUPT refusal: one age entry.

    ``magnitude=0.0`` / ``per_section_delta={}`` because a single canonical artifact
    has no divergence to explain — the DIVERGENT reason with a populated magnitude +
    per-section delta is the two-copy RC-A-2 case (unconstructable through the
    single-source v2 read path; reserved in the CLOSED grammar for the parity harness).
    """
    return RefusePayload(
        plane=plane, absolute_age={plane: age_seconds}, magnitude=0.0, per_section_delta={}
    )


def sunset_stale_payload(
    plane: str, age_seconds: float, *, sunset_after: datetime, observed_at: datetime
) -> RefusePayload:
    """C13-marked payload for a sunset-breach refusal: STALE + a named marker.

    The four frozen fields land exactly as ``single_copy_payload``; the additive
    ``sunset_breach`` makes the surface-lifecycle breach machine-distinguishable from
    an age-only STALE (RC-D-2 stays observable at the payload level with NO new reason
    enum member). The enclosing ``Refused`` still carries ``RefuseReason.STALE`` — the
    marker, not a new enum member, is the discriminator (TDD §11 C13).
    """
    return RefusePayload(
        plane=plane,
        absolute_age={plane: age_seconds},
        magnitude=0.0,
        per_section_delta={},
        sunset_breach=SunsetBreach(
            surface=plane, sunset_after=sunset_after, observed_at=observed_at
        ),
    )


def _plane_label(aid: ArtifactId) -> str:
    """The LOGICAL serving-plane label for a refusal payload (security: no topology).

    ``v2/{entity_type}`` — a logical plane name (matches the harness "v2/offer"
    convention), never an internal S3 key/bucket/version/path. The project_gid is
    omitted from the label: it is a caller-supplied identifier the caller already
    knows, and a path-free label is the refusal-body no-leak posture.
    """
    return f"v2/{aid.entity_type.value}"


# ------------------------------------------------------- serve-side emission ---
# Reuses the ADR-006 put_metric_data SHAPE ([H23]) exactly as S6's
# CloudWatchProvabilityEmitter: a Pascal namespace, frozen metric-name constants, the
# {environment} identity dimension, a synchronous best-effort call.

# Serve-path namespace, sibling to S6's Autom8y/SubstrateProvability. Refusal is a
# FEATURE not an outage (charter P2 / DP-3 sub-decision 1): a DEDICATED refusal count
# with clean attribution is the ratified visibility mechanism — NOT a receiver
# availability 5xx (which would burn the availability SLO for correct behavior).
SUBSTRATE_SERVE_NAMESPACE: str = "Autom8y/SubstrateServe"

# The deployment-scope dimension EVERY metric carries — the load-bearing identity
# contract with the terraform alarms (S6's {environment} lesson: a metric emitted
# without it binds the alarm to a series that never receives a datapoint). Names +
# default match the S6 emitter verbatim so the two seams' alarms share one convention.
DIMENSION_ENVIRONMENT: str = "environment"
DEFAULT_ENVIRONMENT: str = "production"
DIMENSION_REASON: str = "reason"

# The dedicated refusal SLI (DP-3 §Ratification sub-decision 1) — emitted at the
# choke-point on EVERY Refused. Alarmed at {environment}; attributed at
# {environment, reason}.
METRIC_SUBSTRATE_REFUSAL_COUNT: str = "SubstrateRefusalCount"
# Serve-side future-dated-proof anomaly (F8 ruling / QA-s2-freshness §5) — the SAME
# naming family S6 emits on the scheduled sweep (observe.FutureDatedProofCount),
# emitted HERE at serve time so a future-stamped proof is DISCLOSED per-read even
# though is_provable returns PROVABLE for a negative age (the F8 double-hit disclosure).
METRIC_FUTURE_DATED_PROOF_COUNT: str = "FutureDatedProofCount"


class RefusalEmitter(Protocol):
    """Serve-side emission port. DARK this sprint — production wiring is S8's."""

    def emit_refusal(self, aid: ArtifactId, reason: RefuseReason) -> None:
        """Emit the substrate_refusal_count SLI for one refusal at the choke-point."""
        ...

    def emit_future_dated_proof(self, aid: ArtifactId, age_seconds: float) -> None:
        """Disclose a future-dated (negative-age) proof observed at serve time (F8)."""
        ...


class NullRefusalEmitter:
    """No-op emitter — the DARK-build default (no deploy, no AWS). Conforms to the port."""

    def emit_refusal(self, aid: ArtifactId, reason: RefuseReason) -> None:
        return None

    def emit_future_dated_proof(self, aid: ArtifactId, age_seconds: float) -> None:
        return None


class CloudWatchRefusalEmitter:
    """Emits the serve-side refusal SLI + future-dated anomaly via the house put_metric_data shape.

    Best-effort ([H23]): a CloudWatch failure is logged, never raised — an
    observability emit must not take down the serve path. Injectable ``cw_client`` for
    unit proof; production passes None and the lazy boto3 client is built on first
    emit. ``environment`` MUST match the terraform ``var.environment`` or the alarms
    bind to a different series (the identity contract). Synchronous (mirrors S6): no
    asyncio.to_thread offload site is introduced; whether production threads the emit
    is an S8 wiring decision.
    """

    def __init__(
        self, *, environment: str = DEFAULT_ENVIRONMENT, cw_client: Any | None = None
    ) -> None:
        self._environment = environment
        self._cw_client = cw_client

    def emit_refusal(self, aid: ArtifactId, reason: RefuseReason) -> None:
        logger.info(
            "substrate_refusal",
            extra={
                "project_gid": aid.project_gid,
                "entity_type": aid.entity_type.value,
                "reason": reason.value,
            },
        )
        # Two data points: the ALARMED low-cardinality {environment} series (the SLI
        # the RC-F alarms bind to) + an {environment, reason} attribution series.
        self._put(
            [
                {
                    "MetricName": METRIC_SUBSTRATE_REFUSAL_COUNT,
                    "Value": 1.0,
                    "Unit": "Count",
                    "Dimensions": [{"Name": DIMENSION_ENVIRONMENT, "Value": self._environment}],
                },
                {
                    "MetricName": METRIC_SUBSTRATE_REFUSAL_COUNT,
                    "Value": 1.0,
                    "Unit": "Count",
                    "Dimensions": [
                        {"Name": DIMENSION_ENVIRONMENT, "Value": self._environment},
                        {"Name": DIMENSION_REASON, "Value": reason.value},
                    ],
                },
            ]
        )

    def emit_future_dated_proof(self, aid: ArtifactId, age_seconds: float) -> None:
        logger.warning(
            "substrate_future_dated_proof",
            extra={
                "project_gid": aid.project_gid,
                "entity_type": aid.entity_type.value,
                "age_seconds": age_seconds,
            },
        )
        self._put(
            [
                {
                    "MetricName": METRIC_FUTURE_DATED_PROOF_COUNT,
                    "Value": 1.0,
                    "Unit": "Count",
                    "Dimensions": [{"Name": DIMENSION_ENVIRONMENT, "Value": self._environment}],
                }
            ]
        )

    def _put(self, metric_data: list[dict[str, Any]]) -> None:
        client = self._cw_client if self._cw_client is not None else _get_cloudwatch_client()
        try:
            client.put_metric_data(Namespace=SUBSTRATE_SERVE_NAMESPACE, MetricData=metric_data)
        except Exception as exc:  # noqa: BLE001 — best-effort emit; never block serve
            logger.warning(
                "substrate_serve_emit_failed",
                extra={"namespace": SUBSTRATE_SERVE_NAMESPACE, "error": repr(exc)},
            )


def _get_cloudwatch_client() -> Any:
    """Lazy boto3 CloudWatch client (keeps this module boto3-free at import).

    Mirrors ``substrate.observe._get_cloudwatch_client`` (ADR-006 house pattern).
    """
    import os

    import boto3

    region = os.environ.get("AWS_REGION") or os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1")
    return boto3.client("cloudwatch", region_name=region)


# --------------------------------------------------- the gated choke-point ---

# Default future-dated skew tolerance (seconds): ordinary NTP-level clock skew makes
# a freshly-swapped artifact's built_from_live_at marginally exceed the serving
# clock; the F8 ruling (QA-s2-freshness §5.2) REJECTS refusing on that. A future-dated
# DISCLOSURE fires only BEYOND this tolerance (a real bad-stamp / gross skew) so the
# per-read anomaly is not benign-skew noise. Parameterized (not a frozen-core magic
# number) — is_provable is untouched; this governs only the serve-side emission, and
# unlike S6's schedule sweep the serve path is exposed to per-read fresh-swap skew.
_DEFAULT_FUTURE_SKEW_TOLERANCE_SECONDS: float = 5.0


class GatedSubstrateReader:
    """The concrete SubstrateReader — the single public read path (RC-C serve / P2).

    Structurally satisfies the frozen ``SubstrateReader`` Protocol. Every read
    re-runs the gate (C2 — NO result-cache above it): resolve the current artifact,
    derive the served digest at bytes-INGRESS, apply the SAME injected ``is_provable``
    ([H19] shared predicate), and return ``Provable | Refused`` — never a bare value,
    never a 200-shaped stale number. The ``store`` raw byte-reader is reached ONLY
    here + rebuild + observe (the [H17] import-tooth): a consumer cannot obtain bytes
    except through this gate.

    Error taxonomy is deliberate: a DATA-integrity condition (missing / corrupt /
    stale / un-digestable) becomes a ``Refused``; an INFRA condition (a transient S3
    error other than 404/pointer-corruption) PROPAGATES — it is a receiver-health 5xx,
    NOT a 424 data-integrity refusal (TDD RC-F division of labor). Refuse-loud is for
    unprovable DATA, never a mask for infra faults.
    """

    def __init__(
        self,
        *,
        store: ArtifactStore,
        is_provable: IsProvable,
        digest_of_frame: DigestOfFrame,
        emitter: RefusalEmitter | None = None,
        now: Clock | None = None,
        future_skew_tolerance_seconds: float = _DEFAULT_FUTURE_SKEW_TOLERANCE_SECONDS,
    ) -> None:
        self._store = store
        self._is_provable = is_provable
        self._digest_of_frame = digest_of_frame
        self._emitter: RefusalEmitter = emitter if emitter is not None else NullRefusalEmitter()
        self._now: Clock = now if now is not None else _default_now
        self._future_skew_tolerance_seconds = future_skew_tolerance_seconds

    async def read(self, aid: ArtifactId) -> ServedNumber:
        """Resolve → gate → Provable | Refused.

        The gate binds per-read (C2: age arm every read, digest arm at ingress, no
        result-cache above it). The substrate_refusal_count SLI is emitted at THIS
        choke-point on every refusal (DP-3 sub-decision 1).
        """
        plane = _plane_label(aid)
        try:
            frame_bytes, proof = await self._store.read_current(aid)
        except ArtifactMissing:
            # [H5]/[H21] absence is loud — never a bare value / (None, None).
            return self._refuse(aid, RefuseReason.MISSING, missing_payload())
        except PointerCorrupt:
            # Read-side pointer corruption (store QA F5): unprovable, and no trustworthy
            # proof to age → CORRUPT with an empty age map.
            return self._refuse(
                aid,
                RefuseReason.CORRUPT,
                RefusePayload(plane=plane, absolute_age={}, magnitude=0.0, per_section_delta={}),
            )

        now = self._now()
        # C2: the digest arm binds at bytes-INGRESS from the store, re-derived from the
        # PARSED FRAME (never the parquet bytes — the parse is the injected S4 codec).
        try:
            served_digest = self._digest_of_frame(frame_bytes)
        except Exception:  # noqa: BLE001 — un-digestable/foreign bytes are CORRUPT, not a 500
            logger.warning(
                "substrate_serve_undigestable_frame",
                extra={"project_gid": aid.project_gid, "entity_type": aid.entity_type.value},
                exc_info=True,
            )
            age = (now - proof.built_from_live_at).total_seconds()
            self._maybe_disclose_future_dated(aid, age)
            return self._refuse(aid, RefuseReason.CORRUPT, single_copy_payload(plane, age))

        # C2: the age arm executes on EVERY logical read (is_provable, no cache).
        verdict = self._is_provable(proof, served_digest, now)
        age = (now - proof.built_from_live_at).total_seconds()

        # F8 disclosure: a future-dated proof (negative age beyond skew) is an anomaly.
        # is_provable returns PROVABLE for age <= sla (a negative age qualifies); we do
        # NOT invent a verdict and do NOT silently treat-as-fresh — we DISCLOSE and let
        # is_provable's verdict stand (the disclosure IS the "not silent" signal).
        self._maybe_disclose_future_dated(aid, age)

        match verdict:
            case Provability.PROVABLE:
                return Provable(frame=frame_bytes, proof=proof)
            case Provability.STALE:
                return self._refuse(aid, RefuseReason.STALE, single_copy_payload(plane, age))
            case Provability.CORRUPT:
                return self._refuse(aid, RefuseReason.CORRUPT, single_copy_payload(plane, age))
            case _:
                assert_never(verdict)

    def _refuse(self, aid: ArtifactId, reason: RefuseReason, payload: RefusePayload) -> Refused:
        """Build the refusal AND emit the choke-point SLI (every Refused is counted)."""
        self._emitter.emit_refusal(aid, reason)
        return Refused(reason=reason, detail=payload)

    def _maybe_disclose_future_dated(self, aid: ArtifactId, age_seconds: float) -> None:
        if age_seconds < -self._future_skew_tolerance_seconds:
            self._emitter.emit_future_dated_proof(aid, age_seconds)


def _default_now() -> datetime:
    """Default serving clock — tz-aware UTC (is_provable rejects a naive ``now``)."""
    return datetime.now(UTC)
