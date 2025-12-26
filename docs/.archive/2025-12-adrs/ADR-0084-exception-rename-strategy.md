# ADR-HARDENING-A-001: Exception Rename Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: SDK Team
- **Related**: PRD-HARDENING-A, TDD-HARDENING-A

## Context

The SDK's `persistence/exceptions.py` module defines a `ValidationError` exception class that conflicts with `pydantic.ValidationError`. Since the SDK uses Pydantic extensively, and many consumers also use Pydantic directly, this creates import shadowing issues:

```python
# Problem: which ValidationError?
from pydantic import ValidationError as PydanticValidationError  # Must alias
from autom8_asana.persistence import ValidationError  # Or this one

# User confusion when catching exceptions
try:
    task.name = 123  # Pydantic validation
except ValidationError:  # Which one catches this?
    pass
```

The SDK must rename `ValidationError` to eliminate this conflict while maintaining backward compatibility for existing users who catch `ValidationError` from persistence exceptions.

### Forces at Play

1. **Import clarity**: Developers should not need to alias imports when using SDK with Pydantic
2. **Semantic accuracy**: The exception validates GID format, not general validation
3. **Backward compatibility**: Existing `except ValidationError` handlers must continue working
4. **Deprecation signaling**: Users should be guided to migrate to the new name
5. **No breaking changes**: PRD constraint prohibits breaking the public API

## Decision

**Rename `ValidationError` to `GidValidationError` with a backward-compatible alias that emits a deprecation warning on class access.**

### Implementation

```python
# persistence/exceptions.py

class GidValidationError(SaveOrchestrationError):
    """Raised when entity GID validation fails at track time.

    Per ADR-0049: Fail-fast on invalid GIDs.
    Per FR-VAL-001: Validate GID format at track() time.
    """
    pass


# Backward compatibility with deprecation warning
class _DeprecatedValidationErrorMeta(type):
    """Metaclass that warns on ValidationError access."""

    def __getattribute__(cls, name: str) -> Any:
        import warnings
        warnings.warn(
            "ValidationError is deprecated. Use GidValidationError instead. "
            "ValidationError will be removed in v2.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return super().__getattribute__(name)


class ValidationError(GidValidationError, metaclass=_DeprecatedValidationErrorMeta):
    """Deprecated alias for GidValidationError.

    .. deprecated:: 1.x
        Use :class:`GidValidationError` instead.
    """
    pass
```

### Export Strategy

```python
# persistence/__init__.py
__all__ = [
    # ... existing exports ...
    "GidValidationError",      # New canonical name (FR-EXC-004)
    "ValidationError",          # Deprecated alias for backward compat
    "PositioningConflictError", # Missing export (FR-EXC-003)
]

# Root __init__.py (optional convenience export)
from autom8_asana.persistence.exceptions import GidValidationError
```

## Rationale

The metaclass approach was chosen because it:

1. **Warns on any usage** - catches `except ValidationError`, `isinstance(e, ValidationError)`, attribute access
2. **Maintains inheritance** - `except GidValidationError` catches both old and new
3. **Zero runtime overhead** - warning only fires when deprecated class is actually accessed
4. **Clear migration path** - warning message provides actionable guidance

## Alternatives Considered

### Alternative 1: Simple Class Alias Without Warning

- **Description**: `ValidationError = GidValidationError` (no warning)
- **Pros**: Simplest implementation, zero overhead, silent migration
- **Cons**: Users never know they should migrate; alias lives forever
- **Why not chosen**: Perpetuates technical debt without signaling deprecation

### Alternative 2: Warning in `__init__` Only

- **Description**: Override `__init__` to warn when exception is instantiated
- **Pros**: Simpler than metaclass, warns on raise
- **Cons**: Does NOT warn on `except ValidationError` or `isinstance` checks
- **Why not chosen**: Misses the primary use case (catching exceptions)

### Alternative 3: Rename to `EntityValidationError`

- **Description**: Use broader name `EntityValidationError`
- **Pros**: More future-proof if we add non-GID validation
- **Cons**: Less specific, GID validation is the actual purpose
- **Why not chosen**: `GidValidationError` accurately describes current and intended scope

### Alternative 4: Module-Level `__getattr__` for Lazy Warning

- **Description**: Use module `__getattr__` to warn on `from module import ValidationError`
- **Pros**: No metaclass complexity
- **Cons**: Only warns on import, not on `except` clauses or isinstance checks
- **Why not chosen**: Incomplete coverage of deprecation scenarios

## Consequences

### Positive

- **No import conflicts**: `from pydantic import ValidationError` works cleanly alongside SDK
- **Semantic clarity**: Exception name describes its purpose (GID validation)
- **Smooth migration**: Existing code continues to work with deprecation warnings
- **Future-proof**: Alias can be removed in v2.0 with advance notice

### Negative

- **Metaclass complexity**: Adds subtle Python magic that may confuse contributors
- **Warning noise**: Existing users see deprecation warnings until they migrate
- **Documentation updates**: All references to `ValidationError` must be updated

### Neutral

- **Testing**: Tests must be updated to use `GidValidationError` and verify alias behavior
- **Type hints**: Type checkers treat `ValidationError` as `GidValidationError` (correct behavior)

## Compliance

To ensure this decision is followed:

1. **PR checklist**: Verify no new code uses `ValidationError` (use `GidValidationError`)
2. **Linting**: Consider adding a custom lint rule to flag `ValidationError` usage
3. **Documentation**: SDK guide and docstrings reference `GidValidationError`
4. **Tests**: Add test verifying deprecation warning is emitted

## Migration Guide

```python
# Before (deprecated)
from autom8_asana.persistence import ValidationError

try:
    session.track(entity)
except ValidationError as e:
    handle_validation_error(e)

# After (recommended)
from autom8_asana.persistence import GidValidationError

try:
    session.track(entity)
except GidValidationError as e:
    handle_validation_error(e)
```

Both patterns work; the first emits a deprecation warning.
