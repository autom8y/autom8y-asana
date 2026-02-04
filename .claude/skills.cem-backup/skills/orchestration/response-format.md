# CONSULTATION_RESPONSE Format

> Schema for directives returned by the orchestrator

## Schema

```yaml
directive:
  action: "invoke_specialist" | "request_info" | "await_user" | "complete"

specialist:                       # When action is invoke_specialist
  name: string                    # Agent name (e.g., "requirements-analyst")
  prompt: |
    # Context
    [What specialist needs to know]

    # Task
    [What to produce]

    # Constraints
    [Scope boundaries, quality criteria]

    # Deliverable
    [Expected artifact type and format]

    # Handoff Criteria
    - [ ] Criterion 1
    - [ ] Criterion 2

information_needed:               # When action is request_info
  - question: string
    purpose: string

user_question:                    # When action is await_user
  question: string
  options: string[] | null        # null for open-ended

state_update:
  current_phase: string
  next_phases: string[]           # Planned sequence
  routing_rationale: string       # Why this action

throughline:
  decision: string                # What was decided
  rationale: string               # Why
```

## Actions

### invoke_specialist

Route work to a specialist agent. Main agent will invoke via Task tool.

```yaml
directive:
  action: invoke_specialist
specialist:
  name: architect
  prompt: |
    # Context
    Building retry logic for webhook sender. PRD approved with 5-retry
    exponential backoff. Redis chosen for queue state.

    # Task
    Design the retry architecture including job queue schema and failure flow.

    # Constraints
    - Must use existing Redis cluster
    - Compatible with current sender.ts interface
    - Maximum 10s latency for initial dispatch

    # Deliverable
    TDD with sequence diagrams for retry flow and Redis schema

    # Handoff Criteria
    - [ ] Retry state machine documented
    - [ ] Redis key structure defined
    - [ ] DLQ flow specified
state_update:
  current_phase: design
  next_phases: [implementation, validation]
  routing_rationale: "Requirements complete, architect needed for Redis queue design"
throughline:
  decision: "Route to architect for queue design"
  rationale: "PRD approved, Redis confirmed, ready for technical design"
```

### request_info

Orchestrator needs information before deciding next step.

```yaml
directive:
  action: request_info
information_needed:
  - question: "What is the current test coverage for src/webhooks/sender.ts?"
    purpose: "Determine if refactoring requires new test scaffolding"
  - question: "Does the existing Redis cluster have pub/sub enabled?"
    purpose: "Affects choice between polling and subscription for retry worker"
state_update:
  current_phase: design
  next_phases: [design, implementation, validation]
  routing_rationale: "Need technical context before finalizing design approach"
throughline:
  decision: "Request codebase information"
  rationale: "Design depends on existing test coverage and Redis capabilities"
```

### await_user

Need user input to proceed.

```yaml
directive:
  action: await_user
user_question:
  question: |
    The webhook retry system can be implemented two ways:

    A) **In-process retry** - Simpler, but webhooks block during retry windows
    B) **Background worker** - More complex, but non-blocking dispatch

    Which approach do you prefer?
  options:
    - "A: In-process retry (simpler)"
    - "B: Background worker (scalable)"
state_update:
  current_phase: design
  next_phases: [design, implementation, validation]
  routing_rationale: "Architectural decision requires user input"
throughline:
  decision: "Pause for user architectural preference"
  rationale: "Both approaches valid, user should choose based on operational priorities"
```

### complete

Initiative finished successfully.

```yaml
directive:
  action: complete
state_update:
  current_phase: complete
  next_phases: []
  routing_rationale: "All phases complete, validation passed"
throughline:
  decision: "Mark initiative complete"
  rationale: "Implementation merged, tests passing, documentation updated"
```

## Specialist Prompt Structure

The `specialist.prompt` field follows a consistent structure:

| Section | Purpose | Length |
|---------|---------|--------|
| Context | What specialist needs to know | 2-4 sentences |
| Task | Clear directive | 1-2 sentences |
| Constraints | Scope boundaries | Bullet list |
| Deliverable | Expected output | 1 sentence |
| Handoff Criteria | Checkboxes for completion | 3-5 items |

Total prompt target: 200-300 tokens.

## Throughline Tracking

Every response includes `throughline` for decision auditability:

```yaml
throughline:
  decision: "Route to implementer for retry module"
  rationale: "TDD approved, Redis schema finalized, ready for code"
```

This creates a decision trail across consultations.

## Token Budget

| Component | Target |
|-----------|--------|
| Full response | 400-500 tokens |
| Specialist prompt | 200-300 tokens |
| State update + throughline | 100-150 tokens |

## Validation Rules

1. `directive.action` must be one of the four valid values
2. `specialist` required when action is `invoke_specialist`
3. `information_needed` required when action is `request_info`
4. `user_question` required when action is `await_user`
5. `state_update` and `throughline` always required
6. `specialist.prompt` must include all five sections

## See Also

- [request-format.md](request-format.md) - CONSULTATION_REQUEST schema
- [consultation-loop.md](consultation-loop.md) - The loop pattern
