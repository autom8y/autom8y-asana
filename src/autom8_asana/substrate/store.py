"""Substrate-v2 Seam 2 — STORAGE (infra). RC-A / RC-E (storage half).

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 2 (storage half).
S3 lands the concrete ``S3ArtifactStore`` realizing the frozen ``ArtifactStore``
Protocol under the operator-ratified DP-2 **Option C**: versioned-immutable
artifacts + an atomic ``current.json`` pointer carrying the ``FreshnessProof`` +
version ref, swapped by a TRUE compare-and-swap (S3 ``If-Match`` ETag conditional
PUT). The store is POLICY-FREE ([H8]) — it returns bytes+proof and never applies
the SLA/refuse gate (Seam 4).

Physical layout (entity-AFTER-project — DP-2 §Ratification record)::

    {artifact_key}/current.json                 # the CAS pointer: {version_id, proof}
    {artifact_key}/versions/{version_id}/frame  # immutable frame; proof in S3 user-metadata

``version_id = sha256(frame_bytes)`` — content-digest-addressed, so version IDs
are collision-free (C3: no ``max+1`` race) AND identical rebuilds are idempotent
(the adversary's advisory). A pointed-to version's frame is immutable by
construction: the key is a pure function of content, and the stage PUT is
``If-None-Match: *`` (write-once).

**Two distinct 64-hex digests coexist (P13) — do NOT conflate.** ``version_id``
above is a physical ADDRESS digest = ``sha256(frame_bytes)`` over the STORED bytes.
It is NOT ``FreshnessProof.content_digest``, which is the parquet-INDEPENDENT
freshness digest (Seam-1 ``canonical_digest`` — "never GIDs, never parquet bytes").
The store is policy-free ([H8]) and accepts arbitrary divergence between them; a
consumer must never use the address digest as the freshness digest. Because the
address digest is over PHYSICAL bytes, C3 idempotency (identical rebuild → same
version) HOLDS ONLY IF frame serialization is byte-deterministic — that determinism
is Seam-3's ``materialize`` job, carried to the S8 gate, not the store's.

CAS state table (swap_pointer) — DP-2 build notes, SigV4 required:

    outcome         S3 signal                     code path
    ------------    --------------------------    --------------------------------
    won             200                           returns None (pointer swapped)
    CAS lost        412 Precondition Failed       raises CASLost (re-read/retry/refuse)
    pointer gone    404 (If-Match on absent key)  raises PointerAbsent (fall back to create)
    delete race     409 Conflict                  raises ConcurrentPointerDelete

Build notes (S3 owner):

* **Monotonicity is rebuild POLICY, not a store guard.** [H6] mentions a
  "monotonic (reject a swap to a version older than current, unless via an
  explicit rollback capability)" property. That cannot be expressed at the store:
  (a) content-digest-addressed VersionIds carry NO inherent ordering, and (b) the
  frozen ``swap_pointer`` signature carries no rollback discriminator, so a strict
  age-monotonic guard would forbid rollback — a ratified Option-C capability. The
  store is POLICY-FREE ([H8]); the CAS (If-Match) is the load-bearing concurrency
  invariant the adversary's C3 required (no silent clobber). "Advance vs roll
  back" is the rebuilder's decision (Seam 3), which holds the correct target +
  ETag. Surfaced to the architect as a reconciliation, not a silent drop.
* **C11 — no SUNSET_AFTER bridge.** No bounded dual-read / legacy-fallback path is
  added; RC-A/RC-D hold by subtraction. A future temptation to add one requires an
  operator-visible ruling, never a serial date-bump.
* **C14 (architect F1 ruling) — byte-stable proof-advance is S4 policy on the
  mutable pointer.** ``refresh_pointer_proof`` is its store-side write path: it
  republishes ``current.json`` (same version_id, caller-supplied fresher proof)
  under CAS, enforcing a monotonic-non-decreasing ``built_from_live_at`` floor and
  NEVER mutating the immutable version object. Additive beyond the frozen Protocol.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NewType, Protocol

from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from datetime import datetime

    from mypy_boto3_s3 import S3Client

    from autom8_asana.substrate.freshness import FreshnessProof
    from autom8_asana.substrate.identity import ArtifactId

# collision-free (content-digest-addressed — not max+1); see [H6]/C3. NewType (not
# a bare ``str`` alias) so a raw string / project_gid cannot be passed where a
# version identity is required, and VersionId cannot be confused with ETag (potnia
# grant, task item 7 — every frozen Protocol signature still typechecks).
VersionId = NewType("VersionId", str)
# S3 entity-tag carried into the If-Match conditional swap (true CAS).
ETag = NewType("ETag", str)

# Sentinel If-Match value: create the pointer ONLY if it does not yet exist
# (translated to ``If-None-Match: *``). No real S3 ETag equals this token (real
# ETags are quoted hex), so it can never be mistaken for a live CAS token.
CREATE_IF_ABSENT: ETag = ETag("__substrate_create_if_absent__")

_POINTER_KEY = "current.json"
_VERSIONS_SEGMENT = "versions"
_FRAME_OBJECT = "frame"

# S3 user-metadata keys carrying the staged proof (returned lower-cased by S3).
_MD_BUILT_AT = "built-from-live-at"
_MD_DIGEST = "content-digest"
_MD_SLA = "sla-seconds"


class ArtifactMissing(Exception):
    """Raised by ``ArtifactStore.read_current`` when no current pointer/object exists ([H5]).

    NEVER returns ``(None, None)`` — absence is loud (contrast v1's silent
    ``load_dataframe -> (None, None)``).
    """


class PointerCorrupt(Exception):
    """Raised when ``current.json`` is present but unparseable / schema-incomplete (QA F5).

    A READ-side corruption (parallel to ``ArtifactMissing``), distinct from the
    write-side ``PointerCASError`` family. Seam-4 maps it to ``Refused(CORRUPT)``
    (as ``ArtifactMissing`` maps to ``Refused(MISSING)``) instead of letting a bare
    ``JSONDecodeError`` / ``KeyError`` escape as a 500. S3 single-object writes are
    atomic, so this needs external tampering — but the read-path taxonomy is closed.
    """


class PointerCASError(Exception):
    """Base — ``swap_pointer`` could not complete the conditional pointer write.

    Ratified remediation (DP-2 build notes): re-read (``read_pointer``) → re-derive
    the swap → retry-or-refuse. A CAS failure is NEVER resolved by a blind
    overwrite; that is the concurrent-clobber the whole shape exists to forbid.
    """


class CASLost(PointerCASError):
    """412 Precondition Failed — the swap lost the race.

    Either the ``If-Match`` ETag no longer matches (another writer swapped the
    pointer) or an ``If-None-Match: *`` create found an existing pointer (another
    writer created it first). The loser must re-read and retry or refuse — it may
    NOT overwrite.
    """


class PointerAbsent(PointerCASError):
    """404 — an ``If-Match`` swap named an ETag but the pointer object is absent.

    A concurrent reap deleted the pointer, or it never existed. The caller falls
    back to ``CREATE_IF_ABSENT``.
    """


class ConcurrentPointerDelete(PointerCASError):
    """409 Conflict — S3 signalled a concurrent-delete race on the conditional write."""


class StaleProofRefused(ValueError):
    """Raised by ``refresh_pointer_proof`` when the supplied proof would move
    ``built_from_live_at`` strictly BACKWARD for the same version (C14 / architect F1).

    The F1 ruling makes byte-stable proof-advance an S4 policy on the mutable
    pointer; the store enforces the monotonic-non-decreasing floor — equal instants
    republish, strictly-earlier instants are refused loud.
    """


class ArtifactStore(Protocol):
    """Versioned immutable store + atomic CAS pointer (RC-A / RC-E). Seam 2, FROZEN v1.0.

    Single-source, policy-free ([H8]). ``stage_version`` never touches the
    pointer ([H7]); ``swap_pointer`` is the sole atomic monotonic CAS mutation
    ([H6]/C3).
    """

    async def read_current(self, aid: ArtifactId) -> tuple[bytes, FreshnessProof]:
        """[H5] resolves pointer → named immutable version in ONE logical read; raises ArtifactMissing on absence — NEVER (None, None)."""
        ...

    async def stage_version(
        self, aid: ArtifactId, frame_bytes: bytes, proof: FreshnessProof
    ) -> VersionId:
        """Staging only — never touches the pointer ([H7]); returns a collision-free VersionId (C3)."""
        ...

    async def swap_pointer(self, aid: ArtifactId, to: VersionId, *, if_match: ETag) -> None:
        """[H6]/C3 true CAS (If-Match ETag); the sole, atomic, monotonic pointer mutation."""
        ...

    async def list_versions(self, aid: ArtifactId) -> list[VersionId]:
        """Enumerate retained versions for this ArtifactId."""
        ...

    async def gc_versions(self, aid: ArtifactId, keep_after: datetime) -> int:
        """Never deletes current/current-1; reaps only versions older than SLA+grace."""
        ...


@dataclass(frozen=True, slots=True)
class PointerState:
    """The read side of the CAS: the live pointer + the ETag that swaps against it.

    Not part of the frozen Protocol — it is the read-modify-write handle a
    rebuilder (Seam 3) needs: read ``read_pointer`` to obtain the current ETag,
    ``stage_version`` the new bytes, then ``swap_pointer(..., if_match=state.etag)``.
    A lost race surfaces as ``CASLost`` against a now-stale ETag.
    """

    version_id: VersionId
    etag: ETag
    proof: FreshnessProof


class S3ArtifactStore:
    """Concrete ``ArtifactStore`` (RATIFIED DP-2 Option C). Structurally satisfies the Protocol.

    Injectable ``client`` (moto/tests); a real ``boto3`` S3 client is built lazily
    when omitted. Every blocking boto3 call routes ``asyncio.to_thread`` (the house
    async-over-sync-boto3 pattern). There is NO dual-read bridge and NO legacy
    layout: the module simply has no such code path (RC-A/RC-D by subtraction).
    """

    def __init__(
        self,
        bucket: str,
        *,
        client: S3Client | None = None,
        region: str = "us-east-1",
        page_size: int | None = None,
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._client: S3Client | None = client
        # None => S3's native 1000-key page; a small value forces the pagination
        # loop with few objects (F4 test seam). list/gc paginate regardless.
        self._page_size = page_size

    # ------------------------------------------------------------------ keys ---
    @staticmethod
    def _pointer_key(aid: ArtifactId) -> str:
        from autom8_asana.substrate.identity import artifact_key

        return f"{artifact_key(aid)}/{_POINTER_KEY}"

    @staticmethod
    def _versions_prefix(aid: ArtifactId) -> str:
        from autom8_asana.substrate.identity import artifact_key

        return f"{artifact_key(aid)}/{_VERSIONS_SEGMENT}/"

    @classmethod
    def _frame_key(cls, aid: ArtifactId, version_id: VersionId) -> str:
        return f"{cls._versions_prefix(aid)}{version_id}/{_FRAME_OBJECT}"

    def _s3(self) -> S3Client:
        if self._client is None:
            import boto3

            self._client = boto3.client("s3", region_name=self._region)
        return self._client

    # ------------------------------------------------------------ read paths ---
    async def read_current(self, aid: ArtifactId) -> tuple[bytes, FreshnessProof]:
        """Resolve pointer → named immutable version in ONE logical read ([H5]).

        Raises ``ArtifactMissing`` on an absent pointer OR a dangling pointer
        (named version reaped/absent) — never ``(None, None)``.
        """
        state = await self.read_pointer(aid)
        if state is None:
            raise ArtifactMissing(f"no current pointer for {aid!r}")
        try:
            resp = await asyncio.to_thread(
                self._s3().get_object,
                Bucket=self._bucket,
                Key=self._frame_key(aid, state.version_id),
            )
        except ClientError as exc:
            if _status(exc) == 404:
                raise ArtifactMissing(
                    f"pointer for {aid!r} names version {state.version_id} but its frame is absent"
                ) from exc
            raise
        frame_bytes: bytes = resp["Body"].read()
        return frame_bytes, state.proof

    async def read_pointer(self, aid: ArtifactId) -> PointerState | None:
        """CAS read side: the current pointer + its ETag, or ``None`` if absent.

        Not on the frozen Protocol; the read-modify-write handle for swappers.
        """
        try:
            resp = await asyncio.to_thread(
                self._s3().get_object, Bucket=self._bucket, Key=self._pointer_key(aid)
            )
        except ClientError as exc:
            if _status(exc) == 404:
                return None
            raise
        body: bytes = resp["Body"].read()
        etag = ETag(str(resp["ETag"]))
        try:
            obj = json.loads(body)
            version_id = VersionId(str(obj["version_id"]))
            proof = _proof_from_json(obj["proof"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise PointerCorrupt(
                f"current.json for {aid!r} is present but unparseable/malformed"
            ) from exc
        return PointerState(version_id=version_id, etag=etag, proof=proof)

    # ----------------------------------------------------------- write paths ---
    async def stage_version(
        self, aid: ArtifactId, frame_bytes: bytes, proof: FreshnessProof
    ) -> VersionId:
        """Write an immutable version; NEVER touch the pointer ([H7]).

        ``version_id = sha256(frame_bytes)`` and the frame PUT is ``If-None-Match:
        *`` (write-once). Re-staging identical content is an idempotent no-op: S3
        answers 412, which we swallow and return the same VersionId — the version
        is already present and immutable (C3 idempotency).
        """
        version_id = VersionId(hashlib.sha256(frame_bytes).hexdigest())
        try:
            await asyncio.to_thread(
                self._s3().put_object,
                Bucket=self._bucket,
                Key=self._frame_key(aid, version_id),
                Body=frame_bytes,
                Metadata=_proof_to_metadata(proof),
                IfNoneMatch="*",
            )
        except ClientError as exc:
            if _status(exc) == 412:
                return version_id  # already staged; immutable, idempotent
            raise
        return version_id

    async def swap_pointer(self, aid: ArtifactId, to: VersionId, *, if_match: ETag) -> None:
        """The sole atomic pointer mutation — a TRUE CAS ([H6]/C3).

        ``if_match=CREATE_IF_ABSENT`` creates the first pointer (``If-None-Match:
        *``); any other value is an ``If-Match`` ETag conditional PUT. The proof
        published into the pointer is read back from the staged version's
        immutable S3 metadata — so the pointer atomically carries {version_id,
        proof} in ONE object (DP-2 Option C: no serve-time torn window).

        A blank/whitespace ``if_match`` is refused LOUD before any S3 call (QA F2):
        emitting ``IfMatch=""`` degrades to an UNCONDITIONAL overwrite (moto proved
        the clobber; real-S3 ``If-Match:""`` is an S8 integration carry) — the exact
        concurrent-clobber the CAS exists to forbid.
        """
        if if_match != CREATE_IF_ABSENT and not if_match.strip():
            raise ValueError(
                "blank/whitespace if_match would degrade to an UNCONDITIONAL pointer "
                "overwrite (the concurrent-clobber CAS forbids); pass a real ETag from "
                "read_pointer, or CREATE_IF_ABSENT to create the first pointer"
            )
        proof = await self._staged_proof(aid, to)
        body = json.dumps(
            {"version_id": str(to), "proof": _proof_to_json(proof)},
            sort_keys=True,
        ).encode("utf-8")
        put_kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": self._pointer_key(aid),
            "Body": body,
            "ContentType": "application/json",
        }
        if if_match == CREATE_IF_ABSENT:
            put_kwargs["IfNoneMatch"] = "*"
        else:
            put_kwargs["IfMatch"] = str(if_match)
        try:
            await asyncio.to_thread(self._s3().put_object, **put_kwargs)
        except ClientError as exc:
            status = _status(exc)
            if status == 412:
                raise CASLost(
                    f"CAS lost swapping {aid!r} -> {to} "
                    f"({'create' if if_match == CREATE_IF_ABSENT else 'if-match'} precondition failed)"
                ) from exc
            if status == 404:
                raise PointerAbsent(
                    f"If-Match swap of {aid!r} -> {to} but the pointer is absent"
                ) from exc
            if status == 409:
                raise ConcurrentPointerDelete(
                    f"concurrent-delete race swapping {aid!r} -> {to}"
                ) from exc
            raise

    async def refresh_pointer_proof(
        self, aid: ArtifactId, proof: FreshnessProof, *, if_match: ETag
    ) -> None:
        """Republish current.json with the SAME version_id but a FRESHER proof, under CAS (C14/F1).

        The architect's F1/C14 ruling: byte-stable-content proof-advance is S4
        POLICY on the mutable pointer. This is its store-side write path — an
        idempotent rebuild that re-verified identical bytes at a later instant
        advances the served ``built_from_live_at`` WITHOUT minting a new version and
        WITHOUT touching the immutable version object (Option-C decoupling: proof
        lives in the pointer, not the version metadata). Additive beyond the frozen
        Protocol; ``swap_pointer`` is unchanged.

        Enforced invariants: (a) ``built_from_live_at`` is monotonic NON-DECREASING
        for the same version_id — a strictly-backward refresh raises
        ``StaleProofRefused``; (b) only current.json is written under ``If-Match``
        (a lost race raises ``CASLost``); (c) ``versions/{id}/frame`` bytes+metadata
        are NEVER mutated.
        """
        if not if_match.strip():
            raise ValueError(
                "blank/whitespace if_match would degrade to an UNCONDITIONAL pointer "
                "overwrite (QA F2); pass the ETag from read_pointer"
            )
        current = await self.read_pointer(aid)
        if current is None:
            raise ArtifactMissing(f"no current pointer to refresh for {aid!r}")
        if proof.built_from_live_at < current.proof.built_from_live_at:
            raise StaleProofRefused(
                f"refresh_pointer_proof for {aid!r} would move built_from_live_at backward "
                f"({proof.built_from_live_at.isoformat()} < "
                f"{current.proof.built_from_live_at.isoformat()})"
            )
        body = json.dumps(
            {"version_id": str(current.version_id), "proof": _proof_to_json(proof)},
            sort_keys=True,
        ).encode("utf-8")
        try:
            await asyncio.to_thread(
                self._s3().put_object,
                Bucket=self._bucket,
                Key=self._pointer_key(aid),
                Body=body,
                ContentType="application/json",
                IfMatch=str(if_match),
            )
        except ClientError as exc:
            status = _status(exc)
            if status == 412:
                raise CASLost(
                    f"CAS lost refreshing proof for {aid!r} (if-match precondition failed)"
                ) from exc
            if status == 404:
                raise PointerAbsent(f"proof refresh of {aid!r} but the pointer is absent") from exc
            if status == 409:
                raise ConcurrentPointerDelete(
                    f"concurrent-delete race refreshing proof for {aid!r}"
                ) from exc
            raise

    async def _staged_proof(self, aid: ArtifactId, version_id: VersionId) -> FreshnessProof:
        try:
            head = await asyncio.to_thread(
                self._s3().head_object,
                Bucket=self._bucket,
                Key=self._frame_key(aid, version_id),
            )
        except ClientError as exc:
            if _status(exc) == 404:
                raise ValueError(
                    f"cannot swap {aid!r} to unstaged version {version_id} "
                    "(stage_version must precede swap_pointer)"
                ) from exc
            raise
        metadata: dict[str, str] = head["Metadata"]
        return _proof_from_metadata(metadata)

    # -------------------------------------------------------- enumerate / gc ---
    async def _list_all_contents(self, prefix: str) -> list[Any]:
        """Paginate list_objects_v2 over ALL Contents under ``prefix`` (F4: no 1000-key cap).

        Loops on ``NextContinuationToken`` so a >1000-version tail cannot escape
        enumeration (and therefore GC). ``page_size`` (test seam) forces the loop
        with few objects; prod uses S3's native 1000-key page.
        """
        contents: list[Any] = []
        token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"Bucket": self._bucket, "Prefix": prefix}
            if self._page_size is not None:
                kwargs["MaxKeys"] = self._page_size
            if token is not None:
                kwargs["ContinuationToken"] = token
            resp = await asyncio.to_thread(self._s3().list_objects_v2, **kwargs)
            contents.extend(resp.get("Contents", []))
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
            if token is None:
                break
        return contents

    async def list_versions(self, aid: ArtifactId) -> list[VersionId]:
        """Enumerate retained versions (PAGINATED — no 1000-key cap, F4)."""
        prefix = self._versions_prefix(aid)
        vids: set[VersionId] = set()
        for obj in await self._list_all_contents(prefix):
            version_id = str(obj["Key"])[len(prefix) :].split("/", 1)[0]  # "{id}/frame" -> id
            if version_id:
                vids.add(VersionId(version_id))
        return sorted(vids)

    async def gc_versions(self, aid: ArtifactId, keep_after: datetime) -> int:
        """Reap versions older than ``keep_after`` — NEVER current or current-1.

        ``current`` is the pointer's version; ``current-1`` is the most-recently
        created OTHER version (the rollback target). Both are protected regardless
        of age; every remaining version whose frame predates ``keep_after`` is
        deleted. Enumeration is PAGINATED (F4) so a >1000-version tail is still
        reaped. Returns the count reaped. Over-deletion / a reader holding a reaped
        version fails loud downstream (``ArtifactMissing`` → refuse), never silent.
        """
        prefix = self._versions_prefix(aid)
        frames: list[tuple[VersionId, str, datetime]] = []
        for obj in await self._list_all_contents(prefix):
            key = str(obj["Key"])
            if not key.endswith(f"/{_FRAME_OBJECT}"):
                continue
            version_id = VersionId(key[len(prefix) :].rsplit("/", 1)[0])
            frames.append((version_id, key, obj["LastModified"]))

        protected = await self._protected_versions(aid, frames)
        reaped = 0
        for version_id, key, last_modified in frames:
            if version_id in protected:
                continue
            if last_modified >= keep_after:
                continue
            await asyncio.to_thread(self._s3().delete_object, Bucket=self._bucket, Key=key)
            reaped += 1
        return reaped

    async def _protected_versions(
        self, aid: ArtifactId, frames: list[tuple[VersionId, str, datetime]]
    ) -> set[VersionId]:
        state = await self.read_pointer(aid)
        protected: set[VersionId] = set()
        if state is not None:
            protected.add(state.version_id)  # current
        newest_other: tuple[VersionId, datetime] | None = None
        for version_id, _key, last_modified in frames:
            if state is not None and version_id == state.version_id:
                continue
            if newest_other is None or last_modified > newest_other[1]:
                newest_other = (version_id, last_modified)
        if newest_other is not None:
            protected.add(newest_other[0])  # current-1 (rollback target)
        return protected


# ------------------------------------------------------------ proof codecs ---
def _proof_to_metadata(proof: FreshnessProof) -> dict[str, str]:
    """FreshnessProof -> S3 user-metadata (all values ASCII strings)."""
    return {
        _MD_BUILT_AT: proof.built_from_live_at.isoformat(),
        _MD_DIGEST: proof.content_digest,
        _MD_SLA: str(proof.sla_seconds),
    }


def _proof_from_metadata(metadata: dict[str, str]) -> FreshnessProof:
    from datetime import datetime

    from autom8_asana.substrate.freshness import FreshnessProof

    return FreshnessProof(
        built_from_live_at=datetime.fromisoformat(metadata[_MD_BUILT_AT]),
        content_digest=metadata[_MD_DIGEST],
        sla_seconds=int(metadata[_MD_SLA]),
    )


def _proof_to_json(proof: FreshnessProof) -> dict[str, Any]:
    return {
        "built_from_live_at": proof.built_from_live_at.isoformat(),
        "content_digest": proof.content_digest,
        "sla_seconds": proof.sla_seconds,
    }


def _proof_from_json(obj: Any) -> FreshnessProof:
    from datetime import datetime

    from autom8_asana.substrate.freshness import FreshnessProof

    return FreshnessProof(
        built_from_live_at=datetime.fromisoformat(str(obj["built_from_live_at"])),
        content_digest=str(obj["content_digest"]),
        sla_seconds=int(obj["sla_seconds"]),
    )


def _status(exc: ClientError) -> int:
    """HTTP status of a botocore ClientError (0 if unparseable)."""
    meta = exc.response.get("ResponseMetadata", {})
    try:
        return int(meta.get("HTTPStatusCode", 0))
    except (TypeError, ValueError):
        return 0
