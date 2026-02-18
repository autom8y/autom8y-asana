# Pipeline Parity Post-WS6 Analysis (U-001)

**Sprint:** session-20260218-172712-e748524b
**Date:** 2026-02-18
**Branch:** sprint/arch-u005-si5-u001

---

## WS6 Verification

WS6 commits confirmed on branch (via `git log --oneline --grep="RF-00"`):

```
af09b74 refactor(preload,business): annotate legacy fallback and import-time registration [RF-012]
44a6700 refactor(lifecycle): wire creation.py to shared creation helpers [RF-007]
d28c352 refactor(automation): promote seeding helper functions to public API [RF-006]
3d6ecff refactor(core): extract shared creation helpers to core/creation.py [RF-005]
b6bf73e refactor(core): extract generate_entity_name to shared creation module [RF-004]
```

---

## What WS6 Converged

`core/creation.py` contains 6 shared primitives imported identically by both pipelines:

| Primitive | Lines | Purpose |
|---|---|---|
| `generate_entity_name` | 26-98 | Replace `[Business Name]`/`[Unit Name]` placeholders |
| `discover_template_async` | 101-130 | Template discovery with `num_subtasks` opt_field |
| `duplicate_from_template_async` | 133-154 | Duplicate with `include=["subtasks","notes"]` |
| `place_in_section_async` | 157-212 | Case-insensitive section lookup + graceful degradation |
| `compute_due_date` | 215-228 | `(today + offset_days).isoformat()` |
| `wait_for_subtasks_async` | 231-258 | ADR-0111 polling pattern |

Both pipelines import all 6 at module level:
- `automation/pipeline.py:27-34`
- `lifecycle/creation.py:33-40`

Comment at `core/creation.py:6-8`:
> "Seeding is intentionally NOT shared -- automation uses FieldSeeder (explicit
> field lists), lifecycle uses AutoCascadeSeeder (zero-config matching)."

---

## What Remains Divergent

| # | Divergence | Automation | Lifecycle | Classification |
|---|-----------|------------|-----------|----------------|
| 1 | Seeding layer | `FieldSeeder` — explicit static field lists | `AutoCascadeSeeder` — zero-config runtime name-matching; imports `FieldSeeder` infrastructure | **Essential** |
| 2 | Hierarchy placement | Manual `hasattr` walk + private `_process_holder` + `_fetch_holders_async` (`pipeline.py:510-598`) | `ctx.resolve_holder_async(ProcessHolder)` — structured strategy chain with session caching (`lifecycle/creation.py:549-590`) | **Accidental (superseded)** |
| 3 | Assignee resolution | 3-step inline cascade: fixed GID, unit.rep, business.rep (`pipeline.py:600-682`) | 4-step YAML-configurable cascade: `assignee_source` field, fixed GID, unit.rep, business.rep (`lifecycle/creation.py:596-642`) | **Accidental (superseded)** |
| 4 | Blank task fallback | Returns failure `AutomationResult` (`pipeline.py:285-297`) | Creates blank task + continues with configure steps (`lifecycle/creation.py:178-192`) | **Essential** |
| 5 | Duplicate detection | None — webhook events are non-repeating | Full holder subtask scan for matching ProcessType (`lifecycle/creation.py:499-543`) | **Essential** |
| 6 | Onboarding comment | Builds "Pipeline Conversion" audit trail comment (`pipeline.py:684-798`) | None — no equivalent narrative for generic stage transitions | **Essential** |

---

## Detailed Evidence

### 1. Seeding -- Essential Divergence

`AutoCascadeSeeder` (`lifecycle/seeding.py:59-305`) is built **on top of** `FieldSeeder`
(`automation/seeding.py:155-919`). It imports `FieldSeeder`, `get_field_attr`, and
`normalize_custom_fields` from `automation/seeding.py` (lines 29-33) and delegates the
write path to `FieldSeeder.write_fields_async()` (lines 188-193). Only the field discovery
step differs: `FieldSeeder` uses explicit static lists; `AutoCascadeSeeder` dynamically
matches source/target custom field names at runtime.

This is architectural by design. Explicit lists are appropriate for automation's fixed
Sales-to-Onboarding transitions. Zero-config matching is appropriate for lifecycle's
arbitrary stage transitions where target schemas are not known at development time.

### 2. Hierarchy Placement -- Accidental (Superseded)

**Automation** (`pipeline.py:510-598`):
- Tries `source_process.process_holder`, then `unit.process_holder`,
  then `unit._process_holder` (private), then `unit._fetch_holders_async(client)` (private)
- Raw `ASANA_API_ERRORS` exception guard
- No caching of resolved holders

**Lifecycle** (`lifecycle/creation.py:549-590`):
- `ctx.resolve_holder_async(ProcessHolder)` — structured strategy chain
- Uses project GID matching against fetched subtasks
- Caches result in session cache
- Supports multiple holder types (ProcessHolder, DNAHolder, AssetEditHolder, etc.)

The automation path predates `ResolutionContext` and could adopt the same pattern. The
lifecycle approach is strictly better: testable, uses public APIs, supports caching.

### 3. Assignee Resolution -- Accidental (Superseded)

**Automation** (`pipeline.py:600-682`) — 3 steps:
1. Fixed `assignee_gid` from `PipelineStage` constructor
2. `unit.rep[0]`
3. `business.rep[0]`

**Lifecycle** (`lifecycle/creation.py:596-642`) — 4 steps:
1. `assignee_config.assignee_source` field lookup (YAML-configurable)
2. `assignee_config.assignee_gid` fixed GID
3. `unit.rep[0]`
4. `business.rep[0]`

Lifecycle's cascade is a strict superset. Step 1 (`assignee_source`) allows field-level
YAML configuration. Automation could adopt `AssigneeConfig` with no loss.

### 4. Blank Task Fallback -- Essential

Different failure-mode contracts:
- **Automation**: reactive event handler, failing is correct (result flows to event system)
- **Lifecycle**: proactive creation service, degrading gracefully ensures downstream
  configure steps (seeding, hierarchy, assignee) still run

### 5. Duplicate Detection -- Essential

Lifecycle handles retries/replays via holder subtask scan. Automation's webhook events
are non-repeating — adding detection would add API overhead with no benefit.

### 6. Onboarding Comment -- Essential

Specific to Sales-to-Onboarding semantic. Creates a "Pipeline Conversion" audit trail
with source name, date, and source link. Lifecycle has no equivalent narrative because
it handles arbitrary stage transitions.

---

## D-022 Assessment

### Recommendation: Close D-022. Replace with 2 hygiene tickets.

**D-022 (full consolidation) is no longer warranted** because:

1. **WS6 already extracted the meaningful shared surface** — all 6 creation primitives
   are in `core/creation.py` and imported identically by both pipelines.

2. **4 of 6 remaining divergences are essential** — seeding, blank fallback, duplicate
   detection, and onboarding comment reflect genuinely different product requirements.
   Merging them would require conditional branches that make the combined code harder to
   reason about than two well-separated classes.

3. **2 divergences are accidental but small-scope** — hierarchy placement and assignee
   resolution in the automation pipeline are superseded by lifecycle implementations.

### Proposed Replacement Tickets

| Ticket | Scope | Effort | Description |
|--------|-------|--------|-------------|
| D-022a | `pipeline.py:510-598` | ~0.5 day | Migrate `_place_in_hierarchy_async` to use `ctx.resolve_holder_async` |
| D-022b | `pipeline.py:600-682` | ~0.5 day | Migrate `_set_assignee_from_rep_async` to use `AssigneeConfig` pattern |

Combined effort: ~1 day. Low risk. Both changes are internal to `pipeline.py` and do
not affect the lifecycle pipeline.

### Updated Effort Estimate

| Item | Original D-022 Estimate | Post-WS6 Reality |
|------|-------------------------|-------------------|
| Shared creation primitives | 2-3 days | **Done** (WS6) |
| Seeding unification | 3-5 days | **Not needed** (essential divergence) |
| Hierarchy + assignee | 1-2 days | ~1 day (D-022a + D-022b) |
| Blank fallback + duplicate detection + onboarding comment | 2-3 days | **Not needed** (essential divergences) |
| **Total remaining** | ~8-13 days | **~1 day** |

---

## Summary

WS6 converged the high-value shared surface. The remaining divergences are either
essential (different product requirements) or small-scope hygiene. Full consolidation
(D-022) would yield diminishing returns at the cost of conditional complexity in a
merged class. The correct path is to close D-022 and optionally file D-022a/D-022b for
the two accidental divergences.
