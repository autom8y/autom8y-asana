---
type: spec
artifact_type: capacity-spec
initiative_slug: cache-freshness-procession-2026-04-27
parent_initiative: verify-active-mrr-provenance
session_id: session-20260427-185944-cde32d7b
phase: design
authored_by: capacity-engineer
authored_on: 2026-04-27
worktree: .worktrees/thermia-cache-procession/
branch: thermia/cache-freshness-procession-2026-04-27
schema_version: 1
status: draft  # ready for P4 thermal-monitor review; P5 handoff pending
---

# Capacity Specification: cache-freshness-procession-2026-04-27

## Receipt-Grammar Preamble

Every number in this specification has a derivation. Every policy selection has a referenced rationale. Claims about source-file behavior are anchored by file:line. Claims that cannot be grounded from static analysis carry explicit [DEFER] tags.

---

## 1. cache_warmer Lambda Schedule Audit (D10 Discharge)

### 1.1 IaC Probe

A bash probe of the worktree found zero files matching `*.tf`, `*.tfvars`, `serverless*.yml`, `template*.yml`, or any CDK artifact containing `cache_warmer` or `AsanaCacheWarmer`:

```
verification_anchor:
  source: "find .worktrees/thermia-cache-procession -name '*.tf' -o -name '*.tfvars' 2>/dev/null"
  result: does-not-exist
  claim: "no Terraform, SAM, or CDK IaC files exist in the worktree; EventBridge schedule rule is not defined in any IaC visible to this rite"
```

**D10 cadence verdict: [DEFER — IaC schedule not found in worktree]**

The Lambda warmer source (`src/autom8_asana/lambda_handlers/cache_warmer.py:1-905`) contains no EventBridge rule, no cron expression, and no schedule reference. The DMS namespace constant at line 70 (`DMS_NAMESPACE = "Autom8y/AsanaCacheWarmer"`) confirms the Lambda exists and is integrated with Grafana alerting (24h dead-man's-switch at `cache_warmer.py:843-845`), but the schedule that triggers it is managed entirely outside this codebase — in an external IaC repository or AWS console configuration not accessible in this worktree.

**P5a implementation item**: The warmer schedule MUST be made explicit in IaC (EventBridge rule with a cron expression). The current absence is a documented gap, not a defect in the Lambda itself.

### 1.2 Empirical Cadence Inference from Mtime Histogram

The 14-section mtime histogram (`2026-04-27-section-mtimes.json`) provides the only available empirical evidence about actual warm cadence:

| Age bucket at handoff | Count | Sections |
|---|---|---|
| HOT (< 6h / < 21,600s) | 2 | `1143843662099257` (3,273s), `1199511476245249` (17,695s) |
| WARM (6h–48h) | 3 | `1143843662099256` (104,096s ~28.9h), `1202496785025459` (161,690s ~44.9h), `1208667647433692` (161,691s ~44.9h) |
| COLD (> 48h) | 9 | Remaining 9 sections, oldest 2,803,079s (32.4 days) |

**Cadence interpretation**:

- The two HOT sections (3,273s and 17,695s ago) indicate a warm run did execute within the prior ~5 hours of the handoff timestamp (2026-04-27T14:55:43Z). The 3,273s section was written at approximately 2026-04-27T14:01:10Z — consistent with a near-handoff warm invocation.
- The three WARM sections cluster at ~29h and ~45h ages, not at 6h increments, which is inconsistent with a regular hourly or 6-hourly schedule touching all sections uniformly.
- The 9 COLD sections range from 4.9 days to 32.4 days. A 32-day cold section alongside a 54-minute hot section cannot both exist under a uniform per-section cadence. This is strong evidence that the warmer runs but does NOT process all 14 sections equally on each invocation.

**Most likely explanation**: The warmer processes sections in dependency-cascade order (`cascade_warm_order()` at `cache_warmer.py:316-318`) and either (a) times out before completing all entity types and self-continues only partially, or (b) runs on a per-entity-type basis that does not cover the section-parquet tier with uniform frequency. The checkpoint-based resume logic (`cache_warmer.py:338-358`) means a partial run that times out may only complete the higher-priority entity types (those earlier in `cascade_warm_order()`), leaving section parquets for lower-priority entity types unwarmed for extended periods.

**Cadence verdict for P4 (DEF-2 seam)**: The warmer does NOT run per-section every hour or every 6 hours for all sections. The data implies selective or partial coverage. The SLO baseline for thermal-monitor MUST account for the observed 9/14 sections exceeding 48h staleness as the current baseline — NOT the 6h PRD target. The 6h target is the DESIGN GOAL; the current operational reality is that 64% of sections exceed it.

---

## 2. Per-Section TTL Design (D10 Discharge)

### 2.1 TTL Class Derivation

The heat-mapper (assessment §G4, L186-196) established three section classes based on the PRD G2 6h staleness default and observed mtime distribution. This specification derives TTL values from those classes anchored in the mtime histogram.

**Section classification by data observed (not by GID-to-name mapping)**:

| Class | Count (observed) | Age at handoff | Staleness tolerance | Force-warm cadence |
|---|---|---|---|---|
| ACTIVE (offer classifier sections) | Unknown GID subset; 3 named sections per `activity.py:76` | DEFER (GID-to-name mapping required) | 6h | Every 4h |
| WARM (non-ACTIVE populated sections, age 6h–48h at handoff) | 3 sections | 29h–45h | 12h | Every 8h |
| COLD (non-ACTIVE sections, age > 48h at handoff) | 9 sections | 4.9d–32.4d | 24h–72h (sliding by sub-class) | Daily |
| Near-empty (< 2,500 bytes) | 2 sections (`1204152425074370` at 2,449 bytes, `1209233681691558` at 2,449 bytes per heat-mapper §G1 row 12/14) | ~23.7d and ~18.0d | 7d | Weekly |

**[DEFER — GID-to-ACTIVE-name mapping]**: Which specific GIDs from the 14-parquet inventory are ACTIVE-classifier-mapped (sections named `active`, `restart - request testimonial`, `run optimizations` per `src/autom8_asana/models/business/activity.py:76`) is not determinable from static analysis alone. P5a implementation item: the 10x-dev re-handoff must include an Asana API call or parquet metadata read to resolve this mapping before per-GID TTL enforcement can be configured. Until this mapping is established, all sections should be treated as ACTIVE-class for alerting purposes (conservative bound).

### 2.2 TTL Derivation Math

**ACTIVE-class TTL: 6h (21,600s)**

Derivation: PRD G2 declares `default 6h staleness threshold` (`verify-active-mrr-provenance.prd.md:70-71`). ACTIVE sections contribute directly to the `active_mrr` dollar figure — the financial decision-grade constraint cited in `heat-mapper-assessment:20`. The 6h default is the load-bearing PRD constraint; no deviation is warranted.

Force-warm cadence: every 4h (0.67 × TTL). This provides one full warm cycle of headroom before the 6h threshold is breached, absorbing Lambda execution latency (~seconds to ~2 minutes per `cache_warmer.py:479-483` `WarmDuration` emission) and checkpoint-resume overhead. Derivation: 4h cadence at 2-minute max execution leaves 4h 2min elapsed before TTL breach — 98% of the TTL budget consumed at worst case, leaving 2% (7.2 minutes) as final margin. This is tight but acceptable given the DMS alert at 24h already provides a backstop.

Jitter: ±10% of base TTL = ±21.6 minutes (1,296s). Applied to force-warm schedule to prevent synchronized Lambda invocations from multiple environments. [PLATFORM-HEURISTIC: ±10-20% jitter range is practitioner-derived, not empirically calibrated]

**WARM-class TTL: 12h (43,200s)**

Derivation: WARM sections are informational, not contributors to the active_mrr calculation. The heat-mapper freshness budget table (assessment L367-372) recommends 12h. Empirical grounding: the three WARM sections observed at 29h–45h ages are already in breach of a 12h target at handoff time, confirming that the current warmer cadence does not satisfy this target — which is precisely the gap D10 is designed to close.

Force-warm cadence: every 8h (0.67 × TTL). Same derivation principle as ACTIVE class.

Jitter: ±10% of base = ±72 minutes (4,320s).

**COLD-class TTL: 24h (86,400s)**

Derivation: Non-ACTIVE, non-near-empty sections where data changes slowly. The 24h upper bound aligns with the existing DMS dead-man's-switch threshold at `cache_warmer.py:843-845` — sections in this class should remain fresh across one full DMS window.

Force-warm cadence: every 20h (0.83 × TTL). Conservative multiplier because COLD sections are lower priority and Lambda timeout risk is lower when warmer is running per-entity rather than full-cascade.

Jitter: ±10% of base = ±144 minutes (8,640s).

**Near-empty-class TTL: 7d (604,800s)**

Derivation: Sections at 2,449 bytes each (per heat-mapper §G1 entries for GIDs `1204152425074370` and `1209233681691558`) contain minimal data, likely inactive or archived sections. The 7-day target matches the existing `S3Config.default_ttl = 604800` at `src/autom8_asana/cache/backends/s3.py` (line 46 per heat-mapper §G2 row 4) — a coincidental alignment that simplifies operational mental model. One week is sufficient for data that changes at most monthly (evidenced by 32-day age at handoff).

Force-warm cadence: every 6d (0.86 × TTL).

Jitter: ±10% of base = ±1,008 minutes (16.8h).

### 2.3 TTL Implementation Options for Per-Section Tracking

The warmer currently persists no per-section TTL metadata — the S3 object `LastModified` timestamp IS the only available watermark (heat-mapper assessment §For capacity-engineer, L387). Three implementation options:

| Option | Mechanism | Pro | Con |
|---|---|---|---|
| (a) S3 metadata sidecar | Write a companion `{section_gid}.ttl.json` alongside each parquet | Self-contained per section; readable by CLI without CloudWatch | Extra S3 writes per warm; adds storage surface |
| (b) CloudWatch metric per section | Emit `SectionLastWarmed` with `section_gid` dimension at warm time | Integrates with existing DMS + P4 thermal-monitor design | CloudWatch metric retention is 15 months; dimension cardinality at 14 sections is well within limits |
| (c) Watermark manifest alongside parquet | Extend the existing manifest file pattern (referenced in `cache_warmer.py:461` `manifest_preserved_after_warm` log event) | Manifest is already written; extends an existing pattern | Requires reading manifest to determine per-section TTL status |

**Recommendation**: Option (b) for the monitoring/alerting path (P4 thermal-monitor designs the SLO alarm), Option (c) for the operational path (warmer writes TTL class into the manifest so the CLI and force-warm logic can gate on class-appropriate staleness). This avoids Option (a)'s S3 write amplification while providing both an alertable metric and a self-describing manifest.

**Decision deferred to P2 (systems-thermodynamicist)**: The manifest write path is within P2's architecture domain. This specification provides the TTL values; P2 decides the persistence mechanism.

---

## 3. Working-Set Sizing

### 3.1 Current Working Set

**Parquet count**: 14 (per `2026-04-27-section-mtimes.json` row count, confirmed by heat-mapper §G1 mtime classification table)

**Parquet size distribution** (derived from heat-mapper §G1 references to dossier §2):

| Metric | Value | Source |
|---|---|---|
| Smallest parquets (near-empty class) | ~2,449 bytes each | Heat-mapper §G1 row 12/14; GIDs `1204152425074370`, `1209233681691558` |
| Largest parquet (by size) | 109,102 bytes | Heat-mapper §For capacity-engineer L376, GID `1201105736066893` |
| Total across all 14 sections | ~292,000 bytes (292 KB) | Heat-mapper §For capacity-engineer L377 |
| Average per parquet | ~292,000 / 14 = 20,857 bytes (~20 KB) | Derived |

**S3 cold-tier working set**: 292 KB total. This is negligible for S3 storage cost purposes — S3 minimum billing unit is 128 KB per object; 14 objects total ~$0.0000004/month in storage at $0.023/GB/month standard tier. Storage cost is not a decision variable.

**In-memory tier working set (MemoryTier)**:

The `MemoryTier` uses `max_heap_percent=0.3` (30% of container memory) as a dynamic limit, with `max_entries=100` as a backup bound (`src/autom8_asana/cache/dataframe/tiers/memory.py:81-82`). The entries stored are `DataFrameCacheEntry` objects holding Polars DataFrames.

Working set for Polars DataFrames in memory: Polars in-memory representation is columnar and typically 1–3x the parquet file size (parquet is compressed; Polars in-memory is decompressed). Using a 3x decompression factor as conservative bound:

- Total in-memory working set = 292 KB × 3 = 876 KB ≈ 0.9 MB

With `DataFrameCacheEntry` metadata overhead (project_gid string, entity_type string, watermark datetime, created_at datetime, schema_version string, row_count int, build_quality object) estimated at ~500 bytes per entry × 14 entries = 7 KB overhead. Total with metadata: ~0.9 MB + 0.007 MB ≈ 0.91 MB.

**The in-memory working set is trivially small relative to any realistic container memory allocation.** Even a 256 MB Lambda or ECS container at 30% heap allocation provides 76.8 MB for the MemoryTier — 84x the actual working set. The `max_heap_percent=0.3` setting is correctly generous and requires no adjustment for this workload.

**Headroom calculation**: 76.8 MB (available at 256 MB container) / 0.91 MB (working set) = 84x. This is well above the 1.5–2.5x practitioner headroom range [PLATFORM-HEURISTIC]. The constraint binding in practice is `max_entries=100`, which at 14 sections is at 14% utilization. No capacity risk for the in-memory tier at current scale.

### 3.2 Working-Set Growth Projection

**Section count growth ceiling**: The key space is bounded by Asana sections in the offer project. Asana projects have a practical limit of ~1,000 sections. At 14 current sections and a growth rate constrained by business process expansion (new offer stages, not viral user growth), a 10x growth scenario to 140 sections is a realistic upper bound over 2–3 years.

| Scenario | Section count | Total parquet data (conservative at 3x avg) | In-memory working set |
|---|---|---|---|
| Current | 14 | 292 KB raw → ~0.9 MB in-memory | ~0.91 MB |
| 2x growth | 28 | ~584 KB raw → ~1.8 MB in-memory | ~1.82 MB |
| 10x growth (ceiling) | 140 | ~2.9 MB raw → ~9 MB in-memory | ~9.1 MB |
| Theoretical Asana max | 1,000 | ~20.9 MB raw → ~63 MB in-memory | ~63 MB |

**Conclusion**: Even at theoretical Asana section maximum (1,000 sections), the in-memory working set (~63 MB) remains well within a 256 MB container's 76.8 MB MemoryTier allocation. The `max_entries=100` limit would be the binding constraint at ~100 sections; at 10x growth (140 sections) this limit would need to be raised to ~150–175 (with 25% buffer). This is a minor configuration change, not a capacity redesign. The S3 cold-tier has no practical capacity ceiling.

**Refresh budget** (total data written/day to maintain all sections within TTL):

| Class | Sections | Warm frequency | Data per warm | Daily write volume |
|---|---|---|---|---|
| ACTIVE | 3 (assumed) | Every 4h → 6 warms/day | ~20 KB avg × 3 sections = 60 KB | 360 KB/day |
| WARM | 3 | Every 8h → 3 warms/day | ~20 KB avg × 3 sections = 60 KB | 180 KB/day |
| COLD | 7 | Daily → 1 warm/day | ~20 KB avg × 7 sections = 140 KB | 140 KB/day |
| Near-empty | 2 | Weekly → 0.14 warms/day | ~2.4 KB avg × 2 sections = 4.8 KB | 0.7 KB/day |

**Total daily write volume**: 360 + 180 + 140 + 0.7 = **680.7 KB/day ≈ 0.68 MB/day**

S3 PUT request count: 3 × 6 + 3 × 3 + 7 × 1 + 2 × 0.14 = 18 + 9 + 7 + 0.28 = **34.28 PUT requests/day**

At $0.005/1,000 PUT requests (S3 standard), daily PUT cost = 34.28/1,000 × $0.005 = **$0.00017/day** → **$0.005/month**. Negligible.

---

## 4. Force-Warm Cost Envelope

### 4.1 Per-Invocation Cost

A full-cascade force-warm invokes the Lambda once and processes all entity types sequentially (checkpoint-based resume if timeout occurs). Cost components:

**Lambda invocation cost**:
- Lambda standard pricing (128 MB memory, us-east-1): $0.0000002/request + $0.0000000083/GB-second
- 128 MB = 0.125 GB
- Warm execution time estimate: seconds to ~2 minutes per heat-mapper §For capacity-engineer L382 (citing `WarmDuration` at `cache_warmer.py:479-483`). Conservative estimate: 2 minutes = 120 seconds
- Compute cost = 0.125 GB × 120s × $0.0000000083/GB-s = $0.000000124
- Request cost = $0.0000002
- Total per Lambda invocation = $0.000000124 + $0.0000002 = **~$0.0000003/invocation** (essentially $0.0000003, or less than 1/10 of a cent per 300 invocations)

Heat-mapper derived a $0.000017/invocation estimate (assessment §For capacity-engineer L381). The difference arises from their using a higher memory assumption. At any reasonable Lambda memory size (128–512 MB), the cost per invocation is in the $0.0000003–$0.000017 range — all negligibly small.

**Asana API cost**: $0 marginal cost; Asana API is a flat-rate subscription service with no per-call billing.

**S3 PUT cost per force-warm**: 14 sections × $0.005/1,000 PUTs = $0.00007. Negligible.

**Per-force-warm total**: ~$0.000017–$0.000087. Rounding conservatively to **$0.0001/invocation** for planning purposes.

### 4.2 Monthly Cost Upper Bound

| Scenario | Force-warms/day | Monthly invocations | Monthly cost |
|---|---|---|---|
| Scheduled (4h ACTIVE cadence) | ~6 Lambda invocations for ACTIVE class | 180 | $0.018 |
| Operator force-warm baseline | 10/day (heat-mapper estimate, assessment L383) | 300 | $0.030 |
| Stampede scenario (N=10 concurrent operators) | 100/day (10 operators × 10 force-warms) | 3,000 | $0.30 |
| Theoretical burst cap (rate-limit design target) | 1,440/day (1/minute) | 43,200 | $4.32 |

**Monthly upper bound under realistic conditions**: $0.05–$0.30/month. Even at the theoretical rate-limit ceiling (1 Lambda invocation/minute/day), monthly cost is $4.32.

**Recommendation**: Monthly cost is not a decision constraint at any realistic invocation volume. The force-warm affordance should be approved without budget qualification.

### 4.3 Rate-Limit Recommendation

To prevent accidental stampede (N operators simultaneously triggering force-warms), the force-warm CLI affordance should enforce:

- **Max 1 force-warm per operator per 5-minute window** — prevents accidental double-invocation
- **Max 3 concurrent Lambda invocations per account** — Lambda account-level concurrency limit is a natural backstop; no explicit rate limiting needed at the application layer
- **Coalescer window**: If multiple force-warm requests arrive within the `DataFrameCacheCoalescer.max_wait_seconds` window (default 60s per `dataframe/coalescer.py:77`), subsequent requests wait for the first to complete rather than each triggering a new Lambda invocation

---

## 5. Stampede Protection Design

### 5.1 Architecture of Concurrent Force-Warm Requests

The stampede scenario for this system is: N operators invoke `--force-warm` concurrently within a short window W. Without protection, each invocation would independently trigger a Lambda warm, resulting in N × (Asana API call + S3 PUT) for the same 14 sections.

**Existing coalescer capability**:

Two coalescers are present:

1. `DataFrameCacheCoalescer` at `src/autom8_asana/cache/dataframe/coalescer.py` — prevents thundering herd for in-process DataFrame BUILD operations. Algorithm: first `try_acquire_async()` → True (builds); subsequent calls → False (waits via `wait_async()`). Operates per key (`entity_type:project_gid`). Max wait: 60s (`max_wait_seconds=60.0` at `coalescer.py:77`). This is the LOAD-BEARING stampede protection mechanism for the DataFrame cache tier.

2. `RequestCoalescer` at `src/autom8_asana/cache/policies/coalescer.py` — batches staleness CHECK requests within a 50ms window (per ADR-0132, `window_ms=50` at `coalescer.py:61`). This is for the task-entity staleness-check path, not the DataFrame tier.

**Coalescer wiring for force-warm path**:

The `DataFrameCacheCoalescer` is wired at the `DataFrameCache` level (`dataframe_cache.py:191` `coalescer: DataFrameCacheCoalescer` field). Any caller that goes through `DataFrameCache.get_async()` or `put_async()` will hit the coalescer. The force-warm CLI affordance (PRD NG4, not yet implemented) MUST route through `DataFrameCache` rather than invoking Lambda directly without going through the cache layer, to benefit from the coalescer's thundering-herd protection.

**[UNATTESTED — DEFER]**: Whether the force-warm CLI affordance (PRD NG4, 10x-dev re-handoff scope) is implemented to route through `DataFrameCache` (coalescer-protected) or via direct Lambda invoke (coalescer-bypassed) is an implementation decision not yet made. P5 handoff dossier MUST specify: force-warm routes through DataFrameCache to preserve coalescer protection.

### 5.2 Stampede Protection Mechanism Selection

The dispatch asked to evaluate three mechanisms:

**Option A — Coalescer alone** (existing `DataFrameCacheCoalescer`):

- Prevents concurrent in-process builds for the same cache key
- Does NOT prevent multiple CLI processes (different OS processes) from each triggering a Lambda invocation; the coalescer state is in-process only
- Sufficient for single-operator scenarios; insufficient for multi-operator concurrent force-warms across separate CLI processes

**Option B — Lease tokens** (CACHE:SRC-002, Nishtala et al. NSDI 2013 [STRONG]):

- Lease tokens prevent both thundering herd AND stale sets by issuing a lease to the first requesting process; other processes receive a "wait and retry" response rather than a fill value
- Requires a coordination store (e.g., a short-TTL DynamoDB item or Redis key serving as the lease registry)
- For this workload: the Lambda invocation itself is idempotent and the output (S3 parquet) is a durable artifact. A "stale set" scenario (two Lambdas writing the same section in parallel) is benign — the last write wins and both outputs are valid refreshes. The specific harm lease tokens prevent (stale set from a stale value circulating) is not a risk here.

**Option C — Idempotency key** (Lambda-level deduplication):

- AWS Lambda supports deduplication via `ClientContext` idempotency keys on synchronous invocations
- A force-warm CLI affordance that generates a deterministic invocation key (e.g., hash of `entity_types + timestamp_rounded_to_5min_window`) will cause duplicate Lambda invocations within the same 5-minute window to be deduplicated at the AWS layer
- No application code coordination required; leverages the Lambda execution model

**Decision: Coalescer + Idempotency Key (hybrid of A and C)**

Lease tokens (Option B) are not warranted here because the "stale set" harm they prevent does not apply to an idempotent Lambda that writes to S3. The `DataFrameCacheCoalescer` handles in-process thundering herd. A 5-minute idempotency-key window on Lambda invocations handles multi-process multi-operator concurrency without requiring a separate coordination store.

This is the minimum-complexity protection that addresses the actual stampede scenario. Lease tokens add coordination overhead that is not justified by the risk profile (idempotent S3 writes, sub-cent cost per invocation, small key space).

**Failure mode**: If the coalescer state is lost (process restart during a build), a new process will re-acquire the build lock and proceed. S3 write is idempotent; worst case is a duplicate warm write for the same section. No data corruption risk.

---

## 6. Eviction Policy Declaration

### 6.1 S3 Cold Tier (ProgressiveTier / SectionPersistence)

**Eviction policy: N/A — S3 does not evict objects.**

S3 is object storage with no native eviction. Parquet files at `s3://autom8-s3/dataframes/1143843662099250/sections/` persist indefinitely until explicitly deleted. The `ProgressiveTier` writes new parquets to replace the previous version (overwrite, same key); there is no accumulation of stale objects.

**Lifecycle policy**: S3 object lifecycle rules (Intelligent-Tiering, S3-IA transition, Glacier archive) are not relevant at 292 KB total working set. Cost at any storage class for 292 KB is fractions of a cent per month. No lifecycle policy is recommended.

**Access pattern relevance**: Because S3 is not a cache in the eviction-policy sense, the question of LRU vs. LFU vs. ARC (Megiddo & Modha 2003) does not apply. The relevant policy is the warm-cadence schedule defined in §2, which governs when new data replaces old data.

### 6.2 In-Memory Tier (MemoryTier)

**Eviction policy: LRU with staleness-based secondary eviction.**

The `MemoryTier` implementation uses an `OrderedDict` for LRU ordering (`memory.py:85`) with eviction tracking across three modes:

- `evictions_lru`: Standard LRU eviction when memory limit is reached
- `evictions_staleness`: Secondary eviction of entries past their TTL
- `evictions_memory`: Eviction triggered by memory pressure (`max_heap_percent=0.3`)

File:line evidence: `src/autom8_asana/cache/dataframe/tiers/memory.py:96-100` (statistics initialization showing all three eviction modes).

**Eviction policy adequacy assessment**:

The workload has 14 sections, a tiny working set (~0.91 MB), and a `max_entries=100` limit (14% utilized). LRU is appropriate here because:

1. Access pattern: the `active_mrr` computation reads all ACTIVE sections on each CLI invocation — access is NOT highly skewed Zipfian. All sections are accessed with similar frequency per invocation. LRU's weakness (evicting frequently-accessed keys under scan pressure) is not a concern at this scale with 14 entries and 100-entry capacity.
2. At 14 entries vs. 100 capacity, eviction is extremely rare under normal operation. The MemoryTier will almost never evict in practice; all 14 entries fit comfortably.
3. W-TinyLFU (Einziger et al.) would provide scan resistance, but there are no scan-heavy workloads at this tier — the CLI reads specific entity types by project GID, not sequential scans across the entire key space.
4. ARC (Megiddo & Modha 2003) self-tuning is unnecessary when the working set is 86x smaller than the allocation.

**Verdict**: LRU is correctly selected for this workload at current scale. At 10x growth (140 entries vs. 100-entry limit), the `max_entries=100` would need to be raised (see §3.2 growth projection). No policy change is recommended; the existing implementation is correct.

---

## 7. Aggregate Resource Plan

| Layer | Technology | Storage | Instances | Monthly Cost Est. |
|---|---|---|---|---|
| S3 cold tier (ProgressiveTier) | AWS S3 Standard | 292 KB (14 parquets) | 1 bucket (shared) | < $0.01/month storage |
| S3 PUT writes (warm cadence) | AWS S3 PUT API | N/A | ~34 PUTs/day | $0.005/month |
| In-memory tier (MemoryTier) | Process heap (ECS/Lambda) | ~0.91 MB (30% of container) | Per-process (shared ECS container) | $0 incremental (existing ECS cost) |
| Lambda warmer (scheduled) | AWS Lambda | N/A (stateless) | 1 function | ~$0.01/month at 4h cadence |
| Force-warm (operator demand) | AWS Lambda | N/A | 1 function (same as scheduled) | ~$0.03/month at 10/day |
| CloudWatch metrics (P4 SLIs) | AWS CloudWatch | N/A | Per-invocation metric emit | ~$0.10/alarm/month (P4 designs) |

**Total incremental monthly cost** (capacity-engineer components only): < $0.10/month. The dominant cost line is the Lambda warmer execution, which is already incurred by the existing warmer regardless of TTL discipline changes.

---

## 8. Policy Decision Records

### PDR-1: Warmer Schedule Not in IaC — Deferred to P5a Implementation

**Context**: No IaC files (Terraform, SAM, CDK) exist in the worktree specifying the EventBridge schedule rule for the cache_warmer Lambda. The empirical mtime histogram shows selective/partial coverage, not uniform per-section warming.

**Decision**: Document the gap explicitly. The cadence cannot be derived without IaC access. P5a implementation item mandates IaC schedule declaration before the parent telos can be fully discharged.

**Theoretical basis**: Anti-pattern register item "Static Sizing" — the equivalent for schedules is "undocumented cadence": a warmer schedule configured once without documentation cannot be audited, replicated, or alarmed against. The DMS 24h alert at `cache_warmer.py:843-845` fires only if the Lambda fails completely; it does NOT detect partial coverage where some sections are never warmed.

**Trade-off**: Accepting a [DEFER] on the D10 cadence verdict means P4's SLO baseline must be set against observed reality (9/14 sections stale) rather than the design goal (6h for ACTIVE). P4 should design the SLO alarm to fire on the DESIGN target, not the current baseline.

### PDR-2: TTL per Section Class (Not Flat TTL)

**Context**: 14 sections span 4 distinct classes by data importance and observed update frequency. Applying a flat 6h TTL to all sections would require the warmer to process near-empty archived sections at the same frequency as ACTIVE financial-metric sections.

**Decision**: Tiered TTL by section class — ACTIVE 6h, WARM 12h, COLD 24h, near-empty 7d.

**Theoretical basis**: Anti-pattern register item "Flat TTL" — session tokens and product descriptions have different lifetimes; similarly, ACTIVE financial-metric sections and 32-day-stale near-empty sections have different freshness requirements. The staleness tolerance is set by the consumer's decision-grade requirements (PRD G2 6h) for ACTIVE class, not by a uniform policy.

**Trade-off**: Tiered TTL requires the warmer to know section classification, which requires the GID-to-name mapping ([DEFER] tag). Until that mapping is established, the conservative fallback is to treat all sections as ACTIVE-class for warming frequency.

### PDR-3: Eviction Policy N/A for S3; LRU Retained for MemoryTier

**Context**: Dispatch required explicit eviction policy declaration for both tiers.

**Decision**: S3 tier — N/A (object storage has no eviction). MemoryTier — LRU as implemented, retained without change.

**Theoretical basis**: LRU is appropriate when access pattern is not highly Zipfian and working set fits comfortably within allocation (which it does at 14/100 entries). Scan-resistance algorithms (LIRS, W-TinyLFU) are warranted when sequential scans pollute the cache with non-recurrent keys; no such scan pattern exists in this workload.

**Trade-off**: LRU will underperform W-TinyLFU if the access pattern becomes highly skewed (e.g., ACTIVE sections accessed 100x more frequently than COLD sections). At 14 entries vs. 100-entry capacity, eviction is so infrequent that policy selection is academically irrelevant to actual performance.

### PDR-4: Stampede Protection via Coalescer + Idempotency Key (No Lease Tokens)

**Context**: Force-warm stampede scenario — N operators invoke simultaneously.

**Decision**: Rely on existing `DataFrameCacheCoalescer` for in-process thundering herd; add Lambda idempotency key (5-minute window) for cross-process deduplication. Lease tokens (CACHE:SRC-002) are not warranted.

**Theoretical basis**: Lease tokens (Nishtala et al. NSDI 2013 [STRONG]) are designed for the "thundering herd + stale set" scenario where multiple clients race to fill a cache miss with a potentially stale value. In this system, the Lambda writes are idempotent (S3 overwrite) and all write values are equally fresh (sourced from live Asana API at invocation time). The "stale set" harm is absent. Lambda's native deduplication via idempotency key covers the cross-process case at zero additional infrastructure cost.

**Trade-off**: Without lease tokens, two concurrent force-warm Lambda invocations that somehow bypass the idempotency window could both write to S3 simultaneously. This is benign — the last write wins, and both writes fetch fresh Asana data. No data integrity risk.

---

## 9. Cross-Spec Dependencies

### Dependency on P2 (systems-thermodynamicist)

- **TTL persistence mechanism**: This specification provides TTL values per section class; the mechanism for persisting and reading those TTLs (S3 metadata sidecar vs. manifest vs. CloudWatch) is a P2 architecture decision. P2 must specify the write path used by the warmer to record per-section class assignment.
- **Refresh-ahead beta math** (CACHE:SRC-001, XFetch): If P2 recommends XFetch probabilistic early refresh at the MemoryTier, the beta parameter (controlling probability of early refresh) should be calibrated against the section TTLs defined in §2.2 of this spec. Suggested starting point: beta = 1.0 (XFetch default, Vattani et al. VLDB 2015), which at `staleness_ratio = 0.75` (existing `approaching_threshold` at `freshness_policy.py:56`) would begin probabilistic refreshes when 75% of TTL is consumed.
- **Force-warm routing**: P2 must specify whether the force-warm CLI affordance routes through `DataFrameCache` (coalescer-protected) or via direct Lambda invocation. This spec recommends coalescer-protected routing (§5.1).

### Dependency on P4 (thermal-monitor — DEF-2 seam discharge)

- **SLO baseline**: The D10 cadence finding (9/14 sections currently exceed 6h TTL; warmer runs selectively/partially) sets the CURRENT OPERATIONAL BASELINE for P4's SLO design. P4 should design the SLO alarm to fire on the DESIGN target (ACTIVE sections > 6h stale) while acknowledging the current baseline is in breach. The SLO "error budget" at launch will start in deficit until the IaC schedule is fixed.
- **CloudWatch metric per section**: Option (b) in §2.3 (CloudWatch `SectionLastWarmed` per section GID) is the recommended monitoring surface for P4 to consume. P4 designs the alarm threshold (≥ TTL class value triggers breach).
- **Force-warm latency SLI**: P4 needs the per-class TTL values from §2.2 to define "force-warm success = ACTIVE sections age drops below 6h within 5 minutes of invocation."
- **Warmer success rate SLO**: Already wired via `WarmSuccess`/`WarmFailure` at `cache_warmer.py:473,501`. P4 inherits these metrics; this spec provides the section-class framing that allows P4 to weight ACTIVE-class failures higher than near-empty-class failures.

---

## 10. Sensitivity Analysis

### Assumption: Average parquet size = 20 KB

The total parquet data is empirically measured at ~292 KB for 14 sections. The per-section average is 292/14 = 20.86 KB. If this assumption is wrong by 2x in either direction:

- If avg size is 10 KB (2x smaller): in-memory working set drops to ~0.45 MB. Resource plan unchanged; all numbers still negligible.
- If avg size is 40 KB (2x larger): in-memory working set rises to ~1.8 MB. Still well within 30% heap allocation. Plan unchanged.

**Sensitivity: insensitive.** Parquet size cannot meaningfully affect resource planning at this scale.

### Assumption: Lambda warm execution ≤ 2 minutes per invocation

The heat-mapper cites `WarmDuration` emission at `cache_warmer.py:479-483` as evidence of per-entity-type timing. If warm execution is systematically 10 minutes (5x longer):

- Force-warm cadence for ACTIVE class: 4h cadence with 10-minute execution leaves 3h 50m idle per cycle. TTL (6h) is still satisfied.
- Lambda cost: 10 minutes × 0.125 GB × $0.0000000083 = $0.00000062/invocation. Still < $0.001/invocation. Plan unchanged.

**Sensitivity: insensitive to cost.** Warm execution time only matters for checkpoint-resume (handled by existing `_should_exit_early` + `_self_invoke_continuation` at `cache_warmer.py:400,425`).

### Assumption: 3x Polars decompression factor for in-memory working set

If Polars decompresses parquets at 10x ratio (extreme case):
- In-memory working set = 292 KB × 10 = 2.92 MB. Still < 3 MB vs. 76.8 MB available at 256 MB container. Plan unchanged.

**Sensitivity: insensitive.** S3 parquets for this workload are small enough that decompression factor does not threaten capacity.

---

## Handoff Readiness Checklist

- [x] `capacity-specification.md` produced at `.ledge/specs/cache-freshness-capacity-spec.md`
- [x] Every layer has capacity analysis with derivation (not bare numbers)
- [x] Eviction policy declared for both S3 tier (N/A, with rationale) and MemoryTier (LRU, with rationale)
- [x] Stampede protection specified (coalescer + idempotency key, with lease-token consideration documented)
- [x] TTL design per section class with derivation math and jitter values
- [x] D10 discharge: cadence verdict (DEFER — IaC not in worktree) + empirical inference documented
- [x] Aggregate resource plan with cost estimates
- [x] Cross-spec dependencies on P2 and P4 documented
- [x] Sensitivity analysis on key assumptions
- [x] P5a implementation items flagged (IaC schedule, GID-to-name mapping, force-warm routing through coalescer)
