# Workflow Lifecycle

> Complete lifecycle from initiative scoping through delivery validation. This is the operational manual for running the 10x workflow.

---

## Lifecycle Overview

```
+-------------------------------------------------------------------------+
|                         INITIATIVE LIFECYCLE                             |
+-------------------------------------------------------------------------+
|                                                                          |
|  +------------------------------------------------------------------+   |
|  | PHASE 0: SCOPING (Prompt -1)                                      |   |
|  | ------------------------------------                              |   |
|  | Owner: User (with AI assistance)                                  |   |
|  | Purpose: Validate readiness, identify blockers, Go/No-Go         |   |
|  | Output: Scoping document with recommendation                      |   |
|  |                                                                    |   |
|  | Key Questions:                                                    |   |
|  | - Is the problem validated?                                       |   |
|  | - Is scope bounded?                                               |   |
|  | - Are there blocking dependencies?                                |   |
|  | - What's the complexity level?                                    |   |
|  | - What risks exist?                                               |   |
|  +------------------------------------------------------------------+   |
|                              |                                           |
|                              v                                           |
|                     +----------------+                                  |
|                     |   GO / NO-GO   |                                  |
|                     +----------------+                                  |
|                       |           |                                      |
|              +--------+           +--------+                            |
|              v                             v                             |
|           [GO]                         [NO-GO]                          |
|              |                             |                             |
|              |                             v                             |
|              |                    Resolve blockers                       |
|              |                    Gather context                         |
|              |                    Descope if needed                      |
|              |                    Return to Prompt -1                    |
|              |                                                           |
|              v                                                           |
|  +------------------------------------------------------------------+   |
|  | PHASE 1: INITIALIZATION (Prompt 0)                                |   |
|  | ---------------------------------                                 |   |
|  | Owner: User creates -> Orchestrator consumes                       |   |
|  | Purpose: Establish mission, structure sessions, define gates      |   |
|  | Output: Orchestrator initialization document                      |   |
|  |                                                                    |   |
|  | Contents:                                                         |   |
|  | - Mission objective and success criteria                          |   |
|  | - Session-phased approach (starting plan)                         |   |
|  | - Session trigger prompts                                         |   |
|  | - Quality gates per phase                                         |   |
|  | - Context checklist                                               |   |
|  +------------------------------------------------------------------+   |
|                              |                                           |
|                              v                                           |
|  +------------------------------------------------------------------+   |
|  | PHASE 2: ORCHESTRATED EXECUTION                                   |   |
|  | --------------------------------                                  |   |
|  | Owner: Orchestrator (coordinates) -> Specialists (execute)         |   |
|  | Purpose: Execute sessions, enforce quality gates, adapt          |   |
|  |                                                                    |   |
|  | +-------------+   +-------------+   +-------------+              |   |
|  | |  Discovery  | -> |   Design    | -> |Implementation| -> ...       |   |
|  | |  (Analyst)  |   | (Architect) |   | (Engineer)   |              |   |
|  | +-------------+   +-------------+   +-------------+              |   |
|  |        |                |                  |                      |   |
|  |        v                v                  v                      |   |
|  |   [Quality Gate]   [Quality Gate]    [Quality Gate]              |   |
|  |                                                                    |   |
|  | Orchestrator Authority:                                           |   |
|  | - Adapt session order based on discoveries                        |   |
|  | - Skip sessions when not needed                                   |   |
|  | - Add sessions when scope grows                                   |   |
|  | - Route back when gaps are found                                  |   |
|  +------------------------------------------------------------------+   |
|                              |                                           |
|                              v                                           |
|  +------------------------------------------------------------------+   |
|  | PHASE 3: VALIDATION                                               |   |
|  | ------------------                                                |   |
|  | Owner: QA/Adversary                                               |   |
|  | Purpose: Verify implementation meets requirements                 |   |
|  | Output: Validation report, Ship/No-Ship decision                 |   |
|  +------------------------------------------------------------------+   |
|                              |                                           |
|                              v                                           |
|                     +----------------+                                  |
|                     |  SHIP / ITERATE|                                  |
|                     +----------------+                                  |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Role Definitions & Responsibilities

### User (Initiative Owner)

| Responsibility | Description |
|----------------|-------------|
| **Creates Prompt -1** | Scopes initiative with AI assistance |
| **Creates Prompt 0** | Initializes orchestrator with mission context |
| **Approves plans** | Confirms "Proceed with the plan" at each phase |
| **Resolves blockers** | Provides decisions on open questions |
| **Accepts delivery** | Confirms initiative meets success criteria |

### Orchestrator (Coordinator)

| Responsibility | Description |
|----------------|-------------|
| **Assesses** | Evaluates complexity and required agents |
| **Plans** | Creates/adapts session structure |
| **Provides Directives** | Returns specialist prompts for main thread to execute |
| **Verifies** | Enforces quality gates |
| **Adapts** | Adjusts plan based on discoveries |
| **Routes** | Directs work to appropriate specialist |

**Critical**: The Orchestrator does NOT implement. It coordinates.

**Also Critical**: The Orchestrator cannot invoke specialists. It provides DIRECTIVES that the main thread executes via Task tool. See `.claude/skills/orchestration/main-thread-guide.md`.

### Requirements Analyst (Specialist)

| Responsibility | Description |
|----------------|-------------|
| **Clarifies** | Transforms vague requests into precise requirements |
| **Challenges** | Questions assumptions, surfaces ambiguity |
| **Documents** | Creates PRDs with acceptance criteria |
| **Prioritizes** | Applies MoSCoW to requirements |

**Domain Authority**: Scope definition, requirement prioritization, acceptance criteria

**Primary Artifact**: PRD (Product Requirements Document)

### Architect (Specialist)

| Responsibility | Description |
|----------------|-------------|
| **Designs** | Creates system architecture and interfaces |
| **Decides** | Makes technology and pattern choices |
| **Documents** | Creates TDDs and ADRs |
| **Calibrates** | Right-sizes solution to requirements |

**Domain Authority**: System design, technology selection, complexity calibration

**Primary Artifacts**: TDD (Technical Design Document), ADR (Architecture Decision Record)

### Principal Engineer (Specialist)

| Responsibility | Description |
|----------------|-------------|
| **Implements** | Writes production-quality code |
| **Tests** | Creates tests for all paths |
| **Documents** | Records implementation decisions |
| **Maintains** | Ensures code quality and type safety |

**Domain Authority**: Implementation approach, code structure, technical trade-offs

**Primary Artifacts**: Code, tests, implementation ADRs

### QA/Adversary (Specialist)

| Responsibility | Description |
|----------------|-------------|
| **Validates** | Verifies implementation meets requirements |
| **Attacks** | Finds edge cases and failure modes |
| **Documents** | Creates test plans and reports |
| **Assesses** | Determines production readiness |

**Domain Authority**: Test strategy, validation approach, release readiness

**Primary Artifacts**: Test Plan, validation reports, defect lists

---

## Session Protocol

Every session follows this 5-step pattern:

### 1. PLAN (Orchestrator)

```
[ ] Define session goal (one sentence)
[ ] Identify prerequisites (prior artifacts, decisions)
[ ] Specify deliverables (what will be produced)
[ ] Set quality gate criteria
[ ] Prepare context for specialist
[ ] Present plan to user
```

### 2. CLARIFY (Orchestrator + User)

```
[ ] Surface ambiguities or open questions
[ ] Propose resolutions where possible
[ ] Get user input on decisions
[ ] Confirm scope boundaries
[ ] Receive explicit "Proceed with the plan"
```

**Rule**: Never execute without explicit confirmation.

### 3. EXECUTE (Specialist)

```
[ ] Receive context from orchestrator
[ ] Plan approach within domain authority
[ ] Execute work
[ ] Document decisions made
[ ] Produce deliverables
[ ] Report completion
```

### 4. VERIFY (Orchestrator)

```
[ ] Check deliverables against quality gate
[ ] Verify no blocking open questions
[ ] Confirm handoff readiness
[ ] Document outcomes
```

### 5. HANDOFF (Orchestrator)

```
[ ] Summarize what was produced
[ ] List decisions made
[ ] Identify inputs for next phase
[ ] Note scope changes or open items
[ ] Transition to next session or conclude
```

---

## Routing Guidelines

The Orchestrator decides agent routing. These are guidelines, not rules.

### Signal-Based Routing

| Signal | Likely Agent | Considerations |
|--------|--------------|----------------|
| "What should we build?" | Requirements Analyst | Architect if technical constraints dominate |
| "How should we build it?" | Architect | Engineer if design is obvious |
| "Build it" | Principal Engineer | Consider phased implementation |
| "Does it work?" | QA/Adversary | Engineer if bugs, Analyst if requirements unclear |
| "It doesn't work" | Depends | Analyst (scope), Architect (design), Engineer (bugs) |

### Complexity-Based Patterns

| Complexity | Typical Pattern | Orchestrator Judgment |
|------------|-----------------|----------------------|
| **Script** | Engineer -> QA | May skip QA for trivial |
| **Module** | Analyst -> Engineer -> QA | May skip Analyst if clear |
| **Service** | Full workflow | May need multiple Engineer sessions |
| **Platform** | Extended workflow | May need iterative Architect involvement |

### Non-Linear Routing

Routing is not always forward. Common back-routes:

| Situation | Route |
|-----------|-------|
| Implementation reveals design flaw | Engineer -> Architect |
| Design reveals scope gap | Architect -> Analyst |
| Validation reveals requirement ambiguity | QA -> Analyst |
| Edge case needs architectural decision | QA -> Architect |

**Orchestrator Authority**: Recognize when back-routing is needed and execute without waiting to be told.

---

## Communication Patterns

### Plan -> Clarify -> Execute

**Mandatory for all significant work**. The orchestrator:
1. Presents plan to user
2. Surfaces ambiguities and gets input
3. Executes only after "Proceed with the plan"

### Session Trigger Prompts

Each session begins with a trigger prompt containing:
- Prerequisites (what must exist)
- Goals (what we're trying to achieve)
- Scope (in and out for this session)
- Constraints (what limits apply)
- Deliverable specification

### Checkpoints

At phase boundaries, the orchestrator summarizes:
- What was accomplished
- Decisions made
- Scope changes (if any)
- Next steps

---

## Problem Resolution

### Ambiguity Discovered

```
1. Pause execution
2. Surface specific ambiguity to user
3. Propose resolution if possible
4. Get clarification
5. Update plan if needed
6. Continue
```

### Quality Gate Failure

```
1. Do NOT proceed
2. Identify specific gaps
3. Determine remediation:
   - Minor: Current session
   - Major: Route to appropriate agent
4. Get user confirmation
5. Execute remediation
6. Re-verify gate
```

### Scope Creep

```
1. Flag explicitly: "This is scope creep"
2. Categorize:
   - Nice to have -> Defer
   - Actually blocking -> Re-plan
3. Propose handling
4. Get user decision
5. Document in out-of-scope or expand
```

### External Blocker

```
1. Document blocker specifically
2. Identify what can proceed
3. Propose:
   - Parallel work
   - Placeholder approach
   - Wait
4. Get user decision
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|--------------|---------|------------------|
| **Rubber-stamp gates** | Quality issues propagate | Actually verify criteria |
| **Rigid plan adherence** | Ignores discoveries | Adapt based on learning |
| **Specialist overreach** | Domain confusion | Respect domain boundaries |
| **Premature implementation** | Building wrong thing | Requirements before code |
| **Skipped scoping** | Unknown risks | Always do Prompt -1 for significant work |
| **Documentation theater** | Waste without value | Documents should be used |
| **Hidden scope creep** | Uncontrolled growth | Flag and decide explicitly |

---

## Protocol Compliance

### For Orchestrator

```
[ ] I adapt plans based on discoveries, not rigidly follow Prompt 0
[ ] I delegate decisions within domain authority, not just tasks
[ ] I verify quality gates before proceeding, not rubber-stamp
[ ] I surface ambiguities and get confirmation, not assume
[ ] I route to appropriate specialist based on need, not sequence
```

### For Specialists

```
[ ] I make decisions within my domain authority
[ ] I flag decisions outside my authority to the orchestrator
[ ] I produce artifacts that meet quality gate criteria
[ ] I document significant decisions
[ ] I report blockers and discoveries immediately
```

### For Users

```
[ ] I create Prompt -1 for significant initiatives
[ ] I provide Prompt 0 with complete context
[ ] I respond to clarifying questions promptly
[ ] I approve plans before execution begins
[ ] I make decisions when asked, not delegate back
```
