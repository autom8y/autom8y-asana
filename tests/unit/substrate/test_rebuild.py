"""SubstrateRebuilder — stage-validate-swap (Seam 3, RC-E). Two-sided receipts.

Composes the REAL S2 freshness + S3 store against the house S3 double (moto
``mock_aws``); the live Asana leg is a FAKE ``PacedAsanaFetcher`` (dark build,
prod_touch NONE). Every obligation is proven two-sided:

* **C9** — validate gates the swap: a rejected version is NOT published (GREEN),
  and a deliberately-miswired swap-before-validate variant publishes it (RED-caught
  — the guard has teeth).
* **C12** — a staged build strictly older than current is DISCARDED not swapped;
  a CAS loss re-reads and re-applies the monotonicity check (a staler build declines
  on retry); a forward build SWAPS.
* **C14** — byte-stable content refreshes the proof FORWARD for the same version
  (the F1 stale-forever cure); an older proof declines; a concurrent
  ``StaleProofRefused`` is accepted-done; a same-version ``ProofDigestMismatch`` is
  loud.
* **RC-E (DEFECT-seam1 :76)** — a rebuild aborted mid-fetch leaves the store
  BYTE-IDENTICAL (zero writes to any key).
* **C1** — reused sections keep their instant through the MIN-fold; only a content
  fetch advances one.
* **[H9]/RC-E-4** — the rebuilder has no serve-read; ``substrate.rebuild`` imports
  no ``AsanaClient``.
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
from autom8_asana.substrate.freshness import canonical_digest, fold_built_from_live_at
from autom8_asana.substrate.rebuild import (
    DefaultAcceptancePredicates,
    FetchedSections,
    FetchRefused,
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
    CASLost,
    ETag,
    PointerAbsent,
    ProofDigestMismatch,
    S3ArtifactStore,
    StaleProofRefused,
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
    """Injected paced fetcher — returns a canned materialised frame + provenance."""

    def __init__(self, frame: pl.DataFrame, instants: Mapping[str, datetime]) -> None:
        self._frame = frame
        self._instants = dict(instants)
        self.calls: list[ArtifactId] = []

    async def fetch(self, aid: ArtifactId) -> FetchedSections:
        self.calls.append(aid)
        return FetchedSections(frame=self._frame, section_instants=self._instants)


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


# ===================================================================== C9 ===
async def test_validation_failure_does_not_publish(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """A rejected staged version is STAGED_REJECTED; the pointer is never created."""
    fetcher = _FakeFetcher(_empty_offer_frame(), {"section-a": T1})
    result = await _rebuilder(store).rebuild(aid, fetcher, DefaultAcceptancePredicates())

    assert result.outcome is RebuildOutcome.STAGED_REJECTED
    assert "population-floor" in result.detail
    with pytest.raises(ArtifactMissing):
        await store.read_current(aid)  # live untouched — partial ≠ corrupt


class _SwapBeforeValidateRebuilder(SubstrateRebuilder):
    """MISWIRED variant: publishes WITHOUT validating (fabricates the C9 receipt).

    This is the deliberately-broken construction the correct rebuilder's
    validate-gates-publish ordering forbids. It exists ONLY to give the C9 test its
    teeth: the same rejected input that the correct rebuilder discards, this variant
    publishes.
    """

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
        version_id = await self._store.stage_version(aid, frame_bytes, proof)
        staged = StagedVersion(
            version_id=version_id, frame=fetched.frame, frame_bytes=frame_bytes, proof=proof
        )
        forged = ValidationReceipt(version_id=version_id, content_digest=proof.content_digest)
        return await self._publish(aid, staged, forged)  # SWAP with no validation


async def test_swap_before_validate_is_caught_discriminating(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C9 FLOOR (two-sided teeth): the guard is validate-gates-swap, and it bites.

    GREEN — the correctly-wired rebuilder never publishes a version validate rejects.
    RED-caught — the miswired swap-before-validate variant publishes the SAME rejected
    version, proving the ordering guard is the only thing preventing the corruption.
    """
    rejected_frame = _empty_offer_frame()
    predicates = DefaultAcceptancePredicates()  # rejects the empty frame (population-floor)

    # GREEN: correct construction — no publish.
    correct = _rebuilder(store)
    green = await correct.rebuild(aid, _FakeFetcher(rejected_frame, {"s": T1}), predicates)
    assert green.outcome is RebuildOutcome.STAGED_REJECTED
    with pytest.raises(ArtifactMissing):
        await store.read_current(aid)

    # RED-caught: miswired construction — publishes the version validate WOULD reject.
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
    version_id = await store.stage_version(aid, frame_bytes, proof)
    staged = StagedVersion(version_id=version_id, frame=frame, frame_bytes=frame_bytes, proof=proof)
    wrong_receipt = ValidationReceipt(version_id=VersionId("deadbeef"), content_digest="x")
    with pytest.raises(ValueError, match="refusing to publish an unvalidated version"):
        await _rebuilder(store)._publish(aid, staged, wrong_receipt)  # noqa: SLF001


# ==================================================================== C12 ===
async def _seed(store: S3ArtifactStore, aid: ArtifactId, frame: pl.DataFrame, at: datetime) -> str:
    """Publish a first version directly (bypassing the rebuilder) and return its version_id."""
    proof = FreshnessProof(
        built_from_live_at=at, content_digest=canonical_digest(frame), sla_seconds=3600
    )
    frame_bytes = canonical_frame_bytes(frame)
    version_id = await store.stage_version(aid, frame_bytes, proof)
    await store.swap_pointer(aid, version_id, if_match=rebuild_module.CREATE_IF_ABSENT)
    return str(version_id)


async def test_older_build_declined_not_swapped(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """C12: a byte-changed staged build strictly older than current is DISCARDED."""
    current_frame = _offer_frame(offers=5)
    await _seed(store, aid, current_frame, T2)  # current is fresh (T2)

    older_frame = _offer_frame(offers=2)  # different content → different version
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
    await _seed(store, aid, _offer_frame(offers=5), T1)  # current at T1
    newer_frame = _offer_frame(offers=2)
    result = await _rebuilder(store).rebuild(
        aid, _FakeFetcher(newer_frame, {"s": T3}), DefaultAcceptancePredicates()
    )

    assert result.outcome is RebuildOutcome.SWAPPED
    served_bytes, served_proof = await store.read_current(aid)
    assert served_bytes == canonical_frame_bytes(newer_frame)
    assert served_proof.built_from_live_at == T3


class _RaceOnFirstSwap(S3ArtifactStore):
    """Injects a concurrent forward swap right before this rebuild's first swap.

    Models a cross-process rebuild that lands a FRESHER version between our
    read_pointer and our swap — so our ``If-Match`` is stale and 412s (CASLost). The
    C12 contract: we must re-read and re-apply monotonicity, and (being staler) decline.
    """

    def __init__(
        self, *args: object, winner_frame: pl.DataFrame, winner_at: datetime, **kw: object
    ) -> None:
        super().__init__(*args, **kw)  # type: ignore[arg-type]
        self._winner_frame = winner_frame
        self._winner_at = winner_at
        self._fired = False

    async def swap_pointer(self, aid: ArtifactId, to: VersionId, *, if_match: ETag) -> None:
        # Only race the rebuilder's real-ETag advance-swap, not the CREATE_IF_ABSENT seed.
        if not self._fired and if_match != rebuild_module.CREATE_IF_ABSENT:
            self._fired = True
            # a fresher writer lands first, moving the pointer + its ETag
            await _seed_swap(self, aid, self._winner_frame, self._winner_at)
        await super().swap_pointer(aid, to, if_match=if_match)


async def _seed_swap(
    store: S3ArtifactStore, aid: ArtifactId, frame: pl.DataFrame, at: datetime
) -> None:
    """Advance the pointer to a fresh version via the store's real CAS (winner path)."""
    proof = FreshnessProof(
        built_from_live_at=at, content_digest=canonical_digest(frame), sla_seconds=3600
    )
    frame_bytes = canonical_frame_bytes(frame)
    version_id = await store.stage_version(aid, frame_bytes, proof)
    current = await store.read_pointer(aid)
    if current is None:
        await store.swap_pointer(aid, version_id, if_match=rebuild_module.CREATE_IF_ABSENT)
    else:
        await store.swap_pointer(aid, version_id, if_match=current.etag)


async def test_cas_loss_rereads_and_declines_staler_build(aid: ArtifactId) -> None:
    """C12: on a CAS (If-Match) failure the rebuilder re-reads and re-applies monotonicity."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        winner_frame = _offer_frame(offers=9)
        store = _RaceOnFirstSwap(_BUCKET, client=client, winner_frame=winner_frame, winner_at=T3)
        await _seed(store, aid, _offer_frame(offers=5), T1)  # start at T1

        my_frame = _offer_frame(
            offers=2
        )  # my build at T2 — fresher than start, STALER than the racing winner (T3)
        result = await _rebuilder(store).rebuild(
            aid, _FakeFetcher(my_frame, {"s": T2}), DefaultAcceptancePredicates()
        )

        assert result.outcome is RebuildOutcome.STAGED_REJECTED  # declined after re-read
        served_bytes, served_proof = await store.read_current(aid)
        assert served_bytes == canonical_frame_bytes(winner_frame)  # the T3 winner stands
        assert served_proof.built_from_live_at == T3


# ==================================================================== C14 ===
async def test_bytestable_content_refreshes_proof_forward(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C14 (F1 cure): re-verifying byte-stable content advances the served proof forward."""
    frame = _offer_frame()
    rebuilder = _rebuilder(store)

    first = await rebuilder.rebuild(
        aid, _FakeFetcher(frame, {"s": T1}), DefaultAcceptancePredicates()
    )
    assert first.outcome is RebuildOutcome.SWAPPED
    _, proof_1 = await store.read_current(aid)
    assert proof_1.built_from_live_at == T1

    # SAME bytes re-fetched at a later instant → same version_id → pointer-only proof refresh.
    second = await rebuilder.rebuild(
        aid, _FakeFetcher(frame, {"s": T2}), DefaultAcceptancePredicates()
    )
    assert second.outcome is RebuildOutcome.SWAPPED
    served_bytes, proof_2 = await store.read_current(aid)
    assert proof_2.built_from_live_at == T2  # advanced T1 -> T2 (the stale-forever trap is cured)
    assert served_bytes == canonical_frame_bytes(frame)  # identical version bytes
    assert second.version_id == first.version_id  # SAME version — no new object


async def test_bytestable_older_proof_declined(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """C14/C12: a same-version refresh with an OLDER instant is declined (never regresses)."""
    frame = _offer_frame()
    rebuilder = _rebuilder(store)
    await rebuilder.rebuild(aid, _FakeFetcher(frame, {"s": T2}), DefaultAcceptancePredicates())

    result = await rebuilder.rebuild(
        aid, _FakeFetcher(frame, {"s": T0}), DefaultAcceptancePredicates()
    )
    assert result.outcome is RebuildOutcome.STAGED_REJECTED
    assert "staged proof older" in result.detail
    _, proof = await store.read_current(aid)
    assert proof.built_from_live_at == T2  # unchanged


class _StaleProofOnRefresh(S3ArtifactStore):
    """Refresh always loses to a concurrent fresher win (StaleProofRefused)."""

    async def refresh_pointer_proof(
        self, aid: ArtifactId, proof: FreshnessProof, *, if_match: ETag
    ) -> None:
        raise StaleProofRefused("concurrent fresher win")


async def test_refresh_staleproof_is_accepted_done(aid: ArtifactId) -> None:
    """C14: a concurrent ``StaleProofRefused`` means the pointer is already fresher — accept."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        store = _StaleProofOnRefresh(_BUCKET, client=client)
        frame = _offer_frame()
        await _seed(store, aid, frame, T2)  # current at T2, same content as my rebuild

        result = await _rebuilder(store).rebuild(
            aid, _FakeFetcher(frame, {"s": T3}), DefaultAcceptancePredicates()
        )
        assert result.outcome is RebuildOutcome.SWAPPED  # accepted-done, not an error


class _DigestMismatchOnRefresh(S3ArtifactStore):
    """Refresh raises ProofDigestMismatch; read_pointer keeps reporting the SAME version."""

    async def refresh_pointer_proof(
        self, aid: ArtifactId, proof: FreshnessProof, *, if_match: ETag
    ) -> None:
        raise ProofDigestMismatch("same-version digest incoherence")


async def test_refresh_proofdigestmismatch_same_version_is_loud(aid: ArtifactId) -> None:
    """C14: a same-version ProofDigestMismatch is unconstructable from the flow → loud."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        store = _DigestMismatchOnRefresh(_BUCKET, client=client)
        frame = _offer_frame()
        await _seed(store, aid, frame, T1)  # same content → the C14 refresh branch fires

        with pytest.raises(ProofDigestMismatch):
            await _rebuilder(store).rebuild(
                aid, _FakeFetcher(frame, {"s": T2}), DefaultAcceptancePredicates()
            )


# ================================================= RC-E side-effect-free :76 ===
async def test_midfetch_abort_leaves_store_byte_identical(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """DEFECT :76 killed: a fetch that raises mid-way writes ZERO bytes to any key."""
    await _seed(store, aid, _offer_frame(offers=4), T2)  # a healthy live artifact exists
    before = _snapshot(store)
    assert before  # non-empty: pointer + version present

    rebuilder = _rebuilder(store)
    fetcher = _RaisingFetcher(RuntimeError("Asana 500 at section 3 of 7"))
    with pytest.raises(RuntimeError, match="section 3 of 7"):
        await rebuilder.rebuild(aid, fetcher, DefaultAcceptancePredicates())

    assert fetcher.calls == 1
    assert _snapshot(store) == before  # BYTE-IDENTICAL: no staging key, pointer untouched
    served_bytes, served_proof = await store.read_current(aid)
    assert served_proof.built_from_live_at == T2  # the live artifact is exactly as it was


async def test_fetch_refused_writes_nothing(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """A paced FetchRefused → FETCH_REFUSED outcome, zero store writes (empty store stays empty)."""
    before = _snapshot(store)
    assert before == {}
    result = await _rebuilder(store).rebuild(
        aid, _RaisingFetcher(FetchRefused("rate backpressure")), DefaultAcceptancePredicates()
    )
    assert result.outcome is RebuildOutcome.FETCH_REFUSED
    assert _snapshot(store) == {}  # nothing staged, no pointer


# ===================================================================== C1 ===
async def test_reused_section_keeps_instant_min_fold(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C1: a reused (not re-fetched) section keeps its OLD instant; the artifact ages to it."""
    frame = _offer_frame()
    # section-a REUSED at T0 (probe decided NOT to re-fetch); section-b re-fetched at T3.
    result = await _rebuilder(store).rebuild(
        aid, _FakeFetcher(frame, {"section-a": T0, "section-b": T3}), DefaultAcceptancePredicates()
    )
    _, proof = await store.read_current(aid)
    assert proof.built_from_live_at == T0  # MIN-fold drags to the stalest (reused) section
    assert result.built_from_live_at == T0
    # composed S2's fold — same answer, not reimplemented
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
    assert proof.built_from_live_at == T2  # MIN over the two fresh instants


# ============================================= [H9] capability separation ===
def test_rebuilder_has_no_serve_read_capability() -> None:
    """[H9]: the Rebuilder exposes rebuild only — no serve-read, no store mutation re-surfaced."""
    for forbidden in (
        "read",
        "read_current",
        "stage_version",
        "swap_pointer",
        "refresh_pointer_proof",
        "put",
    ):
        assert not hasattr(SubstrateRebuilder, forbidden), f"capability leak: {forbidden}"
    public = {name for name in vars(SubstrateRebuilder) if not name.startswith("_")}
    assert public == {"rebuild"}


def test_substrate_reader_has_no_write_capability() -> None:
    """[H9] (other side): the serve reader exposes read only — no write method."""
    from autom8_asana.substrate.serve import SubstrateReader

    for forbidden in ("stage_version", "swap_pointer", "refresh_pointer_proof", "put", "rebuild"):
        assert not hasattr(SubstrateReader, forbidden), f"reader write leak: {forbidden}"


def test_substrate_rebuilder_satisfies_rebuilder_protocol(store: S3ArtifactStore) -> None:
    """The concrete class structurally conforms to the frozen ``Rebuilder`` Protocol."""
    conforming: Rebuilder = _rebuilder(store)  # mypy-checked structural conformance
    assert hasattr(conforming, "rebuild")


# ================================================ RC-E-4 structural import ===
def test_rebuild_module_binds_no_asana_client() -> None:
    """RC-E-4 (runtime): ``substrate.rebuild`` binds no ``AsanaClient`` name."""
    assert not hasattr(rebuild_module, "AsanaClient")


def test_rebuild_source_imports_no_asana_client() -> None:
    """RC-E-4 (structural): no import of AsanaClient / un-paced Asana surface in the source.

    Parses the module AST (S7 harness pattern, hardened) — a docstring mention does
    not count, only a real import/binding. All live Asana I/O must route the injected
    ``PacedAsanaFetcher``.
    """
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
        return FetchedSections(frame=self._frame, section_instants=self._instants)


async def test_single_flight_coalesces_concurrent_rebuilds(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """[H12]: two concurrent rebuilds of one ArtifactId collapse to ONE fetch/build."""
    fetcher = _GatedFetcher(_offer_frame(), {"s": T1})
    rebuilder = _rebuilder(store, single_flight=LocalSingleFlight())

    first = asyncio.ensure_future(rebuilder.rebuild(aid, fetcher, DefaultAcceptancePredicates()))
    await fetcher.entered.wait()  # first is parked inside fetch
    second = asyncio.ensure_future(rebuilder.rebuild(aid, fetcher, DefaultAcceptancePredicates()))
    for _ in range(5):  # let `second` reach run() and coalesce onto first's task
        await asyncio.sleep(0)
    fetcher.release.set()

    res1, res2 = await asyncio.gather(first, second)
    assert fetcher.calls == 1  # coalesced — the second never re-fetched
    assert res1.outcome is res2.outcome is RebuildOutcome.SWAPPED
    assert res1.version_id == res2.version_id


# ============================================ deterministic serializer (S8 carry) ===
def test_canonical_frame_bytes_is_row_and_column_order_independent() -> None:
    """version_id stability: identical logical content mints identical bytes (C3/C14 premise)."""
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
