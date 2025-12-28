---
name: team-ref
description: "Switch agent team packs or list available teams. Integrates with roster system. Triggers: /team, switch team, change team pack, team management."
---

# /team - Agent Team Pack Switcher

> **Category**: Team Management | **Phase**: Team Switching

## Purpose

Switch between agent team packs to access specialized workflows. Each team pack provides a curated set of agents optimized for specific types of work (development, documentation, code hygiene, technical debt).

This command integrates with the roster system at `~/Code/roster/` and updates the active team context for the current project.

---

## Usage

```bash
/team                 # Show current active team
/team <pack-name>     # Switch to specified team pack
/team --list          # List all available team packs
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `pack-name` | No | Name of team pack to switch to |
| `--list` | No | List all available team packs |

---

## Behavior

When `/team` is invoked, the following sequence occurs:

### 1. Parse Arguments

Determine operation mode:

- **No arguments**: Query and display current active team
- **`--list` or `-l`**: List all available team packs
- **`<pack-name>`**: Switch to specified team pack

### 2. Invoke Roster Script

Execute the swap-team.sh script via Bash tool:

```bash
~/Code/roster/swap-team.sh [args]
```

The script handles:
- Validation of team pack existence
- Backup of current agents (if any)
- Atomic swap of agent files
- Update of `.claude/ACTIVE_TEAM` state file

### 3. Display Results

Show script output to user, which includes:

- **For query**: Current active team name
- **For list**: All available team packs
- **For swap**: Confirmation with agent count loaded

### 4. Update SESSION_CONTEXT (if active)

If a session is active (`.claude/sessions/{session_id}/SESSION_CONTEXT.md` exists):

- Update `active_team` field to new team name
- Append to handoff notes:
  ```
  Team switched: {old-team} → {new-team} ({agent-count} agents)
  Reason: [User-provided or "Manual team switch"]
  ```

---

## Available Team Packs

### 10x-dev-pack
**Agents**: Orchestrator, Requirements Analyst, Architect, Principal Engineer, QA Adversary
**Purpose**: Full-stack development workflow with TDD/PRD documentation
**Quick switch**: `/10x`

### doc-team-pack
**Agents**: Doc Auditor, Information Architect, Tech Writer, Doc Reviewer
**Purpose**: Documentation creation, API docs, technical writing
**Quick switch**: `/docs`

### hygiene-pack
**Agents**: Code Smeller, Architect Enforcer, Janitor, Audit Lead
**Purpose**: Code quality, refactoring, architectural compliance
**Quick switch**: `/hygiene`

### debt-triage-pack
**Agents**: Debt Collector, Risk Assessor, Sprint Planner
**Purpose**: Technical debt identification, prioritization, remediation planning
**Quick switch**: `/debt`

---

## State Changes

### Files Modified

| File | Change | Description |
|------|--------|-------------|
| `.claude/ACTIVE_TEAM` | Overwritten | Contains single line with active team name |
| `.claude/agents/` | Replaced | All agent files swapped atomically |
| `.claude/agents.backup/` | Created | Backup of previous agents (safety net) |
| `.claude/sessions/{session_id}/SESSION_CONTEXT.md` | Updated | If session active, team field updated |

### Exit Codes

The swap-team.sh script returns:

- `0` - Success
- `1` - Invalid arguments
- `2` - Validation failure (pack doesn't exist or invalid structure)
- `3` - Backup failure (disk full, permissions)
- `4` - Swap failure (incomplete copy, file count mismatch)

---

## Examples

### Example 1: Query Current Team

```bash
/team
```

Output:
```
[Roster] Active team: 10x-dev-pack
```

### Example 2: List Available Teams

```bash
/team --list
```

Output:
```
[Roster] Available teams:
  - 10x-dev-pack
  - debt-triage-pack
  - doc-team-pack
  - hygiene-pack
```

### Example 3: Switch to Doc Team

```bash
/team doc-team-pack
```

Output:
```
[Roster] Backed up current agents to .claude/agents.backup/
[Roster] Switched to doc-team-pack (4 agents loaded)
```

After switch, `.claude/agents/` contains:
- `doc-auditor.md`
- `information-architect.md`
- `tech-writer.md`
- `doc-reviewer.md`

### Example 4: Switch During Active Session

```bash
/team hygiene-pack
```

Output:
```
[Roster] Backed up current agents to .claude/agents.backup/
[Roster] Switched to hygiene-pack (4 agents loaded)

Session context updated:
  Active team: hygiene-pack
  Handoff note added: "Team switched: 10x-dev-pack → hygiene-pack (4 agents)"
```

### Example 5: Idempotent Switch

```bash
/team doc-team-pack   # Already active
```

Output:
```
[Roster] Already using doc-team-pack (no changes needed)
```

**Idempotency**: The script automatically detects when already on the target team and exits early. Use `--refresh` to pull latest agent definitions from roster.

---

## Refresh Mode

Use `--refresh` when you need to pull the latest agent definitions from the roster, even if already on that team.

### When to Use

- After updating agents in the roster repository
- When agents seem stale or behaving unexpectedly
- After running `git pull` in the roster repo
- To reset local agent modifications to upstream state

### Examples

```bash
# Refresh current team (most common)
/team --refresh

# Refresh specific team
/team 10x-dev-pack --refresh

# Preview what would change before refreshing
/team --refresh --dry-run
```

### Dry-Run Output

```
[Roster] Dry-run: Would refresh ecosystem-pack

Agent changes:
  ~ orchestrator.md (modified in roster)
  = ecosystem-analyst.md (unchanged)
  = integration-engineer.md (unchanged)
  + new-agent.md (new)

No changes made (--dry-run mode)
```

---

## Error Handling

### Team Pack Not Found

```bash
/team nonexistent-pack
```

Output:
```
[Roster] Error: Team pack 'nonexistent-pack' not found in ~/Code/roster/teams/
[Roster] Use './swap-team.sh --list' to see available packs
```

**Resolution**: Use `/team --list` to see valid team names

### Invalid Pack Structure

If a team pack exists but missing `agents/` directory:

```
[Roster] Error: Team pack 'broken-pack' missing agents/ directory
```

**Resolution**: Fix team pack structure in roster repository

### Backup Failure

If `.claude/` directory not writable:

```
[Roster] Error: Backup failed (disk full? permissions?)
```

**Resolution**: Check disk space, verify `.claude/` permissions

### Swap Failure

If file copy fails or count mismatch:

```
[Roster] Error: File count mismatch (expected 5, got 3)
[Roster] Restore from backup: cp -r .claude/agents.backup/* .claude/agents/
```

**Resolution**: Run restore command, investigate disk/permission issues

---

## Prerequisites

- Roster system installed at `~/Code/roster/`
- At least one team pack exists in `~/Code/roster/teams/`
- `.claude/` directory exists and is writable (created automatically if missing)

---

## Integration with Other Commands

### /start - Session Initialization

The `/start` command supports `--team=PACK` parameter:

```bash
/start "Add dark mode" --team=10x-dev-pack
```

This internally calls `/team 10x-dev-pack` before creating SESSION_CONTEXT.

### /handoff - Agent Coordination

When handing off between agents, if target agent not in current team:

```
Agent 'debt-collector' not found in current team.
Switch to 'debt-triage-pack' with /team debt-triage-pack
```

### /wrap - Session Finalization

On session wrap, current team recorded in session summary:

```
Session completed:
  Team used: hygiene-pack
  Agents invoked: code-smeller, janitor
```

---

## Quick Switch Commands

For frequently used teams, use shorthand commands:

- `/10x` → `/team 10x-dev-pack`
- `/docs` → `/team doc-team-pack`
- `/hygiene` → `/team hygiene-pack`
- `/debt` → `/team debt-triage-pack`

These commands show team roster after switch.

---

## Success Criteria

- Correct team pack loaded in `.claude/agents/`
- `.claude/ACTIVE_TEAM` file updated with team name
- Previous agents backed up to `.claude/agents.backup/`
- All expected agent files present (validated by count)
- If session active, SESSION_CONTEXT updated

---

## Related Commands

- `/10x` - Quick switch to 10x-dev-pack
- `/docs` - Quick switch to doc-team-pack
- `/hygiene` - Quick switch to hygiene-pack
- `/debt` - Quick switch to debt-triage-pack
- `/start` - Initialize session with team selection

---

## Related Documentation

- [swap-team.sh](~/Code/roster/swap-team.sh) - Roster swap script
- [TDD-roster-system.md](~/Code/roster/docs/design/TDD-0003-team-swap.md) - Roster design
- [COMMAND_REGISTRY.md](../../COMMAND_REGISTRY.md) - All registered commands

---

## Notes

### Why Atomic Swaps?

The roster system uses backup-then-swap to prevent corruption:

1. Backup current agents to `.claude/agents.backup/`
2. Clear `.claude/agents/`
3. Copy new agents from roster
4. Validate file count matches
5. Update `.claude/ACTIVE_TEAM`

If any step fails, previous agents can be restored from backup.

### Team Pack Structure

Each team pack in `~/Code/roster/teams/` has:

```
team-name/
  agents/
    agent1.md
    agent2.md
    ...
  README.md  (optional)
```

The `agents/` directory must contain at least one `.md` file.

### Session Context Awareness

This command is session-aware:
- Works with or without active session
- Updates SESSION_CONTEXT.active_team if session exists
- Logs team switch in handoff notes for audit trail

### Environment Variable Override

The roster location can be customized:

```bash
export ROSTER_HOME=/custom/path/to/roster
/team --list
```

Default: `~/Code/roster`
