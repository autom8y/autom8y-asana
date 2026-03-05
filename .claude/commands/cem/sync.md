---
name: sync
description: Sync project with knossos ecosystem using ari CLI
argument-hint: "[--scope=rite|user|all] [--rite=NAME] [--dry-run] [--overwrite-diverged]"
allowed-tools: Bash, Read
model: haiku
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Execute ari sync to synchronize project with knossos ecosystem.

## Behavior

**CRITICAL**: Execute EXACTLY this command based on arguments:

| If $ARGUMENTS is... | Run this command |
|---------------------|------------------|
| Empty (no args) | `ari sync` (sync everything) |
| `--refresh` | `ari sync --scope=rite` *(dromena alias)* |
| Anything else | `ari sync $ARGUMENTS` |

**Interpret output**:
- **"no ACTIVE_RITE"**: Relay the error. For consumer projects, suggest `ari sync --rite=<name> --source=knossos`.
- **ari not found**: `cd ~/Code/knossos && CGO_ENABLED=0 go install ./cmd/ari`
- Otherwise: Report the actual output

## Command Flags

| Flag | Description |
|------|-------------|
| `--scope=SCOPE` | Sync scope: `rite`, `user`, or `all` (default: all) |
| `--rite=NAME` | Generate for specific rite (defaults to ACTIVE_RITE) |
| `--source=PATH` | Rite source: path or `knossos` alias (default: embedded) |
| `--overwrite-diverged` | Overwrite files that have diverged from source |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |
| `--dry-run` | Preview changes without applying |

For all flags: `ari sync --help`

## Legacy Compatibility

- `knossos-sync` shell script → Use `ari sync` instead
- `ari sync materialize` → Use `ari sync` instead
- `ari sync user` → Use `ari sync --scope=user` instead
- `/sync init` → Use `ari sync` for new projects
- `/sync validate` → Use `ari manifest validate` instead

## Common Commands

```bash
# Within knossos repo (has local rites)
/sync                        # Sync everything (rite + user)
/sync --scope=rite           # Sync only rite content
/sync --rite=hygiene         # Switch to hygiene rite

# Bootstrap NEW project (creates .claude/ if missing)
/sync --rite=10x-dev --source=knossos

# Cross-cutting mode (no rite, just base infrastructure)
/sync --source=knossos
```

## Reference

Full documentation: `.claude/skills/ecosystem-ref/INDEX.md`
