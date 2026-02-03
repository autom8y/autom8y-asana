# TDD: Dynamic Query Service -- Sprint 1 (Query Engine Foundation)

## Metadata

| Field | Value |
|-------|-------|
| **TDD ID** | TDD-dynamic-query-service |
| **PRD** | PRD-dynamic-query-service |
| **Status** | Draft |
| **Created** | 2026-02-03 |
| **Author** | Architect |
| **Sprint** | 1 of 3 |
| **Scope** | `/rows` endpoint, predicate AST, section scoping, query guards |

---

## 1. System Context

### 1.1 What We Are Building

A composable query engine that compiles JSON predicate trees into Polars
expressions, replacing the flat equality filtering on the existing
`POST /v1/query/{entity_type}` endpoint. Sprint 1 delivers the `/rows`
endpoint; Sprints 2-3 add `/aggregate` and `/metric`.

### 1.2 Architectural Position

```
                 +-----------------+
                 |   API Gateway   |
                 |  (S2S JWT Auth) |
                 +--------+--------+
                          |
           +--------------+--------------+
           |                             |
  POST /v1/query/{et}          POST /v1/query/{et}/rows
  (existing, deprecated)       (new, Sprint 1)
           |                             |
           v                             v
  +------------------+       +------------------------+
  | EntityQueryService|       | PredicateCompiler      |
  | ._apply_filters() |       | .compile(node, schema) |
  | (flat equality)   |       | -> pl.Expr             |
  +--------+---------+       +-----------+------------+
           |                              |
           +------+-----------------------+
                  |
                  v
       +---------------------+
       | UniversalResolution  |
       | Strategy             |
       | ._get_dataframe()    |
       +---------------------+
                  |
       +----------+----------+
       | DataFrameCache       |
       | Memory -> S3 -> Warm |
       +---------------------+
```

### 1.3 Key Constraint: Section Column Stores Names, Not GIDs

**Verified via codebase analysis** (`dataframes/extractors/base.py:479-509`):
The `_extract_section()` method extracts `section.get("name")` from Asana
memberships. The base schema defines `section` as `Utf8` with description
"Section name within project."

Therefore, when the `section` request parameter is "Active", we filter the
DataFrame by `pl.col("section") == "Active"` -- a **direct name match**.
No GID resolution is needed for the DataFrame filter itself. SectionIndex
is used only to **validate** that the section name is known (preventing
typos from silently returning empty results).

---

## 2. Architecture Decisions

### ADR-DQS-001: Dedicated `query/` Package vs. Extending `services/query_service.py`

**Context**: The existing `EntityQueryService` has flat equality filtering.
The new predicate compiler, Pydantic models, and value coercion logic
represent a significant amount of new code (~400 LOC).

**Options Considered**:
1. **Extend EntityQueryService** with a new `query_expr` method accepting `pl.Expr`
2. **New `query/` package** under `src/autom8_asana/query/` with models, compiler, service
3. **New module in `services/`** (e.g., `services/query_v2.py`)

**Decision**: Option 1 -- Extend `EntityQueryService` with a new method, and
place predicate models and compiler in a new `src/autom8_asana/query/` package.

**Rationale**:
- The service already owns the cache access lifecycle (`_get_dataframe`). Duplicating
  that in a new service creates coupling without benefit.
- The predicate compiler and models are a distinct concern from the service itself,
  warranting their own package.
- A `query/` package provides clean module boundaries for Sprint 2/3 additions
  (`aggregate.py`, `metric_bridge.py`) without bloating `services/`.
- The route handler stays thin -- it validates, compiles, delegates to the service.

**Consequences**:
- `EntityQueryService` gains one new method (`query_with_expr`).
- New `query/` package owns models, compiler, and value coercion.
- Sprint 2/3 can add modules without modifying Sprint 1 code.

### ADR-DQS-002: Predicate Compiler as Functions, Not Class Hierarchy

**Context**: The compiler transforms `PredicateNode -> pl.Expr`. Two patterns:
(a) Visitor class hierarchy with dispatch, (b) recursive function with
pattern matching on discriminated union.

**Decision**: Recursive function with pattern matching on the Pydantic
discriminated union tag.

**Rationale**:
- The AST has exactly 2 node types (comparison, group). A class hierarchy
  for 2 types is over-engineering.
- A single `compile_predicate(node, schema) -> pl.Expr` function with
  `match node.type` is readable and testable.
- Polars expression composition is functional by nature (`&`, `|`, `~`).
- If Sprint 2 adds new node types (e.g., `is_null`), a new match branch
  suffices -- no new classes needed.

**Consequences**:
- Compiler is a single module (`query/compiler.py`) with ~100 LOC.
- Each leaf compilation path is independently unit-testable.
- Operator/dtype validation is a lookup table, not polymorphic dispatch.

### ADR-DQS-003: Section Parameter Uses Direct Name Match

**Context**: EC-010 requires clarity on how `section` parameter maps to
DataFrame filtering. SectionIndex resolves name->GID, but the DataFrame
stores names.

**Decision**: The `section` parameter filters by **direct name comparison**
against the DataFrame `section` column. SectionIndex is used only to
**validate** the section name is known before filtering.

**Rationale**:
- The DataFrame `section` column stores names (e.g., "Active"), confirmed
  by `_extract_section()` which extracts `section.get("name")`.
- Resolving name->GID->name would be a round-trip that adds complexity for
  no benefit.
- Validation via SectionIndex catches typos (e.g., "Actve") that would
  otherwise silently return zero rows.
- The existing test data in `test_routes_query.py` already uses name strings
  ("ACTIVE", "PAUSED") in the section column.

**Consequences**:
- SectionIndex.resolve() is called to validate, but the GID is not used
  for filtering.
- If a section exists in SectionIndex but has a different display name than
  what is stored in the DataFrame, validation would pass but filter would
  return zero rows. This is acceptable because the manifest and extraction
  use the same Asana API name field.
- One additional refinement: validation should be **case-insensitive** (the
  SectionIndex already lowercases), but the DataFrame filter should use the
  **canonical name** from the manifest. For Sprint 1, we accept case-sensitive
  DataFrame matching and rely on consumers passing the correct case.

### ADR-DQS-004: Route Organization -- Extend Existing `query.py`

**Context**: Where to place the new `/rows` route handler.

**Decision**: Extend the existing `api/routes/query.py` file with the new
endpoint. Do not create a new file.

**Rationale**:
- Both endpoints share the prefix `/v1/query`, the same `router` instance,
  and the same auth dependency.
- The existing route registration in `main.py` (line 1363) already includes
  the query router. No registration changes needed.
- The file is currently ~400 LOC. Adding ~150 LOC for the new endpoint
  keeps it under 600 LOC -- manageable.
- A separate `query_v2.py` would require a second router import and
  registration, adding mechanical complexity for no architectural benefit.

**Consequences**:
- Deprecation header logic lives alongside the new endpoint for visibility.
- The file grows but remains cohesive (all query routes).
- Sprint 2/3 endpoints also go here, potentially warranting extraction later.

### ADR-DQS-005: Value Coercion in the Compiler

**Context**: JSON values must be coerced to Polars-compatible types before
expression construction. Options: (a) coerce in the compiler, (b) separate
coercion layer, (c) coerce in Pydantic validators.

**Decision**: Coerce in the compiler, co-located with expression assembly.

**Rationale**:
- Coercion depends on the column's dtype (from SchemaRegistry), which is
  only available at compile time.
- Pydantic validators run before we know which field/dtype the value targets.
- A separate coercion layer would require passing schema context through
  an extra layer for no separation-of-concerns benefit.
- Coercion errors produce `COERCION_FAILED` with field/dtype context --
  this context is naturally available in the compiler.

**Consequences**:
- The compiler module handles validation, coercion, and expression assembly.
- Each step is a separate private function for testability.
- Coercion logic is ~50 LOC covering the 8 dtype cases.

---

## 3. Module Structure

```
src/autom8_asana/
  query/                          # NEW PACKAGE
    __init__.py                   # Public API: compile_predicate, models
    models.py                     # Pydantic models (PredicateNode, RowsRequest, etc.)
    compiler.py                   # PredicateNode -> pl.Expr compilation
    guards.py                     # MAX_RESULT_ROWS, MAX_PREDICATE_DEPTH, depth check
  services/
    query_service.py              # MODIFIED: add query_with_expr() method
  api/routes/
    query.py                      # MODIFIED: add /rows endpoint, deprecation headers
  metrics/
    resolve.py                    # EXISTING: SectionIndex (read-only usage)
```

### 3.1 New Files

| File | Purpose | LOC Estimate |
|------|---------|-------------|
| `query/__init__.py` | Re-exports public API | ~15 |
| `query/models.py` | Pydantic request/response models, predicate AST | ~180 |
| `query/compiler.py` | Predicate compilation with schema validation | ~200 |
| `query/guards.py` | Query guard constants and depth checker | ~40 |

### 3.2 Modified Files

| File | Changes |
|------|---------|
| `services/query_service.py` | Add `query_with_expr(entity_type, project_gid, client, expr, select, limit, offset) -> QueryResult` |
| `api/routes/query.py` | Add `POST /{entity_type}/rows` handler, deprecation headers on existing endpoint |
| `api/routes/__init__.py` | No changes (same router) |
| `api/main.py` | No changes (same router registration) |

---

## 4. Pydantic Model Definitions

### 4.1 Predicate AST Models (`query/models.py`)

```python
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ComparisonOp(str, Enum):
    """Supported comparison operators."""
    eq = "eq"
    ne = "ne"
    gt = "gt"
    lt = "lt"
    gte = "gte"
    lte = "lte"
    in_ = "in"
    not_in = "not_in"
    contains = "contains"
    starts_with = "starts_with"


class ComparisonPredicate(BaseModel):
    """Leaf node: field comparison.

    Example: {"field": "mrr", "op": "gt", "value": 1000}
    """
    model_config = ConfigDict(extra="forbid")

    type: Literal["comparison"] = "comparison"
    field: str
    op: ComparisonOp
    value: Any  # Coerced to column dtype at compile time


class AndGroup(BaseModel):
    """AND group node."""
    model_config = ConfigDict(extra="forbid")

    type: Literal["and"] = "and"
    and_: list[PredicateNode] = Field(alias="and")


class OrGroup(BaseModel):
    """OR group node."""
    model_config = ConfigDict(extra="forbid")

    type: Literal["or"] = "or"
    or_: list[PredicateNode] = Field(alias="or")


class NotGroup(BaseModel):
    """NOT group node."""
    model_config = ConfigDict(extra="forbid")

    type: Literal["not"] = "not"
    not_: PredicateNode = Field(alias="not")


# Discriminated union via the JSON structure (not via `type` field).
# The PRD defines the wire format as {"and": [...]}, {"or": [...]},
# {"not": {...}}, or {"field": ..., "op": ..., "value": ...}.
# We use a custom discriminator based on which key is present.
PredicateNode = Annotated[
    Union[ComparisonPredicate, AndGroup, OrGroup, NotGroup],
    Field(discriminator="type"),
]
```

**Wire Format Mapping**: The PRD wire format uses `{"and": [...]}` without
a `type` discriminator. To bridge this, the route handler includes a
**pre-parse normalizer** that transforms wire format to discriminated form:

```python
def normalize_predicate(raw: Any) -> dict:
    """Transform PRD wire format to discriminated union format.

    - {"and": [...]}        -> {"type": "and", "and": [...]}
    - {"or": [...]}         -> {"type": "or", "or": [...]}
    - {"not": {...}}        -> {"type": "not", "not": {...}}
    - {"field": ..., ...}   -> {"type": "comparison", "field": ..., ...}
    - [...]                 -> {"type": "and", "and": [...]}  (flat array sugar)
    """
```

This normalizer runs recursively before Pydantic validation.

### 4.2 Request/Response Models

```python
class RowsRequest(BaseModel):
    """Request body for POST /v1/query/{entity_type}/rows."""
    model_config = ConfigDict(extra="forbid")

    where: Any | None = None  # Raw JSON, normalized before parse
    section: str | None = None
    select: list[str] | None = None
    limit: int = 100
    offset: int = 0

    @field_validator("limit")
    @classmethod
    def clamp_limit(cls, v: int) -> int:
        if v < 1:
            raise ValueError("limit must be >= 1")
        return min(v, 1000)

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        if v < 0:
            raise ValueError("offset must be >= 0")
        return v


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


class RowsResponse(BaseModel):
    """Response body for POST /v1/query/{entity_type}/rows."""
    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]]
    meta: RowsMeta
```

---

## 5. Predicate Compiler Design (`query/compiler.py`)

### 5.1 Public API

```python
def compile_predicate(
    node: PredicateNode,
    schema: DataFrameSchema,
) -> pl.Expr:
    """Compile a predicate AST into a Polars expression.

    Args:
        node: Root of the predicate tree.
        schema: Entity schema for field/dtype validation.

    Returns:
        Polars expression for DataFrame.filter().

    Raises:
        PredicateCompilationError: With error_code indicating the failure:
            - UNKNOWN_FIELD: Field not in schema
            - INVALID_OPERATOR: Operator/dtype incompatible
            - COERCION_FAILED: Value cannot be coerced to field dtype
    """
```

### 5.2 Compilation Flow

```
PredicateNode
    |
    +-- ComparisonPredicate
    |       |
    |       +-- 1. Validate field exists in schema
    |       +-- 2. Get ColumnDef.dtype
    |       +-- 3. Validate operator/dtype compatibility
    |       +-- 4. Coerce value to target dtype
    |       +-- 5. Build pl.col(field).op(coerced_value)
    |
    +-- AndGroup
    |       +-- Compile each child, reduce with `&`
    |       +-- Empty children -> pl.lit(True)
    |
    +-- OrGroup
    |       +-- Compile each child, reduce with `|`
    |       +-- Empty children -> pl.lit(True)
    |
    +-- NotGroup
            +-- Compile child, apply `~`
```

### 5.3 Operator/Dtype Compatibility Matrix

Encoded as a module-level constant:

```python
# Maps dtype string -> set of allowed operators
DTYPE_OPERATORS: dict[str, set[ComparisonOp]] = {
    "Utf8": {eq, ne, gt, lt, gte, lte, in_, not_in, contains, starts_with},
    "Int64": {eq, ne, gt, lt, gte, lte, in_, not_in},
    "Int32": {eq, ne, gt, lt, gte, lte, in_, not_in},
    "Float64": {eq, ne, gt, lt, gte, lte, in_, not_in},
    "Boolean": {eq, ne, in_, not_in},
    "Date": {eq, ne, gt, lt, gte, lte, in_, not_in},
    "Datetime": {eq, ne, gt, lt, gte, lte, in_, not_in},
    "Decimal": {eq, ne, gt, lt, gte, lte, in_, not_in},
    "List[Utf8]": set(),  # No operators in Sprint 1
}
```

### 5.4 Operator-to-Polars Expression Mapping

```python
def _build_comparison_expr(
    field: str, op: ComparisonOp, coerced_value: Any
) -> pl.Expr:
    col = pl.col(field)
    match op:
        case ComparisonOp.eq:       return col == coerced_value
        case ComparisonOp.ne:       return col != coerced_value
        case ComparisonOp.gt:       return col > coerced_value
        case ComparisonOp.lt:       return col < coerced_value
        case ComparisonOp.gte:      return col >= coerced_value
        case ComparisonOp.lte:      return col <= coerced_value
        case ComparisonOp.in_:      return col.is_in(coerced_value)
        case ComparisonOp.not_in:   return ~col.is_in(coerced_value)
        case ComparisonOp.contains: return col.str.contains(coerced_value, literal=True)
        case ComparisonOp.starts_with: return col.str.starts_with(coerced_value)
```

### 5.5 Value Coercion Rules

```python
def _coerce_value(
    value: Any, dtype: str, field_name: str, op: ComparisonOp
) -> Any:
    """Coerce JSON value to Polars-compatible Python type.

    For in/not_in operators, coerces each element in the list.
    """
```

| Source Type | Target Dtype | Coercion |
|-------------|-------------|----------|
| `str` | Utf8 | Passthrough |
| `int`/`float` | Int64/Int32 | `int(value)` / range check |
| `int`/`float` | Float64 | `float(value)` |
| `str` | Date | `datetime.date.fromisoformat(value)` |
| `str` | Datetime | `datetime.datetime.fromisoformat(value)` |
| `bool` | Boolean | Passthrough (must be actual bool, not int) |
| `int`/`float` | Decimal | `float(value)` (schema maps Decimal->Float64) |
| `int`/`str` -> Utf8 | Permissive | `str(value)` (numeric to string is allowed) |
| `list` | in/not_in | Coerce each element per above rules |

### 5.6 Error Types

```python
class PredicateCompilationError(Exception):
    """Raised when predicate compilation fails."""

    def __init__(
        self,
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(message)
```

Error codes: `UNKNOWN_FIELD`, `INVALID_OPERATOR`, `COERCION_FAILED`.

The route handler catches `PredicateCompilationError` and maps to
HTTP 422 with the error taxonomy from the PRD.

---

## 6. Section Resolution Integration

### 6.1 Integration Pattern

Section validation uses `SectionIndex` but does NOT use FastAPI `Depends`
for async construction. Instead, the route handler builds it inline:

```python
async def _resolve_section(
    section_name: str,
    entity_type: str,
    request: Request,
) -> str:
    """Validate section name and return canonical name for filtering.

    Strategy:
    1. Try SectionIndex.from_manifest_async() using SectionPersistence
    2. Fall back to SectionIndex.from_enum_fallback(entity_type)
    3. If neither resolves, raise UNKNOWN_SECTION error

    Returns:
        The section name as provided (for direct DataFrame column match).

    Raises:
        HTTPException 422 UNKNOWN_SECTION
    """
```

**Why not `Depends`**: SectionIndex requires `SectionPersistence` (S3 bucket)
and `project_gid` (from EntityProjectRegistry), both of which are resolved
inside the route handler. Threading these through FastAPI's DI adds complexity
without benefit for a single call site.

### 6.2 Section Filter Application

When `section` is provided and validated:

```python
# Build section filter expression
section_expr = pl.col("section") == section_name

# Combine with user predicate (if any)
if user_expr is not None:
    final_expr = section_expr & user_expr
else:
    final_expr = section_expr
```

### 6.3 Section Conflict Detection (EC-006)

Before compilation, scan the predicate tree for `ComparisonPredicate` nodes
where `field == "section"`. If found AND `section` parameter is also provided:

1. Log warning: `section_parameter_conflicts_with_predicate`
2. Remove the `section` predicates from the tree (parameter wins)
3. Proceed with parameter-based section filter

Implementation: a `strip_section_predicates(node) -> PredicateNode | None`
function that recursively removes section comparison nodes.

---

## 7. EntityQueryService Extension

### 7.1 New Method

```python
async def query_with_expr(
    self,
    entity_type: str,
    project_gid: str,
    client: AsanaClient,
    expr: pl.Expr | None,
    select: list[str],
    limit: int,
    offset: int,
) -> QueryResult:
    """Query with a compiled Polars expression.

    Same cache lifecycle as query(), but accepts a pre-compiled
    pl.Expr instead of a flat dict.

    Args:
        expr: Compiled Polars expression (None = no filter).
        Other args: Same as query().

    Returns:
        QueryResult with data and metadata.
    """
    strategy = self.strategy_factory(entity_type)
    df = await strategy._get_dataframe(project_gid, client)

    if df is None:
        raise CacheNotWarmError(...)

    # Apply expression filter
    if expr is not None:
        filtered_df = df.filter(expr)
    else:
        filtered_df = df

    total_count = len(filtered_df)
    paginated_df = self._apply_pagination(filtered_df, offset, limit)
    selected_df = self._apply_select(paginated_df, select)
    data = selected_df.to_dicts()

    return QueryResult(data=data, total_count=total_count, project_gid=project_gid)
```

### 7.2 Backward Compatibility

The existing `query()` method is unchanged. The deprecated endpoint
continues to call `query()` with flat dict filtering. No existing behavior
is modified.

---

## 8. Route Handler Design (`api/routes/query.py`)

### 8.1 New Endpoint: `POST /v1/query/{entity_type}/rows`

```python
@router.post("/{entity_type}/rows", response_model=RowsResponse)
async def query_rows(
    entity_type: str,
    request_body: RowsRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> RowsResponse:
```

**Handler Flow**:

```
1. Log request with structured context
2. Validate entity_type (same as existing)
3. Get project_gid from EntityProjectRegistry
4. Get bot_pat for AsanaClient
5. Normalize predicate (wire format -> discriminated union)
6. Check predicate depth (guard: MAX_PREDICATE_DEPTH)
7. If section parameter provided:
   a. Validate via SectionIndex
   b. Strip section predicates from tree (if conflict)
8. Parse normalized predicate into PredicateNode
9. Validate select fields against schema
10. Compile predicate -> pl.Expr (may raise PredicateCompilationError)
11. Combine section filter with compiled expression
12. Call EntityQueryService.query_with_expr()
13. Build RowsResponse with timing metadata
14. Return response
```

### 8.2 Deprecation Headers on Existing Endpoint

Add to the existing `query_entities` handler:

```python
# After building response, before return:
response_obj = JSONResponse(content=response.model_dump())
response_obj.headers["Deprecation"] = "true"
response_obj.headers["Sunset"] = "2026-06-01"
response_obj.headers["Link"] = (
    '</v1/query/{entity_type}/rows>; rel="successor-version"'
)

logger.info(
    "deprecated_query_endpoint_used",
    extra={"caller_service": claims.service_name, "entity_type": entity_type},
)
```

### 8.3 Error Handling Flow

```
PredicateCompilationError
    -> error_code == "UNKNOWN_FIELD"    -> 422 {error, message, available_fields}
    -> error_code == "INVALID_OPERATOR" -> 422 {error, message, field, dtype, op, supported}
    -> error_code == "COERCION_FAILED"  -> 422 {error, message, field, dtype, value}

QueryTooComplexError (from depth guard)
    -> 400 {error: "QUERY_TOO_COMPLEX", message, max_depth}

UNKNOWN_SECTION (from section validation)
    -> 422 {error: "UNKNOWN_SECTION", message, section}

CacheNotWarmError
    -> 503 {error: "CACHE_NOT_WARMED", ...}

Pydantic ValidationError
    -> 422 (standard FastAPI format)
```

---

## 9. Query Guards (`query/guards.py`)

```python
MAX_RESULT_ROWS: int = 10_000
MAX_PREDICATE_DEPTH: int = 5


class QueryTooComplexError(Exception):
    """Raised when predicate tree exceeds MAX_PREDICATE_DEPTH."""

    def __init__(self, depth: int):
        self.depth = depth
        super().__init__(
            f"Predicate tree depth {depth} exceeds maximum of {MAX_PREDICATE_DEPTH}"
        )


def check_predicate_depth(raw: Any, max_depth: int = MAX_PREDICATE_DEPTH) -> int:
    """Compute predicate tree depth and raise if it exceeds max.

    Operates on raw JSON (before Pydantic parse) for fail-fast behavior.
    Returns the actual depth for logging.
    """


def clamp_limit(limit: int) -> int:
    """Clamp limit to MAX_RESULT_ROWS."""
    return min(limit, MAX_RESULT_ROWS)
```

**Depth Calculation**:
- A bare `ComparisonPredicate` (leaf) = depth 1
- `{"and": [leaf]}` = depth 2
- `{"and": [{"or": [leaf]}]}` = depth 3
- The check runs on raw JSON before any Pydantic parsing

**Limit Enforcement**: The Pydantic validator clamps to 1000 (per-request
soft limit). The guard clamps to 10,000 (absolute hard limit). In practice,
the Pydantic limit of 1000 is the binding constraint for Sprint 1. The
10,000 guard exists for Sprint 2's aggregate endpoint which may not have
per-request pagination.

---

## 10. Data Flow: End-to-End Sequence

```
Client                  Route Handler          Compiler         Service          Cache
  |                         |                     |               |               |
  |  POST /rows             |                     |               |               |
  |  {where, section, ...}  |                     |               |               |
  |------------------------>|                     |               |               |
  |                         |                     |               |               |
  |                    validate entity_type        |               |               |
  |                    validate section (SectionIndex)             |               |
  |                    normalize predicate         |               |               |
  |                    check_predicate_depth       |               |               |
  |                         |                     |               |               |
  |                         | compile_predicate   |               |               |
  |                         |-------------------->|               |               |
  |                         |                validate field       |               |
  |                         |                validate op/dtype    |               |
  |                         |                coerce value         |               |
  |                         |                build pl.Expr        |               |
  |                         |<--------------------|               |               |
  |                         |                                     |               |
  |                         | combine section_expr & pred_expr    |               |
  |                         |                                     |               |
  |                         | query_with_expr(expr, ...)          |               |
  |                         |------------------------------------>|               |
  |                         |                                     | _get_dataframe|
  |                         |                                     |-------------->|
  |                         |                                     |    DataFrame  |
  |                         |                                     |<--------------|
  |                         |                                     |               |
  |                         |                                df.filter(expr)      |
  |                         |                                df.slice(off,lim)    |
  |                         |                                df.select(cols)      |
  |                         |                                     |               |
  |                         |              QueryResult            |               |
  |                         |<------------------------------------|               |
  |                         |                                                     |
  |   RowsResponse          |                                                     |
  |   {data, meta}          |                                                     |
  |<------------------------|                                                     |
```

---

## 11. Test Plan

### 11.1 Unit Tests: Predicate Compiler (`tests/unit/query/test_compiler.py`)

| ID | Test Case | Input | Expected |
|----|-----------|-------|----------|
| TC-C001 | Compile eq comparison | `{field: "name", op: "eq", value: "Acme"}` | `pl.col("name") == "Acme"` |
| TC-C002 | Compile gt comparison (numeric) | `{field: "mrr", op: "gt", value: 1000}` | Expression filters correctly |
| TC-C003 | Compile in operator | `{field: "vertical", op: "in", value: ["dental", "medical"]}` | `pl.col("vertical").is_in(...)` |
| TC-C004 | Compile not_in operator | `{field: "vertical", op: "not_in", value: ["dental"]}` | `~pl.col("vertical").is_in(...)` |
| TC-C005 | Compile contains (string) | `{field: "name", op: "contains", value: "Smith"}` | `pl.col("name").str.contains("Smith")` |
| TC-C006 | Compile starts_with | `{field: "name", op: "starts_with", value: "A"}` | `pl.col("name").str.starts_with("A")` |
| TC-C007 | Compile AND group | `{and: [eq1, eq2]}` | `expr1 & expr2` |
| TC-C008 | Compile OR group | `{or: [eq1, eq2]}` | `expr1 \| expr2` |
| TC-C009 | Compile NOT group | `{not: {field: ..., op: eq, ...}}` | `~expr` |
| TC-C010 | Nested AND/OR | `{and: [{or: [a, b]}, c]}` | Correct nesting |
| TC-C011 | Empty AND group | `{and: []}` | `pl.lit(True)` |
| TC-C012 | Unknown field | `{field: "nonexistent", ...}` | `PredicateCompilationError(UNKNOWN_FIELD)` |
| TC-C013 | Invalid operator for dtype | `{field: "mrr", op: "contains", ...}` | `PredicateCompilationError(INVALID_OPERATOR)` |
| TC-C014 | Coercion failure | `{field: "mrr", op: "eq", value: "abc"}` (mrr is Utf8 in schema, so this actually passes) | Verify dtype-specific coercion |
| TC-C015 | Date coercion | `{field: "date", op: "gt", value: "2025-01-01"}` | Correctly coerced Date |
| TC-C016 | Datetime coercion | `{field: "created", op: "gt", value: "2025-01-01T00:00:00Z"}` | Correctly coerced Datetime |
| TC-C017 | Boolean comparison | `{field: "is_completed", op: "eq", value: true}` | `pl.col("is_completed") == True` |
| TC-C018 | List[Utf8] field rejected | `{field: "tags", op: "eq", value: "x"}` | `PredicateCompilationError(INVALID_OPERATOR)` |
| TC-C019 | Numeric to string coercion | `{field: "name", op: "eq", value: 123}` | Coerced to "123" |

### 11.2 Unit Tests: Predicate Normalizer (`tests/unit/query/test_models.py`)

| ID | Test Case | Input | Expected |
|----|-----------|-------|----------|
| TC-N001 | Flat array sugar | `[{field: "a", ...}, {field: "b", ...}]` | `{type: "and", and: [...]}` |
| TC-N002 | Empty array | `[]` | `{type: "and", and: []}` |
| TC-N003 | Nested normalization | `{and: [{or: [{field:...}]}]}` | All nodes get `type` tags |
| TC-N004 | Already-typed passthrough | `{type: "comparison", ...}` | Unchanged |

### 11.3 Unit Tests: Query Guards (`tests/unit/query/test_guards.py`)

| ID | Test Case | Input | Expected |
|----|-----------|-------|----------|
| TC-G001 | Depth 1 (leaf) | Single comparison | depth=1, no error |
| TC-G002 | Depth 2 (one group) | `{and: [leaf]}` | depth=2, no error |
| TC-G003 | Depth 5 (at limit) | 5-deep nesting | depth=5, no error |
| TC-G004 | Depth 6 (exceeds) | 6-deep nesting | `QueryTooComplexError` |
| TC-G005 | Flat array depth | `[leaf, leaf]` | depth=2 (array counts as group) |
| TC-G006 | None predicate | `None` | depth=0, no error |

### 11.4 Unit Tests: Section Resolution (`tests/unit/query/test_section.py`)

| ID | Test Case | Input | Expected |
|----|-----------|-------|----------|
| TC-S001 | Valid section name | "Active" with manifest | Passes validation |
| TC-S002 | Unknown section name | "Nonexistent" | UNKNOWN_SECTION error |
| TC-S003 | Case-insensitive validation | "active" with "Active" in manifest | Passes |
| TC-S004 | Enum fallback for offer | "Active" without manifest | Passes via OfferSection |
| TC-S005 | Section conflict strip | Predicate with section field + section param | Section predicates removed, warning logged |

### 11.5 Integration Tests (`tests/api/test_routes_query_rows.py`)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-I001 | Basic /rows query with eq predicate | 200, filtered results |
| TC-I002 | /rows with section parameter | 200, section-filtered results |
| TC-I003 | /rows with nested AND/OR predicate | 200, correct filtering |
| TC-I004 | /rows with unknown field in predicate | 422 UNKNOWN_FIELD |
| TC-I005 | /rows with invalid operator for dtype | 422 INVALID_OPERATOR |
| TC-I006 | /rows with coercion failure | 422 COERCION_FAILED |
| TC-I007 | /rows with unknown section | 422 UNKNOWN_SECTION |
| TC-I008 | /rows with depth > 5 | 400 QUERY_TOO_COMPLEX |
| TC-I009 | /rows with no predicate (all rows) | 200, all rows |
| TC-I010 | /rows with empty array predicate | 200, all rows |
| TC-I011 | /rows pagination (limit + offset) | 200, correct slice and total_count |
| TC-I012 | /rows select fields with gid always included | 200, gid present |
| TC-I013 | /rows cache not warm | 503 CACHE_NOT_WARMED |
| TC-I014 | /rows missing auth | 401 MISSING_AUTH |
| TC-I015 | /rows PAT token rejected | 401 SERVICE_TOKEN_REQUIRED |
| TC-I016 | /rows response meta includes query_ms | 200, query_ms > 0 |
| TC-I017 | Existing /query/{et} still works | 200, same behavior |
| TC-I018 | Existing /query/{et} has deprecation headers | Deprecation: true, Sunset header present |
| TC-I019 | /rows with flat array sugar predicate | 200, treated as AND |
| TC-I020 | /rows with in operator | 200, correct set membership filtering |

---

## 12. Sprint 1 Implementation Task Breakdown (Ordered)

### Phase 1: Foundation (No Route Changes)

| # | Task | File(s) | Depends On | Est. LOC |
|---|------|---------|-----------|----------|
| 1 | Create `query/` package with `__init__.py` | `query/__init__.py` | -- | 15 |
| 2 | Implement Pydantic models (`PredicateNode`, `RowsRequest`, `RowsResponse`) | `query/models.py` | 1 | 180 |
| 3 | Implement query guards (constants, depth checker) | `query/guards.py` | 1 | 40 |
| 4 | Implement predicate compiler with schema validation and coercion | `query/compiler.py` | 2 | 200 |
| 5 | Unit tests for models and normalizer | `tests/unit/query/test_models.py` | 2 | 80 |
| 6 | Unit tests for guards | `tests/unit/query/test_guards.py` | 3 | 60 |
| 7 | Unit tests for compiler | `tests/unit/query/test_compiler.py` | 4 | 250 |

### Phase 2: Service Extension

| # | Task | File(s) | Depends On | Est. LOC |
|---|------|---------|-----------|----------|
| 8 | Add `query_with_expr()` to `EntityQueryService` | `services/query_service.py` | 4 | 40 |
| 9 | Unit tests for `query_with_expr()` | `tests/unit/services/test_query_service.py` | 8 | 60 |

### Phase 3: Route Integration

| # | Task | File(s) | Depends On | Est. LOC |
|---|------|---------|-----------|----------|
| 10 | Implement section validation helper in route | `api/routes/query.py` | 4 | 50 |
| 11 | Implement `POST /{entity_type}/rows` handler | `api/routes/query.py` | 8, 10 | 120 |
| 12 | Add deprecation headers to existing endpoint | `api/routes/query.py` | -- | 15 |
| 13 | Integration tests for /rows endpoint | `tests/api/test_routes_query_rows.py` | 11 | 350 |
| 14 | Integration test for deprecation headers | `tests/api/test_routes_query_rows.py` | 12 | 30 |

### Phase 4: Polish

| # | Task | File(s) | Depends On | Est. LOC |
|---|------|---------|-----------|----------|
| 15 | Section conflict detection (strip section predicates) | `query/compiler.py` | 7 | 30 |
| 16 | Unit tests for section conflict stripping | `tests/unit/query/test_compiler.py` | 15 | 40 |

**Total estimated LOC**: ~1,560 (implementation + tests)

---

## 13. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Section column content mismatch** | Low | High | Verified via codebase: `_extract_section()` stores names. Add an assertion in integration test. |
| **Polars expression edge cases** (null handling, type mismatches) | Medium | Medium | Comprehensive unit tests for each operator/dtype combination. Polars null semantics are well-documented. |
| **Recursive predicate parsing stack overflow** | Low | Medium | MAX_PREDICATE_DEPTH=5 checked before recursion. Python default recursion limit is 1000. |
| **Performance regression on existing endpoint** | Low | Low | Deprecation headers add negligible overhead. Existing handler is unchanged. |
| **Wire format normalization bugs** | Medium | Medium | Extensive normalizer tests. The normalizer is the most complex piece of Sprint 1 parsing. |
| **SectionPersistence unavailability** | Low | Medium | Enum fallback covers the primary use case (offer sections). Log and return empty SectionIndex if S3 is unreachable. |

---

## 14. Performance Considerations

### 14.1 Latency Budget (p50 target: <50ms)

| Step | Expected Time | Notes |
|------|--------------|-------|
| Auth validation | ~1ms | JWT validation cached |
| Predicate compilation | ~0.1ms | Pure Python dict traversal |
| Section validation | ~2ms | S3 manifest cached in memory |
| DataFrame retrieval | ~0.5ms | Memory-tier cache hit |
| Polars filter + select + slice | ~5ms | In-memory columnar operations |
| Serialization | ~10ms | `to_dicts()` for 100-1000 rows |
| **Total** | **~19ms** | Well under 50ms target |

### 14.2 No Lazy Evaluation in Sprint 1

DataFrames are already materialized in memory cache. Polars lazy evaluation
would add plan compilation overhead without benefit. Revisit in Sprint 2
if aggregate queries benefit from pushdown optimization.

---

## 15. Observability

Each `/rows` request logs:

```python
logger.info(
    "query_rows_request",
    extra={
        "request_id": request_id,
        "entity_type": entity_type,
        "caller_service": claims.service_name,
        "predicate_depth": depth,
        "predicate_leaf_count": leaf_count,
        "section": section_name,
        "section_resolved": section_name is not None,
        "select_fields": select_fields,
        "limit": limit,
        "offset": offset,
    },
)

logger.info(
    "query_rows_complete",
    extra={
        "request_id": request_id,
        "entity_type": entity_type,
        "total_count": result.total_count,
        "returned_count": len(result.data),
        "query_ms": round(elapsed_ms, 2),
        "caller_service": claims.service_name,
    },
)
```

---

## 16. Security Considerations

- **No injection vectors**: Predicate values are used exclusively in Polars
  expression construction. No string interpolation, no SQL, no `eval()`.
- **Depth limit prevents resource exhaustion**: MAX_PREDICATE_DEPTH=5
  checked before any compilation.
- **Row limit prevents memory exhaustion**: Limit clamped to 1000 per
  request (10,000 absolute max).
- **extra="forbid"** on all Pydantic models prevents unexpected fields.
- **S2S JWT required**: Same auth as existing endpoint via
  `require_service_claims()`.

---

## Attestation Table

| File | Absolute Path | Read |
|------|---------------|------|
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-dynamic-query-service.md` | Yes |
| Query Service | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` | Yes |
| Query Route | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query.py` | Yes |
| Route Registration | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/__init__.py` | Yes |
| Main App (route include) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` (lines 1353-1364) | Yes |
| Schema Registry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Yes |
| Schema Model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/schema.py` | Yes |
| Base Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/base.py` | Yes |
| Offer Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/offer.py` | Yes |
| Section Extraction | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/base.py` (lines 479-509) | Yes |
| SectionIndex | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/resolve.py` | Yes |
| SectionPersistence | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Yes |
| OfferSection | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/sections.py` | Yes |
| Auth Dependency | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/internal.py` | Yes |
| MetricExpr | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/expr.py` | Yes |
| Resolver Utils | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Yes |
| Existing Query Tests | `/Users/tomtenuta/Code/autom8_asana/tests/api/test_routes_query.py` | Yes |
