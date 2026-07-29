"""SubstrateRebuilder — stage-validate-swap (Seam 3, RC-E) under Seam-2 **v1.1** (C15).

Composes the REAL S2 freshness + S3 store against the house S3 double (moto
``mock_aws``); the live Asana leg is a FAKE ``PacedAsanaFetcher`` (dark build,
prod_touch NONE). Every obligation is proven two-sided:

* **C9 / F2** — validate gates the swap AND the ValidationReceipt binds the FULL proof
  (version_id + content_digest + built_from_live_at): a rejected version is not
  published (GREEN), a miswired swap-before-validate publishes it (RED-caught), and a
  same-bytes proof-SUBSTITUTION cannot ride an honest receipt.
* **C12** — a staged build strictly older than current is DISCARDED not swapped; a CAS
  loss re-reads and re-applies monotonicity; a forward build SWAPS.
* **C15 (F1 root fix — the DELTA teeth)** — the store persists proof ONLY in the
  pointer, written ONLY by the validated path: **P1** (A→B→A does NOT regress the
  pointer proof), **P3** (a validate-REJECTED future staging leaves NO poison →
  PROVABLE-at-negative-age is unconstructable), **P4** (a re-verified version publishes
  its fresh validated proof, not a frozen T0). N1 graft coherence → ``ProofDigestMismatch``
  loud.
* **C16** — a partial/silently-gapped fetch is ``FETCH_REFUSED`` (incumbent untouched);
  a complete fetch SWAPS. ``min_rows >= 1`` construction guard.
* **RC-E (DEFECT-seam1 :76)** — a mid-fetch abort leaves the store BYTE-IDENTICAL.
* **C1** — reused sections keep their instant through the MIN-fold.
* **[H9]/RC-E-4** — the rebuilder has no serve-read; ``substrate.rebuild`` imports no
  ``AsanaClient``. **CAP-4** — ``FetchTelemetry`` rides ``RebuildResult``.
"""

from __future__ import annotations

import ast
import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.substrate import ArtifactId, FreshnessProof
from autom8_asana.substrate import rebuild as rebuild_module
from autom8_asana.substrate.freshness import (
    Provability,
    canonical_digest,
    fold_built_from_live_at,
    is_provable,
)
from autom8_asana.substrate.rebuild import (
    DefaultAcceptancePredicates,
    FetchedSections,
    FetchRefused,
    FetchTelemetry,
    LocalSingleFlight,
    PacedAsanaFetcher,
    Rebuilder,
    RebuildOutcome,
    StagedVersion,
    SubstrateRebuilder,
    ValidationFailure,
    ValidationReceipt,
    canonical_frame_bytes,
)
from autom8_asana.substrate.store import (
    ArtifactMissing,
    ETag,
    ProofDigestMismatch,
    S3ArtifactStore,
    VersionId,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

try:
    import boto3
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:  # pragma: no cover - moto is a dev dep; guard mirrors the house pattern
    MOTO_AVAILABLE = False

pytestmark = pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")

_BUCKET = "substrate-v2-rebuild-test"

# Fixed instants (all in the past relative to NOW so proofs are well-formed).
T0 = datetime(2026, 7, 29, 10, 0, tzinfo=UTC)
T1 = datetime(2026, 7, 29, 11, 0, tzinfo=UTC)
T2 = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
T3 = datetime(2026, 7, 29, 13, 0, tzinfo=UTC)
NOW = datetime(2026, 7, 29, 14, 0, tzinfo=UTC)


def _now() -> datetime:
    return NOW


def _sla(_entity: EntityType) -> int:
    return 3600


def _offer_frame(*, offers: int = 3) -> pl.DataFrame:
    """A populated offer frame carrying the pinned value columns (non-null)."""
    return pl.DataFrame(
        {
            "offer_id": [f"offer-{i}" for i in range(offers)],
            "cost": [100 + i for i in range(offers)],
            "mrr": [500 + i for i in range(offers)],
            "weekly_ad_spend": [10 + i for i in range(offers)],
        }
    )


def _empty_offer_frame() -> pl.DataFrame:
    """Schema-correct but 0 rows — validate's population-floor must reject it."""
    return pl.DataFrame(
        schema={
            "offer_id": pl.String,
            "cost": pl.Int64,
            "mrr": pl.Int64,
            "weekly_ad_spend": pl.Int64,
        }
    )


@pytest.fixture
def aid() -> ArtifactId:
    return ArtifactId(project_gid="1200000000000042", entity_type=EntityType.OFFER)


@pytest.fixture
def store() -> Iterator[S3ArtifactStore]:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        yield S3ArtifactStore(_BUCKET, client=client)


def _rebuilder(store: S3ArtifactStore, **kw: object) -> SubstrateRebuilder:
    kw.setdefault("now", _now)
    kw.setdefault("sla_for", _sla)
    return SubstrateRebuilder(store, **kw)  # type: ignore[arg-type]


class _FakeFetcher:
    """Injected paced fetcher — a canned materialised frame + provenance + C16 accounting."""

    def __init__(
        self,
        frame: pl.DataFrame,
        instants: Mapping[str, datetime],
        *,
        requested: frozenset[str] | None = None,
        failed: frozenset[str] = frozenset(),
        telemetry: FetchTelemetry | None = None,
    ) -> None:
        self._frame = frame
        self._instants = dict(instants)
        self._requested = frozenset(instants) if requested is None else requested
        self._failed = failed
        self._telemetry = telemetry
        self.calls: list[ArtifactId] = []

    async def fetch(self, aid: ArtifactId) -> FetchedSections:
        self.calls.append(aid)
        return FetchedSections(
            frame=self._frame,
            section_instants=self._instants,
            requested_sections=self._requested,
            failed_sections=self._failed,
            telemetry=self._telemetry,
        )


class _RaisingFetcher:
    """A fetch that aborts mid-way (section k of n) — the DEFECT :76 counterexample."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc
        self.calls = 0

    async def fetch(self, aid: ArtifactId) -> FetchedSections:
        self.calls += 1
        raise self._exc


def _snapshot(store: S3ArtifactStore) -> dict[str, str]:
    """Every key in the bucket -> its ETag (the whole-store byte-identity fingerprint)."""
    client = store._s3()  # noqa: SLF001 — test reaches the injected moto client
    resp = client.list_objects_v2(Bucket=_BUCKET)
    return {obj["Key"]: obj["ETag"] for obj in resp.get("Contents", [])}


async def _seed(store: S3ArtifactStore, aid: ArtifactId, frame: pl.DataFrame, at: datetime) -> str:
    """Publish a first version directly (bypassing the rebuilder) — v1.1 stage+swap(proof)."""
    proof = FreshnessProof(
        built_from_live_at=at, content_digest=canonical_digest(frame), sla_seconds=3600
    )
    frame_bytes = canonical_frame_bytes(frame)
    version_id = await store.stage_version(aid, frame_bytes)
    await store.swap_pointer(aid, version_id, proof, if_match=rebuild_module.CREATE_IF_ABSENT)
    return str(version_id)


# =============================================================== happy path ===
async def test_first_rebuild_swaps_and_serves(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """A first rebuild stages, validates, and CAS-creates the pointer → served."""
    frame = _offer_frame()
    fetcher = _FakeFetcher(frame, {"section-a": T1, "section-b": T2})
    result = await _rebuilder(store).rebuild(aid, fetcher, DefaultAcceptancePredicates())

    assert result.outcome is RebuildOutcome.SWAPPED
    assert result.built_from_live_at == T1  # MIN over {T1, T2}
    served_bytes, served_proof = await store.read_current(aid)
    assert served_bytes == canonical_frame_bytes(frame)
    assert served_proof.built_from_live_at == T1
    assert served_proof.content_digest == canonical_digest(frame)


# ================================================================= C9 / F2 ===
async def test_validation_failure_does_not_publish(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """A rejected staged version is STAGED_REJECTED; the pointer is never created."""
    fetcher = _FakeFetcher(_empty_offer_frame(), {"section-a": T1})
    result = await _rebuilder(store).rebuild(aid, fetcher, DefaultAcceptancePredicates())

    assert result.outcome is RebuildOutcome.STAGED_REJECTED
    assert "population-floor" in result.detail
    with pytest.raises(ArtifactMissing):
        await store.read_current(aid)  # live untouched — partial ≠ corrupt


class _SwapBeforeValidateRebuilder(SubstrateRebuilder):
    """MISWIRED variant: publishes WITHOUT validating (fabricates the C9 receipt)."""

    async def _rebuild_once(
        self,
        aid: ArtifactId,
        fetch: PacedAsanaFetcher,
        validate: object,  # deliberately ignored — the miswire
    ) -> rebuild_module.RebuildResult:
        fetched = await fetch.fetch(aid)
        proof = FreshnessProof(
            built_from_live_at=fold_built_from_live_at(fetched.section_instants),
            content_digest=canonical_digest(fetched.frame),
            sla_seconds=self._sla_for(aid.entity_type),
        )
        frame_bytes = self._serialize(fetched.frame)
        version_id = await self._store.stage_version(aid, frame_bytes)
        staged = StagedVersion(
            version_id=version_id, frame=fetched.frame, frame_bytes=frame_bytes, proof=proof
        )
        forged = ValidationReceipt(  # fabricate the full-proof receipt
            version_id=version_id,
            content_digest=proof.content_digest,
            built_from_live_at=proof.built_from_live_at,
        )
        return await self._publish(aid, staged, forged)  # SWAP with no validation


async def test_swap_before_validate_is_caught_discriminating(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C9 FLOOR (two-sided teeth): validate-gates-swap, and it bites.

    GREEN — the correctly-wired rebuilder never publishes a version validate rejects.
    RED-caught — the miswired swap-before-validate variant publishes the SAME rejected
    version, proving the ordering guard is the only thing preventing the corruption.
    """
    rejected_frame = _empty_offer_frame()
    predicates = DefaultAcceptancePredicates()

    correct = _rebuilder(store)
    green = await correct.rebuild(aid, _FakeFetcher(rejected_frame, {"s": T1}), predicates)
    assert green.outcome is RebuildOutcome.STAGED_REJECTED
    with pytest.raises(ArtifactMissing):
        await store.read_current(aid)

    miswired = _SwapBeforeValidateRebuilder(store, now=_now, sla_for=_sla)
    red = await miswired.rebuild(aid, _FakeFetcher(rejected_frame, {"s": T1}), predicates)
    assert red.outcome is RebuildOutcome.SWAPPED  # the corruption the guard forbids
    served_bytes, _ = await store.read_current(aid)
    assert served_bytes == canonical_frame_bytes(rejected_frame)


async def test_publish_rejects_receipt_for_wrong_version(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C9 construction: ``_publish`` refuses a receipt not bound to the staged version."""
    frame = _offer_frame()
    proof = FreshnessProof(
        built_from_live_at=T1, content_digest=canonical_digest(frame), sla_seconds=3600
    )
    frame_bytes = canonical_frame_bytes(frame)
    version_id = await store.stage_version(aid, frame_bytes)
    staged = StagedVersion(version_id=version_id, frame=frame, frame_bytes=frame_bytes, proof=proof)
    wrong = ValidationReceipt(
        version_id=VersionId("deadbeef"), content_digest="x", built_from_live_at=T1
    )
    with pytest.raises(ValueError, match="does not bind"):
        await _rebuilder(store)._publish(aid, staged, wrong)  # noqa: SLF001


async def test_publish_rejects_proof_substitution_via_full_binding(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """F2 (PROBE-P2): a same-bytes proof-SUBSTITUTION cannot ride an honest receipt.

    An honest receipt minted for proof@T2 does not bind a StagedVersion carrying the
    SAME content_digest but a FUTURE built_from_live_at — ``_publish`` refuses it.
    """
    frame = _offer_frame()
    digest = canonical_digest(frame)
    frame_bytes = canonical_frame_bytes(frame)
    version_id = await store.stage_version(aid, frame_bytes)
    honest_receipt = ValidationReceipt(
        version_id=version_id, content_digest=digest, built_from_live_at=T2
    )
    substituted = StagedVersion(
        version_id=version_id,
        frame=frame,
        frame_bytes=frame_bytes,
        proof=FreshnessProof(
            built_from_live_at=NOW + timedelta(days=1), content_digest=digest, sla_seconds=3600
        ),
    )
    with pytest.raises(ValueError, match="does not bind"):
        await _rebuilder(store)._publish(aid, substituted, honest_receipt)  # noqa: SLF001


# ==================================================================== C12 ===
async def test_older_build_declined_not_swapped(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """C12: a byte-changed staged build strictly older than current is DISCARDED."""
    current_frame = _offer_frame(offers=5)
    await _seed(store, aid, current_frame, T2)

    older_frame = _offer_frame(offers=2)
    result = await _rebuilder(store).rebuild(
        aid, _FakeFetcher(older_frame, {"s": T1}), DefaultAcceptancePredicates()
    )

    assert result.outcome is RebuildOutcome.STAGED_REJECTED
    assert "will not regress" in result.detail
    served_bytes, served_proof = await store.read_current(aid)
    assert served_bytes == canonical_frame_bytes(current_frame)  # pointer UNCHANGED
    assert served_proof.built_from_live_at == T2


async def test_forward_build_swaps(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """C12 (other side): a byte-changed build newer than current SWAPS."""
    await _seed(store, aid, _offer_frame(offers=5), T1)
    newer_frame = _offer_frame(offers=2)
    result = await _rebuilder(store).rebuild(
        aid, _FakeFetcher(newer_frame, {"s": T3}), DefaultAcceptancePredicates()
    )

    assert result.outcome is RebuildOutcome.SWAPPED
    served_bytes, served_proof = await store.read_current(aid)
    assert served_bytes == canonical_frame_bytes(newer_frame)
    assert served_proof.built_from_live_at == T3


class _RaceOnFirstSwap(S3ArtifactStore):
    """Injects a concurrent forward swap right before this rebuild's first real swap.

    Models a cross-process rebuild that lands a competing version between our
    read_pointer and our swap — so our ``If-Match`` is stale and 412s (CASLost). The
    C12 contract: we must re-read and re-apply monotonicity before retrying.
    """

    def __init__(
        self, *args: object, winner_frame: pl.DataFrame, winner_at: datetime, **kw: object
    ) -> None:
        super().__init__(*args, **kw)  # type: ignore[arg-type]
        self._winner_frame = winner_frame
        self._winner_at = winner_at
        self._fired = False

    async def swap_pointer(
        self, aid: ArtifactId, to: VersionId, proof: FreshnessProof, *, if_match: ETag
    ) -> None:
        # Only race the rebuilder's real-ETag advance-swap, not the CREATE_IF_ABSENT seed.
        if not self._fired and if_match != rebuild_module.CREATE_IF_ABSENT:
            self._fired = True
            await _seed_swap(self, aid, self._winner_frame, self._winner_at)
        await super().swap_pointer(aid, to, proof, if_match=if_match)


async def _seed_swap(
    store: S3ArtifactStore, aid: ArtifactId, frame: pl.DataFrame, at: datetime
) -> None:
    """Advance the pointer to a fresh version via the store's real CAS (winner path)."""
    proof = FreshnessProof(
        built_from_live_at=at, content_digest=canonical_digest(frame), sla_seconds=3600
    )
    frame_bytes = canonical_frame_bytes(frame)
    version_id = await store.stage_version(aid, frame_bytes)
    current = await store.read_pointer(aid)
    if current is None:
        await store.swap_pointer(aid, version_id, proof, if_match=rebuild_module.CREATE_IF_ABSENT)
    else:
        await store.swap_pointer(aid, version_id, proof, if_match=current.etag)


async def test_cas_loss_rereads_and_declines_staler_build(aid: ArtifactId) -> None:
    """C12: on a CAS (If-Match) failure the rebuilder re-reads and re-applies monotonicity."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        winner_frame = _offer_frame(offers=9)
        store = _RaceOnFirstSwap(_BUCKET, client=client, winner_frame=winner_frame, winner_at=T3)
        await _seed(store, aid, _offer_frame(offers=5), T1)

        my_frame = _offer_frame(offers=2)  # my build @ T2 — STALER than the racing winner (T3)
        result = await _rebuilder(store).rebuild(
            aid, _FakeFetcher(my_frame, {"s": T2}), DefaultAcceptancePredicates()
        )

        assert result.outcome is RebuildOutcome.STAGED_REJECTED  # declined after re-read
        served_bytes, served_proof = await store.read_current(aid)
        assert served_bytes == canonical_frame_bytes(winner_frame)  # the T3 winner stands
        assert served_proof.built_from_live_at == T3


# ===================================== C15 regression teeth (F1 P1/P3/P4) ===
async def test_p1_recurrence_does_not_regress_pointer_proof(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C15/P1: A→B→A publishes A-again's HONEST fresh proof — the pointer never regresses.

    Under the old wound the byte-changed swap republished A's first-stage frozen T0
    metadata proof (a 3-hour freshness regression, zero adversarial input). C15 kills it.
    """
    frame_a = _offer_frame(offers=3)
    frame_b = _offer_frame(offers=5)
    rebuilder = _rebuilder(store)

    await rebuilder.rebuild(aid, _FakeFetcher(frame_a, {"s": T0}), DefaultAcceptancePredicates())
    await rebuilder.rebuild(aid, _FakeFetcher(frame_b, {"s": T2}), DefaultAcceptancePredicates())
    again = await rebuilder.rebuild(
        aid, _FakeFetcher(frame_a, {"s": T3}), DefaultAcceptancePredicates()
    )

    assert again.outcome is RebuildOutcome.SWAPPED
    assert again.built_from_live_at == T3  # RebuildResult truthful
    served_bytes, served_proof = await store.read_current(aid)
    assert served_bytes == canonical_frame_bytes(frame_a)
    assert served_proof.built_from_live_at == T3  # NOT regressed to T0


async def test_p3_rejected_future_staging_leaves_no_poison(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C15/P3 (the UNCURABLE wound, now unconstructable): a validate-REJECTED future
    staging poisons nothing; a later honest rebuild publishes ONLY its honest proof.
    """
    frame = _offer_frame()
    rebuilder = _rebuilder(store)

    # 1. clock-skewed fetch → FUTURE instant → validate REJECTS (proof-well-formedness).
    rejected = await rebuilder.rebuild(
        aid, _FakeFetcher(frame, {"s": NOW + timedelta(days=1)}), DefaultAcceptancePredicates()
    )
    assert rejected.outcome is RebuildOutcome.STAGED_REJECTED
    assert "proof-well-formedness" in rejected.detail
    with pytest.raises(ArtifactMissing):
        await store.read_current(aid)  # no pointer, and the staged version carries NO proof

    # 2. a later HONEST rebuild of the SAME bytes publishes ONLY its honest validated proof.
    honest = await rebuilder.rebuild(
        aid, _FakeFetcher(frame, {"s": T3}), DefaultAcceptancePredicates()
    )
    assert honest.outcome is RebuildOutcome.SWAPPED
    _, served_proof = await store.read_current(aid)
    assert served_proof.built_from_live_at == T3
    # PROVABLE-at-NEGATIVE-age is unconstructable — is_provable sees a POSITIVE age.
    assert is_provable(served_proof, canonical_digest(frame), NOW) is Provability.PROVABLE
    assert (NOW - served_proof.built_from_live_at).total_seconds() > 0


async def test_p4_reverified_fresh_build_wins_with_validated_proof(aid: ArtifactId) -> None:
    """C15/P4: a re-verified version that wins a race publishes ITS fresh validated proof.

    Old wound: swapping back to X republished X's frozen T0 metadata (regressed below the
    racing winner AND X's own re-verified instant). C15 publishes the validated T3.
    """
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        winner_frame = _offer_frame(offers=7)
        store = _RaceOnFirstSwap(_BUCKET, client=client, winner_frame=winner_frame, winner_at=T2)
        await _seed(store, aid, _offer_frame(offers=3), T0)

        my_frame = _offer_frame(offers=2)  # re-verified FRESH at T3 (fresher than the racing T2)
        result = await _rebuilder(store).rebuild(
            aid, _FakeFetcher(my_frame, {"s": T3}), DefaultAcceptancePredicates()
        )

        assert result.outcome is RebuildOutcome.SWAPPED
        assert result.built_from_live_at == T3
        _, served_proof = await store.read_current(aid)
        assert (
            served_proof.built_from_live_at == T3
        )  # MY validated proof, not a frozen metadata one


async def test_bytestable_content_advances_proof_forward(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C15 byte-stable advance (the F1 availability cure, now via the uniform swap path)."""
    frame = _offer_frame()
    rebuilder = _rebuilder(store)

    first = await rebuilder.rebuild(
        aid, _FakeFetcher(frame, {"s": T1}), DefaultAcceptancePredicates()
    )
    assert first.outcome is RebuildOutcome.SWAPPED
    _, proof_1 = await store.read_current(aid)
    assert proof_1.built_from_live_at == T1

    second = await rebuilder.rebuild(
        aid, _FakeFetcher(frame, {"s": T2}), DefaultAcceptancePredicates()
    )
    assert second.outcome is RebuildOutcome.SWAPPED
    served_bytes, proof_2 = await store.read_current(aid)
    assert proof_2.built_from_live_at == T2  # advanced T1 -> T2 for the SAME bytes
    assert served_bytes == canonical_frame_bytes(frame)
    assert second.version_id == first.version_id  # SAME version — no new object


async def test_bytestable_older_proof_declined(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """C12: a same-version rebuild with an OLDER instant is declined (never regresses)."""
    frame = _offer_frame()
    rebuilder = _rebuilder(store)
    await rebuilder.rebuild(aid, _FakeFetcher(frame, {"s": T2}), DefaultAcceptancePredicates())

    result = await rebuilder.rebuild(
        aid, _FakeFetcher(frame, {"s": T0}), DefaultAcceptancePredicates()
    )
    assert result.outcome is RebuildOutcome.STAGED_REJECTED
    _, proof = await store.read_current(aid)
    assert proof.built_from_live_at == T2  # unchanged


async def test_publish_refuses_incoherent_proof_graft(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """N1 graft (two-sided): a proof describing DIFFERENT content than the staged frame is loud."""
    frame = _offer_frame()
    frame_bytes = canonical_frame_bytes(frame)
    version_id = await store.stage_version(aid, frame_bytes)

    # graft: content_digest describes other content; receipt binds the graft, but the
    # S4 coherence guard (canonical_digest of the frame) refuses it loud.
    graft = StagedVersion(
        version_id=version_id,
        frame=frame,
        frame_bytes=frame_bytes,
        proof=FreshnessProof(built_from_live_at=T2, content_digest="f" * 64, sla_seconds=3600),
    )
    graft_receipt = ValidationReceipt(
        version_id=version_id, content_digest="f" * 64, built_from_live_at=T2
    )
    with pytest.raises(ProofDigestMismatch):
        await _rebuilder(store)._publish(aid, graft, graft_receipt)  # noqa: SLF001

    # complement: a COHERENT proof publishes fine.
    digest = canonical_digest(frame)
    good = StagedVersion(
        version_id=version_id,
        frame=frame,
        frame_bytes=frame_bytes,
        proof=FreshnessProof(built_from_live_at=T2, content_digest=digest, sla_seconds=3600),
    )
    good_receipt = ValidationReceipt(
        version_id=version_id, content_digest=digest, built_from_live_at=T2
    )
    result = await _rebuilder(store)._publish(aid, good, good_receipt)  # noqa: SLF001
    assert result.outcome is RebuildOutcome.SWAPPED


# ================================================= RC-E side-effect-free :76 ===
async def test_midfetch_abort_leaves_store_byte_identical(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """DEFECT :76 killed: a fetch that raises mid-way writes ZERO bytes to any key."""
    await _seed(store, aid, _offer_frame(offers=4), T2)
    before = _snapshot(store)
    assert before

    rebuilder = _rebuilder(store)
    fetcher = _RaisingFetcher(RuntimeError("Asana 500 at section 3 of 7"))
    with pytest.raises(RuntimeError, match="section 3 of 7"):
        await rebuilder.rebuild(aid, fetcher, DefaultAcceptancePredicates())

    assert fetcher.calls == 1
    assert _snapshot(store) == before  # BYTE-IDENTICAL: no staging key, pointer untouched
    _, served_proof = await store.read_current(aid)
    assert served_proof.built_from_live_at == T2


async def test_fetch_refused_writes_nothing(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """A paced FetchRefused → FETCH_REFUSED outcome, zero store writes."""
    before = _snapshot(store)
    assert before == {}
    result = await _rebuilder(store).rebuild(
        aid, _RaisingFetcher(FetchRefused("rate backpressure")), DefaultAcceptancePredicates()
    )
    assert result.outcome is RebuildOutcome.FETCH_REFUSED
    assert _snapshot(store) == {}


# ============================================ C16 fetch-completeness ===
async def test_c16_partial_fetch_refused_incumbent_untouched(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C16 (QA F3): a partial fetch (explicitly-failed sections) → FETCH_REFUSED; incumbent stands."""
    await _seed(store, aid, _offer_frame(offers=500), T2)  # healthy 500-row incumbent
    before = _snapshot(store)

    partial = _FakeFetcher(
        _offer_frame(offers=1),  # a 1-row frame that WOULD pass validate on its own
        {"s1": T3},
        requested=frozenset({"s1", "s2", "s3"}),
        failed=frozenset({"s2", "s3"}),
    )
    result = await _rebuilder(store).rebuild(aid, partial, DefaultAcceptancePredicates())

    assert result.outcome is RebuildOutcome.FETCH_REFUSED
    assert "partial fetch (C16)" in result.detail
    assert _snapshot(store) == before  # the healthy 500-row artifact is byte-identical
    _, served_proof = await store.read_current(aid)
    assert served_proof.built_from_live_at == T2


async def test_c16_silent_gap_refused(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """C16: a SILENT gap (requested section neither fetched nor failed) → FETCH_REFUSED."""
    gappy = _FakeFetcher(
        _offer_frame(offers=1),
        {"s1": T3},
        requested=frozenset({"s1", "s2", "s3"}),  # s2, s3 silently dropped
    )
    result = await _rebuilder(store).rebuild(aid, gappy, DefaultAcceptancePredicates())
    assert result.outcome is RebuildOutcome.FETCH_REFUSED
    assert "incomplete fetch accounting" in result.detail
    with pytest.raises(ArtifactMissing):
        await store.read_current(aid)


async def test_c16_complete_fetch_swaps(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """C16 (other side): a COMPLETE fetch (every requested section fetched) SWAPS."""
    complete = _FakeFetcher(_offer_frame(), {"s1": T2, "s2": T3}, requested=frozenset({"s1", "s2"}))
    result = await _rebuilder(store).rebuild(aid, complete, DefaultAcceptancePredicates())
    assert result.outcome is RebuildOutcome.SWAPPED
    _, proof = await store.read_current(aid)
    assert proof.built_from_live_at == T2  # MIN-fold over the COMPLETE set


# ===================================================================== C1 ===
async def test_reused_section_keeps_instant_min_fold(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C1: a reused section keeps its OLD instant; the artifact ages to it (MIN-fold)."""
    frame = _offer_frame()
    result = await _rebuilder(store).rebuild(
        aid,
        _FakeFetcher(frame, {"section-a": T0, "section-b": T3}),
        DefaultAcceptancePredicates(),
    )
    _, proof = await store.read_current(aid)
    assert proof.built_from_live_at == T0  # MIN-fold drags to the stalest (reused) section
    assert result.built_from_live_at == T0
    assert proof.built_from_live_at == fold_built_from_live_at({"section-a": T0, "section-b": T3})


async def test_all_refetched_advances_to_min_of_fresh(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C1 (other side): when every section is freshly fetched, the artifact is fresh."""
    frame = _offer_frame()
    await _rebuilder(store).rebuild(
        aid, _FakeFetcher(frame, {"section-a": T2, "section-b": T3}), DefaultAcceptancePredicates()
    )
    _, proof = await store.read_current(aid)
    assert proof.built_from_live_at == T2


# ============================================= [H9] capability separation ===
def test_rebuilder_has_no_serve_read_capability() -> None:
    """[H9]: the Rebuilder exposes rebuild only — no serve-read, no store mutation re-surfaced."""
    for forbidden in ("read", "read_current", "stage_version", "swap_pointer", "put"):
        assert not hasattr(SubstrateRebuilder, forbidden), f"capability leak: {forbidden}"
    public = {name for name in vars(SubstrateRebuilder) if not name.startswith("_")}
    assert public == {"rebuild"}


def test_substrate_reader_has_no_write_capability() -> None:
    """[H9] (other side): the serve reader exposes read only — no write method."""
    from autom8_asana.substrate.serve import SubstrateReader

    for forbidden in ("stage_version", "swap_pointer", "put", "rebuild"):
        assert not hasattr(SubstrateReader, forbidden), f"reader write leak: {forbidden}"


def test_substrate_rebuilder_satisfies_rebuilder_protocol(store: S3ArtifactStore) -> None:
    """The concrete class structurally conforms to the frozen ``Rebuilder`` Protocol."""
    conforming: Rebuilder = _rebuilder(store)
    assert hasattr(conforming, "rebuild")


# ================================================ RC-E-4 structural import ===
def test_rebuild_module_binds_no_asana_client() -> None:
    """RC-E-4 (runtime): ``substrate.rebuild`` binds no ``AsanaClient`` name."""
    assert not hasattr(rebuild_module, "AsanaClient")


def test_rebuild_source_imports_no_asana_client() -> None:
    """RC-E-4 (structural): no import of AsanaClient / un-paced Asana surface in the source."""
    source = Path(rebuild_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "AsanaClient" or (node.module and "asana_client" in node.module):
                    offenders.append(f"from {node.module} import {alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "AsanaClient" in alias.name:
                    offenders.append(f"import {alias.name}")
    assert offenders == [], f"un-paced Asana import(s) in substrate.rebuild: {offenders}"


# ============================================ validate() three checks ([H13]) ===
def _staged(
    frame: pl.DataFrame, *, digest: str | None = None, at: datetime = T1, sla: int = 3600
) -> StagedVersion:
    content_digest = digest if digest is not None else canonical_digest(frame)
    frame_bytes = canonical_frame_bytes(frame)
    return StagedVersion(
        version_id=VersionId("v" + content_digest[:8]),
        frame=frame,
        frame_bytes=frame_bytes,
        proof=FreshnessProof(built_from_live_at=at, content_digest=content_digest, sla_seconds=sla),
    )


def test_validate_population_floor_two_sided() -> None:
    """[H13] population-floor: empty/null-value rejects; a populated frame passes."""
    predicates = DefaultAcceptancePredicates()
    assert isinstance(predicates.validate(_staged(_empty_offer_frame()), NOW), ValidationFailure)

    null_frame = pl.DataFrame(
        {"offer_id": ["o1"], "cost": [None], "mrr": [500], "weekly_ad_spend": [10]},
        schema={
            "offer_id": pl.String,
            "cost": pl.Int64,
            "mrr": pl.Int64,
            "weekly_ad_spend": pl.Int64,
        },
    )
    null_result = predicates.validate(_staged(null_frame), NOW)
    assert isinstance(null_result, ValidationFailure)
    assert null_result.check == "population-floor"

    assert isinstance(predicates.validate(_staged(_offer_frame()), NOW), ValidationReceipt)


def test_validate_digest_self_consistency_two_sided() -> None:
    """[H13] digest-self-consistency: a proof digest not re-derivable from the bytes rejects."""
    predicates = DefaultAcceptancePredicates()
    frame = _offer_frame()
    bad = predicates.validate(_staged(frame, digest="f" * 64), NOW)
    assert isinstance(bad, ValidationFailure)
    assert bad.check == "digest-self-consistency"

    good = predicates.validate(_staged(frame), NOW)
    assert isinstance(good, ValidationReceipt)
    assert good.content_digest == canonical_digest(frame)
    assert good.built_from_live_at == T1  # F2: the receipt binds the full proof


def test_validate_proof_well_formedness_two_sided() -> None:
    """[H13] proof-well-formedness: future instant / non-positive sla reject; sane passes."""
    predicates = DefaultAcceptancePredicates()
    frame = _offer_frame()

    future = predicates.validate(_staged(frame, at=NOW + timedelta(hours=1)), NOW)
    assert isinstance(future, ValidationFailure)
    assert future.check == "proof-well-formedness"

    bad_sla = predicates.validate(_staged(frame, sla=0), NOW)
    assert isinstance(bad_sla, ValidationFailure)

    assert isinstance(predicates.validate(_staged(frame, at=T1, sla=3600), NOW), ValidationReceipt)


def test_min_rows_construction_guard() -> None:
    """C16 / QA F3: a min_rows < 1 misconfig is refused at construction (not a shrink threshold)."""
    with pytest.raises(ValueError, match="min_rows must be >= 1"):
        DefaultAcceptancePredicates(min_rows=0)
    with pytest.raises(ValueError, match="min_rows must be >= 1"):
        DefaultAcceptancePredicates(min_rows=-3)
    assert DefaultAcceptancePredicates(min_rows=1).min_rows == 1


# ============================================== [H12] single-flight coalescing ===
class _GatedFetcher:
    """A fetch that parks in-flight until released — so two callers overlap."""

    def __init__(self, frame: pl.DataFrame, instants: Mapping[str, datetime]) -> None:
        self._frame = frame
        self._instants = dict(instants)
        self.calls = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def fetch(self, aid: ArtifactId) -> FetchedSections:
        self.calls += 1
        self.entered.set()
        await self.release.wait()
        return FetchedSections(
            frame=self._frame,
            section_instants=self._instants,
            requested_sections=frozenset(self._instants),
        )


async def test_single_flight_coalesces_concurrent_rebuilds(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """[H12]: two concurrent rebuilds of one ArtifactId collapse to ONE fetch/build."""
    fetcher = _GatedFetcher(_offer_frame(), {"s": T1})
    rebuilder = _rebuilder(store, single_flight=LocalSingleFlight())

    first = asyncio.ensure_future(rebuilder.rebuild(aid, fetcher, DefaultAcceptancePredicates()))
    await fetcher.entered.wait()
    second = asyncio.ensure_future(rebuilder.rebuild(aid, fetcher, DefaultAcceptancePredicates()))
    for _ in range(5):
        await asyncio.sleep(0)
    fetcher.release.set()

    res1, res2 = await asyncio.gather(first, second)
    assert fetcher.calls == 1
    assert res1.outcome is res2.outcome is RebuildOutcome.SWAPPED
    assert res1.version_id == res2.version_id


# ========================================================= CAP-4 telemetry ===
async def test_fetch_telemetry_threads_to_result(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """CAP-4 (P10 receipt): FetchTelemetry rides FetchedSections → RebuildResult on every path."""
    tele = FetchTelemetry(
        requests_issued=7,
        http_429_count=2,
        retries_issued=3,
        sections_refetched=2,
        sections_reused=1,
    )
    swapped = await _rebuilder(store).rebuild(
        aid, _FakeFetcher(_offer_frame(), {"s": T2}, telemetry=tele), DefaultAcceptancePredicates()
    )
    assert swapped.outcome is RebuildOutcome.SWAPPED
    assert swapped.telemetry == tele

    rejected = await _rebuilder(store).rebuild(
        aid,
        _FakeFetcher(_empty_offer_frame(), {"s": T2}, telemetry=tele),
        DefaultAcceptancePredicates(),
    )
    assert rejected.outcome is RebuildOutcome.STAGED_REJECTED
    assert rejected.telemetry == tele  # receipt survives a rejection


# ============================================ deterministic serializer (S8 carry) ===
def test_canonical_frame_bytes_is_row_and_column_order_independent() -> None:
    """version_id stability: identical logical content mints identical bytes (C3/C15 premise)."""
    a = pl.DataFrame(
        {"offer_id": ["o1", "o2"], "cost": [1, 2], "mrr": [5, 6], "weekly_ad_spend": [3, 4]}
    )
    b = pl.DataFrame(
        {"weekly_ad_spend": [4, 3], "mrr": [6, 5], "cost": [2, 1], "offer_id": ["o2", "o1"]}
    )
    assert canonical_frame_bytes(a) == canonical_frame_bytes(b)

    c = pl.DataFrame(
        {"offer_id": ["o1", "o3"], "cost": [1, 9], "mrr": [5, 6], "weekly_ad_spend": [3, 4]}
    )
    assert canonical_frame_bytes(a) != canonical_frame_bytes(c)
