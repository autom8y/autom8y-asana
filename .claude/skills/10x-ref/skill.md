---
name: 10x-ref
description: "Quick switch to 10x-dev-pack (full development workflow). Use when: starting feature development, needing full PRD-TDD-Code-QA pipeline, switching from specialized team to general development. Triggers: /10x, development team, dev workflow, full stack team."
---

# /10x - Quick Switch to Development Team

> **Category**: Team Management | **Phase**: Team Switching

## Purpose

Instantly switch to the 10x-dev-pack, a comprehensive development team with full lifecycle agents for building features from requirements through implementation and testing.

This is a convenience wrapper around `/team 10x-dev-pack` that also displays the team roster after switching.

---

## Usage

```bash
/10x
```

No parameters required. This command:
1. Switches to 10x-dev-pack
2. Displays team roster with agent descriptions

---

## Behavior

### 1. Invoke Team Switch

Execute via Bash tool:

```bash
$ROSTER_HOME/swap-team.sh 10x-dev-pack
```

### 2. Display Team Roster

After successful switch, show the active team roster:

```
Switched to 10x-dev-pack (5 agents loaded)

Team Roster:
┌─────────────────────────┬──────────────────────────────────────────────┐
│ Agent                   │ Role                                         │
├─────────────────────────┼──────────────────────────────────────────────┤
│ orchestrator            │ Coordinates multi-phase workflows            │
│ requirements-analyst    │ Produces PRDs, clarifies intent              │
│ architect               │ Produces TDDs and ADRs, designs solutions    │
│ principal-engineer      │ Implements code with craft and discipline    │
│ qa-adversary            │ Validates quality, finds edge cases          │
└─────────────────────────┴──────────────────────────────────────────────┘

Use /handoff <agent> to delegate work.
```

### 3. Update SESSION_CONTEXT (if active)

If a session is active:
- Update `active_team` field to `10x-dev-pack`
- Add handoff note documenting team switch

---

## Team Details

**Team Name**: 10x-dev-pack
**Agent Count**: 5
**Workflow**: Requirements → Design → Implementation → Testing

### Agents

#### orchestrator.md
**Role**: Multi-phase workflow coordination
**Invocation**: `Act as **Orchestrator**`
**Purpose**: Manages complex initiatives across multiple agents, ensures consistency, tracks progress

**When to use**:
- Platform-level initiatives (SERVICE/PLATFORM complexity)
- Multi-session projects requiring coordination
- Complex handoffs between multiple agents

#### requirements-analyst.md
**Role**: Requirements gathering and PRD creation
**Invocation**: `Act as **Requirements Analyst**`
**Purpose**: Clarifies user intent, produces Product Requirements Documents

**When to use**:
- Starting new features/initiatives
- Ambiguous requirements needing clarification
- Stakeholder needs translation to technical specs

#### architect.md
**Role**: Technical design and architecture decisions
**Invocation**: `Act as **Architect**`
**Purpose**: Produces Technical Design Documents and Architecture Decision Records

**When to use**:
- MODULE/SERVICE/PLATFORM complexity initiatives
- New architectural patterns or technology choices
- Design decisions requiring documentation
- System integration planning

#### principal-engineer.md
**Role**: Implementation with craft and discipline
**Invocation**: `Act as **Principal Engineer**`
**Purpose**: Writes production-quality code following standards and best practices

**When to use**:
- Implementing features from approved TDDs
- Refactoring with architectural changes
- Complex algorithms or business logic
- Performance-critical implementations

#### qa-adversary.md
**Role**: Quality validation and adversarial testing
**Invocation**: `Act as **QA/Adversary**`
**Purpose**: Finds edge cases, validates correctness, produces test plans

**When to use**:
- Pre-production validation
- Test plan creation
- Edge case discovery
- Security/robustness verification

---

## Examples

### Example 1: Basic Switch

```bash
/10x
```

Output:
```
[Roster] Switched to 10x-dev-pack (5 agents loaded)

Team Roster:
  - orchestrator: Coordinates multi-phase workflows
  - requirements-analyst: Produces PRDs, clarifies intent
  - architect: Produces TDDs and ADRs, designs solutions
  - principal-engineer: Implements code with craft and discipline
  - qa-adversary: Validates quality, finds edge cases

Ready for development workflow.
```

### Example 2: Switch During Session

```bash
/10x
```

Output:
```
[Roster] Switched to 10x-dev-pack (5 agents loaded)

Session context updated:
  Active team: 10x-dev-pack
  Handoff note: "Switched to development team for implementation phase"

Team Roster:
  [... agent list ...]

Next step: Use /handoff architect to review design, or /handoff engineer to begin implementation.
```

### Example 3: Already Active (Idempotent)

```bash
/10x
```

Output:
```
[Roster] Already using 10x-dev-pack (no changes needed)

Team Roster:
  [... agent list ...]
```

---

## Typical Workflow with 10x Team

### Phase 1: Requirements
```bash
/10x
/start "Add user authentication" --complexity=MODULE
# Requirements Analyst creates PRD
```

### Phase 2: Design
```bash
/handoff architect
# Architect produces TDD and ADRs
```

### Phase 3: Implementation
```bash
/handoff engineer
# Principal Engineer implements from TDD
```

### Phase 4: Validation
```bash
/handoff qa
# QA Adversary tests and validates
```

### Phase 5: Completion
```bash
/wrap
```

---

## When to Use 10x Team

Use this team for:

- **Feature development**: New capabilities requiring end-to-end workflow
- **Bug fixes (complex)**: Issues requiring design review or architectural changes
- **Refactoring projects**: Code improvements with architectural implications
- **Integration work**: Connecting systems, APIs, third-party services
- **Performance optimization**: Requires design review and testing validation

**Don't use for**:
- Documentation-only work → Use `/docs` instead
- Code quality/hygiene → Use `/hygiene` instead
- Technical debt assessment → Use `/debt` instead

---

## State Changes

### Files Modified

| File | Change | Description |
|------|--------|-------------|
| `.claude/ACTIVE_TEAM` | Set to `10x-dev-pack` | Active team state |
| `.claude/agents/` | Populated | 5 agent files loaded |
| `.claude/sessions/{session_id}/SESSION_CONTEXT.md` | `active_team` updated | If session active |

---

## Success Criteria

- Team switched to 10x-dev-pack
- 5 agent files present in `.claude/agents/`
- Team roster displayed to user
- If session active, SESSION_CONTEXT updated

---

## Error Handling

If swap fails (unlikely - this is a core team):

```
[Roster] Error: Team pack '10x-dev-pack' not found
[Roster] Use '/team --list' to see available packs
```

**Resolution**: Verify roster installation at `$ROSTER_HOME/`

---

## Related Commands

- `/team` - General team switching with options
- `/docs` - Quick switch to documentation team
- `/hygiene` - Quick switch to code hygiene team
- `/debt` - Quick switch to technical debt team
- `/start` - Begin session (can specify team)
- `/handoff` - Delegate to specific agent in current team

---

## Related Documentation

- [10x-workflow skill](../10x-workflow/SKILL.md) - Agent coordination patterns
- [COMMAND_REGISTRY.md](../../COMMAND_REGISTRY.md) - All registered commands
- [swap-team.sh]($ROSTER_HOME/swap-team.sh) - Roster swap implementation

---

## Notes

### Why "10x"?

The name reflects the full-spectrum development workflow:
- Requirements to deployment
- Design documentation to implementation
- Quality gates throughout

This is the "default" team for general development work.

### Difference from /team

| Command | Behavior |
|---------|----------|
| `/team 10x-dev-pack` | Switches team, shows swap confirmation |
| `/10x` | Switches team, shows roster with agent descriptions |

Use `/10x` when you want to see available agents after switching.

### Session Integration

This command is session-aware but doesn't require an active session:
- Works in virgin projects (no active session)
- Updates session context if one exists
- Safe to use before `/start` or after `/wrap`
