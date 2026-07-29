"""ArtifactId + key-builder + servable guard (Seam 2 identity half, RC-C / C6).

The servable set is DERIVED from the entity registry (C6 — no drift enum); the
guard refuses omission by type (see test_c6_type_error) and refuses an explicit
non-servable member LOUD at construction. The key layout is entity-after-project.
"""

from __future__ import annotations

import pytest

from autom8_asana.core.entity_registry import get_registry
from autom8_asana.core.types import EntityType
from autom8_asana.substrate import ArtifactId, artifact_key, is_servable

# Registry-derived at import (the C6 single source) — the same set the guard uses.
_SERVABLE = {d.entity_type for d in get_registry().warmable_entities() if d.entity_type is not None}


# ------------------------------------------------------------- key layout ---
def test_artifact_key_is_entity_after_project() -> None:
    """RATIFIED DP-2 F3: dataframes-v2/{project_gid}/{entity_type} — entity AFTER project."""
    aid = ArtifactId(project_gid="1200000000000042", entity_type=EntityType.OFFER)
    assert artifact_key(aid) == "dataframes-v2/1200000000000042/offer"


def test_artifact_key_uses_enum_value_not_name() -> None:
    aid = ArtifactId(project_gid="99", entity_type=EntityType.BUSINESS)
    assert artifact_key(aid) == "dataframes-v2/99/business"


def test_artifact_key_has_no_legacy_or_none_segment() -> None:
    """There is exactly one key-builder and no plane-blind branch (contrast v1)."""
    aid = ArtifactId(project_gid="7", entity_type=EntityType.CONTACT)
    key = artifact_key(aid)
    assert "None" not in key
    assert "legacy" not in key
    assert key.count("/") == 2  # dataframes-v2 / project / entity — no extra segment


# ---------------------------------------------------- servable derivation ---
def test_is_servable_matches_registry_warmable_set() -> None:
    """C6: servability is DERIVED from the registry, not a hand-maintained enum.

    Every EntityType's servability equals its warmable-registry membership — a
    hardcoded drift-set would fail this the moment the registry changed.
    """
    for entity_type in EntityType:
        assert is_servable(entity_type) == (entity_type in _SERVABLE)


def test_known_servable_members_are_servable() -> None:
    for entity_type in (EntityType.BUSINESS, EntityType.OFFER, EntityType.UNIT, EntityType.CONTACT):
        assert is_servable(entity_type)


def test_unknown_and_structural_members_are_not_servable() -> None:
    for entity_type in (EntityType.UNKNOWN, EntityType.PROJECT, EntityType.SECTION):
        assert not is_servable(entity_type)


# -------------------------------------------------- construction guard [H4] ---
def test_servable_entity_constructs() -> None:
    aid = ArtifactId(project_gid="1", entity_type=EntityType.OFFER)
    assert aid.entity_type is EntityType.OFFER


def test_unknown_entity_refused_loud_at_construction() -> None:
    """C6: explicit UNKNOWN is FAIL-LOUD-at-construction (not a silent legacy default)."""
    with pytest.raises(ValueError, match="non-servable entity_type"):
        ArtifactId(project_gid="1", entity_type=EntityType.UNKNOWN)


def test_structural_members_refused() -> None:
    for entity_type in (EntityType.PROJECT, EntityType.SECTION):
        with pytest.raises(ValueError, match="non-servable entity_type"):
            ArtifactId(project_gid="1", entity_type=entity_type)


def test_empty_project_gid_refused() -> None:
    with pytest.raises(ValueError, match="empty project_gid"):
        ArtifactId(project_gid="", entity_type=EntityType.OFFER)


def test_artifact_id_is_frozen() -> None:
    aid = ArtifactId(project_gid="1", entity_type=EntityType.OFFER)
    with pytest.raises(AttributeError):
        aid.project_gid = "2"  # type: ignore[misc]


def test_entity_type_is_required_by_signature() -> None:
    """C6 structural backbone (fast, always-on): entity_type has NO default.

    Omission is therefore impossible-by-type — a caller that drops the
    discriminator is a mypy error, not a runtime legacy fallback. The exhaustive
    two-sided mypy proof (and the str-discriminator variant) is the slow
    test_c6_type_error.py.
    """
    import inspect

    sig = inspect.signature(ArtifactId)
    assert sig.parameters["entity_type"].default is inspect.Parameter.empty
    assert sig.parameters["project_gid"].default is inspect.Parameter.empty


def test_non_warmable_holder_refused() -> None:
    """A registry entity that exists but is not warmable is not servable (loud refuse)."""
    # OFFER_HOLDER is bound in the registry but warmable=False -> non-servable.
    assert not is_servable(EntityType.OFFER_HOLDER)
    with pytest.raises(ValueError, match="non-servable entity_type"):
        ArtifactId(project_gid="1", entity_type=EntityType.OFFER_HOLDER)
