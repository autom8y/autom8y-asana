---
name: doc-artifacts
description: "PRD, TDD, ADR, and Test templates for 10x development workflow. Use when: writing requirements, creating technical designs, recording architecture decisions, planning tests. Triggers: PRD, TDD, ADR, test plan, requirements document, technical design."
---

# Development Artifact Templates

Templates for the 10x development workflow artifacts.

## PRD Template {#prd-template}

```markdown
# PRD: [Feature Name]

## Overview
[2-3 sentence summary of what and why]

## Background
[Context: why now, what problem, who's affected]

## User Stories
- As a [role], I want [capability], so that [benefit]

## Functional Requirements
### Must Have
- FR-1: [requirement]
- FR-2: [requirement]

### Should Have
- FR-3: [requirement]

### Could Have
- FR-4: [requirement]

## Non-Functional Requirements
- NFR-1: Performance - [specific metric]
- NFR-2: Security - [specific requirement]

## Edge Cases
| Case | Expected Behavior |
|------|------------------|
| [scenario] | [behavior] |

## Success Criteria
- [ ] [Testable criterion 1]
- [ ] [Testable criterion 2]

## Out of Scope
- [Explicitly excluded item]

## Open Questions
- [Any unresolved items - ideally none at handoff]
```

---

## TDD Template {#tdd-template}

```markdown
# TDD: [Feature Name]

## Overview
[2-3 sentence summary of the technical approach]

## Context
[Link to PRD, relevant constraints, existing system context]

## System Design

### Architecture Diagram
[ASCII or description of component relationships]

### Components
| Component | Responsibility | Technology |
|-----------|---------------|------------|
| [name] | [what it does] | [stack] |

### Data Model
[Entity definitions, relationships, storage approach]

### API Contracts
[Endpoint specifications, request/response formats]

### Sequence Diagrams
[Key flows illustrated step by step]

## Non-Functional Considerations

### Performance
[Scaling approach, caching strategy, performance targets]

### Security
[Authentication, authorization, data protection]

### Reliability
[Failure modes, recovery strategies, monitoring]

## Implementation Guidance
[Recommended patterns, libraries, approaches]

## Risks and Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [risk] | [H/M/L] | [H/M/L] | [strategy] |

## ADRs
[List of related ADRs with links]

## Open Items
[Any items requiring resolution during implementation]
```

---

## ADR Template {#adr-template}

```markdown
# ADR-[number]: [Decision Title]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-X]

## Context
[What situation or problem prompted this decision?]

## Decision
[What is the change that we're proposing or have decided?]

## Alternatives Considered
### Option A: [Name]
- Pros: [list]
- Cons: [list]

### Option B: [Name]
- Pros: [list]
- Cons: [list]

## Rationale
[Why did we choose this option over the alternatives?]

## Consequences
### Positive
- [consequence]

### Negative
- [consequence]

### Neutral
- [consequence]
```

---

## Test Case Template {#test-case-template}

```markdown
## TC-[number]: [Test case name]

**Requirement**: [Link to PRD requirement or success criterion]
**Priority**: High / Medium / Low
**Type**: Functional / Security / Performance / Edge Case

### Preconditions
- [Required state before test]

### Steps
1. [Action]
2. [Action]
3. [Action]

### Expected Result
[What should happen]

### Actual Result
[What did happen] - PASS / FAIL

### Notes
[Any observations, variations, or follow-up items]
```

---

## Test Summary Template {#test-summary-template}

```markdown
# Test Summary: [Feature Name]

## Overview
- **Test Period**: [dates]
- **Tester**: QA Adversary
- **Build/Version**: [identifier]

## Results Summary
| Category | Pass | Fail | Blocked | Not Run |
|----------|------|------|---------|---------|
| Acceptance Criteria | | | | |
| Edge Cases | | | | |
| Security | | | | |
| Performance | | | | |

## Critical Defects
[List of critical/high defects with status]

## Release Recommendation
**[GO / NO-GO / CONDITIONAL]**

[Rationale for recommendation]

## Known Issues
[Issues that are acceptable for release, with justification]

## Risks
[Identified risks and their likelihood/impact]

## Not Tested
[What wasn't tested and why]
```
