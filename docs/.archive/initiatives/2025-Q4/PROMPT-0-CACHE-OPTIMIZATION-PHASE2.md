# Orchestrator Initialization: Cache Optimization Phase 2 - Realize Full Cache Potential

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

## The Mission: Extract Maximum Value from Existing Cache Infrastructure

The autom8_asana SDK has a mature cache infrastructure (13 entry types, batch operations, TTL resolution) that was designed for significant performance gains. A recent triage audit revealed a substantial gap between expected and actual cache performance on warm fetches.

### Triage Audit Findings

| Metric | Expected | Observed | Gap |
|--------|----------|----------|-----|
| Cold fetch (3,530 tasks) | ~20s | ~20.56s | Acceptable |
| Warm fetch | <1s | 8.84s | **8x slower than expected** |
| Speedup factor | 5-10x | 2.3x | **Significant underperformance** |

### Observed Symptoms

During warm cache testing, the audit noted:
- API calls still occurring during warm fetch (should be zero)
- Detection warnings appearing on paths that should hit cache
- GID enumeration patterns suggesting cache coordination issues
- Multiple cache layers exist but coordination between them unclear

### Why This Initiative?

- **Infrastructure Already Exists**: 13 entry types defined, 5 clients with caching, batch operations ready
- **Investment Not Realized**: Prior initiatives built the infrastructure; this initiative extracts value
- **Measurable Target**: Clear success criteria (warm fetch <1s, hit rate >90%)
- **Root Cause Unknown**: Triage identified symptoms, not root causes - discovery is essential

### Current State

**Cache Infrastructure (Mature)**:
- `EntryType` enum with 13 types: TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS, DATAFRAME, PROJECT, SECTION, USER, CUSTOM_FIELD, DETECTION
- `CacheEntry` with versioning via `modified_at`, TTL, and metadata
- Batch operations: `get_batch()`, `set_batch()`
- Entity-aware TTL resolution per ADR-0126
- Graceful degradation patterns established
- Invalidation via SaveSession per ADR-0125

**Prior Initiatives Completed**:
- P1 Fetch Path: TaskCacheCoordinator implemented, 91 tests passing, PASS validation
- P2 Detection: EntryType.DETECTION added, detection results cacheable
- P3 Hydration: opt_fields analysis complete (field normalization identified)
- P4 Stories: Discovery complete, wiring pattern defined

**What Remains Unclear**:

```
Triage Audit Observed:
  Warm fetch time: 8.84s (expected <1s)
  API calls during warm fetch: Non-zero (expected 0)
  Detection warnings on cached paths: Unexpected

Root Cause Candidates (Not Yet Verified):
  - Cache coordination between layers?
  - Field set mismatches preventing hits?
  - Race conditions or timing issues?
  - Invalidation happening unexpectedly?
  - Cache being bypassed by certain code paths?
```

### Cache Infrastructure Profile

| Attribute | Value |
|-----------|-------|
| Entry Types | 13 (TASK, PROJECT, SECTION, USER, CUSTOM_FIELD, DETECTION, STORIES, etc.) |
| Default TTL | 300s (task), 900s (project), 1800s (section), 3600s (user) |
| Batch Operations | `get_batch()`, `set_batch()` via CacheProvider |
| Versioning | `modified_at` timestamp, staleness detection |
| Invalidation | SaveSession post-commit hooks |
| Providers | InMemoryCacheProvider, S3CacheProvider, Redis (optional) |
| Metrics | CacheMetrics for hits, misses, latency |

### Target Outcomes

```
Target State (Measurable):
  Warm fetch latency:      <1s (for 3,500+ task projects)
  Cache hit rate:          >90% on second fetch
  API calls on warm:       0 (for fully cached data)
  Detection on cached:     No warnings on cache-hit paths

Non-Functional:
  No regression on cold fetch
  Graceful degradation maintained
  Backward compatibility preserved
```

### Key Constraints

- **Discovery-First**: Root cause unknown; must investigate before prescribing solutions
- **No Breaking Changes**: Existing DataFrame API and client APIs must remain stable
- **Backward Compatibility**: Consumers must not need code changes
- **Infrastructure Reuse**: Solutions must use existing cache infrastructure, not new systems
- **Graceful Degradation**: Cache failures must never break primary operations
- **Observable Outcomes**: All changes must be measurable via existing metrics

### Requirements Summary (Outcome-Based)

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Warm fetch latency <1s for 3,500+ task project | Must | Current: 8.84s |
| Cache hit rate >90% on second identical fetch | Must | Symptom: API calls occurring |
| Zero API calls when cache is warm and sufficient | Must | Symptom: Calls still happening |
| No detection warnings on cache-hit paths | Must | Symptom: Warnings appearing |
| Root cause identification with evidence | Must | Currently unknown |
| Cold fetch latency: no regression | Must | Baseline: ~20s |
| Graceful degradation on cache failure | Must | Established pattern |
| Structured logging for cache behavior | Should | For observability |
| Cache coordination documented | Should | For maintainability |
| Integration tests for warm cache scenario | Should | For regression prevention |

### Success Criteria

1. **Performance Target Met**: Second fetch of 3,500+ task project completes in <1s
2. **Cache Utilization Proven**: >90% hit rate measured via CacheMetrics
3. **Root Cause Documented**: Discovery document explains why gap existed
4. **Fix Verified**: Benchmark script demonstrates before/after improvement
5. **No Regressions**: All existing tests pass, cold fetch unchanged
6. **Patterns Documented**: Solution patterns available for future use
7. **Observable**: Structured logs allow cache behavior monitoring
8. **Maintainable**: Solution understood by team, not mysterious

### Performance Targets

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| Warm fetch latency (3,530 tasks) | 8.84s | <1.0s | `demo_parallel_fetch.py` |
| Cache hit rate (warm) | ~40% (estimated) | >90% | CacheMetrics |
| API calls during warm fetch | >0 | 0 | Request logging |
| Cold fetch latency | ~20.56s | ~20s (no regression) | `demo_parallel_fetch.py` |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Root Cause Discovery** | Requirements Analyst | Analysis document identifying root cause(s) with evidence |
| **2: Requirements** | Requirements Analyst | PRD-CACHE-OPTIMIZATION-P2 with acceptance criteria |
| **3: Architecture** | Architect | TDD-CACHE-OPTIMIZATION-P2 + ADRs for key decisions |
| **4: Implementation P1** | Principal Engineer | Core fix addressing root cause |
| **5: Implementation P2** | Principal Engineer | Observability, configuration, documentation |
| **6: Validation** | QA/Adversary | Performance benchmarks, cache verification |
| **7: Integration** | QA/Adversary | End-to-end validation, regression testing |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must investigate the performance gap with a forensic approach. This is discovery - not solution design.

### Symptom Investigation

| Observed Symptom | Questions to Answer |
|------------------|---------------------|
| Warm fetch 8.84s (expected <1s) | Where is time being spent? What operations run during warm fetch? |
| API calls during warm fetch | Which API calls? What triggers them? What GIDs? |
| Detection warnings on cached paths | What triggers detection? Why isn't cache hit preventing detection? |
| GID enumeration patterns | What is the enumeration pattern? Is it expected? |

### Code Path Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `dataframes/builders/project.py` | What code path executes on second fetch? Where does it check cache? |
| `dataframes/builders/task_cache.py` | Is TaskCacheCoordinator being used? Is it working correctly? |
| `dataframes/builders/parallel_fetch.py` | What happens on second call? Does it check cache first? |
| `models/business/detection/facade.py` | When is detection triggered? Should it run on cached data? |
| `models/business/hydration.py` | Are hydration paths using cache? Or bypassing it? |

### Cache Behavior Analysis

| Component | Questions |
|-----------|-----------|
| Cache population | When does cache get populated? Is it actually happening? |
| Cache lookup | When does cache get checked? Is it being checked on warm path? |
| Cache keys | What cache keys are being used? Are they consistent between write and read? |
| Cache versioning | Is versioning causing false staleness? Is TTL expiring unexpectedly? |
| opt_fields | Are field sets consistent? Could field mismatch cause cache miss? |

### Hypothesis Testing

| Hypothesis | Test Approach |
|------------|---------------|
| Cache not being checked on warm path | Add logging to cache lookup path, observe on second fetch |
| Cache being invalidated between fetches | Check invalidation triggers, TTL timing |
| Field set mismatch causing cache miss | Compare opt_fields at write vs. read |
| Detection bypassing cache | Trace detection call path, check cache check location |
| Coordination issue between layers | Map data flow through all cache-interacting components |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers from Discovery:

### Root Cause Questions (Must Answer)

1. **What is the actual root cause?** Why is warm fetch 8.84s instead of <1s?
2. **Where specifically is cache bypass occurring?** Which code path(s)?
3. **What API calls happen during warm fetch?** List them, with evidence.
4. **Why do detection warnings appear on cached paths?** What triggers detection?

### Cache Behavior Questions (Should Answer)

5. **Is cache population working correctly?** Are entries being written?
6. **Is cache lookup working correctly?** Are entries being found?
7. **Are cache keys consistent?** Same key on write and read?
8. **Is versioning/TTL causing false misses?** Unexpectedly stale or expired?

### Architecture Questions (Should Answer)

9. **Are there multiple cache layers competing?** Task cache, row cache, etc.?
10. **Is there a coordination problem between layers?** Race conditions?
11. **Are there multiple code paths for the same operation?** Inconsistent?
12. **What is the expected vs. actual data flow?** Document both.

### Observability Questions (Nice to Answer)

13. **What cache metrics exist today?** Are they being used?
14. **Can we add tracing without code changes?** Logging levels?
15. **What would make this problem visible in production?** Early warning?

## Related Documentation

Review before Discovery:

| Document | Purpose | Location |
|----------|---------|----------|
| P1 Learnings | Patterns established, components created | `/docs/analysis/INTEGRATION-CACHE-PERF-P1-LEARNINGS.md` |
| Fetch Path PRD | What P1 implemented | `/docs/requirements/PRD-CACHE-PERF-FETCH-PATH.md` |
| Fetch Path Validation | P1 results | `/docs/validation/VP-CACHE-PERF-FETCH-PATH.md` |
| Detection PRD | What P2 implemented | `/docs/requirements/PRD-CACHE-PERF-DETECTION.md` |
| Hydration Analysis | opt_fields investigation | `/docs/analysis/hydration-cache-opt-fields-analysis.md` |
| Stories Discovery | P4 wiring pattern | `/docs/analysis/stories-cache-wiring-discovery.md` |
| Cache Meta-Initiative | Original problem statement | `/docs/initiatives/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md` |

## Your First Task

Confirm understanding by:

1. Summarizing the Cache Optimization Phase 2 goal in 2-3 sentences
2. Acknowledging that the **root cause is unknown** and discovery is required first
3. Listing the 7 sessions and their deliverables
4. Identifying the **Discovery Phase** as the critical first step to understand the gap
5. Confirming the key questions that must be answered before Session 2
6. Acknowledging the constraints: discovery-first, no prescriptive solutions yet

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Root Cause Discovery

```markdown
Begin Session 1: Cache Performance Gap Root Cause Discovery

Work with the @requirements-analyst agent to investigate the cache performance gap with a forensic approach.

**Goals:**
1. Reproduce the 8.84s warm fetch performance issue
2. Trace execution path during second fetch
3. Identify which API calls occur during warm fetch (should be zero)
4. Determine why detection warnings appear on cached paths
5. Map cache lookup/population flow
6. Identify root cause(s) with evidence
7. Document actual vs. expected behavior

**Diagnostic Approach:**
1. Run `demo_parallel_fetch.py` with verbose logging
2. Add temporary logging to trace cache checks
3. Capture API call log during warm fetch
4. Compare cache keys between write and read
5. Verify cache entries exist after first fetch
6. Check if cache is being consulted on second fetch

**Files to Analyze:**
- `src/autom8_asana/dataframes/builders/project.py` - Build flow
- `src/autom8_asana/dataframes/builders/task_cache.py` - Cache coordinator
- `src/autom8_asana/dataframes/builders/parallel_fetch.py` - Fetch path
- `src/autom8_asana/models/business/detection/facade.py` - Detection triggers
- `src/autom8_asana/cache/entry.py` - Cache entry structure

**Deliverable:**
A discovery document with:
- Evidence of root cause (logs, traces, code analysis)
- Actual vs. expected data flow diagram
- Specific code path(s) causing the gap
- Impact assessment
- Recommendations for Session 2 (not solutions - just what needs fixing)

Create the investigation plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Cache Optimization Phase 2 Requirements Definition

Work with the @requirements-analyst agent to create PRD-CACHE-OPTIMIZATION-P2.

**Prerequisites:**
- Session 1 discovery document complete
- Root cause identified with evidence

**Goals:**
1. Define requirements to address identified root cause(s)
2. Define measurable acceptance criteria (<1s warm, >90% hit rate)
3. Define cache coordination requirements if multi-layer issue
4. Define observability requirements for ongoing monitoring
5. Define backward compatibility requirements
6. Define graceful degradation requirements

**Key Questions to Address:**
- What specific change(s) will address the root cause?
- How will we measure success?
- What could regress from these changes?
- What operational visibility do we need?

**PRD Organization:**
- FR-FIX-*: Requirements addressing root cause
- FR-COORD-*: Cache layer coordination (if needed)
- FR-OBSERVE-*: Observability requirements
- NFR-*: Performance targets, compatibility

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Cache Optimization Phase 2 Architecture Design

Work with the @architect agent to create TDD-CACHE-OPTIMIZATION-P2 and ADRs.

**Prerequisites:**
- PRD-CACHE-OPTIMIZATION-P2 approved

**Goals:**
1. Design fix for identified root cause
2. Design cache coordination pattern (if multi-layer issue)
3. Design observability integration
4. Document trade-offs and alternatives considered
5. ADR for key architectural decisions

**Required ADRs:**
- ADR-012X: Root cause fix approach (TBD based on discovery)
- ADR-012Y: Cache layer coordination (if needed)

**Architecture Constraints:**
- Must use existing cache infrastructure
- Must maintain backward compatibility
- Must preserve graceful degradation
- Must be observable via existing metrics

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Core Fix

Work with the @principal-engineer agent to implement the fix for root cause.

**Prerequisites:**
- PRD approved
- TDD approved
- ADR(s) documented

**Phase 1 Scope:**
1. Implement fix for identified root cause
2. Add unit tests for fixed behavior
3. Verify existing tests still pass
4. Verify warm fetch improvement locally

**Hard Constraints:**
- No breaking changes to existing APIs
- Cache failures must not break operations
- Must be backward compatible

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Observability & Documentation

Work with the @principal-engineer agent to add observability and documentation.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Add structured logging for cache behavior
2. Add cache metrics exposure
3. Update relevant documentation
4. Add integration tests for warm cache scenario
5. Update demo script with verification

Create the plan first. I'll review before you execute.
```

## Session 6: Validation

```markdown
Begin Session 6: Cache Optimization Phase 2 Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- Implementation phases complete

**Goals:**

**Part 1: Performance Validation**
- Warm fetch latency: <1s (from 8.84s)
- Cache hit rate (warm): >90%
- Cold fetch latency: No regression
- Zero API calls on warm fetch

**Part 2: Functional Validation**
- Cache population occurs after cold fetch
- Cache lookup occurs before warm fetch
- No detection warnings on cached paths
- Graceful degradation on cache failure

**Part 3: Failure Mode Testing**
- Cache provider unavailable -> Fetch succeeds
- Partial cache (some hits, some misses) -> Correct behavior
- TTL expiration -> Re-fetch occurs

**Part 4: Regression Testing**
- All existing tests pass
- No breaking changes to APIs
- demo_parallel_fetch.py shows improvement

Create the plan first. I'll review before you execute.
```

## Session 7: Integration

```markdown
Begin Session 7: Integration and End-to-End Validation

Work with the @qa-adversary agent to validate end-to-end behavior.

**Prerequisites:**
- Session 6 validation PASS

**Goals:**
1. End-to-end test with production-like data
2. Verify all cache layers coordinate correctly
3. Verify structured logging provides visibility
4. Document final performance results
5. Update /docs/INDEX.md with all deliverables
6. Create final validation report

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Triage Audit Context:**

- [ ] Original triage audit findings (8.84s warm, detection warnings)
- [ ] Prior P1-P4 sub-initiative status and deliverables
- [ ] P1 Learnings document (`INTEGRATION-CACHE-PERF-P1-LEARNINGS.md`)

**Cache Infrastructure:**

- [ ] `src/autom8_asana/cache/entry.py` - EntryType enum, CacheEntry
- [ ] `src/autom8_asana/cache/batch.py` - Batch operations
- [ ] `src/autom8_asana/cache/metrics.py` - CacheMetrics
- [ ] `src/autom8_asana/cache/stories.py` - Stories loader

**DataFrame Path:**

- [ ] `src/autom8_asana/dataframes/builders/project.py` - Build orchestration
- [ ] `src/autom8_asana/dataframes/builders/task_cache.py` - TaskCacheCoordinator
- [ ] `src/autom8_asana/dataframes/builders/parallel_fetch.py` - Parallel fetch

**Detection/Hydration Path:**

- [ ] `src/autom8_asana/models/business/detection/facade.py` - Detection entry
- [ ] `src/autom8_asana/models/business/hydration.py` - Hydration flow

**Demo/Benchmark:**

- [ ] `scripts/demo_parallel_fetch.py` - Benchmark script
- [ ] Existing benchmark results

---

# Appendix: Prior Initiative Reference

## Sub-Initiative Status

| Sub-Initiative | Status | Key Deliverables |
|----------------|--------|------------------|
| P1: Fetch Path | COMPLETE | TaskCacheCoordinator, 91 tests, VP-CACHE-PERF-FETCH-PATH PASS |
| P2: Detection | COMPLETE | EntryType.DETECTION, detection cache integration |
| P3: Hydration | DISCOVERY COMPLETE | opt_fields analysis, field normalization identified |
| P4: Stories | DISCOVERY COMPLETE | Wiring pattern defined, incremental loader exists |

## Key Patterns Established (P1)

- Two-phase cache strategy (enumerate-then-lookup)
- Coordinator pattern (TaskCacheCoordinator)
- Graceful degradation (try/except around cache ops)
- Batch operations (get_batch/set_batch)
- Structured observability (hit/miss logging)

## Known Gaps from Triage

| Gap | Evidence | Status |
|-----|----------|--------|
| Warm fetch 8.84s | Benchmark | Root cause unknown |
| API calls during warm | Observation | Not yet traced |
| Detection warnings | Observation | Not yet traced |

---

*This Prompt 0 initializes the Cache Optimization Phase 2 initiative with a discovery-first approach to identify and resolve the cache performance gap.*
