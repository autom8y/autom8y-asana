---
type: spec
artifact_type: ADR
status: accepted
adr_number: 003
adr_id: ADR-003
title: MemoryTier post-force-warm staleness window
authored_by: thermia.potnia (P5a orchestration)
authored_on: 2026-04-27
session_id: session-20260427-185944-cde32d7b
parent_initiative: verify-active-mrr-provenance
initiative_slug: cache-freshness-procession-2026-04-27
schema_version: 1
worktree: .worktrees/thermia-cache-procession/
branch: thermia/cache-freshness-procession-2026-04-27
companion_specs:
  - .ledge/specs/cache-freshness-architecture.tdd.md
  - .ledge/specs/cache-freshness-capacity-spec.md
  - .ledge/specs/cache-freshness-observability.md
companion_handoff: .ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md
raised_from_latent_decision: LD-P2-3
---

# ADR-003 — MemoryTier post-force-warm staleness window

## Status

**Accepted** — 2026-04-27. Composes with the P2 architecture TDD §4
force-warm design and §6 XFetch refresh-ahead augmentation. Promoted from
latent decision LD-P2-3 (RAISE-TO-ADR per PT-A2 verdict).

## Context

The cache-freshness procession's P2 architecture
(`.ledge/specs/cache-freshness-architecture.tdd.md` §4 force-warm design,
§3 multi-level hierarchy) declares two cache levels for the DataFrame
read path:

- **L1**: `DataFrameCache` `MemoryTier` — in-process Polars DataFrame cache,
  per-ECS-process scope, populated via SWR rebuild from L2.
  Anchor: `src/autom8_asana/cache/integration/dataframe_cache.py:1-33`,
  SWR rebuild callback at `src/autom8_asana/cache/dataframe/factory.py:40-117`.

- **L2**: `ProgressiveTier` — S3 parquet cold tier at
  `s3://autom8-s3/dataframes/{project_gid}/sections/`. Cross-process,
  durable. Anchor: `src/autom8_asana/cache/dataframe/tiers/progressive.py:41-60`.

The PRD NG4 force-warm CLI affordance (designed in P2 §4 of the
architecture TDD) invokes the `cache_warmer` Lambda, which writes refreshed
parquets to L2. P2 §3 explicitly notes (lines 252-265 of the TDD):

> Force-warm CLI affordance (L2 warmed by operator demand): Same as scheduled
> Lambda warm — L2 updated, L1 NOT automatically invalidated. Force-warm
> completion does NOT flush the MemoryTier. The staleness window for L1 post
> force-warm is bounded by the SWR rebuild trigger threshold.

This means: an ECS process serving `active_mrr` from `MemoryTier` will not
see freshened parquet data until its SWR rebuild trigger fires (per
`FreshnessPolicy.approaching_threshold = 0.75` at
`src/autom8_asana/cache/policies/freshness_policy.py:56`), even though the
operator paid for a synchronous Lambda warm.

This composes with the **AP-3 named risk** documented in P2 §7 of the
architecture TDD: the `MutationInvalidator` at
`src/autom8_asana/cache/integration/mutation_invalidator.py:36`
(`_TASK_ENTRY_TYPES = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]`)
excludes the DataFrame parquet tier from task-mutation invalidation. AP-3 is
an upstream eventual-consistency window; this ADR addresses a downstream
window introduced by force-warm asymmetry.

This composes with the **XFetch refresh-ahead augmentation** described in
P2 §6 of the architecture TDD (CACHE:SRC-001, Vattani et al. 2015,
[STRONG]): probabilistic early refresh begins before TTL expiry. XFetch is
orthogonal to force-warm — it triggers from L1 read events; force-warm
triggers from operator CLI events.

The latent decision (LD-P2-3) is: when the operator force-warms L2, what
should happen to L1?

## Decision

**HYBRID** — invalidate L1 `MemoryTier` on force-warm completion **when
`--wait` flag is set** (synchronous mode); accept SWR rebuild lag for
default async mode (`--wait` absent).

### Behavioral contract

| `--force-warm` mode | L1 (MemoryTier) post-warm behavior |
|---|---|
| `--force-warm --wait` (sync) | Invalidate L1 entry for affected key(s); next read repopulates from freshly-warmed L2. Operator sees fresh data immediately. |
| `--force-warm` (default async, fire-and-forget) | L1 not invalidated. Next SWR rebuild trigger (per `approaching_threshold = 0.75`) populates L1 from L2. Operator must re-invoke or wait. |

### Implementation guidance for P6 (10x-dev)

The `--wait` synchronous path SHOULD:

1. After Lambda response confirms success (`InvocationType="RequestResponse"`,
   `body.success=true`), invoke a MemoryTier invalidation hook for the
   affected `entity_type:project_gid` key(s). Anchor:
   `src/autom8_asana/cache/integration/dataframe_cache.py` (the cache
   owner's invalidate API; engineer chooses exact method — `invalidate()`,
   `delete()`, or `evict()` per existing surface).
2. Emit `ForceWarmL1InvalidationCount` CloudWatch metric (lightweight; not
   load-bearing for SLO but observability-useful).
3. The next CLI read (or ECS-process read) for the affected key falls
   through L1 miss to L2, which now contains fresh parquet data.

The default async path is no-op for L1 (current behavior); the SWR rebuild
trigger naturally refreshes L1 within `(1 - approaching_threshold) *
entity_ttl` seconds.

## Alternatives considered

### REJECTED: Always invalidate L1 on force-warm (regardless of mode)

- Pro: simplest semantic — force-warm always means "everything fresh".
- Con: The default async mode is fire-and-forget; the CLI returns
  immediately after Lambda accepts the invocation, BEFORE the warm
  completes. Invalidating L1 at that point would evict the entry while the
  Lambda is still warming L2 — the next L1 read would fall through to
  whatever L2 state existed at that moment (possibly the pre-warm parquet
  if the Lambda has not yet written), then cache the stale value back into
  L1. This produces a worse outcome than no invalidation.
- Con: Even if invalidation were deferred until after Lambda completion
  (synchronous), it would impose Lambda-warm latency (seconds to minutes)
  on every async invocation, defeating the async cost model.

### REJECTED: Never invalidate L1 (current default behavior)

- Pro: simplest implementation — no invalidation hook needed.
- Con: The `--wait` flag becomes semantically useless. The operator pays
  for a synchronous round-trip (waits seconds-to-minutes for Lambda
  completion) and STILL gets stale data from L1 on the next read. This
  contradicts the operator intent expressed by `--wait`: "I want
  certainty that the next read is fresh."
- Con: Probe-3 of P4 §7 in-anger probes
  (`.ledge/specs/cache-freshness-observability.md` Track B) cannot pass
  if L1 is never invalidated post force-warm — the post-warm freshness
  signal would still show stale data via L1 cache hits.

### REJECTED: Auto-detect ECS-vs-CLI process and invalidate accordingly

- Pro: would make L1 invalidation transparent based on caller context.
- Con: couples cache invalidation logic to runtime process detection
  (`os.environ.get("ECS_CONTAINER_METADATA_URI")` or equivalent) — an
  anti-pattern that conflates infrastructure detection with cache
  semantics. Difficult to test, fragile across deployment topologies.
- Con: does not address the cross-process case where one ECS instance
  invokes force-warm and a different ECS instance reads L1 — the
  detection cannot reach across processes.

### ACCEPTED: HYBRID per `--wait` flag (operator opt-in)

- Pro: makes `--wait` semantically meaningful — operator pays for sync
  round-trip, operator gets fresh data immediately.
- Pro: preserves the async cost model — default `--force-warm` returns
  immediately and incurs no extra invalidation work.
- Pro: testable — Probe-3 in-anger probe can be run with `--force-warm
  --wait` and assert post-warm L1 read returns fresh data.
- Pro: composable with both P2 §6 XFetch (orthogonal trigger) and P2 §7
  AP-3 (does not pretend to close AP-3; remains a documented window).
- Con: introduces flag-conditioned behavior. Mitigated by clear
  documentation in CLI help text and dossier §1 work item description.

## Consequences

### Positive

- `--wait` operators see fresh data immediately on the next read (the
  testable acceptance criterion is Probe-3 in
  `.ledge/specs/cache-freshness-observability.md` §7 Track B).
- Default async operators see fresh data when SWR rebuild fires per the
  capacity-spec TTL cadence
  (`.ledge/specs/cache-freshness-capacity-spec.md` §2.2 — ACTIVE class
  6h TTL, refresh budget every 4h).
- The XFetch augmentation (P2 §6) continues to operate independently —
  refresh-ahead from L1 reads triggers SWR rebuild before TTL expiry,
  orthogonal to force-warm.
- AP-3 remains explicitly documented (P2 §7) as an unresolved
  eventual-consistency window. This ADR does NOT silently close AP-3 —
  task-mutation still does not invalidate parquets; this ADR addresses a
  different gap (force-warm-vs-L1).

### Negative

- Two code paths for force-warm completion (sync invalidates L1; async
  does not). Implementation must test both paths.
- Cross-process invalidation is NOT addressed: if ECS process A invokes
  `--force-warm --wait` and ECS process B's MemoryTier holds a stale
  entry, process B is not affected by process A's invalidation. Process
  B's stale entry is bounded by its own SWR rebuild trigger threshold.
  This residual window is small at 14-section scale (per capacity-spec
  §3.1, working set ~0.91 MB) but is acknowledged.
- The ECS preload scenario (separate from CLI invocation) is not
  exercised by the `--wait` path — ECS preloads via SWR rebuild, not via
  CLI. ECS sees post-force-warm freshness only via its own SWR cycle.

### Composition with XFetch refresh-ahead (P2 §6)

XFetch triggers from L1 reads when `current_remaining <= -delta * beta *
ln(random())`. This triggers BEFORE entry expiry, probabilistically. After
a force-warm `--wait` invalidation:

- L1 entry is gone; next read is a miss; falls through to L2 (now fresh).
- XFetch trigger does not fire because there is no L1 entry to evaluate
  against.
- L1 is repopulated from L2 on the read; XFetch resumes its normal
  trigger cycle from the new L1 entry watermark.

In default async mode, force-warm does not interact with XFetch at all —
XFetch continues to trigger SWR rebuilds based on watermark age, which
naturally pulls fresh data from the freshly-warmed L2 parquet on the next
trigger event.

### Composition with AP-3 (P2 §7 named risk)

AP-3 is the gap where `MutationInvalidator` excludes the DataFrame parquet
tier (`mutation_invalidator.py:36`). When an Asana task moves between
sections via REST mutation:

- Task-entity cache entries (TASK, SUBTASKS, DETECTION) are invalidated.
- Parquet at L2 is NOT re-written.
- L1 MemoryTier serving the aggregate is NOT invalidated.

This ADR explicitly does NOT close AP-3. AP-3 requires either (a)
extending `_TASK_ENTRY_TYPES` to include the DataFrame entry type AND
adding a webhook-triggered Lambda invocation path, or (b) accepting the
Lambda warm cadence as the AP-3 staleness ceiling. Both options are out of
scope for the current operationalize procession (per heat-mapper §G3
"DEF-5: Event-driven re-warm — recommended follow-up procession").

The force-warm `--wait` path provides operator-accessible remediation for
AP-3 staleness: an operator who needs post-mutation freshness can invoke
`--force-warm --wait` and see fresh L1 + L2 data immediately. This is the
operational mitigation for AP-3, not an architectural fix.

## Anchors

- P2 §4 force-warm design:
  `.ledge/specs/cache-freshness-architecture.tdd.md:304-424`
- P2 §3 multi-level hierarchy + L1 staleness note:
  `.ledge/specs/cache-freshness-architecture.tdd.md:224-273`
- P2 §6 XFetch augmentation:
  `.ledge/specs/cache-freshness-architecture.tdd.md:516-585`
- P2 §7 AP-3 named risk:
  `.ledge/specs/cache-freshness-architecture.tdd.md:587-645`
- AP-3 source anchor:
  `src/autom8_asana/cache/integration/mutation_invalidator.py:36`
- L1 SWR rebuild callback:
  `src/autom8_asana/cache/dataframe/factory.py:40-117`
- L1 approaching_threshold constant:
  `src/autom8_asana/cache/policies/freshness_policy.py:56`
- L2 ProgressiveTier:
  `src/autom8_asana/cache/dataframe/tiers/progressive.py:41-60`
- DataFrameCache surface:
  `src/autom8_asana/cache/integration/dataframe_cache.py:1-33`
- Force-warm CLI implementation site (P6 work):
  `src/autom8_asana/metrics/__main__.py:160-241`
- P3 capacity-spec ACTIVE class TTL: 6h, refresh every 4h:
  `.ledge/specs/cache-freshness-capacity-spec.md:84-90`
- P4 Probe-3 acceptance criterion:
  `.ledge/specs/cache-freshness-observability.md:516-538`
- Heat-mapper DEF-5 (event-driven re-warm follow-up procession):
  `.sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md:460`

---

*Authored by thermia.potnia (P5a orchestration), thermia procession,
session-20260427-185944-cde32d7b, 2026-04-27. Branch
thermia/cache-freshness-procession-2026-04-27. Promoted from latent
decision LD-P2-3 per PT-A2 verdict (RAISE-TO-ADR).*
