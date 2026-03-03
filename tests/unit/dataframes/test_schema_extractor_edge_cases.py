"""Adversarial tests for SchemaExtractor edge cases.

Per QA Adversary Category 3: Tests designed to break SchemaExtractor
with unusual inputs, boundary conditions, and concurrent access.
"""

from __future__ import annotations

import threading
from typing import Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.dataframes.extractors.default import DefaultExtractor
from autom8_asana.dataframes.extractors.schema import (
    _MODEL_CACHE,
    _MODEL_CACHE_LOCK,
    DTYPE_MAP,
    SchemaExtractor,
)
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.models.task_row import TaskRow
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS, BASE_SCHEMA
from tests.unit.dataframes.conftest import _TestBuilder, make_mock_task


def _make_schema(
    name: str,
    task_type: str,
    extra_columns: list[ColumnDef] | None = None,
) -> DataFrameSchema:
    """Create a test schema with optional extra columns beyond base 13."""
    cols = list(BASE_COLUMNS)
    if extra_columns:
        cols.extend(extra_columns)
    return DataFrameSchema(
        name=name,
        task_type=task_type,
        columns=cols,
        version="1.0.0",
    )


class TestSchemaWithZeroExtraColumns:
    """Schema with 0 extra columns should NOT trigger SchemaExtractor."""

    def test_base_only_schema_uses_default_extractor(self) -> None:
        """A schema with only the base 13 columns should use DefaultExtractor,
        not SchemaExtractor, when passed to _create_extractor via the fallback."""
        schema = _make_schema("test_base_only", "TestBaseOnly")
        builder = _TestBuilder(schema)
        extractor = builder._create_extractor("TestBaseOnly")
        assert isinstance(extractor, DefaultExtractor), (
            f"Expected DefaultExtractor for base-only schema, got {type(extractor).__name__}"
        )

    def test_base_only_schema_extraction_works(self) -> None:
        """Extraction with DefaultExtractor on base-only schema succeeds."""
        from autom8_asana.dataframes.extractors.default import DefaultExtractor

        extractor = DefaultExtractor(BASE_SCHEMA)
        task = make_mock_task()
        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        assert len(d) == 13


class TestSchemaAllNullableColumns:
    """Schema where ALL extra columns are nullable."""

    def test_all_nullable_schema_extracts_without_crash(self) -> None:
        """All-nullable columns should extract cleanly with None values."""
        extra_cols = [
            ColumnDef(
                name="nullable_str",
                dtype="Utf8",
                nullable=True,
                source="cf:Nullable Str",
            ),
            ColumnDef(
                name="nullable_int",
                dtype="Int64",
                nullable=True,
                source="cf:Nullable Int",
            ),
            ColumnDef(
                name="nullable_bool",
                dtype="Boolean",
                nullable=True,
                source="cf:Nullable Bool",
            ),
        ]
        schema = _make_schema("all_nullable", "AllNullable", extra_cols)
        extractor = SchemaExtractor(schema)
        task = make_mock_task()
        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        assert d["nullable_str"] is None
        assert d["nullable_int"] is None
        assert d["nullable_bool"] is None


class TestSchemaAllNonNullableColumns:
    """Schema where ALL extra columns are non-nullable.

    With no resolver providing values, these will be None from extraction
    but should not crash (Pydantic validation may raise if strict).
    """

    def test_non_nullable_columns_with_none_values(self) -> None:
        """Non-nullable columns that extract to None should not crash.

        The SchemaExtractor generates models with Optional types (python_type | None)
        and default None, so even non-nullable schema columns will accept None values
        in the dynamic model. The nullable flag is a schema-level hint for Polars
        column construction, not a Pydantic validation constraint.
        """
        extra_cols = [
            ColumnDef(
                name="required_str",
                dtype="Utf8",
                nullable=False,
                source="cf:Required Str",
            ),
            ColumnDef(
                name="required_int",
                dtype="Int64",
                nullable=False,
                source="cf:Required Int",
            ),
        ]
        schema = _make_schema("all_required", "AllRequired", extra_cols)
        extractor = SchemaExtractor(schema)
        task = make_mock_task()
        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        # Values will be None because resolver is not configured -- no crash
        assert d["required_str"] is None
        assert d["required_int"] is None


class TestSchemaEveryDtype:
    """Schema with every dtype in DTYPE_MAP."""

    def test_every_known_dtype_extracts_without_crash(self) -> None:
        """One column per dtype in DTYPE_MAP should all extract cleanly."""
        extra_cols = []
        for i, (dtype_name, (py_type, default)) in enumerate(DTYPE_MAP.items()):
            col_name = f"col_{dtype_name.lower().replace('[', '_').replace(']', '')}"
            extra_cols.append(
                ColumnDef(
                    name=col_name,
                    dtype=dtype_name,
                    nullable=True,
                    source=f"cf:TestField{i}",
                )
            )

        schema = _make_schema("every_dtype", "EveryDtype", extra_cols)
        extractor = SchemaExtractor(schema)
        task = make_mock_task()
        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        # All extra columns should be present in the row dict
        for col in extra_cols:
            assert col.name in d, f"Column {col.name!r} missing from row"


class TestSchemaUnknownDtype:
    """Schema with an unknown/unusual dtype string."""

    def test_unknown_dtype_falls_back_to_str(self) -> None:
        """An unrecognized dtype string should fall back to (str, None).

        DTYPE_MAP.get(col.dtype, (str, None)) provides this fallback.
        """
        extra_cols = [
            ColumnDef(
                name="exotic_field",
                dtype="Duration",  # Not in DTYPE_MAP
                nullable=True,
                source="cf:Exotic",
            ),
        ]
        schema = _make_schema("unknown_dtype", "UnknownDtype", extra_cols)
        extractor = SchemaExtractor(schema)

        # Verify the model can be built without crash
        _MODEL_CACHE.pop("UnknownDtype", None)  # Clear cache for this type
        model = extractor._build_dynamic_row_model()
        assert model is not None

        # Verify the field exists and accepts None
        task = make_mock_task()
        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        assert d["exotic_field"] is None


class TestEmptyTaskData:
    """Tasks where all fields are None or empty."""

    def test_task_with_all_none_attributes_raises_validation_error(self) -> None:
        """A task with None for ALL attributes raises Pydantic ValidationError.

        This is EXPECTED BEHAVIOR: TaskRow enforces non-nullable on gid, name,
        created, last_modified. A task with None GID is structurally invalid and
        should be rejected by Pydantic validation. This behavior is identical
        across all extractors (Unit, Contact, Default, Schema) -- it is not a
        SchemaExtractor-specific issue.

        The BaseExtractor's BROAD-CATCH in extract() catches per-column errors
        and sets them to None, but Pydantic model_validate() rightfully rejects
        a row where required base fields are None.
        """
        from pydantic import ValidationError

        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        extractor = SchemaExtractor(OFFER_SCHEMA)
        task = MagicMock()
        task.gid = None
        task.name = None
        task.resource_subtype = None
        task.created_at = None
        task.due_on = None
        task.completed = None
        task.completed_at = None
        task.modified_at = None
        task.tags = None
        task.memberships = None
        task.custom_fields = []

        with pytest.raises(ValidationError) as exc_info:
            extractor.extract(task)
        # Should fail on non-nullable base fields
        errors = exc_info.value.errors()
        error_fields = {e["loc"][0] for e in errors}
        assert "gid" in error_fields
        assert "name" in error_fields

    def test_task_with_empty_string_gid(self) -> None:
        """Task with empty string GID should extract without crash."""
        from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA

        extractor = SchemaExtractor(BUSINESS_SCHEMA)
        task = make_mock_task()
        task.gid = ""
        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        assert d["gid"] == ""


class TestExtraFieldsNotInSchema:
    """Tasks with fields that are not in the schema definition."""

    def test_extra_task_attributes_are_ignored(self) -> None:
        """Extra attributes on the task object should not cause errors.

        BaseExtractor only accesses columns defined in the schema.
        Extra attributes on the mock task are simply ignored.
        """
        from autom8_asana.dataframes.schemas.asset_edit_holder import (
            ASSET_EDIT_HOLDER_SCHEMA,
        )

        extractor = SchemaExtractor(ASSET_EDIT_HOLDER_SCHEMA)
        task = make_mock_task()
        # Add extra attributes not in any schema
        task.some_random_field = "random_value"
        task.another_extra = 42
        task.deeply_nested = {"a": {"b": "c"}}

        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        # Extra task attributes should NOT appear in the row
        assert "some_random_field" not in d
        assert "another_extra" not in d
        assert "deeply_nested" not in d


class TestConcurrentExtraction:
    """Thread safety of _MODEL_CACHE and concurrent extraction."""

    def test_concurrent_model_building_produces_single_model(self) -> None:
        """Multiple threads building the same model should produce exactly one."""
        # Clear cache for this test
        test_type = "ConcurrentTest"
        _MODEL_CACHE.pop(test_type, None)

        extra_cols = [
            ColumnDef(
                name="concurrent_field", dtype="Utf8", nullable=True, source="cf:CF1"
            ),
        ]
        schema = _make_schema("concurrent", test_type, extra_cols)

        models: list[type[TaskRow]] = []
        errors: list[Exception] = []

        def build_model() -> None:
            try:
                ext = SchemaExtractor(schema)
                model = ext._build_dynamic_row_model()
                models.append(model)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=build_model) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Thread errors: {errors}"
        assert len(models) == 10, f"Expected 10 results, got {len(models)}"
        # All should be the same cached model
        first = models[0]
        for m in models[1:]:
            assert m is first, (
                "Concurrent model building produced different model instances"
            )

    def test_concurrent_extraction_from_multiple_schemas(self) -> None:
        """Multiple threads extracting from different schemas simultaneously."""
        from autom8_asana.dataframes.schemas.asset_edit import ASSET_EDIT_SCHEMA
        from autom8_asana.dataframes.schemas.asset_edit_holder import (
            ASSET_EDIT_HOLDER_SCHEMA,
        )
        from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        schemas = [
            OFFER_SCHEMA,
            ASSET_EDIT_SCHEMA,
            BUSINESS_SCHEMA,
            ASSET_EDIT_HOLDER_SCHEMA,
        ]
        results: list[tuple[str, bool]] = []
        errors: list[tuple[str, Exception]] = []

        def extract_schema(schema: DataFrameSchema) -> None:
            try:
                ext = SchemaExtractor(schema)
                task = make_mock_task()
                row = ext.extract(task)
                d = row.to_dict()
                results.append((schema.task_type, len(d) == len(schema.columns)))
            except Exception as e:
                errors.append((schema.task_type, e))

        threads = []
        for schema in schemas:
            for _ in range(3):  # 3 threads per schema = 12 threads total
                t = threading.Thread(target=extract_schema, args=(schema,))
                threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"
        assert len(results) == 12, f"Expected 12 results, got {len(results)}"
        for task_type, column_match in results:
            assert column_match, f"{task_type}: column count mismatch"


class TestDynamicModelProperties:
    """Verify properties of the dynamically generated Pydantic model."""

    def test_dynamic_model_inherits_from_task_row(self) -> None:
        """The dynamic model must be a TaskRow subclass."""
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        ext = SchemaExtractor(OFFER_SCHEMA)
        model = ext._build_dynamic_row_model()
        assert issubclass(model, TaskRow)

    def test_dynamic_model_has_extra_ignore(self) -> None:
        """The dynamic model must have extra='ignore' to accept unexpected fields."""
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        ext = SchemaExtractor(OFFER_SCHEMA)
        model = ext._build_dynamic_row_model()
        assert model.model_config.get("extra") == "ignore"

    def test_dynamic_model_has_strict_false(self) -> None:
        """The dynamic model must have strict=False for type coercion."""
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        ext = SchemaExtractor(OFFER_SCHEMA)
        model = ext._build_dynamic_row_model()
        assert model.model_config.get("strict") is False

    def test_dynamic_model_name_format(self) -> None:
        """Dynamic model names should follow {TaskType}SchemaRow pattern."""
        from autom8_asana.dataframes.schemas.asset_edit import ASSET_EDIT_SCHEMA
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        _MODEL_CACHE.pop("Offer", None)
        _MODEL_CACHE.pop("AssetEdit", None)

        ext_offer = SchemaExtractor(OFFER_SCHEMA)
        ext_asset = SchemaExtractor(ASSET_EDIT_SCHEMA)
        assert ext_offer._build_dynamic_row_model().__name__ == "OfferSchemaRow"
        assert ext_asset._build_dynamic_row_model().__name__ == "AssetEditSchemaRow"

    def test_dynamic_model_list_fields_have_default_factory(self) -> None:
        """List-typed fields should have default_factory=list to avoid mutable default."""
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        ext = SchemaExtractor(OFFER_SCHEMA)
        model = ext._build_dynamic_row_model()
        # platforms is List[Utf8]
        platforms_field = model.model_fields.get("platforms")
        assert platforms_field is not None
        assert platforms_field.default_factory is list

    def test_to_dict_includes_all_columns(self) -> None:
        """to_dict() on the extracted row should include every schema column."""
        from autom8_asana.dataframes.schemas.asset_edit import ASSET_EDIT_SCHEMA

        ext = SchemaExtractor(ASSET_EDIT_SCHEMA)
        task = make_mock_task()
        row = ext.extract(task)
        d = row.to_dict()
        for col_name in ASSET_EDIT_SCHEMA.column_names():
            assert col_name in d, f"Column {col_name!r} missing from to_dict()"


class TestSchemaExtractorWithSyntheticSchema:
    """Tests using synthetic schemas to probe boundary conditions."""

    def test_schema_with_single_extra_column(self) -> None:
        """Schema with exactly 1 extra column beyond base 13."""
        _MODEL_CACHE.pop("SingleExtra", None)
        extra = [
            ColumnDef(name="one_extra", dtype="Utf8", nullable=True, source="cf:One")
        ]
        schema = _make_schema("single_extra", "SingleExtra", extra)
        ext = SchemaExtractor(schema)
        task = make_mock_task()
        row = ext.extract(task)
        assert row is not None
        d = row.to_dict()
        assert len(d) == 14  # 13 base + 1 extra

    def test_schema_with_many_extra_columns(self) -> None:
        """Schema with 50 extra columns (stress test)."""
        _MODEL_CACHE.pop("ManyExtra", None)
        extra = [
            ColumnDef(
                name=f"field_{i}", dtype="Utf8", nullable=True, source=f"cf:Field {i}"
            )
            for i in range(50)
        ]
        schema = _make_schema("many_extra", "ManyExtra", extra)
        ext = SchemaExtractor(schema)
        task = make_mock_task()
        row = ext.extract(task)
        assert row is not None
        d = row.to_dict()
        assert len(d) == 63  # 13 base + 50 extra

    def test_schema_with_derived_fields_only(self) -> None:
        """Schema with extra columns that all have source=None (derived)."""
        _MODEL_CACHE.pop("DerivedOnly", None)
        extra = [
            ColumnDef(name="derived_a", dtype="Utf8", nullable=True, source=None),
            ColumnDef(name="derived_b", dtype="Int64", nullable=True, source=None),
        ]
        schema = _make_schema("derived_only", "DerivedOnly", extra)
        ext = SchemaExtractor(schema)
        task = make_mock_task()
        row = ext.extract(task)
        assert row is not None
        d = row.to_dict()
        # Derived fields should be None since SchemaExtractor has no _extract_{name} methods
        assert d["derived_a"] is None
        assert d["derived_b"] is None

    def test_schema_with_column_name_collision_with_task_attribute(self) -> None:
        """Column name that matches a MagicMock attribute should not cause issues."""
        _MODEL_CACHE.pop("NameCollision", None)
        extra = [
            ColumnDef(
                name="assert_called",
                dtype="Utf8",
                nullable=True,
                source="cf:Assert Called",
            ),
        ]
        schema = _make_schema("name_collision", "NameCollision", extra)
        ext = SchemaExtractor(schema)
        task = make_mock_task()
        row = ext.extract(task)
        assert row is not None


class TestExtractTypeOverride:
    """Verify SchemaExtractor._extract_type always returns schema.task_type."""

    def test_extract_type_ignores_resource_subtype(self) -> None:
        """SchemaExtractor should return schema.task_type, not resource_subtype."""
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        ext = SchemaExtractor(OFFER_SCHEMA)
        task = make_mock_task()
        task.resource_subtype = "some_other_subtype"
        assert ext._extract_type(task) == "Offer"

    def test_extract_type_with_none_task(self) -> None:
        """_extract_type should work even if task is None-ish."""
        from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA

        ext = SchemaExtractor(BUSINESS_SCHEMA)
        assert ext._extract_type(None) == "Business"


class TestCacheClearing:
    """Verify _MODEL_CACHE behavior under clearing scenarios."""

    def test_clearing_cache_allows_model_rebuild(self) -> None:
        """After clearing cache, a new model should be built."""
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        ext = SchemaExtractor(OFFER_SCHEMA)
        model1 = ext._build_dynamic_row_model()

        _MODEL_CACHE.clear()

        model2 = ext._build_dynamic_row_model()
        # Models should be equal (same fields) but different instances
        assert model1 is not model2
        assert model1.__name__ == model2.__name__
