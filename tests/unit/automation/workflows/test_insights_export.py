"""Tests for InsightsExportWorkflow.

Per TDD-EXPORT-001 Section 9.2: Unit tests for the insights export
workflow including happy path, skip scenarios, error isolation, upload-first
ordering, feature flag, concurrency, partial/total failure, and unused
asset derivation.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.insights_export import (
    DEFAULT_ATTACHMENT_PATTERN,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_ROW_LIMITS,
    EXPORT_ENABLED_ENV_VAR,
    OFFER_PROJECT_GID,
    TABLE_NAMES,
    TOTAL_TABLE_COUNT,
    InsightsExportWorkflow,
    _sanitize_business_name,
)
from autom8_asana.automation.workflows.insights_formatter import TableResult
from autom8_asana.clients.data.models import (
    ColumnInfo,
    InsightsMetadata,
    InsightsResponse,
)

# Patch path for resolve_section_gids (lazy import inside _enumerate_offers)
_RESOLVE_PATCH = (
    "autom8_asana.automation.workflows.section_resolution.resolve_section_gids"
)


@pytest.fixture()
def _force_fallback():
    """Patch resolve_section_gids to raise, forcing the fallback path.

    Apply via @pytest.mark.usefixtures("_force_fallback") on test classes
    whose mocks target the old project-level fetch pattern.
    """
    with patch(_RESOLVE_PATCH, side_effect=Exception("force-fallback")):
        yield


# --- Helpers ---


def _make_task(
    gid: str,
    name: str,
    parent_gid: str | None = None,
    completed: bool = False,
    section_name: str = "ACTIVE",
) -> MagicMock:
    """Create a mock task object.

    Args:
        section_name: Section name for membership (default "ACTIVE" to pass
            activity filtering). Set to None-ish or non-ACTIVE to test filtering.
    """
    task = MagicMock()
    task.gid = gid
    task.name = name
    task.completed = completed
    if parent_gid:
        task.parent = MagicMock()
        task.parent.gid = parent_gid
    else:
        task.parent = None
    task.memberships = [{"section": {"name": section_name}}] if section_name else []
    return task


def _make_insights_response(
    data: list[dict[str, Any]] | None = None,
    row_count: int | None = None,
) -> InsightsResponse:
    """Create a test InsightsResponse."""
    rows = data if data is not None else [{"spend": 100, "imp": 5000}]
    count = row_count if row_count is not None else len(rows)
    return InsightsResponse(
        data=rows,
        metadata=InsightsMetadata(
            factory="base",
            row_count=count,
            column_count=2,
            columns=[
                ColumnInfo(name="spend", dtype="float64"),
                ColumnInfo(name="imp", dtype="int64"),
            ],
            cache_hit=False,
            duration_ms=50.0,
        ),
        request_id="test-request-id",
    )


def _make_attachment(gid: str, name: str) -> MagicMock:
    """Create a mock Attachment object."""
    att = MagicMock()
    att.gid = gid
    att.name = name
    return att


class _AsyncIterator:
    """Async iterator for mock page iterators."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items
        self._index = 0

    def __aiter__(self) -> _AsyncIterator:
        return self

    async def __anext__(self) -> Any:
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item

    async def collect(self) -> list[Any]:
        return self._items


def _make_mock_business(
    office_phone: str | None = "+17705753103",
    vertical: str | None = "chiropractic",
    name: str = "Test Business",
) -> MagicMock:
    """Create a mock Business entity returned by ResolutionContext."""
    business = MagicMock()
    business.office_phone = office_phone
    business.vertical = vertical
    business.name = name
    return business


def _make_workflow(
    offers: list[MagicMock] | None = None,
    insights_response: InsightsResponse | None = None,
    insights_error: Exception | None = None,
    table_errors: dict[str, Exception] | None = None,
    existing_attachments: dict[str, list[MagicMock]] | None = None,
    mock_business: MagicMock | None = None,
    resolve_returns_none: bool = False,
) -> tuple[InsightsExportWorkflow, MagicMock, MagicMock, MagicMock]:
    """Build an InsightsExportWorkflow with configured mocks.

    Args:
        offers: List of mock task objects for enumerate_offers.
        insights_response: Default InsightsResponse for all table fetches.
        insights_error: Default error to raise for ALL table fetches.
        table_errors: Dict mapping method name -> error (e.g. "get_insights_async").
        existing_attachments: Dict mapping offer GID -> attachments.
        mock_business: Custom mock Business for ResolutionContext.
        resolve_returns_none: If True, ResolutionContext returns None-valued business.

    Returns:
        Tuple of (workflow, mock_asana, mock_data_client, mock_attachments).
    """
    mock_asana = MagicMock()
    mock_data_client = MagicMock()
    mock_attachments = MagicMock()

    # Enumerate offers
    offer_list = offers or []
    mock_asana.tasks.list_async.return_value = _AsyncIterator(offer_list)

    # Resolve parent: get_async returns the offer task (for parent ref)
    offer_by_gid = {o.gid: o for o in offer_list}

    async def mock_get_async(gid: str, **kwargs: Any) -> MagicMock:
        if gid in offer_by_gid:
            return offer_by_gid[gid]
        return _make_task(gid, "Unknown")

    mock_asana.tasks.get_async = AsyncMock(side_effect=mock_get_async)

    # Default InsightsResponse for all calls
    default_response = insights_response or _make_insights_response()

    if insights_error:
        mock_data_client.get_insights_async = AsyncMock(side_effect=insights_error)
        mock_data_client.get_appointments_async = AsyncMock(side_effect=insights_error)
        mock_data_client.get_leads_async = AsyncMock(side_effect=insights_error)
    else:
        mock_data_client.get_insights_async = AsyncMock(return_value=default_response)
        mock_data_client.get_appointments_async = AsyncMock(
            return_value=default_response
        )
        mock_data_client.get_leads_async = AsyncMock(return_value=default_response)

    mock_data_client._circuit_breaker = MagicMock()
    mock_data_client._circuit_breaker.check = AsyncMock()

    # Upload
    mock_attachments.upload_async = AsyncMock(return_value=MagicMock())

    # List attachments for deletion
    att_map = existing_attachments or {}

    def mock_list_for_task(gid: str, **kwargs: Any) -> _AsyncIterator:
        return _AsyncIterator(att_map.get(gid, []))

    mock_attachments.list_for_task_async = MagicMock(side_effect=mock_list_for_task)

    # Delete
    mock_attachments.delete_async = AsyncMock()

    workflow = InsightsExportWorkflow(
        asana_client=mock_asana,
        data_client=mock_data_client,
        attachments_client=mock_attachments,
    )

    return workflow, mock_asana, mock_data_client, mock_attachments


def _default_params() -> dict[str, Any]:
    """Default params for execute_async calls."""
    return {"workflow_id": "insights-export"}


# --- Tests ---


class TestWorkflowId:
    """Test workflow_id property (AC-W01.1)."""

    def test_workflow_id(self) -> None:
        wf, _, _, _ = _make_workflow()
        assert wf.workflow_id == "insights-export"


class TestValidateAsync:
    """Tests for validate_async pre-flight checks (AC-W01.2, AC-W01.3, AC-W05.5, AC-W05.6)."""

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_false(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "false"}):
            errors = await wf.validate_async()
        assert len(errors) == 1
        assert "disabled" in errors[0].lower()

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_zero(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "0"}):
            errors = await wf.validate_async()
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_no(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "no"}):
            errors = await wf.validate_async()
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_feature_flag_enabled_default(self) -> None:
        """Unset env var means enabled."""
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop(EXPORT_ENABLED_ENV_VAR, None)
            errors = await wf.validate_async()
        assert errors == []

    @pytest.mark.asyncio
    async def test_feature_flag_enabled_true(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "true"}):
            errors = await wf.validate_async()
        assert errors == []

    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self) -> None:
        wf, _, mock_data, _ = _make_workflow()

        from autom8y_http import CircuitBreakerOpenError as SdkCBOpen

        mock_cb = AsyncMock()
        mock_cb.check = AsyncMock(
            side_effect=SdkCBOpen(time_remaining=30.0, message="CB open")
        )
        mock_data._circuit_breaker = mock_cb
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop(EXPORT_ENABLED_ENV_VAR, None)
            errors = await wf.validate_async()
        assert len(errors) == 1
        assert "circuit breaker" in errors[0].lower()


@pytest.mark.usefixtures("_force_fallback")
class TestEnumeration:
    """Tests for offer enumeration (AC-W01.4) -- via fallback path."""

    @pytest.mark.asyncio
    async def test_only_non_completed_offers(self) -> None:
        """Only non-completed offers are enumerated."""
        active_offer = _make_task("o1", "Active Offer", parent_gid="biz1")
        completed_offer = _make_task(
            "o2", "Completed Offer", parent_gid="biz2", completed=True
        )
        mock_asana = MagicMock()
        mock_asana.tasks.list_async.return_value = _AsyncIterator(
            [active_offer, completed_offer]
        )

        wf, _, _, _ = _make_workflow(offers=[active_offer, completed_offer])

        # Patch to use ResolutionContext
        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        # Completed offer is filtered out during enumeration
        # Only 1 active offer processed
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_enumeration_calls_correct_project(self) -> None:
        """Enumeration targets the correct project GID."""
        wf, mock_asana, _, _ = _make_workflow(offers=[])
        await wf.execute_async(_default_params())

        mock_asana.tasks.list_async.assert_called_once_with(
            project=OFFER_PROJECT_GID,
            opt_fields=[
                "name",
                "completed",
                "parent",
                "parent.name",
                "memberships.section.name",
            ],
            completed_since="now",
        )


@pytest.mark.usefixtures("_force_fallback")
class TestResolution:
    """Tests for offer resolution (AC-W01.5, AC-W01.6) -- via fallback path."""

    @pytest.mark.asyncio
    async def test_successful_resolution(self) -> None:
        """Successful resolution -> offer processed."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1])

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business(
                office_phone="+17705753103",
                vertical="chiropractic",
                name="Acme Chiro",
            )
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        assert result.succeeded == 1
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_skip_missing_phone(self) -> None:
        """Missing office_phone -> offer skipped."""
        o1 = _make_task("o1", "Offer No Phone", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1])

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business(
                office_phone=None, vertical="chiropractic"
            )
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        assert result.total == 1
        assert result.skipped == 1
        assert result.succeeded == 0

    @pytest.mark.asyncio
    async def test_skip_missing_vertical(self) -> None:
        """Missing vertical -> offer skipped."""
        o1 = _make_task("o1", "Offer No Vertical", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1])

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business(
                office_phone="+17705753103", vertical=None
            )
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        assert result.total == 1
        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_skip_no_parent(self) -> None:
        """Offer with no parent reference -> skipped."""
        o1 = _make_task("o1", "Orphan Offer")  # No parent_gid
        wf, _, _, _ = _make_workflow(offers=[o1])

        # The offer has no parent_gid from enumeration, and get_async
        # returns task with no parent either
        result = await wf.execute_async(_default_params())

        assert result.total == 1
        assert result.skipped == 1


@pytest.mark.usefixtures("_force_fallback")
class TestFetchAllTables:
    """Tests for table fetching (AC-W01.7) -- via fallback path."""

    @pytest.mark.asyncio
    async def test_all_nine_api_calls_dispatched(self) -> None:
        """All 9 API calls are dispatched (UNUSED ASSETS derived)."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, mock_data, _ = _make_workflow(offers=[o1])

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        # 7 insights calls + 1 appointments + 1 leads = 9 total
        assert mock_data.get_insights_async.call_count == 7
        assert mock_data.get_appointments_async.call_count == 1
        assert mock_data.get_leads_async.call_count == 1

    @pytest.mark.asyncio
    async def test_correct_factory_params(self) -> None:
        """Each table uses the correct factory and period."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, mock_data, _ = _make_workflow(offers=[o1])

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            await wf.execute_async(_default_params())

        # Verify factory params in insights calls
        insights_calls = mock_data.get_insights_async.call_args_list
        factory_period_pairs = set()
        for c in insights_calls:
            factory_period_pairs.add((c.kwargs.get("factory"), c.kwargs.get("period")))

        # These are the expected factory+period combinations for the 7 insights calls
        expected_pairs = {
            ("base", "lifetime"),  # SUMMARY
            ("base", "quarter"),  # BY QUARTER
            ("base", "month"),  # BY MONTH
            ("base", "week"),  # BY WEEK
            ("ad_questions", "lifetime"),  # AD QUESTIONS
            ("assets", "t30"),  # ASSET TABLE
            ("business_offers", "t30"),  # OFFER TABLE
        }
        assert factory_period_pairs == expected_pairs


class TestUnusedAssetsFilter:
    """Tests for UNUSED ASSETS derivation (AC-W03.9)."""

    @pytest.mark.asyncio
    async def test_unused_assets_filtered_correctly(self) -> None:
        """UNUSED ASSETS = rows where spend==0 AND imp==0."""
        asset_data = [
            {"name": "Active Ad", "spend": 100, "imp": 5000},
            {"name": "Unused Ad 1", "spend": 0, "imp": 0},
            {"name": "Partial Spend", "spend": 0, "imp": 100},
            {"name": "Partial Imp", "spend": 50, "imp": 0},
            {"name": "Unused Ad 2", "spend": 0, "imp": 0},
        ]
        asset_response = _make_insights_response(data=asset_data)

        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")

        # Make get_insights_async return asset_data for all calls
        wf, _, mock_data, _ = _make_workflow(
            offers=[o1], insights_response=asset_response
        )

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            # We need to verify the UNUSED ASSETS derivation directly.
            # Invoke _fetch_all_tables to inspect the result.
            table_results = await wf._fetch_all_tables(
                office_phone="+17705753103",
                vertical="chiropractic",
                row_limits=DEFAULT_ROW_LIMITS,
                offer_gid="o1",
            )

        unused_result = table_results["UNUSED ASSETS"]
        assert unused_result.success is True
        assert unused_result.row_count == 2
        assert len(unused_result.data) == 2
        assert all(r["spend"] == 0 and r["imp"] == 0 for r in unused_result.data)

    @pytest.mark.asyncio
    async def test_unused_assets_fails_when_asset_table_fails(self) -> None:
        """UNUSED ASSETS inherits failure from ASSET TABLE."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")

        # Make only the assets factory call fail
        default_response = _make_insights_response()

        async def selective_insights(factory: str, **kwargs: Any) -> InsightsResponse:
            if factory == "assets":
                raise ConnectionError("Asset fetch failed")
            return default_response

        wf, _, mock_data, _ = _make_workflow(offers=[o1])
        mock_data.get_insights_async = AsyncMock(side_effect=selective_insights)

        table_results = await wf._fetch_all_tables(
            office_phone="+17705753103",
            vertical="chiropractic",
            row_limits=DEFAULT_ROW_LIMITS,
            offer_gid="o1",
        )

        unused_result = table_results["UNUSED ASSETS"]
        assert unused_result.success is False
        assert "ASSET TABLE which failed" in unused_result.error_message


@pytest.mark.usefixtures("_force_fallback")
class TestUploadAndCleanup:
    """Tests for upload and attachment cleanup (AC-W01.8-W01.10, AC-W03.11) -- via fallback."""

    @pytest.mark.asyncio
    async def test_upload_called_with_correct_params(self) -> None:
        """Upload creates .md file with correct content type."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, mock_att = _make_workflow(offers=[o1])

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            await wf.execute_async(_default_params())

        assert mock_att.upload_async.call_count == 1
        call_kwargs = mock_att.upload_async.call_args[1]
        assert call_kwargs["parent"] == "o1"
        assert call_kwargs["content_type"] == "text/markdown"
        assert call_kwargs["name"].startswith("insights_export_")
        assert call_kwargs["name"].endswith(".md")

    @pytest.mark.asyncio
    async def test_old_attachments_deleted(self) -> None:
        """Old matching attachments are deleted after upload."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        old_att = _make_attachment(
            "old-att-1", "insights_export_Test_Business_20260201.md"
        )

        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [old_att]},
        )

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            await wf.execute_async(_default_params())

        assert mock_att.delete_async.call_count == 1
        assert mock_att.delete_async.call_args[0][0] == "old-att-1"

    @pytest.mark.asyncio
    async def test_non_matching_attachments_not_deleted(self) -> None:
        """Non-matching attachments are left alone."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        other_att = _make_attachment("other-att-1", "some_other_file.pdf")

        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [other_att]},
        )

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            await wf.execute_async(_default_params())

        mock_att.delete_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_before_delete(self) -> None:
        """Upload-first: upload happens before delete (AC-W03.11)."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        old_att = _make_attachment(
            "old-att-1", "insights_export_Test_Business_20260201.md"
        )

        call_order: list[str] = []

        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [old_att]},
        )

        original_upload = mock_att.upload_async

        async def track_upload(**kwargs: Any) -> MagicMock:
            call_order.append("upload")
            return await original_upload(**kwargs)

        original_delete = mock_att.delete_async

        async def track_delete(gid: str) -> None:
            call_order.append("delete")
            return await original_delete(gid)

        mock_att.upload_async = AsyncMock(side_effect=track_upload)
        mock_att.delete_async = AsyncMock(side_effect=track_delete)

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            await wf.execute_async(_default_params())

        assert call_order == ["upload", "delete"]


@pytest.mark.usefixtures("_force_fallback")
class TestConcurrency:
    """Tests for semaphore concurrency bounds (AC-W01.11) -- via fallback path."""

    @pytest.mark.asyncio
    async def test_max_concurrency_from_params(self) -> None:
        """Verify max_concurrency parameter is respected."""
        offers = [
            _make_task(f"o{i}", f"Offer {i}", parent_gid=f"biz{i}") for i in range(10)
        ]
        wf, _, _, _ = _make_workflow(offers=offers)

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            params = {**_default_params(), "max_concurrency": 2}
            result = await wf.execute_async(params)

        # All should succeed even with low concurrency
        assert result.total == 10
        assert result.succeeded == 10

    @pytest.mark.asyncio
    async def test_default_concurrency_used(self) -> None:
        """Default max_concurrency is used when not specified."""
        wf, _, _, _ = _make_workflow(offers=[])
        # Simply verify it doesn't fail with default params
        result = await wf.execute_async(_default_params())
        assert result.total == 0


@pytest.mark.usefixtures("_force_fallback")
class TestWorkflowResult:
    """Tests for WorkflowResult structure (AC-W01.12, AC-W02.4) -- via fallback path."""

    @pytest.mark.asyncio
    async def test_result_includes_per_offer_table_counts(self) -> None:
        """Result metadata includes per-offer table counts."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1])

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        assert "per_offer_table_counts" in result.metadata
        assert "total_tables_succeeded" in result.metadata
        assert "total_tables_failed" in result.metadata
        # With all tables succeeding
        assert result.metadata["total_tables_succeeded"] == TOTAL_TABLE_COUNT
        assert result.metadata["total_tables_failed"] == 0

    @pytest.mark.asyncio
    async def test_result_totals(self) -> None:
        """Result has correct total/succeeded/failed/skipped."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        o2 = _make_task("o2", "Offer 2", parent_gid="biz2")
        o3 = _make_task("o3", "Offer No Parent")  # Will be skipped

        wf, _, _, _ = _make_workflow(offers=[o1, o2, o3])

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        assert result.total == 3
        assert result.succeeded == 2
        assert result.skipped == 1
        assert result.workflow_id == "insights-export"


@pytest.mark.usefixtures("_force_fallback")
class TestPartialFailure:
    """Tests for partial table failure (AC-W02.1, AC-W02.2) -- via fallback path."""

    @pytest.mark.asyncio
    async def test_one_table_fails_rest_succeed(self) -> None:
        """1 of 10 tables fails -> 9 succeed, report still uploaded."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        default_response = _make_insights_response()

        call_count = 0

        async def fail_one_insights(factory: str, **kwargs: Any) -> InsightsResponse:
            nonlocal call_count
            call_count += 1
            # Fail the first insights call (SUMMARY)
            if factory == "base" and kwargs.get("period") == "lifetime":
                raise ConnectionError("Network error on SUMMARY")
            return default_response

        wf, _, mock_data, mock_att = _make_workflow(offers=[o1])
        mock_data.get_insights_async = AsyncMock(side_effect=fail_one_insights)

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        # Offer still succeeds with partial data
        assert result.succeeded == 1
        # Upload still called (partial report)
        assert mock_att.upload_async.call_count == 1
        # Per-offer table counts should show the failure
        table_counts = result.metadata["per_offer_table_counts"]["o1"]
        assert table_counts["tables_failed"] > 0
        assert table_counts["tables_succeeded"] > 0


@pytest.mark.usefixtures("_force_fallback")
class TestTotalFailure:
    """Tests for total table failure (AC-W02.3) -- via fallback path."""

    @pytest.mark.asyncio
    async def test_all_tables_fail_no_upload(self) -> None:
        """All 10 tables fail -> no upload, offer marked failed."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            insights_error=ConnectionError("Service down"),
        )

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        assert result.total == 1
        assert result.failed == 1
        assert result.succeeded == 0
        # No upload should occur
        mock_att.upload_async.assert_not_called()
        # Error should have the all_tables_failed type
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "all_tables_failed"
        assert result.errors[0].recoverable is True


@pytest.mark.usefixtures("_force_fallback")
class TestDeleteFailureTolerance:
    """Tests for non-fatal delete failure -- via fallback path."""

    @pytest.mark.asyncio
    async def test_delete_failure_still_succeeded(self) -> None:
        """Delete-old fails -> offer still counted as succeeded."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        old_att = _make_attachment(
            "old-att-1", "insights_export_Test_Business_20260201.md"
        )

        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [old_att]},
        )

        # Make delete fail
        mock_att.delete_async = AsyncMock(side_effect=Exception("Asana API error"))

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        # Still succeeded because upload worked; delete failure is non-fatal
        assert result.succeeded == 1
        assert result.failed == 0


@pytest.mark.usefixtures("_force_fallback")
class TestEmptyProject:
    """Tests for empty project (no offers) -- via fallback path."""

    @pytest.mark.asyncio
    async def test_no_offers(self) -> None:
        """Empty project -> total=0, all zeros."""
        wf, _, _, _ = _make_workflow(offers=[])

        result = await wf.execute_async(_default_params())

        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.metadata["total_tables_succeeded"] == 0
        assert result.metadata["total_tables_failed"] == 0


class TestSanitizeBusinessName:
    """Tests for _sanitize_business_name helper."""

    def test_spaces_to_underscores(self) -> None:
        assert _sanitize_business_name("Acme Chiro Center") == "Acme_Chiro_Center"

    def test_special_chars_stripped(self) -> None:
        assert _sanitize_business_name("Dr. Smith's Clinic!") == "Dr_Smiths_Clinic"

    def test_alphanumeric_preserved(self) -> None:
        assert _sanitize_business_name("Clinic123") == "Clinic123"

    def test_empty_string(self) -> None:
        assert _sanitize_business_name("") == ""

    def test_underscores_preserved(self) -> None:
        assert _sanitize_business_name("my_business") == "my_business"


class TestConstants:
    """Tests for module constants."""

    def test_table_names_count(self) -> None:
        assert TOTAL_TABLE_COUNT == 10
        assert len(TABLE_NAMES) == 10

    def test_table_names_order(self) -> None:
        assert TABLE_NAMES[0] == "SUMMARY"
        assert TABLE_NAMES[1] == "APPOINTMENTS"
        assert TABLE_NAMES[2] == "LEADS"
        assert TABLE_NAMES[-1] == "UNUSED ASSETS"

    def test_offer_project_gid(self) -> None:
        assert OFFER_PROJECT_GID == "1143843662099250"

    def test_default_row_limits(self) -> None:
        assert DEFAULT_ROW_LIMITS == {"APPOINTMENTS": 100, "LEADS": 100}

    def test_default_max_concurrency(self) -> None:
        assert DEFAULT_MAX_CONCURRENCY == 5

    def test_default_attachment_pattern(self) -> None:
        assert DEFAULT_ATTACHMENT_PATTERN == "insights_export_*.md"


# --- QA-ADVERSARY: Additional Edge Case Tests ---


class TestAdversarialFeatureFlag:
    """QA-ADVERSARY: Feature flag edge cases (AC-W05.5, AC-W05.6)."""

    @pytest.mark.asyncio
    async def test_feature_flag_empty_string_means_enabled(self) -> None:
        """AUTOM8_EXPORT_ENABLED='' (empty string) means enabled."""
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: ""}):
            errors = await wf.validate_async()
        assert errors == []

    @pytest.mark.asyncio
    async def test_feature_flag_uppercase_FALSE(self) -> None:
        """AUTOM8_EXPORT_ENABLED='FALSE' (uppercase) means disabled."""
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "FALSE"}):
            errors = await wf.validate_async()
        assert len(errors) == 1
        assert "disabled" in errors[0].lower()

    @pytest.mark.asyncio
    async def test_feature_flag_mixed_case_No(self) -> None:
        """AUTOM8_EXPORT_ENABLED='No' (mixed case) means disabled."""
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "No"}):
            errors = await wf.validate_async()
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_feature_flag_truthy_strings_mean_enabled(self) -> None:
        """Various truthy strings all mean enabled."""
        for value in ["true", "TRUE", "1", "yes", "enabled", "anything"]:
            wf, _, _, _ = _make_workflow()
            with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: value}):
                errors = await wf.validate_async()
            assert errors == [], f"Expected enabled for value '{value}'"


@pytest.mark.usefixtures("_force_fallback")
class TestAdversarialUploadFailure:
    """QA-ADVERSARY: Upload failure prevents delete loop (AC-W01.10) -- via fallback."""

    @pytest.mark.asyncio
    async def test_upload_failure_prevents_delete(self) -> None:
        """If upload_async raises, delete_old_attachments is never called."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        old_att = _make_attachment(
            "old-att-1", "insights_export_Test_Business_20260201.md"
        )

        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [old_att]},
        )

        # Make upload fail
        mock_att.upload_async = AsyncMock(side_effect=Exception("Upload failed"))

        with patch(
            "autom8_asana.automation.workflows.insights_export.ResolutionContext"
        ) as mock_rc:
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        # Offer should be failed
        assert result.failed == 1
        assert result.succeeded == 0
        # Delete should NOT have been called (upload failed first)
        mock_att.delete_async.assert_not_called()


@pytest.mark.usefixtures("_force_fallback")
class TestAdversarialComposeRaisesPreventsUpload:
    """QA-ADVERSARY: If compose_report raises, no upload occurs -- via fallback."""

    @pytest.mark.asyncio
    async def test_compose_failure_marks_offer_failed(self) -> None:
        """An exception in compose_report is caught by _process_offer."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")

        wf, _, _, mock_att = _make_workflow(offers=[o1])

        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.ResolutionContext"
            ) as mock_rc,
            patch(
                "autom8_asana.automation.workflows.insights_export.compose_report",
                side_effect=TypeError("Unexpected data format"),
            ),
        ):
            mock_ctx = AsyncMock()
            mock_business = _make_mock_business()
            mock_ctx.business_async = AsyncMock(return_value=mock_business)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await wf.execute_async(_default_params())

        assert result.failed == 1
        assert result.succeeded == 0
        # No upload should have happened
        mock_att.upload_async.assert_not_called()


# --- Section-Targeted Enumeration Tests (TDD-SECTION-ENUM-001 Section 7.3) ---


def _make_section_task(
    gid: str,
    name: str,
    parent_gid: str | None = None,
    completed: bool = False,
) -> MagicMock:
    """Create a mock task for section-targeted fetch (no memberships needed)."""
    task = MagicMock()
    task.gid = gid
    task.name = name
    task.completed = completed
    if parent_gid:
        task.parent = MagicMock()
        task.parent.gid = parent_gid
    else:
        task.parent = None
    return task


class TestEnumerateOffersSectionTargeted:
    """Section-targeted primary path: resolve + parallel fetch + dedup."""

    @pytest.mark.asyncio
    async def test_enumerate_offers_section_targeted(self) -> None:
        """Mock resolution + section fetches; verify dedup and dict construction."""
        t1 = _make_section_task("t1", "Offer A", parent_gid="biz1")
        t2 = _make_section_task("t2", "Offer B", parent_gid="biz2")

        wf, mock_asana, _, _ = _make_workflow()

        # Mock section-level task fetches via side_effect
        def list_async_dispatch(**kwargs):
            if kwargs.get("section") == "sec-alpha":
                return _AsyncIterator([t1])
            if kwargs.get("section") == "sec-beta":
                return _AsyncIterator([t2])
            # Fallback path should not be reached
            return _AsyncIterator([])

        mock_asana.tasks.list_async.side_effect = list_async_dispatch

        with patch(
            _RESOLVE_PATCH,
            return_value={"alpha section": "sec-alpha", "beta section": "sec-beta"},
        ):
            offers = await wf._enumerate_offers()

        assert len(offers) == 2
        gids = {o["gid"] for o in offers}
        assert gids == {"t1", "t2"}
        # Verify dict structure
        for o in offers:
            assert "gid" in o
            assert "name" in o
            assert "parent_gid" in o

    @pytest.mark.asyncio
    async def test_section_targeted_skips_completed(self) -> None:
        """Completed tasks from section fetch are excluded."""
        t1 = _make_section_task("t1", "Active", parent_gid="biz1")
        t2 = _make_section_task("t2", "Done", parent_gid="biz2", completed=True)

        wf, mock_asana, _, _ = _make_workflow()
        mock_asana.tasks.list_async.side_effect = (
            lambda **kw: _AsyncIterator([t1, t2])
        )

        with patch(
            _RESOLVE_PATCH,
            return_value={"section": "sec-1"},
        ):
            offers = await wf._enumerate_offers()

        assert len(offers) == 1
        assert offers[0]["gid"] == "t1"

    @pytest.mark.asyncio
    async def test_section_targeted_parent_gid_none(self) -> None:
        """Tasks without parent produce parent_gid=None in dict."""
        t1 = _make_section_task("t1", "No Parent")  # parent_gid=None

        wf, mock_asana, _, _ = _make_workflow()
        mock_asana.tasks.list_async.side_effect = (
            lambda **kw: _AsyncIterator([t1])
        )

        with patch(
            _RESOLVE_PATCH,
            return_value={"section": "sec-1"},
        ):
            offers = await wf._enumerate_offers()

        assert len(offers) == 1
        assert offers[0]["parent_gid"] is None

    @pytest.mark.asyncio
    async def test_section_targeted_opt_fields(self) -> None:
        """Section-level fetch uses reduced opt_fields (no memberships)."""
        wf, mock_asana, _, _ = _make_workflow()
        mock_asana.tasks.list_async.side_effect = (
            lambda **kw: _AsyncIterator([])
        )

        with patch(
            _RESOLVE_PATCH,
            return_value={"section": "sec-1"},
        ):
            await wf._enumerate_offers()

        # Verify the section-level call used the correct opt_fields
        call_kwargs = mock_asana.tasks.list_async.call_args[1]
        assert call_kwargs.get("section") == "sec-1"
        assert "memberships.section.name" not in call_kwargs.get("opt_fields", [])
        assert "parent" in call_kwargs.get("opt_fields", [])
        assert "parent.name" in call_kwargs.get("opt_fields", [])


class TestEnumerateOffersFallbackOnResolutionFailure:
    """Fallback path triggered by resolution failure."""

    @pytest.mark.asyncio
    async def test_fallback_on_resolution_exception(self) -> None:
        """resolve_section_gids raises -> project-level fetch is used."""
        t1 = _make_task("t1", "Offer 1", parent_gid="biz1")

        wf, mock_asana, _, _ = _make_workflow(offers=[t1])

        with patch(
            _RESOLVE_PATCH,
            side_effect=ConnectionError("API timeout"),
        ):
            offers = await wf._enumerate_offers()

        assert len(offers) == 1
        assert offers[0]["gid"] == "t1"
        # Should have called project-level fetch
        mock_asana.tasks.list_async.assert_called_once_with(
            project=OFFER_PROJECT_GID,
            opt_fields=[
                "name",
                "completed",
                "parent",
                "parent.name",
                "memberships.section.name",
            ],
            completed_since="now",
        )

    @pytest.mark.asyncio
    async def test_fallback_on_empty_resolution(self) -> None:
        """resolve_section_gids returns empty dict -> project-level fetch is used."""
        t1 = _make_task("t1", "Offer 1", parent_gid="biz1")

        wf, mock_asana, _, _ = _make_workflow(offers=[t1])

        with patch(
            _RESOLVE_PATCH,
            return_value={},
        ):
            offers = await wf._enumerate_offers()

        assert len(offers) == 1
        assert offers[0]["gid"] == "t1"
        # Should have called project-level fetch (fallback)
        mock_asana.tasks.list_async.assert_called_once()
        call_kwargs = mock_asana.tasks.list_async.call_args[1]
        assert call_kwargs.get("project") == OFFER_PROJECT_GID


class TestEnumerateOffersFallbackOnPartialFetchFailure:
    """Fallback triggered when one section fetch raises during gather."""

    @pytest.mark.asyncio
    async def test_partial_fetch_failure_triggers_full_fallback(self) -> None:
        """One section fetch raises -> full fallback to project-level fetch."""
        t1 = _make_task("t1", "Offer 1", parent_gid="biz1")

        wf, mock_asana, _, _ = _make_workflow(offers=[t1])

        call_count = 0

        def list_async_dispatch(**kwargs):
            nonlocal call_count
            if kwargs.get("section") == "sec-good":
                return _AsyncIterator([_make_section_task("t1", "Offer 1", "biz1")])
            if kwargs.get("section") == "sec-bad":
                # Return an iterator whose collect() raises
                class _FailingIterator:
                    async def collect(self):
                        raise ConnectionError("section fetch failed")
                return _FailingIterator()
            # Project-level fallback
            call_count += 1
            return _AsyncIterator([t1])

        mock_asana.tasks.list_async.side_effect = list_async_dispatch

        with patch(
            _RESOLVE_PATCH,
            return_value={"good section": "sec-good", "bad section": "sec-bad"},
        ):
            offers = await wf._enumerate_offers()

        # Should have fallen back to project-level fetch
        assert call_count == 1
        assert len(offers) == 1
        assert offers[0]["gid"] == "t1"


class TestEnumerateOffersDedup:
    """Deduplication when same task appears in multiple sections."""

    @pytest.mark.asyncio
    async def test_dedup_multi_homed_task(self) -> None:
        """Same task GID in 2 sections appears exactly once in result."""
        # Same task in both sections
        t1_sec1 = _make_section_task("t1", "Multi-Homed", parent_gid="biz1")
        t1_sec2 = _make_section_task("t1", "Multi-Homed", parent_gid="biz1")
        t2 = _make_section_task("t2", "Unique", parent_gid="biz2")

        wf, mock_asana, _, _ = _make_workflow()

        def list_async_dispatch(**kwargs):
            if kwargs.get("section") == "sec-1":
                return _AsyncIterator([t1_sec1, t2])
            if kwargs.get("section") == "sec-2":
                return _AsyncIterator([t1_sec2])
            return _AsyncIterator([])

        mock_asana.tasks.list_async.side_effect = list_async_dispatch

        with patch(
            _RESOLVE_PATCH,
            return_value={"section a": "sec-1", "section b": "sec-2"},
        ):
            offers = await wf._enumerate_offers()

        # t1 appears in both sections but should only be in result once
        assert len(offers) == 2
        gids = [o["gid"] for o in offers]
        assert gids.count("t1") == 1
        assert gids.count("t2") == 1
