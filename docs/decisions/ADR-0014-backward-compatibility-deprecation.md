# ADR-0014: Backward Compatibility and Deprecation

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0114
- **Related**: reference/DATA-MODEL.md

## Context

The Hours model requires fundamental changes based on actual Asana API field structure:

1. **Field name changes**: "Monday Hours" -> "Monday" (for all 6 days)
2. **Type changes**: text -> multi_enum (returns `list[str]` instead of `str | None`)
3. **Field removal**: Timezone, Hours Notes, Sunday Hours don't exist in Asana

The Hours model is used by consuming code that expects:
- `hours.monday_hours` property (snake_case with `_hours` suffix)
- String return type (`str | None`)
- Properties like `hours.timezone` and `hours.sunday_hours`

This represents a broader pattern: how should the SDK handle breaking changes when the underlying API reality doesn't match legacy assumptions?

## Decision

**Implement deprecated aliases with clean break on types.**

### Deprecation Strategy

1. **Primary properties**: Use new names (`monday`, `tuesday`, etc.) with correct return types (`list[str]`)
2. **Deprecated aliases**: Old names (`monday_hours`, etc.) emit `DeprecationWarning` and delegate to new properties
3. **No type compatibility**: Old aliases return new types (breaking change for consumers expecting `str`)
4. **Stale removal**: Remove fields that don't exist in Asana entirely (no aliases)

### Implementation

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

### Deprecation Schedule

| Version | Action | Timeline |
|---------|--------|----------|
| **1.x (Current)** | Aliases emit `DeprecationWarning` | Now |
| **2.0 (Next Major)** | Remove aliases entirely | TBD |

### Migration Path for Consumers

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

## Rationale

### Why Deprecated Aliases?

1. **Consumer discovery**: Deprecation warnings make migration path obvious
2. **Type safety**: Returning correct types prevents silent data loss
3. **Clean future**: Single code path (new properties), aliases are pure delegation
4. **Test visibility**: Consuming code that uses old names will see warnings in test output

### Why No Type Compatibility?

The alternative of returning `str` from deprecated aliases would either:
- **Perpetuate incorrect behavior**: Joining list elements (`", ".join(times)`) loses semantic meaning
- **Lose data**: Returning first element only discards closing time

Neither option is acceptable. Better to break explicitly with clear deprecation than maintain incorrect behavior.

### Why Stale Fields Are Removed Entirely?

Fields like `timezone`, `hours_notes`, and `sunday_hours` don't exist in Asana. No compatibility is possible:
- Can't return meaningful data (doesn't exist)
- Returning `None` forever is confusing (implies optional, not non-existent)
- Better to fail with `AttributeError` than silently return `None`

## Alternatives Considered

### Alternative 1: Clean Break (No Aliases)

- **Description**: Remove old property names entirely. Rename to new names, change types.
- **Pros**: Simplest implementation; no maintenance burden; clear API
- **Cons**: Silent breakage for consumers who don't read changelogs; no migration path
- **Why not chosen**: No migration path - consumers discover breakage at runtime

### Alternative 2: Parallel Properties Forever

- **Description**: Keep both `monday_hours` (returning `str`) and `monday` (returning `list[str]`)
- **Pros**: Full backward compatibility; consumers can migrate at own pace
- **Cons**: Maintenance burden; type confusion; never-ending dual API; `monday_hours` returning `str` when Asana stores `list` is lossy
- **Why not chosen**: Perpetuates incorrect types indefinitely

### Alternative 3: Type-Compatible Aliases

- **Description**: Deprecated aliases that convert `list[str]` to `str` (e.g., `", ".join()`)
- **Pros**: Old code "works" (may compile/run); no immediate breakage
- **Cons**: Semantic change (was hours string, now joined time strings); potential data confusion; "compatible" return value doesn't mean same semantics
- **Why not chosen**: Likely causes more confusion than explicit break

### Alternative 4: Immediate Removal Without Deprecation

- **Description**: Remove incorrect fields immediately with breaking version bump
- **Pros**: Clean codebase immediately; no technical debt; forces consumers to fix code
- **Cons**: Too disruptive; no grace period; violates semantic versioning expectations
- **Why not chosen**: Deprecation period provides better user experience

## Consequences

### Positive

- **Consumers get clear deprecation warnings**: Pointing to correct usage
- **Type safety restored**: No more silent data loss
- **Single code path**: Simplifies maintenance
- **Migration path is explicit**: And testable
- **Aligns with API reality**: Models match actual Asana field structure
- **Future-proof**: New properties match Asana's multi-enum type

### Negative

- **Breaking change for return types**: Unavoidable given Asana reality
- **Consumers must update code**: To handle `list[str]` instead of `str | None`
- **Tests using old names will emit warnings**: Noise, but also visibility
- **Documentation burden**: Must clearly state migration path
- **Changelog visibility**: Must highlight breaking changes

### Neutral

- **Deprecation warnings are temporary**: Removed in v2.0
- **Standard pattern**: Follows semantic versioning conventions
- **Two-phase migration**: Deprecation warnings first, removal second

## Compliance

### Deprecation Standards

1. **Use `DeprecationWarning` category**: For all deprecated properties
2. **Set `stacklevel=2`**: So warning points to caller, not property implementation
3. **Clear message format**: "X is deprecated, use Y instead"
4. **Unit tests verify warnings**: Ensure warnings are emitted correctly

### Documentation Requirements

1. **Changelog documents migration path**: With before/after examples
2. **Deprecation schedule added**: In release notes
3. **Migration guide**: Step-by-step instructions for consumers
4. **API documentation**: Marks deprecated properties with clear replacement guidance

### Code Review Checklist

When implementing backward compatibility:
- [ ] Deprecated properties emit `DeprecationWarning`
- [ ] Warning message includes replacement property name
- [ ] New properties use correct types matching Asana API
- [ ] Deprecated properties delegate to new properties (no duplicate logic)
- [ ] Non-existent fields removed entirely (no returning `None` placeholders)
- [ ] Unit tests cover both deprecated and new properties
- [ ] Changelog documents breaking changes with migration examples
- [ ] Deprecation schedule documented

### Version Planning

**For 1.x releases:**
- Maintain deprecated aliases
- Emit clear warnings
- Document migration path
- Gather feedback on migration difficulty

**For 2.0 release:**
- Remove all deprecated aliases
- Clean up warning emission code
- Update documentation to reflect final API
- Provide comprehensive upgrade guide

## Related Patterns

This deprecation pattern applies beyond the Hours model:

1. **Field name changes**: Use deprecated aliases pointing to new names
2. **Type changes**: Return correct type from aliases, accept breaking change
3. **Field removal**: Remove entirely if doesn't exist in API
4. **Migration window**: One major version deprecation period minimum

### Template for Deprecated Property

```python
@property
def new_name(self) -> CorrectType:
    """Primary property with correct type."""
    return self._get_field(self.Fields.NEW_NAME)

@property
def old_name(self) -> CorrectType:  # Note: Returns NEW type
    """Deprecated: Use .new_name instead."""
    import warnings
    warnings.warn(
        "old_name is deprecated, use new_name instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return self.new_name
```

### Changelog Entry Template

```markdown
## [1.x.0] - YYYY-MM-DD

### Changed (Breaking in v2.0)

**Hours Model Field Updates**

The following Hours model properties have been renamed to match Asana API field names:

- `monday_hours` -> `monday` (returns `list[str]`)
- `tuesday_hours` -> `tuesday` (returns `list[str]`)
- ... (etc)

**Migration Required:**

Old code:
```python
opening = hours.monday_hours  # Deprecated, emits warning
```

New code:
```python
times = hours.monday
opening = times[0] if times else None
closing = times[-1] if len(times) > 1 else None
```

Deprecated properties will be removed in v2.0. Update code before upgrading.

### Removed

**Non-existent Fields:**

The following properties have been removed as they do not exist in Asana:
- `timezone`
- `hours_notes`
- `sunday_hours`

These fields were never populated and have been removed entirely.
```
