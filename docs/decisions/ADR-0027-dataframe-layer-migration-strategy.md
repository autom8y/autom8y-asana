# ADR-0027: Dataframe Layer Migration Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team, User
- **Related**: [PRD-0003](../requirements/PRD-0003-structured-dataframe-layer.md), [ADR-0025](ADR-0025-migration-strategy.md) (caching migration pattern)

## Context

PRD-0003 (Structured Dataframe Layer) introduces a new `to_dataframe()` API to replace the legacy `struc()` method. The legacy system is a ~1,000-line method at `project/main.py:793-1225` that transforms Asana task hierarchies into pandas DataFrames. This ADR documents the migration strategy from `struc()` to `to_dataframe()`.

### Legacy System Characteristics

| Aspect | Current State |
|--------|---------------|
| Location | `project/main.py:793-1225` |
| Size | ~1,000 lines |
| Output | `pandas.DataFrame` |
| Concurrency | ThreadManager (10 workers) |
| Caching | Memory (`STRUCTURE_CACHE`) + S3 (`EntryType.STRUC`) |
| Staleness | Story-based modification detection |
| Coupling | 119 SQL imports, 256 business logic imports |
| Task Types | 50+ subclasses, each with `STRUC_COLS` |

### Target System (PRD-0003)

| Aspect | Target State |
|--------|--------------|
| API | `to_dataframe()` method on Project/Section |
| Output | `polars.DataFrame` |
| Concurrency | Configurable (default 10) |
| Caching | Redis + S3 via TDD-0008 infrastructure |
| MVP Scope | Unit (11 fields) + Contact (9 fields) + Base (12 fields) |
| Timeline | 2-3 weeks |

### Migration Options Considered

1. **Big-bang with Interface Evolution** (chosen): Replace internal implementation entirely; wrap `struc()` as deprecated alias
2. **Phased rollout**: Migrate field-by-field or type-by-type over multiple releases
3. **Parallel implementation**: Maintain both codepaths; let consumers choose
4. **In-place breaking change**: Remove `struc()` entirely with no compatibility layer

### User Decisions (Confirmed)

The user explicitly chose:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Migration Strategy | Big-bang | Clean cutover; no dual-codepath maintenance |
| Compatibility | Interface Evolution | Backward compatible; `struc()` still callable |
| Timeline | 2-3 weeks acceptable | Quality over speed |
| Testing | Integration + mocked API | Validate behavior without live Asana calls |

## Decision

**Implement a big-bang migration with Interface Evolution: replace `struc()` internals with `to_dataframe()` in a single release, maintaining `struc()` as a deprecated wrapper.**

### Migration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            BEFORE (Legacy)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Consumer Code              Legacy System                                   │
│   ─────────────              ─────────────                                   │
│                                                                              │
│   df = project.struc()  ───► struc() method                                 │
│                               │                                              │
│                               ├──► ThreadManager (10 workers)               │
│                               ├──► STRUC_COLS per task subclass             │
│                               ├──► S3 cache (EntryType.STRUC)               │
│                               └──► pandas.DataFrame                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

                                    │
                                    │  Big-bang migration
                                    ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│                            AFTER (New)                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Consumer Code              New System                                      │
│   ─────────────              ──────────                                      │
│                                                                              │
│   df = project.struc()  ───► struc() [DEPRECATED]                           │
│        │                      │                                              │
│        │                      ├──► DeprecationWarning                       │
│        │                      └──► to_dataframe().to_pandas()               │
│        │                                     │                               │
│        │                                     ▼                               │
│        │                          ┌─────────────────────┐                   │
│        └─ OR (new consumers) ────►│  to_dataframe()     │                   │
│                                   │                     │                   │
│                                   ├──► Schema registry  │                   │
│                                   ├──► Concurrent extraction                │
│                                   ├──► TDD-0008 caching │                   │
│                                   └──► polars.DataFrame │                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### struc() Wrapper Implementation

```python
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

def struc(
    self,
    task_type: str | None = None,
    concurrency: int = 10,
    use_cache: bool = True,
) -> "pd.DataFrame":
    """Generate structured dataframe from project tasks.

    .. deprecated:: 1.0.0
        Use `to_dataframe()` instead. `struc()` will be removed in version 2.0.0.

    This method is a compatibility wrapper that calls `to_dataframe()`
    and converts the result to pandas.

    Args:
        task_type: Filter to specific task type (e.g., "Unit", "Contact")
        concurrency: Number of concurrent extraction workers
        use_cache: Whether to use cached struc data

    Returns:
        pandas.DataFrame with extracted task fields
    """
    warnings.warn(
        "struc() is deprecated and will be removed in version 2.0.0. "
        "Use to_dataframe() instead. Migration guide: "
        "https://docs.autom8.dev/migration/struc-to-dataframe",
        DeprecationWarning,
        stacklevel=2,
    )

    # Log caller location for migration tracking
    import traceback
    caller = traceback.extract_stack()[-2]
    self._log.info(
        "struc_deprecated_call",
        caller_file=caller.filename,
        caller_line=caller.lineno,
        caller_function=caller.name,
    )

    # Delegate to new implementation
    polars_df = self.to_dataframe(
        task_type=task_type,
        concurrency=concurrency,
        use_cache=use_cache,
    )

    # Convert to pandas for backward compatibility
    return polars_df.to_pandas()
```

### Deprecation Timeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DEPRECATION TIMELINE                               │
└─────────────────────────────────────────────────────────────────────────────┘

  v1.0.0                v1.1.0                v1.2.0                v2.0.0
    │                     │                     │                     │
    ├─────────────────────┼─────────────────────┼─────────────────────┤
    │                     │                     │                     │
    │  struc() works      │  struc() works      │  struc() works      │  struc()
    │  with soft warning  │  with warning       │  with loud warning  │  REMOVED
    │                     │  (PendingDeprecation)  (DeprecationWarning) │
    │  to_dataframe()     │  to_dataframe()     │  to_dataframe()     │  to_dataframe()
    │  released           │  stable             │  recommended        │  only option
    │                     │                     │                     │
    ▼                     ▼                     ▼                     ▼
```

**Minimum deprecation period**: 2 minor versions (per FR-DF-046)

### Implementation Phases

| Phase | Deliverable | Duration |
|-------|-------------|----------|
| **Phase 1** | Schema definitions (Base, Unit, Contact) | 2-3 days |
| **Phase 2** | Extraction engine with type coercion | 3-4 days |
| **Phase 3** | `to_dataframe()` API on Project/Section | 2-3 days |
| **Phase 4** | Cache integration (STRUC entry type) | 2-3 days |
| **Phase 5** | `struc()` deprecation wrapper | 1 day |
| **Phase 6** | Integration tests + migration guide | 2-3 days |
| **Total** | | **~2-3 weeks** |

### Internal Usage Migration

All internal SDK code using `struc()` will be migrated to `to_dataframe()` in the same release:

```python
# BEFORE: Internal code
df = project.struc()
units = df[df["type"] == "Unit"]

# AFTER: Internal code (same release)
df = project.to_dataframe(task_type="Unit")
units = df  # Already filtered, Polars not pandas
```

External consumers retain backward compatibility via the wrapper.

## Rationale

### Why Big-Bang Over Phased Rollout?

| Factor | Big-Bang | Phased Rollout |
|--------|----------|----------------|
| Codepath complexity | Single codepath | Two codepaths for N releases |
| Testing burden | Test once | Test both paths each release |
| Bug surface | One implementation | Potential divergence bugs |
| Timeline | 2-3 weeks | 2-3 months |
| Team cognitive load | Learn one system | Context-switch between systems |
| Rollback complexity | Revert one release | Complex partial rollback |

Phased rollout would require maintaining both the legacy ThreadManager-based extraction AND the new schema-based extraction for multiple releases. This doubles the testing burden and introduces risk of behavior divergence.

### Why Interface Evolution Over Breaking Change?

| Factor | Interface Evolution | Breaking Change |
|--------|---------------------|-----------------|
| Consumer disruption | None (initially) | Immediate |
| Adoption friction | Low | High |
| Migration timeline | Consumer-controlled | Forced |
| Error handling | Graceful (warnings) | Hard failures |
| Legacy code support | Yes (2+ versions) | No |

Breaking changes force all consumers to update simultaneously. Interface Evolution allows consumers to migrate on their own schedule while receiving clear deprecation guidance.

### Why Accept 2-3 Week Timeline?

The user prioritized "quality over speed":

1. **Schema definitions require accuracy**: Incorrect field mappings cause silent data corruption
2. **Type coercion is subtle**: Edge cases in Asana custom field formats need careful handling
3. **Cache integration is complex**: STRUC entry type must integrate cleanly with TDD-0008
4. **Testing must be comprehensive**: Legacy struc() is battle-tested; replacement must match

Rushing the implementation risks data quality issues that would undermine trust in the new API.

### Why Polars Over Pandas Compatibility?

PRD-0003 explicitly chose Polars for the new API (user decision). The `struc()` wrapper provides pandas compatibility for legacy consumers, but the primary API returns Polars:

- **Performance**: Polars is 10-100x faster for common operations
- **Memory**: Polars is more memory-efficient (lazy evaluation, Arrow backend)
- **Type safety**: Polars has stricter typing than pandas
- **Future-proof**: Polars is the direction of the Python data ecosystem

Consumers who need pandas can call `.to_pandas()` on the result.

## Alternatives Considered

### Alternative 1: Phased Field Migration

- **Description**: Migrate one field (or field group) at a time. Release v1.0 with 5 fields on new system, v1.1 with 10 fields, etc.
- **Pros**:
  - Lowest risk per release
  - Easy to validate each field independently
  - Can pause migration if issues arise
- **Cons**:
  - Requires field-level routing logic ("is this field on new or old system?")
  - Testing complexity increases with each partial state
  - Extended timeline (months vs weeks)
  - Technical debt accumulates during transition
- **Why not chosen**: Complexity of partial implementations outweighs incremental risk reduction. Field extraction is interconnected (e.g., type determines which fields exist).

### Alternative 2: Parallel Client Implementation

- **Description**: Ship `to_dataframe()` as separate API; let consumers choose which to use; never deprecate `struc()`.
- **Pros**:
  - Zero disruption to existing consumers
  - No deprecation warnings
  - Consumers opt-in when ready
- **Cons**:
  - Permanent maintenance of two codepaths
  - Documentation confusion ("which should I use?")
  - No pressure to migrate; legacy code lives forever
  - Divergence risk as systems evolve independently
- **Why not chosen**: Creates permanent technical debt. Legacy `struc()` is tightly coupled to monolith patterns; it should not persist indefinitely.

### Alternative 3: In-Place Breaking Change

- **Description**: Remove `struc()` entirely in v1.0. Consumers must use `to_dataframe()` immediately.
- **Pros**:
  - Cleanest codebase
  - No deprecation wrapper maintenance
  - Forces ecosystem migration
- **Cons**:
  - Breaks all existing consumers on upgrade
  - No migration period
  - User explicitly rejected this approach
  - Violates semantic versioning expectations
- **Why not chosen**: User requirement for backward compatibility (FR-DF-041). Breaking changes should be major version bumps with advance notice.

### Alternative 4: Incremental Type Migration

- **Description**: Migrate one task type at a time (Unit first, then Contact, then others).
- **Pros**:
  - Bounded scope per release
  - Can validate type-specific extraction independently
  - Natural chunking aligned with schema definitions
- **Cons**:
  - Requires type-based routing in `struc()`
  - Mixed behavior depending on task type
  - Extended timeline for full migration
  - User must track which types are "new" vs "old"
- **Why not chosen**: MVP already limits scope to Unit + Contact. Full big-bang within that scope is simpler than per-type phasing.

### Alternative 5: Feature Flag Gradual Rollout

- **Description**: Feature flag controls whether `struc()` uses old or new implementation. Gradually increase percentage.
- **Pros**:
  - Production testing with real traffic
  - Instant rollback via flag
  - A/B comparison possible
- **Cons**:
  - Both codepaths must exist and be tested
  - Feature flag infrastructure complexity
  - Potential for inconsistent results during rollout
  - Debugging difficulty when behavior differs by flag state
- **Why not chosen**: Overkill for dataframe generation. Comprehensive integration tests provide sufficient confidence without production A/B.

## Consequences

### Positive

- **Clean transition**: Single release contains complete new implementation
- **Backward compatibility**: `struc()` continues working for minimum 2 minor versions
- **Clear migration path**: Deprecation warnings include documentation links
- **No dual maintenance**: After release, only one extraction codepath exists
- **Performance improvement**: Polars + schema-based extraction expected 20-30% faster
- **Type safety**: Schema definitions provide explicit typing vs legacy Any returns
- **Migration tracking**: Caller logging enables identifying remaining struc() consumers

### Negative

- **Initial testing burden**: Must validate entire extraction pipeline before release
- **Wrapper overhead**: `struc()` callers pay small overhead for polars-to-pandas conversion
- **No incremental validation**: Cannot ship partial implementation for early feedback
- **Documentation dual-path**: Must document both APIs during deprecation period
- **Consumer migration required**: Eventually, all consumers must update code

### Neutral

- **Polars dependency**: New dependency on Polars (user chose this; not a regression)
- **Schema versioning**: Cached struc includes schema version; migration logic needed if schema changes
- **MVP scope**: Only Unit + Contact initially; other types require additional work post-MVP

## Compliance

To ensure this decision is followed:

### Code Review Checklist

- [ ] New extraction code uses schema-based architecture, not legacy patterns
- [ ] `struc()` is a thin wrapper calling `to_dataframe()` + `.to_pandas()`
- [ ] Deprecation warning includes version and migration guide URL
- [ ] Caller location logged for migration tracking
- [ ] No new code calls `struc()` internally (use `to_dataframe()`)

### Testing Requirements

- [ ] Integration tests cover `to_dataframe()` for Unit and Contact types
- [ ] Integration tests verify `struc()` wrapper produces equivalent results
- [ ] Deprecation warning emission verified in test
- [ ] Type coercion tests for all 32 MVP fields
- [ ] Cache integration tests with mocked TDD-0008 infrastructure

### Documentation Requirements

- [ ] Migration guide at `/docs/guides/struc-to-dataframe.md`
- [ ] API reference updated with deprecation notices
- [ ] CHANGELOG includes deprecation announcement
- [ ] Release notes explain migration path

### Monitoring Requirements

- [ ] Log struc() deprecated calls with caller location
- [ ] Dashboard for struc() vs to_dataframe() call ratio
- [ ] Alert if struc() usage increases (indicates migration regression)
- [ ] Track extraction latency for both methods during deprecation period

### Deprecation Enforcement

- [ ] v1.0.0: `struc()` emits `PendingDeprecationWarning`
- [ ] v1.1.0: `struc()` emits `DeprecationWarning`
- [ ] v1.2.0: `struc()` emits `DeprecationWarning` with "removal imminent" message
- [ ] v2.0.0: `struc()` removed; `AttributeError` if called
