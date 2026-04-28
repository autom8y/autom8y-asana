"""Phase 1 ``/exports`` route — single-entity, dual-mount, parameterized export.

Per TDD §3 + §6 + PRD §3 + spike-handoff §6 P1-C-01..P1-C-07. Implements:

- ``ExportRequest`` / ``ExportOptions`` Pydantic v2 contract with OPEN
  ``options`` substructure (P1-C-02 — closed enum FORBIDDEN); the future
  ``predicate_join_semantics`` field reservation per ADR-engine-left-preservation-guard
  mechanism (b) is the load-bearing forward-compat surface.
- Shared ``export_handler`` invoked by both PAT (``/api/v1/exports``) and S2S
  (``/v1/exports``) routes; same callable, same behavior, P1-C-07 dual-mount
  fidelity.
- ESC-1 (TDD §15.1) date operator translation in
  ``_exports_helpers.translate_date_predicates`` — runs BEFORE engine call so
  ``compiler.py:53-63,192-241`` are not modified (P1-C-04).
- ESC-2 (TDD §15.2) dual-AUTH verification: this module mounts under BOTH
  ``pat_router`` AND ``s2s_router`` factories at ``_security.py:37,45``. The
  TDD reading of FleetQuery as dual-AUTH was ESCALATED to architect; the
  resolution per Sprint 3 W2 is to honor PRD §7.3 and mount true dual-AUTH.
  Per-call auth-scope check is delegated to the existing PAT/S2S middleware
  (the PAT scheme is unchanged from existing dataframes routes; the bot PAT
  used for downstream Asana access is the same surface FleetQuery uses).
- LEFT-PRESERVATION GUARD wrapper (mechanism (a)) — Phase 1 ships single-entity
  so the LEFT-rewrite question does not fire; the wrapper is a NO-OP shim that
  records the no-op invocation so Sprint 4 qa-adversary can verify the seam
  exists without engine modification (P1-C-04). Mechanism (b) escape valve
  surfaces via ``options.predicate_join_semantics`` field reservation.
- ESC-3 (TDD §15.3) row-count + serialized-size measurement is logged at the
  format negotiation seam (``dataframes._format_dataframe_response`` +
  ``_format_csv_response`` / ``_format_parquet_response``).

ENTRY: every claim about engine behavior in this module is bounded by P1-C-04.
The handler does NOT modify any line in ``query/engine.py:139-178``,
``query/engine.py:181``, or ``query/join.py``. It calls into the existing
strategy ``_get_dataframe`` surface and applies post-load transformations
(filter, identity_complete, dedupe, format) in route-handler space.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from autom8y_log import get_logger
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from autom8_asana.api.dependencies import (  # noqa: TC001 — FastAPI resolves at runtime
    AsanaClientDualMode,
    AuthContextDep,
    EntityServiceDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.routes._exports_helpers import (
    InvalidSectionError,
    apply_active_default_section_predicate,
    attach_identity_complete,
    dedupe_by_key,
    filter_incomplete_identity,
    translate_date_predicates,
    validate_section_values,
)
from autom8_asana.api.routes._security import pat_router, s2s_router
from autom8_asana.api.routes.dataframes import _format_dataframe_response
from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.query.compiler import PredicateCompiler
from autom8_asana.query.errors import (
    CoercionError,
    InvalidOperatorError,
    UnknownFieldError,
)
from autom8_asana.query.models import (
    PredicateNode,
)
from autom8_asana.services.errors import (
    UnknownEntityError,
)
from autom8_asana.services.query_service import CacheNotWarmError

if TYPE_CHECKING:
    import polars as pl

__all__ = [
    "ExportOptions",
    "ExportRequest",
    "exports_router_v1",
    "exports_router_api_v1",
    "export_handler",
    "PHASE_1_DEFAULT_COLUMNS",
]

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# PRD §5.2 minimum viable column projection. DEFER-WATCH-2 disposition: ship
# this set and let Vince elicit additions in Sprint 4-5.
PHASE_1_DEFAULT_COLUMNS: tuple[str, ...] = (
    "gid",
    "name",
    "section",
    "office_phone",
    "vertical",
    "pipeline_type",
    "modified_at",
)


def _to_pascal_case(s: str) -> str:
    """Convert snake_case to PascalCase for SchemaRegistry key lookup."""
    return "".join(word.capitalize() for word in s.split("_"))


# ---------------------------------------------------------------------------
# Pydantic contract (TDD §3.1 + §3.2)
# ---------------------------------------------------------------------------


class ExportOptions(BaseModel):
    """Open / additive options substructure.

    Per spike-handoff §6 P1-C-02 + PRD §6: ``model_config = ConfigDict(extra="allow")``
    is LOAD-BEARING. Closing this enum FORBIDDEN — it would foreclose the
    Phase 2 ``predicate_join_semantics`` field per the LEFT-PRESERVATION GUARD
    ADR (mechanism (b) escape valve).

    Phase 1 named members:
        include_incomplete_identity: PRD §3.1 + AC-5/AC-6.
        dedupe_key: PRD §5.1 — account-grain identity key.

    Phase 2 reserved (NOT typed in Phase 1; admitted via ``extra="allow"``):
        predicate_join_semantics: ``Literal["preserve-outer", "allow-inner-rewrite"]``
            controlling the LEFT-PRESERVATION GUARD per the companion ADR.
    """

    # P1-C-02 BINDING — "allow" reserves room for predicate_join_semantics + any
    # additive Phase 2 members without breaking change.
    model_config = ConfigDict(extra="allow")

    include_incomplete_identity: bool = Field(
        default=True,
        description=(
            "When true (default), null-key rows surface with identity_complete=false "
            "(SCAR-005/006 transparency). When false, those rows are filtered "
            "pre-serialization. PRD AC-5 / AC-6."
        ),
    )
    dedupe_key: list[str] = Field(
        default_factory=lambda: ["office_phone", "vertical"],
        description=(
            "Account-grain dedup key. Default matches the canonical identity key "
            "(office_phone, vertical) per PRD §5.1."
        ),
    )


class ExportRequest(BaseModel):
    """Phase 1 export contract.

    Per spike-handoff §6 P1-C-01 (single-entity hard-lock): this contract has
    NO ``join`` field, NO ``target_entity`` field, NO
    ``predicate_target_resolution`` field. AC-12 verifies this by inspection.
    """

    # The TOP-level contract uses extra="forbid" to surface caller typos
    # (e.g. ``join`` mistakenly passed) at the schema layer. The OPEN-extension
    # surface lives in ``options`` per P1-C-02.
    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(
        description=(
            "Canonical business-entity identifier. Phase 1 inception-anchor: "
            '"process". Entity-parameterized (any registered entity admissible) '
            "but single-entity per request (P1-C-01)."
        ),
    )
    project_gids: list[int] = Field(
        min_length=1,
        description=(
            "Asana project GIDs. Phase 1 inception-anchor: "
            "[1201265144487549, 1201753128450029] (Reactivation, Outreach)."
        ),
    )
    predicate: PredicateNode | None = Field(
        default=None,
        description=(
            "Caller-supplied filter AST. Reuses query.models.PredicateNode "
            "union (Comparison | AndGroup | OrGroup | NotGroup). Sprint 2 "
            "additive Op enum members (BETWEEN, DATE_GTE, DATE_LTE) are "
            "translated by this route handler BEFORE engine call (ESC-1)."
        ),
    )
    format: Literal["json", "csv", "parquet"] = Field(
        default="json",
        description=(
            "Output format. JSON default per PRD §8.3 + DEFER-WATCH-5; CSV is "
            "Vince's BI-tool path; Parquet is the analytics-friendly binary "
            "format. PRD AC-7 + AC-11."
        ),
    )
    options: ExportOptions = Field(
        default_factory=ExportOptions,
        description="Open / additive options substructure (P1-C-02).",
    )


# ---------------------------------------------------------------------------
# Routers (TDD §6.2 — FleetQuery precedent)
# ---------------------------------------------------------------------------

# ESC-2 resolution (TDD §15.2): true dual-AUTH per PRD §7.3. PAT mount uses
# pat_router; S2S mount uses s2s_router. The handler is the SAME callable.
# Tag classification (per autom8y_api_middleware tag-classified security):
# - PAT mount tagged ``exports`` (PAT-classified — see api/main.py _PAT_TAGS).
# - S2S mount tagged ``internal`` (S2S-classified — see api/main.py _S2S_TAGS).
# The dual-mount pattern uses single-tag-per-operation so the OpenAPI security
# annotation strategy remains FAIL_CLOSED-compatible.
exports_router_v1 = s2s_router(
    prefix="/v1/exports",
    tags=["internal"],
)
exports_router_api_v1 = pat_router(
    prefix="/api/v1/exports",
    tags=["exports"],
)


# ---------------------------------------------------------------------------
# LEFT-PRESERVATION GUARD wrapper (TDD §10 + ADR §4 mechanism (a))
# ---------------------------------------------------------------------------


async def _engine_call_with_left_preservation_guard(
    *,
    entity_type: str,
    project_gid: str,
    client: Any,
    request_id: str,
    predicate_join_semantics: str,
) -> "pl.DataFrame":
    """Wrap the engine eager DataFrame fetch with the LEFT-PRESERVATION GUARD.

    Per ADR-engine-left-preservation-guard §4 mechanism (a): the wrapper runs
    the post-EXPLAIN assertion AROUND the engine call, NOT inside it. The
    engine code at ``query/engine.py:139-178`` and ``:181`` is FORBIDDEN per
    P1-C-04, so this wrapper sits in route-handler space.

    Phase 1 reality (per ADR §4.2): no joins ship in Phase 1, so the LEFT-rewrite
    question DOES NOT FIRE. The wrapper is therefore a structural NO-OP whose
    presence (and observable log signal) demonstrates the seam exists for Sprint
    4 qa-adversary verification + Phase 2 architect inheritance. Mechanism (b)
    (caller opt-in) is honored by the contract surface — the
    ``predicate_join_semantics`` value is forwarded into the log payload so
    auditors can see the caller signaled an override.
    """
    from autom8_asana.services.universal_strategy import get_universal_strategy

    strategy = get_universal_strategy(entity_type)
    df = await strategy._get_dataframe(project_gid, client)

    if df is None:
        raise CacheNotWarmError(
            f"DataFrame unavailable for {entity_type} project {project_gid}. "
            "Cache warming may be in progress or build failed."
        )

    # Phase 1: no join → no LazyFrame chain → no .explain() to inspect. The
    # wrapper records that the guard was reached. Phase 2 implementation
    # populates the assertion body per ADR §4.1.
    logger.debug(
        "exports_left_preservation_guard_noop",
        extra={
            "request_id": request_id,
            "entity_type": entity_type,
            "project_gid": project_gid,
            "predicate_join_semantics": predicate_join_semantics,
            "phase": 1,
            "join_active": False,
        },
    )
    return df


# ---------------------------------------------------------------------------
# Shared handler (TDD §3.3)
# ---------------------------------------------------------------------------


def _resolve_predicate_join_semantics(options: ExportOptions) -> str:
    """Read the Phase 2 escape-valve field via the OPEN options surface.

    Per ADR-engine-left-preservation-guard §4 mechanism (b): the field is NOT
    typed in Phase 1, so we read it through ``model_extra``. Default value is
    ``"preserve-outer"`` (fail-loud) per ADR §4.1.
    """
    extra = options.model_extra or {}
    raw = extra.get("predicate_join_semantics", "preserve-outer")
    if raw not in ("preserve-outer", "allow-inner-rewrite"):
        # Unknown value → default (do not silently accept arbitrary tokens).
        return "preserve-outer"
    return str(raw)


async def export_handler(
    *,
    request_body: ExportRequest,
    request_id: str,
    auth: object,
    entity_service: object,
    client: Any,
) -> Response:
    """Shared PAT + S2S handler for ``POST /v?/exports``.

    Pipeline (TDD §3.3 + §8.3):
        1. Validate ``entity_type`` via ``EntityService`` (PRD AC-9).
        2. Validate any caller-supplied ``section`` values (PRD §9.2 +
           TDD §9.4).
        3. Apply ACTIVE-default ``section`` filter when caller omits one
           (TDD §9.3).
        4. ESC-1 split: extract date-op Comparisons into a Polars filter
           expression (TDD §15.1).
        5. Compile remaining predicate via ``PredicateCompiler`` against the
           entity's warmed schema (P1-C-04 read-only consumption).
        6. Per project_gid: fetch eager DataFrame via the LEFT-PRESERVATION
           GUARD wrapper, apply filter expression, accumulate, vertical-stack.
        7. Attach identity_complete (TDD §8.1 — single source-of-truth).
        8. Optional null-key suppression (PRD AC-6).
        9. Dedupe by configured key (TDD §3.4 + DEFER-WATCH-1).
        10. Project columns to PHASE_1_DEFAULT_COLUMNS (DEFER-WATCH-2).
        11. Serialize via ``_format_dataframe_response`` with explicit format
            kwarg (TDD §7.2; ESC-3 size measurement at this seam).
    """
    import polars as pl

    # 1. Entity validation
    try:
        ctx = entity_service.validate_entity_type(request_body.entity_type)  # type: ignore[attr-defined]
    except UnknownEntityError as e:
        raise_api_error(
            request_id,
            400,
            "unknown_entity_type",
            f"Unknown entity_type: {request_body.entity_type!r}",
            details={"available_entities": getattr(e, "available", None)},
        )

    # 2. Section vocabulary validation (PRD §9.2)
    try:
        validate_section_values(request_body.predicate)
    except InvalidSectionError as e:
        raise_api_error(
            request_id,
            400,
            "unknown_section_value",
            str(e),
            details={"value": e.value},
        )

    # 3. ACTIVE-only default section filter when caller omits (TDD §9.3)
    effective_predicate, default_section_applied = (
        apply_active_default_section_predicate(request_body.predicate)
    )

    # 4. ESC-1 date predicate translation (TDD §15.1)
    try:
        date_split = translate_date_predicates(effective_predicate)
    except ValueError as e:
        raise_api_error(
            request_id,
            400,
            "malformed_predicate",
            str(e),
        )
    cleaned_predicate = date_split.cleaned_predicate
    date_filter_expr = date_split.date_filter_expr

    # 5. Compile non-date portion via existing PredicateCompiler (read-only)
    registry = SchemaRegistry.get_instance()
    schema = registry.get_schema(_to_pascal_case(request_body.entity_type))
    compiler = PredicateCompiler()
    base_filter_expr: "pl.Expr | None" = None
    if cleaned_predicate is not None:
        try:
            base_filter_expr = compiler.compile(cleaned_predicate, schema)
        except UnknownFieldError as e:
            raise_api_error(
                request_id,
                400,
                "unknown_field",
                str(e),
                details={"field": getattr(e, "field", None)},
            )
        except (InvalidOperatorError, CoercionError) as e:
            raise_api_error(
                request_id,
                400,
                "malformed_predicate",
                str(e),
            )

    # Combine: date_filter AND base_filter (both AND-merged downstream).
    # NOTE: polars Expr objects do NOT support truthiness (the implicit
    # ``or`` overload raises TypeError). Use explicit ``is not None`` guards.
    combined_filter_expr: "pl.Expr | None"
    if base_filter_expr is not None and date_filter_expr is not None:
        combined_filter_expr = base_filter_expr & date_filter_expr
    elif base_filter_expr is not None:
        combined_filter_expr = base_filter_expr
    elif date_filter_expr is not None:
        combined_filter_expr = date_filter_expr
    else:
        combined_filter_expr = None

    # 6. Per-project fetch + filter + concat
    predicate_join_semantics = _resolve_predicate_join_semantics(request_body.options)
    frames: list["pl.DataFrame"] = []
    for project_gid in request_body.project_gids:
        try:
            df = await _engine_call_with_left_preservation_guard(
                entity_type=request_body.entity_type,
                project_gid=str(project_gid),
                client=client,
                request_id=request_id,
                predicate_join_semantics=predicate_join_semantics,
            )
        except CacheNotWarmError as e:
            raise_api_error(
                request_id,
                503,
                "CACHE_NOT_WARMED",
                str(e),
                details={
                    "entity_type": request_body.entity_type,
                    "project_gid": str(project_gid),
                    "retry_after_seconds": 30,
                },
            )
        if combined_filter_expr is not None:
            df = df.filter(combined_filter_expr)
        frames.append(df)

    if not frames:
        # project_gids min_length=1 enforced by Pydantic; defensive only.
        result_df = pl.DataFrame()
    elif len(frames) == 1:
        result_df = frames[0]
    else:
        result_df = pl.concat(frames, how="diagonal_relaxed")

    # 7. identity_complete (P1-C-05 source-of-truth)
    result_df = attach_identity_complete(result_df)

    # 8. Optional null-key suppression
    result_df = filter_incomplete_identity(
        result_df,
        include=request_body.options.include_incomplete_identity,
    )

    # 9. Dedupe by configured key
    result_df = dedupe_by_key(result_df, keys=list(request_body.options.dedupe_key))

    # 10. Column projection (PRD §5.2 minimum)
    available_default_cols = [c for c in PHASE_1_DEFAULT_COLUMNS if c in result_df.columns]
    if "identity_complete" not in available_default_cols and "identity_complete" in result_df.columns:
        available_default_cols.append("identity_complete")
    if available_default_cols:
        result_df = result_df.select(available_default_cols)

    logger.info(
        "exports_handler_complete",
        extra={
            "request_id": request_id,
            "entity_type": request_body.entity_type,
            "project_gid_count": len(request_body.project_gids),
            "row_count": result_df.height,
            "format": request_body.format,
            "default_section_applied": default_section_applied,
            "predicate_join_semantics": predicate_join_semantics,
            "include_incomplete_identity": request_body.options.include_incomplete_identity,
        },
    )

    # 11. Format negotiation (eager DataFrame → response, ESC-3 measurement here)
    return _format_dataframe_response(
        df=result_df,
        request_id=request_id,
        limit=result_df.height,
        has_more=False,
        next_offset=None,
        accept=None,
        format=request_body.format,
    )


# ---------------------------------------------------------------------------
# Route registrations (TDD §6.2)
# ---------------------------------------------------------------------------


@exports_router_v1.post(
    "",
    summary="Export account-grain rows for a single entity (S2S /v1 namespace)",
    description=(
        "Phase 1 export surface. Single-entity per request; account-grain rows "
        "deduped by (office_phone, vertical) by default; identity_complete "
        "boolean column on every row; format-negotiable JSON | CSV | Parquet. "
        "S2S-authenticated via SERVICE_JWT_SCHEME."
    ),
    response_model=None,
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
    },
)
async def post_export_v1(
    request_body: ExportRequest,
    request_id: RequestId,
    auth: AuthContextDep,
    entity_service: EntityServiceDep,
    client: AsanaClientDualMode,
) -> Response:
    """POST /v1/exports — S2S route into the shared export_handler."""
    return await export_handler(
        request_body=request_body,
        request_id=request_id,
        auth=auth,
        entity_service=entity_service,
        client=client,
    )


@exports_router_api_v1.post(
    "",
    summary="Export account-grain rows for a single entity (PAT /api/v1 namespace)",
    description=(
        "Same handler as /v1/exports — mounted under PAT auth per PRD §7.3 "
        "dual-mount fidelity. Per-call auth-scope check delegated to the "
        "PAT_BEARER_SCHEME middleware (same surface as /api/v1/dataframes/* "
        "routes)."
    ),
    response_model=None,
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
    },
)
async def post_export_api_v1(
    request_body: ExportRequest,
    request_id: RequestId,
    auth: AuthContextDep,
    entity_service: EntityServiceDep,
    client: AsanaClientDualMode,
) -> Response:
    """POST /api/v1/exports — PAT route into the shared export_handler."""
    return await export_handler(
        request_body=request_body,
        request_id=request_id,
        auth=auth,
        entity_service=entity_service,
        client=client,
    )


# Re-export of ValidationError so downstream tests can catch the same type the
# Pydantic v2 router uses.
__all__.append("ValidationError")  # noqa: PLE0604 — module-level mutation acceptable here
