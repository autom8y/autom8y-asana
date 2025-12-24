# Orchestrator Initialization: Cache Performance - Stories Incremental Loading Wiring

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

## The Mission: Wire Stories Client to Use Existing Incremental Cache Loader

The `cache/stories.py` module has a complete implementation of `load_stories_incremental()` that supports caching with the Asana `since` parameter for incremental fetching. However, `StoriesClient` (or equivalent) does not use this infrastructure, causing stories to be fetched fresh each time.

### Why This Initiative?

- **Infrastructure Exists**: `load_stories_incremental()` is fully implemented
- **Simple Wiring**: Just need to connect client to loader
- **Incremental Benefit**: Asana `since` parameter reduces API response size
- **Cache Benefit**: Previously fetched stories are merged, not re-fetched

### Current State

**Stories Cache Infrastructure (from `cache/stories.py`)**:

```python
async def load_stories_incremental(
    task_gid: str,
    cache: CacheProvider,
    fetcher: Callable[[str, str | None], Awaitable[list[dict[str, Any]]]],
    current_modified_at: str | None = None,
) -> tuple[list[dict[str, Any]], CacheEntry | None, bool]:
    """Load stories with incremental fetching (since parameter).

    Per ADR-0020:
    - Get cached stories and their last_fetched timestamp
    - Fetch only stories since last_fetched (using Asana 'since' parameter)
    - Merge new stories with cached (dedupe by story GID)
    - Update cache with merged result

    Returns:
        Tuple of (merged_stories, cache_entry, was_incremental_fetch).
    """
```

**Key Features Already Implemented**:
- `EntryType.STORIES` exists in cache entry types
- Incremental fetch using Asana `since` parameter
- Story merging with deduplication by GID
- Cache entry with `last_fetched` metadata
- `filter_relevant_stories()` for struc computation
- `get_latest_story_timestamp()` for tracking

**The Problem**:
- `StoriesClient.list_for_task_async()` (or equivalent) fetches stories directly
- Does NOT call `load_stories_incremental()`
- Stories are fetched fresh each time, ignoring cache
- `since` parameter is not utilized

### Target Architecture

```
Current Flow:
  client.stories.list_for_task_async(task_gid)
    --> API call: GET /tasks/{gid}/stories
    --> Returns ALL stories (could be hundreds)
    --> No caching

Desired Flow:
  client.stories.list_for_task_async(task_gid)
    --> load_stories_incremental(task_gid, cache, fetcher)
    --> Check cache for previous stories
    --> API call: GET /tasks/{gid}/stories?since={last_fetched}
    --> Returns ONLY new stories since last fetch
    --> Merge with cached, update cache
    --> Return merged stories
```

### Key Constraints

- **API Compatibility**: Client API signature should not change
- **Cache Provider**: Must use injected cache provider
- **Asana since Parameter**: Use Asana's native incremental parameter
- **Story Deduplication**: Merge must handle duplicate story GIDs
- **Graceful Degradation**: Cache failure should not break story fetch

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Wire StoriesClient to use load_stories_incremental | Must |
| Support `since` parameter for incremental fetch | Must |
| Merge cached stories with new stories | Must |
| Expose was_incremental_fetch in response | Should |
| Add stories cache metrics | Should |
| Document incremental loading pattern | Should |

### Success Criteria

1. **Incremental Fetch Works**: Second story fetch uses `since` parameter
2. **Cache Integration**: Stories are cached with `last_fetched` metadata
3. **Merge Correctness**: New stories merged with cached correctly
4. **Performance Improvement**: Repeat story fetches are faster
5. **No API Regression**: First fetch works identically

### Performance Targets

| Scenario | Current | Target |
|----------|---------|--------|
| First story fetch (full) | ~500ms | ~500ms (expected) |
| Second story fetch (incremental) | ~500ms | <100ms (fewer stories) |
| Cached stories merge | N/A | <10ms |
| Story cache hit rate | 0% | >90% (incremental) |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | StoriesClient analysis, integration points for incremental loader |
| **2: Requirements** | Requirements Analyst | PRD-CACHE-PERF-STORIES with acceptance criteria |
| **3: Architecture** | Architect | TDD-CACHE-PERF-STORIES + ADR for stories cache wiring |
| **4: Implementation P1** | Principal Engineer | Wire StoriesClient to load_stories_incremental |
| **5: Implementation P2** | Principal Engineer | Metrics, logging, documentation |
| **6: Validation** | QA/Adversary | Incremental fetch verification, merge correctness |
| **7: Integration** | QA/Adversary | Integration with struc computation, DataFrame paths |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Stories Infrastructure Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `cache/stories.py` | Full understanding of load_stories_incremental() |
| `clients/stories.py` | Does StoriesClient exist? What methods? |
| `clients/base.py` | How do other clients integrate with cache? |

### Integration Points

| Component | Questions |
|-----------|-----------|
| StoriesClient | Where to inject load_stories_incremental call? |
| Cache provider | How to get cache provider in client? |
| Fetcher function | How to create fetcher compatible with loader? |

### Struc Computation Analysis

| Area | Questions |
|------|-----------|
| Where are stories used? | DataFrame extraction? Struc computation? |
| filter_relevant_stories() | Is this used? Should client use it? |
| Story types needed | Which resource_subtypes are relevant? |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Client Structure Questions

1. **Does StoriesClient exist?**: Or is it inline in TasksClient?
2. **Where is list_for_task_async?**: What is the current implementation?
3. **How to inject cache provider?**: Client constructor? Method parameter?

### Integration Questions

4. **Fetcher function signature?**: How to adapt client fetch to loader signature?
5. **current_modified_at source?**: Where to get task.modified_at for versioning?
6. **Cache provider access?**: How do clients access the cache provider?

### Behavior Questions

7. **Return type change?**: Should client return was_incremental_fetch?
8. **Filter stories in client?**: Or return all and let caller filter?
9. **Error handling?**: What if incremental fetch fails?

## Your First Task

Confirm understanding by:

1. Summarizing the Stories Cache Wiring goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which files must be analyzed (cache/stories.py, clients/)
5. Listing which client structure questions you need answered before Session 2
6. Acknowledging that the infrastructure exists - this is a wiring task

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Stories Cache Wiring Discovery

Work with the @requirements-analyst agent to analyze story fetching and identify integration points.

**Goals:**
1. Locate current story fetching code (StoriesClient or inline)
2. Understand load_stories_incremental() interface
3. Determine how to inject cache provider
4. Determine how to create compatible fetcher function
5. Identify where stories are consumed (struc computation?)
6. Document integration approach
7. Estimate performance improvement

**Files to Analyze:**
- `src/autom8_asana/cache/stories.py` - Incremental loader (understand fully)
- `src/autom8_asana/clients/` - Find story fetching code
- `src/autom8_asana/dataframes/` - Where are stories consumed?

**Key Questions to Answer:**
- Where is story fetching currently implemented?
- How do other clients integrate with cache?
- What is the fetcher function signature required by loader?
- How to get current_modified_at for versioning?

**Deliverable:**
A discovery document with:
- Current story fetch flow (without cache)
- Proposed integration flow (with incremental cache)
- Fetcher function design
- Cache provider injection approach
- Risk assessment

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Stories Cache Wiring Requirements Definition

Work with the @requirements-analyst agent to create PRD-CACHE-PERF-STORIES.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define client integration requirements (FR-CLIENT-*)
2. Define incremental fetch requirements (FR-INCR-*)
3. Define cache population requirements (FR-CACHE-*)
4. Define merge behavior requirements (FR-MERGE-*)
5. Define acceptance criteria for each requirement

**Key Questions to Address:**
- Where exactly is integration point?
- How is fetcher function created?
- What is return type (include was_incremental_fetch?)
- How to handle errors?

**PRD Organization:**
- FR-CLIENT-*: Client method integration
- FR-INCR-*: Incremental fetch behavior
- FR-CACHE-*: Cache population and lookup
- FR-MERGE-*: Story merging behavior
- NFR-*: Performance targets (<100ms incremental)

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Stories Cache Wiring Architecture Design

Work with the @architect agent to create TDD-CACHE-PERF-STORIES and ADR.

**Prerequisites:**
- PRD-CACHE-PERF-STORIES approved

**Goals:**
1. Design client integration with incremental loader
2. Design fetcher function adapter
3. Design cache provider injection
4. Design return type (include metadata?)
5. Document alternatives and trade-offs

**Required ADRs:**
- ADR-NNNN: Stories Client Cache Integration Pattern

**Component Changes:**
```
src/autom8_asana/
+-- clients/
|   +-- stories.py (or tasks.py)  # UPDATE: Wire to incremental loader
+-- cache/
|   +-- stories.py                # EXISTING: No changes needed
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Client Integration

Work with the @principal-engineer agent to wire client to incremental loader.

**Prerequisites:**
- PRD approved
- TDD approved
- ADR documented

**Phase 1 Scope:**
1. Create fetcher function adapter for API calls
2. Wire client method to call load_stories_incremental
3. Inject cache provider into client
4. Handle current_modified_at versioning
5. Add unit tests for incremental behavior

**Hard Constraints:**
- Client API signature should not break
- Cache failures must not break story fetch
- Incremental must use Asana `since` parameter

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Observability & Polish

Work with the @principal-engineer agent to add observability and documentation.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Add stories cache metrics (incremental vs full fetches)
2. Add logging for cache hit/miss
3. Expose was_incremental_fetch in response (optional)
4. Update documentation
5. Add integration tests for incremental behavior

**Metrics to Track:**
- Full fetches vs incremental fetches
- Stories returned per fetch (should decrease)
- Cache hits on story lookup

Create the plan first. I'll review before you execute.
```

## Session 6: Validation

```markdown
Begin Session 6: Stories Cache Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- Implementation phases complete

**Goals:**

**Part 1: Incremental Fetch Validation**
- First fetch is full (no `since` parameter)
- Second fetch is incremental (uses `since` parameter)
- `since` parameter contains last_fetched timestamp

**Part 2: Merge Validation**
- New stories are added to cached
- Duplicate story GIDs are deduplicated
- Stories sorted by created_at

**Part 3: Performance Validation**
- Second fetch faster than first (fewer stories)
- Cached merge is fast (<10ms)
- Overall story fetch time reduced

**Part 4: Failure Mode Testing**
- Cache unavailable -> Full fetch works
- Incremental fetch fails -> Fallback to full
- Corrupted cache -> Fresh fetch

**Part 5: Correctness Validation**
- All stories returned (no data loss)
- Story order is correct
- Resource subtypes preserved

Create the plan first. I'll review before you execute.
```

## Session 7: Integration

```markdown
Begin Session 7: Integration with Struc Computation

Work with the @qa-adversary agent to validate integration.

**Prerequisites:**
- Stories cache wiring complete

**Goals:**
1. Verify stories cache improves struc computation
2. Verify filter_relevant_stories() integration
3. Verify DataFrame extraction with cached stories
4. Document integration patterns

**Integration Points:**
- Struc computation uses stories for history
- filter_relevant_stories() filters to relevant types
- DEFAULT_STORY_TYPES defines relevant resource_subtypes

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Stories Infrastructure:**

- [ ] `src/autom8_asana/cache/stories.py` - Full understanding
- [ ] load_stories_incremental() signature and behavior
- [ ] filter_relevant_stories() and DEFAULT_STORY_TYPES
- [ ] _create_stories_entry() cache entry structure

**Client Layer:**

- [ ] Where is story fetching currently?
- [ ] StoriesClient or inline in TasksClient?
- [ ] How do other clients integrate cache?

**Consumers:**

- [ ] Where are stories consumed?
- [ ] Struc computation?
- [ ] DataFrame extraction?

**Prior Work:**

- [ ] ADR-0020 (referenced in stories.py comments)
- [ ] ADR-0021 (struc computation story types)
- [ ] `docs/requirements/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md` - Meta context

---

# Appendix: Stories Cache Infrastructure Summary

## load_stories_incremental() Signature

```python
async def load_stories_incremental(
    task_gid: str,
    cache: CacheProvider,
    fetcher: Callable[[str, str | None], Awaitable[list[dict[str, Any]]]],
    current_modified_at: str | None = None,
) -> tuple[list[dict[str, Any]], CacheEntry | None, bool]:
    """
    Args:
        task_gid: The task GID.
        cache: Cache provider.
        fetcher: Async function(task_gid, since) -> list[story_dicts].
            since is ISO timestamp or None for full fetch.
        current_modified_at: Current task modified_at for cache versioning.

    Returns:
        Tuple of (merged_stories, cache_entry, was_incremental_fetch).
    """
```

## Key Helper Functions

| Function | Purpose |
|----------|---------|
| `_create_stories_entry()` | Create CacheEntry with last_fetched metadata |
| `_extract_stories_list()` | Extract stories from cache entry data |
| `_merge_stories()` | Merge existing + new, dedupe by GID, sort by created_at |
| `filter_relevant_stories()` | Filter to struc-relevant resource_subtypes |
| `get_latest_story_timestamp()` | Get latest created_at for next `since` |

## DEFAULT_STORY_TYPES (Struc-Relevant)

```python
DEFAULT_STORY_TYPES = [
    "assignee_changed",
    "due_date_changed",
    "section_changed",
    "added_to_project",
    "removed_from_project",
    "marked_complete",
    "marked_incomplete",
    "enum_custom_field_changed",
    "number_custom_field_changed",
]
```
