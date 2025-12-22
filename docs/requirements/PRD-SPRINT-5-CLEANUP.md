# PRD: Sprint 5 - Cleanup and Consolidation

## Metadata

| Field | Value |
|-------|-------|
| **PRD ID** | PRD-0025 |
| **Status** | Draft |
| **Author** | Requirements Analyst |
| **Created** | 2025-12-19 |
| **Last Updated** | 2025-12-19 |
| **Stakeholders** | SDK Maintainers, Future Contributors |
| **Related PRDs** | PRD-TECH-DEBT-REMEDIATION, PRD-DETECTION, PRD-SPRINT-4-SAVESESSION-DECOMPOSITION |
| **Source** | Session 2 Issue Location Manifest (20 issues) |
| **Sprint Duration** | 1 week (final cleanup sprint of Architectural Remediation Marathon) |

---

## Problem Statement

### What Problem Are We Solving?

The autom8_asana SDK has accumulated **20 MEDIUM severity code quality issues** during the rapid development phases of Sprints 1-4. These issues fall into four categories:

| Category | Count | Impact |
|----------|-------|--------|
| **LISKOV Violation** | 1 | Breaks substitutability; polymorphic calls may fail |
| **DRY Violations** | 8 | Code duplication increases maintenance burden and divergence risk |
| **Inheritance Issues** | 5 | Complex MRO, deprecated aliases, mixin overlap add cognitive load |
| **Abstraction Issues** | 6 | Missing protocols, duplicate types, naming inconsistencies |

### For Whom?

- **SDK Maintainers**: Navigate duplicated code across multiple files; risk introducing bugs when updating one copy but not others.
- **Future Contributors**: Face steep learning curve from complex inheritance and inconsistent abstractions.
- **QA**: Test coverage gaps from duplicated logic with subtle differences.

### Impact of Not Solving

1. **Maintenance Burden Compounds**: Each Sprint adds more code on top of a shaky foundation.
2. **Liskov Violation Causes Runtime Errors**: Calling `_invalidate_refs(_exclude_attr="foo")` on Process or Offer raises `TypeError`.
3. **Duplicate Code Diverges**: DRY violations eventually diverge, causing inconsistent behavior.
4. **114 Lines of Deprecated Aliases in Hours**: Noise that obscures the 6 actual field accessors.
5. **Type Confusion**: Two different `HealingResult` dataclasses with different attributes.

### Why Now?

Sprint 5 is the **final cleanup sprint** of the Architectural Remediation Marathon. Sprint 4 artifacts (ActionBuilder, HealingManager) are FROZEN. This is the last window to address accumulated debt before the codebase enters maintenance mode.

---

## Goals & Success Metrics

| Goal | Metric | Target |
|------|--------|--------|
| Eliminate Liskov violation | Signature-compatible overrides | 100% (3 files fixed) |
| Reduce duplicate code | Lines of duplicate code removed | 200+ lines |
| Consolidate HealingResult | Single source of truth | 1 definition |
| Improve navigation protocols | Protocol/interface coverage | 2+ new Protocols (optional) |
| Maintain stability | Test pass rate | 100% |
| Zero regressions | New bugs introduced | 0 |
| No public API changes | Signature changes | 0 |

---

## Scope

### In Scope

| Area | Files | Issue Count |
|------|-------|-------------|
| Business entity files | `process.py`, `offer.py`, `business.py`, `unit.py`, `asset_edit.py`, `hours.py` | 15 |
| Persistence module | `healing.py`, `models.py` | 2 |
| Holder infrastructure | `holder_factory.py`, `base.py` | 2 |
| All 20 identified issues | See Requirements tables | 20 |

### Out of Scope

| Item | Rationale |
|------|-----------|
| New features or capabilities | Cleanup sprint only |
| Sprint 4 artifacts (ActionBuilder, HealingManager) | FROZEN - considered stable |
| Detection tier refactoring | Low-priority DRY issues (logging/factory) can be deferred |
| Performance optimizations | Not the focus of this sprint |
| Changes to public API signatures | Backward compatibility required |
| Major architectural changes | LOW RISK, isolated fixes only |

---

## Requirements

### Functional Requirements - LISKOV Violation (1 Issue)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-LSK-001 | Fix `_invalidate_refs()` signature mismatch: base.py:372 defines `def _invalidate_refs(self, _exclude_attr: str \| None = None)` but process.py:248, offer.py:109, asset_edit.py:76 override with `def _invalidate_refs(self)` | **Must** | All three overrides accept `_exclude_attr: str \| None = None` parameter; `super()._invalidate_refs(_exclude_attr)` calls work from any subclass; `entity._invalidate_refs(_exclude_attr="foo")` works on all subclasses |

### Functional Requirements - DRY Violations (8 Issues)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DRY-001 | Consolidate duplicate `_identify_holder()` in business.py:525 vs unit.py:276 | **Must** | Single shared function with `filter_to_map` parameter; both callers use the shared function; no functional change |
| FR-DRY-002 | Consolidate duplicate `_fetch_holders_async()` in business.py:591 vs unit.py:295 | **Should** | Template method pattern in base class; subclasses provide holder types, base handles fetch logic |
| FR-DRY-003 | Consolidate duplicate `_populate_holders()` in business.py:508 vs unit.py:250 | **Should** | Template method in base class or shared helper; entity-specific logic via hooks |
| FR-DRY-004 | Consolidate duplicate upward navigation in offer.py:83 vs process.py:222 (unit property pattern) | **Could** | Either single `UnitNavigation` descriptor or document as acceptable 4-location pattern; if fixed: all 4 locations use shared implementation |
| FR-DRY-005 | Consolidate duplicate `_populate_children()` overrides in offer.py:291 vs process.py:496 | **Should** | Single implementation in shared mixin or parameterized in HolderFactory; `_unit` propagation handled generically |
| FR-DRY-006 | Consolidate duplicate `business` property in offer.py:277 vs process.py:482 (OfferHolder and ProcessHolder) | **Must** | Single implementation via mixin or shared method; both holders' `.business` property works identically |
| FR-DRY-007 | Consolidate duplicate `_fetch_holder_children_async()` in business.py:696 vs unit.py:346 | **Should** | Template method or shared helper; reduces duplication |
| FR-DRY-008 | AssetEdit helper methods duplicate descriptor functionality | **Could** | Review if property accessors (lines 107+) duplicate existing descriptors; consolidate or document as acceptable variation |

### Functional Requirements - Inheritance Issues (5 Issues)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-INH-001 | Document 4-base inheritance in Unit (BusinessEntity + 3 mixins) | **Could** | Unit class docstring includes MRO explanation; no code change |
| FR-INH-002 | Document 4-base inheritance in Offer (BusinessEntity + 3 mixins) | **Could** | Offer class docstring includes MRO explanation; no code change |
| FR-INH-003 | Keep deprecated ReconciliationsHolder alias (business.py:77-91) | **Won't** | No change; deprecation warning remains; remove in future major version |
| FR-INH-004 | Review HolderFactory/HolderMixin overlap (holder_factory.py vs base.py:46) | **Should** | Either consolidate into single holder base or document design rationale in ADR; no functional regression |
| FR-INH-005 | Review Hours deprecated alias explosion (hours.py lines 90-202, ~114 lines) | **Should** | Decision: keep for backward compat OR remove in coordinated cleanup; if kept, add deprecation schedule to ADR-0114; if removed: update all callers |

### Functional Requirements - Abstraction Issues (6 Issues)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ABS-001 | Consolidate duplicate HealingResult types (healing.py:50 vs models.py:375) | **Must** | Single `HealingResult` definition in models.py; healing.py imports from models; all tests pass |
| FR-ABS-002 | Define missing NavigationProtocol for entities with `.unit`, `.business` | **Could** | Protocol defined with `unit`, `business` properties; Offer, Process, Contact type-hint as NavigableEntity; mypy validates |
| FR-ABS-003 | Define missing HolderProtocol for entities with `.children`, `.business` | **Could** | Protocol defined with `children`, `business` properties; all holders type-hint as Holder; mypy validates |
| FR-ABS-004 | Address inconsistent HOLDER_KEY_MAP types in business.py vs unit.py | **Could** | Either document acceptable variation (different key sets) or extract shared type alias; no functional change |
| FR-ABS-005 | Address RECONCILIATIONS_HOLDER naming inconsistency (plural vs singular) | **Won't** | Document decision: singular `reconciliation_holder` is canonical; deprecated alias preserved for backward compat |
| FR-ABS-006 | Address duplicate deprecation aliases for reconciliations_holder | **Won't** | Keep for backward compatibility; ReconciliationsHolder deprecated class in business.py:77 remains until major version bump |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | All existing tests pass | 100% | `pytest` exit code 0 |
| NFR-002 | No new mypy errors | 0 new errors | `mypy src/autom8_asana` comparison |
| NFR-003 | Coverage maintained | >= current % | `pytest --cov` comparison |
| NFR-004 | No public API changes | 0 signature changes | Review of `__all__` exports |
| NFR-005 | All fixes are LOW RISK and isolated | 100% | Architect review confirms no cross-cutting changes |
| NFR-006 | Sprint 4 artifacts untouched | 0 modifications | No changes to ActionBuilder or HealingManager classes |

---

## Priority Summary

| Priority | Count | Issues |
|----------|-------|--------|
| **Must** | 4 | FR-LSK-001, FR-DRY-001, FR-DRY-006, FR-ABS-001 |
| **Should** | 6 | FR-DRY-002, FR-DRY-003, FR-DRY-005, FR-DRY-007, FR-INH-004, FR-INH-005 |
| **Could** | 6 | FR-DRY-004, FR-DRY-008, FR-INH-001, FR-INH-002, FR-ABS-002, FR-ABS-003, FR-ABS-004 |
| **Won't** | 4 | FR-INH-003, FR-ABS-005, FR-ABS-006 (backward compat aliases kept) |

### Implementation Order (Recommended)

1. **FR-LSK-001** - Liskov fix (unblocks safe refactoring; breaks polymorphism if unfixed)
2. **FR-ABS-001** - HealingResult consolidation (naming clarity; blocks confusion)
3. **FR-DRY-001, FR-DRY-006** - High-value DRY fixes (most code eliminated)
4. **FR-DRY-002, FR-DRY-003, FR-DRY-005, FR-DRY-007** - Template method patterns
5. **FR-INH-004** - HolderFactory consolidation (if time permits)
6. **FR-INH-005** - Hours aliases decision (requires ADR update)
7. **Remaining Could items** as time allows

---

## User Stories / Use Cases

### US-001: Maintainer Calls Base Class Method Polymorphically

**As a** SDK maintainer
**I want** `_invalidate_refs()` to accept the same parameters on all subclasses
**So that** I can call it polymorphically without checking subclass type

**Scenario**: Code calls `entity._invalidate_refs(_exclude_attr="foo")`
- **Before**: Fails on Process, Offer, AssetEdit with `TypeError: _invalidate_refs() got an unexpected keyword argument`
- **After**: Works on all BusinessEntity subclasses

### US-002: Maintainer Updates Holder Identification Logic

**As a** SDK maintainer
**I want** holder identification logic in one place
**So that** I can update it without hunting through Business and Unit files

**Scenario**: Developer needs to add new holder type identification
- **Before**: Must update `_identify_holder()` in both business.py AND unit.py
- **After**: Updates single shared function

### US-003: Contributor Understands HealingResult

**As a** new contributor
**I want** one HealingResult type with clear attributes
**So that** I know which fields to check after a healing operation

**Scenario**: Developer processes healing results
- **Before**: Confusion between `healing.py:HealingResult` (has `dry_run`, `error: Exception`) and `models.py:HealingResult` (has `entity_type`, `error: str`)
- **After**: Single HealingResult with unified attributes

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| Sprint 4 changes are stable and tested | Completed in prior sprint; FROZEN status |
| All fixes are internal implementation only | No public API changes required |
| Existing test suite provides sufficient regression coverage | 1.6x coverage ratio established |
| MRO complexity is acceptable with documentation | Python handles correctly; docstrings sufficient |
| Backward compatibility aliases should be preserved | Breaking changes require major version bump |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| Issue Location Manifest (20 issues) | Discovery Phase | Complete |
| Existing test suite | Prior sprints | In place |
| Sprint 4 artifacts frozen | Architecture decision | Confirmed |
| ADR-0114 (Hours backward compat) | Prior decision | Exists; may need update for FR-INH-005 |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should FR-DRY-004 (unit property in 4 locations) be fixed or deferred? | Architect | Session 3 | TBD - evaluate effort vs benefit of UnitNavigation descriptor |
| Should NavigationProtocol/HolderProtocol (FR-ABS-002/003) be added? | Architect | Session 3 | TBD - evaluate typing benefit vs added complexity |
| HolderFactory/HolderMixin consolidation approach (FR-INH-004)? | Architect | Session 3 | TBD - ADR required if significant change |
| Hours deprecated aliases (FR-INH-005): keep or remove? | Architect | Session 3 | TBD - requires deprecation schedule decision |
| HealingResult consolidation: which attributes to keep? | Architect | Session 3 | TBD - healing.py has `error: Exception`, models.py has `error: str` and `entity_type` |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Subtle behavior regression from DRY consolidation | Medium | Medium | Comprehensive test suite; characterization tests before refactoring |
| Liskov fix causes unexpected side effects | Low | Medium | Minimal change: add ignored parameter to overrides |
| HealingResult consolidation breaks consumers | Medium | Medium | Keep superset of attributes; deprecate removed fields |
| Hours alias removal breaks existing callers | Medium | High | If removing: require deprecation period with warnings first |
| MRO changes from HolderFactory consolidation | Low | High | Architect review required; test all holder instantiation paths |

---

## Files to Modify

| File | Issue Count | Issues |
|------|-------------|--------|
| `process.py` | 5 | FR-LSK-001, FR-DRY-004, FR-DRY-005, FR-DRY-006 + unit property |
| `offer.py` | 5 | FR-LSK-001, FR-DRY-004, FR-DRY-005, FR-DRY-006 + unit property |
| `business.py` | 4 | FR-DRY-001, FR-DRY-002, FR-DRY-003, FR-DRY-007 |
| `unit.py` | 4 | FR-DRY-001, FR-DRY-002, FR-DRY-003, FR-DRY-007 |
| `asset_edit.py` | 2 | FR-LSK-001, FR-DRY-008 |
| `hours.py` | 1 | FR-INH-005 |
| `base.py` | 1 | FR-INH-004 (HolderMixin) |
| `holder_factory.py` | 1 | FR-INH-004 |
| `healing.py` | 1 | FR-ABS-001 |
| `models.py` | 1 | FR-ABS-001 |

---

## Complexity Estimates

### Quick Fixes (< 30 min each) - 11 issues

| Issue | Estimate | Notes |
|-------|----------|-------|
| FR-LSK-001 | 15 min | Add `_exclude_attr` param to 3 overrides |
| FR-INH-001 | 10 min | Add MRO docstring to Unit |
| FR-INH-002 | 10 min | Add MRO docstring to Offer |
| FR-ABS-004 | 15 min | Document HOLDER_KEY_MAP variation |
| FR-ABS-005 | 5 min | Document naming decision |
| FR-ABS-006 | 5 min | No change needed |
| FR-INH-003 | 0 min | Won't do (keep alias) |

### Medium Fixes (30-60 min each) - 7 issues

| Issue | Estimate | Notes |
|-------|----------|-------|
| FR-DRY-001 | 45 min | Extract shared `_identify_holder()` function |
| FR-DRY-006 | 45 min | Extract shared `business` property mixin |
| FR-ABS-001 | 60 min | Consolidate HealingResult, update imports |
| FR-DRY-004 | 45 min | UnitNavigation descriptor (if doing) |
| FR-DRY-008 | 30 min | Review AssetEdit accessors |
| FR-INH-005 | 45 min | Hours alias decision + implementation |
| FR-ABS-002/003 | 45 min | Define Protocols (if doing) |

### Large Fixes (1-2 hours each) - 2 issues

| Issue | Estimate | Notes |
|-------|----------|-------|
| FR-DRY-002/003/005/007 | 2 hours | Template method pattern for holder operations |
| FR-INH-004 | 1.5 hours | HolderFactory/HolderMixin consolidation |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Requirements Analyst | Initial draft from Discovery manifest (19 issues) |
| 2.0 | 2025-12-19 | Requirements Analyst | Updated to 20 issues per Session 2 manifest; added FR-INH-005 (Hours aliases), refined FR-ABS-005/006; added complexity estimates |

---

## Quality Gate Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out (20 issues in, Sprint 4 frozen)
- [x] All requirements are specific and testable
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented
- [x] Open questions have owners assigned (Architect for Session 3)
- [x] Priority levels assigned (MoSCoW)
- [x] Risk register with mitigations
- [x] Traceability to source manifest (20 issues mapped)
- [x] Files to modify identified
- [x] Complexity estimates provided

---

**PRD Status**: Ready for Architect Review (Session 3)
