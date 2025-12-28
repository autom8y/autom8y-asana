"""Search interface models.

Per TDD-search-interface: Pydantic models for search criteria and results.

Models:
    - FieldCondition: Single field condition for search
    - SearchCriteria: Query specification for search operations
    - SearchHit: Single search result with matched fields
    - SearchResult: Aggregated search results with metadata
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FieldCondition(BaseModel):
    """Single field condition for search.

    Supports equality matching, contains (substring), and IN operations.

    Attributes:
        field: Field name to match (e.g., "Office Phone", "Vertical").
        value: Single value or list of values for OR matching.
        operator: Match operator - "eq" (equality), "contains" (substring),
                  or "in" (value in list).

    Example:
        >>> condition = FieldCondition(field="Vertical", value="Medical")
        >>> condition = FieldCondition(
        ...     field="Status",
        ...     value=["Active", "Pending"],
        ...     operator="in"
        ... )
    """

    field: str
    value: str | list[str]
    operator: Literal["eq", "contains", "in"] = "eq"


class SearchCriteria(BaseModel):
    """Query specification for search operations.

    Defines the search parameters including field conditions, combinator
    logic (AND/OR), project scope, and optional filters.

    Attributes:
        conditions: List of field conditions to match.
        combinator: How to combine conditions - "AND" (all match) or "OR" (any match).
        project_gid: Required project GID - search within specific project.
        entity_type: Optional entity type filter (e.g., "Offer", "Unit").
        limit: Optional maximum results to return.

    Example:
        >>> criteria = SearchCriteria(
        ...     conditions=[
        ...         FieldCondition(field="Vertical", value="Medical"),
        ...         FieldCondition(field="Status", value="Active"),
        ...     ],
        ...     combinator="AND",
        ...     project_gid="1143843662099250",
        ... )
    """

    conditions: list[FieldCondition] = Field(default_factory=list)
    combinator: Literal["AND", "OR"] = "AND"
    project_gid: str
    entity_type: str | None = None
    limit: int | None = None


class SearchHit(BaseModel):
    """Single search result.

    Represents a single matched entity with its GID, type, name,
    and the field values that matched the search criteria.

    Attributes:
        gid: Task/entity GID.
        entity_type: Entity type if detected (e.g., "Offer", "Unit").
        name: Entity name if available.
        matched_fields: Dict of field names to matched values.

    Example:
        >>> hit = SearchHit(
        ...     gid="123456789",
        ...     entity_type="Offer",
        ...     name="Medical Clinic Offer",
        ...     matched_fields={"Vertical": "Medical", "Status": "Active"},
        ... )
    """

    gid: str
    entity_type: str | None = None
    name: str | None = None
    matched_fields: dict[str, str] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Aggregated search results.

    Contains the list of matched entities along with metadata about
    the query execution.

    Attributes:
        hits: List of SearchHit objects matching the criteria.
        total_count: Total number of matches found.
        query_time_ms: Query execution time in milliseconds.
        from_cache: Whether results came from cached DataFrame.

    Example:
        >>> result = SearchResult(
        ...     hits=[SearchHit(gid="123", name="Test")],
        ...     total_count=1,
        ...     query_time_ms=0.5,
        ...     from_cache=True,
        ... )
        >>> for hit in result.hits:
        ...     print(hit.gid)
    """

    hits: list[SearchHit] = Field(default_factory=list)
    total_count: int = 0
    query_time_ms: float = 0.0
    from_cache: bool = False
