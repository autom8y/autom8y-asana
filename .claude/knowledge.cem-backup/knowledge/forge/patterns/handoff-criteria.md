# Handoff Criteria Pattern

> Defining clear, verifiable conditions for passing work downstream

## Purpose

This pattern ensures:
- Work doesn't pass prematurely (incomplete)
- Work doesn't stall (overly strict criteria)
- Downstream agents receive what they need
- Quality gates are explicit and testable

## Pattern Structure

### 1. Section Header

```markdown
## Handoff Criteria

Ready for {Next Agent/Phase} when:
```

### 2. Checklist Items

Each criterion should be:
- **Specific**: Not vague or subjective
- **Verifiable**: Can be checked yes/no
- **Complete**: Covers all handoff requirements

```markdown
- [ ] {Specific, verifiable criterion}
```

### 3. Criterion Categories

Cover these areas:

**Artifact Completeness**:
```markdown
- [ ] {Primary artifact} exists and has all required sections
- [ ] {Secondary artifacts} are complete
```

**Quality Checks**:
```markdown
- [ ] {Quality criterion} has been verified
- [ ] No blocking issues remain
```

**Context Readiness**:
```markdown
- [ ] {Information next agent needs} is documented
- [ ] Open questions are resolved
```

## Example: Requirements Analyst → Architect

```markdown
## Handoff Criteria

Ready for Architect when:
- [ ] PRD exists with all required sections
- [ ] Problem statement is clear and validated
- [ ] Success criteria are measurable
- [ ] Scope boundaries are explicit (in-scope AND out-of-scope)
- [ ] Edge cases are documented
- [ ] Stakeholder sign-off obtained (if required)
- [ ] No open questions that would affect design decisions
```

## Example: Architect → Principal Engineer

```markdown
## Handoff Criteria

Ready for Principal Engineer when:
- [ ] TDD exists with all required sections
- [ ] ADRs document all significant decisions
- [ ] Component interfaces are specified
- [ ] Data models are defined
- [ ] Technology selections are documented with rationale
- [ ] Implementation scope is well-defined
- [ ] No blocking technical questions remain
```

## Example: Principal Engineer → QA Adversary

```markdown
## Handoff Criteria

Ready for QA Adversary when:
- [ ] Implementation is complete per TDD specifications
- [ ] Unit tests exist and pass
- [ ] Code is committed and reviewable
- [ ] Implementation decisions are documented
- [ ] Known edge cases are handled
- [ ] No incomplete features or TODOs blocking validation
```

## Granularity Guidelines

### Too Vague
```markdown
- [ ] PRD is good  # What does "good" mean?
- [ ] Design is complete  # Complete how?
```

### Too Granular
```markdown
- [ ] Line 42 of PRD has correct formatting  # Micromanaging
- [ ] Exactly 5 acceptance criteria  # Arbitrary
```

### Just Right
```markdown
- [ ] PRD has problem statement, success criteria, and scope
- [ ] Each acceptance criterion is testable
```

## Anti-Patterns

- **Subjective Criteria**: "Code is clean" - not verifiable
- **Missing Artifacts**: Not checking that required docs exist
- **Blocking Trivia**: Minor issues blocking handoff
- **No Exit Condition**: Criteria that can never be fully satisfied
- **Implicit Expectations**: Assuming next agent knows what they need

## Checklist for Handoff Criteria

- [ ] 5-8 criteria listed (not too few, not too many)
- [ ] Each criterion is verifiable (yes/no answer)
- [ ] Artifact completeness is covered
- [ ] Quality requirements are explicit
- [ ] Context for next agent is included
- [ ] No subjective language ("good", "complete", "ready")
- [ ] Criteria are achievable (not perfectionistic)
