# SPIKE: CascadingFieldResolver Parent Chain Traversal

**Session**: session-20260303-173218-9ba34f7f
**Date**: 2026-03-03
**Scope**: Investigate why `office_phone` cascade resolution fails for ~30% of unit tasks
**Trigger**: QA validation of `/v1/resolve/unit` — 9/10 known business phone numbers returned no match (FALSE negatives)

---

## Executive Summary

Cascade field resolution (`cascade:Office Phone`, `cascade:Business Name`) is broken for ~30% of unit tasks (859/2810). The root cause is a **hierarchy index gap during S3 resume**: when `ProgressiveProjectBuilder` resumes sections from persisted parquet files, tasks are not re-registered in the `UnifiedStore` or `HierarchyIndex`, leaving the cascade validator (Step 5.5) unable to repair null cascade fields. Contributing factors include silent rate-limit failures during hierarchy warming and the non-warmable status of `unit_holder` entities.

## Data Evidence

### Production API Verification

| Business | Phone | Units Found | office_phone | office |
|----------|-------|-------------|--------------|--------|
| Baystate Dental Implants | +14132056222 | 1 | **None** | None |
| Complete Dental Care | +17177678734 | 1 | **None** | None |
| Healing Arts Chiropractic | +15858530900 | 1 | **None** | None |
| iSmile Dental | +13057510601 | 1 | **None** | None |
| Kent Island Family Dentistry | +14106436600 | 1 | **None** | None |
| Life Chiropractic & Acupuncture | +15033904516 | 1 | **None** | None |
| Life In Balance Wellness Center | +19545657059 | 1 | **None** | None |
| Smiles in Springfield | +15038683190 | 1 | **None** | None |
| Smileworx Dental | +12064026820 | 1 | **None** | None |
| Head and Neck Associates | +14109340014 | 2 | **1 populated, 1 None** | None |

- All 10 businesses exist in Asana with correct phone custom fields.
- All 10 businesses have associated units in the DataFrame.
- 9/10 have `office_phone = None` on ALL their units (cascade failed).
- 1/10 (Head and Neck) has partial cascade: 1 of 2 units has phone, 1 does not.
- `office` (cascade:Business Name) is **None for ALL units** — confirming systemic cascade failure.
- Global rate: 859/2810 units (30.6%) have null `office_phone`.

## Root Cause Analysis

### Primary: S3 Resume Breaks Hierarchy Chain

**Location**: `progressive.py:595-700` (section processing), `progressive.py:466-494` (Step 5.5 validation)

When `ProgressiveProjectBuilder` resumes a section from S3 parquet:

1. The parquet file contains only extracted column values (no raw task data, no `parent.gid`)
2. Tasks are **NOT** re-fetched from the Asana API
3. Tasks are **NOT** registered in `UnifiedStore` via `put_batch_async()`
4. The `HierarchyIndex` remains empty for all resumed tasks
5. Step 5.5 cascade validator calls `hierarchy.get_ancestor_chain(gid)` → returns `[]` → **skips the task**

This means: **any section that was initially built with cascade failures will persist those failures forever**, because every subsequent resume loads the same null values from parquet without any mechanism to repair them.

```
First build: section fetched → hierarchy warming (some fail) → cascade resolution (some null) → parquet persisted
Resume:       parquet loaded → NO hierarchy warming → NO cascade resolution → nulls persist
Validator:    Step 5.5 → get_ancestor_chain() → empty → SKIP → nulls remain
```

### Secondary: Rate-Limit Failures During Hierarchy Warming

**Location**: `unified.py:556-607` (`_fetch_immediate_parents`), `progressive.py:1164` (`_populate_store_with_tasks`)

With `max_concurrent_sections=8`, the builder processes 8 sections simultaneously. Each section's hierarchy warming issues 2+ API calls per task (fetch unit_holder, verify business), quickly exhausting the Asana API rate limit (1500 req/min for premium).

Silent failure points:

1. `_fetch_immediate_parent()` catches `CACHE_TRANSIENT_ERRORS` (includes 429 rate limit) and returns `False` — no retry, no log escalation
2. `_populate_store_with_tasks()` wraps the entire `put_batch_async()` in a broad `except Exception` that logs and continues
3. Missing unit_holders → broken parent chain → `_resolve_cascade_from_dict()` cannot traverse to business → null cascade fields

### Tertiary: unit_holder Not Independently Warmable

**Location**: `entity_registry.py:529-542`

The `unit_holder` entity descriptor has `warmable=False` (default), meaning it is never independently warmed during the progressive preload. It only enters the store as a side effect of hierarchy warming during unit section processing.

Contrast with `asset_edit_holder` which IS warmable (`warm_priority=6`). This inconsistency means unit_holders are the weakest link in the cascade chain — they depend entirely on hierarchy warming succeeding.

### Entity Type Detection Weakness

**Location**: `dataframe_view.py:452-470` (`_detect_entity_type_from_dict`)

The fallback cascade path in `DataFrameViewPlugin._resolve_cascade_from_dict()` uses a primitive heuristic to detect entity types: only `Business` is identified (by `parent=None`); everything else is `UNKNOWN`. This means the grandparent traversal fallback cannot reliably identify when it has reached a Business ancestor, limiting its effectiveness.

## Code Trace

### Cascade Resolution Path (Happy Path)

```
ProgressiveProjectBuilder._fetch_and_persist_section()
  → _populate_store_with_tasks()
    → store.put_batch_async(warm_hierarchy=True)      # registers tasks + warms parents
      → _fetch_immediate_parents()                      # fetches unit_holders
      → _warm_ancestors()                               # fetches businesses
      → HierarchyIndex.register(task_gid, parent_gid)  # builds bidirectional map
  → _build_section_dataframe()
    → DataFrameViewPlugin._extract_rows_async()
      → _resolve_cascade_from_dict(task_dict, col_def)
        → store.get_parent_chain_async(task_gid)        # reads HierarchyIndex
        → traverse chain to find Business                # extract custom field
        → return "Office Phone" value                    # cascade resolved ✓
```

### Cascade Resolution Path (Failure — Resume)

```
ProgressiveProjectBuilder._try_resume_section()
  → polars.read_parquet(s3_path)                        # loads pre-extracted columns
  → return DataFrame                                    # NO store population
                                                        # NO hierarchy registration
Step 5.5: cascade_validator.validate_cascade_fields_async()
  → find null cascade columns                           # finds office_phone=None
  → hierarchy.get_ancestor_chain(gid)                   # EMPTY (task not in index)
  → if not ancestor_gids: continue                      # SKIPS — cannot repair
```

### Cascade Resolution Path (Failure — Rate Limit)

```
store.put_batch_async(warm_hierarchy=True)
  → _fetch_immediate_parents()
    → client.get_task(unit_holder_gid)                  # 429 Rate Limited
    → except CACHE_TRANSIENT_ERRORS: return False       # SILENT failure
  → HierarchyIndex: unit → (no unit_holder registered)

_resolve_cascade_from_dict(task_dict, "Office Phone")
  → store.get_parent_chain_async(task_gid)
  → chain = [unit_gid]                                  # no unit_holder in chain
  → fallback: fetch parent from task_dict["parent"]["gid"]
  → _detect_entity_type_from_dict() → UNKNOWN           # unit_holder, not Business
  → no Business found → return None                     # cascade fails
```

## Key Files

| File | Responsibility | Lines of Interest |
|------|---------------|-------------------|
| `dataframes/schemas/unit.py` | Defines cascade sources | L46-57 (`cascade:Business Name`, `cascade:Office Phone`) |
| `dataframes/builders/progressive.py` | Section build + resume + Step 5.5 | L466-494, L595-700, L949, L1164 |
| `dataframes/views/dataframe_view.py` | Cascade extraction from dict | L365-506 (`_resolve_cascade_from_dict`) |
| `dataframes/views/cascade_view.py` | Cascade via unified cache | L187 (parent chain), L314 (completeness), L452 (entity detection) |
| `cache/providers/unified.py` | Store + hierarchy warming | L451, L556, L607, L681, L707 |
| `cache/policies/hierarchy.py` | HierarchyIndex | L96 (register), L160 (get_ancestor_chain) |
| `dataframes/builders/cascade_validator.py` | Post-build cascade repair | L35-92 |
| `core/entity_registry.py` | Entity descriptors | L385-400 (business), L404-425 (unit), L529-542 (unit_holder) |
| `services/resolver.py` | Field normalization | L232 (aliases), L456 (_normalize_field) |

## Recommended Fixes

### Fix 1: Persist parent_gid in DataFrame Schema (RECOMMENDED)

**Effort**: ~0.5 day | **Impact**: Fixes root cause permanently | **Risk**: Low

Add `parent_gid` as a persisted column in UNIT_SCHEMA (and BASE_SCHEMA):

```python
ColumnDef(
    name="parent_gid",
    dtype="Utf8",
    nullable=True,
    source="task:parent.gid",
    description="Immediate parent task GID (for hierarchy reconstruction on resume)",
)
```

On resume, iterate resumed DataFrame rows and register each `(gid, parent_gid)` pair in the HierarchyIndex. This reconstructs the hierarchy with zero additional API calls.

**Implementation steps**:
1. Add `parent_gid` to `BASE_COLUMNS` in `schemas/base.py`
2. Add `parent_gid` extraction in `BaseExtractor` (from `task.parent.gid`)
3. In `ProgressiveProjectBuilder._try_resume_section()`, after loading parquet, iterate rows and call `hierarchy.register(row["gid"], row["parent_gid"])` for non-null parent_gid values
4. Bump schema version
5. Invalidate S3 manifests (one-time re-build)

### Fix 2: Persist HierarchyIndex to S3

**Effort**: ~1 day | **Impact**: Fixes root cause | **Risk**: Medium (serialization/deserialization edge cases)

Serialize the `HierarchyIndex` (parent/child dicts) to a JSON or msgpack file alongside each section's parquet. Restore on resume.

**Pros**: Preserves full hierarchy without schema changes.
**Cons**: Adds storage/serialization complexity, potential staleness if hierarchy changes between builds.

### Fix 3: Improve Warming Resilience

**Effort**: ~0.5 day | **Impact**: Reduces initial failure rate | **Risk**: Low (but doesn't fix resume problem)

- Add retry with exponential backoff in `_fetch_immediate_parent()` for 429 errors
- Lower `max_concurrent_sections` to 4 (halves concurrent API pressure)
- Add structured logging for hierarchy warming failures (currently silent)

**Note**: This only helps INITIAL builds. Does not fix the S3 resume gap (Fix 1 or 2 needed).

### Fix 4: Make unit_holder Warmable

**Effort**: ~0.25 day | **Impact**: Ensures unit_holders are in store before unit processing | **Risk**: Low

Add `warmable=True, warm_priority=1.5` to the `unit_holder` entity descriptor. This ensures unit_holders are fetched into the store as a dedicated warming step before unit sections process, rather than depending on hierarchy warming as a side effect.

### Fix 5: Immediate Mitigation (Delete Manifests)

**Effort**: ~5 min | **Impact**: Forces full re-build | **Risk**: Temporary (next resume re-breaks)

Delete S3 manifests to force a full re-build. Combined with Fix 3 (improved warming), this may resolve most cascade failures. However, nulls will recur on the next resume cycle unless Fix 1 or Fix 2 is also implemented.

## Recommended Approach

**Phase 1** (immediate): Fix 5 (delete manifests) + Fix 3 (warming resilience) — stops the bleeding.
**Phase 2** (this week): Fix 1 (persist parent_gid) — permanent resolution, simplest implementation.
**Phase 3** (opportunistic): Fix 4 (make unit_holder warmable) — defense in depth.

Fix 2 is viable but Fix 1 is simpler and sufficient.

## Verification Plan

After implementing fixes:

1. Delete S3 manifests for unit project
2. Trigger full re-build via progressive preload
3. Query `/v1/resolve/unit` with the 10 test phone numbers
4. Verify all 10 return matches
5. Check global null rate: `office_phone` nulls should drop from 30% to <5% (legitimate nulls only — businesses without phone custom fields)
6. Trigger a second build (resume path) and verify cascade fields are preserved

## Appendix: Field Normalization Chain

The resolver normalizes `phone` to `office_phone` through this 5-step chain:

```
Input: entity_type="unit", field="phone"
Step 1: Direct match? "phone" not in unit columns → NO
Step 2: Entity alias? unit aliases = ["business_unit"]
Step 3: Check "business_unit" parent → "business" entity
Step 4: "business" aliases = ["office"] → check "office_phone" → MATCH
Step 5: Return entity_type="unit", field="office_phone"
```

This normalization is correct — the resolver correctly identifies that `phone` on a unit should resolve via the `office_phone` cascade column. The failure is in cascade population, not field normalization.
