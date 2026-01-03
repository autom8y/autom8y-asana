---
name: architect-ref
description: "Design-only session producing TDD and ADRs without implementation. Use when: planning architecture before coding, getting design approval, documenting technical decisions, designing complex systems. Triggers: /architect, design session, architecture planning, technical design."
---

# /architect - Design-Only Session

> **Category**: Development Workflows | **Phase**: Design | **Complexity**: Low

## Purpose

Run a design-only session that produces TDD and ADRs without any implementation code. This command is for architectural planning when you want to separate design approval from implementation.

Use this when you need to:
- Design a system before committing to build
- Get stakeholder approval on architecture
- Document technical decisions for future reference
- Plan complex implementations requiring design review

---

## Usage

```bash
/architect "feature-or-system-description" [--complexity=LEVEL]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `feature-or-system-description` | Yes | - | What needs to be designed |
| `--complexity` | No | Auto-detect | MODULE \| SERVICE \| PLATFORM |

**Note**: SCRIPT complexity doesn't need TDD - use `/task` directly instead.

---

## Behavior

### 1. Validate Prerequisite

Check if PRD exists:
- If PRD found: Proceed with design
- If no PRD: Invoke Requirements Analyst to create one first

```markdown
Act as **Requirements Analyst**.

Feature: {feature-description}

Create PRD following template at `.claude/skills/documentation/templates/prd.md`.

Save to: /docs/requirements/PRD-{feature-slug}.md
```

### 2. Invoke Architect

Once PRD exists, invoke Architect agent for design:

```markdown
Act as **Architect**.

Feature: {feature-description}
PRD: /docs/requirements/PRD-{feature-slug}.md
Complexity: {complexity}

Create TDD following template at `.claude/skills/documentation/templates/tdd.md`.

For MODULE:
- Component interfaces
- Key algorithms
- Testing strategy
- No implementation details

For SERVICE:
- System architecture diagram
- API contracts
- Data models
- Integration points
- Deployment considerations

For PLATFORM:
- Multi-service design
- Infrastructure requirements
- Cross-service contracts
- Operational runbooks

Create ADRs for significant architectural decisions using template at `.claude/skills/documentation/templates/adr.md`.

Document:
- Technology choices
- Architectural patterns
- Trade-offs considered
- Rejected alternatives

Save:
- TDD to: /docs/design/TDD-{feature-slug}.md
- ADRs to: /docs/decisions/ADR-{NNNN}-{decision-slug}.md

DO NOT implement any code. Design only.
```

**Quality Gate**: TDD traces to PRD, all design decisions documented in ADRs.

### 3. Design Complete

Display summary of design artifacts:

```
Design Complete: {feature-description}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Artifacts Created:
✓ PRD: /docs/requirements/PRD-{slug}.md
✓ TDD: /docs/design/TDD-{slug}.md
✓ ADRs: /docs/decisions/ADR-{N}-{slug}.md (X decisions documented)

Design Quality:
✓ All requirements traced to components
✓ Interfaces clearly defined
✓ Technology choices justified
✓ Failure modes considered

Next Steps:
- Review TDD and ADRs with stakeholders
- Get design approval
- Use `/build` to implement from approved design
- Or use `/task` for integrated workflow
```

---

## Workflow

```mermaid
graph LR
    A[/architect invoked] --> B{PRD exists?}
    B -->|No| C[Requirements Analyst]
    B -->|Yes| D[Architect]
    C --> D
    D --> E[TDD + ADRs]
    E --> F[Design Complete]
    F --> G[Ready for Review]
```

---

## Deliverables

1. **PRD** (if didn't exist): Requirements document
2. **TDD**: Technical design document
3. **ADRs**: Architecture decision records (as needed)

**NO implementation code is produced.**

---

## Examples

### Example 1: Design API Service

```bash
/architect "Design user authentication API service"
```

Output:
```
Feature: Design user authentication API service
Complexity: SERVICE (detected from description)

[Phase 1] Requirements
✓ PRD exists: /docs/requirements/PRD-user-auth-api.md

[Phase 2] Design
✓ Architect creating TDD...
✓ TDD: /docs/design/TDD-user-auth-api.md
  Components:
  - AuthenticationHandler
  - TokenManager
  - UserStore interface
  - RateLimiter middleware

✓ ADRs created:
  - ADR-0042: JWT vs Session Tokens (chose JWT)
  - ADR-0043: Token Expiration Strategy (15min access, 7day refresh)
  - ADR-0044: Password Hashing (Argon2id)

Design complete. Ready for review.

Next: After approval, use `/build` to implement.
```

### Example 2: Design Module (No PRD)

```bash
/architect "Design cache invalidation module" --complexity=MODULE
```

Output:
```
Feature: Design cache invalidation module
Complexity: MODULE

[Phase 1] Requirements
⚠ No PRD found
✓ Requirements Analyst creating PRD...
✓ PRD: /docs/requirements/PRD-cache-invalidation.md

[Phase 2] Design
✓ Architect creating TDD...
✓ TDD: /docs/design/TDD-cache-invalidation.md
  Interfaces:
  - CacheInvalidator (main API)
  - InvalidationStrategy (policy interface)
  - CacheObserver (notification)

✓ ADR created:
  - ADR-0045: Push vs Pull Invalidation (chose observer pattern)

Design complete.

Next: Review TDD, then `/build` to implement.
```

### Example 3: Platform Design

```bash
/architect "Design multi-tenant data platform" --complexity=PLATFORM
```

Output:
```
Feature: Design multi-tenant data platform
Complexity: PLATFORM

[Phase 1] Requirements
✓ PRD exists: /docs/requirements/PRD-data-platform.md

[Phase 2] Design
✓ Architect creating comprehensive TDD...
✓ TDD: /docs/design/TDD-data-platform.md (18 pages)
  Architecture:
  - Ingestion service
  - Processing pipeline
  - Storage layer
  - Query service
  - Admin API

✓ ADRs created:
  - ADR-0050: Multi-tenancy Isolation Strategy
  - ADR-0051: Data Partitioning Approach
  - ADR-0052: Processing Framework Selection
  - ADR-0053: Storage Technology Choices
  - ADR-0054: Query Engine Selection
  - ADR-0055: Deployment Topology

Design complete.

Estimated implementation: 3-6 months, 3-5 engineers

Next: Schedule architecture review meeting.
After approval: Break into sprints with `/sprint`.
```

---

## When to Use vs Alternatives

| Use /architect when... | Use alternative when... |
|-------------------|-------------------------|
| Design needs approval before build | Ready to implement → Use `/task` or `/build` |
| Multiple implementation approaches | Just building → Use `/task` |
| Architecture decisions need documentation | Simple implementation → Use `/task` |
| Want to separate design phase | Integrated workflow preferred → Use `/task` |

### /architect vs /task

- `/architect`: Design ONLY (TDD + ADRs, no code)
- `/task`: Full lifecycle (PRD → TDD → Code → QA)

### /architect + /build vs /task

- `/architect` then `/build`: Two-phase (design approval gate)
- `/task`: Single-phase (design + implementation together)

---

## Complexity Level

**LOW** - This command:
- Invokes 1-2 agents (Analyst if needed, then Architect)
- Produces documentation only
- No implementation or testing
- Suitable for design planning

**Recommended for**:
- Complex systems needing design review
- Architecture requiring stakeholder approval
- Technology choices needing documentation
- Systems where design uncertainty is high

**Not recommended for**:
- Simple features (use `/task`)
- SCRIPT complexity (doesn't need TDD)
- When design is obvious (use `/task`)
- Urgent work (use `/hotfix` or `/task`)

---

## Prerequisites

- Clear feature/system description
- 10x-dev-pack or team with Architect agent
- MODULE/SERVICE/PLATFORM complexity (SCRIPT doesn't need TDD)

---

## Success Criteria

- TDD created and traces to PRD
- All architectural decisions documented in ADRs
- Interfaces clearly defined
- No implementation code written
- Ready for design review

---

## State Changes

### Files Created

| File Type | Location | Always? |
|-----------|----------|---------|
| PRD | `/docs/requirements/PRD-{slug}.md` | If didn't exist |
| TDD | `/docs/design/TDD-{slug}.md` | Yes |
| ADRs | `/docs/decisions/ADR-{N}-{slug}.md` | As needed |

### No Implementation

This command intentionally does NOT create:
- Source code files
- Test files
- Build configurations

Use `/build` after design approval to create these.

---

## Related Commands

- `/build` - Implement from approved TDD (pairs with /architect)
- `/task` - Full lifecycle including design (alternative)
- `/sprint` - Multi-task with mixed design + implementation
- `/handoff` - Manual agent delegation (alternative approach)

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination patterns
- [documentation](../documentation/SKILL.md) - TDD/ADR templates
- [standards](../standards/SKILL.md) - Architecture conventions

---

## Notes

### Design-First Benefits

Using `/architect` before `/build`:
1. **Stakeholder approval**: Review design before implementation cost
2. **Team alignment**: Shared understanding of approach
3. **Risk reduction**: Find design flaws before coding
4. **Documentation**: Decisions captured for future reference

### When to Skip Design Phase

Use `/task` (which includes design inline) when:
- Feature is straightforward
- Design is obvious
- Speed matters more than approval gates
- Small team that doesn't need formal reviews

### Pairing with /build

Typical workflow:
```bash
# Phase 1: Design
/architect "feature description"
# Review TDD and ADRs with team
# Get approval

# Phase 2: Implement
/build "feature description"
# Implementation from approved TDD
# Produces code + tests
```

This two-phase approach provides a formal approval gate between design and implementation.

---

## Integration with Sessions

Can be used with or without sessions:

**With session**:
```bash
/start "Design auth system"
/architect "authentication service"
# Design artifacts linked to session
/park
# Later...
/resume
/build "authentication service"
/wrap
```

**Without session** (ad-hoc):
```bash
/architect "authentication service"
# Standalone design session
# Can implement later with /build
```

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| No PRD and requirements unclear | Can't design without requirements | Requirements Analyst asks clarifying questions |
| SCRIPT complexity specified | SCRIPT doesn't need TDD | Error: "Use /task for SCRIPT complexity" |
| Missing Architect agent | Team doesn't have architect | Switch to 10x-dev-pack with `/10x` |
| Design too vague | Architect can't specify interfaces | Escalate to Requirements Analyst for clarification |

---

## Metrics to Track

- Time to complete design
- Number of ADRs created
- Design review cycle time
- Changes made during implementation (indicates design quality)
