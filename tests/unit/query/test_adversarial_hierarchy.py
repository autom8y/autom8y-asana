"""Adversarial tests for HierarchyIndex + Cross-Entity Joins.

Sprint 2, Cycle 1: QA Adversary validation.
Tests edge cases, boundary conditions, error paths, and TDD deviation probes
beyond the happy-path coverage in test_hierarchy.py, test_join.py, and
test_engine.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from pydantic import ValidationError

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import JoinError, UnknownFieldError
from autom8_asana.query.hierarchy import (
    ENTITY_RELATIONSHIPS,
    EntityRelationship,
    find_relationship,
    get_join_key,
    get_joinable_types,
)
from autom8_asana.query.join import JoinSpec, JoinResult, execute_join
from autom8_asana.query.models import RowsRequest
from autom8_asana.services.query_service import EntityQueryService


# ==========================================================================
# 1. Hierarchy Registry Edge Cases
# ==========================================================================


class TestHierarchyRegistryAdversarial:
    """Adversarial probes against the EntityRelationship registry."""

    def test_unrelated_entity_types_contact_unit(self) -> None:
        """Query between two entity types with no direct relationship."""
        rel = find_relationship("contact", "unit")
        assert rel is None

    def test_unknown_entity_type_source(self) -> None:
        """Source entity type not in registry at all."""
        rel = find_relationship("unknown_type", "business")
        assert rel is None

    def test_unknown_entity_type_target(self) -> None:
        """Target entity type not in registry at all."""
        rel = find_relationship("offer", "unknown_type")
        assert rel is None

    def test_both_unknown_entity_types(self) -> None:
        """Both entity types are unknown."""
        rel = find_relationship("foo", "bar")
        assert rel is None

    def test_self_join_offer(self) -> None:
        """Self-join: source == target should return None (no self-relationship)."""
        rel = find_relationship("offer", "offer")
        assert rel is None

    def test_self_join_business(self) -> None:
        """Self-join on business also returns None."""
        rel = find_relationship("business", "business")
        assert rel is None

    def test_bidirectional_offer_business(self) -> None:
        """A->B and B->A both return the same relationship object fields."""
        rel_ab = find_relationship("offer", "business")
        rel_ba = find_relationship("business", "offer")
        assert rel_ab is not None
        assert rel_ba is not None
        assert rel_ab.parent_type == rel_ba.parent_type
        assert rel_ab.child_type == rel_ba.child_type
        assert rel_ab.default_join_key == rel_ba.default_join_key

    def test_bidirectional_unit_offer(self) -> None:
        """Unit->Offer and Offer->Unit return same relationship."""
        rel_ab = find_relationship("unit", "offer")
        rel_ba = find_relationship("offer", "unit")
        assert rel_ab is not None
        assert rel_ba is not None
        assert rel_ab.parent_type == rel_ba.parent_type

    def test_get_joinable_types_offer(self) -> None:
        """Offer should join with business and unit only."""
        types = get_joinable_types("offer")
        assert types == ["business", "unit"]

    def test_get_joinable_types_contact(self) -> None:
        """Contact should join with business only."""
        types = get_joinable_types("contact")
        assert types == ["business"]

    def test_get_joinable_types_unit(self) -> None:
        """Unit should join with business and offer."""
        types = get_joinable_types("unit")
        assert types == ["business", "offer"]

    def test_get_joinable_types_unknown(self) -> None:
        """Unknown entity returns empty list."""
        types = get_joinable_types("totally_unknown")
        assert types == []

    def test_get_joinable_types_empty_string(self) -> None:
        """Empty string entity returns empty list."""
        types = get_joinable_types("")
        assert types == []

    def test_get_join_key_explicit_overrides_even_for_unrelated(self) -> None:
        """Explicit key is returned even for unrelated types (bypass check)."""
        key = get_join_key("contact", "unit", "some_column")
        assert key == "some_column"

    def test_get_join_key_no_relationship_no_explicit(self) -> None:
        """No relationship, no explicit key -> None."""
        key = get_join_key("contact", "unit")
        assert key is None

    def test_entity_relationships_all_have_office_phone(self) -> None:
        """All current relationships use office_phone as default join key."""
        for rel in ENTITY_RELATIONSHIPS:
            assert rel.default_join_key == "office_phone", (
                f"Relationship {rel.parent_type}->{rel.child_type} "
                f"has unexpected default key: {rel.default_join_key}"
            )

    def test_entity_relationship_frozen(self) -> None:
        """EntityRelationship is frozen (immutable)."""
        rel = ENTITY_RELATIONSHIPS[0]
        with pytest.raises(AttributeError):
            rel.parent_type = "hacked"  # type: ignore[misc]


# ==========================================================================
# 2. Join Execution Edge Cases
# ==========================================================================


class TestJoinExecutionAdversarial:
    """Adversarial probes against execute_join()."""

    def test_empty_source_df(self) -> None:
        """Empty source DataFrame (0 rows) with join returns empty result."""
        primary = pl.DataFrame(
            {
                "gid": pl.Series([], dtype=pl.Utf8),
                "office_phone": pl.Series([], dtype=pl.Utf8),
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111"],
                "booking_type": ["Online"],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.df.height == 0
        assert "business_booking_type" in result.df.columns
        assert result.matched_count == 0
        assert result.unmatched_count == 0

    def test_empty_target_df(self) -> None:
        """Empty target DataFrame (0 rows) -> all join columns null."""
        primary = pl.DataFrame(
            {
                "gid": ["o1", "o2"],
                "office_phone": ["+1111", "+2222"],
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": pl.Series([], dtype=pl.Utf8),
                "booking_type": pl.Series([], dtype=pl.Utf8),
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.df.height == 2
        assert result.matched_count == 0
        assert result.unmatched_count == 2
        # All join columns should be null
        assert result.df["business_booking_type"].null_count() == 2

    def test_all_source_rows_null_join_key(self) -> None:
        """Source DataFrame where ALL rows have null join key (typed column).

        In production, DataFrames come from cache with explicit Utf8 dtype.
        All-null values should result in zero matches.
        """
        primary = pl.DataFrame(
            {
                "gid": ["o1", "o2", "o3"],
                "office_phone": pl.Series([None, None, None], dtype=pl.Utf8),
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111", "+2222"],
                "booking_type": ["Online", "Phone"],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.df.height == 3
        assert result.matched_count == 0
        assert result.unmatched_count == 3
        assert result.df["business_booking_type"].null_count() == 3

    def test_all_source_rows_null_join_key_untyped_raises(self) -> None:
        """DEFECT: All-null join key without explicit dtype causes SchemaError.

        Severity: LOW -- In production, DataFrames always have explicit
        dtypes from the schema registry. This only manifests if a DataFrame
        is constructed without dtype specification and all join key values
        are null, causing Polars to infer dtype as Null which mismatches
        the target's Utf8 dtype. Documenting as known edge case.
        """
        primary = pl.DataFrame(
            {
                "gid": ["o1", "o2"],
                "office_phone": [None, None],  # Polars infers Null dtype
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111"],
                "booking_type": ["Online"],
            }
        )
        with pytest.raises(Exception):  # polars.exceptions.SchemaError
            execute_join(
                primary_df=primary,
                target_df=target,
                join_key="office_phone",
                select_columns=["booking_type"],
                target_entity_type="business",
            )

    def test_target_duplicate_join_keys_takes_first(self) -> None:
        """Target with duplicate join keys deduplicates with keep='first'."""
        primary = pl.DataFrame(
            {
                "gid": ["o1"],
                "office_phone": ["+1111"],
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111", "+1111", "+1111"],
                "booking_type": ["First", "Second", "Third"],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.df.height == 1  # No row multiplication
        assert result.matched_count == 1
        assert result.df["business_booking_type"][0] == "First"

    def test_join_column_name_collision_with_prefix(self) -> None:
        """Primary already has a column named business_booking_type.

        The prefixed join column should still be added (Polars will suffix
        with _right or similar). This tests whether the implementation
        handles this gracefully.
        """
        primary = pl.DataFrame(
            {
                "gid": ["o1"],
                "office_phone": ["+1111"],
                "business_booking_type": ["existing_value"],
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111"],
                "booking_type": ["Online"],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        # The join should complete without error.
        # Polars will resolve the collision by suffixing the right column.
        assert result.df.height == 1
        # Check that both original and joined columns exist in some form
        col_names = result.df.columns
        assert any("business_booking_type" in c for c in col_names)

    def test_large_join_1000_rows(self) -> None:
        """Performance/correctness: 1000+ rows in both DataFrames."""
        n = 1200
        phones = [f"+{i:04d}" for i in range(n)]
        primary = pl.DataFrame(
            {
                "gid": [f"o{i}" for i in range(n)],
                "office_phone": phones,
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": phones,
                "booking_type": [f"type_{i}" for i in range(n)],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.df.height == n
        assert result.matched_count == n
        assert result.unmatched_count == 0

    def test_target_select_column_all_null_values(self) -> None:
        """Join target select column exists but all values are null."""
        primary = pl.DataFrame(
            {
                "gid": ["o1", "o2"],
                "office_phone": ["+1111", "+2222"],
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111", "+2222"],
                "booking_type": [None, None],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.df.height == 2
        # matched_count uses is_not_null on first join col -- since all
        # join col values are null, matched_count should be 0 even though
        # the join key matched.
        assert result.matched_count == 0
        assert result.unmatched_count == 2

    def test_select_includes_join_key_column(self) -> None:
        """Select list includes the join key itself.

        The join key should not be duplicated in the result. The rename map
        skips the join key, so it should appear un-prefixed.
        """
        primary = pl.DataFrame(
            {
                "gid": ["o1"],
                "office_phone": ["+1111"],
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111"],
                "booking_type": ["Online"],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["office_phone", "booking_type"],
            target_entity_type="business",
        )
        assert result.df.height == 1
        # office_phone should NOT be prefixed (it's the join key)
        assert "office_phone" in result.df.columns
        # booking_type SHOULD be prefixed
        assert "business_booking_type" in result.df.columns

    def test_multiple_select_columns(self) -> None:
        """Join with multiple select columns, verify all are prefixed."""
        primary = pl.DataFrame(
            {
                "gid": ["o1"],
                "office_phone": ["+1111"],
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111"],
                "booking_type": ["Online"],
                "stripe_id": ["str_1"],
                "company_id": ["CMP-1"],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type", "stripe_id", "company_id"],
            target_entity_type="business",
        )
        assert "business_booking_type" in result.df.columns
        assert "business_stripe_id" in result.df.columns
        assert "business_company_id" in result.df.columns


# ==========================================================================
# 3. JoinSpec Model Validation
# ==========================================================================


class TestJoinSpecAdversarial:
    """Adversarial probes against JoinSpec Pydantic model."""

    def test_empty_select_list(self) -> None:
        """Empty select list fails validation (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            JoinSpec(entity_type="business", select=[])
        errors = exc_info.value.errors()
        assert any("too_short" in str(e) for e in errors)

    def test_eleven_select_columns(self) -> None:
        """Exactly 11 columns exceeds max_length=10."""
        with pytest.raises(ValidationError) as exc_info:
            JoinSpec(
                entity_type="business",
                select=[f"col_{i}" for i in range(11)],
            )
        errors = exc_info.value.errors()
        assert any("too_long" in str(e) for e in errors)

    def test_ten_select_columns_accepted(self) -> None:
        """Exactly 10 columns is accepted (max_length=10)."""
        spec = JoinSpec(
            entity_type="business",
            select=[f"col_{i}" for i in range(10)],
        )
        assert len(spec.select) == 10

    def test_one_select_column_accepted(self) -> None:
        """Exactly 1 column is accepted (min_length=1)."""
        spec = JoinSpec(entity_type="business", select=["booking_type"])
        assert len(spec.select) == 1

    def test_extra_fields_rejected(self) -> None:
        """Extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError):
            JoinSpec(
                entity_type="business",
                select=["booking_type"],
                extra_field="bad",  # type: ignore[call-arg]
            )

    def test_missing_entity_type_rejected(self) -> None:
        """Missing entity_type field fails validation."""
        with pytest.raises(ValidationError):
            JoinSpec(select=["booking_type"])  # type: ignore[call-arg]

    def test_missing_select_rejected(self) -> None:
        """Missing select field fails validation."""
        with pytest.raises(ValidationError):
            JoinSpec(entity_type="business")  # type: ignore[call-arg]

    def test_from_dict_with_extra_field(self) -> None:
        """model_validate with extra field also rejected."""
        with pytest.raises(ValidationError):
            JoinSpec.model_validate(
                {
                    "entity_type": "business",
                    "select": ["booking_type"],
                    "malicious_field": "injection",
                }
            )

    def test_on_field_optional(self) -> None:
        """on field defaults to None when not provided."""
        spec = JoinSpec.model_validate(
            {"entity_type": "business", "select": ["booking_type"]}
        )
        assert spec.on is None


# ==========================================================================
# 4. Engine Integration Adversarial
# ==========================================================================


def _make_offer_schema() -> DataFrameSchema:
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("office_phone", "Utf8", nullable=True),
            ColumnDef("mrr", "Utf8", nullable=True),
        ],
    )


def _make_business_schema() -> DataFrameSchema:
    return DataFrameSchema(
        name="business",
        task_type="Business",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("office_phone", "Utf8", nullable=True),
            ColumnDef("booking_type", "Utf8", nullable=True),
            ColumnDef("company_id", "Utf8", nullable=True),
        ],
    )


class TestEngineJoinAdversarial:
    """Adversarial engine-level join tests."""

    @pytest.mark.asyncio
    async def test_join_plus_section_plus_predicate(self) -> None:
        """Join + section filter + predicate all compose correctly."""
        offer_schema = _make_offer_schema()
        business_schema = _make_business_schema()
        schema_map = {"Offer": offer_schema, "Business": business_schema}

        offer_df = pl.DataFrame(
            {
                "gid": ["o1", "o2", "o3", "o4"],
                "name": ["Offer A", "Offer B", "Offer C", "Offer D"],
                "section": ["Active", "Active", "Won", "Active"],
                "office_phone": ["+1111", "+2222", "+3333", "+4444"],
                "mrr": ["100", "200", "300", "400"],
            }
        )
        business_df = pl.DataFrame(
            {
                "gid": ["b1", "b2", "b3", "b4"],
                "name": ["Biz A", "Biz B", "Biz C", "Biz D"],
                "office_phone": ["+1111", "+2222", "+3333", "+4444"],
                "booking_type": ["Online", "Phone", "Walk-in", "Online"],
                "company_id": ["C1", "C2", "C3", "C4"],
            }
        )

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            side_effect=[offer_df, business_df]
        )
        engine = QueryEngine(query_service=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj-123"

        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-123"})

        request = RowsRequest.model_validate(
            {
                "section": "Active",
                "where": {"field": "name", "op": "eq", "value": "Offer A"},
                "select": ["name", "office_phone"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=AsyncMock(),
                request=request,
                section_index=section_index,
                entity_project_registry=mock_epr,
            )

        # Section=Active AND name=Offer A => only o1
        assert result.meta.total_count == 1
        assert result.data[0]["name"] == "Offer A"
        assert result.data[0]["business_booking_type"] == "Online"
        assert result.meta.join_entity == "business"

    @pytest.mark.asyncio
    async def test_join_no_project_configured(self) -> None:
        """Join target entity type has no project configured -> JoinError."""
        offer_schema = _make_offer_schema()
        business_schema = _make_business_schema()
        schema_map = {"Offer": offer_schema, "Business": business_schema}

        offer_df = pl.DataFrame(
            {
                "gid": ["o1"],
                "name": ["Offer A"],
                "section": ["Active"],
                "office_phone": ["+1111"],
                "mrr": ["100"],
            }
        )

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            return_value=offer_df
        )
        engine = QueryEngine(query_service=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = None

        request = RowsRequest.model_validate(
            {
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            with pytest.raises(JoinError, match="No project configured"):
                await engine.execute_rows(
                    entity_type="offer",
                    project_gid="proj-123",
                    client=AsyncMock(),
                    request=request,
                    entity_project_registry=mock_epr,
                )

    @pytest.mark.asyncio
    async def test_join_select_without_join_key_column(self) -> None:
        """Select list doesn't include join key -> join still works."""
        offer_schema = _make_offer_schema()
        business_schema = _make_business_schema()
        schema_map = {"Offer": offer_schema, "Business": business_schema}

        offer_df = pl.DataFrame(
            {
                "gid": ["o1"],
                "name": ["Offer A"],
                "section": ["Active"],
                "office_phone": ["+1111"],
                "mrr": ["100"],
            }
        )
        business_df = pl.DataFrame(
            {
                "gid": ["b1"],
                "name": ["Biz A"],
                "office_phone": ["+1111"],
                "booking_type": ["Online"],
                "company_id": ["C1"],
            }
        )

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            side_effect=[offer_df, business_df]
        )
        engine = QueryEngine(query_service=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj-123"

        # User select does NOT include office_phone, but join still works
        request = RowsRequest.model_validate(
            {
                "select": ["name"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=AsyncMock(),
                request=request,
                entity_project_registry=mock_epr,
            )

        # Join-enriched columns should still appear in response
        assert "business_booking_type" in result.data[0]
        assert result.meta.join_matched == 1

    @pytest.mark.asyncio
    async def test_join_offset_larger_than_result(self) -> None:
        """Offset larger than result count -> empty data with join meta."""
        offer_schema = _make_offer_schema()
        business_schema = _make_business_schema()
        schema_map = {"Offer": offer_schema, "Business": business_schema}

        offer_df = pl.DataFrame(
            {
                "gid": ["o1", "o2"],
                "name": ["Offer A", "Offer B"],
                "section": ["Active", "Active"],
                "office_phone": ["+1111", "+2222"],
                "mrr": ["100", "200"],
            }
        )
        business_df = pl.DataFrame(
            {
                "gid": ["b1", "b2"],
                "name": ["Biz A", "Biz B"],
                "office_phone": ["+1111", "+2222"],
                "booking_type": ["Online", "Phone"],
                "company_id": ["C1", "C2"],
            }
        )

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            side_effect=[offer_df, business_df]
        )
        engine = QueryEngine(query_service=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj-123"

        request = RowsRequest.model_validate(
            {
                "offset": 999,
                "select": ["name", "office_phone"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=AsyncMock(),
                request=request,
                entity_project_registry=mock_epr,
            )

        # Join happened before pagination; total_count reflects joined DF
        assert result.meta.total_count == 2
        assert result.meta.returned_count == 0
        assert result.data == []
        # Join meta should still be populated
        assert result.meta.join_entity == "business"
        assert result.meta.join_key == "office_phone"


# ==========================================================================
# 5. Error Serialization
# ==========================================================================


class TestErrorSerialization:
    """Verify error to_dict() format for join-related errors."""

    def test_join_error_to_dict(self) -> None:
        """JoinError.to_dict() has correct structure."""
        err = JoinError(message="Something went wrong")
        d = err.to_dict()
        assert d["error"] == "JOIN_ERROR"
        assert d["message"] == "Something went wrong"
        assert len(d) == 2  # Only 'error' and 'message'

    def test_join_error_is_query_engine_error(self) -> None:
        """JoinError inherits from QueryEngineError."""
        from autom8_asana.query.errors import QueryEngineError

        err = JoinError(message="test")
        assert isinstance(err, QueryEngineError)

    def test_join_error_is_exception(self) -> None:
        """JoinError can be raised and caught as Exception."""
        with pytest.raises(JoinError):
            raise JoinError(message="test error")

    def test_unknown_field_error_to_dict(self) -> None:
        """UnknownFieldError.to_dict() for join column validation."""
        err = UnknownFieldError(field="bad_col", available=["a", "b", "c"])
        d = err.to_dict()
        assert d["error"] == "UNKNOWN_FIELD"
        assert "bad_col" in d["message"]
        assert d["available_fields"] == ["a", "b", "c"]

    def test_join_error_no_relationship_format(self) -> None:
        """Error message for no relationship includes joinable types hint."""
        err = JoinError(
            "No relationship between 'offer' and 'contact'. "
            "Joinable types: ['business', 'unit']"
        )
        d = err.to_dict()
        assert "Joinable types" in d["message"]
        assert "business" in d["message"]

    def test_join_error_no_project_format(self) -> None:
        """Error message for no project configured."""
        err = JoinError("No project configured for join target: business")
        d = err.to_dict()
        assert "No project configured" in d["message"]


# ==========================================================================
# 6. TDD Deviation Probes
# ==========================================================================


class TestTDDDeviationProbes:
    """Probes to verify implementation matches TDD specification."""

    def test_join_columns_appear_without_user_select(self) -> None:
        """Join-enriched columns appear even when user has no explicit select.

        Per engine code: if request.join is set, prefixed columns are
        appended to the column list regardless of user select.
        """
        primary = pl.DataFrame(
            {
                "gid": ["o1"],
                "name": ["Offer A"],
                "office_phone": ["+1111"],
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111"],
                "booking_type": ["Online"],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        # At execute_join level, join columns are always in result.df
        assert "business_booking_type" in result.df.columns

    def test_null_join_key_left_join_semantics(self) -> None:
        """Null join key rows get null join columns via left join."""
        primary = pl.DataFrame(
            {
                "gid": ["o1", "o2"],
                "office_phone": ["+1111", None],
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111"],
                "booking_type": ["Online"],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        assert result.df.height == 2
        # Row with null join key gets null join columns
        null_row = result.df.filter(pl.col("gid") == "o2")
        assert null_row["business_booking_type"][0] is None

    @pytest.mark.asyncio
    async def test_entity_project_registry_passed_not_singleton(self) -> None:
        """EntityProjectRegistry is passed as parameter, not used as singleton.

        The engine code accepts entity_project_registry as a parameter.
        When provided, it should use that instance, not call get_instance().
        """
        offer_schema = _make_offer_schema()
        business_schema = _make_business_schema()
        schema_map = {"Offer": offer_schema, "Business": business_schema}

        offer_df = pl.DataFrame(
            {
                "gid": ["o1"],
                "name": ["Offer A"],
                "section": ["Active"],
                "office_phone": ["+1111"],
                "mrr": ["100"],
            }
        )
        business_df = pl.DataFrame(
            {
                "gid": ["b1"],
                "name": ["Biz A"],
                "office_phone": ["+1111"],
                "booking_type": ["Online"],
                "company_id": ["C1"],
            }
        )

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            side_effect=[offer_df, business_df]
        )
        engine = QueryEngine(query_service=service)

        mock_epr = MagicMock()
        mock_epr.get_project_gid.return_value = "biz-proj-123"

        request = RowsRequest.model_validate(
            {
                "select": ["name", "office_phone"],
                "join": {
                    "entity_type": "business",
                    "select": ["booking_type"],
                },
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.side_effect = lambda k: schema_map[k]
            mock_registry_cls.get_instance.return_value = mock_registry

            # Patch the singleton fallback to fail if called
            with patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                side_effect=RuntimeError("Should not call singleton"),
            ):
                result = await engine.execute_rows(
                    entity_type="offer",
                    project_gid="proj-123",
                    client=AsyncMock(),
                    request=request,
                    entity_project_registry=mock_epr,
                )

        # If we get here, the passed EPR was used, not the singleton
        assert result.meta.join_entity == "business"
        mock_epr.get_project_gid.assert_called_once_with("business")

    def test_join_result_preserves_row_count(self) -> None:
        """Left join must never change the primary DataFrame row count."""
        primary = pl.DataFrame(
            {
                "gid": [f"o{i}" for i in range(50)],
                "office_phone": ["+1111"] * 50,  # All same phone
            }
        )
        target = pl.DataFrame(
            {
                "office_phone": ["+1111", "+1111", "+1111"],
                "booking_type": ["A", "B", "C"],
            }
        )
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["booking_type"],
            target_entity_type="business",
        )
        # Dedup ensures no row multiplication
        assert result.df.height == 50

    def test_max_join_depth_constant(self) -> None:
        """MAX_JOIN_DEPTH is set to 1 per TDD constraint."""
        from autom8_asana.query.join import MAX_JOIN_DEPTH

        assert MAX_JOIN_DEPTH == 1

    def test_rows_request_join_field_optional(self) -> None:
        """RowsRequest.join defaults to None (backward compat)."""
        request = RowsRequest.model_validate({})
        assert request.join is None

    def test_rows_meta_join_fields_default_none(self) -> None:
        """RowsMeta join fields default to None."""
        from autom8_asana.query.models import RowsMeta

        meta = RowsMeta(
            total_count=0,
            returned_count=0,
            limit=100,
            offset=0,
            entity_type="offer",
            project_gid="proj-123",
            query_ms=1.0,
        )
        assert meta.join_entity is None
        assert meta.join_key is None
        assert meta.join_matched is None
        assert meta.join_unmatched is None
