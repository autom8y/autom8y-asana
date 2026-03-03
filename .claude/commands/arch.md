---
name: arch
description: Quick switch to arch (multi-repo architecture analysis)
argument-hint: "[--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: haiku
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Switch to the arch rite and display the pantheon. $ARGUMENTS

## Behavior

1. Execute: `ari sync --rite arch $ARGUMENTS`
2. Display the pantheon output from ari (agents and their roles)
3. If SESSION_CONTEXT exists, update `active_rite` to `arch`

After the switch, display this condensed overview:

```
ARCH - Multi-Repo Architecture Analysis
========================================

Read-only analysis pipeline for multi-repo platform architecture.

AGENTS (4):
  Topology Cartographer  - Service discovery, tech stack inventory, API surface mapping
  Dependency Analyst     - Cross-repo dependency tracing, coupling analysis
  Structure Evaluator    - Anti-pattern detection, boundary assessment, SPOF identification
  Remediation Planner    - Ranked recommendations, cross-rite referrals, unknowns registry

COMPLEXITY LEVELS:
  SURVEY    - 30,000ft snapshot (discovery only)
  ANALYSIS  - Full pipeline (all 4 phases)
  DEEP-DIVE - ANALYSIS + coupling hotspots, philosophy extraction, migration roadmap

WORKFLOW: discovery -> synthesis -> evaluation -> remediation

Full docs: rites/arch/orchestrator.yaml
```

## Flags

| Flag | Description |
|------|-------------|
| `--overwrite-diverged` | Force regeneration of diverged files |
| `--dry-run` | Preview changes without applying |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |

## When to Use

- Analyzing architecture across multiple repositories
- Mapping service topology and dependencies
- Evaluating structural health and identifying anti-patterns
- Planning architectural remediation and generating cross-rite referrals

## Reference

Full documentation: See arch rite orchestrator (knossos-internal, not materialized to satellites)
