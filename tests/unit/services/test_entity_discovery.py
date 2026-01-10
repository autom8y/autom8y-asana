"""Unit tests for schema-driven entity discovery.

Per TDD-DYNAMIC-RESOLVER-001 / FR-001, FR-002:
Tests dynamic entity discovery from SchemaRegistry + EntityProjectRegistry,
and schema-aware criterion validation.

TASK-004: Schema-Driven Entity Discovery
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from autom8_asana.services.resolver import (
    CriterionValidationResult,
    EntityProjectRegistry,
    ENTITY_ALIASES,
    _apply_legacy_mapping,
    _validate_field_type,
    get_resolvable_entities,
    is_entity_resolvable,
    validate_criterion_for_entity,
)


class TestGetResolvableEntities:
    """Tests for get_resolvable_entities() function."""

    def test_returns_intersection_of_schema_and_project(self) -> None:
        """Discovery returns entities with both schema AND project."""
        # Mock SchemaRegistry with Unit, Contact, Offer schemas
        mock_schema_registry = MagicMock()
        mock_schema_registry.list_task_types.return_value = ["Unit", "Contact", "Offer"]

        # Mock EntityProjectRegistry with only unit and contact registered
        mock_project_registry = MagicMock()
        mock_project_registry.get_project_gid.side_effect = lambda x: {
            "unit": "project-1",
            "contact": "project-2",
            # "offer" not registered - returns None
        }.get(x)

        result = get_resolvable_entities(
            schema_registry=mock_schema_registry,
            project_registry=mock_project_registry,
        )

        # Only unit and contact have both schema AND project
        assert result == {"unit", "contact"}
        assert "offer" not in result

    def test_returns_empty_set_when_no_schemas(self) -> None:
        """Discovery returns empty set when no schemas registered."""
        mock_schema_registry = MagicMock()
        mock_schema_registry.list_task_types.return_value = []

        mock_project_registry = MagicMock()

        result = get_resolvable_entities(
            schema_registry=mock_schema_registry,
            project_registry=mock_project_registry,
        )

        assert result == set()

    def test_returns_empty_set_when_no_projects(self) -> None:
        """Discovery returns empty set when no projects registered."""
        mock_schema_registry = MagicMock()
        mock_schema_registry.list_task_types.return_value = ["Unit", "Contact"]

        mock_project_registry = MagicMock()
        mock_project_registry.get_project_gid.return_value = None

        result = get_resolvable_entities(
            schema_registry=mock_schema_registry,
            project_registry=mock_project_registry,
        )

        assert result == set()

    def test_lowercases_task_types(self) -> None:
        """Discovery lowercases task types from SchemaRegistry."""
        mock_schema_registry = MagicMock()
        mock_schema_registry.list_task_types.return_value = ["Unit", "CONTACT", "Offer"]

        mock_project_registry = MagicMock()
        mock_project_registry.get_project_gid.side_effect = lambda x: {
            "unit": "project-1",
            "contact": "project-2",
            "offer": "project-3",
        }.get(x)

        result = get_resolvable_entities(
            schema_registry=mock_schema_registry,
            project_registry=mock_project_registry,
        )

        # All should be lowercase
        assert "unit" in result
        assert "contact" in result
        assert "offer" in result
        assert "Unit" not in result
        assert "CONTACT" not in result

    def test_uses_singleton_registries_when_not_provided(self) -> None:
        """Discovery uses singleton instances when registries not provided."""
        # Reset singletons for clean test
        EntityProjectRegistry.reset()

        # Register a project in the singleton
        registry = EntityProjectRegistry.get_instance()
        registry.register(
            entity_type="unit",
            project_gid="test-project",
            project_name="Test Project",
        )

        # Call without providing registries - should use singletons
        result = get_resolvable_entities()

        # Should find unit (has schema in SchemaRegistry and project we registered)
        assert "unit" in result

        # Cleanup
        EntityProjectRegistry.reset()


class TestIsEntityResolvable:
    """Tests for is_entity_resolvable() helper function."""

    def test_returns_true_for_resolvable_entity(self) -> None:
        """Returns True for entity in resolvable set."""
        with patch(
            "autom8_asana.services.resolver.get_resolvable_entities"
        ) as mock_get:
            mock_get.return_value = {"unit", "contact"}

            assert is_entity_resolvable("unit") is True
            assert is_entity_resolvable("contact") is True

    def test_returns_false_for_non_resolvable_entity(self) -> None:
        """Returns False for entity not in resolvable set."""
        with patch(
            "autom8_asana.services.resolver.get_resolvable_entities"
        ) as mock_get:
            mock_get.return_value = {"unit"}

            assert is_entity_resolvable("unknown") is False
            assert is_entity_resolvable("offer") is False

    def test_lowercases_entity_type(self) -> None:
        """Lowercases entity type before checking."""
        with patch(
            "autom8_asana.services.resolver.get_resolvable_entities"
        ) as mock_get:
            mock_get.return_value = {"unit"}

            assert is_entity_resolvable("UNIT") is True
            assert is_entity_resolvable("Unit") is True
            assert is_entity_resolvable("unit") is True


class TestValidateCriterionForEntity:
    """Tests for validate_criterion_for_entity() function."""

    def test_valid_criterion_with_schema_fields(self) -> None:
        """Validation passes for valid schema column fields."""
        # Unit schema has office_phone and vertical columns
        result = validate_criterion_for_entity(
            "unit",
            {"office_phone": "+15551234567", "vertical": "dental"},
        )

        assert result.is_valid is True
        assert result.errors == []
        assert result.unknown_fields == []
        assert "office_phone" in result.available_fields
        assert "vertical" in result.available_fields

    def test_valid_criterion_with_legacy_mapping(self) -> None:
        """Legacy fields are mapped and then validated."""
        # "phone" should map to "office_phone" for unit
        result = validate_criterion_for_entity(
            "unit",
            {"phone": "+15551234567", "vertical": "dental"},
        )

        assert result.is_valid is True
        assert result.normalized_criterion["office_phone"] == "+15551234567"
        assert result.normalized_criterion["vertical"] == "dental"
        assert "phone" not in result.normalized_criterion

    def test_invalid_criterion_unknown_field(self) -> None:
        """Validation fails for unknown fields."""
        result = validate_criterion_for_entity(
            "unit",
            {"unknown_field": "value"},
        )

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "unknown_field" in result.unknown_fields
        assert "Unknown field(s)" in result.errors[0]
        # Error message should list available fields
        assert "Valid fields:" in result.errors[0]

    def test_error_message_contains_available_fields(self) -> None:
        """Error message includes list of available fields."""
        result = validate_criterion_for_entity(
            "unit",
            {"bad_field": "value"},
        )

        assert result.is_valid is False
        # The error message should mention available fields
        error_msg = result.errors[0]
        assert "Valid fields:" in error_msg
        # Available fields list should be populated
        assert len(result.available_fields) > 0

    def test_empty_criterion_is_valid(self) -> None:
        """Empty criterion dict is valid (returns empty results)."""
        result = validate_criterion_for_entity("unit", {})

        assert result.is_valid is True
        assert result.errors == []
        assert result.unknown_fields == []
        assert result.normalized_criterion == {}

    def test_multiple_unknown_fields(self) -> None:
        """Multiple unknown fields are all reported."""
        result = validate_criterion_for_entity(
            "unit",
            {"bad_field_1": "value", "bad_field_2": "value"},
        )

        assert result.is_valid is False
        assert "bad_field_1" in result.unknown_fields
        assert "bad_field_2" in result.unknown_fields

    def test_falls_back_to_base_schema(self) -> None:
        """Falls back to base schema if entity-specific not found."""
        # Use an entity type that doesn't have a specific schema
        result = validate_criterion_for_entity(
            "unknown_entity",
            {"gid": "12345"},  # gid is in base schema
        )

        # Should validate against base schema - gid is always valid
        assert result.is_valid is True


class TestApplyLegacyMapping:
    """Tests for _apply_legacy_mapping() helper function."""

    def test_maps_phone_to_office_phone_for_unit(self) -> None:
        """Maps 'phone' to 'office_phone' for unit entity."""
        result = _apply_legacy_mapping(
            "unit",
            {"phone": "+15551234567", "vertical": "dental"},
        )

        assert result["office_phone"] == "+15551234567"
        assert result["vertical"] == "dental"
        assert "phone" not in result

    def test_maps_phone_to_office_phone_for_business(self) -> None:
        """Maps 'phone' to 'office_phone' for business entity."""
        result = _apply_legacy_mapping(
            "business",
            {"phone": "+15551234567"},
        )

        assert result["office_phone"] == "+15551234567"
        assert "phone" not in result

    def test_maps_contact_fields(self) -> None:
        """Maps contact short field names to schema column names.

        Per TDD-dynamic-field-normalization:
        Short names like 'email' expand to prefixed schema columns like 'contact_email'.
        """
        result = _apply_legacy_mapping(
            "contact",
            {"email": "test@example.com", "phone": "+15551234567"},
        )

        assert result["contact_email"] == "test@example.com"
        assert result["contact_phone"] == "+15551234567"
        assert "email" not in result
        assert "phone" not in result

    def test_unmapped_fields_pass_through(self) -> None:
        """Fields without mappings pass through unchanged."""
        result = _apply_legacy_mapping(
            "unit",
            {"vertical": "dental", "gid": "12345"},
        )

        assert result["vertical"] == "dental"
        assert result["gid"] == "12345"

    def test_unknown_entity_type_no_mapping(self) -> None:
        """Unknown entity types have no mapping applied."""
        result = _apply_legacy_mapping(
            "unknown_entity",
            {"phone": "+15551234567"},
        )

        # No mapping for unknown entity - field passes through
        assert result["phone"] == "+15551234567"

    def test_entity_mapping_overrides_global(self) -> None:
        """Entity-specific mappings take precedence over global."""
        # If we had a global mapping and entity-specific, entity wins
        result = _apply_legacy_mapping(
            "unit",
            {"phone": "+15551234567"},
        )

        # Unit-specific mapping: phone -> office_phone
        assert result["office_phone"] == "+15551234567"


class TestValidateFieldType:
    """Tests for _validate_field_type() helper function."""

    def test_string_types_accept_anything(self) -> None:
        """String dtypes accept any value."""
        assert _validate_field_type("field", "string value", "Utf8") is None
        assert _validate_field_type("field", 123, "Utf8") is None
        assert _validate_field_type("field", None, "String") is None

    def test_integer_type_accepts_int(self) -> None:
        """Integer dtypes accept integer values."""
        assert _validate_field_type("field", 123, "Int64") is None
        assert _validate_field_type("field", "456", "Int64") is None
        assert _validate_field_type("field", -789, "Int32") is None

    def test_integer_type_rejects_non_numeric(self) -> None:
        """Integer dtypes reject non-numeric strings."""
        error = _validate_field_type("field", "not a number", "Int64")

        assert error is not None
        assert "expects integer" in error

    def test_float_type_accepts_numbers(self) -> None:
        """Float dtypes accept numeric values."""
        assert _validate_field_type("field", 3.14, "Float64") is None
        assert _validate_field_type("field", 123, "Float64") is None
        assert _validate_field_type("field", "3.14", "Decimal") is None

    def test_float_type_rejects_non_numeric(self) -> None:
        """Float dtypes reject non-numeric strings."""
        error = _validate_field_type("field", "not a number", "Float64")

        assert error is not None
        assert "expects number" in error

    def test_boolean_type_accepts_booleans(self) -> None:
        """Boolean dtype accepts boolean values."""
        assert _validate_field_type("field", True, "Boolean") is None
        assert _validate_field_type("field", False, "Boolean") is None

    def test_boolean_type_accepts_string_booleans(self) -> None:
        """Boolean dtype accepts string representations."""
        assert _validate_field_type("field", "true", "Boolean") is None
        assert _validate_field_type("field", "false", "Boolean") is None
        assert _validate_field_type("field", "TRUE", "Boolean") is None
        assert _validate_field_type("field", "1", "Boolean") is None
        assert _validate_field_type("field", "0", "Boolean") is None

    def test_boolean_type_rejects_invalid(self) -> None:
        """Boolean dtype rejects invalid values."""
        error = _validate_field_type("field", "maybe", "Boolean")

        assert error is not None
        assert "expects boolean" in error

    def test_unknown_dtype_is_permissive(self) -> None:
        """Unknown dtypes are permissive (accept anything)."""
        assert _validate_field_type("field", "anything", "UnknownType") is None
        assert _validate_field_type("field", 123, "CustomType") is None


class TestEntityAliasesConstant:
    """Tests for ENTITY_ALIASES constant structure.

    Per TDD-dynamic-field-normalization:
    ENTITY_ALIASES encodes the semantic domain hierarchy for field resolution.
    """

    def test_has_unit_alias(self) -> None:
        """Unit aliases to business_unit for chain resolution."""
        assert "unit" in ENTITY_ALIASES
        assert "business_unit" in ENTITY_ALIASES["unit"]

    def test_has_offer_alias(self) -> None:
        """Offer aliases to business_offer for chain resolution."""
        assert "offer" in ENTITY_ALIASES
        assert "business_offer" in ENTITY_ALIASES["offer"]

    def test_has_business_alias(self) -> None:
        """Business aliases to office for prefix resolution."""
        assert "business" in ENTITY_ALIASES
        assert "office" in ENTITY_ALIASES["business"]

    def test_has_contact_empty_alias(self) -> None:
        """Contact has empty aliases (uses its own prefix)."""
        assert "contact" in ENTITY_ALIASES
        assert ENTITY_ALIASES["contact"] == []

    def test_alias_values_are_lists(self) -> None:
        """All alias values are lists (not dicts or strings)."""
        for entity_type, aliases in ENTITY_ALIASES.items():
            assert isinstance(aliases, list), f"{entity_type} aliases should be a list"


class TestCriterionValidationResultDataclass:
    """Tests for CriterionValidationResult dataclass."""

    def test_is_valid_true_when_no_errors(self) -> None:
        """is_valid is True when errors list is empty."""
        result = CriterionValidationResult(
            is_valid=True,
            errors=[],
            unknown_fields=[],
            available_fields=["gid", "name"],
            normalized_criterion={"gid": "123"},
        )

        assert result.is_valid is True

    def test_is_valid_false_when_errors(self) -> None:
        """is_valid is False when errors list is non-empty."""
        result = CriterionValidationResult(
            is_valid=False,
            errors=["Unknown field: bad_field"],
            unknown_fields=["bad_field"],
            available_fields=["gid", "name"],
            normalized_criterion={"bad_field": "value"},
        )

        assert result.is_valid is False

    def test_contains_all_expected_fields(self) -> None:
        """Result contains all expected fields."""
        result = CriterionValidationResult(
            is_valid=True,
            errors=[],
            unknown_fields=[],
            available_fields=["gid", "name", "office_phone"],
            normalized_criterion={"office_phone": "+15551234567"},
        )

        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "unknown_fields")
        assert hasattr(result, "available_fields")
        assert hasattr(result, "normalized_criterion")


class TestIntegrationWithSchemaRegistry:
    """Integration tests verifying behavior with actual SchemaRegistry."""

    def test_discovery_with_registered_unit(self) -> None:
        """Integration: Discovery finds unit when both registries have it."""
        # Reset to ensure clean state
        EntityProjectRegistry.reset()

        # Register unit project
        registry = EntityProjectRegistry.get_instance()
        registry.register(
            entity_type="unit",
            project_gid="test-unit-project",
            project_name="Unit Project",
        )

        # SchemaRegistry already has Unit schema loaded
        result = get_resolvable_entities()

        assert "unit" in result

        # Cleanup
        EntityProjectRegistry.reset()

    def test_validation_uses_actual_schema_columns(self) -> None:
        """Integration: Validation checks actual schema columns."""
        # This test verifies that validation uses the real Unit schema
        result = validate_criterion_for_entity(
            "unit",
            {"office_phone": "+15551234567", "vertical": "dental"},
        )

        # office_phone and vertical should be in Unit schema
        assert result.is_valid is True
        assert "office_phone" in result.available_fields
        assert "vertical" in result.available_fields

    def test_validation_rejects_non_schema_fields(self) -> None:
        """Integration: Validation rejects fields not in schema."""
        result = validate_criterion_for_entity(
            "unit",
            {"not_a_real_field": "value"},
        )

        assert result.is_valid is False
        assert "not_a_real_field" in result.unknown_fields
