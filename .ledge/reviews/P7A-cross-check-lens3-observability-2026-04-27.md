---
type: review
status: draft
station: P7.A.1-CROSS
procession_id: cache-freshness-procession-2026-04-27
author_agent: thermia.heat-mapper
parent_telos: verify-active-mrr-provenance
verification_deadline: 2026-05-27
cross_check_seam: rite-disjoint critic per Axiom 1 intra-rite inheritance
target_under_review: P4 observability-spec authored by thermal-monitor
authored_on: 2026-04-27
commit_sha_at_authoring: 2253ebc1
---

# P7.A.1-CROSS — Lens-3 Observability-Completeness Cross-Check
## cache-freshness-procession-2026-04-27

**Rite-disjoint rationale**: `thermia.thermal-monitor` authored
`.ledge/specs/cache-freshness-observability.md` (P4) and is primary verifier
for five of six P7.A sub-phases. Lens-3 (observability-completeness) is
suspended in `P7A-design-review-2026-04-27.md` (station P7.A.1, line 65-71)
pending this artifact. `heat-mapper` carries no authorship surface in P4; it
is the designated disjoint critic per procession plan §8 (`P7-procession-plan-2026-04-27.md:141-147`).

**Acid test governing this review**: does P4 prove that the telemetry is
sufficient, or does it claim sufficiency and defer the proof?

---

## Evidence Substrate Read

| Artifact | Evidence anchor |
|---|---|
| P4 spec (thing under cross-check) | `.ledge/specs/cache-freshness-observability.md` read in full |
| Implementation: 5-metric emitter | `git show feat/cache-freshness-impl-2026-04-27:src/autom8_asana/metrics/cloudwatch_emit.py` |
| Implementation: FreshnessReport + P95 | `git show feat/cache-freshness-impl-2026-04-27:src/autom8_asana/metrics/freshness.py:99-213` |
| Implementation: emit wiring sites | `git show feat/cache-freshness-impl-2026-04-27:src/autom8_asana/metrics/__main__.py:241-263` (wrapper), `:472` (post-warm sync recheck emit), `:889-898` (default-mode emit) |
| Implementation: CoalescerDedupCount | `git show feat/cache-freshness-impl-2026-04-27:src/autom8_asana/cache/dataframe/coalescer.py:34-67` |
| Operator runbook | `.ledge/specs/cache-freshness-runbook.md` read in full |
| Inbound dossier (10x-dev handoff) | `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md` §3.1, §5(c), §A.4 |
| ADR-006 (namespace strategy) | Referenced throughout impl; ADR file absent from worktree — namespace constants verified mechanically against impl |

Note: ADR-006 file at `.ledge/decisions/ADR-006-cloudwatch-namespace-strategy.md` returned
ENOENT in the worktree at review time. Namespace assignments were verified directly against
`cloudwatch_emit.py` constants and `cache_warmer.py:70` (`DMS_NAMESPACE`) rather than the ADR
text. This is not a lens-3 failure — the impl is the authoritative source of truth — but it
is noted as a documentation gap (see Concern C-3 below).

---

## §1 — Heat Visibility Coverage

**Question**: what can a rite-disjoint operator answer from deployed telemetry alone?

### What the operator CAN answer from telemetry (no source-code knowledge)

| Operational question | Metric | Namespace | Source anchor |
|---|---|---|---|
| Is the oldest parquet stale right now? | `MaxParquetAgeSeconds` | `Autom8y/FreshnessProbe` | `cloudwatch_emit.py:41` (constant); `freshness.py:202` (computation); `__main__.py:893-898` (default-mode wiring) |
| How many sections are currently cached? | `SectionCount` | `Autom8y/FreshnessProbe` | `cloudwatch_emit.py:43`; `freshness.py:153` (accumulator); same emit path |
| What is the P95 age distribution of cached sections? | `SectionAgeP95Seconds` | `Autom8y/FreshnessProbe` | `cloudwatch_emit.py:44`; `freshness.py:section_age_p95_seconds()` (lines 110-140) |
| Did a force-warm complete end-to-end? How long did it take? | `ForceWarmLatencySeconds` | `Autom8y/FreshnessProbe` | `cloudwatch_emit.py:42`; `__main__.py:472` (post-warm sync recheck site) |
| Is the warmer Lambda succeeding per entity type? | `WarmSuccess`, `WarmFailure` | `autom8y/cache-warmer` (settings-resolved) | `cache_warmer.py:473-484`, `:501-507` |
| Has the warmer completed a full cycle in the last 24h? | DMS heartbeat via `emit_success_timestamp` | `Autom8y/AsanaCacheWarmer` | `cache_warmer.py:70` (DMS_NAMESPACE), `:843-845` (emit) |
| Is the CLI encountering S3 IO errors? | stderr log lines (`FreshnessError`) — see ALERT-5 note below | no CW metric yet | `__main__.py:738-780` (WI-8 stderr emission only) |
| Did the coalescer deduplicate a concurrent build? | `CoalescerDedupCount` | `autom8y/cache-warmer` | `coalescer.py:34-67` |

### What the operator CANNOT answer from deployed telemetry alone

| Operational question | Gap | Evidence anchor |
|---|---|---|
| Which individual sections are stale (per-section breakdown)? | No per-section-key metric emitted. `MaxParquetAgeSeconds` and `SectionAgeP95Seconds` are fleet-level. Runbook Stale-1 directs the operator to `aws s3 ls` for per-section inspection (runbook lines 54-59) — a CLI command, not a CW metric. This is a known accepted gap, not a surprise design flaw. | P4 §1 SLI-4 discussion; runbook Stale-1 step 2 |
| What is the exact metric name emitted by `autom8y_telemetry.aws.emit_success_timestamp`? | The DMS metric name is encapsulated in the `autom8y_telemetry` external package. Neither P4 nor the runbook specifies it concretely. The runbook DMS-1 Step 1 command uses `[DMS_METRIC_NAME]` as a literal placeholder (runbook line 239). An operator cannot run the prescribed command without first resolving this from package source. | P4 §8 "Blind Spot 1" (observability spec line 724); runbook line 239-245 |
| Are ALERT-3 (WarmFailure) and ALERT-5 (FreshnessError rate) CloudWatch alarms actually deployed? | ALERT-3 alarm ownership is explicitly flagged as UNCLEAR in the 10x-dev handoff (HANDOFF dossier line 196). ALERT-5 is accepted as "CloudWatch Logs Insights query rather than metric alarm" (HANDOFF dossier §A.4 line 493-496). A rite-disjoint operator checking the CW console would find these alarms absent or unverified. | HANDOFF-10x-dev-to-thermia-2026-04-27.md lines 196, 198, 487-497 |
| Is the SLA-gate (--strict) actually configured in CI? | Probe-4 confirms the binary behavior is correct, but CI pipeline wiring is a P5a DEFER item. An operator cannot verify the gate is active by reading CW telemetry. | P4 §7 Probe-4; observability spec line 558-560 |

**Coverage verdict**: The five deployed CLI metrics (`Autom8y/FreshnessProbe` namespace) plus
the warmer metrics (`autom8y/cache-warmer`) and the DMS heartbeat (`Autom8y/AsanaCacheWarmer`)
collectively provide sufficient freshness-heat visibility for the primary staleness question.
The operator CAN detect a freshness breach, a warmer failure, and a DMS absence from telemetry
alone. The CANNOT answers are either (a) acceptable operational gaps with documented workarounds
(per-section breakdown), (b) a named blind spot with a DEFER path (DMS metric name), or (c) an
ownership ambiguity on two alarms that pre-dates P4 (ALERT-3, ALERT-5).

---

## §2 — Alarm/SLO/SLI Coherence

**Question**: does the SLI taxonomy actually drive the SLOs and ALERTs? Are there disconnects?

### SLI-to-SLO mapping

| SLI | SLO | Drives ALERT? | Assessment |
|---|---|---|---|
| SLI-1 `MaxParquetAgeSeconds` | SLO-1 ParquetMaxAgeSLO (95% < 21600s / 7d) | YES — ALERT-1 (single breach), ALERT-2 (sustained 30min) | COHERENT. The SLO error budget (5% of invocations) is arithmetic from the alert design. ALERT-1 fires on every single-invocation breach; ALERT-2 fires on 30-minute sustained breach. The 30-minute window for ALERT-2 is derived from "6 evaluation periods x 5-minute period" (P4 §3 ALERT-2 config, lines 195-200). The 5-minute period + 6 periods = 30 minutes is structurally sound as a budget-burn-rate proxy. No disconnect. |
| SLI-2 `ForceWarmLatencySeconds` | None — no SLO defined for force-warm latency | No alarm today (FLAG-1 boundary; no-alarm-today in `cloudwatch_emit.py:9-10` docstring comment and `ALARMED_METRICS` frozenset at lines 68-75) | GAP — ACCEPTABLE. P4 proposes SLO upper bound of 300s (conservative; SLI-2 §1 lines 56-57) but no SLO record exists in §2 for this SLI, and no ALERT drives from it. The `ALARMED_METRICS` frozenset includes `ForceWarmLatencySeconds` as "alarmable in principle" but cloudwatch_emit.py line 64-65 states "only MaxParquetAgeSeconds has an alarm wired today." This is documented `no-alarm-today` status, not a silent gap. The operator cannot get paged on a slow force-warm. At the current force-warm invocation frequency (low, operator-triggered), this is an acceptable operational deferral. |
| SLI-3 `WarmSuccessRate` | SLO-2 WarmSuccessRateSLO (>=95% over 7d for entity_type=offer) | ALERT-3 (WarmFailure >= 1 in 1h) | DISCONNECT FOUND — MATERIAL. The SLO is defined as a rolling 7-day window ratio, but the implementing alarm (ALERT-3) is a single-hour count of `WarmFailure`. These are not the same predicate. An operator following runbook Warmer-1 is directed by ALERT-3 (1-hour window), but SLO-2 targets the 7-day window. Additionally, ALERT-3's alarm ownership is UNCLEAR per the 10x-dev handoff (HANDOFF dossier line 196) — the alarm may not be deployed. The metric (`WarmFailure` at `cache_warmer.py:501`) is LANDED; the alarm is a PENDING-AWS-VERIFICATION item. The SLO is defined; the alarm that enforces it at the specified confidence level has a deployment uncertainty. |
| SLI-4 `SectionCoverageDelta` / `SectionCount` / `SectionAgeP95Seconds` | No SLO defined | ALERT-6 explicitly NO-ALARM (SectionCoverageDelta); no alert for SectionCount or SectionAgeP95Seconds | COHERENT for SectionCoverageDelta (C-6 constraint correctly applied). For SectionCount and SectionAgeP95Seconds: P4 §4 (dashboard spec lines 292-293) sets informational thresholds (SectionCount < 10 or > 30) but explicitly states "no P1 alarm" — correct for dashboard-only metrics at this scale. |
| DMS heartbeat (`emit_success_timestamp`) | SLO-3 WarmHeartbeatSLO (>=1 emit / 24h rolling) | ALERT-4 (DMS absent > 24h, P1) | COHERENT in design. The alarm config is specified at P4 §8 lines 637-653. ALERT-4 is set to `Treat missing data: breaching` which is correct for a dead-man's-switch. However: the alarm is STASHED in a Terraform stash at the cross-repo level (HANDOFF dossier line 188: "alarm STASHED for Batch-D"). It is NOT currently deployed as an active CloudWatch alarm. The SLO is defined and the alarm spec is written; the deployment is a Batch-D item. |

### ALERT-without-metric and metric-without-ALERT inventory

**ALERT-5 — metric-without-alarm**: `FreshnessError` events are emitted as stderr lines
(WI-8 at `__main__.py:738-780`) but there is no `FreshnessErrorCount` CloudWatch metric.
ALERT-5 as specified in P4 §3 (lines 260-272) requires a CW metric to exist before a CW alarm
can consume it. The 10x-dev handoff §A.4 (line 493-496) accepts this and re-classifies ALERT-5
as a CloudWatch Logs Insights query rather than a metric alarm. This means ALERT-5 as written in
P4 is over-claiming: it describes a CW alarm config (`Namespace: Autom8y/FreshnessProbe`,
`Metric: FreshnessErrorCount`) but the underlying metric does not yet exist. The P4 spec does
not prominently flag this reclassification; it is surfaced only in the dossier §A.4.

**ALERT-3 namespace ambiguity**: P4 §3 ALERT-3 states namespace "varies (see §8 for DMS
namespace)" (observability spec line 218). The actual `WarmFailure` metric is emitted by
`cache_warmer.py:501` via `emit_metric()` in `lambda_handlers/cloudwatch.py`. That function
resolves namespace from `settings.observability.cloudwatch_namespace`, which defaults to
`autom8/lambda` per `settings.py:38` (field `ASANA_CW_NAMESPACE`, default `autom8/lambda`).
The Terraform environment variable is `CLOUDWATCH_NAMESPACE` defaulting to `autom8/cache-warmer`
per `cache_warmer.py:20` (docstring). The coalescer correctly uses `autom8y/cache-warmer`
(lowercase) per `coalescer.py` constant. There are three distinct candidate namespaces for
`WarmFailure`: `autom8/lambda` (settings default), `autom8/cache-warmer` (Terraform env
default), `autom8y/cache-warmer` (coalescer ADR-006 constant). A rite-disjoint operator
configuring ALERT-3 cannot determine the correct namespace from P4 alone — they would wire the
alarm to the wrong namespace and it would never fire. P4 leaves this as "varies (see §8)" which
is insufficient operator guidance.

---

## §3 — Operator Runbook Traceability

**Question**: can a paged operator follow Stale-1 / Warmer-1 / DMS-1 using ONLY deployed
telemetry (not source code)?

### Stale-1 traceability chain

| Step | Metric / source | CW dashboard panel | Assessment |
|---|---|---|---|
| Alert triggers | ALERT-1 or ALERT-2 firing on `MaxParquetAgeSeconds > 21600` | Panel A: `MaxParquetAgeSeconds` time series (P4 §5 row 1, Panel A) | TRACEABLE. Alert sources a real emitted metric (`cloudwatch_emit.py:1-233`; wired at `__main__.py:893`). Panel A shows the time series. |
| Impact: is the breach minor or severe? | `freshness.max_age_seconds` from JSON CLI output | No CW panel — CLI invocation required | OPERATOR DEPENDENCY. Step 1 in runbook (lines 47-51) requires running `python -m autom8_asana.metrics active_mrr --json`. This is not CW-telemetry; it is a CLI invocation. For a paged operator without CLI access (e.g., mobile PagerDuty ack before reaching a terminal), this step is opaque. Acceptable at this scale (internal tooling), but noted. |
| Is warmer running recently? | `WarmSuccess` in `autom8/cache-warmer` namespace | Panel D: `WarmSuccess + WarmFailure` stacked time series (P4 §5 row 2) | TRACEABLE. Runbook Step 2 CW command queries correct metrics. Panel D covers the warmer health. |
| Did offer entity-type warm fail? | `WarmFailure` dimension `entity_type=offer` | Panel D (stacked by entity_type) | TRACEABLE. Runbook Step 3 CW command is operator-runnable (lines 87-93). Correct namespace dependency applies — see ALERT-3 namespace concern above. |
| Force-warm (post-P6) | `ForceWarmLatencySeconds` via post-warm recheck emit | Panel A post-warm datapoint | DEFERRED. Step 4 requires `--force-warm` CLI which is a P6 item. The runbook correctly marks this as post-P6. |
| Recovery verification | `MaxParquetAgeSeconds < 21600` + ALERT-1/2 return to OK | Panel A threshold line | TRACEABLE. Recovery criteria (runbook lines 108-112) map directly to observable metric and alarm state. |

**Stale-1 verdict**: TRACEABLE for the primary detection-and-diagnosis path. One step (impact
severity assessment) requires CLI invocation rather than CW console. Force-warm step is
correctly deferred. No runbook step references source code.

### DMS-1 traceability chain

| Step | Metric / source | CW dashboard | Assessment |
|---|---|---|---|
| Alert triggers | ALERT-4 on DMS heartbeat absent | Panel C: last successful DMS timestamp (P4 §5 row 1, Panel C) | BLOCKED. ALERT-4 alarm is STASHED (Batch-D). Panel C depends on a metric whose name is unknown (`[DMS_METRIC_NAME]` placeholder at runbook line 239). A paged operator cannot verify the alarm fired correctly nor run the Step 1 CW query without knowing the metric name. |
| Step 1: confirm DMS absent | `aws cloudwatch get-metric-statistics --metric-name [DMS_METRIC_NAME]` | N/A | OPERATOR DEPENDENCY. The placeholder at runbook line 239 is explicit and honest about the gap. However, it leaves the operator unable to execute Step 1 without consulting `autom8y_telemetry` package source — which defeats the "no source code" criterion. |
| Step 2: check Lambda invocation history | CloudWatch Logs, not a CW metric | N/A | LOG DEPENDENCY. This is standard operational practice and acceptable for a P1 escalation path. |
| Recovery verification | New DMS datapoint in `Autom8y/AsanaCacheWarmer` | Panel C | BLOCKED UNTIL METRIC NAME RESOLVED. |

**DMS-1 verdict**: PARTIALLY TRACEABLE. The logical structure is correct. The gap is the
unresolved DMS metric name (`emit_success_timestamp` encapsulation in `autom8y_telemetry`).
Steps 1 and recovery verification require resolving this name before the runbook is
operator-executable without source-code access. This is P4's "Blind Spot 1" (observability
spec line 724) — thermal-monitor identified it correctly as the highest-priority gap. What
P4 does not do is provide a resolution path before Track B probes.

### S3-1 (ALERT-5) traceability chain

ALERT-5 cannot be traced to a CW alarm because the underlying `FreshnessErrorCount` metric is
not emitted as a CW metric (WI-8 emits to stderr only; reclassified as a Logs Insights query
per HANDOFF dossier §A.4). A paged operator receiving an "S3 IO error rate" alert would be
arriving via a CW Logs Insights alarm, not a metric alarm — a fundamentally different
operational topology than what P4 §3 ALERT-5 specifies. The runbook Scenario S3-1 maps to the
correct diagnosis steps, but the alarm path that triggers it is mis-specified in P4.

---

## §4 — Self-Review Surfacing: Where P4 May Be Over-Claiming or Under-Claiming

### Over-claims in P4

**Over-claim 1: ALERT-5 as metric alarm**

P4 §3 ALERT-5 (observability spec lines 260-272) specifies a CloudWatch alarm config with
`Namespace: Autom8y/FreshnessProbe` and `Metric: FreshnessErrorCount`. This is over-claiming:
the `FreshnessErrorCount` metric does not exist in the implementation. The 10x-dev handoff
§A.4 (lines 493-496) accepts the reclassification to a Logs Insights query, but this
acceptance is only in the handoff dossier — not in P4 itself. P4 §3 still shows the full
CW alarm config for a metric that is unimplemented. An operator reading P4 without the dossier
would provision the alarm against a metric that will never receive datapoints.

Evidence: `__main__.py` grep returns no `FreshnessErrorCount` emit call; `cloudwatch_emit.py`
ALL_CLI_METRICS frozenset at lines 51-58 does not include `FreshnessErrorCount`. The
`FreshnessError` exception at `freshness.py:39-42` routes to stderr via `_emit_freshness_io_error`
at `__main__.py:906` — no CW metric emission.

**Over-claim 2: ALERT-3 alarm deployed**

P4 §3 ALERT-3 (observability spec lines 209-231) presents a complete alarm config as if the
alarm exists or will exist from a known source. The 10x-dev handoff explicitly flags ALERT-3
ownership as UNCLEAR (dossier line 196: "OWNERSHIP UNCLEAR — see §5(c) re-handoff request")
and leaves it as DEFERRED-PENDING-AWS-VERIFICATION (dossier §A.4 line 487). P4's presentation
of the alarm config implies it is a planned design artifact, but the deployment path is
unresolved. The P4 spec should have carried an explicit [UNATTESTED] tag on this alarm.

**Over-claim 3: ALERT-4 (DMS alarm) presented as a gap-to-be-closed**

P4 §3 ALERT-4 (lines 235-256) describes the alarm config. The §8 DMS Alarm Verification
section correctly concludes "ALARM NOT FOUND IN WORKTREE IaC" and declares it "DEFERRED TO
P5A." However, the actual implementation state is more specific: the alarm is STASHED in a
cross-repo Terraform stash (`autom8y` repo `stash@{0}`) per HANDOFF dossier line 188. P4's
framing ("no IaC found in worktree") is accurate but incomplete — it doesn't distinguish
"never written" from "written but cross-repo-stashed." An operator reading P4 would not know
the Terraform code exists; they would author it from scratch and create a duplicate.

### Under-claims in P4

**Under-claim 1: ALARMED_METRICS frozenset includes ForceWarmLatencySeconds**

P4 §1 SLI-2 and §3 discuss `ForceWarmLatencySeconds` as a latency-only metric with no alarm.
The P4 spec is internally consistent on this point. However, the implementation's
`ALARMED_METRICS` frozenset at `cloudwatch_emit.py:68-75` includes `ForceWarmLatencySeconds`
as "alarmable in principle." The spec says "no alarm," the code says "alarmable in principle
for future extensibility." This is not a bug — the docstring says "only MaxParquetAgeSeconds
has an alarm wired today" — but a rite-disjoint operator reading `ALARMED_METRICS` might
conclude ForceWarmLatencySeconds has or will have an alarm, contradicting the spec's
"no-alarm-today" stance. P4 should note that the code's `ALARMED_METRICS` frozenset is
forward-looking, not a claim that alarms are currently wired for those metrics.

**Under-claim 2: CoalescerDedupCount coverage of stampede observation**

P4 §6 Lens 8 (observability spec lines 403-405) correctly identifies the CoalescerDedupCount
coverage gap and assigns it as a DEFER item. However, the implementation has now LANDED the
metric at `coalescer.py:34-67` per the HANDOFF dossier (line 180: `[WIRED]`). P4 therefore
under-claims: it describes a gap that has been closed. This is a timing artifact (P4 was
authored before Batch-B implementation) and does not constitute a design flaw, but the lens
rubric in P4 lists CoalescerDedupCount as unimplemented when it is in fact shipped.

---

## §5 — C-6 Hard Constraint Cross-Validation

**Constraint**: `SectionCoverageDelta` MUST NOT be wired to any CloudWatch alarm.

### Mechanical enforcement check

`cloudwatch_emit.py:88-106` implements `c6_guard_check(metric_name)`:

```python
if metric_name in ALL_CLI_METRICS and metric_name not in ALARMED_METRICS:
    raise C6ConstraintViolation(
        f"PRD §6 C-6 / ADR-006: metric '{metric_name}' MUST NOT be wired to "
        "any CloudWatch alarm. SectionCoverageDelta is informational only ..."
    )
```

`ALARMED_METRICS` (lines 68-75) is a frozenset that explicitly excludes `SectionCoverageDelta`.
The set difference `ALL_CLI_METRICS - ALARMED_METRICS` = `{SectionCoverageDelta}` exactly. Any
caller invoking `c6_guard_check("SectionCoverageDelta")` at an alarm-wiring site will receive a
`C6ConstraintViolation` at runtime. The guard is mechanically enforced — it is not comment-only.

Evidence: `cloudwatch_emit.py:88-106` (`c6_guard_check` function body visible in git show
output); `ALARMED_METRICS` frozenset at `cloudwatch_emit.py:68-75` confirms `SectionCoverageDelta`
is absent.

### Runbook check

The runbook Quick Reference table (runbook lines 374-384) lists:

```
ALERT-6: SectionCoverageDelta > 0 | NO ALERT — informational | No action needed per PRD C-6
```

The runbook does not instruct operators to alarm on `SectionCoverageDelta` or to take action
when it is nonzero. Scenario S3-1 and all other scenarios are silent on this metric.

### P4 spec check

P4 §3 ALERT-6 (observability spec lines 276-279) is explicit: "Per PRD C-6: empty sections are
expected behavior. `SectionCoverageDelta > 0` is NOT an alert condition." P4 §4
`SectionCoverageDelta` panel (spec line 332) labels it "informational only; no threshold line."

**C-6 verdict**: PASS. The constraint is mechanically enforced in code, explicitly documented
in the spec, and absent from all runbook action paths. The three-way cross-validation is clean.

---

## §6 — Lens-3 Verdict

**Lens-3 question**: Does the implemented telemetry surface sufficiently observe (a) the
freshness-bound (lens 1), (b) the failure-mode (lens 4), (c) the staleness-bound (lens 6) such
that a rite-disjoint operator can detect anomalies and discharge runbooks without reading the
source code?

### Dimension (a) — freshness-bound (lens 1 coverage)

The `MaxParquetAgeSeconds` metric is LANDED at `cloudwatch_emit.py:1-233`, computed at
`freshness.py:202`, and wired at `__main__.py:893`. ALERT-1 and ALERT-2 are specified against
this metric with correct threshold derivation from PRD G2 (21600s). The `SectionAgeP95Seconds`
metric provides distribution-aware visibility. The Stale-1 runbook is traceable from alert to
recovery verification. PASS.

### Dimension (b) — failure-mode (lens 4 coverage)

| Failure mode | Detection path | Verdict |
|---|---|---|
| Cache miss (no parquet) | ALERT-5 (`kind=not-found`) — but ALERT-5 is a Logs Insights query, not a CW metric alarm as specified in P4 | PARTIAL |
| Cache stale (old parquet) | ALERT-1 + ALERT-2 via `MaxParquetAgeSeconds` — LANDED and deployed | PASS |
| Warmer Lambda failure | ALERT-3 via `WarmFailure` — metric LANDED; alarm deployment UNCLEAR (HANDOFF dossier line 196) | PARTIAL |
| S3 unavailability | ALERT-5 (`kind=network`) — same reclassification issue as cache-miss path | PARTIAL |
| Warmer timeout (self-continue) | Correctly not alarmed; CheckpointSaved metric at `cache_warmer.py:422` informational | PASS |
| Warmer never triggered | ALERT-4 DMS (24h) — STASHED Batch-D; metric name unresolved | PARTIAL |

Failure-mode observability is architecturally sound. The three PARTIAL verdicts are
deployment-state gaps (alarms specified but not deployed), not design gaps. A rite-disjoint
operator today has no CW alarm for warmer failure, S3 cache-miss, or DMS absence.

### Dimension (c) — staleness-bound (lens 6 coverage)

The staleness-bound is observable through `MaxParquetAgeSeconds` (fleet-level max) and
`SectionAgeP95Seconds` (distribution-aware). Both are LANDED. The `--strict` exit-code gate
provides a programmatic staleness-enforcement surface. The 6h / 21600s threshold is derived
correctly from PRD G2 and realized consistently across the CLI gate and the CW alarm threshold.
PASS.

### Aggregate lens-3 verdict

**PASS-WITH-NOTE**

The primary freshness-heat surface is observable and operable from deployed telemetry. The
C-6 constraint is mechanically enforced. The Stale-1 runbook is traceable end-to-end. Three
material notes prevent a clean PASS:

**Note 1 (MATERIAL)**: ALERT-5 is over-claimed as a CW metric alarm in P4. The underlying
`FreshnessErrorCount` metric does not exist. S3 IO error observability relies on stderr logs
and a Logs Insights query. The S3-1 runbook scenario is valid; the alert-path that triggers
it is mis-specified in P4.

**Note 2 (MATERIAL)**: The DMS metric name (`emit_success_timestamp` return) is unresolved in
both P4 and the runbook (placeholder `[DMS_METRIC_NAME]` at runbook line 239). A rite-disjoint
operator cannot execute the DMS-1 runbook Step 1 CW query without consulting package source.

**Note 3 (INFORMATIONAL)**: ALERT-3 alarm deployment status is unverified. The `WarmFailure`
metric is LANDED; the alarm is OWNERSHIP UNCLEAR per 10x-dev handoff. The SLI-to-SLO linkage
(SLI-3 ratio over 7d vs ALERT-3 count over 1h) is a semantic mismatch that does not prevent
detection but does mean SLO-2 is not directly alarmed at the SLO's own time granularity.

---

## §7 — Concurrence with thermal-monitor's Adjacent Design Review

Adjacent artifact: `.ledge/reviews/P7A-design-review-2026-04-27.md` (station P7.A.1).

Thermal-monitor's lens-4 (failure-mode) verdict: PASS-WITH-NOTE. The note explicitly
acknowledges AP-3 (parquet not invalidated on task mutation) and that the
`CoalescerDedupCount` metric is LANDED at `coalescer.py:34-67` (P7A-design-review line 89).

Thermal-monitor's lens-6 (staleness-bound) verdict: PASS-WITH-NOTE. Note covers GID-to-name
mapping deferral. The mechanism is in place; population deferred.

This cross-check finds:

**CONCUR on lenses 1, 5, 6, 10** — the design-review verdicts for these lenses are supported
by the same evidence base this cross-check examined. No divergence.

**CONCUR on lens-4 PASS-WITH-NOTE** — the AP-3 acceptance is correctly characterized.
CoalescerDedupCount being LANDED is consistent with the handoff dossier.

**DIVERGE-WITH-REASON on lens-3 scope** — thermal-monitor correctly suspended lens-3. This
cross-check finds lens-3 should be PASS-WITH-NOTE (not FAIL), but with three named notes that
require carry-forward. The two MATERIAL notes (ALERT-5 over-claim, DMS metric name gap) mean
the observability surface is incomplete for a fully source-code-free operator. These are not
design failures — they are deployment-state and external-dependency gaps — but they are
substantive enough to warrant explicit flagging in the Track A close artifact.

**Concurrence verdict**: CONCUR on 5 of 5 non-lens-3 load-bearing lenses, DIVERGE-WITH-REASON
on the scope of lens-3 (thermal-monitor: suspended; heat-mapper: PASS-WITH-NOTE with three
named concerns, two MATERIAL).

---

## §8 — Carry-Forward Concerns

### C-1 — ALERT-5 over-claim in P4 (MATERIAL)

**Finding**: P4 §3 ALERT-5 specifies a CloudWatch metric alarm against `FreshnessErrorCount`
in `Autom8y/FreshnessProbe`. The metric does not exist in the implementation. The alarm type
should be a CloudWatch Logs Insights alarm or the metric must be implemented. The 10x-dev
handoff accepts the reclassification in dossier §A.4 but P4 itself is not updated.

**Evidence anchor**: `cloudwatch_emit.py` ALL_CLI_METRICS frozenset (no `FreshnessErrorCount`
entry); HANDOFF-10x-dev-to-thermia-2026-04-27.md §A.4 line 493-496; observability spec lines
260-272.

**Recommended action**: Update P4 ALERT-5 to reflect the Logs Insights alarm path, OR
implement the `FreshnessErrorCount` CW metric and keep the spec as-is. The spec as currently
written will mislead any engineer provisioning this alarm.

**Gate implication**: Does not block Track A close. Does not block Track B deploy (S3 error
detection is still possible via Logs Insights). Should be resolved before production alarm
provisioning (Batch-D).

### C-2 — DMS metric name unresolved (MATERIAL)

**Finding**: The metric name emitted by `autom8y_telemetry.aws.emit_success_timestamp` is not
known from P4, the runbook, or the implementation files visible in this worktree. The runbook
DMS-1 Step 1 command uses `[DMS_METRIC_NAME]` as a literal placeholder. A paged operator
cannot execute this step without consulting the `autom8y_telemetry` package source.

**Evidence anchor**: Runbook DMS-1 Step 1 (line 239); P4 §8 "Blind Spot 1" (observability
spec line 724); P4 §8 alarm config (line 640: "Metric: [the metric name emitted by
emit_success_timestamp — must be confirmed from autom8y_telemetry.aws source]").

**Recommended action**: Before Batch-D DMS alarm provisioning, read
`autom8y_telemetry.aws.emit_success_timestamp` source and populate the metric name in both
P4 §8 and the runbook DMS-1 Step 1 command. This is the single highest-priority P4 gap
flagged by the heat-mapper.

**Gate implication**: Does not block Track A close. BLOCKS Track B Probe-2 (alarm firing
verification) and DMS-1 runbook operationalization.

### C-3 — ALERT-3 deployment status and namespace ambiguity (INFORMATIONAL)

**Finding**: P4 §3 ALERT-3 presents an alarm config but the target namespace for `WarmFailure`
is ambiguous: settings.py default `autom8/lambda` vs Terraform env default `autom8/cache-warmer`
vs ADR-006 `autom8y/cache-warmer` (lowercase-y, coalescer constant). An operator wiring ALERT-3
cannot determine the correct namespace from P4. The alarm deployment is OWNERSHIP UNCLEAR per
10x-dev handoff.

**Evidence anchor**: `cache_warmer.py:20` (docstring "CLOUDWATCH_NAMESPACE default: autom8/cache-warmer");
`settings.py:38` (ASANA_CW_NAMESPACE default "autom8/lambda"); `coalescer.py:28`
(COALESCER_METRIC_NAMESPACE = "autom8y/cache-warmer"); HANDOFF dossier line 196 (OWNERSHIP UNCLEAR).

**Recommended action**: P7.A.3 (ALERT predicates sub-phase) should execute
`aws cloudwatch describe-alarms --alarm-name-prefix "AsanaCacheWarmer-Failure"` and record
the actual namespace of any existing alarm. If none found, the namespace should be resolved
from the deployed Terraform environment variable before Batch-D alarm provisioning.

**Gate implication**: Does not block Track A close. Should be resolved in P7.A.3 artifact
before Track B Probe-2.

---

## §9 — Recommendation to thermal-monitor

Based on this cross-check, the Track A close artifact should reflect:

1. **Lens-3 verdict**: PASS-WITH-NOTE (not a blocker, not a FAIL). The primary freshness and
   staleness surfaces are observable. The notes are deployment-state gaps, not design defects.

2. **P4 revision recommended (not required for Track A close)**: The ALERT-5 over-claim (C-1)
   should be corrected in the P4 spec before Batch-D alarm provisioning. The DMS metric name
   placeholder (C-2) should be resolved and populated before the DMS runbook can be
   operator-executable. These are pre-production-alarm items; they do not block the design-review
   attestation.

3. **P7.A.3 scope confirmation**: The ALERT predicate sub-phase should specifically address
   the ALERT-3 namespace question (C-3) by running the `describe-alarms` predicate and
   recording the result, consistent with the HANDOFF dossier §A.4 DEFERRED-PENDING-AWS-VERIFICATION
   disposition.

4. **Track A close artifact coverage**: C-1, C-2, and C-3 should each appear in the
   Verification Attestation `## Deferred Decisions` section with named owners and resolution
   paths, so Track B in-anger probe scheduling accounts for them.

---

## Handoff Checklist

- [x] `thermal-assessment.md` equivalent: lens-3 cross-check artifact produced at correct path
- [x] Every claim in §1-§5 cites file:line or git-show evidence
- [x] C-6 constraint cross-validated mechanically (code + spec + runbook)
- [x] ALERT-5 over-claim surfaced with evidence anchors
- [x] DMS metric name gap surfaced as operator-actionable item
- [x] ALERT-3 namespace ambiguity documented
- [x] Concurrence verdict with P7A-design-review-2026-04-27.md: CONCUR (5/5) + DIVERGE-WITH-REASON (lens-3 scope)
- [x] Lens-3 verdict: PASS-WITH-NOTE
- [x] Carry-forward concerns enumerated (C-1 MATERIAL, C-2 MATERIAL, C-3 INFORMATIONAL)
