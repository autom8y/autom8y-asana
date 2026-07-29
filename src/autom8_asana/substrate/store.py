"""Substrate-v2 Seam 2 — STORAGE (infra). RC-A / RC-E (storage half).

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 2 (storage half).
Protocol signatures ONLY; implementations owned by S3. The store is POLICY-FREE
([H8]) — it returns bytes+proof and never applies the SLA/refuse gate (Seam 4).

The PHYSICAL version layout is the operator's DP-2 ruling — this seam is
layout-stable (``stage_version`` / ``swap_pointer`` / ``read_current`` semantics
hold under any ratified shape).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from autom8_asana.substrate.freshness import FreshnessProof
    from autom8_asana.substrate.identity import ArtifactId

# collision-free (UUID/timestamp/digest-addressed — not max+1); see [H6]/C3
type VersionId = str
# S3 entity-tag carried into the If-Match conditional swap (true CAS)
type ETag = str


class ArtifactMissing(Exception):
    """Raised by ``ArtifactStore.read_current`` when no current pointer/object exists ([H5]).

    NEVER returns ``(None, None)`` — absence is loud (contrast v1).
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
