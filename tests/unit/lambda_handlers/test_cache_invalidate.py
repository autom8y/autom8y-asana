"""Unit tests for cache_invalidate Lambda handler.

Per TDD-CASCADE-FAILURE-FIXES-001 Fix 1: Tests for targeted project manifest
invalidation via the ``invalidate_project`` parameter, verifying idempotency,
composability with existing cache-clearing modes, and correct response shape.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.lambda_handlers.cache_invalidate import (
    InvalidateResponse,
    _invalidate_cache_async,
    handler_async,
)


class TestInvalidateResponse:
    """Tests for InvalidateResponse dataclass."""

    def test_projects_invalidated_defaults_to_zero(self) -> None:
        """Response has projects_invalidated=0 by default."""
        response = InvalidateResponse(success=True, message="ok")
        assert response.projects_invalidated == 0

    def test_to_dict_includes_projects_invalidated(self) -> None:
        """to_dict includes the projects_invalidated field."""
        response = InvalidateResponse(
            success=True,
            message="ok",
            projects_invalidated=1,
        )
        result = response.to_dict()
        assert "projects_invalidated" in result
        assert result["projects_invalidated"] == 1


class TestInvalidateProjectAsync:
    """Tests for targeted project manifest invalidation.

    Per TDD-CASCADE-FAILURE-FIXES-001 Fix 1 section 7.1: Verifies that the
    ``invalidate_project`` parameter correctly deletes S3 manifest and section
    parquet files, is idempotent, composable with clear_tasks, and produces
    the expected response shape.
    """

    @pytest.fixture
    def mock_persistence(self) -> MagicMock:
        """Create a mock SectionPersistence with async delete methods."""
        persistence = MagicMock()
        persistence.delete_section_files_async = AsyncMock(return_value=True)
        persistence.delete_manifest_async = AsyncMock(return_value=True)
        return persistence

    @pytest.fixture
    def _patch_tiered_cache(self) -> None:
        """Suppress TieredCacheProvider import (not needed for project invalidation tests)."""
        # We set clear_tasks=False in most tests, so this is only needed
        # when clear_tasks is True. Provided as a convenience fixture.

    @pytest.mark.asyncio
    async def test_invalidate_project_deletes_manifest_and_sections(
        self,
        mock_persistence: MagicMock,
    ) -> None:
        """Invoke with invalidate_project, assert both delete methods called."""
        with patch(
            "autom8_asana.dataframes.section_persistence.create_section_persistence",
            return_value=mock_persistence,
        ):
            response = await _invalidate_cache_async(
                clear_tasks=False,
                clear_dataframes=False,
                invalidate_project="1234567890",
            )

        assert response.success is True
        assert response.projects_invalidated == 1
        mock_persistence.delete_section_files_async.assert_awaited_once_with(
            "1234567890"
        )
        mock_persistence.delete_manifest_async.assert_awaited_once_with("1234567890")

    @pytest.mark.asyncio
    async def test_invalidate_project_idempotent(
        self,
        mock_persistence: MagicMock,
    ) -> None:
        """Invoke twice with same project GID, no error on second invocation."""
        with patch(
            "autom8_asana.dataframes.section_persistence.create_section_persistence",
            return_value=mock_persistence,
        ):
            response_1 = await _invalidate_cache_async(
                clear_tasks=False,
                clear_dataframes=False,
                invalidate_project="1234567890",
            )
            response_2 = await _invalidate_cache_async(
                clear_tasks=False,
                clear_dataframes=False,
                invalidate_project="1234567890",
            )

        assert response_1.success is True
        assert response_2.success is True
        assert response_1.projects_invalidated == 1
        assert response_2.projects_invalidated == 1
        # Both invocations should call delete methods (idempotent)
        assert mock_persistence.delete_section_files_async.await_count == 2
        assert mock_persistence.delete_manifest_async.await_count == 2

    @pytest.mark.asyncio
    async def test_invalidate_project_with_clear_tasks(
        self,
        mock_persistence: MagicMock,
    ) -> None:
        """Both clear_tasks=True and invalidate_project in same event."""
        mock_hot_tier = MagicMock()
        mock_cache = MagicMock()
        mock_cache.clear_all_tasks.return_value = {"redis": 10, "s3": 20}

        with (
            patch(
                "autom8_asana.dataframes.section_persistence.create_section_persistence",
                return_value=mock_persistence,
            ),
            patch(
                "autom8_asana.cache.backends.redis.RedisCacheProvider",
                return_value=mock_hot_tier,
            ),
            patch(
                "autom8_asana.cache.providers.tiered.TieredCacheProvider",
                return_value=mock_cache,
            ),
        ):
            response = await _invalidate_cache_async(
                clear_tasks=True,
                clear_dataframes=False,
                invalidate_project="9876543210",
            )

        assert response.success is True
        # Task cache was cleared
        assert response.tasks_cleared == {"redis": 10, "s3": 20}
        # Project was also invalidated
        assert response.projects_invalidated == 1
        mock_persistence.delete_section_files_async.assert_awaited_once_with(
            "9876543210"
        )
        mock_persistence.delete_manifest_async.assert_awaited_once_with("9876543210")
        mock_cache.clear_all_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_project_missing_gid_noop(self) -> None:
        """Invoke without invalidate_project, no section persistence calls."""
        with patch(
            "autom8_asana.dataframes.section_persistence.create_section_persistence",
        ) as mock_factory:
            response = await _invalidate_cache_async(
                clear_tasks=False,
                clear_dataframes=False,
                invalidate_project=None,
            )

        assert response.success is True
        assert response.projects_invalidated == 0
        # Factory should never be called when invalidate_project is None
        mock_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalidate_project_response_includes_count(
        self,
        mock_persistence: MagicMock,
    ) -> None:
        """Assert projects_invalidated field in response dict."""
        with patch(
            "autom8_asana.dataframes.section_persistence.create_section_persistence",
            return_value=mock_persistence,
        ):
            response = await _invalidate_cache_async(
                clear_tasks=False,
                clear_dataframes=False,
                invalidate_project="5555555555",
            )

        response_dict = response.to_dict()
        assert "projects_invalidated" in response_dict
        assert response_dict["projects_invalidated"] == 1
        assert response.success is True
        assert "manifest(s) invalidated" in response.message

    @pytest.mark.asyncio
    async def test_invalidate_project_no_project_response_zero_count(self) -> None:
        """Without invalidate_project, projects_invalidated is 0 in response."""
        response = await _invalidate_cache_async(
            clear_tasks=False,
            clear_dataframes=False,
            invalidate_project=None,
        )

        response_dict = response.to_dict()
        assert response_dict["projects_invalidated"] == 0
        assert "manifest(s) invalidated" not in response.message


class TestHandlerAsyncInvalidateProject:
    """Tests for handler_async threading of invalidate_project."""

    @pytest.mark.asyncio
    async def test_handler_async_passes_invalidate_project(self) -> None:
        """handler_async threads invalidate_project to _invalidate_cache_async."""
        mock_persistence = MagicMock()
        mock_persistence.delete_section_files_async = AsyncMock(return_value=True)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)

        with patch(
            "autom8_asana.dataframes.section_persistence.create_section_persistence",
            return_value=mock_persistence,
        ):
            result = await handler_async(
                event={
                    "clear_tasks": False,
                    "clear_dataframes": False,
                    "invalidate_project": "7777777777",
                },
            )

        assert result["statusCode"] == 200
        assert result["body"]["projects_invalidated"] == 1
        mock_persistence.delete_section_files_async.assert_awaited_once_with(
            "7777777777"
        )
        mock_persistence.delete_manifest_async.assert_awaited_once_with("7777777777")

    @pytest.mark.asyncio
    async def test_handler_async_no_invalidate_project_in_event(self) -> None:
        """handler_async with no invalidate_project key produces zero count."""
        result = await handler_async(
            event={
                "clear_tasks": False,
                "clear_dataframes": False,
            },
        )

        assert result["statusCode"] == 200
        assert result["body"]["projects_invalidated"] == 0
