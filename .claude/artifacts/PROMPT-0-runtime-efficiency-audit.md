# PROMPT-0: Runtime Efficiency Audit

```yaml
id: INIT-RUNTIME-EFF-001
rite: hygiene
complexity: AUDIT → TARGETED_FIXES
estimated_sprints: 2-3
upstream: session-20260215 (Section-Targeted Enumeration)
```

---

## Executive Summary

Three workflow migrations proved that **section-targeted fetch + dedup caching + pre-filter gating** eliminate ~40% of wasted Asana API calls. This initiative systematically audits the ENTIRE codebase for the same patterns and ships fixes where viable.

**The three proven patterns:**

| Pattern | Mechanism | Proven Savings |
|---------|-----------|----------------|
| **Section-targeted fetch** | `list_async(section=<gid>)` instead of `list_async(project=<gid>)` | ~40% fewer tasks enumerated |
| **Bulk pre-resolution** | Resolve entity state in parallel batch BEFORE entering processing pipeline | ~36% wall-clock improvement |
| **Dedup caching** | `dict[gid, result]` cache eliminates redundant hydrations for shared parents | O(M unique) instead of O(N total) |

**Goal:** Find every place these patterns should be applied but aren't, prioritize by API-call savings, and ship the high-value fixes.

---

## Phase 1: Audit (code-smeller)

### Audit Target 1: Project-Level Fetches That Should Be Section-Targeted

Every `list_async(project=...)` that enumerates tasks from a project with a known `SectionClassifier` is a candidate. The codebase has two classifiers:

- **OFFER_CLASSIFIER** — 36 sections (24 ACTIVE, 5 ACTIVATING, 3 INACTIVE, 4 IGNORED) at project `1143843662099250`
- **UNIT_CLASSIFIER** — 14 sections (3 ACTIVE, 4 ACTIVATING, 6 INACTIVE, 1 IGNORED) at project `1201081073731555`

**Already optimized (skip these):**
- `insights_export.py:299` — section-targeted primary, project fallback ✅
- `pipeline_transition.py:302` — section-targeted primary, project fallback ✅
- `conversation_audit.py:255` — NOT viable (ContactHolder activity is derived from parent Business, not own section; documented in `docs/spikes/SPIKE-contact-holder-section-mapping.md`) ✅

**Known candidates to audit:**
- `src/autom8_asana/dataframes/builders/progressive.py` — `_fetch_and_persist_section()` uses section-level iteration but may have project-level fallback paths
- `src/autom8_asana/dataframes/builders/freshness.py:164,193,331` — freshness probing already section-targeted, but verify no project-level waste in delta merge
- `src/autom8_asana/dataframes/builders/parallel_fetch.py` — `ParallelSectionFetcher.fetch_all()` already section-level; verify it filters to ACTIVE sections or fetches ALL sections
- `src/autom8_asana/cache/integration/hierarchy_warmer.py` — cache warming; does it enumerate entire projects or target sections?

**Audit method:** `grep -rn 'list_async.*project=' src/autom8_asana/` then classify each hit as {already-optimized, candidate, not-applicable}.

### Audit Target 2: Redundant Hydration / N+1 Patterns

Sequential `tasks.get_async()` calls inside loops are N+1 patterns. The bulk pre-resolution pattern (gather + dedup cache) eliminates these.

**Known N+1 hotspots:**

| Location | Pattern | Severity |
|----------|---------|----------|
| `resolution/strategies.py:157,262,270` | `HierarchyTraversalStrategy` — sequential parent chain walk + dependency fetch inside loop | HIGH |
| `freshness.py:343` | `_apply_section_delta()` — sequential `get_async()` for each added GID | MEDIUM |
| `models/business/asset_edit.py:645-707` | Asset → Offer → Unit chain walk (3 sequential fetches) | MEDIUM |
| `models/business/hydration.py:285,325` | Depth traversal walks (already batched within depth, but verify) | LOW |

**Already optimized (skip these):**
- `conversation_audit.py` — `_pre_resolve_business_activities()` with Semaphore(8) + `_activity_map` dedup ✅
- `dataframes/resolver/cascading.py:192` — `_parent_cache` + `warm_parents()` batch pre-fetch ✅

**Audit method:** `grep -rn 'get_async' src/autom8_asana/ | grep -v test | grep -v '#'` then check if each call is inside a loop/gather.

### Audit Target 3: Dedup Caching Gaps

The `_activity_map` pattern in ConversationAudit eliminated redundant Business hydrations. Where else do we resolve the same entity multiple times?

**Pattern to detect:** Any `async def` that:
1. Takes a GID parameter
2. Fetches data from Asana API
3. Is called from inside a loop/gather
4. Does NOT check a cache first

**Known infrastructure:**
- `SectionsClient` has 30-min TTL cache (configured in `settings.py:168`, constant `SECTION_CACHE_TTL` in `sections.py:27`)
- ⚠️ **Bug found:** `sections.py:130` hard-codes `ttl=1800` instead of using `SECTION_CACHE_TTL` constant
- `ParallelSectionFetcher` has 5-min GID enumeration cache + 30-min section list cache
- `_parent_cache` in `cascading.py:192` for parent chain dedup
- `_activity_map` in `conversation_audit.py:83` for Business activity dedup

**Audit method:** Search for `await.*get_async\|await.*list_async` inside `async for\|for.*in\|gather` patterns.

---

## Phase 2: Prioritize (architect-enforcer)

### Prioritization Matrix

Score each finding on:

| Dimension | Weight | Scale |
|-----------|--------|-------|
| **API calls saved per execution** | 40% | Estimate: (N items) × (calls per item) × (% waste) |
| **Execution frequency** | 30% | How often does this code path run? (per-request vs daily cron vs weekly) |
| **Implementation complexity** | 20% | Can we reuse existing patterns (section_resolution.py, dedup cache) or need new infra? |
| **Risk** | 10% | Blast radius of change; does fallback exist? |

### Decision Framework

| Score | Action |
|-------|--------|
| ≥ 70 | Ship in this initiative |
| 40-69 | Document as follow-up, file in deferred roadmap |
| < 40 | Document finding only, no action |

---

## Phase 3: Fix (janitor)

### Reusable Infrastructure (Already Built)

The following are ready to reuse — do NOT rebuild:

**1. `section_resolution.py` — Section Name → GID Resolver**
```
src/autom8_asana/automation/workflows/section_resolution.py
```
- `resolve_section_gids(sections_client, project_gid, target_names)` → `dict[str, str]`
- Case-insensitive matching, missing-section WARNING logs
- Raises on SectionsClient error (caller handles fallback)

**2. Section-Targeted Fetch Pattern (from insights_export.py)**
```python
# Primary path: resolve section GIDs, parallel fetch, dedup
gid_map = await resolve_section_gids(sections_client, PROJECT_GID, ACTIVE_SECTION_NAMES)
semaphore = asyncio.Semaphore(5)
async def fetch_section(section_gid): ...
results = await asyncio.gather(*[fetch_section(gid) for gid in gid_map.values()], return_exceptions=True)
# Dedup by GID
seen_gids: set[str] = set()
# Fallback: project-level fetch on ANY failure
```

**3. Bulk Pre-Resolution Pattern (from conversation_audit.py)**
```python
# Extract unique GIDs, parallel resolve, cache, pre-filter
unique_gids = {item["parent_gid"] for item in items if ...}
semaphore = asyncio.Semaphore(8)
await asyncio.gather(*[resolve_one(gid) for gid in unique_gids], return_exceptions=True)
# Filter: keep only items where cached result == desired state
```

**4. Dedup Cache Pattern**
```python
self._cache: dict[str, Result | None] = {}  # Instance-level, per-execution
if gid in self._cache:
    return self._cache[gid]  # Cache hit
result = await expensive_operation(gid)
self._cache[gid] = result
return result
```

**5. ParallelSectionFetcher** (for dataframe builders)
```
src/autom8_asana/dataframes/builders/parallel_fetch.py
```
- Already handles section-level fetch with Semaphore(8), GID dedup, 5-min cache
- Used by progressive builder; verify other builders use it too

### Implementation Rules

1. **Every optimization MUST have a fallback** — if the optimized path fails, fall back to the original code verbatim
2. **Every optimization MUST log the before/after** — total items, filtered items, cache hits, API calls saved
3. **Every optimization MUST preserve test compatibility** — use `_force_fallback` fixture pattern to route existing tests through fallback path
4. **Concurrency limits:** Semaphore(5) for processing, Semaphore(8) for resolution/enumeration
5. **No new modules** unless absolutely necessary — prefer adding methods to existing classes

---

## Phase 4: Validate (audit-lead)

### Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| All project-level fetches classified | Audit spreadsheet: {optimized, candidate, not-applicable} for every `list_async(project=...)` call |
| All N+1 patterns classified | Audit spreadsheet: {fixed, deferred, acceptable} for every sequential-in-loop `get_async()` |
| All dedup cache gaps classified | Audit spreadsheet: {fixed, deferred, acceptable} |
| High-priority fixes shipped | All findings scored ≥70 have PRs merged |
| Zero test regressions | Full `pytest tests/unit/ -x -q --timeout=60` passes (exclude `tests/unit/api/` for pre-existing slowapi issue) |
| Fallback coverage | Every optimized path has a tested fallback |
| Observability | Every optimization logs savings metrics |

### Regression Baseline

```bash
# Run from project root
.venv/bin/pytest tests/unit/ --ignore=tests/unit/api/ -x -q --timeout=60
# Expected: 8781 passed (as of 2026-02-15)
```

### Pre-existing test failures (not our problem):
- `test_adversarial_pacing.py` — checkpoint assertions
- `test_paced_fetch.py` — checkpoint assertions
- `test_parallel_fetch.py::test_cache_errors_logged_as_warnings` — caplog vs structured logging

---

## Key File Index

### Classifiers & Activity
| File | What |
|------|------|
| `src/autom8_asana/models/business/activity.py` | `OFFER_CLASSIFIER` (24 ACTIVE), `UNIT_CLASSIFIER` (3 ACTIVE), `SectionClassifier`, `AccountActivity` enum |
| `src/autom8_asana/models/business/activity.py:138` | `extract_section_name()` — canonical section extraction (4x duplicated elsewhere) |

### Clients
| File | What |
|------|------|
| `src/autom8_asana/clients/tasks.py:459` | `list_async(*, project=, section=, ...)` — the target API |
| `src/autom8_asana/clients/sections.py:27,130` | `SECTION_CACHE_TTL` constant + hard-coded TTL bug |
| `src/autom8_asana/settings.py:168` | `ttl_section: int = 1800` (30 min) |

### Already-Optimized Workflows (reference implementations)
| File | Pattern |
|------|---------|
| `src/autom8_asana/automation/workflows/section_resolution.py` | Shared `resolve_section_gids()` helper |
| `src/autom8_asana/automation/workflows/insights_export.py:299` | Section-targeted primary + project fallback |
| `src/autom8_asana/automation/workflows/pipeline_transition.py:302` | Section-targeted primary + project fallback |
| `src/autom8_asana/automation/workflows/conversation_audit.py:272` | Bulk pre-resolution + dedup cache + pre-filter |

### Audit Targets (check these)
| File | Why |
|------|-----|
| `src/autom8_asana/dataframes/builders/progressive.py` | Section iteration — verify ACTIVE-only or all sections |
| `src/autom8_asana/dataframes/builders/freshness.py:343` | Sequential `get_async()` in added_gids loop |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Existing infra — verify it filters by activity |
| `src/autom8_asana/cache/integration/hierarchy_warmer.py` | Cache warming scope — project-level or section-level? |
| `src/autom8_asana/resolution/strategies.py:157,262,270` | N+1 parent chain + dependency walk |
| `src/autom8_asana/models/business/asset_edit.py:645-707` | 3-hop chain walk |

### Spikes (prior art)
| File | Finding |
|------|---------|
| `docs/spikes/SPIKE-workflow-activity-gap-analysis.md` | Full gap analysis: phantom method bug (fixed), orphaned module (wired), 4x section extraction duplication |
| `docs/spikes/SPIKE-contact-holder-section-mapping.md` | ContactHolder NOT viable for section-targeted (activity derived from parent) |
| `docs/spikes/SPIKE-conversation-audit-bulk-preresolution.md` | Bulk pre-resolution design + wall-clock analysis |

### DRY Candidate (section extraction 4x duplication)
| File | Implementation |
|------|---------------|
| `src/autom8_asana/models/business/activity.py:138` | Canonical `extract_section_name()` (orphaned, never called) |
| `src/autom8_asana/dataframes/extractors/base.py:488` | `BaseExtractor._extract_section()` (instance method on Task) |
| `src/autom8_asana/dataframes/dataframe_view.py:835` | `DataFrameViewPlugin._extract_section()` (instance method on dict) |
| `src/autom8_asana/models/business/process.py:414` | `Process.pipeline_state` (returns ProcessSection enum, different type) |

---

## Deferred Work Roadmap Integration

This initiative is a **companion to the existing deferred-work roadmap** at `.claude/artifacts/deferred-work-roadmap.md`. That roadmap covers structural quality (7 initiatives, 4 waves). This initiative covers **runtime efficiency** — a dimension not yet addressed.

Suggested placement: **Wave 1.5** (can run in parallel with I1/I4-S1 since it touches different files).

---

## Anti-Patterns to Avoid

1. **Don't optimize fallback paths** — fallback exists for resilience, not performance
2. **Don't add section-targeted fetch where there's no classifier** — only Offer and Unit projects have classifiers; don't fabricate one for ContactHolder
3. **Don't break the `ParallelSectionFetcher` contract** — it's shared infrastructure; modify carefully
4. **Don't remove project-level fetch entirely** — always keep it as fallback
5. **Don't over-cache** — session-level dedup (per-execution) is cheap and safe; persistent caching needs TTL and invalidation strategy
