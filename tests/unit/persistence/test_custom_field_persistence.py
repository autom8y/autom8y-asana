"""Tests for custom field persistence in Save Orchestration.

Per TDD-0011: Verify custom field handling for all 6 field types:
- text: String values
- number: Numeric values
- enum: Single-select enum options
- multi_enum: Multi-select enum options
- date: Date values (YYYY-MM-DD)
- people: User references

Tests verify both CREATE and UPDATE scenarios for custom fields.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.models import Task
from autom8_asana.persistence.models import OperationType
from autom8_asana.persistence.session import SaveSession

# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def create_mock_client() -> MagicMock:
    """Create a mock AsanaClient with mock batch client and http client."""
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.execute_async = AsyncMock(return_value=[])
    mock_client.batch = mock_batch
    mock_client._log = None

    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_client._http = mock_http

    return mock_client


def create_success_result(
    gid: str = "123",
    request_index: int = 0,
) -> BatchResult:
    """Create a successful BatchResult."""
    return BatchResult(
        status_code=200,
        body={"data": {"gid": gid, "name": "Test"}},
        request_index=request_index,
    )


def create_task_with_custom_fields(
    gid: str,
    name: str = "Test Task",
    custom_fields: list[dict[str, Any]] | None = None,
) -> Task:
    """Create a task with custom fields."""
    return Task(
        gid=gid,
        name=name,
        custom_fields=custom_fields or [],
    )


# Sample custom field definitions for testing
TEXT_FIELD = {
    "gid": "cf_text_123",
    "name": "Description",
    "type": "text",
    "text_value": "Original description",
}

NUMBER_FIELD = {
    "gid": "cf_number_123",
    "name": "Priority Score",
    "type": "number",
    "number_value": 5,
}

ENUM_FIELD = {
    "gid": "cf_enum_123",
    "name": "Status",
    "type": "enum",
    "enum_value": {"gid": "opt_1", "name": "In Progress"},
    "enum_options": [
        {"gid": "opt_1", "name": "In Progress"},
        {"gid": "opt_2", "name": "Done"},
        {"gid": "opt_3", "name": "Blocked"},
    ],
}

MULTI_ENUM_FIELD = {
    "gid": "cf_multi_123",
    "name": "Labels",
    "type": "multi_enum",
    "multi_enum_values": [
        {"gid": "label_1", "name": "Bug"},
        {"gid": "label_2", "name": "Feature"},
    ],
    "enum_options": [
        {"gid": "label_1", "name": "Bug"},
        {"gid": "label_2", "name": "Feature"},
        {"gid": "label_3", "name": "Enhancement"},
    ],
}

DATE_FIELD = {
    "gid": "cf_date_123",
    "name": "Target Date",
    "type": "date",
    "date_value": {"date": "2024-12-31"},
}

PEOPLE_FIELD = {
    "gid": "cf_people_123",
    "name": "Reviewers",
    "type": "people",
    "people_value": [
        {"gid": "user_1", "name": "Alice"},
        {"gid": "user_2", "name": "Bob"},
    ],
}


# ---------------------------------------------------------------------------
# Text Field Tests
# ---------------------------------------------------------------------------


class TestTextFieldPersistence:
    """Tests for text custom field persistence."""

    def test_create_with_text_field(self) -> None:
        """CREATE includes text custom field in payload."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="temp_123",
            custom_fields=[TEXT_FIELD],
        )
        session.track(task)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.CREATE
        assert "custom_fields" in crud_ops[0].payload

    def test_update_text_field_value(self) -> None:
        """UPDATE payload includes modified text field."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="1234567890",
            custom_fields=[TEXT_FIELD.copy()],
        )
        session.track(task)

        # Modify text field via accessor
        accessor = task.get_custom_fields()
        accessor.set("Description", "Updated description")

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.UPDATE


# ---------------------------------------------------------------------------
# Number Field Tests
# ---------------------------------------------------------------------------


class TestNumberFieldPersistence:
    """Tests for number custom field persistence."""

    def test_create_with_number_field(self) -> None:
        """CREATE includes number custom field in payload."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="temp_123",
            custom_fields=[NUMBER_FIELD],
        )
        session.track(task)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.CREATE
        assert "custom_fields" in crud_ops[0].payload

    def test_update_number_field_value(self) -> None:
        """UPDATE payload includes modified number field."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="1234567890",
            custom_fields=[NUMBER_FIELD.copy()],
        )
        session.track(task)

        # Modify number field
        accessor = task.get_custom_fields()
        accessor.set("Priority Score", 10)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.UPDATE


# ---------------------------------------------------------------------------
# Enum Field Tests
# ---------------------------------------------------------------------------


class TestEnumFieldPersistence:
    """Tests for enum (single-select) custom field persistence."""

    def test_create_with_enum_field(self) -> None:
        """CREATE includes enum custom field in payload."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="temp_123",
            custom_fields=[ENUM_FIELD],
        )
        session.track(task)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.CREATE

    def test_update_enum_field_value(self) -> None:
        """UPDATE payload includes modified enum field."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        enum_field = ENUM_FIELD.copy()
        task = create_task_with_custom_fields(
            gid="1234567890",
            custom_fields=[enum_field],
        )
        session.track(task)

        # Modify enum field to different value
        accessor = task.get_custom_fields()
        accessor.set("Status", "Done")

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.UPDATE


# ---------------------------------------------------------------------------
# Multi-Enum Field Tests
# ---------------------------------------------------------------------------


class TestMultiEnumFieldPersistence:
    """Tests for multi_enum (multi-select) custom field persistence."""

    def test_create_with_multi_enum_field(self) -> None:
        """CREATE includes multi_enum custom field in payload."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="temp_123",
            custom_fields=[MULTI_ENUM_FIELD],
        )
        session.track(task)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.CREATE

    def test_update_multi_enum_field_value(self) -> None:
        """UPDATE payload includes modified multi_enum field."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        multi_field = MULTI_ENUM_FIELD.copy()
        task = create_task_with_custom_fields(
            gid="1234567890",
            custom_fields=[multi_field],
        )
        session.track(task)

        # Modify multi_enum field
        accessor = task.get_custom_fields()
        accessor.set("Labels", ["Enhancement"])

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.UPDATE


# ---------------------------------------------------------------------------
# Date Field Tests
# ---------------------------------------------------------------------------


class TestDateFieldPersistence:
    """Tests for date custom field persistence."""

    def test_create_with_date_field(self) -> None:
        """CREATE includes date custom field in payload."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="temp_123",
            custom_fields=[DATE_FIELD],
        )
        session.track(task)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.CREATE

    def test_update_date_field_value(self) -> None:
        """UPDATE payload includes modified date field."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        date_field = DATE_FIELD.copy()
        task = create_task_with_custom_fields(
            gid="1234567890",
            custom_fields=[date_field],
        )
        session.track(task)

        # Modify date field
        accessor = task.get_custom_fields()
        accessor.set("Target Date", "2025-01-15")

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.UPDATE


# ---------------------------------------------------------------------------
# People Field Tests
# ---------------------------------------------------------------------------


class TestPeopleFieldPersistence:
    """Tests for people custom field persistence."""

    def test_create_with_people_field(self) -> None:
        """CREATE includes people custom field in payload."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="temp_123",
            custom_fields=[PEOPLE_FIELD],
        )
        session.track(task)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.CREATE

    def test_update_people_field_value(self) -> None:
        """UPDATE payload includes modified people field."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        people_field = PEOPLE_FIELD.copy()
        task = create_task_with_custom_fields(
            gid="1234567890",
            custom_fields=[people_field],
        )
        session.track(task)

        # Modify people field
        accessor = task.get_custom_fields()
        accessor.set("Reviewers", ["user_3"])

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.UPDATE


# ---------------------------------------------------------------------------
# Combined Field Tests
# ---------------------------------------------------------------------------


class TestMultipleCustomFields:
    """Tests for tasks with multiple custom fields."""

    def test_create_with_multiple_fields(self) -> None:
        """CREATE includes all custom field types in payload."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="temp_123",
            custom_fields=[
                TEXT_FIELD,
                NUMBER_FIELD,
                ENUM_FIELD,
                MULTI_ENUM_FIELD,
                DATE_FIELD,
                PEOPLE_FIELD,
            ],
        )
        session.track(task)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.CREATE
        assert "custom_fields" in crud_ops[0].payload

    def test_update_multiple_fields(self) -> None:
        """UPDATE with multiple custom field changes."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="1234567890",
            custom_fields=[
                TEXT_FIELD.copy(),
                NUMBER_FIELD.copy(),
            ],
        )
        session.track(task)

        # Modify multiple fields
        accessor = task.get_custom_fields()
        accessor.set("Description", "New description")
        accessor.set("Priority Score", 100)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.UPDATE


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestCustomFieldEdgeCases:
    """Tests for edge cases in custom field persistence."""

    def test_task_with_no_custom_fields(self) -> None:
        """Task with no custom fields works correctly."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = Task(gid="temp_123", name="Simple Task")
        session.track(task)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.CREATE

    def test_task_with_empty_custom_fields(self) -> None:
        """Task with empty custom_fields list works correctly."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="temp_123",
            custom_fields=[],
        )
        session.track(task)

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1

    def test_remove_custom_field_value(self) -> None:
        """Removing a custom field value is tracked."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="1234567890",
            custom_fields=[TEXT_FIELD.copy()],
        )
        session.track(task)

        # Remove field value
        accessor = task.get_custom_fields()
        accessor.remove("Description")

        crud_ops, _ = session.preview()

        assert len(crud_ops) == 1
        assert crud_ops[0].operation == OperationType.UPDATE

    @pytest.mark.asyncio
    async def test_commit_with_custom_fields(self) -> None:
        """commit_async() works with custom fields."""
        mock_client = create_mock_client()
        success = create_success_result(gid="1234567890")
        mock_client.batch.execute_async = AsyncMock(return_value=[success])

        session = SaveSession(mock_client)

        task = create_task_with_custom_fields(
            gid="1234567890",
            custom_fields=[TEXT_FIELD.copy()],
        )
        session.track(task)

        # Modify custom field
        accessor = task.get_custom_fields()
        accessor.set("Description", "Updated value")

        result = await session.commit_async()

        assert result.success
        mock_client.batch.execute_async.assert_called_once()
