"""Tests for grandparent fallback in DataFrameViewPlugin._resolve_cascade_from_dict.

Per TDD-CASCADE-FAILURE-FIXES-001 Fix 2: Validates that when the parent chain
has entries but none have the target field, the method tries fetching the
grandparent of the last chain entry as a final fallback.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin


@pytest.fixture
def mock_store() -> MagicMock:
    """Create a mock UnifiedTaskStore."""
    store = MagicMock()
    store.get_batch_async = AsyncMock(return_value={})
    store.get_parent_chain_async = AsyncMock(return_value=[])
    store.get_with_upgrade_async = AsyncMock(return_value=None)
    return store


@pytest.fixture
def cascade_schema() -> DataFrameSchema:
    """Create a schema with cascade fields."""
    return DataFrameSchema(
        name="cascade_test",
        task_type="Unit",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False, source=None),
            ColumnDef("name", "Utf8", nullable=False, source=None),
            ColumnDef("office_phone", "Utf8", nullable=True, source="cascade:Office Phone"),
        ],
        version="1.0.0",
    )


def _make_task_data(
    gid: str,
    parent_gid: str | None = None,
    office_phone: str | None = None,
) -> dict[str, Any]:
    """Create a task data dict for testing."""
    task: dict[str, Any] = {
        "gid": gid,
        "name": f"Task {gid}",
        "custom_fields": [],
    }
    if parent_gid:
        task["parent"] = {"gid": parent_gid}
    if office_phone:
        task["custom_fields"].append(
            {
                "gid": "cf-phone",
                "name": "Office Phone",
                "resource_subtype": "text",
                "text_value": office_phone,
            }
        )
    return task


class TestGrandparentFallback:
    """Tests for grandparent fallback in cascade resolution.

    Per TDD-CASCADE-FAILURE-FIXES-001 Fix 2: When the parent chain has
    entries but none contain the target field value, try fetching the
    grandparent of the last chain entry.
    """

    async def test_grandparent_fallback_resolves_field(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Grandparent has the field when parent chain entries do not.

        Scenario: parent chain = [Holder], Holder has no office_phone,
        Holder.parent.gid points to Business, Business has office_phone.
        """
        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        # Task data with parent reference
        task_data = _make_task_data("task-1", parent_gid="holder-1")

        # Parent chain: Holder with no phone, but has parent pointer to Business
        holder_data = _make_task_data("holder-1", parent_gid="business-1")
        mock_store.get_parent_chain_async.return_value = [holder_data]

        # Grandparent (Business) has the phone number
        business_data = _make_task_data("business-1", office_phone="555-999-0000")
        mock_store.get_with_upgrade_async.return_value = business_data

        result = await plugin._resolve_cascade_from_dict(task_data, "Office Phone")

        assert result == "555-999-0000"
        # Verify grandparent was fetched
        mock_store.get_with_upgrade_async.assert_called_once()
        call_kwargs = mock_store.get_with_upgrade_async.call_args
        assert call_kwargs[0][0] == "business-1"

    async def test_grandparent_fallback_skips_when_already_in_chain(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Grandparent already in chain does not trigger redundant fetch.

        Scenario: parent chain = [Holder, Business], Business is already in chain
        but has no value. The grandparent of Holder is Business (already searched).
        No additional fetch should happen.
        """
        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        task_data = _make_task_data("task-1", parent_gid="holder-1")

        # Parent chain: Holder and Business, neither has phone
        holder_data = _make_task_data("holder-1", parent_gid="business-1")
        business_data = _make_task_data("business-1")
        mock_store.get_parent_chain_async.return_value = [
            holder_data,
            business_data,
        ]

        result = await plugin._resolve_cascade_from_dict(task_data, "Office Phone")

        assert result is None
        # Grandparent fetch should NOT be called because business-1 is in chain
        mock_store.get_with_upgrade_async.assert_not_called()

    async def test_grandparent_fallback_noop_when_no_parent_on_last(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """No grandparent fetch when last chain entry has no parent pointer.

        Scenario: parent chain = [Business], Business has no parent and no phone.
        Should return None without any grandparent fetch.
        """
        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        task_data = _make_task_data("task-1", parent_gid="business-1")

        # Business has no parent (root entity) and no phone
        business_data: dict[str, Any] = {
            "gid": "business-1",
            "name": "Root Business",
            "custom_fields": [],
        }
        mock_store.get_parent_chain_async.return_value = [business_data]

        result = await plugin._resolve_cascade_from_dict(task_data, "Office Phone")

        assert result is None
        mock_store.get_with_upgrade_async.assert_not_called()

    async def test_grandparent_fallback_noop_when_chain_empty(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """No grandparent fallback when parent chain is empty.

        The existing empty-chain fallback path handles this case separately.
        """
        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        task_data = _make_task_data("task-1", parent_gid="holder-1")
        mock_store.get_parent_chain_async.return_value = []
        # The empty-chain fallback also uses get_with_upgrade_async
        # but for a different purpose (direct parent fetch).
        # Return None to exercise the None path.
        mock_store.get_with_upgrade_async.return_value = None

        result = await plugin._resolve_cascade_from_dict(task_data, "Office Phone")

        assert result is None

    async def test_grandparent_fallback_noop_when_grandparent_fetch_returns_none(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Grandparent fetch returns None (not cached), returns None."""
        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        task_data = _make_task_data("task-1", parent_gid="holder-1")

        # Holder has parent pointer but no phone
        holder_data = _make_task_data("holder-1", parent_gid="business-1")
        mock_store.get_parent_chain_async.return_value = [holder_data]

        # Grandparent fetch fails (not cached)
        mock_store.get_with_upgrade_async.return_value = None

        result = await plugin._resolve_cascade_from_dict(task_data, "Office Phone")

        assert result is None
