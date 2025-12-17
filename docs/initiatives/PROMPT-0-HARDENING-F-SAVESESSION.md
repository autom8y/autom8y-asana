# Orchestrator Initialization: Architecture Hardening - Initiative F (SaveSession Reliability)

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
- **`standards`** - Tech stack decisions, code conventions, repository structure
- **`10x-workflow`** - Agent coordination, session protocol, quality gates
- **`autom8-asana-domain`** - SDK patterns, SaveSession, Unit of Work pattern
- **`autom8-asana-business-workflows`** - SaveSession patterns, batch operations

**How Skills Work**: Skills load automatically based on your current task.

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

## The Mission: Add Transaction Semantics and Entity Identity to SaveSession

This initiative addresses the **two highest-risk reliability issues**: no transaction guarantees (partial failures leave inconsistent state) and Python id()-based entity identity (same task fetched twice = two tracked entities). These are critical for production reliability.

### Why This Initiative?

- **Data integrity**: Partial failures can leave Asana data in inconsistent state
- **Predictability**: Users can't reason about what happens on failure
- **Correctness**: Entity identity bugs cause silent data corruption
- **Production readiness**: No production system should have these issues
- **Trust**: SDK consumers need to trust SaveSession behavior

### Issues Addressed

| # | Issue | Description | Severity |
|---|-------|-------------|----------|
| 1 | No transaction guarantees | Partial failures leave inconsistent state, no rollback | High |
| 8 | Entity identity uses Python id() | Same task fetched twice = two tracked entities | High |

### Current State

**Transaction Semantics**:
- SaveSession commits changes one at a time (or in small batches)
- If operation 5 of 10 fails, operations 1-4 are already committed
- No rollback capability
- Partial state is committed without explicit acknowledgment
- User may not know what succeeded vs failed

**Entity Identity**:
- Entities tracked by Python `id()` (memory address)
- Same task fetched twice creates two tracked entities
- Both can be modified independently
- On commit, last-write-wins or double-update occurs
- No deduplication by GID

### Target State

```
Transaction Semantics:
  - Clear commit/rollback behavior documented
  - Partial failure clearly reported with succeeded/failed breakdown
  - Optional: atomic semantics where possible
  - Clear recovery guidance for partial failures

Entity Identity:
  - Entities tracked by GID, not Python id()
  - Same GID = same tracked entity
  - Modifications merge correctly
  - Clear behavior for entity refresh
```

### Key Constraints

- **Asana API limitation**: Asana API doesn't support true transactions
- **Backward compatibility**: Existing SaveSession usage must continue to work
- **Performance**: No significant regression in commit performance
- **Explicit semantics**: User must be able to predict behavior
- **This is highest risk**: Spike/prototype phase before full implementation

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Document transaction semantics clearly | Must |
| Report partial failures with succeeded/failed breakdown | Must |
| Implement GID-based entity identity | Must |
| Handle entity refresh/re-fetch correctly | Must |
| Provide recovery guidance for partial failures | Must |
| Consider optimistic concurrency (version checking) | Should |
| Consider batch atomicity where Asana supports | Should |
| Maintain backward compatibility | Must |

### Success Criteria

1. SaveSession documents exact behavior on partial failure
2. Partial failure exception includes succeeded + failed entity lists
3. Entities tracked by GID, not Python id()
4. Same entity fetched twice = single tracked instance
5. Entity refresh merges with tracked instance correctly
6. Recovery documentation for partial failure scenarios
7. No silent data corruption on identity collision
8. Backward compatible with existing SaveSession usage

### Dependencies

**Depends On:**
- Initiative A (Foundation) - For exception hierarchy
- Initiative B (Custom Fields) - For unified change tracking
- Initiative C (Navigation) - For stable reference patterns
- Initiative D (Resolution) - Optional, nice to have
- Initiative E (Hydration) - Optional, nice to have

**Blocks:**
- None (final initiative)

**Requires:**
- **Spike phase** before full implementation due to high risk

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **0: Spike** | Principal Engineer | Transaction semantics prototype, GID identity POC |
| **1: Discovery** | Requirements Analyst | Current behavior documentation, failure mode catalog |
| **2: Requirements** | Requirements Analyst | PRD-HARDENING-F with acceptance criteria |
| **3: Architecture** | Architect | TDD-HARDENING-F + ADRs for transaction semantics, identity |
| **4: Implementation P1** | Principal Engineer | GID-based identity, entity registry |
| **5: Implementation P2** | Principal Engineer | Partial failure handling, recovery support |
| **6: Validation** | QA/Adversary | Failure mode testing, identity collision testing |

---

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Spike Phase: Required Before Discovery

**IMPORTANT**: Due to the high risk and complexity of transaction semantics, a **spike session** is required before formal discovery.

### Spike Goals

1. **Prototype GID-based identity**: Can we replace id() tracking with GID?
2. **Test Asana batch behavior**: What happens on partial batch failure?
3. **Validate recovery approach**: Can we provide meaningful recovery info?
4. **Identify showstoppers**: Any fundamental blockers to the approach?

### Spike Deliverables

- POC code for GID-based entity registry
- Documentation of Asana API batch failure behavior
- Recommended approach with confidence level
- List of risks and mitigations

### Spike Trigger Prompt

```markdown
Begin Session 0: SaveSession Reliability Spike

Work with the @principal-engineer agent on a timeboxed spike.

**Timebox**: 1 session (do not exceed)

**Goals:**
1. Prototype GID-based entity tracking
2. Test Asana API batch failure behavior
3. Document findings and recommendation

**Spike Tasks:**
1. Create minimal entity registry keyed by GID
2. Test: what happens when batch partially fails?
3. Test: can we get succeeded/failed breakdown?
4. Document: what's feasible vs aspirational?

**Deliverable:**
Spike report with:
- GID registry POC code (prototype quality)
- Asana batch failure behavior documentation
- Recommended approach
- Risk assessment
- Go/No-Go for full implementation

This is a SPIKE - prototype quality, not production code.
```

---

## Discovery Phase: What Must Be Explored

**After spike validates feasibility**, the Requirements Analyst must explore:

### Current Behavior Analysis

| Area | Questions to Answer |
|------|---------------------|
| Commit flow | What happens step by step during commit? |
| Failure handling | What happens when an operation fails mid-commit? |
| State after failure | What's the state of tracked entities after failure? |
| User visibility | How does user know what succeeded/failed? |

### Entity Identity Analysis

| Scenario | Questions to Answer |
|----------|---------------------|
| Double fetch | What happens if same task fetched twice? |
| Identity check | How are entities compared for equality? |
| Tracking behavior | Does tracker dedupe by any means? |
| Refresh behavior | What happens on entity refresh? |

### Failure Mode Catalog

| Failure Mode | Questions to Answer |
|--------------|---------------------|
| Network failure mid-batch | What state is left? |
| Single item failure in batch | What's reported? What continues? |
| Rate limit mid-commit | How is this handled? |
| Concurrent modification | What if entity modified externally? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins:

### Transaction Semantics Questions

1. **Semantics model**: "Best effort" vs "all-or-nothing" vs "explicit partial commit"?
2. **Rollback capability**: Is rollback possible? Desirable? How far?
3. **Failure recovery**: What guidance for users on partial failure?
4. **Optimistic locking**: Should we check entity versions before commit?

### Identity Questions

5. **Registry scope**: Global registry? Per-SaveSession? Per-client?
6. **Identity key**: GID only? GID + type? Composite key?
7. **Refresh merge**: How to merge refresh with pending changes?
8. **Weak references**: Use weak refs to allow GC?

### API Questions

9. **Exception design**: What info in partial failure exception?
10. **Recovery API**: Any explicit recovery methods?
11. **Retry support**: Built-in retry for transient failures?
12. **Checkpoint support**: Can user checkpoint mid-commit?

---

## Your First Task

Confirm understanding by:

1. Summarizing the SaveSession Reliability goal in 2-3 sentences
2. Listing the 7 sessions (including spike) and their deliverables
3. Acknowledging the **spike phase is mandatory** before discovery
4. Confirming this initiative depends on A, B, C (and optionally D, E)
5. Listing which open questions you need answered before Session 2
6. Acknowledging this is the highest-risk initiative

**Do NOT begin Session 0 (Spike) yet. Wait for my confirmation.**

---

## Session Trigger Prompts

### Session 0: Spike (MANDATORY)

```markdown
Begin Session 0: SaveSession Reliability Spike

Work with the @principal-engineer agent on a timeboxed spike.

**Timebox**: 1 session (do not exceed)

**Goals:**
1. Prototype GID-based entity tracking
2. Test Asana API batch failure behavior
3. Document findings and recommendation

**Spike Tasks:**
1. Create minimal entity registry keyed by GID
2. Test: what happens when batch partially fails?
3. Test: can we get succeeded/failed breakdown?
4. Document: what's feasible vs aspirational?

**Deliverable:**
Spike report with:
- GID registry POC code (prototype quality)
- Asana batch failure behavior documentation
- Recommended approach
- Risk assessment
- Go/No-Go for full implementation

This is a SPIKE - prototype quality, not production code.
```

### Session 1: Discovery

```markdown
Begin Session 1: SaveSession Reliability Discovery

Work with the @requirements-analyst agent to document current behavior and failure modes.

**Prerequisites:**
- Spike complete with GO recommendation

**Goals:**
1. Document current commit flow in detail
2. Catalog all failure modes
3. Document current entity identity behavior
4. Map user visibility gaps

**Files to Analyze:**
- `src/autom8_asana/persistence/session.py` - SaveSession
- `src/autom8_asana/persistence/tracker.py` - Entity tracker
- Related test files for current behavior

**Deliverable:**
A discovery document with:
- Commit flow sequence diagram
- Failure mode catalog
- Identity behavior documentation
- User visibility gap analysis
- Spike findings integration

Create the analysis plan first. I'll review before you execute.
```

### Session 2: Requirements

```markdown
Begin Session 2: SaveSession Reliability Requirements

Work with the @requirements-analyst agent to create PRD-HARDENING-F.

**Prerequisites:**
- Session 1 discovery document complete
- Spike findings available

**Goals:**
1. Define transaction semantics requirements
2. Define entity identity requirements
3. Define partial failure reporting requirements
4. Define recovery guidance requirements
5. Define acceptance criteria for each

**Key Questions to Address:**
- What transaction semantics model?
- What entity identity key?
- What partial failure information?
- What recovery guidance?

Create the plan first. I'll review before you execute.
```

### Session 3: Architecture

```markdown
Begin Session 3: SaveSession Reliability Architecture

Work with the @architect agent to create TDD-HARDENING-F and required ADRs.

**Prerequisites:**
- PRD-HARDENING-F approved
- Spike POC available for reference

**Goals:**
1. Design GID-based entity registry
2. Design partial failure handling
3. Design recovery mechanisms
4. Refine spike POC into production design

**Required ADRs:**
- ADR: GID-Based Entity Identity
- ADR: SaveSession Transaction Semantics
- ADR: Partial Failure Recovery Strategy

Create the plan first. I'll review before you execute.
```

### Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - GID Identity

Work with the @principal-engineer agent to implement GID-based identity.

**Prerequisites:**
- PRD-HARDENING-F approved
- TDD-HARDENING-F approved
- ADRs documented

**Phase 1 Scope:**
1. Implement GID-based entity registry
2. Replace id()-based tracking with GID-based
3. Handle entity refresh/merge
4. Unit tests for identity behavior

**Explicitly OUT of Phase 1:**
- Partial failure handling (Phase 2)
- Recovery support (Phase 2)

Create the plan first. I'll review before you execute.
```

### Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Partial Failure

Work with the @principal-engineer agent to implement partial failure handling.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Implement partial failure exception
2. Implement succeeded/failed breakdown
3. Add recovery guidance
4. Integration tests
5. Document transaction semantics

Create the plan first. I'll review before you execute.
```

### Session 6: Validation

```markdown
Begin Session 6: SaveSession Reliability Validation

Work with the @qa-adversary agent to validate reliability improvements.

**Prerequisites:**
- All implementation complete

**Goals:**

**Part 1: Identity Validation**
- Test same entity fetched twice = single tracked
- Test entity refresh merges correctly
- Test no double-updates on commit

**Part 2: Failure Mode Testing**
- Test every cataloged failure mode
- Verify succeeded/failed breakdown accurate
- Verify no silent data corruption

**Part 3: Recovery Testing**
- Test recovery guidance accuracy
- Test partial commit recovery
- Test retry scenarios

**Part 4: Backward Compatibility**
- Verify existing SaveSession patterns work
- Verify no regressions

Create the plan first. I'll review before you execute.
```

---

## Context Gathering Checklist

Before starting, gather:

**Codebase:**
- [ ] `src/autom8_asana/persistence/session.py` - SaveSession
- [ ] `src/autom8_asana/persistence/tracker.py` - Entity tracker
- [ ] `src/autom8_asana/persistence/exceptions.py` - Current exceptions
- [ ] Batch API implementation
- [ ] Related test files

**Documentation:**
- [ ] TDD-0010 (Save Orchestration)
- [ ] ADR-0035 (Unit of Work Pattern)
- [ ] ADR-0040 (Partial Failure Handling)
- [ ] SaveSession skill documentation

**Spike Output:**
- [ ] GID registry POC code
- [ ] Asana batch failure behavior docs
- [ ] Spike recommendation

---

## Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Meta Prompt -1 | `/docs/initiatives/PROMPT-MINUS-1-ARCHITECTURE-HARDENING.md` | Parent initiative |
| TDD-0010 | `/docs/design/TDD-0010-save-orchestration.md` | Current design |
| ADR-0035 | `/docs/decisions/ADR-0035-unit-of-work-pattern.md` | UoW pattern |
| ADR-0040 | `/docs/decisions/ADR-0040-partial-failure-handling.md` | Current failure handling |
| SaveSession Skill | `.claude/skills/autom8-asana-business-workflows/composite-savesession.md` | SaveSession patterns |
| Initiative B | `/docs/initiatives/PROMPT-0-HARDENING-B-CUSTOM-FIELDS.md` | Dependency (unified tracking) |

---

## Risk Acknowledgment

This initiative has **HIGH RISK** due to:

1. **Fundamental behavior change**: Transaction semantics affect all SaveSession users
2. **Data integrity implications**: Bugs here can cause data corruption
3. **Asana API constraints**: We cannot achieve true ACID transactions
4. **Backward compatibility tension**: Some behavior changes may be breaking
5. **Complex failure modes**: Distributed partial failures are inherently complex

**Mitigations**:
- Mandatory spike phase before commitment
- Extensive failure mode testing
- Clear documentation of semantics
- Backward compatibility layer where possible
- Gradual rollout with feature flags (if needed)

---

*This is Initiative F of the Architecture Hardening Sprint. It is the FINAL initiative and depends on all others. Spike phase is MANDATORY before proceeding.*
