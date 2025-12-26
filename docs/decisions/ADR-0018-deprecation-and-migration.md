# ADR-0018: Deprecation and Migration Strategies

## Metadata

- **Status**: Accepted (ADR-0027 Completed in v2.0.0)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0011, ADR-0025, ADR-0027, ADR-0084, ADR-0114
- **Related**: reference/OPERATIONS.md

## Context

SDK evolution requires deprecating legacy APIs and migrating to improved implementations. Common scenarios include:

1. **Compatibility layer**: Legacy import paths (_compat.py) must warn users about deprecation
2. **Cache backend migration**: Transition from S3-backed caching to Redis exclusively
3. **DataFrame API migration**: Replace legacy struc() method (~1,000 lines) with to_dataframe()
4. **Exception naming**: Resolve ValidationError conflict with pydantic.ValidationError
5. **Model compatibility**: Handle fundamental field changes (Hours model)

These migrations must balance:
- **Backward compatibility**: Don't break existing consumer code immediately
- **Clear migration path**: Guide users to updated APIs
- **Clean future**: Enable removal of legacy code without perpetual maintenance
- **Production safety**: Minimize downtime and data loss risks

## Decision

### 1. Deprecation Warning Strategy

**Use warnings.warn() with DeprecationWarning category and lazy __getattr__ imports.**

```python
# _compat.py

import warnings

def __getattr__(name: str):
    """Lazy attribute access with deprecation warnings."""
    if name in _known_aliases:
        warnings.warn(
            f"Importing '{name}' from 'autom8_asana.compat' is deprecated. "
            f"Use '{_known_aliases[name]}' instead. "
            f"This alias will be removed in version 1.0.0.",
            DeprecationWarning,
            stacklevel=3,  # Points to the user's import statement
        )
        # Return the actual class from canonical location
        return _import_from_canonical(name)
    raise AttributeError(f"module 'autom8_asana.compat' has no attribute '{name}'")
```

**Key design choices**:

1. **DeprecationWarning category**: Standard Python category for deprecations; filtered by default in __main__ but shown in tests
2. **Lazy __getattr__**: Only warns when attribute actually used, not at module import time
3. **stacklevel=3**: Points warning to user's code, not compat module internals
4. **Removal version in message**: Clear timeline (v1.0.0) for when aliases will be removed

**Rationale**:
- Standard Python mechanism developers recognize (PEP 565)
- Filterable - teams can configure warning behavior or fail CI on deprecation warnings
- pytest shows DeprecationWarning by default in tests
- Lazy imports prevent spam - only warns when deprecated names accessed
- Correct stack level ensures warning points at user import statement

### 2. Big-Bang Migration Strategy for Infrastructure

**Perform big-bang cutover with no data migration for cache and similar infrastructure changes.**

#### Cache Migration: S3 to Redis

**Accept 100% cache miss rate at deployment, relying on cache warming to rebuild.**

Migration timeline:
```
T-7 days: Provision Redis infrastructure (ElastiCache)
T-3 days: Deploy SDK to staging with Redis
T-1 day:  Performance test in staging
T-0:      Production deployment (cutover)
T+15min:  Monitor cache warm-up
T+1hr:    Verify hit rate stabilizing (target >= 80%)
T+24hr:   Confirm normal operations
T+7 days: Decommission S3 cache
```

**Why big-bang over dual-read?**

| Factor | Big-Bang | Dual-Read |
|--------|----------|-----------|
| Complexity | Low | High |
| Tech debt | None | S3 read code remains |
| Consistency | Single source of truth | Potential conflicts |
| Failure modes | Simple (Redis or nothing) | Complex (S3 vs Redis) |
| Migration length | Days | Weeks/months |
| Team effort | Low | High |

**Rollback plan**:
1. **Immediate (<5 min)**: Disable caching via CacheSettings.enabled = False
2. **Short-term (<30 min)**: Revert SDK deployment to previous version
3. **Investigation**: Analyze cache event logs and Redis metrics

**Monitoring checklist**:

| Metric | Expected at T+0 | Expected at T+1hr | Alert Threshold |
|--------|-----------------|-------------------|-----------------|
| Cache hit rate | 0% | >= 80% | < 70% at T+1hr |
| Redis connection errors | 0 | 0 | > 0 sustained |
| API call rate | +100% vs baseline | Normal | > 150% at T+1hr |
| p99 latency | +50% vs baseline | Normal | > 200% at T+1hr |

**Rationale**:
- Dual-read introduces complexity, tech debt, and consistency issues
- Cache data rebuilds quickly from API
- Big-bang enables clean cutover in days vs weeks
- Temporary performance impact acceptable for long-term simplicity

### 3. Interface Evolution for API Migration

**Replace internals with new implementation in single release; maintain deprecated wrapper.**

#### DataFrame Layer Migration: struc() to to_dataframe()

**Implementation**: Big-bang migration with Interface Evolution. Replace struc() internals with to_dataframe() in single release. Maintain struc() as deprecated wrapper.

```python
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

**Deprecation timeline**:

```
v1.0.0: struc() works with PendingDeprecationWarning
v1.1.0: struc() works with DeprecationWarning
v1.2.0: struc() works with loud DeprecationWarning ("removal imminent")
v2.0.0: struc() REMOVED (AttributeError if called)
```

**Minimum deprecation period**: 2 minor versions

**Implementation completed in v2.0.0**:
- All struc() references removed
- Cache infrastructure renamed: EntryType.STRUC -> EntryType.DATAFRAME
- warm_struc() kept as alias for backward compatibility

**Rationale**:
- Clean cutover - no dual codepath maintenance
- Backward compatibility via wrapper allows gradual consumer migration
- Polars performance benefits (10-100x faster for common operations)
- struc() wrapper provides pandas conversion for legacy consumers
- Caller logging enables identifying remaining struc() consumers for targeted migration

### 4. Exception Rename with Metaclass Deprecation

**Rename ValidationError to GidValidationError; provide backward-compatible alias using metaclass.**

```python
# New semantic name
class GidValidationError(ValueError):
    """Raised when GID format validation fails."""
    pass

# Deprecated alias with metaclass warning
class _DeprecatedMeta(type):
    """Metaclass that emits deprecation warning on class access."""

    def __getattribute__(cls, name):
        if name not in ("__class__", "__mro__"):
            warnings.warn(
                "ValidationError is deprecated and conflicts with pydantic. "
                "Use GidValidationError instead. "
                "This alias will be removed in version 1.0.0.",
                DeprecationWarning,
                stacklevel=2,
            )
        return super().__getattribute__(name)

class ValidationError(GidValidationError, metaclass=_DeprecatedMeta):
    """Deprecated alias for GidValidationError.

    .. deprecated:: 0.9.0
        Use GidValidationError instead.
    """
    pass
```

**Warning fires on**:
- `except ValidationError:` clauses
- `isinstance(e, ValidationError)` checks
- Attribute access on class

**Rationale**:
- Eliminates import conflicts with pydantic.ValidationError
- Semantic clarity - name describes purpose (GID validation specifically)
- Metaclass approach warns on any usage, not just instantiation
- Maintains inheritance - `except GidValidationError` catches both old and new

### 5. Deprecated Aliases with Type Changes

**For fundamental incompatible changes, provide aliases with warnings but return correct types.**

#### Hours Model Compatibility

Field changes:
- **Name changes**: `Monday Hours` -> `Monday` (all days)
- **Type changes**: text field -> multi_enum (returns list[str] instead of str)
- **Field removal**: timezone, hours_notes, sunday_hours don't exist in Asana

```python
class Hours(BusinessEntity):
    # === PRIMARY PROPERTIES (correct types) ===
    monday = MultiEnumField(field_name="Monday")      # list[str]
    tuesday = MultiEnumField(field_name="Tuesday")    # list[str]
    # ... other days

    # === DEPRECATED ALIASES (emit warning, return new types) ===
    @property
    def monday_hours(self) -> list[str]:
        """Deprecated alias for monday.

        .. deprecated:: 0.9.0
            Use `monday` instead. Returns list[str], not str.
        """
        warnings.warn(
            "monday_hours is deprecated. Use 'monday' instead. "
            "Note: Returns list[str] (multi_enum), not str. "
            "This alias will be removed in version 1.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.monday

    # Stale fields REMOVED entirely (no compatibility possible)
    # - timezone (doesn't exist in Asana)
    # - hours_notes (doesn't exist in Asana)
    # - sunday_hours (doesn't exist in Asana)
```

**Rationale**:
- Consumer discovery via deprecation warnings
- Type safety prevents silent data loss
- Returning correct types is unavoidable given Asana reality
- Clean future - single code path after deprecation period
- Stale fields are breaking regardless - no compatibility possible for non-existent fields

## Alternatives Considered

### Alternative A: Dual-Read Fallback for Cache

- **Description**: Read from both S3 and Redis during transition; write only to Redis
- **Pros**: Gradual transition; no initial miss spike
- **Cons**: Complex read logic; S3 code must be maintained; unclear deprecation timeline
- **Why not chosen**: Complexity and tech debt outweigh smoother transition

### Alternative B: Phased Field Migration for struc()

- **Description**: Migrate one field (or field group) at a time over multiple releases
- **Pros**: Lowest risk per release; easy to validate each field
- **Cons**: Field-level routing logic; extended timeline; technical debt during transition
- **Why not chosen**: Complexity of partial implementations outweighs incremental risk reduction

### Alternative C: Documentation-Only Deprecation

- **Description**: Mark as deprecated in docs but no runtime warning
- **Pros**: No runtime overhead; no warning noise
- **Cons**: Users don't discover deprecation until reading docs; can't automate detection
- **Why not chosen**: Users need runtime feedback to discover deprecated usage

### Alternative D: FutureWarning Instead of DeprecationWarning

- **Description**: Use FutureWarning which is shown by default
- **Pros**: Visible without configuration
- **Cons**: FutureWarning is for end-users, DeprecationWarning is for developers; would spam production logs
- **Why not chosen**: DeprecationWarning is semantically correct for library API deprecation

## Consequences

### Positive

- **Standard Python pattern**: Developers recognize DeprecationWarning
- **CI integration**: Teams can fail builds on deprecation warnings
- **Test visibility**: pytest shows warnings, catching deprecated usage early
- **Clear migration path**: Warning messages include canonical import/usage and documentation links
- **Timeline clarity**: Removal version explicit in messages
- **Clean cutover**: Single release contains complete new implementation (no dual maintenance)
- **Migration tracking**: Caller logging enables identifying remaining deprecated usage

### Negative

- **Hidden by default in scripts**: DeprecationWarning filtered in __main__ by default
- **Initial performance impact**: Cache miss spike, struc() wrapper overhead
- **Breaking changes eventual**: Consumers must migrate before removal version
- **Type changes unavoidable**: Hours model returns different types despite aliases

### Neutral

- Big-bang migrations reduce maintenance burden (accept short-term pain for long-term simplicity)
- Minimum 2 minor version deprecation period provides migration runway
- Cache data rebuilds naturally (no migration tooling needed)
- Staging validation reduces production risk

## Implementation Guidance

### When deprecating APIs:

1. Use warnings.warn() with DeprecationWarning category
2. Provide stacklevel to point at user code, not SDK internals
3. Include removal version and migration guidance in warning message
4. Consider lazy __getattr__ to warn only on actual usage
5. Maintain minimum 2 minor version deprecation period
6. Log deprecated calls for migration tracking (if valuable)

### When migrating systems:

1. Default to big-bang with interface evolution over dual-codepath maintenance
2. Accept temporary performance impact for cleaner architecture
3. Provide explicit wrapper/alias for backward compatibility during transition
4. Document migration path clearly with code examples
5. Use staging environment for warm-up validation before production
6. Define clear monitoring metrics and alert thresholds
7. Have rollback plan documented and tested

### When handling incompatible changes:

1. Provide deprecated aliases when possible
2. Return correct types even if breaking (type safety over false compatibility)
3. Emit warnings on alias usage
4. Document type changes in warning message
5. Remove stale fields entirely when no compatibility possible

## Compliance

- [ ] Deprecation warnings use DeprecationWarning category
- [ ] Warning messages include removal version and migration path
- [ ] stacklevel points to user code, not SDK internals
- [ ] Minimum 2 minor version deprecation period maintained
- [ ] Big-bang migrations have documented rollback plans
- [ ] Cache migrations include warm-up procedures
- [ ] Monitoring metrics and alert thresholds defined
- [ ] Staging validation performed before production cutover
- [ ] Migration guides published for breaking changes
- [ ] CHANGELOG includes deprecation announcements
