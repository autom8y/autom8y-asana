---
name: handoff-ref
description: "Transfer work from one agent to another within active session. Generates handoff note with context, artifacts, blockers. Updates last_agent and invokes target agent. Triggers: /handoff, switch agent, transfer work, change agent, agent handoff."
---

# /handoff - Transfer Work Between Agents

> **Category**: Session Lifecycle | **Phase**: Agent Transition

## Purpose

Transfer work from the current agent to a different agent within the same active session. Generates a comprehensive handoff note capturing current phase, artifacts produced, decisions made, open questions, and blockers. Appends handoff note to SESSION_CONTEXT, invokes target agent with full context, and updates session metadata.

Use `/handoff` when:
- Transitioning between workflow phases (design → implementation)
- Current agent's work is complete and next phase begins
- Specialist expertise needed (e.g., QA validation after code complete)
- Re-routing due to discoveries or scope changes

---

## Usage

```bash
/handoff <agent-name> [note]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `agent-name` | Yes | N/A | Target agent to hand off to |
| `note` | No | Auto-generated | Optional custom handoff note/context |

### Valid Agent Names

- `requirements-analyst` (or `analyst`)
- `architect`
- `principal-engineer` (or `engineer`)
- `qa-adversary` (or `qa`)

---

## Behavior

When `/handoff` is invoked, the following sequence occurs:

### 1. Pre-flight Validation

- **Check for active session**: Verify `.claude/SESSION_CONTEXT` file exists
  - If missing → Error: "No active session to hand off. Use `/start` to begin"
- **Check not parked**: Verify `parked_at` field not set
  - If parked → Error: "Session is parked. Use `/resume` before handing off"
- **Validate target agent**: Check `.claude/agents/{agent}.md` exists in current team
  - If not found → Error: "Agent '{agent}' not found in active team '{team}'. Use `/roster` to see available agents"
- **Check for same agent handoff**: Compare to `last_agent` field
  - If same → Warning: "Already working with {agent}. Continuing without handoff..."

### 2. Generate Handoff Note

Create structured handoff note:

```markdown
## Handoff: {current_agent} → {target_agent}

**Timestamp**: 2025-12-24 15:45:00
**Handoff reason**: {auto-generated or user-provided note}

### Current Phase

{current_phase}

### Work Completed

Artifacts produced since last handoff:
- ✓ {artifact 1} - {status}
- ✓ {artifact 2} - {status}
- ⧗ {artifact 3} - {status} (if in-progress)

Decisions made:
- {list recent ADRs or key decisions}

### Current State

Progress: {phase completion status}
Blockers: {count} active
{list blockers if any}

Open questions:
{list questions if any}

### Handoff Context

{user-provided note or auto-generated context}

Key points for {target_agent}:
1. {context-specific item 1}
2. {context-specific item 2}
3. {context-specific item 3}

### Next Steps for {target_agent}

1. {recommended first action}
2. {recommended second action}
3. {recommended third action}
```

Auto-generated context varies by agent transition:

**Analyst → Architect**:
```
PRD approved and ready for technical design. Focus on:
- System architecture and component design
- Technology selection and justification (ADRs)
- Interface definitions and data flow
- Risk identification and mitigation strategies
```

**Architect → Engineer**:
```
TDD and ADRs complete and approved. Focus on:
- Implementation following TDD specifications
- Code structure matching architectural decisions
- Test coverage for all requirements
- Type safety and error handling
```

**Engineer → QA**:
```
Implementation complete, code committed. Focus on:
- Validation against PRD acceptance criteria
- Edge case and error condition testing
- Performance and scalability verification
- Production readiness assessment
```

**QA → Any (issues found)**:
```
QA validation identified {count} issues. Focus on:
- Addressing defects listed in test plan
- Re-validation after fixes
- Root cause analysis for critical issues
```

### 3. Append Handoff Note to SESSION_CONTEXT

Add handoff note to SESSION_CONTEXT body:

```markdown
---
{existing YAML frontmatter}
---

{existing context}

---

{newly generated handoff note}

---

{existing handoff notes and content}
```

### 4. Update SESSION_CONTEXT Metadata

Update YAML frontmatter:

```yaml
---
# ... existing fields ...
last_agent: "{target-agent}"
handoff_count: {increment or set to 1}
last_handoff_at: "2025-12-24T15:45:00Z"
current_phase: "{inferred from target agent}"
---
```

Phase inference:
- `requirements-analyst` → "requirements"
- `architect` → "design"
- `principal-engineer` → "implementation"
- `qa-adversary` → "validation"

### 5. Invoke Target Agent

Use Task tool to invoke target agent with full context:

```markdown
Act as **{Target Agent Name}**.

You are receiving a handoff from {current_agent}.

Initiative: {initiative}
Complexity: {complexity}
Current session phase: {current_phase}

Handoff timestamp: {now}
Handoff from: {current_agent}

{full handoff note from step 2}

Full session context:
{entire SESSION_CONTEXT content}

Artifacts available:
{list all artifacts from SESSION_CONTEXT with paths}

Review all handoff context and existing artifacts before proceeding.
Begin work based on the "Next Steps" section in the handoff note.
```

### 6. Confirmation

Display confirmation message:

```
Handoff complete: {current_agent} → {target_agent}

Session: {initiative}
New phase: {current_phase}
Handoff count: {total handoffs this session}

Handoff summary:
✓ Artifacts: {count} delivered
✓ Blockers: {count} active
✓ Context: Preserved in SESSION_CONTEXT

{target_agent} is now active and reviewing handoff.

Next: {first item from next steps}

Commands:
- /park - Pause session
- /handoff - Transfer to another agent
- /wrap - Complete session
```

---

## State Changes

### Fields Modified in SESSION_CONTEXT

| Field | Value | Description |
|-------|-------|-------------|
| `last_agent` | Target agent name | Agent now working on session |
| `handoff_count` | Incremented | Total handoffs in this session |
| `last_handoff_at` | ISO timestamp | When most recent handoff occurred |
| `current_phase` | Inferred from target agent | Current workflow phase |

### Content Additions

- Complete handoff note appended to SESSION_CONTEXT body
- Chronological handoff history preserved

---

## Examples

### Example 1: Design to Implementation Handoff

```bash
/handoff principal-engineer
```

Output:
```
Handoff: architect → principal-engineer

Generating handoff note...
✓ TDD reviewed: /docs/design/TDD-dark-mode.md
✓ ADRs captured: 2 architecture decisions
✓ Design approved by user

Handoff complete: architect → principal-engineer

Session: Add dark mode toggle
New phase: implementation
Handoff count: 1

Handoff summary:
✓ Artifacts: 3 delivered (PRD, TDD, 2 ADRs)
✓ Blockers: 0 active
✓ Context: Preserved in SESSION_CONTEXT

Principal Engineer is reviewing TDD and ready to implement.

Next: Create component structure following TDD specifications
```

### Example 2: Implementation to QA Handoff

```bash
/handoff qa-adversary "All acceptance criteria implemented, tests passing"
```

Output:
```
Handoff: principal-engineer → qa-adversary

Custom handoff note: All acceptance criteria implemented, tests passing

Generating handoff context...
✓ Code committed: src/theme/toggle.py, src/theme/storage.py
✓ Tests passing: 15/15 unit tests, 5/5 integration tests
✓ Type safety: mypy clean
✓ Linting: flake8 clean

Handoff complete: principal-engineer → qa-adversary

Session: Add dark mode toggle
New phase: validation
Handoff count: 2

Handoff summary:
✓ Artifacts: 6 delivered (PRD, TDD, 2 ADRs, code, tests)
✓ Blockers: 0 active
✓ Context: All acceptance criteria met per engineer

QA Adversary is reviewing implementation against PRD acceptance criteria.

Next: Create test plan and validate all requirements
```

### Example 3: QA Back to Engineer (Issues Found)

```bash
/handoff principal-engineer "3 defects found in edge case testing"
```

Output:
```
Handoff: qa-adversary → principal-engineer

Custom handoff note: 3 defects found in edge case testing

Generating handoff context...
✓ Test Plan created: /docs/testing/TP-dark-mode.md
⚠ Defects found: 3 issues logged
  - Issue 1: Theme not persisted on logout
  - Issue 2: Flash of wrong theme on page load
  - Issue 3: System preference override not working

Handoff complete: qa-adversary → principal-engineer

Session: Add dark mode toggle
New phase: implementation (rework)
Handoff count: 3

Handoff summary:
✓ Artifacts: 7 delivered (includes test plan)
✓ Blockers: 3 defects to address
✓ Context: QA validation identified issues requiring fixes

Principal Engineer is reviewing defects and planning fixes.

Next: Address defect #1 (theme persistence on logout)
```

### Example 4: Handoff to Same Agent (Warning)

```bash
/handoff architect
```

When `last_agent` is already `architect`:

Output:
```
⚠ Already working with architect

Session: Multi-tenant authentication
Current phase: design
Last agent: architect

No handoff needed - continuing with same agent.

To switch to a different agent, specify a different agent name.
Available agents:
- requirements-analyst
- principal-engineer
- qa-adversary
```

---

## Prerequisites

- Active session exists (`.claude/SESSION_CONTEXT` with no `parked_at`)
- Target agent exists in current active team
- Current team loaded via roster system

---

## Success Criteria

- Handoff note generated with complete context
- SESSION_CONTEXT updated with handoff metadata
- Target agent invoked with full session context
- User receives clear confirmation and next steps
- All artifacts and decisions preserved in handoff

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| No active session | `.claude/SESSION_CONTEXT` missing | Use `/start` to begin a session |
| Session parked | `parked_at` field set | Use `/resume` first, then `/handoff` |
| Invalid agent | Agent not in roster | Use valid agent name or `/roster` to list available |
| Agent not in team | Agent file missing | Check active team with `/status`, switch team if needed |
| Missing parameter | No agent specified | Provide agent name: `/handoff <agent-name>` |

---

## Related Commands

- `/start` - Begin new session
- `/resume` - Continue parked session (handoff not allowed while parked)
- `/status` - View current agent and phase
- `/wrap` - Complete session
- `/roster` - List available agents in active team

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Understanding workflow phases and transitions
- [documentation](../documentation/SKILL.md) - Artifact handoff protocols (PRD → TDD → Code)

---

## Agent Delegation

This command uses the Task tool to invoke the target agent.

The agent receives:
1. Full SESSION_CONTEXT content
2. Generated handoff note
3. List of all artifacts with paths
4. Explicit next steps from handoff note

No direct execution of agent files - all invocation via Claude Code's native Task tool.

---

## Design Notes

### Why Handoff Notes?

Handoff notes create an audit trail showing:
1. **Decision continuity**: Why work transitioned between agents
2. **Context preservation**: What the next agent needs to know
3. **Session history**: How work evolved over time
4. **Accountability**: Which agent produced which artifacts

This prevents context loss and enables future debugging of sessions.

### Why Validate Same-Agent Handoff?

Handing off to the same agent is usually a user error (confusion about current state). The warning prevents unnecessary handoff overhead while still allowing it (user may want to "reset" agent context explicitly).

### Why Infer Phase from Agent?

Phases map naturally to agents:
- Requirements phase → Analyst
- Design phase → Architect
- Implementation phase → Engineer
- Validation phase → QA

Auto-updating `current_phase` on handoff keeps session state synchronized with actual workflow progression.

### Why Count Handoffs?

`handoff_count` reveals:
1. **Workflow health**: Normal sessions have 2-4 handoffs (analyst → architect → engineer → QA)
2. **Ping-pong issues**: High counts (>6) may indicate unclear requirements or scope creep
3. **Rework patterns**: QA → Engineer → QA loops show where quality issues concentrate

Tracking handoffs enables retrospective analysis and process improvement.

### Auto-generated vs Custom Notes

The system auto-generates standard handoff notes based on phase transitions, but allows custom notes for:
1. **Exceptions**: Unusual transitions or rework loops
2. **Critical context**: Information not captured in artifacts
3. **Urgency flags**: Time-sensitive issues or blockers
4. **External dependencies**: Information from outside the session

Custom notes supplement (not replace) auto-generated context, providing flexibility without losing structure.
