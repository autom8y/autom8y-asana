"""Shared fixtures for GFR resolver tests.

Mocks at the substrate boundary: ``hydrate_from_gid_async`` (the entry fetch) and
``QueryEngine.execute_rows`` (the field read). GFR consumes these as a client, so
the tests drive them via mocks rather than building live frames — keeping the
unit tests fast and the build-on-top boundary clean (no frozen-range exercise).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models.business.business import Business
from autom8_asana.models.business.hydration import HydrationResult
from autom8_asana.query.models import RowsMeta, RowsResponse

if TYPE_CHECKING:
    from autom8_asana.core.types import EntityType

# Anchors used across the suite. The Business project gid is the real
# multi-tenant project (entity_registry.py:445) so the gid-exact read targets
# the correct frame.
BUSINESS_PROJECT_GID = "1200653012566782"


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock AsanaClient with an async task getter."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.get_async = AsyncMock()
    return client


def make_hydration_result(
    *,
    business_gid: str,
    entry_type: EntityType,
    path_len: int = 0,
) -> HydrationResult:
    """Build a HydrationResult anchoring ``business_gid`` for an entry type.

    ``path`` carries ``path_len`` placeholder entities so EntryAnchor.path_len
    reflects the parent-chain depth (offer => 3 per the hydration docstring).
    """
    business = Business(gid=business_gid, name="Anchored Business", resource_type="task")
    path: list[Any] = [
        Business(gid=f"path-{i}", name=f"Path {i}", resource_type="task") for i in range(path_len)
    ]
    return HydrationResult(
        business=business,
        entry_entity=None,
        entry_type=entry_type,
        path=path,
        api_calls=1 + path_len,
    )


def make_rows_response(
    *,
    rows: list[dict[str, Any]],
    entity_type: str = "business",
    project_gid: str = BUSINESS_PROJECT_GID,
    stale_served: bool = False,
    freshness: str | None = "fresh",
) -> RowsResponse:
    """Build a RowsResponse with the given rows and freshness side-channel."""
    meta = RowsMeta(
        total_count=len(rows),
        returned_count=len(rows),
        limit=100,
        offset=0,
        entity_type=entity_type,
        project_gid=project_gid,
        query_ms=1.0,
        freshness=freshness,
        stale_served=stale_served,
    )
    return RowsResponse(data=rows, meta=meta)


@pytest.fixture
def utc_now() -> datetime:
    return datetime.now(UTC)


class FakeByGuidVerifier:
    """In-memory ByGuidVerifier for tier-2 tests.

    Maps guid -> record. ``get_business_by_guid_async`` returns the record (with
    a matching ``.guid``) on hit, None on miss — the 200+data=null envelope shape.
    Counts calls so tests can assert the office_phone join is NOT used for identity.
    """

    def __init__(self, records: dict[str, Any] | None = None) -> None:
        self._records = records or {}
        self.calls: list[str] = []

    async def get_business_by_guid_async(self, guid: str) -> Any | None:
        self.calls.append(guid)
        return self._records.get(guid)


def make_record(guid: str) -> MagicMock:
    """A minimal authoritative record exposing ``.guid``."""
    rec = MagicMock()
    rec.guid = guid
    return rec
