# SPIKE: Dynamic Entity Discovery & Schema-Driven Resolution

> **Status**: Complete
> **Date**: 2026-01-08
> **Author**: Claude (assisted research)

## Question & Context

### Questions

1. **Dynamic Entity Discovery**: Can we eliminate `SUPPORTED_ENTITY_TYPES` hardcoding by using runtime discovery from the business model hierarchy?

2. **Schema-Driven Resolution Criteria**: Can resolution criteria be derived from DataFrame schemas, allowing any indexed column to be a valid lookup parameter?

### Context

The current resolution system has friction points that require tribal knowledge:

- **Entity registration**: Adding a new resolvable entity type requires manual changes to:
  - `SUPPORTED_ENTITY_TYPES` set in `api/routes/resolver.py`
  - `RESOLUTION_STRATEGIES` dict in `services/resolver.py`
  - Strategy class implementation
  - Cache warmer priority list

- **Fixed criteria fields**: Each entity type has hardcoded lookup fields:
  - Unit: `phone` + `vertical`
  - Contact: `email` OR `phone`
  - Offer: `offer_id` OR `phone/vertical/offer_name`

- **Single-GID response**: Current API returns single GID or `NOT_FOUND`, but multi-match scenarios (like Contact) need richer responses.

### Decision This Informs

Whether to evolve the resolution service from:
- **Current**: Strategy-per-entity with fixed criteria fields
- **Target**: Universal schema-driven resolver with dynamic criteria

---

## Research Findings

### Current Architecture Analysis

#### Registration Chain (4 Manual Steps)

```
1. EntityType enum (detection/types.py)
   ↓
2. ENTITY_MODELS list (_bootstrap.py)
   ↓
3. SUPPORTED_ENTITY_TYPES (routes/resolver.py)
   ↓
4. RESOLUTION_STRATEGIES dict (services/resolver.py)
   ↓
5. Strategy class implementation
```

**Key Insight**: Steps 1-2 already exist for model registration. Steps 3-5 are duplicative and could be derived.

#### Existing Discovery Infrastructure

The codebase already has sophisticated discovery mechanisms:

| Component | Location | Function |
|-----------|----------|----------|
| `EntityType` enum | `detection/types.py` | All entity types defined |
| `ProjectTypeRegistry` | `registry.py` | Project GID → EntityType mapping |
| `SchemaRegistry` | `dataframes/models/registry.py` | Task type → DataFrame schema |
| `_bootstrap.py` | `models/business/` | Model-first registration |

**Key Insight**: SchemaRegistry + ProjectTypeRegistry already know which entity types have schemas and projects. This information can drive resolution eligibility.

#### GidLookupIndex Limitations

Current `GidLookupIndex` (services/gid_lookup.py:21-299) is hardcoded to phone/vertical:

```python
# Hardcoded to phone/vertical
required_columns = {"office_phone", "vertical", "gid"}
canonical_key = f"pv1:{phone}:{vertical}"
```

### Industry Patterns Research

Based on [schema-driven API design patterns](https://www.apollographql.com/docs/technotes/TN0027-demand-oriented-schema-design):

1. **GraphQL's Introspective Schema**: Schema is queryable at runtime, clients discover what's available without external documentation.

2. **Dynamic Schema Registration** ([Netflix DGS Framework](https://netflix.github.io/dgs/advanced/dynamic-schemas/)): TypeDefinitionRegistry allows mixing static schemas with dynamic parts, enabling systems that can rewire their API based on external signals.

3. **Demand-Oriented Design**: Design schemas to support actual client use cases rather than mirroring internal data models.

---

## Proposed Architecture

### Option A: Schema-Driven Universal Resolver (Recommended)

#### Core Concept

Replace per-entity strategies with a single `UniversalResolutionStrategy` that:
1. Discovers resolvable entities from SchemaRegistry
2. Builds indexes dynamically from schema column definitions
3. Accepts any schema column as lookup criteria

#### Architecture

```
                    ┌─────────────────────────────────┐
                    │   POST /v1/resolve/{entity}     │
                    │   ?criteria={any_schema_cols}   │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │    UniversalResolutionStrategy  │
                    │                                 │
                    │  1. Check SchemaRegistry        │
                    │  2. Validate criteria vs schema │
                    │  3. Build/use DynamicIndex      │
                    └──────────────┬──────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
┌─────────▼─────────┐  ┌──────────▼──────────┐  ┌─────────▼─────────┐
│   SchemaRegistry  │  │   DynamicIndexCache │  │  DataFrameCache   │
│                   │  │                     │  │                   │
│ entity → columns  │  │ (entity, cols) →    │  │ entity → df       │
│                   │  │    lookup dict      │  │                   │
└───────────────────┘  └─────────────────────┘  └───────────────────┘
```

#### Key Components

**1. Schema-Driven Entity Discovery**

```python
def get_resolvable_entities() -> set[str]:
    """Derive resolvable entities from SchemaRegistry + ProjectRegistry."""
    schema_registry = SchemaRegistry.get_instance()
    project_registry = EntityProjectRegistry.get_instance()

    resolvable = set()
    for task_type in schema_registry.list_task_types():
        entity_type = task_type.lower()  # "Unit" → "unit"
        if project_registry.has_project(entity_type):
            resolvable.add(entity_type)

    return resolvable  # Dynamic, no hardcoding
```

**2. Dynamic Index Builder**

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

class DynamicIndex:
    """Generic O(1) lookup index for any column combination."""

    @classmethod
    def from_dataframe(
        cls,
        df: pl.DataFrame,
        key_columns: list[str],
        value_column: str = "gid",
    ) -> DynamicIndex:
        """Build index for arbitrary column combination."""
        # Validate columns exist
        missing = set(key_columns) - set(df.columns)
        if missing:
            raise KeyError(f"Columns not in schema: {missing}")

        # Build lookup dict with composite keys
        lookup: dict[str, list[str]] = defaultdict(list)
        for row in df.iter_rows(named=True):
            key = DynamicIndexKey(
                columns=tuple(key_columns),
                values=tuple(str(row[c]).lower() for c in key_columns),
            )
            lookup[key.cache_key].append(row[value_column])

        return cls(lookup_dict=lookup)

    def lookup(self, criteria: dict[str, str]) -> list[str]:
        """Return all matching GIDs (supports multi-match)."""
        key = DynamicIndexKey(
            columns=tuple(sorted(criteria.keys())),
            values=tuple(str(criteria[k]).lower() for k in sorted(criteria.keys())),
        )
        return self._lookup.get(key.cache_key, [])
```

**3. Enhanced Resolution Response**

```python
@dataclass
class EnhancedResolutionResult:
    """Rich resolution result supporting multi-match."""
    gids: list[str]  # All matches (not just first)
    match_count: int
    match_context: list[dict[str, Any]] | None = None  # (gid, name, modified_at)
    error: str | None = None

    @property
    def is_unique(self) -> bool:
        return self.match_count == 1

    @property
    def gid(self) -> str | None:
        """Backwards-compatible single GID (first match or None)."""
        return self.gids[0] if self.gids else None
```

**4. Schema-Aware Criterion Validation**

```python
def validate_criterion_for_entity(
    entity_type: str,
    criterion: dict[str, Any],
) -> list[str]:
    """Validate criterion fields against schema."""
    schema = SchemaRegistry.get_instance().get_schema(entity_type.title())
    schema_columns = set(schema.column_names())

    errors = []
    for field in criterion.keys():
        if field not in schema_columns:
            errors.append(
                f"Field '{field}' not in {entity_type} schema. "
                f"Available: {sorted(schema_columns)}"
            )

    return errors
```

#### API Changes

**Before** (current):
```json
POST /v1/resolve/unit
{
  "criteria": [{"phone": "+15551234567", "vertical": "dental"}]
}
Response: {"results": [{"gid": "123"}], "meta": {...}}
```

**After** (proposed):
```json
POST /v1/resolve/unit
{
  "criteria": [{"office_phone": "+15551234567", "vertical": "dental"}],
  "context_fields": ["name", "modified_at"]  // Optional
}
Response: {
  "results": [
    {
      "gids": ["123"],
      "match_count": 1,
      "context": [{"gid": "123", "name": "Acme Dental", "modified_at": "2026-01-07T..."}]
    }
  ],
  "meta": {
    "entity_type": "unit",
    "criteria_schema": ["office_phone", "vertical"],
    "available_fields": ["gid", "name", "office_phone", "vertical", "mrr", ...]
  }
}
```

#### Benefits

| Benefit | Impact |
|---------|--------|
| Zero manual registration | Add schema + project GID = resolvable |
| Arbitrary lookup criteria | Any schema column usable |
| Multi-match support | Contact-style multiple matches for all entities |
| Self-documenting | Available fields returned in meta |
| Backwards compatible | Keep `gid` property for single-match |

---

### Option B: Enhanced Registry Pattern (Lower Effort)

Keep per-entity strategies but auto-register based on schema presence.

```python
def auto_register_strategies() -> None:
    """Auto-register strategies for entities with schemas."""
    schema_registry = SchemaRegistry.get_instance()

    for task_type in schema_registry.list_task_types():
        entity_type = task_type.lower()
        if entity_type not in RESOLUTION_STRATEGIES:
            # Create generic strategy for new entity types
            RESOLUTION_STRATEGIES[entity_type] = GenericResolutionStrategy(
                entity_type=entity_type,
                schema=schema_registry.get_schema(task_type),
            )
```

**Pros**: Lower effort, incremental migration
**Cons**: Still requires defining lookup fields per entity

---

## Comparison Matrix

| Aspect | Current | Option A (Universal) | Option B (Auto-Register) |
|--------|---------|---------------------|-------------------------|
| Add new entity | 4 manual steps | Add schema only | 2 manual steps |
| Lookup flexibility | Fixed per entity | Any schema column | Fixed per entity |
| Multi-match support | Contact only | All entities | Per strategy |
| Backwards compatible | N/A | Yes (gid property) | Yes |
| Implementation effort | N/A | High (2-3 weeks) | Medium (1 week) |
| Schema evolution | Manual sync | Automatic | Semi-automatic |
| Self-documenting API | No | Yes (meta.available_fields) | No |

---

## Recommendation

**Implement Option A (Schema-Driven Universal Resolver)** with phased rollout:

### Phase 1: Foundation (Week 1)
- Implement `DynamicIndex` with multi-column support
- Add `EnhancedResolutionResult` with backwards-compatible `gid` property
- Schema-aware criterion validation

### Phase 2: Migration (Week 2)
- Create `UniversalResolutionStrategy`
- Auto-discover resolvable entities from SchemaRegistry
- Deprecate `SUPPORTED_ENTITY_TYPES` constant
- Migrate Unit → Universal (preserve phone/vertical as defaults)

### Phase 3: Enhancement (Week 3)
- Add `context_fields` support for rich responses
- Migrate remaining entities (Contact, Offer, Business)
- Remove legacy per-entity strategies
- Document dynamic resolution in OpenAPI schema

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Performance regression | Index caching with same TTL as current |
| Breaking existing clients | Backwards-compatible response (gid property) |
| Schema column explosion | Document recommended indexed columns |
| Index memory growth | LRU cache per (entity, column_combo) |

---

## Follow-Up Actions

1. **PRD**: Write PRD-dynamic-resolver-architecture.md for formal requirements
2. **TDD**: Create TDD-dynamic-resolver-architecture.md with interface contracts
3. **ADR**: Document decision to move from per-entity to schema-driven resolution
4. **Schema Update**: Add `indexable: bool` flag to ColumnDef for explicit opt-in

---

## References

- [Apollo GraphQL: Demand-Oriented Schema Design](https://www.apollographql.com/docs/technotes/TN0027-demand-oriented-schema-design)
- [Netflix DGS: Dynamic Schemas](https://netflix.github.io/dgs/advanced/dynamic-schemas/)
- [GraphQL vs REST in 2025](https://api7.ai/blog/graphql-vs-rest-api-comparison-2025)
- Current TDD: `docs/design/TDD-entity-resolver.md`
- Schema Registry: `src/autom8_asana/dataframes/models/registry.py`
