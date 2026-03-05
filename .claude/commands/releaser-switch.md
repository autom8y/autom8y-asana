---
name: releaser
description: "Switch to releaser rite (multi-repo release orchestration). Use when: user says /releaser, releasing SDKs or libraries, bumping consumers after publish, orchestrating cross-repo releases, monitoring CI after push, running PATCH/RELEASE/PLATFORM workflows. Triggers: /releaser, multi-repo release, publish SDK, bump consumers, release orchestration, platform release."
argument-hint: "[--overwrite-diverged] [--dry-run] [--keep-orphans]"
allowed-tools: Bash, Read
model: haiku
disable-model-invocation: true
context: fork
---

# /releaser - Switch to Multi-Repo Release Orchestration Rite

Switch to releaser, the multi-repo release orchestration engine. From committed code to published, CI-verified releases.

## Behavior

### 1. Invoke Rite Switch

Execute via Bash tool:

```bash
ari sync --rite releaser $ARGUMENTS
```

### 2. Display Pantheon

After successful switch, show the agent table:

| Agent | Role |
|-------|------|
| pythia | Coordinates release phases, gates complexity, manages DAG-branch failure halting |
| cartographer | Discovers repos, maps git state, identifies ecosystems and available commands |
| dependency-resolver | Builds cross-repo dependency DAG, detects version mismatches, calculates blast radius |
| release-planner | Creates phased execution plan with parallel groups, rollback boundaries, and CI estimates |
| release-executor | Executes the release plan — publishes, bumps versions, pushes, creates PRs |
| pipeline-monitor | Monitors CI pipelines, reports green/red matrix, diagnoses failures |

### 3. Update Session

Confirm `ari sync` output shows the correct active rite.

## Flags

| Flag | Description |
|------|-------------|
| `--overwrite-diverged` | Force regeneration of diverged files |
| `--dry-run` | Preview changes without applying |
| `--keep-orphans` | Preserve orphaned knossos files (default: auto-remove) |

## When to Use

- Releasing an SDK or library and bumping all downstream consumers
- Full platform release across 10+ repos with mixed ecosystems
- Single-repo push with CI monitoring (PATCH complexity)
- Any release requiring cross-repo dependency ordering

**Don't use for**: Deployment/infrastructure --> `/sre` | Code review before release --> `/review` | Architecture concerns --> `/arch` | General development --> `/10x-dev`

## Complexity Quick Reference

| Level | Scope | Phases |
|-------|-------|--------|
| PATCH | Single repo push + CI watch | recon → execution → verification |
| RELEASE | SDK publish + consumer bumps | All 5 phases |
| PLATFORM | Full platform, all repos | All 5 phases (extended scope) |

PATCH auto-escalates to RELEASE if cartographer detects downstream dependents.

## Reference

Full methodology: `releaser-ref` skill
