# PRD: Sprint 1 - Pattern Completion and DRY Consolidation

## Metadata
- **PRD ID**: PRD-SPRINT-1
- **Status**: Draft
- **Author**: Requirements Analyst (Claude)
- **Created**: 2025-12-19
- **Last Updated**: 2025-12-19
- **Stakeholders**: SDK Maintainers, Platform Team
- **Related PRDs**: PRD-PATTERNS-C (HolderFactory), PRD-0024 (Custom Field Remediation)

## Problem Statement

The autom8_asana SDK contains significant code duplication across 7 holder-related files totaling 3,324 lines. This duplication creates:

1. **Maintenance Burden**: Changes to common patterns (field access, holder population, upward traversal) must be replicated in 4-5 files, increasing risk of inconsistency.

2. **Regression Risk**: 17 near-identical field descriptor declarations across Business, Unit, Offer, and Process increase the surface area for bugs when field semantics change.

3. **Pattern Inconsistency**: Location.py and Hours.py use legacy helper methods (`_get_text_field`, `_get_enum_field`, `_get_multi_enum_field`) instead of the established CustomFieldDescriptor pattern used in all other entity files.

4. **Wasted Effort**: The HolderFactory pattern (TDD-PATTERNS-C) successfully eliminated boilerplate for 4 holders, but 5 candidates remain using the manual pattern.

**Impact of Not Solving**: Technical debt accumulates, making future changes slower and riskier. New developers face inconsistent patterns, increasing onboarding time. Bug fixes require touching multiple files with subtle differences.

## Goals & Success Metrics

| Goal | Metric | Target |
|------|--------|--------|
| Reduce holder boilerplate | Lines of code in holder classes | -258 lines (~62% reduction) |
| Eliminate field duplication | Distinct field declarations for shared fields | 17 to 5 (12 eliminated) |
| Achieve pattern consistency | Entities using legacy helper methods | 2 to 0 |
| Maintain test coverage | Test pass rate | 100% (no regressions) |
| Preserve API surface | Breaking changes | 0 (refactoring only) |

## Scope

### In Scope

1. **HolderFactory Migration** for 5 remaining holders:
   - ContactHolder (simple migration)
   - UnitHolder (simple migration)
   - OfferHolder (with `_populate_children` override for `_unit` ref)
   - ProcessHolder (with `_populate_children` override for `_unit` ref)
   - LocationHolder (with `_populate_children` override for Hours sibling)

2. **Field Mixin Consolidation** for 5 cascading/shared fields:
   - `vertical` (EnumField) - Business, Unit, Offer, Process
   - `rep` (PeopleField) - Business, Unit, Offer, Process
   - `booking_type` (EnumField) - Business, Unit, Process
   - `mrr` (NumberField) - Unit, Offer, Process
   - `weekly_ad_spend` (NumberField) - Unit, Offer, Process

3. **Method Extraction** for duplicated logic:
   - `_identify_holder`: Business.py (49 lines) and Unit.py (51 lines) - 90% identical
   - `to_business_async`: Contact.py, Unit.py, Offer.py - 90% common structure

4. **Descriptor Coverage** for legacy files:
   - Location.py: Replace 3 helper methods with TextField, EnumField, IntField
   - Hours.py: Replace 1 helper method with MultiEnumField

### Out of Scope

- **AssetEdit.py helper methods**: Different structure, requires separate initiative
- **New field additions**: Only migrating existing fields
- **Field name changes**: Asana schema must remain unchanged
- **Detection system modifications**: Refactoring only, no algorithm changes
- **Hydration algorithm changes**: `_traverse_upward_async` remains unchanged
- **Behavior changes**: All observable behavior must remain identical

## Requirements

### Phase 0: Foundation (HolderFactory + Descriptors)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-001 | ContactHolder MUST extend HolderFactory with `child_type="Contact"`, `parent_ref="_contact_holder"` | Must | ContactHolder class definition is 15 lines or fewer; all existing ContactHolder tests pass |
| FR-002 | UnitHolder MUST extend HolderFactory with `child_type="Unit"`, `parent_ref="_unit_holder"` | Must | UnitHolder class definition is 15 lines or fewer; all existing UnitHolder tests pass |
| FR-003 | OfferHolder MUST extend HolderFactory with `_populate_children` override that propagates `_unit` reference to children | Must | OfferHolder.offers returns correctly typed Offer list with `_unit` set; all existing OfferHolder tests pass |
| FR-004 | ProcessHolder MUST extend HolderFactory with `_populate_children` override that propagates `_unit` reference to children | Must | ProcessHolder.processes returns correctly typed Process list with `_unit` set; all existing ProcessHolder tests pass |
| FR-005 | LocationHolder MUST extend HolderFactory with `_populate_children` override that separates Hours from Location siblings | Must | LocationHolder.locations and LocationHolder.hours correctly populated; all existing LocationHolder tests pass |
| FR-006 | Location.py MUST use TextField, EnumField, IntField descriptors instead of `_get_text_field`, `_get_enum_field`, `_get_number_field_int` helper methods | Should | `_get_text_field`, `_get_enum_field`, `_get_number_field_int` methods removed; all Location field properties work identically |
| FR-007 | Hours.py MUST use MultiEnumField descriptor instead of `_get_multi_enum_field` helper method | Should | `_get_multi_enum_field` method removed; all Hours day properties return identical values |

### Phase 1: Field Mixins

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-008 | A `SharedCascadingFieldsMixin` MUST be created containing `vertical` (EnumField) and `rep` (PeopleField) descriptors | Must | Mixin exists in `mixins.py`; fields resolve correctly when used via inheritance |
| FR-009 | A `FinancialFieldsMixin` MUST be created containing `booking_type` (EnumField), `mrr` (NumberField), `weekly_ad_spend` (NumberField) descriptors | Must | Mixin exists in `mixins.py`; fields resolve correctly when used via inheritance |
| FR-010 | Business MUST inherit `vertical`, `rep` from SharedCascadingFieldsMixin and `booking_type` from FinancialFieldsMixin | Must | Business.vertical, Business.rep, Business.booking_type work identically to current; field declarations removed from business.py |
| FR-011 | Unit MUST inherit from both SharedCascadingFieldsMixin and FinancialFieldsMixin | Must | Unit.vertical, Unit.rep, Unit.booking_type, Unit.mrr, Unit.weekly_ad_spend work identically; field declarations removed from unit.py |
| FR-012 | Offer MUST inherit `vertical`, `rep` from SharedCascadingFieldsMixin and `mrr`, `weekly_ad_spend` from FinancialFieldsMixin | Must | All inherited fields work identically; field declarations removed from offer.py |
| FR-013 | Process MUST inherit from both SharedCascadingFieldsMixin and FinancialFieldsMixin | Must | All inherited fields work identically; field declarations removed from process.py |

### Phase 2: Method Extraction

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-014 | `_identify_holder` logic MUST be extracted to a utility function in detection.py accepting optional `filter_keys` parameter | Must | Business._identify_holder and Unit._identify_holder delegate to shared implementation; behavior unchanged |
| FR-015 | Common `to_business_async` traversal and hydration logic SHOULD be extracted to a base implementation | Should | Contact, Unit, Offer call common implementation; entity-specific reference updates remain as hooks |
| FR-016 | OfferHolder and ProcessHolder `_populate_children` intermediate ref propagation COULD be extracted to shared helper | Could | Both holders use shared logic for `_unit` propagation; behavior unchanged |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | Backward Compatibility | 100% API surface preserved | No public method/property signatures changed; all existing consumer code works without modification |
| NFR-002 | Test Coverage | 100% existing tests pass | `pytest` exit code 0; no test modifications required except test file organization |
| NFR-003 | Type Safety | No new mypy errors | `mypy src/autom8_asana` reports same or fewer errors |
| NFR-004 | Code Reduction | Net -400 lines | `wc -l` on modified files shows reduction |
| NFR-005 | Import Performance | No circular import errors | All imports resolve successfully at runtime |

## User Stories / Use Cases

### US-001: SDK Maintainer Adds New Cascading Field

**Current State**: Maintainer must add field descriptor to 4 files (Business, Unit, Offer, Process), ensuring identical definition in each.

**Future State**: Maintainer adds field to appropriate mixin once. All entities inherit automatically.

### US-002: SDK Consumer Accesses Offer.vertical

**Current State**: `offer.vertical` returns EnumField value via descriptor on Offer class.

**Future State**: `offer.vertical` returns identical value via descriptor inherited from SharedCascadingFieldsMixin. Consumer code unchanged.

### US-003: SDK Consumer Creates Custom Holder

**Current State**: Must copy 55-90 lines of boilerplate from existing holder, customize child type.

**Future State**: Extend HolderFactory with 3-5 lines:
```python
class CustomHolder(HolderFactory, child_type="Custom", parent_ref="_custom_holder"):
    pass
```

## Assumptions

| Assumption | Basis |
|------------|-------|
| Pydantic v2 supports descriptor inheritance via mixins | Verified in existing HolderFactory implementation |
| CustomFieldDescriptor MRO resolution is deterministic | Python MRO guarantees left-to-right resolution |
| HolderFactory `_populate_children` can be overridden | Already demonstrated by documentation pattern |
| All 5 cascading fields have identical semantic meaning across entities | Field names match; behavior confirmed in codebase |
| Business, Unit do not need `mrr`/`weekly_ad_spend` | Business confirmed missing these fields; only Unit/Offer/Process have them |

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| HolderFactory pattern (TDD-PATTERNS-C) | SDK Team | Complete - already migrated 4 holders |
| CustomFieldDescriptor implementation | SDK Team | Complete - used by Contact, Unit, Offer, Process |
| Existing test suite | SDK Team | Available - baseline for regression testing |
| detection.py module | SDK Team | Available - target for `_identify_holder` extraction |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should mixins include CascadingFieldDef metadata or just descriptors? | Architect | TDD Phase | Architect to determine in TDD-SPRINT-1 |
| Coarse-grained (2 mixins) vs fine-grained (5 mixins) approach? | Architect | TDD Phase | Start coarse per Discovery recommendation; Architect confirms |
| Should `to_business_async` extraction go in BusinessEntity base, new mixin, or module utility? | Architect | TDD Phase | Architect to determine based on inheritance constraints |
| Mixin file location: new `mixins.py` or extend `base.py`? | Architect | TDD Phase | Discovery recommends separate `mixins.py` |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pydantic mixin inheritance conflicts | Medium | High | Spike test during architecture session; fall back to composition if needed |
| Circular imports from mixin file | Medium | Medium | Place mixins in dedicated `mixins.py`; use TYPE_CHECKING imports |
| Descriptor MRO resolution issues | Low | Medium | Test descriptor inheritance explicitly in unit tests |
| HolderFactory override patterns expand scope | Low | Medium | Accept overrides as "migrated" per discovery confirmation |
| Test modifications required | Low | Low | Discovery indicated refactoring-only; tests verify behavior not implementation |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Requirements Analyst | Initial draft from Discovery document |

---

## Quality Gate Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out
- [x] All requirements are specific and testable
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented
- [x] No open questions blocking design (owners assigned, due in TDD phase)
- [x] Priority guidance exists for trade-offs (MoSCoW in requirements table)
- [x] Dependencies identified with status

## Handoff Notes for Architect

1. **Mixin Strategy Decision Required**: Discovery recommends starting with 2 coarse-grained mixins (SharedCascadingFieldsMixin, FinancialFieldsMixin). Architect should evaluate fine-grained alternative (5 single-field mixins) and decide based on:
   - Reusability vs complexity trade-off
   - Whether cascading semantics should be embedded in mixins

2. **Override Tolerance Confirmed**: HolderFactory migrations can include `_populate_children` overrides for:
   - OfferHolder/ProcessHolder: `_unit` reference propagation
   - LocationHolder: Hours sibling detection

3. **Line Count Targets**: Discovery estimates 444 net line reduction across 7 files. These are targets, not hard requirements.

4. **Phase Independence**: Each phase can be implemented and merged independently. Phase 0 has no dependencies on Phase 1/2.
