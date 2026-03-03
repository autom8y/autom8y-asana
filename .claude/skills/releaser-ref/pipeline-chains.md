---
name: pipeline-chains
description: "Pipeline Chain Model for the releaser rite. Defines chain type taxonomy (trigger_chain, dispatch_chain, deployment_chain), terminal states, and chain-aware verdict rules. Read when: reasoning about multi-stage CI workflows, determining pipeline verdicts with deployment chains, or distinguishing resolved vs unresolved chain states."
---

# Pipeline Chain Model

A **pipeline chain** is a sequence of automated workflows triggered by a code push, where each stage's completion triggers the next. Releases are not verified until the terminal stage resolves.

## Chain Type Taxonomy

| Chain Type | Scope | Example |
|------------|-------|---------|
| trigger_chain | Within a single repo, one workflow triggers another | Test suite triggers packaging workflow |
| dispatch_chain | Across repos, one repo dispatches work to another | Source repo dispatches to infrastructure repo |
| deployment_chain | Any chain whose terminal stage performs deployment | Build + deploy + health check sequence |

A single release may involve multiple chain types composed together (e.g., trigger_chain feeding into dispatch_chain feeding into deployment_chain).

## Terminal States

A chain is **resolved** when its terminal stage reaches a conclusive outcome:

| Terminal State | Meaning |
|----------------|---------|
| succeeded | All stages completed successfully, including health checks |
| failed | Any stage failed; chain cannot proceed |
| timed_out | Terminal stage did not resolve within the configured timeout |
| dispatch_not_received | Cross-repo dispatch was expected but never arrived (after retry exhaustion) |

A chain is **unresolved** while any non-terminal stage is still in progress or pending.

## Chain-Aware Verdict Rules

| Condition | Verdict |
|-----------|---------|
| All CI green AND all chains resolved as succeeded AND all deployments healthy | PASS |
| All CI green AND no chains discovered (flat pipeline) | PASS |
| Any CI red | FAIL |
| All CI green AND any chain failed | FAIL |
| All CI green AND any chain timed out or dispatch not received | PARTIAL |
| Monitoring still in progress | IN_PROGRESS |

Key rule: green CI with a failed deployment chain is a FAIL, not a PASS. The chain extends the definition of "pipeline success" beyond the initial CI run.
