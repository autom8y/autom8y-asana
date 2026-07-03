"""Regression tests for opt_fields-blind TASK cache poisoning (instance #2: memberships).

Root cause (SPIKE-multi-membership-cache-poisoning): the TASK cache key is
opt_fields-blind (FR-CLIENT-002), so the field-shape of the FIRST fetch of a gid is
what every subsequent cache-hit reader receives. A narrow-first ``get_async`` that
omitted ``memberships.*`` cached a membership-less object; a later standard-fields
read then cache-hit that poisoned object and fed ``memberships=None`` to tier-1
detection -> ``entity-type-undetectable`` -> walkthrough ``anchor_unresolved``.

The cure feeds tier-1 detection through ``_MINIMUM_OPT_FIELDS`` (mirrors the
``parent.gid`` precedent that cured instance #1).

This module imports ONLY pre-existing symbols so the poison-repro runs verbatim
against pristine origin/main, where it FAILS (RED); it PASSES on the fix (GREEN).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.cache.models.entry import EntryType
from autom8_asana.clients.tasks import TasksClient
from autom8_asana.models import Task
from autom8_asana.models.business import STANDARD_TASK_OPT_FIELDS

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from autom8_asana.config import AsanaConfig

# Live PLAY gid + Calendar Integrations project from the spike receipts.
PLAY_GID = "1216252254927725"
CONTROL_GID = "1209442849265632"
CALENDAR_INTEGRATIONS_PROJECT_GID = "1209442849265632"
CALENDAR_INTEGRATIONS_PROJECT_NAME = "Calendar Integrations"


def _field_projecting_api(project_gid: str, project_name: str) -> Any:
    """Return a get() side_effect that faithfully models Asana field projection.

    Asana only returns ``memberships`` in a task payload when a ``memberships.*``
    opt_field is requested. Modelling this is what makes the poison-repro a genuine
    two-sided discriminating canary: the SAME mock is used on pre-fix and fix code;
    only the requested opt_fields (driven by the production code under test) differ.
    """

    def _get(path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        gid = path.rsplit("/", 1)[-1]
        opt = (params or {}).get("opt_fields", "")
        requested = set(opt.split(",")) if opt else set()
        data: dict[str, Any] = {
            "gid": gid,
            "resource_type": "task",
            "name": "PLAY: Custom Calendar Integration",
            "modified_at": "2026-07-03T10:19:45Z",
        }
        if any(field.startswith("memberships") for field in requested):
            data["memberships"] = [{"project": {"gid": project_gid, "name": project_name}}]
        return data

    return _get


def _make_client(
    mock_http: MagicMock,
    config: AsanaConfig,
    auth_provider: MagicMock,
    cache_provider: Any,
) -> TasksClient:
    return TasksClient(
        http=mock_http,
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
        client=None,
    )


class TestMembershipCachePoisoning:
    """Instance #2 of the narrow-cache-poisoning class (memberships)."""

    async def test_narrow_fetch_does_not_starve_later_wide_read_of_memberships(
        self,
        mock_http: MagicMock,
        config: AsanaConfig,
        auth_provider: MagicMock,
        cache_provider: Any,
    ) -> None:
        """POISON-REPRO (discriminating canary): narrow get then standard get of the
        SAME gid must return memberships.

        RED on pre-fix main: the narrow fetch omits ``memberships.*`` -> cached
        membership-less -> the standard read cache-hits the poisoned object ->
        ``memberships is None``.
        GREEN on the fix: ``_MINIMUM_OPT_FIELDS`` now carries the membership
        subfields, so the narrow fetch caches a membership-bearing object.
        """
        mock_http.get.side_effect = _field_projecting_api(
            CALENDAR_INTEGRATIONS_PROJECT_GID, CALENDAR_INTEGRATIONS_PROJECT_NAME
        )
        tasks = _make_client(mock_http, config, auth_provider, cache_provider)

        # No-defect control: a cold standard fetch DOES surface memberships, proving
        # the API mock faithfully projects fields when asked (the RED, when it fires,
        # is the narrow-first cache path -- not a mock rigged to withhold memberships).
        control = await tasks.get_async(CONTROL_GID, opt_fields=list(STANDARD_TASK_OPT_FIELDS))
        assert isinstance(control, Task)
        assert control.memberships is not None

        # Defect path: narrow-first fetch populates the opt_fields-blind cache...
        narrow = await tasks.get_async(PLAY_GID, opt_fields=["name", "custom_fields"])
        assert isinstance(narrow, Task)

        # ...then a standard-fields read of the SAME gid cache-hits it.
        wide = await tasks.get_async(PLAY_GID, opt_fields=list(STANDARD_TASK_OPT_FIELDS))

        assert wide.memberships is not None, (
            "membership cache poisoning (instance #2): narrow-first fetch starved the "
            "later standard read of memberships -> tier-1 entity-type-undetectable"
        )
        assert wide.memberships[0]["project"]["gid"] == CALENDAR_INTEGRATIONS_PROJECT_GID
        assert wide.memberships[0]["project"]["name"] == CALENDAR_INTEGRATIONS_PROJECT_NAME

    async def test_narrow_fetch_requests_memberships_from_api(
        self,
        mock_http: MagicMock,
        config: AsanaConfig,
        auth_provider: MagicMock,
        cache_provider: Any,
    ) -> None:
        """The cure mechanism, asserted at the wire: an explicitly-narrowed fetch
        merges the membership subfields into the opt_fields it sends to Asana.

        RED on pre-fix main (narrow request carries only name/custom_fields/parent.gid);
        GREEN on the fix.
        """
        mock_http.get.side_effect = _field_projecting_api(
            CALENDAR_INTEGRATIONS_PROJECT_GID, CALENDAR_INTEGRATIONS_PROJECT_NAME
        )
        tasks = _make_client(mock_http, config, auth_provider, cache_provider)

        await tasks.get_async(PLAY_GID, opt_fields=["name", "custom_fields"])

        sent = set(mock_http.get.call_args.kwargs["params"]["opt_fields"].split(","))
        assert "memberships.project.gid" in sent
        assert "memberships.project.name" in sent


class TestBareGetOptFieldsUnchanged:
    """Bare get_async(gid) (opt_fields=None) semantics are UNTOUCHED (R4)."""

    async def test_bare_get_async_sends_no_opt_fields_param(
        self,
        mock_http: MagicMock,
        config: AsanaConfig,
        auth_provider: MagicMock,
        cache_provider: Any,
    ) -> None:
        """opt_fields=None -> no opt_fields query param -> Asana returns its defaults.

        Passes on both pre-fix main and the fix; guards against a minimum-set widening
        leaking into the bare-None path.
        """
        mock_http.get.return_value = {
            "gid": PLAY_GID,
            "resource_type": "task",
            "name": "Bare Task",
            "modified_at": "2026-07-03T10:19:45Z",
        }
        tasks = _make_client(mock_http, config, auth_provider, cache_provider)

        await tasks.get_async(PLAY_GID)

        params = mock_http.get.call_args.kwargs["params"]
        assert "opt_fields" not in params

    async def test_cache_miss_records_task_entry(
        self,
        mock_http: MagicMock,
        config: AsanaConfig,
        auth_provider: MagicMock,
        cache_provider: Any,
    ) -> None:
        """Sanity: the fetched task is cached under EntryType.TASK (the poisoned key)."""
        mock_http.get.return_value = {
            "gid": PLAY_GID,
            "resource_type": "task",
            "name": "Bare Task",
            "modified_at": "2026-07-03T10:19:45Z",
        }
        tasks = _make_client(mock_http, config, auth_provider, cache_provider)

        await tasks.get_async(PLAY_GID)

        assert len(cache_provider.set_versioned_calls) == 1
        key, entry = cache_provider.set_versioned_calls[0]
        assert key == PLAY_GID
        assert entry.entry_type == EntryType.TASK
