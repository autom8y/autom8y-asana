"""Tests for FieldWriteService.

Per TDD-ENTITY-WRITE-API Section 16.3:
    Validates the validate-resolve-write-invalidate pipeline,
    including single field writes, partial success, error mapping,
    membership verification, and cache invalidation.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.exceptions import NotFoundError, RateLimitError
from autom8_asana.resolution.write_registry import (
    CORE_FIELD_NAMES,
    EntityWriteRegistry,
    WritableEntityInfo,
)
from autom8_asana.services.errors import (
    EntityTypeMismatchError,
    NoValidFieldsError,
    TaskNotFoundError,
)
from autom8_asana.services.field_write_service import FieldWriteService

# ---------------------------------------------------------------------------
# Test data constants
# ---------------------------------------------------------------------------

PROJECT_GID = "1143843662099250"

MOCK_CUSTOM_FIELDS = [
    {
        "gid": "cf_111",
        "name": "Weekly Ad Spend",
        "resource_subtype": "number",
        "text_value": None,
        "number_value": 100,
        "enum_value": None,
        "multi_enum_values": [],
        "enum_options": [],
    },
    {
        "gid": "cf_222",
        "name": "Status",
        "resource_subtype": "enum",
        "text_value": None,
        "number_value": None,
        "enum_value": {"gid": "opt_active", "name": "Active"},
        "multi_enum_values": [],
        "enum_options": [
            {"gid": "opt_active", "name": "Active", "enabled": True},
            {"gid": "opt_paused", "name": "Paused", "enabled": True},
        ],
    },
    {
        "gid": "cf_333",
        "name": "Asset ID",
        "resource_subtype": "text",
        "text_value": "asset-100",
        "number_value": None,
        "enum_value": None,
        "multi_enum_values": [],
        "enum_options": [],
    },
]

MOCK_TASK_DATA: dict = {
    "gid": "9999999999",
    "name": "Test Offer",
    "assignee": None,
    "due_on": None,
    "completed": False,
    "notes": "",
    "custom_fields": MOCK_CUSTOM_FIELDS,
    "memberships": [
        {"project": {"gid": PROJECT_GID}},
    ],
}

DESCRIPTOR_INDEX = {
    "weekly_ad_spend": "Weekly Ad Spend",
    "status": "Status",
    "asset_id": "Asset ID",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_write_info() -> WritableEntityInfo:
    return WritableEntityInfo(
        entity_type="offer",
        model_class=type("FakeOffer", (), {}),
        project_gid=PROJECT_GID,
        descriptor_index=DESCRIPTOR_INDEX,
        core_fields=CORE_FIELD_NAMES,
    )


def _make_write_registry(
    writable: bool = True,
) -> EntityWriteRegistry:
    """Build a mock EntityWriteRegistry."""
    registry = MagicMock(spec=EntityWriteRegistry)
    if writable:
        info = _make_write_info()
        registry.get.return_value = info
        registry.is_writable.return_value = True
        registry.writable_types.return_value = ["offer"]
    else:
        registry.get.return_value = None
        registry.is_writable.return_value = False
        registry.writable_types.return_value = []
    return registry


def _make_mock_client(
    task_data: dict | None = None,
    get_side_effect: Exception | None = None,
    update_side_effect: Exception | None = None,
) -> MagicMock:
    """Build a mock AsanaClient with tasks sub-client."""
    client = MagicMock()
    tasks = MagicMock()

    if get_side_effect is not None:
        tasks.get_async = AsyncMock(side_effect=get_side_effect)
    else:
        tasks.get_async = AsyncMock(return_value=task_data or MOCK_TASK_DATA)

    if update_side_effect is not None:
        tasks.update_async = AsyncMock(side_effect=update_side_effect)
    else:
        tasks.update_async = AsyncMock(return_value=task_data or MOCK_TASK_DATA)

    client.tasks = tasks
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFieldWriteService:
    """Per TDD-ENTITY-WRITE-API Section 16.3."""

    @pytest.mark.asyncio
    async def test_write_success_single_field(self) -> None:
        """Single field write returns fields_written=1."""
        client = _make_mock_client()
        registry = _make_write_registry()
        service = FieldWriteService(client, registry)

        result = await service.write_async(
            entity_type="offer",
            gid="9999999999",
            fields={"weekly_ad_spend": 500},
        )

        assert result.fields_written == 1
        assert result.fields_skipped == 0
        assert result.gid == "9999999999"
        assert result.entity_type == "offer"
        client.tasks.update_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_write_partial_success(self) -> None:
        """3 valid + 1 invalid returns fields_written=3, fields_skipped=1."""
        client = _make_mock_client()
        registry = _make_write_registry()
        service = FieldWriteService(client, registry)

        result = await service.write_async(
            entity_type="offer",
            gid="9999999999",
            fields={
                "name": "Updated Name",  # core field
                "weekly_ad_spend": 500,  # custom via descriptor
                "Status": "Active",  # custom via display name
                "nonexistent_field": "value",  # will be skipped
            },
        )

        assert result.fields_written == 3
        assert result.fields_skipped == 1
        # Check that the skipped field is reported correctly
        skipped = [rf for rf in result.field_results if rf.status == "skipped"]
        assert len(skipped) == 1
        assert skipped[0].input_name == "nonexistent_field"

    @pytest.mark.asyncio
    async def test_write_all_invalid_raises(self) -> None:
        """All fields invalid raises NoValidFieldsError."""
        client = _make_mock_client()
        registry = _make_write_registry()
        service = FieldWriteService(client, registry)

        with pytest.raises(NoValidFieldsError):
            await service.write_async(
                entity_type="offer",
                gid="9999999999",
                fields={"bogus_field_1": "x", "bogus_field_2": "y"},
            )

    @pytest.mark.asyncio
    async def test_task_not_found_raises(self) -> None:
        """Asana 404 raises TaskNotFoundError."""
        client = _make_mock_client(
            get_side_effect=NotFoundError("Not found", status_code=404)
        )
        registry = _make_write_registry()
        service = FieldWriteService(client, registry)

        with pytest.raises(TaskNotFoundError) as exc_info:
            await service.write_async(
                entity_type="offer",
                gid="0000000000",
                fields={"name": "Test"},
            )
        assert "0000000000" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_entity_type_mismatch_raises(self) -> None:
        """Task in wrong project raises EntityTypeMismatchError."""
        wrong_project_data = {
            **MOCK_TASK_DATA,
            "memberships": [
                {"project": {"gid": "WRONG_PROJECT_GID"}},
            ],
        }
        client = _make_mock_client(task_data=wrong_project_data)
        registry = _make_write_registry()
        service = FieldWriteService(client, registry)

        with pytest.raises(EntityTypeMismatchError) as exc_info:
            await service.write_async(
                entity_type="offer",
                gid="9999999999",
                fields={"name": "Test"},
            )
        assert exc_info.value.expected_project == PROJECT_GID
        assert "WRONG_PROJECT_GID" in exc_info.value.actual_projects

    @pytest.mark.asyncio
    async def test_core_and_custom_single_api_call(self) -> None:
        """Verifies one update_async call with both core kwargs and custom_fields dict."""
        client = _make_mock_client()
        registry = _make_write_registry()
        service = FieldWriteService(client, registry)

        await service.write_async(
            entity_type="offer",
            gid="9999999999",
            fields={"name": "New Name", "weekly_ad_spend": 750},
        )

        # Single API call
        client.tasks.update_async.assert_awaited_once()
        call_kwargs = client.tasks.update_async.call_args
        # Core field should be in top-level kwargs
        assert call_kwargs.kwargs.get("name") == "New Name"
        # Custom field should be in custom_fields dict keyed by GID
        assert "cf_111" in call_kwargs.kwargs.get("custom_fields", {})
        assert call_kwargs.kwargs["custom_fields"]["cf_111"] == 750

    @pytest.mark.asyncio
    async def test_mutation_event_emitted(self) -> None:
        """MutationEvent is created after successful write."""
        client = _make_mock_client()
        registry = _make_write_registry()
        service = FieldWriteService(client, registry)

        mock_invalidator = MagicMock()
        mock_invalidator.invalidate_async = AsyncMock()

        result = await service.write_async(
            entity_type="offer",
            gid="9999999999",
            fields={"name": "Updated"},
            mutation_invalidator=mock_invalidator,
        )

        # Allow the fire-and-forget task to run
        await asyncio.sleep(0.05)

        mock_invalidator.invalidate_async.assert_awaited_once()
        event = mock_invalidator.invalidate_async.call_args[0][0]
        assert event.entity_gid == "9999999999"
        assert event.mutation_type.value == "update"
        assert PROJECT_GID in event.project_gids
        assert result.fields_written == 1

    @pytest.mark.asyncio
    async def test_include_updated_refetch(self) -> None:
        """include_updated=True triggers a re-fetch and returns values."""
        # The second get_async call (re-fetch) returns updated data
        refetch_data = {
            **MOCK_TASK_DATA,
            "name": "Updated Offer Name",
        }
        client = _make_mock_client()
        # First call: initial fetch; second call: re-fetch
        client.tasks.get_async = AsyncMock(side_effect=[MOCK_TASK_DATA, refetch_data])
        registry = _make_write_registry()
        service = FieldWriteService(client, registry)

        result = await service.write_async(
            entity_type="offer",
            gid="9999999999",
            fields={"name": "Updated Offer Name"},
            include_updated=True,
        )

        assert result.updated_fields is not None
        assert result.updated_fields["name"] == "Updated Offer Name"
        # Two get_async calls: fetch + re-fetch
        assert client.tasks.get_async.await_count == 2

    @pytest.mark.asyncio
    async def test_asana_rate_limit_propagates(self) -> None:
        """Asana RateLimitError propagates to caller."""
        client = _make_mock_client(
            update_side_effect=RateLimitError(
                "Rate limited", status_code=429, retry_after=30
            )
        )
        registry = _make_write_registry()
        service = FieldWriteService(client, registry)

        with pytest.raises(RateLimitError) as exc_info:
            await service.write_async(
                entity_type="offer",
                gid="9999999999",
                fields={"name": "Test"},
            )
        assert exc_info.value.retry_after == 30

    @pytest.mark.asyncio
    async def test_multi_enum_all_unresolved_skips_field(self) -> None:
        """Multi-enum with all-unresolved options is skipped, not silently cleared.

        Per WS-4 hardening: when every multi-enum option name fails resolution,
        the field becomes skipped (not written). If form_questions is the ONLY
        field, this raises NoValidFieldsError.
        """
        # Task with multi-enum custom field
        task_data = {
            **MOCK_TASK_DATA,
            "custom_fields": [
                {
                    "gid": "cf_fq",
                    "name": "Form Questions",
                    "resource_subtype": "multi_enum",
                    "multi_enum_values": [],
                    "enum_options": [
                        {"gid": "opt_q1", "name": "First Name", "enabled": True},
                        {"gid": "opt_q2", "name": "Last Name", "enabled": True},
                        {"gid": "opt_q3", "name": "Email", "enabled": True},
                    ],
                },
            ],
        }
        client = _make_mock_client(task_data=task_data)
        write_info = WritableEntityInfo(
            entity_type="unit",
            model_class=type("FakeUnit", (), {}),
            project_gid=PROJECT_GID,
            descriptor_index={"form_questions": "Form Questions"},
            core_fields=CORE_FIELD_NAMES,
        )
        registry = MagicMock(spec=EntityWriteRegistry)
        registry.get.return_value = write_info
        service = FieldWriteService(client, registry)

        # All values are bogus -- should raise NoValidFieldsError
        with pytest.raises(NoValidFieldsError):
            await service.write_async(
                entity_type="unit",
                gid="9999999999",
                fields={"form_questions": ["Bogus Q1", "Bogus Q2"]},
            )

    @pytest.mark.asyncio
    async def test_multi_enum_partial_unresolved_writes_matched(self) -> None:
        """Multi-enum with some unresolved options writes matched values.

        Per WS-4: partial resolution writes only matched values
        (unresolved are dropped but the write proceeds).
        """
        task_data = {
            **MOCK_TASK_DATA,
            "custom_fields": [
                {
                    "gid": "cf_fq",
                    "name": "Form Questions",
                    "resource_subtype": "multi_enum",
                    "multi_enum_values": [],
                    "enum_options": [
                        {"gid": "opt_q1", "name": "First Name", "enabled": True},
                        {"gid": "opt_q2", "name": "Last Name", "enabled": True},
                    ],
                },
            ],
        }
        client = _make_mock_client(task_data=task_data)
        write_info = WritableEntityInfo(
            entity_type="unit",
            model_class=type("FakeUnit", (), {}),
            project_gid=PROJECT_GID,
            descriptor_index={"form_questions": "Form Questions"},
            core_fields=CORE_FIELD_NAMES,
        )
        registry = MagicMock(spec=EntityWriteRegistry)
        registry.get.return_value = write_info
        service = FieldWriteService(client, registry)

        result = await service.write_async(
            entity_type="unit",
            gid="9999999999",
            fields={"form_questions": ["First Name", "Bogus"]},
        )

        assert result.fields_written == 1
        # Verify the API call includes only the matched GID
        call_kwargs = client.tasks.update_async.call_args.kwargs
        assert call_kwargs["custom_fields"]["cf_fq"] == ["opt_q1"]
