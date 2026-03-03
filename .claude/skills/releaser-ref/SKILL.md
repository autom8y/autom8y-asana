---
name: releaser-ref
description: "Releaser rite methodology reference. Use when: implementing release agents, orchestrating multi-repo releases, understanding artifact chain, checking complexity levels, detecting package ecosystems, applying DAG-branch failure halting, routing CI failures to peer rites. Triggers: release orchestration, artifact chain, ecosystem detection, publish order, dependency graph, DAG-branch halting, PATCH escalation, release complexity, cross-rite routing, release anti-patterns. Companion files available for pipeline chains, ecosystem detection, failure halting, and cross-rite routing detail."
---

# Releaser Methodology Reference

## Artifact Chain

```
PATCH:    cartographer -> platform-state-map.{yaml,md}
                       -> release-executor -> execution-ledger.{yaml,md}
                       -> pipeline-monitor -> verification-report.{yaml,md}

RELEASE:  cartographer -> platform-state-map.{yaml,md}
       -> dependency-resolver -> dependency-graph.{yaml,md}
       -> release-planner -> release-plan.{yaml,md}
       -> release-executor -> execution-ledger.{yaml,md}
       -> pipeline-monitor -> verification-report.{yaml,md}

PLATFORM: Same as RELEASE, full-scope (all matching repos, extended CI timeout)
```

All artifacts written to `.sos/wip/release/`. YAML consumed by downstream agents; MD for human review.
Downstream agents consume YAML only. Never parse the MD summaries programmatically.

## Complexity Levels

| Level | Phases | Use For |
|-------|--------|---------|
| PATCH | recon → execution → verification | Single repo push + CI watch |
| RELEASE | All 5 phases | SDK publish + consumer version bumps |
| PLATFORM | All 5 phases, full scope | Full platform release, all matching repos |

PATCH auto-escalates to RELEASE if cartographer finds `has_dependents: true`.

## Companion Files

For detailed reference, agents should Read the relevant companion:

| Topic | Path |
|-------|------|
| Pipeline Chain Model | `rites/releaser/mena/releaser-ref/pipeline-chains.md` |
| Ecosystem Detection | `rites/releaser/mena/releaser-ref/ecosystem-detection.md` |
| Failure Halting Protocol | `rites/releaser/mena/releaser-ref/failure-halting.md` |
| Cross-Rite Routing | `rites/releaser/mena/releaser-ref/cross-rite-routing.md` |
