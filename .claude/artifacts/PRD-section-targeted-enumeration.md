# PRD: Section-Targeted Workflow Enumeration

```yaml
id: PRD-SECTION-ENUM-001
status: DRAFT
date: 2026-02-15
author: requirements-analyst
impact: low
impact_categories: []
```

---

## 1. Problem Statement

Three automation workflows enumerate Asana tasks by fetching **all tasks from entire projects** via `tasks.list_async(project=...)` and then discarding tasks that belong to irrelevant sections. The Asana API natively supports section-level task listing via `tasks.list_async(section=<gid>)`, which is already wired in our `TasksClient` and used by the DataFrame layer. The workflow layer is the **only caller pattern** still using project-level fetch with client-side filtering.

### Quantified Waste

| Workflow | Project(s) | Total Sections | Sections Used | Waste Ratio | Amplification |
|----------|-----------|----------------|---------------|-------------|---------------|
| InsightsExport | 1 (Offer, 33 sections) | 33 | 21 (ACTIVE only) | ~36% of tasks fetched are discarded | Each discarded offer triggers **9 API calls** to autom8_data before discard |
| ConversationAudit | 1 (ContactHolder) | Unknown (spike needed) | Unknown | Unknown until spike | Each discarded holder triggers **depth=2 Business hydration** (~3 API calls) before skip |
| PipelineTransition | 8 pipeline projects | N per project | 2 per project (CONVERTED, DID NOT CONVERT) | All sections except 2 are wasted | None (no downstream calls for discarded tasks) |

### Amplification Effects

The waste is not limited to Asana API calls. For **InsightsExport**, each offer that passes enumeration triggers 9 concurrent API calls to autom8_data (SUMMARY, APPOINTMENTS, LEADS, BY QUARTER, BY MONTH, BY WEEK, AD QUESTIONS, ASSET TABLE, OFFER TABLE). Offers in non-ACTIVE sections (INACTIVE, ACTIVATING, IGNORED) are fetched, classified, and discarded -- but only after all 33 sections' tasks have been retrieved from Asana. With section-targeted fetch, the 12 non-ACTIVE sections' tasks are never fetched at all.

For **ConversationAudit**, each holder that survives enumeration resolves its parent Business via `_resolve_business_activity()`, which calls `hydrate_from_gid_async(depth=2)`. The `_activity_map` dedup cache mitigates repeated hydrations for holders sharing a parent Business, but the fundamental waste of fetching ALL holders before filtering remains.

For **PipelineTransition**, the waste is pure Asana API bandwidth -- fetching all tasks across all sections of 8 projects when only 2 sections per project contain actionable tasks. No downstream amplification occurs because non-matching tasks are discarded before any further processing.

---

## 2. Stakeholders

| Stakeholder | Impact | Interest |
|-------------|--------|----------|
| Automation scheduler (EventBridge/Lambda) | Primary consumer -- reduced execution time and API quota usage | Faster workflow cycles, lower rate-limit pressure |
| Asana API quota | Fewer paginated requests per workflow cycle | Stays within rate limits during peak scheduling |
| autom8_data service | Fewer wasted insight/export calls from inactive entities | Reduced load from discarded-offer amplification |
| Workflow test suite | Mock patterns must change from project-level to section-level | Test reliability (MagicMock currently hides API surface mismatches) |
| InsightsExportWorkflow | Direct code change in `_enumerate_offers()` | Eliminates ~36% wasted Asana + ~36% wasted autom8_data calls |
| ConversationAuditWorkflow | Direct code change in `_enumerate_contact_holders()` (gated on spike) | Eliminates fetch of inactive holders |
| PipelineTransitionWorkflow | Direct code change in `_enumerate_processes_async()` | Reduces from N-section fetch to 2-section fetch per project |

---

## 3. User Stories

### US-1: Pipeline Transition Section-Targeted Enumeration
**As** the pipeline transition scheduler,
**I want** to fetch only tasks in CONVERTED and DID NOT CONVERT sections,
**so that** I avoid fetching all tasks across all sections of 8 pipeline projects.

**Acceptance Criteria:**
- AC-1.1: `_enumerate_processes_async()` resolves section GIDs for CONVERTED and DID NOT CONVERT by name using `SectionsClient.list_for_project_async()`.
- AC-1.2: Task enumeration uses `tasks.list_async(section=<gid>)` for each resolved section, not `tasks.list_async(project=...)`.
- AC-1.3: Tasks from both sections are merged into a single list with correct outcome tagging ("converted" / "did_not_convert").
- AC-1.4: If section GID resolution fails for a project (section not found or API error), the workflow falls back to project-level fetch for that project and logs a warning.
- AC-1.5: All existing PipelineTransition tests pass with updated mocks.
- AC-1.6: `completed_since="now"` filter is preserved on section-level fetches.

### US-2: Insights Export Section-Targeted Enumeration
**As** the insights export scheduler,
**I want** to fetch only tasks in ACTIVE sections of the Offer project,
**so that** I avoid fetching and then discarding tasks from ACTIVATING, INACTIVE, and IGNORED sections.

**Acceptance Criteria:**
- AC-2.1: `_enumerate_offers()` uses `OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)` to determine which section names to fetch.
- AC-2.2: Section names are resolved to GIDs via `SectionsClient.list_for_project_async()`.
- AC-2.3: Task enumeration uses `tasks.list_async(section=<gid>)` per ACTIVE section.
- AC-2.4: The post-hoc classification loop (lines 282-297 of current code) is no longer needed for ACTIVE filtering, because only ACTIVE sections are fetched. The `OFFER_CLASSIFIER.classify()` call is removed or retained only as a defensive assertion.
- AC-2.5: If section GID resolution fails, the workflow falls back to project-level fetch with client-side classification (current behavior) and logs a warning.
- AC-2.6: All existing InsightsExport tests pass with updated mocks.
- AC-2.7: `completed_since="now"` filter is preserved on section-level fetches.
- AC-2.8: `opt_fields` include `parent` and `parent.name` (required by `_process_offer()`).

### US-3: Conversation Audit Section-Targeted Enumeration (Gated)
**As** the conversation audit scheduler,
**I want** to fetch only tasks from sections corresponding to active businesses,
**so that** I avoid fetching holders whose parent Business is inactive (which triggers wasted depth=2 hydration).

**Acceptance Criteria:**
- AC-3.1: A spike determines what sections exist in the ContactHolder project (GID `1201500116978260`) and whether they map to activity categories.
- AC-3.2: **If sections map to activity categories**: A `CONTACT_HOLDER_CLASSIFIER` is created (or equivalent mapping) and section-targeted fetch is implemented following the same pattern as US-2.
- AC-3.3: **If sections do NOT map to activity categories**: An alternative optimization is defined. Options include: (a) pre-resolve parent Business GIDs in bulk before individual holder processing, (b) batch the `_activity_map` population as a pre-enumeration step, (c) accept the current pattern as optimal for this workflow.
- AC-3.4: If section-targeted fetch is implemented, fallback to project-level fetch on section resolution failure.
- AC-3.5: The existing `_activity_map` dedup cache is preserved regardless of approach.
- AC-3.6: All existing ConversationAudit tests pass.

### US-4: Fallback Resilience
**As** the workflow execution layer,
**I want** section resolution failures to fall back gracefully to project-level fetch,
**so that** a transient Asana API error in section listing does not block an entire workflow cycle.

**Acceptance Criteria:**
- AC-4.1: Each workflow's section resolution step is wrapped in error handling.
- AC-4.2: On failure, the workflow reverts to `tasks.list_async(project=...)` with client-side filtering (current behavior).
- AC-4.3: A structured log event is emitted at WARNING level with the project GID and error details.
- AC-4.4: The fallback path is tested explicitly (mock section resolution failure, verify project-level fetch is used).

---

## 4. Functional Requirements

### FR-1: Section GID Resolution (MUST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | For each affected workflow, resolve target section names to GIDs by calling `SectionsClient.list_for_project_async(project_gid)` and matching by name (case-insensitive). | MUST |
| FR-1.2 | Section name matching must be case-insensitive to match SectionClassifier behavior (all keys stored lowercase). | MUST |
| FR-1.3 | Section list caching (30 min TTL) already exists in `SectionsClient.list_for_project_async()`. No additional workflow-level caching is required. Architect may override. | SHOULD |
| FR-1.4 | If a target section name does not match any returned section, log a WARNING and exclude it from fetch (do not error). | MUST |

### FR-2: PipelineTransition Migration (MUST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Replace the per-project `list_async(project=...)` call with per-section `list_async(section=<gid>)` calls for CONVERTED and DID NOT CONVERT sections. | MUST |
| FR-2.2 | Retain the per-project loop structure (8 projects). Within each project: resolve 2 section GIDs, fetch 2 section task lists, tag each task with its outcome. | MUST |
| FR-2.3 | Remove the inline section-name extraction loop (lines 260-280 of current code) since section membership is implicit from the fetch target. | MUST |
| FR-2.4 | The `Process.model_validate(task)` call is preserved -- only the enumeration source changes. | MUST |
| FR-2.5 | If neither CONVERTED nor DID NOT CONVERT sections exist in a project, skip that project (log INFO) rather than fetching all tasks. | SHOULD |

### FR-3: InsightsExport Migration (MUST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Replace `list_async(project=OFFER_PROJECT_GID)` with section-level fetches targeting only sections classified as ACTIVE by `OFFER_CLASSIFIER`. | MUST |
| FR-3.2 | Use `OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)` to determine target section names (21 sections). | MUST |
| FR-3.3 | Fetch tasks from all 21 ACTIVE sections. Tasks from multiple sections must be merged and deduplicated by GID (multi-homed tasks). | MUST |
| FR-3.4 | Remove or simplify the post-hoc classification loop. Since only ACTIVE sections are fetched, the `OFFER_CLASSIFIER.classify()` call is redundant for filtering purposes. | SHOULD |
| FR-3.5 | `opt_fields` on section-level fetches must include the same fields currently requested: `name`, `completed`, `parent`, `parent.name`, `memberships.section.name`. Note: `memberships.section.name` may be reducible since section identity is now known from the fetch target. Architect decides. | MUST |

### FR-4: ConversationAudit Migration (SHOULD -- gated on spike)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | Execute a spike to enumerate sections in project `1201500116978260` and determine if they map to activity categories. | MUST (spike is MUST; implementation is SHOULD) |
| FR-4.2 | If sections map to activity: create a classifier or mapping and implement section-targeted fetch following FR-1 and FR-3 patterns. | SHOULD |
| FR-4.3 | If sections do NOT map to activity: document the finding and define an alternative optimization. The current `_activity_map` pattern is acceptable as the baseline. | SHOULD |
| FR-4.4 | Regardless of spike outcome, the existing `_resolve_business_activity()` with its dedup `_activity_map` cache must be preserved as a correctness guard. | MUST |

### FR-5: Fallback Behavior (MUST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | If `list_for_project_async()` fails (network error, 5xx, timeout), fall back to `list_async(project=...)` with client-side filtering. | MUST |
| FR-5.2 | If section name resolution produces zero matching sections (none of the expected section names found in the API response), fall back to project-level fetch. | MUST |
| FR-5.3 | Fallback events are logged at WARNING with structured fields: `workflow_id`, `project_gid`, `error_type`, `error_message`. | MUST |
| FR-5.4 | Fallback is per-project (PipelineTransition) or per-workflow-cycle (InsightsExport, ConversationAudit). A fallback in one pipeline project does not trigger fallback for other projects. | SHOULD |

---

## 5. Non-Functional Requirements

| ID | Category | Requirement | Target | Priority |
|----|----------|-------------|--------|----------|
| NFR-1 | Latency | Section-targeted enumeration must not increase overall workflow execution time compared to project-level fetch. Parallel section fetches should match or beat serial project-level fetch. | <= current wall-clock time | MUST |
| NFR-2 | API Efficiency | InsightsExport Asana API calls for enumeration reduced from ~1 paginated project-level call to 21 section-level calls (parallelizable). Net API call count may increase, but bandwidth (tasks returned) decreases ~36%. | Measurable reduction in total tasks fetched | MUST |
| NFR-3 | API Efficiency | PipelineTransition Asana API calls per project reduced from 1 project-level call to 2 section-level calls + 1 section list call. | 3 calls per project (section list + 2 section fetches) vs. 1 call returning all tasks | MUST |
| NFR-4 | Resilience | Fallback to project-level fetch must activate within the same workflow cycle (no retry-later / dead-letter). | Immediate fallback | MUST |
| NFR-5 | Observability | Each workflow logs: (a) number of sections targeted, (b) number of tasks enumerated, (c) whether fallback was activated. | Structured log events | SHOULD |
| NFR-6 | Cache Behavior | Section list caching (30 min TTL) via `SectionsClient` is sufficient. No new caching layers required. | Rely on existing SectionsClient cache | SHOULD |
| NFR-7 | Concurrency | For InsightsExport (21 parallel section fetches), concurrency must be bounded by a semaphore. Architect determines the limit (precedent: `ParallelSectionFetcher.max_concurrent=8`). | Bounded concurrency | SHOULD |

---

## 6. ContactHolder Spike (Gated Requirement)

### Purpose

Determine whether the ContactHolder project (`1201500116978260`) has sections that map to activity categories, which would enable section-targeted fetch.

### Spike Deliverables

1. **Section inventory**: List all sections in the ContactHolder project with their names and GIDs.
2. **Activity mapping assessment**: Do section names correspond to activity states (e.g., "Active", "Inactive", "Onboarding")?
3. **Recommendation**: One of:
   - (a) **Section-targeted fetch viable**: Define the classifier mapping and proceed with FR-4.2.
   - (b) **No clean mapping**: Document why, and specify what (if any) alternative optimization to pursue.
   - (c) **Hybrid**: Some sections map cleanly; others require the existing hydration gate.

### Decision Gate

The spike outcome determines FR-4.2 vs. FR-4.3. The spike itself is MUST priority; the subsequent implementation is SHOULD.

### Timing

The spike can execute in parallel with US-1 (PipelineTransition) and US-2 (InsightsExport) since those workflows have no dependency on ContactHolder findings.

---

## 7. Design Decision Boundaries

These decisions are **scoped for the architect** -- the PRD defines the problem space; the architect defines the solution space.

### DD-1: Shared SectionFilteredEnumerator vs. Per-Workflow Inline

**Context**: All three workflows need the same pattern: resolve section names to GIDs, fetch tasks per section, merge results. `ParallelSectionFetcher` already implements this pattern for the DataFrame layer.

**Options to evaluate**:
- (a) Extract a reusable `SectionFilteredEnumerator` class used by all three workflows.
- (b) Each workflow implements section-level fetch inline (3 independent implementations).
- (c) Generalize `ParallelSectionFetcher` to serve both DataFrame and workflow use cases.

**Constraints**: The solution must handle the fallback requirement (FR-5) regardless of option chosen. Workflow-specific concerns (e.g., outcome tagging in PipelineTransition, classifier integration in InsightsExport) must not leak into a shared primitive.

### DD-2: Section GID Resolution Caching

**Context**: `SectionsClient.list_for_project_async()` already caches section lists with a 30 min TTL and batch-populates individual section cache entries. The question is whether workflow-level code needs additional caching of the section-name-to-GID mapping.

**Constraints**: The PRD requires no new caching layers (NFR-6 SHOULD). If the architect determines that the SectionsClient cache is insufficient (e.g., cold-start penalty for 8 pipeline projects), they may add workflow-level caching.

### DD-3: Concurrency Model for Multi-Section Fetch

**Context**: InsightsExport needs 21 parallel section fetches. PipelineTransition needs 2 per project times 8 projects (16 total, or 2 at a time sequentially). `ParallelSectionFetcher` uses `asyncio.Semaphore(max_concurrent=8)`.

**Constraints**: Must not exceed Asana API rate limits. Must not starve other concurrent workflows.

### DD-4: opt_fields Reduction

**Context**: Current project-level fetches request `memberships.section.name` to enable client-side classification. With section-targeted fetch, section identity is known from the fetch target. This field may be droppable, reducing response payload.

**Constraints**: Some workflows may still need `memberships.section.name` for logging or downstream processing. Architect determines which fields remain necessary per workflow.

---

## 8. Out of Scope

The following items are explicitly **deferred** and will NOT be addressed in this initiative:

| Item | Reason | Deferred To |
|------|--------|-------------|
| Dead code removal (post-hoc classification loops) | Valuable but not required for functionality. Removing classification code is a cleanup task. | Phase 3 / hygiene rite |
| DRY extraction of `extract_section_name()` across 4+ callers | Section extraction duplication exists in BaseExtractor, DataFrameViewPlugin, Process, and pipeline_transition inline. Worth consolidating but orthogonal. | Hygiene rite |
| Observability dashboard for API call savings | Structured logs are emitted (NFR-5), but building a dashboard or alert is out of scope. | Operations backlog |
| Extension to other project-level enumerations | Other parts of the codebase may use project-level fetch. This initiative targets only the 3 identified workflows. | Future initiative |
| ParallelSectionFetcher refactoring | The existing `ParallelSectionFetcher` in the DataFrame layer may benefit from generalization, but changing it is not required for this initiative. | Architect decides if beneficial |
| ContactHolder project section creation/modification | If the spike reveals no useful section structure, we do not create new sections in Asana. | Out of scope entirely |

---

## 9. Dependencies

### Existing Infrastructure (Leverage -- No Changes Required)

| Component | Location | Role |
|-----------|----------|------|
| `TasksClient.list_async(section=<gid>)` | `src/autom8_asana/clients/tasks.py:459` | Section-level task fetch (already implemented, used by 3+ callers) |
| `SectionsClient.list_for_project_async()` | `src/autom8_asana/clients/sections.py:306` | Section enumeration with cache population (30 min TTL) |
| `SectionClassifier` + `OFFER_CLASSIFIER` | `src/autom8_asana/models/business/activity.py:53,178` | Section-to-activity mapping with `sections_for()` and `active_sections()` |
| `extract_section_name()` | `src/autom8_asana/models/business/activity.py:138` | Canonical section extraction (available if needed for fallback) |
| `ParallelSectionFetcher` | `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Reference implementation of parallel section fetch pattern |
| Project registry | `src/autom8_asana/core/project_registry.py` | All project GIDs centralized |
| `all_pipeline_project_gids()` | `src/autom8_asana/core/project_registry.py:157` | Returns 8 pipeline project GIDs |

### Completed Prior Work (Foundation)

| Work Item | Status | Relevance |
|-----------|--------|-----------|
| P0: API bug fix (`list_for_project_async` -> `list_async`) | COMPLETE | All 3 workflows now use correct `list_async(project=...)` |
| P1: Entity activity properties (Offer.account_activity, etc.) | COMPLETE | Available for defensive assertions post-migration |
| P2: Activity filtering in InsightsExport | COMPLETE | Current code already filters by ACTIVE; this initiative eliminates the fetch-then-filter pattern |

### External Dependencies

None. No new client methods, no new Asana API endpoints, no cross-service changes.

---

## 10. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R-1 | **ContactHolder project has no meaningful section structure** | Medium | Low | Spike (FR-4.1) runs in parallel with US-1/US-2. If no mapping exists, ConversationAudit retains current pattern. Net value still delivered for InsightsExport and PipelineTransition. |
| R-2 | **Section names drift in Asana** (renamed/added/removed) | Low | Medium | Fallback to project-level fetch (FR-5) handles this gracefully. Additionally, OFFER_CLASSIFIER already has 33 sections mapped -- section name changes are rare and coordinated. |
| R-3 | **Mock cascade in test suite** | High | Low | All 3 workflow test files use `MagicMock` for `tasks.list_async`. Changing from `project=` to `section=` requires updating mock setup and assertions in ~15-20 test cases across 3 files. Tedious but mechanically straightforward. |
| R-4 | **API call count increases (more calls, less data per call)** | Medium | Low | Current: 1 paginated call returning N tasks. New: K section calls returning N' < N tasks. Total API calls increase but total data transferred decreases. Rate limit pressure is bounded by concurrency semaphore (NFR-7). |
| R-5 | **Section-level fetch lacks `completed_since` support** | Low | High | Verified: `TasksClient.list_async(section=..., completed_since=...)` passes `completed_since` as a query parameter. This filter is supported on section-level fetches per Asana API documentation. No risk. |
| R-6 | **Multi-homed tasks appear in multiple ACTIVE sections** | Low | Low | Deduplication by GID (FR-3.3) handles this. Same pattern used by `ParallelSectionFetcher.fetch_all()`. |
| R-7 | **21 parallel section fetches for InsightsExport overwhelm rate limits** | Low | Medium | Semaphore-bounded concurrency (NFR-7). Precedent: `ParallelSectionFetcher` uses max_concurrent=8. Architect determines appropriate limit. |

---

## 11. MoSCoW Prioritization

### MUST Have

| Item | Rationale |
|------|-----------|
| PipelineTransition migration (US-1) | Cleanest case, highest waste ratio per project, zero ambiguity about target sections |
| InsightsExport migration (US-2) | Highest amplification cost (9 autom8_data calls per wasted offer) |
| Fallback to project-level fetch (US-4) | Resilience requirement -- cannot allow section resolution failure to block entire workflow cycle |
| Section GID resolution via SectionsClient (FR-1) | Foundation for all section-targeted fetches |
| ContactHolder spike execution (FR-4.1) | Required to unblock SHOULD items; low cost to execute |

### SHOULD Have

| Item | Rationale |
|------|-----------|
| ConversationAudit migration (US-3) | Gated on spike outcome; delivers value if sections map to activity categories |
| Observability logging (NFR-5) | Validates API savings, supports operational monitoring |
| Bounded concurrency for multi-section fetch (NFR-7) | Prevents rate limit issues with 21 parallel fetches |

### COULD Have

| Item | Rationale |
|------|-----------|
| Shared SectionFilteredEnumerator primitive (DD-1) | Reduces duplication across 3 workflows; architect decides if warranted |
| opt_fields reduction (DD-4) | Minor payload optimization; depends on whether `memberships.section.name` is still needed |

### WON'T Have (This Initiative)

| Item | Rationale |
|------|-----------|
| Dead code removal from post-hoc classification | Deferred to Phase 3 / hygiene rite |
| DRY section extraction consolidation | Orthogonal tech debt; deferred to hygiene rite |
| Observability dashboard | Deferred to operations backlog |
| Extension to non-workflow project-level fetches | Future initiative |
| ParallelSectionFetcher generalization | Only if architect determines it beneficial |

---

## 12. Success Criteria (Testable)

| ID | Criterion | Measurement | Owner |
|----|-----------|-------------|-------|
| SC-1 | Zero `list_async(project=...)` calls in workflow `_enumerate_*` methods (excluding fallback paths) | Code review: grep for `project=` in enumeration methods | QA Adversary |
| SC-2 | All 3 workflow `_enumerate_*` methods use `list_async(section=...)` as primary path | Code review + test verification | QA Adversary |
| SC-3 | InsightsExport enumerates only ACTIVE-classified tasks (21 sections, not 33) | Unit test: verify `list_async` called with section GIDs corresponding to ACTIVE sections only | QA Adversary |
| SC-4 | PipelineTransition fetches exactly 2 sections per project (CONVERTED + DID NOT CONVERT) | Unit test: verify `list_async` called 2 times per project with correct section GIDs | QA Adversary |
| SC-5 | Fallback to project-level fetch on section resolution failure | Unit test: mock section resolution failure, verify `list_async(project=...)` is called | QA Adversary |
| SC-6 | All existing tests pass with updated mocks | CI green on `tests/unit/automation/workflows/` | QA Adversary |
| SC-7 | ContactHolder spike completed with documented recommendation | Artifact: spike document in `docs/spikes/` | Requirements Analyst |
| SC-8 | Structured log events emitted for section-targeted enumeration | Unit test: verify log events contain `sections_targeted`, `tasks_enumerated`, `fallback_activated` fields | QA Adversary |

---

## 13. Open Questions

None. All blocking questions are resolved:

- **Q: Does `tasks.list_async(section=..., completed_since=...)` work?** -- Yes, verified in `TasksClient.list_async()` implementation (line 459-528). The `completed_since` parameter is passed regardless of whether `project` or `section` is specified.
- **Q: What is the ContactHolder section structure?** -- Explicitly gated as a spike (FR-4.1). The spike is MUST priority; implementation is SHOULD, gated on spike outcome.
- **Q: Will 21 parallel section fetches cause rate limit issues?** -- Mitigated by semaphore-bounded concurrency (NFR-7). Precedent: `ParallelSectionFetcher` successfully uses this pattern.

---

## Attestation Table

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/PRD-section-targeted-enumeration.md` | Read |
| InsightsExport source | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/insights_export.py` | Read |
| ConversationAudit source | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/conversation_audit.py` | Read |
| PipelineTransition source | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/pipeline_transition.py` | Read |
| SectionClassifier + OFFER_CLASSIFIER | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/activity.py` | Read |
| TasksClient (section kwarg) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` | Read |
| SectionsClient (list_for_project_async) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | Read |
| ParallelSectionFetcher (reference pattern) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/parallel_fetch.py` | Read |
| Project registry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/project_registry.py` | Read |
| ContactHolder model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/contact.py` | Read |
| Prior spike | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-workflow-activity-gap-analysis.md` | Read |
| Initiative brief | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/PROMPT-0-section-targeted-enumeration.md` | Read |
