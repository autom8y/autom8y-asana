# SPIKE: Platform-Level Schema-Driven Lookup Abstraction

> **Status**: Complete
> **Date**: 2026-01-08
> **Author**: Claude (assisted research)
> **Follows**: SPIKE-dynamic-resolver-architecture.md

## Question & Context

### Questions

1. **Platform Extraction Opportunity**: Given that `autom8_cache` already provides centralized caching primitives imported by autom8_asana, should we extract schema-driven DataFrame lookup patterns to the platform level?

2. **Cross-Satellite Applicability**: Can the same abstraction serve both autom8_asana (Asana project lookups) and autom8_data (database analytics lookups)?

### Context

The user observed:
- `autom8_asana` already imports caching primitives from `autom8y/sdks/python/autom8y-cache`
- `autom8_data` service performs database queries for account analytics with similar lookup needs
- Both services need schema-aware data retrieval with flexible query criteria

### Decision This Informs

Whether to:
1. Build the dynamic resolver locally in autom8_asana
2. Extract to `autom8y-cache` SDK for cross-satellite reuse
3. Create a new `autom8y-frame` SDK for DataFrame-specific operations

---

## Research Findings

### Current Platform SDK Inventory

| SDK | Purpose | Extraction Status |
|-----|---------|-------------------|
| `autom8y-cache` | Tiered caching (Memory/Redis/S3), resource versioning | Production |
| `autom8y-http` | Rate limiting, circuit breakers, resilient clients | Production |
| `autom8y-log` | Structured logging protocol | Production |
| `autom8y-config` | Pydantic settings, env var management | Production |
| `autom8y-auth` | JWT validation, service tokens | Production |
| `autom8y-telemetry` | OpenTelemetry integration | Beta |

**Key Pattern**: Platform SDKs follow the "circular extraction" model - primitives are first built in a satellite, proven in production, then extracted to the platform for cross-satellite reuse. (Per TDD-PRIMITIVE-MIGRATION-001)

### Comparison: autom8_asana vs autom8_data Query Patterns

| Aspect | autom8_asana | autom8_data |
|--------|-------------|-------------|
| **Data Source** | Asana API → Polars DataFrame | MySQL/DuckDB → Polars DataFrame |
| **Schema Definition** | `DataFrameSchema` + `ColumnDef` | `Dimension` + `Metric` + `JoinDefinition` |
| **Registry Pattern** | `SchemaRegistry` singleton | `MetricRegistry` singleton |
| **Lookup Index** | `GidLookupIndex` (phone/vertical → GID) | QueryBuilder (dimension filter → rows) |
| **Caching** | Memory → S3 (Parquet) | Redis → DuckDB (materialized views) |
| **Query Interface** | `ResolutionCriterion` (fixed fields) | `QueryBuilder.select().where()` (flexible) |

### Architectural Similarities

```
autom8_asana                          autom8_data
------------                          -----------

DataFrameSchema                       MetricRegistry
    |                                     |
    |  ColumnDef                          |  Dimension + Metric
    |  - name                             |  - name
    |  - dtype                            |  - table
    |  - source                           |  - column
    |  - nullable                         |  - sql_column
    v                                     v

SchemaRegistry                        MetricRegistry
    |                                     |
    |  get_schema(entity_type)            |  get_dimension(name)
    |  list_task_types()                  |  get_metric(name)
    v                                     v

DataFrame (Polars)                    DataFrame (Polars)
    |                                     |
    |  columns defined by schema          |  columns defined by dimensions
    v                                     v

GidLookupIndex                        QueryBuilder.execute()
    |                                     |
    |  from_dataframe(df, key_cols)       |  .select([dims]).where(filter)
    |  lookup(criteria) → GIDs            |  → DataFrame rows
    v                                     v

ResolutionResult                      QueryResult
    - gid                                 - rows
    - error                               - metadata
```

### Key Insight: Common Abstraction Layer

Both systems share a core pattern:

```
Schema Definition → DataFrame → Indexed Lookup → Result
```

The differences are:
- **Schema source**: Static definition (asana) vs. ORM introspection (data)
- **Data source**: API polling (asana) vs. database query (data)
- **Index type**: Hash map (asana, O(1)) vs. SQL WHERE (data, O(log n) with index)

---

## Extractable Components

### Tier 1: Immediately Extractable (Low Risk)

| Component | Current Location | Platform Target | Notes |
|-----------|------------------|-----------------|-------|
| `ColumnDef` dataclass | `autom8_asana/dataframes/models/schema.py` | `autom8y-cache/schema.py` | Already generic |
| `DataFrameSchema` | `autom8_asana/dataframes/models/schema.py` | `autom8y-cache/schema.py` | Remove Polars-specific methods |
| `SchemaRegistry` singleton | `autom8_asana/dataframes/models/registry.py` | `autom8y-cache/registry.py` | Generic pattern |

### Tier 2: Needs Adaptation (Medium Risk)

| Component | Current Location | Challenge | Recommended Approach |
|-----------|------------------|-----------|---------------------|
| `DynamicIndex` (proposed) | N/A (new) | Generic enough for both? | Build in autom8_asana first, extract later |
| DataFrame caching | `autom8_asana/cache/dataframe_cache.py` | Polars-specific | Create `DataFrameCacheProtocol` |
| Progressive builder | `autom8_asana/dataframes/builders/` | Data-source agnostic? | Too coupled to Asana API |

### Tier 3: Satellite-Specific (Don't Extract)

| Component | Location | Reason |
|-----------|----------|--------|
| Entity models (Business, Unit, etc.) | `autom8_asana/models/business/` | Domain-specific |
| Resolution strategies | `autom8_asana/services/resolver.py` | Asana-specific lookup logic |
| MetricRegistry composite metrics | `autom8_data/analytics/` | Database query semantics |
| QueryBuilder | `autom8_data/analytics/` | SQL generation, too specialized |

---

## Proposed Platform Architecture

### New SDK: `autom8y-frame` (Future)

Rather than overloading `autom8y-cache`, a dedicated SDK for DataFrame operations:

```
autom8y/sdks/python/autom8y-frame/
  src/autom8y_frame/
    __init__.py
    schema.py           # ColumnDef, DataFrameSchema, DataFrameSchemaProtocol
    registry.py         # SchemaRegistry (generic singleton pattern)
    index.py            # DynamicIndex (generic O(1) lookup)
    protocols/
      __init__.py
      schema.py         # SchemaProvider protocol
      lookup.py         # LookupIndexProtocol
    cache/
      __init__.py
      entry.py          # DataFrameCacheEntry (schema-versioned)
      provider.py       # DataFrameCacheProvider (Parquet-aware)
```

### Protocol Definitions

```python
# autom8y_frame/protocols/schema.py

@runtime_checkable
class SchemaProvider(Protocol):
    """Protocol for schema registries across satellites."""

    def get_schema(self, schema_name: str) -> DataFrameSchema:
        """Get schema by name."""
        ...

    def list_schemas(self) -> list[str]:
        """List all registered schema names."""
        ...

    def has_schema(self, schema_name: str) -> bool:
        """Check if schema exists."""
        ...
```

```python
# autom8y_frame/protocols/lookup.py

@runtime_checkable
class LookupIndexProtocol(Protocol):
    """Protocol for O(1) DataFrame lookup indexes."""

    def lookup(
        self,
        criteria: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Look up rows matching criteria."""
        ...

    def available_columns(self) -> list[str]:
        """Return indexable column names."""
        ...

    @classmethod
    def from_dataframe(
        cls,
        df: Any,  # pl.DataFrame or pd.DataFrame
        key_columns: list[str],
        value_columns: list[str] | None = None,
    ) -> Self:
        """Build index from DataFrame."""
        ...
```

### Satellite Integration Pattern

```
autom8_asana                          autom8_data
------------                          -----------

Uses autom8y-frame:                   Uses autom8y-frame:
- DataFrameSchema                     - DataFrameSchema (wraps Dimension)
- SchemaRegistry                      - SchemaRegistry (wraps MetricRegistry)
- DynamicIndex                        - DynamicIndex (supplements QueryBuilder)

Satellite-specific:                   Satellite-specific:
- AsanaClient                         - DuckDB connection
- EntityProjectRegistry               - MetricRegistry (composite metrics)
- GidLookupIndex extends DynamicIndex - QueryBuilder (SQL generation)
```

---

## Immediate Opportunity: autom8_data Integration

### Current State

`autom8_data` already has the concepts but different names:

| autom8_asana | autom8_data | Generalization |
|--------------|-------------|----------------|
| `ColumnDef` | `Dimension` | `ColumnDefinition` |
| `DataFrameSchema` | N/A (implicit) | `DataFrameSchema` |
| `SchemaRegistry` | `MetricRegistry` | `SchemaProvider` protocol |
| `GidLookupIndex` | `QueryBuilder` | `LookupIndexProtocol` |

### Integration Path

1. **Phase 1**: Build `DynamicIndex` in autom8_asana (this spike's recommendation)
2. **Phase 2**: Extract to `autom8y-frame` when pattern is proven
3. **Phase 3**: `autom8_data` adopts `autom8y-frame` for cached dimension lookups
4. **Phase 4**: Both satellites use common protocols, different implementations

### Concrete Benefit for autom8_data

`autom8_data` could use `DynamicIndex` for:
- Cached dimension value lookups (e.g., business_name → business_id)
- Pre-computed aggregation lookups (e.g., offer_id → CPS metrics)
- Vertical-specific metric caching

Example:
```python
# autom8_data integration (hypothetical)
from autom8y_frame import DynamicIndex

# Cache vertical CPS metrics
cps_index = DynamicIndex.from_dataframe(
    df=cps_materialized_view,
    key_columns=["vertical", "date"],
    value_columns=["cps", "ad_spend", "appointments"],
)

# O(1) lookup instead of SQL query
result = cps_index.lookup({"vertical": "chiropractic", "date": "2026-01-08"})
```

---

## Comparison Matrix

| Approach | Effort | Risk | Cross-Satellite Value | Recommendation |
|----------|--------|------|----------------------|----------------|
| Build locally in autom8_asana | Low | Low | None | **Phase 1 (Now)** |
| Add to autom8y-cache | Medium | Medium | Limited (cache-adjacent) | Not recommended |
| Create autom8y-frame SDK | High | Medium | High | **Phase 2 (Proven pattern)** |
| Direct autom8_data integration | Medium | Low | Immediate | **Phase 3 (After SDK)** |

---

## Recommendation

### Phased Approach

**Phase 1: Local Implementation (2-3 weeks)**
- Build `DynamicIndex` and schema-driven resolver in autom8_asana
- Prove the pattern works for Asana entity resolution
- No platform SDK changes

**Phase 2: Platform Extraction (1-2 weeks, after Phase 1)**
- Extract proven components to new `autom8y-frame` SDK
- Define `SchemaProvider` and `LookupIndexProtocol` protocols
- Keep satellite-specific logic in satellites

**Phase 3: autom8_data Adoption (1 week)**
- `autom8_data` adopts `autom8y-frame` for dimension caching
- MetricRegistry implements `SchemaProvider` protocol
- QueryBuilder uses `DynamicIndex` for hot-path dimension lookups

### Why This Order?

1. **Circular extraction pattern**: Platform SDKs should be extracted from proven satellite implementations, not designed speculatively.

2. **Risk mitigation**: Building locally first isolates risk to one satellite.

3. **Immediate value**: autom8_asana gets the resolver improvement now, without waiting for platform work.

4. **Cross-satellite validation**: Extracting to platform only after proving the pattern works in production.

---

## Follow-Up Actions

1. **Proceed with SPIKE-dynamic-resolver-architecture recommendations** - Build `DynamicIndex` in autom8_asana first

2. **Tag extraction candidates** - Mark files in autom8_asana that are generic enough for later extraction

3. **Draft autom8y-frame PRD** - After Phase 1 is complete, write requirements for platform SDK

4. **autom8_data stakeholder review** - Validate that `DynamicIndex` would be useful for analytics caching

---

## Key Insight

> "The platform SDK is designed for **resource versioning** (staleness detection against source APIs), not **schema versioning** (data structure compatibility)."
> — ARCH-spike-centralized-schema-validation.md

This principle guides where to draw the line:

| Belongs in Platform SDK | Belongs in Satellite |
|------------------------|---------------------|
| Generic schema definition (`ColumnDef`) | Entity models (Business, Unit) |
| Schema registry pattern | Entity-specific extractors |
| Index protocols | Resolution strategies |
| Cache entry patterns | API client integration |
| Polars-agnostic interfaces | Polars-specific optimizations |

The dynamic resolver itself is satellite-specific because it encodes domain knowledge about entity relationships. The *primitives* it uses (schema, index, cache) can be platform-level.

---

## References

- [SPIKE-dynamic-resolver-architecture.md](./SPIKE-dynamic-resolver-architecture.md) - Phase 1 design
- [ARCH-spike-centralized-schema-validation.md](../design/ARCH-spike-centralized-schema-validation.md) - Platform boundary analysis
- [ADR-0063-platform-concurrency-extraction.md](../decisions/ADR-0063-platform-concurrency-extraction.md) - Extraction precedent
- [TDD-PRIMITIVE-MIGRATION-001.md](../architecture/TDD-PRIMITIVE-MIGRATION-001.md) - Migration pattern
- [autom8_data ARCHITECTURE.md](/Users/tomtenuta/Code/autom8_data/ARCHITECTURE.md) - Analytics layer design
