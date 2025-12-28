# Quality Gates

> Mandatory checkpoints between workflow phases

## What is a Quality Gate?

Quality gates are **mandatory checkpoints** between phases. Passing a gate requires all criteria to be met.

Quality gates prevent low-quality work from propagating downstream. **Failing a gate means routing back, not proceeding.**

---

## PRD Quality Gate

**Owner**: Requirements Analyst produces -> Orchestrator verifies

| Criterion | Validation |
|-----------|------------|
| Problem statement clear | Can be explained in one paragraph |
| Scope explicit | In-scope AND out-of-scope defined |
| Requirements testable | Each has acceptance criteria |
| Priorities assigned | MoSCoW applied |
| No blocking questions | Or owners assigned with dates |

### Detailed Template

For complete PRD structure and expanded quality checklist, see [documentation/templates/prd.md](../documentation/templates/prd.md).

---

## TDD Quality Gate

**Owner**: Architect produces -> Orchestrator verifies

| Criterion | Validation |
|-----------|------------|
| Traces to PRD | Every design element maps to requirement |
| Decisions documented | Significant choices have ADRs |
| Interfaces defined | Component boundaries clear |
| Complexity justified | Matches actual requirement |
| Risks identified | With mitigations |

### Detailed Template

For complete TDD structure and expanded quality checklist, see [documentation/templates/tdd.md](../documentation/templates/tdd.md).

---

## Implementation Quality Gate

**Owner**: Principal Engineer produces -> Orchestrator verifies

| Criterion | Validation |
|-----------|------------|
| Satisfies TDD | Implementation matches design |
| Tests exist | All paths covered including errors |
| Type-safe | Full type hints |
| Readable | Non-author can understand |
| Documented | Implementation decisions recorded |

---

## Validation Quality Gate

**Owner**: QA/Adversary produces -> Orchestrator verifies

| Criterion | Validation |
|-----------|------------|
| Acceptance criteria met | All requirements validated |
| Edge cases covered | Boundary conditions tested |
| Failures handled | Error scenarios verified |
| Production ready | Deployment requirements met |

### Detailed Template

For complete Test Plan structure and expanded quality checklist, see [documentation/templates/test-plan.md](../documentation/templates/test-plan.md).

---

## Workflow Integration

Quality gates are verified in the **VERIFY** step of each session. See [lifecycle.md](lifecycle.md) for the complete session protocol.

**Non-Negotiable Rule**: DO NOT proceed to the next phase if a quality gate has not been met. Route back to the responsible agent to resolve gaps.
