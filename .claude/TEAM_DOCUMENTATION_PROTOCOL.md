# Team Documentation Standards & Workflow Protocol

This document defines the canonical documentation artifacts, ownership, and workflow for the development team. All agents reference this protocol to ensure consistency and avoid redundant work.

---

## Core Principles

### Single Source of Truth
Each piece of knowledge has exactly one canonical location. Reference, don't duplicate. If information exists elsewhere, link to it.

### Document Decisions, Not Just Outcomes
Capture the "why" alongside the "what." Future team members (and future you) need context to understand, maintain, and evolve decisions.

### DRY for Documentation
Before creating a new document:
1. Check if a relevant document already exists
2. If yes: reference it, extend it, or propose amendments
3. If no: create it in the canonical location with proper indexing

### Living Documents
Documentation is never "done." Review and refactor during development. Update when requirements change. Deprecate when obsolete. Version significant changes.

---

## Documentation Artifacts

### PRD — Product Requirements Document
**Owner**: Requirements Analyst  
**Location**: `/docs/requirements/PRD-{feature-slug}.md`  
**Purpose**: Defines WHAT we're building and WHY, from a product/user perspective.

#### Required Sections

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

### TDD — Technical Design Document
**Owner**: Architect  
**Location**: `/docs/design/TDD-{feature-slug}.md`  
**Purpose**: Defines HOW we're building it — system design, components, interfaces, data flow.

#### Required Sections

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

### ADR — Architecture Decision Record
**Owner**: Architect (primary), Engineer (implementation-level)  
**Location**: `/docs/decisions/ADR-{NNNN}-{slug}.md`  
**Purpose**: Captures WHY a specific architectural decision was made. Provides context for future maintainers.

#### When to Write an ADR
- Choosing between multiple viable approaches
- Adopting a new pattern, library, or technology
- Deviating from established patterns
- Making trade-offs with long-term implications
- Any decision someone might later ask "why did we do it this way?"

#### Required Sections

```markdown
# ADR-{NNNN}: {Decision Title}

## Metadata
- **Status**: Proposed | Accepted | Deprecated | Superseded by ADR-{NNNN}
- **Author**: {name}
- **Date**: {date}
- **Deciders**: {who was involved in the decision}
- **Related**: PRD-{NNNN}, TDD-{NNNN}, ADR-{NNNN}

## Context
What is the situation? What forces are at play? What problem or question triggered this decision?

## Decision
What is the decision? State it clearly and directly.

## Rationale
Why this decision over the alternatives? What trade-offs were considered?

## Alternatives Considered

### {Alternative 1}
- **Description**: {What this option entails}
- **Pros**: {Benefits}
- **Cons**: {Drawbacks}
- **Why not chosen**: {Specific reason}

### {Alternative 2}
- **Description**: {What this option entails}
- **Pros**: {Benefits}
- **Cons**: {Drawbacks}
- **Why not chosen**: {Specific reason}

## Consequences
What are the implications of this decision?
- **Positive**: {Good outcomes}
- **Negative**: {Costs, risks, or limitations we're accepting}
- **Neutral**: {Other effects}

## Compliance
How do we ensure this decision is followed?
- {Linting rules, PR checklist items, architectural tests, etc.}
```

---

### Test Plan
**Owner**: QA/Adversary  
**Location**: `/docs/testing/TP-{feature-slug}.md`  
**Purpose**: Defines HOW we validate the implementation meets requirements.

#### Required Sections

```markdown
# Test Plan: {Feature Name}

## Metadata
- **TP ID**: TP-{NNNN}
- **Status**: Draft | In Review | Approved
- **Author**: {name}
- **Created**: {date}
- **PRD Reference**: PRD-{NNNN}
- **TDD Reference**: TDD-{NNNN}

## Test Scope
What is being tested? What is explicitly excluded?

## Requirements Traceability
| Requirement ID | Test Cases     | Coverage Status |
| -------------- | -------------- | --------------- |
| FR-001         | TC-001, TC-002 | Covered         |
| FR-002         | TC-003         | Covered         |
| NFR-001        | PERF-001       | Covered         |

## Test Cases

### Functional Tests
| TC ID  | Description     | Steps | Expected Result      | Priority |
| ------ | --------------- | ----- | -------------------- | -------- |
| TC-001 | {What it tests} | {How} | {What should happen} | High     |

### Edge Cases
| TC ID    | Description          | Input   | Expected Result     |
| -------- | -------------------- | ------- | ------------------- |
| EDGE-001 | {Boundary condition} | {Input} | {Expected behavior} |

### Error Cases
| TC ID   | Description  | Failure Condition | Expected Handling     |
| ------- | ------------ | ----------------- | --------------------- |
| ERR-001 | {What fails} | {How it fails}    | {How system responds} |

### Performance Tests
| PERF ID  | Scenario   | Target          | Measurement Method |
| -------- | ---------- | --------------- | ------------------ |
| PERF-001 | {Scenario} | {Target metric} | {How measured}     |

### Security Tests
| SEC ID  | Attack Vector | Test Method | Expected Defense     |
| ------- | ------------- | ----------- | -------------------- |
| SEC-001 | {Vector}      | {Method}    | {How system defends} |

## Test Environment
Requirements for test execution.

## Risks & Gaps
Known testing limitations or coverage gaps.

## Exit Criteria
What conditions must be met to consider testing complete?
```

---

## Workflow Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WORKFLOW PIPELINE                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   REQUIREMENTS   │     │    ARCHITECT     │     │    ENGINEER      │     │   QA/ADVERSARY   │
│     ANALYST      │     │                  │     │                  │     │                  │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │                        │
         │  ┌─────────────────┐   │                        │                        │
         ├──│ Produce PRD     │   │                        │                        │
         │  └────────┬────────┘   │                        │                        │
         │           │            │                        │                        │
         │           ▼            │                        │                        │
         │  ┌─────────────────┐   │                        │                        │
         │  │ PRD Review      │◄──┼── Clarifying questions │                        │
         │  └────────┬────────┘   │                        │                        │
         │           │            │                        │                        │
         │           ▼            │                        │                        │
         │  ┌─────────────────┐   │                        │                        │
         └──│ PRD Approved    │───┼──► Handoff             │                        │
            └─────────────────┘   │                        │                        │
                                  │  ┌─────────────────┐   │                        │
                                  ├──│ Check existing  │   │                        │
                                  │  │ ADRs & TDDs     │   │                        │
                                  │  └────────┬────────┘   │                        │
                                  │           │            │                        │
                                  │           ▼            │                        │
                                  │  ┌─────────────────┐   │                        │
                                  ├──│ Produce TDD     │   │                        │
                                  │  │ Reference ADRs  │   │                        │
                                  │  └────────┬────────┘   │                        │
                                  │           │            │                        │
                                  │           ▼            │                        │
                                  │  ┌─────────────────┐   │                        │
                                  │  │ New decisions?  │   │                        │
                                  │  │ Write ADRs      │   │                        │
                                  │  └────────┬────────┘   │                        │
                                  │           │            │                        │
                                  │           ▼            │                        │
                                  │  ┌─────────────────┐   │                        │
                                  └──│ TDD Approved    │───┼──► Handoff             │
                                     └─────────────────┘   │                        │
                                                           │  ┌─────────────────┐   │
                                                           ├──│ Implement per   │   │
                                                           │  │ TDD             │   │
                                                           │  └────────┬────────┘   │
                                                           │           │            │
                                                           │           ▼            │
                                                           │  ┌─────────────────┐   │
                                                           │  │ Impl decisions? │   │
                                                           │  │ Write ADRs      │   │
                                                           │  └────────┬────────┘   │
                                                           │           │            │
                                                           │           ▼            │
                                                           │  ┌─────────────────┐   │
                                                           └──│ Code Complete   │───┼──► Handoff
                                                              └─────────────────┘   │
                                                                                    │  ┌─────────────────┐
                                                                                    ├──│ Produce Test    │
                                                                                    │  │ Plan from PRD   │
                                                                                    │  └────────┬────────┘
                                                                                    │           │
                                                                                    │           ▼
                                                                                    │  ┌─────────────────┐
                                                                                    ├──│ Execute Tests   │
                                                                                    │  └────────┬────────┘
                                                                                    │           │
                                                                                    │           ▼
                                                                                    │  ┌─────────────────┐
                                                                                    │  │ Pass?           │
                                                                                    │  └────────┬────────┘
                                                                                    │           │
                                                                          ┌────────┼───────────┴───────────┐
                                                                          │        │                       │
                                                                          ▼        │                       ▼
                                                                   ┌──────────┐    │              ┌──────────────┐
                                                                   │ APPROVED │    │              │ FAIL: Route  │
                                                                   │ Ship it  │    │              │ to Engineer  │
                                                                   └──────────┘    │              │ or Analyst   │
                                                                                   │              └──────────────┘
                                                                                   │                       │
                                                                                   │◄──────────────────────┘
                                                                                   │       (iterate)
```

---

## Document Lifecycle Management

### Status Progression
```
Draft → In Review → Approved → [Active] → Deprecated/Superseded
```

### When to Update vs. Create New

| Situation                                 | Action                                       |
| ----------------------------------------- | -------------------------------------------- |
| Minor clarification or typo               | Update in place, note in revision history    |
| Scope change within same feature          | Update existing doc, increment version       |
| Significant pivot or new direction        | Supersede old doc, create new with reference |
| New feature building on existing patterns | Reference existing ADRs, create new PRD/TDD  |
| Changing a previous decision              | Create new ADR that supersedes the old one   |

### Checking for Existing Documentation

Before creating any document, agents MUST:

1. **Search existing docs** in the canonical locations
2. **Check related documents** linked in PRDs/TDDs/ADRs
3. **Ask**: Does this decision/requirement/design already exist somewhere?

If existing documentation is found:
- **Still valid?** Reference it
- **Needs update?** Propose amendments
- **Obsolete?** Mark as deprecated, create new

### Indexing

Maintain an index at `/docs/INDEX.md`:

```markdown
# Documentation Index

## PRDs
| ID       | Title               | Status   | Date       |
| -------- | ------------------- | -------- | ---------- |
| PRD-0001 | User Authentication | Approved | 2024-01-15 |

## TDDs
| ID       | Title               | PRD      | Status   | Date       |
| -------- | ------------------- | -------- | -------- | ---------- |
| TDD-0001 | Auth Service Design | PRD-0001 | Approved | 2024-01-18 |

## ADRs
| ID       | Title                              | Status   | Date       |
| -------- | ---------------------------------- | -------- | ---------- |
| ADR-0001 | Use JWT for session tokens         | Accepted | 2024-01-17 |
| ADR-0002 | Repository pattern for data access | Accepted | 2024-01-10 |

## Test Plans
| ID      | Title              | PRD      | TDD      | Status   |
| ------- | ------------------ | -------- | -------- | -------- |
| TP-0001 | Auth Service Tests | PRD-0001 | TDD-0001 | Approved |
```

---

## Cross-Agent References

Each agent prompt should include:

```markdown
## Documentation Protocol

You follow the team documentation standards defined in `TEAM_DOCUMENTATION_PROTOCOL.md`.

Before creating documentation:
1. Check `/docs/INDEX.md` for existing relevant documents
2. Search `/docs/{decisions,design,requirements}/` for related content
3. Reference existing ADRs rather than re-explaining decisions
4. Link to existing TDDs for established patterns

When creating documentation:
1. Use the canonical templates exactly
2. Assign the next sequential ID
3. Update `/docs/INDEX.md`
4. Link to all related documents

When existing documentation applies:
1. Reference by ID (e.g., "Per ADR-0042...")
2. Do not duplicate content
3. If updates needed, propose amendments with rationale
```

---

## Quality Gates by Artifact

### PRD Approval Criteria
- [ ] Problem statement is clear and compelling
- [ ] Scope explicitly defines in/out
- [ ] All requirements are specific and testable
- [ ] Acceptance criteria defined for each requirement
- [ ] Assumptions documented
- [ ] No open questions blocking design (or owners assigned)

### TDD Approval Criteria
- [ ] Traces to approved PRD
- [ ] All significant decisions have ADRs
- [ ] Component responsibilities are clear
- [ ] Interfaces are defined
- [ ] Complexity level is justified
- [ ] Risks identified with mitigations
- [ ] Implementation plan is actionable

### ADR Approval Criteria
- [ ] Context clearly explains the situation
- [ ] Decision is stated unambiguously
- [ ] Alternatives were genuinely considered
- [ ] Rationale explains why this choice
- [ ] Consequences (positive and negative) are honest

### Test Plan Approval Criteria
- [ ] All PRD requirements have traced test cases
- [ ] Edge cases identified
- [ ] Error cases covered
- [ ] Performance requirements have test methods
- [ ] Exit criteria are clear