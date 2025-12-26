# ADR-0115: Parallel Section Fetch Strategy

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-WATERMARK-CACHE, TDD-WATERMARK-CACHE, ADR-0021 (DataFrame Caching Strategy)

---

## Context

Project-level DataFrame extraction currently takes 52-59 seconds for a typical project with 3,500+ tasks. This latency is caused by **serial paginated API fetching** - the SDK fetches tasks page-by-page (100 tasks per page, ~35 pages) sequentially.

Asana projects organize tasks into sections. The Asana API supports fetching tasks by section (`GET /sections/{gid}/tasks`), which enables parallel fetching of tasks across sections.

We need to choose a parallelization strategy that:
1. Reduces cold-start latency from 52s to <10s
2. Respects Asana API rate limits (1500 requests/60s)
3. Handles failure gracefully
4. Is backward compatible with existing code

**Forces at play**:
- Asana rate limit: 1500 requests per minute (25 req/s)
- Typical project: 8-12 sections
- Parallel requests multiply rate consumption
- Network latency dominates fetch time
- Sections can be empty
- Tasks can be "multi-homed" (appear in multiple sections)

---

## Decision

We will implement **section-parallel fetch with semaphore control**:

1. Enumerate all sections in the project via `SectionsClient.list_for_project_async()`
2. Fetch tasks from each section concurrently using `asyncio.gather()`
3. Limit concurrent in-flight requests using `asyncio.Semaphore(max_concurrent)` with default of 8
4. Deduplicate results by task GID (handles multi-homed tasks)
5. Fall back to serial project-level fetch on any parallel fetch failure

```python
# Conceptual implementation
sections = await sections_client.list_for_project_async(project_gid).collect()
semaphore = asyncio.Semaphore(8)

async def fetch_section(section_gid):
    async with semaphore:
        return await tasks_client.list_async(section=section_gid).collect()

results = await asyncio.gather(*[fetch_section(s.gid) for s in sections], return_exceptions=True)

# Check for exceptions, fallback if any
if any(isinstance(r, Exception) for r in results):
    # Log warning and fall back to serial
    tasks = await tasks_client.list_async(project=project_gid).collect()
else:
    tasks = deduplicate_by_gid(flatten(results))
```

---

## Rationale

**Why section-parallel over page-parallel?**

| Approach | Pros | Cons |
|----------|------|------|
| **Section-parallel** | Natural parallelization unit; each section independent; simple coordination | Requires section enumeration call; doesn't parallelize large sections |
| Page-parallel | Could parallelize within large sections | Complex offset coordination; depends on knowing total count upfront; race conditions |
| Task-level parallel | Maximum parallelism | Excessive API calls; rate limit exhaustion; no efficiency gain |

Section-parallel is the **right abstraction level**: sections are independent, the API supports section-scoped fetching, and typical projects have 8-12 sections which provides sufficient parallelism.

**Why semaphore with default 8?**

- Asana rate limit: 1500 req/60s = 25 req/s
- With 8 concurrent requests and ~500ms per request: 16 req/s (safe margin)
- Typical project has 8-12 sections, so 8 concurrent covers most projects in single batch
- Higher values (16, 20) risk rate limit exhaustion with multiple consumers

**Why fail-all with fallback?**

Partial results from sections are dangerous - missing a section means missing tasks. Instead of returning incomplete data, we:
1. Fail the entire parallel fetch
2. Automatically fall back to serial project-level fetch (current behavior)
3. Log a warning for observability

This ensures correctness over performance - users always get complete data.

---

## Alternatives Considered

### Alternative 1: Page-Parallel Fetch

- **Description**: Parallelize pagination within a single project query by predicting page offsets
- **Pros**: Could parallelize even single-section projects
- **Cons**:
  - Requires knowing total task count upfront (additional API call)
  - Page boundaries may shift during parallel fetch
  - Complex offset coordination
- **Why not chosen**: Too complex; section-parallel achieves 80% of benefit with 20% of complexity

### Alternative 2: No Parallelization (Optimize Serial)

- **Description**: Keep serial fetch, optimize page size, reduce opt_fields
- **Pros**: No coordination complexity; no rate limit risk
- **Cons**:
  - Still O(pages) latency
  - Cannot achieve <10s target for 3,500 tasks
- **Why not chosen**: Cannot meet performance requirements

### Alternative 3: Search API with Parallel Batch

- **Description**: Use Search API to find modified tasks, then batch fetch
- **Pros**: Could reduce fetch scope with `modified_since`
- **Cons**:
  - Premium API only
  - 100 item limit per query
  - Cannot detect removed/moved tasks
- **Why not chosen**: Premium-only; cannot reliably enumerate project tasks

### Alternative 4: Background Pre-Fetch

- **Description**: Background process continuously fetches and caches
- **Pros**: Consumer sees instant response from warm cache
- **Cons**:
  - Requires background infrastructure
  - Constant API usage even when idle
  - Complex freshness management
- **Why not chosen**: Over-engineering; parallel fetch achieves target without background processes

---

## Consequences

### Positive

- **80% latency reduction**: 52s to ~8s for typical 3,500-task project
- **Rate-limit safe**: 8 concurrent with semaphore stays well under limits
- **Graceful degradation**: Automatic fallback preserves correctness
- **No external dependencies**: Uses existing asyncio primitives
- **Backward compatible**: New `build_async()` method; existing `build()` unchanged

### Negative

- **Additional API call**: Section enumeration adds 1 API call
- **Increased complexity**: More error handling paths (parallel failures)
- **Memory overhead**: Holding tasks from all sections before merging
- **Not optimal for single-section projects**: No parallelism benefit

### Neutral

- **Async-only**: Parallel fetch only available via `build_async()` (sync `build()` unchanged)
- **Configuration surface**: New `max_concurrent_sections` config option

---

## Compliance

To ensure this decision is followed:

1. **Code Review**: Verify `asyncio.gather()` with `return_exceptions=True` is used
2. **Semaphore Usage**: Verify semaphore wraps all section fetches
3. **Fallback Path**: Verify exception handling triggers serial fallback
4. **Unit Tests**: Test parallel fetch, fallback, and deduplication
5. **Performance Tests**: Benchmark cold-start latency in CI
