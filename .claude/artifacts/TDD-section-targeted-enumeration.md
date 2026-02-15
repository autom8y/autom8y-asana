# TDD: Section-Targeted Workflow Enumeration

```yaml
id: TDD-SECTION-ENUM-001
status: DRAFT
date: 2026-02-15
author: Architect Agent
upstream: PRD-SECTION-ENUM-001
pr_strategy: Single branch, 3 sequential commits (Pipeline, Insights, tests)
```

---

## 1. Overview

Three automation workflows enumerate Asana tasks by fetching all tasks from entire projects and discarding those in irrelevant sections. The Asana API supports section-level task listing (`tasks.list_async(section=<gid>)`), already wired in `TasksClient` and used by the DataFrame layer. This TDD specifies how to migrate each workflow from project-level fetch with client-side filtering to section-targeted fetch, preserving fallback resilience.

**Scope**: 2 workflow migrations (PipelineTransition, InsightsExport), 1 gated migration (ConversationAudit pending spike), shared helper function, test updates.

**Files Changed**: ~6 source files, ~3 test files.

---

## 2. Architecture Decision Records

### ADR-1: Per-Workflow Inline with Shared Resolution Helper (DD-1)

**Status**: ACCEPTED

**Context**: All three workflows need the same pattern: resolve section names to GIDs via `SectionsClient.list_for_project_async()`, then fetch tasks per section via `tasks.list_async(section=<gid>)`. Three options were evaluated:

- **(a) SectionFilteredEnumerator class**: A reusable class encapsulating resolve-fetch-merge-fallback.
- **(b) Per-workflow inline**: Each workflow implements the full pattern independently.
- **(c) Generalize ParallelSectionFetcher**: Extend the DataFrame layer's fetcher for workflow use.

**Decision**: **Option (b) with a thin shared helper function** for the name-to-GID resolution step.

Each workflow implements section-targeted fetch inline, with a shared `resolve_section_gids()` async function extracted to `src/autom8_asana/automation/workflows/section_resolution.py`. This function handles the name-matching and missing-section logging. Everything else -- fallback, concurrency, post-processing, return type construction -- remains per-workflow.

**Rationale**:

1. **Return types diverge fundamentally**: PipelineTransition returns `list[tuple[Process, str]]` with outcome tagging; InsightsExport returns `list[dict]` with parent_gid extraction; ConversationAudit returns `list[dict]` with parent object preservation. A class would need generics or callback hooks to accommodate this, adding complexity without proportional benefit.

2. **Fallback granularity differs**: PipelineTransition falls back per-project (8 independent fallback decisions); InsightsExport falls back per-workflow-cycle. A shared class would need a strategy pattern for fallback scope, which is over-engineering for 3 callers.

3. **Post-processing differs**: PipelineTransition tags each task with its source section ("converted" / "did_not_convert"). InsightsExport just merges. This per-section metadata requirement is specific to Pipeline and would leak into a shared abstraction.

4. **The only truly shared logic is name-to-GID resolution**: Given a project GID and a set of target section names, resolve which sections exist and return their GIDs. This is ~15 lines of code. Extracting this as a function (not a class) gives reuse without coupling.

5. **ParallelSectionFetcher (option c) rejected**: It fetches ALL sections in a project. Workflows need TARGETED sections. It returns `FetchResult(tasks=list[Task])` with no per-section metadata. It raises `ParallelFetchError` on any section failure (fail-all), while workflows need per-project graceful degradation. Modifying it violates the PRD constraint ("ParallelSectionFetcher in DataFrame layer is NOT modified").

**Consequences**:
- (+) Each workflow's enumeration logic is self-contained and readable.
- (+) No new class hierarchy or abstraction layer.
- (+) Fallback logic is explicit and per-workflow-appropriate.
- (-) ~20 lines of boilerplate duplicated across workflows (gather + dedup pattern). Acceptable for 2-3 callers.
- (-) If a 4th workflow needs this pattern, extraction to a class should be reconsidered.

---

### ADR-2: SectionsClient Cache Is Sufficient (DD-2)

**Status**: ACCEPTED

**Context**: `SectionsClient.list_for_project_async()` caches section lists with 30-minute TTL and batch-populates individual section cache entries. The question is whether workflows need additional caching of the section-name-to-GID mapping.

**Decision**: Rely exclusively on the existing `SectionsClient` cache. No workflow-level caching.

**Rationale**:

1. **Cold-start cost for PipelineTransition**: 8 projects means 8 `list_for_project_async()` calls on first invocation. Each call returns a small payload (typically 5-15 sections per project). These are sequential within the per-project loop, adding ~8 HTTP round trips. At ~200ms each, this is ~1.6s total cold-start overhead -- acceptable given the workflow runs on a scheduled interval (not user-facing latency).

2. **Warm-path eliminates the concern**: After the first cycle, all 8 project section lists are cached for 30 minutes. The workflow interval is shorter than the TTL, so subsequent cycles hit cache.

3. **InsightsExport**: Single project, single `list_for_project_async()` call. Trivial cost.

4. **Adding a workflow-level mapping cache** would create a second cache layer with its own TTL, staleness risk, and invalidation semantics. The SectionsClient cache is already tested and battle-proven. Adding more caching for a sub-second cold-start penalty is not justified.

**Consequences**:
- (+) No new caching code. No new TTL management. No cache coherence issues.
- (+) Section name changes in Asana propagate naturally through the existing 30-minute TTL.
- (-) Cold-start of PipelineTransition pays ~1.6s overhead (once per 30 minutes). Acceptable.

---

### ADR-3: Semaphore(5) for Section Fetches, Sequential Per-Project for Pipeline (DD-3)

**Status**: ACCEPTED

**Context**: InsightsExport needs 21 section fetches. PipelineTransition needs 2 per project across 8 projects. `ParallelSectionFetcher` uses `Semaphore(8)`. Asana's rate limit is 1500 requests per minute.

**Decision**:

- **InsightsExport**: `asyncio.gather()` with `asyncio.Semaphore(5)` for the 21 ACTIVE section fetches.
- **PipelineTransition**: Retain sequential per-project loop. Within each project, fetch 2 sections sequentially (no gather needed for 2 calls).

**Rationale**:

1. **InsightsExport (21 sections)**: Semaphore(5) means at most 5 concurrent Asana API calls for section task listing. At 100ms per call, 21 sections complete in ~5 rounds = ~500ms wall clock. This is well under the rate limit (5 req/100ms = 3000 req/min theoretical, but the semaphore gates actual concurrency). Semaphore(8) would also work but offers diminishing returns -- the bottleneck is pagination, not parallelism. Semaphore(5) leaves headroom for other concurrent workflows sharing the same Asana API quota.

2. **PipelineTransition (2 sections per project)**: Fetching 2 sections per project is 2 API calls. `asyncio.gather()` for 2 calls adds complexity without meaningful latency improvement (200ms vs 100ms). The per-project loop is already sequential (PRD FR-2.2 says "retain the per-project loop structure"). Keeping it sequential makes fallback logic trivial -- if section resolution fails for one project, we fall back for that project only and continue to the next.

3. **Why not parallelize across all 8 pipeline projects**: The current code is sequential per-project. Parallelizing across projects would change the error isolation model (currently, one project's error does not affect others). The PRD explicitly requires per-project fallback (FR-5.4). Keeping the sequential loop preserves this guarantee trivially.

**Consequences**:
- (+) InsightsExport sees ~4x speedup over serial (21 serial calls at 100ms = 2.1s; 5-wide parallel = ~500ms).
- (+) PipelineTransition keeps simple, debuggable sequential flow.
- (+) Conservative concurrency leaves API quota headroom.
- (-) PipelineTransition does not benefit from cross-project parallelism. This is acceptable because the current sequential pattern already works and the PRD does not require latency improvement for Pipeline.

---

### ADR-4: Drop `memberships.section.name` from Section-Level Fetches (DD-4)

**Status**: ACCEPTED

**Context**: Current project-level fetches request `memberships.section.name` to enable client-side section classification. With section-targeted fetch, the section identity is known from the fetch target.

**Decision**: Drop `memberships.section.name` (and `memberships`, `memberships.section`) from `opt_fields` on the section-targeted primary path. Retain them on the fallback path (which reverts to project-level fetch with client-side filtering).

**Per-workflow opt_fields**:

| Workflow | Primary Path (section-level) | Fallback Path (project-level) |
|----------|------------------------------|-------------------------------|
| PipelineTransition | `name`, `completed` | `name`, `completed`, `memberships`, `memberships.section`, `memberships.section.name` (current) |
| InsightsExport | `name`, `completed`, `parent`, `parent.name` | `name`, `completed`, `parent`, `parent.name`, `memberships.section.name` (current) |
| ConversationAudit | `name`, `completed`, `parent`, `parent.name` | `name`, `completed`, `parent`, `parent.name` (current -- no memberships today) |

**Rationale**:

1. **PipelineTransition**: On the primary path, tasks are fetched per-section. The outcome ("converted" / "did_not_convert") is determined by which section GID the fetch targeted, not by inspecting memberships. The `memberships` field is no longer needed. The `Process.model_validate(task)` call does not require memberships -- `Process` uses `pipeline_state` which reads memberships, but Pipeline populates outcome from the fetch target, not from the task's self-reported memberships. However, `Process.pipeline_state` may be called elsewhere for logging. To be safe, we keep `memberships.section.name` out of opt_fields on the primary path but do NOT break `Process.pipeline_state` -- it gracefully returns `None` when memberships are empty.

2. **InsightsExport**: The downstream `_process_offer()` needs `parent` and `parent.name` to resolve the Business. It does NOT need `memberships.section.name` on the primary path because classification is implicit. The current code's classification loop (lines 282-297) is bypassed on the primary path.

3. **Payload reduction**: Dropping `memberships.section.name` removes a nested object from each task response. For InsightsExport with ~200 ACTIVE offers across 21 sections, this reduces response size meaningfully. For PipelineTransition, removing `memberships`, `memberships.section`, and `memberships.section.name` (3 fields) is a larger reduction.

**Consequences**:
- (+) Reduced API response payload on the primary (common) path.
- (+) Fallback path retains all fields needed for client-side filtering.
- (-) `Process.pipeline_state` returns `None` on the primary path (memberships not populated). This is acceptable because the outcome is determined by fetch target, and `pipeline_state` is not used in the Pipeline workflow's processing logic -- it was only needed for the inline section-name matching that this migration eliminates.

---

## 3. Component Architecture

### 3.1 New Module: Section Resolution Helper

**File**: `src/autom8_asana/automation/workflows/section_resolution.py`

This module contains a single async function that resolves section names to GIDs. It is the only shared code extracted for this initiative.

```
+---------------------------+
| section_resolution.py     |
|                           |
| resolve_section_gids()    |
+---------------------------+
        |
        | calls
        v
+---------------------------+
| SectionsClient            |
| .list_for_project_async() |
| (30-min cached)           |
+---------------------------+
```

### 3.2 Data Flow: PipelineTransition (After)

```
For each project_gid in 8 projects:
  |
  +-- resolve_section_gids(client.sections, project_gid, {"CONVERTED", "DID NOT CONVERT"})
  |     |
  |     +-- list_for_project_async(project_gid).collect()  [cached]
  |     +-- match names (case-insensitive) -> dict[str, str]  {name: gid}
  |     +-- log WARNING for missing names
  |     +-- return resolved: dict[str, str]
  |
  +-- IF resolved is empty OR resolution raised Exception:
  |     +-- FALLBACK: list_async(project=project_gid) with current logic
  |
  +-- ELSE for each (section_name, section_gid) in resolved:
  |     +-- list_async(section=section_gid, completed_since="now", opt_fields=[name, completed]).collect()
  |     +-- for each task: Process.model_validate(task), append (process, outcome)
  |
  +-- dedup by GID (unlikely for 2 non-overlapping sections, but defensive)
```

### 3.3 Data Flow: InsightsExport (After)

```
resolve_section_gids(client.sections, OFFER_PROJECT_GID, OFFER_CLASSIFIER.sections_for(ACTIVE))
  |
  +-- list_for_project_async(OFFER_PROJECT_GID).collect()  [cached]
  +-- match 21 ACTIVE section names -> dict[str, str]  {name: gid}
  +-- return resolved: dict[str, str]

IF resolved is empty OR resolution raised Exception:
  +-- FALLBACK: current project-level fetch + classify loop

ELSE:
  +-- semaphore = asyncio.Semaphore(5)
  +-- async def fetch_section(section_gid):
  |     async with semaphore:
  |       return await list_async(section=section_gid, completed_since="now",
  |                               opt_fields=[name, completed, parent, parent.name]).collect()
  +-- results = await asyncio.gather(*[fetch_section(gid) for gid in resolved.values()],
  |                                   return_exceptions=True)
  +-- if ANY result is Exception: FALLBACK to project-level fetch
  +-- else: flatten, dedup by GID, build offer dicts [{gid, name, parent_gid}]
```

### 3.4 Data Flow: ConversationAudit (Gated -- Pending Spike)

No design specified until the ContactHolder spike (FR-4.1) determines section structure. The current implementation is preserved. If the spike reveals activity-mapped sections, the pattern from InsightsExport applies with a `CONTACT_HOLDER_CLASSIFIER`.

---

## 4. Interface Contracts

### 4.1 resolve_section_gids()

**File**: `src/autom8_asana/automation/workflows/section_resolution.py`

```python
async def resolve_section_gids(
    sections_client: SectionsClient,
    project_gid: str,
    target_names: frozenset[str] | set[str],
) -> dict[str, str]:
    """Resolve section names to GIDs for a project.

    Fetches the project's section list via SectionsClient (cached, 30-min TTL),
    matches target names case-insensitively, and returns a mapping of
    lowercase section name -> section GID.

    Missing sections are logged at WARNING level but do not raise.

    Args:
        sections_client: Sections API client (with cache).
        project_gid: Asana project GID to enumerate sections for.
        target_names: Set of section names to resolve (matched case-insensitively).

    Returns:
        Dict mapping lowercase section name -> section GID.
        Empty dict if no target names matched.

    Raises:
        Exception: Propagates any SectionsClient error (network, 5xx, timeout).
            Callers must handle this for fallback.
    """
```

**Behavior**:
1. Call `sections_client.list_for_project_async(project_gid).collect()` to get all sections.
2. Build lookup: `{section.name.lower(): section.gid for section in sections if section.name}`.
3. For each name in `target_names`: look up `name.lower()` in the lookup.
4. For names not found: log `WARNING` with `section_resolution_miss`, `project_gid`, `missing_name`.
5. Return the matched subset as `dict[str, str]`.

**Contract tests**: Verify that:
- Matching is case-insensitive (`"CONVERTED"` matches section named `"Converted"`).
- Missing names produce WARNING log, not error.
- Empty sections list returns empty dict.
- All target names matching returns full dict.

### 4.2 PipelineTransition._enumerate_processes_async() (Modified)

**File**: `src/autom8_asana/automation/workflows/pipeline_transition.py`

**Current signature** (unchanged):
```python
async def _enumerate_processes_async(
    self,
    project_gids: list[str],
    converted_section: str,
    dnc_section: str,
) -> list[tuple[Process, str]]:
```

**New internal behavior**:
```python
# For each project_gid:
#   1. Try: resolved = await resolve_section_gids(
#              self._client.sections, project_gid,
#              {converted_section, dnc_section})
#   2. If resolved is empty or exception caught:
#        Fall back to current project-level logic (preserved verbatim)
#   3. Else:
#        For each (name, gid) in resolved.items():
#          tasks = await self._client.tasks.list_async(
#              section=gid,
#              opt_fields=["name", "completed"],
#              completed_since="now",
#          ).collect()
#          outcome = "converted" if name == converted_section.lower() else "did_not_convert"
#          for task in tasks:
#              if not task.completed:
#                  process = Process.model_validate(task)
#                  processes.append((process, outcome))
```

### 4.3 InsightsExport._enumerate_offers() (Modified)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`

**Current signature** (unchanged):
```python
async def _enumerate_offers(self) -> list[dict[str, Any]]:
```

**New internal behavior**:
```python
# 1. Determine target sections
#    from autom8_asana.models.business.activity import AccountActivity, OFFER_CLASSIFIER
#    active_sections = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)
#
# 2. Try: resolved = await resolve_section_gids(
#            self._asana_client.sections, OFFER_PROJECT_GID, active_sections)
#
# 3. If resolved is empty or exception caught:
#      Fall back to current project-level logic (preserved verbatim as _enumerate_offers_fallback)
#
# 4. Else:
#      semaphore = asyncio.Semaphore(5)
#      async def fetch_one(section_gid: str) -> list[Task]:
#          async with semaphore:
#              return await self._asana_client.tasks.list_async(
#                  section=section_gid,
#                  opt_fields=["name", "completed", "parent", "parent.name"],
#                  completed_since="now",
#              ).collect()
#
#      results = await asyncio.gather(
#          *[fetch_one(gid) for gid in resolved.values()],
#          return_exceptions=True)
#
#      if any(isinstance(r, Exception) for r in results):
#          log WARNING, fall back to _enumerate_offers_fallback()
#
#      # Flatten, dedup, build dicts
#      seen_gids: set[str] = set()
#      offers: list[dict] = []
#      for section_tasks in results:
#          for t in section_tasks:
#              if t.completed or t.gid in seen_gids:
#                  continue
#              seen_gids.add(t.gid)
#              offers.append({"gid": t.gid, "name": t.name,
#                             "parent_gid": t.parent.gid if t.parent else None})
#
#      log info: sections_targeted=len(resolved), tasks_enumerated=len(offers)
#      return offers
```

---

## 5. Per-Workflow Migration Plan

### 5.1 Phase 1: PipelineTransition (Cleanest Case)

**Why first**: Only 2 target sections per project, well-defined names (`CONVERTED`, `DID NOT CONVERT`), no classifier integration needed, no concurrency concerns within a project.

**File changes**:

| File | Change |
|------|--------|
| `src/autom8_asana/automation/workflows/section_resolution.py` | NEW: `resolve_section_gids()` function |
| `src/autom8_asana/automation/workflows/pipeline_transition.py` | MODIFY: `_enumerate_processes_async()` |
| `tests/unit/automation/workflows/test_pipeline_transition.py` | MODIFY: update mocks, add fallback tests |

**Exact changes to `pipeline_transition.py`**:

Lines 225-289 (`_enumerate_processes_async`): Replace the body while preserving the signature.

Current inner loop (lines 244-281):
```python
# Current: fetch all tasks from project, filter by section name
page_iter = self._client.tasks.list_async(
    project=project_gid,
    opt_fields=["name", "completed", "memberships", "memberships.section", "memberships.section.name"],
    completed_since="now",
)
tasks = await page_iter.collect()
for task in tasks:
    if task.completed:
        continue
    memberships = getattr(task, "memberships", []) or []
    for membership in memberships:
        section = membership.get("section", {})
        section_name = section.get("name", "")
        if section_name.upper() == converted_section.upper():
            process = Process.model_validate(task)
            processes.append((process, "converted"))
            break
        elif section_name.upper() == dnc_section.upper():
            process = Process.model_validate(task)
            processes.append((process, "did_not_convert"))
            break
```

Replacement:
```python
try:
    resolved = await resolve_section_gids(
        self._client.sections,
        project_gid,
        {converted_section, dnc_section},
    )
except Exception:
    logger.warning(
        "section_resolution_failed_fallback",
        project_gid=project_gid,
        workflow_id=self.workflow_id,
    )
    resolved = {}

if not resolved:
    # Fallback: project-level fetch with client-side filtering
    page_iter = self._client.tasks.list_async(
        project=project_gid,
        opt_fields=[
            "name", "completed", "memberships",
            "memberships.section", "memberships.section.name",
        ],
        completed_since="now",
    )
    tasks = await page_iter.collect()
    for task in tasks:
        if task.completed:
            continue
        memberships = getattr(task, "memberships", []) or []
        for membership in memberships:
            section = membership.get("section", {})
            section_name = section.get("name", "")
            if section_name.upper() == converted_section.upper():
                process = Process.model_validate(task)
                processes.append((process, "converted"))
                break
            elif section_name.upper() == dnc_section.upper():
                process = Process.model_validate(task)
                processes.append((process, "did_not_convert"))
                break
else:
    # Primary path: section-targeted fetch
    for section_name_lower, section_gid in resolved.items():
        outcome = (
            "converted"
            if section_name_lower == converted_section.lower()
            else "did_not_convert"
        )
        section_tasks = await self._client.tasks.list_async(
            section=section_gid,
            opt_fields=["name", "completed"],
            completed_since="now",
        ).collect()
        for task in section_tasks:
            if not task.completed:
                process = Process.model_validate(task)
                processes.append((process, outcome))

    logger.info(
        "pipeline_section_targeted_enumeration",
        project_gid=project_gid,
        sections_targeted=len(resolved),
        tasks_enumerated=len(processes),
    )
```

**Import addition** at top of `pipeline_transition.py`:
```python
from autom8_asana.automation.workflows.section_resolution import resolve_section_gids
```

### 5.2 Phase 2: InsightsExport

**Why second**: 21 sections require concurrency (Semaphore), classifier integration, deduplication. More complex than Pipeline but well-understood.

**File changes**:

| File | Change |
|------|--------|
| `src/autom8_asana/automation/workflows/insights_export.py` | MODIFY: `_enumerate_offers()` |
| `tests/unit/automation/workflows/test_insights_export.py` | MODIFY: update mocks, add fallback tests |

**Exact changes to `insights_export.py`**:

Lines 253-312 (`_enumerate_offers`): Replace the body while preserving the signature and return type.

The current project-level logic (lines 267-312) becomes the fallback method `_enumerate_offers_fallback()`. The primary path in `_enumerate_offers()` calls `resolve_section_gids()`, fetches 21 sections in parallel with `Semaphore(5)`, and builds the same `list[dict]` return value.

```python
async def _enumerate_offers(self) -> list[dict[str, Any]]:
    """List ACTIVE (non-completed) Offer tasks using section-targeted fetch.

    Primary path: resolve ACTIVE section GIDs, fetch tasks per section
    in parallel (Semaphore(5)), merge and deduplicate by GID.

    Fallback: project-level fetch with client-side classification (current behavior).
    """
    from autom8_asana.automation.workflows.section_resolution import (
        resolve_section_gids,
    )
    from autom8_asana.models.business.activity import (
        AccountActivity,
        OFFER_CLASSIFIER,
    )

    active_section_names = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)

    # Resolve section GIDs
    try:
        resolved = await resolve_section_gids(
            self._asana_client.sections,
            OFFER_PROJECT_GID,
            active_section_names,
        )
    except Exception:
        logger.warning(
            "section_resolution_failed_fallback",
            workflow_id=self.workflow_id,
            project_gid=OFFER_PROJECT_GID,
        )
        return await self._enumerate_offers_fallback()

    if not resolved:
        logger.warning(
            "section_resolution_empty_fallback",
            workflow_id=self.workflow_id,
            project_gid=OFFER_PROJECT_GID,
        )
        return await self._enumerate_offers_fallback()

    # Parallel section fetch with bounded concurrency
    semaphore = asyncio.Semaphore(5)

    async def fetch_section(section_gid: str) -> list:
        async with semaphore:
            return await self._asana_client.tasks.list_async(
                section=section_gid,
                opt_fields=["name", "completed", "parent", "parent.name"],
                completed_since="now",
            ).collect()

    results = await asyncio.gather(
        *[fetch_section(gid) for gid in resolved.values()],
        return_exceptions=True,
    )

    # If any section fetch failed, fall back entirely
    if any(isinstance(r, Exception) for r in results):
        logger.warning(
            "section_fetch_partial_failure_fallback",
            workflow_id=self.workflow_id,
            project_gid=OFFER_PROJECT_GID,
            failed_count=sum(1 for r in results if isinstance(r, Exception)),
        )
        return await self._enumerate_offers_fallback()

    # Flatten, dedup by GID, build offer dicts
    seen_gids: set[str] = set()
    offers: list[dict[str, Any]] = []
    for section_tasks in results:
        for t in section_tasks:
            if t.completed or t.gid in seen_gids:
                continue
            seen_gids.add(t.gid)
            offers.append({
                "gid": t.gid,
                "name": t.name,
                "parent_gid": t.parent.gid if t.parent else None,
            })

    logger.info(
        "insights_section_targeted_enumeration",
        sections_targeted=len(resolved),
        tasks_enumerated=len(offers),
    )

    return offers

async def _enumerate_offers_fallback(self) -> list[dict[str, Any]]:
    """Fallback: project-level fetch with client-side ACTIVE classification.

    This is the pre-migration enumeration logic, preserved verbatim for
    resilience when section resolution or section-level fetch fails.
    """
    from autom8_asana.models.business.activity import (
        AccountActivity,
        OFFER_CLASSIFIER,
    )

    page_iterator = self._asana_client.tasks.list_async(
        project=OFFER_PROJECT_GID,
        opt_fields=[
            "name", "completed", "parent", "parent.name",
            "memberships.section.name",
        ],
        completed_since="now",
    )
    tasks = await page_iterator.collect()

    offers = []
    skipped = 0
    for t in tasks:
        if t.completed:
            continue
        section_name = None
        for m in getattr(t, "memberships", None) or []:
            sec = m.get("section", {}) if isinstance(m, dict) else getattr(m, "section", None)
            if sec:
                section_name = sec.get("name") if isinstance(sec, dict) else getattr(sec, "name", None)
                break
        activity = OFFER_CLASSIFIER.classify(section_name) if section_name else None
        if activity != AccountActivity.ACTIVE:
            skipped += 1
            continue
        offers.append({
            "gid": t.gid,
            "name": t.name,
            "parent_gid": t.parent.gid if t.parent else None,
        })

    if skipped:
        logger.info(
            "insights_export_offers_filtered_fallback",
            active=len(offers),
            skipped=skipped,
            fallback=True,
        )

    return offers
```

### 5.3 Phase 3: ConversationAudit (Gated)

**Blocked on**: ContactHolder spike (FR-4.1). No implementation specified.

**Design intent**: If the spike reveals activity-mapped sections, follow the InsightsExport pattern with a `CONTACT_HOLDER_CLASSIFIER`. If not, the current implementation is retained.

---

## 6. Error Handling and Fallback Design

### 6.1 Fallback Trigger Conditions

| Condition | Scope | Behavior |
|-----------|-------|----------|
| `resolve_section_gids()` raises any Exception | Per-project (Pipeline), per-cycle (Insights) | Log WARNING, execute fallback path |
| `resolve_section_gids()` returns empty dict | Per-project (Pipeline), per-cycle (Insights) | Log WARNING, execute fallback path |
| Any `list_async(section=...)` raises Exception during gather | Per-cycle (Insights only) | Log WARNING with failed count, execute fallback path |
| Individual `list_async(section=...)` raises Exception | Per-project (Pipeline) | Caught by existing per-project `except Exception` block |

### 6.2 Fallback Path Guarantees

1. **Behavioral equivalence**: The fallback path is the current (pre-migration) code, preserved verbatim. No logic changes.
2. **No double-fetch**: If the primary path is attempted and fails, we do NOT retry section-level fetches. We go straight to project-level.
3. **Logging**: Every fallback activation emits a structured WARNING log with `workflow_id`, `project_gid`, and the trigger reason.
4. **No cascading fallback**: A fallback in one Pipeline project does not trigger fallback for other projects. An InsightsExport fallback is all-or-nothing for the cycle.

### 6.3 Fallback for InsightsExport: Full-Cycle Granularity

For InsightsExport, if ANY of the 21 section fetches fails during `asyncio.gather()`, we fall back to project-level fetch for the entire cycle. This is a deliberate choice:

- **Why not per-section fallback**: If section 5 of 21 fails, we cannot meaningfully fall back to "fetch the whole project and filter out sections 1-4 and 6-21 that we already fetched." That would require tracking which tasks came from which sections and merging partial results with filtered project-level results. The complexity is not justified.
- **Expected frequency**: Section-level `list_async` uses the same HTTP transport as project-level `list_async`. If section fetches are failing, project-level fetch may also fail. The fallback is a best-effort resilience measure, not a guaranteed recovery.

---

## 7. Test Strategy

### 7.1 New Test: section_resolution.py

**File**: `tests/unit/automation/workflows/test_section_resolution.py`

| Test | Description |
|------|-------------|
| `test_resolve_all_names_found` | All target names match sections in the project |
| `test_resolve_partial_match` | Some target names match, others produce WARNING log |
| `test_resolve_no_match` | No target names match, returns empty dict |
| `test_resolve_case_insensitive` | "CONVERTED" matches section named "Converted" |
| `test_resolve_empty_sections_list` | Project has no sections, returns empty dict |
| `test_resolve_propagates_exception` | SectionsClient raises, exception propagates to caller |

**Mock pattern**: Mock `sections_client.list_for_project_async()` to return `_AsyncIterator([Section(...), ...])`.

### 7.2 Modified Tests: PipelineTransition

**File**: `tests/unit/automation/workflows/test_pipeline_transition.py`

**Changes to existing tests**:

All existing tests mock `mock_client.tasks.list_async.return_value` with an `_AsyncIterator` of tasks that include `memberships` with section names. After migration, the primary path calls `list_async(section=<gid>)` instead of `list_async(project=<gid>)`.

**Mock update pattern**:

```python
# Before: single mock for project-level fetch
mock_client.tasks.list_async.return_value = _AsyncIterator([task1, task2])

# After: mock sections resolution + per-section task fetch
mock_sections = [
    MagicMock(gid="sec-converted", name="CONVERTED"),
    MagicMock(gid="sec-dnc", name="DID NOT CONVERT"),
    MagicMock(gid="sec-other", name="IN PROGRESS"),
]
mock_client.sections.list_for_project_async.return_value = _AsyncIterator(mock_sections)

# tasks.list_async now called with section= kwarg
def side_effect_list_async(**kwargs):
    if kwargs.get("section") == "sec-converted":
        return _AsyncIterator([task1])  # task1 in CONVERTED
    elif kwargs.get("section") == "sec-dnc":
        return _AsyncIterator([task2])  # task2 in DID NOT CONVERT
    return _AsyncIterator([])

mock_client.tasks.list_async.side_effect = side_effect_list_async
```

**New tests to add**:

| Test | Description |
|------|-------------|
| `test_enumerate_fallback_on_section_resolution_failure` | Mock `list_for_project_async` to raise; verify `list_async(project=...)` is called |
| `test_enumerate_fallback_on_empty_resolution` | Mock sections with no matching names; verify project-level fallback |
| `test_enumerate_section_targeted_happy_path` | Mock sections + section-level tasks; verify correct outcome tagging |
| `test_enumerate_section_targeted_one_section_missing` | Only CONVERTED exists, not DNC; verify only converted tasks returned |
| `test_enumerate_per_project_fallback_isolation` | Project 1 resolves OK, project 2 fails; verify project 2 falls back independently |

### 7.3 Modified Tests: InsightsExport

**File**: `tests/unit/automation/workflows/test_insights_export.py`

**Mock update pattern**:

The `_make_workflow()` helper currently sets `mock_asana.tasks.list_async.return_value = _AsyncIterator(offer_list)`. After migration, the primary path uses section-level fetches. The helper needs to:

1. Mock `mock_asana.sections.list_for_project_async()` to return sections matching ACTIVE names.
2. Mock `mock_asana.tasks.list_async` with a `side_effect` that returns appropriate tasks based on the `section=` kwarg.

Alternatively, patch `resolve_section_gids` at the module level to control the resolution result directly, keeping task mock setup simpler.

**Recommended approach**: Patch `resolve_section_gids` for most tests (unit isolation). Add 2-3 integration-style tests that exercise the full resolve-then-fetch path with section mocks.

**New tests to add**:

| Test | Description |
|------|-------------|
| `test_enumerate_offers_section_targeted` | Mock resolution + section fetches; verify dedup and dict construction |
| `test_enumerate_offers_fallback_on_resolution_failure` | Mock resolution to raise; verify project-level fetch is used |
| `test_enumerate_offers_fallback_on_partial_fetch_failure` | Mock one section fetch to raise; verify full fallback |
| `test_enumerate_offers_dedup_multi_homed` | Same task GID in 2 sections; verify it appears once |

### 7.4 Contract Test: Section Resolution Correctness

**File**: `tests/unit/automation/workflows/test_section_resolution.py`

Verify that `OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)` returns exactly 21 names:

```python
def test_offer_active_section_count():
    """OFFER_CLASSIFIER has exactly 21 ACTIVE sections."""
    from autom8_asana.models.business.activity import AccountActivity, OFFER_CLASSIFIER
    active = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)
    assert len(active) == 21
```

This guards against accidental classifier changes that would silently alter enumeration behavior.

---

## 8. Implementation Order and Dependency Graph

```
Step 1: section_resolution.py (new module)
  |
  +-- No dependencies on existing workflow code
  +-- Tests: test_section_resolution.py
  |
Step 2: pipeline_transition.py (modify _enumerate_processes_async)
  |
  +-- Depends on: Step 1 (resolve_section_gids)
  +-- Tests: update test_pipeline_transition.py
  |
Step 3: insights_export.py (modify _enumerate_offers, add _enumerate_offers_fallback)
  |
  +-- Depends on: Step 1 (resolve_section_gids)
  +-- Tests: update test_insights_export.py
  |
Step 4 (GATED): conversation_audit.py
  |
  +-- Depends on: ContactHolder spike outcome
  +-- Blocked until spike completes
```

Steps 2 and 3 are independent of each other (both depend only on Step 1) and could theoretically be parallelized, but sequential implementation is recommended for review clarity.

---

## 9. Observability

### 9.1 Structured Log Events

| Event | Level | Fields | Workflow |
|-------|-------|--------|----------|
| `section_resolution_miss` | WARNING | `project_gid`, `missing_name` | All (from helper) |
| `section_resolution_failed_fallback` | WARNING | `workflow_id`, `project_gid` | All |
| `section_resolution_empty_fallback` | WARNING | `workflow_id`, `project_gid` | All |
| `section_fetch_partial_failure_fallback` | WARNING | `workflow_id`, `project_gid`, `failed_count` | InsightsExport |
| `pipeline_section_targeted_enumeration` | INFO | `project_gid`, `sections_targeted`, `tasks_enumerated` | PipelineTransition |
| `insights_section_targeted_enumeration` | INFO | `sections_targeted`, `tasks_enumerated` | InsightsExport |
| `insights_export_offers_filtered_fallback` | INFO | `active`, `skipped`, `fallback=True` | InsightsExport (fallback path) |

### 9.2 Success Criteria Verification

Per PRD SC-1 through SC-8:

| SC | Verification Method |
|----|---------------------|
| SC-1 | Grep: no `list_async(project=` in `_enumerate_*` methods (excluding fallback) |
| SC-2 | Code review: primary path uses `list_async(section=` |
| SC-3 | Unit test: verify `list_async` called with 21 section GIDs |
| SC-4 | Unit test: verify `list_async` called 2 times per project |
| SC-5 | Unit test: mock resolution failure, verify `list_async(project=...)` |
| SC-6 | CI green: `tests/unit/automation/workflows/` |
| SC-7 | Spike document delivered (separate artifact) |
| SC-8 | Unit test: verify log events contain required fields |

---

## 10. Risk Mitigations

| Risk | Mitigation | Implementation |
|------|------------|----------------|
| R-3: Mock cascade in tests (~15-20 test cases) | Use `side_effect` on `list_async` to dispatch by kwarg | See Section 7.2 mock pattern |
| R-4: API call count increase | Bounded by Semaphore(5) for Insights, sequential for Pipeline | See ADR-3 |
| R-6: Multi-homed tasks | GID dedup set in InsightsExport, unlikely in Pipeline (2 non-overlapping sections) | See Section 4.3 |
| R-7: 21 parallel fetches | Semaphore(5) caps concurrent requests | See ADR-3 |
| `Process.model_validate` fails without memberships | Verify Process model handles missing memberships gracefully | Pre-implementation check |

---

## 11. Out of Scope (Confirmed)

Per PRD Section 8, explicitly excluded:

- Dead code removal (post-hoc classification loops retained for fallback).
- DRY extraction of `extract_section_name()` across callers.
- Observability dashboard.
- Extension to non-workflow enumerations.
- ParallelSectionFetcher modification.
- ContactHolder section creation in Asana.

---

## 12. Constraints Checklist

| Constraint | Status |
|------------|--------|
| No new Python packages | Satisfied: only stdlib + existing internal imports |
| No changes to TasksClient | Satisfied: uses existing `list_async(section=)` interface |
| No changes to SectionsClient | Satisfied: uses existing `list_for_project_async()` interface |
| Fallback preserves current behavior | Satisfied: fallback code is verbatim current implementation |
| ParallelSectionFetcher not modified | Satisfied: no changes to DataFrame layer |
| Implementation order: Pipeline first | Satisfied: Step 2 before Step 3 |

---

## Attestation Table

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/PRD-section-targeted-enumeration.md` | Read |
| PipelineTransition source | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/pipeline_transition.py` | Read |
| InsightsExport source | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/insights_export.py` | Read |
| ConversationAudit source | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/conversation_audit.py` | Read |
| TasksClient.list_async | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` | Read (lines 459-528) |
| SectionsClient.list_for_project_async | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | Read (lines 306-384) |
| SectionClassifier + OFFER_CLASSIFIER | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/activity.py` | Read |
| ParallelSectionFetcher | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/parallel_fetch.py` | Read (lines 85-202) |
| Project registry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/project_registry.py` | Read |
| Section model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/section.py` | Read |
| Pipeline test file | `/Users/tomtenuta/Code/autom8_asana/tests/unit/automation/workflows/test_pipeline_transition.py` | Read |
| Insights test file | `/Users/tomtenuta/Code/autom8_asana/tests/unit/automation/workflows/test_insights_export.py` | Read |
| ConvAudit test file | `/Users/tomtenuta/Code/autom8_asana/tests/unit/automation/workflows/test_conversation_audit.py` | Read |
| Workflow conftest | `/Users/tomtenuta/Code/autom8_asana/tests/unit/automation/workflows/conftest.py` | Read |
| TDD (this document) | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/TDD-section-targeted-enumeration.md` | Written |
