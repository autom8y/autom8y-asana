"""Tests for TASK-cache union hydration (FG-BUG fix + QA #212 regression close).

Per HANDOFF-thermia-to-10xdev-taskcache-fix-2026-07-07 (corrected under QA #212
NO-GO): the opt_fields-blind TASK cache silently narrowed a gid to the FIRST
fetch's field-shape. A targeted get_async(gid, ["name", ...]) cached a
custom_fields-less task under the blind cache key; a later custom_fields read
then got that narrow cache hit and saw custom_fields as absent (None/[]).

The fix hydrates every cache MISS with a TRUE SUPERSET of BOTH the caller's
projection AND STANDARD_TASK_OPT_FIELDS (caller-projection UNION STANDARD), so a
stored entry satisfies ANY later projection of the same gid AND does not drop the
caller's own fields. STANDARD alone is NOT a superset of every caller's request --
it drops modified_at/due_on/completed/tags/etc. that BASE_OPT_FIELDS
(freshness/hierarchy_warmer/progressive watermarks) and field_write callers need;
fetching STANDARD alone regressed those callers to None (the #212 NO-GO).

These tests exercise the REAL TasksClient + its real in-process cache (the
MockCacheProvider persists across calls). Only the HTTP transport is mocked --
the fakes-only unit tests are what HID this class, so these assert call count +
params against the actual cache behavior. The C2 regression tests use an
opt_fields-HONORING HTTP mock (returns only requested fields) so a
STANDARD-drops-modified_at regression surfaces instead of being hidden by a
complete-dict stub.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from autom8_asana.cache.models.entry import EntryType
from autom8_asana.clients.tasks import TasksClient
from autom8_asana.dataframes.builders.fields import BASE_OPT_FIELDS
from autom8_asana.models.business import STANDARD_TASK_OPT_FIELDS

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from tests.unit.clients.conftest import MockCacheProvider

    from autom8_asana.config import AsanaConfig


# Valid GID for testing (Asana GIDs are numeric strings)
TASK_GID = "1234567890123"


@pytest.fixture
def tasks_client(
    mock_http: MagicMock,
    config: AsanaConfig,
    auth_provider: MagicMock,
    cache_provider: MockCacheProvider,
) -> TasksClient:
    """Create TasksClient with a REAL (in-process) cache and mocked HTTP."""
    return TasksClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
        client=None,
    )


def _requested_opt_fields(call: Any) -> set[str]:
    """Extract the opt_fields set from a mock_http.get call.

    _build_opt_fields sends params={"opt_fields": "a,b,c"} (comma-joined).
    """
    params = call.kwargs.get("params", {})
    raw = params.get("opt_fields", "")
    return set(raw.split(",")) if raw else set()


def _superset_task_response(gid: str = TASK_GID) -> dict[str, Any]:
    """A full-fields Asana task response (what the superset fetch returns).

    Models the real Asana projection: because the MISS now requests the full
    STANDARD_TASK_OPT_FIELDS, the response carries custom_fields with a real
    display_value -- the exact field the FG-BUG lost.
    """
    return {
        "gid": gid,
        "resource_type": "task",
        "name": "Wholebody Unit",
        "modified_at": "2025-01-01T12:00:00Z",
        "parent": None,
        "memberships": [
            {"project": {"gid": "9990001112223", "name": "Units"}},
        ],
        "custom_fields": [
            {
                "gid": "ph1",
                "name": "Office Phone",
                "display_value": "+15551234567",
            },
        ],
    }


class TestSupersetHydration:
    """Option-B superset hydration: the FG-BUG repro + edge case."""

    async def test_task_cache_superset_hydration_narrow_then_wide(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MagicMock,
    ) -> None:
        """FG-BUG repro: a narrow-first get must hydrate the SUPERSET, so a later
        wide (custom_fields) get of the SAME gid is a cache HIT carrying the real
        custom_fields value -- never a silently-narrowed task.

        RED before the fix: the narrow miss cached only name+memberships, so the
        second (wide) get either issued a 2nd HTTP call OR read custom_fields as
        absent. GREEN after: 1 HTTP call carrying the full STANDARD_TASK_OPT_FIELDS,
        and the 2nd get hits the cache with a populated custom_fields.
        """
        # Arrange: even a NARROW caller projection returns the superset from Asana,
        # because the miss path now requests the full STANDARD_TASK_OPT_FIELDS.
        mock_http.get.return_value = _superset_task_response(TASK_GID)

        # Act 1: narrow-first read (name + memberships only).
        first = await tasks_client.get_async(
            TASK_GID, opt_fields=["name", "memberships.project.gid"]
        )

        # Assert: exactly one HTTP call carrying a TRUE superset of BOTH the caller's
        # projection AND STANDARD (the union). STANDARD subset => custom_fields.* is
        # present (FG-BUG closed); caller subset => the caller's fields are not dropped.
        mock_http.get.assert_called_once()
        requested = _requested_opt_fields(mock_http.get.call_args)
        assert set(STANDARD_TASK_OPT_FIELDS).issubset(requested), (
            "miss-path fetch must include the full STANDARD_TASK_OPT_FIELDS set; "
            f"got {sorted(requested)}"
        )
        assert {"name", "memberships.project.gid"}.issubset(requested), (
            "miss-path fetch must also include the CALLER's projection (union, not "
            f"STANDARD-alone); got {sorted(requested)}"
        )
        assert first.gid == TASK_GID

        # The cache stored the superset entry under the opt_fields-blind key.
        assert len(cache_provider.set_versioned_calls) == 1
        _, stored = cache_provider.set_versioned_calls[0]
        assert "custom_fields" in stored.data

        # Act 2: wide read (custom_fields) of the SAME gid.
        second = await tasks_client.get_async(
            TASK_GID,
            opt_fields=["custom_fields.name", "custom_fields.display_value"],
        )

        # Assert: NO second HTTP call -- the wide read was served from cache.
        mock_http.get.assert_called_once()

        # Assert: the cached task carries the REAL custom_fields value (not None/[]).
        # Task.custom_fields is list[dict] (raw Asana shape), mirroring how the
        # hydration consumer reads display_value off the cached entry.
        assert second.custom_fields, "custom_fields must be present on the cache hit"
        assert second.custom_fields[0]["display_value"] == "+15551234567"

    async def test_task_cache_zero_custom_fields_correct_behavior(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MagicMock,
    ) -> None:
        """Edge case: a task whose HTTP response has custom_fields: [] must STILL
        have been fetched with the full STANDARD_TASK_OPT_FIELDS.

        This is the structural proof that distinguishes "not fetched" (opt_fields-blind
        poisoning) from "fetched-and-empty" (a task that genuinely has no custom
        fields). Under Option B the request always carries the superset; the empty
        list is a truthful answer, not a starved cache.
        """
        # Arrange: response with an EMPTY custom_fields list.
        response = _superset_task_response(TASK_GID)
        response["custom_fields"] = []
        mock_http.get.return_value = response

        # Act: a narrow caller projection still triggers a superset fetch.
        await tasks_client.get_async(TASK_GID, opt_fields=["name"])

        # Assert: exactly one HTTP call, carrying the full superset.
        mock_http.get.assert_called_once()
        requested = _requested_opt_fields(mock_http.get.call_args)
        assert set(STANDARD_TASK_OPT_FIELDS).issubset(requested), (
            "even for a task with zero custom_fields, the fetch must carry the "
            f"full STANDARD_TASK_OPT_FIELDS superset; got {sorted(requested)}"
        )

        # The stored entry carries custom_fields as an explicit empty list --
        # "fetched-and-empty", not "not fetched".
        assert len(cache_provider.set_versioned_calls) == 1
        _, stored = cache_provider.set_versioned_calls[0]
        assert stored.data["custom_fields"] == []


class TestUnionHydrationDoesNotDropCallerFields:
    """C2 regression close (QA #212): the miss fetch must be a TRUE superset of the
    CALLER's projection, not STANDARD alone. STANDARD drops modified_at/due_on/
    completed/tags/etc.; a STANDARD-only fetch regresses BASE_OPT_FIELDS and
    field_write callers to None on a guaranteed-miss refetch.

    These use an opt_fields-HONORING HTTP mock (returns only the requested fields),
    modelling real Asana projection -- so a STANDARD-only regression surfaces as a
    missing field instead of being hidden by a complete-dict stub.
    """

    async def test_base_opt_fields_miss_returns_modified_at(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MagicMock,
    ) -> None:
        """A BASE_OPT_FIELDS-projection miss must return modified_at populated.

        modified_at is in BASE_OPT_FIELDS but NOT in STANDARD_TASK_OPT_FIELDS. Under
        the correct union hydration the fetch carries modified_at, so the watermark
        readers (freshness/hierarchy_warmer/progressive) get a real value.

        RED on the STANDARD-only HEAD: the fetch omitted modified_at -> the honoring
        mock returns it as absent -> modified_at is None (watermark corruption).
        GREEN after: modified_at is populated.
        """
        assert "modified_at" in set(BASE_OPT_FIELDS)
        assert "modified_at" not in set(STANDARD_TASK_OPT_FIELDS)

        real_modified_at = "2026-07-07T18:30:00.000Z"

        def _honor_opt_fields(path: str, params: dict[str, Any]) -> dict[str, Any]:
            """Return ONLY the requested fields (models Asana opt_fields projection)."""
            requested = (
                set(params.get("opt_fields", "").split(",")) if params.get("opt_fields") else set()
            )
            full = {
                "gid": TASK_GID,
                "resource_type": "task",
                "name": "Watermark Task",
                "modified_at": real_modified_at,
                "tags": [{"gid": "t1", "name": "hot"}],
                "custom_fields": [],
                "memberships": [{"project": {"gid": "9990001112223", "name": "Units"}}],
            }
            # Always echo gid + resource_type (Asana returns these unconditionally);
            # every OTHER field is only present if it was requested.
            projected: dict[str, Any] = {"gid": full["gid"], "resource_type": full["resource_type"]}
            for field, value in full.items():
                top = field.split(".")[0]
                if top in requested:
                    projected[field] = value
            return projected

        mock_http.get.side_effect = _honor_opt_fields

        result = await tasks_client.get_async(TASK_GID, raw=True, opt_fields=list(BASE_OPT_FIELDS))

        # The caller's BASE projection field is present and populated (not None).
        assert result.get("modified_at") == real_modified_at, (
            "union hydration must carry the caller's modified_at; STANDARD-only drops it "
            "and corrupts the watermark"
        )
        # And FG-BUG stays closed: custom_fields was fetched (STANDARD subset of union).
        requested = _requested_opt_fields(mock_http.get.call_args)
        assert "custom_fields" in requested


class TestListSubtasksDoNotPoisonTaskCache:
    """Regression guard (Test-3): list_async / subtasks_async results must NOT be
    written to the opt_fields-blind TASK cache. They never _cache_set today (so no
    latent class -- thermal-monitor Finding 2), and this guard fails loudly if a
    future refactor reintroduces the class."""

    async def test_list_async_results_not_written_to_task_cache(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MagicMock,
    ) -> None:
        """list_async pages must not populate the TASK cache."""
        page = [
            _superset_task_response("111"),
            _superset_task_response("222"),
        ]
        mock_http.get_paginated.return_value = (page, None)

        results = await tasks_client.list_async(project="proj1").collect()

        assert len(results) == 2
        # No TASK cache writes occurred from the list path.
        assert cache_provider.set_versioned_calls == []

    async def test_subtasks_async_results_not_written_to_task_cache(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        mock_http: MagicMock,
    ) -> None:
        """subtasks_async pages must not populate the TASK cache."""
        page = [
            _superset_task_response("333"),
            _superset_task_response("444"),
        ]
        mock_http.get_paginated.return_value = (page, None)

        results = await tasks_client.subtasks_async("parent_gid").collect()

        assert len(results) == 2
        assert cache_provider.set_versioned_calls == []
