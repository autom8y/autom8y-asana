# Workflow Phase Transitions

## Metadata
- **Document Type**: Reference
- **Status**: Active
- **Created**: 2025-12-24
- **Last Updated**: 2025-12-24
- **Purpose**: Canonical reference for development workflow phases and quality gates

## Overview

The autom8_asana project follows a structured 5-phase development workflow: **Requirements → Design → Implementation → Validation → Deployment**. Each phase has defined entry criteria, exit criteria (quality gates), responsible agents, and handoff artifacts.

This document serves as the single source of truth for workflow phases and their transitions.

## The Five Phases

### Phase 1: Requirements

**Agent**: @requirements-analyst

**Artifact**: PRD-NNNN

**Purpose**: Define WHAT to build and WHY.

**Entry Criteria**:
- User request or initiative scope defined
- Business value articulated
- Stakeholders identified

**Activities**:
- Clarify user intent
- Define acceptance criteria
- Identify success metrics
- Document edge cases
- List dependencies and constraints

**Exit Criteria (Quality Gate)**:
- [ ] Clear, testable acceptance criteria
- [ ] Success metrics defined
- [ ] Edge cases identified
- [ ] Dependencies documented
- [ ] Non-functional requirements stated
- [ ] Stakeholder approval obtained

**Handoff to**: Phase 2 (Design)

**References**:
- [documentation/templates/prd.md](../../.claude/skills/documentation/templates/prd.md)

---

### Phase 2: Design

**Agent**: @architect

**Artifacts**: TDD-NNNN, ADR-NNNN+

**Purpose**: Define HOW to build it.

**Entry Criteria**:
- Approved PRD from Phase 1

**Activities**:
- Design system architecture
- Define component boundaries
- Specify API contracts
- Create data models
- Make architectural decisions (ADRs)
- Address non-functional requirements
- Plan migration strategy (if applicable)

**Exit Criteria (Quality Gate)**:
- [ ] Component boundaries defined
- [ ] API contracts specified
- [ ] Data flow documented
- [ ] Non-functional requirements addressed
- [ ] Architectural decisions recorded (ADRs)
- [ ] Design reviewed and approved
- [ ] No unresolved design questions

**Handoff to**: Phase 3 (Implementation)

**References**:
- [documentation/templates/tdd.md](../../.claude/skills/documentation/templates/tdd.md)
- [documentation/templates/adr.md](../../.claude/skills/documentation/templates/adr.md)

---

### Phase 3: Implementation

**Agent**: @principal-engineer

**Artifacts**: Code, tests, migration scripts

**Purpose**: Build the system according to design.

**Entry Criteria**:
- Approved TDD from Phase 2
- ADRs documenting key decisions

**Activities**:
- Implement code following TDD specifications
- Write unit tests (target ≥80% coverage)
- Write integration tests
- Implement migration scripts (if needed)
- Update documentation
- Follow code conventions

**Exit Criteria (Quality Gate)**:
- [ ] All tests passing
- [ ] Type checking passing (mypy)
- [ ] Linting passing (ruff)
- [ ] Code coverage ≥ target (typically 80%)
- [ ] Code follows conventions (see [standards/code-conventions.md](../../.claude/skills/standards/code-conventions.md))
- [ ] API contracts match TDD specification
- [ ] Migration scripts tested (if applicable)

**Handoff to**: Phase 4 (Validation)

**References**:
- [standards/code-conventions.md](../../.claude/skills/standards/code-conventions.md)
- [standards/testing-standards.md](../../.claude/skills/standards/testing-standards.md)

---

### Phase 4: Validation

**Agent**: @qa-adversary

**Artifacts**: Test Plan, Validation Report

**Purpose**: Verify the system meets requirements.

**Entry Criteria**:
- Implemented code from Phase 3
- All Phase 3 quality gates passed

**Activities**:
- Create comprehensive test plan
- Execute test plan
- Validate edge cases
- Perform integration testing
- Check performance (if applicable)
- Verify documentation accuracy
- Test error handling
- Find bugs and edge cases

**Exit Criteria (Quality Gate)**:
- [ ] Test plan executed
- [ ] All edge cases validated
- [ ] Performance acceptable (if NFR specified)
- [ ] Documentation updated and accurate
- [ ] No critical bugs
- [ ] Acceptance criteria from PRD met
- [ ] Validation report approved

**Handoff to**: Phase 5 (Deployment)

**References**:
- [documentation/templates/test-plan.md](../../.claude/skills/documentation/templates/test-plan.md)

---

### Phase 5: Deployment

**Agent**: @principal-engineer or @sre-team

**Artifacts**: Deployment log, runbook updates

**Purpose**: Release to production.

**Entry Criteria**:
- Validated code from Phase 4
- All quality gates passed

**Activities**:
- Create pull request
- Code review
- Merge to main branch
- Deploy to production (if applicable)
- Update runbooks
- Monitor initial rollout
- Verify deployment success

**Exit Criteria (Quality Gate)**:
- [ ] Pull request approved and merged
- [ ] Deployment successful
- [ ] Monitoring in place
- [ ] Rollback plan tested
- [ ] Documentation updated
- [ ] Stakeholders notified

**Handoff to**: (Complete)

---

## Phase Transition Diagram

```
┌──────────────┐
│ User Request │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Phase 1:         │  Exit: PRD approved
│ Requirements     │  ────────────────────┐
│ (@req-analyst)   │                      │
└──────────────────┘                      │
                                          ▼
                                ┌──────────────────┐
                                │ Phase 2:         │  Exit: TDD approved
                                │ Design           │  ────────────────────┐
                                │ (@architect)     │                      │
                                └──────────────────┘                      │
                                                                          ▼
                                                                ┌──────────────────┐
                                                                │ Phase 3:         │
                                                                │ Implementation   │
                                                                │ (@principal-eng) │
                                                                └─────┬────────────┘
                                                                      │
                                                    Exit: Tests pass  │
                                                                      ▼
                                                                ┌──────────────────┐
                                                                │ Phase 4:         │
                                                                │ Validation       │
                                                                │ (@qa-adversary)  │
                                                                └─────┬────────────┘
                                                                      │
                                                Exit: Validation pass │
                                                                      ▼
                                                                ┌──────────────────┐
                                                                │ Phase 5:         │
                                                                │ Deployment       │
                                                                │ (@principal-eng) │
                                                                └─────┬────────────┘
                                                                      │
                                                         Exit: Deployed
                                                                      ▼
                                                                ┌──────────┐
                                                                │ Complete │
                                                                └──────────┘

        Iteration Loops:
        ────────────────────
        Validation → Implementation (design flaws found)
        Design → Requirements (missing requirements discovered)
        Implementation → Design (technical blockers require redesign)
```

---

## Fast-Track Scenarios

### Hotfix Workflow (Bypass Design)

**Use When**: Critical production bug requiring immediate fix.

**Phases**: Requirements → Implementation → Validation → Deployment

**Skipped**: Phase 2 (Design) - Minimal design in PRD

**Command**: `/hotfix`

**Example**:
```
User Request: "Fix cache corruption bug in production"
  ↓
Phase 1: PRD-HOTFIX-cache-corruption (minimal, documents fix)
  ↓
Phase 3: Implement fix, add regression test
  ↓
Phase 4: Validate fix doesn't break anything
  ↓
Phase 5: Deploy immediately
```

**Quality Gate Adjustments**:
- PRD can be minimal (problem statement + fix approach)
- TDD may be created retrospectively (optional)
- Test focus: regression + fix validation

---

### Spike Workflow (Investigation Only)

**Use When**: Technical unknowns require investigation.

**Phases**: Requirements → Investigation → Report

**Skipped**: Phases 3-5 (no implementation)

**Command**: `/spike`

**Example**:
```
User Request: "Investigate caching strategies for batch operations"
  ↓
Phase 1: PRD-SPIKE-caching-strategies (questions to answer)
  ↓
Investigation: Research, prototyping, analysis
  ↓
Report: Findings, recommendations, proposed approach
```

**Deliverable**: Spike report (can inform future PRD/TDD)

---

## Iteration Patterns

### Design Iteration (Phase 3 → Phase 2)

**Trigger**: Implementation reveals design is infeasible or flawed.

**Process**:
1. @principal-engineer identifies design issue
2. Document issue and proposed alternative
3. Route to @architect for TDD update
4. @architect revises TDD
5. Return to Phase 3 with updated design

**Example**: "Dependency graph algorithm needs revision due to circular dependency edge case."

---

### Requirements Iteration (Phase 4 → Phase 1)

**Trigger**: Validation reveals missing or incorrect requirements.

**Process**:
1. @qa-adversary identifies requirements gap
2. Document gap in validation report
3. Route to @requirements-analyst for PRD update
4. @requirements-analyst revises PRD
5. Restart from Phase 2 (may need design changes)

**Example**: "Edge case for multi-homed tasks not covered in original PRD."

---

## Quality Gates Reference

### Requirements Quality Gate (Phase 1 → 2)

**Must Pass**:
- Clear acceptance criteria (testable, specific)
- Success metrics defined (quantifiable)
- Edge cases identified
- Dependencies documented
- Non-functional requirements stated

**Review Checklist**:
- [ ] Can acceptance criteria be turned into test cases?
- [ ] Are success metrics measurable?
- [ ] Are edge cases comprehensive?
- [ ] Are all dependencies identified?

---

### Design Quality Gate (Phase 2 → 3)

**Must Pass**:
- Component boundaries defined
- API contracts specified
- Data flow documented
- Non-functional requirements addressed
- Architectural decisions recorded

**Review Checklist**:
- [ ] Are component responsibilities clear?
- [ ] Are API contracts complete (inputs, outputs, errors)?
- [ ] Is data flow end-to-end documented?
- [ ] Are performance, security, scalability addressed?
- [ ] Are all architectural decisions captured in ADRs?

---

### Implementation Quality Gate (Phase 3 → 4)

**Must Pass**:
- All tests passing
- Type checking passing
- Linting passing
- Coverage ≥ target
- Code follows conventions

**Automated Checks**:
```bash
pytest                    # All tests pass
mypy src/autom8_asana     # Type checking pass
ruff check src/           # Linting pass
pytest --cov              # Coverage ≥ 80%
```

---

### Validation Quality Gate (Phase 4 → 5)

**Must Pass**:
- Test plan executed
- Edge cases validated
- Performance acceptable
- Documentation accurate
- Acceptance criteria met

**Review Checklist**:
- [ ] All test plan items executed?
- [ ] Edge cases from PRD validated?
- [ ] Performance meets NFRs?
- [ ] Documentation updated?
- [ ] All PRD acceptance criteria satisfied?

---

## See Also

- [REF-command-decision-tree.md](./REF-command-decision-tree.md) - Which command to use for which scenario
- [10x-workflow/lifecycle.md](../../.claude/skills/10x-workflow/lifecycle.md) - Detailed lifecycle documentation
- [10x-workflow/quality-gates.md](../../.claude/skills/10x-workflow/quality-gates.md) - Quality gate details
