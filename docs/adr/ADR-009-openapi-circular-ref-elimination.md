---
artifact_id: ADR-009
title: "Eliminate Circular $ref from OpenAPI Spec via Internal Route Exclusion"
created_at: "2026-02-12T16:00:00Z"
author: architect
status: proposed
context: "The autom8_asana OpenAPI spec contains circular $ref chains from recursive predicate models (AndGroup, OrGroup, NotGroup). These cycles cause starlight-openapi (via @apidevtools/json-schema-ref-parser) to enter infinite recursion during static site generation, forcing a runtime fallback renderer (Stoplight Elements)."
decision: "Exclude all S2S-only internal routes from the public OpenAPI spec using FastAPI's include_in_schema=False, which removes the recursive predicate schemas entirely. Internal consumers receive a separate spec endpoint."
consequences:
  - type: positive
    description: "Public OpenAPI spec becomes cycle-free, enabling starlight-openapi static doc generation"
  - type: positive
    description: "Zero changes to runtime behavior, API contracts, or Pydantic models"
  - type: positive
    description: "Simpler, smaller public spec focused on the audience that actually reads docs"
  - type: positive
    description: "Reversible -- re-adding routes to schema is a one-line change per router"
  - type: negative
    description: "Internal S2S consumers lose automatic schema discovery from the public spec"
    mitigation: "Add a separate /openapi-internal.json endpoint behind S2S auth for internal consumers"
  - type: neutral
    description: "Internal routes remain fully functional; only their schema visibility changes"
related_artifacts:
  - PRD-dynamic-query-service
  - ADR-QE-002
tags:
  - openapi
  - docs
  - api-design
  - devex
schema_version: "1.0"
---

## Context

The autom8_asana API serves two distinct audiences:

1. **Public consumers** (PAT-authenticated): CRUD operations on tasks, projects, sections, users, workspaces, plus dataframes and webhooks.
2. **Internal S2S consumers** (JWT-authenticated): Query engine (predicate-based row/aggregate queries), entity resolver, entity writes, admin cache management, and internal system routes.

The query engine models use recursive Pydantic types to express composable predicate trees:

```python
# Simplified from autom8_asana/query/models.py
class AndGroup(BaseModel):
    and_: list[PredicateNode] = Field(alias="and")

class OrGroup(BaseModel):
    or_: list[PredicateNode] = Field(alias="or")

class NotGroup(BaseModel):
    not_: PredicateNode = Field(alias="not")

PredicateNode = Annotated[Comparison | AndGroup | OrGroup | NotGroup, ...]
```

FastAPI emits these as circular `$ref` chains in the OpenAPI spec:

```
AndGroup.and -> oneOf[$ref Comparison, $ref AndGroup, $ref OrGroup, $ref NotGroup]
OrGroup.or  -> oneOf[$ref Comparison, $ref AndGroup, $ref OrGroup, $ref NotGroup]
NotGroup.not -> oneOf[$ref Comparison, $ref AndGroup, $ref OrGroup, $ref NotGroup]
```

This creates 6 cycles (each group references the other two groups plus itself). The starlight-openapi plugin uses `@apidevtools/json-schema-ref-parser` which cannot handle circular references and enters infinite recursion. The current workaround is a Stoplight Elements runtime renderer, which is a smell -- it doesn't generate static pages, has no sidebar integration, and requires a client-side JavaScript bundle.

### Prior Fix (Stays)

`SuccessResponse[dict[str, Any]]` was already replaced with `AsanaResource` (Pydantic model with `extra="allow"`), eliminating one class of circular `$ref`. This ADR addresses the remaining cycles from the predicate models.

## Options Considered

### Option A: Exclude Internal Routes from Public Spec (Selected)

Set `include_in_schema=False` on all S2S-only routers. The predicate models (`AndGroup`, `OrGroup`, `NotGroup`, `Comparison`), along with `RowsRequest`, `AggregateRequest`, and all other internal-only schemas, are excluded from the generated spec because no visible route references them.

**Routes to exclude** (all require S2S JWT, no public consumers):

| Router | Prefix | Tag | Reason |
|--------|--------|-----|--------|
| `query_v2_router` | `/v1/query` | query-v2 | Predicate-based rows/aggregate (S2S only) |
| `query_router` | `/v1/query` | query | Legacy query + /rows duplicate (S2S only) |
| `resolver_router` | `/v1/resolve` | resolver | Entity resolution (S2S only) |
| `admin_router` | `/v1/admin` | admin | Cache management (S2S only) |
| `entity_write_router` | `/api/v1/entity` | entity-write | Field writes (S2S only) |
| `internal_router` | `/api/v1/internal` | internal | Internal system routes (S2S only) |

**Routes that remain** (public consumers):

| Router | Prefix | Tag |
|--------|--------|-----|
| `health_router` | `/health` | health |
| `users_router` | `/api/v1/users` | users |
| `workspaces_router` | `/api/v1/workspaces` | workspaces |
| `dataframes_router` | `/api/v1/dataframes` | dataframes |
| `tasks_router` | `/api/v1/tasks` | tasks |
| `projects_router` | `/api/v1/projects` | projects |
| `sections_router` | `/api/v1/sections` | sections |
| `webhooks_router` | `/api/v1/webhooks` | webhooks |

### Option B: Break Recursion in Predicate Models

Flatten the recursive types by introducing explicit depth-limited schemas (e.g., `PredicateNodeDepth0`, `PredicateNodeDepth1`, `PredicateNodeDepth2`) or by using `Any`/`dict` at the leaf level and validating depth in a custom validator.

**Rejected because:**
- Complexity: Requires maintaining parallel schema hierarchies or losing type safety
- Fragility: The depth-limited approach generates combinatorial schema explosion (4 types x N depth = many schemas)
- API contract change: External tooling that reads the spec would see different schema shapes
- Unnecessary: The recursive models are correct; only the *doc toolchain* can't handle them

### Option C: OpenAPI 3.1 `$dynamicRef` / `$recursiveRef`

Use JSON Schema 2020-12's `$dynamicRef` to express recursion in a way that avoids naive ref-parser cycles.

**Rejected because:**
- FastAPI/Pydantic do not emit `$dynamicRef` natively; would require post-processing
- `@apidevtools/json-schema-ref-parser` (starlight-openapi's dependency) does not support `$dynamicRef` as of v11.x
- Two unsupported layers makes this a dead end for the foreseeable future

### Option D: Post-process the Spec (Strip Circular Schemas)

Run a script that detects circular `$ref` chains and either inlines them to a depth limit or replaces recursive types with `{}` (any).

**Rejected because:**
- Lossy: Consumers of the spec lose type information for query models
- Build pipeline complexity: Adds a fragile post-processing step that must evolve with every schema change
- Doesn't address the root problem (wrong audience seeing internal schemas)

### Option E: Split Specs by Audience (Dual Generation)

Generate two separate OpenAPI specs: one for public docs, one for internal. Mount two separate `FastAPI` applications or use OpenAPI tags to filter.

**Rejected as overkill because:**
- Option A achieves the same outcome with less machinery
- A separate `/openapi-internal.json` endpoint is simpler than dual apps
- If we later need a full internal spec site, we can promote to dual generation

## Decision

**Option A: Exclude internal S2S routes from the public OpenAPI spec.**

This is the right choice because:

1. **It addresses the root cause.** The circular refs exist only in internal schemas. Removing them from the public spec eliminates all cycles.

2. **It respects audience boundaries.** Public docs consumers (external developers, partner integrators) never call S2S endpoints. Showing them JWT-only internal routes with complex predicate schemas creates confusion, not value.

3. **It is the simplest viable solution.** One-line change per router (`include_in_schema=False`). No model changes, no post-processing, no new dependencies.

4. **It is fully reversible.** If we later need internal routes in the public spec (e.g., customer-facing query API), we flip the flag back and address the circular ref at that time with the then-current toolchain.

5. **Internal consumers retain access.** A dedicated `/openapi-internal.json` endpoint (behind S2S auth) serves the full spec to programmatic consumers that need it.

## Implementation Plan

### Step 1: Mark S2S Routers as Schema-Excluded

In each internal router module, add `include_in_schema=False` to the `APIRouter` constructor.

**File**: `~/code/autom8_asana/src/autom8_asana/api/routes/query_v2.py`
```python
# Before:
router = APIRouter(prefix="/v1/query", tags=["query-v2"])

# After:
router = APIRouter(prefix="/v1/query", tags=["query-v2"], include_in_schema=False)
```

**File**: `~/code/autom8_asana/src/autom8_asana/api/routes/query.py`
```python
# Before:
router = APIRouter(prefix="/v1/query", tags=["query"])

# After:
router = APIRouter(prefix="/v1/query", tags=["query"], include_in_schema=False)
```

**File**: `~/code/autom8_asana/src/autom8_asana/api/routes/resolver.py`
```python
# Before:
router = APIRouter(prefix="/v1/resolve", tags=["resolver"])

# After:
router = APIRouter(prefix="/v1/resolve", tags=["resolver"], include_in_schema=False)
```

**File**: `~/code/autom8_asana/src/autom8_asana/api/routes/admin.py`
```python
# Before:
router = APIRouter(prefix="/v1/admin", tags=["admin"])

# After:
router = APIRouter(prefix="/v1/admin", tags=["admin"], include_in_schema=False)
```

**File**: `~/code/autom8_asana/src/autom8_asana/api/routes/entity_write.py`
```python
# Before:
router = APIRouter(prefix="/api/v1/entity", tags=["entity-write"])

# After:
router = APIRouter(prefix="/api/v1/entity", tags=["entity-write"], include_in_schema=False)
```

**File**: `~/code/autom8_asana/src/autom8_asana/api/routes/internal.py`
```python
# Before:
router = APIRouter(prefix="/api/v1/internal", tags=["internal"])

# After:
router = APIRouter(prefix="/api/v1/internal", tags=["internal"], include_in_schema=False)
```

### Step 2: Add Internal Spec Endpoint (Optional, Recommended)

Add a new route that serves the full OpenAPI spec (with internal routes) for S2S consumers. This uses FastAPI's `get_openapi()` with all routes included.

**File**: `~/code/autom8_asana/src/autom8_asana/api/routes/internal.py` (add endpoint)
```python
from fastapi.openapi.utils import get_openapi

@router.get("/openapi.json", include_in_schema=False)
async def internal_openapi_spec(
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> JSONResponse:
    """Serve full OpenAPI spec including internal routes.

    S2S-only. Returns the complete spec for programmatic consumers.
    """
    app = request.app
    # Generate spec with all routes (bypass include_in_schema filtering)
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,  # All routes, not just schema-included
    )
    return JSONResponse(content=openapi_schema)
```

### Step 3: Regenerate and Validate the Public Spec

```bash
# Start the app and fetch the spec
cd ~/code/autom8_asana
uvicorn autom8_asana.api.main:create_app --factory --port 8000 &
curl -s http://localhost:8000/openapi.json > /tmp/autom8y-asana-openapi-public.json

# Verify no circular refs remain
python3 -c "
import json, sys

with open('/tmp/autom8y-asana-openapi-public.json') as f:
    spec = json.load(f)

schemas = spec.get('components', {}).get('schemas', {})
circular_schemas = {'AndGroup', 'OrGroup', 'NotGroup', 'Comparison',
                    'RowsRequest', 'RowsResponse', 'AggregateRequest',
                    'AggregateResponse', 'Op', 'AggFunction', 'AggSpec',
                    'RowsMeta', 'AggregateMeta', 'JoinSpec'}
found = circular_schemas & set(schemas.keys())
if found:
    print(f'FAIL: Internal schemas still present: {found}', file=sys.stderr)
    sys.exit(1)
print(f'PASS: {len(schemas)} schemas, no internal schemas present')
print(f'Paths: {len(spec[\"paths\"])}')
"
```

### Step 4: Convert and Deploy to Docs Site

```bash
# Convert to YAML for starlight-openapi
python3 -c "
import json, yaml
with open('/tmp/autom8y-asana-openapi-public.json') as f:
    spec = json.load(f)
with open('sites/docs/specs/autom8y-asana-openapi.yaml', 'w') as f:
    yaml.dump(spec, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
"

# Test starlight-openapi build
cd ~/code/autom8y/sites/docs
npm run build
```

### Step 5: Promote Asana Spec to starlight-openapi

In `sites/docs/astro.config.mjs`, the Asana spec is already configured in starlightOpenAPI. Once the spec is cycle-free, remove the Stoplight Elements fallback:

1. Remove `EmbeddedApiReference.astro` component
2. Remove `src/pages/api/asana.astro` (the Elements wrapper page)
3. Remove the manual "Asana Integration" sidebar entry (starlight-openapi generates it)
4. Remove `@stoplight/elements` from package.json (if added)

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Internal team forgets routes are hidden from public spec | Medium | Low | Comment in each router file explains why `include_in_schema=False` is set |
| New internal route added without `include_in_schema=False` introduces new circular ref | Low | Medium | CI validation step: check generated spec for circular refs before deploy |
| S2S consumer relies on /openapi.json for code generation | Low | Low | `/api/v1/internal/openapi.json` endpoint serves full spec |
| Orphaned schemas remain in spec after route exclusion | None | None | FastAPI only emits schemas referenced by visible routes; unused schemas are automatically pruned |

## Success Criteria

1. Public OpenAPI spec at `/openapi.json` contains zero circular `$ref` chains
2. `AndGroup`, `OrGroup`, `NotGroup`, `Comparison`, `RowsRequest`, `AggregateRequest` are absent from the public spec's `components/schemas`
3. `npm run build` in `sites/docs/` completes without stack overflow
4. starlight-openapi generates static pages for all Asana public endpoints
5. All S2S endpoints remain fully functional (routing, auth, business logic unchanged)
6. Internal spec is accessible at `/api/v1/internal/openapi.json` behind S2S auth

## References

- FastAPI `include_in_schema` parameter: [FastAPI docs](https://fastapi.tiangolo.com/reference/apirouter/)
- starlight-openapi circular ref issue: uses `@apidevtools/json-schema-ref-parser` which does not support circular `$ref`
- OpenAPI 3.1 spec: Circular `$ref` is valid per JSON Schema 2020-12, but tooling support varies widely
