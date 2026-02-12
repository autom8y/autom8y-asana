# Consultation Request Schema

> Structure for consulting an orchestrator agent.

## Purpose

The consultation request is how the main agent provides context to an orchestrator and asks for guidance on next steps. This schema ensures the orchestrator has all information needed to make routing decisions.

## Schema

```yaml
consultation:
  type: "[startup|continuation|failure|completion]"

  initiative:
    title: "[Brief description of overall work]"
    goal: "[What we're trying to achieve]"

  state:
    current_phase: "[Phase name or 'none']"
    completed_phases:
      - "[phase 1]"
      - "[phase 2]"
    blocked_on: "[What's blocking progress, or 'none']"

  results:
    last_specialist: "[Agent name or 'none']"
    last_outcome: "[success|failure|partial]"
    artifacts_ready:
      - "[artifact name]: [location]"

  context_summary: |
    [Brief context the orchestrator needs to know]
    [Include relevant discoveries, constraints, or decisions]
    [Keep concise - orchestrator doesn't read large artifacts]
```

## Field Descriptions

### type
- **startup**: First consultation for new initiative
- **continuation**: Normal phase progression
- **failure**: Last specialist attempt failed
- **completion**: Work appears complete, need signoff

### initiative
High-level context about what we're doing and why.

### state
Current workflow position:
- `current_phase`: What phase we're in (if known)
- `completed_phases`: What's already done
- `blocked_on`: Any blockers preventing progress

### results
What just happened:
- `last_specialist`: Which agent last acted
- `last_outcome`: How it went
- `artifacts_ready`: What artifacts are available for review

### context_summary
Brief prose summary for the orchestrator. Keep focused on decisions, discoveries, or constraints that affect routing. Orchestrator doesn't read large files.

## Example

```yaml
consultation:
  type: "continuation"

  initiative:
    title: "Clean up import hygiene in internal/hook package"
    goal: "Remove unused imports and consolidate duplicate utilities"

  state:
    current_phase: "assessment"
    completed_phases: []
    blocked_on: "none"

  results:
    last_specialist: "code-smeller"
    last_outcome: "success"
    artifacts_ready:
      - "smell-report: docs/hygiene/SMELL_REPORT.md"

  context_summary: |
    Code Smeller identified 23 unused imports across 8 files in internal/hook.
    Also found 3 duplicate utility functions between hook.go and env.go.
    No architectural concerns, just hygiene cleanup.
    All tests currently passing.
```
