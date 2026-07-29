"""Substrate-v2 Seam 2 — IDENTITY (pure core). RC-C / RC-A.

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 2 (identity half).
S3 fills the two owned bodies (``artifact_key`` / ``is_servable``) and the [H4]
registry-servable ``__post_init__`` guard; the field surface stays exactly as
SEAM-0 landed it.

``EntityType`` is REUSED from ``autom8_asana.core.types`` — never re-declared.
The servable set is DERIVED from the entity registry (C6 — no hand-maintained
"drift enum"): an entity is servable iff a *warmable* ``EntityDescriptor`` is
bound to it. The registry lookup is function-local so this module keeps a pure
import surface (stdlib + ``TYPE_CHECKING`` only); the registry is consulted at
construction time, cached once.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.core.types import EntityType


@dataclass(frozen=True, slots=True)
class ArtifactId:
    """Typed (project, entity) address (RC-C). Seam 2, FROZEN v1.0.

    ``entity_type`` is REQUIRED — no default, no None — so the plane-blind wound
    (v1's ``entity_type: str | None = None``) is unconstructable: a caller that
    omits the discriminator is a mypy error, not a runtime fallback. The [H4]
    guard content is FROZEN by the seam and transcribed verbatim below:

    * empty ``project_gid`` is refused;
    * a non-servable ``entity_type`` (``UNKNOWN``, structural ``PROJECT`` /
      ``SECTION``, any non-warmable member) is refused **at construction**
      (C6 posture: omission impossible-by-type, explicit non-servable
      FAIL-LOUD-at-construction — never a silent legacy default).
    """

    project_gid: str
    entity_type: EntityType  # REQUIRED — no default, no None

    def __post_init__(self) -> None:
        if not self.project_gid:
            raise ValueError("empty project_gid")
        if not is_servable(self.entity_type):
            raise ValueError(f"non-servable entity_type: {self.entity_type!r}")


def artifact_key(aid: ArtifactId) -> str:
    """Pure; the ONLY key-builder; no None branch, no legacy segment.

    RATIFIED layout (DP-2, entity-AFTER-project): ``dataframes-v2/{project_gid}/
    {entity_type}``. project-GID stays the primary partition (preserving the v1
    enumeration semantics); the servable ``entity_type`` is the second segment.
    """
    return f"dataframes-v2/{aid.project_gid}/{aid.entity_type.value}"


@lru_cache(maxsize=1)
def _servable_entity_types() -> frozenset[EntityType]:
    """The servable set, DERIVED from the entity registry (C6 — single source).

    Servable == a *warmable* descriptor is bound to the ``EntityType``. This is
    the data-driven derivation the seam mandates instead of a second, drift-prone
    "servable enum": add/remove a warmable entity in the registry and servability
    follows automatically. Cached once — ``ENTITY_DESCRIPTORS`` is a module
    constant built at import and never mutated (registry docstring), so the set
    is invariant across the test-only registry reset.
    """
    from autom8_asana.core.entity_registry import get_registry

    registry = get_registry()
    return frozenset(
        descriptor.entity_type
        for descriptor in registry.warmable_entities()
        if descriptor.entity_type is not None
    )


def is_servable(entity_type: EntityType) -> bool:
    """Servable-set membership, DERIVED from the entity registry (C6 — no drift enum).

    ``True`` iff a warmable ``EntityDescriptor`` is bound to ``entity_type``.
    ``EntityType.UNKNOWN`` (no descriptor) and the structural / non-warmable
    members resolve ``False`` — the guard that closes the typed-world plane-blind
    hole.
    """
    return entity_type in _servable_entity_types()
