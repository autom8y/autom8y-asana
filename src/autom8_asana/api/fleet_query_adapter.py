"""FleetQuery -> EntityQueryService adapter (S3 D4).

Translates a fleet-canonical :class:`autom8y_api_schemas.FleetQuery`
into the kwargs accepted by
:meth:`autom8_asana.services.query_service.EntityQueryService.query`,
and constructs the response-side :class:`PaginationMeta` so the
request's pagination inputs round-trip into the response envelope.

Design notes (S3 TDD section 7.4.3):
- Adapter only — does NOT modify QueryEngine, EntityQueryService, or any
  existing route handler. The legacy POST /v1/query/{entity_type}
  endpoint and the /v1/query/{entity_type}/rows + aggregate handlers
  are untouched and remain functional.
- ``FleetQuery.filters`` is a permissive ``dict[str, Any]``. The asana
  adapter requires the caller to provide ``entity_type`` and
  optionally ``select`` inside the filters dict; all remaining keys
  forward to the legacy ``where`` filter shape verbatim.
- ``FleetQuery.limit`` -> ``EntityQueryService.query(limit=...)`` 1:1.
- ``FleetQuery.offset`` -> ``EntityQueryService.query(offset=...)`` 1:1
  (asana's legacy POST endpoint already supports limit + offset; the
  fleet shape maps cleanly).
- ``PaginationMeta`` is built from the request limit/offset paired
  with the post-execution ``total_count`` from the QueryResult — that
  is the §7.3 pagination round-trip invariant.

This module is the D4 fleet-side seam for asana. It is opt-in: legacy
callers continue to use the existing routes and never touch this file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_api_schemas import FleetQuery, PaginationMeta

if TYPE_CHECKING:
    from autom8_asana.services.query_service import QueryResult

__all__ = [
    "AdapterValidationError",
    "FleetQueryDispatchKwargs",
    "build_pagination_meta",
    "fleet_query_to_dispatch_kwargs",
]


class AdapterValidationError(ValueError):
    """Raised when a FleetQuery cannot be translated for the asana engine.

    Surfaces a developer-facing message naming the missing or invalid
    field. Route handlers convert this into a 400 BAD REQUEST.
    """


class FleetQueryDispatchKwargs:
    """Typed container for the kwargs the asana adapter forwards.

    Attributes:
        entity_type: Required entity type (e.g., "offer", "unit").
        where: Filter dict in the asana legacy ``where`` shape.
        select: Optional list of fields to include in results.
        limit: Maximum rows to return.
        offset: Number of rows to skip.
    """

    __slots__ = ("entity_type", "where", "select", "limit", "offset")

    def __init__(
        self,
        *,
        entity_type: str,
        where: dict[str, Any],
        select: list[str] | None,
        limit: int,
        offset: int,
    ) -> None:
        self.entity_type = entity_type
        self.where = where
        self.select = select
        self.limit = limit
        self.offset = offset


# Filter keys that the adapter recognises as control fields and lifts
# OUT of the ``where`` dict. Anything not in this set is a residual
# ``where`` predicate.
_CONTROL_KEYS: frozenset[str] = frozenset({"entity_type", "select"})


def fleet_query_to_dispatch_kwargs(query: FleetQuery) -> FleetQueryDispatchKwargs:
    """Translate a FleetQuery into asana EntityQueryService.query kwargs.

    The adapter requires ``entity_type`` to be present inside
    ``query.filters`` since FleetQuery is a transport-neutral shape and
    asana's query engine is entity-typed. Optional ``select`` may also
    be supplied via ``query.filters``.

    Args:
        query: The fleet-canonical query input.

    Returns:
        A typed dispatch container suitable for hand-off to
        ``EntityQueryService.query(**kwargs)``.

    Raises:
        AdapterValidationError: If ``entity_type`` is missing or invalid.

    Example:
        >>> from autom8y_api_schemas import FleetQuery
        >>> q = FleetQuery(
        ...     limit=10,
        ...     offset=20,
        ...     filters={
        ...         "entity_type": "offer",
        ...         "select": ["gid", "name", "vertical"],
        ...         "vertical": "chiro",
        ...         "status": "active",
        ...     },
        ... )
        >>> kw = fleet_query_to_dispatch_kwargs(q)
        >>> kw.entity_type
        'offer'
        >>> kw.where
        {'vertical': 'chiro', 'status': 'active'}
        >>> kw.limit, kw.offset
        (10, 20)
    """
    raw_entity_type = query.filters.get("entity_type")
    if raw_entity_type is None:
        raise AdapterValidationError(
            "FleetQuery.filters must include 'entity_type' for asana dispatch"
        )
    if not isinstance(raw_entity_type, str) or not raw_entity_type.strip():
        raise AdapterValidationError(
            "FleetQuery.filters['entity_type'] must be a non-empty string"
        )

    raw_select = query.filters.get("select")
    select: list[str] | None
    if raw_select is None:
        select = None
    elif isinstance(raw_select, list) and all(isinstance(s, str) for s in raw_select):
        select = list(raw_select)
    else:
        raise AdapterValidationError(
            "FleetQuery.filters['select'] must be a list of strings when provided"
        )

    where: dict[str, Any] = {
        key: value for key, value in query.filters.items() if key not in _CONTROL_KEYS
    }

    return FleetQueryDispatchKwargs(
        entity_type=raw_entity_type,
        where=where,
        select=select,
        limit=query.limit,
        offset=query.offset,
    )


def build_pagination_meta(
    query: FleetQuery,
    *,
    total_count: int,
) -> PaginationMeta:
    """Build a response-side PaginationMeta from a FleetQuery + total_count.

    Implements the section 7.3 pagination coupling invariant: the
    request's ``limit``/``offset`` round-trip into the response envelope
    paired with the engine-reported total row count.

    Args:
        query: The originating fleet query.
        total_count: Total matching rows from the asana QueryResult
            (BEFORE pagination is applied).

    Returns:
        A PaginationMeta with ``limit`` mirroring the request,
        ``next_offset`` set to ``offset:{N}`` when more pages exist,
        and ``total_count`` echoed through.
    """
    next_offset_int = query.offset + query.limit
    has_more = next_offset_int < total_count
    next_offset_str: str | None = f"offset:{next_offset_int}" if has_more else None
    return PaginationMeta(
        limit=query.limit,
        has_more=has_more,
        next_offset=next_offset_str,
        total_count=total_count,
    )


def pagination_meta_from_query_result(
    query: FleetQuery,
    result: QueryResult,
) -> PaginationMeta:
    """Convenience: build PaginationMeta directly from an asana QueryResult.

    The asana QueryResult exposes ``total_count`` as the row count BEFORE
    pagination, which is exactly what PaginationMeta needs.

    Args:
        query: The originating fleet query.
        result: An asana QueryResult returned from EntityQueryService.

    Returns:
        A PaginationMeta with the §7.3 round-trip invariant honoured.
    """
    return build_pagination_meta(query, total_count=result.total_count)
