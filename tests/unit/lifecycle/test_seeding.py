"""Unit tests for AutoCascadeSeeder (lifecycle/seeding.py).

Per IMP-02: Tests for the target_task passthrough optimization that
eliminates the double-fetch between seed_async and write_fields_async.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.lifecycle.seeding import AutoCascadeSeeder, SeedingResult


def _make_mock_client() -> MagicMock:
    """Create mock AsanaClient."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.get_async = AsyncMock()
    client.tasks.update_async = AsyncMock()
    return client


def _make_mock_task_with_fields(
    gid: str = "task_123",
    custom_fields: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Create a mock task with custom_fields."""
    task = MagicMock()
    task.gid = gid
    task.custom_fields = custom_fields or [
        {
            "gid": "cf_vertical",
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_options": [
                {"gid": "opt_dental", "name": "Dental", "enabled": True},
            ],
        },
        {
            "gid": "cf_phone",
            "name": "Contact Phone",
            "resource_subtype": "text",
        },
    ]
    return task


def _make_mock_process(custom_fields: list[dict[str, Any]] | None = None) -> MagicMock:
    """Create a mock Process entity with custom fields."""
    process = MagicMock()
    process.gid = "process_123"
    process.name = "Test Process"
    process.custom_fields = custom_fields or [
        {
            "gid": "src_cf_phone",
            "name": "Contact Phone",
            "resource_subtype": "text",
            "text_value": "555-1234",
            "display_value": "555-1234",
        },
    ]
    return process


class TestSeedAsyncTargetTaskPassthrough:
    """Tests for target_task parameter on seed_async (IMP-02)."""

    @pytest.mark.asyncio
    async def test_skips_fetch_when_target_task_provided(self) -> None:
        """When target_task is provided, seed_async should not fetch the task."""
        client = _make_mock_client()
        target_task = _make_mock_task_with_fields()
        process = _make_mock_process()

        seeder = AutoCascadeSeeder(client)

        # Provide target_task -- should skip the fetch
        result = await seeder.seed_async(
            target_task_gid="task_123",
            business=None,
            unit=None,
            source_process=process,
            target_task=target_task,
        )

        # get_async should NOT have been called to fetch the target task
        # (it may be called by write_fields_async, but since we thread
        # the target_task through, that should also be skipped)
        client.tasks.get_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetches_when_target_task_not_provided(self) -> None:
        """When target_task is None, seed_async fetches the task as before."""
        client = _make_mock_client()
        target_task = _make_mock_task_with_fields()
        client.tasks.get_async.return_value = target_task
        process = _make_mock_process()

        seeder = AutoCascadeSeeder(client)

        result = await seeder.seed_async(
            target_task_gid="task_123",
            business=None,
            unit=None,
            source_process=process,
        )

        # get_async should have been called exactly once for target task fetch
        # (seed_async fetches it, then threads it to write_fields_async)
        assert client.tasks.get_async.call_count == 1
        call_args = client.tasks.get_async.call_args
        assert call_args.args[0] == "task_123"

    @pytest.mark.asyncio
    async def test_threads_task_to_write_fields_async(self) -> None:
        """Verify seed_async passes target_task to write_fields_async."""
        client = _make_mock_client()
        target_task = _make_mock_task_with_fields()
        client.tasks.get_async.return_value = target_task
        process = _make_mock_process()

        seeder = AutoCascadeSeeder(client)

        # Patch FieldSeeder.write_fields_async to verify it receives target_task
        with patch("autom8_asana.lifecycle.seeding.FieldSeeder") as MockFieldSeeder:
            mock_field_seeder = MagicMock()
            mock_write = AsyncMock(
                return_value=MagicMock(
                    fields_written=["Contact Phone"],
                    fields_skipped=[],
                    error=None,
                )
            )
            mock_field_seeder.write_fields_async = mock_write
            MockFieldSeeder.return_value = mock_field_seeder

            result = await seeder.seed_async(
                target_task_gid="task_123",
                business=None,
                unit=None,
                source_process=process,
            )

            # write_fields_async should have been called with target_task kwarg
            mock_write.assert_called_once()
            call_kwargs = mock_write.call_args.kwargs
            assert "target_task" in call_kwargs
            assert call_kwargs["target_task"] is target_task

    @pytest.mark.asyncio
    async def test_returns_correct_result_with_passthrough(self) -> None:
        """Verify seed_async produces correct SeedingResult with target_task."""
        client = _make_mock_client()
        target_task = _make_mock_task_with_fields()
        process = _make_mock_process()

        seeder = AutoCascadeSeeder(client)

        # Patch FieldSeeder to return expected write result
        with patch("autom8_asana.lifecycle.seeding.FieldSeeder") as MockFieldSeeder:
            mock_field_seeder = MagicMock()
            mock_write = AsyncMock(
                return_value=MagicMock(
                    fields_written=["Contact Phone"],
                    fields_skipped=[],
                    error=None,
                )
            )
            mock_field_seeder.write_fields_async = mock_write
            MockFieldSeeder.return_value = mock_field_seeder

            result = await seeder.seed_async(
                target_task_gid="task_123",
                business=None,
                unit=None,
                source_process=process,
                target_task=target_task,
            )

            assert result.fields_seeded == ["Contact Phone"]
            assert result.fields_skipped == []
            assert result.warnings == []

    @pytest.mark.asyncio
    async def test_backward_compatible_without_target_task(self) -> None:
        """Existing callers that don't pass target_task still work."""
        client = _make_mock_client()
        # Return a task with no matching fields (no custom fields at all)
        empty_task = MagicMock()
        empty_task.gid = "task_123"
        empty_task.custom_fields = (
            None  # None triggers early return in _normalize_custom_fields
        )
        client.tasks.get_async.return_value = empty_task
        process = _make_mock_process()

        seeder = AutoCascadeSeeder(client)

        # Call without target_task (backward compatible)
        result = await seeder.seed_async(
            target_task_gid="task_123",
            business=None,
            unit=None,
            source_process=process,
        )

        # Should fetch the task since target_task was not provided
        client.tasks.get_async.assert_called_once()
        # No custom fields on target -> early return with empty result
        assert result.fields_seeded == []
        assert result.fields_skipped == []
