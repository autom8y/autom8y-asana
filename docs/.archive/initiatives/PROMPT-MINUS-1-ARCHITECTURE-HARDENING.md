# Prompt -1: Architecture Hardening Sprint (Meta-Initiative)

> **Purpose**: Define the overarching "session of sessions" that will orchestrate multiple sub-initiatives to address critical SDK architecture issues identified during the deep analysis phase.

---

## Initiative Summary

**One-liner**: Systematically address 14 architectural issues across the autom8_asana SDK through a coordinated multi-initiative sprint.

**Sponsor**: SDK Team / Architecture Review

**Triggered by**: Architect's deep analysis revealing critical gaps in transaction semantics, change tracking coherence, hydration performance, and developer experience consistency.

---

## Meta-Initiative Context

This is a **meta-initiative** that coordinates multiple sub-initiatives. Unlike a typical Prompt -1 which leads to a single Prompt 0, this document:

1. **Contextualizes** the full scope of architectural work needed
2. **Segments** 14 issues into 6 logical, cohesive initiatives
3. **Sequences** initiatives by dependency and risk
4. **Identifies** cross-initiative concerns and dependencies
5. **Establishes** success criteria for the overall hardening effort

Each sub-initiative has its own Prompt 0 and can be executed in a separate Claude Code session.

---

## Pre-Flight Checklist

### 1. Problem Validation

| Question | Answer | Confidence |
|----------|--------|------------|
| Is there a real problem? | Yes - Architect's analysis identified 14 issues across severity levels | High |
| Who experiences it? | SDK consumers, maintainers, and the SDK itself (reliability) | High |
| What's the cost of not solving? | Cascading bugs, confused developers, unreliable batch operations, poor performance | High |
| Is this the right time? | Yes - SDK is pre-GA, changes now avoid breaking consumers later | High |

**Problem Statement Draft**:
> The autom8_asana SDK has accumulated architectural debt including inconsistent change tracking, missing transaction guarantees, O(n) hydration performance, and DX inconsistencies. Addressing these before GA ensures a stable, performant, and developer-friendly API surface.

### 2. Issues Inventory

The architect identified 14 issues across three severity tiers:

#### High Severity (Must Address)

| # | Issue | Description | Risk |
|---|-------|-------------|------|
| 1 | No transaction guarantees in SaveSession | Partial failures leave inconsistent state, no rollback | Data integrity |
| 2 | Dual custom field change tracking | Two parallel systems, confusing and error-prone | Correctness |
| 3 | O(n) hydration with no parallelism | 60+ API calls for typical hierarchy, no batching | Performance |

#### Medium Severity

| # | Issue | Description | Risk |
|---|-------|-------------|------|
| 4 | Manual reference invalidation | `_invalidate_refs()` must be called explicitly | Stale data |
| 5 | Resolution coupled to AssetEdit | 600+ lines, can't reuse for other entity types | Maintainability |
| 6 | Copy-paste navigation logic | Each entity duplicates property patterns | Code duplication |
| 7 | Inconsistent holder initialization | `HOLDER_KEY_MAP` + `__getattr__` magic | Confusion |
| 8 | Entity identity uses Python id() | Same task fetched twice = two tracked entities | Correctness |
| 9 | Exception hierarchy inconsistent | Different attribute patterns across exceptions | DX |
| 10 | Naming inconsistencies | `get_custom_fields()` sounds like fetch | DX |

#### Low Severity / Quick Wins

| # | Issue | Description | Risk |
|---|-------|-------------|------|
| 11 | Private functions in `__all__` | API hygiene | Minor DX |
| 12 | Stub holders incomplete | May cause runtime errors | Stability |
| 13 | Logging is minimal | Most modules don't use logging | Debuggability |
| 14 | No observability hooks | No telemetry | Operations |

### 3. Initiative Segmentation

Issues are grouped into 6 logical initiatives based on:
- **Cohesion**: Related issues that should be solved together
- **Dependencies**: Prerequisites that must complete first
- **Risk**: Higher-risk changes are sequenced later
- **Parallelism**: Independent initiatives can run concurrently

#### Initiative A: Foundation & API Hygiene
**Issues**: 9, 10, 11, 12, 13, 14
**Risk**: Low
**Value**: Medium (enables clean base for subsequent work)

| Issue | Description |
|-------|-------------|
| 9 | Exception hierarchy standardization |
| 10 | Naming consistency audit and fixes |
| 11 | Remove private functions from `__all__` |
| 12 | Complete stub holder implementations |
| 13 | Add structured logging throughout |
| 14 | Add observability hooks (telemetry-ready) |

#### Initiative B: Custom Field Unification
**Issues**: 2, 10 (partial)
**Risk**: Medium
**Value**: High (correctness)
**Depends on**: A (for logging during debugging)

| Issue | Description |
|-------|-------------|
| 2 | Unify dual change tracking systems |
| 10 | Fix `get_custom_fields()` naming confusion |

#### Initiative C: Navigation & Relationship Patterns
**Issues**: 4, 6, 7
**Risk**: Medium
**Value**: Medium (maintainability, correctness)
**Depends on**: A (for logging/exceptions)

| Issue | Description |
|-------|-------------|
| 4 | Auto-invalidation of stale references |
| 6 | Navigation descriptor pattern (DRY) |
| 7 | Unified holder initialization |

#### Initiative D: Resolution Framework Extraction
**Issues**: 5
**Risk**: Medium
**Value**: Medium (reusability)
**Depends on**: C (navigation patterns stabilized)

| Issue | Description |
|-------|-------------|
| 5 | Extract resolution from AssetEdit into reusable framework |

#### Initiative E: Hydration Performance
**Issues**: 3
**Risk**: Medium
**Value**: High (performance)
**Can run parallel with**: B
**Depends on**: A (for telemetry/logging)

| Issue | Description |
|-------|-------------|
| 3 | Parallel hydration with batching |

#### Initiative F: SaveSession Reliability
**Issues**: 1, 8
**Risk**: High
**Value**: Critical (data integrity)
**Depends on**: All other initiatives (builds on stable foundation)

| Issue | Description |
|-------|-------------|
| 1 | Transaction semantics and partial failure recovery |
| 8 | GID-based entity identity |

### 4. Dependency Graph

```
                    +------------------+
                    |   A: Foundation  |
                    |  (Low Risk)      |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
    +---------+----+  +------+------+  +---+----------+
    | B: Custom    |  | C: Nav      |  | E: Hydration |
    | Fields       |  | Patterns    |  | Performance  |
    | (Medium)     |  | (Medium)    |  | (Medium)     |
    +-------+------+  +------+------+  +------+-------+
            |                |                |
            |                v                |
            |        +-------+-------+        |
            |        | D: Resolution |        |
            |        | Framework     |        |
            |        | (Medium)      |        |
            |        +-------+-------+        |
            |                |                |
            +-------+--------+--------+-------+
                    |
                    v
           +--------+---------+
           | F: SaveSession   |
           | Reliability      |
           | (High Risk)      |
           +------------------+
```

### 5. Execution Strategy

#### Phase 1: Foundation (1 session)
- Execute Initiative A
- Establishes clean logging, exceptions, API surface

#### Phase 2: Core Improvements (2-3 sessions, parallel)
- Execute Initiative B (Custom Fields) - 2 sessions
- Execute Initiative E (Hydration) - 2 sessions
- These can run in parallel if different engineers/contexts

#### Phase 3: Patterns & Extraction (2 sessions, sequential)
- Execute Initiative C (Navigation) - 1-2 sessions
- Execute Initiative D (Resolution) - 1 session
- C must complete before D

#### Phase 4: Reliability (2-3 sessions)
- Execute Initiative F (SaveSession)
- Highest risk, requires stable foundation
- May need spike/prototype first

**Total estimated sessions**: 8-12 across all initiatives

### 6. Cross-Initiative Dependencies

| Dependency | From | To | Type |
|------------|------|-----|------|
| Structured logging | A | All | Enables debugging |
| Exception hierarchy | A | B, C, F | Consistent error handling |
| Observability hooks | A | E, F | Performance measurement |
| Navigation patterns | C | D | Foundation for extraction |
| Change tracking | B | F | Prerequisite for transaction semantics |
| Entity identity | F-partial | B | May affect tracking model |

### 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking changes to public API | Medium | High | Deprecation warnings, migration guides |
| Regression in existing functionality | Medium | High | Comprehensive test coverage before changes |
| Scope creep across initiatives | Medium | Medium | Strict scope boundaries in each Prompt 0 |
| Inter-initiative conflicts | Low | Medium | Clear dependency sequencing |
| F (SaveSession) complexity underestimated | High | High | Spike/prototype before full implementation |

---

## Success Criteria (Meta-Initiative)

### Per-Initiative Success
Each sub-initiative defines its own success criteria in its Prompt 0. The meta-initiative succeeds when:

1. **All high-severity issues (1, 2, 3) are resolved**
2. **All medium-severity issues have either been resolved or explicitly deferred with rationale**
3. **No regressions in existing functionality** (test suite passes)
4. **API changes are documented** with migration guidance where needed
5. **Each initiative's PRD acceptance criteria are met**

### Measurable Outcomes

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Change tracking systems | 2 (parallel) | 1 (unified) | Code inspection |
| Hydration API calls (typical hierarchy) | 60+ sequential | <20 batched | Instrumentation |
| SaveSession partial failure handling | None | Atomic or explicit partial | Test coverage |
| Private functions in `__all__` | Present | Zero | Static analysis |
| Modules with logging | ~10% | >80% | Code inspection |
| Exception attribute consistency | Inconsistent | Standardized | Type checking |

---

## Open Questions (Meta-Level)

### Must Answer Before Starting

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Can initiatives B and E run truly in parallel? | Yes (different areas) / No (shared concerns) | Yes - minimal overlap |
| 2 | Should Initiative F include a spike phase? | Yes (de-risk) / No (proceed directly) | Yes - transaction semantics are complex |
| 3 | What's the deprecation timeline for breaking changes? | Immediate / 1 release / 2 releases | 1 release with warnings |

### Should Answer (Informing)

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 4 | Should observability hooks (A) be opt-in or opt-out? | Opt-in / Opt-out / Configurable | Configurable with opt-out default |
| 5 | What level of backward compatibility for custom field API? | Full / Breaking with migration | Breaking with clear migration path |

---

## Go/No-Go Decision

### Criteria for "Go"

- [x] Problems are validated and documented (architect's analysis)
- [x] Scope is bounded into manageable initiatives
- [x] Dependencies are mapped
- [x] Risk levels are assessed
- [x] Success metrics are measurable
- [x] Rough effort estimated (8-12 sessions)
- [ ] High-risk items have spike plans (pending for F)

### Recommendation

**CONDITIONAL GO** - Proceed with Initiatives A through E. Initiative F should begin with a spike/prototype phase before full implementation.

**Rationale**:
- Issues are well-documented and segmented
- Dependencies are clear
- Foundation work (A) is low-risk and enables all subsequent work
- SaveSession reliability (F) needs careful prototyping due to transaction complexity

**Conditions**:
1. Initiative F begins with a 1-session spike to validate transaction semantics approach
2. Each initiative's Prompt 0 is reviewed before execution begins
3. Test coverage baseline established before any changes

---

## Next Steps

1. **Review and approve this Prompt -1** (meta-initiative scope)
2. **Execute Initiative A (Foundation)** - Low risk, enables all others
3. **Plan parallel execution of B and E** if resources allow
4. **Sequence C -> D** once A completes
5. **Spike F** once B completes (needs unified change tracking)
6. **Execute F** after spike validates approach

---

## Appendix: Initiative Quick Reference

| Initiative | Issues | Risk | Depends On | Sessions |
|------------|--------|------|------------|----------|
| A: Foundation | 9, 10, 11, 12, 13, 14 | Low | None | 1 |
| B: Custom Fields | 2 | Medium | A | 2 |
| C: Navigation | 4, 6, 7 | Medium | A | 1-2 |
| D: Resolution | 5 | Medium | C | 1 |
| E: Hydration | 3 | Medium | A | 2 |
| F: SaveSession | 1, 8 | High | B, C, D, E | 2-3 (+spike) |

---

## Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Architect's Deep Analysis | (source of this triage) | Primary input |
| SaveSession TDD | `/docs/design/TDD-0010-save-orchestration.md` | Context for Issue 1 |
| Custom Field ADRs | `/docs/decisions/ADR-006*` | Context for Issue 2 |
| Hydration TDD | `/docs/design/TDD-HYDRATION.md` | Context for Issue 3 |
| SDK GA Readiness PRD | `/docs/requirements/PRD-0009-sdk-ga-readiness.md` | Overall quality goals |

---

*This Prompt -1 validated that the Architecture Hardening Sprint is ready for execution as a coordinated set of sub-initiatives. Proceed to individual Prompt 0s for each initiative.*
