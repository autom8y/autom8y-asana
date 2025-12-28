---
description: Switch agent team packs or list available teams
argument-hint: [pack-name] [--list]
model: claude-haiku-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

**Available teams**: !`ls ~/Code/roster/teams/`

## Your Task

Manage agent team packs. $ARGUMENTS

## Behavior

**If no arguments or querying current team:**
1. Read `.claude/ACTIVE_TEAM` and display current team
2. Show: "Active team: {name}" or "No team active"

**If `--list` or `-l`:**
1. Execute: `~/Code/roster/swap-team.sh --list`
2. Display all available team packs

**If `<pack-name>` provided:**
1. Execute: `~/Code/roster/swap-team.sh <pack-name>`
2. Show confirmation with agent count
3. If SESSION_CONTEXT exists, update `active_team` field

## Examples

```bash
/team                    # Show current team
/team --list             # List all teams
/team 10x-dev-pack       # Switch to 10x development team
/team doc-team-pack      # Switch to documentation team
```

## Reference

Full documentation: `.claude/skills/team-ref/skill.md`
