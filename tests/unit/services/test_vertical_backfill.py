"""Tests for VerticalBackfillService.

Per remediation-vertical-investigation-spike Option A:
Verifies backfill logic for cf:Vertical on unit tasks with empty
vertical values, including notes parsing, enum resolution, error
tolerance, and result counting.

Module: tests/unit/services/test_vertical_backfill.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from autom8_asana.services.vertical_backfill import (
    BackfillResult,
    VerticalBackfillService,
    parse_vertical_from_notes,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    """Create a mock Asana client with tasks.get_async and tasks.update_async."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.get_async = AsyncMock()
    client.tasks.update_async = AsyncMock()
    return client


@pytest.fixture
def service(mock_client):
    """Create a VerticalBackfillService with a mock client."""
    return VerticalBackfillService(client=mock_client)


def _make_task_response(
    *,
    notes: str = "",
    vertical_cf_gid: str = "cf_111",
    enum_options: list[dict[str, str]] | None = None,
    has_vertical_cf: bool = True,
) -> dict:
    """Build a mock Asana task response with custom fields."""
    if enum_options is None:
        enum_options = [
            {"gid": "opt_dental", "name": "Dental"},
            {"gid": "opt_chiro", "name": "Chiropractic"},
            {"gid": "opt_vision", "name": "Vision"},
        ]

    custom_fields = []
    if has_vertical_cf:
        custom_fields.append(
            {
                "gid": vertical_cf_gid,
                "name": "Vertical",
                "enum_options": enum_options,
            }
        )
    # Add a non-Vertical custom field to ensure we filter correctly
    custom_fields.append(
        {
            "gid": "cf_222",
            "name": "Status",
            "enum_options": [{"gid": "opt_active", "name": "Active"}],
        }
    )

    return {
        "notes": notes,
        "custom_fields": custom_fields,
    }


# ---------------------------------------------------------------------------
# parse_vertical_from_notes
# ---------------------------------------------------------------------------


class TestParseVerticalFromNotes:
    """Test the notes parsing utility."""

    def test_parses_vertical_dental(self) -> None:
        assert parse_vertical_from_notes("Vertical: Dental") == "Dental"

    def test_parses_vertical_chiropractic(self) -> None:
        assert parse_vertical_from_notes("Vertical: Chiropractic") == "Chiropractic"

    def test_parses_vertical_case_insensitive(self) -> None:
        assert parse_vertical_from_notes("vertical: dental") == "dental"

    def test_parses_vertical_with_leading_text(self) -> None:
        notes = "Some intro text\nVertical: Vision\nMore text"
        assert parse_vertical_from_notes(notes) == "Vision"

    def test_returns_none_for_empty_notes(self) -> None:
        assert parse_vertical_from_notes("") is None

    def test_returns_none_for_none_input(self) -> None:
        # parse_vertical_from_notes guards against falsy input
        assert parse_vertical_from_notes("") is None

    def test_returns_none_when_no_vertical_prefix(self) -> None:
        assert parse_vertical_from_notes("This has no vertical info") is None

    def test_strips_whitespace_from_value(self) -> None:
        assert parse_vertical_from_notes("Vertical:   Dental  ") == "Dental"

    def test_parses_first_occurrence(self) -> None:
        notes = "Vertical: Dental\nVertical: Vision"
        assert parse_vertical_from_notes(notes) == "Dental"


# ---------------------------------------------------------------------------
# BackfillResult
# ---------------------------------------------------------------------------


class TestBackfillResult:
    """Test BackfillResult dataclass defaults."""

    def test_defaults(self) -> None:
        result = BackfillResult()
        assert result.attempted == 0
        assert result.succeeded == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []


# ---------------------------------------------------------------------------
# VerticalBackfillService.backfill_from_dataframe
# ---------------------------------------------------------------------------


class TestBackfillFromDataframe:
    """Test the main entry point for backfill."""

    async def test_identifies_empty_vertical_rows(self, service, mock_client) -> None:
        """Rows with null/empty vertical are identified for backfill."""
        mock_client.tasks.get_async.return_value = _make_task_response(
            notes="Vertical: Dental",
        )

        unit_df = pl.DataFrame(
            {
                "gid": ["task_1", "task_2", "task_3"],
                "vertical": [None, "", "Dental"],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        # task_1 (None) and task_2 ("") are candidates; task_3 has value
        assert result.attempted == 2
        assert result.succeeded == 2

    async def test_skips_tasks_with_existing_vertical(self, service, mock_client) -> None:
        """Rows with non-empty vertical are skipped entirely."""
        unit_df = pl.DataFrame(
            {
                "gid": ["task_1", "task_2"],
                "vertical": ["Dental", "Chiropractic"],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        assert result.attempted == 0
        mock_client.tasks.get_async.assert_not_called()

    async def test_skips_rows_without_gid(self, service, mock_client) -> None:
        """Rows with missing GID are silently skipped."""
        unit_df = pl.DataFrame(
            {
                "gid": [None, "task_2"],
                "vertical": [None, None],
            }
        )

        mock_client.tasks.get_async.return_value = _make_task_response(
            notes="Vertical: Dental",
        )

        result = await service.backfill_from_dataframe(unit_df)

        # Only task_2 is a valid candidate
        assert result.attempted == 1

    async def test_vertical_parsed_from_notes(self, service, mock_client) -> None:
        """Vertical value is extracted from notes and written to custom field."""
        mock_client.tasks.get_async.return_value = _make_task_response(
            notes="Vertical: Dental",
        )

        unit_df = pl.DataFrame(
            {
                "gid": ["task_1"],
                "vertical": [None],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        assert result.succeeded == 1

        # Verify the update call used the correct enum option GID
        mock_client.tasks.update_async.assert_called_once_with(
            "task_1",
            data={"custom_fields": {"cf_111": {"gid": "opt_dental"}}},
        )

    async def test_notes_without_vertical_prefix_skipped(self, service, mock_client) -> None:
        """Tasks with notes lacking 'Vertical: ' prefix are skipped."""
        mock_client.tasks.get_async.return_value = _make_task_response(
            notes="This task has no vertical info",
        )

        unit_df = pl.DataFrame(
            {
                "gid": ["task_1"],
                "vertical": [None],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        assert result.attempted == 1
        assert result.skipped == 1
        assert result.succeeded == 0
        mock_client.tasks.update_async.assert_not_called()

    async def test_result_counts_correct(self, service, mock_client) -> None:
        """Result counts reflect attempted, succeeded, skipped, and failed."""
        # task_1: success (Dental in notes)  # noqa: ERA001
        # task_2: skip (no vertical in notes)
        # task_3: error (API exception)
        # task_4: already has vertical (not attempted)
        responses = [
            _make_task_response(notes="Vertical: Dental"),
            _make_task_response(notes="No vertical here"),
            Exception("API error"),
        ]

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            resp = responses[call_count]
            call_count += 1
            if isinstance(resp, Exception):
                raise resp
            return resp

        mock_client.tasks.get_async.side_effect = side_effect

        unit_df = pl.DataFrame(
            {
                "gid": ["task_1", "task_2", "task_3", "task_4"],
                "vertical": [None, None, None, "Dental"],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        assert result.attempted == 3
        assert result.succeeded == 1
        assert result.skipped == 1
        assert result.failed == 1
        assert len(result.errors) == 1
        assert result.errors[0][0] == "task_3"

    async def test_individual_task_failure_does_not_stop_batch(self, service, mock_client) -> None:
        """A failure on one task does not prevent processing of subsequent tasks."""
        responses = [
            Exception("API error on task_1"),
            _make_task_response(notes="Vertical: Dental"),
        ]

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            resp = responses[call_count]
            call_count += 1
            if isinstance(resp, Exception):
                raise resp
            return resp

        mock_client.tasks.get_async.side_effect = side_effect

        unit_df = pl.DataFrame(
            {
                "gid": ["task_1", "task_2"],
                "vertical": [None, None],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        # task_1 fails, task_2 succeeds -- batch continues
        assert result.attempted == 2
        assert result.failed == 1
        assert result.succeeded == 1

    async def test_missing_gid_column_returns_empty_result(self, service) -> None:
        """DataFrame without 'gid' column returns empty result."""
        unit_df = pl.DataFrame(
            {
                "vertical": [None, None],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        assert result.attempted == 0

    async def test_missing_vertical_column_returns_empty_result(self, service) -> None:
        """DataFrame without 'vertical' column returns empty result."""
        unit_df = pl.DataFrame(
            {
                "gid": ["task_1", "task_2"],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        assert result.attempted == 0

    async def test_no_vertical_custom_field_on_task_skipped(self, service, mock_client) -> None:
        """Task with no 'Vertical' custom field is skipped."""
        mock_client.tasks.get_async.return_value = _make_task_response(
            notes="Vertical: Dental",
            has_vertical_cf=False,
        )

        unit_df = pl.DataFrame(
            {
                "gid": ["task_1"],
                "vertical": [None],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        assert result.skipped == 1
        mock_client.tasks.update_async.assert_not_called()

    async def test_no_matching_enum_option_skipped(self, service, mock_client) -> None:
        """Task where vertical value doesn't match any enum option is skipped."""
        mock_client.tasks.get_async.return_value = _make_task_response(
            notes="Vertical: Podiatry",  # Not in enum options
        )

        unit_df = pl.DataFrame(
            {
                "gid": ["task_1"],
                "vertical": [None],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        assert result.skipped == 1
        mock_client.tasks.update_async.assert_not_called()

    async def test_case_insensitive_enum_matching(self, service, mock_client) -> None:
        """Enum option matching is case-insensitive."""
        mock_client.tasks.get_async.return_value = _make_task_response(
            notes="Vertical: dental",  # lowercase
        )

        unit_df = pl.DataFrame(
            {
                "gid": ["task_1"],
                "vertical": [None],
            }
        )

        result = await service.backfill_from_dataframe(unit_df)

        assert result.succeeded == 1
        # "dental" matches "Dental" enum option (case-insensitive)
        mock_client.tasks.update_async.assert_called_once_with(
            "task_1",
            data={"custom_fields": {"cf_111": {"gid": "opt_dental"}}},
        )
