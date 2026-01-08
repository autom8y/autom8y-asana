# PRD: Dynamic Schema-Driven Resolver Architecture

---
id: PRD-dynamic-resolver-architecture
title: Dynamic Schema-Driven Resolver Architecture
status: draft
author: Requirements Analyst
created: 2026-01-08
sprint: Dynamic Schema-Driven Resolver
task: TASK-001
impact: high
impact_categories: [api_contract, data_model]
---

## Executive Summary

Replace the current per-entity resolution strategy pattern with a universal schema-driven resolver that derives resolvable entities from the existing SchemaRegistry. This eliminates hardcoded entity type lists, enables flexible lookup criteria using any schema column, and provides multi-match support across all entity types.

## Problem Statement

### Current State

The existing resolver architecture requires **4+ manual code changes** to add a new resolvable entity type:

1. Add entity to `SUPPORTED_ENTITY_TYPES` set in `api/routes/resolver.py`
2. Create strategy class in `services/resolver.py`
3. Register strategy in `RESOLUTION_STRATEGIES` dictionary
4. Update cache warmer priority list

Additionally:
- Lookup criteria are **fixed per entity type** (Unit: phone+vertical, Contact: email/phone)
- Multi-match support exists only for Contact (special-cased handling)
- The `GidLookupIndex` is **hardcoded** to phone/vertical pairs with canonical key format `pv1:{phone}:{vertical}`
- No mechanism to query which fields are available for a given entity type

### Pain Points

| Pain Point | Impact |
|------------|--------|
| Adding new entity types requires tribal knowledge | Slow onboarding, error-prone changes |
| Fixed lookup fields per entity | Cannot resolve by alternative criteria (e.g., Unit by name+vertical) |
| Single-GID response (except Contact) | Forces callers to handle ambiguity themselves |
| No self-documenting API | Clients must consult external docs for valid fields |

### Technical Debt

The current architecture duplicates information that already exists elsewhere:
- `SchemaRegistry` knows which entity types have schemas
- `ProjectTypeRegistry` knows which entity types have projects
- `DataFrameSchema.column_names()` knows valid fields per entity

This information could drive resolver eligibility dynamically.

---

## User Stories

### US-001: Zero-Touch Entity Registration

**As a** platform developer adding a new entity type
**I want to** have that entity automatically resolvable when I add its schema
**So that** I don't need to update multiple registration points manually

**Acceptance Criteria**:
- [ ] Entity becomes resolvable when schema is registered in SchemaRegistry
- [ ] Entity becomes resolvable when project GID is configured in ProjectTypeRegistry
- [ ] No changes required to `SUPPORTED_ENTITY_TYPES` or `RESOLUTION_STRATEGIES`
- [ ] Resolver route automatically accepts new entity type in path parameter

### US-002: Flexible Lookup Criteria

**As an** API consumer
**I want to** resolve entities using any valid schema column as lookup criteria
**So that** I can find entities using whatever identifier I have available

**Acceptance Criteria**:
- [ ] Any column defined in entity schema can be used as lookup criterion
- [ ] Multiple criteria fields can be combined in a single lookup
- [ ] Criterion fields are validated against entity schema at request time
- [ ] Invalid field names return 422 with list of valid alternatives

### US-003: Multi-Match Support

**As an** API consumer resolving entities where multiple matches are possible
**I want to** receive all matching GIDs in the response
**So that** I can handle disambiguation in my application logic

**Acceptance Criteria**:
- [ ] Response returns `gids` array (plural) containing all matches
- [ ] Response includes `match_count` for explicit count without array iteration
- [ ] Response preserves backwards-compatible `gid` property (first match or null)
- [ ] Multi-match works consistently across all entity types (not just Contact)

### US-004: Self-Documenting Resolution

**As an** API consumer
**I want to** discover which fields are available for lookup
**So that** I can build resolution requests without consulting external documentation

**Acceptance Criteria**:
- [ ] Response `meta` includes `available_fields` listing all schema columns
- [ ] Response `meta` includes `criteria_schema` showing which fields were used
- [ ] OpenAPI schema reflects dynamic field availability

### US-005: Backwards-Compatible Migration

**As an** existing API consumer
**I want** my current resolution requests to continue working unchanged
**So that** I don't need to update my integration immediately

**Acceptance Criteria**:
- [ ] Existing request format (`phone`, `vertical` fields) continues to work
- [ ] Existing response format (`gid` property) continues to work
- [ ] New `gids` and `match_count` fields are additive, not breaking
- [ ] No changes required to existing clients for basic resolution

---

## Functional Requirements

### Must Have (M)

#### FR-001: Dynamic Entity Discovery

The resolver SHALL derive the set of resolvable entities at runtime from SchemaRegistry and ProjectTypeRegistry:

```python
def get_resolvable_entities() -> set[str]:
    """Derive resolvable entities from existing registries."""
    schema_registry = SchemaRegistry.get_instance()
    project_registry = EntityProjectRegistry.get_instance()

    resolvable = set()
    for task_type in schema_registry.list_task_types():
        entity_type = task_type.lower()
        if project_registry.has_project(entity_type):
            resolvable.add(entity_type)

    return resolvable
```

**Rationale**: Eliminates `SUPPORTED_ENTITY_TYPES` hardcoding.

#### FR-002: Schema-Aware Criterion Validation

The resolver SHALL validate criterion fields against the entity's schema:

| Validation | Behavior |
|------------|----------|
| Unknown field | Return 422 with `available_fields` list |
| Type mismatch | Coerce string to target type or return 422 |
| Missing required field | Return 422 with required field list |
| Empty criteria | Return 200 with empty results |

#### FR-003: DynamicIndex Multi-Column Support

The resolver SHALL support indexes on arbitrary column combinations:

```python
@dataclass
class DynamicIndexKey:
    """Composite key for any column combination."""
    columns: tuple[str, ...]
    values: tuple[str, ...]

    @property
    def cache_key(self) -> str:
        """Versioned key: 'idx1:col1=val1:col2=val2'"""
        pairs = ":".join(f"{c}={v}" for c, v in zip(self.columns, self.values))
        return f"idx1:{pairs}"
```

**Index construction**: O(n) scan of DataFrame on first access for column combination.
**Lookup performance**: O(1) hash-based lookup after index construction.

#### FR-004: Multi-Match Response Structure

The resolver SHALL return all matching GIDs in the response:

```json
{
  "results": [
    {
      "gids": ["123", "456"],
      "match_count": 2,
      "gid": "123"
    }
  ],
  "meta": {
    "entity_type": "contact",
    "available_fields": ["gid", "name", "email", "phone", ...],
    "criteria_schema": ["email"]
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `gids` | `array[string]` | Yes | All matching GIDs |
| `match_count` | `integer` | Yes | Number of matches |
| `gid` | `string\|null` | Yes | First match (backwards compatibility) |

#### FR-005: UniversalResolutionStrategy

Create a single strategy class that handles all entity types:

```python
class UniversalResolutionStrategy(ResolutionStrategy):
    """Schema-driven resolution for any entity type."""

    def __init__(
        self,
        entity_type: str,
        schema_registry: SchemaRegistry,
        index_cache: DynamicIndexCache,
    ) -> None: ...

    async def resolve(
        self,
        criteria: dict[str, Any],
    ) -> EnhancedResolutionResult: ...
```

**Replaces**: `UnitResolutionStrategy`, `BusinessResolutionStrategy`, `OfferResolutionStrategy`, `ContactResolutionStrategy`.

#### FR-006: Backwards-Compatible Field Mapping

Maintain compatibility with existing field names:

| Legacy Field | Schema Column | Entity |
|--------------|---------------|--------|
| `phone` | `office_phone` | Unit, Business |
| `vertical` | `vertical` | Unit, Business, Offer |
| `offer_id` | `offer_id` | Offer |
| `contact_email` | `email` | Contact |
| `contact_phone` | `phone` | Contact |

The resolver SHALL accept both legacy and schema field names.

### Should Have (S)

#### FR-007: Index Column Hints

Schemas SHOULD declare which columns are efficient for indexing:

```python
@dataclass
class ColumnDef:
    name: str
    dtype: str
    indexable: bool = False  # New: hint for index optimization
```

Columns marked `indexable: True` are pre-indexed at cache warm time.

#### FR-008: Context Fields Support

The resolver SHOULD support optional context field retrieval:

```json
{
  "criteria": [{"office_phone": "+15551234567", "vertical": "dental"}],
  "context_fields": ["name", "modified_at"]
}
```

Response includes additional fields for each match:

```json
{
  "results": [{
    "gids": ["123"],
    "match_count": 1,
    "context": [{"gid": "123", "name": "Acme Dental", "modified_at": "2026-01-07T..."}]
  }]
}
```

#### FR-009: Deprecate Legacy Strategies

Mark per-entity strategies as deprecated with removal timeline:

- Phase 1: Log deprecation warning when legacy strategy invoked
- Phase 2: Remove strategy classes after 2 release cycles
- Phase 3: Clean up `RESOLUTION_STRATEGIES` dict

### Could Have (C)

#### FR-010: Fuzzy Matching Mode

Support approximate matching for fields like name:

```json
{
  "criteria": [{"name": "Acme Dental"}],
  "match_mode": "fuzzy",
  "threshold": 0.8
}
```

**Deferred**: Requires string similarity index, higher complexity.

#### FR-011: Resolution Audit Trail

Log all resolution attempts with full criteria for debugging:

```json
{
  "event": "resolution_attempt",
  "entity_type": "unit",
  "criteria": {"office_phone": "+15551234567", "vertical": "dental"},
  "result": {"match_count": 1, "gids": ["123"]},
  "latency_ms": 2
}
```

### Won't Have (W)

| Item | Rationale |
|------|-----------|
| Real-time schema reload | Startup discovery sufficient; runtime changes rare |
| GraphQL resolution interface | REST sufficient for current consumers |
| Cross-entity join resolution | Out of scope; use navigation hydration for relationships |
| Resolution confidence scoring | Binary match/no-match sufficient for current needs |

---

## Non-Functional Requirements

### NFR-001: Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| Single criterion lookup (index hit) | < 5ms p95 | Prometheus histogram |
| Index construction (1000 rows) | < 50ms | Startup timing |
| Index construction (100,000 rows) | < 500ms | Startup timing |
| Memory per index (1000 entries) | < 1MB | Memory profiling |

**Constraint**: Maintain O(1) lookup performance via hash-based index.

### NFR-002: Memory Efficiency

| Metric | Target |
|--------|--------|
| Max indexes per entity | 5 (most common column combinations) |
| Index LRU eviction threshold | 10 indexes per entity type |
| Cache TTL for unused indexes | 1 hour |

**Rationale**: Prevent unbounded memory growth from arbitrary column combinations.

### NFR-003: Reliability

| Metric | Target |
|--------|--------|
| Resolution availability | 99.9% (matches API SLA) |
| Graceful degradation | Return error result, not 500, on index miss |
| Schema mismatch handling | Log warning, continue with available columns |

### NFR-004: Extensibility

| Metric | Target |
|--------|--------|
| Code changes for new entity | 0 (add schema + project = resolvable) |
| Time to add new entity type | < 5 minutes |
| Code changes for new lookup field | 0 (schema column = valid criterion) |

---

## API Contract

### Request Schema (Enhanced)

```json
{
  "criteria": [
    {
      "office_phone": "+15551234567",
      "vertical": "dental"
    }
  ],
  "context_fields": ["name", "modified_at"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `criteria` | `array[object]` | Yes | Lookup criteria (max 1000 items) |
| `criteria[*].<field>` | `string` | Varies | Any valid schema column |
| `context_fields` | `array[string]` | No | Additional fields to return with match |

### Response Schema (Enhanced)

```json
{
  "results": [
    {
      "gids": ["1234567890123456"],
      "match_count": 1,
      "gid": "1234567890123456",
      "context": [
        {
          "gid": "1234567890123456",
          "name": "Acme Dental",
          "modified_at": "2026-01-07T10:30:00Z"
        }
      ]
    }
  ],
  "meta": {
    "entity_type": "unit",
    "project_gid": "1201081073731555",
    "resolved_count": 1,
    "unresolved_count": 0,
    "available_fields": ["gid", "name", "office_phone", "vertical", "mrr", "..."],
    "criteria_schema": ["office_phone", "vertical"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `results[*].gids` | `array[string]` | All matching GIDs |
| `results[*].match_count` | `integer` | Number of matches |
| `results[*].gid` | `string\|null` | First match (backwards compat) |
| `results[*].context` | `array[object]` | Optional context for each match |
| `meta.available_fields` | `array[string]` | Valid fields for this entity |
| `meta.criteria_schema` | `array[string]` | Fields used in this request |

### Error Response (422 - Invalid Criterion)

```json
{
  "detail": "Invalid criterion field 'foo' for entity type 'unit'",
  "error_code": "INVALID_CRITERION_FIELD",
  "available_fields": ["gid", "name", "office_phone", "vertical", "mrr", "..."]
}
```

---

## Edge Cases

| Case | Expected Behavior |
|------|------------------|
| Unknown entity type | 404 with dynamically-generated list of valid types |
| Unknown criterion field | 422 with `available_fields` list |
| Empty criteria array | 200 with empty results |
| No matches for criterion | Result with `gids: []`, `match_count: 0`, `gid: null` |
| Multiple matches | Return all in `gids`, first in `gid` |
| Schema column renamed | Legacy field mapping provides compatibility |
| Index not cached for column combo | Build index on-demand, cache for future |
| Index cache evicted | Rebuild from DataFrame cache (may add latency) |
| Entity has schema but no project | Entity not in resolvable set |
| Entity has project but no schema | Entity not in resolvable set |
| Concurrent index construction | Lock prevents duplicate work |

---

## Success Criteria

### Functional Success

- [ ] All 4 current entity types (unit, business, offer, contact) resolvable via UniversalResolutionStrategy
- [ ] Adding new entity type requires only schema + project registration
- [ ] Any schema column usable as lookup criterion
- [ ] Multi-match response works for all entity types
- [ ] Backwards-compatible `gid` property present in all responses
- [ ] Schema-aware validation returns helpful error messages

### Performance Success

- [ ] Single lookup latency < 5ms p95
- [ ] No regression from current resolver performance
- [ ] Index construction completes within startup timeout

### Migration Success

- [ ] All existing tests pass without modification
- [ ] Existing S2S integrations work without client changes
- [ ] Legacy strategies deprecated with clear migration path

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| Platform SDK extraction (`autom8y-frame`) | Phase 2 per SPIKE-platform-schema-lookup-abstraction |
| Cross-satellite resolution | Requires service mesh, out of scope for this sprint |
| Real-time cache invalidation | TTL-based refresh sufficient for current needs |
| Resolution strategy plugins | UniversalResolutionStrategy handles all cases |
| WebSocket streaming for large batches | Batch API with 1000 limit sufficient |
| Full-text search on text fields | Deferred to FR-010 fuzzy matching |

---

## Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| SchemaRegistry | Implemented | Provides entity schemas |
| ProjectTypeRegistry | Implemented | Provides entity-to-project mapping |
| DataFrameCache | Implemented | Provides cached DataFrames for indexing |
| GidLookupIndex | Implemented | Base pattern for DynamicIndex |
| S2S JWT validation | Implemented | Authentication unchanged |

---

## Traceability

| Requirement | Source |
|-------------|--------|
| FR-001 | SPIKE-dynamic-resolver-architecture: Dynamic Entity Discovery |
| FR-002 | SPIKE-dynamic-resolver-architecture: Schema-Aware Criterion Validation |
| FR-003 | SPIKE-dynamic-resolver-architecture: DynamicIndex |
| FR-004 | SPIKE-dynamic-resolver-architecture: EnhancedResolutionResult |
| FR-005 | SPIKE-dynamic-resolver-architecture: UniversalResolutionStrategy |
| NFR-001 | Existing PRD-entity-resolver performance targets |
| NFR-002 | SPIKE-dynamic-resolver-architecture: LRU cache recommendation |

---

## Appendix A: Current vs. Proposed Architecture

### Current Architecture

```
POST /v1/resolve/{entity_type}
         │
         ▼
┌──────────────────────┐
│ SUPPORTED_ENTITY_TYPES │ ◀── Hardcoded set
│ {"unit", "business",   │
│  "offer", "contact"}   │
└──────────┬─────────────┘
           │
           ▼
┌──────────────────────────┐
│ RESOLUTION_STRATEGIES    │ ◀── Dict of strategy classes
│ {"unit": UnitStrategy,   │
│  "business": BizStrategy}│
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Entity-Specific Strategy │ ◀── One class per entity
│ - Fixed lookup fields    │
│ - Entity-specific logic  │
└──────────────────────────┘
```

### Proposed Architecture

```
POST /v1/resolve/{entity_type}
         │
         ▼
┌─────────────────────────────────┐
│ get_resolvable_entities()       │
│ SchemaRegistry + ProjectRegistry│ ◀── Dynamic discovery
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ UniversalResolutionStrategy     │ ◀── Single strategy class
│ - Schema-driven validation      │
│ - Dynamic column indexing       │
│ - Multi-match support           │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ DynamicIndexCache               │
│ - Per-column-combo indexes      │
│ - LRU eviction                  │
│ - O(1) lookup                   │
└─────────────────────────────────┘
```

---

## Appendix B: Migration Path

### Phase 1: Foundation (Week 1)

1. Implement `DynamicIndex` with multi-column support
2. Implement `DynamicIndexKey` with versioned cache keys
3. Add `EnhancedResolutionResult` with backwards-compatible `gid` property
4. Create schema-aware criterion validation

### Phase 2: Universal Strategy (Week 2)

1. Implement `UniversalResolutionStrategy`
2. Add `get_resolvable_entities()` function
3. Migrate Unit resolution to UniversalResolutionStrategy
4. Add deprecation warnings to legacy strategies

### Phase 3: Complete Migration (Week 3)

1. Migrate remaining entities (Business, Offer, Contact)
2. Add `context_fields` support
3. Remove `SUPPORTED_ENTITY_TYPES` constant
4. Update OpenAPI schema with dynamic fields
5. Remove deprecated strategy classes

---

## Appendix C: Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Performance regression | Low | High | Index caching with same TTL as current; benchmark before/after |
| Breaking existing clients | Low | High | Backwards-compatible response (preserve `gid` property) |
| Schema column explosion | Medium | Medium | LRU cache eviction; document recommended indexed columns |
| Index memory growth | Medium | Medium | LRU cache per (entity, column_combo); configurable limits |
| Discovery timing issues | Low | Medium | Fail-fast at startup if discovery incomplete |
