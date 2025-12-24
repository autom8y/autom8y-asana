# TDD: Sprint 5 - Cleanup and Consolidation

## Metadata
- **TDD ID**: TDD-0026
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-19
- **Last Updated**: 2025-12-19
- **PRD Reference**: [PRD-SPRINT-5-CLEANUP](/docs/planning/sprints/PRD-SPRINT-5-CLEANUP.md)
- **Related TDDs**: TDD-TECH-DEBT-REMEDIATION, TDD-DETECTION
- **Related ADRs**: ADR-0076, ADR-0114, ADR-0075, ADR-0093

## Overview

This TDD defines fix strategies for 20 MEDIUM severity code quality issues identified during Sprint 5 discovery. The focus is on LOW RISK, isolated fixes that reduce technical debt without affecting Sprint 4 frozen artifacts (ActionBuilder, HealingManager).

---

## Requirements Summary

| Priority | Count | Key Issues |
|----------|-------|------------|
| **Must** | 4 | LSK-001 (Liskov), DRY-001, DRY-006, ABS-001 (HealingResult) |
| **Should** | 6 | DRY-002, DRY-003, DRY-005, DRY-007, INH-004, INH-005 |
| **Could** | 6 | DRY-004, DRY-008, INH-001/002, ABS-002/003, ABS-004 |
| **Won't** | 4 | INH-003, ABS-005, ABS-006 (backward compat aliases) |

---

## Open Questions - Resolutions

### OQ-1: FR-DRY-004 (UnitNavigation Descriptor)

**Question**: Should we create a `UnitNavigation` descriptor to consolidate the duplicate `unit` property in `offer.py:83` and `process.py:222`?

**Resolution**: **DEFER** (Document as Acceptable Pattern)

**Rationale**:
1. **Effort**: Creating a navigation descriptor for multi-hop resolution requires significant abstraction complexity
2. **Benefit**: Only 2 locations have identical pattern (not 4 as initially noted - Contact has no unit property)
3. **Risk**: Navigation descriptors with intermediate resolution (`_unit -> holder._unit`) are harder to debug than explicit properties
4. **Pattern Legitimacy**: The current pattern is 8 lines per location (16 total) and is highly readable
5. **Precedent**: `ParentRef` and `HolderRef` descriptors handle single-hop resolution; multi-hop is not their design scope

**Action**: Add code comment documenting the pattern as intentional, not a DRY violation to fix.

---

### OQ-2: FR-ABS-002/003 (NavigationProtocol and HolderProtocol)

**Question**: Should we define `NavigationProtocol` (for entities with `.unit`, `.business`) and `HolderProtocol` (for entities with `.children`, `.business`)?

**Resolution**: **DEFER** (Could Priority - Low Value for Current State)

**Rationale**:
1. **Typing Benefit**: Protocols would enable generic functions accepting "any entity with `.business`"
2. **Current Usage**: No code currently needs polymorphic entity handling - callers know concrete types
3. **Maintenance Cost**: 2 new protocol files, type annotations across 8+ entity classes
4. **mypy Impact**: Adds complexity to type checking; no current type errors to solve
5. **Future Value**: When/if we need generic entity operations, protocols can be added

**Action**: Document as future enhancement. If polymorphic entity handling is needed, create ADR-0119 and implement protocols.

---

### OQ-3: FR-INH-004 (HolderFactory/HolderMixin Overlap)

**Question**: Should `HolderFactory` and `HolderMixin` be consolidated?

**Resolution**: **NO CHANGE NEEDED** (Document Design Rationale)

**Rationale**:
After code review, the relationship is clear and intentional:
1. **HolderMixin** (base.py:46): Generic mixin providing `_populate_children()` template with ClassVars
2. **HolderFactory** (holder_factory.py:55): Extends `Task + HolderMixin` with `__init_subclass__` magic for declarative holder definitions

**Overlap Analysis**:
- `HolderFactory` inherits from `HolderMixin` and overrides `_populate_children()` with dynamic import logic
- This is **composition via inheritance**, not duplication
- `HolderMixin` is still used directly by `BusinessEntity` for non-factory holders

**Action**: Add docstring clarification to `HolderFactory` explaining the relationship. No code change.

---

### OQ-4: FR-INH-005 (Hours Deprecated Aliases)

**Question**: Keep the 114 lines of deprecated aliases in Hours, or remove them?

**Resolution**: **KEEP** (Update ADR-0114 with Deprecation Schedule)

**Rationale**:
1. **ADR-0114 Decision**: Already documents the deprecated alias strategy as intentional
2. **Consumer Discovery**: Warnings help consumers find and update usage
3. **Breaking Change Risk**: Removing aliases without deprecation period causes silent failures
4. **Line Count**: 114 lines is ~50% of Hours file, but aliases are pure delegation (low maintenance)

**Deprecation Schedule** (to add to ADR-0114):
- **Sprint 5**: Keep aliases with `DeprecationWarning`
- **Next Major Version (2.0)**: Remove aliases entirely

**Action**: Update ADR-0114 with deprecation schedule. No code change in Sprint 5.

---

### OQ-5: FR-ABS-001 (HealingResult Consolidation)

**Question**: Which module owns the canonical `HealingResult` type? What attributes should it have?

**Resolution**: **CONSOLIDATE TO `models.py`** with unified attributes

**Analysis of Current Types**:

| Location | Attributes | Purpose |
|----------|------------|---------|
| `healing.py:50` | `entity_gid`, `expected_project_gid`, `success`, `dry_run`, `error: Exception` | Standalone healing |
| `models.py:375` | `entity_gid`, `entity_type`, `project_gid`, `success`, `error: str` | SaveSession healing |

**Unified Design**:
```python
@dataclass(frozen=True, slots=True)
class HealingResult:
    """Outcome of a healing operation.

    Per ADR-0095/0118: Unified result for all healing contexts.
    """
    entity_gid: str
    entity_type: str  # From models.py - useful for logging
    project_gid: str  # Renamed from expected_project_gid for brevity
    success: bool
    dry_run: bool = False  # From healing.py - needed for standalone API
    error: str | None = None  # String for serialization (models.py approach)

    def __bool__(self) -> bool:
        return self.success
```

**Action**:
1. Update `models.py` HealingResult with unified attributes
2. Remove `healing.py` HealingResult
3. Update `healing.py` to import from `models`
4. Update `heal_entity_async` to convert Exception to str

---

## Fix Strategies

### LISKOV VIOLATION (1 Issue)

#### LSK-001: `_invalidate_refs()` Signature Mismatch

**ISSUE**: `base.py:372` defines `_invalidate_refs(_exclude_attr: str | None = None)`, but `process.py:248`, `offer.py:109`, `asset_edit.py:76` override with `_invalidate_refs(self)` (no parameter).

**STRATEGY**: Add Ignored Parameter to Overrides

**APPROACH**:
1. Add `_exclude_attr: str | None = None` parameter to all 3 overrides
2. Parameter is unused in overrides (they clear all refs unconditionally)
3. Preserves polymorphic callability

**FILES TO MODIFY**:
- `src/autom8_asana/models/business/process.py`
- `src/autom8_asana/models/business/offer.py`
- `src/autom8_asana/models/business/asset_edit.py`

**CODE CHANGE** (each file):
```python
def _invalidate_refs(self, _exclude_attr: str | None = None) -> None:
    """Invalidate cached references on hierarchy change.

    Per FR-NAV-006: Clear cached navigation on hierarchy change.

    Args:
        _exclude_attr: Ignored. Clears all refs unconditionally.
    """
    self._business = None
    self._unit = None
    # ... existing clearing logic
```

**RISK**: LOW - Adding unused parameter is purely additive
**DEPENDENCIES**: None
**ESTIMATE**: 15 minutes

---

### DRY VIOLATIONS (8 Issues)

#### DRY-001: Duplicate `_identify_holder()` in business.py:525 vs unit.py:276

**STRATEGY**: Shared Utility Function with `filter_to_map` Parameter

**APPROACH**:
1. Both implementations delegate to `detection.identify_holder_type()`
2. Difference is `filter_to_map` parameter: `False` in Business, `True` in Unit
3. **No change needed** - the duplication is already consolidated via `identify_holder_type`

**ANALYSIS**:
```python
# business.py:525
return identify_holder_type(task, self.HOLDER_KEY_MAP, filter_to_map=False)

# unit.py:276
return identify_holder_type(task, self.HOLDER_KEY_MAP, filter_to_map=True)
```

**RESOLUTION**: Already consolidated. The `_identify_holder()` methods are 4-line wrappers that correctly parameterize the shared function.

**FILES TO MODIFY**: None (already correct)
**RISK**: N/A
**ESTIMATE**: 0 minutes (verification only)

---

#### DRY-002: Duplicate `_fetch_holders_async()` in business.py:591 vs unit.py:295

**STRATEGY**: Template Method in Base Class

**APPROACH**:
1. Create `_fetch_holders_async()` template in `BusinessEntity` base class
2. Subclasses override `_get_holder_fetch_config()` to return list of (holder_attr, children_attr, is_recursive) tuples
3. Base implementation handles common asyncio.gather pattern

**IMPLEMENTATION SKETCH**:
```python
# base.py
async def _fetch_holders_async(self, client: AsanaClient) -> None:
    """Template method for holder fetching."""
    import asyncio

    # Subclass provides configuration
    config = self._get_holder_fetch_config()
    if not config:
        return

    # Fetch subtasks and populate holders
    holder_tasks = await client.tasks.subtasks_async(
        self.gid, include_detection_fields=True
    ).collect()
    self._populate_holders(holder_tasks)

    # Build fetch tasks for each holder's children
    fetch_tasks = []
    for holder_attr, is_recursive in config:
        holder = getattr(self, f"_{holder_attr}", None)
        if holder:
            if is_recursive:
                fetch_tasks.append(asyncio.create_task(
                    self._fetch_recursive_holder_async(client, holder_attr)
                ))
            else:
                fetch_tasks.append(asyncio.create_task(
                    self._fetch_holder_children_async(client, holder)
                ))

    if fetch_tasks:
        await asyncio.gather(*fetch_tasks)

def _get_holder_fetch_config(self) -> list[tuple[str, bool]]:
    """Override to return list of (holder_attr, is_recursive) tuples."""
    return []
```

**FILES TO MODIFY**:
- `src/autom8_asana/models/business/base.py`
- `src/autom8_asana/models/business/business.py`
- `src/autom8_asana/models/business/unit.py`

**RISK**: MEDIUM - Changes core hydration flow; requires thorough testing
**DEPENDENCIES**: None
**ESTIMATE**: 90 minutes

---

#### DRY-003: Duplicate `_populate_holders()` in business.py:508 vs unit.py:250

**STRATEGY**: Consolidate via Shared Helper or Template Method

**APPROACH**:
1. Both implementations iterate subtasks, identify holder type, create typed holder, set `_business` ref
2. **Difference**: Business creates 7 holder types, Unit creates 2 holder types
3. Create shared `_populate_holder_from_subtasks()` helper that takes holder key map and type mapping

**IMPLEMENTATION SKETCH**:
```python
# base.py or new shared module
def _populate_holders(self, subtasks: list[Task]) -> None:
    """Populate holder properties from fetched subtasks."""
    for subtask in subtasks:
        holder_key = self._identify_holder(subtask)
        if holder_key:
            holder = self._create_typed_holder(holder_key, subtask)
            setattr(self, f"_{holder_key}", holder)
```

**ANALYSIS**: Both Business and Unit already follow this pattern. The difference is `_create_typed_holder()` implementation which is necessarily different (different holder types).

**RESOLUTION**: Pattern is already shared; implementations differ only in holder type creation. Document as acceptable variation.

**FILES TO MODIFY**: None (documentation only)
**RISK**: N/A
**ESTIMATE**: 10 minutes (documentation)

---

#### DRY-004: Duplicate Upward Navigation (unit property in offer.py:83 and process.py:222)

**STRATEGY**: Document as Acceptable Pattern (per OQ-1 Resolution)

**APPROACH**:
1. Add code comment explaining the pattern is intentional
2. Multi-hop navigation (`holder._unit`) is clearer as explicit property than descriptor

**CODE COMMENT** (add to both files):
```python
@property
def unit(self) -> Unit | None:
    """Navigate to containing Unit (cached).

    Note: This property duplicates pattern in Offer/Process. This is intentional
    for clarity - multi-hop resolution via holder._unit is more readable as an
    explicit property than a descriptor. See TDD-SPRINT-5-CLEANUP OQ-1.

    Returns:
        Unit entity or None if not populated.
    """
```

**FILES TO MODIFY**:
- `src/autom8_asana/models/business/offer.py`
- `src/autom8_asana/models/business/process.py`

**RISK**: LOW - Documentation only
**DEPENDENCIES**: None
**ESTIMATE**: 10 minutes

---

#### DRY-005: Duplicate `_populate_children()` in offer.py:291 vs process.py:496

**STRATEGY**: Document as Acceptable Override

**ANALYSIS**:
Both `OfferHolder._populate_children()` and `ProcessHolder._populate_children()` override `HolderFactory._populate_children()` to add `_unit` propagation:

```python
def _populate_children(self, subtasks: list[Task]) -> None:
    super()._populate_children(subtasks)
    for child in self.children:
        child._unit = self._unit
```

**RESOLUTION**: This is NOT duplication - it's legitimate method overriding for intermediate reference propagation. The 4-line override is simpler than adding `_unit` propagation to `HolderFactory` (which would require detecting when `_unit` exists).

**FILES TO MODIFY**: None (add documentation comment)
**RISK**: N/A
**ESTIMATE**: 5 minutes

---

#### DRY-006: Duplicate `business` Property in offer.py:277 vs process.py:482

**STRATEGY**: Extract to `UnitNestedHolderMixin`

**APPROACH**:
1. Create mixin with shared `business` property that navigates via `_unit`
2. Apply to `OfferHolder` and `ProcessHolder`

**IMPLEMENTATION**:
```python
# mixins.py (or holder_factory.py)
class UnitNestedHolderMixin:
    """Mixin for holders nested under Unit that need business navigation via _unit.

    Provides business property that navigates _unit.business when _business is None.
    """
    _business: Any = None
    _unit: Any = None

    @property
    def business(self) -> Any:
        """Navigate to parent Business via _unit."""
        if self._business is None and self._unit is not None:
            self._business = self._unit.business
        return self._business
```

**FILES TO MODIFY**:
- `src/autom8_asana/models/business/mixins.py` (add mixin)
- `src/autom8_asana/models/business/offer.py` (use mixin)
- `src/autom8_asana/models/business/process.py` (use mixin)

**RISK**: LOW - Mixin extraction is straightforward
**DEPENDENCIES**: None
**ESTIMATE**: 30 minutes

---

#### DRY-007: Duplicate `_fetch_holder_children_async()` in business.py:696 vs unit.py:346

**STRATEGY**: Move to Base Class

**ANALYSIS**:
```python
# business.py:696
async def _fetch_holder_children_async(
    self, client, holder, children_attr
) -> None:
    subtasks = await client.tasks.subtasks_async(
        holder.gid, include_detection_fields=True
    ).collect()
    if hasattr(holder, "_populate_children"):
        holder._populate_children(subtasks)
    else:
        setattr(holder, children_attr, subtasks)

# unit.py:346
async def _fetch_holder_children_async(
    self, client, holder
) -> None:  # No children_attr parameter
    subtasks = await client.tasks.subtasks_async(
        holder.gid, include_detection_fields=True
    ).collect()
    if hasattr(holder, "_populate_children"):
        holder._populate_children(subtasks)
```

**DIFFERENCE**: Business version takes `children_attr` for fallback; Unit version doesn't need fallback (all holders have `_populate_children`).

**APPROACH**:
1. Move to `BusinessEntity` base class with optional `children_attr` parameter
2. Default to no fallback behavior

**FILES TO MODIFY**:
- `src/autom8_asana/models/business/base.py`
- `src/autom8_asana/models/business/business.py` (remove method)
- `src/autom8_asana/models/business/unit.py` (remove method)

**RISK**: LOW - Simple extraction
**DEPENDENCIES**: None
**ESTIMATE**: 30 minutes

---

#### DRY-008: AssetEdit Helper Methods Duplicate Descriptor Functionality

**STRATEGY**: Review and Document

**ANALYSIS**:
`AssetEdit` has helper methods like `_get_text_field()`, `_get_enum_field()`, `_get_int_field()`, `_get_number_field()`, `_get_multi_enum_field()` that provide type-safe access.

These are NOT duplicates of descriptors because:
1. `AssetEdit` uses manual property accessors (lines 107-232), not descriptors
2. The helpers extract values from `get_custom_fields().get()` with type coercion
3. This is a different pattern than `TextField`, `EnumField` descriptors

**RESOLUTION**: Not a DRY violation. `AssetEdit` uses legacy property pattern with type helpers. Could migrate to descriptors in future cleanup, but out of scope for Sprint 5.

**FILES TO MODIFY**: None
**RISK**: N/A
**ESTIMATE**: 0 minutes

---

### INHERITANCE ISSUES (5 Issues)

#### INH-001: Document 4-Base Inheritance in Unit

**STRATEGY**: Add MRO Explanation to Class Docstring

**APPROACH**:
Add docstring explaining the inheritance hierarchy:
```python
class Unit(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin, UpwardTraversalMixin):
    """Unit entity within a UnitHolder.

    Inheritance (MRO):
        Unit inherits from:
        - BusinessEntity: Core entity behavior, custom field descriptors
        - SharedCascadingFieldsMixin: vertical, rep cascading fields
        - FinancialFieldsMixin: mrr, weekly_ad_spend, booking_type fields
        - UpwardTraversalMixin: to_business_async() method

        The 4-base inheritance is intentional for separation of concerns.
        Each mixin provides orthogonal functionality.
    ...
    """
```

**FILES TO MODIFY**: `src/autom8_asana/models/business/unit.py`
**RISK**: LOW - Documentation only
**ESTIMATE**: 10 minutes

---

#### INH-002: Document 4-Base Inheritance in Offer

**STRATEGY**: Add MRO Explanation to Class Docstring (same as INH-001)

**FILES TO MODIFY**: `src/autom8_asana/models/business/offer.py`
**RISK**: LOW
**ESTIMATE**: 10 minutes

---

#### INH-003: ReconciliationsHolder Deprecated Alias

**RESOLUTION**: **WON'T FIX** - Keep for backward compatibility per PRD.

---

#### INH-004: HolderFactory/HolderMixin Overlap

**RESOLUTION**: **NO CHANGE** per OQ-3 Resolution - relationship is intentional composition.

**ACTION**: Add clarifying docstring to `HolderFactory`:
```python
class HolderFactory(Task, HolderMixin[Task]):
    """Base class for holder tasks using __init_subclass__ pattern.

    Design Note:
        HolderFactory extends HolderMixin (not replaces it). HolderMixin provides
        the core _populate_children template; HolderFactory adds declarative
        configuration via __init_subclass__. HolderMixin is still used directly
        by entities that don't need the factory pattern.
    ...
    """
```

**FILES TO MODIFY**: `src/autom8_asana/models/business/holder_factory.py`
**RISK**: LOW - Documentation only
**ESTIMATE**: 10 minutes

---

#### INH-005: Hours Deprecated Alias Explosion

**RESOLUTION**: **KEEP** per OQ-4 Resolution - update ADR-0114 with deprecation schedule.

**ACTION**: Update ADR-0114 to add:
```markdown
## Deprecation Schedule

| Version | Action |
|---------|--------|
| Current (1.x) | Aliases emit `DeprecationWarning` |
| 2.0 | Remove aliases entirely |

Consumers should migrate from `hours.monday_hours` to `hours.monday` before 2.0.
```

**FILES TO MODIFY**: `docs/decisions/ADR-0114-hours-backward-compat.md`
**RISK**: LOW - Documentation only
**ESTIMATE**: 10 minutes

---

### ABSTRACTION ISSUES (6 Issues)

#### ABS-001: Duplicate HealingResult Types

**STRATEGY**: Consolidate to `models.py` per OQ-5 Resolution

**IMPLEMENTATION**:

1. **Update `models.py:375`**:
```python
@dataclass(frozen=True, slots=True)
class HealingResult:
    """Outcome of a healing operation.

    Per ADR-0095/0118/TDD-SPRINT-5-CLEANUP: Unified result for all healing contexts.

    Attributes:
        entity_gid: GID of the entity that was healed (or would be).
        entity_type: Type name of the entity (e.g., "Contact", "Offer").
        project_gid: GID of the project entity was added to.
        success: True if healing succeeded.
        dry_run: True if this was a dry-run (no actual API call).
        error: Error message if healing failed, None otherwise.
    """
    entity_gid: str
    entity_type: str
    project_gid: str
    success: bool
    dry_run: bool = False
    error: str | None = None

    def __bool__(self) -> bool:
        """Return True if healing succeeded."""
        return self.success
```

2. **Update `healing.py`**:
```python
# Remove local HealingResult dataclass
# Add import:
from autom8_asana.persistence.models import HealingResult

# Update heal_entity_async to use new signature:
return HealingResult(
    entity_gid=entity.gid,
    entity_type=type(entity).__name__,
    project_gid=detection.expected_project_gid,
    success=True,
    dry_run=True,
    error=None,
)
```

3. **Update `healing.py:HealingManager.execute_async()`**:
Already imports and uses `models.HealingResult` - no change needed.

**FILES TO MODIFY**:
- `src/autom8_asana/persistence/models.py`
- `src/autom8_asana/persistence/healing.py`

**RISK**: MEDIUM - Changes public API signature
**DEPENDENCIES**: None
**ESTIMATE**: 45 minutes

---

#### ABS-002: Missing NavigationProtocol

**RESOLUTION**: **DEFER** per OQ-2 Resolution

---

#### ABS-003: Missing HolderProtocol

**RESOLUTION**: **DEFER** per OQ-2 Resolution

---

#### ABS-004: Inconsistent HOLDER_KEY_MAP Types

**STRATEGY**: Document as Acceptable Variation

**ANALYSIS**:
```python
# business.py
HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
    "contact_holder": ("Contacts", "busts_in_silhouette"),
    # ... 7 entries
}

# unit.py
HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
    "offer_holder": ("Offers", "gift"),
    "process_holder": ("Processes", "gear"),
}
```

**RESOLUTION**: Same type signature (`dict[str, tuple[str, str]]`), different keys. This is intentional - each entity has different holders. No type inconsistency.

**FILES TO MODIFY**: None
**RISK**: N/A
**ESTIMATE**: 0 minutes

---

#### ABS-005: RECONCILIATIONS_HOLDER Naming Inconsistency

**RESOLUTION**: **WON'T FIX** - Documented in ADR, deprecated alias preserved.

---

#### ABS-006: Duplicate Deprecation Aliases for reconciliations_holder

**RESOLUTION**: **WON'T FIX** - Keep for backward compatibility per PRD.

---

## Implementation Plan

### Phase 1: Must-Have Fixes (Day 1-2)

| Task | Issue | Estimate | Priority |
|------|-------|----------|----------|
| Fix `_invalidate_refs()` signatures | LSK-001 | 15 min | P0 |
| Consolidate HealingResult | ABS-001 | 45 min | P0 |
| Add UnitNestedHolderMixin | DRY-006 | 30 min | P0 |
| Verify DRY-001 is already resolved | DRY-001 | 5 min | P0 |

**Phase 1 Total**: ~1.5 hours

### Phase 2: Should-Have Fixes (Day 2-3)

| Task | Issue | Estimate | Priority |
|------|-------|----------|----------|
| Move `_fetch_holder_children_async` to base | DRY-007 | 30 min | P1 |
| Template method for holder fetching | DRY-002 | 90 min | P1 |
| Document INH-001/002 (Unit/Offer MRO) | INH-001/002 | 20 min | P1 |
| Update ADR-0114 deprecation schedule | INH-005 | 10 min | P1 |
| Document HolderFactory relationship | INH-004 | 10 min | P1 |

**Phase 2 Total**: ~2.5 hours

### Phase 3: Could-Have Fixes (Day 3-4)

| Task | Issue | Estimate | Priority |
|------|-------|----------|----------|
| Document DRY-004 as acceptable | DRY-004 | 10 min | P2 |
| Document DRY-003 as acceptable | DRY-003 | 10 min | P2 |
| Document DRY-005 as acceptable | DRY-005 | 5 min | P2 |
| Document DRY-008 as non-issue | DRY-008 | 0 min | P2 |

**Phase 3 Total**: ~30 minutes

### Phase 4: Testing and Verification (Day 4-5)

| Task | Estimate |
|------|----------|
| Run full test suite | 30 min |
| Verify mypy passes | 15 min |
| Update any failing tests | 60 min |
| Final review | 30 min |

**Phase 4 Total**: ~2 hours

**Total Estimated Time**: ~6.5 hours (fits within 1-week sprint)

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| HealingResult consolidation breaks consumers | Medium | Low | Run full test suite; HealingResult is internal API |
| Template method pattern causes hydration bugs | Medium | Medium | Extensive testing of all entity loading paths |
| Mixin extraction causes MRO issues | Low | Low | Test all holder instantiation paths |
| Documentation changes don't update everywhere | Low | Low | Grep for affected terms; review in PR |

---

## Testing Strategy

### Unit Tests
- Verify `_invalidate_refs()` accepts `_exclude_attr` parameter on all entities
- Verify `HealingResult` from both contexts has expected attributes
- Verify `UnitNestedHolderMixin.business` property resolves correctly

### Integration Tests
- Full Business hydration with all holder types
- Unit hydration with OfferHolder and ProcessHolder
- Self-healing flow with consolidated HealingResult

### Regression Tests
- All existing tests must pass
- No new mypy errors

---

## Quality Gates

- [ ] All Must-Have fixes implemented
- [ ] All existing tests pass
- [ ] No new mypy errors
- [ ] Coverage >= current level
- [ ] ADR-0114 updated with deprecation schedule
- [ ] Code review approved

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Architect | Initial draft with fix strategies for 20 issues |
