# ADR-0011: Deprecation Warning Strategy for Compatibility Layer

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md) (FR-COMPAT-002), [TDD-0006](../design/TDD-0006-backward-compatibility.md)

## Context

The autom8_asana SDK provides a compatibility layer (`_compat.py`) that allows legacy import paths to continue working during migration. We need to:

1. Warn users that these imports are deprecated
2. Guide them to the correct canonical import paths
3. Allow filtering/promotion of warnings (CI can fail on deprecation warnings)
4. Not break existing code immediately

Python provides several mechanisms for deprecation:
- `warnings.warn()` with various warning categories
- Logging at WARNING level
- Custom decorators that raise exceptions
- Documentation-only (no runtime indicator)

We need to choose the right approach for import-time deprecation warnings.

## Decision

**Use `warnings.warn()` with `DeprecationWarning` category and lazy `__getattr__` imports.**

Implementation:

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

Key design choices:

1. **`DeprecationWarning` category**: Standard Python category for deprecations. Filtered by default in `__main__` but shown in tests.

2. **Lazy `__getattr__`**: Only warns when the attribute is actually used, not at module import time. This means `import autom8_asana.compat` alone doesn't warn.

3. **`stacklevel=3`**: Points the warning to the user's code, not the compat module internals.

4. **Removal version in message**: Clear timeline (v1.0.0) for when aliases will be removed.

## Rationale

`warnings.warn()` with `DeprecationWarning` is the standard Python mechanism because:

1. **Standard Behavior**: Python developers expect deprecation warnings to use this pattern. It's documented in PEP 565.

2. **Filterable**: Teams can configure warning behavior:
   ```python
   # Show all deprecation warnings
   warnings.filterwarnings("always", category=DeprecationWarning)

   # Treat as errors (fail CI)
   warnings.filterwarnings("error", category=DeprecationWarning)

   # Ignore specific warnings
   warnings.filterwarnings("ignore", module="autom8_asana.compat")
   ```

3. **Test Visibility**: pytest shows `DeprecationWarning` by default in test runs, helping teams catch deprecated usage during development.

4. **Lazy Imports Prevent Spam**: Using `__getattr__` means warnings only appear when deprecated names are actually accessed, not on every import of the compat module.

5. **Correct Stack Level**: `stacklevel=3` ensures the warning points to the user's import statement, not internal SDK code.

## Alternatives Considered

### Logging at WARNING Level

- **Description**: Use `logging.getLogger().warning()` instead of `warnings.warn()`
- **Pros**:
  - Always visible (not filtered by default)
  - Integrates with existing logging infrastructure
- **Cons**:
  - Not filterable per-module
  - Can't be promoted to errors for strict CI
  - Non-standard for deprecation
  - Pollutes logs on every import
- **Why not chosen**: Not the standard Python deprecation mechanism; harder to filter

### Eager Imports with Module-Level Warning

- **Description**: Import and re-export everything at module level, warn on module import
- **Pros**:
  - Simpler implementation
  - Warning on first `import autom8_asana.compat`
- **Cons**:
  - Warns even if user doesn't use deprecated names
  - Can't distinguish which names are being used
  - Import-time side effects are discouraged
- **Why not chosen**: Too aggressive; warns even for legitimate exploratory imports

### FutureWarning Instead of DeprecationWarning

- **Description**: Use `FutureWarning` which is shown by default
- **Pros**:
  - Visible without configuration
  - Explicitly for "deprecated features"
- **Cons**:
  - `FutureWarning` is for end-users, `DeprecationWarning` is for developers
  - pytest captures both anyway
  - Would spam production logs
- **Why not chosen**: `DeprecationWarning` is semantically correct for library API deprecation

### Custom DeprecationMeta Class

- **Description**: Create a metaclass that wraps all class access with warnings
- **Pros**:
  - More control over warning behavior
  - Could track usage statistics
- **Cons**:
  - Over-engineered for simple import aliasing
  - Metaclass complexity
  - Potential performance impact
- **Why not chosen**: `__getattr__` is simpler and sufficient

### Documentation-Only Deprecation

- **Description**: Mark as deprecated in docs but no runtime warning
- **Pros**:
  - No runtime overhead
  - No warning noise
- **Cons**:
  - Users don't discover deprecation until reading docs
  - Can't automate migration detection
  - Easy to miss
- **Why not chosen**: Users need runtime feedback to discover deprecated usage

## Consequences

### Positive

- **Standard Python pattern**: Developers recognize and understand DeprecationWarning
- **CI integration**: Teams can fail builds on deprecation warnings
- **Test visibility**: pytest shows warnings, catching deprecated usage early
- **Lazy evaluation**: Only warns when deprecated names are actually used
- **Clear migration path**: Warning message includes canonical import path
- **Timeline clarity**: Removal version (1.0.0) is explicit in message

### Negative

- **Hidden by default in scripts**: `DeprecationWarning` is filtered in `__main__` by default (users must enable)
- **Requires Python knowledge**: Some users may not know how to configure warnings
- **Stack level fragility**: `stacklevel=3` assumes specific call depth; refactoring could break it

### Neutral

- **One warning per import**: Each deprecated import warns once (default behavior)
- **Compat module remains importable**: `import autom8_asana.compat` succeeds without warning (only attribute access warns)

## Compliance

To ensure this decision is followed:

1. **Unit tests**: Verify each alias emits correct warning with correct message and stacklevel
2. **CI configuration**: Run tests with `-W error::DeprecationWarning` to catch any deprecated usage in SDK itself
3. **Documentation**: Migration guide explains warning filtering options
4. **Code review**: Any new compat aliases must follow this pattern
