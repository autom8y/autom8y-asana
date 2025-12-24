# ADR-0118: Rejection of Multi-Level Cache Hierarchy

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: Architect, Principal Engineer, Requirements Analyst
- **Related**: PRD-WATERMARK-CACHE, TDD-WATERMARK-CACHE, ADR-0021 (DataFrame Caching Strategy), ADR-0026 (Two-Tier Cache Architecture)

---

## Context

During the Watermark Cache initiative exploration phase (Prompt 0 and Discovery), we evaluated whether a multi-level cache hierarchy would improve DataFrame performance. The proposed hierarchy was:

```
Level 3: Project-level cache
    |
Level 2: Section-level cache
    |
Level 1: Task-level cache (current)
```

The hypothesis was that higher-level caches could:
- Serve project-wide requests from a single cache entry
- Reduce cache key count
- Simplify invalidation

This ADR documents why this approach was **explicitly rejected**.

**Forces at play**:
- Write frequency: ~10 writes/hour per project (from operational workflows)
- Read patterns: Multiple DataFrame extractions per analysis session
- Task mobility: Tasks can move between sections/projects
- Asana API limitations: No `modified_at` on sections or aggregates
- Cache thrashing under write-heavy patterns

---

## Decision

We will **not implement** a multi-level cache hierarchy. We will continue using **single-level per-task caching** with project context keys (`{task_gid}:{project_gid}`) as defined in ADR-0021.

The multi-level cache was rejected for the following reasons:

1. **Section-level cache is unviable**: Sections have no `modified_at` field - staleness detection is impossible
2. **Project-level cache thrashes**: With 10 writes/hour, cache never warms (invalidated every 6 minutes on average)
3. **"Ghost reference problem"**: Tasks moving between sections/projects leave stale references
4. **Complexity outweighs benefit**: Coordination between levels adds failure modes without performance gain

---

## Rationale

### Section-Level Cache: No Staleness Detection

Sections in Asana are containers for tasks, but they have no modification tracking:

```json
{
  "gid": "1234567890",
  "name": "In Progress",
  "resource_type": "section"
  // NO modified_at field
}
```

Without `modified_at`, we cannot detect when a section's contents have changed. Any of these events invalidate section cache:
- Task added to section
- Task removed from section
- Task modified within section

Without change detection, we would need to either:
- **Always invalidate**: Defeats caching purpose
- **TTL-only**: Arbitrary staleness window
- **API poll**: Additional requests negate benefit

None of these options provide reliable caching semantics.

### Project-Level Cache: Cache Thrashing

Cache thrashing analysis for typical project (3,500 tasks, 10 writes/hour):

| Metric | Value |
|--------|-------|
| Average write interval | 6 minutes |
| Cache TTL | 5 minutes |
| Write-driven invalidations | 10/hour |
| Time to next write (average) | 6 minutes |
| **Probability cache is warm when read** | <50% |

With 10 writes/hour affecting the same project, any project-level cache entry has <6 minutes before invalidation. Combined with 5-minute TTL, the cache effectively never warms.

**Contrast with per-task cache**: Individual task modifications only invalidate that task's entry. The other 3,499 tasks remain cached. Project-level cache invalidates all 3,500 entries on any change.

### Ghost Reference Problem

When a task moves between sections or projects:

```
Time T0: Task T1 in Section S1, Project P1
         Cache: S1_cache contains T1, P1_cache contains T1

Time T1: Task T1 moved to Section S2 (still in P1)
         - S1 cache now has "ghost" reference to T1
         - S2 cache missing T1
         - No event notification to cache layer

Time T2: Task T1 moved to Project P2
         - P1_cache has ghost reference
         - P2_cache missing T1
```

Detecting and handling these ghost references requires:
- Tracking all task memberships in cache metadata
- Scanning/invalidating on membership changes
- Complex reconciliation logic

This complexity is disproportionate to benefit.

### The Insight: Fetch Strategy, Not Cache Architecture

The core discovery:

> **"The cache is already right. The fetch is wrong."**

The 52-second latency is not caused by cache misses - it's caused by **serial paginated API fetching**. With parallel section fetch:
- Cold start: 52s -> ~8s (parallel API calls)
- Warm cache: ~8s -> <1s (cache hits skip API)

A per-task cache with parallel fetch achieves the performance target. Multi-level cache adds complexity without addressing the root cause.

---

## Alternatives Considered

### Alternative 1: Section-Level Cache with TTL-Only Freshness

- **Description**: Cache section task lists with fixed TTL, no staleness detection
- **Pros**: Could serve section-filtered queries
- **Cons**:
  - No change detection - arbitrary staleness
  - TTL too short = useless; too long = stale data
  - Invalidation on any task change in section
- **Why not chosen**: Unreliable freshness semantics

### Alternative 2: Project-Level Cache with Write-Through

- **Description**: Cache entire project DataFrame, invalidate on any project write
- **Pros**: Single cache entry per project; simple lookup
- **Cons**:
  - Cache thrashing (10 writes/hour)
  - All-or-nothing invalidation
  - Large cache entries (3,500 tasks)
- **Why not chosen**: Cache thrashing makes this net-negative

### Alternative 3: Hierarchical Cache with Dependency Tracking

- **Description**: Full hierarchy with explicit dependency graph between levels
- **Pros**: Theoretically optimal if dependencies tracked perfectly
- **Cons**:
  - Massive implementation complexity
  - Dependency graph maintenance overhead
  - Still vulnerable to ghost references
  - Over-engineering for the problem at hand
- **Why not chosen**: Complexity vastly exceeds benefit

### Alternative 4: Search API for Incremental Updates

- **Description**: Use Search API with `modified_since` to fetch only changed tasks
- **Pros**: Could reduce fetch scope significantly
- **Cons**:
  - Premium API only (limits adoption)
  - 100 item limit per query
  - Cannot detect removals (deleted/moved tasks)
  - Search API has separate rate limits
- **Why not chosen**: API limitations make this unreliable for enumeration

---

## Consequences

### Positive

- **Simplicity**: Single cache level with clear semantics
- **Correct by design**: No ghost references or stale aggregates
- **Granular invalidation**: Task change only affects that task's entries
- **Proven pattern**: Per-entity caching is well-understood
- **Performance achieved**: Parallel fetch + per-task cache meets targets

### Negative

- **No aggregate optimization**: Cannot serve "all project tasks" from single entry
- **More cache entries**: 3,500 entries per project vs 1
- **More cache keys**: Key enumeration needed for batch operations

### Neutral

- **TTL still applies**: External changes rely on 5-minute TTL
- **Storage proportional to task count**: Linear in task count, not project count

---

## Compliance

This is a **negative decision** (what NOT to build). Compliance means:

1. **No section-level cache entries**: Code review should reject `EntryType.SECTION` or similar
2. **No project-level cache entries**: No aggregated DataFrame caching by project
3. **Per-task key format**: Keys must be `{task_gid}:{project_gid}` per ADR-0021
4. **Documentation**: Reference this ADR when multi-level caching is proposed

---

## Appendix: Exploration Evidence

This decision was informed by the Discovery Analysis (`/docs/analysis/watermark-cache-discovery.md`) and Prompt 0 (`/docs/requirements/PROMPT-0-WATERMARK-CACHE.md`), which documented:

1. **Section API lacks `modified_at`**: Confirmed via API inspection
2. **Write frequency analysis**: Operational logs showed ~10 writes/hour
3. **Cache hit rate projection**: Modeled project-level cache efficacy
4. **Multi-level architecture review**: Analyzed existing TieredCacheProvider (Redis+S3) - this is storage tiers, not semantic levels
5. **Performance root cause**: Identified serial pagination as the bottleneck

The exploration explicitly called out multi-level cache as "over-engineering" in the "What NOT to Build" section.
