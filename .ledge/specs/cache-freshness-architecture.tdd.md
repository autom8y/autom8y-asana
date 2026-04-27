---
type: spec
artifact_type: TDD
initiative_slug: cache-freshness-procession-2026-04-27
parent_initiative: verify-active-mrr-provenance
session_id: session-20260427-185944-cde32d7b
phase: design
status: draft
authored_by: systems-thermodynamicist
authored_on: 2026-04-27
worktree: .worktrees/thermia-cache-procession/
branch: thermia/cache-freshness-procession-2026-04-27
schema_version: 1
---

# Cache Architecture TDD — cache-freshness-procession-2026-04-27

## Architecture Overview

Three cache tiers exist in this system, each with a distinct access profile,
consistency requirement, and failure contract. This TDD addresses only the
layers carrying `active_mrr` freshness risk; the task-entity Redis/InMemory
tier is out of scope.

```
CLI consumer
     |
     v
[DataFrameCache MemoryTier]  ----SWR rebuild--> [Asana API via ProgressiveProjectBuilder]
     |
     v (miss / refresh-ahead trigger)
[ProgressiveTier — S3 parquet cold tier]
     |
     ^--- Lambda cache_warmer writes on schedule + on-demand (force-warm)

[FreshnessReport probe]  <-- independent list_objects_v2 read, no cache involvement
     |
     v
[CLI stderr / JSON envelope / exit-code matrix]
```

Layers in scope:

1. **S3 parquet cold tier** — `ProgressiveTier` reading `s3://autom8-s3/dataframes/{project_gid}/sections/`
2. **DataFrameCache MemoryTier** — in-process memory cache; SWR rebuild callback
3. **Freshness probe** — `FreshnessReport.from_s3_listing` read-only observability layer

Layer out of scope (passes 6-gate independently, no freshness issue):

- Task-entity Redis/InMemory cache — entity TTL managed by `StalenessCheckCoordinator` and `FreshnessPolicy`

---

## Layer Designs

### Layer 1: S3 Parquet Cold Tier (ProgressiveTier)

**Implementation anchor**: `src/autom8_asana/cache/dataframe/tiers/progressive.py:41-60`

#### Pattern

- **Selected**: Cache-aside (continuation)
- **Rationale**: The origin (Asana API full project traversal) is batch-heavy
  and compute-expensive. Lambda performs the write; CLI performs the read. This
  is a natural cache-aside topology: the application reads from S3; on a miss or
  on forced re-warm, the Lambda warmer writes the updated parquet. Changing this
  to read-through would require the CLI to own the warm path, which violates PRD
  C-4 (no `cache_warmer.py` modifications by 10x-dev) and would entangle the
  read path with the multi-entity sequential warm order managed by
  `cascade_warm_order()` at `src/autom8_asana/lambda_handlers/cache_warmer.py:398`.
- **Trade-off acknowledged**: Cache-aside introduces a visible window between a
  Lambda warm completing and the CLI reading the new parquet. This window is the
  staleness budget; it is explicitly tolerated per DEF-3 (internal-only eventual
  consistency is acceptable). The FreshnessReport makes the window observable.

#### Consistency Model

- **Selected**: Eventual
- **CAP position**: AP (Availability + Partition tolerance)
- **Staleness budget**: 6h default for ACTIVE-classifier sections (PRD G2);
  configurable via `--staleness-threshold`
- **Rationale**: Per CACHE:SRC-003 (Brewer CAP, STRONG): during a network
  partition between Lambda writer and S3, or between CLI reader and S3, the
  system must choose. AP is correct here: the CLI should return the last-known
  parquet value with a freshness WARNING rather than refusing to answer. The
  metric is internal/operational (DEF-3 confirmed); serving a 6h-old figure
  with a visible freshness signal is vastly preferable to serving no figure at
  all. Per CACHE:SRC-004 (Lamport): linearizability is not required. The
  `FreshnessReport.stale` predicate is the enforcement gate when
  `--strict` is passed.
- **Consumer observations per state**:
  - **(a) Cache hit (parquet present, fresh)**: CLI reads parquet, computes
    metric, emits freshness lines with `stale=False`. Exit 0.
  - **(b) Cache miss (no parquet at prefix)**: `load_project_dataframe` raises
    `ValueError`/`FileNotFoundError`; CLI exits 1 per existing handler at
    `src/autom8_asana/metrics/__main__.py:239`. FreshnessReport returns sentinel
    with `parquet_count=0`; CLI exits 1 per `src/autom8_asana/metrics/__main__.py:299-303`.
  - **(c) Stale data (parquet present, max_age > threshold)**: Data served.
    `FreshnessReport.stale = True`. WARNING emitted to stderr. Default mode
    exits 0; `--strict` exits 1.
  - **(d) Post-write-during-warm**: While Lambda is actively warming a section,
    the parquet at that section key reflects the pre-warm state. The CLI
    reads the pre-warm parquet. No lock or coordination mechanism exists
    between Lambda write and CLI read — this is an accepted eventual consistency
    window. The in-progress warm will complete and the next CLI invocation
    will see the new parquet. A force-warm invocation that races an in-progress
    scheduled warm is deduplicated via `DataFrameCacheCoalescer`
    (see Force-Warm section below).

#### Failure Mode Design

| Scenario | Behavior | Rationale |
|---|---|---|
| Cache unavailable (S3 returns ClientError) | Fail-open: FreshnessError surfaces via `src/autom8_asana/metrics/freshness.py:158-182`; CLI emits AC-4.x stderr line and exits 1. Data load path separately fails at `load_project_dataframe` with botocore traceback (MINOR-OBS-2 — see below). | Internal operator tool; a hard error is more actionable than serving nothing. Exit 1 is correct. |
| Origin unavailable (Asana API down during warm) | Fail-open stale: existing parquet remains in S3. Lambda warmer emits `WarmFailure` metric at `src/autom8_asana/lambda_handlers/cache_warmer.py:501-504`. Checkpoint-based resume at `src/autom8_asana/lambda_handlers/cache_warmer.py:399-425` continues on next invocation. CLI reads stale parquet with WARNING. | Stale data + visible signal is better than no data. The DMS heartbeat at `src/autom8_asana/lambda_handlers/cache_warmer.py:843-845` fires if warm does not complete within 24h. |
| Network partition (CLI to S3) | Fail-open bypass not possible for data load (miss = error). For freshness probe: FreshnessError.KIND_NETWORK emitted; CLI exits 1 per AC-4.3/AC-4.4. | Partition during data load is indistinguishable from S3 unavailability. Exit 1 is correct. |

**MINOR-OBS-2 note**: The exception handler at `src/autom8_asana/metrics/__main__.py:239`
catches only `(ValueError, FileNotFoundError)`. A `botocore.exceptions.ClientError`
with code `NoSuchBucket` raised by `load_project_dataframe` will surface as a raw
traceback. This is a pre-existing UX gap. The force-warm CLI affordance design
(Section 4 of this TDD) must validate `ASANA_CACHE_S3_BUCKET` before invoking
Lambda to prevent the bucket-typo case from reaching the warmer. The upstream
handler fix (`__main__.py:239` to also catch `ClientError`) is flagged to P6
(10x-dev re-handoff) for implementation; it is out of scope for this
architecture TDD.

---

### Layer 2: DataFrameCache MemoryTier

**Implementation anchor**: `src/autom8_asana/cache/integration/dataframe_cache.py:1-33`
(SWR rebuild callback wired at `src/autom8_asana/cache/dataframe/factory.py:40-80`)

#### Pattern

- **Selected**: Cache-aside (primary) + Refresh-ahead augmentation (viable
  augmentation, CACHE:SRC-001 XFetch, STRONG grade) — see Section 6
- **Rationale**: The MemoryTier is an in-process cache wrapping the ProgressiveTier.
  The SWR (stale-while-revalidate) rebuild callback at
  `src/autom8_asana/cache/dataframe/factory.py:40-117` already implements a
  form of background refresh: when a MemoryTier entry is approaching stale (per
  `FreshnessPolicy.approaching_threshold = 0.75` at
  `src/autom8_asana/cache/policies/freshness_policy.py:56`), the SWR callback
  triggers a `ProgressiveProjectBuilder` rebuild asynchronously. This is
  cache-aside in shape (application controls the refresh trigger) with a
  refresh-ahead variant possible via XFetch probabilistic early refresh.
  No pattern change from current is required; the XFetch augmentation is additive.
- **Trade-off acknowledged**: The MemoryTier is process-scoped. ECS container
  restarts clear the in-memory tier; the next warm loads from the ProgressiveTier
  (S3). This is acceptable: the MemoryTier is a latency optimization, not a
  durability tier.

#### Consistency Model

- **Selected**: Eventual (same as ProgressiveTier cold tier)
- **CAP position**: AP
- **Staleness budget**: Bounded by `FreshnessPolicy.approaching_threshold` relative
  to the ProgressiveTier's parquet age. The MemoryTier cannot be fresher than the
  ProgressiveTier it reads from; at most it is as fresh as the last S3 parquet write.
- **Rationale**: The MemoryTier is a read acceleration layer. It does not change
  the fundamental consistency model; it inherits the eventual consistency of the
  ProgressiveTier. No linearizability requirement exists for this layer.
- **Consumer observations per state**:
  - **(a) Cache hit**: MemoryTier returns DataFrame from in-process memory. No S3 call.
  - **(b) Cache miss**: Falls through to ProgressiveTier (S3 read). On miss at
    ProgressiveTier, falls through to error per Layer 1 miss behavior.
  - **(c) Stale data**: MemoryTier entry with watermark below
    `approaching_threshold` triggers SWR background rebuild at
    `src/autom8_asana/cache/dataframe/factory.py:40-117`. Stale entry served
    while rebuild proceeds.
  - **(d) Post-write-during-warm**: If a force-warm Lambda invocation completes
    and writes a new parquet to S3, the MemoryTier is NOT automatically
    invalidated. The in-memory entry will reflect the pre-warm state until the
    SWR rebuild triggers or the process restarts. This is the accepted
    eventual consistency window at this layer.

#### Failure Mode Design

| Scenario | Behavior | Rationale |
|---|---|---|
| MemoryTier unavailable (process OOM / eviction) | Fail-open bypass: MemoryTier miss falls through to ProgressiveTier read. No error surfaced unless ProgressiveTier also fails. | In-process cache loss is transparent to the CLI consumer. |
| Origin (Asana API) unavailable during SWR rebuild | Fail-open stale: SWR callback catches the exception at `src/autom8_asana/cache/dataframe/factory.py:118` and logs; the stale MemoryTier entry continues to serve. | Serving a stale metric with a visible freshness WARNING is better than surfacing an Asana API error to the CLI consumer. |
| Network partition (ECS to S3) during SWR rebuild | Fail-open stale: same as origin unavailable; rebuild fails, stale entry serves. FreshnessReport probe independently detects the partition via S3 error and surfaces FreshnessError. | Same rationale. |

---

### Layer 3: Freshness Probe (FreshnessReport)

**Implementation anchor**: `src/autom8_asana/metrics/freshness.py:98-214`

#### Pattern

- **Selected**: Read-through (read-only observability; no cache involvement)
- **Rationale**: The FreshnessReport is not a cache layer; it is a monitoring
  probe that reads S3 `LastModified` metadata via `list_objects_v2` paginator.
  It has no write path. Pattern classification as "read-through" describes the
  probe's relationship to S3, not a cache pattern per se. No pattern change
  is required or applicable.
- **Trade-off acknowledged**: The probe adds one S3 API call per CLI invocation
  (~100-300ms; SM-2 budget confirmed in TDD §2.3). This is a deliberate
  trade-off for explicit freshness visibility.

#### Consistency Model

- **Selected**: Eventual (same S3 consistency model as the data layer)
- **CAP position**: AP
- **Rationale**: The freshness probe reads `LastModified` from the S3 listing,
  which reflects the last-committed parquet write. S3 provides strong
  read-after-write consistency for new objects (since 2020), so the probe
  accurately reflects the most recent write for a given parquet key. The
  probe does not coordinate with the MemoryTier; it reads S3 directly.

#### Failure Mode Design

| Scenario | Behavior | Rationale |
|---|---|---|
| S3 listing fails (auth/network/not-found) | Fail-closed: FreshnessError raised; CLI emits AC-4.x stderr line and exits 1 regardless of --strict per TDD §3.5 conditions 5-6. | A freshness probe failure means the operator cannot assess data currency. Serving the metric without freshness signal defeats the purpose of ADR-001. Exit 1 is mandatory. |
| S3 returns empty prefix (parquet_count == 0) | Fail-closed: sentinel report emitted; CLI exits 1 per `src/autom8_asana/metrics/__main__.py:298-303`. | No parquets means the cache is unwarmed. This is a cache miss, not a staleness condition. |
| Probe races an in-progress warm | No special handling: probe reads whatever `LastModified` S3 reports at probe time. A warm in progress will write the new parquet and the next probe invocation will observe the updated mtime. | S3's read-after-write consistency guarantees the probe observes the completed write on the next call. No coordination mechanism is needed. |

---

## Multi-Level Hierarchy

Three levels exist in the cache hierarchy for the DataFrame path:

| Level | Name | Scope | Population | Eviction |
|---|---|---|---|---|
| L1 | DataFrameCache MemoryTier | In-process | SWR rebuild from L2 | Process restart, eviction-per-capacity |
| L2 | ProgressiveTier (S3 parquet) | Cross-process | Lambda cache_warmer writes | No TTL-based eviction (cadence-scheduled overwrite); [DEFER-POST-P3: P3 capacity-engineer designs TTL eviction policy] |
| L3 | Asana API (origin) | External | On-demand | N/A (origin) |

### Inclusion policy

**Non-inclusive (exclusive by propagation)**: L1 reads from L2 on miss; L2 reads
from L3 (via Lambda warm) on miss. Each level holds the same logical data at
different freshness. There is no explicit inclusion invariant (where L2 always
contains everything in L1) — L1 is a subset of L2 at any point in time.

### Size relationship

L1 is bounded by the number of active project_gid keys loaded into the ECS
process. L2 is bounded by the number of Asana sections (14 at handoff time,
bounded by section count in the offer project). L2 >= L1 by design.

[DEFER-POST-P3: Exact size policy and per-level TTL targets are P3 capacity-engineer
domain per dispatch discipline constraints. This TDD declares the structural
relationships only.]

### Consistency propagation (cross-level invalidation flow)

1. **Lambda warm completes** (writes new parquet to L2): L1 MemoryTier is NOT
   automatically invalidated. The stale L1 entry serves until its SWR rebuild
   trigger fires (when `watermark < approaching_threshold * entity_ttl`).
2. **SWR rebuild trigger** (L1 entry approaches stale): Background rebuild reads
   from L3 (Asana API) via `ProgressiveProjectBuilder` and writes to both L2
   (S3 parquet via `SectionPersistence.write_final_artifacts_async`) and L1
   (MemoryTier via `cache.put_async` at
   `src/autom8_asana/cache/dataframe/factory.py:101-106`). This is the only
   path where L1 and L2 are updated atomically from the same rebuild event.
3. **Force-warm CLI affordance** (L2 warmed by operator demand): Same as scheduled
   Lambda warm — L2 updated, L1 NOT automatically invalidated. Force-warm
   completion does NOT flush the MemoryTier. The staleness window for L1 post
   force-warm is bounded by the SWR rebuild trigger threshold.

**Invisible invalidation chain risk**: The AP-3 gap (MutationInvalidator excludes
DataFrame parquet tier) means that an Asana task mutation (e.g., section move)
invalidates L1's task-entity entries but NOT the L2 parquet that contains the
section-level aggregate. The financial aggregate `active_mrr` may serve a stale
value reflecting the pre-mutation section assignment until the next scheduled
Lambda warm or force-warm. This gap is documented in Section 7 of this TDD.

---

## Invalidation Strategy

### Per-layer

| Layer | Strategy | Details |
|---|---|---|
| L2 (S3 parquet) | Scheduled-overwrite (no explicit TTL eviction) | Lambda warm overwrites parquet keys on cadence. No stale-entry eviction exists; old parquets age indefinitely if the warmer stops. [DEFER-POST-P3: P3 designs per-section TTL targets and whether staleness eviction is needed.] |
| L1 (MemoryTier) | Watermark-based SWR | `FreshnessPolicy.approaching_threshold = 0.75` triggers background rebuild at `src/autom8_asana/cache/policies/freshness_policy.py:56`. Hard eviction on process restart. |
| L3 (origin) | N/A | Asana API is the origin; no invalidation applies. |

### Cross-layer

- **L2 -> L1**: No push invalidation. L1 discovers L2 updates on next SWR rebuild
  trigger cycle.
- **L1 -> L2**: On SWR rebuild success, both L1 and L2 are updated atomically via
  `src/autom8_asana/cache/dataframe/factory.py:101-106`. This is the intended
  write path for the ECS preload scenario.

### Invisible invalidation chain risk

The `MutationInvalidator` at `src/autom8_asana/cache/integration/mutation_invalidator.py:36`
covers `_TASK_ENTRY_TYPES = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]`
but excludes the DataFrame parquet tier. An Asana task mutation does not trigger
a parquet re-write. The staleness window for the aggregate is bounded by the
Lambda warm cadence. This is AP-3; full documentation in Section 7.

---

## Section 4: Force-Warm CLI Affordance Architecture (NG4 discharge)

### Invocation pattern

```
python -m autom8_asana.metrics --force-warm [--wait] [--entity-types TYPES]
```

**Decision: flag, not subcommand**. The force-warm affordance is additive to the
existing metrics CLI at `src/autom8_asana/metrics/__main__.py`. A `--force-warm`
flag integrates naturally with the existing argparse structure (flags at line 160+)
and avoids introducing a subcommand hierarchy into a CLI that does not currently
use one. If the CLI grows to require subcommands (e.g., for multiple verb-style
operations), this is a revisit point but is not warranted now.

**Alternative considered (subcommand)**: `python -m autom8_asana.metrics force-warm`.
Rejected: requires restructuring the entire argparse tree; no other subcommands
exist; the flag form is simpler.

**Behavior**:
1. Parse `--force-warm` flag.
2. Validate `ASANA_CACHE_S3_BUCKET` env var is set and non-empty BEFORE invoking
   Lambda (pre-validate to surface MINOR-OBS-2 bucket-typo case with an
   actionable error, not a raw botocore traceback).
3. Invoke the `cache_warmer` Lambda via `boto3.client("lambda").invoke()` with
   `InvocationType="RequestResponse"` (synchronous) when `--wait` is passed;
   `InvocationType="Event"` (fire-and-forget) without `--wait`.
4. Parse Lambda response:
   - `statusCode: 200` + `body.success: true` -> emit confirmation to stderr +
     exit 0.
   - `statusCode: 500` or `body.success: false` -> emit error + exit 1.
5. On fire-and-forget (no `--wait`): emit "force-warm invoked (async); monitor
   DMS metric at Autom8y/AsanaCacheWarmer for confirmation" to stderr + exit 0.

**Lambda function name resolution**: The Lambda function name is resolved from
settings or env var (e.g., `CACHE_WARMER_LAMBDA_FUNCTION_NAME`). This env var
must be added to the CLI's preflight contract (alongside
`ASANA_CACHE_S3_BUCKET`). The exact env var name is a P6 implementation detail;
the design requires a named Lambda ARN/function-name resolution path.

**HOOK POINT (P4 thermal-monitor)**: The force-warm invocation timestamp and
outcome (success/failure/async) should be emittable as a CloudWatch metric
(e.g., `ForceWarmInvoked`, `ForceWarmSuccess`) for SLO tracking. P4 designs
the SLI/SLO; this TDD declares the hook point exists at force-warm completion.

### Idempotency semantics

**Decision: refresh anyway (not no-op)**. If a force-warm is invoked when
parquets are already fresh, the Lambda still runs. Rationale: the operator
explicitly requested a force-warm, which signals they want certainty about
data currency, not just a freshness check. A no-op on fresh data would
undermine the confidence signal. The Lambda warm itself is idempotent by
design (overwrite is safe; the parquet key is deterministic).

**Alternative considered (no-op on fresh)**: Rejected because the operator
cannot distinguish "no-op because fresh" from "no-op because the check
failed silently." The warm cost ($0.000017/invocation) is negligible.

### Rate limiting / thundering herd prevention

**Decision: delegate to `DataFrameCacheCoalescer`**. The existing
`DataFrameCacheCoalescer` (referenced in heat-mapper assessment at
`src/autom8_asana/cache/dataframe/coalescer.py`) provides the stampede
protection primitive for the DataFrameCache warm path. P2 design position:
the force-warm CLI affordance must verify that the coalescer is correctly
wired for the Lambda invocation path — specifically, that concurrent
`--force-warm` invocations from multiple operators do not issue simultaneous
Lambda `invoke` calls, each triggering a full multi-entity warm cascade.

**Design requirement for P6 (implementation)**: Before invoking Lambda, the CLI
should acquire a coalescing lock (or check a "warm-in-progress" DynamoDB/SSM
flag if cross-process coordination is required). If a warm is already in
progress (e.g., the scheduled EventBridge invocation is running), the CLI
should:
- With `--wait`: poll the DMS metric or Lambda invocation status until the
  current warm completes, then return.
- Without `--wait`: emit a warning ("warm already in progress — invoke DMS
  metric `Autom8y/AsanaCacheWarmer` to track completion") and exit 0.

**DEFER tag**: The specific coordination mechanism (in-process coalescer, DynamoDB
lock, or SSM parameter) requires P3 capacity-engineer input on the Lambda
concurrency configuration.
[DEFER-POST-P3: coordination mechanism for concurrent force-warm invocations
depends on Lambda reserved concurrency settings designed by P3]

### Sync vs async

**Decision: default async (fire-and-forget), opt-in sync (--wait)**.

Rationale: A full cache warm traverses multiple entity types sequentially
(`cascade_warm_order()` at `src/autom8_asana/lambda_handlers/cache_warmer.py:398`)
and can take seconds to minutes
(`WarmDuration` emitted per entity at `src/autom8_asana/lambda_handlers/cache_warmer.py:479-483`).
A CLI invocation that blocks for minutes is a poor operator UX.
The async default (`InvocationType="Event"`) returns immediately after the
Lambda invocation is accepted. The operator can confirm completion by watching
the DMS metric at `Autom8y/AsanaCacheWarmer` (already wired at
`src/autom8_asana/lambda_handlers/cache_warmer.py:843-845`) or by re-running
the metrics CLI with `--strict` to see if freshness has improved.

`--wait` is provided for CI scenarios where a gate must not advance until
the warm is confirmed complete. In sync mode, Lambda `invoke` with
`InvocationType="RequestResponse"` blocks for up to the Lambda timeout (15
minutes maximum). If the warm times out and self-invokes a continuation (per
`src/autom8_asana/lambda_handlers/cache_warmer.py:424-425`), the
`--wait` invocation will receive a partial completion response
(`WarmResponse.success=False`); the CLI should exit 1 and emit a note that
the warm continues in the background.

### Auth: who can force-warm?

**Decision: IAM-bound via the invoker's execution context**. The CLI invokes
Lambda via `boto3.client("lambda").invoke()`. The boto3 session uses the
caller's AWS credentials (same credentials that access S3 for parquet reads).
No separate PAT or service token is required. The invoker must have
`lambda:InvokeFunction` permission on the warmer Lambda ARN. This is
consistent with the existing permission model: the CLI already requires
`s3:GetObject` + `s3:ListBucket` on `autom8-s3`. Adding `lambda:InvokeFunction`
on the warmer Lambda is permission-surface expansion; it must be documented in
the implementation handoff as a new IAM grant required.

---

## Section 5: Freshness SLA Enforcement Model (NG8 discharge)

### Where enforcement lives

**Decision: CLI-side (primary), with a future Lambda-side gate as an
augmentation path**.

The existing `--strict` flag at `src/autom8_asana/metrics/__main__.py:341` already
implements basic SLA enforcement: when `max_age > threshold`, `--strict` exits 1.
This is the correct enforcement seam for the CLI consumer (human operator, CI
gate, downstream automation). NG8 extends this foundation; it does not replace it.

The SLA enforcement model has two gates:

**Gate A — CLI publish-blocking (current + extension)**:
- Already implemented via `--strict` + configurable `--staleness-threshold`.
- Extension: a named SLA profile concept (`--sla-profile={active_mrr|default}`)
  that maps to a threshold value. This allows per-use-case thresholds without
  requiring the caller to remember the numeric value.
  [DEFER-POST-P3: threshold values per SLA profile depend on P3's per-section TTL
  design; the profile names are declared here, the values are P3's output]

**Gate B — Lambda warmer pre-publish gate (future augmentation)**:
- Design position for post-deadline procession: the Lambda warmer, before
  writing a new parquet, could check if the prior parquet is within the SLA
  window. If fresh (< 6h), it skips the expensive Asana API traversal for
  that section. This is a cost optimization, not an enforcement gate, and it
  is deferred.
- [DEFER-POST-DEADLINE: Lambda warmer skip-if-fresh optimization; not part of
  current procession scope]

### Configurable thresholds per use case

Per PRD G2, the default threshold is 6h (`--staleness-threshold 6h`). The
architecture declares three SLA classes, whose numeric values P3 will assign:

| SLA class | Applies to | Design rationale |
|---|---|---|
| `active_mrr` | ACTIVE-classifier sections (offer active, restart, run-optimizations) | Direct contributor to financial aggregate; tightest threshold |
| `informational` | Non-ACTIVE sections (WARM class, 6-48h) | Informational; relaxed threshold acceptable |
| `archival` | Near-empty sections (< 2500 bytes) | Presumably inactive; longest threshold acceptable |

[DEFER-POST-P3: numeric threshold values per class are P3 output. The CLI
architecture implements the named SLA profile lookup; the values are injected
via settings or env var at implementation time.]

### Publish-blocking gate protocol

When `--strict` is passed and `FreshnessReport.stale == True`:

1. CLI emits WARNING to stderr (per `src/autom8_asana/metrics/__main__.py:330-331`).
2. CLI exits 1 (per `src/autom8_asana/metrics/__main__.py:341-342`).
3. The metric VALUE is already emitted to stdout before the exit gate fires
   (stdout emission at line 269, freshness probe at line 276+). This ordering
   is existing behavior. Design position: this is acceptable for human-readable
   output (the value and the staleness signal together form the complete picture);
   for structured consumers (`--json`), the entire envelope including
   `freshness.stale: true` is the output, and the consumer decides whether to
   use the value. No pre-emit gate is required.

**Refusal protocol for gated consumers**: A CI gate consuming `--strict` treats
exit 1 as "do not advance". The metric value on stdout is available for logging
but should not be used in downstream computation when exit code is 1. This is
a consumer-convention contract, not a CLI-enforced suppression.

### Auto-remediation: SLA breach triggers force-warm

**Decision: NOT automatic for CLI invocations; document as an operator workflow**.

Rationale: Automatically triggering a Lambda force-warm on every `--strict`
exit-1 invocation creates a thundering herd risk in CI contexts (multiple parallel
CI jobs, each detecting staleness, each triggering a warm). The Lambda warm is
expensive (multi-entity sequential warm, seconds to minutes). Auto-triggering
from every stale-detected invocation is disproportionate.

**Operator workflow (documented, not automated)**:
1. CI gate: `python -m autom8_asana.metrics active_mrr --strict` exits 1 on stale.
2. Operator sees WARNING in CI logs.
3. Operator invokes `python -m autom8_asana.metrics --force-warm` (or waits for
   the scheduled warm cycle).
4. After warm confirms (DMS metric or `--wait` sync return), re-run
   `active_mrr --strict` to confirm fresh.

**Deduplication for simultaneous stale-detection + force-warm**: If an operator
manually triggers `--force-warm` while a scheduled warm is running, the
coalescing mechanism (Section 4, rate-limiting design) prevents double-warm.

---

## Section 6: Refresh-Ahead Augmentation (G3 VIABLE-AUGMENTATION)

**Source**: CACHE:SRC-001 (Vattani et al. 2015, XFetch, STRONG grade)

### Where in the cache stack

The refresh-ahead (XFetch) augmentation applies at the **DataFrameCache
MemoryTier boundary** — specifically, at the SWR rebuild trigger decision
point in `src/autom8_asana/cache/dataframe/factory.py:40-80`.

The current trigger condition is watermark-based: when the `DataFrameCacheEntry`
watermark indicates the entry is `APPROACHING_STALE` (i.e., age exceeds
`approaching_threshold * entity_ttl` per
`src/autom8_asana/cache/policies/freshness_policy.py:56`), the SWR callback
fires. This is a deterministic trigger — every invocation that reads an
approaching-stale entry fires a rebuild.

XFetch replaces the deterministic threshold with a probabilistic early-trigger:

```
early_trigger = -delta * beta * ln(random())
current_remaining = expiry_time - now
should_refresh_early = current_remaining <= early_trigger
```

Where `delta` is the rebuild cost estimate (seconds) and `beta` is a tuning
parameter.

### XFetch beta parameter selection

Per CACHE:SRC-001 §3.4, `beta = 1.0` is the recommended starting value. This
corresponds to a balanced probability distribution that begins triggering
refreshes at a cost-proportional time before expiry. For the DataFrame rebuild
use case:
- `delta` = observed SWR rebuild duration (seconds); from `WarmDuration` metric
  emitted at `src/autom8_asana/lambda_handlers/cache_warmer.py:479-483`, offer
  entity rebuild takes O(seconds to minutes). Approximate `delta` as 60s as a
  conservative estimate.
- `beta = 1.0` (CACHE:SRC-001 §3.4 default)

[DEFER-POST-P3: exact delta calibration requires P3 capacity-engineer's
WarmDuration analysis across entity types. P3 should provide observed p50/p95
WarmDuration to calibrate delta. beta = 1.0 is the initial value; P3 may
recommend adjustment based on miss-rate analysis.]

### Composition with existing TTL discipline + force-warm

The XFetch augmentation composes with the existing architecture as follows:

1. **Normal path**: XFetch triggers a probabilistic early rebuild from the MemoryTier.
   The rebuild writes to L2 (S3 via `SectionPersistence`) and L1 (MemoryTier
   via `cache.put_async`), as it does today.
2. **Scheduled Lambda warm path**: Lambda warm writes to L2. L1 is not
   immediately updated; XFetch trigger fires on the next L1 read when the
   entry's age exceeds the probabilistic threshold.
3. **Force-warm path**: Force-warm triggers a Lambda warm (L2 write).
   L1 is updated on next SWR rebuild trigger cycle, same as scheduled warm.
4. **No conflict**: XFetch and scheduled warm / force-warm are not mutually
   exclusive. The coalescer (Section 4, rate-limiting design) prevents
   simultaneous L1 SWR rebuild and Lambda warm from racing on L2 writes.

**Implementation location**: The XFetch logic should be introduced at
`src/autom8_asana/cache/dataframe/factory.py` in the `_swr_build_callback`
trigger condition, or at the `DataFrameCache` entry evaluation point. Exact
integration location is a P6 implementation decision; this TDD declares the
interface contract: the trigger replaces (or augments) the current
deterministic `approaching_threshold` check with the XFetch probabilistic
formula.

---

## Section 7: AP-3 Named Risk — MutationInvalidator Gap

**Source**: Heat-mapper assessment AP-3 (`src/autom8_asana/cache/integration/mutation_invalidator.py:36`)

### The gap

`_TASK_ENTRY_TYPES = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]`
at `src/autom8_asana/cache/integration/mutation_invalidator.py:36`.

The `MutationInvalidator` covers REST mutation-triggered invalidation for
task-level entity cache entries. The DataFrame parquet tier is NOT included in
`_TASK_ENTRY_TYPES`. An Asana task mutation (e.g., a task moving from one
section to another) will:
- Invalidate the task-entity cache entries for the affected task.
- NOT trigger a re-write of the parquet file for the source or destination section.

The financial aggregate `active_mrr` reads from section parquets. If a task
moves from an ACTIVE section to a non-ACTIVE section (or vice versa), the parquet
for the source section will contain the task until the next Lambda warm; the
aggregate will report the pre-move state.

### Why tolerable for this procession

Three factors bound the risk:

1. **Eventual consistency is explicitly accepted**: DEF-3 (confirmed by Pythia
   decision) establishes that `active_mrr` is internal/operational only. The
   6h staleness budget means a section-move event will be reflected in the
   metric within the Lambda warm cadence (once that cadence is documented by P3).

2. **Staleness is now visible**: The `FreshnessReport` at
   `src/autom8_asana/metrics/freshness.py:98-214` surfaces `max_age` per
   invocation. An operator who needs post-mutation freshness can invoke
   `--force-warm` and then re-read. The gap is operational, not silent.

3. **Force-warm closes the gap on demand**: The `--force-warm` CLI affordance
   (Section 4 of this TDD) provides the operator-accessible remediation path.
   A section move that materially changes `active_mrr` can be remediated in
   minutes by force-warming.

### Why surfaced for design-review at P7

- The gap represents an architectural seam where task-mutation invalidation
  is incomplete relative to the full cache hierarchy.
- If `active_mrr` usage evolves from internal-operational to investor-grade
  (the USER-ADJUDICATION-REQUIRED flag from heat-mapper G5), the 6h window
  becomes unacceptable and event-driven re-warm (Asana webhooks) becomes
  load-bearing.
- P7 (thermal-monitor design-review) must assess whether the AP-3 gap is
  explicitly documented in the observability plan so that SLA alerting
  reflects the known invalidation window.

### NOT silently worked around

This TDD does not propose to fix AP-3 within the operationalize scope. The gap
is documented here as a known architectural limitation. A future procession
targeting event-driven re-warm (DEF-5 in heat-mapper deferred decisions) would
close this gap by adding a webhook-triggered parquet invalidation path.

---

## Section 8: Cross-References with P3 and P4

### P3 capacity-engineer dependencies

This architecture has the following explicit dependencies on P3 outputs:

| Dependency | What P3 must provide | How this TDD consumes it |
|---|---|---|
| Per-section TTL values (D10) | Numeric TTL targets per SLA class (active_mrr=Xh, informational=Yh, archival=Zd) | Section 5 SLA class table; XFetch delta calibration in Section 6 |
| Lambda warm cadence (DEF-2) | Documented EventBridge/CloudWatch Events schedule for `cache_warmer` Lambda | Section 4 force-warm design's idempotency rationale assumes a known cadence |
| WarmDuration p50/p95 by entity type | Observed rebuild cost for XFetch delta calibration | Section 6 XFetch beta/delta selection |
| Concurrent force-warm coordination mechanism | In-process coalescer vs. DynamoDB lock vs. SSM flag | Section 4 rate-limiting design |
| GID-to-section-name mapping for ACTIVE classifier | Which of the 14 GIDs are ACTIVE-classified | Section 5 SLA class assignment |

**DEF-2 cadence dependency (explicit)**:

This TDD's SLA enforcement model (Section 5) assumes the Lambda warm cadence
is a known, documented value. The SLA gate at `--strict` is meaningful only if
the warm cadence is <= the staleness threshold (i.e., the warm runs frequently
enough to keep ACTIVE sections fresh). If P3 discovers that the warmer schedule
is longer than the 6h threshold, the SLA enforcement model requires a cadence
adjustment (not a cache pattern change). P3's DEF-2 discharge must explicitly
state the cadence and confirm it satisfies or violates the 6h ACTIVE threshold.
If it violates, P3 escalates to the user.

### P4 thermal-monitor hook points

P4 designs the observability instrumentation. This TDD declares the hook points;
P4 owns the metric names, alarm thresholds, and SLO design.

| Hook point | Location | What P4 instruments |
|---|---|---|
| Force-warm invocation event | CLI at `--force-warm` invocation | `ForceWarmInvoked` metric, timestamp, entity_types |
| Force-warm completion | Lambda response parse | `ForceWarmSuccess` / `ForceWarmFailure` metric |
| Stale detection per invocation | `FreshnessReport.stale` at `src/autom8_asana/metrics/freshness.py` | `max_age_seconds` per invocation, SLA class |
| SWR rebuild trigger | `src/autom8_asana/cache/dataframe/factory.py:40` | `SWRRebuildTriggered`, `SWRRebuildDuration` |
| DMS heartbeat | `src/autom8_asana/lambda_handlers/cache_warmer.py:843-845` | Already emitting; P4 designs alarm threshold (currently 24h) |
| WarmSuccess / WarmFailure per entity | `src/autom8_asana/lambda_handlers/cache_warmer.py:473-505` | Already emitting; P4 designs SLO threshold |

---

## Architecture Decision Records

### ADR-003: Cache-aside pattern continuation for S3 parquet cold tier

- **Context**: Heat-mapper G3 evaluated 9 alternatives. Pattern selection for
  the S3 parquet cold tier requires justification.
- **Decision**: Continue cache-aside. Lambda warms; CLI reads. No pattern change.
- **Consequences**: The existing code composes correctly with the architecture.
  The force-warm affordance (Section 4) is a new entry point into the existing
  write path, not a pattern change.
- **Alternatives considered**:
  - Read-through: rejected because it would require the CLI to own the warm path
    and inline the full Asana API traversal, violating PRD C-4 and entangling
    the read path with the multi-entity warm cascade.
  - Write-through: not applicable; the write path is Lambda-owned and not
    triggered by CLI reads.
  - Write-behind: not applicable; the write path is already asynchronous.

### ADR-004: AP positioning for all three cache layers

- **Context**: Per CACHE:SRC-003 (Brewer CAP, STRONG): consistency model selection
  must be explicit, not hand-waved. DEF-3 (internal-only eventual consistency
  acceptable) is the business anchor.
- **Decision**: All three layers (S3 parquet, MemoryTier, freshness probe) are
  AP-positioned. Eventual consistency is the correct model. Linearizability or
  sequential consistency is not warranted for a metric where 6h staleness is
  explicitly accepted.
- **Consequences**:
  - No locking or ordering guarantee between Lambda write and CLI read.
  - `FreshnessReport` is the explicit compensation mechanism: it makes the
    consistency window visible rather than hiding it.
  - `--strict` is the enforcement gate for consumers who require freshness before
    acting on the metric.
  - If DEF-3 changes (investor-grade use case), the consistency model must be
    revisited. USER-ADJUDICATION-REQUIRED flag from heat-mapper G5 is the
    trigger.
- **Alternatives considered**:
  - CP positioning: would require the Lambda warm to complete and confirm before
    the CLI returns a value. This is architecturally impossible with cache-aside
    and the current CLI/Lambda separation. It would also impose Lambda-warm latency
    on every CLI invocation, which is unacceptable for the UX.

---

## Receipt Grammar

All behavioral claims in this TDD are backed by file:line anchors or explicit
DEFER tags. The following cross-references are load-bearing:

| Claim | Anchor |
|---|---|
| Cache-aside pattern for S3 parquet tier | `src/autom8_asana/cache/dataframe/tiers/progressive.py:41-60` |
| SWR rebuild callback (MemoryTier) | `src/autom8_asana/cache/dataframe/factory.py:40-117` |
| approaching_threshold = 0.75 | `src/autom8_asana/cache/policies/freshness_policy.py:56` |
| MutationInvalidator _TASK_ENTRY_TYPES excludes DataFrame | `src/autom8_asana/cache/integration/mutation_invalidator.py:36` |
| DMS namespace and heartbeat | `src/autom8_asana/lambda_handlers/cache_warmer.py:70, 843-845` |
| Checkpoint-based resume + self-invocation | `src/autom8_asana/lambda_handlers/cache_warmer.py:399-425` |
| WarmSuccess / WarmDuration / WarmFailure metrics | `src/autom8_asana/lambda_handlers/cache_warmer.py:473-504` |
| FreshnessReport factory + error mapping | `src/autom8_asana/metrics/freshness.py:98-214` |
| CLI exit-code matrix | `src/autom8_asana/metrics/__main__.py:341-342` |
| CLI exception handler (MINOR-OBS-2 gap) | `src/autom8_asana/metrics/__main__.py:239` |
| CacheProviderFactory env-based detection | `src/autom8_asana/cache/integration/factory.py:36-37` |
| S3Config.default_ttl = 604800 (7 days, entity cache only) | `src/autom8_asana/cache/backends/s3.py:60` |
| cascade_warm_order sequential processing | `src/autom8_asana/lambda_handlers/cache_warmer.py:398` |

---

*Authored by systems-thermodynamicist, thermia procession P2,
session-20260427-185944-cde32d7b, 2026-04-27. Branch:
thermia/cache-freshness-procession-2026-04-27.*
