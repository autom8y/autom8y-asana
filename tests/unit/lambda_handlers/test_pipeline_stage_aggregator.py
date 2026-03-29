"""Unit tests for pipeline stage aggregation post-warm step.

Per ADR-pipeline-stage-aggregation Phase 2: Tests the _aggregate_pipeline_stages
function that scans pipeline DataFrames from cache and produces a per-unit summary
of the latest active process.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch as stdlib_patch

import polars as pl
import pytest

from autom8_asana.lambda_handlers.pipeline_stage_aggregator import (
    _PIPELINE_ENTITY_PREFIX,
    _aggregate_pipeline_stages,
    _derive_pipeline_type,
)

# Patch target for the deferred import inside _aggregate_pipeline_stages
_REGISTRY_PATCH_TARGET = "autom8_asana.core.entity_registry.get_registry"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 3, 29, 12, 0, 0, tzinfo=UTC)


def _make_pipeline_df(
    *,
    office_phones: list[str | None],
    verticals: list[str | None],
    sections: list[str | None],
    created_offsets_hours: list[int],
    is_completed: list[bool] | None = None,
) -> pl.DataFrame:
    """Build a minimal pipeline DataFrame with required columns.

    Uses BASE_COLUMNS subset relevant to the aggregator:
    gid, name, type, created, is_completed, section, office_phone, vertical.
    """
    n = len(office_phones)
    if is_completed is None:
        is_completed = [False] * n

    return pl.DataFrame(
        {
            "gid": [f"gid-{i}" for i in range(n)],
            "name": [f"Task {i}" for i in range(n)],
            "type": ["Process"] * n,
            "date": [None] * n,
            "created": [_NOW + timedelta(hours=h) for h in created_offsets_hours],
            "due_on": [None] * n,
            "is_completed": is_completed,
            "completed_at": [None] * n,
            "url": [f"https://app.asana.com/0/0/gid-{i}" for i in range(n)],
            "last_modified": [_NOW] * n,
            "section": sections,
            "tags": [[] for _ in range(n)],
            "parent_gid": [None] * n,
            "office_phone": office_phones,
            "vertical": verticals,
            "pipeline_type": [None] * n,
        },
        schema_overrides={
            "created": pl.Datetime("us", "UTC"),
            "completed_at": pl.Datetime("us", "UTC"),
            "last_modified": pl.Datetime("us", "UTC"),
            "date": pl.Date,
            "due_on": pl.Date,
        },
    )


def _make_cache_entry(*, dataframe: pl.DataFrame | None = None) -> MagicMock:
    """Create a mock cache entry with a configurable dataframe attribute."""
    entry = MagicMock()
    entry.dataframe = dataframe
    return entry


def _make_mock_cache(
    entity_dfs: dict[str, pl.DataFrame],
) -> MagicMock:
    """Create a mock cache that returns DataFrames by entity type.

    Args:
        entity_dfs: Mapping of entity_name -> DataFrame.
    """
    cache = MagicMock()

    async def _get(project_gid: str, entity_type: str) -> MagicMock | None:
        df = entity_dfs.get(entity_type)
        if df is None:
            return None
        return _make_cache_entry(dataframe=df)

    cache.get_async = AsyncMock(side_effect=_get)
    return cache


def _mock_entity_registry(entity_names: list[str]) -> MagicMock:
    """Create a mock EntityRegistry that returns descriptors for given names."""
    registry = MagicMock()

    def _get(name: str) -> MagicMock | None:
        if name in entity_names:
            desc = MagicMock()
            desc.name = name
            desc.primary_project_gid = f"project-{name}"
            return desc
        return None

    registry.get = _get
    return registry


# ---------------------------------------------------------------------------
# _derive_pipeline_type tests
# ---------------------------------------------------------------------------


class TestDerivePipelineType:
    """pipeline_type is correctly derived from entity name."""

    def test_sales(self) -> None:
        assert _derive_pipeline_type("process_sales") == "sales"

    def test_onboarding(self) -> None:
        assert _derive_pipeline_type("process_onboarding") == "onboarding"

    def test_account_error(self) -> None:
        assert _derive_pipeline_type("process_account_error") == "account_error"

    def test_month1(self) -> None:
        assert _derive_pipeline_type("process_month1") == "month1"

    def test_expansion(self) -> None:
        assert _derive_pipeline_type("process_expansion") == "expansion"


# ---------------------------------------------------------------------------
# Zero pipeline entities
# ---------------------------------------------------------------------------


class TestZeroPipelineEntities:
    """Returns None when no pipeline entities are in completed_entities."""

    @pytest.mark.asyncio
    async def test_returns_none_with_no_pipeline_entities(self) -> None:
        """completed_entities has no process_ entries -> returns None."""
        result = await _aggregate_pipeline_stages(
            completed_entities=["unit", "offer", "contact"],
            cache=MagicMock(),
            invocation_id="test-zero-1",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_with_empty_completed(self) -> None:
        """Empty completed_entities -> returns None."""
        result = await _aggregate_pipeline_stages(
            completed_entities=[],
            cache=MagicMock(),
            invocation_id="test-zero-2",
        )
        assert result is None


# ---------------------------------------------------------------------------
# Single pipeline DF
# ---------------------------------------------------------------------------


class TestSinglePipelineDF:
    """One pipeline DF produces correct summary columns."""

    @pytest.mark.asyncio
    async def test_single_pipeline_returns_summary(
        self,
    ) -> None:
        """Single pipeline DF with one active task -> summary with correct columns."""
        df = _make_pipeline_df(
            office_phones=["555-1234"],
            verticals=["dental"],
            sections=["Outreach"],
            created_offsets_hours=[0],
        )

        entity_dfs = {"process_outreach": df}
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(["process_outreach"])

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["unit", "offer", "process_outreach"],
                cache=cache,
                invocation_id="test-single-1",
            )

        assert result is not None
        assert set(result.columns) == {
            "office_phone",
            "vertical",
            "latest_process_type",
            "latest_process_section",
            "latest_created",
        }
        assert len(result) == 1
        row = result.row(0, named=True)
        assert row["office_phone"] == "555-1234"
        assert row["vertical"] == "dental"
        assert row["latest_process_type"] == "outreach"
        assert row["latest_process_section"] == "Outreach"


# ---------------------------------------------------------------------------
# Multiple pipeline DFs
# ---------------------------------------------------------------------------


class TestMultiplePipelineDFs:
    """Multiple pipeline DFs are concatenated and latest-by-created is picked."""

    @pytest.mark.asyncio
    async def test_concatenation_picks_latest_by_created(self) -> None:
        """Two pipelines for same phone/vertical -> picks most recent created."""
        # Sales: created 2 hours ago
        df_sales = _make_pipeline_df(
            office_phones=["555-1234"],
            verticals=["dental"],
            sections=["Proposal Sent"],
            created_offsets_hours=[-2],
        )

        # Onboarding: created 1 hour ago (more recent)
        df_onboard = _make_pipeline_df(
            office_phones=["555-1234"],
            verticals=["dental"],
            sections=["Welcome Call"],
            created_offsets_hours=[-1],
        )

        entity_dfs = {
            "process_sales": df_sales,
            "process_onboarding": df_onboard,
        }
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(
            ["process_sales", "process_onboarding"]
        )

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=[
                    "unit",
                    "process_sales",
                    "process_onboarding",
                ],
                cache=cache,
                invocation_id="test-multi-1",
            )

        assert result is not None
        assert len(result) == 1
        row = result.row(0, named=True)
        assert row["latest_process_type"] == "onboarding"
        assert row["latest_process_section"] == "Welcome Call"

    @pytest.mark.asyncio
    async def test_different_units_produce_separate_rows(self) -> None:
        """Two units in same pipeline -> two summary rows."""
        df = _make_pipeline_df(
            office_phones=["555-1234", "555-5678"],
            verticals=["dental", "chiro"],
            sections=["Section A", "Section B"],
            created_offsets_hours=[0, -1],
        )

        entity_dfs = {"process_sales": df}
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(["process_sales"])

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales"],
                cache=cache,
                invocation_id="test-multi-2",
            )

        assert result is not None
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Filtering: completed tasks are excluded
# ---------------------------------------------------------------------------


class TestCompletedTaskFiltering:
    """Completed tasks (is_completed=True) must be excluded."""

    @pytest.mark.asyncio
    async def test_completed_tasks_are_excluded(self) -> None:
        """Mix of active and completed -> only active appear in summary."""
        df = _make_pipeline_df(
            office_phones=["555-1234", "555-1234"],
            verticals=["dental", "dental"],
            sections=["Active Section", "Done Section"],
            created_offsets_hours=[-1, 0],  # Completed one is more recent
            is_completed=[False, True],
        )

        entity_dfs = {"process_sales": df}
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(["process_sales"])

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales"],
                cache=cache,
                invocation_id="test-filter-1",
            )

        assert result is not None
        assert len(result) == 1
        row = result.row(0, named=True)
        assert row["latest_process_section"] == "Active Section"

    @pytest.mark.asyncio
    async def test_all_completed_returns_none(self) -> None:
        """All tasks completed -> no active processes -> returns None."""
        df = _make_pipeline_df(
            office_phones=["555-1234"],
            verticals=["dental"],
            sections=["Done"],
            created_offsets_hours=[0],
            is_completed=[True],
        )

        entity_dfs = {"process_sales": df}
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(["process_sales"])

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales"],
                cache=cache,
                invocation_id="test-filter-2",
            )

        assert result is None


# ---------------------------------------------------------------------------
# Grouping: two processes for same phone/vertical
# ---------------------------------------------------------------------------


class TestGroupingPicksMostRecent:
    """When multiple active processes exist for the same (phone, vertical),
    the one with the most recent 'created' timestamp wins."""

    @pytest.mark.asyncio
    async def test_same_pipeline_two_tasks_picks_latest(self) -> None:
        """Two active tasks in same pipeline for same unit -> picks latest."""
        df = _make_pipeline_df(
            office_phones=["555-1234", "555-1234"],
            verticals=["dental", "dental"],
            sections=["Old Section", "New Section"],
            created_offsets_hours=[-5, -1],
        )

        entity_dfs = {"process_sales": df}
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(["process_sales"])

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales"],
                cache=cache,
                invocation_id="test-group-1",
            )

        assert result is not None
        assert len(result) == 1
        row = result.row(0, named=True)
        assert row["latest_process_section"] == "New Section"

    @pytest.mark.asyncio
    async def test_cross_pipeline_picks_latest(self) -> None:
        """Two pipelines, same unit: the one with more recent 'created' wins."""
        # Retention: created 10 hours ago
        df_retention = _make_pipeline_df(
            office_phones=["555-9999"],
            verticals=["chiro"],
            sections=["Account Review"],
            created_offsets_hours=[-10],
        )

        # Reactivation: created 2 hours ago (more recent)
        df_reactivation = _make_pipeline_df(
            office_phones=["555-9999"],
            verticals=["chiro"],
            sections=["Re-engage"],
            created_offsets_hours=[-2],
        )

        entity_dfs = {
            "process_retention": df_retention,
            "process_reactivation": df_reactivation,
        }
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(
            ["process_retention", "process_reactivation"]
        )

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=[
                    "process_retention",
                    "process_reactivation",
                ],
                cache=cache,
                invocation_id="test-group-2",
            )

        assert result is not None
        assert len(result) == 1
        row = result.row(0, named=True)
        assert row["latest_process_type"] == "reactivation"
        assert row["latest_process_section"] == "Re-engage"


# ---------------------------------------------------------------------------
# pipeline_type discriminator derivation
# ---------------------------------------------------------------------------


class TestPipelineTypeDiscriminator:
    """pipeline_type column is correctly derived from entity name."""

    @pytest.mark.asyncio
    async def test_pipeline_type_set_from_entity_name(self) -> None:
        """process_implementation -> latest_process_type='implementation'."""
        df = _make_pipeline_df(
            office_phones=["555-1111"],
            verticals=["dental"],
            sections=["Kickoff"],
            created_offsets_hours=[0],
        )

        entity_dfs = {"process_implementation": df}
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(["process_implementation"])

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_implementation"],
                cache=cache,
                invocation_id="test-disc-1",
            )

        assert result is not None
        row = result.row(0, named=True)
        assert row["latest_process_type"] == "implementation"


# ---------------------------------------------------------------------------
# Null grouping key handling
# ---------------------------------------------------------------------------


class TestNullGroupingKeys:
    """Rows with null office_phone or vertical are dropped before grouping."""

    @pytest.mark.asyncio
    async def test_null_office_phone_excluded(self) -> None:
        """Row with null office_phone is dropped."""
        df = _make_pipeline_df(
            office_phones=[None, "555-1234"],
            verticals=["dental", "dental"],
            sections=["A", "B"],
            created_offsets_hours=[0, -1],
        )

        entity_dfs = {"process_sales": df}
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(["process_sales"])

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales"],
                cache=cache,
                invocation_id="test-null-1",
            )

        assert result is not None
        assert len(result) == 1
        assert result.row(0, named=True)["office_phone"] == "555-1234"

    @pytest.mark.asyncio
    async def test_null_vertical_excluded(self) -> None:
        """Row with null vertical is dropped."""
        df = _make_pipeline_df(
            office_phones=["555-1234", "555-5678"],
            verticals=[None, "chiro"],
            sections=["A", "B"],
            created_offsets_hours=[0, -1],
        )

        entity_dfs = {"process_sales": df}
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(["process_sales"])

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales"],
                cache=cache,
                invocation_id="test-null-2",
            )

        assert result is not None
        assert len(result) == 1
        assert result.row(0, named=True)["vertical"] == "chiro"

    @pytest.mark.asyncio
    async def test_all_null_keys_returns_none(self) -> None:
        """All rows have null grouping keys -> returns None."""
        df = _make_pipeline_df(
            office_phones=[None],
            verticals=[None],
            sections=["A"],
            created_offsets_hours=[0],
        )

        entity_dfs = {"process_sales": df}
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(["process_sales"])

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales"],
                cache=cache,
                invocation_id="test-null-3",
            )

        assert result is None


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------


class TestErrorIsolation:
    """Exceptions must be caught and logged, never propagated."""

    @pytest.mark.asyncio
    async def test_cache_exception_returns_none(self) -> None:
        """Exception in cache.get_async -> returns None, no crash."""
        cache = MagicMock()
        cache.get_async = AsyncMock(side_effect=ConnectionError("cache down"))

        mock_registry = _mock_entity_registry(["process_sales"])

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales"],
                cache=cache,
                invocation_id="test-err-1",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_registry_exception_returns_none(self) -> None:
        """Exception in entity registry -> returns None, no crash."""
        with stdlib_patch(_REGISTRY_PATCH_TARGET, side_effect=RuntimeError("registry boom")):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales"],
                cache=MagicMock(),
                invocation_id="test-err-2",
            )

        assert result is None


# ---------------------------------------------------------------------------
# Cache entry edge cases
# ---------------------------------------------------------------------------


class TestCacheEdgeCases:
    """Edge cases in cache retrieval."""

    @pytest.mark.asyncio
    async def test_cache_returns_none_entry_skipped(self) -> None:
        """Cache returns None for a pipeline entity -> skipped, others still processed."""
        df_sales = _make_pipeline_df(
            office_phones=["555-1234"],
            verticals=["dental"],
            sections=["Sales"],
            created_offsets_hours=[0],
        )

        # process_outreach -> None in cache, process_sales -> has data
        entity_dfs = {"process_sales": df_sales}
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(
            ["process_sales", "process_outreach"]
        )

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales", "process_outreach"],
                cache=cache,
                invocation_id="test-cache-1",
            )

        assert result is not None
        assert len(result) == 1
        assert result.row(0, named=True)["latest_process_type"] == "sales"

    @pytest.mark.asyncio
    async def test_all_cache_entries_none_returns_none(self) -> None:
        """All pipeline cache entries are None -> returns None."""
        entity_dfs: dict[str, pl.DataFrame] = {}  # Nothing in cache
        cache = _make_mock_cache(entity_dfs)
        mock_registry = _mock_entity_registry(
            ["process_sales", "process_outreach"]
        )

        with stdlib_patch(_REGISTRY_PATCH_TARGET, return_value=mock_registry):
            result = await _aggregate_pipeline_stages(
                completed_entities=["process_sales", "process_outreach"],
                cache=cache,
                invocation_id="test-cache-2",
            )

        assert result is None
