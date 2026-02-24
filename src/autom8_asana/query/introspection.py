"""Shared introspection helpers for entity metadata discovery.

Used by both the CLI (`__main__.py`) and API (`routes/query.py`) to
provide consistent entity/field/relation introspection. Centralizing
these functions avoids duplicating logic between the two surfaces.
"""

from __future__ import annotations


def _to_pascal_case(s: str) -> str:
    """Convert snake_case to PascalCase for schema key lookup."""
    return "".join(word.capitalize() for word in s.split("_"))


def list_entities() -> list[dict[str, object]]:
    """List all queryable entity types with metadata.

    Returns:
        List of dicts with keys: entity_type, display_name, project_gid, category.
    """
    from autom8_asana.core.entity_registry import get_registry

    registry = get_registry()
    rows: list[dict[str, object]] = []
    for desc in registry.warmable_entities():
        rows.append(
            {
                "entity_type": desc.name,
                "display_name": desc.display_name,
                "project_gid": desc.primary_project_gid,
                "category": desc.category.value,
            }
        )
    return rows


def list_fields(entity_type: str) -> list[dict[str, object]]:
    """List available fields for an entity type.

    Args:
        entity_type: Snake_case entity type name (e.g., "offer").

    Returns:
        List of dicts with keys: name, dtype, nullable, description.

    Raises:
        ValueError: If entity type has no schema registered.
    """
    from autom8_asana.core.entity_registry import get_registry as get_er
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    pascal_name = _to_pascal_case(entity_type)
    registry = SchemaRegistry.get_instance()

    if not registry.has_schema(pascal_name):
        available = sorted(
            d.name for d in get_er().all_descriptors() if d.schema_module_path
        )
        raise ValueError(
            f"No schema available for '{entity_type}'. "
            f"Queryable entities: {', '.join(available)}"
        )

    schema = registry.get_schema(pascal_name)
    rows: list[dict[str, object]] = []
    for col in schema.columns:
        rows.append(
            {
                "name": col.name,
                "dtype": col.dtype,
                "nullable": col.nullable,
                "description": col.description or "",
            }
        )
    return rows


def list_sections(entity_type: str) -> list[dict[str, object]]:
    """List section names and their classifications for an entity type.

    Reads from the CLASSIFIERS dict in ``models.business.activity``.
    Only entity types with a registered SectionClassifier are supported.

    Args:
        entity_type: Snake_case entity type name (e.g., "offer", "unit").

    Returns:
        List of dicts with keys: section_name, classification.

    Raises:
        ValueError: If entity type has no section classifier registered.
    """
    from autom8_asana.models.business.activity import CLASSIFIERS

    classifier = CLASSIFIERS.get(entity_type)
    if classifier is None:
        available = sorted(CLASSIFIERS.keys())
        raise ValueError(
            f"No section classifier for '{entity_type}'. "
            f"Available: {', '.join(available)}"
        )

    rows: list[dict[str, object]] = []
    for section_name, activity in sorted(classifier._mapping.items()):
        rows.append(
            {
                "section_name": section_name,
                "classification": activity.value,
            }
        )
    return rows


def list_relations(entity_type: str) -> list[dict[str, object]]:
    """List joinable entity types and their join keys for a given entity.

    Args:
        entity_type: Snake_case entity type name (e.g., "offer").

    Returns:
        List of dicts with keys: target, direction, default_join_key,
        cardinality, description.
    """
    from autom8_asana.query.hierarchy import ENTITY_RELATIONSHIPS

    rows: list[dict[str, object]] = []
    for rel in ENTITY_RELATIONSHIPS:
        if rel.parent_type == entity_type:
            rows.append(
                {
                    "target": rel.child_type,
                    "direction": "parent->child",
                    "default_join_key": rel.default_join_key,
                    "cardinality": rel.cardinality,
                    "description": rel.description,
                }
            )
        elif rel.child_type == entity_type:
            rows.append(
                {
                    "target": rel.parent_type,
                    "direction": "child->parent",
                    "default_join_key": rel.default_join_key,
                    "cardinality": rel.cardinality,
                    "description": rel.description,
                }
            )
    return rows
