"""Substrate-v2 Seam 4 — SERVING (core policy + thin adapters). RC-C(serve) / P2.

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 4. Value objects +
the single public read Protocol; the per-read gate and adapter bodies are owned
by S4. The cross-process WIRE contract is the operator's DP-3 ruling — this seam
is wire-stable (the ``Refused`` FIELDS hold under any ratified status class).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping

    from autom8_asana.substrate.freshness import FreshnessProof
    from autom8_asana.substrate.identity import ArtifactId


class RefuseReason(Enum):
    """CLOSED refusal taxonomy ([H14]): {STALE, CORRUPT, MISSING, DIVERGENT}."""

    STALE = "stale"
    CORRUPT = "corrupt"
    MISSING = "missing"
    DIVERGENT = "divergent"


@dataclass(frozen=True, slots=True)
class RefusePayload:
    """OQ-1 frozen observable ([H14] — do NOT narrow): the RC-A-2 explanation surface.

    Seam 4, FROZEN v1.0. The wire FORMAT is DP-3; the FIELDS below are the seam.
    Every dimension the design mandates is present and un-narrowed — the
    ``of each`` / ``per-section`` multiplicities are preserved as mappings, not
    collapsed into a single opaque message.
    """

    plane: str  # which copy / plane the refusal concerns
    absolute_age: Mapping[str, float]  # absolute age (seconds) of EACH copy/plane
    magnitude: float  # divergence magnitude between copies
    per_section_delta: Mapping[str, float]  # per-section composition delta


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
