# TDD: Cascade Resolution Failure Fixes

```yaml
id: TDD-CASCADE-FAILURE-FIXES-001
status: DRAFT
date: 2026-02-20
author: architect
spike: SPIKE-unit-resolution-cascade-failure
impact: high
impact_categories: [data_integrity, cache_layer, operational_tooling]
```

---

## 1. Problem Statement

Two compounding failure modes cause intermittent `office_phone=None` in section parquets, producing "Paying, No Ads" anomalies in the reconcile-spend report (7 confirmed cases). Full root cause analysis is in `docs/spikes/SPIKE-unit-resolution-cascade-failure.md`.

**FM1 -- Hierarchy Warming Gap**: When `_warm_ancestors()` or `_fetch_immediate_parents()` absorbs a transient API error (unified.py:612-617, hierarchy_warmer.py:95-100), the Business grandparent is never cached. `get_parent_chain_async()` (unified.py:741-757) breaks at the first missing ancestor, returning `[Holder]` only. Cascade resolution searches Holder for `office_phone`, finds None, and bakes that into the section parquet.

**FM2 -- S3 Parquet Staleness**: Freshness probing (freshness.py:231-457) only detects changes to tasks within a section. It cannot detect that a parent/ancestor outside the section was subsequently cached or updated. A section marked `CLEAN` retains stale cascade values indefinitely until a task within the section is itself modified.

---

## 2. Scope

This TDD covers three fixes of increasing durability:

| Fix | Addresses | Effort | Reversibility |
|-----|-----------|--------|---------------|
| Fix 1: Operational Force-Rebuild | FM1 + FM2 (one-shot) | Small | N/A (operational) |
| Fix 2: Gap-Tolerant Parent Chain | FM1 (systemic) | ~0.5 day | One-way door (behavior change) |
| Fix 3: Post-Build Cascade Validation | FM2 (systemic) | ~1 day | Reversible (feature flag) |

**Explicitly out of scope**: Fix 4 (Index-Time Enrichment) from the spike. That is a significant architectural change deferred unless Fix 2+3 prove insufficient.

---

## 3. Fix 1: Operational Force-Rebuild

### 3.1 Purpose

Provide a safe, idempotent mechanism to invalidate the S3 manifest for a specific project, triggering a full section rebuild on the next warm-up cycle. This is the immediate operational response to unblock the 7 affected units.

### 3.2 Tradeoff Analysis

| Approach | Pros | Cons |
|----------|------|------|
| A. Extend `cache_invalidate` Lambda | Reuses existing handler, deployed infra | Handler currently does all-or-nothing (Redis + S3), no project targeting |
| B. Standalone script / CLI command | Simple, no deployment needed | Not repeatable from monitoring/alerting |
| C. New Lambda parameter on existing handler | Deployed, targetable, logged | Adds parameter surface to existing handler |

**Decision**: Option C -- extend the existing `cache_invalidate` Lambda handler (`src/autom8_asana/lambda_handlers/cache_invalidate.py`) with a `project_gid` parameter for targeted manifest invalidation. This reuses deployed infrastructure, is invocable from AWS console/CLI, and produces CloudWatch metrics for auditability.

### 3.3 Design

**File**: `src/autom8_asana/lambda_handlers/cache_invalidate.py`

**Event Schema Extension**:

```python
# Existing parameters (unchanged):
#   clear_tasks: bool (default True)
#   clear_dataframes: bool (default False)
#
# New parameter:
#   invalidate_project: str | None (default None)
#     When set, deletes the S3 manifest for this specific project GID
#     and all its section parquet files. Does NOT clear task cache or
#     dataframe memory cache. Triggers full rebuild on next warm-up.
```

**Implementation in `_invalidate_cache_async`**:

```python
# After existing clear_tasks / clear_dataframes blocks, add:

project_gid = event.get("invalidate_project")  # passed in from handler
projects_invalidated = 0

if project_gid:
    from autom8_asana.dataframes.section_persistence import create_section_persistence

    persistence = create_section_persistence()

    # Delete section files first, then manifest
    await persistence.delete_section_files_async(project_gid)
    await persistence.delete_manifest_async(project_gid)
    projects_invalidated = 1

    logger.info(
        "project_manifest_invalidated",
        extra={
            "project_gid": project_gid,
            "invocation_id": invocation_id,
        },
    )

    emit_metric(
        "ProjectManifestInvalidated",
        1,
        dimensions={"project_gid": project_gid},
    )
```

**Response Extension**: Add `projects_invalidated: int` field to `InvalidateResponse`.

**Safety Properties**:
- **Idempotent**: `delete_manifest_async` and `delete_section_files_async` succeed silently if already deleted.
- **Logged**: CloudWatch metric + structured log with project GID and invocation ID.
- **Non-destructive to task cache**: Only removes section parquets and manifest. Task cache entries remain intact. Hierarchy warming runs fresh on next build.

### 3.4 ADR: Targeted Project Invalidation via Existing Handler

**Context**: Need an operational mechanism to force-rebuild a specific project's section parquets without clearing the entire task cache or dataframe memory cache.

**Decision**: Extend `cache_invalidate` Lambda with `invalidate_project` parameter rather than creating a new Lambda or script.

**Rationale**: The existing Lambda is already deployed with correct IAM permissions for S3 and Redis. Adding a parameter is simpler than deploying new infrastructure. The `SectionPersistence` class already has `delete_manifest_async` and `delete_section_files_async` methods that are idempotent and safe.

**Consequences**: The handler gains a third mode of operation (task cache, dataframe cache, project manifest). This is acceptable because the modes are orthogonal and independently testable. If the handler grows further, decomposition into separate Lambdas would be warranted.

---

## 4. Fix 2: Gap-Tolerant Parent Chain

### 4.1 Purpose

When `get_parent_chain_async` encounters a missing ancestor in the cache, continue past the gap instead of breaking. This ensures that if the Business grandparent is cached but the intermediate Holder was missed (or vice versa), cascade resolution still reaches the entity with the target field.

### 4.2 Tradeoff Analysis

| Approach | Pros | Cons |
|----------|------|------|
| A. Skip gaps in `get_parent_chain_async` (unified.py:741-757) | Single fix point, all callers benefit | Returns out-of-order chain; could affect `allow_override=True` fields |
| B. Extended fallback in `_resolve_cascade_from_dict` (dataframe_view.py:420-455) | Targeted to cascade resolution only | Only fixes the `dataframe_view` path; `cascade_view.py` still breaks at gap |
| C. Skip gaps + order preservation | All callers benefit, maintains semantic ordering | Slightly more complex than A |

**Analysis of `allow_override` Risk**:

The concern with gap-skipping is that `allow_override=True` fields use parent-chain ordering to determine priority (nearest ancestor wins). If a gap causes the chain to be `[Holder, Business]` when it should have been `[Holder, ???, Business]`, the missing intermediate entity is simply absent from resolution -- it would never have provided the value anyway, since the gap means its data is not cached. The chain ordering of the entities that ARE present remains correct because `HierarchyIndex.get_ancestor_chain()` returns GIDs in parent-to-root order. Skipping a missing entry preserves the relative ordering of present entries.

Furthermore, analysis of actual `allow_override=True` fields confirms the risk is negligible:
- **Business.CascadingFields**: ALL fields have `allow_override=False` (default). Business is the root -- no ordering concern.
- **Unit.CascadingFields**: Only `PLATFORMS` has `allow_override=True`. Platforms cascades from Unit to Offer (1 level). The parent chain for an Offer finding a Unit is always direct parent or one hop through OfferHolder. The Business grandparent is irrelevant for this field because `target_types={"Offer"}` and Business is not an Offer.

**Decision**: Option A -- skip gaps in `get_parent_chain_async`. The ordering analysis confirms no semantic risk for existing cascade fields. The fix benefits all callers (both `dataframe_view.py` and `cascade_view.py`).

### 4.3 Design

**File**: `src/autom8_asana/cache/providers/unified.py`

**Method**: `get_parent_chain_async` (line 741-757)

**Current code** (lines 741-757):

```python
# Build ordered chain, stopping at first missing
chain: list[dict[str, Any]] = []
for ancestor_gid in ancestor_gids:
    entry = entries.get(ancestor_gid)
    if entry is not None:
        chain.append(entry.data)
    else:
        # Stop at first missing - can't continue chain
        logger.debug(
            "parent_chain_incomplete",
            extra={
                "gid": gid,
                "missing_gid": ancestor_gid,
                "found_count": len(chain),
            },
        )
        break
```

**Proposed code**:

```python
# Build ordered chain, skipping gaps for resilience
# Per TDD-CASCADE-FAILURE-FIXES-001 Fix 2: Transient hierarchy warming
# failures can leave gaps in the ancestor chain. Skipping gaps preserves
# the relative ordering of present ancestors, which is sufficient for
# cascade resolution (all allow_override=True fields cascade within a
# single parent-child level, not across gaps).
chain: list[dict[str, Any]] = []
gaps: list[str] = []
for ancestor_gid in ancestor_gids:
    entry = entries.get(ancestor_gid)
    if entry is not None:
        chain.append(entry.data)
    else:
        gaps.append(ancestor_gid)

if gaps:
    logger.info(
        "parent_chain_gaps_skipped",
        extra={
            "gid": gid,
            "gap_gids": gaps,
            "found_count": len(chain),
            "total_ancestors": len(ancestor_gids),
        },
    )
    self._stats.setdefault("parent_chain_gaps", 0)
    self._stats["parent_chain_gaps"] += len(gaps)
```

**Secondary Fix -- `_get_parent_chain_with_completeness_async`**:

**File**: `src/autom8_asana/dataframes/views/cascade_view.py`

The `CascadeViewPlugin._get_parent_chain_with_completeness_async` (lines 314-367) has the same break-on-missing pattern. Apply the identical gap-skipping change:

```python
# Current (line 356-365):
else:
    # Stop at first missing/failed - can't continue chain
    logger.debug(...)
    break

# Proposed:
else:
    # Per TDD-CASCADE-FAILURE-FIXES-001 Fix 2: Skip gaps, continue chain
    logger.info(
        "parent_chain_gap_skipped_with_upgrade",
        extra={
            "gid": gid,
            "missing_gid": ancestor_gid,
            "found_count": len(chain),
        },
    )
    continue  # Try remaining ancestors
```

**Tertiary improvement -- `_resolve_cascade_from_dict` extended fallback**:

**File**: `src/autom8_asana/dataframes/views/dataframe_view.py`

The existing fallback (lines 420-455) fetches only the immediate parent when `parent_chain` is empty. With Fix 2 in place, `get_parent_chain_async` will return partial chains rather than empty chains in most gap scenarios. However, the fallback should also attempt grandparent traversal when the parent chain is present but the field is not found on any returned ancestor.

After the existing search loop (lines 460-468), before returning None (line 470):

```python
# Per TDD-CASCADE-FAILURE-FIXES-001 Fix 2: If chain returned parents but
# none had the field, the owner entity may be beyond a gap. Try fetching
# the grandparent of the last chain entry as a final fallback.
if parent_chain:
    last_parent = parent_chain[-1]
    last_parent_parent = last_parent.get("parent")
    if last_parent_parent and isinstance(last_parent_parent, dict):
        grandparent_gid = last_parent_parent.get("gid")
        if grandparent_gid:
            # Check if grandparent was already in chain
            chain_gids = {p.get("gid") for p in parent_chain}
            if grandparent_gid not in chain_gids:
                from autom8_asana.cache.models.completeness import CompletenessLevel

                grandparent_data = await self._store.get_with_upgrade_async(
                    grandparent_gid,
                    required_level=CompletenessLevel.STANDARD,
                    freshness=FreshnessMode.IMMEDIATE,
                )
                if grandparent_data and self._cascade_plugin is not None:
                    value = self._cascade_plugin._get_custom_field_value_from_dict(
                        grandparent_data, field_name
                    )
                    if value is not None:
                        logger.info(
                            "cascade_grandparent_fallback_resolved",
                            extra={
                                "task_gid": task_gid,
                                "field_name": field_name,
                                "grandparent_gid": grandparent_gid,
                            },
                        )
                        return value
```

### 4.4 ADR: Skip Gaps vs. Break in Parent Chain Traversal

**Context**: `get_parent_chain_async` currently breaks at the first missing ancestor, based on the assumption that a gap makes the rest of the chain unreliable. However, the hierarchy index (`get_ancestor_chain`) correctly returns the full ancestor GID list even when some ancestors are not cached. The gap is a cache miss, not a hierarchy miss.

**Decision**: Change `get_parent_chain_async` and `CascadeViewPlugin._get_parent_chain_with_completeness_async` to skip gaps instead of breaking.

**Rationale**:
1. The hierarchy index maintains correct parent-child relationships regardless of cache state. GID ordering from `get_ancestor_chain` is always correct.
2. All `allow_override=True` cascade fields in the system (only `Unit.PLATFORMS`) cascade within a single parent-child level. No override-sensitive field traverses a multi-level chain where gap ordering matters.
3. All Business cascade fields (Office Phone, Company ID, Business Name, Primary Contact Phone) use `allow_override=False`, meaning parent always wins. For these fields, any ancestor with the value is correct -- the closest ancestor with it would be the Business itself.
4. The current break behavior transforms a temporary cache miss (transient API error during warming) into a permanent data loss (baked into parquet). This is a worse failure mode than the theoretical risk of out-of-order resolution.

**Consequences**:
- Parent chains may contain gaps. Callers that depend on contiguous chains for non-cascade purposes should be audited. Current callers are cascade resolution only.
- The `parent_chain_gaps` stat counter enables monitoring. If gap frequency is high, it signals a hierarchy warming reliability problem that should be addressed at the source.

---

## 5. Fix 3: Post-Build Cascade Validation Pass

### 5.1 Purpose

After all sections are merged in `build_progressive_async`, validate that cascade-critical fields are populated for rows where the hierarchy index indicates an ancestor exists with that field. Re-resolve and re-persist any stale rows.

### 5.2 Tradeoff Analysis

| Approach | Pros | Cons |
|----------|------|------|
| A. Validate after merge, before final artifact write | Single pass over merged DF, catches all sections | Adds time to every build, even when no issues exist |
| B. Validate per-section after section build | Earlier detection, targeted re-persist | Hierarchy may not be fully warmed for early sections |
| C. Validate after merge, gated by feature flag | Controllable, measurable overhead | Extra config surface |

**Decision**: Option C -- post-merge validation gated by a feature flag (`section_cascade_validation` in runtime settings, default `"1"` = enabled). The validation runs after Step 5 (merge) and before Step 6 (final artifact write) in `build_progressive_async`.

### 5.3 Design

#### 5.3.1 Cascade Validation Function

**New file**: `src/autom8_asana/dataframes/builders/cascade_validator.py`

```python
"""Post-build cascade validation for progressive builder.

Per TDD-CASCADE-FAILURE-FIXES-001 Fix 3: Validates cascade-critical fields
after section merge and re-resolves from live store when stale values detected.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger

from dataclasses import dataclass, field

if TYPE_CHECKING:
    from autom8_asana.cache.providers.unified import UnifiedTaskStore
    from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin

logger = get_logger(__name__)

# Fields that cascade from Business and are critical for downstream
# consumers (reconcile-spend, resolution index). These are the fields
# worth validating because a None here causes downstream anomalies.
CASCADE_CRITICAL_FIELDS: list[tuple[str, str]] = [
    ("office_phone", "Office Phone"),  # (column_name, cascade_field_name)
]


@dataclass
class CascadeValidationResult:
    """Result of cascade validation pass."""

    rows_checked: int = 0
    rows_stale: int = 0
    rows_corrected: int = 0
    sections_affected: set[str] = field(default_factory=set)
    duration_ms: float = 0.0


async def validate_cascade_fields_async(
    merged_df: pl.DataFrame,
    store: UnifiedTaskStore,
    cascade_plugin: CascadeViewPlugin,
    project_gid: str,
    entity_type: str,
) -> tuple[pl.DataFrame, CascadeValidationResult]:
    """Validate and correct cascade-critical fields in merged DataFrame.

    For each row where a cascade-critical field is None, checks whether
    the hierarchy index has an ancestor that should provide the value.
    If the live store can resolve the value, updates the row.

    Args:
        merged_df: Merged DataFrame from all sections.
        store: UnifiedTaskStore for parent chain lookups.
        cascade_plugin: CascadeViewPlugin for field resolution.
        project_gid: Project GID for logging.
        entity_type: Entity type for logging.

    Returns:
        Tuple of (corrected DataFrame, validation result).
        DataFrame is the same object if no corrections needed.
    """
    start = time.perf_counter()
    result = CascadeValidationResult()

    if "gid" not in merged_df.columns:
        result.duration_ms = (time.perf_counter() - start) * 1000
        return merged_df, result

    hierarchy = store.get_hierarchy_index()
    corrections: dict[int, dict[str, Any]] = {}  # row_index -> {col: value}

    for col_name, cascade_field_name in CASCADE_CRITICAL_FIELDS:
        if col_name not in merged_df.columns:
            continue

        # Find rows where the cascade field is null
        null_mask = merged_df[col_name].is_null()
        null_indices = null_mask.arg_true().to_list()

        for row_idx in null_indices:
            result.rows_checked += 1
            gid = merged_df["gid"][row_idx]

            if gid is None:
                continue

            # Check if hierarchy index has ancestors for this task
            ancestor_gids = hierarchy.get_ancestor_chain(str(gid), max_depth=5)
            if not ancestor_gids:
                continue

            # Try to resolve the cascade field from live store
            parent_chain = await store.get_parent_chain_async(str(gid))
            if not parent_chain:
                continue

            # Search parent chain for field value using cascade plugin
            for parent_data in parent_chain:
                value = cascade_plugin._get_custom_field_value_from_dict(
                    parent_data, cascade_field_name
                )
                if value is not None:
                    result.rows_stale += 1
                    if row_idx not in corrections:
                        corrections[row_idx] = {}
                    corrections[row_idx][col_name] = value

                    # Track affected section for re-persistence
                    if "section_gid" in merged_df.columns:
                        section_gid = merged_df["section_gid"][row_idx]
                        if section_gid is not None:
                            result.sections_affected.add(str(section_gid))
                    break

    # Apply corrections if any
    if corrections:
        # Build correction series for each column
        for col_name, _ in CASCADE_CRITICAL_FIELDS:
            if col_name not in merged_df.columns:
                continue

            col_corrections = {
                idx: vals[col_name]
                for idx, vals in corrections.items()
                if col_name in vals
            }
            if col_corrections:
                # Create updated column
                values = merged_df[col_name].to_list()
                for idx, val in col_corrections.items():
                    values[idx] = val
                    result.rows_corrected += 1
                merged_df = merged_df.with_columns(
                    pl.Series(col_name, values).cast(merged_df[col_name].dtype)
                )

    result.duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "cascade_validation_complete",
        extra={
            "project_gid": project_gid,
            "entity_type": entity_type,
            "rows_checked": result.rows_checked,
            "rows_stale": result.rows_stale,
            "rows_corrected": result.rows_corrected,
            "sections_affected": list(result.sections_affected),
            "duration_ms": round(result.duration_ms, 2),
        },
    )

    return merged_df, result
```

#### 5.3.2 Integration Point

**File**: `src/autom8_asana/dataframes/builders/progressive.py`

**Method**: `build_progressive_async` (line 385-551)

Insert the validation pass between Step 5 (merge) and Step 6 (final artifact write). Currently at line 481-495:

```python
# Step 5: Merge sections
merged_df = await self._merge_section_dataframes()
total_rows = len(merged_df)
watermark = datetime.now(UTC)

# --- NEW: Step 5.5: Cascade validation pass ---
cascade_validation_result = None
if total_rows > 0 and self._store is not None:
    from autom8_asana.settings import get_settings

    if get_settings().runtime.section_cascade_validation != "0":
        from autom8_asana.dataframes.builders.cascade_validator import (
            validate_cascade_fields_async,
        )

        # Get cascade plugin from dataframe view
        cascade_plugin = getattr(self._dataframe_view, "_cascade_plugin", None)
        if cascade_plugin is not None:
            merged_df, cascade_validation_result = (
                await validate_cascade_fields_async(
                    merged_df=merged_df,
                    store=self._store,
                    cascade_plugin=cascade_plugin,
                    project_gid=self._project_gid,
                    entity_type=self._entity_type,
                )
            )
            total_rows = len(merged_df)  # Refresh after potential corrections
# --- END NEW ---

# Step 6: Write final artifacts
if total_rows > 0:
    index_data = self._build_index_data(merged_df)
    ...
```

#### 5.3.3 Section Re-Persistence

When the validation pass corrects rows, the affected section parquets on S3 are now stale relative to the corrected merged DataFrame. The corrected merged DataFrame is written as the final artifact (Step 6), which is the primary read path for the query engine. Section parquets are only used for resume and freshness probing.

**Decision**: Do NOT re-persist corrected section parquets. The final merged `dataframe.parquet` is the authoritative artifact read by consumers. Section parquets are intermediate build artifacts. On the next full build cycle, sections will be rebuilt with fresh hierarchy data and will naturally produce correct values.

This avoids the complexity of splitting the merged DataFrame back into per-section chunks and re-writing individual sections.

#### 5.3.4 Performance Budget

The validation pass iterates only over rows where cascade-critical fields are null. For a typical project with ~200 offers and good hierarchy warming, this should be 0-5 rows requiring live store lookups. Each lookup is a cache read (no API call) via `get_parent_chain_async`.

**Target**: <5 seconds additional build time.

**Measured cost components**:
- Polars `is_null()` + `arg_true()`: O(n), negligible for n < 10,000
- Cache lookups per null row: ~1-5ms each (in-memory TieredCache)
- Column replacement via `with_columns`: O(n), negligible

**Escape hatch**: Feature flag `section_cascade_validation=0` disables the pass entirely.

### 5.4 ADR: Post-Merge Validation vs. Per-Section Validation

**Context**: Cascade-critical fields can be stale in section parquets due to hierarchy warming failures at build time. Need to detect and correct stale values.

**Decision**: Validate after all sections are merged (post-merge, pre-final-write), not per-section.

**Rationale**:
1. Post-merge validation runs after all hierarchy warming is complete, maximizing the chance that ancestors are now cached even if they were missing when an early section was built.
2. Per-section validation would need to re-trigger hierarchy warming mid-build, adding API calls and complexity.
3. The merged DataFrame is the authoritative artifact. Correcting it before the final write ensures downstream consumers get correct data.
4. Performance cost is bounded by the number of null cascade rows, which is small in the normal case and proportional to the problem severity in failure cases.

**Consequences**:
- Section parquets on S3 may contain stale cascade values until the next full rebuild. This is acceptable because section parquets are intermediate artifacts.
- The validation pass adds latency to every build that has null cascade rows. The feature flag provides an escape hatch.

---

## 6. Interaction Between Fixes

The three fixes form a defense-in-depth strategy:

```
Hierarchy Warming Failure (transient API error)
    |
    v
Fix 2: get_parent_chain_async skips gaps
    |-- Chain now includes Business even if Holder missing
    |-- Cascade resolution finds office_phone on Business
    |
    v (if Fix 2 insufficient, e.g., Business itself missing)
Fix 3: Post-build validation detects office_phone=None
    |-- Re-resolves from live store (may have been warmed
    |   by a later section's warming pass)
    |-- Corrects merged DataFrame before final write
    |
    v (if both Fix 2 and 3 fail, e.g., prolonged API outage)
Fix 1: Operator invokes targeted project invalidation
    |-- Deletes manifest + section parquets
    |-- Next warm-up cycle rebuilds all sections
    |-- Fresh hierarchy warming resolves the field
```

---

## 7. Test Strategy

### 7.1 Fix 1: Targeted Project Invalidation

**Unit tests** (`tests/unit/lambda_handlers/test_cache_invalidate.py`):

| Test | Description |
|------|-------------|
| `test_invalidate_project_deletes_manifest_and_sections` | Invoke with `invalidate_project=<gid>`, assert `delete_manifest_async` and `delete_section_files_async` called with correct GID |
| `test_invalidate_project_idempotent` | Invoke twice with same project GID, assert no error on second invocation |
| `test_invalidate_project_with_clear_tasks` | Both `clear_tasks=True` and `invalidate_project=<gid>` in same event, assert both paths execute |
| `test_invalidate_project_missing_gid_noop` | Invoke without `invalidate_project`, assert no section persistence calls |
| `test_invalidate_project_response_includes_count` | Assert `projects_invalidated` field in response |

### 7.2 Fix 2: Gap-Tolerant Parent Chain

**Unit tests** (`tests/unit/cache/providers/test_unified_parent_chain.py`):

| Test | Description |
|------|-------------|
| `test_parent_chain_skips_gap_returns_remaining` | Setup: A -> B -> C, B missing from cache. Assert chain = [A_data, C_data] (skip B) |
| `test_parent_chain_no_gaps_unchanged_behavior` | Setup: A -> B -> C, all cached. Assert chain = [A_data, B_data, C_data] |
| `test_parent_chain_all_missing_returns_empty` | Setup: A -> B -> C, none cached. Assert chain = [] |
| `test_parent_chain_gap_logged_at_info` | Assert "parent_chain_gaps_skipped" log event with gap GIDs |
| `test_parent_chain_gap_stat_counter_incremented` | Assert `_stats["parent_chain_gaps"]` incremented by gap count |

**Unit tests** (`tests/unit/dataframes/views/test_cascade_view_gaps.py`):

| Test | Description |
|------|-------------|
| `test_cascade_view_skips_gap_in_completeness_chain` | Setup: ancestor GIDs [A, B, C], B returns None from `get_with_upgrade_async`. Assert chain = [A_data, C_data] |

**Unit tests** (`tests/unit/dataframes/views/test_dataframe_view_grandparent_fallback.py`):

| Test | Description |
|------|-------------|
| `test_grandparent_fallback_resolves_field` | Setup: parent chain has Holder (no office_phone), Holder.parent.gid points to Business. Assert `get_with_upgrade_async` called for Business GID and field resolved |
| `test_grandparent_fallback_skips_when_already_in_chain` | Setup: Business already in chain but has no value. Assert no redundant fetch |
| `test_grandparent_fallback_noop_when_no_parent_on_last` | Setup: last parent has no parent. Assert returns None without fetch |

### 7.3 Fix 3: Post-Build Cascade Validation

**Unit tests** (`tests/unit/dataframes/builders/test_cascade_validator.py`):

| Test | Description |
|------|-------------|
| `test_validation_corrects_null_office_phone` | Setup: merged DF with 1 row where office_phone=None, store has parent with Office Phone value. Assert corrected DF has value, result.rows_corrected=1 |
| `test_validation_noop_when_all_fields_populated` | Setup: all rows have office_phone. Assert result.rows_checked=0, DF unchanged |
| `test_validation_noop_when_no_ancestors` | Setup: row has office_phone=None but no ancestors in hierarchy. Assert result.rows_stale=0 |
| `test_validation_noop_when_ancestors_also_null` | Setup: row has office_phone=None, ancestors exist but also have None. Assert rows_stale=0 |
| `test_validation_multiple_rows_corrected` | Setup: 3 rows with null, 2 resolvable. Assert rows_corrected=2 |
| `test_validation_performance_under_budget` | Setup: 200-row DF with 5 null cascade rows. Assert duration < 5000ms |
| `test_validation_disabled_by_feature_flag` | Set `section_cascade_validation=0`, assert validation function not called |

**Integration test** (`tests/integration/test_cascade_validation_progressive.py`):

| Test | Description |
|------|-------------|
| `test_progressive_build_with_hierarchy_gap_corrected` | End-to-end: warm hierarchy with simulated gap, build sections, verify validation corrects merged DF |

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Fix 2 changes behavior for a caller that depended on break-at-gap | Low | Medium | Audit confirms only cascade callers use `get_parent_chain_async`. Stats counter enables monitoring. |
| Fix 3 validation pass exceeds 5s budget | Low | Low | Feature flag disables it. Budget is generous: 5s for typically 0-5 cache lookups. |
| Fix 1 is invoked on wrong project GID | Low | Low | Idempotent. Worst case: unnecessary rebuild of a healthy project. |
| Fix 2 returns ancestors out of order for future fields | Low | Medium | ADR documents the `allow_override` analysis. Any new `allow_override=True` cascade field added in the future must be evaluated against this design. |
| Fix 3 accesses `_cascade_plugin` private attr | Low | Low | The attribute is stable and used by other callers. If refactored, test failure will catch it. |

---

## 9. Rollback Plan

| Fix | Rollback |
|-----|----------|
| Fix 1 | Remove `invalidate_project` parameter handling. No data impact -- the parameter is additive. |
| Fix 2 | Revert `get_parent_chain_async` to `break` behavior. Revert `cascade_view.py` to `break` behavior. Remove grandparent fallback in `dataframe_view.py`. |
| Fix 3 | Set `section_cascade_validation=0` in runtime settings for immediate disable. Remove `cascade_validator.py` and integration point for permanent rollback. |

---

## 10. Implementation Order

1. **Fix 1** first (immediate operational unblock, minutes to deploy)
2. **Fix 2** second (prevents recurrence, ~0.5 day)
3. **Fix 3** third (catches residual staleness, ~1 day)

Fix 2 and Fix 3 are independent and can be implemented in parallel if needed, but Fix 2 should be deployed first because it prevents new stale data from being created, while Fix 3 only detects and corrects existing stale data.

---

## 11. Key File Reference

| Component | File | Lines |
|-----------|------|-------|
| Cache invalidation handler | `src/autom8_asana/lambda_handlers/cache_invalidate.py` | Full file |
| Parent chain (Fix 2 primary) | `src/autom8_asana/cache/providers/unified.py` | 741-757 |
| Cascade view chain (Fix 2 secondary) | `src/autom8_asana/dataframes/views/cascade_view.py` | 314-367 |
| DataFrame view fallback (Fix 2 tertiary) | `src/autom8_asana/dataframes/views/dataframe_view.py` | 420-470 |
| Progressive builder (Fix 3 integration) | `src/autom8_asana/dataframes/builders/progressive.py` | 481-495 |
| Cascade validator (Fix 3 new) | `src/autom8_asana/dataframes/builders/cascade_validator.py` | New file |
| Section persistence (Fix 1 dependency) | `src/autom8_asana/dataframes/section_persistence.py` | 850-893 |
| Hierarchy warmer (context) | `src/autom8_asana/cache/integration/hierarchy_warmer.py` | 79-100 |
| Cascade field definitions | `src/autom8_asana/models/business/fields.py` | 18-59 |
| Business cascade fields | `src/autom8_asana/models/business/business.py` | 287-320 |
| Unit cascade fields | `src/autom8_asana/models/business/unit.py` | 161-195 |
| Spike report | `docs/spikes/SPIKE-unit-resolution-cascade-failure.md` | Full file |
