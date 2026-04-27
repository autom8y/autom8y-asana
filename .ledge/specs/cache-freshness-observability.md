---
type: spec
artifact_type: observability-spec
status: draft
initiative_slug: cache-freshness-procession-2026-04-27
parent_initiative: verify-active-mrr-provenance
session_id: session-20260427-185944-cde32d7b
phase: design
authored_by: thermal-monitor
authored_on: 2026-04-27
worktree: .worktrees/thermia-cache-procession/
branch: thermia/cache-freshness-procession-2026-04-27
schema_version: 1
attester_role: de-facto-verification-auditor (per pantheon-role disambiguation)
---

# Cache Freshness Observability Spec — cache-freshness-procession-2026-04-27

## 1. SLI Definitions

Four SLIs derived from heat-mapper assessment L394-401 and grounded in specific source lines.

---

### SLI-1: max_mtime (primary freshness signal)

**Name**: `MaxParquetAgeSeconds`

**Computation source**: `src/autom8_asana/metrics/freshness.py:202` — `max_age = int((now - min_mtime).total_seconds())`. The `FreshnessReport.max_age_seconds` field is the age of the oldest parquet key under the prefix. This is the per-invocation staleness reading for the entire section fleet.

**Emission path**: Computed inside `FreshnessReport.from_s3_listing` (line 202). Currently emitted to stdout/stderr only (`src/autom8_asana/metrics/__main__.py:326-331`). P5a implementation work: add a CloudWatch `put_metric_data` call after the report is built, emitting `MaxParquetAgeSeconds` to namespace `Autom8y/FreshnessProbe` with dimension `metric_name=active_mrr`.

**Emission frequency**: Per CLI invocation. Frequency is operator-driven; estimated O(1-10/day) [PLATFORM-HEURISTIC — actual frequency unvalidated; thermal-monitor recommends establishing a CloudWatch Logs Insights baseline post-deploy].

**Cardinality**: Single dimension `metric_name`. At current scale (1 metric, 1 project), cardinality = 1 time series. Adding `project_gid` as a second dimension would produce 1 series per project; defer until multi-project support is confirmed.

**Cost**: CloudWatch custom metric: $0.30/metric/month at standard resolution. One metric = $0.30/month. Negligible.

**Receipt-grammar**: `src/autom8_asana/metrics/freshness.py:202` [LANDED — computation exists]; CloudWatch emission is [UNATTESTED — DEFER-POST-HANDOFF: requires P5a 10x-dev impl at `__main__.py` after `report` is built, before exit-code resolution at line 341].

---

### SLI-2: force_warm_latency

**Name**: `ForceWarmLatencySeconds`

**Computation source**: Not yet implemented. The force-warm CLI affordance (PRD NG4) is a P5a/P6 10x-dev impl item. Once implemented, latency is measured as: wall-clock time from `--force-warm` invocation start to receipt of a successful `WarmSuccess` metric in namespace `Autom8y/AsanaCacheWarmer` (or equivalently, the Lambda response payload `response.success == True` plus `WarmDuration` metric at `src/autom8_asana/lambda_handlers/cache_warmer.py:479-483`).

**Emission path**: [UNATTESTED — DEFER-POST-HANDOFF: requires force-warm CLI impl (PRD NG4). P5a 10x-dev item. Emit `ForceWarmLatencySeconds` to `Autom8y/FreshnessProbe` on completion of force-warm invocation.]

**Emission frequency**: Per `--force-warm` invocation. Expected infrequent (operator-triggered or CI-triggered).

**Cardinality**: Single series. No per-entity-type dimension needed at this scale; the full warm cycle is the unit.

**Cost**: Negligible (same CloudWatch pricing; infrequent emission).

**P3 cadence dependency (DEF-2 seam)**: SLO baseline for this SLI depends on P3 capacity-engineer establishing the warmer Lambda execution profile (typical `WarmDuration` per entity type). Until P3 delivers the cadence finding, force_warm_latency SLO is declared with a conservative upper bound of 300 seconds (5 minutes), based on the `WarmDuration` metric emission at `cache_warmer.py:479-483` and the checkpoint-based self-continuation pattern at lines 399-425.

---

### SLI-3: warmer_success_rate

**Name**: `WarmSuccessRate` (derived ratio)

**Computation source**: `src/autom8_asana/lambda_handlers/cache_warmer.py:473` emits `WarmSuccess` metric (value=1) per successful entity warm. Line 501 emits `WarmFailure` metric (value=1) per failed entity warm. Both are emitted to the namespace declared at line 70 via the `emit_metric` function imported from `src/autom8_asana/lambda_handlers/cloudwatch.py`. The SLI is the rolling ratio: `sum(WarmSuccess) / (sum(WarmSuccess) + sum(WarmFailure))` over a 7-day window, scoped to dimension `entity_type=offer` (the entity type that drives `active_mrr`).

**Emission path**: Already emitted at `cache_warmer.py:473` and `cache_warmer.py:501` [LANDED — metric emission exists in deployed code]. CloudWatch alarm consuming these metrics: see DMS Alarm Verification section (§8) for verdict.

**Emission frequency**: Per Lambda invocation, per entity type warmed. With documented schedule (P3 D10 closure), frequency will be known; currently UNDOCUMENTED (AP-1 per heat-mapper assessment).

**Cardinality**: One series per `entity_type`. For `active_mrr` freshness SLO, filter to `entity_type=offer`. Total series at current scale: ~6 (one per entity type in `cascade_warm_order()`).

**Cost**: Already emitting. No incremental cost for monitoring existing metrics.

**Receipt-grammar**: `src/autom8_asana/lambda_handlers/cache_warmer.py:473` (WarmSuccess) [LANDED]; `src/autom8_asana/lambda_handlers/cache_warmer.py:501` (WarmFailure) [LANDED].

---

### SLI-4: section_coverage

**Name**: `SectionCoverageDelta` + `SectionCount` + `SectionAgeP95`

**Computation source**: Derived from `FreshnessReport.parquet_count` (`src/autom8_asana/metrics/freshness.py:153` — `count` accumulator) and the classifier section list at `src/autom8_asana/models/business/activity.py:76` (ACTIVE section names) and line 317 (CLASSIFIERS dict). `SectionCoverageDelta` = `classifier_section_count - parquet_count`. `SectionCount` = `FreshnessReport.parquet_count`. `SectionAgeP95` = 95th percentile of per-section `age_seconds` values (requires per-section mtime list, not just min/max — see P5a note below).

**Emission path**: `SectionCount` can be emitted from `FreshnessReport.parquet_count` with no additional S3 calls. `SectionAgeP95` requires storing per-key mtimes during the paginator loop (currently only min/max are retained at `freshness.py:154-157`); this requires a minor enhancement to `from_s3_listing` to retain the full mtime list. [UNATTESTED — DEFER-POST-HANDOFF: P5a 10x-dev impl item — extend `from_s3_listing` to return per-key mtime list for P95 computation, or emit P95 as a separate CloudWatch metric from CLI layer.]

**C-6 false-alert guard**: PRD §6 C-6 states "EMPTY SECTIONS ARE NOT A FAILURE SIGNAL." `SectionCoverageDelta > 0` MUST NOT trigger an alert. It is an informational metric only. The alert design in §3 explicitly excludes `SectionCoverageDelta` from any alarm condition. Justification: the cache_warmer writes parquet only for sections with tasks; an empty section produces no parquet by design (`prd.md:290-294` C-6 constraint).

**Emission frequency**: Per CLI invocation (same as SLI-1).

**Cardinality**: Three metrics, single dimension each. Total: 3 series.

**Cost**: 3 CloudWatch custom metrics = $0.90/month. Negligible.

**Receipt-grammar**: `src/autom8_asana/metrics/freshness.py:153` (parquet count accumulator) [LANDED]; `src/autom8_asana/models/business/activity.py:76` (classifier section names) [LANDED]; per-section mtime list for P95 [UNATTESTED — DEFER-POST-HANDOFF].

---

## 2. SLO Definitions

Three SLOs derived from PRD G2 (6h default), DEF-3 (internal/operational, eventual consistency tolerable), and the capacity spec's class-based TTL targets from heat-mapper G4.

---

### SLO-1: Freshness SLO (primary)

**Name**: ParquetMaxAgeSLO

**Target**: 95% of CLI invocations over a rolling 7-day window report `MaxParquetAgeSeconds < 21600` (6h = 21,600 seconds) for the ACTIVE-classifier section fleet.

**Derivation**: PRD G2 (`prd.md:70-71`) declares 6h as the default staleness threshold. The 95th-percentile window (not 100%) accommodates scheduled maintenance windows and known warmer schedule gaps without requiring perfect freshness at every invocation. 95% over 7 days = at most 8.4 hours of non-fresh invocations per week — operationally acceptable for an internal CLI.

**DEF-3 anchor**: `active_mrr` is internal/operational (not investor-grade reporting per DEF-3 user adjudication). Eventual consistency is tolerable; freshness signal makes staleness visible. If DEF-3 is ever resolved as "investor-grade," this SLO target must tighten to 99% and the threshold may need to drop to 1h.

**SLO tier**: Operational (internal tooling; no external SLA commitment).

**Breach action**: WARNING alert to operator Slack channel (P2 severity). No auto-remediation at SLO breach. If breach persists > 2 hours, escalate to force-warm (P1 severity, on-call page). See runbook scenario Stale-1.

**Error budget**: 5% of invocations may be stale. At O(5/day) invocations, that is 0.25 stale invocations/day or ~1.75/week — less than 2 stale CLI readings per week before the budget is consumed.

---

### SLO-2: Warmer Availability SLO

**Name**: WarmSuccessRateSLO

**Target**: `WarmSuccessRate` for `entity_type=offer` >= 95% over rolling 7-day window.

**Derivation**: Heat-mapper assessment L403-404 proposes 95% success rate. The warmer already emits `WarmSuccess`/`WarmFailure` at `cache_warmer.py:473,501`. At the current observed frequency (schedule unknown; D10), 95% allows at most 1 failure per 20 invocations before the budget is consumed. This is derived from the operationalize architecture: the checkpoint-resume mechanism at `cache_warmer.py:399-425` means a single Lambda timeout does not count as a failure (it self-continues). A `WarmFailure` represents a genuine entity-warm error.

**P3 cadence dependency (DEF-2 seam)**: This SLO's practical meaning depends on P3 establishing the warmer schedule. If the warmer runs daily, 95% over 7 days = at most 0.35 failures/day. If it runs hourly, the budget is proportionally tighter. P3 must confirm cadence for this SLO to be operationally bounded.

**SLO tier**: Operational.

**Breach action**: P2 alert to on-call. Runbook scenario Warmer-1.

---

### SLO-3: DMS Heartbeat SLO

**Name**: WarmHeartbeatSLO

**Target**: At least 1 `emit_success_timestamp` call to `DMS_NAMESPACE = "Autom8y/AsanaCacheWarmer"` (`cache_warmer.py:70`) within every rolling 24-hour window.

**Derivation**: The dead-man's-switch pattern at `cache_warmer.py:843-845` is designed for exactly this SLO. The `emit_success_timestamp` call fires only on `response.success == True` (line 844). A 24h absence of this signal means the warmer has not completed a successful run in 24 hours, which at a daily (or more frequent) cadence represents a full missed cycle. The heat-mapper confirms this is "already wired" (assessment L238).

**SLO tier**: Operational. This is the highest-urgency SLO — a 24h warmer absence directly causes freshness degradation beyond the 6h SLO-1 budget.

**Breach action**: P1 alert (critical). On-call page. DMS heartbeat absence is the leading indicator of freshness SLO-1 breach. Runbook scenario DMS-1.

---

## 3. Alert Design

All thresholds are derived from the SLO definitions above and the upstream architecture constraints. No arbitrary percentages.

---

### ALERT-1: Freshness Breach — WARNING

**Condition**: `MaxParquetAgeSeconds` > 21600 (6h) for any single invocation.

**Severity**: P2 (WARNING)

**Derivation**: PRD G2 6h threshold. Single-invocation breach is informational — the SLO allows 5% of invocations to breach. This alert fires on every breach so operators know the data is stale, but it does not page unless it sustains (see ALERT-2).

**CloudWatch alarm config**:
- Namespace: `Autom8y/FreshnessProbe`
- Metric: `MaxParquetAgeSeconds`
- Statistic: Maximum
- Period: 300 seconds (5 minutes; covers batched invocations)
- Threshold: > 21600
- Evaluation periods: 1
- Treat missing data: `notBreaching` (CLI not invoked = no staleness reading, not an alert condition)

**Notification channel**: Slack `#autom8y-ops` (informational). No PagerDuty page.

**Suppression**: Suppress during force-warm operations (ALERT-1 is expected to fire transiently during the window between a detected stale state and completion of force-warm). Suppression window: 15 minutes post force-warm initiation.

**Response**: Operator acknowledges; checks freshness signal; triggers `--force-warm` if age exceeds 2x threshold (12h). See runbook Stale-1.

---

### ALERT-2: Freshness Breach — Sustained (SLO Budget Burn)

**Condition**: `MaxParquetAgeSeconds` > 21600 sustained for 30 consecutive minutes (6 evaluation periods x 5-minute period).

**Severity**: P1 (CRITICAL)

**Derivation**: 30 minutes of sustained breach means the warmer has not run within the expected window AND the operator has not responded to ALERT-1 within 30 minutes. This is the SLO budget burn rate alert: at 5/day invocations, 30 minutes of sustained staleness beyond 6h represents a material error budget burn.

**CloudWatch alarm config**:
- Namespace: `Autom8y/FreshnessProbe`
- Metric: `MaxParquetAgeSeconds`
- Statistic: Maximum
- Period: 300 seconds
- Threshold: > 21600
- Evaluation periods: 6 (30 minutes total)
- Treat missing data: `notBreaching`

**Notification channel**: PagerDuty on-call rotation + Slack `#autom8y-ops`.

**Suppression**: None. If the warmer is running and taking > 30 minutes, the DMS heartbeat has not fired yet — this alert is the backstop.

**Response**: On-call engineer follows runbook Stale-1 immediately.

---

### ALERT-3: Warmer Failure Rate

**Condition**: `WarmFailure` count (dimension `entity_type=offer`) > 0 in any 1-hour window.

**Severity**: P2 (WARNING)

**Derivation**: Any warmer failure for the `offer` entity type directly affects `active_mrr` freshness. A single failure in an hour is significant enough to warrant notification; the 95% SLO allows failure only 5% of the time, and at daily cadence that means at most 1 failure per 20 cycles.

**CloudWatch alarm config**:
- Namespace: `autom8y/cache-warmer` (lowercase, with 'y'); production-runtime value sourced from `settings.observability.cloudwatch_namespace` Pydantic field at `settings.py:604`. `WarmSuccess`/`WarmFailure` emit via `emit_metric` at `cache_warmer.py:473,501` (delegating to the local helper at `lambda_handlers/cloudwatch.py` whose default falls back to `settings.observability.cloudwatch_namespace`). NOTE: the `cache_warmer.py:20` module-docstring claim of `autom8/cache-warmer` (no 'y') is OUTDATED; the runtime-config tri-partition is documented in `.ledge/decisions/ADR-007-cw-namespace-tri-partition.md`. As of 2026-04-27 the warmer-side metrics have not yet been emitted in production (no `WarmFailure` datapoints exist in any CloudWatch namespace per P7.A.3 evidence) — Track B Probe-2 will validate alarm-firing semantics empirically post-Batch-D apply.
- Metric: `WarmFailure`
- Dimensions: `entity_type=offer`
- Statistic: Sum
- Period: 3600 seconds (1 hour)
- Threshold: >= 1
- Evaluation periods: 1
- Treat missing data: `notBreaching`

**Notification channel**: Slack `#autom8y-ops`. No page for first occurrence.

**Escalation**: If `WarmFailure` count >= 3 in any 24-hour window (separate alarm), escalate to PagerDuty P1. Three consecutive failures exhaust the 95% success-rate SLO budget at daily cadence.

**Response**: Runbook scenario Warmer-1.

---

### ALERT-4: DMS Heartbeat Absent (dead-man's-switch)

**Condition**: `emit_success_timestamp` metric absent from `DMS_NAMESPACE = "Autom8y/AsanaCacheWarmer"` (`cache_warmer.py:70`) for > 24 hours.

**Severity**: P1 (CRITICAL)

**Derivation**: This is SLO-3 enforcement. The 24h window is derived from the existing dead-man's-switch design at `cache_warmer.py:843-845`. The heat-mapper confirmed the DMS emission is wired in the Lambda but no CloudWatch alarm consuming it was found in the worktree (assessment L159). This alert closes that gap — see §8 for alarm verification verdict.

**CloudWatch alarm config**:
- Namespace: `Autom8y/AsanaCacheWarmer`
- Metric: the metric emitted by `emit_success_timestamp` (see §8 — metric name depends on `autom8y_telemetry.aws.emit_success_timestamp` implementation; DEFER-POST-HANDOFF resolution required)
- Statistic: SampleCount (or Sum, depending on metric type)
- Period: 3600 seconds (1 hour)
- Threshold: < 1
- Evaluation periods: 24 (24 hours total with missing-data)
- Treat missing data: `breaching` — CRITICAL: missing data IS the alert condition for a dead-man's-switch

**Notification channel**: PagerDuty on-call (P1) + Slack `#autom8y-ops`.

**Suppression**: None. The DMS must not be suppressible — that defeats its purpose.

**Response**: Runbook scenario DMS-1. This is the highest-urgency alert in the system. A 24h warmer absence means SLO-1 is already breached.

---

### ALERT-5: S3 IO Error Rate

**Condition**: `FreshnessError` count of any kind (auth/not-found/network/unknown) >= 2 in any 1-hour window.

**Severity**: P2 (WARNING); P1 if `kind=not-found` (bucket-missing is an outage condition)

**Derivation**: A single S3 IO error may be transient. Two errors in an hour suggest a systemic issue. `kind=not-found` at the `NoSuchBucket` level is never transient — the bucket is either misconfigured or deleted; this is a P1 condition regardless of count.

**Emission path** (REFRAMED 2026-04-28 per hygiene W1 DRIFT-3): the P6 10x-dev implementation chose **stderr-only error reporting** (WI-8 at `__main__.py:738-780`) rather than a CloudWatch metric. As of P7.A.3 verification (`.ledge/reviews/P7A-alert-predicates-2026-04-27.md` PRED-2), no `FreshnessErrorCount` metric exists in `Autom8y/FreshnessProbe` namespace and adding one is not in immediate scope (acceptance §A.4 ACCEPTED stderr-only). ALERT-5 is therefore **NOT a CloudWatch metric alarm**. It is realized as a **CloudWatch Logs Insights scheduled query** against the CLI-host log group:

```
fields @timestamp, @message
| filter @message like /FreshnessError/
| stats count() as occurrences by bin(1h)
| sort @timestamp desc
| limit 24
```

Alarm condition: `occurrences >= 2` in any 1h window. Severity routing per the `kind=` substring in the matched stderr line (`kind=not-found` → P1; other kinds → P2). Future procession may upgrade this to a metric-alarm topology by adding a `FreshnessErrorCount` CW metric with `kind` dimension to `cloudwatch_emit.py` (DEFER-FOLLOWUP per acceptance §A.5).

**Notification channel**: P2 → Slack; P1 (not-found) → PagerDuty.

**MINOR-OBS-2 note**: The botocore `ClientError(NoSuchBucket)` gap at `__main__.py:239` (load_project_dataframe path, before the freshness probe) MAY produce raw tracebacks in stderr that are not caught by the `FreshnessError` handler. RESOLVED in P6 WI-8 at `__main__.py:738-780` (handler extended to catch `botocore.exceptions.ClientError` for `NoSuchBucket`, `NoSuchKey`, `AccessDenied`, `InvalidAccessKeyId`, `SignatureDoesNotMatch`, unknown codes; AND `botocore.exceptions.NoCredentialsError`). Logs Insights query above MAY be tightened to filter on the friendly stderr lines emitted by WI-8 rather than raw botocore tracebacks once production volume confirms the WI-8 path covers all real-world error shapes.

---

### ALERT-6: SectionCoverageDelta (informational only — NO alarm)

Per PRD C-6 (`prd.md:290-294`): empty sections are expected behavior. `SectionCoverageDelta > 0` is NOT an alert condition. The metric is emitted as an informational dashboard panel only. This is explicitly documented as a non-alarm to prevent false on-call pages when sections legitimately contain no tasks.

---

## 4. Section-Coverage Telemetry Hooks (D5 discharge)

This section discharges D5 (section-coverage telemetry, deferred from PRD NG5).

### SectionCount

**Metric name**: `SectionCount`
**Namespace**: `Autom8y/FreshnessProbe`
**Value**: `FreshnessReport.parquet_count` — the count of `.parquet` keys enumerated by the `list_objects_v2` paginator at `freshness.py:153`.
**Emission trigger**: Per CLI invocation, after `FreshnessReport` is built.
**Dimensions**: `metric_name=active_mrr`, `project_gid={project_gid}`.
**Baseline**: 14 (observed at handoff 2026-04-27). Alert if `SectionCount < 10` (would indicate significant cache depopulation) or `SectionCount > 30` (unexpected growth). These thresholds are informational; no P1 alarm. P3 should validate growth bounds.
**Implementation**: [UNATTESTED — DEFER-POST-HANDOFF: P5a 10x-dev impl — emit after `report` is built at `__main__.py` between lines 291 and 298.]

### SectionAgeP95

**Metric name**: `SectionAgeP95Seconds`
**Namespace**: `Autom8y/FreshnessProbe`
**Value**: 95th percentile of per-section `age_seconds` values across all parquets in the prefix.
**Computation**: Requires per-key mtime list. The current `from_s3_listing` implementation retains only `min_mtime` and `max_mtime` (lines 154-157). Enhancement required: collect all mtimes in a list, sort, take P95 index.
**Implementation**: [UNATTESTED — DEFER-POST-HANDOFF: P5a 10x-dev impl — enhance `from_s3_listing` at `freshness.py:142-157` to accumulate per-key mtime list; add `section_age_p95_seconds` as a computed value returned to the caller; emit as CloudWatch metric.]
**Why P95 matters**: The current `max_age_seconds` (SLI-1) is driven by the single oldest parquet. P95 shows the fleet-wide staleness distribution and is less sensitive to a single long-tailed outlier.

### SectionCoverageDelta

**Metric name**: `SectionCoverageDelta`
**Namespace**: `Autom8y/FreshnessProbe`
**Value**: `classifier_active_section_count - parquet_count`. Positive value means the classifier knows about sections that have no parquet (expected for empty sections per C-6). Negative value would be anomalous (more parquets than classified sections — possible if sections are deleted from Asana but parquets persist).
**C-6 guard**: This metric MUST NOT be wired to any alarm. It is a dashboard-only informational signal. The telemetry design explicitly encodes the C-6 constraint in the alarm layer by having no alarm for this metric.
**Implementation**: [UNATTESTED — DEFER-POST-HANDOFF: requires knowing `classifier_active_section_count` at runtime, which requires the GID-to-name mapping (DEF-1 deferred to P3). P5a item: once P3 resolves DEF-1, pass classifier section count to the CLI emission layer.]

---

## 5. Dashboard Specification

### Dashboard: Cache Freshness — Overview

**Panel row 1 — Primary health signal**:
- Panel A: `MaxParquetAgeSeconds` time series (7d window, 5m resolution). Horizontal threshold line at 21600 (6h). Color: green below threshold, red above.
- Panel B: `SLO-1 error budget remaining` — gauge showing `(1 - stale_fraction_7d) / 0.05 * 100%`. Turns red when error budget < 20%.
- Panel C: DMS heartbeat — last successful `emit_success_timestamp` timestamp. Time-since-last-success counter. Red if > 6h.

**Panel row 2 — Warmer health**:
- Panel D: `WarmSuccess` + `WarmFailure` stacked time series by `entity_type`. 7d window.
- Panel E: `WarmSuccessRate` (7d rolling) for `entity_type=offer`. Threshold line at 95%.
- Panel F: `WarmDuration` P95 by `entity_type`. Baseline for detecting performance regressions.

**Panel row 3 — Section coverage (D5)**:
- Panel G: `SectionCount` over time. Threshold lines at 10 (low) and 30 (high).
- Panel H: `SectionAgeP95Seconds` vs `MaxParquetAgeSeconds` overlay. Divergence indicates a single outlier driving the max.
- Panel I: `SectionCoverageDelta` bar chart. Informational only; no threshold line. Label clearly: "Positive = empty sections (expected per C-6)."

**Panel row 4 — IO error tracking**:
- Panel J: `FreshnessErrorCount` by `kind` (stacked). 7d window.
- Panel K: CLI invocation count proxy (derived from CloudWatch Logs if available, or from `SectionCount` emission frequency).

**Correlation view**: Overlay `MaxParquetAgeSeconds` against `WarmSuccess` events. A freshness spike that correlates with a warmer failure is root-cause identified. A freshness spike with no warmer failure indicates the schedule gap (AP-1 / D10) is the driver.

---

## 6. Cross-Architecture Validation Rubric (11-Lens)

This rubric is the P7 design-review evidence chain. Each lens is stated as a concrete question with a pass criterion. To apply at P7, answer each question by citing the relevant spec file:line.

### Lens 1 — Pattern Coherence
**Question**: Does the observability design match the cache-aside pattern? (Lambda writes; CLI reads; no invalidation path.)
**Pass criterion**: Every alert and metric accounts for the write-path (Lambda warmer) and read-path (CLI/ECS) separately. No alert assumes write-through or event-driven invalidation semantics.
**P7 evidence**: Verify ALERT-4 (DMS heartbeat) covers write-path; ALERT-1/2 cover read-path; no alert assumes push invalidation.

### Lens 2 — Consistency Model Fidelity
**Question**: Does the observability design reflect eventual consistency as the declared model? Are there alerts that would fire spuriously under valid eventual-consistency lag?
**Pass criterion**: No alert treats a non-zero `MaxParquetAgeSeconds` reading as an error; only readings exceeding the 6h threshold trigger action. The SLO-1 5% error budget explicitly accommodates eventual-consistency lag windows.
**P7 evidence**: Confirm ALERT-1 threshold = 21600 (6h) exactly, not 0.

### Lens 3 — Failure-Mode Completeness
**Question**: Does every failure mode documented in the heat-mapper assessment have a corresponding alert or detection path?

| Failure mode | Heat-mapper source | Alert coverage |
|---|---|---|
| Cache miss (no parquet) | assessment L110 | ALERT-5 (`kind=not-found`) + ALERT-4 |
| Cache stale (old parquet) | assessment L111 | ALERT-1 + ALERT-2 |
| Warmer Lambda failure | assessment L112 | ALERT-3 + ALERT-4 |
| S3 unavailability | assessment L113 | ALERT-5 (`kind=network`) |
| Warmer timeout (self-continue) | assessment L114 | Not a failure — checkpoint resume. No alert needed; `CheckpointSaved` metric at `cache_warmer.py:422` is informational. |

**Pass criterion**: All 4 non-transient failure modes have alert coverage.

### Lens 4 — Capacity Sizing Accuracy
**Question**: Are the alert thresholds consistent with the capacity spec delivered by P3?
**P3 dependency**: P3 capacity-engineer must deliver per-section TTL targets and warmer schedule (DEF-1, DEF-2). This lens CANNOT be fully evaluated until P3 artifacts exist.
**Pre-P3 pass criterion (partial)**: Thresholds are set at PRD-declared values (6h for ACTIVE sections). Post-P3, this lens must be re-evaluated to confirm the warmer schedule is tight enough to keep ACTIVE sections within the 6h budget 95% of the time.
**P7 action**: After P3 delivers, verify that the warmer cadence * expected execution time < 21600 seconds. If not, SLO-1 is architecturally unachievable and must be re-negotiated.

### Lens 5 — Telemetry Coverage
**Question**: Is there a metric for every significant operational state?

| Operational state | Metric |
|---|---|
| Freshness reading per invocation | `MaxParquetAgeSeconds` (SLI-1) |
| Force-warm completion | `ForceWarmLatencySeconds` (SLI-2) [DEFER-P5a] |
| Warmer success/failure per entity | `WarmSuccess`/`WarmFailure` (SLI-3) [LANDED] |
| Parquet fleet size | `SectionCount` (SLI-4) [DEFER-P5a] |
| Fleet age distribution | `SectionAgeP95` (SLI-4) [DEFER-P5a] |
| S3 access errors | `FreshnessErrorCount` [DEFER-P5a] |
| Warmer heartbeat | `emit_success_timestamp` to `Autom8y/AsanaCacheWarmer` [LANDED at `cache_warmer.py:845`] |

**Pass criterion**: All DEFER-P5a items are implemented before P7 in-anger probe. No gap between landed metrics and probe requirements.

### Lens 6 — SLO Realism
**Question**: Are the SLO targets achievable given the current architecture?
**Analysis**: SLO-1 (95% of invocations < 6h) is achievable only if the warmer runs at least once per 6h. The observed max staleness of 32 days (assessment L66) indicates the warmer is NOT currently running at 6h cadence. SLO-1 will breach immediately in the current production state.
**Verdict**: SLO-1 is aspirational until P3 closes D10 (warmer schedule audit). The SLO defines the target state post-procession, not the current state.
**P7 pass criterion**: Warmer schedule confirmed by P3 at cadence <= 6h for ACTIVE sections, OR the SLO target is revised downward in consultation with the user.

### Lens 7 — Force-Warm Composability
**Question**: When `--force-warm` is invoked, does the telemetry clearly show the system moving from stale to fresh without ambiguity?
**Pass criterion**: `MaxParquetAgeSeconds` reading taken after force-warm completion shows a value < threshold. The delta between pre-warm and post-warm readings is observable in the dashboard (Panel A correlation with Panel D warmer events).
**P7 probe**: Probe-1 and Probe-3 in the pre-attestation checklist (§7) directly exercise this composability.

### Lens 8 — Stampede Protection Adequacy
**Question**: The capacity-engineer (P3) is responsible for verifying the `DataFrameCacheCoalescer` (`src/autom8_asana/cache/dataframe/coalescer.py`) is wired for the force-warm path. Does the observability design cover stampede activation?
**Coverage gap assessment**: No `StampedeProtectionActivation` metric is currently emitted by the coalescer. If multiple concurrent force-warm invocations are issued (e.g., CI + operator simultaneously), the coalescer should deduplicate them. Without a metric, this is an operational blind spot.
**Action**: [UNATTESTED — DEFER-POST-HANDOFF: P5a 10x-dev impl item — emit `CoalescerDedupCount` metric when the coalescer prevents a duplicate warm. This is a low-priority item given expected force-warm frequency, but required for Lens 8 coverage.]
**P7 pass criterion**: Either (a) `CoalescerDedupCount` is emitted and monitored, or (b) force-warm is designed to be idempotent and concurrent invocations are harmless (P3 must confirm).

### Lens 9 — Cost Envelope Adherence
**Question**: Does the telemetry cost stay within the G6 cost envelope from heat-mapper assessment L227-249?
**Assessment**: G6 allocates CloudWatch alarm evaluation at ~$0.10/alarm/month. This design specifies 5 alarms (ALERT-1 through ALERT-5) + 1 non-alarm metric (ALERT-6) = ~$0.50/month for alarm evaluations. Custom metric storage: 7 metrics (SLI-1 through SLI-4 expanded) at $0.30/metric = $2.10/month. Total: ~$2.60/month. This exceeds the G6 single-alarm estimate but is well within a reasonable operational budget.
**Verdict**: WITHIN COST ENVELOPE. The heat-mapper's G6 estimate was for a single alarm; the full observability design costs ~$2.60/month, which is proportionally reasonable and expected for a STANDARD-mode engagement.

### Lens 10 — Runbook Completeness
**Question**: Does every alert have a runbook scenario?

| Alert | Runbook scenario |
|---|---|
| ALERT-1 (freshness breach WARNING) | Stale-1 (initial response) |
| ALERT-2 (freshness breach sustained) | Stale-1 (escalated response) |
| ALERT-3 (warmer failure rate) | Warmer-1 |
| ALERT-4 (DMS heartbeat absent) | DMS-1 |
| ALERT-5 (S3 IO error rate) | S3-1 |
| ALERT-6 (SectionCoverageDelta, informational) | No runbook — by design (C-6) |

**Pass criterion**: Runbook artifact at `.ledge/specs/cache-freshness-runbook.md` covers Stale-1, Warmer-1, DMS-1, S3-1.

### Lens 11 — Receipt-Grammar
**Question**: Does every "shipped/landed/verified" claim in this spec have a file:line anchor OR a DEFER tag?
**Self-audit**: All claims in this document use either `[LANDED]` with a specific `file:line` anchor, `[UNATTESTED — DEFER-POST-HANDOFF]` with a named implementing agent, or `[PLATFORM-HEURISTIC]` for estimates. No unsupported claims.
**Pass criterion**: A mechanical scan of this document finds zero instances of "shipped/landed/verified/measures" without a parenthetical `file:line` or DEFER tag.

---

## 7. Pre-Attestation Checklist (P7 Readiness)

### Track A — Design-Review (pre-impl)

The design-review applies the 11-lens rubric to the P2 and P3 artifacts. For each artifact:

**Step 1**: Read `.ledge/specs/cache-freshness-architecture.tdd.md` (P2). Apply Lenses 1, 2, 3, 7, 8. Record pass/fail per lens with file:line anchor from the P2 spec.

**Step 2**: Read `.ledge/specs/cache-freshness-capacity-spec.md` (P3). Apply Lenses 4, 6, 8. Confirm warmer schedule cadence vs SLO-1 target (Lens 6). Record P3 cadence finding.

**Step 3**: Apply Lenses 5, 9, 10, 11 to this observability spec. Confirm all DEFER items are resolved in P5a/P6.

**Step 4**: Record pass/fail for each of the 11 lenses in a design-review evidence artifact at `.ledge/reviews/design-review-P7-cache-freshness-{date}.md`.

**Expected pass criteria**: All 11 lenses PASS. A FAIL on any lens blocks P7 in-anger probe. Lens 4 and Lens 6 are dependent on P3 delivery; if P3 has not delivered by P7 date, those lenses carry a DEFERRED status and the in-anger probe is conditional.

---

### Track B — In-Anger Probe (post-impl)

Five concrete probes. Each probe specifies command, expected output, and pass/fail criteria.

---

**Probe-1: Force-warm reduces oldest-parquet age below SLA threshold**

**Command**:
```
python -m autom8_asana.metrics active_mrr --staleness-threshold 6h --strict
# (before force-warm — expected to exit 1 if cache is currently stale)
python -m autom8_asana.metrics --force-warm
# wait for completion
python -m autom8_asana.metrics active_mrr --staleness-threshold 6h --strict
```

**Expected stdout** (post-warm invocation):
```
Loaded N rows from project 1143843662099250
Unique (office_phone, vertical) combos: 71
  
  active_mrr: $94,076.00
parquet mtime: oldest=YYYY-MM-DD HH:MM UTC, newest=..., max_age=Nm
```
(max_age line shows minutes, not hours)

**Expected stderr**: No WARNING line (data is fresh post-warm)

**Expected exit code**: 0

**Pass criterion**: The post-warm invocation exits 0 with no stale WARNING. `max_age` value in `parquet mtime` line shows < 360 minutes (6h). If the pre-warm invocation exits 0 (data was already fresh), the probe is inconclusive — rerun after artificially aging a parquet or on a day when the warmer has not run.

**P2/P3 dependency**: Force-warm CLI (`--force-warm` flag) is a P6 impl item (PRD NG4). This probe cannot execute until P6 delivers. [DEFERRED-TO-POST-P6]

---

**Probe-2: Telemetry surfaces alert on max_mtime > SLA threshold within M minutes of breach**

**Command**:
```
# Verify alert fires by simulating a stale state observation
# (Either: observe current production state if max_age > 6h,
#  OR: invoke CLI against a test prefix with a known-stale parquet)
python -m autom8_asana.metrics active_mrr --staleness-threshold 6h
# Verify CloudWatch metric was emitted:
aws cloudwatch get-metric-statistics \
  --namespace Autom8y/FreshnessProbe \
  --metric-name MaxParquetAgeSeconds \
  --start-time $(date -u -v-10M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 600 \
  --statistics Maximum
```

**Expected output**: JSON with `Datapoints` array containing at least one entry with `Maximum > 21600` (if current state is stale).

**Expected alert firing**: Within 5 minutes (one evaluation period) of the CloudWatch data point landing, ALERT-1 transitions to ALARM state. Verify in CloudWatch console: `Autom8y/FreshnessProbe` → `MaxParquetAgeSeconds` → alarm status.

**Pass criterion**: (a) Metric datapoint present in CloudWatch within 2 minutes of CLI invocation; (b) ALERT-1 alarm transitions to ALARM state within the next evaluation period (5 minutes).

**P5a dependency**: CloudWatch metric emission from CLI is a P5a impl item [DEFERRED-TO-POST-P5A].

---

**Probe-3: Force-warm + freshness CLI compose; post-warm freshness signal shows fresh state**

**Command**:
```
# Step 1: Capture pre-warm freshness
python -m autom8_asana.metrics active_mrr --json | python -m json.tool
# Note freshness.max_age_seconds value

# Step 2: Force-warm
python -m autom8_asana.metrics --force-warm
# (wait for completion signal)

# Step 3: Capture post-warm freshness
python -m autom8_asana.metrics active_mrr --json | python -m json.tool
# Note freshness.max_age_seconds value
```

**Expected behavior**: Step 3 output shows `freshness.stale = false` and `freshness.max_age_seconds` significantly lower than Step 1 value. `freshness.parquet_count` unchanged (same 14 sections).

**Pass criterion**: `freshness.stale == false` in Step 3 JSON envelope. `freshness.max_age_seconds < 21600`. No manual intervention between steps.

**P6 dependency**: Requires force-warm CLI impl [DEFERRED-TO-POST-P6].

---

**Probe-4: SLA-gate publish-blocker fires when freshness violates threshold (NG8 enforcement)**

**Command**:
```
# In CI pipeline with --strict flag
python -m autom8_asana.metrics active_mrr --strict --staleness-threshold 6h
echo "Exit code: $?"
```

**Expected stdout**: Dollar figure + freshness line (current production values)

**Expected stderr** (if stale): `WARNING: data older than 6h (max_age=Xd Yh Zm)`

**Expected exit code**: 1 (if stale), 0 (if fresh)

**Pass criterion**: Exit code is 1 when `freshness.max_age_seconds > 21600`. CI pipeline configured to treat exit-1 as a gate failure, blocking publish.

**Current state**: This probe is executable TODAY against the existing implementation at `src/autom8_asana/metrics/__main__.py:341` — the `--strict` flag and exit-code logic are already shipped [LANDED at `__main__.py:341`]. The NG8 "SLA gate" is simply this `--strict` invocation in a CI pipeline. No new impl needed for Probe-4 itself; only the CI pipeline wiring is a P5a/P6 item.

**P5a dependency for CI wiring**: Pipeline configuration is a P5a impl item. The probe itself can be run manually now.

---

**Probe-5: Section-coverage telemetry emits expected metrics (D5 discharge verified observable)**

**Command**:
```
# Invoke CLI (which should emit SectionCount + SectionAgeP95 to CloudWatch)
python -m autom8_asana.metrics active_mrr

# Verify CloudWatch metric emission
aws cloudwatch list-metrics \
  --namespace Autom8y/FreshnessProbe \
  --metric-name SectionCount

aws cloudwatch get-metric-statistics \
  --namespace Autom8y/FreshnessProbe \
  --metric-name SectionCount \
  --start-time $(date -u -v-10M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 600 \
  --statistics Average
```

**Expected output**: `Datapoints` array with value approximately 14 (observed section count at handoff). `SectionAgeP95Seconds` datapoint present in same window.

**Pass criterion**: Both `SectionCount` and `SectionAgeP95Seconds` metrics present in `Autom8y/FreshnessProbe` namespace with values in expected range (10-20 sections; P95 age plausible given observed distribution).

**P5a dependency**: Both metrics require P5a impl [DEFERRED-TO-POST-P5A].

---

### Probe Dependency Summary

| Probe | Executable today? | Dependency |
|---|---|---|
| Probe-1 | No | P6 force-warm CLI (PRD NG4) |
| Probe-2 | No | P5a CloudWatch metric emission |
| Probe-3 | No | P6 force-warm CLI (PRD NG4) |
| Probe-4 | YES — partial | `--strict` impl LANDED; CI wiring is P5a |
| Probe-5 | No | P5a CloudWatch metric emission |

Probe-4 can and should be run manually before P7 to confirm `--strict` exit-code behavior is correct end-to-end. All other probes require P5a/P6 delivery first. P7 attestation MUST NOT be scheduled until P5a and P6 are complete.

---

## 8. DMS Alarm Verification

### Verification approach

The heat-mapper assessment (L158-159) states: "A dead-man's-switch alert at 24h is already wired (`cache_warmer.py:843-845`). If the DMS alert fires and no one responds, that is an operational gap."

The heat-mapper also states (L159): "no CloudWatch alarm consuming it was found in the worktree."

The P4 dispatch requires: discover whether the alarm exists in IaC by inspection, OR declare as P5a impl item.

### IaC inspection result

**Scope searched**: The worktree at `.worktrees/thermia-cache-procession/` was searched by the heat-mapper (assessment L124) for `*.tf`, `serverless*.yml`, `template*.yml`, and CDK files referencing `cache_warmer`. Result: zero IaC files found in the worktree.

**DMS mechanism inspection**: The `emit_success_timestamp` function is imported at `cache_warmer.py:45`:
```python
from autom8y_telemetry.aws import emit_success_timestamp, instrument_lambda
```

This is a dependency on the `autom8y_telemetry` package, which is external to the worktree. The function name `emit_success_timestamp` suggests it writes a CloudWatch metric (likely a timestamp value or a count=1 heartbeat) to the `DMS_NAMESPACE = "Autom8y/AsanaCacheWarmer"` namespace declared at `cache_warmer.py:70`. The metric name emitted by `emit_success_timestamp` is NOT visible from the source in this worktree — it is encapsulated in the `autom8y_telemetry.aws` package.

**Verdict**: ALARM NOT FOUND IN WORKTREE IaC.

The DMS metric emission is confirmed as wired in code (`cache_warmer.py:843-845`). However, no CloudWatch alarm definition consuming `Autom8y/AsanaCacheWarmer` was found in any IaC file within the worktree. The `autom8y_telemetry.aws` package may provision alarms programmatically outside this worktree, but this cannot be confirmed from static analysis of the available files.

**DEFERRED TO P5A**: The DMS CloudWatch alarm creation is declared as a P5a 10x-dev implementation item.

### Required alarm configuration (for P5a implementation)

```
Alarm name: AsanaCacheWarmer-DMS-24h
Namespace: Autom8y/AsanaCacheWarmer
Metric: [the metric name emitted by emit_success_timestamp — must be confirmed from autom8y_telemetry.aws source]
Statistic: SampleCount (or Sum)
Period: 3600 seconds (1 hour)
Evaluation periods: 24
Datapoints to alarm: 24
Threshold: < 1
Treat missing data: breaching
Comparison operator: LessThanThreshold
Alarm actions: [PagerDuty SNS topic ARN] + [Slack #autom8y-ops SNS topic ARN]
OK actions: [same channels — notify when warmer resumes]
Insufficient data actions: [same channels]
Description: "Dead-man's switch: cache_warmer Lambda has not completed a successful
  full warm cycle in >24 hours. If firing, freshness SLO-1 is breached.
  Follow runbook: .ledge/specs/cache-freshness-runbook.md scenario DMS-1."
```

**Prerequisite for P5a**: Confirm the metric name emitted by `autom8y_telemetry.aws.emit_success_timestamp` by reading the `autom8y_telemetry` package source. The alarm `MetricName` field must match exactly.

---

## 9. Cross-Spec Dependencies

### Dependency on P2 (systems-thermodynamicist)

- **Failure-mode matrix** (Lens 3): P2 must confirm the failure modes listed in the heat-mapper assessment table (assessment L350-354) are complete. Any new failure mode introduced by P2 architecture decisions must have a corresponding alert added to this spec.
- **Force-warm composability** (Lens 7): P2 owns the force-warm design (PRD NG4, DEF-4). The observability design for Probe-1 and Probe-3 assumes the force-warm path follows the Lambda invoke pattern described at assessment L358-362. If P2 changes this design, Probes 1 and 3 must be updated.
- **Stampede protection** (Lens 8): P2 owns the `DataFrameCacheCoalescer` wiring decision. The `CoalescerDedupCount` metric (Lens 8 coverage gap) requires P2 to confirm or deny that the coalescer is wired for force-warm deduplication.

P2 artifact: `.ledge/specs/cache-freshness-architecture.tdd.md` [NOT YET PRODUCED — P2 phase not yet run at time of P4 authoring]

### Dependency on P3 (capacity-engineer)

- **Warmer schedule cadence (DEF-2 seam)**: This observability spec explicitly states this dependency at SLI-2, SLO-2, and Lens 4/6. P3 must deliver the warmer schedule cadence (EventBridge rule interval or equivalent) for SLO-1 and SLO-2 to be operationally bounded.
- **Per-section TTL targets (DEF-1)**: The ACTIVE vs non-ACTIVE section classification affects which sections the freshness SLO applies to at full strictness. Until DEF-1 is resolved by P3, all 14 sections are treated uniformly under the 6h threshold for SLO-1 purposes.
- **`SectionCoverageDelta` denominator**: The classifier section count (numerator for `SectionCoverageDelta`) requires the GID-to-name mapping from P3 DEF-1 resolution.

P3 artifact: `.ledge/specs/cache-freshness-capacity-spec.md` [NOT YET PRODUCED — P3 phase not yet run at time of P4 authoring]

### PT-A2 cross-spec consistency verification

The potnia fan-in (PT-A2) must verify:
1. P3 warmer cadence value is consumed in this spec's SLO-1 realism assessment (Lens 6).
2. P2 failure-mode matrix is complete relative to the alert set in §3.
3. DEFER tags in this spec are enumerated in the P5a implementation handoff dossier.

---

## 10. Cross-Rite Routing Recommendations

### Implementation work (route to 10x-dev at P5a)

| Item | Description | Source |
|---|---|---|
| CloudWatch metric emission from CLI | Emit `MaxParquetAgeSeconds`, `SectionCount`, `SectionAgeP95Seconds`, `FreshnessErrorCount` to `Autom8y/FreshnessProbe` after `FreshnessReport` is built | `__main__.py` after line 291 |
| `from_s3_listing` per-key mtime list | Extend accumulator to retain full mtime list for P95 computation | `freshness.py:154-157` |
| DMS CloudWatch alarm creation | Alarm config specified in §8; confirm metric name from `autom8y_telemetry.aws` | IaC or boto3 CDK |
| Force-warm CLI affordance | PRD NG4 — `--force-warm` flag; Lambda invoke via boto3 | `__main__.py` + new handler |
| CI pipeline `--strict` wiring | Probe-4 CI integration for NG8 SLA enforcement | Pipeline config |
| `FreshnessErrorCount` metric emission | Emit from `except FreshnessError` block | `__main__.py:292-294` |
| `CoalescerDedupCount` metric | Emit from `DataFrameCacheCoalescer` when dedup fires | `coalescer.py` |

### Monitoring infrastructure (route to SRE if dedicated monitoring infra needed)

The alert definitions in §3 are specified as CloudWatch alarms. If the team uses Grafana (the heat-mapper mentions "A Grafana alert fires when this metric is absent or stale >24h" at `cache_warmer.py:843` comment), the ALERT-4 DMS alarm may already be configured in Grafana outside the worktree. SRE should verify whether the Grafana alert config exists in a separate IaC/config repo and whether it covers the same 24h threshold.

---

## Design Validation Checklist

- [x] Miss rate (MaxParquetAgeSeconds) is the primary metric for the S3 parquet tier — not hit rate
- [x] Every alerting threshold is derived from PRD G2 (6h = 21600s) or architecture/capacity specs
- [x] ALERT-4 (DMS heartbeat) covers the stampede/warmer heartbeat detection
- [x] Replication lag not applicable (no replication in this architecture — single S3 cold tier)
- [x] Dashboard spec covers full thermal landscape (freshness + warmer + section coverage + IO errors)
- [x] Runbook covers every failure mode in architecture (Stale-1, Warmer-1, DMS-1, S3-1 in separate runbook artifact)
- [x] C-6 false-alert mitigation: `SectionCoverageDelta` explicitly excluded from alarm conditions
- [x] DMS alarm verification completed: DEFERRED TO P5A (no IaC found in worktree)
- [x] 11-lens rubric completed; Lenses 4 and 6 flagged as P3-dependent
- [x] 5-probe in-anger set defined; Probes 1/2/3/5 are post-P5a/P6; Probe-4 executable now
- [x] P2 and P3 cross-spec dependencies explicitly declared
- [ ] ALERT-2 threshold (30 minutes sustained breach) — validate against P3 warmer cadence at fan-in
- [ ] `autom8y_telemetry.aws.emit_success_timestamp` metric name — unresolved; required for ALERT-4 and DMS alarm config

### Identified blind spots

**Blind spot 1**: The `emit_success_timestamp` metric name is unknown without reading the `autom8y_telemetry` package source. If the metric name does not match the alarm configuration, ALERT-4 will never fire. This is the highest-priority unresolved gap.

**Blind spot 2**: The warmer schedule (D10) is undocumented. Until P3 resolves D10, the SLO-1 and SLO-2 breaching conditions cannot be evaluated against realistic expectations. The current production state has 9/14 sections beyond the 6h threshold — the SLO is already breached. The observability design assumes this is a pre-operationalize state, not a permanent condition.

**Blind spot 3**: There is no metric for "warmer never triggered" (distinct from "warmer triggered but failed"). If the EventBridge rule is disabled or deleted, `WarmFailure` will be 0 (no invocations) and `WarmSuccess` will be 0 — both indicate no activity. The DMS heartbeat (ALERT-4) is the only signal for this condition. This is correct by design but the on-call engineer must understand that a zero-value `WarmFailure` rate is NOT evidence of a healthy warmer.
