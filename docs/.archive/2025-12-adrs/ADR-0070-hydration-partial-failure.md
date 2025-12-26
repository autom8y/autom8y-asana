# ADR-0070: Hydration Partial Failure Handling

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-HYDRATION, TDD-HYDRATION, ADR-0040 (SaveSession Partial Failure), ADR-0069

## Context

During hierarchy hydration, individual API calls may fail (network issues, rate limits, deleted tasks). We need to decide how to handle partial failures:

- Should a single holder fetch failure abort the entire hydration?
- Should partially-loaded hierarchies be returned to the caller?
- How do we communicate what succeeded vs. failed?

**Question from PRD (Q4)**: Should partial hydration return `HydrationResult` or raise with partial data?

### Failure Scenarios

1. **Business holder fetch fails**: One of 7 holders fails to load its subtasks
2. **Nested holder fetch fails**: Unit's OfferHolder fails to load Offers
3. **Upward traversal fails**: Parent task is deleted mid-traversal
4. **Rate limit during hydration**: API returns 429 mid-operation
5. **Transient network error**: Timeout on one request

### Forces

1. **Consistency**: ADR-0040 established `SaveResult` pattern for partial failures
2. **Usability**: Callers need to know what succeeded to make decisions
3. **Fail-fast vs. best-effort**: Different use cases have different needs
4. **Debugging**: Failures must be diagnosable
5. **Data integrity**: Partially-loaded hierarchies may have inconsistent references

## Decision

We will use **HydrationResult with explicit partial success tracking** (Option C from Discovery), following the SaveResult pattern from ADR-0040.

### HydrationResult Structure

```python
@dataclass
class HydrationResult:
    """Result of hydration operation with success/failure tracking.

    Attributes:
        business: The root Business entity (always populated, may be partial).
        entry_entity: The original entry entity (for non-Business starts).
        entry_type: Detected type of entry entity.
        path: Entities traversed during upward navigation.
        api_calls: Total API calls made.
        succeeded: List of successfully hydrated branches.
        failed: List of branches that failed to hydrate.
        warnings: Non-fatal issues encountered.
        is_complete: True if all branches hydrated successfully.
    """
    business: Business
    entry_entity: BusinessEntity | None = None
    entry_type: EntityType | None = None
    path: list[BusinessEntity] = field(default_factory=list)
    api_calls: int = 0
    succeeded: list[HydrationBranch] = field(default_factory=list)
    failed: list[HydrationFailure] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """True if hydration completed with no failures."""
        return len(self.failed) == 0


@dataclass
class HydrationBranch:
    """A successfully hydrated branch of the hierarchy.

    Attributes:
        holder_type: Type of holder that was hydrated.
        holder_gid: GID of the holder task.
        child_count: Number of children populated.
    """
    holder_type: str
    holder_gid: str
    child_count: int


@dataclass
class HydrationFailure:
    """A branch that failed to hydrate.

    Attributes:
        holder_type: Type of holder that failed.
        holder_gid: GID of the holder task (if known).
        phase: "downward" or "upward" traversal phase.
        error: The exception that caused the failure.
        recoverable: True if retry might succeed (transient error).
    """
    holder_type: str
    holder_gid: str | None
    phase: Literal["downward", "upward"]
    error: Exception
    recoverable: bool
```

### Behavior Modes

#### Default Behavior: Fail-Fast (Consistent, Safe)

```python
# Default: Any failure raises HydrationError
business = await Business.from_gid_async(client, gid)
# Raises HydrationError if any branch fails
```

#### Opt-in: Best-Effort (Partial Results)

```python
# Explicit opt-in for partial results
result = await Business.from_gid_async(client, gid, partial_ok=True)
if not result.is_complete:
    for failure in result.failed:
        logger.warning(f"Failed to load {failure.holder_type}: {failure.error}")
business = result.business  # May be partially populated
```

### HydrationError Exception

```python
class HydrationError(AsanaError):
    """Hydration operation failed.

    Raised when hydration fails and partial_ok=False (default).

    Attributes:
        entity_gid: GID of the entity where hydration started.
        entity_type: Detected type of the entity.
        phase: "downward" or "upward" indicating where failure occurred.
        partial_result: The HydrationResult with what succeeded before failure.
        cause: The underlying exception that caused the failure.
    """
    def __init__(
        self,
        message: str,
        *,
        entity_gid: str,
        entity_type: str | None = None,
        phase: Literal["downward", "upward"],
        partial_result: HydrationResult | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.entity_gid = entity_gid
        self.entity_type = entity_type
        self.phase = phase
        self.partial_result = partial_result
        self.__cause__ = cause
```

### API Signatures with Partial Support

```python
class Business(BusinessEntity):
    @classmethod
    async def from_gid_async(
        cls,
        client: AsanaClient,
        gid: str,
        *,
        hydrate: bool = True,
        partial_ok: bool = False,
    ) -> Business | HydrationResult:
        """Load Business with optional partial failure tolerance.

        Args:
            client: AsanaClient for API calls.
            gid: Business task GID.
            hydrate: If True, load full hierarchy.
            partial_ok: If True, return HydrationResult even on partial failure.
                       If False (default), raise HydrationError on any failure.

        Returns:
            Business if partial_ok=False and successful.
            HydrationResult if partial_ok=True (check is_complete).

        Raises:
            HydrationError: If hydration fails and partial_ok=False.
        """
```

### Concurrency and Failure Isolation

Per NFR-PERF-001, holders at the same level are fetched concurrently. Failure isolation:

```python
async def _hydrate_holders_concurrent(
    business: Business,
    client: AsanaClient,
) -> tuple[list[HydrationBranch], list[HydrationFailure]]:
    """Fetch all Business-level holders concurrently with failure isolation."""

    async def fetch_holder(holder_key: str, holder: Task) -> HydrationBranch | HydrationFailure:
        try:
            subtasks = await client.tasks.subtasks_async(holder.gid).collect()
            holder._populate_children(subtasks)
            return HydrationBranch(holder_key, holder.gid, len(subtasks))
        except AsanaError as e:
            return HydrationFailure(
                holder_type=holder_key,
                holder_gid=holder.gid,
                phase="downward",
                error=e,
                recoverable=isinstance(e, (RateLimitError, TimeoutError)),
            )

    # Gather with return_exceptions=False - we handle errors in fetch_holder
    results = await asyncio.gather(
        *[fetch_holder(key, holder) for key, holder in business._holders_to_fetch()],
    )

    succeeded = [r for r in results if isinstance(r, HydrationBranch)]
    failed = [r for r in results if isinstance(r, HydrationFailure)]

    return succeeded, failed
```

## Rationale

**Why HydrationResult instead of raising with partial data?**

- Matches established `SaveResult` pattern (ADR-0040)
- Clear separation: success returns data, failure raises (unless opted in)
- Callers can inspect `is_complete` for simple pass/fail
- `failed` list enables retry logic for recoverable errors

**Why fail-fast by default?**

- Partial hierarchies may have inconsistent bidirectional references
- Most callers expect complete data or error
- Advanced callers can opt into partial results

**Why `partial_ok` parameter instead of separate method?**

- Single entry point, clear behavior toggle
- Return type is explicit based on parameter
- Matches common patterns (`requests.get(..., raise_for_status=True)`)

**Why include `partial_result` in HydrationError?**

- Enables advanced error handlers to salvage partial data
- Matches `SaveSessionError.partial_result` pattern
- Useful for debugging what succeeded before failure

## Alternatives Considered

### Option A: Fail Entire Hydration on Any Error

- **Description**: Any fetch failure aborts hydration, raises exception
- **Pros**: Simple, consistent, no partial states
- **Cons**: Brittle for transient errors, loses successful work
- **Why not chosen**: Too strict for real-world API reliability

### Option B: Mark Failed Branches as None, Continue

- **Description**: Set failed holders to `None`, return Business
- **Pros**: Simple, always returns something
- **Cons**: Callers may not notice failures, inconsistent data state
- **Why not chosen**: Silent failures are dangerous, violates principle of explicit error handling

### Option D: Retry-First, Then Fail

- **Description**: Automatic retry on transient errors before failing
- **Pros**: Handles transient issues transparently
- **Cons**: Implicit retries complicate timing, may hit rate limits harder
- **Why not chosen**: Retry policy should be controlled by transport layer (ADR-0048), not hydration

## Consequences

### Positive

- **Explicit**: Callers know exactly what succeeded and failed
- **Flexible**: Default is safe (fail-fast), opt-in for advanced use cases
- **Debuggable**: `HydrationFailure` includes full error context
- **Consistent**: Matches SaveResult pattern from ADR-0040
- **Recoverable**: `recoverable` flag enables smart retry logic

### Negative

- **Complexity**: Two return types based on parameter
- **Partial state**: When `partial_ok=True`, Business may have inconsistent references
- **API learning curve**: Users must understand `is_complete` check

### Neutral

- Rate limit errors (429) are marked recoverable
- Network timeouts are marked recoverable
- NotFoundError (404) is not recoverable (task deleted)

## Compliance

- `HydrationError` MUST be added to `exceptions.py` with all specified attributes
- `HydrationResult` MUST be defined in `src/autom8_asana/models/business/hydration.py`
- Default behavior MUST be fail-fast (`partial_ok=False`)
- `partial_result` MUST be populated in `HydrationError` when available
- Unit tests MUST cover both fail-fast and partial_ok modes
- Integration tests MUST simulate partial failures (mock one holder fetch to fail)

## Implementation Notes

### Error Classification

```python
def _is_recoverable(error: Exception) -> bool:
    """Classify error as transient (retry-worthy) or permanent."""
    if isinstance(error, RateLimitError):
        return True
    if isinstance(error, TimeoutError):
        return True
    if isinstance(error, ServerError):
        return True  # 5xx errors may be transient
    if isinstance(error, NotFoundError):
        return False  # 404 = deleted, won't recover
    if isinstance(error, ForbiddenError):
        return False  # 403 = permission issue, won't recover
    return False  # Default: assume permanent
```

### Logging on Partial Failure

When `partial_ok=True` and failures occur:

```python
logger.warning(
    "Hydration completed with partial failures",
    extra={
        "business_gid": business.gid,
        "succeeded_count": len(result.succeeded),
        "failed_count": len(result.failed),
        "failed_holders": [f.holder_type for f in result.failed],
    }
)
```
