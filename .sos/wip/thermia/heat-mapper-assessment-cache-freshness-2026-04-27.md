---
type: audit
artifact_type: thermal-assessment
initiative_slug: cache-freshness-procession-2026-04-27
parent_initiative: verify-active-mrr-provenance
authored_by: heat-mapper
authored_on: 2026-04-27
phase: P1
session_id: session-20260427-185944-cde32d7b
worktree: .worktrees/thermia-cache-procession/
branch: thermia/cache-freshness-procession-2026-04-27
---

# Thermal Assessment — cache-freshness-procession-2026-04-27

## System Context

- **Service assessed**: `autom8_asana` metrics CLI + DataFrameCache + Lambda cache_warmer
- **Current caching**: S3 parquet persistence at `s3://autom8-s3/dataframes/{project_gid}/sections/` via `ProgressiveTier` — plus in-memory tier (DataFrameCache) + optional Redis (production) + task-level entity cache (InMemory/Redis)
- **Primary concern**: Freshness discipline for a decision-grade financial metric (`active_mrr = $94,076.00`) backed by S3 parquets whose staleness is currently opaque at runtime
- **Complexity level**: STANDARD (design-review + in-anger-probe per telos SQ-3)

---

## G1 — Access Pattern Analysis

### Source evidence

- Parquet inventory: `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md:62-77` (14 objects, `aws s3 ls` capture 2026-04-27T14:55:43Z)
- Mtime histogram: `.ledge/handoffs/2026-04-27-section-mtimes.json` (14-row JSON, `age_seconds_at_handoff` per section)
- Classifier ACTIVE sections: `HANDOFF:44-52` (`src/autom8_asana/models/business/activity.py:76` + `317`)
- Consumer profile: `src/autom8_asana/metrics/__main__.py:160-241` (CLI; also Lambda via DataFrameCache warm path)

### Read / write ratio

- **Write path**: Lambda warmer (`src/autom8_asana/lambda_handlers/cache_warmer.py`) writes parquets per entity type via `ProgressiveTier`; writes are batch-initiated by Lambda invocation (schedule undocumented — see Open Questions below)
- **Read path**: CLI reads via `load_project_dataframe` (data path), then separately via `FreshnessReport.from_s3_listing` (freshness probe, `src/autom8_asana/metrics/freshness.py:98-214`). ECS preload also reads DataFrameCache via SWR rebuild path (`src/autom8_asana/cache/dataframe/factory.py:40-80`)
- **Read/write ratio estimate**: Reads are on-demand (each CLI invocation, each ECS preload). Writes are Lambda-cadence. Given a daily-ish warm cadence (observed oldest parquet ≈32 days), actual read-write ratio on the parquet objects is high (many reads per write) but total CLI invocation volume is unknown from code alone

### Mtime histogram classification

All ages computed from reference timestamp 2026-04-27T14:55:43Z.

| section_gid | age_seconds | age_human | class |
|---|---|---|---|
| 1143843662099257 | 3,273 | ~54 min | HOT |
| 1199511476245249 | 17,695 | ~4.9h | HOT |
| 1143843662099256 | 104,096 | ~28.9h | WARM |
| 1202496785025459 | 161,690 | ~44.9h | WARM |
| 1208667647433692 | 161,691 | ~44.9h | WARM |
| 1201105736066893 | 424,628 | ~4.9d | COLD |
| 1201131323536610 | 584,940 | ~6.8d | COLD |
| 1207396100287952 | 584,940 | ~6.8d | COLD |
| 1201990715810461 | 604,515 | ~7.0d | COLD |
| 1202005604742382 | 1,328,116 | ~15.4d | COLD |
| 1201990715810462 | 1,559,458 | ~18.0d | COLD |
| 1209233681691558 | 1,559,458 | ~18.0d | COLD |
| 1204152425074370 | 2,052,794 | ~23.7d | COLD |
| 1155403608336729 | 2,803,079 | ~32.4d | COLD |

**Per-class summary**:
- HOT (< 6h / 21,600s): 2 sections
- WARM (6h–48h / 21,600s–172,800s): 3 sections
- COLD (> 48h): 9 sections

**Critical observation**: 9 of 14 sections (64%) exceed the PRD G2 default 6h staleness threshold. The single coldest section (`1155403608336729`) is 32.4 days stale — 130x the threshold. The `active_mrr` aggregate is computed across all sections that contain offer tasks; any ACTIVE sections in the COLD class contribute stale data to the reported `$94,076.00` figure.

**Frequency**: CLI invocation frequency is unknown from code structure alone. It is an internal operator tool. Assumed O(1–10/day) based on use-case ("operator running `python -m autom8_asana.metrics active_mrr`" — PRD §4 US-1). Lambda warmer cadence: UNDOCUMENTED (see Open Questions).

**Hot keys**: Sections `1143843662099257` (62,414 bytes, largest parquet) and `1201105736066893` (109,102 bytes, largest parquet by size) are highest-volume. The largest-by-size section is COLD at 4.9 days — a hot key by data mass with a cold freshness profile.

---

## G2 — Current Cache Architecture Audit

### Architecture snapshot

**Cache layer structure** (file:line evidence):

1. **Entity-level cache (task/subtask/detection/dataframe)**: `src/autom8_asana/cache/integration/factory.py:25-44` — `CacheProviderFactory` with 5-priority detection chain. Production auto-detects Redis if `REDIS_HOST` is set, otherwise falls back to InMemory. Environment gated by `AUTOM8Y_ENV` at `src/autom8_asana/cache/integration/factory.py:36-37`.

2. **DataFrame cache (DataFrameCache)**: `src/autom8_asana/cache/integration/dataframe_cache.py:1-33` — Memory tier + ProgressiveTier (S3). The `DataFrameCacheEntry` dataclass holds a polars DataFrame + watermark-based freshness tracking. SWR rebuild path in `src/autom8_asana/cache/dataframe/factory.py:40-80`.

3. **ProgressiveTier (S3 cold tier)**: `src/autom8_asana/cache/dataframe/tiers/progressive.py:1-60` — translates `{entity_type}:{project_gid}` key to `dataframes/{project_gid}/` prefix. Reads and writes via `SectionPersistence`. This is the persistence layer the parquets at `s3://autom8-s3/dataframes/1143843662099250/sections/` belong to.

4. **S3 cache backend**: `src/autom8_asana/cache/backends/s3.py:35-80` — `S3Config.default_ttl = 604800` (7 days). This is the task-level entity cache TTL, not the parquet DataFrame TTL.

5. **Lambda warmer**: `src/autom8_asana/lambda_handlers/cache_warmer.py:1-905` — entry point `handler`. Warms all entity types sequentially in cascade dependency order (`cascade_warm_order()`). No EventBridge/CloudWatch Events rule present in the Python source. Schedule is managed externally to this file — IaC not found in worktree.

6. **Freshness module** (new, from 10x-dev sprint): `src/autom8_asana/metrics/freshness.py:98-214` — `FreshnessReport.from_s3_listing` performs a `list_objects_v2` paginator probe independently of the DataFrameCache to extract `LastModified` timestamps. This is a read-only observability layer; it does not write to or invalidate the cache.

7. **Staleness coordination (task-level)**: `src/autom8_asana/cache/integration/staleness_coordinator.py:1-60` — `StalenessCheckCoordinator` with `base_ttl=300s`, `max_ttl=86400s`, exponential extension via `ADR-0133`. This is the task-entity cache staleness mechanism, separate from the DataFrame/parquet tier.

8. **Mutation invalidator**: `src/autom8_asana/cache/integration/mutation_invalidator.py:1-60` — `MutationInvalidator` for REST mutation-triggered invalidation. Covers task/subtask/detection entries. Soft invalidation disabled by default (`SoftInvalidationConfig.enabled=False`).

9. **Freshness policy (entity tier)**: `src/autom8_asana/cache/policies/freshness_policy.py:1-60` — `FreshnessPolicy` with three states (FRESH / APPROACHING_STALE / STALE); `approaching_threshold=0.75` of entity TTL.

### Pattern classification

The DataFrame/parquet tier implements **cache-aside** (Lambda warms; CLI reads directly from S3). The entity-level cache (task/subtask) implements **read-through** with optional **staleness-check extension** (Asana Batch API `modified_at` probe before hard eviction). No event-driven invalidation for the parquet DataFrame tier.

### Consistency model

**Eventual** — the parquet is written by Lambda, read by CLI. No causal ordering guarantee between write and read events. The 10x-dev freshness signal (`FreshnessReport`) makes this visible at runtime, but does not enforce it.

### Failure modes (current)

| Scenario | Current behavior |
|---|---|
| Cache miss (no parquet) | `load_project_dataframe` raises `ValueError`/`FileNotFoundError`; CLI exits 1 (HANDOFF:187, `__main__.py:239`) |
| Cache stale (old parquet) | Data is served, `FreshnessReport` emits WARNING to stderr; exits 0 unless `--strict` passed (`freshness.py:90-96`) |
| Warmer Lambda failure | Parquet ages in place; no re-warm trigger exists beyond the next scheduled invocation; no documented SLA |
| S3 unavailability | `FreshnessError` raised and surfaced per AC-4.x (`freshness.py:158-182`); botocore `ClientError(NoSuchBucket)` NOT caught upstream of `load_project_dataframe` at `__main__.py:234-241` (MINOR-OBS-2) |
| Warmer timeout | Checkpoint-based resume via `CheckpointManager`; self-invocation continuation (`cache_warmer.py:399-425`) |

### Anti-pattern audit

**Anti-pattern 1: Invisible invalidation**
- The parquet DataFrame tier has no invalidation trigger from Asana state changes. The `MutationInvalidator` covers task/subtask/detection entry types (`mutation_invalidator.py:36`) but NOT the DataFrame parquet writes. A section moving tasks between states in Asana will not trigger a parquet re-write until the next Lambda warm cycle.
- **Severity**: HIGH (decision-grade financial metric, 32-day observed staleness)
- **Location**: `src/autom8_asana/cache/integration/mutation_invalidator.py:36` — `_TASK_ENTRY_TYPES` excludes DataFrame type

**Anti-pattern 2: Undocumented warmer schedule (D10)**
- `src/autom8_asana/lambda_handlers/cache_warmer.py` contains no EventBridge rule or schedule expression. No IaC (Terraform `.tf`, SAM template, CDK) was found in the worktree (bash probe: zero results for `*.tf`, `serverless*.yml`, `template*.yml`, `cdk*` containing `cache_warmer`).
- **Severity**: HIGH — the frequency of re-warm is the primary control lever for freshness SLA compliance. Absence of documentation means the observed 32-day staleness cannot be attributed to a schedule failure vs. expected behavior.
- **Flagged explicitly per RR-2 and dossier §5**: `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md:115-121`

**Anti-pattern 3: TTL mismatch between tiers**
- `S3Config.default_ttl = 604800` (7 days) is set at `src/autom8_asana/cache/backends/s3.py:46` for the task-entity S3 backend. The `StalenessCheckSettings.max_ttl = 86400` (24h) is the task-entity in-memory ceiling (`staleness_settings.py:48`). Neither of these applies to the parquet DataFrame tier — the parquet tier has no configured TTL. The Lambda warmer alone controls when parquets are refreshed, and its cadence is undocumented.
- **Severity**: MEDIUM — creates the illusion of TTL discipline where none exists for the DataFrame tier

**Anti-pattern 4: Band-aid freshness signal**
- The `FreshnessReport.from_s3_listing` probe (added by 10x-dev) is a monitoring layer that surfaces the staleness problem without addressing it. This is the correct design for P1 (signal before enforcement), but it means the P2 architecture must close the enforcement gap. The 6h default threshold is already breached by 9/14 sections — the warning fires on every current invocation.
- **Severity**: LOW (by design; P2 must address)

---

## G3 — Alternatives Assessment

### Hot path: active_mrr freshness (primary path)

| Alternative | Feasibility | Expected Impact | Effort | Assessment |
|---|---|---|---|---|
| Query optimization | LOW | No benefit — origin is S3 parquet (not a queryable DB). No indexes, no joins to optimize. | N/A | DISMISS |
| Materialized views | LOW | Parquet IS the materialized view. Re-materializing into another format adds complexity without addressing staleness. | HIGH | DISMISS |
| Connection pooling | LOW | CLI invocations are short-lived processes; connection overhead is not the bottleneck. | N/A | DISMISS |
| CDN / edge caching | LOW | Internal operator CLI, not browser-served content. CDN does not apply. | N/A | DISMISS |
| Read replicas | LOW | No relational database in this path. S3 is globally durable. | N/A | DISMISS |
| Denormalization | LOW | Parquet files already denormalize the Asana task data. Further denormalization does not address freshness. | N/A | DISMISS |
| **Event-driven re-warm via Asana webhooks** | MEDIUM | Push invalidation triggered by Asana section-move events would reduce max staleness from days to minutes for ACTIVE sections. Requires webhook registration + Lambda consumer + circuit-breaker. Cost: medium engineering effort, Asana webhook API stability risk. | HIGH | VIABLE-ALTERNATIVE (see below) |
| **Refresh-ahead (XFetch, CACHE:SRC-001)** | MEDIUM | Probabilistic early re-warm when parquet is near-expiry would reduce stampede risk at re-warm time. Applicable at DataFrameCache memory tier, not the S3 parquet tier directly. Complements scheduled re-warm but does not replace it. | LOW-MEDIUM | VIABLE-AUGMENTATION |
| **Multi-tier hot+warm+cold in-memory hot** | LOW-MEDIUM | An in-memory hot tier already exists (DataFrameCache `MemoryTier`). Adding Redis warm tier adds complexity. Freshness problem is at the S3 cold tier; adding warm tiers above it does not fix staleness at origin. | HIGH | DISMISS for freshness problem; VIABLE for latency |
| **Operationalize-as-is (TTL discipline + telemetry + force-warm + SLA alerting)** | HIGH | Adds documentation of warmer schedule, per-section TTL targets, force-warm CLI affordance (PRD NG4), alerting on `max_mtime > SLA threshold`. Baseline: no new components, additive instrumentation only. | LOW | RECOMMENDED PRIMARY |

### Event-driven re-warm analysis (SQ-1 secondary verdict trigger assessment)

Asana webhook-driven invalidation would be the most architecturally pure solution: push invalidation on section-move events eliminates the staleness window entirely. However:
- Asana webhooks require per-resource registration, heartbeat management, and deduplication. This is a meaningful implementation surface beyond the operationalize scope.
- The staleness observed (32 days) is more likely attributable to an undocumented or misconfigured warmer schedule than to an architectural limitation — the warmer Lambda already implements checkpoint-based resume and success metric emission (`DMS_NAMESPACE = "Autom8y/AsanaCacheWarmer"`, `cache_warmer.py:70`). A dead-man's-switch alert at 24h is already wired (`cache_warmer.py:843-845`). If the DMS alert fires and no one responds, that is an operational gap, not a caching architecture gap.
- The `active_mrr` metric changes slowly (subscription churn cadence, not transaction-per-second). A 6h staleness threshold is likely appropriate for business decisions; reducing to near-zero via webhooks would be disproportionate.
- **Verdict**: Event-driven re-warm is a viable future-procession candidate, but does NOT score clearly enough above the operationalize baseline to mandate redesign NOW per SQ-1. The current architecture with documented schedule + TTL discipline + force-warm + SLA alerting is sufficient for the parent telos discharge by 2026-05-27.

### Verdict

**OPERATIONALIZE** — the existing architecture is sufficient when augmented with:
1. Documented warmer schedule (D10 closure)
2. Per-section TTL targets (derived from G4 budget)
3. Force-warm CLI affordance (PRD NG4)
4. SLA alerting (section max_mtime > threshold triggers dead-man's-switch extension)
5. Section-coverage telemetry (D5)

Event-driven re-warm is logged as a recommended follow-up procession candidate but does not satisfy the "clearly-better alternative" bar required to trigger REDESIGN per SQ-1.

---

## G4 — Freshness Budget

### Source evidence

- PRD G2: 6h staleness default — `verify-active-mrr-provenance.prd.md:70-71`
- PRD G3: `--strict` semantics (stale → non-zero exit) — `prd.md:74-78`
- Observed max staleness: 32.4 days (`1155403608336729.parquet`, mtime-histogram JSON row 3)

### Section-class budget allocation

| Section class | Criteria | Staleness tolerance | Rationale |
|---|---|---|---|
| ACTIVE sections (offer classifier) | Mapped to `AccountActivity.ACTIVE` per `activity.py:76+317` — 3 named sections | 6h (PRD default) | Direct contributors to `active_mrr` dollar figure; financial decision-grade data |
| Non-ACTIVE / informational sections | Not in ACTIVE classifier output | 24h | Do not contribute to `active_mrr` computation; may be needed for completeness signal |
| Archived / near-empty sections (< 2500 bytes) | `1204152425074370` (2449 bytes), `1209233681691558` (2449 bytes) | 7d | Minimal data, presumably inactive sections; staleness matters least |

**Classifier cross-reference**: The three ACTIVE section names (`active`, `restart - request testimonial`, `run optimizations`) at `activity.py:76` map to some subset of the 14 observed GIDs. The section GID to section name mapping requires an Asana API call or the parquet metadata itself; this mapping is not available from the dossier alone.

**DEFER tag**: Which specific GIDs from the 14-parquet inventory are ACTIVE-classifier-mapped is not ascertainable from static analysis. Capacity-engineer (P3) must obtain the GID-to-name mapping to apply per-GID TTL targets.

[UNATTESTED — DEFER-POST-HANDOFF: GID-to-section-name mapping required to assign ACTIVE vs. non-ACTIVE TTL class per GID | METHOD: Asana API call or parquet metadata read at P3 | REASON: mapping not available in dossier or code at P1 altitude]

### Consistency model per use case

Per CACHE:SRC-003 (Brewer CAP, STRONG): the system already accepts eventual consistency (parquet is written asynchronously by Lambda; read by CLI without ordering guarantee). This is appropriate because:
- The consumer (human operator / downstream automation) uses `active_mrr` for business decisions, not real-time transaction gating
- Staleness is now VISIBLE via the freshness signal (10x-dev contribution)
- The `--strict` flag provides a mechanically-gated escape valve for CI consumers who require freshness enforcement

Per CACHE:SRC-004 (Lamport): sequential consistency is NOT required at the metric-aggregation layer. The parquet represents a point-in-time snapshot; the operator is informed of the snapshot age.

**Consistency verdict**: EVENTUAL is sufficient. FreshnessReport makes staleness visible; `--strict` makes it enforceable. No architectural change to consistency model is required for P2.

---

## G5 — Consistency Tolerance

| Use case | Consumer | Staleness tolerance | Consistency model | Verdict |
|---|---|---|---|---|
| Operator CLI default mode | Human operator | 6h (configurable) | Eventual + freshness signal | TOLERABLE |
| CI gate with `--strict` | Automated pipeline | Configurable threshold | Eventual + enforced exit-1 | TOLERABLE — CI operator sets threshold |
| Downstream automation via `--json` | Parsing tool | Configurable threshold | Eventual + JSON envelope | TOLERABLE |
| SLA alerting (design by P4) | Monitoring system | Alert fires on threshold breach | Eventual + alerting SLO | TOLERABLE |
| Financial reporting / investor | Human (high-stakes) | Near-real-time | Would require webhook invalidation | FLAG for user adjudication |

**Flag — financial reporting use case**: If `active_mrr` is used for investor reporting or binding financial commitments (not just internal operator dashboards), the 6h-default threshold may be insufficient and event-driven re-warm should be re-evaluated. This is a business decision, not a technical one. Surfacing to user for adjudication.

[USER-ADJUDICATION-REQUIRED: Is `active_mrr` used for investor-grade reporting or binding financial commitments where 6h staleness is unacceptable? If YES, event-driven re-warm (Asana webhooks) becomes load-bearing; if NO (internal dashboards only), operationalize verdict holds.]

---

## G6 — Cost / Complexity Envelope

### Operationalize-as-is (augmented baseline)

| Component | Cost estimate | Complexity |
|---|---|---|
| Force-warm CLI affordance (PRD NG4) | Lambda invocation cost x invocation count. At ~$0.000017/invocation (Lambda standard), a 6-entity warm is negligible per invocation. Monthly upper bound at 10 forced re-warms/day: $0.05/month. | LOW — CLI flag + Lambda invoke SDK call |
| SLA alerting (CloudWatch alarm on DMS metric) | CloudWatch alarm evaluation: ~$0.10/alarm/month at standard resolution. One alarm per SLA dimension. | LOW — alarm config only, DMS already emits at `cache_warmer.py:843-845` |
| Warmer schedule documentation | Zero incremental cost. | MINIMAL — IaC audit + ADR |
| Per-section TTL targets (capacity spec) | Zero incremental runtime cost. | LOW — configuration + documentation |
| Section-coverage telemetry (D5) | CloudWatch metric emit per invocation: negligible at operator invocation frequency. | LOW — instrumentation in freshness CLI |
| Dead-man's-switch at 24h (already wired) | Already emitting (`cache_warmer.py:70, 843-845`). No incremental cost. | ZERO — already shipped |

### Event-driven re-warm alternative (comparison)

| Component | Cost estimate | Complexity |
|---|---|---|
| Asana webhook registration | Free from Asana; Lambda invocation per event. At 100 Asana events/day: $0.17/month Lambda cost. | HIGH — webhook lifecycle management, deduplication, retry, heartbeat |
| Webhook consumer Lambda | Additional Lambda function | MEDIUM — new function, IAM, monitoring |
| Invalidation coordination | Must invalidate parquet + in-memory tier consistently | HIGH — distributed invalidation race conditions |
| Engineering effort | New rite procession scope | HIGH |

**Complexity verdict**: Operationalize baseline is 4–5x lower engineering complexity than event-driven re-warm, with a cost difference of < $0.50/month. The operationalize path is the correct primary choice per SQ-1.

---

## 6-Gate Summary

| Candidate | Freq | Cost | Stale | UX | Safety | Scale | Verdict |
|---|---|---|---|---|---|---|---|
| active_mrr parquet freshness SLA | PASS (CLI invocations, automated consumers) | PASS (S3 list_objects is cheap; Lambda warm is batch) | PASS-WITH-FLAG (6h configurable; 32d observed breach; eventual is acceptable with signal) | PASS (freshness signal now visible; `--strict` enforces) | PASS (financial metric but internal; no PII in parquet tier itself; stakeholder affirmation on bucket identity) | PASS (14 parquets, bounded key space, linear growth) | CACHE — OPERATIONALIZE |

**Gate detail**:

- **Frequency (PASS)**: Every CLI invocation reads from the parquet tier. DataFrameCache SWR rebuild also reads. Frequency is sufficient to justify the existing cache investment.
- **Computation cost (PASS)**: Origin fetch = full Asana API page traversal for all tasks in a project. Lambda warm for offer entity type completes in seconds to minutes. Caching eliminates O(N) API calls per CLI invocation where N = task count.
- **Staleness tolerance (PASS-WITH-FLAG)**: Default 6h is PRD-declared acceptable. Operator can tighten with `--staleness-threshold`. The 32-day observed staleness is a warmer schedule gap, not an architectural impossibility. Financial-reporting use case flagged for user adjudication above.
- **UX impact (PASS)**: Without cache, CLI latency would be minutes (API traversal). With cache, milliseconds (parquet read). User-visible impact is high — caching is load-bearing for the UX.
- **Safety (PASS)**: No PII is stored in the parquet files based on the metrics use case (aggregated MRR by section). Bucket is production-confirmed by stakeholder affirmation (`prd.md:261-267`). No multi-tenant isolation concern (single workspace). Redis task-entity cache may carry task metadata with customer contact data but that is the entity tier, not the parquet tier — out of scope for this assessment.
- **Scale (PASS)**: 14 parquets at handoff time. Key space is bounded by number of Asana sections in the offer project. Growth is linear (new sections = new parquets). No exponential cardinality concern.

---

## Q1 — Architecture Sufficiency Verdict

**PRIMARY VERDICT: OPERATIONALIZE**

The existing cache architecture (Lambda warmer + ProgressiveTier S3 parquets + DataFrameCache in-memory + freshness signal CLI) is sufficient for parent telos discharge by 2026-05-27 when augmented with:

1. **TTL discipline**: Document warmer schedule (D10 closure by P3); define per-section-class TTL targets; wire schedule to a documented EventBridge rule or equivalent.
2. **Telemetry**: Section-coverage telemetry (D5); SLI emission per invocation.
3. **Force-warm CLI affordance**: PRD NG4 — operator-accessible Lambda invocation path.
4. **SLA alerting**: Extend dead-man's-switch (already at `cache_warmer.py:70,843-845`) to per-section staleness alerting; P4 thermal-monitor designs SLO.

**SECONDARY VERDICT: NOT TRIGGERED**

No G3 alternative scores clearly enough above the operationalize baseline to require a redesign-recommendation spike. Event-driven re-warm via Asana webhooks is logged as a recommended follow-up procession candidate in the Deferred Decisions section, not a primary recommendation. The `.ledge/spikes/cache-architecture-redesign-recommendation-2026-04-27.md` artifact is NOT produced.

---

## Q3 — D7 Disposition (Env-Matrix Legacy-Cruft)

**Source**: `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md:139-163` (12-match inventory from `rg -n 'AUTOM8Y_ENV|autom8-s3-(staging|dev|prod)' src/`)

| # | file:line | matched_text | cache-architecture-relevant? | Disposition |
|---|---|---|---|---|
| 1 | `src/autom8_asana/models/base.py:14` | `# for test clarity. Controlled via AUTOM8Y_ENV.` | NO | cleanup-shaped |
| 2 | `src/autom8_asana/models/base.py:17` | `if os.environ.get("AUTOM8Y_ENV", "production") not in ("test", "local", "LOCAL")` | NO | cleanup-shaped |
| 3 | `src/autom8_asana/cache/integration/factory.py:32` | `4. Environment-based auto-detection (AUTOM8Y_ENV)` | CONDITIONAL — see note | see note |
| 4 | `src/autom8_asana/cache/integration/factory.py:36` | `- AUTOM8Y_ENV=production/staging: Prefer Redis if REDIS_HOST configured` | CONDITIONAL — see note | see note |
| 5 | `src/autom8_asana/cache/integration/factory.py:37` | `- AUTOM8Y_ENV=local/test or not set: Use InMemory` | CONDITIONAL — see note | see note |
| 6 | `src/autom8_asana/api/models.py:44` | `if os.environ.get("AUTOM8Y_ENV", "production") not in ("test", "local", "LOCAL")` | NO | cleanup-shaped |
| 7 | `src/autom8_asana/settings.py:554` | `# Override autom8y_env with explicit alias so AUTOM8Y_ENV is read directly` | NO | cleanup-shaped |
| 8 | `src/autom8_asana/settings.py:560` | `"AUTOM8Y_ENV", # canonical (Tier 1)` | NO | cleanup-shaped |
| 9 | `src/autom8_asana/settings.py:590` | `with ASANA_CW_ENVIRONMENT to avoid collision with AUTOM8Y_ENV.` | NO | cleanup-shaped |
| 10 | `src/autom8_asana/settings.py:801` | `# SDK-standard environment field. AUTOM8Y_ENV is the canonical Tier 1 name.` | NO | cleanup-shaped |
| 11 | `src/autom8_asana/settings.py:805` | `"AUTOM8Y_ENV", # canonical (Tier 1)` | NO | cleanup-shaped |
| 12 | `src/autom8_asana/settings.py:845` | `Uses the explicit-only pattern: only fires when AUTOM8Y_ENV` | NO | cleanup-shaped |

**Note on items 3–5 (factory.py)**: `CacheProviderFactory` uses `AUTOM8Y_ENV` in its auto-detection chain (Tier 4: `AUTOM8Y_ENV=production/staging → Redis if REDIS_HOST set`). This is a cache-architecture-adjacent reference, not a cache-architecture-critical one. The PRD already affirms there is one production bucket, no multi-env buckets. The `AUTOM8Y_ENV` detection in `factory.py` is used to select the Redis vs. InMemory provider for the task-entity cache, not for the parquet DataFrame tier. Replacing it with a simpler `settings.is_production` check (already used at `factory.py:153`) is hygiene-shaped cleanup, not a cache-architecture decision. This does not warrant user adjudication.

**D7 disposition confirmed**: All 12 items are cleanup-shaped. No item is cache-architecture-load-bearing. Factory items 3–5 are cache-adjacent but are self-consistent with the existing architecture and carry no freshness-SLA risk. Secondary handoff to hygiene rite is confirmed per SQ-2 presumption. Thermia will produce a structured hygiene handoff dossier containing this 12-item inventory.

---

## Q5 — Pre-Existing Observations Triage

### MINOR-OBS-1 — xdist test flake

**Source**: `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md:186`
**Test**: `tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order`
**Nature**: Hypothesis property test fails intermittently under xdist parallel execution; passes deterministically in isolation.

**Assessment**: Not cache-architecture-relevant. The test exercises ordering logic in persistence, not cache freshness or invalidation. The failure mode (xdist scheduling non-determinism with Hypothesis seed) is a test-infrastructure issue.

**Confirmed disposition: HYGIENE HANDOFF** — carry into the D7/hygiene secondary-handoff dossier. No thermal-monitor or thermia-architecture impact.

### MINOR-OBS-2 — botocore traceback on bucket-typo

**Source**: `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md:187`
**Location**: `src/autom8_asana/metrics/__main__.py:234-241`
**Nature**: `load_project_dataframe` raises raw `botocore.exceptions.ClientError(NoSuchBucket)` traceback when `ASANA_CACHE_S3_BUCKET` is set to a non-existent bucket. The existing handler at line 239 catches only `(ValueError, FileNotFoundError)`. The freshness module's own AC-4.2 `not-found` mapping at `freshness.py:164-177` is correct but reached AFTER the bucket-existence check.

**Assessment**: Cache-architecture-adjacent. This is a UX gap in the operator error path, not a caching correctness issue. However, it is directly relevant to force-warm CLI affordance design (PRD NG4) — if a force-warm CLI invocation hits a misconfigured bucket, it must surface actionable errors. The P2 systems-thermodynamicist and P4 thermal-monitor should account for this when designing the force-warm error path and SLA alerting.

**Confirmed disposition: THERMIA ABSORBS (UX shape)** per dossier §8.2 default. Recommend extending the exception handler at `__main__.py:239` to include `botocore.exceptions.ClientError` with `NoSuchBucket` mapping — this is a one-line fix but is implementation-territory (10x-dev re-handoff, P6). Surfaced to P2 and P4 as a known UX gap in the force-warm error path design.

---

## Strategic Anchors for Downstream Specialists

### For systems-thermodynamicist (P2)

**Pattern selection candidates (ranked)**:

1. **Cache-aside (existing)** — Lambda warms S3; CLI reads. Appropriate for batch, compute-heavy origin data (full Asana project traversal). Continuation is natural.
2. **Refresh-ahead augmentation (CACHE:SRC-001, XFetch, STRONG grade)** — Applicable at the DataFrameCache `MemoryTier` layer. When the MemoryTier entry's `staleness_ratio` exceeds the `approaching_threshold` (currently 0.75 at `freshness_policy.py:56`), a background SWR rebuild can be triggered before the entry goes fully stale. The SWR callback is already wired in `factory.py:40-80`. This is a low-effort augmentation to the existing architecture that reduces cold-miss latency at ECS preload.
3. **Read-through for force-warm path** — The force-warm CLI affordance (PRD NG4) should trigger a Lambda invocation that warms all ACTIVE-classifier sections synchronously (or with a status poll). This is not a pattern change but a new entry point to the existing write path.

**Consistency model recommendation**: EVENTUAL — confirmed appropriate per G5. The freshness signal is now visible; `--strict` gate provides enforcement. No architectural change needed.

**Failure-mode behaviors per layer**:

| Layer | Cache miss | Cache stale | Warmer failure | S3 unavailability |
|---|---|---|---|---|
| DataFrameCache MemoryTier | Falls through to ProgressiveTier (S3 read) | Serve + SWR background rebuild | Parquet ages; no re-trigger | S3 `ClientError` to `FreshnessError` |
| ProgressiveTier (S3 parquet) | `FileNotFoundError` to CLI exits 1 | Data served with freshness WARNING | Parquet ages; DMS fires at 24h | `ClientError(NoSuchBucket)` — NOT caught at `__main__.py:239` (MINOR-OBS-2) |
| Lambda warmer | — | DMS alert at `Autom8y/AsanaCacheWarmer` namespace | Checkpoint + self-invoke continuation | `WarmResponse(success=False)` |
| Freshness probe | `parquet_count=0` sentinel | `FreshnessReport.stale=True` | N/A (read-only probe) | `FreshnessError.KIND_NOT_FOUND` |

**Force-warm CLI affordance sketch (PRD NG4)**:
- New flag `--force-warm` (or subcommand) on `python -m autom8_asana.metrics`
- Invokes Lambda `handler` via AWS SDK (boto3 Lambda invoke)
- Polls response or returns immediately (fire-and-forget with DMS confirmation)
- Should handle MINOR-OBS-2 bucket-typo case gracefully before invoking Lambda

### For capacity-engineer (P3)

**Per-section TTL scaling guidance**:

| Class | Sections | Recommended TTL target | Rationale |
|---|---|---|---|
| ACTIVE (offer classifier, 3 named) | GID mapping DEFERRED (see G4 DEFER tag) | 6h (PRD default) | Financial metric consumers; matches PRD G2 |
| WARM (other sections, 6–48h current age) | 3 sections observed | 12h | Informational; relaxed threshold acceptable |
| COLD (aged > 48h, likely stable sections) | 9 sections observed | 24–72h | Minimal churn; long TTL acceptable |
| Near-empty sections (< 2500 bytes) | 2 sections observed | 7d | Presumably inactive; archival retention |

**Working-set sizing inputs**:
- 14 parquet objects at handoff time; bounded by Asana section count
- Largest parquet: `1201105736066893` at 109,102 bytes — well within S3 object cost floor
- Total parquet data: ~292KB across all 14 sections — negligible S3 cost
- Per-invocation freshness probe: 1 `list_objects_v2` page (14 objects, single page at S3 1,000-object page limit)

**Force-warm cost envelope**:
- Lambda invocation: ~$0.000017/invocation (128MB default tier)
- Warm execution: multi-entity warm completes in seconds to ~2 minutes based on `WarmDuration` metric emission at `cache_warmer.py:480-483`
- At 10 force-warms/day: Lambda cost approx $0.05/month; S3 write cost approx negligible (292KB x 10 = ~3MB/day)

**Stampede protection candidate**: Lease tokens per CACHE:SRC-002 (Nishtala et al. 2013, STRONG grade). The `DataFrameCacheCoalescer` already exists at `src/autom8_asana/cache/dataframe/coalescer.py` — this is the existing mechanism. P3 should verify the coalescer is correctly wired for the force-warm path to prevent multiple concurrent force-warms issuing simultaneous Lambda invocations.

**Per-section TTL implementation anchor**: The warmer currently does not persist a per-section TTL anywhere in the observable state (no TTL metadata in the parquet `LastModified` timestamp). P3 must decide whether TTL tracking should be implemented as (a) a metadata sidecar in S3, (b) a CloudWatch metric per section, or (c) a watermark manifest alongside the parquet.

### For thermal-monitor (P4)

**SLI candidates**:

1. `max_mtime` per invocation — the oldest `LastModified` timestamp across all ACTIVE-classifier parquets. Currently computed by `FreshnessReport.max_age_seconds` at `freshness.py:202`. Emit as a CloudWatch metric per CLI invocation.
2. Force-warm latency — time from `--force-warm` invocation to successful `DMS_NAMESPACE` metric emission. Measured by comparing force-warm trigger timestamp to next DMS success timestamp.
3. Warmer success rate — `WarmSuccess` vs `WarmFailure` CloudWatch metrics already emitted at `cache_warmer.py:473,501`. P4 designs SLO threshold (e.g., 95% success rate over rolling 7-day window).
4. `FreshnessError` rate — rate of `FreshnessError` exceptions surfaced to CLI operators (auth/network/not-found errors). Indicates S3 access health.

**SLO candidates (per PRD G2 6h default)**:

| SLO | Target | Breach action |
|---|---|---|
| `max_mtime` for ACTIVE sections | < 6h at 95th percentile | Alert to force-warm trigger |
| Warmer success rate | >= 95% over 7-day rolling | Alert to on-call |
| DMS heartbeat (24h) | At least 1 success per 24h | Alert already wired (`cache_warmer.py:843-845`) |

**Section-coverage telemetry hooks (D5 discharge)**:
- Emit a CloudWatch metric `SectionCount` (observed parquet count = 14 at handoff) per warmer invocation
- Emit `SectionAgeP95` (95th percentile parquet age in seconds) per CLI invocation from `FreshnessReport`
- Diff classifier section count vs. parquet count and emit `SectionCoverageDelta` (informational — not a failure signal per PRD C-6)
- The empty-sections-are-expected rule (`PRD §6 C-6`) must be encoded in the telemetry so `SectionCoverageDelta > 0` does not trigger a false alert

**MINOR-OBS-2 for P4**: The botocore traceback gap at `__main__.py:239` means some operator error conditions produce unparseable stderr output. If SLA alerting includes parsing CLI stderr (e.g., via Lambda-invoked healthcheck), the alert logic must tolerate raw botocore tracebacks from the bucket-typo case until MINOR-OBS-2 is fixed in P6.

---

## Anti-Pattern Register (existing caches)

### AP-1: Undocumented warmer schedule

- **Location**: `src/autom8_asana/lambda_handlers/cache_warmer.py:1` — handler function; scheduling expression not in code
- **Risk**: Cannot audit whether observed 32-day staleness represents a schedule failure or expected behavior. SLA cannot be formally defined without known cadence.
- **Severity**: HIGH

### AP-2: No per-section TTL enforcement

- **Location**: `ProgressiveTier` write path; `src/autom8_asana/cache/dataframe/tiers/progressive.py` — no TTL metadata written alongside parquet
- **Risk**: A section that stops receiving tasks will never have its parquet evicted; it ages indefinitely. This is observed in practice (`1155403608336729` = 32 days, `1204152425074370` = 23.7 days).
- **Severity**: MEDIUM (mitigated by freshness signal; unmitigated before 10x-dev sprint)

### AP-3: MutationInvalidator excludes DataFrame tier

- **Location**: `src/autom8_asana/cache/integration/mutation_invalidator.py:36` — `_TASK_ENTRY_TYPES` = `[EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]`
- **Risk**: An Asana task mutation (e.g., section move) invalidates the task-entity cache but NOT the parquet DataFrame. The financial aggregate can serve a stale value that reflects the pre-move section assignment.
- **Severity**: HIGH — but not addressable in the operationalize path (requires either webhook invalidation or accepting eventual consistency window). Document as known gap.

---

## Recommended Cache Layers

The following layer is confirmed as the architecture to operationalize:

1. **S3 parquet cold tier** (ProgressiveTier) — OPERATIONALIZE with TTL documentation + schedule audit
2. **DataFrameCache MemoryTier** — OPERATIONALIZE; verify SWR wiring for force-warm path
3. **Freshness probe** (FreshnessReport) — OPERATIONALIZE; add section-coverage telemetry (D5)

The following layers are out of scope for this assessment (not related to `active_mrr` freshness):
- Task-entity Redis/InMemory cache — passes 6-gate independently; no freshness issue observed
- Story cache — separate warm path; not assessed here

---

## Deferred Decisions

| # | Decision | Required by | Owner |
|---|---|---|---|
| DEF-1 | GID-to-section-name mapping for ACTIVE classifier sections — which of the 14 GIDs are ACTIVE-classifier-mapped? | P3 per-section TTL assignment | Capacity-engineer (Asana API call or parquet metadata read) |
| DEF-2 | Warmer schedule audit — what is the current EventBridge/CloudWatch Events rule for `cache_warmer`? | D10 closure | P3 capacity-engineer (IaC inspection outside worktree) |
| DEF-3 | Is `active_mrr` used for investor-grade reporting or binding financial commitments? | G5 financial-reporting use-case flag | USER-ADJUDICATION-REQUIRED |
| DEF-4 | Force-warm CLI affordance design (PRD NG4) — fire-and-forget vs. synchronous with status poll? | P2 systems-thermodynamicist | Potnia to include in P2 scope |
| DEF-5 | Event-driven re-warm (Asana webhooks) — recommended follow-up procession scope | Future procession | Potnia at next procession kickoff |
| DEF-6 | MINOR-OBS-2 fix — extend `__main__.py:239` exception handler to cover `ClientError(NoSuchBucket)` | P6 10x-dev re-handoff | 10x-dev; flag to P4 for UX alert design |

---

## Open Questions Surfaced (Procession-Completion Risks)

**RR-2 (schedule undocumented)**: The cache_warmer Lambda has no documented schedule in any source file within the worktree. IaC search returned zero results for Terraform, SAM, or CDK files referencing `cache_warmer`. This is the primary procession-completion risk: if the schedule cannot be established from IaC inspection (outside the worktree or in a sibling repo), the D10 closure requires stakeholder interview.

**Evidence grade note**: The access-frequency analysis (G1) is based on structural heuristics from the dossier and mtime histogram, not production metrics or logs. The "O(1–10/day) CLI invocation" estimate is a [PLATFORM-HEURISTIC] — actual frequency may differ. Thermal-monitor (P4) should establish actual invocation frequency as part of SLI baseline.

---

*Authored by heat-mapper, thermia procession P1, session-20260427-185944-cde32d7b, 2026-04-27. All file:line anchors reference `.worktrees/thermia-cache-procession/` as root.*
