"""Pydantic v2 predicate models for the query engine.

Implements a discriminated union for PredicateNode (Comparison | AndGroup |
OrGroup | NotGroup) using a callable discriminator that inspects dict keys.

See ADR-QE-002 for the rationale behind this approach.
"""

from __future__ import annotations

import re
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

# Asana GID pattern: exactly 16 decimal digits.
# Sprint 2 receiver-surface — A1 body-precedence field validator.
_ASANA_GID_PATTERN: re.Pattern[str] = re.compile(r"^\d{16}$")


class Op(StrEnum):
    """Supported comparison operators.

    Sprint 2 additive members per TDD §5 (BETWEEN, DATE_GTE, DATE_LTE) extend the
    operator vocabulary for date filtering. AST shape is unchanged; per P1-C-03
    `Comparison.field` stays free-form `str` and `Comparison.value: Any` admits
    the new value shapes (e.g. `[date_lo, date_hi]` for BETWEEN).

    The new date operators are NOT compiled by `PredicateCompiler` in Phase 1
    — `compiler.py:53-63` and `compiler.py:192-241` are P1-C-04 forbidden. Date
    operators are translated to filter expressions by the `/exports` route
    handler BEFORE the engine call (see ESC-1 resolution in TDD §5.3 +
    `api/routes/exports.py:translate_date_predicates`).
    """

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
    # Sprint 2 additive (Phase 1 ESC-1 resolution): translated by the /exports
    # route handler, NOT by PredicateCompiler. See TDD §5.3.
    BETWEEN = "between"
    DATE_GTE = "date_gte"
    DATE_LTE = "date_lte"


class Comparison(BaseModel):
    """Leaf predicate node: single field comparison."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(description="Column name to compare against.", examples=["completed"])
    op: Op = Field(description="Comparison operator to apply.", examples=["eq"])
    value: Any = Field(description="Value to compare the field against.", examples=[False])


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

    not_: PredicateNode = Field(alias="not", description="Child predicate that must not match.")


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

    column: str = Field(description="Column to aggregate (must exist in SchemaRegistry).")
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
    aggregation_count: int = Field(description="Number of aggregation columns computed.")
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
    # ADR-serve-stale-within-bound (2026-06-03): mirror of RowsMeta.stale_served.
    # AggregateMeta is extra="forbid" and shares the engine._get_freshness_meta
    # side-channel (spread at engine.py execute_aggregate), so it must carry the
    # same additive field to accept the boolean.
    stale_served: bool = Field(
        default=False,
        description=(
            "True iff this read was served from a cache entry past its TTL "
            "(APPROACHING_STALE+SWR or STALE+LKG), i.e. served stale-within-bound "
            "rather than fresh. False for fresh serves or when no freshness "
            "side-channel is available."
        ),
        examples=[False],
    )


class AggregateResponse(BaseModel):
    """Response body for /aggregate endpoint."""

    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]] = Field(description="Aggregated result rows, one dict per group.")
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
    # FM-5 ARM-B (ADR-fm5-armb-contract-locus): the honest-refusal consumer-column
    # contract. A consumer declares the columns its code INDEXES and requires
    # served; the server answers, per request, whether the served schema can
    # satisfy that declaration (meta.contract_complete). This is the AUTHORITATIVE
    # runtime wire contract. Null (default) yields today's behavior — no
    # enforcement, contract_complete=True (additive, two-way door). Distinct from
    # ``select`` (which projects columns and 400s on an explicit unknown field via
    # UnknownFieldError): ``required_columns`` is a DECLARATION the no-select path
    # also honors, surfacing a typed signal instead of a silent narrow frame.
    required_columns: list[str] | None = Field(
        default=None,
        description=(
            "FM-5 ARM-B honest-refusal contract: columns the consumer's code "
            "indexes and requires served. The response meta reports "
            "contract_complete=False plus the named unservable columns if the "
            "served schema cannot satisfy them — never a silent drop. Null "
            "(default) preserves today's behavior."
        ),
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10_000,
        description="Maximum number of rows to return (1-10000). Clamped at server by max_result_rows.",
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
    # Sprint 2 receiver-surface — A1 body-precedence fields.
    # When present, body GID wins over registry-routed GID at the route handler.
    # Allows arbitrary Asana fleet project GIDs without pre-registration.
    # Pattern: exactly 16 decimal digits (Asana GID format).
    project_gid: str | None = Field(
        default=None,
        description=(
            "Optional Asana project GID (16 decimal digits). "
            "When set, overrides the EntityProjectRegistry-derived project_gid "
            "for this request. Enables arbitrary-GID consumer flows without "
            "requiring static registry pre-registration."
        ),
        examples=["1200653012566782"],
    )
    section_gid: str | None = Field(
        default=None,
        description=(
            "Optional Asana section GID (16 decimal digits). "
            "When set alongside project_gid, scopes the query to this section. "
            "Only valid when project_gid is also provided."
        ),
        examples=["1200653012566783"],
    )

    @field_validator("where", mode="before")
    @classmethod
    def wrap_flat_array(cls, v: Any) -> Any:
        """Auto-wrap bare list to AND group (FR-001 sugar)."""
        return _wrap_flat_array_to_and_group(v)

    @field_validator("project_gid", "section_gid", mode="before")
    @classmethod
    def validate_asana_gid(cls, v: Any) -> Any:
        """Validate Asana GID format: exactly 16 decimal digits."""
        if v is None:
            return v
        if not isinstance(v, str) or not _ASANA_GID_PATTERN.match(v):
            raise ValueError(
                f"Invalid Asana GID '{v}': must be exactly 16 decimal digits (e.g., '1200653012566782')"
            )
        return v

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
    # ADR-serve-stale-within-bound (2026-06-03): additive boolean attestation of
    # whether THIS read was served past TTL (APPROACHING_STALE/SWR or STALE/LKG),
    # i.e. NOT a fresh serve. Companion to the freshness/staleness_ratio fields:
    # a single unambiguous "was this read served stale?" signal the consumer (and
    # the S7 GetDfFallback-cause disaggregation) can read without re-parsing the
    # `freshness` enum string. Derived at the serve-path source (engine
    # _get_freshness_meta) from FreshnessInfo.freshness — never fabricated.
    # Default False: a fresh serve, or no freshness side-channel, is NOT stale.
    stale_served: bool = Field(
        default=False,
        description=(
            "True iff this read was served from a cache entry past its TTL "
            "(APPROACHING_STALE+SWR or STALE+LKG), i.e. served stale-within-bound "
            "rather than fresh. False for fresh serves or when no freshness "
            "side-channel is available."
        ),
        examples=[False],
    )
    # Sprint 1 — asana-clean-break-leaf T1.5 (PG-01 mandatory).
    # Option G binding: envelope-canonical receipt shape per PR #271 FW-AUTOM8Y_ENV-CANONICAL.
    # AC-3: DERIVED from SectionPersistence.get_manifest_async() via is_honest_complete().
    # S-01 (unconditional True) is REFUSED — this field reflects real per-section completeness.
    # Default False: if no manifest is available, we do not claim completeness.
    honest_contract_complete: bool = Field(
        default=False,
        description=(
            "Structural attestation field. True iff zero sections have SectionStatus.FAILED "
            "in the SectionManifest at query time. Derived from SectionPersistence — not "
            "fabricated. False if no manifest exists or any section failed during progressive build."
        ),
        examples=[True],
    )
    # ADR-1 (honest-empty-200): additive attestation that a genuinely-empty
    # project was served as a 200 with empty data (NOT a stuck
    # CACHE_BUILD_IN_PROGRESS 503). True iff the manifest is honest-complete AND
    # the query yielded zero rows. Distinguishes a legitimately-empty project
    # (honest_empty=True, attested) from a still-building/failed one
    # (honest_contract_complete=False -> 503). The query endpoint's
    # "NEVER a silent empty-200" invariant is preserved: this empty-200 is
    # ATTESTED, not silent. Consumer-additive — the bridge reads meta by key and
    # ignores unknowns (verified: bridge_response_to_df does not strict-reject
    # extra meta keys, and skips the honest-contract stamp on empty frames).
    honest_empty: bool = Field(
        default=False,
        description=(
            "True iff the project is honest-complete (no FAILED sections) AND the query "
            "returned zero rows — a legitimately-empty project served as an attested "
            "honest-empty-200, not a stuck build-in-progress 503. False otherwise."
        ),
        examples=[False],
    )
    # FM-5 ARM-B (ADR-fm5-armb-contract-locus D2): the column analogue of
    # honest_contract_complete, co-derived at the SAME one gate but emitted as a
    # DISTINCT sibling field — NOT a mutation of honest_contract_complete. Folding
    # column-completeness into honest_contract_complete would route a STRUCTURAL
    # column gap into the section-completeness 503/retry semantics above
    # ("honest_contract_complete=False -> 503"), a retry-forever conflation (a
    # missing schema column is never fixed by retrying). Completeness is derived
    # from SCHEMA membership, never df.columns (immune to a 100%-NULL served
    # column). Default True: a non-declaring consumer (no required_columns) gets
    # today's behavior — byte-equivalent meta semantics for existing callers.
    contract_complete: bool = Field(
        default=True,
        description=(
            "FM-5 ARM-B honest-refusal contract. True iff every column the consumer "
            "declared in request.required_columns is present in the served schema. "
            "False iff any declared column is unservable — a TYPED contract-incomplete "
            "signal, never a silent narrow frame, a KeyError, or a $0/7-row fossil. "
            "Distinct sibling of honest_contract_complete (which carries section "
            "completeness and drives 503/retry); a column gap is structural, not a "
            "retry. True by default for non-declaring consumers."
        ),
        examples=[True],
    )
    unservable_required_columns: list[str] = Field(
        default_factory=list,
        description=(
            "The declared required columns the served schema cannot satisfy (the "
            "named cause behind contract_complete=False). Empty when the contract is "
            "complete or no columns were declared."
        ),
        examples=[["offer_id"]],
    )
    column_manifest: dict[str, object] | None = Field(
        default=None,
        description=(
            "Belt-and-braces population detail, computed ONLY when required_columns "
            "is declared (non-declaring callers pay nothing): the served columns "
            "present in this frame and their per-column non-null counts, so a consumer "
            "can fail fast on a present-but-empty column. Null when no contract is "
            "declared."
        ),
    )


class RowsResponse(BaseModel):
    """Response body for /rows endpoint.

    Canonical envelope shape (B1 ratification — Sprint 2 receiver-surface):
    The route handler returns ``SuccessResponse[RowsResponse]``, producing a
    **double-envelope** JSON shape::

        {
            "data": {                        # SuccessResponse.data
                "data": [...],               # RowsResponse.data  (rows)
                "meta": {                    # RowsResponse.meta
                    "total_count": N,
                    "project_gid": "...",
                    "honest_contract_complete": true|false,
                    ...
                }
            }
        }

    Consumer-side access pattern (autom8 legacy Sprint 2)::

        rows = response.json()["data"]["data"]
        meta = response.json()["data"]["meta"]
        project_gid = meta["project_gid"]
        honest = meta["honest_contract_complete"]

    Option B1 chosen: double-envelope confirmed canonical. Consumer ADR §3.4
    must reference ``response.json()['data']['data']`` (not ``['data']`` directly).
    SVR-4 (HANDOFF-10x-dev-to-rnd §2.2) resolved by this docstring amendment.
    """

    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]] = Field(description="Result rows, one dict per entity.")
    meta: RowsMeta = Field(description="Query execution and pagination metadata.")
