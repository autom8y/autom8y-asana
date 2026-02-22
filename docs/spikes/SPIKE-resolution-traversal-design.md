# SPIKE: Optimal Resolution Strategy for Offer-to-Business Traversal

**Date:** 2026-02-20
**Timebox:** 3 hours
**Status:** COMPLETE
**Prior Art:** SPIKE-resolution-context-misuse.md (2026-02-19, fixed caller-level bug)

## Question

`HierarchyTraversalStrategy._traverse_to_business_async()` stops at the wrong entity level when traversing from Offer to Business. What is the optimal, clean, integrated fix?

## Context

### The Entity Hierarchy

```
Business (root) -- has office_phone, vertical custom fields
  +-- UnitHolder
        +-- Unit
              +-- OfferHolder   <-- Offer.parent (NOT Business!)
                    +-- Offer
```

### The Bug

In `src/autom8_asana/resolution/strategies.py`, line 283:

```python
# Fetch the full parent task (single call instead of two)
parent = await context.client.tasks.get_async(parent_gid)
budget.consume(1)

# Try to cast parent to Business
try:
    business = Business.model_validate(parent.model_dump())
    context.cache_entity(business)
    return business
except (ValueError, ValidationError):
    pass
```

`Business.model_validate()` succeeds on ANY Asana task because `Business` inherits from `BusinessEntity -> Task` with no required discriminating fields. Pydantic's `extra="allow"` configuration means any task data validates cleanly as a `Business`. The traversal therefore stops at the **first parent** (OfferHolder) and returns it as a "Business" with `office_phone=None` and `vertical=None`.

### What Changed Since the Previous SPIKE

The earlier SPIKE-resolution-context-misuse.md (2026-02-19) identified and fixed a caller-level bug where `_resolve_offer()` passed `business_gid=offer_task.parent.gid` (an OfferHolder GID) as a fast-path. The fix changed the caller to use `trigger_entity=offer_entity`, which correctly invokes `HierarchyTraversalStrategy`. However, the strategy itself still has the `model_validate` permissiveness bug, meaning the traversal terminates at OfferHolder even when properly invoked via the strategy chain.

### Affected Call Sites

| Call Site | How It Resolves Business | Status |
|-----------|-------------------------|--------|
| `insights_export.py:_resolve_offer()` | `trigger_entity=offer_entity` -> HierarchyTraversalStrategy | **BROKEN** (stops at OfferHolder) |
| `conversation_audit.py` | `business_gid=holder_task.parent.gid` (ContactHolder.parent IS Business) | Works (structural coincidence) |
| `lifecycle/engine.py` | `trigger_entity=source_process` | Works for Process (3 levels, not 4) |
| `pipeline.py` | Pre-resolved `source_process.business.gid` | Works (bypasses traversal) |

### Confirmed Impact

When `_resolve_offer()` invokes the traversal chain for an Offer with GID `1205925604226368`:
1. `SessionCacheStrategy`: miss (first call)
2. `NavigationRefStrategy`: miss (no `_business` ref set on bare BusinessEntity)
3. `HierarchyTraversalStrategy._traverse_to_business_async()`:
   - `current` = BusinessEntity(gid=offer_gid) with parent pointing to OfferHolder
   - Fetches OfferHolder task (GID 1205925357582412)
   - `Business.model_validate(offerholder_data)` **succeeds** -- returns OfferHolder as "Business"
   - `business.office_phone` = None, `business.vertical` = None
   - Resolution returns None at the `_resolve_offer` level (no phone/vertical)

The actual Business is at GID `1205925355204559`, **three more levels up** from OfferHolder.

## Methodology

1. Read the full resolution stack: `context.py`, `strategies.py`, `budget.py`, `result.py`
2. Read the entity model hierarchy: `base.py`, `business.py`, `offer.py`, `unit.py`, `registry.py`, `_bootstrap.py`
3. Read the detection system: `detection/__init__.py`, `detection/types.py`, `detection/tier1.py`, `detection/config.py`
4. Audited all callers of `ResolutionContext`
5. Verified that `tasks.get_async()` (default, no opt_fields) returns `STANDARD_TASK_OPT_FIELDS` which **includes `memberships.project.gid`** -- meaning fetched parent tasks have project membership data available for type detection
6. Evaluated five fix strategies against complexity, regression risk, and architectural cleanliness

## Analysis of Fix Strategies

### Option A: Fix the Traversal Discriminator (Registry-Based Type Detection)

**Approach:** Replace the permissive `Business.model_validate()` with entity type detection using the `ProjectTypeRegistry`. The registry already maps project GIDs to `EntityType` enum values. Since `tasks.get_async()` returns tasks with `memberships.project.gid` data, the traversal can check whether each parent is actually a `BUSINESS` entity type before accepting it.

**Implementation sketch:**

```python
async def _traverse_to_business_async(
    self,
    entity: BusinessEntity,
    context: ResolutionContext,
    budget: ApiBudget,
) -> Business | None:
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.detection import detect_entity_type
    from autom8_asana.models.business.detection.types import EntityType

    cached_business = context.get_cached_business()
    if cached_business is not None:
        return cached_business

    current: Any = entity
    depth = 0
    max_depth = 5

    while depth < max_depth:
        if isinstance(current, Business):
            context.cache_entity(current)
            return current

        if budget.exhausted:
            return None

        parent_gid = getattr(getattr(current, "parent", None), "gid", None)

        if parent_gid is None:
            parent_task = await context.client.tasks.get_async(
                current.gid, opt_fields=["parent", "parent.gid"]
            )
            budget.consume(1)
            if parent_task.parent is None or parent_task.parent.gid is None:
                return None
            parent_gid = parent_task.parent.gid

        # Fetch the full parent task (includes memberships for detection)
        parent = await context.client.tasks.get_async(parent_gid)
        budget.consume(1)

        # Use detection system to determine if parent is Business
        detection_result = detect_entity_type(parent)
        if detection_result and detection_result.entity_type == EntityType.BUSINESS:
            try:
                business = Business.model_validate(parent.model_dump())
                context.cache_entity(business)
                return business
            except (ValueError, ValidationError):
                pass

        # Not a Business -- continue traversal
        current = parent
        depth += 1

    return None
```

**Pros:**
- Fixes the root cause at the lowest level -- every caller benefits
- Uses the existing, well-tested detection system (Tier 1: O(1) project membership lookup)
- No change to any caller code
- All existing callers (conversation_audit, lifecycle/engine, pipeline) continue working identically
- The `Business.PRIMARY_PROJECT_GID = "1200653012566782"` is already registered in `_bootstrap.py`
- Detection data is already present in the fetched task (STANDARD_TASK_OPT_FIELDS includes `memberships.project.gid`)
- Zero additional API calls (detection operates on data already fetched)

**Cons:**
- Adds a dependency from `strategies.py` to the detection subsystem (currently only depends on `models.business.base` and `models.business.business`)
- If a task has no memberships data (edge case), detection returns None and traversal skips that node (safe -- continues traversal)

**Regression risk:** LOW. The `model_validate` call now only runs after positive type detection. If detection fails on a genuine Business (e.g., missing project membership), the traversal continues upward instead of stopping -- which is strictly better than today's behavior of stopping at the wrong entity.

### Option B: Fix the Caller

**Approach:** Have `_resolve_offer()` in `insights_export.py` explicitly walk the parent chain (Offer -> OfferHolder -> Unit -> UnitHolder -> Business) and pass the known-correct Business GID via `business_gid=` fast-path.

**Implementation sketch:**

```python
async def _resolve_offer(self, offer_gid):
    # Walk 4 parents: Offer -> OfferHolder -> Unit -> UnitHolder -> Business
    current_gid = offer_gid
    for _ in range(4):
        task = await self._asana_client.tasks.get_async(
            current_gid, opt_fields=["parent", "parent.gid"]
        )
        if not task.parent or not task.parent.gid:
            return None
        current_gid = task.parent.gid

    # current_gid is now the Business GID
    async with ResolutionContext(
        self._asana_client,
        business_gid=current_gid,
    ) as ctx:
        business = await ctx.business_async()
        ...
```

**Pros:**
- Simple, explicit, easy to understand
- No changes to shared resolution infrastructure

**Cons:**
- Hard-codes hierarchy depth assumption (4 levels) -- brittle if hierarchy changes
- Does not fix `HierarchyTraversalStrategy` for other callers or future Offer-related use cases
- 4 API calls just to discover the Business GID, plus 1 more to fetch it = 5 calls minimum
- The traversal strategy remains broken for any future caller
- Duplicates the same upward-walk pattern already in `asset_edit.py` (code smell)

**Regression risk:** LOW for this caller, but leaves a landmine for future callers.

### Option C: Add Model-Level Discriminator to Business

**Approach:** Add a Pydantic validator to `Business` that rejects non-Business tasks by checking for a distinguishing field (e.g., `office_phone` existence in custom_fields, or project membership).

**Implementation sketch:**

```python
class Business(BusinessEntity, ...):
    @model_validator(mode="after")
    def _validate_is_business(self) -> Business:
        # Check if this task has Business's project membership
        if self.memberships:
            for m in self.memberships:
                if m.get("project", {}).get("gid") == self.PRIMARY_PROJECT_GID:
                    return self
        raise ValueError("Task is not a Business entity (no matching project membership)")
```

**Pros:**
- Makes `model_validate` semantically correct everywhere it's used
- Fixes the bug AND all `_try_cast` calls in `DependencyShortcutStrategy`

**Cons:**
- **BREAKING CHANGE**: Every existing `Business.model_validate()` call would now require project membership data in the input, including hydration paths, test fixtures, and factory methods
- `Business.from_gid_async()` constructs Business from API data that may or may not include memberships depending on opt_fields
- Tests that construct `Business(gid="...", name="...")` directly would break
- The validator conflates data validation with entity type detection -- these are separate concerns

**Regression risk:** HIGH. Would break numerous existing patterns that construct Business objects without membership data.

### Option D: Use Entity Registry for Type-Aware Traversal

This is essentially Option A with a more specific framing. The `ProjectTypeRegistry` IS the entity registry. The implementation is identical to Option A.

### Option E: Hybrid -- Fix Traversal Strategy + Add DependencyShortcutStrategy Guard

**Approach:** Option A for `HierarchyTraversalStrategy` PLUS apply the same detection guard to `DependencyShortcutStrategy._try_cast()`, which has the same `model_validate` permissiveness bug.

The `_try_cast` method at line 174-178:

```python
def _try_cast(self, task: Any, target_type: type[T]) -> T | None:
    try:
        return target_type.model_validate(task.model_dump())
    except (ValueError, ValidationError):
        return None
```

This has the same vulnerability: it uses `model_validate` to determine entity type, which is always permissive. It should also use the detection system.

## Recommendation

### Primary Fix: Option A (Registry-Based Type Detection in Traversal)

**Rationale:**

1. **Fixes the root cause.** The bug is not in any caller -- it is in `_traverse_to_business_async()` itself. A traversal method that cannot distinguish a Business from an OfferHolder is fundamentally broken. Any caller-level fix (Option B) leaves this landmine for future callers.

2. **Zero additional API calls.** The fetched task already contains `memberships.project.gid` because `tasks.get_async()` uses `STANDARD_TASK_OPT_FIELDS`. The `ProjectTypeRegistry.lookup()` is an O(1) dict lookup.

3. **Battle-tested detection system.** The Tier 1 detection system (`detect_entity_type -> _detect_tier1_project_membership`) is used throughout the codebase for holder identification, entity classification, and caching TTL resolution. It has 100% accuracy by design (project membership is deterministic).

4. **Minimal blast radius.** Only two methods change in one file (`strategies.py`). No caller changes needed. No model changes needed. No test fixture changes needed.

5. **Architectural coherence.** The detection system exists precisely for this purpose -- determining entity type from task data. The traversal strategy should have been using it from the start.

### Secondary Fix: Harden DependencyShortcutStrategy._try_cast()

Apply the same detection guard to `_try_cast()` to prevent the same class of bug when resolving via dependency links.

## Exact Files and Methods to Change

### File 1: `src/autom8_asana/resolution/strategies.py`

#### Change 1: `HierarchyTraversalStrategy._traverse_to_business_async()`

Replace the permissive `Business.model_validate()` guard with detection-based type checking.

**Before (lines 282-288):**
```python
# Try to cast parent to Business
try:
    business = Business.model_validate(parent.model_dump())
    context.cache_entity(business)
    return business
except (ValueError, ValidationError):
    pass
```

**After:**
```python
# Use entity type detection to verify parent is actually a Business
from autom8_asana.models.business.detection import detect_entity_type
from autom8_asana.models.business.detection.types import EntityType

detection_result = detect_entity_type(parent)
if detection_result and detection_result.entity_type == EntityType.BUSINESS:
    try:
        business = Business.model_validate(parent.model_dump())
        context.cache_entity(business)
        return business
    except (ValueError, ValidationError):
        logger.warning(
            "traversal_business_detection_but_validation_failed",
            task_gid=parent.gid,
            task_name=parent.name,
        )
```

**Note on imports:** The detection imports should be placed inside the method (alongside the existing `from autom8_asana.models.business.business import Business`) to avoid circular imports at module load time. Alternatively, they can be added to the existing deferred imports at the top of the method.

#### Change 2: `DependencyShortcutStrategy._try_cast()` (defense-in-depth)

When casting to `Business` specifically, add the same detection guard.

**Before (lines 174-179):**
```python
def _try_cast(self, task: Any, target_type: type[T]) -> T | None:
    try:
        return target_type.model_validate(task.model_dump())
    except (ValueError, ValidationError):
        return None
```

**After:**
```python
def _try_cast(self, task: Any, target_type: type[T]) -> T | None:
    from autom8_asana.models.business.business import Business

    # Guard against permissive model_validate for Business type
    if target_type is Business:
        from autom8_asana.models.business.detection import detect_entity_type
        from autom8_asana.models.business.detection.types import EntityType

        detection_result = detect_entity_type(task)
        if not detection_result or detection_result.entity_type != EntityType.BUSINESS:
            return None

    try:
        return target_type.model_validate(task.model_dump())
    except (ValueError, ValidationError):
        return None
```

### No Other Files Need Changes

- No caller changes required
- No model changes required
- No test fixture changes required for existing passing tests

## Edge Cases and Fallback Behavior

### Edge Case 1: Task with No Memberships

If a parent task has no `memberships` data (e.g., fetched with restricted opt_fields), `detect_entity_type()` returns a result with `EntityType.UNKNOWN` via Tier 5 fallback. The traversal correctly **continues upward** instead of stopping. This is strictly better than today's behavior of stopping at the wrong entity.

### Edge Case 2: Business Task Missing Project Membership

If the actual Business task is missing its project membership (a data integrity issue), Tier 1 detection fails but Tier 2 (name pattern) and Tier 3 (parent inference) may still succeed. The `detect_entity_type()` function runs all tiers. If all tiers fail, the traversal exhausts max_depth and returns None -- the caller gets a clear "resolution failed" signal rather than silently wrong data.

### Edge Case 3: Budget Exhaustion

The detection check adds zero API calls (pure in-memory lookup). Budget behavior is unchanged.

### Edge Case 4: Contact -> ContactHolder -> Business Path

This path currently works correctly because:
1. Contact has `_business` navigation ref set during hydration -> NavigationRefStrategy resolves immediately
2. Even via HierarchyTraversalStrategy, ContactHolder.parent IS Business, so the traversal finds Business on the first parent fetch

With the fix: The detection check runs on the first parent (Business), detects `EntityType.BUSINESS`, and `model_validate` proceeds. Behavior is identical to today.

### Edge Case 5: Process -> ProcessHolder -> Unit -> UnitHolder -> Business

Similar to Offer, but 4 levels deep (not 4 from Offer but 4 from Process). Current callers (lifecycle/engine.py) pass `trigger_entity=source_process` and the traversal should work with the fix:
- ProcessHolder: detected as PROCESS_HOLDER, not Business -> continue
- Unit: detected as UNIT, not Business -> continue
- UnitHolder: detected as UNIT_HOLDER, not Business -> continue
- Business: detected as BUSINESS -> accept

## Test Strategy

### Unit Tests (New)

Add to `tests/unit/resolution/test_strategies.py`:

1. **`test_traverse_stops_at_real_business`**: Mock a 2-level chain (child -> Business with correct project membership). Verify traversal returns Business.

2. **`test_traverse_skips_offerholder_finds_business`**: Mock a 4-level chain (Offer -> OfferHolder -> Unit -> UnitHolder -> Business). OfferHolder task has `memberships.project.gid = "1210679066066870"` (OfferHolder project). Business task has `memberships.project.gid = "1200653012566782"`. Verify traversal skips OfferHolder and returns Business.

3. **`test_traverse_returns_none_when_no_business_found`**: Chain of tasks, none with Business project membership. Verify returns None after max_depth.

4. **`test_traverse_handles_task_without_memberships`**: Parent task with `memberships=None`. Verify traversal continues upward (does not crash or stop).

5. **`test_try_cast_rejects_non_business_for_business_type`**: `_try_cast` with Business target type on an OfferHolder task. Verify returns None.

### Integration Tests (Verify No Regression)

Run the existing test suite to confirm no regressions:
```bash
pytest tests/ -x -q
```

Expected: 10,552+ pass, no new failures.

### E2E Validation

Re-run against the known-broken offer GID `1205925604226368`:
1. Invoke `_resolve_offer("1205925604226368")`
2. Verify `office_phone` and `vertical` are non-None
3. Verify the returned Business GID is `1205925355204559` (the actual Business, not the OfferHolder)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Detection system not bootstrapped during traversal | LOW | MEDIUM | `detect_entity_type` internally calls `register_all_models()` via bootstrap guard in `_detect_tier1_project_membership` |
| Circular import from detection in strategies.py | LOW | HIGH | Use deferred imports inside methods (same pattern already used for `Business` import) |
| Detection returns false negative for Business | VERY LOW | MEDIUM | Traversal continues upward (safe failure mode), falls through to max_depth limit |
| Performance regression from detection call | NONE | NONE | O(1) dict lookup on already-fetched data, zero API calls |
| Existing tests break | VERY LOW | LOW | No model or caller changes; mock tasks in existing tests lack memberships but those tests don't exercise the new guard |

## API Call Budget Analysis

Current behavior for Offer -> Business traversal:
- 1 call: fetch parent ref (OfferHolder GID discovery)
- 1 call: fetch OfferHolder task
- **STOPS HERE** (2 calls)

With fix:
- 1 call: fetch parent ref (OfferHolder GID discovery)
- 1 call: fetch OfferHolder task (detection: not Business -> continue)
- 1 call: fetch Unit task (detection: not Business -> continue)
- 1 call: fetch UnitHolder task (detection: not Business -> continue)
- 1 call: fetch Business task (detection: IS Business -> accept)
- **Total: 5 calls** (within default budget of 8)

**Note:** If the first iteration already has `parent.gid` set on the trigger entity (which it does in the current `_resolve_offer` code, which sets `offer_entity.parent = offer_task.parent`), the first "fetch parent ref" call is skipped, reducing to 4 calls.

## Architectural Decision Record

This fix should be accompanied by an ADR documenting:
- **Context:** model_validate is not a type discriminator
- **Decision:** Use ProjectTypeRegistry-based detection for entity type identification in traversal
- **Consequences:** Traversal is now O(n) in hierarchy depth but correct, with n bounded by max_depth=5

See ADR template in doc-artifacts skill if the team wants formal documentation.

## Summary

| Dimension | Value |
|-----------|-------|
| **Fix scope** | 1 file, 2 methods |
| **Root cause** | `Business.model_validate()` accepts any Task data |
| **Fix mechanism** | Gate `model_validate` behind `detect_entity_type()` check |
| **API call cost** | Zero additional (detection uses already-fetched data) |
| **Regression risk** | LOW (safe failure mode: continue traversal) |
| **Files to change** | `src/autom8_asana/resolution/strategies.py` |
| **Callers affected** | None (all benefit automatically) |
| **Estimated effort** | 2-3 hours (implementation + tests) |
