"""Pydantic v2 predicate models for the query engine.

Implements a discriminated union for PredicateNode (Comparison | AndGroup |
OrGroup | NotGroup) using a callable discriminator that inspects dict keys.

See ADR-QE-002 for the rationale behind this approach.
"""

from __future__ import annotations

from enum import Enum
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


class Op(str, Enum):
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

    field: str
    op: Op
    value: Any


class AndGroup(BaseModel):
    """AND group node: all children must match."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    and_: list[PredicateNode] = Field(alias="and")


class OrGroup(BaseModel):
    """OR group node: at least one child must match."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    or_: list[PredicateNode] = Field(alias="or")


class NotGroup(BaseModel):
    """NOT group node: child must not match."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    not_: PredicateNode = Field(alias="not")


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


class AggFunction(str, Enum):
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

    column: str
    agg: AggFunction
    alias: str | None = None

    @property
    def resolved_alias(self) -> str:
        """Return the alias, or generate default from agg + column."""
        if self.alias is not None:
            return self.alias
        return f"{self.agg.value}_{self.column}"


class AggregateRequest(BaseModel):
    """POST /v1/query/{entity_type}/aggregate request body."""

    model_config = ConfigDict(extra="forbid")

    where: PredicateNode | None = None
    section: str | None = None
    group_by: list[str] = Field(min_length=1, max_length=5)
    aggregations: list[AggSpec] = Field(min_length=1, max_length=10)
    having: PredicateNode | None = None  # Post-aggregation filter

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

    group_count: int
    aggregation_count: int
    group_by: list[str]
    entity_type: str
    project_gid: str
    query_ms: float
    # LKG freshness metadata
    freshness: str | None = None
    data_age_seconds: float | None = None
    staleness_ratio: float | None = None


class AggregateResponse(BaseModel):
    """Response body for /aggregate endpoint."""

    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]]
    meta: AggregateMeta


class RowsRequest(BaseModel):
    """POST /v1/query/{entity_type}/rows request body."""

    model_config = ConfigDict(extra="forbid")

    where: PredicateNode | None = None
    section: str | None = None
    classification: str | None = None
    select: list[str] | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    order_by: str | None = None
    order_dir: Literal["asc", "desc"] = "asc"
    join: JoinSpec | None = None  # Cross-entity join specification

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

    total_count: int
    returned_count: int
    limit: int
    offset: int
    entity_type: str
    project_gid: str
    query_ms: float
    join_entity: str | None = None
    join_key: str | None = None
    join_matched: int | None = None
    join_unmatched: int | None = None
    # LKG freshness metadata
    freshness: str | None = None
    data_age_seconds: float | None = None
    staleness_ratio: float | None = None


class RowsResponse(BaseModel):
    """Response body for /rows endpoint."""

    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]]
    meta: RowsMeta
