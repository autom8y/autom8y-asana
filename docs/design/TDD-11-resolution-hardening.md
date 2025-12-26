# TDD-11: Resolution & Foundation Hardening

> Consolidated TDD for cross-holder resolution, cascade fixes, and foundation hardening.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-0016 (Cascade and Fixes), TDD-0018 (Cross-Holder Resolution), TDD-0019 (Foundation Hardening)
- **Related ADRs**: ADR-0024 (Name Resolution), ADR-0038 (Resilience & Graceful Degradation)

---

## Overview

This TDD consolidates three related design documents addressing cross-holder entity resolution, cascade operation fixes, and SDK foundation hardening. Together, these designs ensure:

1. **Cross-Holder Resolution**: AssetEdit entities can resolve to their owning Unit and Offer across the business model hierarchy using pluggable resolution strategies
2. **Cascade Fixes**: Critical bugs in cascade execution and custom field handling are addressed
3. **Foundation Hardening**: Exception naming, API surface cleanup, logging standardization, and observability protocol improvements

**Why consolidated?** These designs share common patterns around error handling, resolution strategies, and foundation quality improvements that benefit from unified documentation.

---

## Cross-Holder Resolution

### Problem Statement

AssetEdit entities exist outside the standard Unit/Offer containment hierarchy. They need to resolve their owning business entities dynamically using multiple strategies.

### Resolution Architecture

```
                                    +------------------------+
                                    |      AsanaClient       |
                                    | (tasks.get_async,      |
                                    |  tasks.dependents_async)|
                                    +------------------------+
                                              |
                                              v
+------------------+    resolve     +-------------------+
|   AssetEdit      |--------------->|  Resolution       |
| (extends Process)|                |  Module           |
| - 11 typed fields|                | - strategies      |
| - resolve_unit() |                | - batch helpers   |
| - resolve_offer()|                +-------------------+
+------------------+                          |
        |                                     |
        v                                     v
+------------------+                +-------------------+
| Business Model   |                | ResolutionResult  |
| - Business       |<---------------|  [T]              |
| - Unit           |    returns     | - entity          |
| - Offer          |                | - strategy_used   |
+------------------+                | - candidates      |
                                    +-------------------+
```

### Resolution Strategy Enum

```python
class ResolutionStrategy(str, Enum):
    """Available resolution strategies with priority ordering.

    Priority order (for AUTO mode):
    1. DEPENDENT_TASKS - Most reliable, domain-specific relationship
    2. CUSTOM_FIELD_MAPPING - Vertical field matching
    3. EXPLICIT_OFFER_ID - Direct ID reference

    AUTO executes strategies in priority order until one succeeds.
    """

    DEPENDENT_TASKS = "dependent_tasks"
    CUSTOM_FIELD_MAPPING = "custom_field_mapping"
    EXPLICIT_OFFER_ID = "explicit_offer_id"
    AUTO = "auto"

    @classmethod
    def priority_order(cls) -> list[ResolutionStrategy]:
        """Return strategies in priority order (for AUTO mode)."""
        return [
            cls.DEPENDENT_TASKS,
            cls.CUSTOM_FIELD_MAPPING,
            cls.EXPLICIT_OFFER_ID,
        ]
```

### Resolution Result Pattern

```python
@dataclass
class ResolutionResult(Generic[T]):
    """Result of a resolution operation with strategy transparency.

    Per ADR-0024: First match with ambiguous flag and candidates.

    Attributes:
        entity: Resolved entity or None. If ambiguous, contains first match.
        strategy_used: Strategy that produced the result.
        strategies_tried: All strategies attempted in order.
        ambiguous: True if multiple matches were found.
        candidates: All matching entities.
        error: Error message if resolution failed.
    """

    entity: T | None = None
    strategy_used: ResolutionStrategy | None = None
    strategies_tried: list[ResolutionStrategy] = field(default_factory=list)
    ambiguous: bool = False
    candidates: list[T] = field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        """True if exactly one match found (entity set, not ambiguous)."""
        return self.entity is not None and not self.ambiguous
```

### AssetEdit Entity

```python
class AssetEdit(Process):
    """AssetEdit entity extending Process with 11 typed field accessors.

    Hierarchy:
        Business
            +-- AssetEditHolder
                  +-- AssetEdit (this entity)

    Resolution:
        AssetEdit is NOT in the Unit/Offer containment hierarchy.
        It must resolve to Unit/Offer via resolution strategies.
    """

    NAME_CONVENTION: ClassVar[str] = "[AssetEdit Name]"

    class Fields:
        """Custom field name constants for IDE discoverability."""
        ASSET_APPROVAL = "Asset Approval"
        ASSET_ID = "Asset ID"
        EDITOR = "Editor"
        REVIEWER = "Reviewer"
        OFFER_ID = "Offer ID"
        RAW_ASSETS = "Raw Assets"
        REVIEW_ALL_ADS = "Review All Ads"
        SCORE = "Score"
        SPECIALTY = "Specialty"
        TEMPLATE_ID = "Template ID"
        VIDEOS_PAID = "Videos Paid"

    # Resolution methods
    async def resolve_unit_async(
        self,
        client: AsanaClient,
        *,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> ResolutionResult[Unit]:
        """Resolve to owning Unit using configured strategy."""
        ...

    async def resolve_offer_async(
        self,
        client: AsanaClient,
        *,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> ResolutionResult[Offer]:
        """Resolve to owning Offer using configured strategy."""
        ...
```

### Resolution Data Flow (AUTO Strategy)

```
AssetEdit.resolve_unit_async(client, strategy=AUTO)
    |
    v
[1. DEPENDENT_TASKS Strategy]
    |-- Call client.tasks.dependents_async(self.gid).collect()
    |-- For each dependent: check if Unit or in Unit hierarchy
    |-- Result: Unit found?
           +-- YES (single) --> Return ResolutionResult(entity=Unit)
           +-- YES (multiple) --> Mark ambiguous, continue
           +-- NO/Error --> Continue to next strategy
    v
[2. CUSTOM_FIELD_MAPPING Strategy]
    |-- Read self.vertical (inherited from Process)
    |-- Iterate business.units, find matching vertical
    |-- Result: Unit found?
           +-- YES (single) --> Return ResolutionResult(entity=Unit)
           +-- YES (multiple) --> Mark ambiguous, continue
           +-- NO --> Continue to next strategy
    v
[3. EXPLICIT_OFFER_ID Strategy]
    |-- Read self.offer_id
    |-- Fetch Offer: client.tasks.get_async(offer_id)
    |-- Navigate: offer.unit
    |-- Result: Unit found?
           +-- YES --> Return ResolutionResult(entity=Unit)
           +-- NO --> Continue
    v
[All Strategies Exhausted]
    |-- If any ambiguous: Return ResolutionResult(ambiguous=True, candidates=[...])
    |-- Otherwise: Return ResolutionResult(entity=None, error="No match found")
```

### Batch Resolution

```python
async def resolve_units_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    """Batch resolve multiple AssetEdits to Units.

    Optimizes shared lookups by:
    1. Grouping by Business (shared units)
    2. Pre-fetching dependents concurrently
    3. Batch fetching offer_ids

    Returns:
        Dict mapping asset_edit.gid to ResolutionResult[Unit].
    """
```

---

## Cascade Patterns

### Problem Statement

The cascade feature (`CascadeExecutor`) exists but is never invoked during `commit_async()`. Additionally, direct custom field modifications via `task.custom_fields` are silently ignored.

### Cascade Execution Integration

#### Data Model Changes

Add `cascade_results` to `SaveResult`:

```python
@dataclass
class SaveResult:
    """Result of a commit operation."""

    succeeded: list[AsanaResource] = field(default_factory=list)
    failed: list[SaveError] = field(default_factory=list)
    action_results: list[ActionResult] = field(default_factory=list)
    cascade_results: list[CascadeResult] = field(default_factory=list)  # NEW

    @property
    def success(self) -> bool:
        """True if all operations succeeded (CRUD, actions, AND cascades)."""
        crud_ok = len(self.failed) == 0
        actions_ok = all(r.success for r in self.action_results)
        cascades_ok = all(r.success for r in self.cascade_results)
        return crud_ok and actions_ok and cascades_ok
```

#### Commit Flow Integration

```python
async def commit_async(self) -> SaveResult:
    """Execute all pending changes (async).

    Per TDD-TRIAGE-FIXES: Execute cascade operations after actions.
    """
    # Phase 1: Execute CRUD operations and actions
    crud_result, action_results = await self._pipeline.execute_with_actions(
        entities=dirty_entities,
        actions=pending_actions,
        action_executor=self._action_executor,
    )

    # Phase 2: Clear successful actions (selective clearing)
    self._clear_successful_actions(action_results)

    # Phase 3: Execute cascade operations
    cascade_results: list[CascadeResult] = []
    if pending_cascades:
        cascade_result = await self._cascade_executor.execute(pending_cascades)
        cascade_results = [cascade_result]

        # Clear successful cascades, keep failed for retry
        if cascade_result.success:
            self._cascade_operations.clear()

    return SaveResult(
        succeeded=crud_result.succeeded,
        failed=crud_result.failed,
        action_results=action_results,
        cascade_results=cascade_results,
    )
```

### Direct Custom Field Detection

Add snapshot-based detection for direct `custom_fields` modifications:

```python
class Task(AsanaResource):
    """Asana Task resource model."""

    # Snapshot for direct modification detection
    _original_custom_fields: list[dict[str, Any]] | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _capture_custom_fields_snapshot(self) -> "Task":
        """Capture snapshot at initialization."""
        if self.custom_fields is not None:
            self._original_custom_fields = copy.deepcopy(self.custom_fields)
        return self

    def _has_direct_custom_field_changes(self) -> bool:
        """Check if custom_fields was modified directly (not via accessor)."""
        if self._original_custom_fields is None:
            return self.custom_fields is not None and len(self.custom_fields) > 0
        if self.custom_fields is None:
            return True
        return self.custom_fields != self._original_custom_fields

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override to include custom field modifications."""
        data = super().model_dump(**kwargs)

        accessor_changes = (
            self._custom_fields_accessor is not None
            and self._custom_fields_accessor.has_changes()
        )
        direct_changes = self._has_direct_custom_field_changes()

        if accessor_changes and direct_changes:
            # Accessor takes precedence, log warning
            logger.warning("Both accessor and direct modifications detected")
            data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
        elif accessor_changes:
            data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
        elif direct_changes:
            data["custom_fields"] = self._convert_direct_changes_to_api()

        return data
```

### Selective Action Clearing

Clear only successful actions, preserving failed ones for retry:

```python
def _clear_successful_actions(self, action_results: list[ActionResult]) -> None:
    """Remove only successful actions from pending list.

    Failed actions remain for inspection/retry.
    """
    if not action_results:
        self._pending_actions.clear()
        return

    # Build set of successful action identities
    successful_identities: set[tuple[str, ActionType, str | None]] = set()
    for result in action_results:
        if result.success:
            action = result.action
            identity = (action.task.gid, action.action, action.target_gid)
            successful_identities.add(identity)

    # Keep only failed actions
    self._pending_actions = [
        action for action in self._pending_actions
        if (action.task.gid, action.action, action.target_gid) not in successful_identities
    ]
```

---

## Foundation Hardening

### Exception Hierarchy

Rename `ValidationError` to `GidValidationError` with backward-compatible deprecation:

```python
class GidValidationError(SaveOrchestrationError):
    """Raised when entity GID validation fails at track time."""
    pass


# Backward compatibility with deprecation warning
class _DeprecatedValidationErrorMeta(type):
    """Metaclass that warns on ValidationError access."""

    _warned = False

    def __instancecheck__(cls, instance: object) -> bool:
        cls._warn()
        return isinstance(instance, GidValidationError)

    @classmethod
    def _warn(cls) -> None:
        if not cls._warned:
            import warnings
            warnings.warn(
                "ValidationError is deprecated. Use GidValidationError instead. "
                "ValidationError will be removed in v2.0.",
                DeprecationWarning,
                stacklevel=4,
            )
            cls._warned = True


class ValidationError(GidValidationError, metaclass=_DeprecatedValidationErrorMeta):
    """Deprecated alias for GidValidationError."""
    pass
```

### SaveSessionError Exception

New exception for P1 convenience method failures:

```python
class SaveSessionError(SaveOrchestrationError):
    """Raised when a SaveSession commit fails in a convenience method.

    Wraps the SaveResult so callers can inspect what succeeded and failed.
    """

    def __init__(self, result: SaveResult) -> None:
        self.result = result
        failures: list[str] = []

        # CRUD failures
        for err in result.failed:
            failures.append(f"CRUD {err.operation.value}: {err.error}")

        # Action failures
        for action_result in result.action_results:
            if not action_result.success:
                failures.append(f"Action {action_result.action.action.value}: {action_result.error}")

        message = f"SaveSession commit failed. {len(failures)} failure(s)"
        super().__init__(message)
```

### API Surface Cleanup

Remove private functions from `__all__`:

```python
# models/business/__init__.py
# REMOVE from __all__:
# - "_traverse_upward_async"
# - "_convert_to_typed_entity"
# - "_is_recoverable"
```

### Stub Models for Typed Holders

Create minimal typed models for DNA, Reconciliation, and Videography:

```python
class DNA(BusinessEntity):
    """DNA entity - child of DNAHolder.

    Minimal typed model providing type-safe children and bidirectional navigation.
    """

    _dna_holder: DNAHolder | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    @property
    def dna_holder(self) -> DNAHolder | None:
        """Navigate to parent DNAHolder."""
        return self._dna_holder

    @property
    def business(self) -> Business | None:
        """Navigate to root Business."""
        return self._business


class DNAHolder(Task, HolderMixin[DNA]):
    """Holder task containing DNA children."""

    CHILD_TYPE: ClassVar[type[DNA]] = DNA
    _children: list[DNA] = PrivateAttr(default_factory=list)

    @property
    def children(self) -> list[DNA]:
        """All DNA children (typed)."""
        return self._children
```

### ObservabilityHook Protocol

```python
@runtime_checkable
class ObservabilityHook(Protocol):
    """Protocol for observability integration."""

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
        """Called on HTTP request error."""
        ...

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        """Called on rate limit 429."""
        ...

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        """Called on circuit breaker state change."""
        ...

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        """Called before retry attempt."""
        ...
```

### Logging Standardization

```python
@dataclass
class LogContext:
    """Structured logging context."""

    correlation_id: str | None = None
    operation: str | None = None
    entity_gid: str | None = None
    entity_type: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging extra parameter."""
        return {k: v for k, v in asdict(self).items() if v is not None}


# Usage
ctx = LogContext(correlation_id="abc123", operation="track")
logger.info("Processing", extra=ctx.to_dict())
```

---

## Error Recovery

### Circuit Breaker Pattern (Opt-In)

Per ADR-0038, circuit breaker is opt-in for backward compatibility:

```python
@dataclass(frozen=True)
class CircuitBreakerConfig:
    enabled: bool = False  # Opt-in for backward compatibility
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 1
```

**State Machine**:

```
CLOSED --> (failure_threshold reached) --> OPEN
OPEN --> (recovery_timeout elapsed) --> HALF_OPEN
HALF_OPEN --> (probe succeeds) --> CLOSED
HALF_OPEN --> (probe fails) --> OPEN
```

### Cache Graceful Degradation

Cache failures are logged and treated as misses:

```python
def _cache_get(self, key: str, entry_type: EntryType) -> CacheEntry | None:
    """Check cache with graceful degradation."""
    if self._cache is None:
        return None

    try:
        entry = self._cache.get_versioned(key, entry_type)
        if entry and not entry.is_expired():
            return entry
        return None
    except Exception as exc:
        # Graceful degradation: log and return miss
        logger.warning(
            "Cache get failed for %s (key=%s): %s",
            entry_type.value,
            key,
            exc,
        )
        return None  # Treat as cache miss
```

| Scenario | Behavior |
|----------|----------|
| Cache `get()` fails | Log WARNING, return `None`, fetch from API |
| Cache `set()` fails | Log WARNING, continue (next request will re-fetch) |
| Cache `invalidate()` fails | Log WARNING, continue (stale data may remain) |

### P1 Method Error Checking

P1 convenience methods now check `SaveResult.success`:

```python
@error_handler
async def add_tag_async(
    self, task_gid: str, tag_gid: str, *, refresh: bool = False
) -> Task:
    """Add tag to task without explicit SaveSession.

    Args:
        task_gid: Target task GID
        tag_gid: Tag GID to add
        refresh: If True, fetch fresh task state after commit

    Raises:
        SaveSessionError: If the action operation fails
    """
    from autom8_asana.persistence.exceptions import SaveSessionError

    async with SaveSession(self._client) as session:
        task = await self.get_async(task_gid)
        session.add_tag(task, tag_gid)
        result = await session.commit_async()

        if not result.success:
            raise SaveSessionError(result)

    if refresh:
        return await self.get_async(task_gid)
    return task
```

---

## Testing Strategy

### Cross-Holder Resolution Tests

| Category | Tests |
|----------|-------|
| **AssetEdit Entity** | Field accessors, type conversions, enum-to-bool mapping |
| **ResolutionStrategy** | Priority ordering, enum values |
| **ResolutionResult** | success property, ambiguous handling |
| **Strategy Isolation** | Mock API responses, verify resolution logic per strategy |
| **AUTO Orchestration** | Strategy ordering, fallback behavior, ambiguity handling |
| **Batch Helpers** | Optimization verification, partial failure handling |

### Cascade Integration Tests

| Test | Description |
|------|-------------|
| `test_cascade_operations_queued` | Verify `cascade_field()` adds to list |
| `test_cascades_executed_during_commit` | Mock executor, verify `execute()` called |
| `test_cascades_cleared_on_success` | After success, `get_pending_cascades()` empty |
| `test_cascades_preserved_on_failure` | After failure, operations remain |
| `test_direct_modification_detected` | Snapshot comparison works |
| `test_accessor_takes_precedence` | Both modified, accessor wins |

### Foundation Hardening Tests

| Area | Coverage Focus |
|------|----------------|
| Exception rename | Deprecation warning emitted, catching works |
| API surface | Private functions not in namespace |
| Stub models | Type checking, navigation, holder population |
| LogContext | Serialization, None handling |
| ObservabilityHook | Protocol satisfaction, NullObservabilityHook |

### Error Recovery Tests

| Area | Tests |
|------|-------|
| Circuit breaker | State transitions, threshold behavior, recovery |
| Cache degradation | Failure logging, miss behavior, continued operation |
| P1 methods | SaveSessionError raised, result accessible |
| Selective clearing | Partial success preserves failed actions |

---

## Cross-References

### Related ADRs

| ADR | Topic | Relevance |
|-----|-------|-----------|
| ADR-0024 | Name Resolution & Dynamic Discovery | Resolution strategy patterns, ambiguity handling |
| ADR-0038 | Resilience & Graceful Degradation | Circuit breaker, cache degradation |

### Related TDDs

| TDD | Relationship |
|-----|--------------|
| TDD-04 (Batch Save Operations) | SaveSession patterns referenced |
| TDD-07 (Navigation & Hydration) | Business model hierarchy |
| TDD-08 (Business Domain) | Business, Unit, Offer entities |

### Implementation Files

**Cross-Holder Resolution**:
- `src/autom8_asana/models/business/asset_edit.py` - AssetEdit entity
- `src/autom8_asana/models/business/resolution.py` - Resolution module
- `src/autom8_asana/clients/tasks.py` - `dependents_async()` method

**Cascade Fixes**:
- `src/autom8_asana/persistence/session.py` - Cascade integration
- `src/autom8_asana/persistence/models.py` - SaveResult with cascade_results
- `src/autom8_asana/models/task.py` - Custom field snapshot detection

**Foundation Hardening**:
- `src/autom8_asana/persistence/exceptions.py` - Exception hierarchy
- `src/autom8_asana/protocols/observability.py` - ObservabilityHook
- `src/autom8_asana/models/business/dna.py` - Stub model
- `src/autom8_asana/observability/context.py` - LogContext

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Tech Writer | Initial consolidated version from TDD-0016, TDD-0018, TDD-0019 |
