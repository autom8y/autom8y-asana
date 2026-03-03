---
name: rite
description: Switch rites or list available rites
argument-hint: "[rite-name] [--list] [--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: sonnet
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

Available rites are listed in your session context (`available_rites` field). If not available, run `ls rites/` to discover them.

## Your Task

Manage rites. $ARGUMENTS

## Behavior

**If no arguments or querying current rite:**
1. Read `.claude/ACTIVE_RITE` and display current rite
2. Show: "Active rite: {name}" or "No rite active"

**If `--list` or `-l`:**
1. Execute: `ari rite list`
2. Display all available rites

**If `<rite-name>` provided:**
1. Execute: `ari sync --rite <rite-name>`
2. If orphan agents exist (agents in current project but not in target rite):
   - **Interactive (TTY)**: Prompt user for each orphan agent
   - **Non-interactive**: Require `--keep-orphans` flag
3. Show confirmation with agent count
4. If SESSION_CONTEXT exists, update `active_rite` field

**Note**: The `ari sync` command is the standard approach as of v0.2.0.

## Orphan Agent Handling

When switching rites, agents that exist in the current project but not in the target rite are called "orphans". You'll be prompted to choose for each:

| Choice | Key | Effect |
|--------|-----|--------|
| Keep | k | Agent stays in project (survives swap) |
| Promote | p | Agent moves to `~/.claude/agents/` (user-level) |
| Remove | r | Agent removed |
| Apply to all | a | Apply same choice to remaining orphans |

For CI/scripts (non-interactive), use flags:
- `--overwrite-diverged`: Force regeneration of diverged files
- `--dry-run`: Preview changes without applying
- `--keep-orphans`: Preserve orphaned knossos files (default: auto-remove)

## Agent Provenance

Agent provenance is derived from ACTIVE_RITE and the rite's manifest.yaml.
Per-agent origin tracking (AGENT_MANIFEST.json) is planned but not yet implemented.

**Note**: Rite context (phase->agent routing) is automatically injected into every session via the session-context hook.

## Quick Switch Commands

Quick-switch commands are derived from rite names:

| Rite | Quick Switch | Domain |
|------|--------------|--------|
| 10x-dev | `/10x` | Full feature development |
| debt-triage | `/debt` | Technical debt management |
| docs | `/docs` | Documentation workflows |
| ecosystem | `/ecosystem` | Knossos infrastructure |
| forge | `/forge` | Rite creation |
| hygiene | `/hygiene` | Code quality, refactoring |
| intelligence | `/intelligence` | Analytics, research |
| rnd | `/rnd` | Exploration, prototyping |
| security | `/security` | Security assessment |
| sre | `/sre` | Operations, reliability |
| strategy | `/strategy` | Business analysis |

**Note**: Use `rite-discovery` skill for programmatic rite metadata access.

## Examples

```bash
/rite                           # Show current rite
/rite --list                    # List all rites
/rite 10x-dev                   # Switch (prompts for orphans)
/rite hygiene --keep-orphans    # Switch, keep all orphans
/rite docs --overwrite-diverged  # Force regeneration of diverged files
```

## Reference

Full documentation: `mena/navigation/rite.dro.md` (self-contained)
