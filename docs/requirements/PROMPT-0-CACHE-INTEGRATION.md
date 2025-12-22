# Orchestrator Initialization: Cache Integration Initiative

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`autom8-asana`** - SDK patterns, SaveSession, Business entities, cache infrastructure
  - Activates when: Working with cache providers, entity hierarchy, persistence layer

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

- **`prompting`** - Agent invocation patterns, workflow examples
  - Activates when: Invoking agents, structuring prompts

**How Skills Work**: Skills load automatically based on your current task. When you need template formats, the `documentation` skill activates. When you need SDK patterns, the `autom8-asana` skill activates.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, performance verification |

## The Mission: Wire Up Existing Cache Infrastructure for Transparent Performance

The autom8_asana SDK has sophisticated caching infrastructure (~4,000 lines across 15 modules) that is currently **dormant**. This initiative activates that infrastructure to deliver transparent performance improvements without requiring consumer code changes.

### Why This Initiative?

- **Immediate Performance**: A 3,527-task project currently takes ~1 minute with zero caching
- **Infrastructure ROI**: Two-tier cache (Redis+S3) with versioning, staleness detection, and graceful degradation already exists but is unused
- **Developer Experience**: Consumers should get intelligent caching by default, not require explicit configuration
- **Scale Preparation**: Entity hierarchy operations (Business > Unit > Offer) amplify API calls; caching is essential at scale

### Current State

**Cache Infrastructure (Sophisticated - EXISTS)**:
- `TieredCacheProvider`: Redis (hot) + S3 (cold) with write-through and promotion
- `InMemoryCacheProvider`: Full implementation with TTL, versioning, eviction
- `CacheEntry` with EntryType enum (TASK, SUBTASKS, DEPENDENCIES, DATAFRAME, etc.)
- Versioning via `modified_at` timestamp with staleness detection
- STRICT vs EVENTUAL freshness modes
- Overflow protection, graceful degradation, metrics collection
- `CacheSettings` with TTL configuration, overflow thresholds

**What's NOT Working (The Gap)**:
- `NullCacheProvider` is the default in `client.py` line 125
- `TasksClient.get_async()` has `_cache` but never uses it
- `DataFrameCacheIntegration` requires explicit instantiation and wiring
- No entity-type-aware TTL configuration exposed
- Write-through invalidation not connected to SaveSession mutations

```
Current Flow:
  client.tasks.get_async("gid")
    --> HTTP call (always)
    --> Returns Task

Desired Flow:
  client.tasks.get_async("gid")
    --> Check cache (InMemoryCacheProvider by default)
    --> Cache hit? Return cached Task
    --> Cache miss? HTTP call --> Store in cache --> Return Task
```

### SDK Scale Profile

| Attribute | Value |
|-----------|-------|
| Entity Types | Business, Unit, Contact, Offer, Process, Address, Hours |
| Custom Fields | 127+ across entity hierarchy |
| Hierarchy Depth | 4 levels (Business > Unit > Offer > Process) |
| Typical Operation | Load Business + all descendants (50-500 tasks) |
| Current Latency | ~1 minute for 3,500-task project (uncached) |
| Target Latency | Sub-second for cached entity access |

### Target Architecture

```
AsanaClient(cache_provider=None)  <-- Uses InMemoryCacheProvider by default
    |
    v
TasksClient
    |
    +-- get_async(gid)
    |       |
    |       v
    |   CacheProvider.get_versioned(gid, EntryType.TASK)
    |       |
    |       +-- Cache hit? --> Return cached Task
    |       |
    |       +-- Cache miss? --> HTTP --> cache.set_versioned() --> Return
    |
    +-- update_async(gid, **data)
            |
            v
        HTTP.put() --> cache.invalidate(gid)  <-- Write-through invalidation

SaveSession.commit_async()
    |
    v
ActionExecutor
    |
    +-- On successful UPDATE/DELETE --> cache.invalidate(affected_gids)
```

### Key Constraints

- **Backward Compatibility**: No breaking changes to existing consumer code
- **Opt-Out Available**: Consumers must be able to disable caching via `NullCacheProvider()`
- **Python 3.10+**: Must support autom8 runtime (not 3.12+ only)
- **Async-First**: Cache operations must be async-compatible
- **Graceful Degradation**: Cache failures must never break API operations
- **Protocol Compliance**: Must implement existing `CacheProvider` protocol

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Change default from NullCacheProvider to InMemoryCacheProvider | Must |
| Wire TasksClient.get_async to check cache before HTTP | Must |
| Invalidate cache on SaveSession mutations | Must |
| Entity-type-specific TTL defaults (Business longer than Process) | Must |
| DataFrame builder uses cache by default | Must |
| Expose cache configuration in AsanaConfig | Must |
| Support opt-out via explicit NullCacheProvider | Must |
| Holder hydration uses cached subtask responses | Should |
| Warm cache for known entity hierarchies | Should |
| Metrics exposure for cache hit/miss rates | Should |
| Two-tier (Redis+S3) configuration guide for production | Could |

### Success Criteria

1. `AsanaClient()` with no arguments uses InMemoryCacheProvider by default
2. Repeated `client.tasks.get_async(same_gid)` returns cached result (no HTTP)
3. `SaveSession.commit_async()` invalidates cache for mutated task GIDs
4. Entity-type-specific TTLs are applied (e.g., Business: 1hr, Process: 5min)
5. DataFrame extraction uses cache by default (no explicit `cache_integration` required)
6. Existing tests pass without modification (backward compat)
7. Cache failures log warnings but do not raise exceptions (graceful degradation)
8. Performance improvement measurable in benchmark (target: 10x for repeated access)

### Performance Targets

| Metric | Uncached (Current) | Cached (Target) |
|--------|-------------------|-----------------|
| Single task fetch (cold) | ~200ms | ~200ms (same) |
| Single task fetch (warm) | ~200ms | <5ms |
| Business entity hydration (cold) | ~5s | ~5s (same) |
| Business entity hydration (warm) | ~5s | <500ms |
| 3,500-task DataFrame extraction | ~60s | <10s (after warm) |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Cache integration analysis - current wiring gaps, injection points |
| **2: Requirements** | Requirements Analyst | PRD-CACHE-INTEGRATION with acceptance criteria |
| **3: Architecture** | Architect | TDD-CACHE-INTEGRATION + ADRs for key decisions |
| **4: Implementation P1** | Principal Engineer | Default provider change, client-level cache integration |
| **5: Implementation P2** | Principal Engineer | SaveSession invalidation, entity-type TTLs |
| **6: Implementation P3** | Principal Engineer | DataFrame default caching, configuration exposure |
| **7: Validation** | QA/Adversary | Performance benchmarks, failure mode testing |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Codebase Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/client.py` | Where exactly is NullCacheProvider instantiated? How is cache_provider passed to sub-clients? |
| `src/autom8_asana/clients/base.py` | How is `_cache` stored? What's the cleanest injection point? |
| `src/autom8_asana/clients/tasks.py` | Which methods should check cache? What about list_async/subtasks_async? |
| `src/autom8_asana/cache/` | What's the complete EntryType enum? How does versioning work with Task.modified_at? |
| `src/autom8_asana/persistence/session.py` | Where does commit_async complete? How to trigger invalidation? |
| `src/autom8_asana/dataframes/` | How does DataFrameCacheIntegration connect? What's the default behavior? |

### Entity Hierarchy Audit

| Entity | Cache Considerations |
|--------|---------------------|
| Business | Long TTL (1hr?), root of hierarchy, invalidate cascades down |
| Unit | Medium TTL, composite with holders |
| Contact | Medium TTL, rarely changes |
| Offer | Short TTL (5min?), frequently updated |
| Process | Very short TTL, pipeline state changes often |
| Address/Hours | Long TTL, rarely changes |

### Integration Points

| System | Questions |
|--------|-----------|
| SaveSession | How to hook into post-commit for invalidation? ActionResult contains GIDs? |
| Holder hydration | Does prefetch_pending() already batch subtask calls? Can results be cached? |
| Detection system | Does detection use cached tasks? Should it? |
| PageIterator | Should paginated results be cached? Or just individual task fetches? |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Default Behavior Questions

1. **Which cache provider should be default?**: InMemoryCacheProvider seems right, but should Redis be auto-detected if REDIS_URL env var exists?
2. **Should list operations cache?**: `list_async()` returns PageIterator - should individual tasks from list be cached? Or only `get_async()`?
3. **Subtask caching**: When fetching subtasks via `subtasks_async()`, should each subtask be individually cached for later `get_async()` calls?

### TTL Strategy Questions

4. **Entity-type TTL source**: Should TTLs come from CacheSettings, or should each entity class define its own TTL constant?
5. **Override mechanism**: How should consumers customize TTLs? Per-entity-type? Per-project? Both?
6. **Staleness mode default**: STRICT (always validate version) or EVENTUAL (trust TTL)? What's the right default?

### Invalidation Questions

7. **Cascade invalidation**: When Business is updated, should all descendants (Unit, Contact, Offer) be invalidated?
8. **SaveSession batch handling**: With 10 mutations in one commit, how to batch invalidations efficiently?
9. **Existing cache entries**: On SDK upgrade, how to handle cache entries without version metadata?

### Configuration UX Questions

10. **AsanaConfig integration**: Should CacheSettings be nested in AsanaConfig or separate?
11. **Environment variables**: Should `ASANA_CACHE_ENABLED=false` disable default caching?
12. **Two-tier activation**: What environment variables trigger TieredCacheProvider with Redis+S3?

## Your First Task

Confirm understanding by:

1. Summarizing the cache integration goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which files/systems must be analyzed before PRD-CACHE-INTEGRATION
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Cache Integration Discovery

Work with the @requirements-analyst agent to analyze the cache infrastructure and identify integration gaps.

**Goals:**
1. Map current cache provider injection points (client.py, base.py, tasks.py)
2. Document which TasksClient methods should use cache
3. Analyze SaveSession for post-commit hook opportunities
4. Review entity-type TTL requirements based on update frequency
5. Identify DataFrame caching default behavior gap
6. Document current InMemoryCacheProvider capabilities
7. List all open questions requiring user input

**Files to Analyze:**
- `src/autom8_asana/client.py` - Provider injection
- `src/autom8_asana/clients/base.py` - Cache storage pattern
- `src/autom8_asana/clients/tasks.py` - Methods needing cache
- `src/autom8_asana/cache/` - Infrastructure capabilities
- `src/autom8_asana/persistence/session.py` - Invalidation hooks
- `src/autom8_asana/dataframes/cache_integration.py` - DataFrame caching

**Cache Infrastructure to Audit:**
- InMemoryCacheProvider (default candidate)
- TieredCacheProvider (production option)
- CacheEntry and EntryType enum
- CacheSettings and TTLSettings
- Versioning and staleness detection

**Deliverable:**
A discovery document with:
- Current state mapping (what exists vs. what's wired)
- Integration point recommendations
- Entity-type TTL recommendations
- Configuration UX proposal
- Resolved vs. unresolved open questions
- Risk assessment for backward compatibility

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Cache Integration Requirements Definition

Work with the @requirements-analyst agent to create PRD-CACHE-INTEGRATION.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define default cache provider behavior
2. Define client-level cache integration requirements
3. Define SaveSession invalidation requirements
4. Define entity-type TTL configuration
5. Define DataFrame default caching behavior
6. Define configuration exposure in AsanaConfig
7. Define acceptance criteria for each requirement

**Key Questions to Address:**
- What's the exact default behavior for new clients?
- Which methods cache vs. which bypass?
- How does invalidation cascade (if at all)?
- What's the opt-out mechanism?

**PRD Organization:**
- FR-DEFAULT-*: Default cache provider behavior
- FR-CLIENT-*: Client-level cache integration
- FR-INVALIDATE-*: Write-through invalidation
- FR-TTL-*: Entity-type TTL configuration
- FR-DF-*: DataFrame caching defaults
- FR-CONFIG-*: Configuration exposure
- NFR-*: Performance, backward compatibility requirements

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Cache Integration Architecture Design

Work with the @architect agent to create TDD-CACHE-INTEGRATION and foundational ADRs.

**Prerequisites:**
- PRD-CACHE-INTEGRATION approved

**Goals:**
1. Design default provider selection logic
2. Design client-level cache check pattern
3. Design SaveSession invalidation hook
4. Design entity-type TTL resolution
5. Design DataFrame default behavior
6. Design configuration structure
7. Design backward compatibility layer

**Required ADRs:**
- ADR-NNNN: Default Cache Provider Selection
- ADR-NNNN: Client Cache Check Pattern
- ADR-NNNN: SaveSession Invalidation Strategy
- ADR-NNNN: Entity-Type TTL Configuration
- ADR-NNNN: DataFrame Cache Default Behavior

**Module Structure to Consider:**

```
src/autom8_asana/
+-- client.py              # Update: default InMemoryCacheProvider
+-- config.py              # Update: Add CacheConfig
+-- cache/
|   +-- settings.py        # Update: Entity-type TTL defaults
+-- clients/
|   +-- base.py            # Update: Cache check helper methods
|   +-- tasks.py           # Update: get_async uses cache
+-- persistence/
|   +-- session.py         # Update: Post-commit invalidation
+-- dataframes/
    +-- cache_integration.py  # Update: Default-on behavior
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Default Provider & Client Integration

Work with the @principal-engineer agent to implement foundational components.

**Prerequisites:**
- PRD-CACHE-INTEGRATION approved
- TDD-CACHE-INTEGRATION approved
- ADRs documented

**Phase 1 Scope:**
1. Change default from NullCacheProvider to InMemoryCacheProvider
2. Add CacheConfig to AsanaConfig
3. Wire TasksClient.get_async to check cache
4. Implement cache check helper in BaseClient
5. Add opt-out documentation
6. Update existing tests for new default

**Hard Constraints:**
- No breaking changes to public API
- All existing tests must pass
- Cache failures must not raise exceptions
- Maintain async-first pattern

**Explicitly OUT of Phase 1:**
- SaveSession invalidation (Phase 2)
- Entity-type TTLs (Phase 2)
- DataFrame defaults (Phase 3)
- Production two-tier configuration (Phase 3)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Invalidation & TTLs

Work with the @principal-engineer agent to complete write-through invalidation.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Implement SaveSession post-commit invalidation hook
2. Implement entity-type TTL configuration
3. Implement TTL resolution in cache operations
4. Wire invalidation to ActionExecutor results
5. Add invalidation metrics
6. Update tests for invalidation behavior

**Integration Points:**
- SaveSession.commit_async() completion
- ActionResult with mutated task GIDs
- CacheSettings.entity_type_ttls configuration

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - DataFrame & Configuration

Work with the @principal-engineer agent to complete DataFrame integration.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope:**
1. Make DataFrame caching default-on
2. Expose cache configuration in AsanaConfig
3. Add environment variable support
4. Document two-tier (Redis+S3) configuration
5. Add cache health endpoint/check
6. Integration tests for full flow
7. Performance benchmark suite

**Configuration Structure:**

```python
AsanaConfig(
    cache=CacheConfig(
        enabled=True,  # Default
        provider="memory",  # or "redis", "tiered"
        ttl=TTLSettings(
            default_ttl=300,
            entity_type_ttls={
                "business": 3600,
                "process": 300,
            },
        ),
    ),
)
```

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Cache Integration Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation phases complete
- Cache integration deployed to test environment

**Goals:**

**Part 1: Functional Validation**
- Default provider is InMemoryCacheProvider (not Null)
- Repeated get_async returns cached result
- SaveSession mutations invalidate cache
- Entity-type TTLs are applied correctly
- DataFrame caching works by default

**Part 2: Failure Mode Testing**
- Cache provider raises exception -> Graceful degradation, operation succeeds
- Invalid cache entry (corrupt data) -> Treated as miss, fetched from API
- TTL expired -> Entry evicted, fresh fetch
- Versioned staleness -> Entry evicted, fresh fetch
- Memory pressure -> LRU eviction, no crash

**Part 3: Performance Validation**
- Single task cache hit < 5ms (vs ~200ms HTTP)
- Entity hierarchy warm access < 500ms
- Memory usage bounded (max_size eviction works)
- No regression in cold path performance

**Part 4: Backward Compatibility**
- Existing consumer code works without changes
- Explicit NullCacheProvider disables caching
- Custom CacheProvider implementations still work
- All existing tests pass

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Cache Infrastructure:**
- [ ] `src/autom8_asana/cache/__init__.py` - Public API
- [ ] `src/autom8_asana/cache/tiered.py` - Two-tier implementation
- [ ] `src/autom8_asana/cache/settings.py` - TTL configuration
- [ ] `src/autom8_asana/_defaults/cache.py` - InMemory and Null providers

**Client Layer:**
- [ ] `src/autom8_asana/client.py` - Main client, default provider
- [ ] `src/autom8_asana/clients/base.py` - BaseClient, _cache storage
- [ ] `src/autom8_asana/clients/tasks.py` - Methods to wire up
- [ ] `src/autom8_asana/protocols/cache.py` - CacheProvider protocol

**Persistence Layer:**
- [ ] `src/autom8_asana/persistence/session.py` - SaveSession
- [ ] `src/autom8_asana/persistence/action_executor.py` - ActionResult

**Entity Layer:**
- [ ] `src/autom8_asana/models/business/` - Entity hierarchy
- [ ] `src/autom8_asana/dataframes/cache_integration.py` - DataFrame caching

**Configuration:**
- [ ] `src/autom8_asana/config.py` - AsanaConfig structure
- [ ] Current environment variable patterns
