# Consultation Response Schema

> Structure for orchestrator's directive to main agent.

## Purpose

The consultation response is the orchestrator's structured directive to the main agent. It specifies which specialist should act next, provides a focused prompt for that specialist, and updates workflow state.

## Schema

```yaml
directive:
  action: "[invoke_specialist|await_user|complete]"
  rationale: "[Why this is the right next step]"

specialist:
  agent: "[Agent name]"
  prompt: |
    [Focused, self-contained prompt for the specialist]
    [Include relevant context and what to produce]
    [Keep concise - specialist has domain knowledge]

information_needed:
  - "[Question 1 for main agent to answer]"
  - "[Question 2]"

user_question:
  prompt: "[Question to escalate to user]"
  context: "[Why we need user input]"

state_update:
  current_phase: "[New phase name]"
  next_phases:
    - "[Upcoming phase 1]"
    - "[Upcoming phase 2]"
  dependencies:
    - "[What must complete before what]"

throughline:
  rationale: "[Why these decisions make sense together]"
  risks: "[Known risks or tradeoffs]"
  assumptions: "[What we're assuming is true]"
```

## Field Descriptions

### directive
The core decision:
- `action`: What should happen next
  - `invoke_specialist`: Delegate to a specialist agent
  - `await_user`: Need user input before proceeding
  - `complete`: Work is done, no further action
- `rationale`: Brief explanation of why

### specialist (required if action = invoke_specialist)
- `agent`: Which specialist to invoke
- `prompt`: Self-contained instructions for the specialist
  - Include what to produce (artifact, analysis, etc.)
  - Provide relevant context from consultation request
  - Keep focused on specialist's domain
  - Target ~200-300 tokens

### information_needed (optional)
List of questions main agent should answer before orchestrator can provide better guidance. Used when context is insufficient.

### user_question (optional, required if action = await_user)
Structured escalation to user:
- `prompt`: The question to ask
- `context`: Why we need this input

### state_update
Updates to workflow state:
- `current_phase`: What phase we're now in
- `next_phases`: Planned upcoming phases
- `dependencies`: What must happen before what

### throughline
Maintains consistency across consultations:
- `rationale`: Why decisions connect to earlier choices
- `risks`: Known risks being accepted
- `assumptions`: What we're assuming (may need validation)

## Example

```yaml
directive:
  action: "invoke_specialist"
  rationale: "Assessment complete with smell report ready. Need refactoring plan before execution."

specialist:
  agent: "architect-enforcer"
  prompt: |
    Review the smell report at docs/hygiene/SMELL_REPORT.md and create a phased refactoring plan.

    Context: 23 unused imports across 8 files in internal/hook package, plus 3 duplicate
    utility functions between hook.go and env.go. All tests passing. No architectural concerns.

    Produce: Refactoring plan with atomic commit sequence. Prioritize unused imports first
    (low risk), then duplicate function consolidation (requires careful testing).

    Constraints: Each commit must leave tests passing. No behavior changes.

information_needed: []

user_question: null

state_update:
  current_phase: "planning"
  next_phases:
    - "execution"
    - "audit"
  dependencies:
    - "execution blocked until planning complete"

throughline:
  rationale: "Following standard smell→plan→execute→audit flow. Assessment revealed low-risk cleanup suitable for systematic refactoring."
  risks: "Duplicate function consolidation could have subtle behavior differences if not carefully tested."
  assumptions: "Test suite has good coverage of internal/hook package."
```

## Response Size Target

Keep responses compact (~400-500 tokens). The specialist prompt is the largest component. Focus it on what the specialist needs, not exhaustive context dump.

## Actions Reference

| Action | When to Use |
|--------|-------------|
| `invoke_specialist` | Clear next specialist and sufficient context |
| `await_user` | Need user decision or clarification |
| `complete` | All phases done, handoff criteria met |
