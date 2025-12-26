# ADR-0001: Demo Infrastructure Design

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0088, ADR-0089, ADR-0090
- **Related**: reference/DEMO.md, PRD-SDKDEMO, TDD-SDKDEMO

## Context

The SDK Demonstration Suite showcases autom8_asana capabilities through interactive examples that must be reversible, user-friendly, and resilient to failures. Three infrastructure challenges emerged:

1. **State Management**: Demo operations must restore entities to their initial state after demonstrating each capability
2. **Name Resolution**: Scripts need human-readable names (tags, users, sections) without hardcoding GIDs
3. **Error Handling**: Demos encounter API errors, rate limits, and partial failures

The architecture must balance demonstration value (readable names, graceful failures) with technical pragmatism (session-scoped caching, manual recovery). The system demonstrates SDK functionality while maintaining clear boundaries between SDK code and demo-specific utilities.

## Decision

Implement three-layer demo infrastructure:

### 1. State Capture: Shallow Copy with GID References

Capture scalar fields by value and relationships as GID references only. Restoration uses SDK action operations to re-establish relationships.

```python
@dataclass
class EntityState:
    """Captured state of an entity for restoration."""
    gid: str
    notes: str | None
    custom_fields: dict[str, Any]  # {field_gid: value}

@dataclass
class TaskSnapshot:
    """Complete snapshot of a task for restoration."""
    entity_state: EntityState
    tag_gids: list[str]
    parent_gid: str | None
    memberships: list[MembershipState]
    dependency_gids: list[str]
```

Restoration logic:
- Use `session.add_tag()` / `session.remove_tag()` for tags
- Use `session.set_parent()` for parent restoration
- Use `session.move_to_section()` for section restoration
- Perform differential restoration by comparing initial vs. current GID sets

### 2. Name Resolution: Lazy-Loading with Session-Scoped Caching

Centralized NameResolver class with case-insensitive matching and graceful None returns.

```python
class NameResolver:
    """Resolves human-readable names to Asana GIDs with caching."""

    def __init__(self, client: AsanaClient, workspace_gid: str):
        self._client = client
        self._workspace_gid = workspace_gid
        self._tag_cache: dict[str, str] | None = None  # name -> gid
        self._user_cache: dict[str, str] | None = None
        self._section_cache: dict[str, dict[str, str]] | None = None

    async def resolve_tag(self, name: str) -> str | None:
        """Resolve tag name to GID. Returns None if not found."""
        if self._tag_cache is None:
            await self._load_tags()
        return self._tag_cache.get(name.lower())
```

Behaviors:
- **Lazy loading**: Cache populates on first use
- **Session-scoped**: Single instance per demo run
- **Case-insensitive**: "Optimize" == "optimize"
- **None on miss**: Caller decides handling strategy

### 3. Error Handling: Graceful Degradation with Manual Recovery

Structured error classification enabling operation-level failures without aborting demos.

```python
@dataclass
class DemoError:
    """Structured error with recovery guidance."""
    category: str  # "tag_operation", "custom_field", "restoration"
    operation: str  # "add_tag", "set_field", "restore_notes"
    entity_gid: str
    message: str
    recovery_hint: str | None = None
```

Error response strategy:

| Error Type | Severity | Response |
|------------|----------|----------|
| Pre-flight check failure | Fatal | Abort with clear message |
| API error (4xx) | Operation | Log, skip operation, continue |
| API error (5xx) | Operation | Retry once, then skip |
| Rate limit (429) | Transient | Wait retry_after, then retry |
| Name resolution miss | Soft | Warn, offer to create or skip |
| Restoration failure | Serious | Log, provide manual recovery commands |

## Rationale

### State Capture
- **GID-based restoration is idempotent**: Adding existing tags is no-op, enabling safe partial restoration
- **Memory efficient**: GID strings (16-20 bytes) vs. full objects (potentially KB each)
- **Aligns with SDK patterns**: SaveSession action operations already work with GIDs
- **Enables differential restoration**: Compare initial vs. current GID sets to determine exact changes

### Name Resolution
- **Lazy loading minimizes API calls**: If demo skips tag operations, tag cache never loads
- **Session scope appropriate**: Resources won't change during single demo run
- **Case-insensitive matching improves usability**: Handles natural capitalization variations
- **Centralized resolver reusable**: All 10 demo categories share one instance
- **None return enables caller-controlled handling**: Each context decides skip vs. create vs. error

### Error Handling
- **Graceful degradation maximizes demo value**: Individual failures don't hide working functionality
- **Manual recovery acceptable for demo context**: Not production code; clear instructions suffice
- **Rate limit handling transparent**: Users shouldn't manage 429s manually
- **Pre-flight failures fail fast**: If test entities don't exist, nothing will work
- **Structured errors enable reporting**: DemoError provides consistent logging format

## Alternatives Considered

### State Capture Alternatives

#### Deep Copy State Capture
- **Description**: Store complete serialized copies of all related entities
- **Pros**: Complete state, no re-fetching needed
- **Cons**: Memory intensive, stale data risk, complex serialization
- **Why not chosen**: Overkill for restoration needs; only need to re-establish relationships

#### No State Capture (Re-fetch Before Restore)
- **Description**: Fetch current state from API at restoration time
- **Pros**: Always accurate, minimal memory
- **Cons**: Additional API calls, cannot determine original state after multiple changes
- **Why not chosen**: Cannot restore to initial state without knowing it

#### Full Entity Tracking via SaveSession
- **Description**: Use SaveSession's ChangeTracker for state management
- **Pros**: Leverages existing infrastructure
- **Cons**: Different lifecycle, couples demo to SDK internals
- **Why not chosen**: Demo state has different lifecycle than SaveSession operations

### Name Resolution Alternatives

#### Eager Loading at Startup
- **Description**: Load all caches before any operations
- **Pros**: Fast resolution during demo, predictable latency
- **Cons**: Slow startup, loads unused data, users wait for all caches
- **Why not chosen**: Lazy loading provides better perceived performance

#### No Caching (Lookup Each Time)
- **Description**: Every name resolution makes API call
- **Pros**: Always fresh data
- **Cons**: Extremely slow, unnecessary API load, rate limit risk
- **Why not chosen**: Unacceptable performance for interactive demo

#### Extend CustomFieldAccessor Pattern
- **Description**: Adapt CustomFieldAccessor's approach for all resource types
- **Pros**: Consistent pattern, leverages existing code
- **Cons**: CustomFieldAccessor works with entity-specific lists; tags/users are workspace-level
- **Why not chosen**: Fundamentally different resource types require different patterns

#### Global Persistent Cache
- **Description**: Cache persists across demo runs (file/redis)
- **Pros**: Instant resolution after first run
- **Cons**: Stale data, invalidation complexity, overkill for demos
- **Why not chosen**: Session-scoped caching simpler and sufficient

### Error Handling Alternatives

#### Fail-Fast on Any Error
- **Description**: Any error aborts demo immediately
- **Pros**: No partial state, simple logic, obvious failure point
- **Cons**: One API hiccup stops entire demo, hides working functionality
- **Why not chosen**: Too aggressive for demo context

#### Silent Error Swallowing
- **Description**: Log errors but always continue
- **Pros**: Demo always completes
- **Cons**: User may not notice failures, inconsistent state without warning
- **Why not chosen**: Hides important information

#### Automatic Rollback on Failure
- **Description**: Any failure triggers immediate restoration
- **Pros**: Guaranteed clean state
- **Cons**: Restoration itself may fail, loses progress, complex tracking
- **Why not chosen**: Rollback complexity not justified for demo scripts

#### Transaction-Style All-or-Nothing
- **Description**: Preview operations, execute only if all will succeed
- **Pros**: Clean semantics, no partial state
- **Cons**: Can't predict success without trying, Asana API doesn't support transactions
- **Why not chosen**: Not technically feasible

## Consequences

### Positive
1. **Efficient memory usage**: Only GID strings and scalars stored
2. **Minimal startup latency**: Lazy loading defers API calls until needed
3. **User-friendly interface**: Human-readable names throughout
4. **Demo resilience**: Individual failures don't abort entire demonstration
5. **Clear error visibility**: Structured errors with actionable recovery guidance
6. **Centralized resolution logic**: Easy to maintain and test
7. **Idempotent restoration**: Safe to retry failed operations

### Negative
1. **Related entity changes not detected**: If tag renamed during demo, GID restoration is correct but name change invisible
2. **First lookup is slow**: API call required to populate cache
3. **Manual state update discipline required**: Developer must call update_current() after operations
4. **Manual recovery may be needed**: Restoration failures require user intervention
5. **Partial state possible**: Some operations may succeed while others fail
6. **Cache not shared across runs**: Fresh lookups required each demo run

### Neutral
1. **Two-phase restoration**: First restore fields (CRUD), then relationships (actions)
2. **Enum option resolution requires field definition**: Must fetch field to get option name→GID mapping
3. **Project-scoped section caching**: Section cache keyed by project_gid
4. **Error list grows during demo**: More operations create more potential errors
5. **Recovery hints operation-specific**: Each operation type needs custom guidance

## Compliance

Ensure adherence through:

### State Capture
- Code review checklist: "State capture uses GID references, not deep copies"
- Unit tests verify EntityState contains only GIDs for relationships
- Integration tests verify restoration produces identical API responses

### Name Resolution
- Code review: "Name resolution uses NameResolver class, not inline lookups"
- No hardcoded GIDs in demo scripts (except entity GIDs from test data doc)
- All resolution calls use `await resolver.resolve_*()` pattern
- Missing name handling is explicit (check for None, decide action)

### Error Handling
- All API calls wrapped in run_operation() or equivalent
- No bare except: clauses that swallow errors silently
- Pre-flight checks use assert or early return with message
- Restoration failures always provide recovery_hint
- Demo summary includes error count and recovery instructions
