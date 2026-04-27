---
type: spec
artifact_type: ADR
status: accepted
adr_number: 006
adr_id: ADR-006
title: CloudWatch namespace strategy for cache-freshness emissions
authored_by: 10x-dev.architect
authored_on: 2026-04-27
session_id: session-20260427-205201-668a10f4
parent_initiative: cache-freshness-impl-from-thermia-2026-04-27
schema_version: 1
worktree: .worktrees/cache-freshness-impl/
branch: feat/cache-freshness-impl-2026-04-27
companion_handoff: .ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md
companion_specs:
  - .ledge/specs/cache-freshness-observability.md
  - .ledge/specs/cache-freshness-architecture.tdd.md
discharges:
  - thermia HANDOFF §1 work-item-4 (CloudWatch metric emissions)
  - P4 observability §1-§3 namespace + alarm assignments
  - PRD §6 C-6 guard (SectionCoverageDelta NO alarm)
---

# ADR-006 — CloudWatch namespace strategy for cache-freshness emissions

## Status

**Accepted** — 2026-04-27. Engineer dispatch can proceed; the namespace
choice and alarm-vs-metric matrix below are normative.

## Context

Thermia HANDOFF §1 work-item-4 codifies six CloudWatch metric emissions:
five from the CLI plus one from the coalescer. Per HANDOFF §1 and P4
observability §1-§3:

| # | Metric | Emitted by | Source anchor |
|---|---|---|---|
| 1 | `MaxParquetAgeSeconds` | CLI | `FreshnessReport.max_age_seconds` (`freshness.py:202`) |
| 2 | `ForceWarmLatencySeconds` | CLI | New (per FLAG-1 boundary) |
| 3 | `SectionCount` | CLI | `FreshnessReport.parquet_count` (`freshness.py:153`) |
| 4 | `SectionAgeP95Seconds` | CLI | New (requires `from_s3_listing` enhancement at `freshness.py:142-157`) |
| 5 | `SectionCoverageDelta` | CLI | New (informational only; NO alarm per PRD §6 C-6) |
| 6 | `CoalescerDedupCount` | DataFrameCacheCoalescer | New (`coalescer.py`) |

P4 observability spec assumes namespace `Autom8y/FreshnessProbe` for the
CLI metrics (lines 168, 193, 289, 299, 308, 498, 573, 587, 692). The
`CoalescerDedupCount` metric's namespace is left unspecified.

Three CloudWatch namespaces are already in flight in the fleet:

| Existing namespace | Owner | Source |
|---|---|---|
| `Autom8y/AsanaCacheWarmer` | Lambda DMS dead-man's-switch | `cache_warmer.py:70` (`DMS_NAMESPACE`) |
| `autom8y/cache-warmer` (lowercase) | Lambda generic warm metrics | Set in Terraform `ASANA_CW_NAMESPACE` env var, `terraform/services/asana/main.tf:265` |
| `autom8y/unit-reconciliation` (lowercase) | Unit-reconciliation Lambda | Terraform `terraform/services/asana/main.tf:419` |

The architectural question this ADR closes: **which namespace(s) carry
the six new metrics, what is the alarm-vs-metric matrix, and how does
the namespace choice interact with the C-6 guard?**

If the engineer is left to decide during implementation, three silent
choices loom:
1. Default to `Autom8y/FreshnessProbe` for all six (collapsing the CLI
   vs coalescer distinction).
2. Wire an alarm to `SectionCoverageDelta` because it "looks alertable"
   (violating C-6).
3. Mix capitalization conventions (Pascal `Autom8y/X` vs lowercase
   `autom8y/x`) without realizing the fleet is already inconsistent.

This ADR closes all three before the engineer touches code.

## Decision

**Single namespace for all CLI freshness metrics: `Autom8y/FreshnessProbe`.
Coalescer metric lands in the existing Lambda namespace
`autom8y/cache-warmer` (the warmer's runtime namespace, NOT the DMS
namespace). Five-of-six metrics inform; one alarms. SectionCoverageDelta
is explicitly NO ALARM per PRD C-6 guard.**

### Namespace assignment table

| Metric | Namespace | Emitter | Justification |
|---|---|---|---|
| `MaxParquetAgeSeconds` | `Autom8y/FreshnessProbe` | CLI | Probe metric for CLI-altitude freshness signal |
| `ForceWarmLatencySeconds` | `Autom8y/FreshnessProbe` | CLI | Probe metric measured CLI-to-CLI per FLAG-1 boundary |
| `SectionCount` | `Autom8y/FreshnessProbe` | CLI | Probe metric for fleet sizing observation |
| `SectionAgeP95Seconds` | `Autom8y/FreshnessProbe` | CLI | Probe metric for distribution-aware staleness |
| `SectionCoverageDelta` | `Autom8y/FreshnessProbe` | CLI | Informational only — NO ALARM (C-6) |
| `CoalescerDedupCount` | `autom8y/cache-warmer` | DataFrameCacheCoalescer | Runtime metric inside the cache warm path; aligns with existing warmer-namespace convention (lowercased per Terraform `ASANA_CW_NAMESPACE`) |

The capitalization mismatch (`Autom8y/FreshnessProbe` Pascal/CamelCase
vs `autom8y/cache-warmer` lowercased-kebab) is **intentional and
inherited**. The CLI metrics adopt the P4 observability spec's stated
casing (`Autom8y/FreshnessProbe`). The coalescer metric joins the
already-deployed `autom8y/cache-warmer` namespace where its peer warm-
duty metrics live (`WarmSuccess`, `WarmFailure`, `WarmDuration` —
emitted by `cache_warmer.py:473, 501, 479-483`). The engineer does NOT
attempt to unify casing across namespaces; that is a fleet-cleanup
question outside this ADR's scope.

### Alarm-vs-metric matrix (normative)

This is the load-bearing receipt the engineer carries forward. Every
emission MUST land in exactly one row, and every row's `alarm` column
is a hard contract.

| Metric | Namespace | Alarm? | Alarm anchor (if alarms) | Notes |
|---|---|---|---|---|
| `MaxParquetAgeSeconds` | `Autom8y/FreshnessProbe` | **YES (P2 + P1)** | P4 §3 ALERT-1 (`> 21600`, single eval, P2 WARNING); P4 §3 ALERT-2 (`> 21600` for 30 min, P1 CRITICAL) | Two alarms on same metric, different evaluation windows. SLO-1 burn-rate signal. |
| `ForceWarmLatencySeconds` | `Autom8y/FreshnessProbe` | **NO** | n/a | Latency-distribution observation only; SLO-1 carries the freshness verdict per FLAG-1. Engineer MAY add a future alarm if `> 300s` becomes load-bearing — defer to followup. |
| `SectionCount` | `Autom8y/FreshnessProbe` | **NO** | n/a | Sizing/cardinality observation. Drift detection via dashboard, not page. |
| `SectionAgeP95Seconds` | `Autom8y/FreshnessProbe` | **NO** | n/a | Distribution-aware staleness signal. P4 §1 SLI-4 declares this as informational; SLO-1 alarms on `MaxParquetAgeSeconds` (the worst-case), not P95. |
| `SectionCoverageDelta` | `Autom8y/FreshnessProbe` | **NO — HARD CONSTRAINT** | n/a | PRD §6 C-6 explicit guard: "EMPTY SECTIONS ARE NOT A FAILURE SIGNAL." A `> 0` value means a classifier section produced no parquet (no tasks in section), which is by design. Wiring an alarm on this metric is a **specification violation**, not an oversight. Engineer codifies this in the emission site's docstring. |
| `CoalescerDedupCount` | `autom8y/cache-warmer` | **NO** | n/a | Counter metric for in-process force-warm dedup. Useful for verifying LD-P3-2 coalescer-routing in P7 Probe-3, but not actionable as a page. |

### Additionally — DMS heartbeat alarm (out-of-scope here, in P4 ALERT-4)

The pre-existing `Autom8y/AsanaCacheWarmer` namespace's
`emit_success_timestamp` heartbeat carries a separate alarm (P4 §8
ALERT-4 / SLO-3 / HANDOFF AC-5). That alarm is owned by HANDOFF
work-item-5 and ADR-004's IaC engine; this ADR scopes only the six new
metric emissions and does not re-decide the DMS alarm.

### Cardinality budget

| Namespace | Existing metrics | New metrics this ADR | Total post-ADR |
|---|---|---|---|
| `Autom8y/FreshnessProbe` | 0 | 5 | 5 |
| `autom8y/cache-warmer` | ~3 (`WarmSuccess`, `WarmFailure`, `WarmDuration`, possibly more) | 1 | ~4 |
| `Autom8y/AsanaCacheWarmer` | 1 (heartbeat) | 0 | 1 (unchanged) |

CloudWatch custom-metric pricing is $0.30/metric/month at standard
resolution. Six new metrics → +$1.80/month. Negligible vs the freshness-
SLO operational value.

### Emission site anchors (engineer's landing map)

| Metric | Lands at |
|---|---|
| `MaxParquetAgeSeconds` | After `report` is built in `__main__.py` (between current emission lines ~291 and exit-code resolution at line 341) |
| `ForceWarmLatencySeconds` | New `--force-warm --wait` completion handler in `__main__.py` (or new module per engineer's choice) |
| `SectionCount` | Same insertion point as `MaxParquetAgeSeconds` — single CloudWatch put_metric_data batch |
| `SectionAgeP95Seconds` | Same insertion point; requires `from_s3_listing` enhancement at `freshness.py:142-157` to retain per-key mtime list |
| `SectionCoverageDelta` | Same insertion point; computed as `classifier_section_count - parquet_count` per P4 §1 SLI-4 |
| `CoalescerDedupCount` | `coalescer.py` dedup-fire path — emit via `emit_metric` from `cloudwatch.py` (existing helper) |

The five CLI metrics SHOULD be batched into a single
`put_metric_data` call (CloudWatch supports 1000 metric data points per
call, well above 5). Single-batch reduces API round-trips and ensures
all five share the same emission timestamp for P95 computation
correctness.

## Rationale

1. **Single namespace for CLI metrics — query-cost over access-control**.
   The default recommendation in the dispatch is "single, unless fleet
   convention dictates otherwise." Fleet convention (per the three
   existing namespaces) does not dictate splitting; it dictates
   "namespace per Lambda or per probe surface." `Autom8y/FreshnessProbe`
   IS one probe surface (the CLI). Splitting it (e.g.,
   `Autom8y/FreshnessProbe/CLI` vs `Autom8y/FreshnessProbe/Latency`)
   would inflate the dashboard query surface without adding access-
   control benefit at current scale.

2. **Coalescer metric joins the warmer namespace, not FreshnessProbe**.
   The coalescer is a runtime component of the cache_warmer Lambda's
   warm-routing path; its peer metrics (`WarmSuccess`, `WarmFailure`)
   already live in `autom8y/cache-warmer`. Putting `CoalescerDedupCount`
   alongside them preserves the "metrics about warmer behavior live
   together" pattern. Putting it in `Autom8y/FreshnessProbe` would
   conflate "metrics emitted by the CLI" with "metrics about the
   coalescer the CLI invokes" — wrong altitude.

3. **C-6 alarm prohibition is a hard contract, codified in the matrix
   above**. The PRD constraint
   (`verify-active-mrr-provenance.prd.md:290-294`) is unambiguous:
   empty sections are not a failure signal. P4 §1 SLI-4 echoes this
   ("`SectionCoverageDelta > 0` MUST NOT trigger an alert"). This
   ADR's matrix elevates that to "the engineer cannot accidentally
   wire it" by listing the row with explicit `NO — HARD CONSTRAINT`
   in the alarm column.

4. **Two alarms on `MaxParquetAgeSeconds` is intentional, not
   redundant**. P4 §3 ALERT-1 is single-eval / 5-min / WARNING (
   informational page-channel). ALERT-2 is 6-eval / 30-min /
   CRITICAL (SLO budget burn). The two alarms answer different
   questions: "data is stale right now" (ALERT-1) vs "stale
   condition has persisted long enough to consume budget" (ALERT-2).
   Both fire on the same metric; the engineer wires both per the P4
   spec.

5. **Single `put_metric_data` batch for the five CLI metrics — atomic
   timestamp**. CloudWatch's per-data-point timestamp is set at
   emission. Batching the five CLI metrics into one call ensures
   they share the same observation timestamp, which is load-bearing
   for cross-metric correlation (e.g., joining
   `MaxParquetAgeSeconds` with `SectionCount` for a per-invocation
   density curve).

6. **Capitalization is inherited, not unified**. The fleet is
   inconsistent (`Autom8y/AsanaCacheWarmer` Pascal, `autom8y/cache-
   warmer` lowercase). This ADR adopts each namespace's existing
   casing. A future fleet-cleanup ADR may unify; that is out of
   scope for the freshness initiative.

## Consequences

### Positive

- Engineer's AC-4 work is unambiguous at the namespace level. No
  re-decision during implementation.
- C-6 guard is enforced at architectural altitude — engineer
  cannot accidentally wire a `SectionCoverageDelta` alarm because
  the matrix explicitly forbids it.
- Cost envelope is bounded ($1.80/month for six new metrics).
- Single namespace for CLI metrics simplifies dashboard authoring
  (one namespace selector instead of two).
- Emission-site batching gives free correlation across the five CLI
  metrics.

### Negative

- Capitalization inconsistency between
  `Autom8y/FreshnessProbe` (Pascal) and `autom8y/cache-warmer`
  (lowercase) is preserved — operator running console queries must
  type both. Mitigation: dashboards can save the namespace strings
  as widgets; no manual typing in steady state.
- Two-namespace surface for the freshness initiative as a whole
  (`Autom8y/FreshnessProbe` + `autom8y/cache-warmer`). A
  freshness-question dashboard must source from both. Mitigation:
  the source rationale is intuitive (CLI vs Lambda runtime), so
  the split is comprehensible.

### Neutral

- The two `MaxParquetAgeSeconds` alarms (ALERT-1 + ALERT-2) double-
  fire on sustained breaches (ALERT-1 at minute 5, ALERT-2 at minute
  30). This is intentional per P4 spec; alert-suppression rules in
  the operational tier handle the duplicate noise.

## Alternatives considered

### REJECTED: Single namespace for ALL six metrics (`Autom8y/FreshnessProbe`)

- **Pro**: Simplest possible — one namespace selector everywhere.
- **Con**: Misclassifies the coalescer metric. The coalescer is a
  cache_warmer-internal component; its dedup behavior is about the
  warmer's request-routing, not about the CLI's freshness probe.
  Putting it in `FreshnessProbe` would be the wrong altitude.
- **Con**: Diverges from fleet convention (each Lambda owns a
  namespace named after itself; the CLI is its own probe surface).

### REJECTED: Dual namespace, split by access control

- **Pro**: If freshness metrics ever needed restricted IAM access,
  splitting CLI from Lambda would enable per-namespace IAM scoping.
- **Con**: No current access-control requirement. PRD §6 declares no
  multi-env or multi-tenancy posture. Pre-emptive splitting for an
  imagined future requirement is YAGNI.
- **Con**: Doubles the dashboard authoring surface. At 5 + 1
  metrics, the simplification value of single-namespace exceeds the
  speculative value of split namespaces.

### REJECTED: Unified namespace casing (rename `autom8y/cache-warmer` to `Autom8y/CacheWarmer`)

- **Pro**: Eliminates capitalization inconsistency.
- **Con**: Out-of-scope. The renaming would invalidate every existing
  alarm, dashboard, and CloudWatch Logs Insights query targeting the
  current lowercase namespace. The renaming is a separate (and
  expensive) operation.
- **Con**: PRD §6 C-2 backwards-compatibility constraint applies to
  the CLI surface; while CloudWatch namespaces are not strictly the
  CLI surface, renaming them is a comparable break for downstream
  dashboard consumers.

### REJECTED: Wire `SectionCoverageDelta` to a low-priority informational alarm

- **Pro**: Tempting because the metric is "alertable in shape" — a
  delta is naturally a threshold candidate.
- **Con**: **Direct violation of PRD §6 C-6**. The constraint is
  not "alert at low priority" — it is "DO NOT ALERT." An empty
  section is by-design state.
- **Con**: Even at low priority, false-alert noise erodes operator
  trust in the alerting system. The SLO is "operators page on
  freshness breaches"; it is not "operators see informational
  flutter on classifier population deltas."

### REJECTED: Per-section dimension on `MaxParquetAgeSeconds`

- **Pro**: Would enable per-section SLO tracking instead of fleet-
  wide max.
- **Con**: Cardinality cost — 14 sections at $0.30/metric/month = $4.20/month
  vs $0.30/month for the single fleet-wide metric. At current
  scale, marginal cost is acceptable but not justified.
- **Con**: The freshness probe's question is "is the freshest worst-
  case stale?" — a fleet-max question, not a per-section question.
  Per-section staleness is observable via `SectionAgeP95Seconds`
  distribution at lower cost.
- **Defer**: Engineer MAY add `section_gid` dimension as a follow-up
  if multi-section SLO becomes load-bearing post-deploy. Not in P6
  scope.

### REJECTED: Move the DMS heartbeat alarm into `Autom8y/FreshnessProbe`

- **Pro**: Would consolidate freshness-related alarms under one
  namespace.
- **Con**: The DMS heartbeat is wired to
  `Autom8y/AsanaCacheWarmer` already; moving it requires a Lambda
  code change in the warmer plus an alarm rewrite. HANDOFF
  work-item-5 (ALERT-4 verification) explicitly scopes this to "verify
  or create" at existing namespace, not migrate.

## Anchors

### Substrate this discharges

- HANDOFF §1 work-item-4 (CloudWatch metric emissions list):
  `.ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md:79-93`
- HANDOFF §4 AC-4 acceptance criteria:
  `.ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md:405-431`
- P4 observability §1 SLI definitions:
  `.ledge/specs/cache-freshness-observability.md:19-95`
- P4 observability §3 ALERT-1 + ALERT-2 (`MaxParquetAgeSeconds`
  alarms):
  `.ledge/specs/cache-freshness-observability.md:159-220`
- P4 observability §1 SLI-4 C-6 false-alert guard:
  `.ledge/specs/cache-freshness-observability.md:79-95`

### PRD constraints honored

- PRD §6 C-6 EMPTY SECTIONS ARE NOT A FAILURE SIGNAL:
  `.ledge/specs/verify-active-mrr-provenance.prd.md:290-294`

### Existing namespace anchors (read-only context)

- `Autom8y/AsanaCacheWarmer` (DMS heartbeat):
  `src/autom8_asana/lambda_handlers/cache_warmer.py:70`
- `autom8y/cache-warmer` (warmer runtime metrics) — set in Terraform:
  `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/asana/main.tf:265`
  (`ASANA_CW_NAMESPACE = "autom8y/cache-warmer"`)
- `WarmSuccess` / `WarmFailure` emission sites:
  `src/autom8_asana/lambda_handlers/cache_warmer.py:473, 501`
- `WarmDuration` emission site:
  `src/autom8_asana/lambda_handlers/cache_warmer.py:479-483`

### Cross-ADR composition

- ADR-003 (MemoryTier post-force-warm staleness): the
  `ForceWarmLatencySeconds` metric measures the `--force-warm --wait`
  end-to-end window, which exercises ADR-003's HYBRID L1
  invalidation. Probe-3 verifies both ADRs in a single test.
- ADR-004 (IaC engine for warmer schedule): the 4h warmer cadence
  established by ADR-004 is the operational baseline against which
  `MaxParquetAgeSeconds` ALERT-1 fires. Without ADR-004's cadence
  change, ALERT-1 would fire continuously at the current daily
  cadence.
- ADR-005 (TTL manifest schema): the per-section `sla_class` from
  ADR-005's manifest determines which `MaxParquetAgeSeconds`
  threshold applies in future per-class SLO stratification (deferred
  per HANDOFF §3 LD-P2-1 "until DEF-1 lands").

---

*Authored by 10x-dev.architect, session-20260427-205201-668a10f4,
2026-04-27. Worktree
.worktrees/cache-freshness-impl/, branch
feat/cache-freshness-impl-2026-04-27. Discharges HANDOFF §1 work-item-4
namespace question via single-CLI-namespace + coalescer-joins-warmer
split with hardcoded C-6 alarm prohibition.*
