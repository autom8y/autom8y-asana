# Smell Report: Runtime Efficiency Audit

```yaml
id: SMELL-RUNTIME-EFF-001
initiative: INIT-RUNTIME-EFF-001
rite: hygiene
agent: code-smeller
date: 2026-02-15
status: complete
```

---

## Executive Summary

| Category | Findings | Confirmed Bug | DRY Candidate |
|----------|----------|---------------|---------------|
| AT-1: Project-Level Fetches | 2 candidates, 3 not-applicable | -- | -- |
| AT-2: Redundant Hydration / N+1 | 5 findings (1 HIGH, 2 MEDIUM, 2 LOW) | -- | -- |
| AT-3: Dedup Caching Gaps | 2 findings (1 HIGH, 1 MEDIUM) | -- | -- |
| BUG: sections.py TTL | -- | 1 confirmed (2 locations) | -- |
| DRY: Section Extraction | -- | -- | 1 (4 locations) |
| **Total** | **9 efficiency findings + 1 bug + 1 DRY** | **1** | **1** |

Three patterns proven to reduce Asana API waste by ~40% (section-targeted fetch, bulk pre-resolution, dedup caching) have been audited across the entire `src/autom8_asana/` codebase. This report documents every location where these patterns should be applied but are not, along with one confirmed bug and one DRY violation.

---

## AT-1 Findings: Project-Level Fetches That Should Be Section-Targeted

### Context

Two `SectionClassifier` instances exist:
- **OFFER_CLASSIFIER**: 36 sections total (24 ACTIVE, 5 ACTIVATING, 3 INACTIVE, 4 IGNORED) at project `1143843662099250`
- **UNIT_CLASSIFIER**: 14 sections total (3 ACTIVE, 4 ACTIVATING, 6 INACTIVE, 1 IGNORED) at project `1201081073731555`

Section-targeted fetch reduces enumerated tasks by ~40% for the Offer project (skipping 12 non-ACTIVE sections) and ~78% for the Unit project (skipping 11 non-ACTIVE sections).

### Already Optimized (SKIP)

| File:Line | Pattern | Status |
|-----------|---------|--------|
| `insights_export.py:299` | Section-targeted primary, project fallback | Already optimized |
| `pipeline_transition.py:302` | Section-targeted primary, project fallback | Already optimized |
| `conversation_audit.py:255` | Project-level `list_async` on ContactHolder project | Not viable (no classifier; documented in SPIKE) |

### AT-1 Findings Table

| ID | File:Line | Current Pattern | Classification | Evidence | Estimated API Waste |
|----|-----------|-----------------|----------------|----------|---------------------|
| AT1-001 | `src/autom8_asana/dataframes/builders/progressive.py:562-567` | `_list_sections()` returns ALL sections; every section is fetched | **Candidate** | `list_for_project_async(self._project_gid)` returns all 36 Offer sections or all 14 Unit sections. Build loop at :454 iterates `resume_result.sections_to_fetch` which includes all non-COMPLETE sections regardless of ACTIVE status. No classifier filtering applied. | Offer: 12 unnecessary section fetches per build; Unit: 11 unnecessary section fetches per build |
| AT1-002 | `src/autom8_asana/dataframes/builders/parallel_fetch.py:144,164` | `fetch_all()` fetches ALL sections without ACTIVE filtering | **Candidate** | `_list_sections()` at :204 returns all sections via `list_for_project_async`. `_fetch_section()` at :164 is called for every section. No classifier gating to skip INACTIVE/IGNORED sections. | Same as AT1-001: 12 (Offer) or 11 (Unit) wasted section fetches |
| AT1-003 | `src/autom8_asana/automation/workflows/pipeline_transition.py:263` | Fallback path: `list_async(project=project_gid)` with client-side section filtering | **Not-applicable** | This is the intentional fallback when section resolution fails. Preserving project-level fetch as fallback is correct per design (Anti-Pattern #4 in PROMPT-0). | N/A (fallback) |
| AT1-004 | `src/autom8_asana/automation/workflows/insights_export.py:353` | Fallback path: `list_async(project=OFFER_PROJECT_GID)` with OFFER_CLASSIFIER client-side filter | **Not-applicable** | Same as AT1-003 -- intentional fallback method `_enumerate_offers_fallback()`. Already has client-side ACTIVE classification at :380. | N/A (fallback) |
| AT1-005 | `src/autom8_asana/automation/workflows/conversation_audit.py:255` | `list_async(project=CONTACT_HOLDER_PROJECT_GID)` | **Not-applicable** | No SectionClassifier exists for ContactHolder project. ContactHolder activity is derived from parent Business, not own section (documented in `docs/spikes/SPIKE-contact-holder-section-mapping.md`). | N/A (no classifier) |

### AT1-001 Detail: ProgressiveProjectBuilder Fetches All Sections

**File**: `src/autom8_asana/dataframes/builders/progressive.py:562-567`

```python
async def _list_sections(self) -> list[Section]:
    """List sections for the project."""
    sections: list[Section] = await self._client.sections.list_for_project_async(
        self._project_gid
    ).collect()
    return sections
```

The builder iterates every returned section at line 454-466:
```python
if resume_result.sections_to_fetch:
    ...
    section_map = {s.gid: s for s in sections}
    fetch_tasks = [
        self._fetch_and_persist_section_with_result(
            section_gid,
            section_map.get(section_gid),
            idx,
            len(resume_result.sections_to_fetch),
        )
        for idx, section_gid in enumerate(resume_result.sections_to_fetch)
    ]
```

No filtering by classifier activity status is applied. INACTIVE and IGNORED sections (12 for Offer, 11 for Unit) are fetched, processed, persisted to S3, and included in the merged DataFrame despite containing tasks that downstream consumers typically filter out anyway.

**Blast Radius**: 2 builder files, Offer + Unit project builds
**Severity**: MEDIUM -- wasted work on cold builds; mitigated by S3 resume on subsequent runs

### AT1-002 Detail: ParallelSectionFetcher Fetches All Sections

**File**: `src/autom8_asana/dataframes/builders/parallel_fetch.py:144,164`

```python
async def fetch_all(self) -> FetchResult:
    ...
    sections = await self._list_sections()  # ALL sections
    ...
    results = await asyncio.gather(
        *[self._fetch_section(section.gid, semaphore) for section in sections],
        return_exceptions=True,
    )
```

`_list_sections()` at line 204-226 fetches all sections via `list_for_project_async()` with no ACTIVE filtering. The 5-min GID enumeration cache (`:362-409`) and 30-min section list cache (`:299-342`) cache ALL sections, not just ACTIVE ones.

**Blast Radius**: Shared infrastructure used by `ProgressiveProjectBuilder`
**Severity**: MEDIUM -- same impact as AT1-001, but this is the shared infra that AT1-001 delegates to

---

## AT-2 Findings: Redundant Hydration / N+1 Patterns

### Already Optimized (SKIP)

| File:Line | Pattern | Status |
|-----------|---------|--------|
| `conversation_audit.py:272` | `_pre_resolve_business_activities()` with Semaphore(8) + `_activity_map` dedup | Already optimized |
| `cascading.py:192` | `_parent_cache` + `warm_parents()` batch pre-fetch | Already optimized |

### AT-2 Findings Table

| ID | File:Line | Pattern | Severity | Loop Context | Estimated Redundant Calls |
|----|-----------|---------|----------|--------------|--------------------------|
| AT2-001 | `src/autom8_asana/resolution/strategies.py:156-157` | Sequential `get_async(dep.gid)` for each dependency in loop | HIGH | `for dep in deps:` loop, no batching | 1-4 calls per resolution (depends on dep count); no dedup across calls |
| AT2-002 | `src/autom8_asana/resolution/strategies.py:262,270` | Sequential parent chain walk: 2x `get_async` per depth level | HIGH | `while depth < max_depth:` loop, up to 5 iterations | Up to 10 API calls per traversal (2 per depth x 5 levels max) |
| AT2-003 | `src/autom8_asana/dataframes/builders/freshness.py:340-346` | Sequential `get_async(gid)` for each added GID in delta merge | MEDIUM | `for gid in added_gids:` loop | 1 call per added GID; O(N) where N = new tasks since last probe |
| AT2-004 | `src/autom8_asana/models/business/asset_edit.py:645-663` | 3-hop sequential chain: Offer -> OfferHolder -> Unit | MEDIUM | Not in a loop, but 3 sequential awaits | 3 sequential API calls per resolution |
| AT2-005 | `src/autom8_asana/lifecycle/init_actions.py:199-204` | Sequential `get_async(dep_gid)` checking each dependency for project membership | LOW | `for dep in dependencies:` loop; early-returns on match | 1-N calls (N = dependency count); bounded by early return |

### AT2-001 Detail: DependencyShortcutStrategy Sequential Dep Walk

**File**: `src/autom8_asana/resolution/strategies.py:140-172`

```python
async def resolve_async(self, target_type, context, *, from_entity, budget):
    ...
    deps = await context.client.tasks.dependencies_async(from_entity.gid).collect()
    budget.consume(1)

    for dep in deps:
        dep_task = await context.client.tasks.get_async(dep.gid)  # N+1!
        budget.consume(1)
        entity = self._try_cast(dep_task, target_type)
        if entity is not None:
            ...
            return ResolutionResult.resolved(...)
        if budget.exhausted:
            return None
    return None
```

Each dependency is fetched sequentially. No `asyncio.gather()` or batch fetch. The budget tracks calls but does not prevent the sequential pattern. If a task has 4 dependencies, this makes 4 sequential API calls even though they could be parallelized.

**Blast Radius**: Resolution pipeline -- every entity resolution that reaches strategy index 2 (DependencyShortcut)
**Severity**: HIGH -- sequential in hot path, no caching across resolutions

### AT2-002 Detail: HierarchyTraversalStrategy Sequential Parent Walk

**File**: `src/autom8_asana/resolution/strategies.py:253-282`

```python
while depth < max_depth:
    ...
    parent_task = await context.client.tasks.get_async(
        current.gid, opt_fields=["parent", "parent.gid"]
    )
    budget.consume(1)
    ...
    parent = await context.client.tasks.get_async(parent_task.parent.gid)
    budget.consume(1)
    ...
    current = parent
    depth += 1
```

Two sequential `get_async` calls per depth level: one to fetch parent reference, one to fetch parent data. The first call fetches only `["parent", "parent.gid"]` which could be combined with the full fetch on the next line if the parent GID were known. Up to 5 depth levels = 10 API calls.

**Blast Radius**: Resolution pipeline -- every entity resolution that reaches strategy index 3 (HierarchyTraversal)
**Severity**: HIGH -- 2x API calls per depth, could be halved by requesting parent + full fields in single call

### AT2-003 Detail: Freshness Delta Sequential Added GID Fetch

**File**: `src/autom8_asana/dataframes/builders/freshness.py:340-346`

```python
for gid in added_gids:
    if gid not in fetched_gids:
        try:
            task = await self._client.tasks.get_async(
                gid, opt_fields=BASE_OPT_FIELDS
            )
            delta_tasks.append(task)
        except Exception as e:
            ...
```

Added GIDs (tasks newly appearing in a section since last probe) are fetched one-by-one sequentially. No `asyncio.gather()` batching. The `added_gids` set excludes tasks already fetched via `modified_since`, but remaining additions are fetched sequentially.

**Blast Radius**: Delta merge path in freshness probing; frequency depends on how often sections gain new tasks
**Severity**: MEDIUM -- only fires during delta merge when new GIDs are detected; typically small N

### AT2-004 Detail: AssetEdit 3-Hop Chain Walk

**File**: `src/autom8_asana/models/business/asset_edit.py:645-663`

```python
task = await client.tasks.get_async(offer_gid)         # Hop 1: Offer
...
parent_task = await client.tasks.get_async(offer.parent.gid)  # Hop 2: OfferHolder
...
unit_task = await client.tasks.get_async(parent_task.parent.gid)  # Hop 3: Unit
```

Three sequential API calls to walk Offer -> OfferHolder -> Unit. This could be a single call if the parent chain were pre-loaded, or 1-2 calls if `opt_fields=["parent", "parent.parent.gid"]` were used (Asana supports nested parent references up to 2 levels).

**Blast Radius**: `_resolve_unit_via_offer_id_async()` -- AssetEdit Unit resolution
**Severity**: MEDIUM -- 3 sequential calls, but this is a less frequently hit code path than resolution strategies

### AT2-005 Detail: Lifecycle Init Sequential Dependency Check

**File**: `src/autom8_asana/lifecycle/init_actions.py:199-204`

```python
for dep in dependencies:
    dep_gid = dep.gid if hasattr(dep, "gid") else dep.get("gid")
    if dep_gid:
        dep_task = await self._client.tasks.get_async(
            dep_gid, opt_fields=["memberships"]
        )
        ...
        if proj.get("gid") == action_config.project_gid:
            return CreationResult(success=True, entity_gid=dep_gid)  # early return
```

Sequential dependency fetch to check project membership. Mitigated by early return on first match. Typical dependency count is low (1-3).

**Blast Radius**: `CreatePlayAction.execute_async()` -- lifecycle play creation
**Severity**: LOW -- early return bounds worst case; low frequency code path

---

## AT-3 Findings: Dedup Caching Gaps

### Known Infrastructure (SKIP)

| Infrastructure | Cache Type | Location |
|----------------|-----------|----------|
| SectionsClient | 30-min TTL | `sections.py:27` (constant), `:130` (hard-coded; see BUG-001) |
| ParallelSectionFetcher | 5-min GID enum + 30-min section list | `parallel_fetch.py:121-122` |
| `_parent_cache` | Instance-level dict | `cascading.py:192` |
| `_activity_map` | Instance-level dict | `conversation_audit.py:83` |

### AT-3 Findings Table

| ID | File:Line | Function | Caller Context | Cache Status | Estimated Redundancy |
|----|-----------|----------|----------------|--------------|---------------------|
| AT3-001 | `src/autom8_asana/automation/workflows/insights_export.py:552-593` | `_resolve_offer()` | Called per-offer in `asyncio.gather` at :197-198 | No dedup cache | Multiple offers sharing same parent_gid each create separate `ResolutionContext` and fetch same Business |
| AT3-002 | `src/autom8_asana/resolution/strategies.py:262,270` | `_traverse_to_business_async()` | Called per-resolution via strategy chain | Session cache per-context only | Different `ResolutionContext` instances resolving entities under same Business re-traverse parent chain |

### AT3-001 Detail: InsightsExport Missing Business Dedup Cache

**File**: `src/autom8_asana/automation/workflows/insights_export.py:552-593`

```python
async def _resolve_offer(self, offer_gid, parent_gid):
    ...
    # Each offer creates its own ResolutionContext
    async with ResolutionContext(
        self._asana_client,
        business_gid=parent_gid,
    ) as ctx:
        business = await ctx.business_async()
        office_phone = business.office_phone
        vertical = business.vertical
        business_name = business.name
```

This is called from `_process_offer()` at :425, which is dispatched via `asyncio.gather` at :197-198 for ALL active offers:

```python
await asyncio.gather(
    *[process_one(o["gid"], o.get("name"), o.get("parent_gid")) for o in offers]
)
```

Offers are grouped under Business tasks. If 5 offers share the same `parent_gid` (Business), the same Business is fetched 5 times because each `ResolutionContext` has its own isolated session cache (cleared on `__aexit__` at line 88 of `context.py`).

The `conversation_audit.py` solved this exact problem with `_activity_map` (dedup cache at instance level). `insights_export.py` has no equivalent.

**Blast Radius**: All offer processing in insights_export workflow
**Severity**: HIGH -- M unique businesses fetched O(N) times where N = total offers; if 100 offers across 20 businesses, that's 80 redundant Business fetches
**Existing Pattern to Reuse**: `conversation_audit.py:83` `_activity_map` pattern

### AT3-002 Detail: Resolution Strategy Cross-Context Cache Miss

**File**: `src/autom8_asana/resolution/strategies.py:244-248`

```python
async def _traverse_to_business_async(self, entity, context, budget):
    ...
    cached_business = context.get_cached_business()  # checks THIS context only
    if cached_business is not None:
        return cached_business
```

The `SessionCacheStrategy` (first in chain, line 63-85) checks `context.get_cached(target_type)`, but each `ResolutionContext` instance has its own `_session_cache` dict. When multiple workflows or loop iterations create separate contexts for entities under the same Business, the cache is empty each time.

This is lower severity than AT3-001 because resolution strategies are typically invoked once per workflow item, not in a tight loop. The primary impact is when `HierarchyTraversalStrategy` re-walks the same parent chain that a previous resolution already discovered.

**Blast Radius**: Entity resolution across multiple contexts in same execution
**Severity**: MEDIUM -- cross-context redundancy; bounded by budget limits (max 8 API calls per chain)

---

## BUG-001: sections.py Hard-Coded TTL Instead of Constant

**Category**: Bug (configuration drift)
**Severity**: LOW (values currently match, but will diverge if config changes)

**File**: `src/autom8_asana/clients/sections.py`

**Constant defined at line 27**:
```python
SECTION_CACHE_TTL = get_settings().cache.ttl_section
```

**Hard-coded at line 130** (in `get()` method):
```python
# Step 5: Store in cache (30 min TTL, no modified_at available)
self._cache_set(section_gid, data, EntryType.SECTION, ttl=1800)
```

**Hard-coded at line 365** (in `list_for_project_async()` closure):
```python
entry = CacheEntry(
    key=gid,
    data=section_data,
    entry_type=EntryType.SECTION,
    version=now,  # No modified_at for sections
    ttl=1800,  # 30 min TTL
)
```

Both locations use literal `1800` instead of `SECTION_CACHE_TTL`. The constant exists at line 27 specifically to be configurable via `ASANA_CACHE_TTL_SECTION` environment variable (routed through `settings.py:168`). If a deployment overrides `ttl_section` via env var, the constant would pick up the new value but these two hard-coded sites would not, creating silent configuration drift.

**Fix Complexity**: Trivial -- replace `1800` with `SECTION_CACHE_TTL` in both locations.

---

## DRY-001: Section Extraction 4x Duplication

**Category**: DRY Violation
**Severity**: MEDIUM (4 implementations with subtle divergences; one orphaned canonical version)

### Location 1: Canonical `extract_section_name()` (ORPHANED)

**File**: `src/autom8_asana/models/business/activity.py:138-171`

```python
def extract_section_name(
    task: Any,
    project_gid: str | None = None,
) -> str | None:
    """Extract section name from task memberships.

    Canonical implementation of section name extraction. DRYs the pattern
    currently inline in Process.pipeline_state, BaseExtractor._extract_section,
    and DataFrameView._extract_section.
    """
    if not task.memberships:
        return None

    for membership in task.memberships:
        if project_gid:
            project = membership.get("project", {})
            if isinstance(project, dict) and project.get("gid") != project_gid:
                continue

        section = membership.get("section")
        if section and isinstance(section, dict):
            name = section.get("name")
            if name is not None and isinstance(name, str):
                return str(name)

    return None
```

**Status**: Exists but is never called. Docstring explicitly documents intent to DRY the other 3 implementations. Was written during spike (`docs/spikes/SPIKE-workflow-activity-gap-analysis.md`) but never wired in.

### Location 2: `BaseExtractor._extract_section()` (operates on Task model)

**File**: `src/autom8_asana/dataframes/extractors/base.py:488-521`

```python
def _extract_section(
    self,
    task: Task,
    project_gid: str | None = None,
) -> str | None:
    if not task.memberships:
        return None

    for membership in task.memberships:
        if project_gid:
            project = membership.get("project", {})
            if isinstance(project, dict) and project.get("gid") != project_gid:
                continue

        section = membership.get("section")
        if section and isinstance(section, dict):
            section_name = section.get("name")
            if section_name is not None and isinstance(section_name, str):
                return str(section_name)

    return None
```

**Difference from canonical**: Instance method on BaseExtractor; takes `Task` model instead of `Any`. Logic is **identical**.

### Location 3: `DataFrameViewPlugin._extract_section()` (operates on dict)

**File**: `src/autom8_asana/dataframes/views/dataframe_view.py:835-870`

```python
def _extract_section(
    self,
    task_data: dict[str, Any],
    project_gid: str | None = None,
) -> str | None:
    memberships = task_data.get("memberships")
    if not memberships:
        return None

    for membership in memberships:
        if not isinstance(membership, dict):
            continue

        if project_gid:
            project = membership.get("project", {})
            if isinstance(project, dict) and project.get("gid") != project_gid:
                continue

        section = membership.get("section")
        if section and isinstance(section, dict):
            section_name = section.get("name")
            if section_name is not None:
                return str(section_name)

    return None
```

**Differences from canonical**:
1. Takes `dict[str, Any]` instead of task model -- uses `task_data.get("memberships")` instead of `task.memberships`
2. Adds `isinstance(membership, dict)` guard (Location 1 and 2 do not)
3. Missing `isinstance(section_name, str)` check (subtle: Location 1 and 2 check it)

### Location 4: `Process.pipeline_state` (returns enum, different return type)

**File**: `src/autom8_asana/models/business/process.py:414-430`

```python
@property
def pipeline_state(self) -> ProcessSection | None:
    if not self.memberships:
        return None

    for membership in self.memberships:
        section_name = membership.get("section", {}).get("name")
        if section_name:
            return ProcessSection.from_name(section_name)

    return None
```

**Differences from canonical**:
1. Returns `ProcessSection` enum instead of `str | None`
2. Simpler extraction: no project_gid filtering, no type guards
3. Could use canonical + enum conversion: `name = extract_section_name(self); return ProcessSection.from_name(name) if name else None`

### Divergence Risk

The subtle differences (dict guard in Location 3, missing str check in Location 3, no project filter in Location 4) create maintenance risk. If a bug is fixed in one location, the others remain unfixed. The canonical implementation at Location 1 was written specifically to address this but was never wired in.

---

## Summary Table

| ID | Category | File:Line | Severity | Estimated API Savings | Recommended Action |
|----|----------|-----------|----------|----------------------|-------------------|
| AT1-001 | Section-Targeted | `progressive.py:562-567` | MEDIUM | 12 section fetches (Offer), 11 (Unit) per cold build | Filter sections by classifier ACTIVE status before fetch |
| AT1-002 | Section-Targeted | `parallel_fetch.py:144,164` | MEDIUM | Same as AT1-001 (shared infra) | Add optional section filter parameter to `fetch_all()` |
| AT2-001 | N+1 | `strategies.py:156-157` | HIGH | 1-4 sequential calls parallelizable per resolution | Batch dependency fetch via gather |
| AT2-002 | N+1 | `strategies.py:262,270` | HIGH | 2x calls per depth reducible to 1x | Combine parent ref + full data in single call |
| AT2-003 | N+1 | `freshness.py:340-346` | MEDIUM | O(N) sequential for N added GIDs | Batch added GID fetch via gather |
| AT2-004 | N+1 | `asset_edit.py:645-663` | MEDIUM | 3 sequential -> 1-2 with parent prefetch | Pre-fetch parent chain or use nested opt_fields |
| AT2-005 | N+1 | `init_actions.py:199-204` | LOW | 1-N sequential, bounded by early return | Parallel fetch with early cancellation |
| AT3-001 | Dedup Cache Gap | `insights_export.py:552-593` | HIGH | O(N-M) redundant Business fetches (N=offers, M=unique businesses) | Add instance-level `_business_cache` dict (same as conversation_audit pattern) |
| AT3-002 | Dedup Cache Gap | `strategies.py:244-248` | MEDIUM | Cross-context parent chain re-traversal | Consider shared resolution cache across contexts |
| BUG-001 | Bug | `sections.py:130,365` | LOW | N/A (correctness issue) | Replace `1800` with `SECTION_CACHE_TTL` |
| DRY-001 | DRY Violation | `activity.py:138` + 3 locations | MEDIUM | N/A (maintenance risk) | Wire orphaned canonical `extract_section_name()` into all 3 consumers |

---

## Attestation

| Artifact | Verified Via | Status |
|----------|-------------|--------|
| `src/autom8_asana/clients/sections.py:27,130,365` | Read tool | Confirmed: constant defined but not used at 2 sites |
| `src/autom8_asana/resolution/strategies.py:156-157,262,270` | Read tool | Confirmed: sequential get_async in loops |
| `src/autom8_asana/dataframes/builders/freshness.py:340-346` | Read tool | Confirmed: sequential get_async in for loop |
| `src/autom8_asana/models/business/asset_edit.py:645-663` | Read tool | Confirmed: 3-hop sequential chain |
| `src/autom8_asana/lifecycle/init_actions.py:199-204` | Read tool | Confirmed: sequential get_async in dep loop |
| `src/autom8_asana/automation/workflows/insights_export.py:552-593` | Read tool | Confirmed: no dedup cache for Business resolution |
| `src/autom8_asana/dataframes/builders/progressive.py:562-567` | Read tool | Confirmed: ALL sections fetched, no ACTIVE filter |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py:144,164` | Read tool | Confirmed: ALL sections fetched, no ACTIVE filter |
| `src/autom8_asana/models/business/activity.py:138-171` | Read tool | Confirmed: orphaned canonical, never called |
| `src/autom8_asana/dataframes/extractors/base.py:488-521` | Read tool | Confirmed: duplicate implementation |
| `src/autom8_asana/dataframes/views/dataframe_view.py:835-870` | Read tool | Confirmed: duplicate with divergences |
| `src/autom8_asana/models/business/process.py:414-430` | Read tool | Confirmed: simplified variant returning enum |

---

## Handoff Notes for Architect Enforcer

1. **AT1-001 and AT1-002 are coupled**: Fixing AT1-002 (ParallelSectionFetcher) likely fixes AT1-001 (ProgressiveProjectBuilder delegates to it). Consider adding an optional `section_filter: Callable[[Section], bool]` parameter to `fetch_all()`.

2. **AT2-001 and AT2-002 share context**: Both are in `resolution/strategies.py` and affect the resolution pipeline. AT2-002's double-fetch pattern (parent ref then full data) is the higher-value fix -- reducing 2 calls to 1 per depth level saves more than parallelizing the dependency loop.

3. **AT3-001 has a proven pattern**: The `conversation_audit.py:83` `_activity_map` is the exact pattern needed. Estimated effort: add `_business_cache: dict[str, Business]` to `InsightsExportWorkflow.__init__` and check before creating `ResolutionContext`.

4. **BUG-001 is a quick win**: Two-line fix with no blast radius.

5. **DRY-001 has an orphaned canonical**: The canonical `extract_section_name()` at `activity.py:138` was written during spike analysis but never wired in. The spike documented this at `docs/spikes/SPIKE-workflow-activity-gap-analysis.md`. Location 3 has subtle divergences (missing `isinstance(str)` check) that could mask real bugs.
