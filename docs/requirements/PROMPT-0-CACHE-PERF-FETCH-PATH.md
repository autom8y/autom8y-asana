# Orchestrator Initialization: Cache Performance - Fetch Path Investigation

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

## The Mission: Identify and Fix Why DataFrame Second Fetch is 11.56s Instead of <1s

The primary symptom of the cache performance gap is that a second DataFrame fetch takes 11.56 seconds when it should take less than 1 second. This sub-initiative investigates the root cause and implements the fix.

### Why This Initiative?

- **Core Symptom**: This is THE evidence that cache is not being utilized
- **Prerequisite Knowledge**: Understanding this gap will inform other sub-initiatives
- **Highest Impact**: Fixing this directly addresses the 10x gap
- **Diagnostic Value**: Discovery will reveal cache integration patterns

### Current State

**What We Observe**:
```
First fetch (cache miss):   13.55s
Second fetch (cache hit):   11.56s  <-- Only 1.2x faster, should be <1s
```

**Possible Root Causes**:

1. **Cache Population Not Happening**
   - ParallelSectionFetcher fetches tasks but does not call `set_batch()` on cache
   - Tasks are returned but never written to cache

2. **Cache Lookup Not Happening**
   - Second fetch does not check cache before fetching
   - `ProjectDataFrameBuilder` bypasses cache on build

3. **Opt_fields Mismatch**
   - First fetch uses different opt_fields than cache expects
   - Cache key includes opt_fields, so different fields = different cache entry

4. **Cache Key Mismatch**
   - First fetch uses `{task_gid}`, second uses `{task_gid}:{project_gid}`
   - Keys don't match, so cache miss

5. **TTL Already Expired**
   - Unlikely with 300s TTL and back-to-back fetches
   - Rule out during investigation

### Key Files to Investigate

| File | What to Check |
|------|---------------|
| `src/autom8_asana/dataframes/builders/project.py` | How does `build()` orchestrate fetch? Does it check cache? |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Does `ParallelSectionFetcher` write to cache after fetch? |
| `src/autom8_asana/dataframes/cache_integration.py` | What cache integration exists? Is it wired? |
| `src/autom8_asana/clients/tasks.py` | How does `list_async()` interact with cache? |
| `src/autom8_asana/cache/batch.py` | What are `get_batch()`/`set_batch()` signatures? |

### Target Architecture

```
Current Flow (SUSPECTED):
  project.to_dataframe_async() [1st call]
    --> ParallelSectionFetcher.fetch_all()
    --> Tasks returned (NOT cached?)
    --> DataFrame built

  project.to_dataframe_async() [2nd call]
    --> ParallelSectionFetcher.fetch_all()
    --> Tasks fetched AGAIN from API (cache miss)
    --> DataFrame built
    --> 11.56s instead of <1s

Desired Flow:
  project.to_dataframe_async() [1st call]
    --> ParallelSectionFetcher.fetch_all()
    --> Tasks returned AND cached via set_batch()
    --> DataFrame built

  project.to_dataframe_async() [2nd call]
    --> Check cache via get_batch()
    --> Cache HIT for all tasks
    --> DataFrame built from cache
    --> <1s
```

### Key Constraints

- **No Breaking Changes**: Existing DataFrame API must remain stable
- **Backward Compatibility**: Consumers must not need code changes
- **Cache-First Design**: Cache check should happen BEFORE API calls
- **Graceful Degradation**: Cache failures must not break DataFrame extraction

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Investigate why second fetch is 11.56s | Must |
| Identify specific cache integration gap | Must |
| Implement fix with full cache utilization | Must |
| Achieve <1s second fetch latency | Must |
| Add cache hit/miss logging for debugging | Should |
| Document cache integration pattern | Should |
| Add benchmark test for regression detection | Should |

### Success Criteria

1. **Root Cause Identified**: Clear understanding of why cache is bypassed
2. **Fix Implemented**: Code change that enables cache utilization
3. **Second Fetch <1s**: Benchmark proves 10x+ improvement
4. **All Tests Pass**: No regressions in existing tests
5. **Documentation**: Cache integration pattern documented

### Performance Targets

| Scenario | Current | Target |
|----------|---------|--------|
| First fetch (3,500 tasks) | 13.55s | 13.55s (cold cache expected) |
| Second fetch (3,500 tasks) | 11.56s | <1.0s |
| Cache hit rate (warm) | ~10% | >95% |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Root cause analysis - trace fetch path, identify cache integration gap |
| **2: Requirements** | Requirements Analyst | PRD-CACHE-PERF-FETCH-PATH with acceptance criteria |
| **3: Architecture** | Architect | TDD-CACHE-PERF-FETCH-PATH + ADR for cache integration pattern |
| **4: Implementation** | Principal Engineer | Fix implementation with cache integration |
| **5: Implementation P2** | Principal Engineer | Logging, configuration, documentation |
| **6: Validation** | QA/Adversary | Performance benchmarks, cache hit verification |
| **7: Integration** | QA/Adversary | Integration with other sub-initiatives |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Fetch Path Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `dataframes/builders/project.py` | How does `ProjectDataFrameBuilder.build()` orchestrate the fetch? |
| `dataframes/builders/parallel_fetch.py` | Does `ParallelSectionFetcher` interact with cache at all? |
| `dataframes/cache_integration.py` | What does this module do? Is it wired into the build process? |
| `clients/tasks.py` | How does `TasksClient.list_async()` interact with cache? |

### Cache Integration Analysis

| Component | Questions |
|-----------|-----------|
| `ProjectDataFrameBuilder` | Is there a cache parameter? Is it used? |
| `ParallelSectionFetcher` | Does it have cache awareness? Should it? |
| `TasksClient.list_async()` | Does list operation populate individual task cache? |
| `get_batch()` / `set_batch()` | Are these called anywhere in the DataFrame path? |

### Opt_fields Analysis

| Location | Questions |
|----------|-----------|
| ParallelSectionFetcher | What opt_fields does it request? |
| TasksClient cache | What opt_fields does cache expect? |
| Cache key structure | Is opt_fields part of the cache key? |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Root Cause Questions

1. **Is cache population happening?**: Does ParallelSectionFetcher call set_batch()?
2. **Is cache lookup happening?**: Does second build() check cache first?
3. **What is the opt_fields situation?**: Do fetch and cache use same fields?
4. **What is the cache key structure?**: Does it include project_gid, opt_fields?

### Design Questions

5. **Where should cache integration live?**: In builder? In fetcher? In client?
6. **Should ParallelSectionFetcher be cache-aware?**: Or should builder handle it?
7. **How to handle partial cache scenarios?**: Some cached, some not?

### Validation Questions

8. **How to measure cache hit rate?**: CacheMetrics? Logging?
9. **What is acceptable warm cache latency?**: <500ms? <1s?
10. **How to benchmark reliably?**: Repeated runs? Averaged?

## Your First Task

Confirm understanding by:

1. Summarizing the Fetch Path Investigation goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which files must be analyzed to understand the cache bypass
5. Listing which root cause questions you need answered before Session 2
6. Acknowledging that this is the FIRST sub-initiative and may inform others

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Fetch Path Discovery

Work with the @requirements-analyst agent to trace the DataFrame fetch path and identify the cache integration gap.

**Goals:**
1. Trace ProjectDataFrameBuilder.build() execution flow
2. Determine if ParallelSectionFetcher writes to cache
3. Determine if second build() checks cache first
4. Analyze opt_fields used in fetch vs cache expectations
5. Identify the specific point where cache integration is missing
6. Document current vs desired fetch flow
7. Propose fix location and approach

**Files to Analyze:**
- `src/autom8_asana/dataframes/builders/project.py` - Builder implementation
- `src/autom8_asana/dataframes/builders/parallel_fetch.py` - Parallel fetch
- `src/autom8_asana/dataframes/cache_integration.py` - Existing cache integration
- `src/autom8_asana/clients/tasks.py` - TasksClient cache pattern
- `src/autom8_asana/cache/batch.py` - Batch operation signatures

**Diagnostic Steps:**
1. Add logging to trace fetch path (or read code carefully)
2. Check if set_batch() is ever called after fetch
3. Check if get_batch() is ever called before fetch
4. Compare opt_fields between fetch and cache
5. Document findings

**Deliverable:**
A discovery document with:
- Current fetch flow diagram (where cache is bypassed)
- Root cause identification (which of the 5 hypotheses is correct)
- Proposed fix location
- Impact assessment
- Risk assessment

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Fetch Path Requirements Definition

Work with the @requirements-analyst agent to create PRD-CACHE-PERF-FETCH-PATH.

**Prerequisites:**
- Session 1 discovery document complete
- Root cause identified

**Goals:**
1. Define cache population requirements
2. Define cache lookup requirements
3. Define cache key requirements
4. Define opt_fields normalization requirements (if needed)
5. Define graceful degradation requirements
6. Define acceptance criteria for each requirement

**Key Questions to Address:**
- Where exactly should cache integration be added?
- What is the cache key structure?
- How to handle partial cache scenarios?
- What metrics should be exposed?

**PRD Organization:**
- FR-POPULATE-*: Cache population after fetch
- FR-LOOKUP-*: Cache lookup before fetch
- FR-KEY-*: Cache key structure
- FR-DEGRADE-*: Graceful degradation
- NFR-*: Performance targets (<1s cached)

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Fetch Path Architecture Design

Work with the @architect agent to create TDD-CACHE-PERF-FETCH-PATH and ADR.

**Prerequisites:**
- PRD-CACHE-PERF-FETCH-PATH approved

**Goals:**
1. Design cache integration pattern for DataFrame builder
2. Design cache population flow after parallel fetch
3. Design cache lookup flow before fetch
4. Design cache key structure
5. Document rejected alternatives

**Required ADRs:**
- ADR-NNNN: DataFrame Builder Cache Integration Pattern

**Architecture Constraints:**
- Must use existing cache infrastructure
- Must not break existing DataFrame API
- Must support graceful degradation

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Cache Integration

Work with the @principal-engineer agent to implement cache integration.

**Prerequisites:**
- PRD approved
- TDD approved
- ADR documented

**Phase 1 Scope:**
1. Implement cache population after ParallelSectionFetcher.fetch_all()
2. Implement cache lookup before fetch
3. Wire cache into ProjectDataFrameBuilder
4. Add unit tests for cache integration

**Hard Constraints:**
- No breaking changes to DataFrame API
- Cache failures must not break fetch
- Must use set_batch()/get_batch() for efficiency

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Observability & Configuration

Work with the @principal-engineer agent to add observability and configuration.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Add cache hit/miss logging
2. Add cache metrics exposure
3. Add configuration for cache behavior
4. Update documentation
5. Add integration tests

Create the plan first. I'll review before you execute.
```

## Session 6: Validation

```markdown
Begin Session 6: Fetch Path Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- Implementation phases complete

**Goals:**

**Part 1: Performance Validation**
- Second fetch latency: <1s (from 11.56s)
- Cache hit rate (warm): >95%
- First fetch latency: No regression

**Part 2: Functional Validation**
- Cache population occurs after fetch
- Cache lookup occurs before fetch
- Graceful degradation on cache failure

**Part 3: Failure Mode Testing**
- Cache provider unavailable -> Fetch succeeds
- Partial cache (some hits, some misses) -> Correct behavior
- TTL expiration -> Re-fetch occurs

**Part 4: Regression Testing**
- All existing DataFrame tests pass
- All existing cache tests pass

Create the plan first. I'll review before you execute.
```

## Session 7: Integration

```markdown
Begin Session 7: Integration with Meta-Initiative

Work with the @qa-adversary agent to validate integration with other sub-initiatives.

**Prerequisites:**
- All sessions complete
- Other sub-initiatives progressing

**Goals:**
1. Verify findings from this initiative inform other sub-initiatives
2. Ensure cache patterns are consistent across initiatives
3. Create shared benchmark methodology
4. Document lessons learned

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**DataFrame Infrastructure:**

- [ ] `src/autom8_asana/dataframes/builders/project.py` - Build process
- [ ] `src/autom8_asana/dataframes/builders/parallel_fetch.py` - Fetch implementation
- [ ] `src/autom8_asana/dataframes/cache_integration.py` - Existing integration
- [ ] `src/autom8_asana/dataframes/builders/base.py` - Base patterns

**Client Layer:**

- [ ] `src/autom8_asana/clients/tasks.py` - Cache pattern in TasksClient
- [ ] `src/autom8_asana/clients/base.py` - Base client cache patterns

**Cache Infrastructure:**

- [ ] `src/autom8_asana/cache/batch.py` - Batch operations
- [ ] `src/autom8_asana/cache/entry.py` - Entry structure
- [ ] `src/autom8_asana/cache/metrics.py` - Metrics available

**Prior Work:**

- [ ] `docs/requirements/PROMPT-0-WATERMARK-CACHE.md` - Prior initiative
- [ ] `docs/requirements/PROMPT-0-CACHE-UTILIZATION.md` - Client caching patterns
