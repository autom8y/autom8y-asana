"""Contract tests for semantic annotation registry.

Per ADR-omniscience-semantic-introspection (D4): Three test categories verify
annotation completeness, cascade consistency, and backward compatibility.

Category 1: Annotation Presence
    Every cascade-sourced column in any schema has a corresponding entry
    in SEMANTIC_ANNOTATIONS with a cascade_behavior block.

Category 2: Cascade Consistency
    cascade_behavior.source_entity matches the owner entity from
    get_cascading_field_registry(). cascade_behavior.allow_override matches
    CascadingFieldDef.allow_override. Key cascade columns have
    resolution_impact containing "CRITICAL".

Category 3: Backward Compatibility
    description.split("---")[0].strip() returns non-empty human-readable text
    with no YAML syntax. yaml.safe_load(parts[1]) parses without error.
    Enrichment does not modify the original schema object.
"""

from __future__ import annotations

import yaml

from autom8_asana.dataframes.annotations import (
    SEMANTIC_ANNOTATIONS,
    VALID_SEMANTIC_TYPES,
    YAML_DELIMITER,
    enrich_description,
    enrich_schema,
    get_semantic_type,
    parse_semantic_metadata,
)
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_schemas() -> dict[str, DataFrameSchema]:
    """Load all registered schemas by name."""
    from autom8_asana.dataframes.schemas import (
        ASSET_EDIT_HOLDER_SCHEMA,
        ASSET_EDIT_SCHEMA,
        CONTACT_SCHEMA,
        OFFER_SCHEMA,
        UNIT_SCHEMA,
    )

    return {
        "unit": UNIT_SCHEMA,
        "offer": OFFER_SCHEMA,
        "contact": CONTACT_SCHEMA,
        "asset_edit": ASSET_EDIT_SCHEMA,
        "asset_edit_holder": ASSET_EDIT_HOLDER_SCHEMA,
    }


def _cascade_columns() -> list[tuple[str, str, ColumnDef]]:
    """Return (schema_name, cascade_field_name, col) for all cascade columns."""
    result = []
    for schema_name, schema in _all_schemas().items():
        for col in schema.columns:
            if col.source and col.source.lower().startswith("cascade:"):
                cascade_field = col.source[len("cascade:") :].strip()
                result.append((schema_name, cascade_field, col))
    return result


def _key_columns_by_entity() -> dict[str, tuple[str, ...]]:
    """Return key_columns per entity from the entity registry."""
    from autom8_asana.core.entity_registry import get_registry

    registry = get_registry()
    result = {}
    for desc in registry.all_descriptors():
        if desc.key_columns:
            result[desc.name] = desc.key_columns
    return result


# =========================================================================
# Category 1: Annotation Presence
# =========================================================================


class TestAnnotationPresence:
    """Every cascade column must have a SEMANTIC_ANNOTATIONS entry."""

    def test_every_cascade_column_has_annotation(self) -> None:
        """Every column with source='cascade:*' has a matching annotation."""
        missing = []
        for schema_name, _cascade_field, col in _cascade_columns():
            key = f"{schema_name}.{col.name}"
            if key not in SEMANTIC_ANNOTATIONS:
                missing.append(key)

        assert not missing, f"Cascade columns missing from SEMANTIC_ANNOTATIONS: {missing}"

    def test_every_cascade_annotation_has_cascade_behavior(self) -> None:
        """Every cascade column annotation contains a cascade_behavior block."""
        missing_behavior = []
        for schema_name, _cascade_field, col in _cascade_columns():
            key = f"{schema_name}.{col.name}"
            annotation = SEMANTIC_ANNOTATIONS.get(key)
            if annotation is not None and "cascade_behavior" not in annotation:
                missing_behavior.append(key)

        assert not missing_behavior, (
            f"Cascade annotations without cascade_behavior block: {missing_behavior}"
        )

    def test_annotation_count_matches_scope(self) -> None:
        """Verify we have annotations for all 19 column-schema combinations."""
        assert len(SEMANTIC_ANNOTATIONS) == 19, (
            f"Expected 19 annotations (12 cascade + 7 HD-02), got {len(SEMANTIC_ANNOTATIONS)}"
        )

    def test_all_annotations_have_required_fields(self) -> None:
        """Every annotation has business_meaning and data_type_semantic."""
        for key, annotation in SEMANTIC_ANNOTATIONS.items():
            assert "business_meaning" in annotation, f"Annotation {key} missing business_meaning"
            assert "data_type_semantic" in annotation, (
                f"Annotation {key} missing data_type_semantic"
            )

    def test_all_semantic_types_are_valid(self) -> None:
        """Every data_type_semantic value is from the closed vocabulary."""
        for key, annotation in SEMANTIC_ANNOTATIONS.items():
            sem_type = annotation.get("data_type_semantic")
            assert sem_type in VALID_SEMANTIC_TYPES, (
                f"Annotation {key} has invalid data_type_semantic: "
                f"{sem_type!r}. Valid: {sorted(VALID_SEMANTIC_TYPES)}"
            )


# =========================================================================
# Category 2: Cascade Consistency
# =========================================================================


class TestCascadeConsistency:
    """Verify annotations match the runtime cascade field registry."""

    def test_cascade_source_entity_matches_registry(self) -> None:
        """cascade_behavior.source_entity matches owner from field registry."""
        from autom8_asana.models.business.fields import (
            get_cascading_field_registry,
        )

        cascade_registry = get_cascading_field_registry()
        mismatches = []

        for schema_name, cascade_field, col in _cascade_columns():
            key = f"{schema_name}.{col.name}"
            annotation = SEMANTIC_ANNOTATIONS.get(key)
            if annotation is None:
                continue

            cascade_behavior = annotation.get("cascade_behavior", {})
            annotated_source = cascade_behavior.get("source_entity")

            # Look up the field in the cascade registry
            normalized = cascade_field.lower().strip()
            entry = cascade_registry.get(normalized)
            if entry is None:
                continue

            owner_class, _field_def = entry
            actual_source = owner_class.__name__

            if annotated_source != actual_source:
                mismatches.append(
                    f"{key}: annotation says {annotated_source!r}, registry says {actual_source!r}"
                )

        assert not mismatches, "cascade_behavior.source_entity mismatches:\n" + "\n".join(
            mismatches
        )

    def test_cascade_allow_override_matches_registry(self) -> None:
        """cascade_behavior.allow_override matches CascadingFieldDef."""
        from autom8_asana.models.business.fields import (
            get_cascading_field_registry,
        )

        cascade_registry = get_cascading_field_registry()
        mismatches = []

        for schema_name, cascade_field, col in _cascade_columns():
            key = f"{schema_name}.{col.name}"
            annotation = SEMANTIC_ANNOTATIONS.get(key)
            if annotation is None:
                continue

            cascade_behavior = annotation.get("cascade_behavior", {})
            annotated_override = cascade_behavior.get("allow_override")

            normalized = cascade_field.lower().strip()
            entry = cascade_registry.get(normalized)
            if entry is None:
                continue

            _owner_class, field_def = entry

            if annotated_override != field_def.allow_override:
                mismatches.append(
                    f"{key}: annotation says allow_override={annotated_override}, "
                    f"registry says allow_override={field_def.allow_override}"
                )

        assert not mismatches, "cascade_behavior.allow_override mismatches:\n" + "\n".join(
            mismatches
        )

    def test_key_cascade_columns_have_critical_resolution_impact(self) -> None:
        """Key cascade columns must have resolution_impact containing 'CRITICAL'."""
        key_cols = _key_columns_by_entity()
        missing_critical = []

        for schema_name, _cascade_field, col in _cascade_columns():
            entity_key_cols = key_cols.get(schema_name, ())
            if col.name not in entity_key_cols:
                continue

            key = f"{schema_name}.{col.name}"
            annotation = SEMANTIC_ANNOTATIONS.get(key)
            if annotation is None:
                missing_critical.append(f"{key}: no annotation")
                continue

            impact = annotation.get("resolution_impact", "")
            if "CRITICAL" not in impact:
                missing_critical.append(f"{key}: resolution_impact does not contain 'CRITICAL'")

        assert not missing_critical, (
            "Key cascade columns without CRITICAL resolution_impact:\n"
            + "\n".join(missing_critical)
        )


# =========================================================================
# Category 3: Backward Compatibility
# =========================================================================


class TestBackwardCompatibility:
    """Verify enriched descriptions preserve backward compatibility."""

    def test_human_readable_prefix_is_nonempty(self) -> None:
        """description.split('---')[0].strip() returns non-empty text."""
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for col in enriched.columns:
                if col.description and YAML_DELIMITER in col.description:
                    prefix = col.description.split("---")[0].strip()
                    assert prefix, (
                        f"{schema_name}.{col.name}: human-readable prefix is empty after enrichment"
                    )

    def test_human_readable_prefix_contains_no_yaml(self) -> None:
        """The text before --- contains no YAML syntax markers."""
        yaml_markers = ("semantic:", "business_meaning:", "cascade_behavior:")
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for col in enriched.columns:
                if col.description and YAML_DELIMITER in col.description:
                    prefix = col.description.split("---")[0].strip()
                    for marker in yaml_markers:
                        assert marker not in prefix, (
                            f"{schema_name}.{col.name}: human-readable "
                            f"prefix contains YAML marker {marker!r}"
                        )

    def test_yaml_block_parses_without_error(self) -> None:
        """yaml.safe_load on the block after --- succeeds."""
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for col in enriched.columns:
                if col.description and YAML_DELIMITER in col.description:
                    parts = col.description.split("---", 1)
                    assert len(parts) == 2, (
                        f"{schema_name}.{col.name}: expected exactly one --- delimiter"
                    )
                    parsed = yaml.safe_load(parts[1])
                    assert isinstance(parsed, dict), (
                        f"{schema_name}.{col.name}: YAML block did not parse to a dict"
                    )
                    assert "semantic" in parsed, (
                        f"{schema_name}.{col.name}: YAML block missing top-level 'semantic' key"
                    )

    def test_enrichment_does_not_modify_original_schema(self) -> None:
        """enrich_schema returns a NEW schema; original is untouched."""
        for schema_name, schema in _all_schemas().items():
            # Capture original descriptions
            original_descriptions = {col.name: col.description for col in schema.columns}

            # Enrich
            enriched = enrich_schema(schema, include_semantic=True)

            # Verify original is unchanged
            for col in schema.columns:
                assert col.description == original_descriptions[col.name], (
                    f"{schema_name}.{col.name}: original schema was mutated by enrichment"
                )

            # Verify enriched is a different object
            assert enriched is not schema, f"{schema_name}: enrich_schema returned the same object"

    def test_include_semantic_false_returns_original(self) -> None:
        """enrich_schema with include_semantic=False returns schema unchanged."""
        for _schema_name, schema in _all_schemas().items():
            result = enrich_schema(schema, include_semantic=False)
            assert result is schema

    def test_to_dict_includes_enriched_description(self) -> None:
        """DataFrameSchema.to_dict() preserves enriched descriptions."""
        for _schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            d = enriched.to_dict()
            for col_dict in d["columns"]:
                col = enriched.get_column(col_dict["name"])
                if col is not None:
                    assert col_dict["description"] == col.description


# =========================================================================
# Unit Tests for Individual Functions
# =========================================================================


class TestEnrichDescription:
    """Unit tests for enrich_description()."""

    def test_no_annotation_returns_original(self) -> None:
        """Column without annotation returns original description."""
        col = ColumnDef(
            name="unknown_field",
            dtype="Utf8",
            description="Some field",
        )
        result = enrich_description("unit", col)
        assert result == "Some field"

    def test_none_description_returns_empty_string(self) -> None:
        """Column with None description and no annotation returns ''."""
        col = ColumnDef(name="unknown_field", dtype="Utf8", description=None)
        result = enrich_description("unknown_schema", col)
        assert result == ""

    def test_enriched_description_has_delimiter(self) -> None:
        """Enriched column has --- delimiter in description."""
        col = ColumnDef(
            name="office_phone",
            dtype="Utf8",
            source="cascade:Office Phone",
            description="Office phone number (cascades from Business)",
        )
        result = enrich_description("unit", col)
        assert YAML_DELIMITER in result

    def test_enriched_yaml_has_semantic_key(self) -> None:
        """YAML block after delimiter has 'semantic' top-level key."""
        col = ColumnDef(
            name="office_phone",
            dtype="Utf8",
            source="cascade:Office Phone",
            description="Office phone number (cascades from Business)",
        )
        result = enrich_description("unit", col)
        parts = result.split("---", 1)
        parsed = yaml.safe_load(parts[1])
        assert "semantic" in parsed
        assert "business_meaning" in parsed["semantic"]


class TestParseSemanticMetadata:
    """Unit tests for parse_semantic_metadata()."""

    def test_none_description(self) -> None:
        assert parse_semantic_metadata(None) is None

    def test_plain_description(self) -> None:
        assert parse_semantic_metadata("Just a plain description") is None

    def test_enriched_description(self) -> None:
        col = ColumnDef(
            name="office_phone",
            dtype="Utf8",
            source="cascade:Office Phone",
            description="Office phone",
        )
        enriched = enrich_description("unit", col)
        metadata = parse_semantic_metadata(enriched)
        assert metadata is not None
        assert metadata["data_type_semantic"] == "phone"

    def test_malformed_yaml_returns_none(self) -> None:
        result = parse_semantic_metadata("text\n---\n: invalid : yaml :")
        assert result is None


class TestGetSemanticType:
    """Unit tests for get_semantic_type()."""

    def test_returns_type_for_enriched(self) -> None:
        col = ColumnDef(
            name="vertical",
            dtype="Utf8",
            source="cascade:Vertical",
            description="Business vertical",
        )
        enriched = enrich_description("offer", col)
        assert get_semantic_type(enriched) == "enum"

    def test_returns_none_for_unenriched(self) -> None:
        assert get_semantic_type("plain text") is None

    def test_returns_none_for_none(self) -> None:
        assert get_semantic_type(None) is None


class TestEnrichSchema:
    """Unit tests for enrich_schema()."""

    def test_enriched_schema_has_same_column_count(self) -> None:
        """Enrichment does not add or remove columns."""
        for _name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            assert len(enriched.columns) == len(schema.columns)

    def test_enriched_schema_preserves_metadata(self) -> None:
        """Schema name, version, task_type are preserved."""
        for _name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            assert enriched.name == schema.name
            assert enriched.version == schema.version
            assert enriched.task_type == schema.task_type

    def test_unannotated_columns_unchanged(self) -> None:
        """Columns without annotations keep their original description."""
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for orig_col, new_col in zip(schema.columns, enriched.columns):
                key = f"{schema_name}.{orig_col.name}"
                if key not in SEMANTIC_ANNOTATIONS:
                    assert new_col.description == orig_col.description
