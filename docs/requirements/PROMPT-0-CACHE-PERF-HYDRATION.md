# Orchestrator Initialization: Cache Performance - Hydration Path Optimization

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

## The Mission: Enable Hydration Path to Leverage Task Cache

`_traverse_upward_async()` and `hydrate_from_gid_async()` use custom `opt_fields` (`_DETECTION_OPT_FIELDS` and `_BUSINESS_FULL_OPT_FIELDS`) for task fetches. These custom field sets may not align with what `TasksClient` caches, causing cache misses even when tasks have been previously fetched.

### Why This Initiative?

- **Repeated Parent Fetches**: Hydration traverses parent chain, fetching same parents repeatedly
- **Opt_fields Mismatch**: Custom fields bypass TasksClient cache
- **Hierarchy Depth**: Business hierarchy is 4-5 levels deep, multiplying cache misses
- **Integration Point**: Connects hydration to existing task cache infrastructure

### Current State

**Hydration Opt_fields (from `hydration.py`)**:

```python
# Fields needed for entity type detection during initial fetch and traversal
_DETECTION_OPT_FIELDS: list[str] = [
    "memberships.project.gid",
    "memberships.project.name",
    "name",
    "parent.gid",
]

# Full fields needed for Business entities
_BUSINESS_FULL_OPT_FIELDS: list[str] = [
    "memberships.project.gid",
    "memberships.project.name",
    "name",
    "parent.gid",
    "custom_fields",
    "custom_fields.name",
    # ... more custom_field expansions
]
```

**The Problem**:
- `_traverse_upward_async()` calls `client.tasks.get_async(gid, opt_fields=_DETECTION_OPT_FIELDS)`
- `TasksClient` cache may use different default opt_fields
- Cache key may include opt_fields, so different fields = cache miss
- Same parent task fetched multiple times during different traversals

**Traversal Pattern**:
```
Contact -> ContactHolder -> Business (3 fetches)
Offer -> OfferHolder -> Unit -> UnitHolder -> Business (5 fetches)

If same Business traversed via different paths:
- Contact path: 3 fetches
- Offer path: 5 fetches
- Business fetched TWICE (once per path) due to opt_fields mismatch
```

### Target Architecture

```
Current Flow:
  _traverse_upward_async(entity, client)
    --> client.tasks.get_async(parent_gid, opt_fields=_DETECTION_OPT_FIELDS)
    --> Cache miss (custom opt_fields)
    --> API call (~200ms)
    --> [Repeat for each parent]

Desired Flow (Option A - Normalize opt_fields):
  _traverse_upward_async(entity, client)
    --> client.tasks.get_async(parent_gid, opt_fields=STANDARD_FIELDS)
    --> Cache HIT (if previously fetched)
    --> <5ms per cached parent

Desired Flow (Option B - Field subsetting):
  _traverse_upward_async(entity, client)
    --> client.tasks.get_async(parent_gid, opt_fields=_DETECTION_OPT_FIELDS)
    --> Cache checks if cached fields are superset of requested
    --> Cache HIT (superset match)
    --> <5ms per cached parent
```

### Key Constraints

- **Detection Accuracy**: Opt_fields normalization must not break detection
- **Business Full Fields**: Business needs custom_fields for cascading
- **Cache Key Strategy**: Must work with existing TasksClient cache
- **Backward Compatibility**: Hydration API must not change

### Design Options

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A: Normalize opt_fields** | Use standard field set that includes detection fields | Simple; uses existing cache | May fetch more fields than needed |
| **B: Field subsetting** | Cache returns hit if cached fields superset of requested | Minimal change to callers | Complex cache logic |
| **C: Separate cache** | Hydration has own cache with custom key | Isolated from task cache | Duplication; more complexity |
| **D: Two-phase fetch** | First check cache, then fetch missing fields | Optimal field coverage | Two cache operations |

**Recommended**: Option A (normalize opt_fields) is simplest and aligns with existing TasksClient cache.

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Investigate current opt_fields vs cache expectation | Must |
| Implement strategy to enable cache hits on hydration | Must |
| Achieve cache hits for repeated parent traversals | Must |
| Maintain detection accuracy | Must |
| Document opt_fields normalization approach | Should |
| Add hydration cache metrics | Should |

### Success Criteria

1. **Cache Hits on Hydration**: Same parent GID returns cached task
2. **Detection Accuracy Preserved**: Entity type detection is accurate
3. **Business Fields Available**: Business entities have custom_fields for cascading
4. **Performance Improvement**: Repeated hydrations are faster
5. **No API Regression**: No increase in API calls

### Performance Targets

| Scenario | Current | Target |
|----------|---------|--------|
| Parent fetch (cache miss) | ~200ms | ~200ms (expected) |
| Parent fetch (cache hit) | ~200ms | <5ms |
| Full traversal (5 levels, cached) | ~1s | <50ms |
| Repeated Business hydration | ~1s | <50ms |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Opt_fields analysis, cache key structure, integration strategy |
| **2: Requirements** | Requirements Analyst | PRD-CACHE-PERF-HYDRATION with acceptance criteria |
| **3: Architecture** | Architect | TDD-CACHE-PERF-HYDRATION + ADR for opt_fields normalization |
| **4: Implementation P1** | Principal Engineer | Opt_fields normalization in hydration |
| **5: Implementation P2** | Principal Engineer | Cache integration verification, metrics |
| **6: Validation** | QA/Adversary | Cache hit verification, detection accuracy |
| **7: Integration** | QA/Adversary | Integration with detection caching |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Opt_fields Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `models/business/hydration.py` | What opt_fields are used? Where? |
| `clients/tasks.py` | What opt_fields does TasksClient cache use? |
| `cache/` | Is opt_fields part of cache key? |

### Cache Key Structure Analysis

| Component | Questions |
|-----------|-----------|
| TasksClient.get_async() | What is the cache key structure? |
| Cache entry | Does key include opt_fields hash? |
| Cache lookup | Does it require exact opt_fields match? |

### Normalization Feasibility

| Consideration | Questions |
|---------------|-----------|
| Standard field set | What fields does TasksClient cache by default? |
| Detection fields | Are detection fields subset of standard? |
| Business fields | Are business fields subset of standard? |
| Field superset | Can we define a superset that works for all? |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Opt_fields Questions

1. **What does TasksClient cache by default?**: What opt_fields?
2. **Is opt_fields part of cache key?**: Different fields = different cache entry?
3. **What fields does detection need?**: Can we use standard set?
4. **What fields does Business need?**: Can we use standard set?

### Strategy Questions

5. **Normalize or subset?**: Which approach is better?
6. **Standard field set definition**: What should it include?
7. **Business special case**: Does Business need separate treatment?
8. **Detection special case**: Does Tier 4 structure inspection need specific fields?

### Integration Questions

9. **Coordination with detection caching?**: How do these interact?
10. **Invalidation coordination?**: Do both use same invalidation triggers?

## Your First Task

Confirm understanding by:

1. Summarizing the Hydration Path Optimization goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which files must be analyzed (hydration.py, tasks.py, cache/)
5. Listing which opt_fields questions you need answered before Session 2
6. Acknowledging the relationship to detection caching sub-initiative

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Hydration Path Discovery

Work with the @requirements-analyst agent to analyze opt_fields usage and cache integration.

**Goals:**
1. Document opt_fields used in hydration paths
2. Determine TasksClient cache key structure
3. Determine if opt_fields affects cache key
4. Identify standard field set for normalization
5. Assess detection accuracy with normalized fields
6. Recommend normalization strategy
7. Document integration with detection caching

**Files to Analyze:**
- `src/autom8_asana/models/business/hydration.py` - Opt_fields definitions
- `src/autom8_asana/clients/tasks.py` - Cache integration, default fields
- `src/autom8_asana/cache/entry.py` - Cache key structure
- `src/autom8_asana/models/business/detection/` - Detection field requirements

**Key Questions to Answer:**
- What exact opt_fields are in _DETECTION_OPT_FIELDS?
- What exact opt_fields are in _BUSINESS_FULL_OPT_FIELDS?
- What fields does TasksClient cache by default?
- Is opt_fields part of cache key?

**Deliverable:**
A discovery document with:
- Opt_fields comparison table (hydration vs TasksClient)
- Cache key structure analysis
- Normalization strategy recommendation
- Risk assessment (detection accuracy)
- Integration notes with detection caching

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Hydration Path Requirements Definition

Work with the @requirements-analyst agent to create PRD-CACHE-PERF-HYDRATION.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define opt_fields normalization requirements (FR-FIELDS-*)
2. Define cache integration requirements (FR-CACHE-*)
3. Define detection accuracy requirements (FR-DETECT-*)
4. Define Business special case requirements (FR-BUSINESS-*)
5. Define acceptance criteria for each requirement

**Key Questions to Address:**
- What is the normalized field set?
- How to handle Business custom_fields requirement?
- How to verify detection accuracy is preserved?

**PRD Organization:**
- FR-FIELDS-*: Opt_fields normalization
- FR-CACHE-*: Cache hit enablement
- FR-DETECT-*: Detection accuracy preservation
- FR-BUSINESS-*: Business special case handling
- NFR-*: Performance targets (<5ms cached)

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Hydration Path Architecture Design

Work with the @architect agent to create TDD-CACHE-PERF-HYDRATION and ADR.

**Prerequisites:**
- PRD-CACHE-PERF-HYDRATION approved

**Goals:**
1. Design opt_fields normalization approach
2. Design standard field set definition
3. Design Business full-field fetch strategy
4. Document trade-offs and alternatives
5. Coordinate with detection caching design

**Required ADRs:**
- ADR-NNNN: Hydration Opt_fields Normalization Strategy

**Architecture Options:**
- Option A: Normalize to standard field set
- Option B: Implement field subsetting in cache
- Option C: Two-phase fetch (check cache, fetch missing)

**Component Changes:**
```
src/autom8_asana/
+-- models/business/
|   +-- hydration.py          # UPDATE: Normalize opt_fields
+-- clients/
|   +-- tasks.py              # VERIFY: Default opt_fields
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Opt_fields Normalization

Work with the @principal-engineer agent to implement opt_fields normalization.

**Prerequisites:**
- PRD approved
- TDD approved
- ADR documented

**Phase 1 Scope:**
1. Define standard field set constant
2. Update _traverse_upward_async() to use standard fields
3. Update hydrate_from_gid_async() to use standard fields
4. Verify detection accuracy with new fields
5. Add unit tests for cache hit behavior

**Hard Constraints:**
- Detection accuracy must not regress
- Business custom_fields must be available for cascading
- Hydration API signature unchanged

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Cache Integration Verification

Work with the @principal-engineer agent to verify and enhance cache integration.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Verify cache hits occur on repeated traversals
2. Add hydration cache metrics
3. Add logging for cache hit/miss during traversal
4. Update documentation
5. Add integration tests for repeated traversals

**Metrics to Track:**
- Cache hits during traversal
- API calls per traversal (should decrease)
- Traversal latency (should decrease on repeat)

Create the plan first. I'll review before you execute.
```

## Session 6: Validation

```markdown
Begin Session 6: Hydration Path Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- Implementation phases complete

**Goals:**

**Part 1: Cache Hit Validation**
- Same parent GID returns cached task on repeat traversal
- Cache hit rate for repeated Business hydration >90%
- No cache misses due to opt_fields mismatch

**Part 2: Detection Accuracy Validation**
- Entity type detection with normalized fields is accurate
- Tier 1-4 detection works correctly
- No detection regressions

**Part 3: Business Fields Validation**
- Business has custom_fields populated for cascading
- Field cascading works correctly after hydration

**Part 4: Performance Validation**
- Single parent fetch (cached): <5ms
- Full traversal (5 levels, cached): <50ms
- Repeated Business hydration: <50ms

**Part 5: Failure Mode Testing**
- Cache unavailable -> Hydration works (uncached)
- Partial cache -> Correct behavior

Create the plan first. I'll review before you execute.
```

## Session 7: Integration

```markdown
Begin Session 7: Integration with Detection Caching

Work with the @qa-adversary agent to validate integration.

**Prerequisites:**
- Hydration path complete
- Detection caching sub-initiative complete (ideally)

**Goals:**
1. Verify hydration + detection caching work together
2. Measure combined performance improvement
3. Ensure no conflicting cache behavior
4. Document integration patterns

**Integration Points:**
- detect_entity_type_async() is called during _traverse_upward_async()
- Both use TasksClient cache (should not conflict)
- Detection cache + task cache = compounding benefit

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Hydration Infrastructure:**

- [ ] `src/autom8_asana/models/business/hydration.py` - Opt_fields definitions
- [ ] _DETECTION_OPT_FIELDS exact contents
- [ ] _BUSINESS_FULL_OPT_FIELDS exact contents
- [ ] _traverse_upward_async() implementation

**Client Layer:**

- [ ] `src/autom8_asana/clients/tasks.py` - Cache integration
- [ ] Default opt_fields in TasksClient
- [ ] Cache key structure

**Cache Infrastructure:**

- [ ] `src/autom8_asana/cache/entry.py` - Entry structure
- [ ] How cache key is constructed
- [ ] Whether opt_fields affects key

**Detection:**

- [ ] What fields does detection require?
- [ ] What fields does Tier 4 structure inspection need?

**Prior Work:**

- [ ] `docs/requirements/PROMPT-0-CACHE-PERF-DETECTION.md` - Related initiative
- [ ] `docs/requirements/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md` - Meta context
