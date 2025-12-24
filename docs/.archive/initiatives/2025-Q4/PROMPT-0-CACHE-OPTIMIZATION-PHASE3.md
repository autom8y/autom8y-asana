# Orchestrator Initialization: Cache Optimization Phase 3 - GID Enumeration Caching

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

## The Mission: Cache GID Enumeration to Achieve 10x Speedup

Phase 2 of cache optimization implemented task object caching and is functionally working. However, a three-agent triage audit (QA-Adversary, Architect, Principal Engineer) with **unanimous consensus** identified that warm fetch latency is still 9.67s instead of the target <1s. The root cause is now **known and verified**: GID enumeration is NOT cached.

### Triage Audit Findings (Verified Root Cause)

| Finding | Evidence |
|---------|----------|
| Task cache IS working | Log shows `cache_hit_skip_api_fetch` at 9.6s mark |
| GID enumeration NOT cached | 35+ API calls per fetch regardless of cache state |
| Time waste location | 9.5s spent on GID enumeration before cache is even consulted |

### The Bottleneck (Verified)

**File:** `src/autom8_asana/dataframes/builders/parallel_fetch.py` (lines 200-281)

```
WARM FETCH (Current - Broken):
1. API: _list_sections()                              ~0.5s   <- NOT CACHED
2. API: _fetch_section_gids() x 34 sections           ~9s     <- NOT CACHED
   -----------------------------------------------------------------
3. Cache lookup (100% HIT)                            ~0.1s   <- WORKS
4. [LOG: cache_hit_skip_api_fetch]
5. Build DataFrame                                    ~0.05s
-----------------------------------------------------------------
TOTAL: 9.67s (9.5s wasted on uncached GID enumeration)

TARGET STATE:
1. Cache: section list lookup                         ~0.01s  <- CACHED
2. Cache: GID enumeration lookup                      ~0.01s  <- CACHED
   -----------------------------------------------------------------
3. Cache lookup (100% HIT)                            ~0.1s   <- WORKS
4. Build DataFrame                                    ~0.05s
-----------------------------------------------------------------
TOTAL: <1s
```

### Why This Initiative?

- **Root Cause is KNOWN**: Unlike Phase 2 which required discovery, the bottleneck is identified with evidence
- **Surgical Fix Required**: Cache the GID enumeration results, section list, or both
- **Cache Infrastructure Exists**: EntryType.SECTION already exists; pattern is established
- **Measurable Target**: 10x speedup from 9.67s to <1s is clearly achievable

### Current State

**Cache Infrastructure (Mature)**:
- `EntryType` enum with 13 types including SECTION (TTL: 1800s)
- `CacheEntry` with versioning, TTL, batch operations
- Task cache working correctly (verified by `cache_hit_skip_api_fetch` log)
- Graceful degradation patterns established

**Phase 2 Achievements**:
- Task object caching: WORKING
- Cache population after fetch: WORKING
- Miss handling optimization: WORKING
- Cache hit on warm fetch: VERIFIED

**What's Not Cached (The Gap)**:
- `_list_sections()` result (line 195-198)
- `fetch_section_task_gids_async()` result (lines 200-257)
- Each `_fetch_section_gids()` call (lines 259-281)

### Current Performance Profile

| Metric | Value | Notes |
|--------|-------|-------|
| Warm fetch time | 9.67s | Target: <1s |
| API calls (warm) | 35+ | Target: 0 |
| Cache speedup | 2.3x | Target: 10x+ |
| Task cache hit rate | 100% | Already working |
| GID enumeration cache hit rate | 0% | Not implemented |

### Target Outcomes

```
Target State (Measurable):
  Warm fetch latency:      <1s (currently 9.67s)
  API calls on warm:       0 (currently 35+)
  Cache speedup:           10x+ (currently 2.3x)
  GID enumeration cached:  Yes (currently no)

Non-Functional:
  No regression on cold fetch
  Graceful degradation maintained
  Backward compatibility preserved
```

### Key Constraints

- **Known Root Cause**: Do not re-discover; focus on solution design
- **Surgical Scope**: Only cache GID enumeration and section list; no other changes
- **Pattern Reuse**: Use existing cache infrastructure (EntryType, CacheProvider, batch ops)
- **No Breaking Changes**: Existing APIs must remain stable
- **Graceful Degradation**: Cache failures must not break primary operations
- **Observable**: All changes must be measurable via existing metrics

### Requirements Summary (Outcome-Based)

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Warm fetch latency <1s | Must | Currently 9.67s |
| Zero API calls when cache warm | Must | Currently 35+ |
| GID enumeration results cached | Must | Core fix |
| Section list cached | Must | Prerequisite for GID cache |
| TTL strategy appropriate for GID data | Must | Sections change infrequently |
| Invalidation strategy defined | Must | When do cached GIDs become stale? |
| Cold fetch latency: no regression | Must | Baseline: ~20s |
| Cache population on cold fetch | Must | Prime the cache |
| Graceful degradation on cache failure | Must | Established pattern |
| Structured logging for GID cache ops | Should | For observability |

### Success Criteria

1. **Performance Target Met**: Warm fetch completes in <1s (from 9.67s)
2. **Zero Warm API Calls**: No API calls when cache is fully warm
3. **10x Speedup Achieved**: Cache speedup factor >10x (from 2.3x)
4. **GID Enumeration Cached**: Section-to-GID mappings served from cache
5. **Section List Cached**: `_list_sections()` result served from cache
6. **No Regressions**: All existing tests pass, cold fetch unchanged
7. **Observable**: Structured logs show GID cache hit/miss
8. **Graceful Degradation**: Cache failure falls back to API fetch

### Performance Targets

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| Warm fetch latency | 9.67s | <1.0s | `demo_parallel_fetch.py` |
| API calls (warm) | 35+ | 0 | Request logging |
| Cache speedup | 2.3x | 10x+ | Cold/warm ratio |
| GID cache hit rate | 0% | 100% | CacheMetrics |
| Cold fetch latency | ~20s | ~20s (no regression) | Benchmark |

## Session-Phased Approach

**Note**: Discovery is minimal for this initiative because the root cause is already verified by three-agent consensus. Sessions are streamlined accordingly.

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Requirements** | Requirements Analyst | PRD-CACHE-OPTIMIZATION-P3 with acceptance criteria |
| **2: Architecture** | Architect | TDD-CACHE-OPTIMIZATION-P3 + ADRs for caching strategy |
| **3: Implementation** | Principal Engineer | GID enumeration caching, section list caching |
| **4: Validation** | QA/Adversary | Performance benchmarks, cache verification |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Architecture Questions for Architect (Session 2)

The root cause is known. The Architect must design the caching strategy:

### Caching Strategy Questions

| Question | Options to Consider |
|----------|---------------------|
| What is the cache key format for GID enumeration? | `project:{gid}:section_gids` vs `section:{gid}:task_gids` |
| Should we cache per-section or per-project? | Project-level (one entry) vs Section-level (N entries) |
| What EntryType should be used? | New `SECTION_TASK_GIDS` vs reuse `SECTION` |
| What TTL is appropriate? | 1800s (section TTL) vs 900s vs 300s |
| How should invalidation work? | TTL-only vs explicit invalidation on task move |
| Should section list be cached separately? | Yes (prerequisite) vs included in GID cache |

### Integration Points

| Component | Question |
|-----------|----------|
| `ParallelSectionFetcher` | Where to add cache check - in constructor or in method? |
| `ProjectDataFrameBuilder` | Who owns cache population - fetcher or builder? |
| `TaskCacheCoordinator` | Should GID cache use same coordinator or new one? |
| `CacheProvider` | Use existing batch operations or single entry? |

## Open Questions (Minimal - Root Cause Known)

| Question | Owner | Priority |
|----------|-------|----------|
| Per-section vs per-project GID caching? | Architect | Must answer in TDD |
| What invalidation triggers are needed? | Architect | Must answer in TDD |
| Should section list use same or separate cache entry? | Architect | Should answer in TDD |

## Related Documentation

| Document | Purpose | Location |
|----------|---------|----------|
| Phase 2 Prompt 0 | Prior phase context | `/docs/initiatives/PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md` |
| Phase 2 PRD | Prior requirements | `/docs/requirements/PRD-CACHE-OPTIMIZATION-P2.md` |
| Phase 2 TDD | Prior design | `/docs/design/TDD-CACHE-OPTIMIZATION-P2.md` |
| Cache Entry Types | Existing EntryType enum | `src/autom8_asana/cache/entry.py` |
| Parallel Fetcher | Bottleneck code | `src/autom8_asana/dataframes/builders/parallel_fetch.py` |
| Task Cache Coordinator | Existing pattern | `src/autom8_asana/dataframes/builders/task_cache.py` |

## Your First Task

Confirm understanding by:

1. Summarizing the Cache Optimization Phase 3 goal in 2-3 sentences
2. Acknowledging that the **root cause is KNOWN** (GID enumeration not cached)
3. Listing the 4 sessions and their deliverables
4. Confirming the key architectural questions for Session 2
5. Acknowledging the constraints: surgical fix, pattern reuse, no breaking changes

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Requirements

```markdown
Begin Session 1: GID Enumeration Caching Requirements

Work with the @requirements-analyst agent to create PRD-CACHE-OPTIMIZATION-P3.

**Context (Root Cause Known)**:
The three-agent triage audit identified that warm fetch takes 9.67s because:
- `_list_sections()` makes an API call (not cached)
- `fetch_section_task_gids_async()` makes N API calls (not cached)
- Task cache lookup happens AFTER these calls (works, but too late)

**Goals:**
1. Define requirements for GID enumeration caching
2. Define requirements for section list caching
3. Define cache key format requirements
4. Define TTL and invalidation requirements
5. Define measurable acceptance criteria (<1s warm, 0 API calls)
6. Define graceful degradation requirements
7. Define observability requirements

**Key Constraints:**
- Surgical scope: Only GID enumeration and section list caching
- Pattern reuse: Use existing cache infrastructure
- No breaking changes to public APIs

**PRD Organization:**
- FR-GID-*: GID enumeration caching requirements
- FR-SECTION-*: Section list caching requirements
- FR-CACHE-*: Cache behavior requirements (TTL, invalidation)
- FR-OBS-*: Observability requirements
- NFR-*: Performance targets, compatibility

Create the plan first. I'll review before you execute.
```

## Session 2: Architecture

```markdown
Begin Session 2: GID Enumeration Cache Architecture

Work with the @architect agent to create TDD-CACHE-OPTIMIZATION-P3 and ADRs.

**Prerequisites:**
- PRD-CACHE-OPTIMIZATION-P3 approved

**Goals:**
1. Design cache key format for GID enumeration
2. Design per-section vs per-project caching strategy
3. Design EntryType usage (new type vs reuse SECTION)
4. Design TTL strategy for GID data
5. Design invalidation strategy
6. Design integration with ParallelSectionFetcher
7. Document trade-offs and alternatives

**Required ADRs:**
- ADR-0121: GID Enumeration Cache Strategy
- ADR-0122: Section List Cache Integration (if separate from GID cache)

**Architecture Constraints:**
- Must use existing cache infrastructure
- Must maintain backward compatibility
- Must preserve graceful degradation
- Must be observable via structured logging

**Key Design Questions:**
1. Cache key format: `project:{gid}:section_gids` vs `section:{gid}:task_gids`?
2. Per-project (1 entry) vs per-section (N entries)?
3. New `EntryType.SECTION_TASK_GIDS` vs reuse `EntryType.SECTION`?
4. TTL: 1800s (section TTL) vs shorter?
5. Cache population: in fetcher or in builder?
6. Cache lookup: before or during `fetch_section_task_gids_async()`?

Create the plan first. I'll review before you execute.
```

## Session 3: Implementation

```markdown
Begin Session 3: GID Enumeration Cache Implementation

Work with the @principal-engineer agent to implement the caching fix.

**Prerequisites:**
- PRD approved
- TDD approved
- ADR(s) documented

**Implementation Scope:**
1. Add cache lookup in `_list_sections()` or wrapper
2. Add cache lookup in `fetch_section_task_gids_async()`
3. Add cache population after cold fetch
4. Add structured logging for GID cache operations
5. Add unit tests for GID cache behavior
6. Verify warm fetch improvement

**Key Files to Modify:**
- `src/autom8_asana/dataframes/builders/parallel_fetch.py` (lines 195-281)
- `src/autom8_asana/cache/entry.py` (if new EntryType needed)
- `tests/unit/dataframes/test_parallel_fetch.py`

**Hard Constraints:**
- No breaking changes to existing APIs
- Cache failures must not break operations
- Must be backward compatible
- Follow existing patterns from TaskCacheCoordinator

Create the plan first. I'll review before you execute.
```

## Session 4: Validation

```markdown
Begin Session 4: Cache Optimization Phase 3 Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- Implementation complete

**Goals:**

**Part 1: Performance Validation**
- Warm fetch latency: <1s (from 9.67s)
- API calls (warm): 0 (from 35+)
- Cache speedup: 10x+ (from 2.3x)
- Cold fetch latency: No regression

**Part 2: Functional Validation**
- GID enumeration cache populated after cold fetch
- GID enumeration served from cache on warm fetch
- Section list served from cache on warm fetch
- Graceful degradation on cache failure

**Part 3: Failure Mode Testing**
- Cache provider unavailable -> Fetch succeeds via API
- Partial cache (some sections cached) -> Correct behavior
- TTL expiration -> Re-enumeration occurs
- Task moved between sections -> Eventually consistent

**Part 4: Regression Testing**
- All existing tests pass
- No breaking changes to APIs
- Phase 2 cache behavior unchanged
- demo_parallel_fetch.py shows 10x improvement

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Triage Audit Context:**

- [x] Three-agent consensus finding: GID enumeration not cached
- [x] Benchmark data: 9.67s warm, 2.3x speedup, 35+ API calls
- [x] Evidence: `cache_hit_skip_api_fetch` log proves task cache works

**Bottleneck Code:**

- [x] `parallel_fetch.py:195-198` - `_list_sections()` API call
- [x] `parallel_fetch.py:200-257` - `fetch_section_task_gids_async()` N API calls
- [x] `parallel_fetch.py:259-281` - `_fetch_section_gids()` per-section call

**Cache Infrastructure:**

- [x] `src/autom8_asana/cache/entry.py` - EntryType enum (SECTION exists, TTL 1800s)
- [x] `src/autom8_asana/cache/batch.py` - Batch operations available
- [x] `src/autom8_asana/dataframes/builders/task_cache.py` - Pattern reference

**Prior Phase Context:**

- [x] `/docs/initiatives/PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md`
- [x] `/docs/requirements/PRD-CACHE-OPTIMIZATION-P2.md`
- [x] `/docs/design/TDD-CACHE-OPTIMIZATION-P2.md` (reference)

---

# Appendix: Three-Agent Triage Summary

## Unanimous Finding

**Root Cause**: GID enumeration is NOT cached.

## Evidence Chain

1. **Benchmark Data**: Warm fetch 9.67s (target <1s)
2. **Log Analysis**: `cache_hit_skip_api_fetch` appears at 9.6s mark
3. **Interpretation**: Task cache IS working; 9.5s wasted before cache is consulted
4. **Code Review**: `fetch_section_task_gids_async()` makes N+1 API calls with no cache check

## Data Flow (Current vs Target)

```
CURRENT (Broken):
_list_sections()           -> API (0.5s)
_fetch_section_gids() x N  -> API x N (9s)
cache_lookup()             -> CACHE HIT (0.1s)
build_dataframe()          -> Memory (0.05s)
-------------------------------------------------
TOTAL: 9.67s

TARGET (Fixed):
_list_sections()           -> CACHE HIT (0.01s)
fetch_section_task_gids()  -> CACHE HIT (0.01s)
cache_lookup()             -> CACHE HIT (0.1s)
build_dataframe()          -> Memory (0.05s)
-------------------------------------------------
TOTAL: <1s
```

## Agent Consensus

| Agent | Finding | Confidence |
|-------|---------|------------|
| QA-Adversary | GID enumeration is the bottleneck | High |
| Architect | Cache infrastructure supports this fix | High |
| Principal Engineer | Surgical fix is feasible | High |

---

*This Prompt 0 initializes Cache Optimization Phase 3 with a known root cause and focused scope for a surgical fix to achieve 10x cache speedup.*
