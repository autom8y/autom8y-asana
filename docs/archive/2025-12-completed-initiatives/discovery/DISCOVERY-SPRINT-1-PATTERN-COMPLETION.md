# Discovery: Sprint 1 - Pattern Completion and DRY Consolidation

> **Phase**: Discovery (Session 1)
> **Date**: 2025-12-19
> **Status**: Complete
> **Next**: PRD-SPRINT-1-PATTERN-COMPLETION.md

---

## 1. Executive Summary

Sprint 1 targets code consolidation across 7 holder-related files totaling 3,324 lines. Analysis confirms significant duplication opportunities: 5 holders ready for HolderFactory migration (with override tolerance), 17 field descriptor instances reducible to 5 via mixins, 2 near-identical `_identify_holder` implementations (~50 lines each), and 3 `to_business_async` implementations (~80 lines each) sharing 90% common structure. Location and Hours files use legacy helper methods instead of CustomFieldDescriptor pattern, representing a descriptor coverage gap. All migrations can proceed independently with low coupling risk.

---

## 2. Pattern Inventory: HolderFactory Adoption

### 2.1 Current State

| Holder Class | Base Class | Pattern | Lines | Migration Status |
|--------------|------------|---------|-------|------------------|
| **DNAHolder** | HolderFactory | Declarative | 12 | MIGRATED |
| **ReconciliationHolder** | HolderFactory | Declarative | 15 | MIGRATED |
| **AssetEditHolder** | HolderFactory | Declarative | 10 | MIGRATED |
| **VideographyHolder** | HolderFactory | Declarative | 10 | MIGRATED |
| **ContactHolder** | Task, HolderMixin | Manual | 55 | CANDIDATE |
| **UnitHolder** | Task, HolderMixin | Manual | 58 | CANDIDATE |
| **OfferHolder** | Task, HolderMixin | Manual | 85 | CANDIDATE (override needed) |
| **ProcessHolder** | Task, HolderMixin | Manual | 92 | CANDIDATE (override needed) |
| **LocationHolder** | Task, HolderMixin | Manual | 128 | CANDIDATE (override needed) |

### 2.2 Migration Candidates Analysis

**Simple Migrations (can use HolderFactory directly):**
- `ContactHolder`: No special logic, uses generic `_populate_children` from HolderMixin
- `UnitHolder`: No special logic, uses generic `_populate_children` from HolderMixin

**Override-Required Migrations (use HolderFactory with `_populate_children` override):**
- `OfferHolder`: Propagates intermediate `_unit` reference to children (lines 359-381)
- `ProcessHolder`: Propagates intermediate `_unit` reference to children (lines 503-525)
- `LocationHolder`: Special Hours sibling detection logic (lines 365-403)

### 2.3 Estimated Line Reduction

| Holder | Current Lines | Post-Migration | Savings |
|--------|---------------|----------------|---------|
| ContactHolder | 55 | 15 | 40 |
| UnitHolder | 58 | 15 | 43 |
| OfferHolder | 85 | 35 | 50 |
| ProcessHolder | 92 | 35 | 57 |
| LocationHolder | 128 | 60 | 68 |
| **Total** | **418** | **160** | **258 (~62%)** |

---

## 3. Field Duplication Map

### 3.1 Cascading/Shared Fields

| Field | Type | Occurrences | Files |
|-------|------|-------------|-------|
| `vertical` | EnumField | 4 | business.py, unit.py, offer.py, process.py |
| `rep` | PeopleField | 4 | business.py, unit.py, offer.py, process.py |
| `booking_type` | EnumField | 3 | business.py, unit.py, process.py |
| `mrr` | NumberField | 3 | unit.py, offer.py, process.py |
| `weekly_ad_spend` | NumberField | 3 | unit.py, offer.py, process.py |

**Total: 17 field declarations reducible to 5**

### 3.2 Proposed Mixin Structure

```python
class SharedCascadingFieldsMixin:
    """Fields that cascade through hierarchy."""
    vertical = EnumField()
    rep = PeopleField()

class FinancialFieldsMixin:
    """Financial tracking fields."""
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField()
    booking_type = EnumField()
```

### 3.3 Mixin Application Matrix

| Entity | SharedCascadingFieldsMixin | FinancialFieldsMixin |
|--------|---------------------------|---------------------|
| Business | YES (vertical, rep only) | YES (booking_type only) |
| Unit | YES | YES |
| Offer | YES | YES (mrr, weekly_ad_spend only) |
| Process | YES | YES |

**Note**: Business has `vertical`, `rep`, `booking_type` but NOT `mrr`/`weekly_ad_spend`. Mixin granularity may need adjustment.

### 3.4 Alternative: Fine-Grained Mixins

```python
class VerticalFieldMixin:
    vertical = EnumField()

class RepFieldMixin:
    rep = PeopleField()

class BookingTypeFieldMixin:
    booking_type = EnumField()

class MRRFieldMixin:
    mrr = NumberField(field_name="MRR")

class WeeklyAdSpendFieldMixin:
    weekly_ad_spend = NumberField()
```

**Recommendation for Architect**: Evaluate coarse-grained (2 mixins) vs fine-grained (5 mixins) approach in TDD. Consider cascading semantics - should mixins know about cascading behavior?

---

## 4. Method Duplication Map

### 4.1 `_identify_holder` Method

| File | Lines | Key Difference |
|------|-------|----------------|
| business.py | 524-572 (49 lines) | Returns any holder key |
| unit.py | 339-389 (51 lines) | Filters to `self.HOLDER_KEY_MAP` keys only |

**Structure Comparison:**
- Both import `detect_entity_type`, `get_holder_attr` from detection module
- Both try detection system first, fall back to HOLDER_KEY_MAP
- Both use identical `_matches_holder` helper method
- Only difference: Unit filters returned key against its own HOLDER_KEY_MAP

**Extraction Opportunity**:
- Extract to `HolderIdentificationMixin` or utility function
- Parameterize with optional filter set
- Estimated savings: ~50 lines

### 4.2 `to_business_async` Method

| File | Lines | Traversal Path | Post-Hydration Update |
|------|-------|----------------|----------------------|
| contact.py | 118-199 (82 lines) | Contact -> ContactHolder -> Business | `self._contact_holder`, `self._business` |
| unit.py | 229-309 (81 lines) | Unit -> UnitHolder -> Business | `self._unit_holder`, `self._business` |
| offer.py | 193-282 (90 lines) | Offer -> OfferHolder -> Unit -> UnitHolder -> Business | Complex hierarchy walk |

**Structure Comparison:**
- All three share identical core logic (~60 lines):
  1. Import HydrationError, `_traverse_upward_async`
  2. Call `_traverse_upward_async(self, client)`
  3. Conditionally hydrate with `business._fetch_holders_async(client)`
  4. Handle `partial_ok` error logging
  5. Wrap non-HydrationError exceptions
- Differences in post-hydration reference updates (entity-specific)

**Extraction Opportunity**:
- Extract common traversal + hydration to base class or mixin
- Keep entity-specific reference updates as override hook
- Estimated savings: ~160 lines (from 253 total)

### 4.3 `_populate_children` Overrides

| File | Lines | Reason for Override |
|------|-------|---------------------|
| base.py (HolderMixin) | 103-148 (46 lines) | Base implementation |
| holder_factory.py | 226-307 (82 lines) | Dynamic import, runtime CHILD_TYPE |
| offer.py | 359-381 (23 lines) | Propagate `_unit` ref |
| process.py | 503-525 (23 lines) | Propagate `_unit` ref |
| location.py | 365-403 (39 lines) | Hours sibling detection |

**Note**: OfferHolder and ProcessHolder overrides are nearly identical - candidate for extraction.

---

## 5. Descriptor Coverage Gap Analysis

### 5.1 Current State

| File | Pattern | Helper Methods | Properties |
|------|---------|----------------|------------|
| **contact.py** | CustomFieldDescriptor | None | 19 descriptors |
| **unit.py** | CustomFieldDescriptor | None | 31 descriptors |
| **offer.py** | CustomFieldDescriptor | None | 39 descriptors |
| **process.py** | CustomFieldDescriptor | None | 54+ descriptors |
| **location.py** | Manual helpers | 3 methods (27 lines) | 17 properties (93 lines) |
| **hours.py** | Manual helpers | 1 method (19 lines) | 16 properties (87 lines) |
| **asset_edit.py** | Manual helpers | 4 methods (33 lines) | 11 properties |

### 5.2 Location.py Gap

**Current helper methods:**
```python
def _get_text_field(self, field_name: str) -> str | None  # line 87-92
def _get_enum_field(self, field_name: str) -> str | None  # line 94-106
def _get_number_field_int(self, field_name: str) -> int | None  # line 108-113
```

**Properties using helpers (13 field accessors):**
- street_number, street_name, city, state, zip_code, country
- time_zone, suite, neighborhood, office_location, min_radius, max_radius

**Migration path**: Replace with TextField, EnumField, IntField descriptors

### 5.3 Hours.py Gap

**Current helper method:**
```python
def _get_multi_enum_field(self, field_name: str) -> list[str]  # line 84-102
```

**Properties using helper (6 field accessors + 12 deprecated aliases):**
- monday, tuesday, wednesday, thursday, friday, saturday

**Migration path**: Replace with MultiEnumField descriptors

### 5.4 AssetEdit.py Gap

**Note**: AssetEdit extends Process and has its own helper methods. Lower priority since it's less central to Sprint 1 scope. Consider for Phase 2 or separate initiative.

---

## 6. Risk Assessment

### 6.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pydantic mixin inheritance conflicts | Medium | High | Spike test during architecture session; use composition if needed |
| Circular import from mixin files | Medium | Medium | Place mixins in dedicated `mixins.py`; use TYPE_CHECKING imports |
| Descriptor inheritance resolution | Low | Medium | Test descriptor MRO explicitly |
| Test coverage gaps in holder behavior | Low | Medium | QA to audit holder tests before implementation |

### 6.2 Scope Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AssetEdit.py helper methods out of scope | High | Low | Explicitly defer to future sprint |
| Business.py vertical/rep not same semantic | Medium | Low | Architect to confirm field identity |
| Override patterns expand scope | Low | Medium | Accept overrides as "migrated" per user confirmation |

### 6.3 Dependency Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Detection system coupling | Low | Low | Keep fallback HOLDER_KEY_MAP during transition |
| Hydration module changes | Low | Medium | `to_business_async` extraction should not modify `_traverse_upward_async` |

---

## 7. Recommendations for PRD

### 7.1 Must Include (P0)

1. **HolderFactory Migration**: ContactHolder, UnitHolder, OfferHolder, ProcessHolder, LocationHolder
   - Accept `_populate_children` overrides for intermediate ref propagation
   - Estimated: 258 lines saved

2. **Field Mixin Consolidation**: vertical, rep, booking_type, mrr, weekly_ad_spend
   - Create SharedCascadingFieldsMixin and FinancialFieldsMixin
   - Estimated: 12 field declarations eliminated

3. **Method Extraction**: `_identify_holder`
   - Single implementation with filter parameter
   - Estimated: 50 lines saved

### 7.2 Should Include (P1)

4. **Descriptor Coverage**: Location.py and Hours.py
   - Replace manual helper methods with CustomFieldDescriptor
   - Estimated: 46 lines helper code eliminated, 33 properties simplified

5. **Method Extraction**: `to_business_async`
   - Common base implementation with entity-specific hooks
   - Estimated: 160 lines saved

### 7.3 Could Include (P2)

6. **OfferHolder/ProcessHolder `_populate_children` Consolidation**
   - Extract intermediate ref propagation to shared logic
   - Estimated: 20 lines saved

### 7.4 Won't Include (Out of Scope)

- AssetEdit.py helper method migration (separate initiative)
- New field additions or field name changes
- Detection system modifications
- Hydration algorithm changes

---

## 8. Open Questions for Architecture Session

### 8.1 Mixin Strategy

1. **Coarse vs Fine-Grained Mixins**: Should we use 2 mixins (SharedCascadingFieldsMixin, FinancialFieldsMixin) or 5 single-field mixins?
   - Trade-off: Reusability vs complexity
   - Recommendation: Start coarse, refine if needed

2. **Mixin Location**: New `mixins.py` file or inline in `base.py`?
   - Recommendation: Separate `mixins.py` for clarity

3. **Cascading Semantics in Mixins**: Should mixins include CascadingFieldDef metadata or just descriptors?
   - Current: CascadingFields inner class on each entity
   - Question: Should mixin carry cascading behavior definition?

### 8.2 Descriptor Migration

4. **Hours Field Type**: Hours uses multi_enum for time values. Should we create a `TimeMultiEnumField` descriptor or use generic `MultiEnumField`?
   - Current: `_get_multi_enum_field` returns `list[str]`
   - Recommendation: Use MultiEnumField, add docstring clarifying time semantics

5. **Location Number Fields**: Location has `street_number`, `min_radius`, `max_radius` as integers. Use IntField or NumberField?
   - Current: `_get_number_field_int` returns `int | None`
   - Recommendation: IntField (already exists in descriptors.py)

### 8.3 Method Extraction

6. **`to_business_async` Base Location**: Should extracted implementation go in:
   - (a) BusinessEntity base class
   - (b) New mixin (UpwardTraversalMixin)
   - (c) Module-level utility function
   - Recommendation: (b) - keeps BusinessEntity focused, enables opt-in

7. **`_identify_holder` Extraction**: Should extracted implementation go in:
   - (a) Utility in detection.py
   - (b) New mixin (HolderIdentificationMixin)
   - (c) HolderMixin base class
   - Recommendation: (a) - detection module is natural home

---

## 9. Appendix: Line Count Summary

### Files Modified

| File | Current Lines | Estimated Post-Sprint | Change |
|------|---------------|----------------------|--------|
| business.py | 787 | 740 | -47 |
| unit.py | 553 | 460 | -93 |
| contact.py | 328 | 290 | -38 |
| offer.py | 381 | 310 | -71 |
| process.py | 525 | 450 | -75 |
| location.py | 410 | 340 | -70 |
| hours.py | 340 | 290 | -50 |
| **Total** | **3,324** | **2,880** | **-444 (~13%)** |

### Files Created

| File | Estimated Lines | Purpose |
|------|-----------------|---------|
| mixins.py | ~50 | SharedCascadingFieldsMixin, FinancialFieldsMixin |
| (detection.py modification) | +30 | Extracted `_identify_holder` |

---

## 10. Next Steps

1. **Session 2 (Requirements)**: Create PRD-SPRINT-1-PATTERN-COMPLETION using this discovery
2. **Session 3 (Architecture)**: Create TDD-SPRINT-1 + ADR-0119-mixin-strategy
3. **Session 4-6 (Implementation)**: Execute in 3 phases per Prompt 0
4. **Session 7 (Validation)**: Regression testing + pattern verification
