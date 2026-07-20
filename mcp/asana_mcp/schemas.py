"""Hand-authored tool-argument schemas (C2 / R6).

Spec-driven generation is STRUCTURALLY IMPOSSIBLE for the workhorse tools: the
query-execution router is ``include_in_schema=False`` (SVR-2), so the OpenAPI
spec does not describe /rows, /aggregate, or /resolve. These Pydantic models are
therefore hand-authored FROM the native models — ``autom8_asana.query.models``
(``RowsRequest`` / ``AggregateRequest``) and
``autom8_asana.api.routes.resolver_models`` (``ResolutionRequest``) — transcribed
at authoring time against HEAD f3d8eec1.

Constraint 5: these are INDEPENDENT models. This module does NOT import
autom8_asana. Fidelity to the native models is guarded by the WS-2-EP
pin-and-canary in ``tests/test_schema_canary.py`` (A5): it hashes the native
``query/models.py`` source (read as text, never imported) and trips if it drifts,
signalling that these mirrors need re-review. See ``NATIVE_SOURCE`` below.

Ergonomic curation (documented shortcut): the native ``where`` field is a
recursive discriminated-union ``PredicateNode``. Reproducing that union verbatim
hurts LLM tool ergonomics and would duplicate a large AST. It is mirrored here as
a flexible ``list | dict`` whose DESCRIPTION carries the full predicate grammar
(comparison / and / or / not / flat-array sugar) — the schema-grounding the LLM
needs, without the AST. The native ``extra="forbid"`` strictness is enforced
server-side on the real request; the tool arg is permissive by design.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# --- WS-2-EP pin-and-canary anchor (A5) --------------------------------------
# Native source of truth these schemas mirror, and the fields transcribed. The
# canary test asserts the source file's sha256 matches; on drift it fails with a
# "re-review asana_mcp/schemas.py" message. A7 semantic-score static gate is
# NOTED as a production upgrade — this POC ships the content-hash + token-presence
# check (a semantic-lite gate), not the full semantic-diff scorer.
NATIVE_SOURCE = {
    "rows_and_aggregate": "src/autom8_asana/query/models.py",
    "rows_and_aggregate_sha256": (
        "cca0dbf9ecc524b7f2fbbaaeb8aa4d50d4fb514bc90a6f5aab7f14a7dde82af4"
    ),
    "resolve": "src/autom8_asana/api/routes/resolver_models.py",
    "mirrored_rows_fields": [
        "where",
        "section",
        "classification",
        "select",
        "required_columns",
        "limit",
        "offset",
        "order_by",
        "order_dir",
        "project_gid",
        "section_gid",
    ],
    "mirrored_aggregate_fields": ["where", "section", "group_by", "aggregations", "having"],
    "mirrored_resolve_fields": ["criteria", "fields", "active_only"],
}

_PREDICATE_GRAMMAR = (
    'Composable predicate. A leaf comparison is {"field": <col>, "op": <op>, '
    '"value": <v>} where op is one of eq, ne, gt, lt, gte, lte, in, not_in, '
    "contains, starts_with (date ops between/date_gte/date_lte exist on exports). "
    'Groups: {"and": [..]}, {"or": [..]}, {"not": {..}}. A bare list of '
    "comparisons is auto-wrapped as AND (flat-array sugar). Null = no filter."
)


class RowsArgs(BaseModel):
    """Arguments for ``query_rows`` — mirrors native ``RowsRequest``."""

    model_config = ConfigDict(extra="forbid")

    where: list[Any] | dict[str, Any] | None = Field(
        default=None, description=f"Filter predicate to narrow rows. {_PREDICATE_GRAMMAR}"
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
        default=None, description="Columns to return. Null returns all columns."
    )
    required_columns: list[str] | None = Field(
        default=None,
        description=(
            "Honest-refusal contract (FM-5 ARM-B): columns your code requires served. "
            "The response meta reports contract_complete=False plus the named "
            "unservable columns if the served schema cannot satisfy them — never a "
            "silent drop. Null preserves default behavior."
        ),
    )
    limit: int = Field(default=100, ge=1, le=10_000, description="Max rows to return (1-10000).")
    offset: int = Field(default=0, ge=0, description="Rows to skip for pagination.")
    order_by: str | None = Field(default=None, description="Column to sort by.")
    order_dir: Literal["asc", "desc"] = Field(default="asc", description="Sort direction.")
    project_gid: str | None = Field(
        default=None,
        description=(
            "Optional Asana project GID (16 decimal digits). Overrides the "
            "registry-derived project for this request; required for "
            "body-parameterized entity types (e.g. project, section)."
        ),
    )
    section_gid: str | None = Field(
        default=None,
        description="Optional Asana section GID (16 digits); only valid with project_gid.",
    )


class AggSpecArg(BaseModel):
    """One aggregation — mirrors native ``AggSpec``."""

    model_config = ConfigDict(extra="forbid")

    column: str = Field(description="Column to aggregate.")
    agg: Literal["sum", "count", "mean", "min", "max", "count_distinct"] = Field(
        description="Aggregation function."
    )
    alias: str | None = Field(
        default=None, description="Output column name (defaults to agg_column)."
    )


class AggregateArgs(BaseModel):
    """Arguments for ``query_aggregate`` — mirrors native ``AggregateRequest``."""

    model_config = ConfigDict(extra="forbid")

    where: list[Any] | dict[str, Any] | None = Field(
        default=None, description=f"Pre-aggregation filter. {_PREDICATE_GRAMMAR}"
    )
    section: str | None = Field(default=None, description="Section name to scope the aggregation.")
    group_by: list[str] = Field(
        min_length=1, max_length=5, description="Columns to group by (1-5)."
    )
    aggregations: list[AggSpecArg] = Field(
        min_length=1, max_length=10, description="Aggregations to compute per group (1-10)."
    )
    having: list[Any] | dict[str, Any] | None = Field(
        default=None,
        description=f"Post-aggregation filter on grouped results. {_PREDICATE_GRAMMAR}",
    )


class ResolveArgs(BaseModel):
    """Arguments for ``resolve_entity`` — mirrors native ``ResolutionRequest``."""

    model_config = ConfigDict(extra="forbid")

    criteria: list[dict[str, Any]] = Field(
        description=(
            "Lookup criteria to resolve (max 1000). Each is a dict of identifier "
            'fields, e.g. {"phone": "+15551234567", "vertical": "dental"} or '
            '{"offer_id": "..."}. Use GET /v1/resolve/{entity_type}/schema to '
            "discover valid fields per entity type."
        ),
    )
    fields: list[str] | None = Field(
        default=None, description="Optional fields to enrich each match with."
    )
    active_only: bool = Field(
        default=True, description="Filter to active statuses only (default True)."
    )
