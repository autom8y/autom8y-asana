# Command Integration

> How commands implement the consultation loop pattern

## Commands Using This Pattern

| Command | Purpose | Orchestrator Used |
|---------|---------|-------------------|
| `/task` | Single initiative execution | Team orchestrator |
| `/sprint` | Multi-initiative batch | Team orchestrator |
| `/consolidate` | Session wrap-up | Team orchestrator |

## Integration Pattern

### Step 1: Command Entry Point

Command file (e.g., `.claude/commands/task.md`) sets up the consultation:

```markdown
# /task - Execute Initiative

## Initialization

1. Read SESSION_CONTEXT.md for current state
2. Identify active team and orchestrator
3. Parse user input for initiative name and scope

## Consultation Setup

Build initial CONSULTATION_REQUEST:

- type: "initial"
- initiative.name: [from user input]
- initiative.complexity: [infer or ask]
- context_summary: [from session + user input]
```

### Step 2: Orchestrator Invocation

Command invokes orchestrator via Task tool:

```markdown
## Execute Consultation Loop

Invoke orchestrator with CONSULTATION_REQUEST:

**Agent**: `.claude/agents/orchestrator.md`
**Prompt**: [CONSULTATION_REQUEST as YAML block]

Parse CONSULTATION_RESPONSE and execute directive.action.
```

### Step 3: Directive Execution

Command handles each directive type:

```markdown
## Handle Directive

### If invoke_specialist:
1. Invoke specialist.name via Task tool with specialist.prompt
2. Capture result and build checkpoint CONSULTATION_REQUEST
3. Return to orchestrator consultation

### If request_info:
1. Gather each item in information_needed
2. Build updated CONSULTATION_REQUEST with gathered info
3. Return to orchestrator consultation

### If await_user:
1. Present user_question to user
2. Capture response
3. Build decision CONSULTATION_REQUEST
4. Return to orchestrator consultation

### If complete:
1. Update SESSION_CONTEXT.md
2. Report completion to user
3. Exit command
```

## Minimal Command Template

A command implementing the consultation loop:

```markdown
# /example - Example Command

## Purpose
[What this command does]

## Entry

1. Load current session state from SESSION_CONTEXT.md
2. Parse user input: `{{user_input}}`
3. Determine complexity based on scope

## Consultation Loop

### Initial Request

Build CONSULTATION_REQUEST:
- type: initial
- initiative.name: [parsed from input]
- initiative.complexity: [determined from scope]
- state: current_phase null, empty completed/artifacts
- context_summary: [relevant context]

### Loop Execution

Until directive.action is "complete":

1. Invoke orchestrator with current request
2. Parse CONSULTATION_RESPONSE
3. Execute based on directive.action:
   - invoke_specialist: Task tool with prompt, build checkpoint
   - request_info: Gather info, rebuild request
   - await_user: Ask user, build decision request
   - complete: Exit loop

### Completion

1. Update SESSION_CONTEXT.md with final state
2. Report summary to user
```

## State Management

Commands maintain state across the loop:

```yaml
# Tracked by command during loop execution
loop_state:
  iteration: number          # Current cycle count
  last_action: string        # Previous directive.action
  artifacts: string[]        # Accumulated artifact paths
  phase_history: string[]    # Completed phases
```

This state feeds into each CONSULTATION_REQUEST's `state` field.

## Error Handling

Commands handle failures at each step:

### Orchestrator Invocation Fails

```markdown
If orchestrator Task tool fails:
1. Log error with context
2. Report to user: "Orchestrator unavailable: [error]"
3. Offer fallback: Execute without orchestration?
```

### Specialist Invocation Fails

```markdown
If specialist Task tool fails:
1. Build failure CONSULTATION_REQUEST
2. Set results.failure_reason with error details
3. Consult orchestrator for recovery
```

### User Abandons

```markdown
If user cancels during await_user:
1. Update SESSION_CONTEXT.md with partial state
2. Log abandonment reason
3. Exit cleanly (work can resume later)
```

## Token Economics

Commands should track token usage:

| Component | Budget | Notes |
|-----------|--------|-------|
| Request building | 100-200 | Context summarization |
| Orchestrator call | 400-500 | Response parsing |
| Specialist call | Varies | Depends on phase |
| State update | 50-100 | SESSION_CONTEXT write |

**Optimization**: Summarize artifacts in requests, don't pass full content.

## Testing Commands

Validate command integration:

```bash
# Test initial consultation flow
/task "Add logging to auth module"

# Verify:
# 1. Orchestrator was consulted (check logs)
# 2. CONSULTATION_REQUEST was well-formed
# 3. CONSULTATION_RESPONSE was parsed correctly
# 4. Specialist was invoked with correct prompt
# 5. Checkpoint request was built after specialist
# 6. Loop continued until complete
```

## See Also

- [SKILL.md](SKILL.md) - Skill overview
- [consultation-loop.md](consultation-loop.md) - The loop pattern
- [request-format.md](request-format.md) - Request schema
- [response-format.md](response-format.md) - Response schema
