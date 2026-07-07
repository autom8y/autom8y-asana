---
name: handoff
description: Transfer work to a different agent with context
argument-hint: "<agent-name> [notes]"
allowed-tools: Bash, Read, Task
disallowed-tools: Write, Edit, NotebookEdit
disable-model-invocation: true
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

Available agents are listed in your session context (`available_agents` field). If not available, run `ls .claude/agents/` to discover them.

## Your Task

Hand off work to a different agent with full context transfer. $ARGUMENTS

## Pre-flight

1. Verify active session exists (check `status` in YAML frontmatter above)
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
   - **Session complexity** (`complexity` from hook frontmatter) — tells the receiving agent the expected ceremony level
   - Determine FROM agent (from SESSION_CONTEXT last_agent or infer from current phase)

3. **Execute atomic handoff** via Moirai agent:
   Use the Task tool to invoke the moirai agent for state mutation:
   ```
   Task(moirai, "handoff from <FROM_AGENT> to <TO_AGENT> with notes: <NOTES>")
   ```
   This will:
   - Acquire lock to prevent race conditions
   - Create backup of SESSION_CONTEXT.md
   - Update last_agent in frontmatter
   - Increment handoff_count
   - Add handoff note to body (from → to, timestamp, notes)
   - Validate the result
   - Log to audit trail
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

## Sigil

### On Success

End your response with:

🤝 handed off · next: /go

The handoff itself IS the phase transition — the target agent is now active. Suggest `/go` so the user can see the updated status.

### On Failure

❌ handoff failed: {brief reason} · fix: {recovery}

Infer recovery: agent not found → check name against `ls .claude/agents/`; no active session → `/sos start`; state conflict → `/go` to check status; uncertain → `/consult`.

