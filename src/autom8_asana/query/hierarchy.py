"""Entity relationship registry for cross-entity joins.

Defines the known parent-child relationships between entity types
and their default join keys (shared columns used for matching).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityRelationship:
    """A directed relationship between two entity types.

    Attributes:
        parent_type: The parent entity type (e.g., "business").
        child_type: The child entity type (e.g., "offer").
        default_join_key: The column name present in both entity DataFrames
            that can be used to match rows (e.g., "office_phone").
        description: Human-readable description of the relationship.
        cardinality: Relationship cardinality indicator.
            Derived from EntityCategory: ROOT/COMPOSITE parent to LEAF child
            is "1:N", LEAF child to ROOT/COMPOSITE parent is "N:1",
            same category defaults to "unknown".
    """

    parent_type: str
    child_type: str
    default_join_key: str
    description: str
    cardinality: str = "unknown"  # "1:1", "1:N", "N:1", "N:M", "unknown"


# Known entity type relationships with their default join keys.
# Derived from EntityDescriptor.join_keys via _build_relationships_from_registry().
# Per ARCH-descriptor-driven-auto-wiring section 3.4: The derived list is a
# superset of the original 4 hardcoded entries (more relationships discoverable
# from bidirectional join_key declarations on descriptors).


def _derive_cardinality(parent_category: str, child_category: str) -> str:
    """Derive cardinality from EntityCategory values.

    Rules:
        - ROOT/COMPOSITE parent -> LEAF child = "1:N" (one parent has many children)
        - LEAF child -> ROOT/COMPOSITE parent = "N:1" (many children share one parent)
        - Same category = "unknown" (default)

    Args:
        parent_category: EntityCategory.value of the source descriptor.
        child_category: EntityCategory.value of the target descriptor.

    Returns:
        Cardinality string: "1:N", "N:1", or "unknown".
    """
    high_categories = {"root", "composite"}
    if parent_category in high_categories and child_category == "leaf":
        return "1:N"
    if parent_category == "leaf" and child_category in high_categories:
        return "N:1"
    return "unknown"


def _build_relationships_from_registry() -> list[EntityRelationship]:
    """Derive entity relationships from descriptor join_keys.

    Per ARCH-descriptor-driven-auto-wiring section 3.4: Loops over all
    descriptors and creates an EntityRelationship for each join_key entry.
    Cardinality is derived from EntityCategory of each side.

    Import of get_registry is deferred inside the function body to avoid
    circular imports (core/ must not be imported at module scope from query/).

    Returns:
        List of EntityRelationship instances derived from descriptor join_keys.
    """
    from autom8_asana.core.entity_registry import get_registry

    registry = get_registry()
    relationships: list[EntityRelationship] = []
    for desc in registry.all_descriptors():
        for target, key in desc.join_keys:
            target_desc = registry.get(target)
            if target_desc is not None:
                cardinality = _derive_cardinality(desc.category.value, target_desc.category.value)
            else:
                cardinality = "unknown"
            relationships.append(
                EntityRelationship(
                    parent_type=desc.name,
                    child_type=target,
                    default_join_key=key,
                    description=(f"Auto-derived: {desc.pascal_name} -> {target} via {key}"),
                    cardinality=cardinality,
                )
            )
    return relationships


ENTITY_RELATIONSHIPS: list[EntityRelationship] = _build_relationships_from_registry()


def find_relationship(
    source_type: str,
    target_type: str,
) -> EntityRelationship | None:
    """Find a relationship between two entity types.

    Searches for a direct relationship in either direction
    (source as parent or source as child of target).

    Args:
        source_type: The primary entity type being queried.
        target_type: The entity type to join with.

    Returns:
        EntityRelationship if found, None otherwise.
    """
    for rel in ENTITY_RELATIONSHIPS:
        if (rel.parent_type == source_type and rel.child_type == target_type) or (
            rel.child_type == source_type and rel.parent_type == target_type
        ):
            return rel
    return None


def get_join_key(
    source_type: str,
    target_type: str,
    explicit_key: str | None = None,
) -> str | None:
    """Determine the join key for two entity types.

    Args:
        source_type: The primary entity type.
        target_type: The join target entity type.
        explicit_key: User-specified join key (overrides default).

    Returns:
        Column name to join on, or None if no relationship exists.
    """
    if explicit_key is not None:
        return explicit_key

    rel = find_relationship(source_type, target_type)
    if rel is None:
        return None
    return rel.default_join_key


def get_joinable_types(source_type: str) -> list[str]:
    """Return entity types that can be joined with the source type.

    Args:
        source_type: The primary entity type.

    Returns:
        List of entity type names that have a relationship with source.
    """
    result: list[str] = []
    for rel in ENTITY_RELATIONSHIPS:
        if rel.parent_type == source_type:
            result.append(rel.child_type)
        elif rel.child_type == source_type:
            result.append(rel.parent_type)
    return sorted(set(result))
