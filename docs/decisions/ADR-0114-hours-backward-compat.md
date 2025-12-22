# ADR-0114: Hours Model Backward Compatibility Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-18
- **Deciders**: Architect, Engineering Lead
- **Related**: PRD-0024, TDD-CUSTOM-FIELD-REMEDIATION

## Context

The Hours model requires fundamental changes per PRD-0024:

1. **Field name changes**: "Monday Hours" -> "Monday" (for all 6 days)
2. **Type changes**: text -> multi_enum (returns `list[str]` instead of `str | None`)
3. **Field removal**: Timezone, Hours Notes, Sunday Hours don't exist in Asana

The Hours model is used by consuming code that expects:
- `hours.monday_hours` property (snake_case with `_hours` suffix)
- String return type (`str | None`)
- Properties like `hours.timezone` and `hours.sunday_hours`

We must choose between:
- **Clean break**: Rename properties, change types, remove stale - all at once
- **Parallel properties**: Keep old names alongside new (maintenance burden)
- **Deprecated aliases**: New names are primary, old names emit deprecation warnings

## Decision

**Deprecated aliases with clean break on types.**

1. **Primary properties**: Use new names (`monday`, `tuesday`, etc.) with correct return types (`list[str]`)
2. **Deprecated aliases**: Old names (`monday_hours`, etc.) emit `DeprecationWarning` and delegate to new properties
3. **No type compatibility**: Old aliases return new types (breaking change for consumers expecting `str`)
4. **Stale removal**: Remove `timezone`, `hours_notes`, `sunday_hours` entirely (no aliases)

```python
@property
def monday(self) -> list[str]:
    """Monday operating hours (multi-enum time values)."""
    return self._get_multi_enum_field(self.Fields.MONDAY)

@property
def monday_hours(self) -> list[str]:
    """Deprecated: Use .monday instead."""
    import warnings
    warnings.warn(
        "monday_hours is deprecated, use monday instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return self.monday
```

## Rationale

1. **Consumer discovery**: Deprecation warnings make migration path obvious
2. **Type safety**: Returning correct types prevents silent data loss
3. **Clean future**: Single code path (new properties), aliases are pure delegation
4. **Test visibility**: Consuming code that uses old names will see warnings in test output
5. **Stale fields are breaking regardless**: No way to provide compatibility for fields that don't exist

The alternative of returning `str` from deprecated aliases would perpetuate the incorrect behavior (joining list elements?) or lose data (returning first element only).

## Alternatives Considered

### Alternative 1: Clean Break (No Aliases)

- **Description**: Remove old property names entirely. Rename to new names, change types.
- **Pros**: Simplest implementation, no maintenance burden
- **Cons**: Silent breakage for consumers who don't read changelogs
- **Why not chosen**: No migration path; consumers discover breakage at runtime

### Alternative 2: Parallel Properties Forever

- **Description**: Keep both `monday_hours` (returning `str`) and `monday` (returning `list[str]`)
- **Pros**: Full backward compatibility
- **Cons**: Maintenance burden, type confusion, never-ending dual API
- **Why not chosen**: Perpetuates incorrect types indefinitely; `monday_hours` returning `str` when Asana stores `list` is lossy

### Alternative 3: Type-Compatible Aliases

- **Description**: Deprecated aliases that convert `list[str]` to `str` (e.g., `", ".join()`)
- **Pros**: Old code "works" (may compile/run)
- **Cons**: Semantic change (was hours string, now joined time strings), potential data confusion
- **Why not chosen**: "Compatible" return value doesn't mean same semantics; likely causes more confusion

## Consequences

### Positive
- Consumers get clear deprecation warnings pointing to correct usage
- Type safety restored - no more silent data loss
- Single code path simplifies maintenance
- Migration path is explicit and testable

### Negative
- Breaking change for return types (unavoidable given Asana reality)
- Consumers must update code to handle `list[str]` instead of `str | None`
- Tests using old names will emit warnings (noise, but also visibility)

### Neutral
- Documentation must clearly state migration path
- Changelog must highlight breaking changes

## Deprecation Schedule

Per TDD-SPRINT-5-CLEANUP (FR-INH-005 Resolution):

| Version | Action | Timeline |
|---------|--------|----------|
| **1.x (Current)** | Aliases emit `DeprecationWarning` | Now |
| **2.0 (Next Major)** | Remove aliases entirely | TBD |

**Migration Path for Consumers:**

1. Update property names: `hours.monday_hours` -> `hours.monday`
2. Update type handling: `str | None` -> `list[str]`
3. Update logic for multi-value fields (opening/closing times as separate list elements)

**Example Migration:**
```python
# Before (deprecated)
opening = hours.monday_hours  # Returns list[str], not str!

# After (correct)
times = hours.monday  # Returns list[str] like ["08:00:00", "17:00:00"]
opening = times[0] if times else None
closing = times[-1] if len(times) > 1 else None
```

## Compliance

- [ ] PRD-0024 requirements met
- [ ] TDD-CUSTOM-FIELD-REMEDIATION references this ADR
- [ ] TDD-SPRINT-5-CLEANUP references this ADR
- [ ] Deprecation warnings use `DeprecationWarning` category
- [ ] Unit tests verify warnings are emitted
- [ ] Changelog documents migration path
- [ ] Deprecation schedule added (Sprint 5)
