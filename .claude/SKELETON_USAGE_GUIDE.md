# Skeleton Usage Guide

> How to use this skeleton to bootstrap new projects, migrate legacy systems, and run effective development workflows.

## What This Skeleton Provides

This is a **recipe module**—a pre-configured development environment with:

- **4-agent workflow**: Analyst → Architect → Engineer → QA
- **Documentation standards**: PRD, TDD, ADR, Test Plan templates
- **Code conventions**: Patterns, structure, naming
- **Quality gates**: Explicit approval criteria at each handoff

Copy this skeleton, fill in project-specific context, and start building with a principled workflow from day one.

---

## Quick Start Scenarios

### Scenario A: New Project from Scratch

```bash
# 1. Copy skeleton to new project
cp -r skeleton_claude my-new-project
cd my-new-project/

# 2. Initialize git
git init

# 3. Fill in project context
# Edit: .claude/PROJECT_CONTEXT.md
# Edit: .claude/GLOSSARY.md (domain terms)

# 4. Start Claude Code
claude
```

**First prompt to Claude:**

```text
I'm starting a new project. Read .claude/CLAUDE.md to understand the
project structure and workflow. Then read .claude/PROJECT_CONTEXT.md
for what we're building.

Let's begin with requirements. Act as the Requirements Analyst and
help me create PRD-0001 for: {describe the core feature}
```

### Scenario B: Migrate Legacy Module to Microservice

```bash
# 1. Copy skeleton to new service directory
cp -r skeleton_claude/ services/new-user-service/
cd services/new-user-service/

# 2. Fill in context (reference legacy system)
# Edit: .claude/PROJECT_CONTEXT.md
```

**First prompt to Claude:**

```text
I'm migrating a module from a legacy monolith to a new microservice.
Read .claude/CLAUDE.md for workflow context.

The legacy code is at: {path or paste code}
It currently handles: {describe functionality}

Act as the Requirements Analyst. Help me create a PRD that captures
the existing behavior we need to preserve, plus any improvements
we should make during migration.
```

### Scenario C: Add Feature to Existing Project

```text
I need to add a new feature to this project.
Read .claude/CLAUDE.md and .claude/PROJECT_CONTEXT.md first.

The feature: {describe feature}

Check /docs/INDEX.md for existing PRDs, TDDs, and ADRs that might
be relevant. Then act as the Requirements Analyst and help me
create a PRD for this feature.
```

---

## Initialization Checklist

Before starting development, complete these steps:

### Required (Do First)

- [ ] Copy skeleton to project directory
- [ ] Edit `PROJECT_CONTEXT.md`:
  - [ ] What is this project? (one paragraph)
  - [ ] Current stage (Prototype/MVP/Growth/Mature)
  - [ ] Tech stack table
  - [ ] Architecture overview
  - [ ] Current priorities
  - [ ] Known constraints
- [ ] Edit `GLOSSARY.md`:
  - [ ] Add 5-10 core domain terms
  - [ ] Define any ambiguous terms upfront
- [ ] Create `/docs/INDEX.md` (empty template is fine)
- [ ] Create directory structure:

  ```bash
  mkdir -p docs/{requirements,design,decisions,testing}
  mkdir -p src/{api,domain,infrastructure,shared}
  mkdir -p tests/{unit,integration,fixtures}
  ```

### Recommended (Do Early)

- [ ] Review `TECH_STACK.md` — confirm defaults work for this project
- [ ] Write ADR-0001: Core technology choices (if deviating from TECH_STACK.md)
- [ ] Write ADR-0002: Architecture style decision
- [ ] Customize `CODE_CONVENTIONS.md` if your stack differs
- [ ] Update `REPOSITORY_MAP.md` if structure differs

### Optional (Do When Needed)

- [ ] Add `SECURITY_GUIDELINES.md` when handling auth/PII
- [ ] Add `API_STANDARDS.md` when building APIs
- [ ] Add `RUNBOOKS.md` when approaching production

---

## Working with the 4-Agent Workflow

### Invoking Specific Agents

Each agent has a distinct role. Invoke them explicitly:

```text
Act as the Requirements Analyst. {task}
```

```text
Act as the Architect. {task}
```

```text
Act as the Principal Engineer. {task}
```

```text
Act as the QA/Adversary. {task}
```

### Agent Handoff Patterns

**Analyst → Architect:**

```text
The PRD for {feature} is complete at /docs/requirements/PRD-0001-{slug}.md

Act as the Architect. Review the PRD and create a TDD. Check
/docs/decisions/ for existing ADRs that apply. Create new ADRs
for any significant design decisions.
```

**Architect → Engineer:**

```text
The TDD is complete at /docs/design/TDD-0001-{slug}.md
Related ADRs: ADR-0001, ADR-0003

Act as the Principal Engineer. Implement the design. Follow
CODE_CONVENTIONS.md and place files per REPOSITORY_MAP.md.
Create implementation ADRs for any decisions the TDD didn't specify.
```

**Engineer → QA:**

```text
Implementation is complete.
- PRD: /docs/requirements/PRD-0001-{slug}.md
- TDD: /docs/design/TDD-0001-{slug}.md
- Code: /src/{path}

Act as the QA/Adversary. Create a Test Plan, then validate the
implementation against the PRD acceptance criteria. Find edge
cases, error handling gaps, and security issues.
```

### Skipping Agents (When Appropriate)

Not every task needs all four agents:

| Task Type                     | Agents to Use                       |
| ----------------------------- | ----------------------------------- |
| Simple bug fix                | Engineer → QA                       |
| Exploratory prototype         | Engineer only                       |
| New feature                   | Analyst → Architect → Engineer → QA |
| Architecture change           | Analyst → Architect → Engineer → QA |
| Refactor (no behavior change) | Engineer → QA                       |
| Performance optimization      | Architect → Engineer → QA           |

---

## Prompting Patterns

### Pattern: Context Loading

Always start sessions by loading context:

```text
Read these files to understand the project:
1. .claude/CLAUDE.md (entry point)
2. .claude/PROJECT_CONTEXT.md (what we're building)
3. /docs/INDEX.md (existing documentation)

Then let me know you're ready.
```

### Pattern: Requirement Clarification

When starting with vague requirements:

```text
Act as the Requirements Analyst.

I have a vague requirement: "{vague requirement}"

Before writing a PRD, ask me clarifying questions to understand:
- The actual problem being solved
- Who experiences this problem
- What success looks like
- What's explicitly out of scope
```

### Pattern: Design Review

Before implementation:

```text
Act as the Architect.

Review this TDD: /docs/design/TDD-{NNNN}-{slug}.md

Check for:
- Complexity appropriate to requirements?
- All significant decisions have ADRs?
- Interfaces clearly defined?
- Risks identified?
- Testability considered?

Provide feedback or approve for implementation.
```

### Pattern: Code Review

After implementation:

```text
Act as the QA/Adversary.

Review this implementation:
- Code: /src/{path}
- TDD: /docs/design/TDD-{NNNN}.md
- PRD: /docs/requirements/PRD-{NNNN}.md

Check for:
- Does it satisfy the TDD?
- Are acceptance criteria from PRD met?
- Error handling complete?
- Edge cases covered?
- Type hints complete?
- Would you approve this for production?
```

### Pattern: Incremental Development

For larger features, work in slices:

```text
Act as the Architect.

The PRD defines these requirements: FR-001, FR-002, FR-003, FR-004

Let's implement incrementally. Design a phased approach where each
phase delivers working functionality:

Phase 1: {minimal viable slice}
Phase 2: {add capability}
Phase 3: {complete feature}

Create a TDD for Phase 1 only. We'll extend it after Phase 1 ships.
```

### Pattern: Migration Planning

For legacy migrations:

```text
Act as the Architect.

I'm migrating this legacy code to our new architecture:
{paste or reference legacy code}

Current behavior we must preserve:
- {behavior 1}
- {behavior 2}

Improvements to make during migration:
- {improvement 1}
- {improvement 2}

Design a migration approach that:
1. Maintains backward compatibility during transition
2. Allows incremental rollout
3. Has clear rollback strategy
4. Validates parity with legacy behavior
```

### Pattern: Debugging/Investigation

When something's broken:

```text
Act as the Principal Engineer.

There's an issue: {describe symptom}

Before proposing fixes:
1. Read the relevant TDD to understand intended behavior
2. Read the relevant PRD to understand requirements
3. Check ADRs for context on why it was built this way

Then investigate the code and propose a fix with rationale.
```

---

## Plan Templates

### Template: New Feature Plan

```markdown
# Feature Plan: {Feature Name}

## Phase 0: Requirements (Analyst)
- [ ] Create PRD-{NNNN}
- [ ] Clarify acceptance criteria
- [ ] Define scope boundaries
- [ ] Identify dependencies

## Phase 1: Design (Architect)
- [ ] Review existing ADRs
- [ ] Create TDD-{NNNN}
- [ ] Create ADRs for new decisions
- [ ] Define interfaces
- [ ] Identify risks

## Phase 2: Implementation (Engineer)
- [ ] Set up module structure
- [ ] Implement core logic
- [ ] Implement API layer
- [ ] Add error handling
- [ ] Write unit tests
- [ ] Create implementation ADRs

## Phase 3: Validation (QA)
- [ ] Create Test Plan
- [ ] Execute functional tests
- [ ] Execute edge case tests
- [ ] Verify error handling
- [ ] Performance validation
- [ ] Security review

## Phase 4: Ship
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Observability in place
- [ ] Rollback plan documented
```

### Template: Migration Plan

```markdown
# Migration Plan: {Legacy Module} → {New Service}

## Phase 0: Discovery
- [ ] Document current behavior (PRD as-is)
- [ ] Identify all consumers
- [ ] Map data dependencies
- [ ] Define success criteria

## Phase 1: Design
- [ ] Create target TDD
- [ ] Define interface compatibility strategy
- [ ] Design data migration approach
- [ ] Plan parallel running period
- [ ] Create rollback strategy ADR

## Phase 2: Build
- [ ] Implement new service
- [ ] Create adapter for legacy interface (if needed)
- [ ] Implement data sync mechanism
- [ ] Build comparison tooling

## Phase 3: Validate
- [ ] Unit + integration tests
- [ ] Shadow traffic comparison
- [ ] Performance benchmarking vs. legacy
- [ ] Failure mode testing

## Phase 4: Migrate
- [ ] Deploy new service (dark)
- [ ] Enable parallel running
- [ ] Gradual traffic shift
- [ ] Monitor parity
- [ ] Decommission legacy

## Rollback Triggers
- {condition that triggers rollback}
- {condition that triggers rollback}
```

### Template: Refactor Plan

```markdown
# Refactor Plan: {What's Being Refactored}

## Scope
- **In scope**: {specific code/patterns being changed}
- **Out of scope**: {what we're NOT touching}

## Safety Net
- [ ] Existing tests pass
- [ ] Add tests for any uncovered behavior
- [ ] Identify integration points to verify

## Approach
- [ ] Create ADR explaining why this refactor
- [ ] Define incremental steps
- [ ] Each step must leave tests passing

## Steps
1. {First atomic change}
2. {Second atomic change}
3. {Third atomic change}

## Validation
- [ ] All existing tests still pass
- [ ] No behavior changes (unless intentional + documented)
- [ ] Performance not degraded
```

---

## Anti-Patterns to Avoid

### Don't: Skip Context Loading

```text
❌ "Build me a user service"
✅ "Read .claude/CLAUDE.md and PROJECT_CONTEXT.md first, then help me build a user service"
```

### Don't: Mix Agent Roles

```text
❌ "Write the requirements and then implement them"
✅ "Act as the Analyst and create the PRD. I'll review it, then we'll move to design."
```

### Don't: Skip Documentation

```text
❌ "Just implement it, we don't need a TDD for something this simple"
✅ "This is simple, so the TDD should be short. Create a minimal TDD that captures the design."
```

### Don't: Ignore Existing ADRs

```text
❌ "Let's use MongoDB for this"
✅ "Check existing ADRs for database decisions first. If we need to deviate, create a new ADR explaining why."
```

### Don't: Implement Without Acceptance Criteria

```text
❌ "Make the search feature work better"
✅ "Act as the Analyst. What does 'better' mean? Help me define testable acceptance criteria before we change anything."
```

---

## Customizing the Skeleton

### For Different Tech Stacks

If not using the default stack (Python/FastAPI/PostgreSQL/uv):

1. Review `TECH_STACK.md` — update or create ADRs for deviations
2. Update `PROJECT_CONTEXT.md` tech stack table
3. Update `CODE_CONVENTIONS.md` patterns
4. Update `REPOSITORY_MAP.md` directory structure
5. Update Engineer prompt language-specific sections

### For Different Team Sizes

**Solo developer:**

- You'll play all four roles, but still follow the workflow
- Prompts become: "Switching to Architect role. Review the PRD I just wrote..."

**Larger team:**

- Each agent prompt can map to a human role
- Humans do the work, AI assists each role

### For Different Project Types

**API-only service:**

- Emphasize API_STANDARDS.md (create if missing)
- TDD focuses on endpoint contracts

**Data pipeline:**

- Add DATA_CONTRACTS.md
- TDD focuses on schema evolution, idempotency

**CLI tool:**

- Simplify layered architecture (may not need all layers)
- Emphasize user experience in PRDs
