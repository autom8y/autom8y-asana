---
name: debt
description: Quick switch to debt-triage (technical debt workflow)
argument-hint: "[--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: haiku
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Switch to the technical debt triage rite and display the pantheon. $ARGUMENTS

## Behavior

1. Execute: `ari sync --rite debt-triage $ARGUMENTS`
2. Display the pantheon output from ari (agents and their roles)
3. If SESSION_CONTEXT exists, update `active_rite` to `debt-triage`

## Flags

| Flag | Description |
|------|-------------|
| `--overwrite-diverged` | Force regeneration of diverged files |
| `--dry-run` | Preview changes without applying |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |

## When to Use

- Technical debt inventory
- Prioritizing debt paydown
- Sprint planning for maintenance
- Risk assessment of shortcuts

## Reference

Full documentation: `rites/debt-triage/mena/debt-ref/INDEX.lego.md`
