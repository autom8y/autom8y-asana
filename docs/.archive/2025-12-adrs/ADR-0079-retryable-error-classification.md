# ADR-0079: Retryable Error Classification

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Author** | Architect |
| **Date** | 2025-12-16 |
| **Deciders** | Architect, Principal Engineer |
| **Related** | PRD-HARDENING-F, TDD-HARDENING-F |

---

## Context

When `SaveSession.commit_async()` encounters partial failures, users receive a `SaveResult` containing a list of `SaveError` objects. Each `SaveError` captures:

```python
@dataclass
class SaveError:
    entity: AsanaResource
    operation: OperationType
    error: Exception
    payload: dict[str, Any]
```

Users currently must inspect the raw `error` object to determine if a failure is potentially recoverable. This requires:
1. Knowledge of Asana API error codes
2. Type checking the exception
3. Extracting and interpreting HTTP status codes

Common questions users ask:
- "Can I retry this operation?"
- "Is this a transient failure or a permanent error?"
- "Which errors should I log vs. retry vs. escalate?"

Without guidance, users implement ad-hoc classification logic, often incorrectly.

---

## Decision

**Classify errors as retryable based on HTTP status code, with `429` and `5xx` being retryable.**

### Implementation

Add an `is_retryable` property to `SaveError`:

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

        Classification based on HTTP status code semantics:
        - 429 (Rate Limit): Retryable after delay
        - 5xx (Server Error): Retryable (transient)
        - 4xx (Client Error): Not retryable (bad request)

        Returns:
            True if error type suggests retry may succeed.
        """
        status_code = self._extract_status_code()
        if status_code is None:
            return False  # Unknown errors are not retryable

        if status_code == 429:
            return True

        if 500 <= status_code < 600:
            return True

        return False

    def _extract_status_code(self) -> int | None:
        """Extract HTTP status code from error."""
        from autom8_asana.exceptions import AsanaError

        if isinstance(self.error, AsanaError):
            return self.error.status_code

        if hasattr(self.error, 'status_code'):
            return getattr(self.error, 'status_code')

        return None
```

### Classification Table

| HTTP Status | `is_retryable` | Reason |
|-------------|----------------|--------|
| 400 Bad Request | `False` | Client error - payload is invalid |
| 401 Unauthorized | `False` | Authentication error - needs credential fix |
| 403 Forbidden | `False` | Permission error - needs access grant |
| 404 Not Found | `False` | Resource doesn't exist |
| 409 Conflict | `False` | Conflict - needs manual resolution |
| **429 Too Many Requests** | `True` | Rate limit - retry after delay |
| **500 Internal Server Error** | `True` | Server error - transient |
| **502 Bad Gateway** | `True` | Server error - transient |
| **503 Service Unavailable** | `True` | Server error - transient |
| **504 Gateway Timeout** | `True` | Server error - transient |

### Convenience Methods on SaveResult

```python
@dataclass
class SaveResult:
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

---

## Rationale

### Why HTTP status code based?

1. **Standard semantics**: HTTP status codes have well-defined meanings (RFC 7231)
2. **Universal**: All Asana API errors include HTTP status codes
3. **Simple**: No need for error message parsing or special cases
4. **Extensible**: Easy to add new status codes if Asana introduces them

### Why 429 and 5xx as retryable?

**429 (Rate Limit)**:
- Explicitly designed to be retryable
- Asana returns `Retry-After` header with delay guidance
- Temporary condition that resolves with backoff

**5xx (Server Errors)**:
- Indicate server-side issues, not client errors
- Transient by nature (service temporarily unavailable)
- Standard practice to retry with exponential backoff

### Why not 4xx (except 429)?

- 4xx errors indicate client-side problems
- Retrying the same request will produce the same error
- Requires payload fix, permission change, or resource creation

### Why default to not retryable for unknown errors?

- Conservative approach: assume errors need investigation
- Prevents infinite retry loops on unexpected error types
- Users can override based on domain knowledge

---

## Alternatives Considered

### Alternative 1: Error message pattern matching

- **Description**: Parse error messages for keywords like "rate limit" or "try again"
- **Pros**: Catches cases where status code doesn't tell full story
- **Cons**: Brittle; Asana can change message format; i18n issues
- **Why not chosen**: Status codes are more reliable and standardized

### Alternative 2: Whitelist specific Asana error codes

- **Description**: Maintain list of specific Asana error codes that are retryable
- **Pros**: Precise control over classification
- **Cons**: Requires ongoing maintenance; may miss new error codes
- **Why not chosen**: HTTP status codes are sufficient and require no maintenance

### Alternative 3: User-provided classifier function

- **Description**: Allow users to provide custom `is_retryable` function
- **Pros**: Maximum flexibility
- **Cons**: Complexity; users still need defaults; harder to document
- **Why not chosen**: Over-engineering; sensible defaults are sufficient

### Alternative 4: Automatic retry mechanism

- **Description**: SaveSession automatically retries retryable errors
- **Pros**: Seamless recovery from transient failures
- **Cons**: Scope creep; needs backoff strategy, max attempts, circuit breaker
- **Why not chosen**: Deferred to future initiative per PRD-HARDENING-F non-goals

---

## Consequences

### Positive

1. **User guidance**: Clear API for determining retry eligibility
2. **Correct defaults**: Classification follows HTTP/REST best practices
3. **Reduced boilerplate**: Users don't need custom classification code
4. **Composable**: Works with user's own retry logic

### Negative

1. **No automatic retry**: Users must implement retry loops themselves
   - *Mitigation*: Provide documentation with example retry patterns
2. **Unknown errors not retryable**: Some edge cases might be incorrectly classified
   - *Mitigation*: Users can check `error` directly for domain-specific handling

### Neutral

1. Classification is advisory, not prescriptive
2. Users can ignore `is_retryable` and use their own logic
3. Does not include backoff timing (out of scope)

---

## Compliance

### How to enforce this decision

1. **Code review**: Ensure `is_retryable` uses status code only
2. **Unit tests**: Test each status code classification
3. **Documentation**: Document classification table in API docs

### Validation

- [ ] `is_retryable` returns `True` for 429 status
- [ ] `is_retryable` returns `True` for 500, 502, 503, 504
- [ ] `is_retryable` returns `False` for 400, 401, 403, 404, 409
- [ ] `is_retryable` returns `False` for unknown/missing status
- [ ] `get_retryable_errors()` filters correctly
