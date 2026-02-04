# CONSULTATION_REQUEST Format

> Schema for requests sent to the orchestrator

## Schema

```yaml
type: "initial" | "checkpoint" | "decision" | "failure"

initiative:
  name: string                    # Initiative name
  complexity: "SCRIPT" | "MODULE" | "SERVICE" | "PLATFORM"

state:
  current_phase: string | null    # null for initial
  completed_phases: string[]      # Ordered list
  artifacts_produced: string[]    # File paths

results:                          # Required for checkpoint/decision/failure
  phase_completed: string         # Phase that just finished
  artifact_summary: string        # 1-2 sentences, NOT full content
  handoff_criteria_met: boolean[] # Which criteria were satisfied
  failure_reason: string | null   # Only for failure type

context_summary: string           # 200 words max
```

## Field Details

### type

| Value | When to Use |
|-------|-------------|
| `initial` | First consultation for new initiative |
| `checkpoint` | Specialist completed a phase successfully |
| `decision` | User answered a question from orchestrator |
| `failure` | Specialist failed or could not proceed |

### initiative.complexity

Determines phase count and rigor level:

| Complexity | Description | Typical Phases |
|------------|-------------|----------------|
| `SCRIPT` | Single file, hours | Implement, validate |
| `MODULE` | Multi-file, 1-2 days | Req, design, implement, validate |
| `SERVICE` | Cross-system, 1-2 weeks | Full 10x workflow |
| `PLATFORM` | Multi-team, months | Extended 10x with governance |

### context_summary

What main agent tells orchestrator about current state. Keep under 200 words.

Include:
- Relevant codebase context
- User requirements/preferences expressed
- Blockers or constraints discovered

Exclude:
- Full file contents (use artifact_summary instead)
- Detailed implementation notes
- Historical context orchestrator doesn't need

## Examples

### Initial Request

Starting a new initiative:

```yaml
type: initial
initiative:
  name: "Add webhook retry logic"
  complexity: MODULE
state:
  current_phase: null
  completed_phases: []
  artifacts_produced: []
context_summary: |
  Node.js service with existing webhook dispatch in src/webhooks/sender.ts.
  Currently fire-and-forget. User wants exponential backoff with max 5 retries.
  Dead letter queue for failed webhooks after max retries.
```

### Checkpoint Request

After specialist completes work:

```yaml
type: checkpoint
initiative:
  name: "Add webhook retry logic"
  complexity: MODULE
state:
  current_phase: requirements
  completed_phases: []
  artifacts_produced:
    - docs/PRD-webhook-retry.md
results:
  phase_completed: requirements
  artifact_summary: |
    PRD defines retry intervals (1s, 5s, 30s, 2m, 10m), dead letter table schema,
    and monitoring requirements. 6 user stories, acceptance criteria for each.
  handoff_criteria_met: [true, true, true]
  failure_reason: null
context_summary: |
  PRD approved by user. Covers retry timing, DLQ table, and Grafana dashboard.
  Ready for design phase.
```

### Decision Request

After user answers a question:

```yaml
type: decision
initiative:
  name: "Add webhook retry logic"
  complexity: MODULE
state:
  current_phase: design
  completed_phases: [requirements]
  artifacts_produced:
    - docs/PRD-webhook-retry.md
results:
  phase_completed: design-question
  artifact_summary: |
    User chose Redis over PostgreSQL for retry queue. Rationale: existing
    Redis cluster, better suited for transient queue data.
  handoff_criteria_met: []
  failure_reason: null
context_summary: |
  Architect asked whether to use Redis or PostgreSQL for retry state.
  User chose Redis. Resume design with this constraint.
```

### Failure Request

When specialist cannot proceed:

```yaml
type: failure
initiative:
  name: "Add webhook retry logic"
  complexity: MODULE
state:
  current_phase: implementation
  completed_phases: [requirements, design]
  artifacts_produced:
    - docs/PRD-webhook-retry.md
    - docs/TDD-webhook-retry.md
results:
  phase_completed: implementation
  artifact_summary: |
    Implementer started retry logic but discovered sender.ts uses deprecated
    HTTP client that doesn't support retry interceptors.
  handoff_criteria_met: [false, false]
  failure_reason: |
    Cannot implement retry logic with current HTTP client (request@2.x).
    Need architectural decision: upgrade HTTP client or implement retry
    wrapper around existing client.
context_summary: |
  Implementation blocked. The TDD assumed axios but codebase uses deprecated
  request library. Two paths forward, need decision.
```

## Validation Rules

1. `type` must be one of the four valid values
2. `initiative.name` and `complexity` are always required
3. `state` fields are always required (use empty arrays for initial)
4. `results` required for checkpoint/decision/failure types
5. `context_summary` should not exceed 200 words
6. `artifact_summary` in results should be 1-2 sentences, not full content

## See Also

- [response-format.md](response-format.md) - CONSULTATION_RESPONSE schema
- [consultation-loop.md](consultation-loop.md) - The loop pattern
