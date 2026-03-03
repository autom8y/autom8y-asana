---
name: failure-halting
description: "Failure Halting Protocol and DAG-Branch Semantics for the releaser rite. Defines how release-executor handles failures by halting downstream dependents while continuing independent branches. Read when: reasoning about partial release failures, skipping downstream repos after a dependency publish failure, or understanding DAG-branch halting behavior."
---

# Failure Halting Protocol (DAG-Branch Semantics)

When release-executor reports a failure on repo X:
1. Identify X in the dependency graph
2. Find all repos that depend on X (direct + transitive consumers)
3. Mark all downstream repos as `skipped` in the execution ledger
4. Continue executing repos in branches with no dependency on X
5. Pipeline-monitor only monitors repos that were actually pushed (not skipped)

Goal: maximize successful releases while preventing cascading failures from unpublished dependencies.
