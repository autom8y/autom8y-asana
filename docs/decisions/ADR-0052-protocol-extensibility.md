# ADR-0052: Protocol-Based Extensibility

## Metadata
- **Status**: Accepted
- **Consolidated From**: ADR-0007 (Consistent Client Pattern), ADR-0016 (Cache Protocol Extension), ADR-0085 (ObservabilityHook), ADR-0103 (Automation Rule Protocol)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Related**: [reference/PATTERNS.md](reference/PATTERNS.md), ADR-SUMMARY-API-INTEGRATION

---

## Context

The SDK requires multiple extensibility points for:
- Cache backends (Redis, in-memory, null)
- Observability integration (Prometheus, DataDog, OpenTelemetry)
- Automation rules (custom trigger/execute logic)
- Consistent resource clients (Tasks, Projects, Sections, Users)

These integration points must:
1. **Support duck-typing**: Consumers shouldn't need to inherit from SDK base classes
2. **Enable structural subtyping**: Any object matching method signatures works
3. **Provide type safety**: Static analysis catches interface mismatches
4. **Follow Python idioms**: Use standard patterns, not heavyweight frameworks
5. **Be discoverable**: IDE autocomplete and type checkers provide guidance

---

## Decision

**Use `typing.Protocol` for all dependency injection points and public extension interfaces.**

All extensibility boundaries follow this pattern:
1. Define protocol with `@runtime_checkable` decorator
2. Use structural subtyping (no inheritance required)
3. Provide null/default implementations for optional integrations
4. Document protocol contracts in docstrings with examples

### Key Protocols

#### 1. CacheProvider Protocol

**Purpose**: Abstract cache backend for versioned entity caching.

**Evolution**: Extended from 3 methods (basic get/set/delete) to 11 methods (versioned operations, batching, health checks).

```python
@runtime_checkable
class CacheProvider(Protocol):
    """Protocol for cache backend integration.

    Supports both basic key-value operations and versioned caching
    with staleness detection. Consumers can implement any subset:
    - Minimal: get, set, delete
    - Full: all 11 methods for intelligent caching
    """

    # === Basic operations (original) ===
    def get(self, key: str) -> dict[str, Any] | None: ...
    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...

    # === Versioned operations ===
    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Freshness = Freshness.EVENTUAL,
    ) -> CacheEntry | None: ...

    def set_versioned(self, key: str, entry: CacheEntry) -> None: ...

    # === Batch operations ===
    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]: ...

    def set_batch(self, entries: dict[str, CacheEntry]) -> None: ...

    # === Cache management ===
    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType],
    ) -> WarmResult: ...

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool: ...

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None: ...

    def is_healthy(self) -> bool: ...
```

**Rationale**: Extended protocol preserves backward compatibility. Existing `NullCacheProvider` and `InMemoryCacheProvider` gained stub implementations for new methods. Consumers can incrementally adopt versioned methods.

#### 2. ObservabilityHook Protocol

**Purpose**: Integration point for metrics, tracing, and telemetry systems.

```python
@runtime_checkable
class ObservabilityHook(Protocol):
    """Protocol for observability integration.

    Implement to receive SDK operation events for metrics, tracing,
    or logging. All methods are async to support non-blocking backends.

    Example:
        class DataDogHook:
            async def on_request_start(
                self, method: str, path: str, correlation_id: str
            ) -> None:
                statsd.increment('asana.requests.started')
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        """Called before HTTP request."""
        ...

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        """Called after HTTP request completes."""
        ...

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        """Called when request fails."""
        ...

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        """Called on 429 rate limit response."""
        ...

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        """Called when circuit breaker changes state."""
        ...

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        """Called before retry attempt."""
        ...
```

**Default Implementation**:
```python
class NullObservabilityHook:
    """No-op implementation (zero-cost default)."""

    async def on_request_start(self, method: str, path: str, correlation_id: str) -> None:
        pass

    # ... all other methods are no-ops
```

**Rationale**: Async-only methods support non-blocking telemetry. Null Object pattern eliminates conditional checks (`if hook is not None`). Protocol enables duck-typing for custom integrations.

#### 3. AutomationRule Protocol

**Purpose**: Declarative automation rule system for business logic.

```python
@runtime_checkable
class AutomationRule(Protocol):
    """Protocol for automation rules.

    Rules execute actions when trigger conditions match. Consumers
    create custom rules by implementing this protocol.
    """

    id: str
    name: str
    trigger: TriggerCondition

    def should_trigger(
        self,
        entity: AsanaResource,
        event: str,
        context: dict[str, Any],
    ) -> bool:
        """Evaluate if rule should execute.

        Args:
            entity: Resource that triggered evaluation.
            event: Event type (created, updated, section_changed).
            context: Additional context (e.g., old_section, new_section).

        Returns:
            True if rule should execute.
        """
        ...

    async def execute_async(
        self,
        entity: AsanaResource,
        context: AutomationContext,
    ) -> AutomationResult:
        """Execute rule action.

        Args:
            entity: Resource to act upon.
            context: Execution context with client, session, etc.

        Returns:
            Result with success status and details.
        """
        ...
```

**TriggerCondition Design**:
```python
@dataclass(frozen=True)
class TriggerCondition:
    """Declarative specification for rule matching."""

    entity_type: str  # "Process", "Offer", etc.
    event: str        # "created", "updated", "section_changed"
    filters: dict[str, Any] = field(default_factory=dict)

    def matches(self, entity: AsanaResource, event: str, context: dict) -> bool:
        """Check if entity/event match this condition."""
        # Entity type check, event check, filter evaluation
        ...
```

**Rationale**: Protocol allows structural subtyping—rules can be dataclasses, Pydantic models, or custom classes. Runtime-checkable protocol validates interface at registration time.

#### 4. Consistent Client Pattern

**Purpose**: Standardized structure for resource clients (Tasks, Projects, Sections, Users).

**Convention** (not formal protocol, but documented pattern):

```python
class {Resource}Client(BaseClient):
    """Client for {resource} operations."""

    # === Async primary methods ===
    async def get_async(
        self, {resource}_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None
    ) -> Model | dict[str, Any]:
        """Get single {resource} by GID."""
        ...

    async def create_async(
        self, data: dict[str, Any], *, raw: bool = False
    ) -> Model | dict[str, Any]:
        """Create new {resource}."""
        ...

    async def update_async(
        self, {resource}_gid: str, data: dict[str, Any], *, raw: bool = False
    ) -> Model | dict[str, Any]:
        """Update existing {resource}."""
        ...

    async def delete_async(self, {resource}_gid: str) -> None:
        """Delete {resource}."""
        ...

    # === Sync wrappers ===
    @sync_wrapper
    def get(self, {resource}_gid: str, **kwargs) -> Model | dict[str, Any]:
        """Sync wrapper for get_async."""
        return self.get_async({resource}_gid, **kwargs)

    # === List operations ===
    def list_async(self, *, limit: int = 100, offset: str | None = None) -> PageIterator[Model]:
        """List all {resources}."""
        ...

    def list_for_{parent}_async(
        self, {parent}_gid: str, *, limit: int = 100
    ) -> PageIterator[Model]:
        """List {resources} for specific parent."""
        ...
```

**Type Overloads** for `raw` parameter:
```python
@overload
async def get_async(
    self, {resource}_gid: str, *, raw: Literal[False] = ..., ...
) -> Model: ...

@overload
async def get_async(
    self, {resource}_gid: str, *, raw: Literal[True], ...
) -> dict[str, Any]: ...

async def get_async(
    self, {resource}_gid: str, *, raw: bool = False, ...
) -> Model | dict[str, Any]:
    # Implementation
    ...
```

**Rationale**: Consistency reduces cognitive load. Developers learn one client, understand all clients. Type overloads provide correct inference for `raw` parameter without runtime cost.

---

## Rationale

### Why Protocols Over ABC?

| Aspect | Protocol | ABC |
|--------|----------|-----|
| Structural typing | Yes | No |
| Inheritance required | No | Yes |
| Runtime checkable | Optional (`@runtime_checkable`) | Always |
| Duck-typing | Enabled | Disabled |
| Pattern in SDK | Established (LogProvider, CacheProvider) | Would break pattern |

Protocols match Python's philosophy: "If it quacks like a duck...". Consumers integrate existing systems without modification.

### Why Runtime-Checkable?

`@runtime_checkable` enables `isinstance()` checks:
```python
if isinstance(rule, AutomationRule):
    # Type checker knows rule has id, name, trigger
    print(rule.name)
```

This combines structural subtyping (compile-time) with runtime validation.

### Why Null Object Pattern?

Null implementations (`NullCacheProvider`, `NullObservabilityHook`) eliminate conditionals:

```python
# Without null object
if self._observability_hook is not None:
    await self._observability_hook.on_request_start(...)

# With null object
await self._observability_hook.on_request_start(...)  # Always safe
```

Null object methods are no-ops with zero side effects.

### Why Extend Rather Than Replace?

CacheProvider grew from 3 to 11 methods rather than creating `VersionedCacheProvider`:
- **Zero breakage**: Existing `cache.get()` calls work unchanged
- **Incremental migration**: Consumers adopt versioned methods gradually
- **Single protocol**: No conditional logic for "which protocol" checks
- **Separation of concerns**: Basic methods for simple caching, versioned methods for Asana resources

---

## Alternatives Considered

### Alternative 1: Abstract Base Classes (ABC)

- **Description**: Use ABC with `@abstractmethod` decorators
- **Pros**: Explicit contract, IDE support for unimplemented methods
- **Cons**: Requires inheritance, breaks duck-typing, inconsistent with SDK patterns
- **Why not chosen**: SDK uses Protocol pattern for all injection points; ABC would create inconsistency

### Alternative 2: Separate Protocols for Each Capability

- **Description**: `BasicCacheProvider` + `VersionedCacheProvider` as distinct protocols
- **Pros**: Clear capability boundaries, minimal interfaces
- **Cons**: SDK must accept both protocols, complex conditional logic, confuses consumers about which to implement
- **Why not chosen**: Single extended protocol is simpler; Protocol flexibility handles capability detection

### Alternative 3: Decorator/Mixin-Based Extension

- **Description**: Add versioning via decorators or mixins rather than protocol methods
- **Pros**: Composable capabilities
- **Cons**: Multiple inheritance complexity, MRO issues, violates Protocol pattern
- **Why not chosen**: Explicit protocol methods are clearer and type-checkable

### Alternative 4: Callback Dict Pattern

- **Description**: Pass `{event_name: callable}` dict instead of protocol
- **Pros**: Simple, no class needed
- **Cons**: No type safety, no IDE completion, easy to misspell event names
- **Why not chosen**: Protocol provides better developer experience

---

## Consequences

### Positive

1. **Clean integration**: Teams plug in custom systems without SDK modifications
2. **Type safety**: Protocol violations caught at development time
3. **Zero overhead**: Null implementations are effectively no-cost
4. **Consistent pattern**: All extensibility points follow same approach
5. **Future extensibility**: New protocol methods can be added (with defaults)
6. **Duck-typing**: Existing classes work if they match signatures

### Negative

1. **Protocol verbose**: Multiple methods per protocol
2. **Learning curve**: Developers must understand Protocol pattern
3. **Method overhead**: Each call goes through protocol boundary (minimal cost)
4. **Default implementations**: Existing providers must add stub methods for new protocol methods

### Neutral

1. **Runtime-checkable**: Optional `isinstance()` support
2. **Documentation**: Protocols must show usage examples
3. **Testing**: Need tests for protocol compliance

---

## Compliance

### How This Decision Will Be Enforced

1. **All new extensibility points**: Must use `typing.Protocol`
2. **Protocol definitions**: Must include `@runtime_checkable` decorator and docstring examples
3. **Default implementations**: Required for optional protocols (Null Object pattern)
4. **Type checking**: `mypy --strict` validates protocol compliance in CI
5. **Documentation**: Each protocol must have usage example in docstring

### Code Review Checklist

- [ ] Protocol defined with `@runtime_checkable`
- [ ] Docstring includes usage example
- [ ] Null/default implementation provided
- [ ] Methods use type hints
- [ ] Protocol follows existing naming conventions

---

## Pattern Index

**When you need to...**

| Need | Pattern | Protocol |
|------|---------|----------|
| Integrate cache backend | Implement CacheProvider | CacheProvider |
| Add metrics/tracing | Implement ObservabilityHook | ObservabilityHook |
| Create custom automation | Implement AutomationRule | AutomationRule |
| Add new resource client | Follow Consistent Client Pattern | (convention, not protocol) |

---

**Related**: ADR-SUMMARY-CACHE (versioning details), ADR-SUMMARY-API-INTEGRATION (client implementations), reference/PATTERNS.md (full catalog)

**Supersedes**: Individual ADRs ADR-0007, ADR-0016, ADR-0085, ADR-0103
