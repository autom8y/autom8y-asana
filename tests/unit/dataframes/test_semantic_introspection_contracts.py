"""SI-01 through SI-16: Domain 3 Semantic Introspection contract tests.

Per ADR-omniscience-semantic-introspection: Validates the semantic annotation
enrichment pipeline, cascade-annotation consistency, and API query parameter
contracts.

Test IDs map 1:1 to the SI specification matrix:
    SI-01: include_semantic=false default returns plain descriptions
    SI-02: include_semantic=true returns descriptions with YAML block
    SI-03: Human-readable prefix always present
    SI-04: YAML block parses without error
    SI-05: Parsed YAML always has 'semantic' top-level key
    SI-06: Every cascade-sourced column has cascade_behavior in annotations
    SI-07: cascade_behavior.source_entity matches cascading field registry
    SI-08: cascade_behavior.allow_override matches CascadingFieldDef
    SI-09: Key cascade columns have resolution_impact containing "CRITICAL"
    SI-10: semantic_type filter works
    SI-11: include_enums parameter
    SI-12: Enum detail endpoint
    SI-13: Enriched description preserved in schema dict
    SI-14: Unannotated columns return plain descriptions with include_semantic=true
    SI-15: 12 cascade column-schema combinations annotated
    SI-16: 7 HD-02 priority non-cascade fields annotated
"""

from __future__ import annotations

import pytest
import yaml

from autom8_asana.dataframes.annotations import (
    SEMANTIC_ANNOTATIONS,
    YAML_DELIMITER,
    enrich_description,
    enrich_schema,
    get_semantic_type,
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


def _make_annotated_col(schema_name: str, col_name: str) -> ColumnDef:
    """Create a minimal ColumnDef for an annotated column.

    Uses the annotation key to fabricate a ColumnDef with a plausible
    description and source for testing enrichment functions directly.
    """
    annotation = SEMANTIC_ANNOTATIONS[f"{schema_name}.{col_name}"]
    has_cascade = "cascade_behavior" in annotation
    source = f"cascade:FakeField" if has_cascade else f"cf:{col_name}"
    return ColumnDef(
        name=col_name,
        dtype="Utf8",
        source=source,
        description=f"Test description for {col_name}",
    )


# ---------------------------------------------------------------------------
# SI-01: include_semantic=false default returns plain descriptions
# ---------------------------------------------------------------------------


class TestSI01IncludeSemanticFalseDefault:
    """SI-01: When include_semantic=False, descriptions have no YAML block."""

    def test_enrich_schema_false_returns_original_object(self) -> None:
        """enrich_schema(include_semantic=False) returns the same schema object."""
        for _name, schema in _all_schemas().items():
            result = enrich_schema(schema, include_semantic=False)
            assert result is schema, (
                f"Schema '{_name}': include_semantic=False should return "
                f"the original schema object (identity), not a copy"
            )

    def test_no_yaml_delimiter_when_semantic_disabled(self) -> None:
        """No column descriptions contain the YAML delimiter when disabled."""
        for schema_name, schema in _all_schemas().items():
            result = enrich_schema(schema, include_semantic=False)
            for col in result.columns:
                if col.description:
                    assert YAML_DELIMITER not in col.description, (
                        f"{schema_name}.{col.name}: description contains "
                        f"YAML delimiter even with include_semantic=False"
                    )


# ---------------------------------------------------------------------------
# SI-02: include_semantic=true returns descriptions with YAML block
# ---------------------------------------------------------------------------


class TestSI02IncludeSemanticTrueYAML:
    """SI-02: Annotated columns gain a YAML block when include_semantic=True."""

    def test_annotated_columns_have_yaml_delimiter(self) -> None:
        """Every annotated column has the --- delimiter after enrichment."""
        missing = []
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for col in enriched.columns:
                key = f"{schema_name}.{col.name}"
                if key in SEMANTIC_ANNOTATIONS:
                    if not col.description or YAML_DELIMITER not in col.description:
                        missing.append(key)

        assert not missing, (
            f"Annotated columns missing YAML block after enrichment: {missing}"
        )

    def test_enriched_schema_is_different_object(self) -> None:
        """enrich_schema(include_semantic=True) returns a new DataFrameSchema."""
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            # At least one annotated column should exist per schema we test
            has_annotations = any(
                f"{schema_name}.{col.name}" in SEMANTIC_ANNOTATIONS
                for col in schema.columns
            )
            if has_annotations:
                assert enriched is not schema, (
                    f"Schema '{schema_name}': enrich_schema should return "
                    f"a new object, not the original"
                )


# ---------------------------------------------------------------------------
# SI-03: Human-readable prefix always present
# ---------------------------------------------------------------------------


class TestSI03HumanReadablePrefix:
    """SI-03: Text before '---' is non-empty for all enriched descriptions."""

    def test_prefix_is_nonempty(self) -> None:
        """Every enriched description has non-empty text before the delimiter."""
        empty_prefixes = []
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for col in enriched.columns:
                if col.description and YAML_DELIMITER in col.description:
                    prefix = col.description.split("---")[0].strip()
                    if not prefix:
                        empty_prefixes.append(f"{schema_name}.{col.name}")

        assert not empty_prefixes, (
            f"Enriched columns with empty human-readable prefix: {empty_prefixes}"
        )

    def test_prefix_contains_no_yaml_syntax(self) -> None:
        """Human-readable prefix must not contain YAML structural markers."""
        yaml_markers = ("semantic:", "business_meaning:", "cascade_behavior:",
                        "data_type_semantic:", "resolution_impact:")
        violations = []
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for col in enriched.columns:
                if col.description and YAML_DELIMITER in col.description:
                    prefix = col.description.split("---")[0]
                    for marker in yaml_markers:
                        if marker in prefix:
                            violations.append(
                                f"{schema_name}.{col.name}: prefix contains '{marker}'"
                            )

        assert not violations, (
            "Human-readable prefix contains YAML markers:\n"
            + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# SI-04: YAML block parses without error
# ---------------------------------------------------------------------------


class TestSI04YAMLParses:
    """SI-04: yaml.safe_load on the block after '---' succeeds for all."""

    def test_all_yaml_blocks_parse(self) -> None:
        """Every YAML block after the delimiter parses as a dict."""
        failures = []
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for col in enriched.columns:
                if col.description and YAML_DELIMITER in col.description:
                    parts = col.description.split("---", 1)
                    try:
                        parsed = yaml.safe_load(parts[1])
                    except yaml.YAMLError as exc:
                        failures.append(
                            f"{schema_name}.{col.name}: YAML parse error: {exc}"
                        )
                        continue

                    if not isinstance(parsed, dict):
                        failures.append(
                            f"{schema_name}.{col.name}: YAML parsed to "
                            f"{type(parsed).__name__}, expected dict"
                        )

        assert not failures, (
            "YAML parse failures:\n" + "\n".join(failures)
        )


# ---------------------------------------------------------------------------
# SI-05: Parsed YAML always has 'semantic' top-level key
# ---------------------------------------------------------------------------


class TestSI05SemanticTopLevelKey:
    """SI-05: Every parsed YAML annotation block has 'semantic' as root key."""

    def test_semantic_key_present(self) -> None:
        """All YAML blocks have exactly 'semantic' as the top-level key."""
        missing = []
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for col in enriched.columns:
                if col.description and YAML_DELIMITER in col.description:
                    parts = col.description.split("---", 1)
                    parsed = yaml.safe_load(parts[1])
                    if not isinstance(parsed, dict) or "semantic" not in parsed:
                        missing.append(f"{schema_name}.{col.name}")

        assert not missing, (
            f"YAML blocks missing 'semantic' top-level key: {missing}"
        )

    def test_semantic_key_is_a_dict(self) -> None:
        """The 'semantic' value is itself a dict (not a scalar or list)."""
        non_dict = []
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for col in enriched.columns:
                if col.description and YAML_DELIMITER in col.description:
                    parts = col.description.split("---", 1)
                    parsed = yaml.safe_load(parts[1])
                    if isinstance(parsed, dict):
                        sem_val = parsed.get("semantic")
                        if not isinstance(sem_val, dict):
                            non_dict.append(
                                f"{schema_name}.{col.name}: "
                                f"semantic value is {type(sem_val).__name__}"
                            )

        assert not non_dict, (
            "'semantic' value is not a dict:\n" + "\n".join(non_dict)
        )


# ---------------------------------------------------------------------------
# SI-06: Every cascade-sourced column has cascade_behavior in annotations
# ---------------------------------------------------------------------------


class TestSI06CascadeBehaviorPresence:
    """SI-06: Columns with source='cascade:...' must have cascade_behavior."""

    def test_cascade_columns_have_cascade_behavior(self) -> None:
        """Every cascade-sourced column's annotation includes cascade_behavior."""
        missing = []
        for schema_name, _cascade_field, col in _cascade_columns():
            key = f"{schema_name}.{col.name}"
            annotation = SEMANTIC_ANNOTATIONS.get(key)
            if annotation is None:
                missing.append(f"{key}: no annotation at all")
            elif "cascade_behavior" not in annotation:
                missing.append(f"{key}: annotation exists but no cascade_behavior")

        assert not missing, (
            "Cascade columns missing cascade_behavior:\n" + "\n".join(missing)
        )


# ---------------------------------------------------------------------------
# SI-07: cascade_behavior.source_entity matches cascading field registry
# ---------------------------------------------------------------------------


class TestSI07SourceEntityMatch:
    """SI-07: Annotation source_entity matches the runtime CascadingFieldDef owner."""

    def test_source_entity_matches_registry(self) -> None:
        """cascade_behavior.source_entity equals the owner class name from registry."""
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

            normalized = cascade_field.lower().strip()
            entry = cascade_registry.get(normalized)
            if entry is None:
                mismatches.append(
                    f"{key}: cascade field '{cascade_field}' not found in registry"
                )
                continue

            owner_class, _field_def = entry
            actual_source = owner_class.__name__

            if annotated_source != actual_source:
                mismatches.append(
                    f"{key}: annotation says source_entity={annotated_source!r}, "
                    f"registry says owner={actual_source!r}"
                )

        assert not mismatches, (
            "cascade_behavior.source_entity mismatches:\n" + "\n".join(mismatches)
        )


# ---------------------------------------------------------------------------
# SI-08: cascade_behavior.allow_override matches CascadingFieldDef
# ---------------------------------------------------------------------------


class TestSI08AllowOverrideMatch:
    """SI-08: Annotation allow_override matches CascadingFieldDef.allow_override."""

    def test_allow_override_matches_registry(self) -> None:
        """cascade_behavior.allow_override equals the CascadingFieldDef value."""
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
                    f"CascadingFieldDef says allow_override={field_def.allow_override}"
                )

        assert not mismatches, (
            "cascade_behavior.allow_override mismatches:\n" + "\n".join(mismatches)
        )


# ---------------------------------------------------------------------------
# SI-09: Key cascade columns have resolution_impact containing "CRITICAL"
# ---------------------------------------------------------------------------


class TestSI09CriticalResolutionImpact:
    """SI-09: office_phone and vertical annotations contain 'CRITICAL' in impact."""

    @pytest.mark.parametrize(
        "key",
        [
            "unit.office_phone",
            "offer.office_phone",
            "contact.office_phone",
            "asset_edit.office_phone",
            "asset_edit_holder.office_phone",
            "unit.vertical",
            "offer.vertical",
            "asset_edit.vertical",
        ],
    )
    def test_critical_impact_present(self, key: str) -> None:
        """Annotation resolution_impact contains 'CRITICAL' for key columns."""
        annotation = SEMANTIC_ANNOTATIONS.get(key)
        assert annotation is not None, f"Annotation {key} does not exist"
        impact = annotation.get("resolution_impact", "")
        assert "CRITICAL" in impact, (
            f"{key}: resolution_impact does not contain 'CRITICAL'. "
            f"Got: {impact!r}"
        )


# ---------------------------------------------------------------------------
# SI-10: semantic_type filter works
# ---------------------------------------------------------------------------


class TestSI10SemanticTypeFilter:
    """SI-10: get_semantic_type() returns correct types for annotated columns."""

    @pytest.mark.parametrize(
        ("schema_name", "col_name", "expected_type"),
        [
            ("unit", "office_phone", "phone"),
            ("offer", "office_phone", "phone"),
            ("offer", "vertical", "enum"),
            ("offer", "mrr", "currency"),
            ("offer", "platforms", "multi_enum"),
            ("offer", "language", "enum"),
            ("offer", "offer_id", "identifier"),
            ("unit", "office", "text"),
            ("offer", "cost", "currency"),
        ],
    )
    def test_semantic_type_extraction(
        self, schema_name: str, col_name: str, expected_type: str
    ) -> None:
        """get_semantic_type() returns the correct data_type_semantic."""
        col = _make_annotated_col(schema_name, col_name)
        enriched_desc = enrich_description(schema_name, col)
        result = get_semantic_type(enriched_desc)
        assert result == expected_type, (
            f"{schema_name}.{col_name}: expected semantic_type={expected_type!r}, "
            f"got {result!r}"
        )

    def test_unenriched_returns_none(self) -> None:
        """get_semantic_type on a plain description returns None."""
        assert get_semantic_type("Just a regular description") is None

    def test_none_returns_none(self) -> None:
        """get_semantic_type(None) returns None."""
        assert get_semantic_type(None) is None


# ---------------------------------------------------------------------------
# SI-11: include_enums parameter
# ---------------------------------------------------------------------------


class TestSI11IncludeEnums:
    """SI-11: include_enums query parameter for schema endpoints."""

    def test_include_enums_parameter_exists(self) -> None:
        """Schema endpoints should accept include_enums query parameter.

        When include_enums=true, enum-typed columns should include their
        valid_values list in the response.
        """
        from autom8_asana.api.routes.dataframes import router  # noqa: F401

        # Search for include_enums in the route signatures
        route_sources = []
        for route in router.routes:
            if hasattr(route, "endpoint"):
                import inspect

                sig = inspect.signature(route.endpoint)
                route_sources.append(str(sig))

        found = any("include_enums" in src for src in route_sources)
        assert found, "include_enums parameter not found in dataframes routes"


# ---------------------------------------------------------------------------
# SI-12: Enum detail endpoint
# ---------------------------------------------------------------------------


class TestSI12EnumDetailEndpoint:
    """SI-12: GET /v1/resolve/{entity_type}/schema/enums/{field_name} route."""

    def test_enum_detail_route_exists(self) -> None:
        """Resolver schema should expose an enums/{field_name} sub-route."""
        from autom8_asana.api.routes.resolver_schema import schema_router

        route_paths = []
        for route in schema_router.routes:
            if hasattr(route, "path"):
                route_paths.append(route.path)

        found = any("enums/" in path for path in route_paths)
        assert found, (
            "No enum detail route found matching pattern 'enums/{field_name}' "
            f"in resolver_schema routes. Found: {route_paths}"
        )


# ---------------------------------------------------------------------------
# SI-13: Enriched description preserved in schema dict
# ---------------------------------------------------------------------------


class TestSI13EnrichedInSchemaDict:
    """SI-13: to_dict() output preserves the enriched description text."""

    def test_to_dict_preserves_enriched_descriptions(self) -> None:
        """DataFrameSchema.to_dict() includes the full enriched description."""
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            d = enriched.to_dict()

            for col_dict in d["columns"]:
                col = enriched.get_column(col_dict["name"])
                assert col is not None, (
                    f"{schema_name}: column {col_dict['name']} missing from schema"
                )
                assert col_dict["description"] == col.description, (
                    f"{schema_name}.{col_dict['name']}: to_dict() description "
                    f"does not match the enriched ColumnDef description"
                )

    def test_yaml_survives_dict_roundtrip(self) -> None:
        """YAML annotation can be extracted from to_dict() output."""
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            d = enriched.to_dict()

            for col_dict in d["columns"]:
                desc = col_dict.get("description", "")
                if desc and YAML_DELIMITER in desc:
                    parts = desc.split("---", 1)
                    parsed = yaml.safe_load(parts[1])
                    assert isinstance(parsed, dict), (
                        f"{schema_name}.{col_dict['name']}: YAML from to_dict() "
                        f"output did not parse to dict"
                    )
                    assert "semantic" in parsed, (
                        f"{schema_name}.{col_dict['name']}: YAML from to_dict() "
                        f"output missing 'semantic' key"
                    )


# ---------------------------------------------------------------------------
# SI-14: Unannotated columns return plain descriptions
# ---------------------------------------------------------------------------


class TestSI14UnannotatedColumnsPlain:
    """SI-14: Columns NOT in SEMANTIC_ANNOTATIONS keep plain descriptions."""

    def test_unannotated_columns_unchanged_with_semantic_true(self) -> None:
        """Columns without annotations return their original description."""
        violations = []
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for orig_col, new_col in zip(schema.columns, enriched.columns):
                key = f"{schema_name}.{orig_col.name}"
                if key not in SEMANTIC_ANNOTATIONS:
                    if new_col.description != orig_col.description:
                        violations.append(
                            f"{key}: expected {orig_col.description!r}, "
                            f"got {new_col.description!r}"
                        )

        assert not violations, (
            "Unannotated columns were modified by enrichment:\n"
            + "\n".join(violations)
        )

    def test_unannotated_column_has_no_yaml_delimiter(self) -> None:
        """Unannotated columns must not have the YAML delimiter."""
        violations = []
        for schema_name, schema in _all_schemas().items():
            enriched = enrich_schema(schema, include_semantic=True)
            for col in enriched.columns:
                key = f"{schema_name}.{col.name}"
                if key not in SEMANTIC_ANNOTATIONS:
                    if col.description and YAML_DELIMITER in col.description:
                        violations.append(key)

        assert not violations, (
            f"Unannotated columns have YAML delimiter: {violations}"
        )


# ---------------------------------------------------------------------------
# SI-15: 12 cascade column-schema combinations annotated
# ---------------------------------------------------------------------------


class TestSI15CascadeAnnotationCount:
    """SI-15: Exactly 12 SEMANTIC_ANNOTATIONS entries have cascade_behavior."""

    def test_cascade_annotation_count_is_12(self) -> None:
        """Count of annotations with cascade_behavior must be exactly 12."""
        cascade_entries = [
            key
            for key, annotation in SEMANTIC_ANNOTATIONS.items()
            if "cascade_behavior" in annotation
        ]
        assert len(cascade_entries) == 12, (
            f"Expected exactly 12 cascade annotations, got {len(cascade_entries)}. "
            f"Entries: {sorted(cascade_entries)}"
        )


# ---------------------------------------------------------------------------
# SI-16: 7 HD-02 priority non-cascade fields annotated
# ---------------------------------------------------------------------------


class TestSI16HD02AnnotationCount:
    """SI-16: Exactly 7 SEMANTIC_ANNOTATIONS entries WITHOUT cascade_behavior."""

    def test_non_cascade_annotation_count_is_7(self) -> None:
        """Count of annotations without cascade_behavior must be exactly 7."""
        non_cascade_entries = [
            key
            for key, annotation in SEMANTIC_ANNOTATIONS.items()
            if "cascade_behavior" not in annotation
        ]
        assert len(non_cascade_entries) == 7, (
            f"Expected exactly 7 HD-02 non-cascade annotations, "
            f"got {len(non_cascade_entries)}. "
            f"Entries: {sorted(non_cascade_entries)}"
        )

    def test_total_is_19(self) -> None:
        """Total annotation count must be 12 + 7 = 19."""
        assert len(SEMANTIC_ANNOTATIONS) == 19, (
            f"Expected 19 total annotations (12 cascade + 7 HD-02), "
            f"got {len(SEMANTIC_ANNOTATIONS)}"
        )
