"""Unit tests for SchemaExtractor.

Per TDD-ENTITY-EXT-001: Verifies dynamic Pydantic model generation,
dtype mapping, list defaults, derived field None returns, model caching,
and type extraction for the generic schema-driven extractor.
"""

from __future__ import annotations

import pytest

from autom8_asana.dataframes.extractors.schema import (
    _MODEL_CACHE,
    DTYPE_MAP,
    SchemaExtractor,
)
from autom8_asana.dataframes.schemas.asset_edit import ASSET_EDIT_SCHEMA
from autom8_asana.dataframes.schemas.asset_edit_holder import ASSET_EDIT_HOLDER_SCHEMA
from autom8_asana.dataframes.schemas.base import BASE_SCHEMA
from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA
from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA
from tests.unit.dataframes.conftest import make_mock_task


class TestSchemaExtractor:
    """Unit tests for SchemaExtractor."""

    def test_offer_extraction_does_not_crash(self) -> None:
        """AC-1.1: Offer extraction succeeds."""
        extractor = SchemaExtractor(OFFER_SCHEMA)
        task = make_mock_task()
        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        assert len(d) == len(OFFER_SCHEMA.columns)

    def test_asset_edit_extraction_does_not_crash(self) -> None:
        """AC-3.1: AssetEdit extraction succeeds."""
        extractor = SchemaExtractor(ASSET_EDIT_SCHEMA)
        task = make_mock_task()
        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        assert len(d) == len(ASSET_EDIT_SCHEMA.columns)

    def test_asset_edit_holder_extraction_does_not_crash(self) -> None:
        """AC-4.1: AssetEditHolder extraction succeeds."""
        extractor = SchemaExtractor(ASSET_EDIT_HOLDER_SCHEMA)
        task = make_mock_task()
        row = extractor.extract(task)
        assert row is not None

    def test_business_extraction_does_not_crash(self) -> None:
        """AC-2.1: Business extraction succeeds."""
        extractor = SchemaExtractor(BUSINESS_SCHEMA)
        task = make_mock_task()
        row = extractor.extract(task)
        assert row is not None

    def test_extract_type_returns_schema_task_type(self) -> None:
        """AC-5.3: _extract_type returns schema.task_type."""
        extractor = SchemaExtractor(OFFER_SCHEMA)
        task = make_mock_task()
        assert extractor._extract_type(task) == "Offer"

    def test_dynamic_model_cached(self) -> None:
        """AC-5.6: Model created once per schema type."""
        _MODEL_CACHE.clear()
        ext1 = SchemaExtractor(OFFER_SCHEMA)
        ext2 = SchemaExtractor(OFFER_SCHEMA)
        model1 = ext1._build_dynamic_row_model()
        model2 = ext2._build_dynamic_row_model()
        assert model1 is model2

    def test_list_fields_default_to_empty_list(self) -> None:
        """AC-5.2: List fields default to [] not None."""
        extractor = SchemaExtractor(OFFER_SCHEMA)
        task = make_mock_task()
        row = extractor.extract(task)
        d = row.to_dict()
        assert d["platforms"] == []

    def test_derived_fields_return_none(self) -> None:
        """AC-5.3: source=None fields without custom extractors return None."""
        extractor = SchemaExtractor(OFFER_SCHEMA)
        task = make_mock_task()
        row = extractor.extract(task)
        d = row.to_dict()
        # office and vertical_id have source=None with no _extract method
        assert d["office"] is None
        assert d["vertical_id"] is None

    def test_dtype_map_covers_all_used_types(self) -> None:
        """FR-11: All dtypes in existing schemas are mapped."""
        required_dtypes = {
            "Utf8",
            "Int64",
            "Float64",
            "Boolean",
            "Date",
            "Datetime",
            "Decimal",
            "List[Utf8]",
        }
        assert required_dtypes.issubset(DTYPE_MAP.keys())

    def test_row_has_all_schema_columns(self) -> None:
        """Verify extracted row dict has all schema column names."""
        extractor = SchemaExtractor(ASSET_EDIT_SCHEMA)
        task = make_mock_task()
        row = extractor.extract(task)
        d = row.to_dict()
        for col_name in ASSET_EDIT_SCHEMA.column_names():
            assert col_name in d, f"Column {col_name!r} missing from row"

    def test_asset_edit_list_fields_default_to_empty_list(self) -> None:
        """AssetEdit List[Utf8] fields (specialty, asset_edit_specialty) default to []."""
        extractor = SchemaExtractor(ASSET_EDIT_SCHEMA)
        task = make_mock_task()
        row = extractor.extract(task)
        d = row.to_dict()
        assert d["specialty"] == []
        assert d["asset_edit_specialty"] == []

    def test_base_schema_has_no_extra_columns(self) -> None:
        """BASE_SCHEMA should not trigger SchemaExtractor (no extra cols)."""
        from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

        base_col_names = {c.name for c in BASE_COLUMNS}
        schema_col_names = {c.name for c in BASE_SCHEMA.columns}
        assert schema_col_names == base_col_names

    def test_business_type_set_correctly(self) -> None:
        """Business schema task_type is 'Business' (PascalCase, matches convention)."""
        extractor = SchemaExtractor(BUSINESS_SCHEMA)
        task = make_mock_task()
        row = extractor.extract(task)
        d = row.to_dict()
        assert d["type"] == "Business"

    def test_different_schemas_produce_different_models(self) -> None:
        """Each schema type produces a distinct cached model."""
        _MODEL_CACHE.clear()
        ext_offer = SchemaExtractor(OFFER_SCHEMA)
        ext_asset = SchemaExtractor(ASSET_EDIT_SCHEMA)
        model_offer = ext_offer._build_dynamic_row_model()
        model_asset = ext_asset._build_dynamic_row_model()
        assert model_offer is not model_asset
        assert model_offer.__name__ == "OfferSchemaRow"
        assert model_asset.__name__ == "AssetEditSchemaRow"
