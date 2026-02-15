# INIT: Section-Targeted Workflow Enumeration

## Problem Statement

Three automation workflows enumerate tasks by fetching ALL tasks from an entire Asana
project via `tasks.list_async(project=...)` and then post-hoc filter by section
membership. This is architecturally naive because:

1. The Asana API natively supports section-level task listing via
   `tasks.list_async(section=<gid>)` — it is already wired in our TasksClient.
2. The SectionClassifier module already maps section names to activity categories
   (ACTIVE, ACTIVATING, INACTIVE, IGNORED) with O(1) lookup.
3. The ParallelSectionFetcher already implements parallel section-level fetch
   for the DataFrame layer.
4. The workflow layer is the ONLY caller pattern still using project-level fetch +
   client-side filtering.

The result: ~40% of API bandwidth is wasted fetching tasks that are immediately
discarded. For InsightsExport, each wasted offer then triggers 9 additional API
calls to autom8_data before being discarded. For ConversationAudit, each wasted
holder triggers expensive depth=2 Business hydration before being skipped.

## Three Affected Workflows

### 1. InsightsExportWorkflow._enumerate_offers()
- File: `src/autom8_asana/automation/workflows/insights_export.py` (line ~253)
- Project: OFFER_PROJECT_GID = "1143843662099250" (33 sections)
- Current: `list_async(project=...) → collect() → for each: classify → keep ACTIVE`
- Desired: Resolve ACTIVE section GIDs → `list_async(section=<gid>)` per section → merge
- Context: OFFER_CLASSIFIER (21 active, 5 activating, 3 inactive, 4 ignored sections)
  already knows which sections are ACTIVE. The client-side classification loop
  becomes unnecessary after this change.

### 2. ConversationAuditWorkflow._enumerate_contact_holders()
- File: `src/autom8_asana/automation/workflows/conversation_audit.py` (line ~221)
- Project: CONTACT_HOLDER_PROJECT_GID = "1201500116978260"
- Current: `list_async(project=...) → collect() → return all non-completed`
  Then in `_process_holder()`, each holder resolves parent Business activity
  via depth=2 hydration — expensive and redundant.
- Desired: Either (a) create a CONTACT_HOLDER_CLASSIFIER and do section-level
  fetch, or (b) map ContactHolder sections to Business activity zones. This
  workflow may need a spike to determine the right section-to-activity mapping
  since ContactHolder sections might not map 1:1 to activity categories.
- Note: The `_activity_map` dedup cache already optimizes the current pattern
  but doesn't eliminate the fundamental waste of fetching ALL holders first.

### 3. PipelineTransitionWorkflow._enumerate_processes_async()
- File: `src/autom8_asana/automation/workflows/pipeline_transition.py` (line ~225)
- Projects: 8 pipeline projects (SALES, OUTREACH, ONBOARDING, IMPLEMENTATION,
  RETENTION, REACTIVATION, ACCOUNT_ERROR, EXPANSION)
- Current: For each project, `list_async(project=...) → collect() → for each:
  check if section name matches CONVERTED or DID NOT CONVERT`
- Desired: For each project, resolve the GIDs of CONVERTED and DID_NOT_CONVERT
  sections, then `list_async(section=<gid>)` for just those 2 sections.
- This is the cleanest case — exactly 2 known section names per project.

## Existing Infrastructure to Leverage

### TasksClient.list_async(section=<gid>)
- File: `src/autom8_asana/clients/tasks.py` (line ~459)
- Already supports `section` kwarg — no client changes needed.
- Already used by: TemplateDiscovery (templates.py), ProgressiveFetcher
  (progressive.py), FreshnessProbe (freshness.py).

### SectionsClient.list_for_project_async(project_gid)
- File: `src/autom8_asana/clients/sections.py` (line ~306)
- Returns PageIterator[Section] with automatic cache population.
- Already used by 7+ callers.

### SectionClassifier.sections_for(*categories) -> frozenset[str]
- File: `src/autom8_asana/models/business/activity.py` (line 80)
- Returns lowercase section names matching given categories.
- `active_sections()` and `billable_sections()` convenience methods exist.
- OFFER_CLASSIFIER and UNIT_CLASSIFIER are module-level singletons.

### ParallelSectionFetcher
- File: `src/autom8_asana/dataframes/builders/parallel_fetch.py`
- Implements: list sections → parallel fetch per section → dedup by GID.
- Could be generalized or its pattern extracted for workflow use.

### extract_section_name(task, project_gid)
- File: `src/autom8_asana/models/business/activity.py` (line 138)
- Canonical section extraction — currently duplicated 4x across codebase.
- Relevant for DRYing the inline extraction in pipeline_transition.py.

## Key Design Decisions to Make

1. **Reusable primitive vs. per-workflow inline**: Should we build a
   `SectionFilteredEnumerator` that all three workflows share, or should each
   workflow implement section-level fetch inline? The ParallelSectionFetcher
   is a precedent for a shared primitive.

2. **Section GID resolution caching**: Section-to-GID mapping changes rarely.
   The sections client already caches section lists (30 min TTL). Should the
   workflow-level resolution also cache, or rely on the client-level cache?

3. **ContactHolder classification**: Unlike Offers and Pipeline processes,
   ContactHolders may not have a clean section-to-activity mapping. The spike
   should determine: (a) what sections exist in the ContactHolder project,
   (b) whether they map to activity states, (c) whether the hydration-based
   gate can be fully replaced.

4. **Fallback behavior**: If section GID resolution fails (API error, missing
   section), should we fall back to project-level fetch? The
   ParallelSectionFetcher has this pattern.

## Project Context

### Testing
- Pytest path: `.venv/bin/pytest tests/ -x -q --timeout=60`
- Test count: ~9500 tests
- Pre-existing failures: test_adversarial_pacing.py, test_paced_fetch.py,
  test_parallel_fetch.py::test_cache_errors_logged_as_warnings
- slowapi import failures (all api/ and related test dirs)
- All workflow tests use MagicMock — the mocks need updating to match new
  call patterns.

### Project Registry
- File: `src/autom8_asana/core/project_registry.py`
- All project GIDs centralized. Pipeline projects: 8 total.
- Entity projects: OFFER_PROJECT, CONTACT_HOLDER_PROJECT, UNIT_PROJECT, etc.

### Related Completed Work
- SPIKE: `docs/spikes/SPIKE-workflow-activity-gap-analysis.md` (complete)
- Activity module: `models/business/activity.py` — wired with entity properties
  and __init__.py exports (Offer.account_activity, Unit.account_activity,
  Business.max_unit_activity)
- P0 (API bug fix: list_for_project_async → list_async), P1 (entity properties),
  P2 (activity filtering) — ALL DONE in prior session.
- The current code already uses `list_async(project=...)` correctly and
  already filters by activity. This initiative is the NEXT optimization layer:
  eliminating the project-level fetch entirely.

## Proposed Workflow

### Phase 1: Spike (10x-dev requirements phase)
1. Enumerate actual sections in ContactHolder project (API call or known mapping)
2. Determine if ContactHolder sections map to activity categories
3. Quantify waste: count tasks per section across affected projects
4. Design the section-filtered enumeration pattern (shared primitive vs inline)

### Phase 2: Implementation (10x-dev)
1. PipelineTransitionWorkflow — cleanest case, exactly 2 sections per project
2. InsightsExportWorkflow — OFFER_CLASSIFIER provides the mapping
3. ConversationAuditWorkflow — depends on spike findings
4. Contract tests: verify section-level fetch returns subset of project-level fetch
5. Integration test: mock section list + section-level task lists

### Phase 3: Optimization Squeeze (hygiene rite)
1. Remove now-dead client-side classification code in insights_export
2. Remove or simplify the hydration-based activity gate in conversation_audit
3. DRY section extraction: replace inline copies with extract_section_name()
4. Add observability: log API calls saved vs project-level baseline
5. Consider extending to other project-level enumerations if any exist

## Success Criteria
- Zero project-level task enumerations in workflow code
- All workflow _enumerate_* methods use section-level fetch
- API call count reduced by ~40% for InsightsExport and ConversationAudit
- PipelineTransition API calls reduced from N*all_tasks to N*2_sections
- All existing tests pass (updated mocks)
- Fallback to project-level fetch on section resolution failure

## Session Configuration
- Rite: 10x-dev (primary), hygiene (Phase 3 squeeze)
- Entry: `/go` then select 10x-dev
- This is a fresh session — no prior session state to continue
- Start with: `/spike` for Phase 1, then `/build` for Phase 2, then `/hygiene` for Phase 3
