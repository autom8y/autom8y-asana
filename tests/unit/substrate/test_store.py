"""S3ArtifactStore — CAS, immutability, and fail-loud absence (Seam 2, RC-A/RC-E).

Two-sided receipts against the house S3 double (moto ``mock_aws``): the CAS race
has exactly one winner and one 412 loser; a partial stage never corrupts the
pointed-to artifact; a pointed-to version's frame is immutable; ``read_current``
on an empty store raises ``ArtifactMissing`` (never ``(None, None)``). The store
is policy-free — these tests never call ``is_provable`` (S2).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

from autom8_asana.core.types import EntityType
from autom8_asana.substrate import ArtifactId, FreshnessProof
from autom8_asana.substrate.store import (
    CREATE_IF_ABSENT,
    ArtifactMissing,
    ArtifactStore,
    CASLost,
    ConcurrentPointerDelete,
    ETag,
    PointerAbsent,
    PointerCorrupt,
    S3ArtifactStore,
    StaleProofRefused,
)

try:
    import boto3
    from botocore.exceptions import ClientError
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:  # pragma: no cover - moto is a dev dep; guard mirrors the house pattern
    MOTO_AVAILABLE = False

pytestmark = pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")

_BUCKET = "substrate-v2-test"


def _proof(digest: str = "a" * 64, sla: int = 3600, minutes_ago: int = 0) -> FreshnessProof:
    return FreshnessProof(
        built_from_live_at=datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
        - timedelta(minutes=minutes_ago),
        content_digest=digest,
        sla_seconds=sla,
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


# --------------------------------------------------------------- lifecycle ---
async def test_stage_swap_read_roundtrip(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """stage -> create-swap -> read_current returns the exact bytes + proof."""
    frame = b"offer-frame-parquet-bytes"
    proof = _proof(digest="c" * 64, sla=7200)

    version_id = await store.stage_version(aid, frame, proof)
    await store.swap_pointer(aid, version_id, if_match=CREATE_IF_ABSENT)

    got_bytes, got_proof = await store.read_current(aid)
    assert got_bytes == frame
    assert got_proof.content_digest == "c" * 64
    assert got_proof.sla_seconds == 7200
    assert got_proof.built_from_live_at == proof.built_from_live_at
    assert got_proof.built_from_live_at.tzinfo is not None  # tz survives the round-trip


async def test_version_id_is_content_digest(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """VersionId is the sha256 of the frame bytes (collision-free C3, idempotent)."""
    import hashlib

    frame = b"deterministic-content"
    version_id = await store.stage_version(aid, frame, _proof())
    assert version_id == hashlib.sha256(frame).hexdigest()


async def test_key_layout_entity_after_project(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """Ratified DP-2 layout: dataframes-v2/{project}/{entity}/... entity-after-project."""
    frame = b"x"
    version_id = await store.stage_version(aid, frame, _proof())
    await store.swap_pointer(aid, version_id, if_match=CREATE_IF_ABSENT)

    keys = {obj["Key"] for obj in store._s3().list_objects_v2(Bucket=_BUCKET)["Contents"]}
    assert f"dataframes-v2/1200000000000042/offer/versions/{version_id}/frame" in keys
    assert "dataframes-v2/1200000000000042/offer/current.json" in keys


# ------------------------------------------------------------- [H5] absence ---
async def test_read_current_empty_raises_artifact_missing(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """[H5]: an absent pointer is LOUD — ArtifactMissing, never (None, None)."""
    with pytest.raises(ArtifactMissing):
        await store.read_current(aid)


async def test_read_current_dangling_pointer_raises(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """A pointer naming a reaped version is loud (ArtifactMissing), not silent."""
    frame = b"soon-reaped"
    version_id = await store.stage_version(aid, frame, _proof())
    await store.swap_pointer(aid, version_id, if_match=CREATE_IF_ABSENT)
    # simulate a reap of the pointed-to frame out from under the pointer
    store._s3().delete_object(
        Bucket=_BUCKET, Key=f"dataframes-v2/1200000000000042/offer/versions/{version_id}/frame"
    )
    with pytest.raises(ArtifactMissing):
        await store.read_current(aid)


async def test_read_pointer_absent_returns_none(store: S3ArtifactStore, aid: ArtifactId) -> None:
    assert await store.read_pointer(aid) is None


# ---------------------------------------------------------- CAS race (two-sided) ---
async def test_concurrent_swap_exactly_one_wins(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """Two swappers race the SAME ETag: exactly one wins, the loser gets CASLost (412).

    The winning side is the two-sided complement — one swap succeeds, one raises;
    never both, never neither.
    """
    # establish a pointer at version A
    frame_a = b"frame-A"
    vid_a = await store.stage_version(aid, frame_a, _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid_a, if_match=CREATE_IF_ABSENT)

    state = await store.read_pointer(aid)
    assert state is not None
    contested_etag = state.etag

    # two rebuilders stage distinct next-versions and race the same (now-live) ETag
    vid_b = await store.stage_version(aid, b"frame-B", _proof(digest="b" * 64))
    vid_c = await store.stage_version(aid, b"frame-C", _proof(digest="d" * 64))

    results = await asyncio.gather(
        store.swap_pointer(aid, vid_b, if_match=contested_etag),
        store.swap_pointer(aid, vid_c, if_match=contested_etag),
        return_exceptions=True,
    )
    winners = [r for r in results if r is None]
    losers = [r for r in results if isinstance(r, CASLost)]
    assert len(winners) == 1, f"expected exactly one winner, got {results!r}"
    assert len(losers) == 1, f"expected exactly one CASLost loser, got {results!r}"

    # the ratified remediation path: the loser re-reads and retries against the fresh ETag
    fresh = await store.read_pointer(aid)
    assert fresh is not None
    assert fresh.version_id in {vid_b, vid_c}  # the winner is live
    loser_vid = vid_c if fresh.version_id == vid_b else vid_b
    await store.swap_pointer(aid, loser_vid, if_match=fresh.etag)  # retry-succeeds
    reread = await store.read_pointer(aid)
    assert reread is not None
    assert reread.version_id == loser_vid


async def test_stale_etag_swap_raises_cas_lost(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """A swap with an ETag that another swap already superseded raises CASLost."""
    vid_a = await store.stage_version(aid, b"A", _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid_a, if_match=CREATE_IF_ABSENT)
    stale = await store.read_pointer(aid)
    assert stale is not None

    vid_b = await store.stage_version(aid, b"B", _proof(digest="b" * 64))
    await store.swap_pointer(aid, vid_b, if_match=stale.etag)  # advances the pointer

    vid_c = await store.stage_version(aid, b"C", _proof(digest="d" * 64))
    with pytest.raises(CASLost):
        await store.swap_pointer(aid, vid_c, if_match=stale.etag)  # stale now


async def test_create_if_absent_loses_to_existing_pointer(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """A second CREATE_IF_ABSENT (If-None-Match:*) on an existing pointer is CASLost."""
    vid_a = await store.stage_version(aid, b"A", _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid_a, if_match=CREATE_IF_ABSENT)
    vid_b = await store.stage_version(aid, b"B", _proof(digest="b" * 64))
    with pytest.raises(CASLost):
        await store.swap_pointer(aid, vid_b, if_match=CREATE_IF_ABSENT)


async def test_swap_absent_pointer_if_match_raises_pointer_absent(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """404: an If-Match swap whose pointer was concurrently reaped raises PointerAbsent."""
    vid_a = await store.stage_version(aid, b"A", _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid_a, if_match=CREATE_IF_ABSENT)
    state = await store.read_pointer(aid)
    assert state is not None
    store._s3().delete_object(
        Bucket=_BUCKET, Key="dataframes-v2/1200000000000042/offer/current.json"
    )
    vid_b = await store.stage_version(aid, b"B", _proof(digest="b" * 64))
    with pytest.raises(PointerAbsent):
        await store.swap_pointer(aid, vid_b, if_match=state.etag)


async def test_swap_409_maps_to_concurrent_delete(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """409 Conflict on the conditional write maps to ConcurrentPointerDelete.

    moto does not synthesize the concurrent-delete race, so inject a 409 at the
    put_object boundary to prove the DP-2 build-note code path resolves. head_object
    (proof read) stays real, so the failure is isolated to the pointer PUT.
    """
    from unittest.mock import patch

    vid_a = await store.stage_version(aid, b"A", _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid_a, if_match=CREATE_IF_ABSENT)
    state = await store.read_pointer(aid)
    assert state is not None
    vid_b = await store.stage_version(aid, b"B", _proof(digest="b" * 64))

    conflict_response: Any = {
        "Error": {"Code": "Conflict"},
        "ResponseMetadata": {"HTTPStatusCode": 409},
    }
    conflict = ClientError(conflict_response, "PutObject")
    with patch.object(store._s3(), "put_object", side_effect=conflict):
        with pytest.raises(ConcurrentPointerDelete):
            await store.swap_pointer(aid, vid_b, if_match=state.etag)


# -------------------------------------------------------------- immutability ---
async def test_restage_identical_content_is_idempotent(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """Re-staging identical bytes returns the same VersionId and never rewrites the frame."""
    frame = b"immutable-content"
    vid1 = await store.stage_version(aid, frame, _proof(digest="a" * 64))
    etag1 = store._s3().head_object(
        Bucket=_BUCKET, Key=f"dataframes-v2/1200000000000042/offer/versions/{vid1}/frame"
    )["ETag"]

    vid2 = await store.stage_version(aid, frame, _proof(digest="b" * 64, minutes_ago=5))
    etag2 = store._s3().head_object(
        Bucket=_BUCKET, Key=f"dataframes-v2/1200000000000042/offer/versions/{vid2}/frame"
    )["ETag"]

    assert vid1 == vid2  # content-addressed
    assert etag1 == etag2  # the object was NOT rewritten (write-once, immutable)


async def test_different_content_cannot_target_a_pointed_version(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """A pointed-to version is immutable: different bytes necessarily land a different key.

    Overwriting the served frame in place is impossible by construction — the key
    is a pure function of content, so distinct content can never address the same
    version object.
    """
    frame_a = b"served-content"
    vid_a = await store.stage_version(aid, frame_a, _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid_a, if_match=CREATE_IF_ABSENT)

    vid_b = await store.stage_version(aid, b"different-content", _proof(digest="b" * 64))
    assert vid_a != vid_b  # cannot collide onto the pointed-to key

    # the served frame is byte-for-byte the original
    got_bytes, _ = await store.read_current(aid)
    assert got_bytes == frame_a


async def test_partial_stage_does_not_corrupt_pointed_artifact(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """RC-E: staging a new version (no swap) leaves the live artifact untouched."""
    frame_a = b"live-A"
    proof_a = _proof(digest="a" * 64)
    vid_a = await store.stage_version(aid, frame_a, proof_a)
    await store.swap_pointer(aid, vid_a, if_match=CREATE_IF_ABSENT)

    # stage B — a "partial build" that never reaches swap
    await store.stage_version(aid, b"staged-but-abandoned-B", _proof(digest="b" * 64))

    got_bytes, got_proof = await store.read_current(aid)
    assert got_bytes == frame_a  # live pointer never moved
    assert got_proof.content_digest == "a" * 64
    assert len(await store.list_versions(aid)) == 2  # both versions exist; only A served


async def test_swap_to_unstaged_version_raises(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """swap_pointer to a version that was never staged is a loud ordering error."""
    from autom8_asana.substrate.store import VersionId

    with pytest.raises(ValueError, match="unstaged version"):
        await store.swap_pointer(aid, VersionId("f" * 64), if_match=CREATE_IF_ABSENT)


# ----------------------------------------------------------- enumerate / gc ---
async def test_list_versions_enumerates_staged(store: S3ArtifactStore, aid: ArtifactId) -> None:
    vid_a = await store.stage_version(aid, b"A", _proof(digest="a" * 64))
    vid_b = await store.stage_version(aid, b"B", _proof(digest="b" * 64))
    assert set(await store.list_versions(aid)) == {vid_a, vid_b}


async def test_pointer_carries_proof_atomically(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """DP-2 Option C: current.json carries {version_id, proof} in ONE object."""
    vid = await store.stage_version(aid, b"A", _proof(digest="e" * 64, sla=1800))
    await store.swap_pointer(aid, vid, if_match=CREATE_IF_ABSENT)
    body = (
        store._s3()
        .get_object(Bucket=_BUCKET, Key="dataframes-v2/1200000000000042/offer/current.json")["Body"]
        .read()
    )
    pointer = json.loads(body)
    assert pointer["version_id"] == vid
    assert pointer["proof"]["content_digest"] == "e" * 64
    assert pointer["proof"]["sla_seconds"] == 1800


async def test_gc_never_reaps_current_or_current_minus_one(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """gc reaps old non-protected versions but never current or current-1."""
    vid_a = await store.stage_version(aid, b"A", _proof(digest="a" * 64))
    vid_b = await store.stage_version(aid, b"B", _proof(digest="b" * 64))
    vid_c = await store.stage_version(aid, b"C", _proof(digest="d" * 64))
    await store.swap_pointer(aid, vid_c, if_match=CREATE_IF_ABSENT)  # current = C

    # keep_after in the future so every frame is "old" and eligible by age
    reaped = await store.gc_versions(aid, keep_after=datetime.now(tz=UTC) + timedelta(days=1))

    survivors = set(await store.list_versions(aid))
    assert vid_c in survivors  # current — protected
    assert len(survivors) == 2  # current + current-1 kept; the third reaped
    assert reaped == 1


async def test_gc_keeps_recent_versions(store: S3ArtifactStore, aid: ArtifactId) -> None:
    """A version newer than keep_after is retained regardless of protection."""
    vid_a = await store.stage_version(aid, b"A", _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid_a, if_match=CREATE_IF_ABSENT)
    reaped = await store.gc_versions(aid, keep_after=datetime(2000, 1, 1, tzinfo=UTC))
    assert reaped == 0
    assert set(await store.list_versions(aid)) == {vid_a}


# ---------------------------------------------------------- protocol shape ---
def test_s3_store_satisfies_frozen_protocol() -> None:
    """The concrete store structurally satisfies the frozen ArtifactStore Protocol."""
    accepted: ArtifactStore = S3ArtifactStore(_BUCKET)
    assert accepted is not None


# ------------------------------------------------- F2: blank if_match guard ---
async def test_blank_if_match_refused_before_clobber(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """F2: a blank/whitespace if_match is refused LOUD before any S3 call.

    Emitting ``IfMatch=""`` degrades to an unconditional overwrite (the clobber CAS
    forbids). Two-sided: the live pointer never moves when the guard fires; a real
    ETag swaps fine (the complement, proven throughout the CAS suite).
    """
    vid_a = await store.stage_version(aid, b"A", _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid_a, if_match=CREATE_IF_ABSENT)
    vid_b = await store.stage_version(aid, b"B", _proof(digest="b" * 64))
    for blank in (ETag(""), ETag("   "), ETag("\t")):
        with pytest.raises(ValueError, match="blank/whitespace if_match"):
            await store.swap_pointer(aid, vid_b, if_match=blank)
    # the pointer NEVER moved — the unconditional clobber was prevented
    got_bytes, _ = await store.read_current(aid)
    assert got_bytes == b"A"


# ---------------------------------------------------- F4: list/gc pagination ---
async def test_list_versions_paginates_beyond_one_page(aid: ArtifactId) -> None:
    """F4: >1 page of versions are ALL enumerated (continuation-token loop)."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        paged = S3ArtifactStore(_BUCKET, client=client, page_size=1)  # 1 key/page → forces loop
        vids = {
            await paged.stage_version(aid, f"frame-{i}".encode(), _proof(digest=str(i) * 64))
            for i in range(5)
        }
        listed = set(await paged.list_versions(aid))
        assert listed == vids
        assert len(listed) == 5  # nothing lost past page 1


async def test_gc_paginates_beyond_one_page(aid: ArtifactId) -> None:
    """F4: gc reaps the tail beyond page 1 (paginated enumeration, not a 1000-cap head)."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        paged = S3ArtifactStore(_BUCKET, client=client, page_size=1)
        vids = [
            await paged.stage_version(aid, f"f{i}".encode(), _proof(digest=str(i) * 64))
            for i in range(5)
        ]
        await paged.swap_pointer(aid, vids[-1], if_match=CREATE_IF_ABSENT)  # current = last
        reaped = await paged.gc_versions(aid, keep_after=datetime.now(tz=UTC) + timedelta(days=1))
        assert reaped == 3  # 5 staged − (current + current-1) = 3 reaped across pages
        assert len(await paged.list_versions(aid)) == 2


# ------------------------------------------------ F5: corrupt-pointer taxonomy ---
async def test_corrupt_pointer_raises_pointer_corrupt(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """F5: an unparseable current.json raises PointerCorrupt, not a bare JSONDecodeError."""
    vid = await store.stage_version(aid, b"A", _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid, if_match=CREATE_IF_ABSENT)
    store._s3().put_object(
        Bucket=_BUCKET,
        Key="dataframes-v2/1200000000000042/offer/current.json",
        Body=b"not json{",
    )
    with pytest.raises(PointerCorrupt):
        await store.read_current(aid)
    with pytest.raises(PointerCorrupt):
        await store.read_pointer(aid)


async def test_schema_incomplete_pointer_raises_pointer_corrupt(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """F5: valid JSON missing the required 'proof' key → PointerCorrupt (two-sided vs roundtrip)."""
    vid = await store.stage_version(aid, b"A", _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid, if_match=CREATE_IF_ABSENT)
    store._s3().put_object(
        Bucket=_BUCKET,
        Key="dataframes-v2/1200000000000042/offer/current.json",
        Body=json.dumps({"version_id": vid}).encode(),  # 'proof' absent
    )
    with pytest.raises(PointerCorrupt):
        await store.read_current(aid)


# ------------------------------------- C14 (architect F1): pointer proof-refresh ---
async def test_refresh_pointer_proof_advances_byte_stable_freshness(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C14/F1: byte-stable content advances served freshness via pointer-only refresh — no new version."""
    frame = b"byte-stable-content"
    vid = await store.stage_version(aid, frame, _proof(digest="c" * 64, minutes_ago=120))
    await store.swap_pointer(aid, vid, if_match=CREATE_IF_ABSENT)

    state = await store.read_pointer(aid)
    assert state is not None
    fresher = _proof(digest="c" * 64, minutes_ago=0)  # same content, later instant
    await store.refresh_pointer_proof(aid, fresher, if_match=state.etag)

    got_bytes, got_proof = await store.read_current(aid)
    assert got_bytes == frame  # same bytes served
    assert got_proof.built_from_live_at == fresher.built_from_live_at  # freshness advanced
    assert set(await store.list_versions(aid)) == {vid}  # NO new version minted


async def test_refresh_pointer_proof_rejects_strictly_backward(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C14: a strictly-earlier built_from_live_at is refused loud (StaleProofRefused)."""
    vid = await store.stage_version(aid, b"x", _proof(digest="a" * 64, minutes_ago=0))
    await store.swap_pointer(aid, vid, if_match=CREATE_IF_ABSENT)
    state = await store.read_pointer(aid)
    assert state is not None
    with pytest.raises(StaleProofRefused):
        await store.refresh_pointer_proof(
            aid, _proof(digest="a" * 64, minutes_ago=60), if_match=state.etag
        )


async def test_refresh_pointer_proof_allows_equal_instant(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C14: non-decreasing means an EQUAL instant republishes (not rejected)."""
    same = _proof(digest="a" * 64, minutes_ago=0)
    vid = await store.stage_version(aid, b"x", same)
    await store.swap_pointer(aid, vid, if_match=CREATE_IF_ABSENT)
    state = await store.read_pointer(aid)
    assert state is not None
    await store.refresh_pointer_proof(aid, same, if_match=state.etag)  # equal → allowed
    _, got = await store.read_current(aid)
    assert got.built_from_live_at == same.built_from_live_at


async def test_refresh_pointer_proof_cas_lost_on_stale_etag(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C14: a losing CAS on refresh raises CASLost (the 412 tooth bites here too)."""
    vid = await store.stage_version(aid, b"x", _proof(digest="a" * 64, minutes_ago=120))
    await store.swap_pointer(aid, vid, if_match=CREATE_IF_ABSENT)
    stale = await store.read_pointer(aid)
    assert stale is not None
    # first refresh consumes the etag (11:00 >= 10:00, CAS ok)
    await store.refresh_pointer_proof(
        aid, _proof(digest="a" * 64, minutes_ago=60), if_match=stale.etag
    )
    # second refresh with the now-stale etag → CASLost (12:00 >= 11:00, so not stale-rejected first)
    with pytest.raises(CASLost):
        await store.refresh_pointer_proof(
            aid, _proof(digest="a" * 64, minutes_ago=0), if_match=stale.etag
        )


async def test_refresh_pointer_proof_leaves_version_object_untouched(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C14: the immutable version object's bytes + metadata are byte-identical after a refresh."""
    frame = b"immutable-body"
    vid = await store.stage_version(aid, frame, _proof(digest="a" * 64, minutes_ago=120))
    await store.swap_pointer(aid, vid, if_match=CREATE_IF_ABSENT)
    frame_key = f"dataframes-v2/1200000000000042/offer/versions/{vid}/frame"
    before = store._s3().head_object(Bucket=_BUCKET, Key=frame_key)

    state = await store.read_pointer(aid)
    assert state is not None
    await store.refresh_pointer_proof(
        aid, _proof(digest="a" * 64, minutes_ago=0), if_match=state.etag
    )

    after = store._s3().head_object(Bucket=_BUCKET, Key=frame_key)
    assert before["ETag"] == after["ETag"]  # frame bytes untouched
    assert before["Metadata"] == after["Metadata"]  # frozen proof metadata untouched


async def test_refresh_pointer_proof_blank_if_match_refused(
    store: S3ArtifactStore, aid: ArtifactId
) -> None:
    """C14 inherits the F2 blank-if_match guard."""
    vid = await store.stage_version(aid, b"x", _proof(digest="a" * 64))
    await store.swap_pointer(aid, vid, if_match=CREATE_IF_ABSENT)
    with pytest.raises(ValueError, match="blank/whitespace if_match"):
        await store.refresh_pointer_proof(aid, _proof(digest="a" * 64), if_match=ETag(""))
