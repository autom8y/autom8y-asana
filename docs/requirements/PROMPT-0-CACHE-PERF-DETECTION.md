# Orchestrator Initialization: Cache Performance - Detection Result Caching

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

## The Mission: Cache Detection Results to Eliminate Redundant API Calls

`detect_entity_type_async()` is called frequently during DataFrame extraction and hydration operations. When `allow_structure_inspection=True`, it makes a Tier 4 API call (subtask fetch) to determine entity type. These results are not cached, causing repeated API calls for the same task GID.

### Why This Initiative?

- **High Frequency**: Detection is called for every task during extraction
- **API Cost**: Tier 4 makes subtask API call that adds ~200ms per detection
- **Deterministic Results**: Entity type for a given task GID is stable
- **Simple Fix**: Add EntryType.DETECTION and cache the DetectionResult

### Current State

**Detection Architecture (from `detection/facade.py`)**:

```python
async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    """
    Detection order:
    1. Async Tier 1: Project membership with lazy workspace discovery
    2-3. Sync tiers: Name patterns, parent inference (no API)
    4. Structure inspection (requires API call, disabled by default)
    5. UNKNOWN fallback
    """
```

**The Problem**:
- Tier 4 (structure inspection) fetches subtasks via API
- DetectionResult is returned but NOT cached
- Same task detected again = same API call again
- During DataFrame extraction, this multiplies across thousands of tasks

**Detection Result Structure**:
```python
@dataclass
class DetectionResult:
    entity_type: EntityType
    confidence: float
    tier_used: int
    needs_healing: bool
    expected_project_gid: str | None
```

### Target Architecture

```
Current Flow:
  detect_entity_type_async(task, client, allow_structure_inspection=True)
    --> Tier 1-3 (no API)
    --> Tier 4: fetch subtasks (API call ~200ms)
    --> Return DetectionResult (not cached)

  [Same task detected again]
    --> Tier 1-3 (no API)
    --> Tier 4: fetch subtasks AGAIN (~200ms)
    --> Return DetectionResult

Desired Flow:
  detect_entity_type_async(task, client, allow_structure_inspection=True)
    --> Check cache for detection result
    --> Cache MISS: Execute tiers, cache result
    --> Return DetectionResult

  [Same task detected again]
    --> Check cache for detection result
    --> Cache HIT: Return cached DetectionResult (<5ms)
```

### Key Constraints

- **Tier Preservation**: Cache should not bypass lower tiers (1-3 are O(1))
- **Versioning Strategy**: Detection result validity tied to task.modified_at
- **Cache Key**: Simple `{task_gid}` with EntryType.DETECTION
- **TTL Alignment**: Match task TTL (300s) for consistency
- **Invalidation**: SaveSession mutations should invalidate detection cache

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Add EntryType.DETECTION to cache entry types | Must |
| Cache DetectionResult after Tier 4 execution | Must |
| Check cache before executing Tier 4 | Must |
| Use task.modified_at for versioning | Must |
| Invalidate detection cache on task mutation | Should |
| Add detection cache metrics | Should |
| TTL matching task cache (300s) | Should |

### Success Criteria

1. **Cache Hit on Repeat Detection**: Same task GID returns cached result
2. **No Regression**: Tiers 1-3 still execute (they're fast)
3. **API Call Reduction**: Tier 4 only executes once per task per TTL
4. **Detection Accuracy**: Cached results are correct for unchanged tasks
5. **Invalidation Works**: Mutated tasks get re-detected

### Performance Targets

| Scenario | Current | Target |
|----------|---------|--------|
| Tier 4 detection (cache miss) | ~200ms | ~200ms (expected) |
| Tier 4 detection (cache hit) | ~200ms | <5ms |
| Detection during extraction (1000 tasks) | 200s (worst case) | <5s |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Detection call sites analysis, cache integration points |
| **2: Requirements** | Requirements Analyst | PRD-CACHE-PERF-DETECTION with acceptance criteria |
| **3: Architecture** | Architect | TDD-CACHE-PERF-DETECTION + ADR for detection caching pattern |
| **4: Implementation P1** | Principal Engineer | EntryType.DETECTION, cache check/store in facade |
| **5: Implementation P2** | Principal Engineer | Invalidation wiring, metrics |
| **6: Validation** | QA/Adversary | Detection accuracy, cache hit verification |
| **7: Integration** | QA/Adversary | Integration with hydration and DataFrame paths |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Detection Facade Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `models/business/detection/facade.py` | Where exactly is Tier 4 executed? Where to inject cache? |
| `models/business/detection/tier4.py` | What does structure inspection return? What to cache? |
| `models/business/detection/types.py` | Is DetectionResult serializable for cache? |

### Call Site Analysis

| Component | Questions |
|-----------|-----------|
| `hydration.py` | How often is detect_entity_type_async called? |
| DataFrame extraction | Where is detection invoked during extraction? |
| Other callers | What other code paths call detection? |

### Cache Integration Points

| Component | Questions |
|-----------|-----------|
| `cache/entry.py` | How to add EntryType.DETECTION? |
| Cache key structure | `{task_gid}` or `{task_gid}:detection`? |
| Versioning | How to use task.modified_at for detection cache? |
| Invalidation | How to wire SaveSession to invalidate detection? |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Caching Strategy Questions

1. **What to cache?**: Full DetectionResult or just entity_type?
2. **Cache key structure?**: `{task_gid}` with EntryType.DETECTION?
3. **Versioning field?**: task.modified_at (but task may not be fetched yet)?
4. **Where to inject cache?**: In facade? In tier4 specifically?

### Tier Interaction Questions

5. **Should tiers 1-3 check cache?**: Or only tier 4?
6. **Cache tier_used field?**: Should we cache which tier succeeded?
7. **Handle UNKNOWN results?**: Cache or re-detect?

### Invalidation Questions

8. **What mutations invalidate detection?**: Task name change? Project change?
9. **Cascade invalidation?**: If parent changes, invalidate children?
10. **TTL vs explicit invalidation?**: Which is primary strategy?

## Your First Task

Confirm understanding by:

1. Summarizing the Detection Caching goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which files must be analyzed (detection facade, tier4, types)
5. Listing which caching strategy questions you need answered before Session 2
6. Acknowledging the relationship to hydration (which uses detection heavily)

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Detection Caching Discovery

Work with the @requirements-analyst agent to analyze detection call sites and identify cache integration points.

**Goals:**
1. Map all call sites of detect_entity_type_async()
2. Understand Tier 4 structure inspection implementation
3. Determine what should be cached (full DetectionResult?)
4. Identify cache integration point in facade
5. Determine cache key and versioning strategy
6. Analyze invalidation requirements
7. Estimate API call savings

**Files to Analyze:**
- `src/autom8_asana/models/business/detection/facade.py` - Main entry points
- `src/autom8_asana/models/business/detection/tier4.py` - Structure inspection
- `src/autom8_asana/models/business/detection/types.py` - DetectionResult structure
- `src/autom8_asana/models/business/hydration.py` - Major call site
- `src/autom8_asana/cache/entry.py` - EntryType enum

**Detection Flow to Trace:**
1. detect_entity_type_async() entry
2. Tier 1-3 execution (fast, no API)
3. Tier 4 execution (API call)
4. Result return (currently not cached)

**Deliverable:**
A discovery document with:
- Detection call site map
- Proposed cache integration design
- Cache key and versioning strategy
- Invalidation approach
- Estimated performance impact

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Detection Caching Requirements Definition

Work with the @requirements-analyst agent to create PRD-CACHE-PERF-DETECTION.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define cache entry type requirements (FR-ENTRY-*)
2. Define cache integration requirements (FR-INTEGRATE-*)
3. Define versioning requirements (FR-VERSION-*)
4. Define invalidation requirements (FR-INVALIDATE-*)
5. Define detection accuracy requirements (FR-ACCURACY-*)
6. Define acceptance criteria for each requirement

**Key Questions to Address:**
- What exact data is cached?
- What is the cache key structure?
- How is versioning handled without fetching task first?
- What triggers cache invalidation?

**PRD Organization:**
- FR-ENTRY-*: EntryType.DETECTION definition
- FR-INTEGRATE-*: Cache check/store in detection facade
- FR-VERSION-*: Versioning strategy
- FR-INVALIDATE-*: Cache invalidation triggers
- NFR-*: Performance targets (<5ms cached)

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Detection Caching Architecture Design

Work with the @architect agent to create TDD-CACHE-PERF-DETECTION and ADR.

**Prerequisites:**
- PRD-CACHE-PERF-DETECTION approved

**Goals:**
1. Design DetectionResult cache entry structure
2. Design cache integration in detect_entity_type_async()
3. Design versioning without pre-fetching task
4. Design invalidation triggers
5. Document trade-offs and alternatives

**Required ADRs:**
- ADR-NNNN: Detection Result Caching Strategy

**Architecture Constraints:**
- Must not slow down Tiers 1-3 (they're already fast)
- Must use existing cache infrastructure
- Must handle case where task.modified_at is unknown

**Component Changes:**
```
src/autom8_asana/
+-- cache/
|   +-- entry.py              # ADD: EntryType.DETECTION
+-- models/business/detection/
|   +-- facade.py             # UPDATE: Add cache check/store
|   +-- cache.py              # NEW: Detection cache integration
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Core Detection Caching

Work with the @principal-engineer agent to implement core detection caching.

**Prerequisites:**
- PRD approved
- TDD approved
- ADR documented

**Phase 1 Scope:**
1. Add EntryType.DETECTION to cache/entry.py
2. Create detection cache integration module
3. Add cache check before Tier 4 execution
4. Add cache store after Tier 4 execution
5. Add unit tests for detection caching

**Hard Constraints:**
- Tiers 1-3 remain unaffected
- Detection accuracy must not regress
- Cache failures must not break detection

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Invalidation & Metrics

Work with the @principal-engineer agent to add invalidation and metrics.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Wire SaveSession to invalidate detection cache on task mutation
2. Add detection cache metrics (hits, misses)
3. Add configuration for detection cache TTL
4. Update documentation
5. Add integration tests

**Invalidation Triggers:**
- Task name change (affects Tier 2)
- Task project change (affects Tier 1)
- Task parent change (affects hierarchy)

Create the plan first. I'll review before you execute.
```

## Session 6: Validation

```markdown
Begin Session 6: Detection Caching Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- Implementation phases complete

**Goals:**

**Part 1: Cache Behavior Validation**
- Cache hit returns correct DetectionResult
- Cache miss executes Tier 4 and stores result
- Repeat detection for same GID hits cache

**Part 2: Detection Accuracy Validation**
- Cached result matches fresh detection
- Entity type detection is accurate
- Tier information is preserved

**Part 3: Performance Validation**
- Cached detection: <5ms
- Fresh detection: ~200ms (unchanged)
- 1000 detections (cached): <5s

**Part 4: Invalidation Validation**
- Task mutation invalidates detection cache
- Re-detection after mutation is accurate

**Part 5: Failure Mode Testing**
- Cache unavailable -> Detection works (uncached)
- Corrupted cache entry -> Re-detection occurs

Create the plan first. I'll review before you execute.
```

## Session 7: Integration

```markdown
Begin Session 7: Integration with Hydration and DataFrame Paths

Work with the @qa-adversary agent to validate integration.

**Prerequisites:**
- Detection caching complete
- Hydration sub-initiative progressing

**Goals:**
1. Verify detection caching improves hydration performance
2. Verify detection caching improves DataFrame extraction
3. Ensure cache patterns are consistent
4. Document integration points

**Integration Points:**
- hydrate_from_gid_async() uses detect_entity_type_async()
- _traverse_upward_async() uses detect_entity_type_async()
- DataFrame extraction may use detection

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Detection Infrastructure:**

- [ ] `src/autom8_asana/models/business/detection/facade.py` - Entry points
- [ ] `src/autom8_asana/models/business/detection/tier4.py` - Structure inspection
- [ ] `src/autom8_asana/models/business/detection/types.py` - DetectionResult
- [ ] `src/autom8_asana/models/business/detection/config.py` - Configuration

**Call Sites:**

- [ ] `src/autom8_asana/models/business/hydration.py` - Major caller
- [ ] Other files calling detect_entity_type_async

**Cache Infrastructure:**

- [ ] `src/autom8_asana/cache/entry.py` - EntryType enum
- [ ] `src/autom8_asana/cache/settings.py` - TTL configuration
- [ ] `src/autom8_asana/cache/batch.py` - Batch operations (if needed)

**Prior Work:**

- [ ] `docs/requirements/PROMPT-0-CACHE-UTILIZATION.md` - Caching patterns
- [ ] `docs/requirements/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md` - Meta context
