---
name: Cascade Warming API Path Design
description: TDD produced for warming cascade store on DataFrame API endpoint path -- root cause was 3 compounding defects in build_project_dataframe()
type: project
---

TDD-cascade-warming-api-path produced at `.ledge/specs/tdd-cascade-warming-api-path.md` (2026-03-25).

Root cause: 3 compounding defects in DataFrameService.build_project_dataframe():
1. TASK_OPT_FIELDS missing `parent`/`parent.gid` -- tasks fetched without parent references
2. UnifiedTaskStore created but never populated with fetched tasks
3. No hierarchy warming -- parent task data never fetched

**Why:** asset_edit schema cascade columns (cascade:Vertical, cascade:Office Phone) always resolve to None on API path because the resolution infrastructure has no data to search.

**How to apply:** The fix is localized to DataFrameService: add parent fields to TASK_OPT_FIELDS, add _warm_cascade_store() method that calls put_batch_async(warm_hierarchy=True), invoke it before extraction. No changes to ViewPlugin or CascadePlugin. MAX_CASCADE_PARENTS=50 safety bound. Section endpoint deferred (uses SectionDataFrameBuilder which doesn't support cascade: resolution).
