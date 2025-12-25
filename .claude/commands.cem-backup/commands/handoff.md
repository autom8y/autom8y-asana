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

1. Verify active session exists (check Session Status in context above)
2. **CRITICAL: Validate target agent exists BEFORE any state changes**:
   ```bash
   [ -f ".claude/agents/$AGENT_NAME.md" ] || { echo "Agent not found: $AGENT_NAME"; exit 1; }
   ```

## Behavior

1. **Parse and validate arguments** (BEFORE modifying any state):
   - Extract agent name (required)
   - Verify agent file exists in `.claude/agents/`
   - Extract handoff notes (optional)
   - If validation fails, exit without modifying SESSION_CONTEXT

2. **Generate handoff context**:
   - Current phase and what's complete
   - Key decisions made
   - Open questions and blockers
   - Artifacts produced with locations
   - Determine FROM agent (from SESSION_CONTEXT last_agent or infer from current phase)

3. **Execute atomic handoff mutation**:
   ```bash
   FROM_AGENT="requirements-analyst"  # Get from SESSION_CONTEXT
   TO_AGENT="$1"
   NOTES="${2:-Agent handoff}"
   .claude/hooks/lib/session-manager.sh mutate handoff "$FROM_AGENT" "$TO_AGENT" "$NOTES"
   ```
   This will:
   - Acquire lock to prevent race conditions
   - Create backup of SESSION_CONTEXT.md
   - Update last_agent in frontmatter
   - Increment handoff_count
   - Add handoff note to body (from → to, timestamp, notes)
   - Validate the result
   - Log to audit trail (.claude/sessions/.audit/session-mutations.log)
   - Rollback on failure

4. **Invoke target agent** via Task tool:
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
