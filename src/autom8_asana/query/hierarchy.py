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
    """

    parent_type: str
    child_type: str
    default_join_key: str
    description: str


# Known entity type relationships with their default join keys.
# These are derived from the Asana subtask hierarchy and cascade field
# extraction: parent fields cascade to children during DataFrame build.
ENTITY_RELATIONSHIPS: list[EntityRelationship] = [
    EntityRelationship(
        parent_type="business",
        child_type="unit",
        default_join_key="office_phone",
        description="Business is parent of Unit (office_phone cascades)",
    ),
    EntityRelationship(
        parent_type="business",
        child_type="contact",
        default_join_key="office_phone",
        description="Business is parent of Contact (office_phone cascades)",
    ),
    EntityRelationship(
        parent_type="business",
        child_type="offer",
        default_join_key="office_phone",
        description="Business is grandparent of Offer via Unit (office_phone cascades)",
    ),
    EntityRelationship(
        parent_type="unit",
        child_type="offer",
        default_join_key="office_phone",
        description="Unit is parent of Offer (office_phone cascades from Business)",
    ),
]


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
        if (rel.parent_type == source_type and rel.child_type == target_type) or \
           (rel.child_type == source_type and rel.parent_type == target_type):
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
