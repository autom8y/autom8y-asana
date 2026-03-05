---
name: rnd
description: Quick switch to rnd (innovation lab workflow)
argument-hint: "[--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: haiku
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Switch to the Innovation Lab (R&D) rite and display the pantheon. $ARGUMENTS

## Behavior

1. Execute: `ari sync --rite rnd $ARGUMENTS`
2. Display the pantheon output from ari (agents and their roles)
3. Confirm `ari sync` output shows the correct active rite

## Flags

| Flag | Description |
|------|-------------|
| `--overwrite-diverged` | Force regeneration of diverged files |
| `--dry-run` | Preview changes without applying |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |

## When to Use

- Evaluating new technologies
- Building proof-of-concept prototypes
- Long-term architecture planning
- Innovation and R&D exploration

## Workflow

```
scouting -> integration-analysis -> prototyping -> future-architecture
```

## Reference

Full documentation: `.claude/skills/rnd-ref/INDEX.md`
