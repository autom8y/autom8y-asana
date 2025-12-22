# Prompt -1: Initiative Scoping - Architectural Remediation Marathon

> **Purpose**: Validate readiness for the 5-sprint architectural cleanhouse initiative. Answer: "Do we know enough to scope and execute 6 phases of remediation across 10 weeks?"

---

## Initiative Summary

**One-liner**: Execute a systematic 6-phase remediation of 44 architectural failures identified across 3 triage reports, eliminating technical debt and establishing consistent patterns across the autom8_asana SDK.

**Sponsor**: SDK maintainers / platform stability

**Triggered by**: Comprehensive architectural triage identifying CRITICAL, HIGH, and MEDIUM severity issues across DRY violations, abstraction leaks, and pattern inconsistencies that compound development friction and increase bug surface area.

---

## Pre-Flight Checklist

### 1. Problem Validation

| Question | Answer | Confidence |
|----------|--------|------------|
| Is there a real problem? | **Yes** - 44 architectural failures documented: 5 CRITICAL field duplications (4x vertical, 4x rep, 3x booking_type, 3x mrr, 3x weekly_ad_spend), 2 god classes (detection.py 1016 lines, session.py 2192 lines), 5 holders not migrated to HolderFactory, scattered field resolution across 4+ modules | **High** |
| Who experiences it? | SDK developers adding features, debugging issues, or extending patterns; each duplicate requires changes in 3-4 locations; each god class requires full mental model to modify safely | **High** |
| What's the cost of not solving? | Exponential maintenance burden: every new feature requires N updates (N=duplication count), inconsistent patterns cause bugs, god classes become modification-resistant | **High** |
| Is this the right time? | **Yes** - Core SDK layers (persistence, detection, business entities) are functionally stable. Addressing debt now prevents compounding costs as more consumers adopt the SDK | **High** |

**Problem Statement Draft**:
> The autom8_asana SDK has accumulated 44 architectural failures across pattern inconsistencies, critical field duplications, and god classes. These issues increase maintenance burden exponentially - a single field like `vertical` requires changes in 4 locations, `detection.py` at 1016 lines resists safe modification, and `session.py` at 2192 lines with 14+ responsibilities violates single-responsibility principles. A systematic 6-phase remediation over 5 sprints will eliminate these issues, establishing consistent patterns and reducing the maintenance surface by an estimated 60%.

### 2. Scope Boundaries

| Dimension | In Scope | Out of Scope | Decision Rationale |
|-----------|----------|--------------|-------------------|
| **Pattern Completion** | Complete HolderFactory migration (5 holders), add descriptors to Location/Hours | New patterns not yet established, experimental approaches | Complete proven patterns before introducing new ones |
| **Field Consolidation** | 5 CRITICAL duplications (vertical, rep, booking_type, mrr, weekly_ad_spend), field mixins | LOW severity duplications, new field additions | Focus on highest-impact duplications first |
| **Method Deduplication** | _identify_holder (50 lines x 2), to_business_async (80 lines x 3), _populate_children | One-off utility functions, test helpers | Target methods with 2+ instances and significant line counts |
| **Accessor/Descriptor** | Unify CustomFieldAccessor and descriptor patterns, centralize field resolution | Redesign persistence layer, change custom field API | Resolve duality without breaking consumers |
| **Detection Decomposition** | Split detection.py into tier-based modules (types, tier1-4, facade) | Rewrite detection algorithm, add new detection tiers | Structural decomposition preserving existing behavior |
| **SaveSession Decomposition** | Split session.py into focused modules (state, tracking, operations, actions, healing, commit) | Redesign Unit of Work pattern, change SaveSession API | Structural decomposition preserving existing behavior |

### 3. Complexity Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| **Scope** | **Platform** | Touches all major SDK subsystems over 5 sprints |
| **Technical Risk** | **High** (Phases 3, 5) / **Medium** (Phases 1, 2, 4) / **Low** (Phases 0, 6) | God class decomposition and accessor unification are keystone decisions |
| **Integration Points** | **High** | Every business entity, persistence layer, detection system |
| **Team Familiarity** | **High** | Extensive codebase analysis already completed; patterns documented |
| **Unknowns** | **Medium** | Accessor/descriptor resolution requires design spike; decomposition seams not yet identified |

**Recommended Complexity Level**: Platform

**Workflow Recommendation**: Full 4-agent workflow per sprint, with sprint-level orchestration

**Rationale**: Each sprint requires discovery, requirements, architecture, implementation, and validation phases. The 5-sprint structure allows for controlled risk management - each sprint can be evaluated before proceeding to the next.

### 4. Dependencies & Blockers

| Dependency | Status | Owner | Blocking? |
|------------|--------|-------|-----------|
| HolderFactory pattern proven | **Done** | SDK Team | No - 3 holders migrated |
| Field descriptor pattern proven | **Done** | SDK Team | No - CascadingDescriptor works |
| SaveSession stable | **Done** | SDK Team | No |
| Detection system functional | **Done** | SDK Team | No |
| All existing tests passing | **In Progress** | SDK Team | **Soft block** - validate before Phase 0 |
| Accessor/Descriptor design decision | **Not Started** | @architect | **Blocking Phase 3** |

**Blockers**:
1. **Run full test suite** - Validate current state before beginning remediation
2. **Phase 3 design spike** - "Do descriptors replace accessor or wrap it?" must be answered before Sprint 2

### 5. Success Definition (Draft)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Field duplication instances | 17 across 5 fields | 5 (one per field) | Count definitions per field |
| detection.py line count | 1016 | ~200 (facade) + 5x~150 (tier modules) | wc -l |
| session.py line count | 2192 | ~6x300-400 (focused modules) | wc -l |
| Holders using HolderFactory | 3/8 | 8/8 | grep HolderFactory |
| Method duplication (_identify_holder, to_business_async) | 2+3 = 5 | 2 (one per method) | Count implementations |
| Test suite passing | ~95% | 100% | pytest |

### 6. Rough Effort Estimate

| Sprint | Phases | Effort | Confidence |
|--------|--------|--------|------------|
| Sprint 1: Pattern Completion & DRY | 0 + 1 + 2 | 2 weeks | **High** |
| Sprint 2: Field Unification | 3 | 2 weeks | **Medium** (design spike needed) |
| Sprint 3: Detection Decomposition | 4 | 2 weeks | **High** |
| Sprint 4: SaveSession Decomposition | 5 | 3 weeks | **Medium** (scope uncertainty) |
| Sprint 5: Cleanup | 6 | 1 week | **High** |
| **Total** | All 6 phases | 10 weeks | **Medium** |

### 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Breaking existing consumers** | Medium | High | Each phase maintains backward compatibility; deprecation before removal |
| **Test suite regression** | Medium | High | Run full test suite after each phase; rollback if >5% failure increase |
| **Accessor/descriptor unification complexity** | High | High | Design spike before Phase 3; fallback to "wrap, don't replace" |
| **SaveSession decomposition creates bugs** | Medium | High | Comprehensive test coverage before decomposition; preserve all existing tests |
| **Scope creep between sprints** | Medium | Medium | Strict phase boundaries; defer discoveries to Phase 6 or future initiative |
| **Detection decomposition breaks edge cases** | Low | Medium | Preserve behavior via facade pattern; tier modules are internal |

---

## The 6 Phases

### Phase 0: Foundation Completion (2-3 days) - LOW Risk

**Objective**: Complete proven patterns before introducing new consolidations.

**Deliverables**:
- Migrate 5 remaining holders to HolderFactory: ContactHolder, UnitHolder, OfferHolder, ProcessHolder, LocationHolder
- Add CascadingDescriptor usage to Location.py (business_name, address fields)
- Add CascadingDescriptor usage to Hours.py (business_name, days fields)

**Files Modified**: 6 files
- `src/autom8_asana/models/business/contact.py`
- `src/autom8_asana/models/business/unit.py`
- `src/autom8_asana/models/business/offer.py`
- `src/autom8_asana/models/business/process.py`
- `src/autom8_asana/models/business/location.py`
- `src/autom8_asana/models/business/hours.py`

### Phase 1: Field Descriptor Consolidation (3-4 days) - MEDIUM Risk

**Objective**: Eliminate 5 CRITICAL field duplications through shared mixins.

**Deliverables**:
- Create `SharedCascadingFieldsMixin` for: vertical (4x), rep (4x)
- Create `FinancialFieldsMixin` for: booking_type (3x), mrr (3x), weekly_ad_spend (3x)
- Apply mixins to Contact, Unit, Offer, Process entities
- Update tests to verify field access through mixins

**Files Modified**: 6 files
- Create `src/autom8_asana/models/business/mixins.py` (new)
- Modify `src/autom8_asana/models/business/contact.py`
- Modify `src/autom8_asana/models/business/unit.py`
- Modify `src/autom8_asana/models/business/offer.py`
- Modify `src/autom8_asana/models/business/process.py`
- Update tests

### Phase 2: Method Deduplication (2-3 days) - MEDIUM Risk

**Objective**: Extract duplicated methods to shared utilities.

**Deliverables**:
- Extract `_identify_holder` (50 lines x 2) to shared utility module
- Extract `to_business_async` (80 lines x 3) to mixin/utility
- Consolidate `_populate_children` usage patterns

**Files Modified**: 5 files
- Create `src/autom8_asana/models/business/utils.py` (new, or extend existing)
- Modify entities using _identify_holder
- Modify entities using to_business_async
- Update tests

### Phase 3: CustomFieldAccessor/Descriptor Unification (5-7 days) - HIGH Risk

**Objective**: Resolve architectural duality between accessor and descriptor patterns.

**KEYSTONE DECISION**: Do descriptors replace accessor or wrap it?

**Options**:
1. **Descriptors wrap accessor** - Accessor remains source of truth, descriptors delegate
2. **Descriptors replace accessor** - Migrate all field access to descriptors, deprecate accessor
3. **Hybrid** - Different patterns for different use cases

**Deliverables**:
- ADR documenting the decision
- Centralized field name resolution (currently scattered across 4+ modules)
- Refactored entity field access
- Updated tests

**Files Modified**: ALL entity files + persistence layer

### Phase 4: Detection Module Decomposition (3-4 days) - MEDIUM Risk

**Objective**: Split detection.py (1016 lines) into maintainable tier-based modules.

**Target Structure**:
```
src/autom8_asana/models/business/detection/
    __init__.py          # Re-exports for backward compatibility
    types.py             # EntityType, DetectionResult, enums
    tier1.py             # Project membership detection (O(1), 0 API)
    tier2.py             # Name convention detection
    tier3.py             # Parent inference detection
    tier4.py             # Structure inspection detection (API calls)
    facade.py            # detect_entity_type() - orchestrates tiers
```

**Files Modified**: 1 file -> 6 files (net 5 new)

### Phase 5: SaveSession Decomposition (7-10 days) - HIGH Risk

**Objective**: Split session.py (2192 lines, 14+ responsibilities) into focused modules.

**Target Structure**:
```
src/autom8_asana/persistence/session/
    __init__.py          # Re-exports SaveSession
    state.py             # SessionState management
    tracking.py          # Entity tracking, dirty detection
    operations.py        # PlannedOperation management
    actions.py           # ActionOperation handling
    healing.py           # Self-healing logic
    commit.py            # Commit orchestration
```

**Files Modified**: 1 file -> 7 files (net 6 new)

### Phase 6: Remaining Items (5-7 days) - LOW-MEDIUM Risk

**Objective**: Resolve remaining MEDIUM severity items.

**Deliverables**:
- 8 MEDIUM DRY violations
- Liskov violation fix in `_invalidate_refs`
- 5 MEDIUM inheritance issues
- 6 MEDIUM abstraction issues

**Characteristic**: Parallelizable - items can be addressed independently.

---

## Sprint Batching

| Sprint | Phases | Duration | Theme | Risk Level |
|--------|--------|----------|-------|------------|
| Sprint 1 | 0 + 1 + 2 | 2 weeks | Pattern Completion & DRY | LOW-MEDIUM |
| Sprint 2 | 3 | 2 weeks | Accessor/Descriptor Unification | HIGH |
| Sprint 3 | 4 | 2 weeks | Detection Decomposition | MEDIUM |
| Sprint 4 | 5 | 3 weeks | SaveSession Decomposition | HIGH |
| Sprint 5 | 6 | 1 week | Cleanup & Consolidation | LOW |

### Dependency Graph

```
Phase 0 (HolderFactory) ─────────────────────────────────────────────────┐
    │                                                                     │
    v                                                                     │
Phase 1 (Field Mixins) ────────────────────────────────────────┐         │
    │                                                           │         │
    v                                                           v         v
Phase 2 (Method Dedup) ───────────────────────────────> Phase 3 (Accessor/Descriptor)
                                                              │
                                                              v
                                        ┌─────────────────────┴─────────────────────┐
                                        │                                           │
                                        v                                           v
                                Phase 4 (Detection)                        Phase 5 (SaveSession)
                                        │                                           │
                                        └─────────────────┬─────────────────────────┘
                                                          │
                                                          v
                                                    Phase 6 (Cleanup)
```

**Notes**:
- Phase 4 can run in parallel with Phase 3 or 5 (no dependencies)
- Phase 6 must wait for all prior phases (may discover additional items during earlier phases)

---

## Open Questions to Resolve Before Prompt 0

### Must Answer (Blocking)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 1 | Do descriptors replace or wrap CustomFieldAccessor? | Replace, Wrap, Hybrid | **Wrap** - accessor is proven, descriptors add ergonomics | Requires design spike |
| 2 | What is the decomposition seam for session.py? | By operation type, by lifecycle phase, by responsibility | **By responsibility** - matches SRP | Requires analysis |
| 3 | Are all existing tests passing? | Yes/No | Must be Yes before proceeding | Requires test run |

### Should Answer (Informing)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 4 | Should mixins be abstract or concrete? | Abstract (require override), Concrete (provide default) | **Concrete** - reduce boilerplate | ? |
| 5 | Should detection tier modules be public or private? | Public (consumers can access), Private (facade only) | **Private** - internal implementation detail | ? |
| 6 | What backward compatibility period for deprecated patterns? | Immediate removal, 1 minor version, 2 minor versions | **1 minor version** - document + deprecation warning | ? |

### Nice to Answer (Context)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 7 | Should Phase 6 items be tracked in separate issues? | Yes (separate tracking), No (single cleanup issue) | **Yes** - allows parallelization | ? |
| 8 | Should we add architecture tests to prevent regression? | Yes (arch tests), No (rely on code review) | **Yes** - prevent re-introduction of god classes | ? |

---

## Spike Recommendations

### Spike 1: Accessor/Descriptor Design (2-4 hours)

**Goal**: Make keystone decision for Phase 3.

**Tasks**:
1. Document current CustomFieldAccessor usage patterns
2. Document current CascadingDescriptor usage patterns
3. Prototype "wrap" approach with 1 entity
4. Prototype "replace" approach with 1 entity
5. Compare complexity, test coverage, migration effort
6. Write ADR with recommendation

**Output**: ADR-ACCESSOR-DESCRIPTOR-UNIFICATION with clear recommendation

### Spike 2: SaveSession Responsibility Mapping (2-3 hours)

**Goal**: Identify decomposition seams for Phase 5.

**Tasks**:
1. Catalog all 14+ responsibilities in session.py
2. Group by cohesion (what changes together)
3. Identify call graph between responsibility clusters
4. Propose module boundaries
5. Identify circular dependency risks

**Output**: Decomposition map for session.py with proposed module structure

---

## Go/No-Go Decision

### Criteria for "Go"

- [x] Problem is validated and worth solving (44 documented failures)
- [x] Scope is bounded and achievable (6 phases, clear deliverables)
- [ ] No blocking dependencies (need test suite validation, design spike)
- [x] Complexity level appropriate for chosen workflow
- [x] Success metrics are measurable
- [x] Rough effort estimate acceptable (10 weeks)
- [x] High-risk items have mitigation plans

### Recommendation

**CONDITIONAL GO** - Begin with Sprint 1 while completing blocking dependencies

**Rationale**:
- 44 architectural failures are documented with high confidence
- 6-phase plan with clear deliverables and boundaries
- Sprint 1 (Phases 0, 1, 2) has no blocking dependencies on design spikes
- Design spike for Phase 3 can run in parallel with Sprint 1 execution
- Each sprint is independently valuable - can stop after any sprint if priorities change

**Conditions (for full GO on Sprints 2-5)**:
- Test suite passes at >95% before Phase 0
- Accessor/Descriptor design spike complete before Sprint 2
- SaveSession responsibility mapping complete before Sprint 4

---

## Next Steps

1. **Run full test suite** (30 minutes)
   - Validate current baseline
   - Document any pre-existing failures

2. **Create Prompt 0 for Sprint 1** (1 hour)
   - Phases 0, 1, 2
   - Pattern completion and DRY focus
   - LOW-MEDIUM risk

3. **Execute Spike 1: Accessor/Descriptor Design** (2-4 hours, parallel with Sprint 1)
   - Required for Sprint 2
   - ADR output

4. **Create Prompt 0 documents for Sprints 2-5** (2 hours)
   - Can be created now with placeholders for spike outputs

5. **Execute Sprint 1** (2 weeks)
   - Complete HolderFactory migration
   - Create field mixins
   - Deduplicate methods

---

## Appendix: Failure Inventory

### CRITICAL (5 items - Phase 1)

| Field | Duplication | Files |
|-------|-------------|-------|
| vertical | 4x | Contact, Unit, Offer, Process |
| rep | 4x | Contact, Unit, Offer, Process |
| booking_type | 3x | Unit, Offer, Process |
| mrr | 3x | Unit, Offer, Process |
| weekly_ad_spend | 3x | Unit, Offer, Process |

### HIGH (2 items - Phases 4, 5)

| Issue | Lines | File |
|-------|-------|------|
| detection.py god class | 1016 | detection.py |
| session.py god class | 2192 | session.py |

### MEDIUM (19 items - Phase 6)

- 8 DRY violations (various files)
- 1 Liskov violation (_invalidate_refs)
- 5 inheritance issues
- 6 abstraction issues

### Pattern Gaps (Phase 0)

| Pattern | Missing | Status |
|---------|---------|--------|
| HolderFactory | 5 holders (Contact, Unit, Offer, Process, Location) | Not migrated |
| CascadingDescriptor | Location.py, Hours.py | Not using descriptors |

### Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| HolderFactory Pattern | `src/autom8_asana/models/business/holder_factory.py` | Phase 0 reference |
| Field Descriptor Pattern | `src/autom8_asana/models/business/base.py` | Phase 1 reference |
| Detection System | `src/autom8_asana/models/business/detection.py` | Phase 4 target |
| SaveSession | `src/autom8_asana/persistence/session.py` | Phase 5 target |
| Existing ADRs | `/docs/decisions/` | Pattern decisions |

---

*This Prompt -1 **conditionally validates** that the initiative is ready for the 5-sprint architectural remediation. Proceed with Sprint 1 Prompt 0 while completing design spikes in parallel.*
