# SDK Design Evolution

## Overview

The autom8_asana SDK architecture evolved through four major design phases, from initial extraction architecture through functional parity extensions, production hardening mechanisms, and operational validation tooling. This document synthesizes the technical design decisions across all phases.

## Evolution Timeline

| Phase | Document | Key Design Focus | Complexity Level |
|-------|----------|------------------|------------------|
| **Foundation** | TDD-0001 (2025-12-08) | Layered architecture, protocol-based DI | SERVICE |
| **Expansion** | TDD-0012 (2025-12-10) | ActionOperation extensions, minimal changes | MODULE |
| **Hardening** | TDD-0014 (2025-12-10) | Circuit breaker, validation, documentation | MODULE |
| **Validation** | TDD-0029 (2025-12-12) | Interactive demo, state management | MODULE |

## Phase 1: Foundation (TDD-0001)

**Design Goal**: Extract pure Asana API functionality into standalone SDK with zero coupling to autom8 internals.

### Layered Architecture

```
autom8_asana/
├── client.py               # AsanaClient facade
├── config.py               # Configuration dataclasses
├── exceptions.py           # Error hierarchy
├── transport/              # HTTP, rate limiting, retry
│   ├── http.py
│   ├── rate_limiter.py
│   ├── retry.py
│   └── sync.py
├── clients/                # Resource-specific operations
│   ├── tasks.py
│   ├── projects.py
│   └── ... (13 clients total)
├── batch/                  # Batch API composition
│   ├── client.py
│   └── request.py
├── models/                 # Pydantic v2 models
│   ├── base.py
│   ├── tasks.py
│   └── ...
├── protocols/              # Boundary contracts
│   ├── auth.py
│   ├── cache.py
│   └── log.py
└── _defaults/              # Default implementations
    ├── auth.py
    ├── cache.py
    └── log.py
```

### Key Architectural Decisions

**Decision 1: Protocol-based Extensibility** (ADR-0001)
- **Choice**: `typing.Protocol` for boundary contracts
- **Rationale**: Structural subtyping allows any compatible class without inheritance. autom8 can inject implementations without SDK depending on autom8.
- **Alternative Rejected**: Abstract base classes (too coupled)

**Decision 2: Sync Wrapper Strategy** (ADR-0002)
- **Choice**: Fail-fast in async context
- **Rationale**: Prevents deadlocks. `get_running_loop()` check raises clear error if sync wrapper called from async context.
- **Alternative Rejected**: Threading (complexity, deadlock risk)

**Decision 3: Asana SDK Integration** (ADR-0003)
- **Choice**: Replace HTTP layer, keep types/errors
- **Rationale**: Better control over transport (httpx, connection pooling) while leveraging official type definitions.
- **Alternative Rejected**: Fork entire SDK (maintenance burden)

**Decision 4: Item Class Boundary** (ADR-0004)
- **Choice**: Minimal `AsanaResource` base in SDK
- **Rationale**: Avoids coupling SDK to autom8 business domain. autom8 keeps full `Item` class with business logic.
- **Alternative Rejected**: Move entire Item to SDK (couples SDK to autom8)

**Decision 5: Pydantic Configuration** (ADR-0005)
- **Choice**: `extra="ignore"` for forward compatibility
- **Rationale**: Asana API adds fields; SDK ignores unknown fields. Prevents breakage on API changes.
- **Alternative Rejected**: `extra="forbid"` (breaks on new fields)

### Data Flow: Standard Request

```
User Code → AsanaClient → TasksClient
  → AsyncHTTPClient → RateLimiter.acquire()
  → httpx.AsyncClient → Asana API
  → Response → Pydantic validation → Task model
```

### Data Flow: Retry on 429

```
AsyncHTTPClient → httpx.request()
  → 429 + Retry-After: 30
  → RetryHandler.should_retry(429) → True
  → wait(30s + jitter)
  → httpx.request() (retry)
  → 200 OK
```

### Implementation Phases

| Phase | Deliverable | Estimate |
|-------|-------------|----------|
| 1 | Foundation (protocols, config, exceptions) | 2 days |
| 2 | Transport layer (HTTP, rate limiter, retry, sync) | 2 days |
| 3 | Models & base client | 2 days |
| 4 | 13 resource clients | 3 days |
| 5 | Integration & polish (AsanaClient, import aliases, tests) | 3 days |

**Total**: 12 days

## Phase 2: Expansion (TDD-0012)

**Design Goal**: Extend SaveSession with 7 new ActionTypes, positioning parameters, and comment operations—**without new infrastructure**.

### Surgical Extension Strategy

**Only 4 Files Modified**:
1. `ActionType` enum: +7 values
2. `ActionOperation` dataclass: +`extra_params` field, `target_gid` optional
3. `SaveSession`: +9 methods, 2 extended methods
4. `persistence/exceptions.py`: +`PositioningConflictError`

### ActionOperation Extension

```python
@dataclass(frozen=True)
class ActionOperation:
    task: AsanaResource
    action: ActionType
    target_gid: str | None = None         # CHANGED: Optional for likes
    extra_params: dict[str, Any] = field(default_factory=dict)  # NEW

    def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
        match self.action:
            # Existing cases...
            case ActionType.ADD_TO_PROJECT:
                payload = {"data": {"project": self.target_gid}}
                if self.extra_params.get("insert_before"):
                    payload["data"]["insert_before"] = self.extra_params["insert_before"]
                if self.extra_params.get("insert_after"):
                    payload["data"]["insert_after"] = self.extra_params["insert_after"]
                return ("POST", f"/tasks/{task_gid}/addProject", payload)

            # New cases...
            case ActionType.ADD_FOLLOWER:
                return ("POST", f"/tasks/{task_gid}/addFollowers",
                        {"data": {"followers": [self.target_gid]}})
            case ActionType.ADD_LIKE:
                return ("POST", f"/tasks/{task_gid}/addLike",
                        {"data": {}})  # No target needed
            case ActionType.ADD_COMMENT:
                comment_data = {"text": self.extra_params.get("text", "")}
                if self.extra_params.get("html_text"):
                    comment_data["html_text"] = self.extra_params["html_text"]
                return ("POST", f"/tasks/{task_gid}/stories",
                        {"data": comment_data})
```

### Key Design Decisions

**Decision 1: extra_params Field Design** (ADR-0044)
- **Choice**: `dict[str, Any]` with `default_factory=dict`
- **Rationale**: Flexible, type-safe at runtime, frozen-compatible. Alternative of separate dataclasses required 3 new types.

**Decision 2: Like Operations Without Target** (ADR-0045)
- **Choice**: `target_gid: str | None = None`
- **Rationale**: Simpler than sentinel value, explicit intent. Likes use authenticated user (no target needed).

**Decision 3: Comment Text Storage** (ADR-0046)
- **Choice**: Store via `extra_params`
- **Rationale**: Consistent with positioning. Alternative of new field on ActionOperation adds coupling.

**Decision 4: Positioning Validation Timing** (ADR-0047)
- **Choice**: Fail-fast at queue time (not commit time)
- **Rationale**: Better DX—error has full context. Commit-time errors lack method call stack.

### Implementation Estimate

**7-8 hours total**:
- Phase 1: ActionType enum +7 values (1 hour)
- Phase 2: ActionOperation extensions (30 min)
- Phase 3-7: New methods (3.5 hours)
- Phase 8-9: Error handling, UNSUPPORTED_FIELDS (20 min)
- Phase 10: Unit tests (2-3 hours)

## Phase 3: Hardening (TDD-0014)

**Design Goal**: Production-ready resilience with circuit breaker, validation, and documentation.

### Circuit Breaker State Machine

```
         ┌──────────────────┐
         │                  │
         ▼                  │
    ┌────────┐              │
────│ CLOSED │              │
    └────┬───┘              │
         │                  │
         │ failure_threshold│
         │ reached          │
         ▼                  │
    ┌────────┐              │
    │  OPEN  │              │
    └────┬───┘              │
         │                  │
         │ recovery_timeout │
         │ elapsed          │
         ▼                  │
    ┌──────────┐   probe    │
    │HALF_OPEN │───succeeds─┘
    └────┬─────┘
         │
         │ probe fails
         ▼
    ┌────────┐
    │  OPEN  │ (reset timer)
    └────────┘
```

### Circuit Breaker Integration

```python
class AsyncHTTPClient:
    def __init__(self, config, auth_provider, logger, cache_provider):
        # NEW: Circuit breaker (opt-in)
        self._circuit_breaker = CircuitBreaker(
            config.circuit_breaker, logger
        ) if config.circuit_breaker.enabled else None

    async def request(self, method: str, path: str, ...) -> dict:
        # NEW: Check circuit breaker before request
        if self._circuit_breaker:
            await self._circuit_breaker.check()  # May raise CircuitBreakerOpenError

        attempt = 0
        while True:
            try:
                response = await client.request(...)
                if response.status_code < 400:
                    # NEW: Record success
                    if self._circuit_breaker:
                        await self._circuit_breaker.record_success()
                    return self._parse_response(response)

                error = AsanaError.from_response(response)
                # NEW: Record failure
                if self._circuit_breaker:
                    await self._circuit_breaker.record_failure(error)

                # Existing retry logic...
                if self._retry_handler.should_retry(response.status_code, attempt):
                    await self._retry_handler.wait(attempt, ...)
                    attempt += 1
                    continue
                raise error
            except Exception as e:
                if self._circuit_breaker:
                    await self._circuit_breaker.record_failure(e)
                raise
```

### GID Validation Strategy (ADR-0049)

**Location**: `persistence/tracker.py` at `track()` time

```python
GID_PATTERN = re.compile(r"^(temp_\d+|\d+)$")

def _validate_gid_format(self, gid: str | None) -> None:
    if gid is None:
        return  # New entities have no GID

    if gid == "":
        raise ValidationError("GID cannot be empty string. Use None for new entities.")

    if not GID_PATTERN.match(gid):
        raise ValidationError(
            f"Invalid GID format: {gid!r}. "
            f"GID must be a numeric string or temp_<number>."
        )
```

### Key Design Decisions

**Decision 1: Circuit Breaker Pattern** (ADR-0048)
- **Choice**: Composition wrapping HTTP client
- **Rationale**: Opt-in, per-client instance. Alternative of global circuit breaker couples clients.

**Decision 2: GID Validation Timing** (ADR-0049)
- **Choice**: Validate at `track()` time
- **Rationale**: Fail-fast with full context. Validation at commit time loses call stack.

### Documentation Architecture

```
/
├── README.md                   [NEW]
├── docs/
│   ├── guides/
│   │   ├── limitations.md      [NEW]
│   │   ├── save-session.md     [NEW]
│   │   └── sdk-adoption.md     [NEW]
```

**Discoverability**:
1. README.md → Guides: Direct links
2. session.py docstring → save-session.md: Reference in module docstring
3. UnsupportedOperationError → limitations.md: Link in error message

### Implementation Phases

| Phase | Deliverable | Estimate |
|-------|-------------|----------|
| 1 | Documentation (4 docs) | 11-16 hours |
| 2 | Validation & tests | 7-8 hours |
| 3 | Circuit breaker | 13-17 hours |

## Phase 4: Validation (TDD-0029)

**Design Goal**: Interactive demonstration suite proving SDK functionality against real Asana workspace.

### Component Architecture

```
scripts/
    demo_sdk_operations.py    # Main entry (10 categories)
    demo_business_model.py    # Business model traversal
    _demo_utils.py            # Shared utilities

_demo_utils.py components:
    UserAction (enum)         # EXECUTE, SKIP, QUIT
    confirm()                 # Interactive prompts
    NameResolver              # Tag/user/section/project name → GID
    StateManager              # Capture, store, restore
    DemoLogger                # Structured logging
    DemoRunner                # Orchestration, error collection
```

### State Management Strategy (ADR-DEMO-001)

**Shallow copy with GID references** (not deep copy):

```python
@dataclass
class TaskSnapshot:
    entity_state: EntityState
    tag_gids: list[str]
    parent_gid: str | None
    memberships: list[MembershipState]
    dependency_gids: list[str]
    dependent_gids: list[str]
```

**Restoration Order**:
1. CRUD first: Track entity, set scalar/custom fields
2. Commit CRUD
3. Actions second: Tags, parent, section, dependencies
4. Commit actions

### Name Resolution Strategy (ADR-DEMO-002)

**Lazy-loading with session cache**:

```python
class NameResolver:
    async def resolve_tag(self, name: str) -> str | None:
        if not self._tags:
            self._tags = await self._client.tags.list_for_workspace_async(...)
        return next((t.gid for t in self._tags if t.name.lower() == name.lower()), None)
```

**Benefits**: Minimizes startup latency, avoids loading resources not used in demo run.

### Confirmation Flow

```
Demo Category Function
  │
  ├─ Set up operation (e.g., session.add_tag(task, tag_gid))
  │
  ├─ session.preview() → (crud_ops, action_ops)
  │
  ├─ confirm(description, crud_ops, action_ops)
  │    │
  │    ├─ Display operations
  │    ├─ Prompt: "Enter to execute, 's' to skip, 'q' to quit"
  │    └─ Return UserAction
  │
  ├─ Match UserAction:
  │    ├─ EXECUTE → commit_async() → update state → log success
  │    ├─ SKIP → continue to next operation
  │    └─ QUIT → restore all → exit
  │
  └─ Next operation
```

### Key Design Decisions

**Decision 1: State Capture Strategy** (ADR-DEMO-001)
- **Choice**: Shallow copy with GID references
- **Rationale**: Memory efficient, SDK-aligned. Deep copy wastes memory on full entity graphs.

**Decision 2: Name Resolution** (ADR-DEMO-002)
- **Choice**: Lazy-loading with session cache
- **Rationale**: Minimizes startup latency. Alternative of pre-loading all resources slow.

**Decision 3: Error Handling** (ADR-DEMO-003)
- **Choice**: Graceful degradation with recovery guidance
- **Rationale**: Demo continuity over fail-fast. Users learn more from partial completion.

### Implementation Phases

| Phase | Deliverable | Estimate |
|-------|-------------|----------|
| 1 | Foundation (confirm, datatypes, NameResolver) | 2-3 hours |
| 2 | StateManager | 2 hours |
| 3 | Demo infrastructure (Logger, Runner) | 1-2 hours |
| 4 | 10 demo categories | 3-4 hours |
| 5 | Polish (restoration, logging) | 1 hour |

**Total**: 9-12 hours

## Cross-Phase Patterns

### Complexity Management

- **Phase 1 (Foundation)**: SERVICE complexity justified by production requirements, DI, observability
- **Phases 2-4 (Extensions)**: MODULE complexity—clean boundaries, no layered architecture

### Error Handling Evolution

| Phase | Error Strategy | Example |
|-------|---------------|---------|
| 1 | Exception hierarchy with correlation IDs | `AsanaError` base with subclasses |
| 2 | Fail-fast validation | `PositioningConflictError` at queue time |
| 3 | Validation errors with guidance | `ValidationError("Invalid GID format: {gid!r}. Must be...")` |
| 4 | Graceful degradation with recovery | `DemoError` with `recovery_hint` field |

### Observability Evolution

| Phase | Logging | Metrics |
|-------|---------|---------|
| 1 | LogProvider protocol, correlation IDs | Requests, latency, rate limit |
| 2 | No new logging (existing ActionExecutor handles it) | No new metrics |
| 3 | Circuit breaker state changes, validation failures | Circuit breaker state, failures |
| 4 | Demo operations, name resolution, restoration | Not applicable (CLI tool) |

## Lessons Learned

1. **Protocol-based DI enables gradual migration**: Phase 1 decision to use protocols (not ABCs) was critical. autom8 injected implementations without SDK depending on autom8.

2. **Minimal changes maximize safety**: Phase 2 changed only 4 files. Alternative of new infrastructure would have risked existing functionality.

3. **Fail-fast validation improves DX**: Phase 2/3 validation at queue time (not commit time) gave errors with full call stack context.

4. **Circuit breaker must be opt-in**: Phase 3 backward compatibility requirement. Breaking existing behavior would block adoption.

5. **Executable validation finds edge cases**: Phase 4 demo suite operating against real Asana found issues unit tests missed.

6. **State restoration requires two-phase commit**: Phase 4 learned that CRUD operations must commit before Action operations to avoid conflicts.

## Archived Documents

This summary synthesizes technical designs from:

| Original | Archive Location |
|----------|------------------|
| TDD-0001-sdk-architecture.md | `docs/.archive/2025-12-tdds/TDD-0001-sdk-architecture.md` |
| TDD-0012-sdk-functional-parity.md | `docs/.archive/2025-12-tdds/TDD-0012-sdk-functional-parity.md` |
| TDD-0014-sdk-ga-readiness.md | `docs/.archive/2025-12-tdds/TDD-0014-sdk-ga-readiness.md` |
| TDD-0029-sdk-demo.md | `docs/.archive/2025-12-tdds/TDD-0029-sdk-demo.md` |

---

**Last Updated**: 2025-12-25 (Phase 4 consolidation)
