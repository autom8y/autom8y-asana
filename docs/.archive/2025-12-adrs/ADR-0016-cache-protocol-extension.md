# ADR-0016: Cache Protocol Extension

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team
- **Related**: [PRD-0002](../requirements/PRD-0002-intelligent-caching.md), [TDD-0008](../design/TDD-0008-intelligent-caching.md), [ADR-0001](ADR-0001-protocol-extensibility.md)

## Context

The autom8_asana SDK currently has a basic `CacheProvider` protocol with three methods:

```python
class CacheProvider(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...
    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
```

PRD-0002 requires intelligent caching with:
- Versioned entries (modified_at tracking)
- Entry types (TASK, SUBTASKS, DEPENDENCIES, etc.)
- Freshness control (strict vs eventual)
- Batch operations for efficiency
- Cache warming API
- Staleness checking

The existing protocol is too simple for these requirements. We need to extend it without breaking existing consumers who may have implemented the basic protocol.

**Forces at play**:
1. **Backward compatibility**: Existing `NullCacheProvider` and `InMemoryCacheProvider` must continue working
2. **Type safety**: New methods must be statically type-checkable
3. **Optional adoption**: Consumers can use new methods incrementally
4. **Protocol compliance**: Per ADR-0001, we use `typing.Protocol` for extensibility

## Decision

**Extend the existing `CacheProvider` protocol with new versioned methods while preserving the original methods.**

The extended protocol adds:

```python
class CacheProvider(Protocol):
    # === Original methods (preserved) ===
    def get(self, key: str) -> dict[str, Any] | None: ...
    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...

    # === New versioned methods ===
    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Freshness = Freshness.EVENTUAL,
    ) -> CacheEntry | None: ...

    def set_versioned(self, key: str, entry: CacheEntry) -> None: ...

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]: ...

    def set_batch(self, entries: dict[str, CacheEntry]) -> None: ...

    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType],
    ) -> WarmResult: ...

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool: ...

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None: ...

    def is_healthy(self) -> bool: ...
```

Default implementations are provided for all new methods in existing providers:

```python
class NullCacheProvider:
    # Original methods (unchanged)
    def get(self, key: str) -> dict[str, Any] | None:
        return None

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        pass

    def delete(self, key: str) -> None:
        pass

    # New methods with no-op defaults
    def get_versioned(self, key: str, entry_type: EntryType, ...) -> CacheEntry | None:
        return None

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        pass

    # ... etc
```

## Rationale

**Why extend rather than replace?**

1. **Zero breakage**: Any code using `cache.get()`, `cache.set()`, `cache.delete()` continues working unchanged.

2. **Incremental migration**: Consumers can adopt versioned methods one operation at a time. A service might use `get_versioned()` for tasks but still use basic `get()` for other resources.

3. **Protocol flexibility**: Python's `typing.Protocol` allows structural subtyping. Existing custom implementations that only have the original 3 methods will still type-check for operations that only use those methods.

4. **Separation of concerns**: The original methods remain useful for simple key-value caching (e.g., configuration, non-Asana data). Versioned methods are specifically for Asana resources with `modified_at` semantics.

**Why not a separate protocol?**

A new `VersionedCacheProvider` protocol would require:
- Two protocol parameters on AsanaClient
- Complex conditional logic to check which protocol to use
- Confusion about which provider to implement
- Potential for mismatched provider capabilities

A single extended protocol is simpler.

## Alternatives Considered

### Alternative 1: New Separate Protocol

- **Description**: Create `VersionedCacheProvider` as a distinct protocol, keep original `CacheProvider` unchanged.
- **Pros**:
  - Original protocol remains minimal
  - Clear separation of capabilities
  - Existing implementations unaffected
- **Cons**:
  - SDK would need to accept both protocols
  - Complex type signatures: `cache: CacheProvider | VersionedCacheProvider`
  - Runtime checks to determine available methods
  - Consumers confused about which to implement
- **Why not chosen**: Adds complexity without benefit. The extended protocol is strictly additive.

### Alternative 2: Inheritance-Based Extension

- **Description**: Create `class VersionedCacheProvider(CacheProvider)` using ABC inheritance.
- **Pros**:
  - Clear hierarchy
  - Can enforce method implementation
  - Standard OOP pattern
- **Cons**:
  - Violates ADR-0001 (we use Protocol, not ABC)
  - Requires explicit inheritance from consumers
  - Breaks structural subtyping benefits
- **Why not chosen**: Contradicts established protocol pattern.

### Alternative 3: Mixin Approach

- **Description**: Define `CacheVersioningMixin` that adds versioned methods, consumers inherit from both.
- **Pros**:
  - Composable capabilities
  - Selective adoption
- **Cons**:
  - Multiple inheritance complexity
  - Method resolution order issues
  - Still requires inheritance (violates ADR-0001)
- **Why not chosen**: Too complex for the problem being solved.

### Alternative 4: Wrapper/Decorator Pattern

- **Description**: Create `VersionedCacheWrapper` that wraps a basic `CacheProvider` and adds versioned methods on top.
- **Pros**:
  - Basic providers unchanged
  - Versioning logic centralized
  - Easy to test independently
- **Cons**:
  - Runtime overhead from wrapping
  - Two objects to manage
  - Wrapper must implement caching logic using only basic methods (inefficient)
  - Can't leverage Redis-specific features
- **Why not chosen**: Prevents backend-specific optimizations. Redis has native features (HGETALL, MULTI) that a wrapper couldn't use if limited to basic get/set/delete.

## Consequences

### Positive

- **Full backward compatibility**: No changes required for existing consumers
- **Type-safe extension**: mypy validates new method signatures
- **Incremental adoption**: Consumers can use new methods as needed
- **Backend optimization**: Redis provider can use native features for versioned operations
- **Clear API surface**: Single protocol with related methods grouped together

### Negative

- **Larger protocol surface**: Protocol now has 11 methods instead of 3
- **Default implementations required**: Existing providers must add stub methods
- **Documentation complexity**: Must explain both basic and versioned usage patterns
- **Potential confusion**: Two ways to cache (basic vs versioned) for Asana data

### Neutral

- **Protocol still uses `typing.Protocol`**: Consistent with ADR-0001
- **No runtime behavior change for basic methods**: Original methods work identically
- **New data types introduced**: `CacheEntry`, `EntryType`, `Freshness` are new public types

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - New cache operations for Asana resources use versioned methods
   - Basic methods reserved for non-Asana or simple caching
   - Custom providers implement all protocol methods (even as stubs)

2. **Type checking in CI**:
   - `mypy --strict` verifies protocol compliance
   - Any new provider must satisfy the full protocol

3. **Documentation**:
   - README shows versioned methods as primary API for Asana caching
   - Basic methods documented as legacy/simple-case option

4. **Architecture tests**:
   - Verify `NullCacheProvider` and `InMemoryCacheProvider` implement all methods
   - Verify `RedisCacheProvider` implements all methods with proper Redis operations
