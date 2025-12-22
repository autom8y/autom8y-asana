# Orchestrator Initialization: Sprint 1 - Pattern Completion and DRY Consolidation

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana`** - SDK patterns, SaveSession, Business entities, HolderFactory, field descriptors
  - Activates when: Working with holder migration, field descriptors, entity patterns

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

- **`prompting`** - Agent invocation patterns, workflow examples
  - Activates when: Invoking agents, structuring prompts

**How Skills Work**: Skills load automatically based on your current task. When you need SDK-specific patterns (like HolderFactory), the `autom8-asana` skill activates.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

---

## The Mission: Complete Pattern Migration and Eliminate Critical Field Duplications

Sprint 1 addresses the foundation layers of the architectural remediation: completing proven patterns (HolderFactory, CascadingDescriptor) and eliminating the 5 CRITICAL field duplications that require 3-4x maintenance effort per change. This sprint is LOW-MEDIUM risk because all patterns are already proven in the codebase - we are extending, not inventing.

### Why This Sprint?

- **Pattern Completion**: 5 holders (ContactHolder, UnitHolder, OfferHolder, ProcessHolder, LocationHolder) still use legacy pattern; HolderFactory provides 90% code reduction
- **Descriptor Coverage**: Location.py and Hours.py don't use CascadingDescriptor; adding descriptors ensures consistent field access
- **Field Consolidation**: 17 instances of 5 fields (vertical, rep, booking_type, mrr, weekly_ad_spend) create 3-4x maintenance burden
- **Method Deduplication**: `_identify_holder` (50 lines x 2) and `to_business_async` (80 lines x 3) are maintenance hazards

### Current State

**HolderFactory Migration Status**:
- Migrated: DNAHolder, ReconciliationHolder, AssetEditHolder (3 holders)
- Remaining: ContactHolder, UnitHolder, OfferHolder, ProcessHolder, LocationHolder (5 holders)
- Pattern location: `src/autom8_asana/models/business/holder_factory.py`

**CascadingDescriptor Usage**:
- Using descriptors: Contact, Unit, Offer, Process, Business entities
- Not using descriptors: Location.py, Hours.py
- Pattern location: `src/autom8_asana/models/business/base.py`

**Field Duplication Inventory**:

| Field | Instances | Files |
|-------|-----------|-------|
| vertical | 4 | Contact, Unit, Offer, Process |
| rep | 4 | Contact, Unit, Offer, Process |
| booking_type | 3 | Unit, Offer, Process |
| mrr | 3 | Unit, Offer, Process |
| weekly_ad_spend | 3 | Unit, Offer, Process |

**Method Duplication**:
- `_identify_holder`: 50 lines x 2 locations
- `to_business_async`: 80 lines x 3 locations
- `_populate_children`: varies by entity

### Sprint Profile

| Attribute | Value |
|-----------|-------|
| Duration | 2 weeks |
| Phases | 0 (Foundation) + 1 (Fields) + 2 (Methods) |
| Risk Level | LOW-MEDIUM |
| Blast Radius | ~12 files |
| Prerequisites | Test suite passing at >95% |
| Success Metric | 5 holders migrated, 17 field instances -> 5, 5 method instances -> 2 |

### Target Architecture

**Before (Phase 0)**:
```python
# ContactHolder - 100+ lines of boilerplate
class ContactHolder(Task, HolderMixin[Contact]):
    _children: list[Contact]
    _child_type = Contact
    _parent_ref_field = "_contact_holder"

    @property
    def contacts(self) -> list[Contact]:
        return self._children

    async def fetch_children(self, client: AsyncAsanaClient) -> None:
        # 20+ lines of fetch logic
        ...
```

**After (Phase 0)**:
```python
# ContactHolder - 2 lines
class ContactHolder(HolderFactory, child_type="Contact", parent_ref="_contact_holder"):
    """Holder for Contact entities. Inherits all behavior from HolderFactory."""
```

**Before (Phase 1)**:
```python
# In Contact, Unit, Offer, Process - 4x each
@property
def vertical(self) -> str | None:
    return self._get_custom_field("Vertical")
```

**After (Phase 1)**:
```python
# In mixins.py - 1x
class SharedCascadingFieldsMixin:
    vertical = CascadingDescriptor("Vertical", cascade_from="unit")
    rep = CascadingDescriptor("Rep", cascade_from="unit")

# In Contact, Unit, Offer, Process
class Contact(SharedCascadingFieldsMixin, ...):
    pass  # vertical and rep inherited
```

### Key Constraints

- **Backward Compatibility**: All existing public APIs must continue to work unchanged
- **Test Preservation**: Existing tests must pass; add tests for new patterns
- **No Behavior Changes**: This is refactoring, not feature addition
- **Incremental Migration**: Each holder can be migrated independently
- **Mixin Composition**: Mixins should be composable without conflicts

### Requirements Summary

| Requirement | Priority | Phase |
|-------------|----------|-------|
| Migrate ContactHolder to HolderFactory | Must | 0 |
| Migrate UnitHolder to HolderFactory | Must | 0 |
| Migrate OfferHolder to HolderFactory | Must | 0 |
| Migrate ProcessHolder to HolderFactory | Must | 0 |
| Migrate LocationHolder to HolderFactory | Must | 0 |
| Add CascadingDescriptor to Location.py | Must | 0 |
| Add CascadingDescriptor to Hours.py | Must | 0 |
| Create SharedCascadingFieldsMixin (vertical, rep) | Must | 1 |
| Create FinancialFieldsMixin (booking_type, mrr, weekly_ad_spend) | Must | 1 |
| Apply mixins to Contact, Unit, Offer, Process | Must | 1 |
| Extract _identify_holder to shared utility | Must | 2 |
| Extract to_business_async to mixin/utility | Must | 2 |
| Consolidate _populate_children patterns | Should | 2 |
| Add unit tests for mixins | Must | 1 |
| Update existing tests for new patterns | Must | All |

### Success Criteria

1. All 8 holder classes use HolderFactory pattern
2. Location.py uses CascadingDescriptor for business_name, address fields
3. Hours.py uses CascadingDescriptor for relevant fields
4. `vertical` field defined in 1 location (SharedCascadingFieldsMixin), used by 4 entities
5. `rep` field defined in 1 location (SharedCascadingFieldsMixin), used by 4 entities
6. `booking_type`, `mrr`, `weekly_ad_spend` defined in 1 location (FinancialFieldsMixin)
7. `_identify_holder` defined in 1 location, called from 2+ entities
8. `to_business_async` defined in 1 location, called from 3+ entities
9. All existing tests pass
10. New tests cover mixin behavior

### Performance Targets

| Metric | Before | After |
|--------|--------|-------|
| Lines in holder classes (total) | ~600 | ~50 |
| Field definition instances | 17 | 5 |
| Method definition instances | 5 | 2 |
| Test suite pass rate | >95% | 100% |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | HolderFactory pattern analysis, field duplication map, method duplication inventory |
| **2: Requirements** | Requirements Analyst | PRD-SPRINT-1-PATTERN-COMPLETION with acceptance criteria |
| **3: Architecture** | Architect | TDD-SPRINT-1 + ADR for mixin composition strategy |
| **4: Implementation P1** | Principal Engineer | Phase 0: HolderFactory migrations (5 holders) + Location/Hours descriptors |
| **5: Implementation P2** | Principal Engineer | Phase 1: SharedCascadingFieldsMixin, FinancialFieldsMixin, apply to entities |
| **6: Implementation P3** | Principal Engineer | Phase 2: Method extraction (_identify_holder, to_business_async) |
| **7: Validation** | QA/Adversary | Pattern verification, test coverage, regression testing |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Codebase Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/models/business/holder_factory.py` | What are the exact `__init_subclass__` parameters? What's auto-generated? |
| `src/autom8_asana/models/business/contact.py` | What fields need CascadingDescriptor? What's ContactHolder's current structure? |
| `src/autom8_asana/models/business/unit.py` | What fields are duplicated? What's UnitHolder's current structure? |
| `src/autom8_asana/models/business/offer.py` | What fields are duplicated? What's OfferHolder's current structure? |
| `src/autom8_asana/models/business/process.py` | What fields are duplicated? What's ProcessHolder's current structure? |
| `src/autom8_asana/models/business/location.py` | What fields need CascadingDescriptor? What's LocationHolder's current structure? |
| `src/autom8_asana/models/business/hours.py` | What fields need CascadingDescriptor? |

### Pattern Analysis

| Pattern | Questions to Answer |
|---------|---------------------|
| HolderFactory | What are `child_type`, `parent_ref` parameters for each holder? |
| CascadingDescriptor | What cascade chains exist (entity -> parent -> grandparent)? |
| Field access | Are there any custom getters that can't use descriptors? |
| Method signatures | Are `_identify_holder` and `to_business_async` identical or do they vary? |

### Duplication Inventory

| Area | Questions |
|------|-----------|
| Field definitions | Exact file:line locations for each duplicated field |
| Method definitions | Exact file:line locations for each duplicated method |
| Cascade chains | What's the inheritance chain for each field? |
| Test coverage | What tests exercise each field/method? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Pattern Questions

1. **HolderFactory child_type**: Should `child_type` be a string or class reference?
2. **Descriptor cascade order**: When multiple ancestors define a field, what's the resolution order?
3. **Mixin method resolution**: How should mixins interact with `__init_subclass__`?

### Field Questions

4. **Null handling**: How should descriptors handle None values from parent entities?
5. **Override capability**: Can an entity override a mixin-provided field?
6. **Custom field names**: Are field names identical across all Asana projects?

### Method Questions

7. **Signature compatibility**: Do all instances of `_identify_holder` have identical signatures?
8. **Async/sync variants**: Does `to_business_async` have a sync equivalent that also needs extraction?

---

## Scope Boundaries

### Explicitly In Scope

- Phase 0: HolderFactory migration (5 holders)
- Phase 0: CascadingDescriptor for Location, Hours
- Phase 1: SharedCascadingFieldsMixin (vertical, rep)
- Phase 1: FinancialFieldsMixin (booking_type, mrr, weekly_ad_spend)
- Phase 2: Method extraction (_identify_holder, to_business_async)
- Tests for all new patterns
- Backward compatibility for all public APIs

### Explicitly Out of Scope

- CustomFieldAccessor changes (Sprint 2)
- Detection module changes (Sprint 3)
- SaveSession changes (Sprint 4)
- New field additions
- Performance optimization
- API documentation updates (defer to post-remediation)
- CI/CD changes

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| HolderFactory `__init_subclass__` edge cases | Low | Medium | Follow exact pattern from working holders (DNA, Reconciliation, AssetEdit) |
| Mixin composition conflicts | Medium | Medium | Test mixin combinations before full rollout |
| Field cascade resolution differs per entity | Medium | Medium | Document cascade chains in discovery; handle edge cases explicitly |
| Method signature drift | Low | Low | Verify signatures match before extraction |
| Test regression | Medium | High | Run full test suite after each holder migration |

---

## Dependencies

### Prerequisites (Already Implemented)

| Dependency | Status | Notes |
|------------|--------|-------|
| HolderFactory base class | Implemented | Proven with 3 holders |
| CascadingDescriptor | Implemented | Proven with Contact, Unit, etc. |
| DNAHolder (reference) | Implemented | Pattern to follow |
| ReconciliationHolder (reference) | Implemented | Pattern to follow |
| AssetEditHolder (reference) | Implemented | Pattern to follow |

### Implementation Dependencies

| Dependency | Blocks | Notes |
|------------|--------|-------|
| Test suite passing | Phase 0 start | Baseline validation required |
| HolderFactory migrations | Phase 1 | Mixins may need holder references |
| Phase 1 complete | Phase 2 | Method extraction may reference mixin fields |

---

## File Inventory

### Files to Modify

| File | Phase | Changes |
|------|-------|---------|
| `contact.py` | 0, 1 | Migrate ContactHolder, apply mixins |
| `unit.py` | 0, 1 | Migrate UnitHolder, apply mixins |
| `offer.py` | 0, 1 | Migrate OfferHolder, apply mixins |
| `process.py` | 0, 1 | Migrate ProcessHolder, apply mixins |
| `location.py` | 0 | Migrate LocationHolder, add descriptors |
| `hours.py` | 0 | Add descriptors |

### Files to Create

| File | Phase | Purpose |
|------|-------|---------|
| `mixins.py` | 1 | SharedCascadingFieldsMixin, FinancialFieldsMixin |
| `utils.py` (or extend) | 2 | _identify_holder, to_business_async |

### Test Files to Update

| File | Changes |
|------|---------|
| `test_contact.py` | Add mixin tests, verify holder behavior |
| `test_unit.py` | Add mixin tests, verify holder behavior |
| `test_offer.py` | Add mixin tests, verify holder behavior |
| `test_process.py` | Add mixin tests, verify holder behavior |
| `test_location.py` | Verify descriptor behavior |
| `test_hours.py` | Verify descriptor behavior |
| (new) `test_mixins.py` | Unit tests for mixin behavior |

---

## Your First Task

Confirm understanding by:

1. Summarizing the Sprint 1 goal in 2-3 sentences (Pattern completion + field consolidation + method deduplication)
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step - mapping exact duplication locations
4. Confirming which files must be analyzed before PRD-SPRINT-1-PATTERN-COMPLETION
5. Listing which open questions you need answered before Session 2
6. Noting the key constraint: this is refactoring only - no behavior changes

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Sprint 1 Pattern Discovery

Work with the @requirements-analyst agent to analyze existing patterns and map duplications.

**Goals:**
1. Document HolderFactory pattern requirements (child_type, parent_ref for each holder)
2. Map exact field duplication locations (file:line for all 17 instances)
3. Map exact method duplication locations (file:line for _identify_holder, to_business_async)
4. Document CascadingDescriptor usage patterns and cascade chains
5. Identify any edge cases or custom overrides that break patterns
6. Verify test coverage for each duplicated element
7. Document mixin composition requirements

**Files to Analyze:**
- `src/autom8_asana/models/business/holder_factory.py` - Pattern reference
- `src/autom8_asana/models/business/business.py` - Working holder examples
- `src/autom8_asana/models/business/contact.py` - Migration target
- `src/autom8_asana/models/business/unit.py` - Migration target
- `src/autom8_asana/models/business/offer.py` - Migration target
- `src/autom8_asana/models/business/process.py` - Migration target
- `src/autom8_asana/models/business/location.py` - Migration target
- `src/autom8_asana/models/business/hours.py` - Descriptor target

**Deliverable:**
A discovery document with:
- HolderFactory parameter mapping for each holder
- Field duplication inventory with exact locations
- Method duplication inventory with signature analysis
- Cascade chain documentation
- Edge case registry
- Test coverage map

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Sprint 1 Requirements Definition

Work with the @requirements-analyst agent to create PRD-SPRINT-1-PATTERN-COMPLETION.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define HolderFactory migration requirements for each holder
2. Define CascadingDescriptor requirements for Location, Hours
3. Define SharedCascadingFieldsMixin requirements
4. Define FinancialFieldsMixin requirements
5. Define method extraction requirements
6. Define acceptance criteria for each migration
7. Define backward compatibility requirements

**Key Questions to Address:**
- What makes a holder migration "complete"?
- How do we verify field access works through mixins?
- What's the rollback strategy if a migration breaks?
- How do we handle edge cases discovered in discovery?

**PRD Organization:**
- FR-HOLDER-*: HolderFactory migration requirements
- FR-DESC-*: CascadingDescriptor requirements
- FR-MIXIN-*: Mixin requirements
- FR-METHOD-*: Method extraction requirements
- FR-COMPAT-*: Backward compatibility requirements
- NFR-*: Test coverage, code reduction metrics

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Sprint 1 Architecture Design

Work with the @architect agent to create TDD-SPRINT-1-PATTERN-COMPLETION and ADR for mixin strategy.

**Prerequisites:**
- PRD-SPRINT-1-PATTERN-COMPLETION approved

**Goals:**
1. Design mixin class hierarchy
2. Design method extraction module structure
3. Document mixin composition rules
4. Document migration order (which holder first?)
5. Define rollback procedures
6. Create ADR for mixin composition strategy

**Required ADR:**
- ADR-0116: Mixin Composition Strategy for Field Consolidation

**Design Questions:**
- Should mixins inherit from object or a base class?
- How do mixins interact with __init_subclass__?
- What's the test isolation strategy for mixins?

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Foundation Completion (Phase 0)

Work with the @principal-engineer agent to migrate holders and add descriptors.

**Prerequisites:**
- PRD and TDD approved
- Test suite passing

**Phase 0 Scope:**
1. Migrate ContactHolder to HolderFactory
2. Migrate UnitHolder to HolderFactory
3. Migrate OfferHolder to HolderFactory
4. Migrate ProcessHolder to HolderFactory
5. Migrate LocationHolder to HolderFactory
6. Add CascadingDescriptor to Location.py
7. Add CascadingDescriptor to Hours.py

**Migration Order:**
1. LocationHolder (simplest, no children)
2. ContactHolder (medium complexity)
3. UnitHolder (medium complexity)
4. OfferHolder (medium complexity)
5. ProcessHolder (most complex)

**Hard Constraints:**
- Run tests after each holder migration
- No behavior changes
- Preserve all public APIs

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Field Consolidation (Phase 1)

Work with the @principal-engineer agent to create mixins and apply to entities.

**Prerequisites:**
- Phase 0 complete and tested

**Phase 1 Scope:**
1. Create mixins.py with SharedCascadingFieldsMixin
2. Add vertical, rep fields to SharedCascadingFieldsMixin
3. Create FinancialFieldsMixin
4. Add booking_type, mrr, weekly_ad_spend to FinancialFieldsMixin
5. Apply SharedCascadingFieldsMixin to Contact, Unit, Offer, Process
6. Apply FinancialFieldsMixin to Unit, Offer, Process
7. Remove duplicate field definitions
8. Add unit tests for mixins

**Integration Points:**
- Mixins must work with CascadingDescriptor
- Field access must be identical to current behavior
- Tests must verify cascade chains

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Method Deduplication (Phase 2)

Work with the @principal-engineer agent to extract duplicated methods.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Create utils.py (or extend existing)
2. Extract _identify_holder to shared utility
3. Update callers to use shared _identify_holder
4. Extract to_business_async to mixin or utility
5. Update callers to use shared to_business_async
6. Consolidate _populate_children patterns where possible
7. Remove duplicate method definitions
8. Add unit tests for extracted methods

**Design Decision:**
- _identify_holder: Standalone function (stateless)
- to_business_async: Mixin method (needs entity context)

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Sprint 1 Validation

Work with the @qa-adversary agent to validate the sprint deliverables.

**Prerequisites:**
- All implementation phases complete

**Goals:**

**Part 1: HolderFactory Validation**
- All 8 holders use HolderFactory pattern
- Children access works correctly
- Parent references set correctly
- Lazy loading behavior preserved

**Part 2: Descriptor Validation**
- Location fields accessible via descriptors
- Hours fields accessible via descriptors
- Cascade chains work correctly

**Part 3: Mixin Validation**
- vertical field works on Contact, Unit, Offer, Process
- rep field works on Contact, Unit, Offer, Process
- Financial fields work on Unit, Offer, Process
- No conflicts between mixins

**Part 4: Method Validation**
- _identify_holder works from all call sites
- to_business_async works from all call sites
- Behavior identical to pre-extraction

**Part 5: Regression Testing**
- All existing tests pass
- No performance regression
- No memory leaks

**Part 6: Metrics Verification**
- Count holder class lines (target: ~50 total)
- Count field definition instances (target: 5)
- Count method definition instances (target: 2)

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**HolderFactory Context:**

- [ ] `holder_factory.py` - HolderFactory base class, __init_subclass__ parameters
- [ ] `business.py` - DNAHolder, ReconciliationHolder, AssetEditHolder examples
- [ ] Each holder's current structure and child_type

**Field Duplication Context:**

- [ ] vertical field locations (4 files)
- [ ] rep field locations (4 files)
- [ ] booking_type field locations (3 files)
- [ ] mrr field locations (3 files)
- [ ] weekly_ad_spend field locations (3 files)
- [ ] CascadingDescriptor usage patterns
- [ ] Cascade chain documentation

**Method Duplication Context:**

- [ ] _identify_holder implementations (2 locations)
- [ ] to_business_async implementations (3 locations)
- [ ] _populate_children variations
- [ ] Signature comparison

**Test Context:**

- [ ] Existing test coverage for fields
- [ ] Existing test coverage for methods
- [ ] Existing test coverage for holders
- [ ] Test suite baseline pass rate
