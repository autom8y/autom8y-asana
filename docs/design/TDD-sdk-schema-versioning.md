# TDD: SDK-Level Schema Versioning

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Author** | Architect |
| **Date** | 2026-01-07 |
| **Related PRD** | N/A (Platform Infrastructure) |
| **Related ADRs** | ADR-0064 (pending) |
| **Complexity** | SYSTEM |
| **Satellites Affected** | All (autom8_asana, autom8_contacts, future satellites) |

## Executive Summary

This TDD proposes elevating schema versioning from a satellite-specific concern to a first-class platform SDK feature. The stakeholder's challenge is valid: schema versioning is a **universal pattern** for any system that caches structured data, and treating it as satellite-specific violates DRY while ignoring industry best practices.

### Previous Analysis Flaws Acknowledged

| Flaw | Correction |
|------|------------|
| "Only one satellite needs this" | Premature optimization fallacy inverted. Platform design anticipates patterns. |
| Resource vs schema versioning dichotomy | False dichotomy. Both are valid, not mutually exclusive. |
| "Schema versioning is domain-specific" | Wrong. Avro, Protobuf, Kafka all treat it as infrastructure. |
| YAGNI applied to infrastructure | Misapplied. YAGNI is for features, not foundational capabilities. |
| Metadata dict as escape hatch | Admission of SDK incompleteness, not a design choice. |

## Industry Standards Analysis

### How Do Industry-Leading Systems Handle Schema Versioning?

| System | Approach | Key Insight |
|--------|----------|-------------|
| **Apache Avro** | Writer schema embedded in data; reader schema comparison at read time | Schema is data's companion, not metadata afterthought |
| **Protocol Buffers** | Field numbers + wire type in format; backward/forward compatible | Wire format encodes structure version implicitly |
| **Kafka Schema Registry** | **Centralized** schema registry; subjects + versions | Schema management is platform concern, not application concern |
| **Redis Modules** | Supports schema evolution via modules like RedisJSON | Even key-value stores evolve toward schema awareness |
| **GraphQL** | Schema is central; versioning via deprecation | Schema is API contract, versioned at platform level |
| **Database ORMs** | Centralized migration tracking (Alembic, Django migrations) | Schema evolution is infrastructure, not application code |

**Common Pattern**: Every mature system treats schema versioning as **infrastructure**, not application-level code.

### Kafka Schema Registry Deep Dive

Kafka's approach is particularly instructive:

```
┌─────────────────────────────────────────────────────────────┐
│                    Schema Registry                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Subject:    │  │ Subject:    │  │ Subject:    │         │
│  │ user-value  │  │ order-value │  │ payment     │         │
│  │ v1, v2, v3  │  │ v1, v2      │  │ v1          │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ Compatibility Check
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Producer/Consumer                                            │
│  - Embeds schema ID in message                               │
│  - Registry validates compatibility on write                 │
│  - Consumer looks up schema by ID on read                    │
└──────────────────────────────────────────────────────────────┘
```

Key takeaways:
1. **Centralized registry** - not per-topic versioning
2. **Compatibility modes** - BACKWARD, FORWARD, FULL, NONE
3. **Schema ID in wire format** - data carries its schema identity
4. **Separation of concerns** - producers don't implement version logic

## Current State Analysis

### Platform SDK (`autom8y-cache`)

Current `CacheEntry`:

```python
@dataclass(frozen=True)
class CacheEntry:
    key: str
    data: dict[str, Any]
    entry_type: str              # Type classification
    version: datetime            # RESOURCE version (modified_at)
    cached_at: datetime
    ttl: int | None
    project_gid: str | None
    metadata: dict[str, Any]     # <-- Escape hatch for everything else
```

**Problem**: The `metadata: dict[str, Any]` is an admission that the SDK doesn't know what satellites need. Schema version is stuffed in there:

```python
# autom8_asana's workaround
entry = CacheEntry(
    ...,
    metadata={"schema_version": "1.0.0"}  # SDK doesn't know about this
)
```

### Satellite (`autom8_asana`)

Currently implements its own schema versioning:

```python
# cache_integration.py - satellite-level implementation
metadata={"schema_version": schema_version}

# dataframe_cache.py - satellite-level validation
def _is_valid(self, entry: CacheEntry, ...) -> bool:
    expected_version = _get_schema_version_for_entity(entry.entity_type)
    if entry.schema_version != expected_version:
        return False  # Satellite-specific logic
```

**Problem**: When `autom8_contacts`, `autom8_hubspot`, `autom8_salesforce` need schema versioning, they'll copy-paste this pattern. DRY violation.

## Proposed Design

### Core Principle

**Schema versioning is cache infrastructure**, not application code. The SDK should:
1. Provide schema version storage in `CacheEntry` (not metadata)
2. Provide a protocol for version providers
3. Provide opt-in version validation at retrieval time
4. Support compatibility modes (like Kafka)

### Schema Version Model

```python
# autom8y_cache/schema_version.py

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class CompatibilityMode(Enum):
    """Schema compatibility modes (mirrors Kafka Schema Registry)."""
    NONE = "none"              # No compatibility check
    BACKWARD = "backward"       # New can read old
    FORWARD = "forward"         # Old can read new
    FULL = "full"              # Both directions
    EXACT = "exact"            # Must match exactly


@dataclass(frozen=True)
class SchemaVersion:
    """Semantic version for cache schemas.

    Follows semver convention:
    - major: Breaking changes (incompatible schema)
    - minor: Backward-compatible additions
    - patch: Backward-compatible fixes

    Example:
        >>> v1 = SchemaVersion(1, 0, 0)
        >>> v2 = SchemaVersion(1, 1, 0)
        >>> v1.is_compatible_with(v2, CompatibilityMode.BACKWARD)
        True
    """
    major: int
    minor: int
    patch: int = 0

    @classmethod
    def from_string(cls, version: str) -> SchemaVersion:
        """Parse version string like '1.2.3' or '1.0'."""
        parts = version.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return cls(major, minor, patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(
        self,
        other: SchemaVersion,
        mode: CompatibilityMode = CompatibilityMode.EXACT,
    ) -> bool:
        """Check compatibility with another version.

        Args:
            other: Version to check compatibility against
            mode: Compatibility mode to use

        Returns:
            True if versions are compatible under the given mode
        """
        if mode == CompatibilityMode.NONE:
            return True
        if mode == CompatibilityMode.EXACT:
            return self == other
        if mode == CompatibilityMode.BACKWARD:
            # Can read older versions (same major, any minor/patch)
            return self.major == other.major and self >= other
        if mode == CompatibilityMode.FORWARD:
            # Can be read by older versions (same major, any minor/patch)
            return self.major == other.major and self <= other
        if mode == CompatibilityMode.FULL:
            # Both directions (same major)
            return self.major == other.major
        return False

    def __lt__(self, other: SchemaVersion) -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: SchemaVersion) -> bool:
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: SchemaVersion) -> bool:
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: SchemaVersion) -> bool:
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)
```

### Updated CacheEntry

```python
# autom8y_cache/entry.py (updated)

@dataclass(frozen=True)
class CacheEntry:
    """Immutable cache entry with versioning metadata.

    Now includes explicit schema version field (not relegated to metadata).
    """
    key: str
    data: dict[str, Any]
    entry_type: str
    version: datetime                          # Resource version (modified_at)
    cached_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl: int | None = 300
    project_gid: str | None = None

    # NEW: First-class schema versioning
    schema_version: SchemaVersion | None = None

    # Retained for satellite-specific extensions
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_schema_compatible(
        self,
        current_version: SchemaVersion,
        mode: CompatibilityMode = CompatibilityMode.EXACT,
    ) -> bool:
        """Check if cached data is compatible with current schema.

        Args:
            current_version: Current schema version to check against
            mode: Compatibility mode (EXACT, BACKWARD, FORWARD, FULL, NONE)

        Returns:
            True if schema is compatible, False otherwise.
            Returns True if no schema version is set (backward compatibility).
        """
        if self.schema_version is None:
            # Legacy entries without schema version - caller decides policy
            return True
        return self.schema_version.is_compatible_with(current_version, mode)
```

### Schema Version Provider Protocol

```python
# autom8y_cache/protocols/schema.py

from typing import Protocol, runtime_checkable


@runtime_checkable
class SchemaVersionProvider(Protocol):
    """Protocol for types that declare their schema version.

    Satellites implement this for their domain types to enable
    SDK-level schema validation.

    Example (satellite implementation):
        class AsanaTaskSchema:
            @property
            def schema_version(self) -> SchemaVersion:
                return SchemaVersion(1, 1, 0)

            @property
            def compatibility_mode(self) -> CompatibilityMode:
                return CompatibilityMode.BACKWARD
    """

    @property
    def schema_version(self) -> SchemaVersion:
        """Current schema version for this type."""
        ...

    @property
    def compatibility_mode(self) -> CompatibilityMode:
        """Compatibility mode for version checking."""
        ...


# Global registry for schema providers (like completeness registry)
_schema_registry: dict[str, SchemaVersionProvider] = {}


def register_schema_provider(
    entry_type: str,
    provider: SchemaVersionProvider,
) -> None:
    """Register a schema version provider for an entry type.

    Satellites call this at initialization to enable SDK-level
    schema validation for their entry types.

    Args:
        entry_type: Entry type string (e.g., "asana:task", "contact:entity")
        provider: Schema version provider implementation

    Example:
        register_schema_provider("asana:task", AsanaTaskSchema())
    """
    _schema_registry[entry_type] = provider


def get_schema_provider(entry_type: str) -> SchemaVersionProvider | None:
    """Get registered schema provider for an entry type."""
    return _schema_registry.get(entry_type)


def get_current_schema_version(entry_type: str) -> SchemaVersion | None:
    """Get current schema version for an entry type.

    Convenience function for retrieval operations.
    """
    provider = get_schema_provider(entry_type)
    return provider.schema_version if provider else None
```

### Enhanced CacheProvider Protocol

```python
# autom8y_cache/protocols/cache.py (additions)

class CacheProvider(Protocol):
    # ... existing methods ...

    def get_versioned(
        self,
        key: str,
        entry_type: str,
        freshness: Freshness | None = None,
        schema_version: SchemaVersion | None = None,  # NEW
        compatibility_mode: CompatibilityMode = CompatibilityMode.EXACT,  # NEW
    ) -> CacheEntry | None:
        """Retrieve versioned cache entry with optional schema validation.

        Args:
            key: Cache key to retrieve
            entry_type: Expected entry type
            freshness: Freshness mode (STRICT or EVENTUAL)
            schema_version: If provided, validate cached schema against this
            compatibility_mode: Mode for schema compatibility check

        Returns:
            CacheEntry if found, valid, and schema-compatible.
            None if not found, invalid, or schema-incompatible.

        Note:
            If schema_version is provided but entry has no schema_version,
            behavior depends on compatibility_mode:
            - NONE: Returns entry (no validation)
            - Others: Returns None (treats missing schema as incompatible)
        """
        ...
```

### Schema Validation Helper

```python
# autom8y_cache/helpers.py (additions)

def get_with_schema_validation(
    cache: CacheProvider,
    key: str,
    entry_type: str,
    freshness: Freshness = Freshness.EVENTUAL,
) -> CacheEntry | None:
    """Get cache entry with automatic schema validation.

    Uses the registered schema provider for the entry type to determine
    the current schema version and compatibility mode.

    Args:
        cache: Cache provider
        key: Cache key
        entry_type: Entry type (must have registered schema provider)
        freshness: Freshness mode

    Returns:
        CacheEntry if valid and schema-compatible, None otherwise.

    Example:
        # Satellite registers schema at startup
        register_schema_provider("asana:task", AsanaTaskSchema())

        # SDK handles validation automatically
        entry = get_with_schema_validation(cache, "task:123", "asana:task")
    """
    provider = get_schema_provider(entry_type)

    if provider is None:
        # No schema provider - fall back to basic retrieval
        return cache.get_versioned(key, entry_type, freshness)

    return cache.get_versioned(
        key=key,
        entry_type=entry_type,
        freshness=freshness,
        schema_version=provider.schema_version,
        compatibility_mode=provider.compatibility_mode,
    )
```

## Migration Path

### Phase 1: SDK Enhancement (Non-Breaking)

Add to `autom8y-cache` SDK:
1. `SchemaVersion` dataclass
2. `CompatibilityMode` enum
3. Optional `schema_version` field on `CacheEntry`
4. `SchemaVersionProvider` protocol
5. Registry functions
6. Helper functions

**Breaking changes**: None. All additions are optional.

### Phase 2: Satellite Migration (autom8_asana)

```python
# Before (current satellite implementation)
entry = CacheEntry(
    key=key,
    data=data,
    entry_type=EntryType.DATAFRAME,
    version=version_dt,
    metadata={"schema_version": schema_version},  # In metadata
)

# After (using SDK feature)
from autom8y_cache import SchemaVersion

entry = CacheEntry(
    key=key,
    data=data,
    entry_type=EntryType.DATAFRAME,
    version=version_dt,
    schema_version=SchemaVersion.from_string(schema_version),  # First-class field
    metadata={},  # Cleaned up
)
```

Validation changes:
```python
# Before (satellite-specific validation)
def _is_valid(self, entry: CacheEntry, ...) -> bool:
    expected_version = _get_schema_version_for_entity(entry.entity_type)
    cached_schema = entry.metadata.get("schema_version")
    if cached_schema != expected_version:
        return False

# After (SDK-provided validation)
def _is_valid(self, entry: CacheEntry, ...) -> bool:
    if not entry.is_schema_compatible(self._current_schema_version):
        return False
```

### Phase 3: Other Satellites

Future satellites (`autom8_contacts`, etc.) use SDK feature from day one:

```python
from autom8y_cache import (
    CacheEntry,
    SchemaVersion,
    CompatibilityMode,
    register_schema_provider,
)

class ContactSchema:
    @property
    def schema_version(self) -> SchemaVersion:
        return SchemaVersion(1, 0, 0)

    @property
    def compatibility_mode(self) -> CompatibilityMode:
        return CompatibilityMode.BACKWARD

# Register at startup
register_schema_provider("contact:entity", ContactSchema())
```

## Backward Compatibility

### Existing Cached Data

Entries without `schema_version` field:
- `CacheEntry.schema_version` defaults to `None`
- `is_schema_compatible()` returns `True` for `None` schema (configurable)
- Satellites can choose to treat as stale and rebuild

### Existing Satellite Code

No changes required immediately:
- `metadata` dict still available
- Satellites can migrate incrementally
- Old validation logic continues to work

### SDK Version Compatibility

| SDK Version | `schema_version` field | `is_schema_compatible()` | Registry functions |
|-------------|------------------------|--------------------------|-------------------|
| Current     | No                     | No                       | No                |
| v2.0        | Optional               | Yes                      | Yes               |
| Future      | Optional               | Yes                      | Yes               |

## Real Complexity Cost

The stakeholder asked: "What's the REAL cost?"

### SDK Changes

| Component | Lines of Code | Complexity |
|-----------|--------------|------------|
| `SchemaVersion` dataclass | ~60 lines | Low - pure data + comparison |
| `CompatibilityMode` enum | ~6 lines | Trivial |
| `CacheEntry.schema_version` field | ~1 line | Trivial |
| `CacheEntry.is_schema_compatible()` | ~10 lines | Low - delegation |
| `SchemaVersionProvider` protocol | ~15 lines | Low - interface only |
| Registry functions | ~20 lines | Low - dict operations |
| Helper functions | ~20 lines | Low |
| **Total** | **~130 lines** | **Low** |

### Satellite Migration (autom8_asana)

| Change | Lines Changed | Risk |
|--------|--------------|------|
| Import new types | +3 lines | None |
| Update CacheEntry creation | ~20 call sites, 1 line each | Low - mechanical |
| Update validation logic | ~5 locations | Low - simplification |
| Register schema providers | +20 lines at startup | None |
| Remove duplicate logic | -100 lines | Positive - cleanup |
| **Net change** | **~-50 lines** | **Low** |

### Test Coverage

| Test Category | Effort |
|---------------|--------|
| `SchemaVersion` unit tests | ~15 test cases |
| Compatibility mode tests | ~10 test cases |
| Integration tests | ~5 test cases |
| Migration tests | ~5 test cases |
| **Total new tests** | **~35 test cases** |

## Answering the Challenge Questions

### 1. "Why is resource versioning 'generic' but schema versioning 'domain-specific'?"

**Answer**: It shouldn't be. Both are about data validity:
- Resource version: "Is cached data fresh compared to source?"
- Schema version: "Is cached data structurally compatible with current code?"

The previous analysis created a false distinction. Both are cache infrastructure concerns.

### 2. "What happens when multiple satellites need schema versioning?"

**Answer (before this proposal)**: Copy-paste pattern into each satellite. DRY violation.

**Answer (with this proposal)**: All satellites use `CacheEntry.schema_version` and `is_schema_compatible()`. Zero duplication.

### 3. "Isn't `metadata: dict[str, Any]` an escape hatch?"

**Answer**: Yes. It's an admission that the SDK anticipated needing flexibility but didn't know the patterns yet. Now we know: schema versioning is a pattern. Time to promote it from escape hatch to first-class citizen.

### 4. "How do industry standards handle this?"

**Answer**: Kafka Schema Registry, Avro, Protobuf all treat schema versioning as **centralized infrastructure**. We should too.

### 5. "What's the REAL complexity cost?"

**Answer**: ~130 lines to SDK, ~-50 lines net to satellite. Low complexity, proven patterns. Calling this "over-engineering" was a lazy dismissal.

## Architectural Principles Alignment

| Principle | How This Design Aligns |
|-----------|----------------------|
| **Prefer Boring Technology** | semver is boring and proven |
| **Design for Failure** | Graceful handling of missing schema versions |
| **Make Decisions Reversible** | Optional field, incremental migration |
| **Optimize for Change** | Schema evolution built-in, not bolted-on |
| **Document the "Why"** | This TDD explains rationale extensively |

## ADR Reference

See `ADR-0064-sdk-schema-versioning.md` (to be created) for decision record.

## Handoff Checklist

- [ ] SDK changes implemented and tested
- [ ] Documentation updated
- [ ] Migration guide created for satellites
- [ ] autom8_asana migrated
- [ ] Performance benchmarks show no regression
- [ ] Backward compatibility verified

## Attestation Table

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| This TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-sdk-schema-versioning.md` | Pending |
| Related ADR | `/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0064-sdk-schema-versioning.md` | Pending |

---

## Summary

The stakeholder was right. Schema versioning is a universal pattern that belongs in the SDK:

1. **Industry precedent**: Kafka, Avro, Protobuf all centralize schema versioning
2. **DRY**: Prevents copy-paste across satellites
3. **Low cost**: ~130 lines of SDK code
4. **High value**: Every satellite benefits automatically
5. **Backward compatible**: Opt-in, incremental migration

The previous analysis committed the sin of "not invented here" combined with premature optimization in reverse. Platform infrastructure should anticipate patterns, not wait for them to become painful.
