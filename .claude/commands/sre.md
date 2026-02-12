---
name: sre
description: Quick switch to sre (reliability workflow)
argument-hint: "[--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: haiku
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Switch to the SRE rite and display the pantheon. $ARGUMENTS

## Behavior

1. Execute: `ari sync --rite sre $ARGUMENTS`
2. Display the pantheon output from ari (agents and their roles)
3. If SESSION_CONTEXT exists, update `active_rite` to `sre`

## Flags

| Flag | Description |
|------|-------------|
| `--overwrite-diverged` | Force regeneration of diverged files |
| `--dry-run` | Preview changes without applying |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |

## When to Use

- System reliability improvements
- Observability and monitoring work
- Incident response preparation
- Chaos engineering experiments
- Platform and infrastructure work

## Reference

Full documentation: `rites/sre/mena/sre-ref/INDEX.lego.md`
