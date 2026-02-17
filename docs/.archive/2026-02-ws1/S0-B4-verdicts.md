# Sprint 0, Batch 4: Automation & Lifecycle -- Spike Verdicts

**Initiative**: INIT-RUNTIME-OPT-002 (Runtime Efficiency Remediation v2)
**Phase**: Sprint 0 (Spike Investigation)
**Author**: Architect
**Date**: 2026-02-15

---

## S0-SPIKE-07: Duplicate Section Listing Across Lifecycle

**Verdict**: NO-GO

### Evidence

#### (a) Tracing each section listing call site

There are **5 distinct call sites** that invoke `client.sections.list_for_project_async(project_gid).collect()` within lifecycle/automation code:

1. **`automation/pipeline.py:693`** -- `_move_to_target_section_async`: Lists sections in target project to find section by name, then moves newly created task there.

2. **`lifecycle/creation.py:548`** -- `_move_to_section_async`: Lists sections in target project to find section by name (step 5a of configure phase), then moves task.

3. **`lifecycle/sections.py:181`** -- `CascadingSectionService._move_to_section_async`: Lists sections in the entity's primary project (extracted from memberships) to move Offer/Unit/Business to new section.

4. **`lifecycle/reopen.py:177`** -- `ReopenService._move_to_section_async`: Lists sections in target project to find section by name, then moves reopened process.

5. **`automation/templates.py:81`** -- `TemplateDiscovery.find_template_section_async`: Lists sections in target project to find the "Template" section for template discovery.

All call sites follow the identical pattern: `sections.list_for_project_async(project_gid).collect()` followed by a name-based linear search.

#### (b) Does SectionsClient have a cache on list_for_project_async?

**No.** The `SectionsClient.list_for_project_async` (sections.py:306-384) returns a `PageIterator` that makes a fresh HTTP GET to `/projects/{project_gid}/sections` every time `.collect()` is called. There is no result-level caching on the list operation.

What IS cached: individual sections by GID. During pagination, the `fetch_page` closure populates the cache with individual `CacheEntry` objects keyed by section GID (lines 352-379). But this is a per-section-GID cache used by `get_async(section_gid)`, not by `list_for_project_async()`. Calling `list_for_project_async().collect()` twice for the same project will make two separate HTTP requests.

The `section_resolution.py` helper comments say "30-min cached" but this refers to individual section entries cached during pagination, not the list operation itself.

#### (c) Are these calls in the same async context within a single lifecycle transition?

**Critical finding: they target DIFFERENT projects in most cases.**

Tracing a standard CONVERTED lifecycle transition (engine.py `_run_pipeline_async`):

**Phase 1: CREATE** (via `EntityCreationService.create_process_async`):
- `TemplateDiscovery.find_template_section_async(target_project_gid)` -- lists sections in **target project** (e.g., Sales project)
- `EntityCreationService._move_to_section_async(task_gid, target_project_gid, section_name)` -- lists sections in the **same target project**

These two calls target the **same project**. This is a genuine duplicate: template discovery lists sections to find the template section, then configure lists sections again to find the target section for placement. **2 API calls to the same project, same request.**

**Phase 2: CONFIGURE** (via `CascadingSectionService.cascade_async`):
- `_move_to_section_async(offer, section_name, "offer")` -- lists sections in **Offer's project** (from offer.memberships)
- `_move_to_section_async(unit, section_name, "unit")` -- lists sections in **Unit's project** (from unit.memberships)
- `_move_to_section_async(business, section_name, "business")` -- lists sections in **Business's project** (from business.memberships)

These three calls target **different projects** (Offer project, Unit project, Business project). These are NOT duplicates of each other or of the target project calls above.

**Alternative flow: DNC reopen:**
- `ReopenService._move_to_section_async(task_gid, target_project_gid, section_name)` -- lists sections in **target project**

This is a separate code path from creation; reopen does NOT also call template discovery, so only 1 section listing per project in the reopen flow.

**Alternative flow: automation/pipeline.py (legacy pipeline):**
- `TemplateDiscovery.find_template_task_async(target_project_gid)` -- lists sections in **target project**
- `_move_to_target_section_async(new_task, target_project_gid, section_name)` -- lists sections in **same target project**

Same pattern as lifecycle/creation: 2 calls to the same target project.

#### (d) Count: how many times are sections listed for the SAME project per transition?

**Lifecycle creation path**: 2 calls to target project (template discovery + section placement). The 3 cascade section calls go to different projects.

**Automation pipeline path**: 2 calls to target project (template discovery + section placement).

**DNC reopen path**: 1 call to target project (section placement only; no template discovery).

**Maximum for same project per transition: 2.**

#### (e) What would be needed to add a per-request cache?

A simple `dict[str, list[Section]]` keyed by `project_gid` on the client or passed as context would eliminate the second call. The first call's result could be cached for the duration of the request/transition.

However, the savings are exactly **1 API call per lifecycle creation**. The `list_for_project_async` pagination for sections typically completes in a single page (most projects have fewer than 100 sections, and the page size is 100). So the savings is 1 HTTP request (~50-100ms).

### Verdict Rationale: NO-GO

The spike's GO criteria was **">2 actual API calls (cache misses) per transition for the same project's sections."** The investigation reveals:

1. **Maximum 2 calls per project per transition**, not >2. The two calls are from template discovery + section placement, both targeting the target project.

2. **The 4 call sites across lifecycle modules target different projects.** The cascade section calls (Offer/Unit/Business) each query a different project -- they are not duplicates of each other.

3. **Savings of exactly 1 API call** (~50-100ms) per creation transition. With 200+ transitions/day, this is ~200 saved API calls -- meaningful but modest.

4. **IMP-07 (Template Discovery Section Listing) already addresses this.** IMP-07 adds `template_section_gid` to YAML config, which eliminates the template discovery section listing entirely. Once IMP-07 is implemented, the creation path drops to 1 section listing call (for placement) and there is no duplication to optimize.

The optimization is real but:
- Below the >2 threshold specified in the GO criteria
- Already subsumed by IMP-07 which eliminates the source of the duplication
- Net savings after IMP-07: zero (only 1 call remains per project per transition)

### Risks (if this were pursued)

1. **Staleness**: A per-request cache means if a section is created/deleted mid-transition, the cached list is stale. Low risk for the ~2-second transition duration, but a correctness concern.
2. **IMP-07 overlap**: Implementing both this and IMP-07 would be redundant effort.

### Affected Files

N/A -- NO-GO, no changes recommended. IMP-07 already addresses the root cause.

---

## S0-SPIKE-11: Batch API for Independent Configure Steps

**Verdict**: NO-GO

### Evidence

#### (a) Batch client capabilities today

`batch/client.py` implements a full Asana Batch API client:

- **`execute_async(requests)`**: Accepts a list of `BatchRequest` objects, each with `relative_path`, `method`, `data`, and `options`.
- **Auto-chunking**: Splits requests into groups of 10 (Asana's per-batch limit, `BATCH_SIZE_LIMIT = 10`).
- **Sequential chunk execution**: Chunks are executed sequentially per ADR-0010.
- **Partial failure handling**: Individual actions fail independently; `BatchResult.success` tracks per-action status.
- **Mixed operation support**: `BatchRequest` supports GET, POST, PUT, DELETE with arbitrary paths. A single batch can mix `/tasks` POST with `/tasks/123` PUT and `/sections/456/addTask` POST.

The `BatchRequest.to_action_dict()` method (models.py:68-88) produces standard Asana batch action format. Asana's batch API does support mixing different operation types in a single batch.

#### (b) Configure phase API calls in lifecycle/creation.py

Tracing `_configure_async` (creation.py:353-481), the sequential steps are:

| Step | Operation | API Call | Dependencies |
|------|-----------|----------|-------------|
| a. Section placement | `_move_to_section_async` | 1. `list_for_project_async().collect()` (GET sections) | None |
| | | 2. `sections.add_task_async()` (POST addTask) | Depends on step a.1 (needs section GID) |
| b. Due date | `tasks.update_async(gid, due_on=...)` | 1 PUT /tasks/{gid} | None (independent) |
| c. Wait subtasks | `waiter.wait_for_subtasks_async()` | 0-3 GET /tasks/{gid}/subtasks (polling) | Must complete before seeding |
| d. Auto-cascade seeding | `seeder.seed_async()` | 1 GET /tasks/{gid} (fetch target) + 1 PUT /tasks/{gid} (write fields) | Depends on step c (subtasks must exist) |
| e. Hierarchy placement | `SaveSession.set_parent()` + `commit_async()` | 1 PUT /tasks/{gid} (set parent) | None (independent) |
| f. Set assignee | `_set_assignee_async()` | 1 PUT /tasks/{gid} (set assignee) | None (independent) |

**Total: 5-8 API calls**, of which steps b, e, and f are independent write operations (PUT /tasks/{gid}).

#### (c) Ordering dependencies between configure steps

**Critical dependencies exist:**

1. **Step a (section placement)**: Two-phase -- first lists sections (GET), then adds task to section (POST). The POST depends on the GET result (needs section GID). These two calls CANNOT be batched together.

2. **Step c (wait subtasks)**: Polling loop that waits for Asana to asynchronously create subtasks from template duplication. This is a **blocking dependency** -- steps d (seeding) must wait for subtasks to exist before writing fields to them.

3. **Step d (auto-cascade seeding)**: Fetches the target task to resolve custom field GIDs, then writes fields. The GET and PUT are sequential internally. The fetch depends on the task being fully created (after step c).

**Independent steps**: b (due date), e (hierarchy placement), f (assignee) are genuinely independent -- they could theoretically run in parallel or be batched.

#### (d) Does Asana's batch API support the needed operations?

Asana's batch API supports mixing operation types. A batch could contain:

```json
[
  {"relative_path": "/tasks/NEW_GID", "method": "PUT", "data": {"due_on": "2026-03-01"}},
  {"relative_path": "/tasks/NEW_GID", "method": "PUT", "data": {"parent": "HOLDER_GID"}},
  {"relative_path": "/tasks/NEW_GID", "method": "PUT", "data": {"assignee": "USER_GID"}}
]
```

**However**: Asana's batch API does NOT guarantee execution order within a batch. Actions execute concurrently server-side. For tasks, this means:

- Multiple PUTs to the same task GID in one batch may have **last-write-wins** semantics on overlapping fields.
- The three independent PUTs above update DIFFERENT fields (due_on, parent, assignee), so they would not conflict.

**Section placement cannot be batched** because it requires a preceding GET to resolve the section GID.

#### (e) Error handling for partial batch failures

The existing `BatchClient` handles partial failures well (models.py:119-147): each `BatchResult` has independent `success`/`error` properties. However, the current configure phase has per-step error handling with specific warning messages and graceful degradation:

```python
# Step b (due date)
except Exception as e:
    warnings.append(f"Due date set failed: {e}")

# Step e (hierarchy)
except Exception as e:
    warnings.append(f"Hierarchy placement failed: {e}")
```

Converting to batch would require:
1. Collecting independent operations
2. Sending one batch
3. Mapping `BatchResult` items back to original operations for error reporting
4. Maintaining the same warning semantics per step

This is feasible but adds indirection and complexity to error reporting.

#### (f) Count of independent API calls that could be batched

From step (b) analysis, the genuinely batchable independent calls are:

| Call | Current | Batchable? |
|------|---------|-----------|
| Section list (GET) | 1 call | No (needs result for POST) |
| Section addTask (POST) | 1 call | No (depends on GET result) |
| Due date (PUT) | 1 call | **Yes** |
| Subtask wait (GET polling) | 0-3 calls | No (polling) |
| Seeding fetch (GET) | 1 call | No (needs result for PUT) |
| Seeding write (PUT) | 1 call | No (depends on GET) |
| Hierarchy (PUT) | 1 call | **Yes** |
| Assignee (PUT) | 1 call | **Yes** |

**3 calls are batchable** (due date, hierarchy, assignee). All three are PUTs to the same task GID with non-overlapping fields.

**But**: These 3 PUTs could also be combined into a **single PUT** with all three field updates in one `tasks.update_async()` call, which is simpler than batching and avoids the Asana batch API entirely:

```python
await client.tasks.update_async(
    new_task.gid,
    due_on=due_date,
    parent=holder_gid,
    assignee=assignee_gid,
)
```

This is a merge optimization, not a batch optimization. And it would require restructuring `_configure_async` to collect all write fields upfront and apply them in a single call -- a different (and simpler) approach than batch API.

### Verdict Rationale: NO-GO

The GO criteria was "saves 2+ API calls per creation" via Asana batch API. The investigation reveals:

1. **Only 3 out of 5-8 calls are independent** (due date, hierarchy, assignee). The rest have data dependencies that prevent batching.

2. **Those 3 independent calls can be merged into 1 regular PUT** without using the batch API at all. The batch API is overkill for combining 3 PUTs to the same task.

3. **Ordering constraints are real**: Section placement requires a preceding GET, subtask waiting is a polling loop, and seeding depends on subtask completion. Batch API cannot help with these dependencies.

4. **Error handling complexity**: The current per-step error handling with specific warnings would need to be restructured for batch result mapping. The complexity cost exceeds the benefit.

5. **Net savings via batch API: 2 calls** (3 independent calls become 1 batch). But a simple field-merge approach (combine all PUTs into one) achieves the same savings without batch API complexity.

6. **The field-merge approach is already partially addressed by IMP-02** (AutoCascadeSeeder/FieldSeeder double-fetch elimination), which consolidates the seeding write path.

The Asana batch API is the wrong tool for this problem. The real optimization is consolidating sequential PUTs to the same task into a single PUT -- and that is a simpler implementation that does not require the batch API machinery.

### Risks (if this were pursued)

1. **Last-write-wins on same GID**: Multiple PUTs to the same task in one batch may produce race conditions if Asana processes them concurrently. Non-overlapping fields should be safe, but this is undocumented behavior.
2. **Error reporting regression**: Batch results are positional, making per-step error messages harder to correlate.
3. **Batch API limit (10 actions)**: Not a concern for 3 actions, but adds an architectural dependency on the batch client for a simple case.

### Affected Files

N/A -- NO-GO, no changes recommended. Consider a simpler field-merge optimization (combine independent PUTs into single update call) as a minor boy-scout improvement when IMP-02 touches the configure phase.

---

## Summary Table

| Spike | Verdict | Score | Rationale |
|-------|---------|-------|-----------|
| S0-SPIKE-07 | **NO-GO** | 52 | Maximum 2 section listings per project per transition (template discovery + section placement). Cascade calls target different projects. IMP-07 already eliminates the template discovery listing, reducing to 1 call per project. Below the >2 threshold. |
| S0-SPIKE-11 | **NO-GO** | 42 | Only 3 of 5-8 configure calls are independent (due date, hierarchy, assignee). These can be merged into a single PUT without batch API. Ordering dependencies prevent batching the remaining calls. Batch API is the wrong tool for this problem. |
