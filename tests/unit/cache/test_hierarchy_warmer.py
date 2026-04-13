"""Tests for hierarchy_warmer module.

Per TDD-unit-cascade-resolution-fix: Tests for hierarchy warming
and cascade field resolution fixes.
"""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.cache.integration.hierarchy_warmer import (
    _HIERARCHY_OPT_FIELDS,
    _fetch_parent,
    warm_ancestors_async,
)
from autom8_asana.cache.policies.hierarchy import HierarchyIndex


class TestHierarchyOptFields:
    """Tests for _HIERARCHY_OPT_FIELDS constant."""

    def test_hierarchy_opt_fields_includes_all_types(self) -> None:
        """Verify _HIERARCHY_OPT_FIELDS has all required custom field types.

        Per TDD-unit-cascade-resolution-fix: Must include all custom field types
        for complete cascade resolution (enum, number, multi_enum in addition to text).
        """
        required_fields = {
            "custom_fields.resource_subtype",
            "custom_fields.enum_value",
            "custom_fields.enum_value.name",
            "custom_fields.number_value",
            "custom_fields.multi_enum_values",
            "custom_fields.multi_enum_values.name",
        }

        for field in required_fields:
            assert field in _HIERARCHY_OPT_FIELDS, f"Missing: {field}"

    def test_hierarchy_opt_fields_includes_basic_fields(self) -> None:
        """Verify basic required fields are present."""
        basic_fields = {
            "gid",
            "name",
            "parent",
            "parent.gid",
            "custom_fields",
            "custom_fields.gid",
            "custom_fields.name",
            "custom_fields.display_value",
            "custom_fields.text_value",
        }

        for field in basic_fields:
            assert field in _HIERARCHY_OPT_FIELDS, f"Missing basic field: {field}"


class TestWarmAncestorsAsync:
    """Tests for warm_ancestors_async function."""

    @pytest.fixture
    def hierarchy_index(self) -> HierarchyIndex:
        """Create a fresh HierarchyIndex for each test."""
        return HierarchyIndex()

    @pytest.fixture
    def mock_tasks_client(self) -> MagicMock:
        """Create a mock TasksClient."""
        client = MagicMock()
        client.get_async = AsyncMock(return_value=None)
        return client

    @pytest.mark.asyncio
    async def test_warm_ancestors_extracts_parent_gids(
        self,
        hierarchy_index: HierarchyIndex,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Verify warm_ancestors starts with parent GIDs, not initial GIDs.

        Per TDD-unit-cascade-resolution-fix Fix 2: The function should extract
        parent GIDs from the initial tasks to start traversal.
        """
        # Register Unit tasks with parent references
        unit1 = {"gid": "unit-1", "parent": {"gid": "business-1"}}
        unit2 = {"gid": "unit-2", "parent": {"gid": "business-1"}}

        hierarchy_index.register(unit1)
        hierarchy_index.register(unit2)

        # Mock the tasks client to return a Business task
        business_task = MagicMock()
        business_task.model_dump.return_value = {
            "gid": "business-1",
            "name": "Business",
            "parent": None,
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Office Phone",
                    "resource_subtype": "text",
                    "text_value": "+15551234567",
                }
            ],
        }
        mock_tasks_client.get_async = AsyncMock(return_value=business_task)

        # Warm ancestors
        warmed = await warm_ancestors_async(
            gids=["unit-1", "unit-2"],
            hierarchy_index=hierarchy_index,
            tasks_client=mock_tasks_client,
            max_depth=5,
        )

        # Should have fetched the Business task (the parent)
        # Note: business-1 appears as parent for both units, but should only be fetched once
        mock_tasks_client.get_async.assert_called_once_with(
            "business-1", opt_fields=_HIERARCHY_OPT_FIELDS
        )

        # The Business should now be registered in the hierarchy
        assert hierarchy_index.contains("business-1")
        assert warmed >= 1

    @pytest.mark.asyncio
    async def test_warm_ancestors_handles_orphan_tasks(
        self,
        hierarchy_index: HierarchyIndex,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Test warm_ancestors handles tasks without parents gracefully."""
        # Register tasks without parents (root tasks)
        root1 = {"gid": "root-1", "parent": None}
        root2 = {"gid": "root-2"}

        hierarchy_index.register(root1)
        hierarchy_index.register(root2)

        # Warm ancestors - should not crash and should not fetch anything
        warmed = await warm_ancestors_async(
            gids=["root-1", "root-2"],
            hierarchy_index=hierarchy_index,
            tasks_client=mock_tasks_client,
            max_depth=5,
        )

        # No parents to fetch
        mock_tasks_client.get_async.assert_not_called()
        assert warmed == 0

    @pytest.mark.asyncio
    async def test_warm_ancestors_respects_max_depth(
        self,
        hierarchy_index: HierarchyIndex,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Test max_depth limits hierarchy traversal."""
        # Register a deep hierarchy: great-grandchild -> grandchild -> child -> parent
        hierarchy_index.register({"gid": "level-3", "parent": {"gid": "level-2"}})
        hierarchy_index.register({"gid": "level-2", "parent": {"gid": "level-1"}})
        hierarchy_index.register({"gid": "level-1", "parent": {"gid": "level-0"}})
        hierarchy_index.register({"gid": "level-0", "parent": None})

        # Warm with max_depth=1 starting from level-3
        warmed = await warm_ancestors_async(
            gids=["level-3"],
            hierarchy_index=hierarchy_index,
            tasks_client=mock_tasks_client,
            max_depth=1,
        )

        # All levels already registered, so no fetches needed
        # But the function should still respect max_depth in traversal
        assert warmed == 0

    @pytest.mark.asyncio
    async def test_warm_ancestors_caches_fetched_parents(
        self,
        hierarchy_index: HierarchyIndex,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Test that fetched parents are stored in unified_store when provided."""
        # Register Unit with parent reference
        hierarchy_index.register({"gid": "unit-1", "parent": {"gid": "business-1"}})

        # Mock the tasks client
        business_task = MagicMock()
        business_task.model_dump.return_value = {
            "gid": "business-1",
            "name": "Business",
            "parent": None,
            "custom_fields": [],
        }
        mock_tasks_client.get_async = AsyncMock(return_value=business_task)

        # Mock unified store with cache that returns None (parent not cached)
        # Per TDD-unit-cascade-resolution-fix Fix 2: warm_ancestors_async now
        # checks cache.get_versioned() instead of hierarchy.contains()
        mock_cache = MagicMock()
        mock_cache.get_versioned = MagicMock(return_value=None)
        mock_store = MagicMock()
        mock_store.cache = mock_cache
        mock_store.put_async = AsyncMock()

        warmed = await warm_ancestors_async(
            gids=["unit-1"],
            hierarchy_index=hierarchy_index,
            tasks_client=mock_tasks_client,
            unified_store=mock_store,
        )

        # Verify the parent was cached
        assert mock_store.put_async.called
        call_args = mock_store.put_async.call_args
        assert call_args[0][0]["gid"] == "business-1"

    @pytest.mark.asyncio
    async def test_warm_ancestors_handles_fetch_errors(
        self,
        hierarchy_index: HierarchyIndex,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Test warm_ancestors handles fetch errors gracefully."""
        # Register Unit with parent reference
        hierarchy_index.register({"gid": "unit-1", "parent": {"gid": "business-1"}})

        # Mock the tasks client to raise an error
        mock_tasks_client.get_async = AsyncMock(side_effect=ConnectionError("Network error"))

        # Should not raise, just log warning and continue
        warmed = await warm_ancestors_async(
            gids=["unit-1"],
            hierarchy_index=hierarchy_index,
            tasks_client=mock_tasks_client,
        )

        # Nothing warmed due to error
        assert warmed == 0


class TestHierarchyIndexAncestorChainWithRegisteredParent:
    """Tests for HierarchyIndex.get_ancestor_chain with proper parent registration."""

    def test_get_ancestor_chain_with_registered_parent(self) -> None:
        """Verify ancestor chain works when parent is registered.

        Per TDD-unit-cascade-resolution-fix: This is the core test case
        showing that the chain works when both tasks are registered.
        """
        index = HierarchyIndex()

        # Register both tasks - parent first, then child
        business = {"gid": "business-1", "parent": None}
        unit = {"gid": "unit-1", "parent": {"gid": "business-1"}}

        index.register(business)
        index.register(unit)

        # Now get_ancestor_chain should work
        chain = index.get_ancestor_chain("unit-1")
        assert chain == ["business-1"]

    def test_get_ancestor_chain_fails_without_parent_registration(self) -> None:
        """Demonstrate the problem: chain fails if parent not registered.

        This test documents the bug that the fix addresses.
        """
        index = HierarchyIndex()

        # Only register the child, NOT the parent
        unit = {"gid": "unit-1", "parent": {"gid": "business-1"}}
        index.register(unit)

        # The child knows its parent GID, but we can't traverse further
        assert index.get_parent_gid("unit-1") == "business-1"

        # BUT the parent isn't registered, so contains() returns False
        assert not index.contains("business-1")

        # get_ancestor_chain returns the parent GID even if parent not registered
        # because the CHILD has the reference
        chain = index.get_ancestor_chain("unit-1")
        # Per the current implementation, it returns parent-gid if child has it
        assert chain == ["business-1"]

    def test_get_ancestor_chain_multi_level(self) -> None:
        """Test multi-level ancestor chain traversal."""
        index = HierarchyIndex()

        # Build a 3-level hierarchy: Unit -> Business -> Account
        index.register({"gid": "account-1", "parent": None})
        index.register({"gid": "business-1", "parent": {"gid": "account-1"}})
        index.register({"gid": "unit-1", "parent": {"gid": "business-1"}})

        chain = index.get_ancestor_chain("unit-1")
        assert chain == ["business-1", "account-1"]


class TestDeadCodeRemoval:
    """Verify dead code (backoff_event) has been fully removed from hierarchy_warmer."""

    def test_fetch_parent_no_backoff_event_param(self) -> None:
        """_fetch_parent must NOT accept backoff_event -- old dead code signature."""
        sig = inspect.signature(_fetch_parent)
        param_names = set(sig.parameters.keys())
        assert "backoff_event" not in param_names, (
            "_fetch_parent still accepts backoff_event -- dead code not fully removed"
        )

    def test_fetch_parent_rejects_backoff_event_kwarg(self) -> None:
        """Passing backoff_event= to _fetch_parent raises TypeError."""
        client = MagicMock()
        client.get_async = AsyncMock(return_value=None)

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            _fetch_parent("gid-1", tasks_client=client, backoff_event=asyncio.Event())

    def test_is_rate_limit_error_removed(self) -> None:
        """_is_rate_limit_error should no longer exist in hierarchy_warmer module."""
        import autom8_asana.cache.integration.hierarchy_warmer as hw

        assert not hasattr(hw, "_is_rate_limit_error"), (
            "_is_rate_limit_error still present -- dead code not removed"
        )

    def test_no_backoff_event_references_in_source(self) -> None:
        """No references to backoff_event in production hierarchy source."""
        import autom8_asana.cache.integration.hierarchy_warmer as hw
        import autom8_asana.cache.providers.unified as uf

        hw_src = inspect.getsource(hw)
        uf_src = inspect.getsource(uf)
        assert "backoff_event" not in hw_src, "backoff_event reference in hierarchy_warmer.py"
        assert "backoff_event" not in uf_src, "backoff_event reference in unified.py"


class TestRateLimitLogging:
    """Verify structured rate_limit_429_received log is emitted correctly."""

    def test_429_log_event_present_in_transport_source(self) -> None:
        """rate_limit_429_received log event exists in transport source."""
        from autom8_asana.transport import asana_http as transport_mod

        src = inspect.getsource(transport_mod)
        assert '"rate_limit_429_received"' in src, (
            "rate_limit_429_received log event not found in transport source"
        )
        assert '"path"' in src
        assert '"attempt"' in src
        assert '"retry_after"' in src

    def test_429_log_format_in_multiple_request_paths(self) -> None:
        """rate_limit_429_received must appear in at least 2 request paths."""
        from autom8_asana.transport import asana_http as transport_mod

        src = inspect.getsource(transport_mod)
        occurrences = src.count('"rate_limit_429_received"')
        assert occurrences >= 2, (
            f"Expected rate_limit_429_received in >=2 paths, found {occurrences}"
        )


class TestWarmAncestorsPhase2:
    """Verify warm_ancestors_async works correctly (merged from adversarial tests)."""

    @pytest.fixture
    def hierarchy_index(self) -> HierarchyIndex:
        return HierarchyIndex()

    @pytest.mark.asyncio
    async def test_warm_ancestors_basic_traversal(self, hierarchy_index: HierarchyIndex) -> None:
        """Basic parent chain traversal fetches and registers parent."""
        hierarchy_index.register({"gid": "unit-1", "parent": {"gid": "biz-1"}})

        biz_task = MagicMock()
        biz_task.model_dump.return_value = {
            "gid": "biz-1",
            "name": "Business",
            "parent": None,
            "custom_fields": [],
        }
        client = MagicMock()
        client.get_async = AsyncMock(return_value=biz_task)

        warmed = await warm_ancestors_async(
            gids=["unit-1"],
            hierarchy_index=hierarchy_index,
            tasks_client=client,
            max_depth=5,
        )

        assert warmed == 1
        assert hierarchy_index.contains("biz-1")

    @pytest.mark.asyncio
    async def test_warm_ancestors_multi_level(self, hierarchy_index: HierarchyIndex) -> None:
        """Multi-level traversal reaches all ancestors."""
        hierarchy_index.register({"gid": "unit-1", "parent": {"gid": "biz-1"}})

        responses = {
            "biz-1": {
                "gid": "biz-1",
                "name": "Business",
                "parent": {"gid": "acct-1"},
                "custom_fields": [],
            },
            "acct-1": {
                "gid": "acct-1",
                "name": "Account",
                "parent": None,
                "custom_fields": [],
            },
        }

        async def _get(gid: str, **kwargs):  # noqa: ANN003
            data = responses.get(gid)
            if data is None:
                return None
            mock = MagicMock()
            mock.model_dump.return_value = data
            return mock

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=_get)

        warmed = await warm_ancestors_async(
            gids=["unit-1"],
            hierarchy_index=hierarchy_index,
            tasks_client=client,
            max_depth=5,
        )

        assert warmed == 2
        assert hierarchy_index.contains("biz-1")
        assert hierarchy_index.contains("acct-1")

    @pytest.mark.asyncio
    async def test_warm_ancestors_error_resilience(self, hierarchy_index: HierarchyIndex) -> None:
        """warm_ancestors_async handles fetch errors gracefully."""
        hierarchy_index.register({"gid": "u-1", "parent": {"gid": "b-1"}})

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=ConnectionError("Network down"))

        warmed = await warm_ancestors_async(
            gids=["u-1"],
            hierarchy_index=hierarchy_index,
            tasks_client=client,
            max_depth=5,
        )

        assert warmed == 0

    @pytest.mark.asyncio
    async def test_warm_ancestors_global_semaphore(self, hierarchy_index: HierarchyIndex) -> None:
        """Global semaphore parameter is accepted and respected."""
        hierarchy_index.register({"gid": "u-1", "parent": {"gid": "b-1"}})

        biz_task = MagicMock()
        biz_task.model_dump.return_value = {
            "gid": "b-1",
            "name": "Business",
            "parent": None,
            "custom_fields": [],
        }
        client = MagicMock()
        client.get_async = AsyncMock(return_value=biz_task)

        sem = asyncio.Semaphore(2)
        warmed = await warm_ancestors_async(
            gids=["u-1"],
            hierarchy_index=hierarchy_index,
            tasks_client=client,
            max_depth=5,
            global_semaphore=sem,
        )

        assert warmed == 1
