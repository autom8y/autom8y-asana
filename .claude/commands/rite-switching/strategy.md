---
name: strategy
description: Quick switch to strategy (business strategy workflow)
argument-hint: "[--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: haiku
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Switch to the Strategy rite and display the pantheon. $ARGUMENTS

## Behavior

1. Execute: `ari sync --rite strategy $ARGUMENTS`
2. Display the pantheon output from ari (agents and their roles)
3. Confirm `ari sync` output shows the correct active rite

## Flags

| Flag | Description |
|------|-------------|
| `--overwrite-diverged` | Force regeneration of diverged files |
| `--dry-run` | Preview changes without applying |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |

## When to Use

- Market analysis and sizing
- Competitive intelligence gathering
- Pricing and business model analysis
- Strategic roadmap planning

## Workflow

```
market-research -> competitive-analysis -> business-modeling -> strategic-planning
```

## Reference

Full documentation: `.claude/skills/strategy-ref/INDEX.md`
