---
user-invocable: false
---

# /handoff Behavior Specification

> Full step-by-step sequence for transferring work between agents.

## Behavior Sequence

### 1. Pre-flight Validation

Apply [Session Resolution Pattern](../shared/session-resolution.md):
- Requires: Active session (not parked)
- Verb: "hand off"

Apply [Workflow Resolution Pattern](../shared/workflow-resolution.md):
- Target agent: User-specified agent name
- Validate agent exists in current rite

**Additional Check**:
- **Check for same agent handoff**: Compare to `last_agent` field
  - If same → Warning: "Already working with {agent}. Continuing without handoff..."

See [session-validation](../../session-common/session-validation.md) for validation patterns.

### 2. Generate Handoff Note

Create structured handoff note. See [handoff-notes.md](handoff-notes.md) for templates.

Note includes:
- Transition header (current → target)
- Timestamp and handoff reason
- Artifacts produced since last handoff
- Decisions made (ADRs, key choices)
- Current state (progress, blockers, questions)
- Context-specific guidance for target agent
- Recommended next steps

### 3. Execute Atomic Handoff via Moirai

Delegate SESSION_CONTEXT mutation to Moirai agent using the Task tool:

```
Task(moirai, "handoff from <FROM_AGENT> to <TO_AGENT> with notes: <NOTES>")
```

Moirai will:
- Acquire lock to prevent race conditions
- Create backup of SESSION_CONTEXT.md
- Update last_agent in frontmatter
- Increment handoff_count
- Set last_handoff_at timestamp
- Infer and update current_phase from target agent
- Append handoff note to body (from → to, timestamp, notes)
- Validate the result
- Log to audit trail
- Rollback on failure

**Phase inference** (performed by Moirai):
| Agent | Phase |
|-------|-------|
| requirements-analyst | requirements |
| architect | design |
| principal-engineer | implementation |
| qa-adversary | validation |

See [session-context-schema](../../session-common/session-context-schema.md) for field definitions.

### 4. Invoke Target Agent

Use Task tool to invoke target agent with:
- Full SESSION_CONTEXT content
- Generated handoff note
- List of all artifacts with paths
- Explicit next steps

### 5. Confirmation

Display confirmation message with:
- Transition summary
- New phase and handoff count
- Artifact summary
- Next steps for target agent

---

## State Changes

### Fields Modified

| Field | Value | Description |
|-------|-------|-------------|
| `last_agent` | Target agent name | Agent now working on session |
| `handoff_count` | Incremented | Total handoffs in this session |
| `last_handoff_at` | ISO timestamp | When handoff occurred |
| `current_phase` | Inferred from target | Current workflow phase |

### Content Additions

- Complete handoff note appended to SESSION_CONTEXT body
- Chronological handoff history preserved

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| No active session | No session for current project | Use `/start` to begin a session |
| Session parked | `parked_at` field set | Use `/resume` first, then `/handoff` |
| Invalid agent | Agent not in this rite | Use valid agent name or `/rite` to list |
| Agent not in rite | Agent file missing | Check active rite, switch if needed |
| Missing parameter | No agent specified | Provide: `/handoff <agent-name>` |

---

## Design Notes

### Why Count Handoffs?

`handoff_count` reveals:
1. **Workflow health**: Normal sessions have 2-4 handoffs
2. **Ping-pong issues**: High counts (>6) indicate unclear requirements
3. **Rework patterns**: QA → Engineer loops show quality hotspots

### Why Infer Phase from Agent?

Phases map naturally to agents, keeping session state synchronized with actual workflow progression.

### Auto-generated vs Custom Notes

Auto-generated notes provide structure; custom notes add exception context, urgency flags, or external dependencies.
