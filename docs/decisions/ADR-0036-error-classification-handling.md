# ADR-0036: Error Classification & Retryability

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0079 (Retryable Classification), ADR-0084 (Exception Rename), ADR-0091 (Mixin), ADR-0065 (SaveSessionError)
- **Related**: reference/API-INTEGRATION.md

## Context

Users need clear guidance on whether failed operations should be retried or require manual intervention. The SDK returns structured error information in `SaveResult` and `HydrationResult`, but users must inspect raw exceptions to determine retry eligibility.

Common user questions:
- "Can I retry this operation?"
- "Is this a transient failure or permanent error?"
- "Which errors should I log vs. retry vs. escalate?"

Additionally, the SDK's exception hierarchy must avoid naming conflicts with dependencies (Pydantic's `ValidationError`) and provide clear semantic names.

## Decision

### Retryable Error Classification

**Classify errors based on HTTP status code semantics per RFC 7231.**

Add `is_retryable` property to `SaveError` and `ActionResult`:

```python
@dataclass
class SaveError:
    entity: AsanaResource
    operation: OperationType
    error: Exception
    payload: dict[str, Any]

    @property
    def is_retryable(self) -> bool:
        """Determine if this error is potentially retryable.

        Classification based on HTTP status code:
        - 429 (Rate Limit): Retryable after delay
        - 5xx (Server Error): Retryable (transient)
        - 4xx (Client Error): Not retryable (bad request)

        Returns:
            True if error suggests retry may succeed.
        """
        status_code = self._extract_status_code()
        if status_code is None:
            return False  # Unknown errors not retryable

        if status_code == 429:
            return True  # Rate limit - retry after delay

        if 500 <= status_code < 600:
            return True  # Server error - transient

        return False  # Client error - fix required

    def _extract_status_code(self) -> int | None:
        """Extract HTTP status code from error."""
        if isinstance(self.error, AsanaError):
            return self.error.status_code
        if hasattr(self.error, 'status_code'):
            return getattr(self.error, 'status_code')
        return None
```

### Classification Table

| HTTP Status | `is_retryable` | Reason |
|-------------|----------------|--------|
| 400 Bad Request | `False` | Client error - invalid payload |
| 401 Unauthorized | `False` | Authentication error - credential fix needed |
| 403 Forbidden | `False` | Permission error - access grant needed |
| 404 Not Found | `False` | Resource doesn't exist |
| 409 Conflict | `False` | Conflict - manual resolution needed |
| 410+ | `False` | Client errors - fix required |
| **429 Too Many Requests** | `True` | Rate limit - retry after delay |
| **500 Internal Server Error** | `True` | Server error - transient |
| **502 Bad Gateway** | `True` | Server error - transient |
| **503 Service Unavailable** | `True` | Server error - transient |
| **504 Gateway Timeout** | `True` | Server error - transient |

### Exception Taxonomy

**Rename `ValidationError` to `GidValidationError` to avoid Pydantic conflict.**

```python
class GidValidationError(SaveOrchestrationError):
    """Raised when GID format is invalid."""

# Backward-compatible alias with deprecation warning
class ValidationError(GidValidationError, metaclass=DeprecatedExceptionMeta):
    """DEPRECATED: Use GidValidationError instead."""
```

**Metaclass-based deprecation** catches all usage patterns:
- `except ValidationError:` - triggers warning
- `isinstance(exc, ValidationError)` - triggers warning
- `ValidationError.__name__` - triggers warning

**Convenience exception for SaveSession**:

```python
class SaveSessionError(SaveOrchestrationError):
    """Raised when SaveSession convenience methods fail.

    Wraps SaveResult with descriptive message.
    """
    def __init__(self, message: str, result: SaveResult):
        super().__init__(message)
        self.result = result
```

### RetryableErrorMixin (DRY)

**Extract shared classification logic into mixin to eliminate duplication.**

```python
class RetryableErrorMixin:
    """Mixin providing retryability classification."""

    error: Exception  # Type hint for protocol

    @property
    def is_retryable(self) -> bool:
        """Determine if error is retryable based on HTTP status."""
        status_code = self._extract_status_code()
        if status_code is None:
            return False
        if status_code == 429:
            return True
        if 500 <= status_code < 600:
            return True
        return False

    def _extract_status_code(self) -> int | None:
        """Extract HTTP status code from error."""
        if isinstance(self.error, AsanaError):
            return self.error.status_code
        if hasattr(self.error, 'status_code'):
            return getattr(self.error, 'status_code')
        return None

@dataclass
class SaveError(RetryableErrorMixin):
    entity: AsanaResource
    operation: OperationType
    error: Exception
    payload: dict[str, Any]

@dataclass
class ActionResult(RetryableErrorMixin):
    success: bool
    entity: AsanaResource | None
    error: Exception | None
```

**Eliminates ~90 lines of duplication** between `SaveError` and `ActionResult`.

### Convenience Methods on SaveResult

```python
@dataclass
class SaveResult:
    succeeded: list[EntityResult]
    failed: list[SaveError]
    action_results: list[ActionResult]

    @property
    def failed_count(self) -> int:
        """Number of failed operations."""
        return len(self.failed)

    def get_failed_entities(self) -> list[AsanaResource]:
        """Get entities that failed to save."""
        return [error.entity for error in self.failed]

    def get_retryable_errors(self) -> list[SaveError]:
        """Get errors that may be retried."""
        return [error for error in self.failed if error.is_retryable]
```

## Rationale

### Why HTTP Status Code Based?

1. **Standard semantics**: HTTP status codes have well-defined meanings (RFC 7231)
2. **Universal**: All Asana API errors include HTTP status codes
3. **Simple**: No error message parsing or special cases needed
4. **Extensible**: Easy to add new status codes if Asana introduces them

### Why 429 and 5xx as Retryable?

**429 (Rate Limit)**:
- Explicitly designed to be retryable
- Asana returns `Retry-After` header with timing guidance
- Temporary condition resolves with backoff

**5xx (Server Errors)**:
- Indicate server-side issues, not client errors
- Transient by nature (service temporarily unavailable)
- Standard practice to retry with exponential backoff

### Why Not 4xx (Except 429)?

4xx errors indicate client-side problems:
- Retrying the same request produces the same error
- Requires payload fix, permission change, or resource creation
- Wasted effort and API quota to retry

### Why Default to Not Retryable for Unknown?

Conservative approach:
- Assume errors need investigation
- Prevents infinite retry loops on unexpected error types
- Users can override based on domain knowledge

### Why GidValidationError Rename?

**Conflict**: `ValidationError` conflicts with Pydantic's exception used throughout SDK for model validation.

**Clarity**: `GidValidationError` accurately describes purpose (GID format validation).

**Migration**: Metaclass warnings catch all usage patterns while maintaining inheritance.

### Why RetryableErrorMixin?

**DRY principle**: Both `SaveError` and `ActionResult` need identical retryability logic.

**Single source of truth**: Classification logic in one place.

**Extensibility**: Easy to add new error types with retryability.

## Alternatives Considered

### Error Message Pattern Matching

- **Description**: Parse error messages for keywords like "rate limit" or "try again"
- **Pros**: Catches cases where status code doesn't tell full story
- **Cons**: Brittle; Asana can change messages; i18n issues
- **Why not chosen**: Status codes are reliable and standardized

### Whitelist Specific Asana Error Codes

- **Description**: Maintain list of specific Asana error codes that are retryable
- **Pros**: Precise control over classification
- **Cons**: Ongoing maintenance, may miss new codes
- **Why not chosen**: HTTP status codes sufficient and maintenance-free

### User-Provided Classifier Function

- **Description**: Allow users to provide custom `is_retryable` function
- **Pros**: Maximum flexibility
- **Cons**: Complexity, users still need defaults, harder to document
- **Why not chosen**: Over-engineering; sensible defaults sufficient

### Automatic Retry Mechanism

- **Description**: SaveSession automatically retries retryable errors
- **Pros**: Seamless recovery from transient failures
- **Cons**: Scope creep, needs backoff strategy, max attempts, circuit breaker
- **Why not chosen**: Deferred to future; current scope is classification only

### Keep ValidationError Name

- **Description**: Accept conflict with Pydantic
- **Pros**: No migration needed
- **Cons**: Import conflicts, confusion in error handling
- **Why not chosen**: Conflict causes real issues; rename with migration path is better

## Consequences

### Positive

- **User guidance**: Clear API for retry eligibility
- **Correct defaults**: Classification follows HTTP/REST best practices
- **Reduced boilerplate**: Users don't need custom classification code
- **Composable**: Works with user's own retry logic
- **No conflicts**: Exception names don't conflict with dependencies
- **DRY**: Mixin eliminates duplication
- **Smooth migration**: Deprecation warnings guide users to new names

### Negative

- **No automatic retry**: Users must implement retry loops themselves (mitigation: documentation with examples)
- **Unknown errors not retryable**: Some edge cases might be incorrectly classified (mitigation: users can check `error` directly)
- **Deprecation warnings**: Users see warnings until they migrate (mitigation: clear migration path)

### Neutral

- Classification is advisory, not prescriptive
- Users can ignore `is_retryable` and use own logic
- Does not include backoff timing (out of scope)
- Metaclass adds minimal overhead for deprecated exceptions

## Compliance

### Enforcement

1. **Code review**: Ensure `is_retryable` uses status code only
2. **Unit tests**: Test each status code classification
3. **Documentation**: Document classification table in API docs
4. **Mixin usage**: All error types with retryability use `RetryableErrorMixin`

### Validation

- [ ] `is_retryable` returns `True` for 429 status
- [ ] `is_retryable` returns `True` for 500, 502, 503, 504
- [ ] `is_retryable` returns `False` for 400, 401, 403, 404, 409
- [ ] `is_retryable` returns `False` for unknown/missing status
- [ ] `get_retryable_errors()` filters correctly
- [ ] `GidValidationError` is canonical exception name
- [ ] `ValidationError` alias triggers deprecation warning
- [ ] `SaveSessionError` wraps `SaveResult` with descriptive message
- [ ] No duplication between `SaveError` and `ActionResult` classification
