---
name: ecosystem
description: Quick switch to ecosystem (knossos infrastructure workflow)
argument-hint: "[--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: sonnet
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Switch to the ecosystem infrastructure rite and display the pantheon. $ARGUMENTS

## Behavior

1. Execute: `ari sync --rite ecosystem $ARGUMENTS`
2. Display the ari output (agents and their roles)
3. If SESSION_CONTEXT exists, update `active_rite` to `ecosystem`

**Note**: If `ari` is not in PATH, use `~/bin/ari` or build with:
`CGO_ENABLED=0 go build -o ~/bin/ari ${KNOSSOS_HOME:-~/Code/knossos}/cmd/ari`

## Flags

| Flag | Description |
|------|-------------|
| `--overwrite-diverged` | Force regeneration of diverged files |
| `--dry-run` | Preview changes without applying |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |

## When to Use

- Sync failures or conflicts
- Hook/skill registration issues
- Designing new hook or skill patterns
- Migrating satellites to new ecosystem versions
- Cross-satellite compatibility work
- Infrastructure bug fixes in knossos internals

## Workflow Phases

1. **Analysis** - Diagnose issues, trace root causes (Gap Analysis)
2. **Design** - Design hooks/skills/schemas (Context Design) [MODULE+]
3. **Implementation** - Code knossos infrastructure changes
4. **Documentation** - Write migration runbooks [MODULE+]
5. **Validation** - Test across satellite matrix (Compatibility Report)

## Complexity Levels

- **PATCH**: Single file change, no schema impact (Analysis -> Implementation -> Validation)
- **MODULE**: Single system change (materialize, provenance, or hooks) - all phases
- **SYSTEM**: Multi-system change - all phases + ADRs
- **MIGRATION**: Cross-satellite rollout - all phases + extended validation

## Reference

Full documentation: `Skill("ecosystem-ref")`
