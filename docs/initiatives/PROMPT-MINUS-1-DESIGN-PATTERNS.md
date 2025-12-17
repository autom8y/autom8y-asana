# Prompt -1: Design Patterns Sprint (Meta-Initiative)

> **Purpose**: Define the overarching "session of sessions" that will systematically leverage Pythonic design patterns to reduce code duplication, improve type safety, and enhance maintainability across the autom8_asana SDK.

---

## Initiative Summary

**One-liner**: Leverage 5 high-impact Python design patterns to eliminate ~2,550 lines of duplicated code while improving type safety and developer experience.

**Sponsor**: SDK Architecture Team

**Triggered by**: Architect's comprehensive design pattern analysis following the success of the Navigation Descriptor Pattern (Initiative C, ~800 lines eliminated).

**Reference Document**: `/docs/architecture/DESIGN-PATTERN-OPPORTUNITIES.md`

---

## Meta-Initiative Context

This is a **meta-initiative** that coordinates multiple sub-initiatives. Unlike a typical Prompt -1 which leads to a single Prompt 0, this document:

1. **Contextualizes** the full scope of design pattern opportunities
2. **Segments** 5 pattern opportunities into logical, cohesive initiatives (A through E)
3. **Sequences** initiatives by risk and dependency
4. **Identifies** cross-initiative concerns and synergies
5. **Establishes** success criteria for the overall pattern adoption effort

Each sub-initiative has its own Prompt 0 and can be executed in a separate Claude Code session.

---

## Pre-Flight Checklist

### 1. Problem Validation

| Question | Answer | Confidence |
|----------|--------|------------|
| Is there a real problem? | Yes - Architect identified 5 pattern opportunities with ~2,550 lines of duplication | High |
| Who experiences it? | SDK maintainers (code bloat), SDK consumers (inconsistent APIs), future contributors | High |
| What's the cost of not solving? | Continued duplication, copy-paste bugs, inconsistent behavior across similar code paths | High |
| Is this the right time? | Yes - Navigation Descriptor success proves the approach; SDK is pre-GA so changes don't break consumers | High |

**Problem Statement Draft**:
> The autom8_asana SDK contains significant code duplication across multiple areas: async/sync method pairs (~1,200 lines), custom field property boilerplate (~400 lines), holder class implementations (~300 lines), error classification logic (~150 lines), and CRUD client methods (~500 lines). The successful Navigation Descriptor Pattern in Initiative C demonstrated that well-designed Python patterns can eliminate substantial duplication while improving type safety. This sprint applies the same approach systematically across the remaining duplication hotspots.

### 2. Pattern Opportunity Inventory

The Architect identified 5 high-impact opportunities:

| # | Pattern | Description | Lines Saved | Complexity | Risk |
|---|---------|-------------|-------------|------------|------|
| **A** | Custom Field Property Descriptor | Unifies field accessor boilerplate with `TextField`, `EnumField`, `NumberField` descriptors | ~400 | Low | Low |
| **B** | Error Classification Mixin | Eliminates duplicated `is_retryable`/`recovery_hint` logic in `SaveError` and `ActionResult` | ~150 | Low | Low |
| **C** | Holder Factory (`__init_subclass__`) | Consolidates 4 near-identical holder implementations into declarative pattern | ~300 | Medium | Medium |
| **D** | Async/Sync Method Generator | Decorator generating method pairs with proper `@overload` signatures | ~1,200 | Medium | Medium |
| **E** | CRUD Client Metaclass | Auto-generates standard CRUD methods from model + resource_name config | ~500 | High | High |

**Total Estimated Savings**: ~2,550 lines of code

### 3. Scope Boundaries

| Dimension | In Scope | Out of Scope | Decision Rationale |
|-----------|----------|--------------|-------------------|
| **Pattern Types** | Descriptors, mixins, `__init_subclass__`, decorators, metaclasses | Factory patterns, dependency injection | Focus on code-generation/elimination patterns |
| **Affected Code** | Business models, holders, error types, client methods | Test infrastructure, documentation | Target production SDK code |
| **API Changes** | Internal refactoring; preserve public API surface | Breaking API changes | Maintain backward compatibility |
| **Tooling** | Runtime patterns only | `.pyi` stub generation (may revisit in D) | Keep scope manageable initially |

### 4. Complexity Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| **Scope** | Module-level (5 independent pattern areas) | Each pattern is self-contained |
| **Technical Risk** | Low to High (varies by pattern) | Sequenced from lowest to highest risk |
| **Integration Points** | Medium | Patterns affect models, errors, clients |
| **Team Familiarity** | High for descriptors; Medium for metaclasses | Navigation Descriptors proved approach |
| **Unknowns** | Low | Architect provided detailed designs |

**Recommended Complexity Level**: Module (per sub-initiative)

**Workflow Recommendation**: Full 4-agent workflow per sub-initiative

**Rationale**: Each pattern benefits from proper PRD, TDD, implementation, and validation phases. The patterns are independent enough to be separate initiatives but share common success criteria.

### 5. Initiative Segmentation

Initiatives are ordered by risk (lowest first) and grouped by pattern similarity:

#### Initiative A: Custom Field Property Descriptors
**Pattern**: Custom Field Descriptor
**Issues Addressed**: Repetitive property boilerplate in Business, Contact, Unit, Offer, Process models
**Risk**: Low (descriptors proven with Navigation Pattern)
**Value**: High (immediate ~400 lines, plus consistency)
**Depends On**: None (builds on existing Navigation Descriptor success)

| Deliverable | Description |
|-------------|-------------|
| `TextField`, `EnumField`, `NumberField` | Descriptor classes for common field types |
| `PeopleField`, `DateField` | Descriptor classes for complex field types |
| Migrated Business model | 19 fields converted to descriptors |
| Migrated Contact, Unit, Offer, Process | All custom field properties converted |

#### Initiative B: Error Classification Mixin
**Pattern**: RetryableErrorMixin
**Issues Addressed**: Duplicated `is_retryable`, `recovery_hint` in SaveError and ActionResult
**Risk**: Low (simple mixin, no magic)
**Value**: Medium (~150 lines, plus single source of truth)
**Depends On**: None

| Deliverable | Description |
|-------------|-------------|
| `RetryableErrorMixin` | Mixin providing error classification |
| `HasError` protocol | Protocol for types with error property |
| Updated SaveError | Uses mixin for classification |
| Updated ActionResult | Uses mixin for classification |

#### Initiative C: Holder Factory with `__init_subclass__`
**Pattern**: `__init_subclass__` class factory
**Issues Addressed**: 4 near-identical holder implementations (DNA, Reconciliation, AssetEdit, Videography)
**Risk**: Medium (`__init_subclass__` less familiar, but well-documented)
**Value**: Medium (~300 lines, plus extensibility)
**Depends On**: None (but benefits from A's descriptor familiarity)

| Deliverable | Description |
|-------------|-------------|
| `HolderBase` | Base class with `__init_subclass__` hook |
| Migrated DNAHolder | 3-line declaration |
| Migrated ReconciliationHolder | 3-line declaration |
| Migrated AssetEditHolder, VideographyHolder | 3-line declarations |

#### Initiative D: Async/Sync Method Generator
**Pattern**: Method generator decorator
**Issues Addressed**: Massive client method duplication (~48 lines per method)
**Risk**: Medium (requires careful `@overload` handling for IDE support)
**Value**: Very High (~1,200 lines across all clients)
**Depends On**: None (but benefits from pattern momentum)

| Deliverable | Description |
|-------------|-------------|
| `@async_method` decorator | Generates async/sync pairs from single definition |
| `AsyncSyncMethodPair` descriptor | Runtime method pair access |
| Migrated SectionsClient | Proof of concept |
| Migration guide | For remaining clients |

#### Initiative E: CRUD Client Metaclass
**Pattern**: Metaclass with method generation
**Issues Addressed**: Identical CRUD patterns across TasksClient, SectionsClient, TagsClient, ProjectsClient
**Risk**: High (metaclasses are powerful but complex)
**Value**: High (~500+ lines, plus consistency)
**Depends On**: Initiative D (may share patterns)
**Recommendation**: Consider after D validates method generation approach

| Deliverable | Description |
|-------------|-------------|
| `CRUDClientMeta` | Metaclass generating CRUD methods |
| `CRUDClient[T]` | Generic base class |
| Migrated SectionsClient | Proof of concept |
| Evaluation report | Go/no-go for remaining clients |

### 6. Dependency Graph

```
                    +------------------+
                    |   A: Custom      |
                    | Field Descriptor |
                    |   (Low Risk)     |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
    +---------+----+             +----------+--------+
    | B: Error     |             | C: Holder         |
    | Mixin        |             | Factory           |
    | (Low Risk)   |             | (Medium Risk)     |
    +--------------+             +-------------------+
              |                             |
              +-------------+---------------+
                            |
                            v
                  +---------+---------+
                  | D: Async/Sync     |
                  | Method Generator  |
                  | (Medium Risk)     |
                  +--------+----------+
                           |
                           v
                  +--------+----------+
                  | E: CRUD Client    |
                  | Metaclass         |
                  | (High Risk)       |
                  +-------------------+
```

### 7. Execution Strategy

#### Phase 1: Quick Wins (1-2 sessions each)

1. **Initiative A: Custom Field Descriptors** (1-2 sessions)
   - Lowest risk, highest familiarity
   - Proven descriptor pattern from Navigation
   - Immediate visible impact

2. **Initiative B: Error Classification Mixin** (1 session)
   - Simple mixin pattern
   - Quick win to build momentum

#### Phase 2: Medium Lift (2-3 sessions each)

3. **Initiative C: Holder Factory** (1-2 sessions)
   - Moderate complexity
   - Prepares codebase for future holders

4. **Initiative D: Async/Sync Generator** (2-3 sessions)
   - Highest single impact
   - May need IDE compatibility spike

#### Phase 3: Major Refactor (3+ sessions)

5. **Initiative E: CRUD Metaclass** (2-3 sessions)
   - Highest complexity
   - Consider after D validates approach
   - May be deferred or descoped based on D learnings

**Total estimated sessions**: 8-12 across all initiatives

### 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **IDE support degradation** | Medium | High | Test with VSCode/PyCharm before merging; consider `.pyi` stubs |
| **Pydantic compatibility** | Low | High | Follow ADR-0077 pattern (no type annotations on descriptors) |
| **Runtime performance regression** | Low | Medium | Profile descriptor `__get__` calls; cache where needed |
| **Debugging difficulty** | Medium | Medium | Add clear `__repr__` to all descriptors; comprehensive logging |
| **Scope creep within initiatives** | Medium | Low | Strict scope boundaries in each Prompt 0 |
| **Initiative E complexity underestimated** | Medium | Medium | Defer E if D learnings suggest higher risk |

---

## Success Criteria (Meta-Initiative)

### Per-Initiative Success

Each sub-initiative defines its own success criteria in its Prompt 0. The meta-initiative succeeds when:

1. **All Low-risk initiatives (A, B) completed**
2. **Medium-risk initiatives (C, D) completed or have explicit deferral rationale**
3. **High-risk initiative (E) evaluated with go/no-go decision**
4. **No regressions in existing functionality** (test suite passes)
5. **IDE autocomplete preserved** for all refactored code
6. **Each initiative's PRD acceptance criteria met**

### Measurable Outcomes

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Custom field property lines | ~800 (5 models) | ~200 (descriptors) | `wc -l` before/after |
| Error classification duplication | 2 copies (~150 lines) | 1 (mixin) | Code inspection |
| Holder implementation lines | ~400 (4 holders) | ~100 (factory) | `wc -l` before/after |
| Client method lines per operation | ~48 | ~12 | Sample measurement |
| Test coverage | >95% | >95% | `pytest --cov` |
| Type check pass | 100% | 100% | `mypy --strict` |

---

## Open Questions (Meta-Level)

### Must Answer Before Starting

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 1 | Can initiatives run in parallel? | Yes (independent) / No (sequential) | Yes for A+B, then C+D in parallel | Answered |
| 2 | Should E (metaclass) be included or deferred? | Include / Defer to future sprint | Include with explicit go/no-go checkpoint | Answered |
| 3 | What's the backward compatibility policy? | Strict / Deprecation warnings / Breaking | Deprecation warnings for any API changes | Answered |

### Should Answer (Informing)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 4 | Should we generate `.pyi` stubs for D? | Yes / No / Evaluate during D | Evaluate during D | Open |
| 5 | How to handle existing unit tests? | Update in-place / Write new tests | Update in-place; add pattern-specific tests | Answered |

---

## Why Now?

### Evidence of Success

The **Navigation Descriptor Pattern** (Initiative C of Architecture Hardening) proved this approach works:
- Eliminated ~800 lines of duplicated `@property` implementations
- Improved consistency across 10 business entities
- Maintained full Pydantic compatibility (ADR-0077)
- Preserved IDE autocomplete
- Documented in ADR-0075, ADR-0076, ADR-0077

### Window of Opportunity

- **Pre-GA timing**: SDK is not yet generally available; changes now don't break external consumers
- **Pattern momentum**: Team has fresh experience with descriptor patterns
- **Architecture clarity**: Architect's analysis provides clear guidance
- **Incremental approach**: Each initiative is independent; can pause if needed

### Cost of Delay

- Continued accumulation of copy-paste bugs
- Higher maintenance burden for each new feature
- Increasing test coverage requirements for duplicated code
- Missed opportunity to establish patterns before API stabilization

---

## Go/No-Go Decision

### Criteria for "Go"

- [x] Problems are validated and documented (Architect's analysis)
- [x] Patterns are proven (Navigation Descriptor success)
- [x] Scope is bounded into manageable initiatives
- [x] Dependencies are mapped
- [x] Risk levels are assessed with mitigations
- [x] Success metrics are measurable
- [x] Rough effort estimated (8-12 sessions)
- [x] Low-risk items identified to start with

### Recommendation

**GO** - Proceed with the Design Patterns Sprint as a coordinated set of sub-initiatives.

**Rationale**:
- Patterns are well-documented in Architect's analysis
- Navigation Descriptor success proves the approach
- Risk is managed by sequencing from low to high
- Each initiative is independent with clear scope
- Pre-GA timing is ideal for these improvements

**Execution Order**:
1. Initiative A (Custom Field Descriptors) - Start immediately
2. Initiative B (Error Mixin) - Can parallel with A
3. Initiative C (Holder Factory) - After A completes
4. Initiative D (Async/Sync Generator) - After B completes
5. Initiative E (CRUD Metaclass) - Evaluate after D

---

## Next Steps

1. **Review and approve this Prompt -1** (meta-initiative scope)

2. **Execute Initiative A (Custom Field Descriptors)** - 1-2 sessions
   - Lowest risk, highest immediate visibility
   - Builds on Navigation Descriptor familiarity
   - See: `PROMPT-0-PATTERNS-A-CUSTOM-FIELD-DESCRIPTORS.md`

3. **Execute Initiative B (Error Mixin)** in parallel - 1 session
   - Quick win to maintain momentum

4. **Plan C and D** once A and B complete

5. **Evaluate E** after D completes

---

## Appendix: Quick Reference

| Initiative | Pattern | Lines Saved | Risk | Sessions | Depends On |
|------------|---------|-------------|------|----------|------------|
| A: Custom Field Descriptors | Descriptor | ~400 | Low | 1-2 | None |
| B: Error Classification Mixin | Mixin | ~150 | Low | 1 | None |
| C: Holder Factory | `__init_subclass__` | ~300 | Medium | 1-2 | None |
| D: Async/Sync Generator | Decorator | ~1,200 | Medium | 2-3 | None |
| E: CRUD Client Metaclass | Metaclass | ~500 | High | 2-3 | D (optional) |

---

## Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Design Pattern Analysis | `/docs/architecture/DESIGN-PATTERN-OPPORTUNITIES.md` | Primary input |
| Navigation Descriptor ADR | `/docs/decisions/ADR-0075-navigation-descriptor-pattern.md` | Proven pattern |
| Auto-Invalidation ADR | `/docs/decisions/ADR-0076-auto-invalidation-strategy.md` | Descriptor behavior |
| Pydantic Compatibility ADR | `/docs/decisions/ADR-0077-pydantic-descriptor-compatibility.md` | Critical constraint |
| Existing Descriptors | `src/autom8_asana/models/business/descriptors.py` | Reference implementation |
| Business Model (current) | `src/autom8_asana/models/business/business.py` | Target for A |

---

*This Prompt -1 validated that the Design Patterns Sprint is ready for execution as a coordinated set of sub-initiatives. Proceed to individual Prompt 0s for each initiative, starting with Initiative A: Custom Field Property Descriptors.*
