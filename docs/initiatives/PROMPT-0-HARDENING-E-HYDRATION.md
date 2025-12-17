# Orchestrator Initialization: Architecture Hardening - Initiative E (Hydration Performance)

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
- **`standards`** - Tech stack decisions, code conventions, repository structure
- **`10x-workflow`** - Agent coordination, session protocol, quality gates
- **`autom8-asana-domain`** - SDK patterns, SaveSession, Asana resources
- **`autom8-asana-business-workflows`** - Workflow patterns, batch operations

**How Skills Work**: Skills load automatically based on your current task.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

---

## The Mission: Parallelize and Batch Hydration for Performance

This initiative addresses the **highest-impact performance issue**: O(n) sequential hydration making 60+ API calls for typical hierarchies. Parallelization and batching will dramatically reduce hydration latency.

### Why This Initiative?

- **Performance**: 60+ sequential API calls is unacceptable for production use
- **Scalability**: Linear scaling with hierarchy depth doesn't scale
- **User experience**: Long wait times during data loading
- **API efficiency**: Asana API supports batching, not being leveraged
- **Competitive parity**: Modern SDKs batch and parallelize by default

### Issues Addressed

| # | Issue | Description | Severity |
|---|-------|-------------|----------|
| 3 | O(n) hydration with no parallelism | 60+ API calls for typical hierarchy, no batching | High |

### Current State

**Sequential Hydration**:
- Each entity hydrated one at a time
- Parent hydrated, then children, then grandchildren...
- No parallel fetching even for independent entities
- No batching of API requests
- No request pipelining

**Typical Hierarchy**:
```
Portfolio (1 call)
  |-- Project 1 (1 call)
  |     |-- Task 1 (1 call)
  |     |-- Task 2 (1 call)
  |     |-- ...
  |-- Project 2 (1 call)
  |     |-- Task 3 (1 call)
  |     |-- ...
  ...
```

**Current Performance**:
- 60+ API calls for medium hierarchy
- Each call: ~100-300ms latency
- Total: 6-18 seconds for full hydration
- Blocks entire operation during hydration

### Target State

```
Parallel Hydration:
  - Concurrent fetches for independent entities
  - Batched API requests where possible
  - Configurable parallelism limits
  - Progress tracking/callbacks

Performance Targets:
  - Same hierarchy: <2 seconds (vs 6-18s)
  - API calls: <20 batched (vs 60+ sequential)
  - Configurable concurrency: 1-10 parallel
```

### Key Constraints

- **API rate limits**: Must respect Asana rate limits
- **Memory usage**: Don't load entire hierarchy into memory at once
- **Error handling**: Partial failure handling for batch requests
- **Backward compatibility**: Existing hydration API must continue to work
- **Configurability**: Allow tuning parallelism for different use cases

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Parallel fetching for independent entities | Must |
| Batch API requests where Asana supports | Must |
| Configurable parallelism limits | Must |
| Respect Asana rate limits | Must |
| Partial failure handling | Must |
| Progress tracking/callbacks | Should |
| Memory-efficient streaming hydration | Should |
| Maintain backward compatibility | Must |

### Success Criteria

1. Hydration performance: 60+ calls -> <20 batched requests
2. Latency reduction: 6-18s -> <2s for typical hierarchy
3. Parallel fetching for independent branches
4. Rate limit compliance (no 429 errors)
5. Partial failure reports which entities failed
6. Configurable concurrency (1-10 parallel requests)
7. Backward compatible API
8. Observability: timing metrics for hydration phases

### Dependencies

**Depends On:**
- Initiative A (Foundation) - For observability hooks (timing metrics)

**Blocks:**
- Initiative F (SaveSession) - May interact with transaction semantics

**Can Run Parallel With:**
- Initiative B (Custom Fields) - Different code areas
- Initiative C (Navigation) - Different code areas
- Initiative D (Resolution) - Different code areas

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Hydration flow analysis, API batching audit, rate limit analysis |
| **2: Requirements** | Requirements Analyst | PRD-HARDENING-E with acceptance criteria |
| **3: Architecture** | Architect | TDD-HARDENING-E + ADRs for batching strategy, parallelism |
| **4: Implementation P1** | Principal Engineer | Parallel infrastructure, batch API integration |
| **5: Implementation P2** | Principal Engineer | Entity-specific hydration, rate limiting, testing |
| **6: Validation** | QA/Adversary | Performance benchmarks, rate limit verification |

---

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Current Hydration Analysis

| Area | Questions to Answer |
|------|---------------------|
| Hydration entry points | Where does hydration start? What triggers it? |
| Entity traversal order | How is hierarchy walked? BFS? DFS? |
| API calls per entity | What API calls are made? Which can be batched? |
| Blocking points | What waits on what? Where are the bottlenecks? |

### Asana API Batching Analysis

| Endpoint | Questions to Answer |
|----------|---------------------|
| Task batch | Does Asana support batch task fetch? How? |
| Project batch | Does Asana support batch project fetch? |
| Custom field batch | Can custom fields be batched? |
| Rate limits | What are Asana's rate limits? Headers? |

### Parallelism Opportunities

| Opportunity | Questions to Answer |
|-------------|---------------------|
| Sibling entities | Can siblings be fetched in parallel? |
| Different types | Can tasks and projects be fetched in parallel? |
| Hierarchy levels | Can Level N+1 start while N is completing? |
| Pre-fetching | Can we predict and pre-fetch? |

### Error Handling

| Scenario | Questions to Answer |
|----------|---------------------|
| Partial batch failure | What if 3 of 10 batch items fail? |
| Rate limit hit | How to back off and retry? |
| Network timeout | How to handle timeout mid-hydration? |
| Entity not found | What if referenced entity is deleted? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins:

### Parallelism Questions

1. **Concurrency model**: asyncio.gather? TaskGroup? Semaphore-limited?
2. **Default parallelism**: What's a safe default? 5? 10?
3. **Backpressure**: How to handle slow consumers?
4. **Cancellation**: Can hydration be cancelled mid-way?

### Batching Questions

5. **Batch size**: What's optimal batch size? 10? 25? 50?
6. **Batch composition**: Batch by entity type? By parent? Mixed?
7. **Asana batch endpoint**: Does `/batch` work for reads? Just writes?
8. **Alternative batching**: Can we use `opt_fields` expansion instead?

### Rate Limiting Questions

9. **Rate limit detection**: How to detect approaching limit?
10. **Backoff strategy**: Exponential? Fixed? Adaptive?
11. **Rate limit budget**: How to allocate across parallel requests?
12. **Circuit breaker**: Should we use circuit breaker pattern?

---

## Your First Task

Confirm understanding by:

1. Summarizing the Hydration Performance goal in 2-3 sentences
2. Listing the 6 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which code areas and APIs must be analyzed
5. Listing which open questions you need answered before Session 2
6. Acknowledging this initiative depends on A and can run parallel with B, C, D

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

## Session Trigger Prompts

### Session 1: Discovery

```markdown
Begin Session 1: Hydration Performance Discovery

Work with the @requirements-analyst agent to analyze current hydration and API capabilities.

**Goals:**
1. Document current hydration flow and bottlenecks
2. Identify Asana API batching capabilities
3. Map parallelism opportunities
4. Document rate limit constraints
5. Catalog error handling requirements

**Areas to Analyze:**
- Hydration entry points and flow
- API call patterns during hydration
- Asana API documentation for batching
- Rate limit headers and behavior
- Existing TDD-HYDRATION and PRD-HYDRATION

**Deliverable:**
A discovery document with:
- Current hydration flow diagram
- API batching capability matrix
- Parallelism opportunity map
- Rate limit constraints
- Recommended strategy

Create the analysis plan first. I'll review before you execute.
```

### Session 2: Requirements

```markdown
Begin Session 2: Hydration Performance Requirements

Work with the @requirements-analyst agent to create PRD-HARDENING-E.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define parallelism requirements
2. Define batching requirements
3. Define rate limit handling requirements
4. Define performance targets
5. Define acceptance criteria for each

**Key Questions to Address:**
- What parallelism model to use?
- What batch sizes are optimal?
- How to handle rate limits?
- What are the performance targets?

Create the plan first. I'll review before you execute.
```

### Session 3: Architecture

```markdown
Begin Session 3: Hydration Performance Architecture

Work with the @architect agent to create TDD-HARDENING-E and required ADRs.

**Prerequisites:**
- PRD-HARDENING-E approved

**Goals:**
1. Design parallel hydration infrastructure
2. Design batch API integration
3. Design rate limit management
4. Design progress tracking

**Required ADRs:**
- ADR: Parallel Hydration Strategy
- ADR: Rate Limit Management
- ADR: Batch Request Composition

Create the plan first. I'll review before you execute.
```

### Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Parallel Infrastructure

Work with the @principal-engineer agent to implement parallel infrastructure.

**Prerequisites:**
- PRD-HARDENING-E approved
- TDD-HARDENING-E approved
- ADRs documented

**Phase 1 Scope:**
1. Implement parallel execution infrastructure
2. Implement rate limit manager
3. Implement batch request builder
4. Unit tests for infrastructure

**Explicitly OUT of Phase 1:**
- Entity-specific hydration changes (Phase 2)
- Integration with existing hydration (Phase 2)
- Performance benchmarks (Phase 2)

Create the plan first. I'll review before you execute.
```

### Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Hydration Integration

Work with the @principal-engineer agent to integrate with hydration.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Integrate parallel infrastructure with hydration
2. Implement entity-specific optimizations
3. Add progress tracking
4. Integration tests
5. Performance benchmarks

Create the plan first. I'll review before you execute.
```

### Session 6: Validation

```markdown
Begin Session 6: Hydration Performance Validation

Work with the @qa-adversary agent to validate performance improvements.

**Prerequisites:**
- All implementation complete

**Goals:**

**Part 1: Performance Validation**
- Benchmark: before vs after (60+ -> <20 calls)
- Benchmark: latency improvement (6-18s -> <2s)
- Benchmark: various hierarchy sizes

**Part 2: Reliability Validation**
- Verify rate limit compliance (no 429s)
- Test partial failure handling
- Test cancellation behavior

**Part 3: Backward Compatibility**
- Verify existing hydration API works
- Verify no regressions

Create the plan first. I'll review before you execute.
```

---

## Context Gathering Checklist

Before starting, gather:

**Codebase:**
- [ ] Current hydration implementation
- [ ] API client implementation
- [ ] Batch API implementation (if exists)
- [ ] Rate limit handling (if exists)

**Documentation:**
- [ ] TDD-HYDRATION
- [ ] PRD-HYDRATION
- [ ] ADR-0069 (Hydration API Design)
- [ ] ADR-0070 (Hydration Partial Failure)
- [ ] Asana API documentation for batching

**Performance Data:**
- [ ] Current hydration timings (if available)
- [ ] Asana rate limit specifications

---

## Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Meta Prompt -1 | `/docs/initiatives/PROMPT-MINUS-1-ARCHITECTURE-HARDENING.md` | Parent initiative |
| TDD-HYDRATION | `/docs/design/TDD-HYDRATION.md` | Existing hydration design |
| PRD-HYDRATION | `/docs/requirements/PRD-HYDRATION.md` | Hydration requirements |
| ADR-0069 | `/docs/decisions/ADR-0069-hydration-api-design.md` | API design |
| ADR-0070 | `/docs/decisions/ADR-0070-hydration-partial-failure.md` | Partial failure |
| Batch Skill | `.claude/skills/autom8-asana-business-workflows/batch-operation-patterns.md` | Batch patterns |

---

*This is Initiative E of the Architecture Hardening Sprint. It depends on Initiative A. Can run in parallel with Initiatives B, C, and D.*
