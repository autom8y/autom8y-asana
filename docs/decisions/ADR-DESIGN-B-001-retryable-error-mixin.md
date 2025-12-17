# ADR-DESIGN-B-001: RetryableErrorMixin for Error Classification

| Metadata | Value |
|----------|-------|
| Status | Accepted |
| Date | 2024-12-16 |
| Decision Makers | Principal Engineer, Architect |
| Initiative | DESIGN-PATTERNS-B |
| Supersedes | N/A |
| Related | ADR-0079 (Retryable Error Classification) |

## Context

### Problem Statement

`SaveError` and `ActionResult` in `/src/autom8_asana/persistence/models.py` contained nearly identical error classification logic:

1. **`is_retryable`** property (~30 lines each): Network error detection, status code extraction, 429/5xx classification
2. **`recovery_hint`** property (~40 lines each): Status-specific recovery guidance
3. **`retry_after_seconds`** property (~5 lines each): Rate limit backoff extraction
4. **`_extract_status_code`** helper (~15 lines each): Status code extraction from various error types

**Total duplication**: ~180 lines (90 lines x 2 classes)

This duplication violated DRY principles and created maintenance burden:
- Bug fixes needed in two places
- Recovery hints could drift out of sync
- New error types required updates in multiple files

### Requirements

| ID | Requirement |
|----|-------------|
| R-1 | Eliminate duplication of error classification logic |
| R-2 | Maintain 100% behavioral equivalence |
| R-3 | Zero breaking changes to public API |
| R-4 | Existing tests must pass without modification |
| R-5 | Pattern must be reusable for future result types |

## Decision

Implement a **RetryableErrorMixin** class that provides error classification behavior through composition.

### Key Design Choices

1. **Mixin Pattern over Inheritance**: Uses mixin rather than base class to avoid complicating the dataclass inheritance hierarchy.

2. **Protocol for Contract**: `HasError` protocol defines the `_get_error()` contract that implementers must satisfy.

3. **Static Method for Extraction**: `_extract_status_code` is a static method to enable testing in isolation.

4. **Lazy Import for AsanaError**: Maintains lazy import pattern to avoid circular dependencies.

## Implementation

### New Module Structure

```
src/autom8_asana/patterns/
    __init__.py          # Exports HasError, RetryableErrorMixin
    error_classification.py  # Implementation
```

### HasError Protocol

```python
@runtime_checkable
class HasError(Protocol):
    """Protocol for types that may contain an error."""

    @abstractmethod
    def _get_error(self) -> Exception | None:
        """Return the error if present, None otherwise."""
        ...
```

### RetryableErrorMixin

```python
class RetryableErrorMixin:
    """Mixin providing error classification and recovery hints."""

    @abstractmethod
    def _get_error(self) -> Exception | None:
        """Return the error if present."""
        ...

    @property
    def is_retryable(self) -> bool: ...

    @property
    def recovery_hint(self) -> str: ...

    @property
    def retry_after_seconds(self) -> int | None: ...

    @staticmethod
    def _extract_status_code(error: Exception) -> int | None: ...
```

### Updated SaveError

```python
@dataclass
class SaveError(RetryableErrorMixin):
    entity: AsanaResource
    operation: OperationType
    error: Exception
    payload: dict[str, Any]

    def _get_error(self) -> Exception | None:
        return self.error
```

### Updated ActionResult

```python
@dataclass
class ActionResult(RetryableErrorMixin):
    action: ActionOperation
    success: bool
    error: Exception | None = None
    response_data: dict[str, Any] | None = None

    def _get_error(self) -> Exception | None:
        if self.success:
            return None
        return self.error
```

## Consequences

### Positive

1. **Single Source of Truth**: Error classification logic exists in one place
2. **Lines Saved**: ~90 lines removed from `models.py`
3. **Consistency**: Recovery hints guaranteed to be identical
4. **Testability**: Mixin can be tested in isolation with 48 dedicated tests
5. **Extensibility**: New result types get error classification for free
6. **Maintainability**: Bug fixes applied once, propagate everywhere

### Negative

1. **Additional Module**: New `patterns/` module adds to codebase surface area
2. **Indirection**: `_get_error()` adds one level of indirection
3. **Learning Curve**: Developers must understand mixin pattern

### Neutral

1. **MRO Complexity**: Python's MRO handles mixin + dataclass correctly
2. **Type Checking**: mypy handles mixin types correctly

## Alternatives Considered

### Alternative 1: Base Class Inheritance

```python
class ClassifyableError:
    error: Exception | None

    @property
    def is_retryable(self) -> bool: ...

class SaveError(ClassifyableError):
    ...
```

**Rejected**: Complicates dataclass inheritance; SaveError and ActionResult have different shapes.

### Alternative 2: Composition with Helper Object

```python
@dataclass
class SaveError:
    error: Exception
    _classifier: ErrorClassifier = field(default_factory=ErrorClassifier)

    @property
    def is_retryable(self) -> bool:
        return self._classifier.is_retryable(self.error)
```

**Rejected**: Adds runtime overhead and complicates serialization.

### Alternative 3: Free Functions

```python
def is_retryable(error: Exception) -> bool: ...
def recovery_hint(error: Exception) -> str: ...
```

**Rejected**: Changes public API; users expect properties on error objects.

## Validation

### Test Coverage

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_error_classification.py` | 48 | PASS |
| `test_models.py` (SaveError) | 22 | PASS |
| `test_models.py` (ActionResult) | 11 | PASS |
| Full persistence suite | 129 | PASS |

### Behavioral Equivalence Verified

All existing tests pass without modification, proving:
- `is_retryable` returns identical values
- `recovery_hint` returns compatible strings (keyword matches preserved)
- `retry_after_seconds` extracts correctly

## References

- [ADR-0079: Retryable Error Classification](./ADR-0079-retryable-error-classification.md)
- [DESIGN-PATTERN-OPPORTUNITIES.md](../architecture/DESIGN-PATTERN-OPPORTUNITIES.md) - Opportunity 4
- [Initiative PROMPT-0-INITIATIVE-B](../initiatives/PROMPT-0-INITIATIVE-B.md)
