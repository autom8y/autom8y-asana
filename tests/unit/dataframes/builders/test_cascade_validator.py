"""Unit tests for cascade_validator module.

Per TDD-CASCADE-FAILURE-FIXES-001 section 7.3: Tests post-build cascade
validation that detects and corrects stale cascade-critical fields in
merged DataFrames.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.builders.cascade_validator import (
    CascadeValidationResult,
    validate_cascade_fields_async,
)


def _make_office_phone_schema() -> MagicMock:
    """Create a mock schema with office_phone as a cascade column.

    Returns a mock DataFrameSchema where ``get_cascade_columns()``
    returns ``[("office_phone", "Office Phone")]``.
    """
    schema = MagicMock()
    schema.get_cascade_columns.return_value = [("office_phone", "Office Phone")]
    return schema


def _make_mock_store(
    *,
    ancestor_chains: dict[str, list[str]] | None = None,
    parent_chains: dict[str, list[dict]] | None = None,
) -> MagicMock:
    """Create a mock UnifiedTaskStore with hierarchy index and parent chain.

    Args:
        ancestor_chains: Mapping of gid -> list of ancestor GIDs for hierarchy index.
        parent_chains: Mapping of gid -> list of parent data dicts for get_parent_chain_async.

    Returns:
        Mock store with configured hierarchy index and parent chain behavior.
    """
    ancestor_chains = ancestor_chains or {}
    parent_chains = parent_chains or {}

    mock_hierarchy = MagicMock()
    mock_hierarchy.get_ancestor_chain.side_effect = lambda gid, max_depth=5: (
        ancestor_chains.get(gid, [])
    )

    mock_store = MagicMock()
    mock_store.get_hierarchy_index.return_value = mock_hierarchy
    mock_store.get_parent_chain_async = AsyncMock(
        side_effect=lambda gid, **kw: parent_chains.get(gid, [])
    )

    return mock_store


def _make_mock_cascade_plugin(
    *,
    field_values: dict[str, dict[str, str | None]] | None = None,
) -> MagicMock:
    """Create a mock CascadeViewPlugin.

    Args:
        field_values: Mapping of parent_gid -> {field_name: value}.
            Uses parent_data["gid"] to key lookups.

    Returns:
        Mock cascade plugin with configured field value extraction.
    """
    field_values = field_values or {}

    mock_plugin = MagicMock()

    def _get_value(task_data: dict, field_name: str) -> str | None:
        gid = task_data.get("gid", "")
        return field_values.get(gid, {}).get(field_name)

    mock_plugin._get_custom_field_value_from_dict.side_effect = _get_value

    return mock_plugin


@pytest.mark.asyncio
async def test_validation_corrects_null_office_phone() -> None:
    """1 row with null office_phone, store resolves from parent chain."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
            "office_phone": [None],
            "section_gid": ["sec-1"],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
            "section_gid": pl.Utf8,
        },
    )

    store = _make_mock_store(
        ancestor_chains={"task-1": ["holder-1", "business-1"]},
        parent_chains={
            "task-1": [
                {"gid": "holder-1", "custom_fields": []},
                {
                    "gid": "business-1",
                    "custom_fields": [
                        {"name": "Office Phone", "display_value": "555-1234"}
                    ],
                },
            ]
        },
    )

    plugin = _make_mock_cascade_plugin(
        field_values={
            "holder-1": {"Office Phone": None},
            "business-1": {"Office Phone": "555-1234"},
        }
    )

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 1
    assert result.rows_stale == 1
    assert result.rows_corrected == 1
    assert result.sections_affected == {"sec-1"}
    assert corrected_df["office_phone"][0] == "555-1234"


@pytest.mark.asyncio
async def test_validation_noop_when_all_populated() -> None:
    """No null rows, assert unchanged."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1", "task-2"],
            "name": ["Offer 1", "Offer 2"],
            "office_phone": ["555-1111", "555-2222"],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    store = _make_mock_store()
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 0
    assert result.rows_stale == 0
    assert result.rows_corrected == 0
    assert corrected_df["office_phone"].to_list() == ["555-1111", "555-2222"]


@pytest.mark.asyncio
async def test_validation_noop_when_no_ancestors() -> None:
    """Null row but no ancestors in hierarchy, assert not corrected."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
            "office_phone": [None],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    # No ancestors registered in hierarchy
    store = _make_mock_store(
        ancestor_chains={},
        parent_chains={},
    )
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 1
    assert result.rows_stale == 0
    assert result.rows_corrected == 0
    assert corrected_df["office_phone"][0] is None


@pytest.mark.asyncio
async def test_validation_noop_when_ancestors_also_null() -> None:
    """Ancestors exist but also have null for the cascade field."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
            "office_phone": [None],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    store = _make_mock_store(
        ancestor_chains={"task-1": ["holder-1", "business-1"]},
        parent_chains={
            "task-1": [
                {"gid": "holder-1", "custom_fields": []},
                {"gid": "business-1", "custom_fields": []},
            ]
        },
    )

    # All ancestors return None for Office Phone
    plugin = _make_mock_cascade_plugin(
        field_values={
            "holder-1": {"Office Phone": None},
            "business-1": {"Office Phone": None},
        }
    )

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 1
    assert result.rows_stale == 0
    assert result.rows_corrected == 0
    assert corrected_df["office_phone"][0] is None


@pytest.mark.asyncio
async def test_validation_multiple_rows() -> None:
    """3 rows with null, 2 resolvable, assert 2 corrected."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1", "task-2", "task-3"],
            "name": ["Offer 1", "Offer 2", "Offer 3"],
            "office_phone": [None, None, None],
            "section_gid": ["sec-1", "sec-1", "sec-2"],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
            "section_gid": pl.Utf8,
        },
    )

    store = _make_mock_store(
        ancestor_chains={
            "task-1": ["holder-1", "business-1"],
            "task-2": ["holder-2", "business-1"],
            "task-3": ["holder-3"],  # ancestors exist but no parent chain resolves
        },
        parent_chains={
            "task-1": [
                {"gid": "holder-1", "custom_fields": []},
                {"gid": "business-1", "custom_fields": []},
            ],
            "task-2": [
                {"gid": "holder-2", "custom_fields": []},
                {"gid": "business-1", "custom_fields": []},
            ],
            "task-3": [
                {"gid": "holder-3", "custom_fields": []},
            ],
        },
    )

    plugin = _make_mock_cascade_plugin(
        field_values={
            "holder-1": {"Office Phone": None},
            "holder-2": {"Office Phone": None},
            "holder-3": {"Office Phone": None},
            "business-1": {"Office Phone": "555-9999"},
        }
    )

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 3
    assert result.rows_stale == 2
    assert result.rows_corrected == 2
    # task-3 was NOT corrected (holder-3 has no Office Phone), so sec-2 is
    # not in sections_affected. Only sec-1 (task-1, task-2 both corrected).
    assert result.sections_affected == {"sec-1"}
    assert corrected_df["office_phone"][0] == "555-9999"
    assert corrected_df["office_phone"][1] == "555-9999"
    assert corrected_df["office_phone"][2] is None


@pytest.mark.asyncio
async def test_validation_skips_when_no_gid_column() -> None:
    """DataFrame without gid column should return immediately."""
    merged_df = pl.DataFrame(
        {
            "name": ["Offer 1"],
            "office_phone": [None],
        },
        schema={
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    store = _make_mock_store()
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 0
    assert result.rows_corrected == 0


@pytest.mark.asyncio
async def test_validation_skips_when_column_not_present() -> None:
    """DataFrame without cascade column should return immediately."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
        },
    )

    store = _make_mock_store(
        ancestor_chains={"task-1": ["holder-1"]},
    )
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 0
    assert result.rows_corrected == 0


@pytest.mark.asyncio
async def test_validation_skips_when_parent_chain_empty() -> None:
    """Ancestors exist in hierarchy but parent chain returns empty."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
            "office_phone": [None],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    # Hierarchy says ancestors exist, but store returns empty parent chain
    store = _make_mock_store(
        ancestor_chains={"task-1": ["holder-1", "business-1"]},
        parent_chains={"task-1": []},
    )
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 1
    assert result.rows_stale == 0
    assert result.rows_corrected == 0
    assert corrected_df["office_phone"][0] is None


@pytest.mark.asyncio
async def test_validation_result_duration_populated() -> None:
    """Verify duration_ms is populated on the result."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
            "office_phone": ["555-1111"],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    store = _make_mock_store()
    plugin = _make_mock_cascade_plugin()

    _, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.duration_ms >= 0.0


def test_feature_flag_default_is_enabled() -> None:
    """section_cascade_validation defaults to '1' (enabled).

    Per TDD-CASCADE-FAILURE-FIXES-001 section 5.2: Feature flag
    section_cascade_validation defaults to enabled. Setting to '0' disables.
    """
    from autom8_asana.settings import Settings

    settings = Settings()
    assert settings.runtime.section_cascade_validation == "1"


def test_feature_flag_disabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """When SECTION_CASCADE_VALIDATION=0, the setting reflects disabled state."""
    monkeypatch.setenv("SECTION_CASCADE_VALIDATION", "0")

    from autom8_asana.settings import Settings

    settings = Settings()
    assert settings.runtime.section_cascade_validation == "0"


@pytest.mark.asyncio
async def test_schema_driven_validates_all_cascade_columns() -> None:
    """When schema is passed, validates ALL its cascade columns, not just office_phone."""
    schema = MagicMock()
    schema.get_cascade_columns.return_value = [
        ("office_phone", "Office Phone"),
        ("vertical", "Vertical"),
    ]

    merged_df = pl.DataFrame(
        {"gid": ["t-1"], "office_phone": [None], "vertical": [None]},
        schema={"gid": pl.Utf8, "office_phone": pl.Utf8, "vertical": pl.Utf8},
    )

    store = _make_mock_store(
        ancestor_chains={"t-1": ["holder-1", "biz-1"]},
        parent_chains={
            "t-1": [
                {"gid": "holder-1", "custom_fields": []},
                {"gid": "biz-1", "custom_fields": []},
            ]
        },
    )
    plugin = _make_mock_cascade_plugin(
        field_values={
            "holder-1": {"Office Phone": None, "Vertical": None},
            "biz-1": {"Office Phone": "555-0001", "Vertical": "Chiro"},
        }
    )

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="test",
        schema=schema,
    )

    # Both cascade columns should be checked and corrected
    assert result.rows_checked == 2  # 1 row x 2 cascade columns
    assert result.rows_corrected == 2
    assert corrected_df["office_phone"][0] == "555-0001"
    assert corrected_df["vertical"][0] == "Chiro"


@pytest.mark.asyncio
async def test_no_schema_validates_nothing() -> None:
    """When schema=None, no cascade fields are checked (safe degradation)."""
    merged_df = pl.DataFrame(
        {"gid": ["t-1"], "office_phone": [None]},
        schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
    )

    store = _make_mock_store()
    plugin = _make_mock_cascade_plugin()

    _, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="test",
        # schema=None (default)
    )

    assert result.rows_checked == 0
    assert result.rows_corrected == 0
