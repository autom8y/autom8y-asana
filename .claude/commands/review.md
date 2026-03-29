---
name: review
description: "Switch to review rite (language-agnostic code review). Use when: user says /review, wants codebase health check, triage unknown codebase, code audit, generate health report card, assess code quality across any language. Triggers: /review, code review, health check, codebase audit, triage, code assessment."
argument-hint: "[--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: haiku
disable-model-invocation: true
context: fork
---

# /review - Switch to Code Review Rite

Switch to review, the language-agnostic codebase health assessment rite. Read-only forensic investigation.

## Behavior

### 1. Invoke Rite Switch

Execute via Bash tool:

```bash
ari sync --rite review $ARGUMENTS
```

### 2. Display Pantheon

After successful switch, show the agent table:

| Agent | Role |
|-------|------|
| signal-sifter | Reads codebase structure and sifts signal from noise using structural heuristics |
| pattern-profiler | Connects dots across signals, assigns severity and health grades (FULL only) |
| case-reporter | Writes the definitive case file with health report card and cross-rite routing |

### 3. Update Session

Confirm `ari sync` output shows the correct active rite.

## Flags

| Flag | Description |
|------|-------------|
| `--overwrite-diverged` | Force regeneration of diverged files |
| `--dry-run` | Preview changes without applying |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |

## When to Use

- First contact with an unknown codebase (generalist triage)
- Language-agnostic health assessment with A-F grading
- Pre-engagement diagnostic before deeper specialist rite work
- Codebase audit producing cross-rite routing recommendations
- Quick structural triage (QUICK mode) or full assessment (FULL mode)

**Don't use for**: Security audits --> `/security` | AI code detection --> `/slop-chop` | Code cleanup --> `/hygiene` | Debt planning --> `/debt` | Architecture analysis --> `/arch`

**Read-only**: Review observes and reports. It never modifies the target codebase.

## Reference

Full documentation: `review-ref` skill
