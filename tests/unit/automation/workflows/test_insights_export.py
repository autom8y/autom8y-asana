"""Tests for InsightsExportWorkflow.

Per TDD-EXPORT-001 Section 9.2: Unit tests for the insights export
workflow including happy path, skip scenarios, error isolation, upload-first
ordering, feature flag, concurrency, partial/total failure, and unused
asset derivation.
"""

from __future__ import annotations

import os
import pathlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.insights.tables import (
    DispatchType,
    TableSpec,
)
from autom8_asana.automation.workflows.insights.workflow import (
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
from autom8_asana.clients.data._endpoints._pacer import OperatorCallPacer
from autom8_asana.clients.data.models import (
    ColumnInfo,
    InsightsMetadata,
    InsightsResponse,
)
from autom8_asana.core.scope import EntityScope
from autom8_asana.errors import (
    OperatorAccessDeniedError,
    OperatorMintRefusedError,
)

# Patch path for resolve_section_gids (lazy import inside _enumerate_offers)
_RESOLVE_PATCH = "autom8_asana.automation.workflows.section_resolution.resolve_section_gids"


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
    section_name: str | None = "ACTIVE",
) -> MagicMock:
    """Create a mock task object.

    Args:
        gid: Task GID.
        name: Task name.
        parent_gid: Optional parent Business GID.
        completed: Whether the task is completed.
        section_name: Section name for memberships. Defaults to "ACTIVE"
            (classified as active by OFFER_CLASSIFIER). Set to None for
            no memberships.
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
    if section_name is not None:
        task.memberships = [
            {
                "project": {"gid": OFFER_PROJECT_GID},
                "section": {"name": section_name},
            }
        ]
    else:
        task.memberships = None
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


def _make_workflow(
    offers: list[MagicMock] | None = None,
    insights_response: InsightsResponse | None = None,
    insights_error: Exception | None = None,
    table_errors: dict[str, Exception] | None = None,
    existing_attachments: dict[str, list[MagicMock]] | None = None,
    preview_dir: pathlib.Path | None = None,
    operator_rows: list[dict[str, Any]] | None = None,
    operator_error: Exception | None = None,
    operator_insight_errors: dict[str, Exception] | None = None,
    operator_insight_rows: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[InsightsExportWorkflow, MagicMock, MagicMock, MagicMock]:
    """Build an InsightsExportWorkflow with configured mocks.

    GAP-1 PR-A: the cross-tenant export consumes the operator-plane batch
    (``get_operator_insights_batch_async``), NOT the per-table SA methods. This
    mocks the operator batch to return ``{phone: rows}`` for every requested phone
    and keeps the SA methods as AsyncMocks so tests can assert they are NEVER
    called on the cross-tenant path (M3 / AT-DROP-1).

    Args:
        offers: List of mock task objects for enumerate_offers.
        operator_rows: Rows each office receives for every clean table.
        operator_error: Exception the operator batch raises for ALL insights
            (e.g. OperatorMintRefusedError -> the INERT/dark-plane path).
        operator_insight_errors: Per-insight_name exception (e.g. one table denied).
        operator_insight_rows: Per-insight_name rows override.
        existing_attachments: Dict mapping offer GID -> attachments.

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

    # GAP-1: the operator-plane batch is the ONLY data path for the cross-tenant
    # export. Return the same rows for every requested office (the resolution
    # fixture maps all offers to one phone, so O is a single-element set).
    default_op_rows = operator_rows if operator_rows is not None else default_response.data

    async def mock_operator_batch(
        insight_name: str, phones: list[str], **kwargs: Any
    ) -> dict[str, list[dict[str, Any]]]:
        if operator_error is not None:
            raise operator_error
        if operator_insight_errors and insight_name in operator_insight_errors:
            raise operator_insight_errors[insight_name]
        rows = (operator_insight_rows or {}).get(insight_name, default_op_rows)
        return {phone: list(rows) for phone in phones}

    mock_data_client.get_operator_insights_batch_async = AsyncMock(side_effect=mock_operator_batch)

    # The SA per-table methods MUST NOT be called on the cross-tenant path (M3).
    # Keep them as AsyncMocks purely so call_count assertions can prove zero use;
    # a stray call returns benign data rather than a MagicMock.
    if insights_error:
        mock_data_client.get_insights_async = AsyncMock(side_effect=insights_error)
        mock_data_client.get_appointments_async = AsyncMock(side_effect=insights_error)
        mock_data_client.get_leads_async = AsyncMock(side_effect=insights_error)
        mock_data_client.get_reconciliation_async = AsyncMock(side_effect=insights_error)
    else:
        mock_data_client.get_insights_async = AsyncMock(return_value=default_response)
        mock_data_client.get_appointments_async = AsyncMock(return_value=default_response)
        mock_data_client.get_leads_async = AsyncMock(return_value=default_response)
        mock_data_client.get_reconciliation_async = AsyncMock(return_value=default_response)

    mock_data_client._circuit_breaker = MagicMock()
    mock_data_client._circuit_breaker.check = AsyncMock()
    # is_healthy() is the public health-check interface used by
    # BridgeWorkflowAction.validate_async() (per ADR-bridge-validate-extraction).
    mock_data_client.is_healthy = AsyncMock()

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
        preview_dir=preview_dir,
    )

    return workflow, mock_asana, mock_data_client, mock_attachments


def _default_params() -> dict[str, Any]:
    """Default params for execute_async calls."""
    return {"workflow_id": "insights-export"}


def _default_scope() -> EntityScope:
    """Default scope for full enumeration."""
    return EntityScope()


async def _enumerate_and_execute(
    wf: InsightsExportWorkflow,
    params: dict[str, Any] | None = None,
    scope: EntityScope | None = None,
) -> Any:
    """Helper: call enumerate_async then execute_async.

    Per TDD-ENTITY-SCOPE-001: The handler factory orchestrates
    enumerate -> execute. This helper simulates that for tests.
    """
    s = scope or _default_scope()
    p = params or _default_params()
    entities = await wf.enumerate_async(s)
    return await wf.execute_async(entities, p)


# --- Tests ---


class TestWorkflowId:
    """Test workflow_id property (AC-W01.1)."""

    def test_workflow_id(self) -> None:
        wf, _, _, _ = _make_workflow()
        assert wf.workflow_id == "insights-export"


class TestValidateAsync:
    """Tests for validate_async pre-flight checks (AC-W01.2, AC-W01.3, AC-W05.5, AC-W05.6)."""

    async def test_feature_flag_disabled_false(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "false"}):
            errors = await wf.validate_async()
        assert len(errors) == 1
        assert "disabled" in errors[0].lower()

    async def test_feature_flag_disabled_zero(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "0"}):
            errors = await wf.validate_async()
        assert len(errors) == 1

    async def test_feature_flag_disabled_no(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "no"}):
            errors = await wf.validate_async()
        assert len(errors) == 1

    async def test_feature_flag_enabled_default(self) -> None:
        """Unset env var means enabled."""
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop(EXPORT_ENABLED_ENV_VAR, None)
            errors = await wf.validate_async()
        assert errors == []

    async def test_feature_flag_enabled_true(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "true"}):
            errors = await wf.validate_async()
        assert errors == []

    async def test_circuit_breaker_open(self) -> None:
        wf, _, mock_data, _ = _make_workflow()

        from autom8y_http import CircuitBreakerOpenError as SdkCBOpen

        # Mock is_healthy() to raise CircuitBreakerOpenError, matching
        # the BridgeWorkflowAction.validate_async() code path
        # (per ADR-bridge-validate-extraction Decision 1).
        mock_data.is_healthy = AsyncMock(
            side_effect=SdkCBOpen(time_remaining=30.0, message="CB open")
        )
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop(EXPORT_ENABLED_ENV_VAR, None)
            errors = await wf.validate_async()
        assert len(errors) == 1
        assert "circuit breaker" in errors[0].lower()


@pytest.mark.usefixtures("_force_fallback")
class TestEnumeration:
    """Tests for offer enumeration (AC-W01.4) -- via fallback path."""

    async def test_only_non_completed_offers(self, mock_resolution_context) -> None:
        """Only non-completed offers are enumerated."""
        active_offer = _make_task("o1", "Active Offer", parent_gid="biz1")
        completed_offer = _make_task("o2", "Completed Offer", parent_gid="biz2", completed=True)

        wf, _, _, _ = _make_workflow(offers=[active_offer, completed_offer])

        result = await _enumerate_and_execute(wf)

        # Completed offer is filtered out during enumeration
        # Only 1 active offer processed
        assert result.total == 1

    async def test_enumeration_calls_correct_project(self) -> None:
        """Enumeration targets the correct project GID."""
        wf, mock_asana, _, _ = _make_workflow(offers=[])
        await _enumerate_and_execute(wf)

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


class TestActivityFiltering:
    """Tests for section-based activity filtering in _enumerate_offers."""

    async def test_offers_in_inactive_section_excluded(self, mock_resolution_context) -> None:
        """Offers in an INACTIVE section are excluded by enumeration."""
        active = _make_task("o1", "Active Offer", parent_gid="biz1", section_name="ACTIVE")
        inactive = _make_task("o2", "Inactive Offer", parent_gid="biz2", section_name="INACTIVE")
        wf, _, _, _ = _make_workflow(offers=[active, inactive])

        result = await _enumerate_and_execute(wf)

        # Only the ACTIVE offer should be processed
        assert result.total == 1
        assert result.succeeded == 1

    async def test_offers_in_unknown_section_excluded(self, mock_resolution_context) -> None:
        """Offers in an unknown/unclassified section are excluded."""
        active = _make_task("o1", "Active Offer", parent_gid="biz1", section_name="ACTIVE")
        unknown = _make_task(
            "o2",
            "Unknown Section",
            parent_gid="biz2",
            section_name="SomeUnknownSection",
        )
        wf, _, _, _ = _make_workflow(offers=[active, unknown])

        result = await _enumerate_and_execute(wf)

        assert result.total == 1
        assert result.succeeded == 1

    async def test_offers_with_no_memberships_excluded(self, mock_resolution_context) -> None:
        """Offers with no memberships (section_name=None) are excluded."""
        active = _make_task("o1", "Active Offer", parent_gid="biz1", section_name="ACTIVE")
        no_membership = _make_task("o2", "No Membership", parent_gid="biz2", section_name=None)
        wf, _, _, _ = _make_workflow(offers=[active, no_membership])

        result = await _enumerate_and_execute(wf)

        assert result.total == 1
        assert result.succeeded == 1

    async def test_activating_section_excluded(self, mock_resolution_context) -> None:
        """Offers in ACTIVATING sections are excluded (only ACTIVE passes)."""
        active = _make_task("o1", "Active", parent_gid="biz1", section_name="ACTIVE")
        activating = _make_task("o2", "Activating", parent_gid="biz2", section_name="ACTIVATING")
        wf, _, _, _ = _make_workflow(offers=[active, activating])

        result = await _enumerate_and_execute(wf)

        assert result.total == 1
        assert result.succeeded == 1


@pytest.mark.usefixtures("_force_fallback")
class TestResolution:
    """Tests for offer resolution (AC-W01.5, AC-W01.6) -- via fallback path."""

    async def test_successful_resolution(self, mock_resolution_context) -> None:
        """Successful resolution -> offer processed."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1])

        mock_resolution_context.set_business(
            office_phone="+17705753103",
            vertical="chiropractic",
            name="Acme Chiro",
        )

        result = await _enumerate_and_execute(wf)

        assert result.succeeded == 1
        assert result.skipped == 0

    async def test_skip_missing_phone(self, mock_resolution_context) -> None:
        """Missing office_phone -> offer skipped."""
        o1 = _make_task("o1", "Offer No Phone", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1])

        mock_resolution_context.set_business(office_phone=None)

        result = await _enumerate_and_execute(wf)

        assert result.total == 1
        assert result.skipped == 1
        assert result.succeeded == 0

    async def test_skip_missing_vertical(self, mock_resolution_context) -> None:
        """Missing vertical -> offer skipped."""
        o1 = _make_task("o1", "Offer No Vertical", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1])

        mock_resolution_context.set_business(vertical=None)

        result = await _enumerate_and_execute(wf)

        assert result.total == 1
        assert result.skipped == 1

    async def test_skip_no_parent(self) -> None:
        """Offer with no parent reference -> skipped."""
        o1 = _make_task("o1", "Orphan Offer")  # No parent_gid
        wf, _, _, _ = _make_workflow(offers=[o1])

        # The offer has no parent_gid from enumeration, and get_async
        # returns task with no parent either
        result = await _enumerate_and_execute(wf)

        assert result.total == 1
        assert result.skipped == 1


@pytest.mark.usefixtures("_force_fallback")
class TestFetchAllTables:
    """GAP-1: the 4 clean tables are served from the operator-plane batch."""

    async def test_operator_batch_fetched_once_per_clean_table(
        self, mock_resolution_context
    ) -> None:
        """One operator batch call per clean table (batch-over-O), NOT per office."""
        offers = [_make_task(f"o{i}", f"Offer {i}", parent_gid=f"biz{i}") for i in range(5)]
        wf, _, mock_data, _ = _make_workflow(offers=offers)

        await _enumerate_and_execute(wf)

        # 4 clean tables -> exactly 4 operator batch calls regardless of office count.
        assert mock_data.get_operator_insights_batch_async.call_count == TOTAL_TABLE_COUNT
        called_insights = {
            c.kwargs["insight_name"]
            for c in mock_data.get_operator_insights_batch_async.call_args_list
        }
        assert called_insights == {
            "account_level_stats",
            "offer_level_stats",
            "question_level_stats",
            "asset_level_stats",
        }

    async def test_clean_tables_use_correct_insight_names(self, mock_resolution_context) -> None:
        """Each clean table maps to its de-identified aggregate insight name."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, mock_data, _ = _make_workflow(offers=[o1])

        await _enumerate_and_execute(wf)

        by_insight = {
            c.kwargs["insight_name"]: c.kwargs
            for c in mock_data.get_operator_insights_batch_async.call_args_list
        }
        assert by_insight["account_level_stats"]["period"] == "lifetime"
        assert by_insight["offer_level_stats"]["period"] == "t30"
        assert by_insight["question_level_stats"]["period"] == "lifetime"
        assert by_insight["asset_level_stats"]["period"] == "t30"

    async def test_no_sa_fleet_read_methods_called(self, mock_resolution_context) -> None:
        """M3 / AT-DROP-1: the cross-tenant path NEVER calls the SA fleet-read methods."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, mock_data, _ = _make_workflow(offers=[o1])

        await _enumerate_and_execute(wf)

        mock_data.get_insights_async.assert_not_called()
        mock_data.get_appointments_async.assert_not_called()
        mock_data.get_leads_async.assert_not_called()
        mock_data.get_reconciliation_async.assert_not_called()

    async def test_batch_over_owned_set_single_call_for_many_offices(
        self, mock_resolution_context
    ) -> None:
        """All offers resolve to one phone -> one-element O sent to each batch call."""
        offers = [_make_task(f"o{i}", f"Offer {i}", parent_gid=f"biz{i}") for i in range(3)]
        wf, _, mock_data, _ = _make_workflow(offers=offers)

        await _enumerate_and_execute(wf)

        for c in mock_data.get_operator_insights_batch_async.call_args_list:
            # The resolution fixture maps every offer to +17705753103.
            assert c.kwargs["phones"] == ["+17705753103"]


@pytest.mark.usefixtures("_force_fallback")
class TestUploadAndCleanup:
    """Tests for upload and attachment cleanup (AC-W01.8-W01.10, AC-W03.11) -- via fallback."""

    async def test_upload_called_with_correct_params(self, mock_resolution_context) -> None:
        """Upload creates .md file with correct content type."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, mock_att = _make_workflow(offers=[o1])

        await _enumerate_and_execute(wf)

        assert mock_att.upload_async.call_count == 1
        call_kwargs = mock_att.upload_async.call_args[1]
        assert call_kwargs["parent"] == "o1"
        assert call_kwargs["content_type"] == "text/html"
        assert call_kwargs["name"].startswith("insights_export_")
        assert call_kwargs["name"].endswith(".html")

    async def test_old_attachments_deleted(self, mock_resolution_context) -> None:
        """Old matching attachments are deleted after upload."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        old_att = _make_attachment("old-att-1", "insights_export_Test_Business_20260201.html")

        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [old_att]},
        )

        await _enumerate_and_execute(wf)

        assert mock_att.delete_async.call_count == 1
        assert mock_att.delete_async.call_args[0][0] == "old-att-1"

    async def test_non_matching_attachments_not_deleted(self, mock_resolution_context) -> None:
        """Non-matching attachments are left alone."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        other_att = _make_attachment("other-att-1", "some_other_file.pdf")

        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [other_att]},
        )

        await _enumerate_and_execute(wf)

        mock_att.delete_async.assert_not_called()

    async def test_upload_before_delete(self, mock_resolution_context) -> None:
        """Upload-first: upload happens before delete (AC-W03.11)."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        old_att = _make_attachment("old-att-1", "insights_export_Test_Business_20260201.html")

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

        await _enumerate_and_execute(wf)

        assert call_order == ["upload", "delete"]


@pytest.mark.usefixtures("_force_fallback")
class TestConcurrency:
    """Tests for semaphore concurrency bounds (AC-W01.11) -- via fallback path."""

    async def test_max_concurrency_from_params(self, mock_resolution_context) -> None:
        """Verify max_concurrency parameter is respected."""
        offers = [_make_task(f"o{i}", f"Offer {i}", parent_gid=f"biz{i}") for i in range(10)]
        wf, _, _, _ = _make_workflow(offers=offers)

        params = {**_default_params(), "max_concurrency": 2}
        result = await _enumerate_and_execute(wf, params=params)

        # All should succeed even with low concurrency
        assert result.total == 10
        assert result.succeeded == 10

    async def test_default_concurrency_used(self) -> None:
        """Default max_concurrency is used when not specified."""
        wf, _, _, _ = _make_workflow(offers=[])
        # Simply verify it doesn't fail with default params
        result = await _enumerate_and_execute(wf)
        assert result.total == 0


@pytest.mark.usefixtures("_force_fallback")
class TestWorkflowResult:
    """Tests for WorkflowResult structure (AC-W01.12, AC-W02.4) -- via fallback path."""

    async def test_result_includes_per_offer_table_counts(self, mock_resolution_context) -> None:
        """Result metadata includes per-offer table counts."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1])

        result = await _enumerate_and_execute(wf)

        assert "per_offer_table_counts" in result.metadata
        assert "total_tables_succeeded" in result.metadata
        assert "total_tables_failed" in result.metadata
        # With all tables succeeding
        assert result.metadata["total_tables_succeeded"] == TOTAL_TABLE_COUNT
        assert result.metadata["total_tables_failed"] == 0

    async def test_result_totals(self, mock_resolution_context) -> None:
        """Result has correct total/succeeded/failed/skipped."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        o2 = _make_task("o2", "Offer 2", parent_gid="biz2")
        o3 = _make_task("o3", "Offer No Parent")  # Will be skipped

        wf, _, _, _ = _make_workflow(offers=[o1, o2, o3])

        result = await _enumerate_and_execute(wf)

        assert result.total == 3
        assert result.succeeded == 2
        assert result.skipped == 1
        assert result.workflow_id == "insights-export"


@pytest.mark.usefixtures("_force_fallback")
class TestPartialAllowlist:
    """GAP-1: one insight denied (e.g. not yet allowlisted) -> that table is a TYPED
    denial (not silently empty); the rest serve and the deck still publishes."""

    async def test_one_insight_denied_others_serve(self, mock_resolution_context) -> None:
        """A 404 on offer_level_stats makes OFFER TABLE a typed denial; the rest serve.

        provenance-to-the-human Sprint-3: the denied table is now counted as FAILED
        (a typed refusal routed through the error channel), NOT as a silently-
        succeeded empty table. This asserts the counter altitude only -- the render-
        level two-sided proof (denied -> typed error-box vs genuinely-empty -> empty
        section, at the consumed HTML) is the disjoint numerical-adversary's fixture
        against the named _fetch_table fire-seam, authored separately.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            operator_insight_errors={
                "offer_level_stats": OperatorAccessDeniedError(
                    "not allowlisted", reason="route_denied_404", status_code=404
                )
            },
        )

        result = await _enumerate_and_execute(wf)

        # Offer still succeeds (3 tables serve + 1 typed denial); report uploaded.
        # The daily-run-doesn't-crash intent is preserved: a per-table denial does
        # NOT abort the offer.
        assert result.succeeded == 1
        assert mock_att.upload_async.call_count == 1
        # The denied table is now a TYPED refusal -> counted as failed, no longer
        # null-coerced into a silently-succeeded empty table (the C2 drift is dead).
        table_counts = result.metadata["per_offer_table_counts"]["o1"]
        assert table_counts["tables_succeeded"] == TOTAL_TABLE_COUNT - 1
        assert table_counts["tables_failed"] == 1


@pytest.mark.usefixtures("_force_fallback")
class TestOperatorPlaneInertNoOp:
    """GAP-1 deploy-INERT: a mint REFUSAL makes the export a TRUE no-op.

    The hazard (rite-disjoint gate finding): the un-guarded INERT path
    UPLOADED an empty HTML deck per Offer and DELETED prior matching
    attachments. If the EventBridge schedule fired pre-FLIP, every Offer's
    prior (last-good) deck was replaced with an empty one -- a real
    (non-PII) data-loss regression.

    The fix: on ``OperatorMintRefusedError`` the publish step is SKIPPED
    ENTIRELY -- no empty deck is built/uploaded and NO prior attachment is
    deleted; prior decks stay intact. Two-sided canary:

    - REFUSAL arm -> NO upload, NO delete, prior attachment untouched, the
      INERT WARNING is emitted, and nothing is counted as succeeded
      (the counter stays RED).
    - LIVE arm -> mint succeeds, so upload + prior-delete still happen
      (no regression).

    A third test pins the distinction: a successful-but-EMPTY live result
    is NOT a refusal, so it still follows the normal publish path.
    """

    async def test_mint_refused_is_true_no_op(self, mock_resolution_context) -> None:
        """REFUSAL arm: NO upload, NO delete; prior deck untouched; counter RED.

        RED against the un-guarded behavior (empty deck uploaded + prior
        attachment deleted); GREEN once the INERT no-op guard skips publish.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        prior_deck = _make_attachment("prior-deck-1", "insights_export_Acme_20260201.html")
        wf, _, mock_data, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [prior_deck]},
            operator_error=OperatorMintRefusedError(
                "operator token mint refused (HTTP 403)",
                reason="mint_refused_403",
                status_code=403,
            ),
        )

        with patch("autom8_asana.automation.workflows.insights.workflow.logger") as mock_logger:
            result = await _enumerate_and_execute(wf)

        # TRUE no-op: NOTHING published, NOTHING deleted -> prior deck intact.
        mock_att.upload_async.assert_not_called()
        mock_att.delete_async.assert_not_called()
        # We never even list a task's attachments for deletion on the INERT path.
        mock_att.list_for_task_async.assert_not_called()
        # G-NO-FALLBACK: the SA fleet-read methods are NEVER called.
        mock_data.get_insights_async.assert_not_called()
        mock_data.get_appointments_async.assert_not_called()
        mock_data.get_leads_async.assert_not_called()
        mock_data.get_reconciliation_async.assert_not_called()
        # Counter stays RED: nothing succeeded; the whole run is INERT (all skipped).
        assert result.total == 1
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.skipped == 1
        assert result.metadata.get("operator_plane_inert") is True
        # The INERT skip WARNING is emitted.
        warning_events = [c.args[0] for c in mock_logger.warning.call_args_list if c.args]
        assert "insights_export_skipped_operator_plane_inert" in warning_events

    async def test_live_mint_still_uploads_and_deletes(self, mock_resolution_context) -> None:
        """LIVE arm (no regression): mint succeeds -> upload + prior-delete happen."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        prior_deck = _make_attachment("prior-deck-1", "insights_export_Acme_20260201.html")
        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [prior_deck]},
        )

        result = await _enumerate_and_execute(wf)

        assert result.succeeded == 1
        assert mock_att.upload_async.call_count == 1
        assert mock_att.delete_async.call_count == 1
        assert mock_att.delete_async.call_args[0][0] == "prior-deck-1"

    async def test_successful_but_empty_live_result_still_publishes(
        self, mock_resolution_context
    ) -> None:
        """Distinction: a successful-but-EMPTY live result is NOT a refusal.

        Only a mint REFUSAL triggers the no-op skip. A live mint that returns
        genuinely-empty data still follows the existing publish-empty behavior
        (the counter behavior is unchanged for the non-INERT path).
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, mock_data, mock_att = _make_workflow(
            offers=[o1],
            operator_rows=[],  # mint SUCCEEDS, returns empty rows for every office
        )

        result = await _enumerate_and_execute(wf)

        # Live (non-INERT) path is unchanged: the empty deck is still published.
        assert result.succeeded == 1
        assert mock_att.upload_async.call_count == 1
        # Still no SA fleet-read fallback on the live path (G-NO-FALLBACK).
        mock_data.get_insights_async.assert_not_called()
        mock_data.get_appointments_async.assert_not_called()
        mock_data.get_leads_async.assert_not_called()
        mock_data.get_reconciliation_async.assert_not_called()
        # All clean tables are empty-but-success (counter stays RED on content).
        counts = result.metadata["per_offer_table_counts"]["o1"]
        assert counts["tables_succeeded"] == TOTAL_TABLE_COUNT
        assert counts["tables_failed"] == 0


@pytest.mark.usefixtures("_force_fallback")
class TestDeleteFailureTolerance:
    """Tests for non-fatal delete failure -- via fallback path."""

    async def test_delete_failure_still_succeeded(self, mock_resolution_context) -> None:
        """Delete-old fails -> offer still counted as succeeded."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        old_att = _make_attachment("old-att-1", "insights_export_Test_Business_20260201.md")

        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [old_att]},
        )

        # Make delete fail
        mock_att.delete_async = AsyncMock(side_effect=Exception("Asana API error"))

        result = await _enumerate_and_execute(wf)

        # Still succeeded because upload worked; delete failure is non-fatal
        assert result.succeeded == 1
        assert result.failed == 0


@pytest.mark.usefixtures("_force_fallback")
class TestEmptyProject:
    """Tests for empty project (no offers) -- via fallback path."""

    async def test_no_offers(self) -> None:
        """Empty project -> total=0, all zeros."""
        wf, _, _, _ = _make_workflow(offers=[])

        result = await _enumerate_and_execute(wf)

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
        assert _sanitize_business_name("") == "unknown"

    def test_all_special_chars_returns_unknown(self) -> None:
        """All-special-char names produce 'unknown' instead of empty string (F-10)."""
        assert _sanitize_business_name("!@#$%^&*()") == "unknown"

    def test_underscores_preserved(self) -> None:
        assert _sanitize_business_name("my_business") == "my_business"


class TestConstants:
    """Tests for module constants."""

    def test_table_names_count(self) -> None:
        # GAP-1 PR-A: the cross-tenant export serves the 4 CLEAN de-identified
        # aggregate tables (PII dropped; BY-period + UNUSED ASSETS deferred to FF).
        assert TOTAL_TABLE_COUNT == 4
        assert len(TABLE_NAMES) == 4

    def test_table_names_are_the_four_clean_tables(self) -> None:
        assert set(TABLE_NAMES) == {"SUMMARY", "AD QUESTIONS", "ASSET TABLE", "OFFER TABLE"}
        # The dropped PII tables are gone from the cross-tenant view.
        for dropped in (
            "APPOINTMENTS",
            "LEADS",
            "LIFETIME RECONCILIATIONS",
            "T14 RECONCILIATIONS",
            "UNUSED ASSETS",
            "BY QUARTER",
        ):
            assert dropped not in TABLE_NAMES

    def test_offer_project_gid(self) -> None:
        assert OFFER_PROJECT_GID == "1143843662099250"

    def test_default_row_limits(self) -> None:
        # GAP-1 PR-A: APPOINTMENTS/LEADS dropped (PII); only ASSET TABLE remains.
        assert DEFAULT_ROW_LIMITS == {
            "ASSET TABLE": 150,
        }

    def test_default_max_concurrency(self) -> None:
        assert DEFAULT_MAX_CONCURRENCY == 5

    def test_default_attachment_pattern(self) -> None:
        assert DEFAULT_ATTACHMENT_PATTERN == "insights_export_*.html"


# --- QA-ADVERSARY: Additional Edge Case Tests ---


class TestAdversarialFeatureFlag:
    """QA-ADVERSARY: Feature flag edge cases (AC-W05.5, AC-W05.6)."""

    async def test_feature_flag_empty_string_means_enabled(self) -> None:
        """AUTOM8_EXPORT_ENABLED='' (empty string) means enabled."""
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: ""}):
            errors = await wf.validate_async()
        assert errors == []

    async def test_feature_flag_uppercase_FALSE(self) -> None:
        """AUTOM8_EXPORT_ENABLED='FALSE' (uppercase) means disabled."""
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "FALSE"}):
            errors = await wf.validate_async()
        assert len(errors) == 1
        assert "disabled" in errors[0].lower()

    async def test_feature_flag_mixed_case_No(self) -> None:
        """AUTOM8_EXPORT_ENABLED='No' (mixed case) means disabled."""
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {EXPORT_ENABLED_ENV_VAR: "No"}):
            errors = await wf.validate_async()
        assert len(errors) == 1

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

    async def test_upload_failure_prevents_delete(self, mock_resolution_context) -> None:
        """If upload_async raises, delete_old_attachments is never called."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        old_att = _make_attachment("old-att-1", "insights_export_Test_Business_20260201.md")

        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [old_att]},
        )

        # Make upload fail
        mock_att.upload_async = AsyncMock(side_effect=Exception("Upload failed"))

        result = await _enumerate_and_execute(wf)

        # Offer should be failed
        assert result.failed == 1
        assert result.succeeded == 0
        # Delete should NOT have been called (upload failed first)
        mock_att.delete_async.assert_not_called()


@pytest.mark.usefixtures("_force_fallback")
class TestAdversarialComposeRaisesPreventsUpload:
    """QA-ADVERSARY: If compose_report raises, no upload occurs -- via fallback."""

    async def test_compose_failure_marks_offer_failed(self, mock_resolution_context) -> None:
        """An exception in compose_report is caught by _process_offer."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")

        wf, _, _, mock_att = _make_workflow(offers=[o1])

        with patch(
            "autom8_asana.automation.workflows.insights.workflow.compose_report",
            side_effect=TypeError("Unexpected data format"),
        ):
            result = await _enumerate_and_execute(wf)

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

    async def test_section_targeted_skips_completed(self) -> None:
        """Completed tasks from section fetch are excluded."""
        t1 = _make_section_task("t1", "Active", parent_gid="biz1")
        t2 = _make_section_task("t2", "Done", parent_gid="biz2", completed=True)

        wf, mock_asana, _, _ = _make_workflow()
        mock_asana.tasks.list_async.side_effect = lambda **kw: _AsyncIterator([t1, t2])

        with patch(
            _RESOLVE_PATCH,
            return_value={"section": "sec-1"},
        ):
            offers = await wf._enumerate_offers()

        assert len(offers) == 1
        assert offers[0]["gid"] == "t1"

    async def test_section_targeted_no_parent_gid_in_dict(self) -> None:
        """Enumeration dicts do not include parent_gid (resolution handles traversal)."""
        t1 = _make_section_task("t1", "No Parent")

        wf, mock_asana, _, _ = _make_workflow()
        mock_asana.tasks.list_async.side_effect = lambda **kw: _AsyncIterator([t1])

        with patch(
            _RESOLVE_PATCH,
            return_value={"section": "sec-1"},
        ):
            offers = await wf._enumerate_offers()

        assert len(offers) == 1
        assert "parent_gid" not in offers[0]

    async def test_section_targeted_opt_fields(self) -> None:
        """Section-level fetch uses reduced opt_fields (no memberships)."""
        wf, mock_asana, _, _ = _make_workflow()
        mock_asana.tasks.list_async.side_effect = lambda **kw: _AsyncIterator([])

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


# --- enumerate_async Tests (TDD-ENTITY-SCOPE-001 Section 8.3) ---


class TestEnumerateAsync:
    """Tests for the enumerate_async protocol method."""

    async def test_enumerate_with_entity_ids_returns_synthetic_dicts(self) -> None:
        """Targeted scope returns synthetic dicts with gid, name=None."""
        wf, _, _, _ = _make_workflow()
        scope = EntityScope(entity_ids=("111", "222"))
        result = await wf.enumerate_async(scope)
        assert len(result) == 2
        assert result[0] == {"gid": "111", "name": None}
        assert result[1] == {"gid": "222", "name": None}

    @pytest.mark.usefixtures("_force_fallback")
    async def test_enumerate_without_entity_ids_calls_enumerate_offers(self) -> None:
        """Full scope triggers _enumerate_offers."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1])
        scope = EntityScope()
        result = await wf.enumerate_async(scope)
        assert len(result) == 1
        assert result[0]["gid"] == "o1"

    @pytest.mark.usefixtures("_force_fallback")
    async def test_enumerate_with_limit_truncates(self) -> None:
        """scope.limit=2 with 5 offers returns 2."""
        offers = [_make_task(f"o{i}", f"Offer {i}", parent_gid="biz1") for i in range(5)]
        wf, _, _, _ = _make_workflow(offers=offers)
        scope = EntityScope(limit=2)
        result = await wf.enumerate_async(scope)
        assert len(result) == 2

    async def test_enumerate_targeted_does_not_call_enumerate_offers(self) -> None:
        """_enumerate_offers mock NOT called when entity_ids are provided."""
        wf, mock_asana, _, _ = _make_workflow()
        scope = EntityScope(entity_ids=("999",))
        await wf.enumerate_async(scope)
        # With targeted scope, tasks.list_async should NOT be called
        mock_asana.tasks.list_async.assert_not_called()


# --- Dry-Run Tests (TDD-ENTITY-SCOPE-001 Section 8.6) ---


class TestDryRun:
    """Tests for dry_run gating in _process_offer."""

    @pytest.mark.usefixtures("_force_fallback")
    async def test_dry_run_skips_upload(self, mock_resolution_context, tmp_path) -> None:
        """_attachments_client.upload_async NOT called in dry_run mode."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, mock_att = _make_workflow(offers=[o1], preview_dir=tmp_path)

        scope = EntityScope(dry_run=True)
        entities = await wf.enumerate_async(scope)
        params = {**_default_params(), "dry_run": True}
        await wf.execute_async(entities, params)

        mock_att.upload_async.assert_not_called()

    @pytest.mark.usefixtures("_force_fallback")
    async def test_dry_run_skips_delete(self, mock_resolution_context, tmp_path) -> None:
        """_delete_old_attachments NOT called in dry_run mode."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        existing = [_make_attachment("att1", "insights_export_old.md")]
        wf, _, _, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": existing},
            preview_dir=tmp_path,
        )

        scope = EntityScope(dry_run=True)
        entities = await wf.enumerate_async(scope)
        params = {**_default_params(), "dry_run": True}
        await wf.execute_async(entities, params)

        mock_att.delete_async.assert_not_called()

    @pytest.mark.usefixtures("_force_fallback")
    async def test_dry_run_metadata_flag(self, mock_resolution_context, tmp_path) -> None:
        """metadata['dry_run'] is True when dry_run=True."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1], preview_dir=tmp_path)

        scope = EntityScope(dry_run=True)
        entities = await wf.enumerate_async(scope)
        params = {**_default_params(), "dry_run": True}
        result = await wf.execute_async(entities, params)

        assert result.metadata.get("dry_run") is True

    async def test_dry_run_writes_preview_files(self, mock_resolution_context, tmp_path) -> None:
        """Dry-run writes full HTML to the (injected) preview dir, reports paths in metadata."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1], preview_dir=tmp_path)

        scope = EntityScope(dry_run=True)
        entities = await wf.enumerate_async(scope)
        params = {**_default_params(), "dry_run": True}
        result = await wf.execute_async(entities, params)

        paths = result.metadata.get("preview_paths")
        assert paths is not None
        assert isinstance(paths, dict)
        assert "o1" in paths
        # Verify the file was written under the per-test isolated preview dir
        # (no shared cwd-relative .wip path → no xdist write/read truncation race).
        preview_file = pathlib.Path(paths["o1"])
        assert preview_file.parent == tmp_path
        assert preview_file.exists()
        content = preview_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Test Business" in content
        # Cleanup
        preview_file.unlink(missing_ok=True)


# --- GAP-1 PR-A: OQ-4a asana-side activity filter ---


class TestActivityFilterArm:
    """GAP-1: OQ-4a -- ASSET TABLE / AD QUESTIONS drop zero-activity rows asana-side."""

    async def test_asset_table_drops_zero_activity_rows(self) -> None:
        """ASSET TABLE keeps spend>0 OR leads>0; zero-activity rows are removed."""
        phone = "+17705753103"
        rows = [
            {"name": "active spend", "spend": 100, "leads": 0},
            {"name": "active leads", "spend": 0, "leads": 3},
            {"name": "zero activity", "spend": 0, "leads": 0},
        ]
        wf, _, _, _ = _make_workflow()
        # Pre-populate the batch-over-O cache (normally filled by the prefetch).
        wf._operator_batch = {"ASSET TABLE": {phone: rows}}

        table_results = await wf._fetch_all_tables(
            office_phone=phone,
            vertical="chiropractic",
            row_limits=DEFAULT_ROW_LIMITS,
            offer_gid="o1",
        )

        asset = table_results["ASSET TABLE"]
        assert asset.success is True
        # The zero-activity row is dropped (OQ-4a).
        assert asset.row_count == 2
        names = {r["name"] for r in asset.data}
        assert "zero activity" not in names

    async def test_summary_is_not_activity_filtered(self) -> None:
        """SUMMARY (account_level_stats) has no activity filter -> rows pass through."""
        phone = "+17705753103"
        rows = [{"office": "A", "spend": 0, "leads": 0}]
        wf, _, _, _ = _make_workflow()
        wf._operator_batch = {"SUMMARY": {phone: rows}}

        table_results = await wf._fetch_all_tables(
            office_phone=phone,
            vertical="chiropractic",
            row_limits=DEFAULT_ROW_LIMITS,
            offer_gid="o1",
        )

        summary = table_results["SUMMARY"]
        assert summary.success is True
        assert summary.row_count == 1


# --- F-02: Business Cache Dedup Tests ---


class TestBusinessCacheDedup:
    """F-02: Verify business cache keys by business_gid, not offer_gid.

    Two sibling offers sharing the same parent Business should:
    - Share one _business_cache entry (keyed by business_gid)
    - Have separate _offer_to_business entries
    - Increment _cache_hits on the sibling detection path
    - Return identical (phone, vertical, name) tuples
    """

    async def test_sibling_offers_share_business_cache_entry(self, mock_resolution_context) -> None:
        """Two offers resolving to the same business_gid share one cache entry."""
        shared_business_gid = "biz-shared-123"
        offer_a = _make_task("offer-a", "Offer A", parent_gid="holder-a")
        offer_b = _make_task("offer-b", "Offer B", parent_gid="holder-b")

        wf, mock_asana, _, _ = _make_workflow(offers=[offer_a, offer_b])

        # Both offers resolve to the same business
        biz = mock_resolution_context.set_business(
            office_phone="+17705553000",
            vertical="chiropractic",
            name="Shared Business",
        )
        biz.gid = shared_business_gid

        result_a = await wf._resolve_offer("offer-a")
        result_b = await wf._resolve_offer("offer-b")

        # Both return same tuple
        assert result_a == ("+17705553000", "chiropractic", "Shared Business")
        assert result_b == result_a

        # One business_cache entry, two offer_to_business entries
        assert len(wf._business_cache) == 1
        assert shared_business_gid in wf._business_cache
        assert len(wf._offer_to_business) == 2
        assert wf._offer_to_business["offer-a"] == shared_business_gid
        assert wf._offer_to_business["offer-b"] == shared_business_gid

        # Sibling detection incremented cache_hits
        assert wf._cache_hits >= 1

    async def test_same_offer_gid_hits_offer_cache(self, mock_resolution_context) -> None:
        """Re-resolving the same offer_gid returns from _offer_to_business cache."""
        offer = _make_task("offer-1", "Offer 1", parent_gid="holder-1")
        wf, _, _, _ = _make_workflow(offers=[offer])

        mock_resolution_context.mock_business.gid = "biz-1"

        first = await wf._resolve_offer("offer-1")
        second = await wf._resolve_offer("offer-1")

        assert first == second
        # Second call should be a cache hit
        assert wf._cache_hits == 1
        # ResolutionContext should only have been entered once
        assert mock_resolution_context.mock_rc.return_value.__aenter__.call_count == 1

    async def test_failed_resolution_cached_as_none(self) -> None:
        """Offer whose parent has no GID is cached as None in _offer_to_business."""
        offer = _make_task("offer-orphan", "Orphan", parent_gid=None)
        wf, _, _, _ = _make_workflow(offers=[offer])

        result = await wf._resolve_offer("offer-orphan")

        assert result is None
        assert wf._offer_to_business["offer-orphan"] is None
        # No business_cache entry for None resolution
        assert len(wf._business_cache) == 0


# --- WS-2: run-scoped pacer threading + partial-run deck protection ---


@pytest.mark.usefixtures("_force_fallback")
class TestOperatorPacerThreading:
    """RISK-5: ONE shared pacer threaded across all 4 insight calls (not 4xB)."""

    async def test_one_pacer_shared_across_all_insight_calls(self, mock_resolution_context) -> None:
        """The workflow builds ONE pacer per run and passes the SAME instance to
        every operator insight call -- so the aggregate wire-call cap is per-RUN."""
        offers = [_make_task(f"o{i}", f"Offer {i}", parent_gid=f"biz{i}") for i in range(3)]
        wf, _, mock_data, _ = _make_workflow(offers=offers)
        # The MagicMock data client returns a MagicMock from new_operator_pacer();
        # wire a REAL run-scoped pacer so threading/identity is exercised.
        mock_data.new_operator_pacer = lambda: OperatorCallPacer()

        captured: list[object] = []

        async def capture_pacer(
            insight_name: str, phones: list[str], *, pacer: object = None, **kwargs: Any
        ) -> dict[str, list[dict[str, Any]]]:
            captured.append(pacer)
            return {p: [{"x": 1}] for p in phones}

        mock_data.get_operator_insights_batch_async = AsyncMock(side_effect=capture_pacer)

        await _enumerate_and_execute(wf)

        # One call per clean table, every one carrying the SAME pacer instance.
        assert len(captured) == TOTAL_TABLE_COUNT
        assert captured[0] is not None
        assert isinstance(captured[0], OperatorCallPacer)
        assert all(p is captured[0] for p in captured)


@pytest.mark.usefixtures("_force_fallback")
class TestPartialRunDeckProtection:
    """RISK-4: a budget-capped partial run must NOT overwrite an unreached office's
    prior deck (no empty-deck upload, no prior-attachment delete)."""

    async def test_budget_unreached_office_skips_publish_prior_deck_intact(
        self, mock_resolution_context
    ) -> None:
        """The operator batch leaves the resolved office unreached (budget-capped) ->
        the offer is SKIPPED: NO upload, NO delete, prior deck intact, run partial."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        prior_deck = _make_attachment("prior-deck-1", "insights_export_Acme_20260201.html")
        wf, _, mock_data, mock_att = _make_workflow(
            offers=[o1],
            existing_attachments={"o1": [prior_deck]},
        )
        # Wire a REAL pacer (the MagicMock client otherwise returns a MagicMock).
        mock_data.new_operator_pacer = lambda: OperatorCallPacer()

        async def unreached_mock(
            insight_name: str, phones: list[str], *, pacer: Any = None, **kwargs: Any
        ) -> dict[str, list[dict[str, Any]]]:
            # Simulate the bisection running out of budget before serving these
            # offices: mark them unreached (NON-definitive) and serve nothing.
            if pacer is not None:
                pacer.mark_unreached(phones)
            return {}

        mock_data.get_operator_insights_batch_async = AsyncMock(side_effect=unreached_mock)

        with patch("autom8_asana.automation.workflows.insights.workflow.logger") as mock_logger:
            result = await _enumerate_and_execute(wf)

        # Prior deck protected: NO upload, NO delete, no list-for-delete.
        mock_att.upload_async.assert_not_called()
        mock_att.delete_async.assert_not_called()
        mock_att.list_for_task_async.assert_not_called()
        # The offer is SKIPPED (not failed, not succeeded).
        assert result.total == 1
        assert result.succeeded == 0
        assert result.skipped == 1
        # The run is honestly flagged partial.
        assert result.metadata.get("operator_run_partial") is True
        assert result.metadata.get("operator_unreached_office_count") == 1
        # The per-office protection WARNING is emitted.
        warning_events = [c.args[0] for c in mock_logger.warning.call_args_list if c.args]
        assert "insights_export_offer_skipped_budget_unreached" in warning_events

    async def test_process_offer_skips_unreached_office_directly(
        self, mock_resolution_context
    ) -> None:
        """Unit guard: an office in _operator_unreached_offices skips publish."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, mock_att = _make_workflow(offers=[o1])
        wf._operator_unreached_offices = {"+17705753103"}  # the resolution-fixture phone

        outcome = await wf._process_offer(
            offer_gid="o1",
            offer_name="Offer 1",
            attachment_pattern=DEFAULT_ATTACHMENT_PATTERN,
            row_limits=DEFAULT_ROW_LIMITS,
        )

        assert outcome.status == "skipped"
        assert outcome.reason == "operator_budget_unreached"
        mock_att.upload_async.assert_not_called()
        mock_att.delete_async.assert_not_called()

    async def test_fully_served_run_publishes_and_is_not_partial(
        self, mock_resolution_context
    ) -> None:
        """Positive control: a fully-served run publishes and is NOT flagged partial."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, mock_att = _make_workflow(offers=[o1])

        result = await _enumerate_and_execute(wf)

        # Fully served -> normal publish path runs; no partial flag, no unreached.
        mock_att.upload_async.assert_called_once()
        assert result.succeeded == 1
        assert result.metadata.get("operator_run_partial") is None
        assert wf._operator_unreached_offices == set()
