# Main Thread Guide: Consultation Loop Execution

> THE discoverable template for how the main thread interacts with orchestrator

## You Are the Coach

When a workflow command (/task, /sprint, /consolidate) is active, YOU are the Coach:

- **You own the Task tool** - only you spawn specialists
- **You control execution** - orchestrator advises, you decide
- **You track state** - session context lives with you
- **You never play** - no Edit/Write during active workflow

## The Consultation Loop

```
STEP 1: Build Request
=====================
Main Thread builds CONSULTATION_REQUEST:
- type: initial | checkpoint | decision | failure
- initiative: name and complexity
- state: phases completed, artifacts produced
- context_summary: 200 words max

STEP 2: Consult (not Execute)
=============================
Invoke orchestrator via Task tool:

  Task tool -> orchestrator.md
  Prompt: |
    ## Consultation Request

    [YAML CONSULTATION_REQUEST here]

    Respond with CONSULTATION_RESPONSE only.

STEP 3: Parse Directive
=======================
Orchestrator returns CONSULTATION_RESPONSE with:
- directive.action: invoke_specialist | request_info | await_user | complete
- specialist.name and specialist.prompt (if invoke_specialist)
- state_update and throughline

STEP 4: Execute Directive
=========================
Based on directive.action:

invoke_specialist:
  Task tool -> [specialist.name].md
  Prompt: specialist.prompt from response

request_info:
  Gather info from codebase/user
  Build new request with info
  Return to Step 2

await_user:
  Present question to user
  Capture response
  Build decision request
  Return to Step 2

complete:
  Finalize session
  Exit loop
```

## Correct Invocation

**DO THIS**:
```
Task tool invocation:

Agent: orchestrator
Prompt: |
  ## Consultation Request

  type: initial
  initiative:
    name: "Add user authentication"
    complexity: MODULE
  state:
    current_phase: null
    completed_phases: []
    artifacts_produced: []
  context_summary: |
    Express.js API needs OAuth2 authentication with Google provider.
    No existing auth infrastructure. PostgreSQL database.

  Respond with CONSULTATION_RESPONSE only.
```

**DO NOT DO THIS**:
```
# WRONG - asking orchestrator to execute
"Execute the sprint. Spawn the requirements analyst."

# WRONG - treating orchestrator as implementer
"Create the PRD for user authentication."

# WRONG - prose conversation
"What should we do first?"
```

## After Orchestrator Returns

Parse the CONSULTATION_RESPONSE. If action is `invoke_specialist`:

```
Task tool invocation:

Agent: [specialist.name from response]
Prompt: [specialist.prompt from response, verbatim]
```

Then build checkpoint request and return to consultation.

## Why This Pattern Exists

1. **Orchestrator is stateless** - has no memory between calls
2. **Orchestrator has no Task tool** - cannot spawn subagents
3. **Orchestrator sees summaries** - you don't pass full artifacts
4. **Main thread owns execution** - you decide what actually happens

The orchestrator is your strategic advisor. You are the executor.

## Quick Reference

| What | Who |
|------|-----|
| Decides next phase | Orchestrator (advises) |
| Invokes specialists | Main Thread (executes) |
| Reads full files | Main Thread |
| Tracks session state | Main Thread |
| Uses Edit/Write | Specialists (via Main Thread Task invocation) |
| Uses Task tool | Main Thread ONLY |

## Workflow Detection

Check session context for:
```yaml
workflow:
  active: true
  name: "task"
```

If `workflow.active: true`, this guide applies. You are in Coach mode.
