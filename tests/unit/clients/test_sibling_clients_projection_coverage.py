"""PHE coverage for the sibling entity clients (TDD SS3 row 15, ADR fork d).

Projects / sections / users / custom_fields share the exact opt_fields-blind
hit-serve pattern the TASK flagship cured. Each gets the mechanical 3-line
graft: ``_cache_get_covering`` on the hit path; re-hydration union =
requested UNION stored (no STANDARD analogue); projection stamp at write.

Per client, the minimal 2-sided pair: narrow-write-then-wide-read WIDENS
(one extra fetch carrying the union -- RED pre-fix as a starved serve), and
a covered read HITs with zero extra fetches (teeth). Plus the default-path
pin: plain ``get(gid)`` reads (no declared projection) keep serving from
cache exactly as before.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.unit.clients.conftest import MockCacheProvider

from autom8_asana.clients.custom_fields import CustomFieldsClient
from autom8_asana.clients.projects import ProjectsClient
from autom8_asana.clients.sections import SectionsClient
from autom8_asana.clients.users import UsersClient

GID = "1234567890123"


class EchoEntityTransport:
    """Echoes the requested opt_fields for any entity endpoint.

    ``gid``/``resource_type`` always present (Asana returns them
    unconditionally); every other known field present iff requested; when
    NO opt_fields are sent, returns the default compact shape.
    """

    _FULL: dict[str, Any] = {
        "name": "Entity Name",
        "notes": "entity notes",
        "color": "light-green",
        "email": "user@example.com",
        "resource_subtype": "text",
        "created_at": "2026-07-08T12:00:00.000Z",
    }

    def __init__(self, resource_type: str) -> None:
        self.resource_type = resource_type
        self.calls: list[tuple[str, set[str]]] = []

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        raw = params.get("opt_fields", "")
        requested = set(raw.split(",")) if raw else set()
        self.calls.append((path, requested))
        gid = path.rsplit("/", 1)[-1]
        data: dict[str, Any] = {"gid": gid, "resource_type": self.resource_type}
        if not requested:
            # Default compact shape (no projection declared).
            data["name"] = self._FULL["name"]
            return data
        for fld, value in self._FULL.items():
            if fld in requested:
                data[fld] = value
        return data


CLIENT_MATRIX = [
    pytest.param(ProjectsClient, "project", "projects", id="projects"),
    pytest.param(SectionsClient, "section", "sections", id="sections"),
    pytest.param(UsersClient, "user", "users", id="users"),
    pytest.param(CustomFieldsClient, "custom_field", "custom_fields", id="custom_fields"),
]


def _make(client_cls: type, resource_type: str, config: Any, auth_provider: Any) -> tuple[Any, Any]:
    transport = EchoEntityTransport(resource_type)
    client = client_cls(
        http=transport,
        config=config,
        auth_provider=auth_provider,
        cache_provider=MockCacheProvider(),
    )
    return client, transport


@pytest.mark.parametrize(("client_cls", "resource_type", "_path"), CLIENT_MATRIX)
class TestSiblingClientCoverage:
    async def test_narrow_then_wide_read_widens_with_union(
        self,
        client_cls: type,
        resource_type: str,
        _path: str,
        config: Any,
        auth_provider: Any,
    ) -> None:
        """2-sided arm 1: a wide read after a narrow write coverage-misses and
        re-fetches the UNION (requested + stored). RED pre-fix: the wide read
        was served the narrow entry (one call, starved fields)."""
        client, transport = _make(client_cls, resource_type, config, auth_provider)

        narrow = await client.get_async(GID, raw=True, opt_fields=["name"])
        assert len(transport.calls) == 1
        assert narrow["name"] == "Entity Name"

        wide = await client.get_async(GID, raw=True, opt_fields=["name", "created_at"])

        assert len(transport.calls) == 2, (
            f"{client_cls.__name__}: uncovered read must re-fetch, not serve narrowed"
        )
        assert transport.calls[1][1] == {"name", "created_at"}, "union = requested | stored"
        assert wide["created_at"] == "2026-07-08T12:00:00.000Z"

    async def test_covered_read_hits_with_zero_extra_fetches(
        self,
        client_cls: type,
        resource_type: str,
        _path: str,
        config: Any,
        auth_provider: Any,
    ) -> None:
        """2-sided arm 2 (teeth): requested within the stored projection =>
        HIT, zero extra HTTP; disjoint pairs converge in ONE widening."""
        client, transport = _make(client_cls, resource_type, config, auth_provider)

        await client.get_async(GID, raw=True, opt_fields=["name", "created_at"])
        await client.get_async(GID, raw=True, opt_fields=["created_at"])
        assert len(transport.calls) == 1, (
            f"{client_cls.__name__}: covered read must serve with zero extra fetches"
        )

        # Ping-pong bound: alternate two disjoint projections; the widened
        # union covers both after ONE widening fetch.
        for _ in range(5):
            await client.get_async(GID, raw=True, opt_fields=["name"])
            await client.get_async(GID, raw=True, opt_fields=["notes"])
        assert len(transport.calls) == 2, (
            f"{client_cls.__name__}: union-monotone convergence violated"
        )

    async def test_default_projection_reads_keep_serving(
        self,
        client_cls: type,
        resource_type: str,
        _path: str,
        config: Any,
        auth_provider: Any,
    ) -> None:
        """The empty request declares no demand: plain get(gid) then get(gid)
        stays ONE fetch (no permanent re-fetch regression on the default path),
        and a default read is served by any live entry."""
        client, transport = _make(client_cls, resource_type, config, auth_provider)

        await client.get_async(GID, raw=True)
        await client.get_async(GID, raw=True)
        assert len(transport.calls) == 1

        # A projection-stamped entry also serves the empty request.
        client2, transport2 = _make(client_cls, resource_type, config, auth_provider)
        await client2.get_async(GID, raw=True, opt_fields=["name"])
        served = await client2.get_async(GID, raw=True)
        assert len(transport2.calls) == 1
        assert served["name"] == "Entity Name"
