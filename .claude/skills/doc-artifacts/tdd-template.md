---
name: doc-artifacts-tdd
description: "TDD (Technical Design Document) template. Use when: writing a technical design, documenting system architecture, specifying API contracts. Triggers: TDD, technical design, system design, architecture diagram, data model."
---

# TDD Template

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
