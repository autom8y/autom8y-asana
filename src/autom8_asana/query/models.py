"""Pydantic v2 predicate models for the query engine.

Implements a discriminated union for PredicateNode (Comparison | AndGroup |
OrGroup | NotGroup) using a callable discriminator that inspects dict keys.

See ADR-QE-002 for the rationale behind this approach.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    field_validator,
    model_validator,
)

from autom8_asana.query.join import JoinSpec


class Op(StrEnum):
    """Supported comparison operators."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"


class Comparison(BaseModel):
    """Leaf predicate node: single field comparison."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(description="Column name to compare against.")
    op: Op = Field(description="Comparison operator to apply.")
    value: Any = Field(description="Value to compare the field against.")


class AndGroup(BaseModel):
    """AND group node: all children must match."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    and_: list[PredicateNode] = Field(
        alias="and", description="Child predicates that must all match."
    )


class OrGroup(BaseModel):
    """OR group node: at least one child must match."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    or_: list[PredicateNode] = Field(
        alias="or", description="Child predicates where at least one must match."
    )


class NotGroup(BaseModel):
    """NOT group node: child must not match."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    not_: PredicateNode = Field(
        alias="not", description="Child predicate that must not match."
    )


def _predicate_discriminator(v: Any) -> str:
    """Callable discriminator for PredicateNode union.

    Inspects the raw dict to determine which variant to parse.
    """
    if isinstance(v, dict):
        if "and" in v:
            return "and"
        if "or" in v:
            return "or"
        if "not" in v:
            return "not"
        if "field" in v:
            return "comparison"
    # Pydantic will raise a validation error for unrecognized shapes
    return "comparison"


def _wrap_flat_array_to_and_group(v: Any) -> Any:
    """Auto-wrap a bare list of predicates into an AND group.

    Provides FR-001 syntactic sugar: callers can pass a flat array of
    comparisons instead of an explicit ``{"and": [...]}`` wrapper.
    An empty array becomes None (no filter, per EC-005).
    """
    if isinstance(v, list):
        if len(v) == 0:
            return None
        return {"and": v}
    return v


PredicateNode = Annotated[
    Annotated[Comparison, Tag("comparison")]
    | Annotated[AndGroup, Tag("and")]
    | Annotated[OrGroup, Tag("or")]
    | Annotated[NotGroup, Tag("not")],
    Discriminator(_predicate_discriminator),
]

# Rebuild forward refs after PredicateNode is defined
AndGroup.model_rebuild()
OrGroup.model_rebuild()
NotGroup.model_rebuild()


class AggFunction(StrEnum):
    """Supported aggregation functions for /aggregate endpoint."""

    SUM = "sum"
    COUNT = "count"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    COUNT_DISTINCT = "count_distinct"


class AggSpec(BaseModel):
    """Single aggregation specification within an /aggregate request.

    Attributes:
        column: Column to aggregate (must exist in SchemaRegistry).
        agg: Aggregation function to apply.
        alias: Output column name. Defaults to "{agg}_{column}".
    """

    model_config = ConfigDict(extra="forbid")

    column: str = Field(
        description="Column to aggregate (must exist in SchemaRegistry)."
    )
    agg: AggFunction = Field(description="Aggregation function to apply.")
    alias: str | None = Field(
        default=None, description="Output column name. Defaults to '{agg}_{column}'."
    )

    @property
    def resolved_alias(self) -> str:
        """Return the alias, or generate default from agg + column."""
        if self.alias is not None:
            return self.alias
        return f"{self.agg.value}_{self.column}"


class AggregateRequest(BaseModel):
    """POST /v1/query/{entity_type}/aggregate request body."""

    model_config = ConfigDict(extra="forbid")

    where: PredicateNode | None = Field(
        default=None,
        description="Pre-aggregation filter predicate to narrow rows before grouping.",
    )
    section: str | None = Field(
        default=None,
        description="Section name to scope the aggregation to.",
    )
    group_by: list[str] = Field(
        min_length=1,
        max_length=5,
        description="Columns to group by (1-5 columns).",
    )
    aggregations: list[AggSpec] = Field(
        min_length=1,
        max_length=10,
        description="Aggregation specifications to compute per group (1-10).",
    )
    having: PredicateNode | None = Field(
        default=None,
        description="Post-aggregation filter predicate applied to grouped results.",
    )

    @field_validator("where", mode="before")
    @classmethod
    def wrap_flat_array(cls, v: Any) -> Any:
        """Auto-wrap bare list to AND group (reuse FR-001 sugar)."""
        return _wrap_flat_array_to_and_group(v)

    @field_validator("having", mode="before")
    @classmethod
    def wrap_having_flat_array(cls, v: Any) -> Any:
        """Auto-wrap bare list HAVING to AND group."""
        return _wrap_flat_array_to_and_group(v)


class AggregateMeta(BaseModel):
    """Response metadata for /aggregate endpoint."""

    model_config = ConfigDict(extra="forbid")

    group_count: int = Field(description="Number of groups in the result.")
    aggregation_count: int = Field(
        description="Number of aggregation columns computed."
    )
    group_by: list[str] = Field(description="Columns used for grouping.")
    entity_type: str = Field(description="Entity type that was aggregated.")
    project_gid: str = Field(description="Asana project GID the query ran against.")
    query_ms: float = Field(description="Query execution time in milliseconds.")
    # LKG freshness metadata
    freshness: str | None = Field(
        default=None,
        description="Cache freshness state (e.g., 'fresh', 'stale', 'lkg').",
    )
    data_age_seconds: float | None = Field(
        default=None,
        description="Age of the cached data in seconds since last refresh.",
    )
    staleness_ratio: float | None = Field(
        default=None,
        description="Ratio of data age to configured TTL (1.0 = at TTL boundary).",
    )


class AggregateResponse(BaseModel):
    """Response body for /aggregate endpoint."""

    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]] = Field(
        description="Aggregated result rows, one dict per group."
    )
    meta: AggregateMeta = Field(description="Query execution metadata.")


class RowsRequest(BaseModel):
    """POST /v1/query/{entity_type}/rows request body."""

    model_config = ConfigDict(extra="forbid")

    where: PredicateNode | None = Field(
        default=None,
        description="Filter predicate to narrow rows before returning.",
    )
    section: str | None = Field(
        default=None,
        description="Section name to scope the query to. Mutually exclusive with classification.",
    )
    classification: str | None = Field(
        default=None,
        description="Classification label to scope the query to. Mutually exclusive with section.",
    )
    select: list[str] | None = Field(
        default=None,
        description="Columns to return. Null returns all columns.",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of rows to return (1-1000).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of rows to skip for pagination.",
    )
    order_by: str | None = Field(
        default=None,
        description="Column name to sort results by.",
    )
    order_dir: Literal["asc", "desc"] = Field(
        default="asc",
        description="Sort direction: 'asc' for ascending, 'desc' for descending.",
    )
    join: JoinSpec | None = Field(
        default=None,
        description="Cross-entity join specification for enriching rows.",
    )

    @field_validator("where", mode="before")
    @classmethod
    def wrap_flat_array(cls, v: Any) -> Any:
        """Auto-wrap bare list to AND group (FR-001 sugar)."""
        return _wrap_flat_array_to_and_group(v)

    @model_validator(mode="after")
    def section_classification_exclusive(self) -> RowsRequest:
        """Ensure section and classification are mutually exclusive."""
        if self.section is not None and self.classification is not None:
            raise ValueError("section and classification are mutually exclusive")
        return self


class RowsMeta(BaseModel):
    """Response metadata for /rows endpoint."""

    model_config = ConfigDict(extra="forbid")

    total_count: int = Field(description="Total number of rows matching the filter.")
    returned_count: int = Field(description="Number of rows in this page of results.")
    limit: int = Field(description="Maximum rows requested per page.")
    offset: int = Field(description="Row offset used for this page.")
    entity_type: str = Field(description="Entity type that was queried.")
    project_gid: str = Field(description="Asana project GID the query ran against.")
    query_ms: float = Field(description="Query execution time in milliseconds.")
    join_entity: str | None = Field(
        default=None,
        description="Entity type that was joined, if a join was performed.",
    )
    join_key: str | None = Field(
        default=None,
        description="Column used as the join key.",
    )
    join_matched: int | None = Field(
        default=None,
        description="Number of rows that matched during the join.",
    )
    join_unmatched: int | None = Field(
        default=None,
        description="Number of rows that did not match during the join.",
    )
    # LKG freshness metadata
    freshness: str | None = Field(
        default=None,
        description="Cache freshness state (e.g., 'fresh', 'stale', 'lkg').",
    )
    data_age_seconds: float | None = Field(
        default=None,
        description="Age of the cached data in seconds since last refresh.",
    )
    staleness_ratio: float | None = Field(
        default=None,
        description="Ratio of data age to configured TTL (1.0 = at TTL boundary).",
    )


class RowsResponse(BaseModel):
    """Response body for /rows endpoint."""

    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]] = Field(description="Result rows, one dict per entity.")
    meta: RowsMeta = Field(description="Query execution and pagination metadata.")
