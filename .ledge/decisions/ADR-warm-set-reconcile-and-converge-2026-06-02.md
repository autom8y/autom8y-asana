---
type: decision
status: proposed
id: ADR-warm-set-reconcile-and-converge
date: 2026-06-02
author: architect (10x-dev)
initiative: receiver-bulk-fanout-integration-readiness
consumer_visible: false
related:
  - ADR-honest-empty-200-serving-2026-06-02
  - ADR-build-gap-commission-pauseabusiness-2026-06-02
tdd: .sos/wip/thermia/TDD-receiver-warm-convergence-2026-06-02.md
---

# ADR — Warm-set reconciliation 23→34 + warmer convergence

## Status

PROPOSED. Interior (warmer / registry / S3); non-consumer-visible (the 34 is consumer-derived, so
reconciliation is consumer-aligned by construction). Closes CF-1/CF-2/CF-3/CF-4 from the SRE
verdict.

## Context (all source-verified, canonical `src/`)

- `bulk_prematerialization_keys()` enumerates `list(_REGISTRY.values())` × `("project","section")`
  = **23 GIDs × 2 = 46 keys** (`core/project_registry.py:194-225`; `_REGISTRY` has exactly 23
  entries, `:73-99`). The consumer enumerates **34** `Project` subclasses
  (`/Users/tomtenuta/Code/autom8/.../refresh_frames.py:9-18,92`). 11 absent; 3 frameless.
- The registry docstring at `project_registry.py:189-192` FALSELY claims the 23 keys are "the only
  width-driving keys the receiver serves cold." REFUTED against consumer source.
- The warmer processes keys in `_REGISTRY`-declaration order (`cache_warmer.py:338`), entity
  projects first (`:74-88`), pipelines last (`:89-98`); on timeout it checkpoints the pending tail
  (`:339-358`). The 12 heavy pipeline/holder GIDs (DNA ~30k, SALES) are warmed LAST, amputated
  FIRST.
- Convergence estimate `≤162s for 46 keys` (`cache_warmer.py:224`) is ~5× wrong (times out at
  23/46 in 900s).
- Self-invoke fires ONLY in the clean-timeout branch gated by `_should_exit_early(context)`
  (`cache_warmer.py:339`; `timeout.py:32-54,104-113`). An OOM-kill terminates the process before
  that branch → silent strand until the next 4-hourly schedule.
- reserved_concurrency=1: the async `InvocationType="Event"` self-invoke survives only by
  side-effect (parent exits, frees the slot, child lands via async-retry).

## Decision

### A — Reconcile the warm set to 34 (CF-3)

Make the warm set == the consumer's 34-GID set, set-diff = ∅. Add the 11 missing GIDs to
`_REGISTRY` (the single source of truth `bulk_prematerialization_keys` enumerates), including
Commission / PauseABusinessUnit / CustomerHealth. Rewrite the false docstring (`:189-192`) to state
the set is consumer-derived and must equal the `refresh_frames` subclass set. VG-004 static ⊇ live
correspondence must hold on a LIVE probe (re-gate acceptance) — verify against live subclasses, not
a stale copy. Confirm the 11 additions are pure-additive warm targets that do not change resolution
behavior for the existing 23 (`_REGISTRY` is also the resolution/lookup registry — one-way-door
check).

### B — Converge the warmer (CF-1/CF-2/CF-4)

1. **Heaviest-first ordering** (CF-2): order the warm set by descending build-cost (row-count) so a
   partial warm keeps the heavy GIDs (the expensive cold-503s) and defers only the cheap tail.
   Implement as explicit cost-ordering in/around `bulk_prematerialization_keys` — do not rely on
   declaration order for priority.
2. **Per-link key-budget chunking + memory sizing** (CF-1): cap each invocation at a key budget
   sized to complete well under 900s AND under the memory ceiling, then self-invoke for the
   remainder (reusing the existing checkpoint/self-invoke machinery, `cache_warmer.py:221-222`;
   `timeout.py`). Raise warmer Lambda memory so a single heavy GID cannot OOM a link at 1024MB.
   Coordinate the memory value with (do not collide with) the ECS cpu=1024 deploy work.
3. **OOM-resilience** (CF-1): the robust fix is to PREVENT OOM (item 2) so the OOM-skip-self-invoke
   path is never exercised — you cannot reliably run a finalizer after a Lambda OOM-kill.
   Defense-in-depth fallback (flag if item 2 alone is judged insufficient): an external
   checkpoint-reaper / shorter schedule that re-invokes a stranded non-cleared checkpoint. Do NOT
   rely on an in-process finalizer surviving an OOM-kill.
4. **Honest coverage** (CF-4): compute `coverage` from the reconciled 34-denominator and ASSERT it
   from telemetry. Acceptance = `coverage=1.0 + checkpoint_cleared` observed in warmer telemetry,
   not inferred from an assumed precondition.
5. **reserved_concurrency=1**: keep it (it is the warmer singleflight guarantee — widening
   re-opens thundering-herd). Make the chain robust via 2+3 so correctness does not depend on the
   free-slot-race. If chunking pushes link count high enough that the race becomes a latency
   problem, flag warmer-concurrency sizing as a follow-up; default is fewer/fatter/memory-sized
   links over many fragile thin ones.

## Alternatives considered

1. **Widen reserved_concurrency > 1 to parallelize the warm.** Rejected — it re-opens the
   bulk-fan-out thundering-herd that the Semaphore(4) + singleflight design specifically closes
   (resilience axis, RESOLVED); a parallel warmer would re-introduce the exact load the receiver
   was just hardened against. Vertical-within-a-link (memory + chunking) beats horizontal warmer
   concurrency.
2. **Keep declaration order; just raise the timeout / memory.** Rejected — the Lambda 900s budget
   is a hard ceiling (cannot be raised past 900s), and at 68 keys even more time is needed; ordering
   determines WHICH GIDs survive a partial warm, so heaviest-first is strictly better regardless of
   budget. Raising memory alone does not fix the amputation of the heavy tail.
3. **Move warming out of Lambda into the long-lived ECS task.** Rejected for THIS sprint — a larger
   architectural change (ownership, scheduling, the deploy-order discipline) that the verdict did
   not scope and that the bounded fix (chunking + ordering + sizing) makes unnecessary. Could be a
   future moonshot if the warmer continues to strain, but out of scope here.
4. **In-process atexit/signal finalizer for the OOM-skip.** Rejected — a SIGKILL OOM-kill does not
   run Python finalizers reliably; depending on it is the bug, not the fix. Prevent OOM instead.

Each alternative is a genuinely different axis (concurrency model, budget lever, execution
substrate, recovery mechanism) — not a strawman. Selected: A + B(1-5).

## Consequences

- Warm set covers all 34 consumer GIDs; the 11-absent cold-503 surface closes; Commission's
  build-gap closes as a side-effect (ADR-2).
- The warmer converges to TRUE `coverage=1.0 + checkpoint_cleared` over 34×2=68 keys within budget,
  heaviest-first, no silent OOM strand.
- The FALSE-GREEN coverage gate (CF-4) is replaced by a telemetry-asserted value.
- The false docstring is corrected (a discoverability + correctness fix).

## Reversibility

Two-way door — registry additions are additive dict entries; ordering/chunking/sizing are tunable
config + code; reserved_concurrency unchanged. No irreversible state introduced.
