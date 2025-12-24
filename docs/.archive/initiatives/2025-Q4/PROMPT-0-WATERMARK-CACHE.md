# Orchestrator Initialization: Watermark Cache Performance Initiative

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

## The Mission: Reduce Project-Level DataFrame Latency from 52s to <10s

Project-level dataframe operations take **52-59 seconds** for a typical project (3,500+ tasks). Users run this operation frequently as it is a primitive for business operational logic. Back-to-back runs show no cache benefit despite having cache infrastructure in place.

This initiative implements **parallel section fetch** to reduce cold-start latency from O(pages) to O(1), while leveraging the existing per-task cache infrastructure that is already correctly designed.

### The Core Insight

> **"The cache is already right. The fetch is wrong."**

Extensive exploration with the Architect and Principal Engineer revealed that:

1. **Cache infrastructure is correct** - Per-task granularity with project context (`{task_gid}:{project_gid}`) enables surgical O(1) invalidation
2. **Multi-level caching is over-engineering** - Section-level and project-level caches provide negative utility under write-frequent patterns
3. **The missing piece is fetch parallelization** - Serial paginated API calls cause the 52-second latency, not cache misses

### Why This Initiative?

- **Immediate User Impact**: 80% latency reduction (52s to <10s) for the most common SDK operation
- **Zero Configuration**: Transparent performance improvement with no consumer code changes
- **Infrastructure ROI**: Activate dormant parallel fetch capability that aligns with existing cache design
- **Correct Architecture First**: Avoid over-engineering traps (multi-level caching, Search API) that the exploration phase identified

### Current State

**What Works (Already Correct)**:
- `TasksClient.get_async()` has cache integration points (unused but ready)
- Per-task cache with project context key structure is optimal
- `TieredCacheProvider`: Redis (hot) + S3 (cold) infrastructure exists
- `CacheEntry` with versioning via `modified_at` timestamp
- SaveSession can trigger cache invalidation (wiring needed)

**What Does NOT Work (The Gap)**:
- `list_async(project=...)` fetches tasks **serially** via paginated API calls
- `to_dataframe_async()` requires explicit `cache_integration` parameter (not auto-wired)
- Bulk fetch does not populate individual task cache entries
- No parallel section fetch to reduce cold-start latency

```
Current Flow (52-59 seconds for 3,500 tasks):
  project.to_dataframe_async()
    --> list_async(project_gid)
    --> Page 1 (100 tasks, ~500ms)
    --> Page 2 (100 tasks, ~500ms)
    --> ... 35 pages sequentially
    --> Returns DataFrame

Desired Flow (<10 seconds):
  project.to_dataframe_async()
    --> Get sections (1 call)
    --> Parallel fetch all sections (8 sections x ~1s = ~1s wall time)
    --> Batch cache set for 3,500 tasks
    --> Returns DataFrame
```

### Architecture Decision Summary

Through exploration, the following design decisions were made:

| Decision | Rationale |
|----------|-----------|
| **Per-task cache granularity** | Multi-homed tasks need project context; enables O(1) invalidation |
| **Single logical cache level** | Multi-level hierarchy rejected as over-engineering with negative utility |
| **Eventual consistency (5 min TTL)** | Self-writes immediate via SaveSession; external changes via TTL expiration |
| **Parallel section fetch** | The 80% solution that transforms 52s to <8s with minimal complexity |
| **Batch cache operations** | `get_batch()` / `set_batch()` for 3,500 tasks must be first-class |

### What NOT to Build (Explicitly Rejected)

| Feature | Reason |
|---------|--------|
| Section-level cache | Invalidation cost exceeds benefit; no `modified_at` on sections |
| Project-level cache | Cache thrashing under write patterns (10 writes/hour = never warm) |
| Multi-level hierarchy | Over-engineering; "ghost reference problem" with moved tasks |
| Search API staleness detection | Premium-only; cannot detect removals (deleted/moved tasks) |
| Manual cache warming API | Parallel fetch warms automatically; no explicit API needed |
| Background refresh | TTL expiration is sufficient; avoid complexity |

### SDK Performance Profile

| Attribute | Value |
|-----------|-------|
| Typical Project Size | 3,500+ tasks |
| Current Latency (cold) | 52-59 seconds |
| Current Latency (warm) | ~1 second (if explicitly wired) |
| Target Latency (cold) | <10 seconds |
| Target Latency (warm) | <1 second |
| Cache Hit Target | <5ms per task |
| Section Count (typical) | 8-12 sections per project |
| Write Frequency | ~10 writes/hour per project |

### Target Architecture

```
User: project.to_dataframe_async()
           |
           v
+------------------------------------------+
|   PARALLEL SECTION FETCH (NEW)           |  <-- The only missing piece
|   1. Get sections: GET /projects/{gid}/  |
|      sections (1 call)                   |
|   2. Parallel fetch: asyncio.gather()    |
|      GET /sections/{gid}/tasks x N       |
|   3. Wall time: O(1) vs O(pages)         |
+------------------------------------------+
           |
           v
+------------------------------------------+
|   WATERMARK CACHE (EXISTING - WIRE UP)   |  <-- Already built correctly
|   Key: {task_gid}:{project_gid}          |
|   Version: task.modified_at              |
|   Invalidation: SaveSession post-commit  |
|   Batch: get_batch() / set_batch()       |
+------------------------------------------+
           |
           v
    Redis (hot) + S3 (cold)                   <-- Already built
```

### Key Constraints

- **Backward Compatibility**: No breaking changes to existing consumer code
- **Zero Configuration**: Default behavior must provide performance improvement
- **Opt-Out Available**: Consumers can disable with explicit `NullCacheProvider()`
- **Graceful Degradation**: Cache/parallel failures must fall back to current behavior
- **Async-First**: All new code must be async-compatible
- **Asana API Limits**: Respect rate limits; parallel fetch must not exceed burst capacity

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Implement parallel section fetch in `ProjectDataFrameBuilder` | Must |
| Wire batch cache operations (`get_batch`/`set_batch`) into DataFrame build | Must |
| Auto-populate task cache on bulk fetch (no explicit wiring needed) | Must |
| Connect SaveSession post-commit to cache invalidation | Must |
| Provide configuration for parallelism limits | Should |
| Expose cache metrics (hit/miss rates, latency) | Should |
| Document "Watermark Cache" pattern for SDK consumers | Should |
| Support partial cache scenarios (some tasks cached, some not) | Must |
| Fall back gracefully if parallel fetch fails | Must |

### Success Criteria

1. **Cold Start Performance**: 3,500-task project DataFrame in <10 seconds (from 52-59s)
2. **Warm Cache Performance**: Repeated DataFrame extraction in <1 second
3. **Partial Cache Performance**: 10% cache miss scenario completes in <2 seconds
4. **Zero Configuration**: `project.to_dataframe_async()` with no parameters uses parallel fetch
5. **Backward Compatibility**: Existing consumer code works without modification
6. **Graceful Degradation**: Parallel fetch failure falls back to serial (current behavior)
7. **Cache Invalidation**: SaveSession mutations invalidate affected task cache entries
8. **No Regressions**: All existing tests pass

### Performance Targets

| Scenario | Current | Target |
|----------|---------|--------|
| Cold start (3,500 tasks) | 52-59s | <10s |
| Warm cache | ~1s (explicit wiring) | <1s (automatic) |
| Partial cache (10% miss) | N/A | <2s |
| Single task cache hit | ~200ms (HTTP) | <5ms |
| Cache invalidation | Not wired | O(1) per task |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Parallel fetch integration analysis - current TasksClient patterns, section API, batch cache ops |
| **2: Requirements** | Requirements Analyst | PRD-WATERMARK-CACHE with acceptance criteria |
| **3: Architecture** | Architect | TDD-WATERMARK-CACHE + ADRs for parallel fetch, batch cache, invalidation |
| **4: Implementation P1** | Principal Engineer | Parallel section fetch in ProjectDataFrameBuilder |
| **5: Implementation P2** | Principal Engineer | Batch cache integration, auto-population |
| **6: Implementation P3** | Principal Engineer | SaveSession invalidation, configuration, metrics |
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
| `src/autom8_asana/dataframes/builders/project.py` | How does `ProjectDataFrameBuilder` currently fetch tasks? Where to inject parallel fetch? |
| `src/autom8_asana/clients/sections.py` | Does `list_async(project=...)` return sections? What's the response structure? |
| `src/autom8_asana/clients/tasks.py` | Does `list_async(section=...)` support section-scoped fetch? What opt_fields are needed? |
| `src/autom8_asana/cache/batch.py` | What are the `get_batch()` / `set_batch()` signatures? How do they handle misses? |
| `src/autom8_asana/persistence/session.py` | Where does `commit_async()` complete? How to hook post-commit invalidation? |
| `src/autom8_asana/cache/settings.py` | What TTL settings exist? How to configure per-entity-type TTLs? |

### API Behavior Audit

| API Endpoint | Questions to Answer |
|--------------|---------------------|
| `GET /projects/{gid}/sections` | What fields are returned? Is ordering preserved? |
| `GET /sections/{gid}/tasks` | Does this support pagination? What's the page size? |
| Rate limiting | What's the burst capacity? How many parallel requests are safe? |
| `modified_since` filter | Is it reliable for section-scoped queries? (Known bug history) |

### Existing Cache Infrastructure

| Component | Questions |
|-----------|-----------|
| `InMemoryCacheProvider` | What's the current default? Is batch operation supported? |
| `TieredCacheProvider` | How is Redis/S3 promotion handled? Is async batch supported? |
| `CacheEntry` versioning | How does `modified_at` comparison work? What about missing versions? |
| Cache key format | Is `{task_gid}:{project_gid}` already the key format? |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Parallel Fetch Questions

1. **Concurrency limit**: How many parallel section fetches are safe? (Rate limit consideration)
2. **Error handling**: If one section fetch fails, should we fail all or fall back to serial?
3. **Empty sections**: Should empty sections be skipped or fetched anyway?
4. **Section ordering**: Does section fetch order need to match project section order?

### Cache Integration Questions

5. **Batch population**: Should parallel fetch populate individual task cache entries?
6. **Partial cache**: How to handle scenario where some tasks are cached and some are not?
7. **Cache key confirmation**: Is `{task_gid}:{project_gid}` the correct key format already?
8. **TTL strategy**: Should DataFrame-fetched tasks have different TTL than individual fetches?

### Invalidation Questions

9. **Invalidation scope**: When task moves between sections, what cache entries are invalidated?
10. **Batch invalidation**: How to efficiently invalidate 100 tasks in a single SaveSession commit?
11. **External changes**: How do we handle tasks modified outside our SDK? (TTL-based expiration)

### Configuration Questions

12. **Default parallelism**: What's the default concurrency limit for parallel fetch?
13. **Opt-out mechanism**: How does consumer disable parallel fetch if needed?
14. **Metrics exposure**: What cache/performance metrics should be exposed?

## Exploration Context Summary

This initiative benefits from extensive prior exploration that ruled out several approaches:

### Approaches Explored and Rejected

1. **Section-level caching**: Sections have no `modified_at` field, making staleness detection impossible
2. **Project-level caching**: Cache thrashing under typical write patterns (10 writes/hour)
3. **Search API for staleness**: Premium-only, 100-item limit, cannot detect removals
4. **Multi-level cache hierarchy**: "Ghost reference problem" when tasks move between projects
5. **Watermark-based incremental refresh**: Search API limitations make this unreliable

### Key Insight That Emerged

The existing cache design is optimal. The performance problem is not cache architecture - it's **fetch strategy**. Serial paginated API calls cause the latency. Parallel section fetch solves 80% of the problem with minimal complexity.

### Preserved Decisions

- Per-task cache granularity with project context key
- Eventual consistency (5 min TTL) for external changes
- Immediate consistency for self-writes via SaveSession invalidation
- Single logical cache level (no hierarchy)

## Your First Task

Confirm understanding by:

1. Summarizing the Watermark Cache goal in 2-3 sentences (focus on **parallel fetch**, not cache redesign)
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which files/systems must be analyzed before PRD-WATERMARK-CACHE
5. Listing which open questions you need answered before Session 2
6. Acknowledging the "what NOT to build" list from exploration

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Watermark Cache Discovery

Work with the @requirements-analyst agent to analyze the parallel fetch integration points and cache infrastructure.

**Goals:**
1. Map current ProjectDataFrameBuilder task fetching flow
2. Document SectionsClient API for section listing
3. Verify TasksClient supports section-scoped task listing
4. Analyze batch cache operation signatures and behavior
5. Identify SaveSession post-commit hook insertion point
6. Document current cache key format and TTL settings
7. Determine safe concurrency limits for parallel section fetch

**Files to Analyze:**
- `src/autom8_asana/dataframes/builders/project.py` - Current fetch flow
- `src/autom8_asana/clients/sections.py` - Section listing API
- `src/autom8_asana/clients/tasks.py` - Section-scoped task listing
- `src/autom8_asana/cache/batch.py` - Batch cache operations
- `src/autom8_asana/persistence/session.py` - Post-commit hook point
- `src/autom8_asana/cache/settings.py` - TTL configuration

**Cache Infrastructure to Audit:**
- InMemoryCacheProvider batch support
- TieredCacheProvider async batch operations
- CacheEntry versioning mechanism
- Cache key format convention

**Deliverable:**
A discovery document with:
- Current fetch flow diagram (serial pagination)
- Proposed fetch flow diagram (parallel sections)
- Cache integration points identified
- Concurrency limit recommendation
- Risk assessment for parallel fetch failure modes
- Resolved vs. unresolved open questions

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Watermark Cache Requirements Definition

Work with the @requirements-analyst agent to create PRD-WATERMARK-CACHE.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define parallel fetch requirements (FR-FETCH-*)
2. Define cache integration requirements (FR-CACHE-*)
3. Define invalidation requirements (FR-INVALIDATE-*)
4. Define configuration requirements (FR-CONFIG-*)
5. Define fallback/degradation requirements (FR-FALLBACK-*)
6. Define acceptance criteria for each requirement
7. Document explicit scope boundaries (what NOT to build)

**Key Questions to Address:**
- What is the exact parallel fetch behavior?
- How does batch cache population work?
- What triggers cache invalidation?
- How does fallback to serial fetch work?

**PRD Organization:**
- FR-FETCH-*: Parallel section fetch requirements
- FR-CACHE-*: Batch cache population and lookup
- FR-INVALIDATE-*: SaveSession post-commit invalidation
- FR-CONFIG-*: Configuration and opt-out mechanisms
- FR-FALLBACK-*: Graceful degradation requirements
- NFR-*: Performance targets, backward compatibility

**Explicit OUT of Scope (from exploration):**
- Section-level caching
- Project-level caching
- Multi-level cache hierarchy
- Search API integration
- Background refresh mechanisms

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Watermark Cache Architecture Design

Work with the @architect agent to create TDD-WATERMARK-CACHE and foundational ADRs.

**Prerequisites:**
- PRD-WATERMARK-CACHE approved

**Goals:**
1. Design parallel section fetch implementation in ProjectDataFrameBuilder
2. Design batch cache population flow
3. Design SaveSession post-commit invalidation hook
4. Design configuration structure for parallelism limits
5. Design fallback mechanism for fetch failures
6. Define module structure for new components
7. Document rejected alternatives (from exploration)

**Required ADRs:**
- ADR-NNNN: Parallel Section Fetch Strategy
- ADR-NNNN: Batch Cache Population Pattern
- ADR-NNNN: Post-Commit Invalidation Hook Design
- ADR-NNNN: Rejection of Multi-Level Cache Hierarchy

**Architecture Constraints (from exploration):**
- Single logical cache level (per-task with project context)
- Eventual consistency via TTL (5 min default)
- Immediate consistency for self-writes via invalidation
- No section-level or project-level cache aggregates

**Component Changes:**

```
src/autom8_asana/
+-- dataframes/
|   +-- builders/
|       +-- project.py          # UPDATE: Add parallel section fetch
+-- cache/
|   +-- batch.py                # VERIFY: Batch operations exist
+-- persistence/
|   +-- session.py              # UPDATE: Add post-commit invalidation hook
+-- config.py                   # UPDATE: Add parallelism configuration
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Parallel Section Fetch

Work with the @principal-engineer agent to implement parallel section fetch.

**Prerequisites:**
- PRD-WATERMARK-CACHE approved
- TDD-WATERMARK-CACHE approved
- ADRs documented

**Phase 1 Scope:**
1. Implement parallel section fetch in ProjectDataFrameBuilder
2. Add section listing via SectionsClient
3. Implement asyncio.gather for parallel task fetches
4. Add concurrency limiting (semaphore)
5. Implement fallback to serial fetch on failure
6. Add unit tests for parallel fetch logic

**Hard Constraints:**
- No breaking changes to ProjectDataFrameBuilder public API
- Parallel fetch must respect rate limits
- Fallback must be automatic and transparent
- All existing DataFrame tests must pass

**Explicitly OUT of Phase 1:**
- Batch cache population (Phase 2)
- SaveSession invalidation (Phase 3)
- Configuration exposure (Phase 3)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Batch Cache Integration

Work with the @principal-engineer agent to implement batch cache operations.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Wire batch cache population into parallel fetch results
2. Implement get_batch for cache lookup before fetch
3. Implement set_batch for cache population after fetch
4. Handle partial cache scenarios (some hits, some misses)
5. Add cache hit/miss metrics
6. Update tests for cache integration

**Integration Points:**
- ProjectDataFrameBuilder.build() checks cache before fetch
- Parallel fetch results populate cache via set_batch
- Cache key format: {task_gid}:{project_gid}

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Invalidation & Configuration

Work with the @principal-engineer agent to complete invalidation and configuration.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope:**
1. Implement SaveSession post-commit invalidation hook
2. Wire ActionExecutor results to cache invalidation
3. Add parallelism configuration to AsanaConfig
4. Add cache configuration (TTL, max entries)
5. Expose cache metrics via logging/callbacks
6. Document Watermark Cache pattern
7. Integration tests for full flow

**Configuration Structure:**

```python
AsanaConfig(
    cache=CacheConfig(
        enabled=True,  # Default
        ttl_seconds=300,  # 5 min default
    ),
    dataframe=DataFrameConfig(
        parallel_fetch=True,  # Default
        max_concurrent_sections=8,  # Rate limit safe
    ),
)
```

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Watermark Cache Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation phases complete

**Goals:**

**Part 1: Performance Validation**
- Cold start (3,500 tasks): <10 seconds (from 52-59s)
- Warm cache: <1 second
- Partial cache (10% miss): <2 seconds
- Single task cache hit: <5ms

**Part 2: Functional Validation**
- Parallel fetch returns same data as serial fetch
- Cache population occurs automatically
- SaveSession mutations invalidate cache
- Configuration options work as documented

**Part 3: Failure Mode Testing**
- Section fetch fails -> Falls back to serial (current behavior)
- Cache provider fails -> Continues without caching
- Rate limit hit -> Backs off and retries
- Partial section failure -> Completes with available sections

**Part 4: Backward Compatibility**
- Existing consumer code works without changes
- All existing tests pass
- No new required parameters
- Opt-out via configuration works

**Part 5: Edge Cases**
- Empty project (0 tasks)
- Single section project
- Project with 100+ sections
- Task moved between sections during fetch

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**DataFrame Infrastructure:**

- [ ] `src/autom8_asana/dataframes/builders/project.py` - Current fetch implementation
- [ ] `src/autom8_asana/dataframes/builders/base.py` - Base builder patterns
- [ ] `src/autom8_asana/dataframes/cache_integration.py` - Existing cache integration

**Client Layer:**

- [ ] `src/autom8_asana/clients/sections.py` - Section listing API
- [ ] `src/autom8_asana/clients/tasks.py` - Task listing with section filter
- [ ] `src/autom8_asana/client.py` - Main client configuration

**Cache Infrastructure:**

- [ ] `src/autom8_asana/cache/batch.py` - Batch operations
- [ ] `src/autom8_asana/cache/backends/memory.py` - InMemoryProvider implementation
- [ ] `src/autom8_asana/cache/settings.py` - TTL configuration
- [ ] `src/autom8_asana/cache/entry.py` - CacheEntry with versioning

**Persistence Layer:**

- [ ] `src/autom8_asana/persistence/session.py` - SaveSession, post-commit hooks
- [ ] `src/autom8_asana/persistence/action_executor.py` - Action execution results

**Configuration:**

- [ ] `src/autom8_asana/config.py` - AsanaConfig structure
- [ ] Environment variable patterns for cache configuration
