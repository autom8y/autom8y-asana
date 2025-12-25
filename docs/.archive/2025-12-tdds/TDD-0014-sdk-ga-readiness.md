# TDD-0014: SDK GA Readiness

## Metadata

- **TDD ID**: TDD-0014
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-10
- **PRD Reference**: [PRD-0009](../requirements/PRD-0009-sdk-ga-readiness.md)
- **Related TDDs**: [TDD-0001](TDD-0001-sdk-architecture.md) (SDK Architecture)
- **Related ADRs**: [ADR-0048](../decisions/ADR-0048-circuit-breaker-pattern.md), [ADR-0049](../decisions/ADR-0049-gid-validation-strategy.md)

---

## Overview

This TDD defines the technical design for achieving SDK GA readiness. The key finding during architecture is that **retry with exponential backoff already exists** (`transport/retry.py`). The remaining work focuses on: (1) adding circuit breaker pattern for cascading failure prevention, (2) GID format validation at track time, (3) empty session warning, and (4) documentation.

---

## Requirements Summary

From PRD-0009, the following requirements are addressed:

| Category | IDs | Summary |
|----------|-----|---------|
| Circuit Breaker | FR-RETRY-005 to FR-RETRY-010 | Failure threshold, half-open probing, event hooks |
| Validation | FR-VAL-001 to FR-VAL-002 | GID format validation, untracked modification warning |
| Documentation | FR-DOC-001 to FR-DOC-007 | README, Limitations, SaveSession guide, Migration guide |
| Non-Functional | NFR-COMPAT-*, NFR-PERF-* | Backward compatibility, performance targets |

**Already Satisfied** (existing implementation):
- FR-RETRY-001: Configurable retry handler ✅ (`RetryHandler`)
- FR-RETRY-002: Exponential backoff with jitter ✅ (`RetryConfig`)
- FR-RETRY-003: Retryable error detection ✅ (429, 503, 504)
- FR-RETRY-004: Max retry configuration ✅ (`max_retries`)

---

## System Context

The SDK has a layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     User Application                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      AsanaClient                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   Resource Clients                       ││
│  │   TasksClient, ProjectsClient, SectionsClient, etc.     ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  SaveSession    │ │  BatchClient    │ │  AsyncHTTPClient│
│  (Persistence)  │ │                 │ │  (Transport)    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Transport Layer                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │ CircuitBreaker│ │ RetryHandler │ │ RateLimiter  │         │
│  │    (NEW)      │ │  (EXISTS)    │ │  (EXISTS)    │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        Asana REST API
```

---

## Design

### Component Architecture

| Component | Location | Responsibility | Status |
|-----------|----------|----------------|--------|
| `CircuitBreaker` | `transport/circuit_breaker.py` | Cascading failure prevention | NEW |
| `CircuitBreakerConfig` | `config.py` | Circuit breaker settings | NEW |
| `GID Validation` | `persistence/tracker.py` | Format validation at track() | MODIFY |
| `Empty Session Warning` | `persistence/session.py` | Warning at commit() | MODIFY |
| Documentation | `/docs/guides/` | User guides | NEW |

---

### Circuit Breaker Design

#### State Machine

```
                    ┌──────────────────────────┐
                    │                          │
                    ▼                          │
              ┌──────────┐                     │
    ──────────│  CLOSED  │◄────────────────────┤
    Request   └────┬─────┘                     │
    succeeds       │                           │
                   │ failure_threshold         │
                   │ failures reached          │
                   ▼                           │
              ┌──────────┐                     │
              │   OPEN   │                     │
              └────┬─────┘                     │
                   │                           │
                   │ recovery_timeout          │
                   │ elapsed                   │
                   ▼                           │
              ┌──────────┐    probe            │
              │HALF_OPEN │────succeeds─────────┘
              └────┬─────┘
                   │
                   │ probe fails
                   ▼
              ┌──────────┐
              │   OPEN   │ (reset timer)
              └──────────┘
```

#### Configuration

```python
# config.py (addition)
@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration.

    Per ADR-0048: Opt-in behavior for backward compatibility.
    """
    enabled: bool = False
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 1

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")
        if self.half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be >= 1")
```

#### Interface

```python
# transport/circuit_breaker.py (new file)
from enum import Enum
from dataclasses import dataclass
import asyncio
import time

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    def __init__(self, time_until_recovery: float):
        self.time_until_recovery = time_until_recovery
        super().__init__(f"Circuit breaker open. Retry in {time_until_recovery:.1f}s")

class CircuitBreaker:
    """Circuit breaker for cascading failure prevention.

    Per ADR-0048: Composition pattern wrapping request execution.
    """

    def __init__(self, config: CircuitBreakerConfig, logger: LogProvider | None = None):
        self._config = config
        self._logger = logger
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

        # Event hooks
        self._on_state_change: list[Callable[[CircuitState, CircuitState], None]] = []
        self._on_failure: list[Callable[[Exception], None]] = []
        self._on_success: list[Callable[[], None]] = []

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    async def check(self) -> None:
        """Check if request is allowed. Raises CircuitBreakerOpenError if not."""
        if not self._config.enabled:
            return

        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return

            if self._state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self._transition_to(CircuitState.HALF_OPEN)
                    return
                time_until_recovery = self._time_until_recovery()
                raise CircuitBreakerOpenError(time_until_recovery)

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self._config.half_open_max_calls:
                    raise CircuitBreakerOpenError(self._config.recovery_timeout)
                self._half_open_calls += 1

    async def record_success(self) -> None:
        """Record successful request."""
        if not self._config.enabled:
            return

        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0

        for hook in self._on_success:
            hook()

    async def record_failure(self, error: Exception) -> None:
        """Record failed request."""
        if not self._config.enabled:
            return

        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
            elif self._failure_count >= self._config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

        for hook in self._on_failure:
            hook(error)

    def on_state_change(self, callback: Callable[[CircuitState, CircuitState], None]) -> None:
        """Register state change callback."""
        self._on_state_change.append(callback)

    def on_failure(self, callback: Callable[[Exception], None]) -> None:
        """Register failure callback."""
        self._on_failure.append(callback)

    def on_success(self, callback: Callable[[], None]) -> None:
        """Register success callback."""
        self._on_success.append(callback)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._half_open_calls = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0

        if self._logger:
            self._logger.info(
                "circuit_breaker_state_change",
                old_state=old_state.value,
                new_state=new_state.value,
            )

        for hook in self._on_state_change:
            hook(old_state, new_state)

    def _should_attempt_recovery(self) -> bool:
        """Check if recovery timeout has elapsed."""
        if self._last_failure_time is None:
            return True
        elapsed = time.monotonic() - self._last_failure_time
        return elapsed >= self._config.recovery_timeout

    def _time_until_recovery(self) -> float:
        """Calculate time until recovery attempt."""
        if self._last_failure_time is None:
            return 0.0
        elapsed = time.monotonic() - self._last_failure_time
        return max(0.0, self._config.recovery_timeout - elapsed)
```

#### Integration with HTTP Client

```python
# transport/http.py (modification)
class AsyncHTTPClient:
    def __init__(
        self,
        config: AsanaConfig,
        auth_provider: AuthProvider,
        logger: LogProvider | None = None,
        cache_provider: CacheProvider | None = None,
    ):
        # ... existing initialization ...

        # NEW: Circuit breaker (opt-in)
        self._circuit_breaker = CircuitBreaker(
            config.circuit_breaker,
            logger
        ) if config.circuit_breaker.enabled else None

    async def request(self, method: str, path: str, ...) -> dict[str, Any]:
        # NEW: Check circuit breaker before request
        if self._circuit_breaker:
            await self._circuit_breaker.check()

        attempt = 0
        while True:
            async with semaphore:
                await self._rate_limiter.acquire()
                try:
                    response = await client.request(...)

                    if response.status_code < 400:
                        # NEW: Record success
                        if self._circuit_breaker:
                            await self._circuit_breaker.record_success()
                        return self._parse_response(response)

                    # Handle error...
                    error = AsanaError.from_response(response)

                    # NEW: Record failure for circuit breaker
                    if self._circuit_breaker:
                        await self._circuit_breaker.record_failure(error)

                    # Existing retry logic...
                    if self._retry_handler.should_retry(response.status_code, attempt):
                        await self._retry_handler.wait(attempt, ...)
                        attempt += 1
                        continue

                    raise error

                except Exception as e:
                    # NEW: Record failure
                    if self._circuit_breaker:
                        await self._circuit_breaker.record_failure(e)
                    raise
```

---

### GID Validation Design

#### Location

**File**: `src/autom8_asana/persistence/tracker.py`

**Method**: `ChangeTracker.track()`

#### Implementation

```python
# persistence/tracker.py (modification)
import re

# GID format: numeric string or temp_<number>
GID_PATTERN = re.compile(r"^(temp_\d+|\d+)$")

class ValidationError(Exception):
    """Raised when entity validation fails."""
    pass

class ChangeTracker:
    def track(self, entity: T) -> T:
        """Track an entity for change detection.

        Per ADR-0049: Validates GID format at track time.
        """
        # NEW: Validate GID format
        self._validate_gid_format(entity.gid)

        # ... existing tracking logic ...

    def _validate_gid_format(self, gid: str | None) -> None:
        """Validate GID format.

        Args:
            gid: The GID to validate. None is allowed for new entities.

        Raises:
            ValidationError: If GID format is invalid.
        """
        if gid is None:
            return  # New entities have no GID

        if gid == "":
            raise ValidationError("GID cannot be empty string. Use None for new entities.")

        if not GID_PATTERN.match(gid):
            raise ValidationError(
                f"Invalid GID format: {gid!r}. "
                f"GID must be a numeric string or temp_<number> for new entities."
            )
```

---

### Empty Session Warning Design

#### Location

**File**: `src/autom8_asana/persistence/session.py`

**Method**: `SaveSession.commit_async()`

#### Implementation

```python
# persistence/session.py (modification)
class SaveSession:
    async def commit_async(self) -> SaveResult:
        """Commit all tracked changes.

        Per FR-VAL-002: Warns if no entities or actions to commit.
        """
        self._ensure_open()

        dirty_entities = self._tracker.get_dirty_entities()
        pending_actions = self._pending_actions

        # NEW: Warn on empty commit
        if not dirty_entities and not pending_actions:
            if self._log:
                self._log.warning(
                    "commit_empty_session",
                    message="No tracked entities or pending actions to commit. "
                            "Did you forget to call track() on your entities?",
                )
            return SaveResult(succeeded=[], failed=[])

        # ... existing commit logic ...
```

---

### Documentation Architecture

#### File Structure

```
/
├── README.md                           [NEW - FR-DOC-001,002,003]
│   └── Links to: /docs/guides/, /examples/
│
├── docs/
│   ├── INDEX.md                        [UPDATE]
│   │
│   ├── guides/
│   │   ├── limitations.md              [NEW - FR-DOC-004,005]
│   │   ├── save-session.md             [NEW - FR-DOC-006]
│   │   ├── sdk-adoption.md             [NEW - FR-DOC-007]
│   │   └── autom8-migration.md         [EXISTS]
│   │
│   ├── requirements/
│   │   └── PRD-0009-sdk-ga-readiness.md [EXISTS]
│   │
│   └── design/
│       └── TDD-0014-sdk-ga-readiness.md [THIS FILE]
│
└── examples/
    └── README.md                        [EXISTS - Quick Start]
```

#### Discoverability Mechanisms

1. **README.md → Guides**: Direct links in "Documentation" section
2. **session.py docstring → save-session.md**: Add reference in module docstring
3. **UnsupportedOperationError → limitations.md**: Add link in error message
4. **CircuitBreakerOpenError → README.md**: Add troubleshooting section

---

## Technical Decisions

| Decision | Choice | ADR |
|----------|--------|-----|
| Circuit breaker pattern | Composition wrapping HTTP client | [ADR-0048](../decisions/ADR-0048-circuit-breaker-pattern.md) |
| Circuit breaker scope | Per-client instance | [ADR-0048](../decisions/ADR-0048-circuit-breaker-pattern.md) |
| GID validation timing | At track() time | [ADR-0049](../decisions/ADR-0049-gid-validation-strategy.md) |
| GID format | `^(temp_\d+|\d+)$` | [ADR-0049](../decisions/ADR-0049-gid-validation-strategy.md) |
| Untracked detection | Warning at commit() | Inline decision (simple) |

---

## Complexity Assessment

**Level**: Module

**Rationale**:
- Circuit breaker is a self-contained module with clear boundaries
- Validation changes are localized to tracker
- Documentation is additive, no code changes
- No cross-system integration required

---

## Implementation Plan

### Phase 1: Documentation (Session 4)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| README.md | None | 2-3 hours |
| limitations.md | None | 2-3 hours |
| save-session.md | None | 3-4 hours |
| sdk-adoption.md | None | 4-6 hours |

### Phase 2: Validation & Tests (Session 5)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| GID validation in tracker | None | 2 hours |
| Empty session warning | None | 1 hour |
| Boundary tests (P0) | Validation code | 4-6 hours |

### Phase 3: Circuit Breaker (Session 6)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| CircuitBreaker class | None | 4-6 hours |
| CircuitBreakerConfig | None | 1 hour |
| HTTP client integration | CircuitBreaker | 2-3 hours |
| Unit tests | Implementation | 4-6 hours |
| Event hooks | CircuitBreaker | 2 hours |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Circuit breaker overhead | Performance degradation | Low | Opt-in by default, benchmark tests |
| GID validation false positives | Breaking existing valid code | Medium | Thorough regex testing, allow None |
| Documentation gaps | Poor adoption | Low | QA validation in Session 7 |
| Backward compatibility break | User code fails | High | NFR-COMPAT requirements, opt-in |

---

## Observability

### Metrics (Future)

- `circuit_breaker_state_changes_total`: Counter by old_state, new_state
- `circuit_breaker_failures_total`: Counter by error_type
- `circuit_breaker_open_duration_seconds`: Histogram

### Logging

| Event | Level | Fields |
|-------|-------|--------|
| `circuit_breaker_state_change` | INFO | old_state, new_state |
| `circuit_breaker_open` | WARNING | time_until_recovery |
| `commit_empty_session` | WARNING | message |
| `gid_validation_failed` | ERROR | gid, reason |

---

## Testing Strategy

### Unit Tests

| Component | Test File | Coverage Target |
|-----------|-----------|-----------------|
| CircuitBreaker | `tests/unit/transport/test_circuit_breaker.py` | 95% |
| GID Validation | `tests/unit/persistence/test_tracker.py` | 90% |
| Empty Session | `tests/unit/persistence/test_session.py` | 80% |

### Integration Tests

| Scenario | Test File |
|----------|-----------|
| Circuit breaker with real HTTP | `tests/integration/test_circuit_breaker.py` |
| End-to-end with failures | `tests/integration/test_resilience.py` |

### Boundary Tests (from PRD-0009)

| Test | Priority | Location |
|------|----------|----------|
| Empty GID string | P0 | `test_boundary_conditions.py` |
| Malformed GID | P0 | `test_boundary_conditions.py` |
| Very long strings | P0 | `test_boundary_conditions.py` |
| Unicode characters | P1 | `test_boundary_conditions.py` |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should circuit breaker reset on successful retry? | Architect | Resolved | Yes - success resets count |
| Include network errors (httpx.HTTPError) in CB failures? | Architect | Resolved | Yes - all transport errors |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Architect | Initial draft |
