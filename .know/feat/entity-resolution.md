---
domain: feat/entity-resolution
generated_at: "2026-04-01T16:10:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/resolution/**/*.py"
  - "./src/autom8_asana/services/resolver.py"
  - "./src/autom8_asana/services/universal_strategy.py"
  - "./src/autom8_asana/api/routes/resolver.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.82
format_version: "1.0"
---

# Entity Resolution (Phone+Vertical to GID)

## Purpose and Design Rationale

Entity resolution converts business identifiers (phone number + vertical) into Asana task GIDs. This bridges external CRM data and the Asana task graph. Every cross-service operation (intake, reconciliation, automation) requires GID resolution before acting on an entity.

**O(1) lookup via DynamicIndex**: Primary path skips Asana API entirely. DataFrames pre-warmed into memory/Redis at startup. `UniversalResolutionStrategy` builds `DynamicIndex` keyed on criterion columns.

**Schema-driven, not entity-specific**: Unified `UniversalResolutionStrategy` per TDD-DYNAMIC-RESOLVER-001. New entity types become resolvable automatically when they have a schema in `SchemaRegistry` and a project in `EntityProjectRegistry`.

**Hierarchy traversal as fallback**: Strategy chain (`SessionCacheStrategy` -> `NavigationRefStrategy` -> `DependencyShortcutStrategy` -> `HierarchyTraversalStrategy`) for automation workflows resolving from a trigger entity. Not used by HTTP API.

**Status-aware filtering**: `active_only` (default `true`) filters to active/activating via `SectionClassifier`. `total_match_count` preserves pre-filter count.

## Conceptual Model

### Two Distinct Sub-systems

**Sub-system A: HTTP API Resolution** -- `POST /v1/resolve/{entity_type}`, S2S JWT only, entirely DataFrame-backed. Validates criteria against SchemaRegistry, normalizes field names (5-step alias resolution: `"phone"` -> `"office_phone"`), builds/retrieves DynamicIndex per key_column group, classifies GIDs by section activity, filters by active_only, returns all matches sorted by ACTIVITY_PRIORITY.

**Sub-system B: Programmatic Resolution** -- `ResolutionContext` for automation workflows. Strategy chain with `ApiBudget(max_calls=8)` ceiling. Session-scoped cache across calls within one `async with` block.

### EntityWriteRegistry (same package, different concern)

`write_registry.py` auto-discovers writable entity types by scanning for `CustomFieldDescriptor` properties. Initialized on `app.state.entity_write_registry` at startup.

## Implementation Map

### resolution/ package (8 files)

`budget.py` (ApiBudget), `context.py` (ResolutionContext session manager), `result.py` (ResolutionResult[T] generic), `selection.py` (FieldPredicate, CompoundPredicate, EntitySelector), `strategies.py` (4 strategies + DEFAULT_CHAIN/BUSINESS_CHAIN), `write_registry.py` (EntityWriteRegistry), `field_resolver.py` (FieldResolver for snake_case -> API payload).

### Service layer (3 files)

`services/resolver.py` (EntityProjectRegistry singleton, criterion validation, 5-step alias normalization), `services/universal_strategy.py` (UniversalResolutionStrategy, DynamicIndexCache, SectionClassifier integration), `services/resolution_result.py` (API-facing ResolutionResult with GIDs and status annotations).

### Route: `api/routes/resolver.py`

S2S JWT only. `POST /v1/resolve/{entity_type}`. OTel-instrumented. Error tier taxonomy per ADR.

**Naming collision**: Two `ResolutionResult` types exist -- `resolution/result.py` (internal generic with entity) and `services/resolution_result.py` (API-facing with GIDs). Maintenance trap.

## Boundaries and Failure Modes

### Hard Boundaries

- **S2S JWT only**: No PAT path
- **DataFrame cache dependency**: Does NOT trigger builds on miss; returns INDEX_UNAVAILABLE
- **Schema+Project gating**: Entity resolvable only if both schema and project GID exist
- **Cascade health gate**: >20% null rate in key columns raises CascadeNotReadyError (503)
- **Batch limit**: 1000 criteria per request
- **Package scope separation**: strategy chain is for intra-process navigation, not HTTP API

### Failure Modes

| Failure | Result |
|---------|--------|
| Discovery incomplete | 503 DISCOVERY_INCOMPLETE |
| Project not configured | 503 PROJECT_NOT_CONFIGURED |
| DataFrame cache miss | INDEX_UNAVAILABLE per-criterion |
| Cascade >20% null | 503 CascadeNotReadyError |
| Phone normalization failure | Bypassed descriptor misses E.164 (SCAR-020) |
| All matches inactive | NOT_FOUND with total_match_count > 0 |
| Multi-match | All GIDs returned; caller handles |

## Knowledge Gaps

1. **`DynamicIndex` internals** (data structure, collision behavior) not read.
2. **`resolver_models.py`** (Pydantic request/response models) not read.
3. **`intake_resolve.py` relationship** to generic resolver not documented.
4. **`SectionClassifier` implementation depth** not verified in source.
