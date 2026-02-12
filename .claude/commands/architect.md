---
name: architect
description: "Design-only session producing TDD and ADRs. Use when: user says /architect, wants architecture planning, technical design without implementation. Triggers: /architect, design session, architecture planning, technical design."
argument-hint: "<feature-description> [--complexity=MODULE|SERVICE|PLATFORM]"
context: fork
---

# /architect - Design-Only Session

Run a design-only session that produces TDD and ADRs without any implementation code. Separates design approval from implementation.

## Behavior

### 1. Validate Prerequisites

Check if PRD exists. If not, invoke Requirements Analyst first:

```
Act as **Requirements Analyst**.

Feature: {feature-description}

Create PRD following documentation templates.
Save to: docs/requirements/PRD-{feature-slug}.md
```

### 2. Invoke Architect

Once PRD exists, delegate to Architect:

```
Act as **Architect**.

Feature: {feature-description}
PRD: docs/requirements/PRD-{feature-slug}.md
Complexity: {complexity}

Create TDD following documentation templates.

For MODULE: Component interfaces, key algorithms, testing strategy.
For SERVICE: System architecture, API contracts, data models, integration points, deployment.
For PLATFORM: Multi-service design, infrastructure requirements, cross-service contracts, operational runbooks.

Create ADRs for significant architectural decisions:
- Technology choices and trade-offs considered
- Architectural patterns and rejected alternatives

Save:
- TDD to: docs/design/TDD-{feature-slug}.md
- ADRs to: docs/decisions/ADR-{NNNN}-{decision-slug}.md

DO NOT implement any code. Design only.
```

**Quality gate**: TDD traces to PRD, all design decisions documented in ADRs.

### 3. Display Completion Summary

Show artifacts created (PRD if new, TDD, ADRs) and suggest next steps: review with stakeholders, then `/build` to implement.

## When to Use

| Use /architect when | Use alternative when |
|--------------------|---------------------|
| Design needs approval before build | Ready to implement --> `/task` or `/build` |
| Architecture decisions need documentation | Simple implementation --> `/task` |
| Want to separate design phase | Integrated workflow --> `/task` |

**Note**: SCRIPT complexity does not need TDD. Use `/task` directly.

## Pairing with /build

```bash
/architect "feature description"   # Phase 1: Design
# Review TDD and ADRs, get approval
/build "feature description"       # Phase 2: Implement from approved TDD
```
