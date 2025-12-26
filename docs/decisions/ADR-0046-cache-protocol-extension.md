# ADR-0046: Cache Protocol Extension

## Metadata
- **Status**: Accepted
- **Author**: Tech Writer (consolidation)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0016
- **Related**: reference/CACHE.md, ADR-0047 (Two-Tier Architecture)

## Context

The autom8_asana SDK cache infrastructure evolved from a basic key-value protocol to a sophisticated versioned caching system. The original `CacheProvider` protocol offered only three methods: `get()`, `set()`, and `delete()`. This simple interface proved insufficient for intelligent caching requirements including versioned entries, batch operations, staleness checking, and entity-type-aware TTL management.

The challenge: extend the protocol to support new capabilities without breaking existing implementations like `NullCacheProvider` and `InMemoryCacheProvider`.

**Forces at Play**:
- Backward compatibility with existing provider implementations
- Need for versioned operations with `modified_at` tracking
- Batch efficiency for large-scale operations
- Staleness detection with freshness control
- Protocol-based extensibility pattern (ADR-0001)

## Decision

**Extend the existing `CacheProvider` protocol with eight new versioned methods while preserving original methods.**

The extended protocol:

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

All new methods receive default no-op implementations in existing providers to maintain protocol compliance.

## Rationale

### Why Extension Over Replacement?

An additive approach provides zero-breakage migration:
- Existing code using `cache.get()`, `cache.set()`, `cache.delete()` continues working unchanged
- Incremental adoption allows consumers to use versioned methods selectively
- Python's structural subtyping means existing custom implementations remain valid for operations using only original methods
- Original methods remain useful for simple key-value caching of non-Asana data

### Why Single Protocol Over Separate Protocols?

A new `VersionedCacheProvider` protocol would require:
- Dual protocol parameters on AsanaClient (`cache: CacheProvider | VersionedCacheProvider`)
- Complex conditional logic to check provider capabilities
- Consumer confusion about which protocol to implement
- Risk of mismatched provider capabilities

A single extended protocol is simpler and more maintainable.

### Why Backend Optimization Matters?

The protocol extension enables provider-specific optimizations:
- Redis can use native `MGET`/`MSET` for batch operations
- S3 can leverage multipart upload for large entries
- In-memory providers can optimize with LRU eviction
- Providers can implement custom staleness algorithms

A wrapper-based approach would limit all providers to basic get/set/delete semantics.

## Alternatives Considered

### Alternative 1: Separate VersionedCacheProvider Protocol
**Rejected**: Adds complexity without benefit. Requires dual protocol handling in SDK.

### Alternative 2: Inheritance-Based Extension
**Rejected**: Violates ADR-0001 protocol pattern. Requires explicit inheritance from consumers.

### Alternative 3: Wrapper/Decorator Pattern
**Rejected**: Prevents backend-specific optimizations. Redis wrapper couldn't use `MGET` if limited to basic protocol.

## Consequences

### Positive
- Full backward compatibility with existing consumers
- Type-safe extension verified by mypy
- Incremental adoption path for new methods
- Backend-specific optimizations enabled
- Clear API surface with related methods grouped

### Negative
- Protocol surface increased from 3 to 11 methods
- Default stub implementations required in existing providers
- Documentation complexity explaining basic vs versioned usage
- Potential confusion about which methods to use for Asana data

### Neutral
- Protocol still uses `typing.Protocol` (consistent with ADR-0001)
- Original methods work identically
- New data types introduced: `CacheEntry`, `EntryType`, `Freshness`

## Impact

This protocol extension serves as the foundation for all subsequent cache features:
- Two-tier Redis+S3 architecture (ADR-0047)
- Staleness detection with progressive TTL (ADR-0048)
- Batch operations for DataFrame caching (ADR-0049)
- Entity-aware TTL management (ADR-0050)
- Cache invalidation hooks (ADR-0051)

Zero breaking changes while enabling eight new methods represents successful API evolution.

## Compliance

**Enforcement mechanisms**:
1. Code review: New cache operations for Asana resources use versioned methods
2. Type checking: `mypy --strict` verifies protocol compliance in CI
3. Architecture tests: Verify all providers implement full protocol
4. Documentation: README shows versioned methods as primary API

**Configuration**: None required - protocol extension is API-level change.
