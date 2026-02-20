# SPIKE: Root Cause Analysis — Asana Unit Resolution Failures

**Date:** 2026-02-20
**Timebox:** 2 hours
**Status:** COMPLETE
**Decision:** Confirms 2 compounding failure modes; recommends 4-tier fix strategy

---

## Question

Why do some business units fail to resolve `office_phone` via cascade, causing
"Paying, No Ads" anomalies in the reconcile-spend report?

## Context

The Asana task hierarchy for business units is 3 levels deep:

```
Business (root, BUSINESS project 1200653012566782)
  "Transformity Weight Loss..." — gid=1210523029742351
  Office Phone: +17542809788
  Vertical: weight_loss
    |
    +-- Business Units Holder (UNIT_HOLDER project 1204433992667196)
        "...Business Units" — gid=1210522938772065
        Office Phone: None  (not set on holder)
          |
          +-- Weight Loss Unit (UNIT project, "Account Review" section)
          +-- Mens Health/ED Unit (UNIT project, "Implementing" section)
          +-- Integrative Therapy Unit (UNIT project, "Account Review" section)
```

Cascade resolution must traverse Unit → Holder → Business (2 parent levels) to find
`office_phone`. The code supports `max_depth=5`, which is sufficient. But two
compounding failure modes cause intermittent resolution failures.

---

## Findings

### Confirmed Failure Mode 1: Hierarchy Warming Gap → Incomplete Parent Chain

**Evidence chain:**

1. **`_populate_store_with_tasks`** (progressive.py:1142-1190) runs BEFORE
   `_build_section_dataframe` (progressive.py:660). This is the critical ordering:

   ```
   Phase 3: _populate_store_with_tasks(tasks)    ← hierarchy warming here
   Phase 4: _build_section_dataframe(tasks)       ← cascade resolution here
   Phase 5: _persist_section(...)                  ← baked into parquet here
   ```

2. **Hierarchy warming** (unified.py:537-541) runs two phases:
   - Phase 1: `_fetch_immediate_parents()` — fetches Holder (1 API call per parent)
   - Phase 2: `_warm_ancestors()` — fetches Business (recursive, up to depth 5)

3. **Both phases absorb failures silently** (unified.py:612-617, hierarchy_warmer.py:79-100):
   ```python
   except CACHE_TRANSIENT_ERRORS as e:
       logger.warning("warm_immediate_parent_failed", ...)
   return False  # Silently skipped
   ```
   Individual parent fetch failures are logged at WARNING but **do not fail the build**.

4. **`get_parent_chain_async`** (unified.py:741-757) **breaks at first missing ancestor**:
   ```python
   for ancestor_gid in ancestor_gids:
       entry = entries.get(ancestor_gid)
       if entry is not None:
           chain.append(entry.data)
       else:
           break  # Stop at first missing - can't continue chain
   ```
   If Business (grandparent) failed to warm, chain = `[holder_data]` only.

5. **Cascade resolution** (dataframe_view.py:460-468) searches parent chain for
   `office_phone`. Holder has `office_phone=None` → cascade returns `None`.

6. **Fallback** (dataframe_view.py:420-455) only tries the **immediate parent**
   (Holder), not the grandparent (Business). This is by design per
   `TDD-unit-cascade-resolution-fix Fix 3`, but it's insufficient for 3-level
   hierarchies where the target field is on the root.

### Confirmed Failure Mode 2: S3 Parquet Staleness

**Evidence chain:**

1. **Section-level independence**: Each section's parquet is built and persisted
   independently (progressive.py:573-685). Sections in the same project can be
   built in different runs or in the same run but at different times.

2. **Watermark-based freshness** (watermark.py, freshness.py:231-457) only detects
   changes to tasks **within the section**:
   - GID hash comparison (structural: adds/removes)
   - `modified_since` API call (content: field edits)
   - Neither detects changes to **parent/ancestor data outside the section**

3. **A stale parquet persists indefinitely** when:
   - No tasks in the section are modified (probe returns `CLEAN`)
   - Even if hierarchy warming would now succeed (e.g., transient error resolved)
   - Even if the Business entity's `office_phone` was updated

4. **Cross-section divergence**: Units in "Account Review" and "Implementing" are
   processed as separate sections. If hierarchy warming succeeded for one section's
   build but failed for the other, they'll have different cascade outcomes. The
   failing section's parquet persists with `office_phone=None` until a task in that
   section is modified.

### Impact Path

```
Hierarchy warming fails (transient API error)
  → Business data missing from cache
    → get_parent_chain_async returns [Holder] only (breaks at gap)
      → Cascade searches Holder for office_phone → None
        → office_phone=None baked into section parquet
          → Resolution index missing this unit (no phone → no key)
            → Reconcile-spend can't match unit → "Paying, No Ads" anomaly
```

### Scope of Impact

- **7 confirmed anomalies** in reconcile-spend report (all "Paying, No Ads")
- Affects any unit whose section's parquet was built during a hierarchy warming failure
- Units in the same section share fate (all succeed or all fail together)
- Parquet staleness means the failure persists across warm-up cycles

---

## Recommended Fix Strategy

### Fix 1: Immediate — Force Rebuild (operational, no code change)

**Action:** Invalidate the S3 manifest for the UNIT project to trigger a full rebuild.

**How:**
- Delete the manifest via `SectionPersistence.delete_manifest_async(project_gid)`
  or the cache invalidation Lambda with `clear_dataframes=True`
- On next warm-up, all sections rebuild with fresh hierarchy warming
- Resolution index gets rebuilt with correct `office_phone` values

**Risk:** Low. Full rebuild is more expensive but safe. Idempotent.

**Timeline:** Immediate (minutes).

### Fix 2: Short-term — Grandparent Fallback in Cascade Resolution

**Problem:** `_resolve_cascade_from_dict` fallback (dataframe_view.py:420-455) only
tries the immediate parent when `parent_chain` is empty.

**Fix:** When the parent chain returns a value of `None` for the target field, AND
the last parent in the chain itself has a parent, continue traversal by fetching the
grandparent via `get_with_upgrade_async`.

**Alternative approach:** Instead of modifying the fallback, make `get_parent_chain_async`
skip gaps instead of breaking:

```python
# Current (breaks at first missing):
if entry is None:
    break

# Proposed (skip gaps, continue chain):
if entry is None:
    logger.debug("parent_chain_gap", extra={"missing_gid": ancestor_gid})
    continue  # Try remaining ancestors
```

**Risk:** Medium. Skipping gaps could return ancestors out of order, which matters
for cascade fields with `allow_override=True`. Need to evaluate which cascade fields
use override semantics.

**Timeline:** ~0.5 day.

### Fix 3: Medium-term — Post-Build Cascade Validation Pass

**Problem:** Watermark freshness only detects task-level changes, not hierarchy
data changes. A section can be "fresh" but have stale cascade-resolved fields.

**Fix:** After all sections are merged, validate cascade-critical fields:
- For any row with `office_phone=None` where the hierarchy index shows a Business
  ancestor exists, re-resolve the cascade from the live store
- If the re-resolved value differs, update the row and re-persist the section

**Risk:** Low. Read-only validation pass with targeted updates. Could add ~2-5s
to build time for affected projects.

**Timeline:** ~1 day.

### Fix 4: Long-term — Index-Time Enrichment

**Problem:** Baking cascade-resolved fields into parquets at build time creates a
staleness window. The resolution depends on hierarchy data that may change
independently of the section's tasks.

**Fix:** Instead of resolving cascade fields during DataFrame extraction, resolve
them at index build time from the live hierarchy store:
- Section parquets store raw task data only (no cascade fields)
- `GidLookupIndex.from_dataframe()` resolves cascade fields from the store
  when building the index
- Eliminates the staleness window entirely

**Risk:** High. Significant architectural change. Changes the data contract for
section parquets and the index builder. Requires careful migration.

**Timeline:** ~3-5 days.

---

## Comparison Matrix

| Fix | Effort | Risk | Durability | Addresses FM1 | Addresses FM2 |
|-----|--------|------|------------|---------------|---------------|
| 1. Force Rebuild | Minutes | Low | One-shot | Yes (this run) | Yes (this run) |
| 2. Grandparent Fallback | 0.5 day | Medium | Partial | Yes | No |
| 3. Validation Pass | 1 day | Low | Good | Yes | Yes |
| 4. Index-Time Enrichment | 3-5 days | High | Complete | Yes | Yes |

**FM1** = Hierarchy Warming Gap. **FM2** = S3 Parquet Staleness.

---

## Recommendation

**Execute Fix 1 immediately** to unblock the 7 affected units.

**Implement Fix 2 + Fix 3 together** as a short-term hardening:
- Fix 2 prevents the gap from occurring on future builds
- Fix 3 catches any residual staleness from prior builds

**Defer Fix 4** unless cascade staleness recurs after Fix 2+3. The architectural
cost is high and Fix 2+3 should be sufficient for the known failure modes.

---

## Key Code Locations

| Component | File | Lines |
|-----------|------|-------|
| Build pipeline ordering | `dataframes/builders/progressive.py` | 643-664 |
| Hierarchy warming (Phase 1) | `cache/providers/unified.py` | 558-681 |
| Hierarchy warming (Phase 2) | `cache/integration/hierarchy_warmer.py` | 103-274 |
| Parent chain with break | `cache/providers/unified.py` | 741-757 |
| Cascade resolution | `dataframes/views/dataframe_view.py` | 365-470 |
| Fallback (immediate parent only) | `dataframes/views/dataframe_view.py` | 420-455 |
| Error absorption | `cache/providers/unified.py` | 612-617 |
| Freshness probing | `dataframes/builders/freshness.py` | 231-457 |
| Section persistence | `dataframes/section_persistence.py` | 496-563 |
| Resolution index | `services/gid_lookup.py` | all |

## Follow-Up Actions

- [ ] Execute Fix 1: Invalidate UNIT project manifest (operational)
- [ ] File debt item for Fix 2: Grandparent fallback in cascade resolution
- [ ] File debt item for Fix 3: Post-build cascade validation pass
- [ ] Monitor reconcile-spend report after Fix 1 to confirm resolution
- [ ] Add structured logging for cascade resolution failures (office_phone=None
      when hierarchy index has Business ancestor) to detect future occurrences
