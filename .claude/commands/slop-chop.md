---
name: slop-chop
description: Quick switch to slop-chop (AI code quality gate)
argument-hint: "[--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: haiku
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Switch to the slop-chop rite and display the pantheon. $ARGUMENTS

## Behavior

1. Execute: `ari sync --rite slop-chop $ARGUMENTS`
2. Display the pantheon output from ari (agents and their roles)
3. If SESSION_CONTEXT exists, update `active_rite` to `slop-chop`

## Flags

| Flag | Description |
|------|-------------|
| `--overwrite-diverged` | Force regeneration of diverged files |
| `--dry-run` | Preview changes without applying |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |

## When to Use

- AI-assisted code review (Copilot, Cursor, Codeium, GPT-generated code)
- Hallucination detection (phantom imports, invented APIs, non-existent methods)
- Temporal debt audit (stale feature flags, ephemeral comments, outdated AI assumptions)
- PR quality gate for AI-generated or AI-assisted code
- Vibe coding quality checks before merge

## Reference

Full documentation: `rites/slop-chop/mena/slop-chop-ref/slop-chop-ref.lego.md`
