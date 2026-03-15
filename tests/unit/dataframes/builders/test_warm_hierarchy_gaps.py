"""Tests for _warm_hierarchy_gaps_async fix in ProgressiveProjectBuilder.

Per WS-1-cascade-null-fix: Validates that _warm_hierarchy_gaps_async fetches
full task data from the API instead of storing GID-only stubs. The stubs
lacked the ``parent`` field needed by put_batch_async's hierarchy warming
to discover ancestor levels (e.g., unit_holder -> business), causing cascade
fields like office_phone to remain null for ~30% of units.

Root Cause:
    _warm_hierarchy_gaps_async created stub dicts ``[{"gid": gid}]`` and passed
    them to ``put_batch_async(warm_hierarchy=True)``. Without a ``parent`` field,
    ``_fetch_immediate_parents`` found no parents to fetch, leaving the hierarchy
    chain incomplete at the unit_holder level.

Fix:
    Fetch full task data from the API before calling put_batch_async, ensuring
    the ``parent`` field is present so hierarchy warming discovers the complete
    chain (unit -> unit_holder -> business).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.builders.fields import BASE_OPT_FIELDS

# ---------------------------------------------------------------------------
# Test data: 3-level hierarchy  Unit -> UnitHolder -> Business
# ---------------------------------------------------------------------------

BUSINESS_TASK_DICT = {
    "gid": "business-001",
    "name": "Test Business",
    "parent": None,
    "resource_subtype": None,
    "completed": None,
    "completed_at": None,
    "created_at": "2026-01-01T00:00:00Z",
    "modified_at": "2026-01-06T12:00:00Z",
    "due_on": None,
    "tags": [],
    "memberships": [],
    "custom_fields": [
        {
            "gid": "cf-phone",
            "name": "Office Phone",
            "resource_subtype": "text",
            "text_value": "+15551234567",
            "display_value": "+15551234567",
        },
    ],
}

UNIT_HOLDER_TASK_DICT = {
    "gid": "unit-holder-001",
    "name": "Unit Holder 1",
    "parent": {"gid": "business-001"},
    "resource_subtype": None,
    "completed": None,
    "completed_at": None,
    "created_at": "2026-01-01T00:00:00Z",
    "modified_at": "2026-01-06T12:00:00Z",
    "due_on": None,
    "tags": [],
    "memberships": [],
    "custom_fields": [],
}


def _make_mock_task(data: dict[str, Any]) -> MagicMock:
    """Create a mock Task-like object from a dict."""
    task = MagicMock()
    task.gid = data["gid"]
    task.name = data.get("name", "")
    task.resource_subtype = data.get("resource_subtype")
    task.completed = data.get("completed")
    task.completed_at = data.get("completed_at")
    task.created_at = data.get("created_at")
    task.modified_at = data.get("modified_at")
    task.due_on = data.get("due_on")
    task.tags = data.get("tags", [])
    task.memberships = data.get("memberships", [])
    task.custom_fields = data.get("custom_fields", [])

    parent_data = data.get("parent")
    if parent_data and isinstance(parent_data, dict):
        parent = MagicMock()
        parent.gid = parent_data["gid"]
        parent.model_dump = MagicMock(return_value=parent_data)
        task.parent = parent
    else:
        task.parent = None

    task.model_dump = MagicMock(return_value=data)

    return task


def _make_merged_df_with_parent_gids() -> pl.DataFrame:
    """Create a merged DataFrame with unit GIDs and parent_gid column."""
    return pl.DataFrame(
        {
            "gid": ["unit-001", "unit-002"],
            "parent_gid": ["unit-holder-001", "unit-holder-001"],
            "name": ["Unit 1", "Unit 2"],
            "office_phone": [None, None],
        },
        schema={
            "gid": pl.Utf8,
            "parent_gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )


class TestWarmHierarchyGapsFetchesFullData:
    """Verify that _warm_hierarchy_gaps_async fetches full task data from API."""

    @pytest.mark.asyncio
    async def test_fetches_from_api_not_stubs(self) -> None:
        """The fix must fetch full task data, not pass GID-only stubs.

        Before the fix, _warm_hierarchy_gaps_async created stubs like
        ``[{"gid": "unit-holder-001"}]`` and passed them to put_batch_async.
        Without a ``parent`` field, the hierarchy warming could not discover
        the unit_holder -> business link. The fix fetches full task data
        from the API so the parent field is present.
        """
        from autom8_asana.dataframes.builders.progressive import (
            ProgressiveProjectBuilder,
        )

        # Setup mocks
        mock_client = MagicMock()

        # Mock tasks.get_async to return unit_holder with parent info
        mock_task = _make_mock_task(UNIT_HOLDER_TASK_DICT)
        mock_client.tasks.get_async = AsyncMock(return_value=mock_task)

        mock_store = MagicMock()
        # Cache check: unit-holder-001 is NOT cached (triggers fetch)
        mock_store.cache.get_versioned.return_value = None
        mock_store.put_batch_async = AsyncMock(return_value=1)

        mock_schema = MagicMock()
        mock_schema.columns = []
        mock_schema.to_polars_schema.return_value = {}
        mock_schema.version = "1.0.0"

        mock_persistence = MagicMock()

        # Patch settings to avoid real config access
        with patch(
            "autom8_asana.dataframes.builders.progressive.get_settings"
        ) as mock_settings:
            mock_settings.return_value.runtime.section_cascade_validation = "1"
            mock_settings.return_value.pacing.hierarchy_batch_delay = 0.0
            mock_settings.return_value.pacing.hierarchy_batch_size = 10
            mock_settings.return_value.pacing.hierarchy_threshold = 100

            builder = ProgressiveProjectBuilder(
                client=mock_client,
                project_gid="test-project",
                entity_type="unit",
                schema=mock_schema,
                persistence=mock_persistence,
                store=mock_store,
            )

        df = _make_merged_df_with_parent_gids()
        result = await builder._warm_hierarchy_gaps_async(df)

        # Verify: API was called to fetch the full task
        mock_client.tasks.get_async.assert_called_once_with(
            "unit-holder-001", opt_fields=BASE_OPT_FIELDS
        )

        # Verify: put_batch_async was called with task data that has parent field
        mock_store.put_batch_async.assert_called_once()
        call_args = mock_store.put_batch_async.call_args
        task_dicts = call_args[0][0]
        assert len(task_dicts) == 1
        assert task_dicts[0]["gid"] == "unit-holder-001"
        # The critical assertion: parent field must be present
        assert task_dicts[0]["parent"] is not None
        assert task_dicts[0]["parent"]["gid"] == "business-001"

        # Verify: warm_hierarchy was enabled
        assert call_args[1].get("warm_hierarchy") is True

        # Verify: returned count is correct
        assert result == 1

    @pytest.mark.asyncio
    async def test_skips_already_cached_parents(self) -> None:
        """Parents that are already cached should not be re-fetched."""
        from autom8_asana.dataframes.builders.progressive import (
            ProgressiveProjectBuilder,
        )

        mock_client = MagicMock()
        mock_client.tasks.get_async = AsyncMock()

        mock_store = MagicMock()
        # Cache check: unit-holder-001 IS cached
        mock_cached_entry = MagicMock()
        mock_store.cache.get_versioned.return_value = mock_cached_entry

        mock_schema = MagicMock()
        mock_schema.columns = []
        mock_schema.to_polars_schema.return_value = {}
        mock_schema.version = "1.0.0"

        mock_persistence = MagicMock()

        with patch(
            "autom8_asana.dataframes.builders.progressive.get_settings"
        ) as mock_settings:
            mock_settings.return_value.runtime.section_cascade_validation = "1"

            builder = ProgressiveProjectBuilder(
                client=mock_client,
                project_gid="test-project",
                entity_type="unit",
                schema=mock_schema,
                persistence=mock_persistence,
                store=mock_store,
            )

        df = _make_merged_df_with_parent_gids()
        result = await builder._warm_hierarchy_gaps_async(df)

        # Verify: API was NOT called (parent already cached)
        mock_client.tasks.get_async.assert_not_called()
        mock_store.put_batch_async.assert_not_called()

        # Verify: returned 0 (nothing to warm)
        assert result == 0

    @pytest.mark.asyncio
    async def test_handles_api_fetch_failure_gracefully(self) -> None:
        """If API fetch fails for a parent, continue with remaining parents."""
        from autom8_asana.dataframes.builders.progressive import (
            ProgressiveProjectBuilder,
        )

        mock_client = MagicMock()

        # First call fails, simulating API error
        mock_client.tasks.get_async = AsyncMock(return_value=None)

        mock_store = MagicMock()
        mock_store.cache.get_versioned.return_value = None
        mock_store.put_batch_async = AsyncMock(return_value=0)

        mock_schema = MagicMock()
        mock_schema.columns = []
        mock_schema.to_polars_schema.return_value = {}
        mock_schema.version = "1.0.0"

        mock_persistence = MagicMock()

        with patch(
            "autom8_asana.dataframes.builders.progressive.get_settings"
        ) as mock_settings:
            mock_settings.return_value.runtime.section_cascade_validation = "1"

            builder = ProgressiveProjectBuilder(
                client=mock_client,
                project_gid="test-project",
                entity_type="unit",
                schema=mock_schema,
                persistence=mock_persistence,
                store=mock_store,
            )

        df = _make_merged_df_with_parent_gids()
        result = await builder._warm_hierarchy_gaps_async(df)

        # API was called but returned None
        mock_client.tasks.get_async.assert_called_once()

        # put_batch_async should NOT be called (no tasks fetched)
        mock_store.put_batch_async.assert_not_called()

        # Result is 0 (nothing successfully warmed)
        assert result == 0

    @pytest.mark.asyncio
    async def test_no_store_returns_zero(self) -> None:
        """Without a store, _warm_hierarchy_gaps_async returns 0."""
        from autom8_asana.dataframes.builders.progressive import (
            ProgressiveProjectBuilder,
        )

        mock_client = MagicMock()
        mock_schema = MagicMock()
        mock_schema.columns = []
        mock_schema.to_polars_schema.return_value = {}
        mock_schema.version = "1.0.0"
        mock_persistence = MagicMock()

        with patch(
            "autom8_asana.dataframes.builders.progressive.get_settings"
        ) as mock_settings:
            mock_settings.return_value.runtime.section_cascade_validation = "1"

            builder = ProgressiveProjectBuilder(
                client=mock_client,
                project_gid="test-project",
                entity_type="unit",
                schema=mock_schema,
                persistence=mock_persistence,
                store=None,  # No store
            )

        df = _make_merged_df_with_parent_gids()
        result = await builder._warm_hierarchy_gaps_async(df)
        assert result == 0

    @pytest.mark.asyncio
    async def test_multiple_uncached_parents_fetched(self) -> None:
        """Multiple distinct uncached parents should all be fetched."""
        from autom8_asana.dataframes.builders.progressive import (
            ProgressiveProjectBuilder,
        )

        unit_holder_2 = {
            **UNIT_HOLDER_TASK_DICT,
            "gid": "unit-holder-002",
            "name": "Unit Holder 2",
        }

        mock_client = MagicMock()

        # Return different tasks for different GIDs
        async def mock_get_async(gid: str, **kwargs: Any) -> MagicMock | None:
            if gid == "unit-holder-001":
                return _make_mock_task(UNIT_HOLDER_TASK_DICT)
            elif gid == "unit-holder-002":
                return _make_mock_task(unit_holder_2)
            return None

        mock_client.tasks.get_async = AsyncMock(side_effect=mock_get_async)

        mock_store = MagicMock()
        mock_store.cache.get_versioned.return_value = None
        mock_store.put_batch_async = AsyncMock(return_value=2)

        mock_schema = MagicMock()
        mock_schema.columns = []
        mock_schema.to_polars_schema.return_value = {}
        mock_schema.version = "1.0.0"
        mock_persistence = MagicMock()

        with patch(
            "autom8_asana.dataframes.builders.progressive.get_settings"
        ) as mock_settings:
            mock_settings.return_value.runtime.section_cascade_validation = "1"

            builder = ProgressiveProjectBuilder(
                client=mock_client,
                project_gid="test-project",
                entity_type="unit",
                schema=mock_schema,
                persistence=mock_persistence,
                store=mock_store,
            )

        # DataFrame with two different parent GIDs
        df = pl.DataFrame(
            {
                "gid": ["unit-001", "unit-002", "unit-003"],
                "parent_gid": [
                    "unit-holder-001",
                    "unit-holder-002",
                    "unit-holder-001",
                ],
                "name": ["Unit 1", "Unit 2", "Unit 3"],
            },
            schema={"gid": pl.Utf8, "parent_gid": pl.Utf8, "name": pl.Utf8},
        )

        result = await builder._warm_hierarchy_gaps_async(df)

        # Both unit holders should have been fetched
        assert mock_client.tasks.get_async.call_count == 2

        # put_batch_async should have been called with 2 task dicts
        mock_store.put_batch_async.assert_called_once()
        task_dicts = mock_store.put_batch_async.call_args[0][0]
        assert len(task_dicts) == 2

        # Both should have parent field
        for td in task_dicts:
            assert td["parent"] is not None
            assert td["parent"]["gid"] == "business-001"

        assert result == 2


class TestWarmHierarchyGapsRootCause:
    """Tests that directly validate the root cause scenario.

    The root cause: When sections resume from S3, hierarchy reconstruction
    registers unit -> unit_holder links, but _warm_hierarchy_gaps_async
    previously stored GID-only stubs for unit_holders. These stubs had no
    ``parent`` field, so put_batch_async's _fetch_immediate_parents found
    no parents, leaving the unit_holder -> business chain incomplete.
    Cascade resolution for office_phone then failed.
    """

    @pytest.mark.asyncio
    async def test_stub_dicts_lack_parent_field(self) -> None:
        """Demonstrate that GID-only stubs lack the parent field.

        This test documents what the OLD code did wrong: it created
        ``[{"gid": gid}]`` stubs. When put_batch_async's
        _fetch_immediate_parents iterated these, it found no ``parent``
        key, so no parents were fetched.
        """
        stub = {"gid": "unit-holder-001"}
        assert "parent" not in stub, "Stubs lack parent field"

        # The fix creates full task dicts with parent info
        full_dict = UNIT_HOLDER_TASK_DICT
        assert "parent" in full_dict
        assert full_dict["parent"]["gid"] == "business-001"
