# PRD (Product Requirements Document) Template

## When to Create a PRD

**Owner**: Requirements Analyst
**Location**: `/docs/requirements/PRD-{feature-slug}.md`
**Purpose**: Defines WHAT we're building and WHY, from a product/user perspective.

Create a PRD when:
- Starting a new feature or capability
- Formalizing user requirements for development
- Establishing scope and success criteria for a deliverable

---

## Template

```markdown
# PRD: {Feature Name}

## Metadata
- **PRD ID**: PRD-{NNNN}
- **Status**: Draft | In Review | Approved | Superseded
- **Author**: {name}
- **Created**: {date}
- **Last Updated**: {date}
- **Stakeholders**: {list}
- **Related PRDs**: {links to related or dependent PRDs}

## Problem Statement
What problem are we solving? For whom? What's the impact of not solving it?

## Goals & Success Metrics
How will we measure success? What outcomes matter?

## Scope
### In Scope
- {Specific capability or behavior}
- {Specific capability or behavior}

### Out of Scope
- {What we are explicitly NOT doing}
- {What we are explicitly NOT doing}

## Requirements

### Functional Requirements
| ID     | Requirement                      | Priority | Acceptance Criteria     |
| ------ | -------------------------------- | -------- | ----------------------- |
| FR-001 | {Specific, testable requirement} | Must     | {How QA validates this} |
| FR-002 | {Specific, testable requirement} | Should   | {How QA validates this} |

### Non-Functional Requirements
| ID      | Requirement  | Target      | Measurement    |
| ------- | ------------ | ----------- | -------------- |
| NFR-001 | Latency      | p95 < 200ms | {How measured} |
| NFR-002 | Availability | 99.9%       | {How measured} |

## User Stories / Use Cases
{Narrative descriptions of how users interact with the feature}

## Assumptions
- {Assumption and its basis}

## Dependencies
- {External dependency and owner}

## Open Questions
| Question   | Owner | Due Date | Resolution             |
| ---------- | ----- | -------- | ---------------------- |
| {Question} | {Who} | {When}   | {Answer when resolved} |

## Revision History
| Version | Date   | Author   | Changes       |
| ------- | ------ | -------- | ------------- |
| 1.0     | {date} | {author} | Initial draft |
```

---

## Quality Gates

A PRD is ready for approval when:

- [ ] Problem statement is clear and compelling
- [ ] Scope explicitly defines in/out
- [ ] All requirements are specific and testable
- [ ] Acceptance criteria defined for each requirement
- [ ] Assumptions documented
- [ ] No open questions blocking design (or owners assigned)
