# Orchestration Skill

> Consultation protocol for coordinating multi-phase workflows

## Description

This skill defines the consultation loop pattern that all orchestrated commands (/task, /sprint, /consolidate) use to coordinate work through the orchestrator agent.

## When to Use

- Multi-phase workflows requiring specialist coordination
- Commands that route work through team agents
- Any workflow where orchestrator provides the "throughline"

## Key Concept: Consultative Throughline

The orchestrator is NOT invoked to do work. It is CONSULTED for direction.

```
Main Agent ──[consult]──> Orchestrator
           <──[directive]──
Main Agent ──[Task tool]──> Specialist
           <──[artifact]──
Main Agent ──[checkpoint]──> Orchestrator
           <──[next step]──
```

## Consultation Loop

All orchestrated commands follow this loop:

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONSULTATION LOOP                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. BUILD REQUEST                                               │
│     Main agent builds CONSULTATION_REQUEST with current state    │
│                                                                  │
│  2. CONSULT ORCHESTRATOR                                        │
│     Invoke orchestrator via Task tool                           │
│     Orchestrator returns CONSULTATION_RESPONSE                  │
│                                                                  │
│  3. EXECUTE DIRECTIVE                                           │
│     Parse directive.action:                                     │
│                                                                  │
│     "invoke_specialist":                                        │
│       → Invoke specialist via Task tool with provided prompt    │
│       → Capture artifact, build checkpoint request              │
│       → Return to step 2                                        │
│                                                                  │
│     "request_info":                                             │
│       → Gather requested information                            │
│       → Build updated request with info                         │
│       → Return to step 2                                        │
│                                                                  │
│     "await_user":                                               │
│       → Present question to user                                │
│       → Capture response, build decision request                │
│       → Return to step 2                                        │
│                                                                  │
│     "complete":                                                 │
│       → Finalize session, exit loop                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Request Format

```yaml
# CONSULTATION_REQUEST
type: "initial" | "checkpoint" | "decision" | "failure"
initiative:
  name: string
  complexity: "SCRIPT" | "MODULE" | "SERVICE" | "PLATFORM"
state:
  current_phase: string | null
  completed_phases: string[]
  artifacts_produced: string[]
results:  # For checkpoint/failure
  phase_completed: string
  artifact_summary: string  # 1-2 sentences
  handoff_criteria_met: boolean[]
  failure_reason: string | null
context_summary: string  # 200 words max
```

## Response Format

```yaml
# CONSULTATION_RESPONSE
directive:
  action: "invoke_specialist" | "request_info" | "await_user" | "complete"

specialist:  # When action is invoke_specialist
  name: string
  prompt: |
    [Complete prompt for specialist]

information_needed:  # When action is request_info
  - question: string
    purpose: string

user_question:  # When action is await_user
  question: string
  options: string[] | null

state_update:
  current_phase: string
  next_phases: string[]
  routing_rationale: string

throughline:
  decision: string
  rationale: string
```

## Token Economics

| Component | Target |
|-----------|--------|
| Request | 200-400 tokens |
| Response | 400-500 tokens |
| Specialist prompt (within response) | 200-300 tokens |

**Key**: Main agent provides summaries, not full artifacts. Orchestrator trusts summaries.

## Invariants

1. **Main agent owns Task tool** - only main agent invokes specialists
2. **Orchestrator is stateless** - all state comes from request
3. **Summaries not files** - main agent summarizes artifacts for orchestrator
4. **Structured formats only** - no prose back-and-forth
5. **Throughline tracking** - every response includes decision/rationale

## Example: Initial Consultation

```yaml
# Main agent sends:
type: initial
initiative:
  name: "Add user authentication"
  complexity: MODULE
state:
  current_phase: null
  completed_phases: []
  artifacts_produced: []
context_summary: |
  Express.js API, PostgreSQL database. No existing auth.
  User wants OAuth2 with Google provider.

# Orchestrator returns:
directive:
  action: invoke_specialist
specialist:
  name: requirements-analyst
  prompt: |
    # Context
    Express.js API adding OAuth2 authentication with Google.
    No existing auth infrastructure.

    # Task
    Produce PRD for user authentication feature.

    # Constraints
    - OAuth2 with Google provider
    - Must integrate with existing user table
    - SESSION complexity (MODULE)

    # Deliverable
    PRD following standard template

    # Handoff Criteria
    - [ ] User stories defined
    - [ ] OAuth flow documented
    - [ ] Security requirements captured
state_update:
  current_phase: requirements
  next_phases: [design, implementation, validation]
  routing_rationale: "Starting with requirements per MODULE complexity"
throughline:
  decision: "Route to requirements-analyst"
  rationale: "No PRD exists, must define before design"
```

## Example: Checkpoint Consultation

```yaml
# Main agent sends:
type: checkpoint
initiative:
  name: "Add user authentication"
  complexity: MODULE
state:
  current_phase: requirements
  completed_phases: []
  artifacts_produced: [docs/PRD-auth.md]
results:
  phase_completed: requirements
  artifact_summary: "PRD covers OAuth2 with Google, 8 user stories, security reqs for token storage"
  handoff_criteria_met: [true, true, true]
  failure_reason: null
context_summary: |
  PRD approved. Covers OAuth2 flow, session management, token refresh.

# Orchestrator returns:
directive:
  action: invoke_specialist
specialist:
  name: architect
  prompt: |
    # Context
    PRD: docs/PRD-auth.md
    Scope: OAuth2 Google auth, session management, token refresh

    # Task
    Design authentication architecture for Express.js API.

    # Constraints
    - Must use existing PostgreSQL
    - Token storage must be secure (see PRD security reqs)
    - SESSION complexity

    # Deliverable
    TDD + ADRs for auth provider choice, token storage, session strategy

    # Handoff Criteria
    - [ ] OAuth flow sequence diagram
    - [ ] Database schema for tokens/sessions
    - [ ] ADR for token storage decision
state_update:
  current_phase: design
  next_phases: [implementation, validation]
  routing_rationale: "Requirements complete, moving to design per workflow"
throughline:
  decision: "Route to architect for design"
  rationale: "PRD approved with all criteria met, next phase is design"
```

## Reference

- Orchestrator agent: `.claude/agents/orchestrator.md`
- Base template: `roster/shared/base-orchestrator.md`
