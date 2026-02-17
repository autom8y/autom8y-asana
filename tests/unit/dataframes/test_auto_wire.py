"""Tests for WS1-S2: Descriptor-driven auto-wiring of SchemaRegistry and extractor factory.

Verifies that SchemaRegistry._ensure_initialized() and _create_extractor()
produce identical results when driven by EntityDescriptor metadata instead
of hardcoded imports and match/case branches.
"""

from __future__ import annotations

import pytest

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.extractors.contact import ContactExtractor
from autom8_asana.dataframes.extractors.default import DefaultExtractor
from autom8_asana.dataframes.extractors.schema import SchemaExtractor
from autom8_asana.dataframes.extractors.unit import UnitExtractor
from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.dataframes.schemas import (
    BASE_SCHEMA,
    CONTACT_SCHEMA,
    UNIT_SCHEMA,
)

from .conftest import _TestBuilder


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset SchemaRegistry before each test for isolation."""
    SchemaRegistry.reset()
    yield
    SchemaRegistry.reset()


# =============================================================================
# SchemaRegistry Auto-Discovery Tests
# =============================================================================


class TestSchemaRegistryAutoWire:
    """Verify SchemaRegistry._ensure_initialized() discovers schemas from descriptors."""

    EXPECTED_TASK_TYPES = sorted([
        "Unit",
        "Contact",
        "Business",
        "Offer",
        "AssetEdit",
        "AssetEditHolder",
    ])

    def test_auto_discovered_task_types_match_expected(self) -> None:
        """SchemaRegistry must discover the exact set of schema-bearing entity types."""
        registry = SchemaRegistry.get_instance()
        actual = sorted(registry.list_task_types())
        assert actual == self.EXPECTED_TASK_TYPES

    def test_base_schema_still_registered_as_wildcard(self) -> None:
        """BASE_SCHEMA must remain at '*' key, not driven by descriptors."""
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema("*")
        assert schema.name == "base"
        assert schema.task_type == "*"

    def test_each_schema_resolves_to_correct_name(self) -> None:
        """Each auto-discovered schema's .name must match the entity's snake_case name."""
        registry = SchemaRegistry.get_instance()
        schemas = registry.get_all_schemas()

        expected_names = {
            "Unit": "unit",
            "Contact": "contact",
            "Business": "business",
            "Offer": "offer",
            "AssetEdit": "asset_edit",
            "AssetEditHolder": "asset_edit_holder",
        }
        for key, expected_name in expected_names.items():
            assert key in schemas, f"Missing schema for {key}"
            assert schemas[key].name == expected_name, (
                f"Schema for {key} has name {schemas[key].name!r}, "
                f"expected {expected_name!r}"
            )

    def test_descriptor_schema_key_matches_registry_key(self) -> None:
        """effective_schema_key on each descriptor must match the SchemaRegistry key."""
        from autom8_asana.core.entity_registry import get_registry

        entity_registry = get_registry()
        schema_registry = SchemaRegistry.get_instance()
        all_schemas = schema_registry.get_all_schemas()

        for desc in entity_registry.all_descriptors():
            if desc.schema_module_path:
                key = desc.effective_schema_key
                assert key in all_schemas, (
                    f"Descriptor {desc.name!r} has effective_schema_key={key!r} "
                    f"but no schema registered under that key"
                )

    def test_schemas_not_duplicated_with_runtime_register(self) -> None:
        """Auto-wired schemas must not interfere with runtime registration."""
        from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema

        registry = SchemaRegistry.get_instance()

        custom = DataFrameSchema(
            name="custom",
            task_type="CustomType",
            columns=[ColumnDef("gid", "Utf8", nullable=False)],
            version="1.0.0",
        )
        registry.register("CustomType", custom)

        # Custom schema accessible
        assert registry.has_schema("CustomType")
        # Auto-wired schemas still present
        assert sorted(registry.list_task_types()) == sorted(
            self.EXPECTED_TASK_TYPES + ["CustomType"]
        )


# =============================================================================
# Extractor Factory Auto-Wire Tests
# =============================================================================


class TestExtractorFactoryAutoWire:
    """Verify _create_extractor() resolves correct classes from descriptors."""

    def test_unit_extractor_resolved(self) -> None:
        """Unit task_type must resolve to UnitExtractor via descriptor."""
        builder = _TestBuilder(UNIT_SCHEMA)
        extractor = builder._create_extractor("Unit")
        assert isinstance(extractor, UnitExtractor)

    def test_contact_extractor_resolved(self) -> None:
        """Contact task_type must resolve to ContactExtractor via descriptor."""
        builder = _TestBuilder(CONTACT_SCHEMA)
        extractor = builder._create_extractor("Contact")
        assert isinstance(extractor, ContactExtractor)

    def test_wildcard_returns_default_extractor(self) -> None:
        """'*' task_type must always return DefaultExtractor (not descriptor-driven)."""
        builder = _TestBuilder(BASE_SCHEMA)
        extractor = builder._create_extractor("*")
        assert isinstance(extractor, DefaultExtractor)

    def test_unknown_type_with_base_schema_returns_default(self) -> None:
        """Unknown task_type with base-only columns falls back to DefaultExtractor."""
        builder = _TestBuilder(BASE_SCHEMA)
        extractor = builder._create_extractor("CompletelyUnknown")
        assert isinstance(extractor, DefaultExtractor)

    def test_known_type_without_extractor_path_uses_schema_extractor(self) -> None:
        """Offer has schema_module_path but no extractor_class_path.

        Since OFFER_SCHEMA has columns beyond BASE_COLUMNS, the fallback
        path should produce a SchemaExtractor, not a DefaultExtractor.
        """
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        builder = _TestBuilder(OFFER_SCHEMA)
        extractor = builder._create_extractor("Offer")
        assert isinstance(extractor, SchemaExtractor)

    def test_business_without_extractor_path_uses_schema_extractor(self) -> None:
        """Business has schema but no extractor_class_path -- SchemaExtractor fallback."""
        from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA

        builder = _TestBuilder(BUSINESS_SCHEMA)
        extractor = builder._create_extractor("Business")
        assert isinstance(extractor, SchemaExtractor)

    def test_all_descriptor_extractors_are_base_extractor_subclasses(self) -> None:
        """Every extractor_class_path in the registry must resolve to a BaseExtractor subclass."""
        from autom8_asana.core.entity_registry import _resolve_dotted_path, get_registry

        for desc in get_registry().all_descriptors():
            if desc.extractor_class_path:
                cls = _resolve_dotted_path(desc.extractor_class_path)
                assert issubclass(cls, BaseExtractor), (
                    f"Descriptor {desc.name!r}: extractor class {cls!r} "
                    f"is not a subclass of BaseExtractor"
                )

    def test_extractor_receives_schema_and_resolver(self) -> None:
        """Auto-wired extractor must receive schema and resolver from builder."""
        from unittest.mock import MagicMock

        resolver = MagicMock()
        builder = _TestBuilder(UNIT_SCHEMA)
        builder._resolver = resolver

        extractor = builder._create_extractor("Unit")

        assert isinstance(extractor, UnitExtractor)
        assert extractor._schema is UNIT_SCHEMA
        assert extractor._resolver is resolver
