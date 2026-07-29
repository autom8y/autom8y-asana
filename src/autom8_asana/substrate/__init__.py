"""Substrate-v2 — the five FROZEN seam contracts (v1.0-frozen-2026-07-29).

This package lands the SEAM-0 contract surface for TDD-substrate-v2 §4: the value
objects, closed enums, type aliases, exceptions, and Protocol signatures that the
S2-S7 build fan converges on. It is built DARK beside v1's ``dataframes/`` (§2
placement); v1 is untouched and frozen.

Owned-function bodies raise ``NotImplementedError`` with an owner tag
(``is_provable`` / ``canonical_digest`` — S2; ``artifact_key`` / ``is_servable``
— S3). The two value-object ``__post_init__`` guards ([H2] tz-reject, [H4]
registry-servable) are DELIBERATELY left to their owners per the FORK-W1 scope
cut. Fan sprints ADD module bodies and never restructure this root.

See TDD-substrate-v2 §4 for the frozen contract; §5 for the fork rulings.
"""

from __future__ import annotations

from autom8_asana.substrate.freshness import (
    FreshnessProof,
    Provability,
    canonical_digest,
    is_provable,
)
from autom8_asana.substrate.identity import (
    ArtifactId,
    artifact_key,
    is_servable,
)
from autom8_asana.substrate.observe import (
    EvaluationRun,
    ProvabilityEvaluator,
)
from autom8_asana.substrate.rebuild import (
    AcceptancePredicates,
    PacedAsanaFetcher,
    Rebuilder,
    RebuildOutcome,
    RebuildResult,
)
from autom8_asana.substrate.serve import (
    Provable,
    Refused,
    RefusePayload,
    RefuseReason,
    ServedNumber,
    SubstrateReader,
)
from autom8_asana.substrate.store import (
    ArtifactMissing,
    ArtifactStore,
    ETag,
    VersionId,
)

__all__ = [
    # Seam 1 — FRESHNESS (substrate.freshness)
    "FreshnessProof",
    "Provability",
    "is_provable",
    "canonical_digest",
    # Seam 2 — IDENTITY + STORAGE (substrate.identity, substrate.store)
    "ArtifactId",
    "artifact_key",
    "is_servable",
    "ArtifactStore",
    "ArtifactMissing",
    "VersionId",
    "ETag",
    # Seam 3 — REBUILD (substrate.rebuild)
    "RebuildOutcome",
    "Rebuilder",
    "RebuildResult",
    "PacedAsanaFetcher",
    "AcceptancePredicates",
    # Seam 4 — SERVING (substrate.serve)
    "Provable",
    "Refused",
    "RefuseReason",
    "RefusePayload",
    "ServedNumber",
    "SubstrateReader",
    # Seam 5 — OBSERVABILITY (substrate.observe)
    "ProvabilityEvaluator",
    "EvaluationRun",
]
