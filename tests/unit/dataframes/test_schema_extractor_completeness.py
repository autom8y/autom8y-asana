"""Parametrized completeness test for schema-extractor-row triad.

Per TDD-ENTITY-EXT-001 US-6: Iterates all registered schemas and verifies
each can produce a DataFrame row without crashing. This test would have
caught bugs B1-B4 (schema registered without capable extractor) and
prevents all future instances of this class of wiring gap.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from autom8_asana.dataframes.extractors.default import DefaultExtractor
from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS
from tests.unit.dataframes.conftest import _TestBuilder, make_mock_task


def _get_base_column_names() -> set[str]:
    """Return the set of base 12 column names."""
    return {c.name for c in BASE_COLUMNS}


@pytest.fixture
def schema_registry() -> SchemaRegistry:
    """Get an initialized SchemaRegistry."""
    return SchemaRegistry.get_instance()


class TestSchemaExtractorCompleteness:
    """Verify every registered schema can produce a row without crashing."""

    def test_all_schemas_have_capable_extractors(
        self, schema_registry: SchemaRegistry
    ) -> None:
        """AC-6.1 through AC-6.4: Every schema type can extract without crash.

        Parametrized dynamically over SchemaRegistry.list_task_types() so
        adding a new schema automatically includes it with zero test code
        changes.
        """
        base_col_names = _get_base_column_names()
        task_types = schema_registry.list_task_types()

        # Sanity: we expect at least 6 non-wildcard schemas
        assert len(task_types) >= 6, (
            f"Expected at least 6 registered schemas, got {len(task_types)}: "
            f"{task_types}"
        )

        for task_type in task_types:
            schema = schema_registry.get_schema(task_type)
            schema_col_names = set(schema.column_names())
            extra_columns = schema_col_names - base_col_names

            # Create a concrete builder subclass for testing
            builder = _TestBuilder(schema)
            extractor = builder._create_extractor(task_type)

            # AC-6.3: Schemas with extra columns must NOT use DefaultExtractor
            if extra_columns:
                assert not isinstance(extractor, DefaultExtractor), (
                    f"{task_type} has {len(extra_columns)} extra columns "
                    f"({', '.join(sorted(extra_columns))}) but falls through "
                    f"to DefaultExtractor, which will crash on "
                    f"TaskRow(extra='forbid')"
                )

            # AC-6.2: Extractor can create a row without crash
            mock_task = make_mock_task()
            row = extractor.extract(mock_task)
            assert row is not None, f"{task_type}: extract() returned None"

            # Verify row has all schema columns
            row_dict = row.to_dict()
            for col_name in schema.column_names():
                assert col_name in row_dict, (
                    f"{task_type}: column {col_name!r} missing from "
                    f"extracted row"
                )


class TestImportTimeValidation:
    """Verify import-time validation warnings for generic extractors."""

    def test_warning_emitted_for_generic_extractors(self) -> None:
        """AC-7.1, AC-7.2: Warning emitted for schemas using SchemaExtractor."""
        from unittest.mock import patch

        warnings_emitted: list[dict] = []

        mock_logger = MagicMock()

        def capture_warning(event: str, **kwargs: object) -> None:
            extra = kwargs.get("extra", {})
            warnings_emitted.append({"event": event, "extra": extra})

        mock_logger.warning = capture_warning

        registry = SchemaRegistry.get_instance()
        # Force re-initialization to trigger validation
        registry._initialized = False
        registry._schemas = {}

        # Patch get_logger where it is imported (autom8y_log.get_logger)
        with patch("autom8y_log.get_logger", return_value=mock_logger):
            registry._ensure_initialized()

        # Should have warnings for Offer, Business, AssetEdit, AssetEditHolder
        generic_warnings = [
            w for w in warnings_emitted
            if w["event"] == "schema_using_generic_extractor"
        ]
        warned_entities = {
            w["extra"]["entity"] for w in generic_warnings
        }
        expected_warned = {"Offer", "Business", "AssetEdit", "AssetEditHolder"}
        assert warned_entities == expected_warned, (
            f"Expected warnings for {expected_warned}, got {warned_entities}"
        )

    def test_no_warning_for_dedicated_extractors(self) -> None:
        """AC-7.4: No warning for Unit and Contact."""
        from unittest.mock import patch

        warnings_emitted: list[dict] = []

        mock_logger = MagicMock()

        def capture_warning(event: str, **kwargs: object) -> None:
            extra = kwargs.get("extra", {})
            warnings_emitted.append({"event": event, "extra": extra})

        mock_logger.warning = capture_warning

        registry = SchemaRegistry.get_instance()
        registry._initialized = False
        registry._schemas = {}

        with patch("autom8y_log.get_logger", return_value=mock_logger):
            registry._ensure_initialized()

        # No warnings should mention Unit or Contact
        generic_warnings = [
            w for w in warnings_emitted
            if w["event"] == "schema_using_generic_extractor"
        ]
        for w in generic_warnings:
            entity = w["extra"].get("entity", "")
            assert entity not in ("Unit", "Contact", "*"), (
                f"Unexpected warning for {entity}"
            )

    def test_validation_failure_does_not_crash_startup(self) -> None:
        """R1.1: Validation failure must not crash startup."""
        from unittest.mock import patch

        registry = SchemaRegistry.get_instance()
        registry._initialized = False
        registry._schemas = {}

        # Make _validate_extractor_coverage raise an exception
        with patch.object(
            SchemaRegistry,
            "_validate_extractor_coverage",
            side_effect=RuntimeError("simulated validation failure"),
        ):
            # This should NOT raise -- the try/except in _ensure_initialized catches it
            registry._ensure_initialized()

        # Registry should still be initialized
        assert registry._initialized is True
        assert len(registry._schemas) >= 6


class TestSchemaAudit:
    """Verify the schema inventory matches expectations."""

    def test_known_schema_inventory(self, schema_registry: SchemaRegistry) -> None:
        """FR-14: All schemas are accounted for."""
        task_types = set(schema_registry.list_task_types())
        expected = {
            "Unit",
            "Contact",
            "Offer",
            "Business",
            "AssetEdit",
            "AssetEditHolder",
        }
        assert task_types == expected, (
            f"Schema inventory mismatch. "
            f"Extra: {task_types - expected}. "
            f"Missing: {expected - task_types}"
        )

    def test_wildcard_base_schema_exists(
        self, schema_registry: SchemaRegistry
    ) -> None:
        """The '*' base schema must always be registered."""
        schema = schema_registry.get_schema("*")
        assert schema.task_type == "*"
        assert len(schema.columns) == 12
