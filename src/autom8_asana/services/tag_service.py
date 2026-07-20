"""Workspace tag read + name-resolution service.

Per WS-B1 (asana-mcp-postfelt-hardening, TAG-1): the composite write path
requires a ``tag_gid``, but humans and agents think in tag NAMES, and nothing
in the satellite could resolve a name to a GID -- the only tag-touching route
was the composite's own ``POST /api/v1/tasks/{gid}/tags`` leg, and the query
engine's ``tags`` field carries names without GIDs. This service is the
SATELLITE half of the fix: a read surface over workspace tags with an
exact-name filter that IS the name->GID resolution primitive.

The sidecar (WS-B2, downstream) calls this surface and caches; caching is NOT
this service's concern -- it is a thin, stateless passthrough.

Design notes (see HANDOFF-wsb1-s3-tags-surface-2026-07-20):
- Workspace tags are fetched via the same endpoint the SDK ``TagsClient`` uses
  (``/workspaces/{workspace_gid}/tags`` through ``client._http.get_paginated``),
  mirroring ``TaskService`` for cursor pagination and raw-dict envelope fidelity.
- ``name`` filtering is EXACT (byte-for-byte, case-sensitive) and is applied
  CLIENT-SIDE because the Asana tags-list endpoint has no server-side name
  filter. A name query scans ALL pages (a match may live on any page) and
  returns EVERY exact match -- Asana tag names are NOT unique, so surfacing all
  candidates (rather than the first) keeps the resolution honest for the caller.
- A name MISS returns an empty list under HTTP 200 (a filtered collection with
  zero matches is an empty collection, not a missing resource); the caller
  distinguishes miss via ``len(data) == 0``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.services.errors import ServiceNotConfiguredError

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)

# Opt-fields requested from the Asana tags-list endpoint. ``name`` is REQUIRED
# for the exact-name filter to function; ``color`` and ``permalink_url`` are
# included because they make the listing directly useful for resolution (the
# witness-day workaround scraped a tag's GID from its permalink URL -- TAG-1).
_TAG_OPT_FIELDS = "name,color,permalink_url"

# Hard cap on pages scanned during a name resolution to bound a pathological
# cursor loop. 100 pages * 100 tags/page = 10k tags, far above any real
# workspace tag count; reaching it signals an anomaly, logged and truncated.
_MAX_NAME_SCAN_PAGES = 100

# Asana caps a single page at 100 records.
_ASANA_PAGE_MAX = 100


@dataclass(frozen=True, slots=True)
class TagListResult:
    """Result of a workspace tag list/resolve operation.

    Attributes:
        data: Tag resources as raw dicts (gid, name, and requested opt_fields).
        has_more: Whether more pages exist. Always False for a name-filtered
            result (a name scan returns the complete match set, not a page).
        next_offset: Opaque pagination cursor for the next page, or None.
            Always None for a name-filtered result.
    """

    data: list[dict[str, Any]]
    has_more: bool
    next_offset: str | None


class TagService:
    """Read + name-resolution operations over workspace tags.

    Stateless. No per-request state, no cache -- the downstream sidecar owns
    caching. Instantiated per request via ``get_tag_service`` DI, mirroring
    the stateless ``DataFrameService`` factory pattern.
    """

    async def list_tags(
        self,
        client: AsanaClient,
        *,
        name: str | None = None,
        limit: int = _ASANA_PAGE_MAX,
        offset: str | None = None,
    ) -> TagListResult:
        """List workspace tags, or resolve an exact tag name to its GID(s).

        Two modes on one surface:

        - ``name`` provided (non-empty): the resolution primitive. Scans ALL
          workspace tag pages and returns every tag whose name matches ``name``
          EXACTLY (case-sensitive). Returns an empty list on a miss. Pagination
          does not apply -- the returned set is complete.
        - ``name`` omitted/empty: a paginated passthrough of the workspace's
          tags, one page per call, honoring ``limit`` and ``offset``.

        Args:
            client: Asana SDK client for API calls.
            name: Exact tag name to resolve. Empty/None means "no filter".
            limit: Maximum items per page for the unfiltered listing (1-100).
            offset: Pagination cursor from a previous unfiltered response.

        Returns:
            TagListResult with tag data and pagination info.

        Raises:
            ServiceNotConfiguredError: No default workspace GID is configured
                on the client (maps to HTTP 503).
        """
        workspace_gid = client.default_workspace_gid
        if not workspace_gid:
            raise ServiceNotConfiguredError(
                "Asana workspace GID is not configured; cannot list tags. "
                "Set ASANA_WORKSPACE_GID or provide workspace_gid to the client."
            )

        endpoint = f"/workspaces/{workspace_gid}/tags"

        # Empty-string name (e.g. `?name=`) is treated as "no filter" so the
        # surface never filters for a tag literally named "".
        if name:
            return await self._resolve_by_name(client, endpoint, name)

        params: dict[str, Any] = {
            "limit": min(limit, _ASANA_PAGE_MAX),
            "opt_fields": _TAG_OPT_FIELDS,
        }
        if offset:
            params["offset"] = offset

        data, next_offset = await client._http.get_paginated(endpoint, params=params)

        return TagListResult(
            data=data,
            has_more=next_offset is not None,
            next_offset=next_offset,
        )

    @staticmethod
    async def _resolve_by_name(
        client: AsanaClient,
        endpoint: str,
        name: str,
    ) -> TagListResult:
        """Scan all workspace tag pages for exact-name matches.

        Asana provides no server-side name filter on the tags-list endpoint, so
        the match is applied client-side across every page. All exact matches
        are returned (Asana tag names are not unique).
        """
        matches: list[dict[str, Any]] = []
        offset: str | None = None
        pages = 0

        while True:
            params: dict[str, Any] = {
                "limit": _ASANA_PAGE_MAX,
                "opt_fields": _TAG_OPT_FIELDS,
            }
            if offset:
                params["offset"] = offset

            page, next_offset = await client._http.get_paginated(endpoint, params=params)
            matches.extend(tag for tag in page if tag.get("name") == name)

            pages += 1
            if not next_offset:
                break
            if pages >= _MAX_NAME_SCAN_PAGES:
                logger.warning(
                    "tag_name_scan_page_cap_reached",
                    extra={"pages": pages, "name_query": name, "matches": len(matches)},
                )
                break
            offset = next_offset

        return TagListResult(data=matches, has_more=False, next_offset=None)


__all__ = ["TagService", "TagListResult"]
