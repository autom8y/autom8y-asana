---
name: forge
description: Quick switch to forge (meta-rite for building and maintaining rites)
argument-hint: "[--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: haiku
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Switch to the forge rite and display the pantheon. $ARGUMENTS

## Behavior

1. Execute: `ari sync --rite forge $ARGUMENTS`
2. Display the pantheon output from ari (agents and their roles)
3. If SESSION_CONTEXT exists, update `active_rite` to `forge`

After the switch, display this condensed overview:

```
THE FORGE - Agent Factory Rite
==============================

The rite that builds rites. Global singleton (always available).

AGENTS (7):
  Agent Designer     - Role specs and contracts
  Domain Forensics   - Codebase archaeology and domain extraction
  Prompt Architect   - System prompts (11 sections)
  Workflow Engineer  - Orchestration and commands
  Platform Engineer  - Knossos infrastructure
  Eval Specialist    - Testing and validation
  Agent Curator      - Versioning and integration

COMMANDS:
  /new-rite <name>      - Direct rite creation (no archaeology)
  /forge-rite <name>    - Archaeology-first rite creation
  /validate-rite <name> - Run validation suite on rite
  /eval-agent <name>    - Test single agent in isolation

Full docs: rites/forge/mena/forge-ref/INDEX.lego.md
```

## Flags

| Flag | Description |
|------|-------------|
| `--overwrite-diverged` | Force regeneration of diverged files |
| `--dry-run` | Preview changes without applying |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |

## When to Use

- Creating or modifying rites
- Designing new agents or workflows
- Testing and validating agent behavior
- Any meta-work on the Knossos platform itself

## Reference

Full documentation: `.claude/skills/forge-ref/INDEX.md`
