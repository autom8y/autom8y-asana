"""Substrate-v2 Seam 1 — FRESHNESS (pure core). RC-B.

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 1. This module lands
the frozen contract surface ONLY; the freshness law bodies are owned by S2.

``is_provable`` is the SOLE freshness definition ([H3]/C1); ``canonical_digest``
is [H1] the ONE digest function. Both are consumed identically by serving
(Seam 4) and observability (Seam 5).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class FreshnessProof:
    """Content-derived freshness proof (RC-B). Seam 1, FROZEN v1.0.

    Fields transcribed verbatim from TDD §4 Seam 1. The [H2] tz-reject
    ``__post_init__`` guard is DELIBERATELY left to the S2 owner (FORK-W1
    scope cut); SEAM-0 lands fields only, no guard logic.
    """

    # tz-aware UTC; = MIN over constituent sections' last REAL content-fetch instants (C1)
    built_from_live_at: datetime
    # sha256 hex over canonical_digest() form — never GIDs, never parquet bytes
    content_digest: str
    # freshness contract for this (project, entity) class; sourced from the entity registry
    sla_seconds: int


class Provability(Enum):
    """CLOSED — shared verbatim with Seam 5; no builder adds a member."""

    PROVABLE = "provable"
    STALE = "stale"
    CORRUPT = "corrupt"


def is_provable(proof: FreshnessProof, served_frame_digest: str, now: datetime) -> Provability:
    """PROVABLE iff (now - built_from_live_at) <= sla_seconds AND served_frame_digest == content_digest.

    Else STALE (age) or CORRUPT (digest mismatch). Pure; deterministic in its 3
    args; no I/O, no now().

    Owned by S2 (substrate.freshness). SEAM-0 lands the signature only.
    """
    raise NotImplementedError("owned by S2")


def canonical_digest(frame: object) -> str:
    """[H1] the ONE digest function; every producer/consumer calls it.

    Owned by S2 (substrate.freshness). SEAM-0 lands the signature only.

    NOTE: ``frame`` is un-annotated in the §4 draw; the parsed-frame in-memory
    type is an S2-owned decision. Annotated ``object`` here purely to satisfy the
    repo mypy-strict default (P11) — maximally open, imposes zero narrowing on S2.
    """
    raise NotImplementedError("owned by S2")
