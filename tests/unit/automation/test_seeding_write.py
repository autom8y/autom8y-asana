"""Unit tests for FieldSeeder.write_fields_async().

Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT Phase 2: Test field writing.
Per FR-SEED-001: Persist seeded values to API.
Per FR-SEED-002: Single update_async() call (batch all fields).
Per FR-SEED-005: Skip missing fields with warning log.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the accessor module for patching
import autom8_asana.models.custom_field_accessor as custom_field_accessor_module
from autom8_asana.automation.seeding import FieldSeeder, WriteResult


def create_mock_client() -> MagicMock:
    """Create mock AsanaClient with async task methods."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.get_async = AsyncMock()
    client.tasks.update_async = AsyncMock()
    return client


def create_mock_task_with_custom_fields(
    field_definitions: list[dict[str, Any]],
) -> MagicMock:
    """Create mock task with custom field definitions.

    Args:
        field_definitions: List of field definitions with gid, name, type, and options.

    Returns:
        Mock task object with custom_fields property.
    """
    task = MagicMock()
    task.gid = "task_123"
    task.custom_fields = field_definitions
    return task


class TestWriteResult:
    """Tests for WriteResult dataclass."""

    def test_success_result(self) -> None:
        """Test creating a success WriteResult."""
        result = WriteResult(
            success=True,
            fields_written=["Vertical", "Priority"],
            fields_skipped=[],
        )

        assert result.success is True
        assert result.fields_written == ["Vertical", "Priority"]
        assert result.fields_skipped == []
        assert result.error is None

    def test_failure_result(self) -> None:
        """Test creating a failure WriteResult."""
        result = WriteResult(
            success=False,
            fields_written=[],
            fields_skipped=["All", "Fields"],
            error="API error occurred",
        )

        assert result.success is False
        assert result.fields_written == []
        assert result.fields_skipped == ["All", "Fields"]
        assert result.error == "API error occurred"

    def test_partial_result(self) -> None:
        """Test WriteResult with some fields skipped."""
        result = WriteResult(
            success=True,
            fields_written=["Vertical"],
            fields_skipped=["Unknown Field"],
        )

        assert result.success is True
        assert len(result.fields_written) == 1
        assert len(result.fields_skipped) == 1

    def test_repr_success(self) -> None:
        """Test string representation for success."""
        result = WriteResult(
            success=True,
            fields_written=["A", "B"],
            fields_skipped=["C"],
        )

        repr_str = repr(result)
        assert "success" in repr_str
        assert "written=2" in repr_str
        assert "skipped=1" in repr_str

    def test_repr_failure(self) -> None:
        """Test string representation for failure."""
        result = WriteResult(
            success=False,
            error="Connection failed",
        )

        repr_str = repr(result)
        assert "failed" in repr_str
        assert "Connection failed" in repr_str


class TestWriteFieldsAsync:
    """Tests for FieldSeeder.write_fields_async()."""

    @pytest.mark.asyncio
    async def test_empty_fields_returns_success(self) -> None:
        """Test that empty fields dict returns immediate success."""
        client = create_mock_client()
        seeder = FieldSeeder(client)

        result = await seeder.write_fields_async("task_123", {})

        assert result.success is True
        assert result.fields_written == []
        assert result.fields_skipped == []
        # Should not call API
        client.tasks.get_async.assert_not_called()
        client.tasks.update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_writes_single_field(self) -> None:
        """Test writing a single field to target task."""
        client = create_mock_client()

        # Mock task with one custom field
        mock_task = create_mock_task_with_custom_fields(
            [
                {
                    "gid": "cf_123",
                    "name": "Vertical",
                    "type": "enum",
                    "enum_options": [
                        {"gid": "opt_1", "name": "Dental"},
                        {"gid": "opt_2", "name": "Medical"},
                    ],
                },
            ]
        )
        client.tasks.get_async.return_value = mock_task

        seeder = FieldSeeder(client)

        with patch.object(
            custom_field_accessor_module,
            "CustomFieldAccessor",
        ) as mock_accessor_class:
            # Setup accessor mock
            mock_accessor = MagicMock()
            mock_accessor.list_available_fields.return_value = ["Vertical"]
            mock_accessor.has_changes.return_value = True
            mock_accessor.to_api_dict.return_value = {"cf_123": "opt_1"}
            mock_accessor_class.return_value = mock_accessor

            result = await seeder.write_fields_async(
                "task_123",
                {"Vertical": "Dental"},
            )

        assert result.success is True
        assert "Vertical" in result.fields_written
        assert result.fields_skipped == []

        # Verify API calls
        client.tasks.get_async.assert_called_once()
        client.tasks.update_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_writes_multiple_fields(self) -> None:
        """Test writing multiple fields in a single API call (FR-SEED-002)."""
        client = create_mock_client()

        mock_task = create_mock_task_with_custom_fields(
            [
                {"gid": "cf_1", "name": "Vertical", "type": "enum"},
                {"gid": "cf_2", "name": "Priority", "type": "enum"},
                {"gid": "cf_3", "name": "Status", "type": "text"},
            ]
        )
        client.tasks.get_async.return_value = mock_task

        seeder = FieldSeeder(client)

        with patch.object(
            custom_field_accessor_module,
            "CustomFieldAccessor",
        ) as mock_accessor_class:
            mock_accessor = MagicMock()
            mock_accessor.list_available_fields.return_value = [
                "Vertical",
                "Priority",
                "Status",
            ]
            mock_accessor.has_changes.return_value = True
            mock_accessor.to_api_dict.return_value = {
                "cf_1": "val1",
                "cf_2": "val2",
                "cf_3": "val3",
            }
            mock_accessor_class.return_value = mock_accessor

            result = await seeder.write_fields_async(
                "task_123",
                {
                    "Vertical": "Dental",
                    "Priority": "High",
                    "Status": "Active",
                },
            )

        assert result.success is True
        assert len(result.fields_written) == 3
        assert "Vertical" in result.fields_written
        assert "Priority" in result.fields_written
        assert "Status" in result.fields_written

        # Verify only one update call (FR-SEED-002)
        assert client.tasks.update_async.call_count == 1

    @pytest.mark.asyncio
    async def test_skips_missing_field_with_warning(self) -> None:
        """Test that missing fields are skipped with warning log (FR-SEED-005)."""
        client = create_mock_client()

        mock_task = create_mock_task_with_custom_fields(
            [
                {"gid": "cf_1", "name": "Vertical", "type": "enum"},
            ]
        )
        client.tasks.get_async.return_value = mock_task

        seeder = FieldSeeder(client)

        with patch.object(
            custom_field_accessor_module,
            "CustomFieldAccessor",
        ) as mock_accessor_class:
            mock_accessor = MagicMock()
            mock_accessor.list_available_fields.return_value = ["Vertical"]
            mock_accessor.has_changes.return_value = True
            mock_accessor.to_api_dict.return_value = {"cf_1": "val1"}
            mock_accessor_class.return_value = mock_accessor

            with patch("autom8_asana.automation.seeding.logger") as mock_logger:
                result = await seeder.write_fields_async(
                    "task_123",
                    {
                        "Vertical": "Dental",
                        "Unknown Field": "value",  # This should be skipped
                    },
                )

                # Verify warning was logged
                mock_logger.warning.assert_called()
                warning_call = mock_logger.warning.call_args
                assert "Unknown Field" in str(warning_call)

        assert result.success is True
        assert "Vertical" in result.fields_written
        assert "Unknown Field" in result.fields_skipped

    @pytest.mark.asyncio
    async def test_case_insensitive_field_matching(self) -> None:
        """Test that field names are matched case-insensitively."""
        client = create_mock_client()

        mock_task = create_mock_task_with_custom_fields(
            [
                {"gid": "cf_1", "name": "Vertical", "type": "enum"},
            ]
        )
        client.tasks.get_async.return_value = mock_task

        seeder = FieldSeeder(client)

        with patch.object(
            custom_field_accessor_module,
            "CustomFieldAccessor",
        ) as mock_accessor_class:
            mock_accessor = MagicMock()
            mock_accessor.list_available_fields.return_value = ["Vertical"]
            mock_accessor.has_changes.return_value = True
            mock_accessor.to_api_dict.return_value = {"cf_1": "val1"}
            mock_accessor_class.return_value = mock_accessor

            # Use lowercase "vertical" instead of "Vertical"
            result = await seeder.write_fields_async(
                "task_123",
                {"vertical": "Dental"},  # lowercase
            )

        assert result.success is True
        assert "Vertical" in result.fields_written  # Uses matched case

    @pytest.mark.asyncio
    async def test_api_error_returns_failure(self) -> None:
        """Test that API errors return failure result."""
        client = create_mock_client()
        client.tasks.get_async.side_effect = Exception("API connection failed")

        seeder = FieldSeeder(client)

        result = await seeder.write_fields_async(
            "task_123",
            {"Vertical": "Dental"},
        )

        assert result.success is False
        assert result.error == "API connection failed"
        assert "Vertical" in result.fields_skipped

    @pytest.mark.asyncio
    async def test_no_changes_skips_api_call(self) -> None:
        """Test that no API call is made when accessor has no changes."""
        client = create_mock_client()

        mock_task = create_mock_task_with_custom_fields(
            [
                {"gid": "cf_1", "name": "Vertical", "type": "enum"},
            ]
        )
        client.tasks.get_async.return_value = mock_task

        seeder = FieldSeeder(client)

        with patch.object(
            custom_field_accessor_module,
            "CustomFieldAccessor",
        ) as mock_accessor_class:
            mock_accessor = MagicMock()
            mock_accessor.list_available_fields.return_value = ["Vertical"]
            mock_accessor.has_changes.return_value = False  # No changes
            mock_accessor_class.return_value = mock_accessor

            result = await seeder.write_fields_async(
                "task_123",
                {"Vertical": "Dental"},
            )

        assert result.success is True
        # No update call since no changes
        client.tasks.update_async.assert_not_called()


class TestWriteFieldsAsyncIntegration:
    """Integration-style tests for write_fields_async with real accessor patterns."""

    @pytest.mark.asyncio
    async def test_all_fields_skipped_returns_success(self) -> None:
        """Test that if all fields are skipped, still returns success."""
        client = create_mock_client()

        mock_task = create_mock_task_with_custom_fields([])  # No fields defined
        client.tasks.get_async.return_value = mock_task

        seeder = FieldSeeder(client)

        with patch.object(
            custom_field_accessor_module,
            "CustomFieldAccessor",
        ) as mock_accessor_class:
            mock_accessor = MagicMock()
            mock_accessor.list_available_fields.return_value = []  # No available fields
            mock_accessor.has_changes.return_value = False
            mock_accessor_class.return_value = mock_accessor

            result = await seeder.write_fields_async(
                "task_123",
                {"Field1": "val1", "Field2": "val2"},
            )

        assert result.success is True
        assert result.fields_written == []
        assert len(result.fields_skipped) == 2

    @pytest.mark.asyncio
    async def test_update_async_receives_correct_custom_fields(self) -> None:
        """Test that update_async receives correct custom_fields parameter."""
        client = create_mock_client()

        mock_task = create_mock_task_with_custom_fields(
            [
                {"gid": "cf_123", "name": "Vertical", "type": "enum"},
            ]
        )
        client.tasks.get_async.return_value = mock_task

        seeder = FieldSeeder(client)

        expected_api_dict = {"cf_123": "enum_opt_gid"}

        with patch.object(
            custom_field_accessor_module,
            "CustomFieldAccessor",
        ) as mock_accessor_class:
            mock_accessor = MagicMock()
            mock_accessor.list_available_fields.return_value = ["Vertical"]
            mock_accessor.has_changes.return_value = True
            mock_accessor.to_api_dict.return_value = expected_api_dict
            mock_accessor_class.return_value = mock_accessor

            await seeder.write_fields_async("task_123", {"Vertical": "Dental"})

        # Verify update_async was called with correct parameters
        client.tasks.update_async.assert_called_once_with(
            "task_123",
            custom_fields=expected_api_dict,
        )

    @pytest.mark.asyncio
    async def test_skips_empty_people_field(self) -> None:
        """Test that empty people fields are skipped, allowing other fields to write.

        Per bug fix: Empty string for people field (Rep: '') was causing
        'Custom field expects people (list), got str' error. The fix skips
        empty people fields so other fields can still be written.
        """
        client = create_mock_client()

        mock_task = create_mock_task_with_custom_fields(
            [
                {
                    "gid": "cf_1",
                    "name": "Vertical",
                    "resource_subtype": "enum",
                    "enum_options": [{"gid": "opt_1", "name": "spinal_decomp"}],
                },
                {"gid": "cf_2", "name": "Rep", "resource_subtype": "people"},
                {
                    "gid": "cf_3",
                    "name": "Products",
                    "resource_subtype": "multi_enum",
                    "enum_options": [{"gid": "opt_2", "name": "meta_marketing"}],
                },
            ]
        )
        client.tasks.get_async.return_value = mock_task

        seeder = FieldSeeder(client)

        with patch.object(
            custom_field_accessor_module,
            "CustomFieldAccessor",
        ) as mock_accessor_class:
            mock_accessor = MagicMock()
            mock_accessor.list_available_fields.return_value = [
                "Vertical",
                "Rep",
                "Products",
            ]
            mock_accessor.has_changes.return_value = True
            mock_accessor.to_api_dict.return_value = {
                "cf_1": "opt_1",
                "cf_3": ["opt_2"],
            }
            mock_accessor_class.return_value = mock_accessor

            # Simulate cascade fields with empty Rep (the bug scenario)
            result = await seeder.write_fields_async(
                "task_123",
                {
                    "Vertical": "spinal_decomp",
                    "Rep": "",  # Empty string - should be skipped
                    "Products": ["meta_marketing"],
                },
            )

        assert result.success is True
        # Rep should be skipped (empty people field)
        assert "Rep" in result.fields_skipped
        # Other fields should be written
        assert "Vertical" in result.fields_written
        assert "Products" in result.fields_written
        # API should still be called for non-people fields
        client.tasks.update_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_empty_list_people_field(self) -> None:
        """Test that empty list for people field is also skipped."""
        client = create_mock_client()

        mock_task = create_mock_task_with_custom_fields(
            [
                {
                    "gid": "cf_1",
                    "name": "Vertical",
                    "resource_subtype": "enum",
                    "enum_options": [{"gid": "opt_1", "name": "dental"}],
                },
                {"gid": "cf_2", "name": "Rep", "resource_subtype": "people"},
            ]
        )
        client.tasks.get_async.return_value = mock_task

        seeder = FieldSeeder(client)

        with patch.object(
            custom_field_accessor_module,
            "CustomFieldAccessor",
        ) as mock_accessor_class:
            mock_accessor = MagicMock()
            mock_accessor.list_available_fields.return_value = ["Vertical", "Rep"]
            mock_accessor.has_changes.return_value = True
            mock_accessor.to_api_dict.return_value = {"cf_1": "opt_1"}
            mock_accessor_class.return_value = mock_accessor

            result = await seeder.write_fields_async(
                "task_123",
                {
                    "Vertical": "dental",
                    "Rep": [],  # Empty list - should also be skipped
                },
            )

        assert result.success is True
        assert "Rep" in result.fields_skipped
        assert "Vertical" in result.fields_written
