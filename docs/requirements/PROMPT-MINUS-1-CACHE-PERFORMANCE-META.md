# Prompt -1: Initiative Scoping - Cache Performance Gap Closure Meta-Initiative

> **Purpose**: Validate readiness for the 4-agent workflow. Answer: "Do we know enough to write Prompt 0 for each sub-initiative?"

---

## Initiative Summary

**One-liner**: Close the cache performance gap from 1.2x to 10x speedup through targeted fixes to the four identified hot paths that bypass caching.

**Sponsor**: SDK Performance Team

**Triggered by**: Observed performance regression despite completing Watermark Cache Performance and Cache Utilization initiatives - second fetch still takes 11.56s instead of <1s.

---

## The Performance Gap

```
First fetch (cache miss):   13.55s
Second fetch (cache hit):   11.56s  <-- Only 1.2x faster

Expected with working cache:
First fetch (cache miss):   13.55s
Second fetch (cache hit):   <1.0s   <-- 10x+ faster
```

**Root Cause Analysis Summary**:

| Gap | Impact | Evidence |
|-----|--------|----------|
| Detection results NOT cached | High (P1) | `detect_entity_type_async()` makes Tier 4 API calls repeatedly; results discarded |
| Hydration uses custom opt_fields | Medium (P2) | `_traverse_upward_async()` uses `_DETECTION_OPT_FIELDS` which bypass client cache |
| DataFrame fetch path not hitting cache | High (P1) | ParallelSectionFetcher populates tasks but subsequent calls re-fetch |
| Stories incremental loader not wired | High (P1) | `cache/stories.py` has infrastructure; `StoriesClient` does not use it |

---

## Pre-Flight Checklist

### 1. Problem Validation

| Question | Answer | Confidence |
|----------|--------|------------|
| Is there a real problem? | Yes - 11.56s second fetch proves cache bypass | High |
| Who experiences it? | All SDK consumers using DataFrame extraction | High |
| What's the cost of not solving? | Wasted API calls, poor UX, unnecessary Asana API load | High |
| Is this the right time? | Yes - cache infrastructure is mature, only wiring is missing | High |

**Problem Statement Draft**:
> The autom8_asana SDK has comprehensive caching infrastructure that is not being utilized on the hot paths. Despite two major caching initiatives, the observed speedup is only 1.2x (11.56s vs 13.55s) when it should be 10x+ (<1s cached). Four specific code paths bypass caching: detection results, hydration traversal, DataFrame fetch, and stories loading.

### 2. Scope Boundaries

| Dimension | In Scope | Out of Scope | Decision Rationale |
|-----------|----------|--------------|-------------------|
| **Cache Infrastructure** | Wiring existing infrastructure to hot paths | New cache backends, new TTL strategies | Infrastructure is mature per prior initiatives |
| **Entry Types** | Add DETECTION entry type; verify existing types | Multi-level hierarchy, aggregate caching | Per ADR decisions from prior work |
| **Clients** | TasksClient, StoriesClient integration | ProjectsClient, SectionsClient (already done) | Focus on gaps causing 1.2x |
| **Hydration** | opt_fields normalization for cache hits | Hydration algorithm changes | Algorithm is correct; only cache wiring is wrong |

### 3. Complexity Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| **Scope** | Module | Four targeted changes to existing modules |
| **Technical Risk** | Medium | Changes touch hot paths; need careful testing |
| **Integration Points** | Medium | Detection, hydration, DataFrame, stories - all interconnected |
| **Team Familiarity** | High | Prior initiatives documented architecture thoroughly |
| **Unknowns** | Low | Root causes identified; fixes are clear |

**Recommended Complexity Level**: Module

**Workflow Recommendation**: 4 parallel sub-initiatives (can be executed independently)

**Rationale**: Each gap is in a distinct code area. Sub-initiatives can proceed in parallel but should share common validation criteria.

### 4. Dependencies & Blockers

| Dependency | Status | Owner | Blocking? |
|------------|--------|-------|-----------|
| Watermark Cache Performance initiative | Done | SDK Team | No |
| Cache Utilization initiative | Done | SDK Team | No |
| EntryType enum extensibility | Done | cache/entry.py | No |
| Incremental stories loader | Done | cache/stories.py | No (exists, not wired) |

**Blockers**: None identified

### 5. Success Definition (Draft)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Second fetch latency (3500 tasks) | 11.56s | <1.0s | Benchmark script |
| Cache hit rate on warm | ~10% (estimated) | >90% | CacheMetrics |
| Detection cache hits | 0% | 100% (same GID) | New metric |
| Stories incremental fetch | N/A | <10ms for cached | Benchmark |

### 6. Rough Effort Estimate

| Phase | Effort | Confidence |
|-------|--------|------------|
| Discovery / Requirements | 1-2 sessions per sub-initiative | High |
| Architecture / Design | 1 session per sub-initiative | High |
| Implementation | 2-3 sessions per sub-initiative | Medium |
| Validation / QA | 1 session shared + per-sub validation | Medium |
| **Total** | 5-7 sessions per sub-initiative | Medium |

### 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cache invalidation bugs | Medium | High | Extensive testing; feature flags |
| Performance regression during fix | Low | Medium | Benchmark before/after each change |
| Opt_fields normalization breaks detection | Medium | High | Unit tests for detection accuracy |
| Cross-initiative dependency issues | Low | Medium | Clear interface contracts |

---

## Sub-Initiative Structure

### Priority Order (by Expected Impact)

| Priority | Sub-Initiative | Expected Impact | Rationale |
|----------|---------------|-----------------|-----------|
| P1 | **Fetch Path Investigation** | 40% of gap | Understand why parallel fetch results aren't being cached |
| P2 | **Detection Caching** | 25% of gap | High-frequency operation during DataFrame extraction |
| P3 | **Hydration Path Optimization** | 20% of gap | Repeated parent fetches during traversal |
| P4 | **Stories Cache Wiring** | 15% of gap | Incremental loader exists but unused |

### Sub-Initiative Dependency Graph

```
                    +------------------------+
                    | PROMPT-MINUS-1 (META)  |
                    | (This Document)        |
                    +------------------------+
                              |
              +---------------+---------------+
              |               |               |
              v               v               v
  +----------------+  +----------------+  +----------------+
  | PROMPT-0       |  | PROMPT-0       |  | PROMPT-0       |
  | FETCH-PATH (P1)|  | DETECTION (P2) |  | HYDRATION (P3) |
  +----------------+  +----------------+  +----------------+
              |               |               |
              +---------------+---------------+
                              |
                              v
                    +----------------+
                    | PROMPT-0       |
                    | STORIES (P4)   |
                    +----------------+

Note: Sub-initiatives are independent but Fetch Path should
      be investigated first as it may reveal additional insights.
```

### Sub-Initiative Summaries

#### 1. Fetch Path Investigation (P1) - `PROMPT-0-CACHE-PERF-FETCH-PATH.md`

**Problem**: ParallelSectionFetcher fetches tasks but subsequent DataFrame extraction calls still take 11.56s instead of <1s.

**Hypothesis**: Either (a) cache population is not happening, (b) cache lookup is not happening, or (c) opt_fields mismatch causes cache misses.

**Deliverable**: Root cause identified and fixed; cached DataFrame extraction in <1s.

#### 2. Detection Caching (P2) - `PROMPT-0-CACHE-PERF-DETECTION.md`

**Problem**: `detect_entity_type_async()` with `allow_structure_inspection=True` makes API calls (Tier 4: subtask fetch) and results are not cached.

**Solution**: Add `EntryType.DETECTION` and cache detection results by task GID.

**Deliverable**: Detection results cached; repeated detection for same GID is O(1).

#### 3. Hydration Path Optimization (P3) - `PROMPT-0-CACHE-PERF-HYDRATION.md`

**Problem**: `_traverse_upward_async()` uses `_DETECTION_OPT_FIELDS` for parent fetches. These custom opt_fields may bypass task cache which expects standard fields.

**Solution**: Either normalize opt_fields to match cache expectations, or implement field subsetting in cache.

**Deliverable**: Hydration traversal leverages task cache for parent lookups.

#### 4. Stories Cache Wiring (P4) - `PROMPT-0-CACHE-PERF-STORIES.md`

**Problem**: `cache/stories.py` has `load_stories_incremental()` with cache support, but `StoriesClient` does not use it.

**Solution**: Wire `StoriesClient.list_for_task_async()` to use incremental loader.

**Deliverable**: Stories fetched incrementally using cache; repeated calls use `since` parameter.

---

## Open Questions to Resolve Before Prompt 0

### Must Answer (Blocking)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 1 | Why does second fetch take 11.56s? | Cache not populated / Cache not checked / opt_fields mismatch | Investigate in Fetch Path sub-initiative | Open |
| 2 | What opt_fields does TasksClient cache use? | Standard set / Configurable / Any | Determine in Discovery | Open |
| 3 | How does ParallelSectionFetcher populate cache? | set_batch after fetch / Individual sets / Not at all | Verify in code analysis | Open |

### Should Answer (Informing)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 4 | Detection cache TTL? | Match task TTL (300s) / Longer (1hr) / Shorter | 300s (matches task) | Recommendation |
| 5 | Detection cache key structure? | `{task_gid}` / `{task_gid}:detection` | `{task_gid}` with EntryType.DETECTION | Recommendation |
| 6 | Stories cache key structure? | `{task_gid}` / `{task_gid}:{project_gid}` | `{task_gid}` (stories are task-specific) | Existing design |

### Nice to Answer (Context)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 7 | Metrics exposure for new cache types? | Per-type metrics / Aggregate only | Per-type for debugging | Nice-to-have |
| 8 | Feature flags for each fix? | Yes / No | Yes, for safe rollout | Recommendation |

---

## Go/No-Go Decision

### Criteria for "Go"

- [x] Problem is validated and worth solving (11.56s vs <1s is 10x gap)
- [x] Scope is bounded and achievable (four targeted fixes)
- [x] No blocking dependencies (infrastructure complete)
- [x] Complexity level appropriate for chosen workflow (module-level)
- [x] Success metrics are measurable (<1s cached fetch)
- [x] Rough effort estimate acceptable (5-7 sessions per sub-initiative)
- [x] High-risk items have mitigation plans (testing, feature flags)

### Recommendation

**GO** - Proceed to create Prompt 0 documents for each sub-initiative

**Rationale**:
- Clear evidence of cache bypass (11.56s vs expected <1s)
- Root causes identified through prior analysis
- Infrastructure is mature; only wiring changes needed
- Sub-initiatives are independent and can proceed in parallel
- Success criteria are measurable and achievable

---

## Next Steps

1. **Create Prompt 0 documents** (This session)
   - PROMPT-0-CACHE-PERF-FETCH-PATH.md (P1)
   - PROMPT-0-CACHE-PERF-DETECTION.md (P2)
   - PROMPT-0-CACHE-PERF-HYDRATION.md (P3)
   - PROMPT-0-CACHE-PERF-STORIES.md (P4)

2. **Execute Fetch Path first** (P1)
   - May reveal additional insights about cache integration patterns
   - Results inform other sub-initiatives

3. **Execute remaining sub-initiatives** (P2-P4)
   - Can proceed in parallel after Fetch Path discovery
   - Share validation criteria and benchmark methodology

---

## Appendix: Quick Reference

### Key Files by Sub-Initiative

| Sub-Initiative | Primary Files |
|---------------|---------------|
| Fetch Path | `dataframes/builders/project.py`, `dataframes/builders/parallel_fetch.py`, `dataframes/cache_integration.py` |
| Detection | `models/business/detection/facade.py`, `cache/entry.py` |
| Hydration | `models/business/hydration.py`, `clients/tasks.py` |
| Stories | `cache/stories.py`, `clients/stories.py` (if exists) |

### Cache Infrastructure Reference

| Component | Location | Status |
|-----------|----------|--------|
| EntryType enum | `cache/entry.py` | Extensible (add DETECTION) |
| CacheEntry | `cache/entry.py` | Complete |
| Batch operations | `cache/batch.py` | Complete |
| Stories incremental | `cache/stories.py` | Complete (not wired) |
| Metrics | `cache/metrics.py` | Complete |

### Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Watermark Cache Prompt 0 | `docs/requirements/PROMPT-0-WATERMARK-CACHE.md` | Prior architecture decisions |
| Cache Utilization Prompt 0 | `docs/requirements/PROMPT-0-CACHE-UTILIZATION.md` | Client caching patterns |
| Multi-level cache analysis | `docs/analysis/multi-level-cache-hierarchy-analysis.md` | Why single-level is correct |

---

*This Prompt -1 validated that the meta-initiative is ready for the 4-agent workflow. Proceed to create Prompt 0 documents for each sub-initiative.*
