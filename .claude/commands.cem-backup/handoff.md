---
description: Transfer work to a different agent with context
argument-hint: <agent-name> [notes]
allowed-tools: Bash, Read, Write, Task
model: claude-opus-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

**Available agents**: !`ls .claude/agents/`

## Your Task

Hand off work to a different agent with full context transfer. $ARGUMENTS

## Pre-flight

1. Verify `.claude/SESSION_CONTEXT` exists
2. Validate target agent exists in `.claude/agents/`

## Behavior

1. **Parse arguments**:
   - Extract agent name (required)
   - Extract handoff notes (optional)

2. **Generate handoff context**:
   - Current phase and what's complete
   - Key decisions made
   - Open questions and blockers
   - Artifacts produced with locations

3. **Update SESSION_CONTEXT**:
   ```yaml
   last_agent: {previous-agent}
   current_phase: {updated-phase}
   handoff_count: {n+1}
   ```

4. **Add handoff note** to SESSION_CONTEXT:
   ```markdown
   ## Handoff: {from} → {to}
   Time: {timestamp}
   Notes: {user notes or auto-generated summary}
   Context: {what to continue}
   ```

5. **Invoke target agent** via Task tool:
   - Include full session context
   - Include handoff notes
   - Reference relevant artifacts

## Example

```
/handoff architect "PRD approved, ready for design"
/handoff principal-engineer
```

## Reference

Full documentation: `.claude/skills/handoff-ref/skill.md`
