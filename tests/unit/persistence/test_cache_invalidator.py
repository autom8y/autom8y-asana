"""Tests for CacheInvalidator project-level DataFrameCache invalidation.

Per TDD-CACHE-INVALIDATION-001: CacheInvalidator must invalidate System B
(project-level DataFrameCache) after SaveSession commits, mirroring
MutationInvalidator._invalidate_project_dataframes().

Per ADR-CA-001: Conservative blanket invalidation for all succeeded entities.
Per ADR-CA-002: Optional dataframe_cache parameter with None default.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, call

import pytest

from autom8_asana.persistence.cache_invalidator import CacheInvalidator
from autom8_asana.persistence.models import SaveResult

# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

PROJECT_GID_1 = "1111111111111"
PROJECT_GID_2 = "2222222222222"
PROJECT_GID_3 = "3333333333333"


def _make_entity(
    gid: str,
    memberships: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Create a mock entity with optional memberships."""
    entity = MagicMock()
    entity.gid = gid
    if memberships is not None:
        entity.memberships = memberships
    else:
        # Explicitly remove memberships attribute so hasattr returns False
        del entity.memberships
    return entity


def _make_crud_result(succeeded: list[Any]) -> SaveResult:
    """Create a SaveResult with succeeded entities."""
    result = MagicMock(spec=SaveResult)
    result.succeeded = succeeded
    result.failed = []
    return result


def _make_cache_provider() -> MagicMock:
    """Create a mock cache provider (System A)."""
    cache = MagicMock()
    cache.invalidate = MagicMock()
    return cache


def _make_dataframe_cache() -> MagicMock:
    """Create a mock DataFrameCache (System B)."""
    df_cache = MagicMock()
    df_cache.invalidate_project = MagicMock()
    return df_cache


# ---------------------------------------------------------------------------
# Tests: Constructor Injection
# ---------------------------------------------------------------------------


class TestCacheInvalidatorInit:
    """Tests for CacheInvalidator constructor with dataframe_cache parameter."""

    def test_init_without_dataframe_cache(self) -> None:
        """CacheInvalidator without dataframe_cache defaults to None."""
        invalidator = CacheInvalidator(cache_provider=_make_cache_provider())
        assert invalidator._dataframe_cache is None

    def test_init_with_dataframe_cache(self) -> None:
        """CacheInvalidator stores dataframe_cache when provided."""
        mock_df_cache = _make_dataframe_cache()
        invalidator = CacheInvalidator(
            cache_provider=_make_cache_provider(),
            dataframe_cache=mock_df_cache,
        )
        assert invalidator._dataframe_cache is mock_df_cache


# ---------------------------------------------------------------------------
# Tests: No-op When dataframe_cache Is None (Backward Compatibility)
# ---------------------------------------------------------------------------


class TestCacheInvalidatorNoOp:
    """Tests that CacheInvalidator with dataframe_cache=None behaves identically
    to pre-CACHE-1 behavior (no project-level DataFrame invalidation)."""

    async def test_no_dataframe_cache_does_not_call_invalidate_project(self) -> None:
        """When dataframe_cache is None, no invalidate_project call is made.

        Per ADR-CA-002: Optional with None default means project-level
        DataFrame invalidation is silently skipped.
        """
        entity = _make_entity(
            "task-1",
            memberships=[{"project": {"gid": PROJECT_GID_1, "name": "P1"}}],
        )
        crud_result = _make_crud_result([entity])
        gid_lookup = {"task-1": entity}

        invalidator = CacheInvalidator(
            cache_provider=_make_cache_provider(),
            dataframe_cache=None,
        )
        # Should not raise AttributeError or any error
        await invalidator.invalidate_for_commit(crud_result, [], gid_lookup)


# ---------------------------------------------------------------------------
# Tests: Project-Level Invalidation on Commit
# ---------------------------------------------------------------------------


class TestProjectLevelInvalidation:
    """Tests for project-level DataFrameCache invalidation after commit."""

    async def test_invalidate_project_called_for_each_affected_project(self) -> None:
        """invalidate_project is called for each unique project GID in memberships.

        Per ADR-CA-001: All succeeded entities trigger invalidate_project.
        """
        mock_df_cache = _make_dataframe_cache()

        entity = _make_entity(
            "task-1",
            memberships=[
                {"project": {"gid": PROJECT_GID_1, "name": "P1"}},
                {"project": {"gid": PROJECT_GID_2, "name": "P2"}},
            ],
        )
        crud_result = _make_crud_result([entity])
        gid_lookup = {"task-1": entity}

        invalidator = CacheInvalidator(
            cache_provider=_make_cache_provider(),
            dataframe_cache=mock_df_cache,
        )
        await invalidator.invalidate_for_commit(crud_result, [], gid_lookup)

        # Both project GIDs should be invalidated
        assert mock_df_cache.invalidate_project.call_count == 2
        called_gids = {c.args[0] for c in mock_df_cache.invalidate_project.call_args_list}
        assert called_gids == {PROJECT_GID_1, PROJECT_GID_2}

    async def test_deduplication_across_entities_in_same_project(self) -> None:
        """invalidate_project is called once per project, not per entity.

        Per CACHE-1 design: A commit that touches 5 tasks in the same
        project triggers exactly one invalidate_project call.
        """
        mock_df_cache = _make_dataframe_cache()

        entities = [
            _make_entity(
                f"task-{i}",
                memberships=[{"project": {"gid": PROJECT_GID_1, "name": "P1"}}],
            )
            for i in range(5)
        ]
        crud_result = _make_crud_result(entities)
        gid_lookup = {f"task-{i}": entities[i] for i in range(5)}

        invalidator = CacheInvalidator(
            cache_provider=_make_cache_provider(),
            dataframe_cache=mock_df_cache,
        )
        await invalidator.invalidate_for_commit(crud_result, [], gid_lookup)

        # Only one call despite 5 entities
        assert mock_df_cache.invalidate_project.call_count == 1
        mock_df_cache.invalidate_project.assert_called_once_with(PROJECT_GID_1)


# ---------------------------------------------------------------------------
# Tests: Failure Isolation (Fire-and-Forget)
# ---------------------------------------------------------------------------


class TestProjectInvalidationFailureIsolation:
    """Tests that project-level invalidation failures do not propagate."""

    async def test_invalidation_failure_does_not_fail_commit(self) -> None:
        """RuntimeError in invalidate_project does not propagate.

        Per NFR-DEGRADE-001: Invalidation failure must not fail commit.
        """
        mock_df_cache = _make_dataframe_cache()
        mock_df_cache.invalidate_project.side_effect = RuntimeError("cache down")

        entity = _make_entity(
            "task-1",
            memberships=[{"project": {"gid": PROJECT_GID_1, "name": "P1"}}],
        )
        crud_result = _make_crud_result([entity])
        gid_lookup = {"task-1": entity}

        invalidator = CacheInvalidator(
            cache_provider=_make_cache_provider(),
            dataframe_cache=mock_df_cache,
        )
        # Must not raise
        await invalidator.invalidate_for_commit(crud_result, [], gid_lookup)

    async def test_invalidation_failure_logs_warning(self) -> None:
        """Warning logged with 'project_dataframe_invalidation_failed' on failure."""
        mock_df_cache = _make_dataframe_cache()
        mock_df_cache.invalidate_project.side_effect = RuntimeError("cache down")

        mock_log = MagicMock()

        entity = _make_entity(
            "task-1",
            memberships=[{"project": {"gid": PROJECT_GID_1, "name": "P1"}}],
        )
        crud_result = _make_crud_result([entity])
        gid_lookup = {"task-1": entity}

        invalidator = CacheInvalidator(
            cache_provider=_make_cache_provider(),
            log=mock_log,
            dataframe_cache=mock_df_cache,
        )
        await invalidator.invalidate_for_commit(crud_result, [], gid_lookup)

        # Verify warning logged with correct event name
        warning_calls = [str(c) for c in mock_log.warning.call_args_list]
        assert any("project_dataframe_invalidation_failed" in c for c in warning_calls)


# ---------------------------------------------------------------------------
# Tests: Edge Cases
# ---------------------------------------------------------------------------


class TestProjectInvalidationEdgeCases:
    """Tests for edge cases in project-level invalidation."""

    async def test_empty_commit_batch_no_invalidation(self) -> None:
        """Empty succeeded list triggers no invalidation calls.

        Per FR-INVALIDATE-005: Batch efficiency -- no work for empty batch.
        """
        mock_df_cache = _make_dataframe_cache()

        crud_result = _make_crud_result([])
        gid_lookup: dict[str, Any] = {}

        invalidator = CacheInvalidator(
            cache_provider=_make_cache_provider(),
            dataframe_cache=mock_df_cache,
        )
        await invalidator.invalidate_for_commit(crud_result, [], gid_lookup)

        mock_df_cache.invalidate_project.assert_not_called()

    async def test_entity_without_memberships_no_project_invalidation(self) -> None:
        """Entity without memberships does not contribute project GIDs.

        If an entity has no .memberships attribute (e.g., a lightweight
        entity or entity loaded without expand), project-level invalidation
        is skipped for that entity.
        """
        mock_df_cache = _make_dataframe_cache()

        entity = _make_entity("task-1", memberships=None)
        crud_result = _make_crud_result([entity])
        gid_lookup = {"task-1": entity}

        invalidator = CacheInvalidator(
            cache_provider=_make_cache_provider(),
            dataframe_cache=mock_df_cache,
        )
        await invalidator.invalidate_for_commit(crud_result, [], gid_lookup)

        mock_df_cache.invalidate_project.assert_not_called()
