# ADR Summary: Core Architecture

> Consolidated decision record for core structural decisions and module organization. Individual ADRs archived.

## Overview

The autom8_asana system is built on a layered architecture that separates SDK infrastructure from business domain logic while maintaining clean extensibility boundaries. The architecture follows three core principles:

**Protocol-based extensibility**: All integration points use `typing.Protocol` for structural subtyping, enabling dependency injection without coupling. This allows the SDK to integrate with external systems (auth, caching, logging) while consumers inject their own implementations without inheritance.

**Layered integration boundaries**: The system maintains clear separation between the Asana SDK layer (custom httpx-based transport with rate limiting and retry logic), the core SDK layer (minimal `AsanaResource` base class with Pydantic models), and the autom8 business layer (full `Item` class with lazy loading, caching, and domain-specific logic).

**Two-tier persistence with graceful degradation**: Cache architecture uses Redis for hot data (sub-5ms latency) and S3 for cold/durable storage, with write-through to both tiers and cache-aside reads with promotion. Thread safety is guaranteed via Redis WATCH/MULTI for atomic operations and connection pooling for concurrent access.

## Key Decisions

### 1. Foundation: Protocol-Based Extensibility
**Context**: SDK must integrate with external systems without coupling to specific implementations

**Decision**: Use `typing.Protocol` for all extensibility points (ADR-0001)

**Implementation**:
- `AuthProvider`: Secret/token retrieval
- `CacheProvider`: Get/set/delete caching operations
- `LogProvider`: Python logging-compatible interface

**Rationale**: Structural subtyping requires no inheritance. Existing classes like `logging.Logger` automatically satisfy protocols. Enables static type checking while maintaining zero coupling between SDK and consumers.

### 2. SDK Integration: Custom Transport Layer
**Context**: Official Asana SDK is sync-only and lacks custom rate limiting, retry, and concurrency control

**Decision**: Replace Asana SDK's HTTP layer with httpx-based transport, retain types and error parsing (ADR-0003)

**What we replaced**:
- HTTP request handling → custom `AsyncHTTPClient` with httpx
- Authentication → `AuthProvider` protocol
- Pagination → custom `PageIterator`
- Sync/async handling → async-first with sync wrappers

**What we kept**:
- Type definitions for API compatibility reference
- Error response parsing patterns

**Rationale**: Full control over transport enables async-first design, custom rate limiting (1500 req/min token bucket), exponential backoff with jitter, and configurable connection pooling. Official SDK remains as dependency for type reference and API change tracking.

### 3. Entity Model Boundary: Minimal SDK, Full Monolith
**Context**: Legacy `Item` class mixes pure API data with business logic, caching, lazy loading, and SQL integration

**Decision**: SDK provides minimal `AsanaResource` base class; full `Item` stays in autom8 monolith (ADR-0004)

**SDK layer** (`AsanaResource`):
- Pydantic BaseModel with `gid`, `resource_type`
- Serialization via `to_api_dict()`, `from_api_response()`
- Optional `LazyLoader` protocol (no implementation)
- Zero dependencies on caching, SQL, or business logic

**Monolith layer** (`Item extends AsanaResource`):
- Lazy loading via TaskCache
- Business model instantiation (Offer, Business, Unit)
- Domain validation
- SQL synchronization

**Rationale**: Clean separation enables SDK reuse across microservices while autom8 owns domain complexity. New services use `AsanaResource` directly without inheriting business logic.

### 4. API Surface Definition: Three-Tier Visibility
**Context**: Python lacks runtime API visibility enforcement; need conventions for stable vs internal APIs

**Decision**: Use explicit `__all__` exports and underscore prefixes for three-tier visibility model (ADR-0012)

**Tier 1 - Public API** (exported from root):
- Semantic versioning applies
- Everything in `autom8_asana.__all__`
- Main entry point (`AsanaClient`), config classes, exceptions, protocols, models

**Tier 2 - Semi-Public API** (submodule exports):
- Individual client classes, model classes, protocols, transport utilities
- Accessible via submodule imports
- Stable signatures, new methods may be added in minor versions

**Tier 3 - Internal API** (underscore prefix):
- `_defaults/`, `_internal/`, `_compat.py`
- May change or disappear in any release
- No documentation

**Rationale**: Clear public surface enables refactoring internals without version bumps. IDE autocomplete shows only stable APIs. Follows Python community conventions while maintaining explicit contracts.

### 5. Cache Backend: Redis for Hot Tier
**Context**: Legacy S3 caching has 50-200ms latency; requirements demand <5ms p99 reads

**Decision**: Redis-only backend with structured keys for entry types and metadata (ADR-0017)

**Key structure**:
```
asana:tasks:{gid}:task          -> JSON (full task data)
asana:tasks:{gid}:subtasks      -> JSON array
asana:tasks:{gid}:dependencies  -> JSON array
asana:tasks:{gid}:_meta         -> HASH (version timestamps)
asana:struc:{task_gid}:{project_gid} -> JSON (structural data)
```

**Operations**:
- Versioned get/set with TTL support
- Batch operations via MGET and pipelined HSET
- Connection pooling with max_connections=10
- Health checks via PING

**Rationale**: Redis provides sub-5ms latency (vs S3's 50-200ms), native TTL support, atomic operations via WATCH/MULTI, and efficient batch operations. Purpose-built for caching workloads.

### 6. Cache Architecture: Two-Tier with Promotion
**Context**: Redis-only lacks durability and is expensive for cold data; computed STRUC data is costly to rebuild

**Decision**: Two-tier cache with Redis (hot) and S3 (cold), coordinated by `TieredCacheProvider` (ADR-0026)

**Architecture**:
- **Write strategy**: Write-through to both Redis and S3 (durability)
- **Read strategy**: Cache-aside with promotion (Redis → S3 → API)
- **Failure mode**: Graceful degradation (S3 failures don't break Redis)
- **Feature flag**: `ASANA_CACHE_S3_ENABLED` for gradual rollout

**Tier placement**:
- **Redis (hot)**: Modification timestamps (25s TTL), active metadata (1h), promoted STRUC (1h)
- **S3 (cold)**: Full task snapshots (7d), STRUC (30d), subtasks/dependencies (30d), dataframes (24h)

**Cost impact**: ~$25/month vs ~$92/month for Redis-only (80-90% reduction)

**Rationale**: Durability is mandatory for expensive computed data. Heterogeneous access patterns benefit from tiered storage. S3 failures don't impact hot path.

### 7. Thread Safety: Optimistic Locking
**Context**: Concurrent access to cache creates race conditions in multi-threaded/async environments

**Decision**: Redis WATCH/MULTI for atomic updates, per-operation connections from pool, threading.Lock for in-memory caches (ADR-0024)

**Redis pattern**:
```python
conn.watch(redis_key)           # Monitor for changes
current_data = conn.hgetall()   # Read current value
new_data = update_fn(current)   # Apply update
pipe = conn.pipeline()          # Start transaction
pipe.hset(key, new_data)        # Write update
pipe.execute()                  # Commit (fails if key changed)
```

**Retry on conflict**: Max 3 retries, raises `ConcurrentModificationError` on exhaustion

**In-memory locking**: `threading.Lock` for BatchModificationChecker and CacheMetrics (process-local only)

**Rationale**: WATCH/MULTI provides optimistic locking across all clients (ECS tasks, processes). Connection pooling enables concurrent operations. No distributed locks (Redlock) needed.

### 8. Entity Registry: Per-Session Scope
**Context**: GID-based entity tracking scope affects memory, isolation, and concurrency

**Decision**: Registry scoped to `SaveSession` instance, not global or client-scoped (ADR-0080)

**Lifecycle**:
```
Session A created    → Tracker A created (empty)
Session A tracks X   → X in Tracker A
Session B created    → Tracker B created (empty, independent)
Session B tracks X   → X in Tracker B (independent copy)
Session A commits    → X saved, Tracker A marks clean
Session A exits      → Tracker A garbage collected
```

**Implications**:
- Entities tracked in Session A are not visible in Session B
- Same GID can be tracked independently in multiple sessions
- Registry is garbage collected when session exits
- No cross-session synchronization or locks needed

**Rationale**: Matches ORM patterns (SQLAlchemy, Django). Predictable isolation with clear lifecycle. No concurrency complexity. Memory bounded by single session's entities.

### 9. Pipeline Architecture: Canonical Projects as Pipelines
**Context**: Initial design assumed separate "pipeline projects" for Processes; discovery showed canonical projects ARE the pipelines

**Decision**: Remove ProcessProjectRegistry; canonical project IS the pipeline (ADR-0101)

**Corrected model**:
```
Process
  ├── Hierarchy: subtask of ProcessHolder
  └── Pipeline: MEMBER of canonical project (e.g., "Sales")
              The canonical project HAS sections = pipeline states
```

**Removed**:
- `ProcessProjectRegistry` singleton and all registry lookup logic
- `add_to_pipeline()` method (concept was wrong)
- `move_to_state()` wrapper (use `SaveSession.move_to_section()` directly)

**Simplified**:
- `pipeline_state`: Extract from canonical project section membership
- `process_type`: Derive from canonical project name matching

**Rationale**: Processes receive project membership through creation/hierarchy, not separate "add to pipeline" operation. Eliminates ~1,000 lines of incorrect code and configuration burden.

### 10. Post-Commit Hook System
**Context**: Automation Layer requires evaluating rules after SaveSession commits complete

**Decision**: Extend EventSystem with `on_post_commit` hook type, consistent with existing pre/post_save patterns (ADR-0102)

**Implementation**:
```python
@dataclass
class EventSystem:
    _post_commit_hooks: list[PostCommitHook]

    async def emit_post_commit(self, result: SaveResult) -> None:
        for hook in self._post_commit_hooks:
            try:
                await hook(result)
            except Exception:
                pass  # Post-commit hooks cannot fail the commit
```

**Integration**: AutomationEngine registers as built-in consumer; custom handlers also supported

**Rationale**: Consistent with existing hook patterns. Extensible beyond automation. Post-commit failures don't fail primary commit. Testable independently.

### 11. Field Seeding: Dedicated Service
**Context**: Pipeline conversion requires populating fields from hierarchy cascade, source Process carry-through, and computed values

**Decision**: Create dedicated `FieldSeeder` service separate from entity creation and rule execution (ADR-0105)

**Field sources** (in precedence order):
1. Cascade from Business (lowest priority): Office Phone, Company ID, Business Name
2. Cascade from Unit: Vertical, Platforms, Booking Type
3. Carry-through from source Process: Contact Phone, Priority, Assigned To
4. Computed fields (highest priority): Started At = today

**Implementation**:
```python
class FieldSeeder:
    async def seed_fields_async(self, business, unit, source_process) -> dict[str, Any]:
        fields = {}
        fields.update(await self.cascade_from_hierarchy_async(business, unit))
        fields.update(await self.carry_through_from_process_async(source_process))
        fields.update(await self.compute_fields_async(source_process))
        return fields
```

**Rationale**: Single responsibility (compute values, don't create entities). Testable independently. Reusable across automation rules. Explicit field source precedence.

### 12. Workspace Project Registry: Dynamic Discovery
**Context**: Static `ProjectTypeRegistry` works for entities with dedicated projects but fails for Processes in multiple pipeline projects

**Decision**: `WorkspaceProjectRegistry` as composition wrapper with lazy discovery triggered on first unregistered GID lookup (ADR-0108)

**Architecture**:
- **Composition** over extension: Delegates Tier 1 to `ProjectTypeRegistry`, adds workspace discovery
- **Module-level singleton**: Projects are stable; test isolation via `reset()`
- **Lazy discovery timing**: First unregistered GID triggers discovery; explicit `discover_async()` available
- **ProcessType derivation**: Case-insensitive contains matching of ProcessType values in project names

**Integration**:
- Async detection uses `lookup_or_discover_async()`
- Sync detection uses static registry only (no async discovery)
- O(1) name-to-GID lookup after discovery

**Rationale**: Process entities exist in multiple projects; dynamic discovery adapts to workspace. Lazy timing provides good DX. Contains matching handles project name variations.

### 13. Process Field Organization: Composition Over Inheritance
**Context**: Process entities have 8 generic fields but actual pipelines have 67+ (Sales), 41+ (Onboarding), 35+ (Implementation)

**Decision**: Single `Process` class with all pipeline fields organized in logical groups (ADR-0136)

**Architecture**:
```python
class Process(BusinessEntity):
    # === COMMON FIELDS (8, shared across all pipelines) ===
    started_at = TextField()
    process_notes = TextField(field_name="Process Notes")
    # ...

    # === SALES PIPELINE FIELDS (54+) ===
    deal_value = NumberField(field_name="Deal Value")
    close_date = DateField(field_name="Close Date")
    sales_stage = EnumField(field_name="Sales Stage")
    # ...

    # === ONBOARDING PIPELINE FIELDS (33+) ===
    onboarding_status = EnumField(field_name="Onboarding Status")
    # ...
```

**Field access**: All fields accessible on any Process instance; returns `None` when field doesn't exist on underlying task

**Runtime type checking**:
```python
if process.process_type == ProcessType.SALES:
    value = process.deal_value  # Decimal | None
```

**Rationale**: Process type is determined at runtime by project membership. Composition avoids casting burden. Descriptor pattern gracefully handles non-existent fields. Consistent with other entity patterns.

### 14. Detection Package Structure: Module Organization
**Context**: `detection.py` grew to 1,125 lines containing 4 distinct concerns, violating 250-line soft limit

**Decision**: Convert to package directory with 7 focused modules organized by tier and concern (ADR-0142)

**Structure**:
```
detection/
    __init__.py        # Re-exports for backward compatibility
    types.py           # Types and constants (170 lines)
    config.py          # Configuration data (230 lines)
    tier1.py           # Project membership detection (180 lines)
    tier2.py           # Name pattern detection (150 lines)
    tier3.py           # Parent inference detection (60 lines)
    tier4.py           # Structure inspection detection (80 lines)
    facade.py          # Unified orchestration (200 lines)
```

**Dependency layering**: `types.py` → `config.py` → `tier{1-4}.py` → `facade.py` → `__init__.py`

**Re-export strategy**: `__init__.py` re-exports all 22 public symbols plus 5 private functions for test compatibility

**Rationale**: Each module has single responsibility. 60-230 line files vs 1,125. Reduced cognitive load. Separate files enable parallel work on different tiers. Backward compatible via re-exports.

## Cross-References

**Related Summaries**:
- ADR-SUMMARY-PATTERNS: Protocol definitions, descriptor patterns, factory patterns
- ADR-SUMMARY-CACHE: Staleness detection, TTL strategies, invalidation patterns
- ADR-SUMMARY-PERSISTENCE: SaveSession lifecycle, change tracking, action management

**Related Technical Decisions**:
- TDD-0001: SDK Architecture (overall system design)
- TDD-0008: Intelligent Caching (cache layer implementation)
- TDD-AUTOMATION-LAYER: Automation rule execution
- TDD-HARDENING-F: GID-based entity identity

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| [ADR-0001](ADR-0001-protocol-extensibility.md) | Protocol-Based Extensibility | 2025-12-08 | Use `typing.Protocol` for all integration points |
| [ADR-0003](ADR-0003-asana-sdk-integration.md) | Asana SDK Integration | 2025-12-08 | Replace HTTP layer, retain types and error parsing |
| [ADR-0004](ADR-0004-item-class-boundary.md) | Item Class Boundary | 2025-12-08 | Minimal `AsanaResource` in SDK, full `Item` in monolith |
| [ADR-0012](ADR-0012-public-api-surface.md) | Public API Surface | 2025-12-08 | Three-tier visibility with `__all__` and underscore prefixes |
| [ADR-0017](ADR-0017-redis-backend-architecture.md) | Redis Backend | 2025-12-09 | Redis-only backend with structured keys and connection pooling |
| [ADR-0024](ADR-0024-thread-safety-guarantees.md) | Thread Safety | 2025-12-09 | Redis WATCH/MULTI for atomicity, connection pooling for concurrency |
| [ADR-0026](ADR-0026-two-tier-cache-architecture.md) | Two-Tier Cache | 2025-12-09 | Redis (hot) + S3 (cold) with write-through and promotion |
| [ADR-0080](ADR-0080-entity-registry-scope.md) | Entity Registry Scope | 2025-12-16 | Per-SaveSession registry for isolation and predictable lifecycle |
| [ADR-0101](ADR-0101-process-pipeline-correction.md) | Pipeline Architecture | 2025-12-17 | Canonical projects ARE pipelines; remove ProcessProjectRegistry |
| [ADR-0102](ADR-0102-post-commit-hook-architecture.md) | Post-Commit Hooks | 2025-12-17 | EventSystem `on_post_commit` for automation integration |
| [ADR-0105](ADR-0105-field-seeding-architecture.md) | Field Seeding | 2025-12-17 | Dedicated `FieldSeeder` service for cascade and carry-through |
| [ADR-0108](ADR-0108-workspace-project-registry.md) | Workspace Project Registry | 2025-12-18 | Lazy discovery with composition wrapper for dynamic projects |
| [ADR-0136](ADR-0136-process-field-architecture.md) | Process Field Architecture | 2025-12-19 | Composition with field groups on single Process class |
| [ADR-0142](ADR-0142-detection-package-structure.md) | Detection Package Structure | 2025-12-19 | Convert 1,125-line file to 7-module package by tier |

## Evolution Notes

**Major architectural pivots**:

1. **Cache architecture** (ADR-0017 → ADR-0026): Evolved from Redis-only to two-tier after production analysis revealed durability requirements and cost inefficiency for cold data.

2. **Pipeline architecture** (ADR-0098 → ADR-0101): Corrected from "dual membership" model to "canonical projects as pipelines" after discovering actual Asana implementation. Removed ~1,000 lines of incorrect code.

3. **Process field organization** (ADR-0136): Chose composition over inheritance for pipeline-specific fields, enabling runtime type determination while maintaining single Process class simplicity.

**Stability indicators**:

- **Foundation decisions stable**: Protocol-based extensibility, SDK integration layer, API surface definition have not changed since initial design.
- **Infrastructure decisions stable**: Redis backend, thread safety patterns, entity registry scope remain unchanged.
- **Business layer evolved**: Pipeline and Process architecture corrected based on domain discovery.

**Design patterns established**:

- Protocols over inheritance for extensibility
- Composition over inheritance for runtime type determination
- Per-operation connections from pool for thread safety
- Lazy discovery with feature flags for gradual rollout
- Package organization by concern with backward-compatible re-exports
