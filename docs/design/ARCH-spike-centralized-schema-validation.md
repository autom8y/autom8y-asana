---
artifact_id: ARCH-spike-001
title: "Architectural Spike: Centralized Schema Validation at Platform SDK Level"
created_at: "2026-01-07T00:00:00Z"
author: architect
status: completed
complexity: SYSTEM
related_adrs:
  - ADR-0064-cascade-persistence-layer-alignment
  - ADR-0063-platform-concurrency-extraction
schema_version: "1.0"
---

# Architectural Spike: Centralized Schema Validation at Platform SDK Level

## Executive Summary

Following ADR-0064, we investigated whether schema version validation could be centralized in the Platform SDK (`autom8y_cache`) rather than implemented at the application layer (`autom8_asana`).

**Conclusion**: The Platform SDK is designed for **resource versioning** (staleness detection against source APIs), not **schema versioning** (data structure compatibility). Pushing schema validation down to the SDK would violate separation of concerns and couple the platform to satellite-specific domain concepts.

**Recommendation**: Implement schema version validation at the application layer as proposed in ADR-0064, with a clear understanding of the architectural boundaries between platform and satellite responsibilities.

---

## Analysis Scope

### Codebases Explored

| Location | Component | Purpose |
|----------|-----------|---------|
| `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/` | Platform SDK | Shared caching primitives |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/` | Satellite Cache | Application-specific caching |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/` | DataFrame Layer | Schema-aware data transformation |

---

## Platform SDK Inventory

### 1. autom8y-cache Module Structure

```
autom8y/sdks/python/autom8y-cache/src/autom8y_cache/
|-- __init__.py           # Factory and exports
|-- entry.py              # CacheEntry with version datetime
|-- freshness.py          # STRICT/EVENTUAL/IMMEDIATE modes
|-- protocols/
|   |-- cache.py          # CacheProvider protocol
|   |-- upgrade.py        # CompletenessUpgrader protocol
|-- backends/
|   |-- memory.py         # InMemoryCacheProvider
|   |-- redis.py          # RedisCacheProvider
|   |-- s3.py             # S3CacheProvider
|-- tiered.py             # TieredCacheProvider (hot+cold)
|-- completeness.py       # CompletenessLevel tracking
|-- hierarchy.py          # HierarchyTracker for parent-child
|-- batch.py              # ModificationCheckCache
|-- metrics.py            # CacheMetrics
|-- settings.py           # CacheSettings, TTLSettings
```

### 2. Existing Version Tracking in SDK

The SDK's `CacheEntry` has a `version` field, but it tracks **resource freshness**, not schema compatibility:

```python
@dataclass(frozen=True)
class CacheEntry:
    key: str
    data: dict[str, Any]
    entry_type: str
    version: datetime        # <-- Resource modified_at timestamp
    cached_at: datetime
    ttl: int | None = 300
    project_gid: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Key methods**:
- `is_current(current_version: datetime) -> bool` - Compares cached vs source timestamp
- `is_stale(current_version: datetime) -> bool` - Inverse of is_current
- `is_expired(now: datetime) -> bool` - TTL-based expiration

**Critical insight**: The SDK's `version` is a **datetime** comparing against API `modified_at`. It answers "Is my cached data as fresh as the source?" not "Is my cached data structurally compatible with current code?"

### 3. SDK Extension Points

| Extension Point | Purpose | Schema Validation Fit |
|-----------------|---------|----------------------|
| `metadata: dict[str, Any]` | Arbitrary key-value storage | Could store schema_version |
| `entry_type: str` | Type classification | Domain-specific, not schema |
| `CompletenessUpgrader` protocol | Fetch missing fields | Upgrades data, not schema |
| `Freshness` enum | Validation strictness | Resource freshness, not schema |

---

## Gap Analysis

### What the SDK Provides (Resource Versioning)

```
API Source                 Cache Layer
----------                 -----------
modified_at: 2026-01-07    version: 2026-01-06
         |                         |
         +-------- Compare --------+
                     |
                 "Stale!" -> Refetch from API
```

The SDK excels at detecting when **cached data is older than source data**.

### What the Application Needs (Schema Versioning)

```
Code (SchemaRegistry)      Cache Layer (S3 Parquet)
---------------------      ----------------------
UNIT_SCHEMA.version:       entry.schema_version:
  "1.1.0"                    "1.0.0"
         |                         |
         +-------- Compare --------+
                     |
         "Incompatible!" -> Rebuild DataFrame
                           (different column structure)
```

The application needs to detect when **cached data is structurally incompatible with current code**, regardless of how fresh it is relative to the API.

### The Conceptual Mismatch

| Aspect | Resource Version (SDK) | Schema Version (App) |
|--------|----------------------|---------------------|
| **Question** | "Is this data current?" | "Is this data usable?" |
| **Comparison** | Cache timestamp vs API timestamp | Cache schema vs code schema |
| **Scope** | Per-entity freshness | Per-entity-type compatibility |
| **Source of truth** | External API | Local code (SchemaRegistry) |
| **Failure mode** | Stale data (functional) | Corrupt data (broken) |

---

## Design Options

### Option 1: Envelope Pattern in SDK (Rejected)

**Approach**: Add a `schema_version: str` field to SDK's `CacheEntry`.

```python
# autom8y_cache/entry.py
@dataclass(frozen=True)
class CacheEntry:
    # ... existing fields ...
    schema_version: str | None = None  # NEW
```

**Pros**:
- Single enforcement point
- All SDK consumers benefit
- Consistent pattern

**Cons**:
- **Violates separation of concerns**: SDK should not know about schema versioning
- **Couples platform to satellite concepts**: SchemaRegistry is satellite-specific
- **No source of truth at SDK level**: Where does the SDK get "expected" schema version?
- **Breaks backward compatibility**: Requires all satellites to adopt
- **Over-engineering**: Schema versioning is a satellite concern

**Tradeoff Analysis**:
- Risk: HIGH - SDK changes affect all consumers
- Value: LOW - Only autom8_asana needs this currently
- Reversibility: LOW - SDK API changes are hard to undo

**Verdict**: REJECTED - Wrong layer of abstraction

### Option 2: Metadata Convention (Considered)

**Approach**: Use SDK's `metadata` field with a conventional key.

```python
entry = CacheEntry(
    key="task:12345",
    data={"name": "My Task"},
    entry_type="asana:task",
    version=datetime.now(timezone.utc),
    metadata={"schema_version": "1.1.0"},  # Convention
)
```

**Pros**:
- No SDK changes required
- Opt-in for satellites that need it
- Backward compatible

**Cons**:
- **No enforcement**: SDK doesn't validate metadata keys
- **No type safety**: Schema version is just a string in a dict
- **Application must implement validation**: SDK doesn't help
- **Pattern duplication**: Each satellite implements the same check

**Tradeoff Analysis**:
- Risk: LOW - No SDK changes
- Value: MEDIUM - Provides a convention but no enforcement
- Reversibility: HIGH - Can change convention anytime

**Verdict**: CONSIDERED - Reasonable but shifts burden to application

### Option 3: Application-Layer Validation (Recommended)

**Approach**: Implement schema version checking where it belongs - in the application layer that owns schema definitions.

```
autom8_asana Architecture:
--------------------------

SchemaRegistry (Source of Truth)
    |
    | get_schema("Unit").version -> "1.1.0"
    |
    v
+-------------------------------------------+
| DataFrameCache.put_async()                |
| - Looks up schema version from registry   |
| - Stores in CacheEntry.schema_version     |
+-------------------------------------------+
    |
    v
+-------------------------------------------+
| DataFrameCache._is_valid()                |
| - Compares entry.schema_version vs        |
|   registry.get_schema(entity_type).version|
| - Invalidates on mismatch                 |
+-------------------------------------------+
    |
    v
+-------------------------------------------+
| SectionPersistence (NEW in ADR-0064)      |
| - SectionManifest.schema_version          |
| - manifest.is_schema_compatible(version)  |
| - Invalidates stale sections on mismatch  |
+-------------------------------------------+
```

**Pros**:
- **Right layer of abstraction**: Schema versioning is a satellite concern
- **Clear ownership**: SchemaRegistry is the single source of truth
- **No SDK coupling**: Platform SDK stays generic
- **Already partially implemented**: DataFrameCache has schema validation
- **Focused fix**: Only needs SectionManifest extension per ADR-0064

**Cons**:
- Pattern duplication if other satellites need this later
- Each persistence layer must implement the check

**Tradeoff Analysis**:
- Risk: LOW - Changes isolated to autom8_asana
- Value: HIGH - Directly solves the cascade resolution bug
- Reversibility: HIGH - Can refactor to SDK later if needed

**Verdict**: RECOMMENDED - Correct architectural placement

### Option 4: Registry Protocol in SDK (Future Consideration)

**Approach**: SDK provides a protocol for schema registries that satellites can implement.

```python
# autom8y_cache/protocols/schema.py (hypothetical)
@runtime_checkable
class SchemaVersionProvider(Protocol):
    """Protocol for satellites to provide schema versions."""

    def get_schema_version(self, entry_type: str) -> str:
        """Get expected schema version for an entry type."""
        ...
```

```python
# SDK would call this during validation
class CacheProvider:
    def __init__(
        self,
        schema_provider: SchemaVersionProvider | None = None,
    ):
        self._schema_provider = schema_provider

    def get_versioned(
        self,
        key: str,
        entry_type: str,
    ) -> CacheEntry | None:
        entry = self._get_raw(key, entry_type)
        if entry and self._schema_provider:
            expected = self._schema_provider.get_schema_version(entry_type)
            if entry.metadata.get("schema_version") != expected:
                return None  # Invalidate
        return entry
```

**Pros**:
- SDK provides enforcement without coupling
- Satellites opt-in by implementing protocol
- Type-safe through protocol definition

**Cons**:
- Over-engineering for current needs
- Requires SDK changes
- Only one satellite currently needs this

**Tradeoff Analysis**:
- Risk: MEDIUM - SDK changes but opt-in
- Value: MEDIUM - Generic solution for future
- Reversibility: MEDIUM - Protocol can evolve

**Verdict**: DEFERRED - Consider if multiple satellites need schema versioning

---

## Recommendation

**Implement Option 3: Application-Layer Validation** as specified in ADR-0064.

### Rationale

1. **Separation of Concerns**: The Platform SDK (`autom8y_cache`) provides generic caching primitives. Schema versioning is a domain-specific concern owned by the satellite application.

2. **Single Responsibility**: SchemaRegistry already exists as the source of truth for schemas. Adding schema validation to SectionManifest keeps related concerns together.

3. **Minimal Blast Radius**: Changes are isolated to `autom8_asana`. No risk to other SDK consumers.

4. **Already Proven**: DataFrameCache already implements this pattern successfully. SectionManifest is the only gap.

5. **Appropriate Coupling**: The fix couples SectionPersistence to SchemaRegistry, which is appropriate since they both exist in the same codebase and share the same domain.

### Architecture After Fix

```
+------------------------------------------------------------------+
|                     PLATFORM SDK (autom8y_cache)                  |
|  - Generic caching primitives                                     |
|  - Resource versioning (modified_at staleness)                    |
|  - TTL-based expiration                                           |
|  - Tiered storage (Memory + S3)                                   |
|  - NO schema versioning (satellite concern)                       |
+------------------------------------------------------------------+
                               |
                    Dependency Inversion
                               |
+------------------------------------------------------------------+
|                 SATELLITE APP (autom8_asana)                      |
|                                                                   |
|  SchemaRegistry (Source of Truth)                                 |
|       |                                                           |
|       +-----> DataFrameCache._is_valid()                          |
|       |       - Validates schema_version on GET                   |
|       |                                                           |
|       +-----> SectionManifest.is_schema_compatible() [NEW]        |
|               - Validates schema_version on resume                |
|               - Invalidates stale sections                        |
+------------------------------------------------------------------+
```

### Migration Path

No migration required for SDK. Application changes per ADR-0064:

1. Add `schema_version: str` field to `SectionManifest`
2. Add `is_schema_compatible()` method to `SectionManifest`
3. Update `ProgressiveProjectBuilder` to validate schema before resume
4. Pass schema version to `create_manifest_async()`

---

## Appendix: Key Files for Reference

### Platform SDK (autom8y_cache)

| File | Purpose |
|------|---------|
| `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/__init__.py` | Package exports and factory |
| `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/entry.py` | CacheEntry with resource version |
| `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/freshness.py` | Freshness modes |
| `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/protocols/cache.py` | CacheProvider protocol |
| `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/tiered.py` | TieredCacheProvider |
| `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/backends/s3.py` | S3CacheProvider |

### Satellite Application (autom8_asana)

| File | Purpose |
|------|---------|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/schema.py` | DataFrameSchema with version |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | SchemaRegistry singleton |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` | DataFrameCache with schema validation |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | SectionPersistence (needs schema_version) |

---

## Decision Record

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-07 | Do NOT push schema validation to SDK | Wrong layer - SDK is for resource versioning, not schema versioning |
| 2026-01-07 | Implement at application layer per ADR-0064 | Correct separation of concerns, minimal risk |
| 2026-01-07 | Defer SDK protocol option | Over-engineering for current single-satellite need |
| 2026-01-07 | SchemaRegistry remains single source of truth | Already established, well-understood |

---

## Artifacts Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| ADR-0064 | `/Users/tomtenuta/Code/autom8_asana/docs/design/ADR-0064-cascade-persistence-layer-alignment.md` | Read |
| Platform SDK entry.py | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/entry.py` | Read |
| Platform SDK protocols | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-cache/src/autom8y_cache/protocols/cache.py` | Read |
| SectionPersistence | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Read |
| SchemaRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Read |
| DataFrameCache | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` | Read |
