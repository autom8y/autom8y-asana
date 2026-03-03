# Agent Delegation Patterns

> Task tool invocation patterns for session-lifecycle workflows.

## Overview

Session-lifecycle commands frequently delegate to specialist agents via the Task tool. This document defines standard patterns for agent invocation, context passing, and response handling.

## Invocation Pattern

### Basic Structure

```markdown
Task({agent-name}, "{instruction}

Session Context:
- Session ID: {session_id}
- Initiative: {initiative}
- Complexity: {complexity}
- Current Phase: {current_phase}
- Artifacts: {artifact_list}

{agent-specific-context}")
```

### Context Required

All agent invocations MUST include:

1. **Session ID** - For state correlation
2. **Initiative** - What's being built
3. **Complexity** - Scope indicator
4. **Current Phase** - Workflow position
5. **Artifacts** - What already exists

### Optional Context

Include when relevant:

- **Blockers** - Current impediments
- **Open Questions** - Unresolved issues
- **Handoff Notes** - Context from previous agent
- **Git Status** - Code state
- **Next Steps** - Pending actions

## Agent-Specific Patterns

### Requirements Analyst

**When**: /start (all complexity), iteration from QA/Engineer

**Invocation**:
```markdown
Task(requirements-analyst, "Create PRD for initiative.

Session Context:
- Session ID: {session_id}
- Initiative: {initiative}
- Complexity: {complexity}

Create PRD following template at `.claude/skills/documentation/templates/prd.md` -- template paths are illustrative; actual templates vary by rite.

Clarify ambiguities with user before drafting.

Save to: .ledge/specs/PRD-{slug}.md

Update SESSION_CONTEXT artifacts array when complete.")
```

**Expected Artifacts**:
- PRD at `.ledge/specs/PRD-{slug}.md`

**Duration**: 10-30 minutes

---

### Architect

**When**: /start (MODULE+), design iteration, engineer escalation

**Invocation**:
```markdown
Task(architect, "Create technical design for initiative.

Session Context:
- Session ID: {session_id}
- Initiative: {initiative}
- Complexity: {complexity}
- PRD: .ledge/specs/PRD-{slug}.md

Create TDD following template at `.claude/skills/documentation/templates/tdd.md` -- template paths are illustrative; actual templates vary by rite.

Identify architecture decisions and create ADRs using template at `.claude/skills/documentation/templates/adr.md` -- template paths are illustrative; actual templates vary by rite.

Save artifacts:
- TDD: .ledge/specs/TDD-{slug}.md
- ADRs: .ledge/decisions/ADR-{NNNN}-{decision-slug}.md

Update SESSION_CONTEXT artifacts array when complete.")
```

**Expected Artifacts**:
- TDD at `.ledge/specs/TDD-{slug}.md`
- ADRs at `.ledge/decisions/ADR-{NNNN}-*.md`

**Duration**: 30-90 minutes

---

### Principal Engineer

**When**: /handoff engineer, implementation phase

**Invocation**:
```markdown
Task(principal-engineer, "Implement feature following design.

Session Context:
- Session ID: {session_id}
- Initiative: {initiative}
- Complexity: {complexity}
- Current Phase: implementation
- PRD: .ledge/specs/PRD-{slug}.md
- TDD: .ledge/specs/TDD-{slug}.md (if MODULE+)
- Artifacts: {artifact_list}

Follow TDD specifications, create tests, ensure type safety.

Commit code when complete.

Update SESSION_CONTEXT artifacts array with code paths.")
```

**Expected Artifacts**:
- Code (implementation)
- Tests
- Git commits

**Duration**: 2-8 hours (may park/resume)

---

### QA Adversary

**When**: /handoff qa, final validation before /wrap

**Invocation**:
```markdown
Task(qa-adversary, "Validate implementation against requirements.

Session Context:
- Session ID: {session_id}
- Initiative: {initiative}
- Complexity: {complexity}
- Current Phase: validation
- PRD: .ledge/specs/PRD-{slug}.md
- TDD: .ledge/specs/TDD-{slug}.md (if exists)
- Implementation: {code_paths}
- Artifacts: {artifact_list}

Validate all PRD acceptance criteria.
Test edge cases and error conditions.
Create Test Plan documenting validation.

Save Test Plan to: .ledge/specs/TP-{slug}.md

Report defects in SESSION_CONTEXT blockers array if found.")
```

**Expected Artifacts**:
- Test Plan at `.ledge/specs/TP-{slug}.md`
- Defect list (if issues found)

**Duration**: 30-90 minutes

---

### moirai

**When**: Any session state mutation (park, resume, wrap)

**Invocation**:
```markdown
Task(moirai, "{operation}

Session Context:
- Session ID: {session_id}
- Session Path: .sos/sessions/{session_id}/SESSION_CONTEXT.md")
```

**Operations**:
- `park_session reason='{reason}'`
- `resume_session`
- `wrap_session`
- `update_field {field}='{value}'`

**Expected Response**: JSON with success/failure and state changes

See: [Moirai Invocation Pattern](../shared/moirai-invocation.md)

**Duration**: < 1 second

## Response Handling

### Success Response

Agent completes task and returns artifacts:

1. **Verify artifacts exist** via Read tool
2. **Update SESSION_CONTEXT** via moirai
3. **Display confirmation** to user
4. **Proceed** to next step

### Partial Success

Agent completes but flags issues:

1. **Surface warnings** to user
2. **Update SESSION_CONTEXT** with notes
3. **Offer next steps** (handoff, park, continue)

### Failure Response

Agent unable to complete:

1. **Parse error message**
2. **Surface to user** with context
3. **Suggest resolution** (clarify, re-scope, handoff)
4. **Do NOT update state** (preserve pre-failure state)

## Context Passing Best Practices

### Do

- ✓ Always include session metadata
- ✓ Reference artifact paths explicitly
- ✓ Pass blockers and open questions
- ✓ Specify output paths clearly
- ✓ Update SESSION_CONTEXT after artifacts produced

### Don't

- ✗ Assume agent has context from previous work
- ✗ Pass stale artifact references
- ✗ Omit complexity (agents adjust behavior)
- ✗ Forget to specify output paths
- ✗ Update SESSION_CONTEXT directly (use moirai)

## Handoff Context

When invoking agent after /handoff, include additional context:

```markdown
Task({target_agent}, "{instruction}

Session Context:
{standard context}

Handoff Context:
- From: {previous_agent}
- Handoff Reason: {reason}
- Work Completed: {completed_artifacts}
- Blockers: {blockers}
- Open Questions: {questions}

{handoff-specific-instruction}")
```

See: [Handoff Notes](../handoff-ref/handoff-notes.md) for transition-specific templates.

## Complexity-Aware Invocation

Agents adjust behavior based on complexity:

| Complexity | Agent Adjustments |
|------------|-------------------|
| SCRIPT | Analyst: Brief PRD; Engineer: Minimal tests |
| MODULE | Analyst: Standard PRD; Architect: Detailed TDD; Engineer: Comprehensive tests |
| SERVICE | Architect: Extended TDD + multiple ADRs; QA: Integration tests |
| PLATFORM | Analyst: Initiative-level PRD; Architect: High-level + phase breakdown |

**Include complexity in ALL invocations** so agents can adjust.

## Error Escalation

If agent fails 2+ times on same task:

1. **Surface to user**: "Agent unable to complete, possible scope issue"
2. **Suggest re-scope**: Break into smaller tasks or sessions
3. **Offer handoff**: Different agent may have better approach
4. **Consider park**: May need external input or blocker resolution

## Artifact Verification

After agent invocation:

```bash
# 1. Verify artifact exists
Read({artifact_path})

# 2. Verify artifact completeness (section headers, required content)
Grep("## ", {artifact_path})

# 3. Update SESSION_CONTEXT via moirai
Task(moirai, "append_artifact type='{type}' path='{path}' status='draft'

Session Context:
- Session ID: {session_id}
- Session Path: {session_path}")
```

**Anti-pattern**: Assuming artifact exists without verification. Always Read after Write.

## Parallel Invocation

**Do NOT** invoke multiple agents in parallel for same session:

- ✗ Causes state conflicts
- ✗ Breaks handoff chain
- ✗ Confuses workflow phase

**Exception**: Different sessions can run parallel agents.

## Timeout Handling

If agent invocation times out (rare):

1. **Check artifact paths** - May have completed despite timeout
2. **Verify SESSION_CONTEXT** - May have partial update
3. **Retry once** - Transient issue
4. **Escalate to user** - If repeated failures

## Cross-References

- [Session Context Schema](session-context-schema.md) - Field definitions for context passing
- [Session Phases](session-phases.md) - Agent-to-phase mapping
- [Moirai Invocation](../shared/moirai-invocation.md) - State mutation pattern
- [Handoff Notes](../handoff-ref/handoff-notes.md) - Transition-specific context
