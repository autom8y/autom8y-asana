"""S5 SERVING — the gated choke-point reader, refusal payloads, and serve-side emission.

Bar: TDD-substrate-v2 §4 Seam 4 ([H14]-[H18], C2) + §3 RC-C(serve) + DP-3
(424 + Retry-After + substrate_refusal_count SLI; shape-hostile bodies; no Refused-200)
+ RC-acceptance RC-C-2 + QA-s2-freshness §5 F8 (negative-age disclosure).

The gate is INJECTED (is_provable + digest_of_frame) exactly as S6's evaluator injects
them — so these tests prove the gate LOGIC with fixtures, no S4 serialization required.
Two-sided: every unprovable state REFUSES (loud, SLI-emitted); every provable state
SERVES; no code path yields a bare value or a 200-shaped stale number.
"""

from __future__ import annotations

import hashlib
import inspect
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.freshness import FreshnessProof, Provability, is_provable
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.serve import (
    DEFAULT_ENVIRONMENT,
    DIMENSION_ENVIRONMENT,
    METRIC_FUTURE_DATED_PROOF_COUNT,
    METRIC_SUBSTRATE_REFUSAL_COUNT,
    SUBSTRATE_SERVE_NAMESPACE,
    CloudWatchRefusalEmitter,
    GatedSubstrateReader,
    NullRefusalEmitter,
    Provable,
    Refused,
    RefusePayload,
    RefuseReason,
    SubstrateReader,
    SunsetBreach,
    missing_payload,
    single_copy_payload,
    sunset_stale_payload,
)
from autom8_asana.substrate.store import ArtifactMissing, PointerCorrupt

if TYPE_CHECKING:
    from autom8_asana.substrate.serve import IsProvable, RefusalEmitter

NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC)
AID = ArtifactId(project_gid="1200000000000001", entity_type=EntityType.OFFER)


def _digest_of(raw: bytes) -> str:
    """The injected served-digest derivation (a stand-in for parse+canonical_digest)."""
    return hashlib.sha256(raw).hexdigest()


def _provable_entry(raw: bytes = b"frame-fresh") -> tuple[bytes, FreshnessProof]:
    return raw, FreshnessProof(
        built_from_live_at=NOW - timedelta(seconds=60),
        content_digest=_digest_of(raw),
        sla_seconds=3600,
    )


def _stale_entry(raw: bytes = b"frame-stale") -> tuple[bytes, FreshnessProof]:
    return raw, FreshnessProof(
        built_from_live_at=NOW - timedelta(seconds=7200),
        content_digest=_digest_of(raw),
        sla_seconds=3600,
    )


def _corrupt_entry(raw: bytes = b"frame-rotted") -> tuple[bytes, FreshnessProof]:
    """Fresh age, but the recorded digest diverges from the bytes' re-derived digest."""
    return raw, FreshnessProof(
        built_from_live_at=NOW - timedelta(seconds=60),
        content_digest=_digest_of(b"frame-before-rot"),
        sla_seconds=3600,
    )


def _future_entry(raw: bytes = b"frame-future") -> tuple[bytes, FreshnessProof]:
    return raw, FreshnessProof(
        built_from_live_at=NOW + timedelta(days=365),
        content_digest=_digest_of(raw),
        sla_seconds=3600,
    )


class FakeStore:
    """Minimal ``ArtifactStore`` — only ``read_current`` is exercised by the reader."""

    def __init__(
        self,
        entries: dict[ArtifactId, tuple[bytes, FreshnessProof]] | None = None,
        errors: dict[ArtifactId, Exception] | None = None,
    ) -> None:
        self._entries = entries or {}
        self._errors = errors or {}

    async def read_current(self, aid: ArtifactId) -> tuple[bytes, FreshnessProof]:
        if aid in self._errors:
            raise self._errors[aid]
        if aid not in self._entries:
            raise ArtifactMissing(f"no current pointer for {aid.project_gid}")
        return self._entries[aid]

    async def stage_version(
        self, aid: ArtifactId, frame_bytes: bytes, proof: FreshnessProof
    ) -> Any:
        raise NotImplementedError

    async def swap_pointer(self, aid: ArtifactId, to: Any, *, if_match: Any) -> None:
        raise NotImplementedError

    async def list_versions(self, aid: ArtifactId) -> list[Any]:
        raise NotImplementedError

    async def gc_versions(self, aid: ArtifactId, keep_after: datetime) -> int:
        raise NotImplementedError


class RecordingEmitter:
    """Captures refusal + future-dated signals without touching AWS (DARK)."""

    def __init__(self) -> None:
        self.refusals: list[RefuseReason] = []
        self.future_dated: list[float] = []

    def emit_refusal(self, aid: ArtifactId, reason: RefuseReason) -> None:
        self.refusals.append(reason)

    def emit_future_dated_proof(self, aid: ArtifactId, age_seconds: float) -> None:
        self.future_dated.append(age_seconds)


class RecordingCwClient:
    """Fake boto3 CloudWatch client — records ``put_metric_data`` calls; never touches AWS."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[dict[str, Any]] = []
        self._fail = fail

    def put_metric_data(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)
        if self._fail:
            raise RuntimeError("simulated CloudWatch put_metric_data failure")


def _reader(
    store: FakeStore,
    *,
    emitter: RefusalEmitter | None = None,
    is_provable_fn: IsProvable = is_provable,
    digest_of_frame: Any = _digest_of,
    now: datetime = NOW,
) -> GatedSubstrateReader:
    return GatedSubstrateReader(
        store=store,
        is_provable=is_provable_fn,
        digest_of_frame=digest_of_frame,
        emitter=emitter,
        now=lambda: now,
    )


# --------------------------------------------------------- protocol conformance ---


def test_gated_reader_satisfies_frozen_protocol() -> None:
    """The S5 reader structurally satisfies the FROZEN ``SubstrateReader`` Protocol."""
    reader = _reader(FakeStore())
    typed: SubstrateReader = reader  # mypy-checked structural conformance
    assert inspect.iscoroutinefunction(typed.read)


# ------------------------------------------------- two-sided gate mapping (RC-C) ---


async def test_provable_serves_and_emits_no_refusal() -> None:
    emitter = RecordingEmitter()
    reader = _reader(FakeStore({AID: _provable_entry()}), emitter=emitter)
    served = await reader.read(AID)
    assert isinstance(served, Provable)
    assert served.frame == b"frame-fresh"
    assert emitter.refusals == []  # a provable read never counts as a refusal


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (_stale_entry(), RefuseReason.STALE),
        (_corrupt_entry(), RefuseReason.CORRUPT),
    ],
)
async def test_unprovable_refuses_loud_and_emits_sli(
    entry: tuple[bytes, FreshnessProof], expected: RefuseReason
) -> None:
    emitter = RecordingEmitter()
    reader = _reader(FakeStore({AID: entry}), emitter=emitter)
    served = await reader.read(AID)
    assert isinstance(served, Refused)
    assert served.reason is expected
    # The substrate_refusal_count SLI fires at the choke-point on EVERY refusal (DP-3).
    assert emitter.refusals == [expected]


async def test_missing_artifact_refuses_missing_with_empty_payload() -> None:
    emitter = RecordingEmitter()
    reader = _reader(FakeStore(entries={}), emitter=emitter)  # read_current raises ArtifactMissing
    served = await reader.read(AID)
    assert isinstance(served, Refused)
    assert served.reason is RefuseReason.MISSING
    # Enumeration-oracle safe: no plane, no age — reveals only "not provable".
    assert served.detail.plane == ""
    assert served.detail.absolute_age == {}
    assert emitter.refusals == [RefuseReason.MISSING]


async def test_pointer_corrupt_refuses_corrupt_with_no_age() -> None:
    store = FakeStore(errors={AID: PointerCorrupt("current.json malformed")})
    reader = _reader(store)
    served = await reader.read(AID)
    assert isinstance(served, Refused)
    assert served.reason is RefuseReason.CORRUPT
    assert served.detail.absolute_age == {}  # no trustworthy proof to age


async def test_undigestable_frame_is_corrupt_not_a_crash() -> None:
    """A frame the injected digest cannot derive (foreign/partial/rotted) → CORRUPT, loud."""

    def _raises(_: bytes) -> str:
        raise ValueError("frame is missing pinned value columns")

    emitter = RecordingEmitter()
    reader = _reader(FakeStore({AID: _provable_entry()}), emitter=emitter, digest_of_frame=_raises)
    served = await reader.read(AID)
    assert isinstance(served, Refused)
    assert served.reason is RefuseReason.CORRUPT
    assert emitter.refusals == [RefuseReason.CORRUPT]


async def test_no_code_path_yields_a_200_shaped_stale_number() -> None:
    """The two-sided invariant: every unprovable state is Refused (never a bare value).

    The SUPERSEDED ADR-serve-stale-within-bound's stale-200 paradigm is unconstructable
    here: a stale/corrupt/missing state can only produce ``Refused``.
    """
    for entry_or_missing in (_stale_entry(), _corrupt_entry()):
        served = await _reader(FakeStore({AID: entry_or_missing})).read(AID)
        assert isinstance(served, Refused)
    served_missing = await _reader(FakeStore(entries={})).read(AID)
    assert isinstance(served_missing, Refused)


async def test_infra_error_propagates_not_masked_as_refusal() -> None:
    """A non-404/non-corrupt store error is INFRA (receiver 5xx), NOT a 424 data refusal.

    Refuse-loud is for unprovable DATA; masking an infra fault as a refusal would hide a
    receiver-health signal (TDD RC-F division of labor).
    """
    store = FakeStore(errors={AID: RuntimeError("S3 throttled")})
    with pytest.raises(RuntimeError, match="S3 throttled"):
        await _reader(store).read(AID)


# --------------------------------------------------- the gate binds per-read (C2) ---


async def test_gate_reruns_is_provable_every_read_no_result_cache() -> None:
    """C2: the age arm executes on EVERY logical read — no memoized ServedNumber."""
    calls: list[int] = []

    def _counting_is_provable(proof: FreshnessProof, digest: str, now: datetime) -> Provability:
        calls.append(1)
        return is_provable(proof, digest, now)

    reader = _reader(FakeStore({AID: _provable_entry()}), is_provable_fn=_counting_is_provable)
    await reader.read(AID)
    await reader.read(AID)
    assert len(calls) == 2  # re-gated each read, not served from a cached verdict


# -------------------------------------------- F8 negative-age disclosure (QA §5) ---


async def test_future_dated_proof_is_disclosed_and_still_serves() -> None:
    """A future-dated proof → PROVABLE (per is_provable) AND a FutureDatedProofCount anomaly.

    The F8 ruling: do NOT invent a verdict, do NOT silently treat-as-fresh — DISCLOSE and
    let is_provable's verdict stand. The disclosure IS the "not silent" signal.
    """
    emitter = RecordingEmitter()
    reader = _reader(FakeStore({AID: _future_entry()}), emitter=emitter)
    served = await reader.read(AID)
    assert isinstance(served, Provable)  # is_provable returns PROVABLE for negative age
    assert len(emitter.future_dated) == 1
    assert emitter.future_dated[0] < 0  # the negative age was disclosed


async def test_benign_sub_tolerance_skew_does_not_disclose() -> None:
    """Ordinary NTP-level skew (a freshly-swapped artifact marginally ahead) is NOT noise.

    F8 §5.2: the disclosure fires only BEYOND the skew tolerance, so a fresh swap does not
    spam a per-read anomaly.
    """
    raw = b"frame-just-swapped"
    proof = FreshnessProof(
        built_from_live_at=NOW + timedelta(seconds=1),
        content_digest=_digest_of(raw),
        sla_seconds=3600,
    )
    emitter = RecordingEmitter()
    reader = _reader(FakeStore({AID: (raw, proof)}), emitter=emitter)  # default tolerance 5s
    served = await reader.read(AID)
    assert isinstance(served, Provable)
    assert emitter.future_dated == []  # 1s < 5s tolerance → no anomaly


# ------------------------------------------------- refusal payload builders (C13) ---


def test_missing_payload_is_empty_and_unmarked() -> None:
    payload = missing_payload()
    assert payload == RefusePayload(plane="", absolute_age={}, magnitude=0.0, per_section_delta={})
    assert payload.sunset_breach is None


def test_single_copy_payload_carries_one_age_and_no_divergence() -> None:
    payload = single_copy_payload("v2/offer", 7200.0)
    assert payload.absolute_age == {"v2/offer": 7200.0}
    assert payload.magnitude == 0.0
    assert payload.per_section_delta == {}
    assert payload.sunset_breach is None  # a plain STALE is NOT a sunset breach


def test_sunset_payload_marks_the_breach_but_reason_stays_stale() -> None:
    """C13: a sunset-breach STALE carries the named marker; the reason enum stays closed."""
    sunset_after = datetime(2026, 6, 1, tzinfo=UTC)
    payload = sunset_stale_payload("v2/offer", 999.0, sunset_after=sunset_after, observed_at=NOW)
    assert isinstance(payload.sunset_breach, SunsetBreach)
    assert payload.sunset_breach.surface == "v2/offer"
    assert payload.sunset_breach.sunset_after == sunset_after
    assert payload.sunset_breach.observed_at == NOW
    # the frozen FOUR are exactly the single-copy shape — nothing narrowed.
    assert payload.absolute_age == {"v2/offer": 999.0}
    # a sunset-breach Refused still carries STALE (no EXPIRED member — C13).
    refused = Refused(reason=RefuseReason.STALE, detail=payload)
    assert refused.reason is RefuseReason.STALE


def test_c13_additive_field_leaves_frozen_four_constructible() -> None:
    """The frozen 4-field ctor still works (default None) — additive, not a signature change."""
    payload = RefusePayload(plane="v2/offer", absolute_age={}, magnitude=0.0, per_section_delta={})
    assert payload.sunset_breach is None


def test_refusal_payloads_carry_no_topology() -> None:
    """Security: no plane label leaks an S3 key / bucket / version / path."""
    for payload in (
        single_copy_payload("v2/offer", 1.0),
        sunset_stale_payload("v2/offer", 1.0, sunset_after=NOW, observed_at=NOW),
    ):
        assert payload.plane == "v2/offer"
        assert "dataframes-v2" not in payload.plane
        assert "/" not in payload.plane.removeprefix("v2/")  # no nested path segments


# --------------------------------------------------------- CloudWatch emission ---


def test_cloudwatch_emitter_refusal_carries_environment_and_reason() -> None:
    """The SLI is emitted at {environment} (alarmed) AND {environment, reason} (attribution).

    The {environment} dimension is the load-bearing identity contract (S6's lesson): a
    metric without it binds the alarm to a series that never receives a datapoint.
    """
    cw = RecordingCwClient()
    emitter = CloudWatchRefusalEmitter(cw_client=cw)
    emitter.emit_refusal(AID, RefuseReason.STALE)
    assert len(cw.calls) == 1
    call = cw.calls[0]
    assert call["Namespace"] == SUBSTRATE_SERVE_NAMESPACE
    data = call["MetricData"]
    assert all(d["MetricName"] == METRIC_SUBSTRATE_REFUSAL_COUNT for d in data)
    # every datum carries {environment}; one is attributed by {reason}.
    for datum in data:
        dims = {d["Name"]: d["Value"] for d in datum["Dimensions"]}
        assert dims[DIMENSION_ENVIRONMENT] == DEFAULT_ENVIRONMENT
    reason_dims = [d for d in data if any(dim["Name"] == "reason" for dim in d["Dimensions"])]
    assert len(reason_dims) == 1
    assert reason_dims[0]["Dimensions"][-1]["Value"] == "stale"


def test_cloudwatch_emitter_future_dated_uses_the_s6_naming_family() -> None:
    cw = RecordingCwClient()
    CloudWatchRefusalEmitter(cw_client=cw).emit_future_dated_proof(AID, -86400.0)
    assert len(cw.calls) == 1
    data = cw.calls[0]["MetricData"]
    assert [d["MetricName"] for d in data] == [METRIC_FUTURE_DATED_PROOF_COUNT]
    assert data[0]["Dimensions"][0]["Name"] == DIMENSION_ENVIRONMENT


def test_cloudwatch_emit_is_best_effort_never_raises() -> None:
    """A CloudWatch failure must not take down the serve path (best-effort, logged)."""
    cw = RecordingCwClient(fail=True)
    emitter = CloudWatchRefusalEmitter(cw_client=cw)
    emitter.emit_refusal(AID, RefuseReason.MISSING)  # must not raise
    emitter.emit_future_dated_proof(AID, -1.0)  # must not raise
    assert len(cw.calls) == 2  # both attempted


async def test_reader_default_emitter_is_null_and_never_touches_aws() -> None:
    """The DARK-build default emitter is a no-op — a refusal works with no AWS wiring."""
    reader = GatedSubstrateReader(
        store=FakeStore({AID: _stale_entry()}),
        is_provable=is_provable,
        digest_of_frame=_digest_of,
        now=lambda: NOW,
    )
    assert isinstance(reader._emitter, NullRefusalEmitter)  # noqa: SLF001 — behavior-anchoring
    served = await reader.read(AID)
    assert isinstance(served, Refused)  # refuses without any emitter wired
