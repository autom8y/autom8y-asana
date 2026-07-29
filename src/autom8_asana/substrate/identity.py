"""Substrate-v2 Seam 2 — IDENTITY (pure core). RC-C / RC-A.

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 2 (identity half).
Lands the frozen identity contract; the [H4] registry-servable guard and the
key-builder bodies are owned by S3.

``EntityType`` is REUSED from ``autom8_asana.core.types`` — never re-declared.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.core.types import EntityType


@dataclass(frozen=True, slots=True)
class ArtifactId:
    """Typed (project, entity) address (RC-C). Seam 2, FROZEN v1.0.

    ``entity_type`` is REQUIRED — no default, no None — so the plane-blind wound
    is unconstructable. The [H4] registry-servable ``__post_init__`` guard is
    DELIBERATELY left to the S3 owner (FORK-W1 scope cut); SEAM-0 lands fields
    only, no guard logic.
    """

    project_gid: str
    entity_type: EntityType  # REQUIRED — no default, no None


def artifact_key(aid: ArtifactId) -> str:
    """Pure; the ONLY key-builder; no None branch, no legacy segment.

    Owned by S3 (substrate.identity). SEAM-0 lands the signature only.
    """
    raise NotImplementedError("owned by S3")


def is_servable(entity_type: EntityType) -> bool:
    """Servable-set membership, DERIVED from the entity registry (C6 — no drift enum).

    Owned by S3 (substrate.identity). SEAM-0 lands the signature only.

    NOTE: signature inferred from the §4 usage ``if not is_servable(self.entity_type)``
    inside the frozen ArtifactId guard (param is the discriminator; result used in
    boolean context).
    """
    raise NotImplementedError("owned by S3")
