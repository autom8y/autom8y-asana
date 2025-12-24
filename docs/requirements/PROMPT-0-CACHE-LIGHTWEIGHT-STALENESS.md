# Orchestrator Initialization: Cache Lightweight Staleness Check Initiative

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

- **`prompting`** - Agent invocation patterns, workflow examples
  - Activates when: Invoking agents, structuring prompts

- **`autom8-asana`** - SDK patterns, cache infrastructure, batch operations
  - Activates when: Working with cache layer, entity operations, Asana API integration

**How Skills Work**: Skills load automatically based on your current task. You do not need to read or load them manually.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

## The Mission: Implement Lightweight Staleness Checks with Progressive TTL Extension

The current cache system performs FULL API fetches when TTL expires, even when cached data is unchanged. This initiative implements lightweight `modified_at` checks that extend TTL progressively when data is stable, dramatically reducing unnecessary API bandwidth for unchanged entities.

### Why This Initiative?

- **API Quota Conservation**: Lightweight checks use minimal bandwidth compared to full fetches
- **Reduced Latency**: Batch `modified_at` checks are faster than individual full fetches
- **Progressive Efficiency**: Stable entities extend TTL exponentially (5min -> 10min -> ... -> 24h max)
- **Foundation for Scale**: Enables efficient long-running sessions with stable entity sets

### Current State

**Cache Infrastructure (Complete)**:
- Two-tier cache architecture (Redis + S3) per ADR-0026
- TTL-based expiration fully functional
- `CacheEntry.is_stale(current_version)` machinery exists at `cache/entry.py:128`
- `check_entry_staleness()` exists at `cache/staleness.py:19`
- `Freshness.STRICT` mode defined at `cache/freshness.py:12`
- GID enumeration caching complete per ADR-0131

**What's Missing**:

```
# Current flow (inefficient):
TTL Expired? -> YES -> FULL API CALL (even if unchanged)

# Target flow (optimized):
TTL Expired? -> YES -> Batch lightweight check (opt_fields=modified_at)
                          |
                          +-> Unchanged? -> Extend TTL progressively, return cached
                          +-> Changed? -> Full API call, reset TTL
```

### Cache Entry Profile

| Attribute | Value |
|-----------|-------|
| Base TTL | 300 seconds (5 minutes) |
| Progressive Extension | Double on unchanged (5 -> 10 -> 20 -> 40 -> ...) |
| Max TTL Ceiling | 86,400 seconds (24 hours) |
| Batch Window | 50ms coalescing window |
| Entities Supported | All with `modified_at` (Tasks, Projects, etc.) |
| Scope Limitation | Task-level only (nested attributes follow own TTL) |

### Target Architecture

```
Cache Lookup (TTL expired)
    |
    v
+---------------------------+
| Batch Request Coalescer   |  50ms window
| (collect expired entries) |
+---------------------------+
    |
    v
+---------------------------+
| Lightweight API Check     |  GET /tasks?opt_fields=modified_at
| (batch modified_at only)  |
+---------------------------+
    |
    +-- Unchanged entries --> Extend TTL progressively, return cached
    |
    +-- Changed entries --> Queue for full fetch, reset TTL
    |
    v
+---------------------------+
| Full Fetch (if changed)   |  Standard API call
+---------------------------+
```

### Key Constraints

- **Batch-First**: Coalesce requests within 50ms window to minimize API calls
- **Progressive Extension**: TTL doubles on each unchanged check (5min max -> 24h ceiling)
- **Task-Level Scope**: Only task `modified_at` checked; nested attributes (subtasks, dependencies) follow own TTL
- **Backward Compatible**: Must work with existing cache infrastructure (Redis, CacheProvider protocol)
- **Graceful Degradation**: If lightweight check fails, fall back to full fetch (no worse than current)
- **Phase 3 Separation**: GID enumeration optimization (ADR-0131) is complete and separate

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Batch coalescing of expired cache lookups within 50ms window | Must |
| Lightweight API check using `opt_fields=modified_at` only | Must |
| Progressive TTL extension (double on unchanged, up to 24h) | Must |
| Support for all entities with `modified_at` field | Must |
| Graceful degradation to full fetch on check failure | Must |
| Structured logging for staleness check metrics | Must |
| Integration with existing `check_entry_staleness()` machinery | Should |
| Activation of `Freshness.STRICT` mode for this flow | Should |
| Per-entity type TTL ceiling configuration | Should |

### Success Criteria

1. **90%+ API call reduction** for stable entities after initial fetch
2. **Warm fetch latency** for unchanged entities < 100ms (lightweight check only)
3. **Zero regressions** in correctness (changed entities always refetched)
4. **Batch efficiency**: Average batch size > 10 entities per API call
5. **Progressive TTL working**: Entities unchanged for 2+ hours have TTL >= 1 hour
6. **Graceful degradation**: Failed lightweight checks do not break cache operations
7. **Observable**: Metrics available for cache hit rate, extension count, batch size
8. **Test coverage**: 90%+ for new staleness check paths

### Performance Targets

| Metric | Current | Target |
|--------|---------|--------|
| API calls per warm fetch (stable entities) | 1 per entity | 1 per batch (10+ entities) |
| Latency for unchanged entity | ~200ms (full fetch) | <100ms (lightweight check) |
| TTL for stable entity (after 2h) | 5 minutes (constant) | 60+ minutes (progressive) |
| Bandwidth per staleness check | Full payload (~5KB) | modified_at only (~100 bytes) |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Staleness infrastructure analysis, batch API capability audit |
| **2: Requirements** | Requirements Analyst | PRD-CACHE-LIGHTWEIGHT-STALENESS with acceptance criteria |
| **3: Architecture** | Architect | TDD-CACHE-LIGHTWEIGHT-STALENESS + ADRs for batching strategy |
| **4: Implementation** | Principal Engineer | Core lightweight check + progressive TTL + batch coalescer |
| **5: Validation** | QA/Adversary | Validation report, performance benchmarks, failure mode testing |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Existing Staleness Infrastructure

| File/Area | Questions to Answer |
|-----------|---------------------|
| `cache/staleness.py` | How is `check_entry_staleness()` currently used? What's the gap? |
| `cache/entry.py` | How does `is_stale()` compare versions? What triggers it? |
| `cache/freshness.py` | When is `Freshness.STRICT` vs `EVENTUAL` used today? |
| `cache/versioning.py` | How are versions compared? What format is `modified_at`? |

### Asana API Batch Capability

| Resource/System | Questions to Answer |
|-----------------|---------------------|
| Asana Batch API | What's the format for batch `modified_at` checks? Max batch size? |
| `opt_fields` parameter | Can `modified_at` be the only field returned? |
| Rate limits | Does lightweight check count differently toward quota? |
| Legacy codebase | Where was batch `modified_at` check used before? Pattern to follow? |

### Cache Provider Integration

| Area | Questions |
|------|-----------|
| `CacheProvider` protocol | What methods support batch operations? |
| `TaskCacheCoordinator` | How does it handle cache misses today? Extension point? |
| Progressive TTL storage | Where is TTL stored? Can it be updated without replacing entry? |
| Batch request coalescing | Existing patterns for request batching? 50ms window implementation? |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Technical Questions

1. **Batch API format**: What is the exact Asana API call for batch `modified_at` checks? (User confirms it exists in legacy)
2. **Coalescing implementation**: Should we use asyncio gather, queue, or dedicated coalescer class?
3. **TTL storage**: Can we update TTL in-place on CacheEntry or must we replace the entry?
4. **Entry type filtering**: Which `EntryType` values have `modified_at`? (Tasks yes, but Sections no per `entry.py`)

### Scope Questions

5. **Project coverage**: Should Projects also use lightweight staleness checks? (Have `modified_at`)
6. **First-session activation**: Enable immediately on new sessions or require opt-in?
7. **Ceiling configuration**: Should 24h max be configurable per entity type?

### Integration Questions

8. **Freshness mode trigger**: Does this activate `Freshness.STRICT` mode or create new mode?
9. **Phase 3 interaction**: How does this interact with GID enumeration caching (ADR-0131)?
10. **Observability**: What metrics/logs are needed for debugging staleness check issues?

## Your First Task

Confirm understanding by:

1. Summarizing the lightweight staleness check goal in 2-3 sentences
2. Listing the 5 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which files/systems must be analyzed before PRD-CACHE-LIGHTWEIGHT-STALENESS
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Staleness Infrastructure Discovery

Work with the @requirements-analyst agent to analyze the existing staleness detection machinery and audit Asana batch API capabilities.

**Goals:**
1. Map current usage of `check_entry_staleness()` and `CacheEntry.is_stale()`
2. Identify integration points in `TaskCacheCoordinator` and cache flow
3. Document Asana API batch `modified_at` check format from legacy codebase
4. Understand `opt_fields` parameter behavior for minimal responses
5. Analyze progressive TTL storage options (in-place vs replacement)
6. Document which `EntryType` values support `modified_at`
7. Identify existing batch coalescing patterns in codebase

**Files to Analyze:**
- `src/autom8_asana/cache/staleness.py` - Existing staleness detection
- `src/autom8_asana/cache/entry.py` - CacheEntry versioning
- `src/autom8_asana/cache/freshness.py` - Freshness modes
- `src/autom8_asana/cache/versioning.py` - Version comparison logic

**APIs/Systems to Audit:**
- Asana batch API documentation (legacy usage)
- `opt_fields` parameter specification
- Rate limit implications for lightweight checks

**Deliverable:**
A discovery document with:
- Current staleness detection usage map
- Gap analysis: what exists vs what's needed
- Asana batch API specification for `modified_at` checks
- Progressive TTL implementation options
- Entity type support matrix (which have `modified_at`)
- Recommended coalescing pattern

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Lightweight Staleness Check Requirements Definition

Work with the @requirements-analyst agent to create PRD-CACHE-LIGHTWEIGHT-STALENESS.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define batch coalescing requirements (50ms window, max batch size)
2. Define progressive TTL extension algorithm (doubling, ceiling)
3. Define lightweight API check format and response handling
4. Define graceful degradation behavior
5. Define entity type scope (what has `modified_at`)
6. Define observability requirements (metrics, logging)
7. Define acceptance criteria for each requirement

**Key Questions to Address:**
- How does batch coalescing interact with concurrent requests?
- What triggers progressive TTL reset (any change, or only structural changes)?
- How do we measure success (API call reduction, latency improvement)?
- What failure modes must be handled?

**PRD Organization:**
- FR-BATCH-*: Batch coalescing requirements
- FR-STALE-*: Staleness check logic requirements
- FR-TTL-*: Progressive TTL extension requirements
- FR-DEGRADE-*: Graceful degradation requirements
- FR-OBS-*: Observability requirements
- NFR-*: Performance, latency, reliability requirements

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Lightweight Staleness Check Architecture Design

Work with the @architect agent to create TDD-CACHE-LIGHTWEIGHT-STALENESS and foundational ADRs.

**Prerequisites:**
- PRD-CACHE-LIGHTWEIGHT-STALENESS approved

**Goals:**
1. Design batch request coalescer component
2. Design lightweight staleness check flow
3. Design progressive TTL extension mechanism
4. Design integration with existing cache infrastructure
5. Design graceful degradation paths
6. Design observability instrumentation

**Required ADRs:**
- ADR-0132: Batch Request Coalescing Strategy
- ADR-0133: Progressive TTL Extension Algorithm
- ADR-0134: Lightweight Staleness Check API Design
- ADR-0135: Freshness Mode Integration

**Architecture to Consider:**

```
src/autom8_asana/cache/
    staleness.py          # Extend with lightweight check
    entry.py              # Progressive TTL support
    freshness.py          # New mode or extend STRICT?
    coalescer.py          # NEW: Batch request coalescer
    lightweight_check.py  # NEW: Lightweight API check
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation

```markdown
Begin Session 4: Lightweight Staleness Check Implementation

Work with the @principal-engineer agent to implement the core components.

**Prerequisites:**
- PRD-CACHE-LIGHTWEIGHT-STALENESS approved
- TDD-CACHE-LIGHTWEIGHT-STALENESS approved
- ADRs documented

**Implementation Scope:**
1. Batch request coalescer with 50ms window
2. Lightweight `modified_at` API check
3. Progressive TTL extension logic (doubling up to 24h)
4. Integration with `check_entry_staleness()` flow
5. Graceful degradation on check failure
6. Structured logging for metrics

**Hard Constraints:**
- Must use existing `CacheProvider` protocol
- Must integrate with existing `TaskCacheCoordinator`
- Must not break backward compatibility
- Must follow Phase 2 patterns (structured logging, graceful degradation)

**Explicitly OUT of Scope:**
- Nested attribute staleness (subtasks, dependencies follow own TTL)
- GID enumeration changes (Phase 3 complete, separate)
- S3 tier staleness checks (Redis-only for this phase)
- Configuration UI (code/env config only)

Create the plan first. I'll review before you execute.
```

## Session 5: Validation

```markdown
Begin Session 5: Lightweight Staleness Check Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- Implementation complete

**Goals:**

**Part 1: Functional Validation**
- Batch coalescing works within 50ms window
- Lightweight check correctly identifies changed vs unchanged entities
- Progressive TTL doubles correctly up to 24h ceiling
- Graceful degradation on API failure

**Part 2: Failure Mode Testing**
- API timeout during lightweight check -> Falls back to full fetch
- Malformed `modified_at` response -> Treats as changed
- Batch size exceeds API limit -> Splits into sub-batches
- Concurrent requests -> Properly coalesced
- Redis unavailable -> Graceful degradation to API

**Part 3: Performance Validation**
- API calls reduced by 90%+ for stable entities
- Lightweight check latency <100ms
- Batch efficiency >10 entities per call average
- No regression in changed entity detection

**Part 4: Observability Validation**
- Metrics for cache hit/miss/extension rates
- Logging for staleness check outcomes
- Debug capability for staleness flow issues

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Existing Cache Infrastructure:**

- [ ] `cache/staleness.py` - Current staleness detection usage
- [ ] `cache/entry.py` - CacheEntry versioning and TTL
- [ ] `cache/freshness.py` - Freshness modes
- [ ] Understanding of when these are called today

**Asana API Context:**

- [ ] Legacy codebase batch `modified_at` check pattern
- [ ] `opt_fields` parameter documentation
- [ ] Batch API rate limit implications
- [ ] Maximum batch size for Asana API

**Related Documentation:**

- [ ] ADR-0026: Two-tier cache architecture
- [ ] ADR-0131: GID enumeration cache strategy
- [ ] PRD-CACHE-OPTIMIZATION-P2/P3 learnings

**User Decisions:**

- [ ] Progressive TTL strategy: Double on unchanged (confirmed)
- [ ] Max TTL ceiling: 24 hours (confirmed)
- [ ] Batch window: 50ms coalescing (confirmed)
- [ ] Scope: Task-level only, not nested attributes (confirmed)
