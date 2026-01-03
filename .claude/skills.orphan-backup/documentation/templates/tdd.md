# TDD (Technical Design Document) Template

## When to Create a TDD

**Owner**: Architect
**Location**: `/docs/design/TDD-{feature-slug}.md`
**Purpose**: Defines HOW we're building it — system design, components, interfaces, data flow.

Create a TDD when:
- An approved PRD needs technical design
- System architecture decisions need documentation
- Complex implementations require upfront planning

---

## Template

```markdown
# TDD: {Feature Name}

## Metadata
- **TDD ID**: TDD-{NNNN}
- **Status**: Draft | In Review | Approved | Superseded
- **Author**: {name}
- **Created**: {date}
- **Last Updated**: {date}
- **PRD Reference**: PRD-{NNNN} (link)
- **Related TDDs**: {links to related designs}
- **Related ADRs**: {links to relevant architecture decisions}

## Overview
Brief summary of the technical approach. One paragraph max.

## Requirements Summary
{Brief restatement of key requirements from PRD — link, don't duplicate}

## System Context
How does this feature fit into the broader system? What existing components does it interact with?

{Diagram: system context}

## Design

### Component Architecture
What are the major components? What are their responsibilities?

{Diagram: component architecture}

| Component | Responsibility | Owner          |
| --------- | -------------- | -------------- |
| {Name}    | {What it does} | {Team/service} |

### Data Model
What data structures, schemas, or models are involved?

{Schema definitions, ER diagrams, or references to existing models}

### API Contracts
What interfaces does this feature expose or consume?

{OpenAPI spec references, gRPC definitions, or interface contracts}

### Data Flow
How does data move through the system for key operations?

{Sequence diagrams for critical paths}

## Technical Decisions
Key technical choices made in this design. For significant decisions, link to ADRs.

| Decision         | Choice          | Rationale   | ADR        |
| ---------------- | --------------- | ----------- | ---------- |
| {Decision point} | {What we chose} | {Brief why} | ADR-{NNNN} |

## Complexity Assessment
What level of complexity is this solution? (Script / Module / Service / Platform)
Why is this level appropriate?

## Implementation Plan

### Phases
| Phase | Deliverable | Dependencies    | Estimate |
| ----- | ----------- | --------------- | -------- |
| 1     | {What}      | {What it needs} | {Time}   |

### Migration Strategy
{If modifying existing systems, how do we get from current state to target state?}

## Risks & Mitigations
| Risk   | Impact       | Likelihood   | Mitigation          |
| ------ | ------------ | ------------ | ------------------- |
| {Risk} | High/Med/Low | High/Med/Low | {How we address it} |

## Observability
How will we monitor this in production?
- Metrics: {what we measure}
- Logging: {what we log}
- Alerting: {what triggers alerts}

## Testing Strategy
High-level testing approach. QA will elaborate in Test Plan.
- Unit testing scope
- Integration testing scope
- Performance testing needs

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

A TDD is ready for approval when:

- [ ] Traces to approved PRD
- [ ] All significant decisions have ADRs
- [ ] Component responsibilities are clear
- [ ] Interfaces are defined
- [ ] Complexity level is justified
- [ ] Risks identified with mitigations
- [ ] Implementation plan is actionable
