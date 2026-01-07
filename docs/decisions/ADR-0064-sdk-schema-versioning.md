# ADR-0064: SDK-Level Schema Versioning

## Metadata

- **Status**: Proposed
- **Author**: Architect
- **Date**: 2026-01-07
- **Deciders**: Platform Team, Satellite Leads
- **Related**: TDD-sdk-schema-versioning, ADR-0033 (Schema Enforcement)

## Context

The autom8_asana satellite currently implements schema versioning for cached DataFrames at the application layer:

```python
# Current: Satellite-specific implementation
metadata={"schema_version": "1.0.0"}

def _is_valid(self, entry: CacheEntry, ...) -> bool:
    cached_schema = entry.metadata.get("schema_version")
    if cached_schema != expected_version:
        return False
```

This approach was chosen during initial development with the rationale that:
1. Only one satellite needed schema versioning
2. Schema versioning was considered "domain-specific"
3. YAGNI suggested waiting until the pattern was proven

**Stakeholder Challenge**: A stakeholder raised a valid objection:

> "Schema versioning is a principle that could apply to lots of domains. I disagree with keeping it at the application layer."

Upon deeper analysis, the stakeholder's intuition is correct. The previous analysis had several flaws:

| Previous Argument | Counterargument |
|-------------------|-----------------|
| "Only one satellite needs this" | Platform design anticipates patterns |
| "Schema versioning is domain-specific" | Avro, Protobuf, Kafka treat it as infrastructure |
| "YAGNI" | YAGNI applies to features, not foundational capabilities |
| "Use metadata dict" | Escape hatch is admission of SDK incompleteness |

### Industry Evidence

Every major data platform centralizes schema versioning:

- **Apache Avro**: Writer schema embedded in data
- **Protocol Buffers**: Field numbers in wire format
- **Kafka Schema Registry**: Centralized schema management
- **Database ORMs**: Centralized migration tracking

The common pattern: Schema versioning is **infrastructure**, not application code.

## Decision

**Elevate schema versioning from satellite-specific implementation to a first-class Platform SDK (`autom8y-cache`) feature.**

Specifically:

1. **Add `SchemaVersion` type** to SDK with semver semantics and comparison operators

2. **Add `schema_version` field** to `CacheEntry` as optional field (not metadata)

3. **Add `CompatibilityMode` enum** supporting EXACT, BACKWARD, FORWARD, FULL, NONE (mirroring Kafka)

4. **Add `SchemaVersionProvider` protocol** for satellites to register their schemas

5. **Add `is_schema_compatible()` method** to `CacheEntry` for validation

6. **Add helper functions** for automatic schema validation on retrieval

### API Surface

```python
from autom8y_cache import (
    CacheEntry,
    SchemaVersion,
    CompatibilityMode,
    register_schema_provider,
    get_with_schema_validation,
)

# Satellite registration
class MySchema:
    @property
    def schema_version(self) -> SchemaVersion:
        return SchemaVersion(1, 0, 0)

    @property
    def compatibility_mode(self) -> CompatibilityMode:
        return CompatibilityMode.BACKWARD

register_schema_provider("myapp:entity", MySchema())

# Cache entry creation with schema
entry = CacheEntry(
    key="entity:123",
    data={"name": "test"},
    entry_type="myapp:entity",
    version=datetime.now(timezone.utc),
    schema_version=SchemaVersion(1, 0, 0),  # First-class field
)

# Validation
if entry.is_schema_compatible(SchemaVersion(1, 1, 0), CompatibilityMode.BACKWARD):
    # Use cached data
    ...

# Or automatic validation via helper
entry = get_with_schema_validation(cache, "entity:123", "myapp:entity")
```

## Rationale

### Why Centralize in SDK?

1. **DRY Principle**: Without centralization, every satellite copies the same pattern:
   - autom8_asana: 150+ lines of schema validation
   - autom8_contacts: Would copy same pattern
   - autom8_hubspot: Would copy same pattern
   - Each copy diverges over time

2. **Industry Standard**: The universal pattern is centralized schema management. We're not innovating; we're catching up.

3. **Reduced Cognitive Load**: Developers expect schema versioning to be SDK-provided, not hand-rolled.

4. **Better API**: `entry.is_schema_compatible(v)` is clearer than `entry.metadata.get("schema_version") != expected`.

### Why Compatibility Modes?

Mirroring Kafka's compatibility modes provides flexibility:

| Mode | Use Case |
|------|----------|
| EXACT | Breaking changes require full rebuild |
| BACKWARD | New code can read old data (additive fields) |
| FORWARD | Old code can read new data (removable fields) |
| FULL | Both directions (most flexible) |
| NONE | No validation (legacy compatibility) |

### Why Optional Field vs Required?

Backward compatibility. Existing cached data and satellite code continue working. Migration is incremental.

## Alternatives Considered

### Alternative 1: Keep at Satellite Layer (Status Quo)

- **Description**: Each satellite implements its own schema versioning
- **Pros**: No SDK changes; satellites have full control
- **Cons**:
  - DRY violation
  - Inconsistent implementations
  - No compatibility modes
  - Escape hatch pattern
- **Why not chosen**: The stakeholder is right - this is a universal concern

### Alternative 2: Metadata Convention (Document Pattern)

- **Description**: Define a convention for `metadata["schema_version"]` across satellites
- **Pros**: No code changes; just documentation
- **Cons**:
  - No type safety
  - No validation helpers
  - No compatibility modes
  - Still requires satellite-level validation code
- **Why not chosen**: A convention is a weak contract; SDK support is a strong contract

### Alternative 3: Full Schema Registry Service

- **Description**: Implement Kafka-style central schema registry service
- **Pros**: Full schema evolution support; cross-satellite coordination
- **Cons**:
  - Significant infrastructure complexity
  - Network dependency for caching
  - Over-engineered for current needs
- **Why not chosen**: Start with in-SDK support; can evolve to service later if needed

### Alternative 4: Generic Version Field (String)

- **Description**: Add `schema_version: str` field without structured semantics
- **Pros**: Simple; flexible
- **Cons**:
  - No comparison operators
  - No compatibility modes
  - String parsing required everywhere
- **Why not chosen**: Structured `SchemaVersion` type is marginally more complex but significantly more useful

## Consequences

### Positive

- **Eliminates duplication**: ~150 lines of satellite code becomes ~10 lines
- **Type safety**: `SchemaVersion` vs stringly-typed `metadata["schema_version"]`
- **Compatibility modes**: Support for schema evolution strategies
- **Discoverable API**: First-class field is easier to find than metadata convention
- **Future-proof**: New satellites get schema versioning for free

### Negative

- **SDK change required**: Must update `autom8y-cache` package
- **Migration effort**: Existing satellite code must be updated (low effort)
- **Learning curve**: Developers must learn new API (offset by documentation)

### Neutral

- **Backward compatible**: Existing code continues working until migrated
- **Performance**: No measurable impact (comparison operations are trivial)

## Implementation Plan

1. **Phase 1 (SDK)**: Add types, field, protocols to `autom8y-cache`
2. **Phase 2 (autom8_asana)**: Migrate to SDK feature, remove duplicate code
3. **Phase 3 (Documentation)**: Update guides, patterns, examples
4. **Phase 4 (Other Satellites)**: Apply pattern to future satellites

## Compliance

### How This Decision Is Enforced

1. **Code review**: New satellites must use SDK schema versioning, not metadata convention
2. **SDK documentation**: Schema versioning section in SDK docs
3. **Migration tracking**: Track autom8_asana migration to completion

### Metrics

- Lines of schema validation code per satellite (target: <20)
- Schema version consistency across cache entries (target: 100%)
- Migration completion percentage

## References

- TDD-sdk-schema-versioning: Full technical design
- ADR-0033: Schema Enforcement (type coercion, related but distinct)
- [Kafka Schema Registry](https://docs.confluent.io/platform/current/schema-registry/index.html)
- [Avro Schema Evolution](https://avro.apache.org/docs/current/spec.html#Schema+Resolution)
