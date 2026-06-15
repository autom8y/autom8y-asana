---
type: review
status: accepted
evidence_grade: MODERATE
station: SOAK-S2 (observability-engineer)
rite: sre — "Soak Sentinel & Clear-Readiness"
date: 2026-06-11
soak_anchor: 2026-06-11T15:24:21Z on :511 / 49099b1 (clear 2026-06-18T15:24:21Z)
subject: RECEIVER_SLI_EMF_ENABLED — cost/benefit decision surface
flip_authority: OPERATOR-ONLY (ECS env change = new task-def = deploy = soak-clock RESET)
self_ref_cap: MODERATE (single-author observability assessment; no rite-disjoint corroboration)
---

# Observability Report: `RECEIVER_SLI_EMF_ENABLED` Decision Surface (asana receiver SLI)

## Executive Summary

The ship-dark EMF emitter `emit_receiver_sli_emf` (landed CR-3 GATE-2 P2-a,
`d9ab8f46`) is gated behind the env flag `RECEIVER_SLI_EMF_ENABLED`, which is
**ABSENT from the `:511` task-def env** — the emitter no-ops on every request
(`src/autom8_asana/api/metrics.py:405-406`). This review establishes, by live
AMP/ECS/terraform receipts, that **the flag currently buys nothing downstream**:
the metric namespace it would write to (`Autom8y/AsanaReceiverSLI`) is referenced
NOWHERE in the autom8y monorepo or its terraform (zero alarms, zero dashboards,
zero extraction config), and the three deployed receiver-SLI alert rules (#486
FastBurn / SlowBurn / HeartbeatAbsent — all `health: ok` live in AMP) consume the
platform HTTP histogram `autom8y_http_request_duration_seconds_count`, **NOT** the
domain counter `autom8y_asana_receiver_query_outcome_total` that the EMF emitter
mirrors. The AMP OTLP counter is alive and proven (1392 successes, project arm).
The flip is a deliberate ECS env change = a deploy = a **soak-clock reset**, which
alone disqualifies any mid-soak flip. **RECOMMENDATION: leave-dark-keep-optionality
— do NOT flip pre-`2026-06-18`; sequence the flip (if pursued) into the first
deliberate post-soak deploy, AND make it conditional on the cross-repo EMF sink +
a CloudWatch alarm consumer existing first, else the second plane is a silent-dead
write.** Full reasoning and the rejected alternatives are in §Recommendations.

## Scope

- Service analyzed: `asana` receiver (ECS FastAPI, single uvicorn worker, instance
  `ip-10-0-138-103.ec2.internal:8000` live at probe time).
- Decision under review: flip vs leave-dark vs delete of `RECEIVER_SLI_EMF_ENABLED`.
- Data sources: source (`src/autom8_asana/api/metrics.py`, `.../routes/query.py`);
  live AMP workspace `ws-26b271ef-afd6-4158-82cc-74dbcb273976` (`autom8y-production`,
  ACTIVE); autom8y monorepo terraform tree (`/Users/tomtenuta/code/a8/repos/autom8y/terraform`).
- Probe timestamp: 2026-06-11 (`value[0]` epoch `1781197311`–`1781197313`, ~17:01Z).
- Authority: READS only. The flip is an operator lever, post-soak. Every flip
  mention in this artifact carries that fence.

---

## Current State — What Exists vs What Is Behind The Flag

### G-PROVE Receipts Table (file:line + pasted-JSON for every claim)

| # | Claim | Method | Receipt |
|---|-------|--------|---------|
| R1 | EMF emitter exists, no-ops unless flag set | file-read | `src/autom8_asana/api/metrics.py:405-406` — `if not _receiver_sli_emf_enabled():` then `return` (first two body statements of `emit_receiver_sli_emf`) |
| R2 | Flag env var name | file-read | `src/autom8_asana/api/metrics.py:355` — `RECEIVER_SLI_EMF_FLAG_ENV = "RECEIVER_SLI_EMF_ENABLED"` |
| R3 | Flag is read at CALL time (per-task flippable, no code change) | file-read | `src/autom8_asana/api/metrics.py:358-370` — `_receiver_sli_emf_enabled()` reads `os.environ.get(...)` in-body, accepts `{1,true,yes,on}` |
| R4 | EMF target namespace (the published cross-repo contract) | file-read | `src/autom8_asana/api/metrics.py:354` — `RECEIVER_SLI_EMF_NAMESPACE = "Autom8y/AsanaReceiverSLI"` |
| R5 | EMF metric set + dimension | file-read | `src/autom8_asana/api/metrics.py:417-431` — `ReceiverQueryOutcomeSuccess`, `ReceiverQueryOutcomeServerError`, `ServingStaleTotal`; `Dimensions: [["arm"]]`; `"arm": entity_type` |
| R6 | Emitter writes one JSON line to stdout (no network I/O) | file-read | `src/autom8_asana/api/metrics.py:437` — `sys.stdout.write(json.dumps(document) + "\n")` |
| R7 | Call site is the query route finally-block, body-parameterized arms only | file-read | `src/autom8_asana/api/routes/query.py:589`,`604-608` — `if ctx.project_gid is None:` then `emit_receiver_sli_emf(entity_type, success=..., serving_stale_total=_serving_stale_total_value())` |
| R8 | The flag mirror does NOT gate the AMP OTLP counter (that's unconditional) | file-read | `src/autom8_asana/api/routes/query.py:598` — `record_receiver_query_outcome(...)` is OUTSIDE the EMF gate, same finally-block; flag-independent |
| R9 | AMP OTLP counter is ALIVE (project/success) | api-probe (AMP `/api/v1/query`) | `sum by (entity_type,outcome)(autom8y_asana_receiver_query_outcome_total)` → `{entity_type:"project",outcome:"success"} = "1392"` (epoch `1781197311`) |
| R10 | #486 receiver-SLI alert rules are LIVE and `health: ok` in AMP | api-probe (AMP `/api/v1/rules`) | group `slo_asana_receiver_alerts`: `AsanaReceiverAvailabilityFastBurn` / `...SlowBurn` / `AsanaReceiverHeartbeatAbsent`, all `health: ok` |
| R11 | Those alerts consume the HTTP histogram, NOT the domain counter | api-probe (AMP `/api/v1/rules`) | FastBurn expr → `slo:asana_receiver:availability_burn_rate:1h > 14.4 and ...:5m > 14.4`; recording rule `sli:asana_receiver:availability:5m` = `1 - ((sum(rate(autom8y_http_request_duration_seconds_count{route_class="business",service="asana",status=~"5.."}[5m])) or vector(0)) / sum(rate(autom8y_http_request_duration_seconds_count{route_class="business",service="asana"}[5m])))` |
| R12 | HeartbeatAbsent dead-man also keys off the HTTP histogram (probe class) | api-probe (AMP `/api/v1/rules`) | `AsanaReceiverHeartbeatAbsent` expr = `absent(autom8y_http_request_duration_seconds_count{route_class="probe",service="asana"})`, `for: 600` |
| R13 | `Autom8y/AsanaReceiverSLI` namespace referenced NOWHERE in autom8y monorepo | bash-probe | `grep -rn "AsanaReceiverSLI" /Users/tomtenuta/code/a8/repos/autom8y/` → `GREP_RC=1` (no match) |
| R14 | Sibling Asana CW namespaces ARE referenced (so R13 is not a search miss) | bash-probe | `grep -rn "Autom8y/Asana" .../terraform/` → hits for `Autom8y/AsanaCacheWarmer` (`services/grafana/alerting.tf:840`, `services/asana/main.tf:824`), `AsanaAudit` (`:866`), `AsanaInsights` (`:892`) |
| R15 | EMF-mirror metric NAME is absent from AMP (two disjoint planes) | api-probe (AMP) | `ReceiverQueryOutcomeSuccess` → `data.result` length `0` |
| R16 | asana repo has zero terraform (rules cannot live here) | bash-probe | `find ... -name "*.tf"` → `tf_count=0` |
| R17 | The flag is referenced only in asana tests/spec/source — never in monorepo env/task-def | bash-probe | asana hits: `tests/unit/api/test_receiver_sli_emf_export.py:39`, TDD spec, `metrics.py:355`; monorepo grep `RECEIVER_SLI_EMF_ENABLED` → no match |
| R18 | S7 fallback-cause + serving_stale counters are live in AMP (the EMF co-read source) | api-probe (AMP) | `autom8y_asana_receiver_query_fallback_cause_total` → `data_2xx=1389`, `honest_refusal=3` (project); `autom8y_asana_serving_stale_total{entity_type="project"} = 1388` |
| R19 | Organic cadence ~98/hr (the ~100-class burst) | api-probe (AMP) | `rate(autom8y_asana_receiver_query_outcome_total{entity_type="project",outcome="success"}[1h]) * 3600` → `98.41` |

### Metrics

| Surface | Plane | Live? | Consumed downstream? | Receipt |
|---------|-------|-------|----------------------|---------|
| `autom8y_asana_receiver_query_outcome_total` (domain counter; **flag-independent**) | AMP / OTLP | YES (1392, project/success) | By the AMP scrape; NOT by any deployed alert rule | R8, R9, R11 |
| `autom8y_http_request_duration_seconds_count` (platform HTTP histogram) | AMP / OTLP | YES (denom present; probe class count=1) | BY all three #486 alert rules + recording rules | R10, R11, R12 |
| EMF doc → `Autom8y/AsanaReceiverSLI` (`ReceiverQueryOutcomeSuccess`/`...ServerError`/`ServingStaleTotal`, dim `arm`) | CloudWatch (EMF extraction) | **NO — emitter no-ops; namespace has no producer and no consumer** | nothing references it | R4, R5, R13, R15 |
| `autom8y_asana_receiver_query_fallback_cause_total` (S7 disaggregation; flag-independent) | AMP / OTLP | YES (data_2xx=1389, honest_refusal=3) | Read by S7 verdict accessor (in-process) | R18 |
| `autom8y_asana_serving_stale_total` (co-read context) | AMP / OTLP | YES (1388) | Co-read in EMF doc AND in-process `success_rate_with_stale_context` | R18 |

**The precise telemetry delta gated by the flag** (what exists ONLY behind it, vs
already covered): the flag gates EXACTLY ONE thing — a **second observability plane**
(CloudWatch EMF, namespace `Autom8y/AsanaReceiverSLI`) carrying the per-arm outcome
constituents and `ServingStaleTotal` (R4, R5). Everything semantically equivalent
already exists in AMP and is flag-independent: the success/server_error split
(`autom8y_asana_receiver_query_outcome_total`, R9), the stale co-read
(`autom8y_asana_serving_stale_total`, R18), and the cause disaggregation
(`...fallback_cause_total`, R18). The flag adds NO new *information* the receiver
can't already self-report to AMP; it adds a *durable, deploy-surviving,
fleet-aggregated sink* on a *different transport* (CloudWatch, not the OTLP scrape).
That sink's value is entirely contingent on a consumer existing — and none does (R13).

### Alerting

| Alert (live in AMP, `slo_asana_receiver_alerts`) | Class | Consumes | False-positive guard | Action on flip? |
|---|---|---|---|---|
| `AsanaReceiverAvailabilityFastBurn` (page) | symptom (5xx burn) | `autom8y_http_request_duration_seconds_count` business/asana | multi-window 1h+5m > 14.4, `for: 120s` | **none** — does not read the EMF/domain metric |
| `AsanaReceiverAvailabilitySlowBurn` (ticket) | symptom (5xx burn) | same HTTP histogram | 6h+30m > 6, `for: 900s` | **none** |
| `AsanaReceiverHeartbeatAbsent` (page, dead-man) | symptom (absence) | `...{route_class="probe",service="asana"}` | `absent(...)`, `for: 600s` | **none** |

The deployed alerting plane is symptom-based and complete against the HTTP-histogram
SLI. The EMF mirror would not touch it. (Note: SLI:5m read `NaN` at probe time — zero
business-traffic denominator that instant — which is precisely why the absence-based
HeartbeatAbsent dead-man exists alongside the burn-rate pair. The dead-man was
satisfied: probe-class series present, count=1, R12.)

---

## Gap Analysis

### Critical Gaps (Must Fix) — none introduced by leaving the flag dark
The deployed symptom-based alert plane (R10–R12) catches receiver 5xx burn and
liveness loss off the HTTP histogram independently of this flag. Leaving the flag
dark creates **no** alerting blind spot today.

### Important Gaps (Should Fix)
1. **Naming-contract trap if ever flipped without a consumer**: the EMF namespace
   `Autom8y/AsanaReceiverSLI` is a *published cross-repo contract* (`metrics.py:354`
   comment: "renaming is a breaking change to the monorepo alarm/gate consumer") —
   but **no such consumer exists** (R13). Flipping the flag would begin paying
   CloudWatch custom-metric + PutLogEvents cost to feed a namespace nothing reads:
   a vanity-metric / silent-dead-plane anti-pattern. → Gate any flip on the consumer
   existing first.
2. **The domain counter the EMF mirrors is itself not wired to any alert** (R8/R9
   vs R11). If the intent of P2-a was "a receiver-self-measured SLI independent of
   the platform HTTP histogram," that intent is unrealized on BOTH planes: AMP has
   the counter but no rule reads it; CloudWatch has a rule-capable namespace but no
   producer. This is a coherence gap, not a soak blocker (the AMBER-2 note in
   `.know/telos/dataframe-resolution-coherence.md:128` already catalogs it as
   DEFERRED-OBSERVABILITY).

### Nice-to-Have
1. Single-arm reality: only the `project` arm is live (R9, R18) — no `section`
   arm series and no `server_error` series have been recorded. A second
   observability plane buys nothing extra until the section arm actually flows
   traffic and a 5xx is observed.

---

## The Decision Surface

### (a) What the EMF mirror would ADD
- **A second observability plane for the dead-man.** A CloudWatch-native alarm on
  `Autom8y/AsanaReceiverSLI` would be independent of the AMP scrape path (OTLP →
  collector → AMP). If that scrape path wedges, the EMF plane (awslogs →
  CloudWatch Logs → EMF extraction) survives. This is real defense-in-depth value
  — BUT only once a CloudWatch alarm is built to consume it (none exists, R13), and
  the AMP `HeartbeatAbsent` dead-man (R12) already covers the most common scrape-loss
  case from the other direction.
- **Deploy-surviving, fleet-aggregated durability** the process-local Prometheus
  counter lacks (the stated P2-a rationale, `metrics.py:332-335`): the AMP counter
  resets on every ECS task replacement (visibly so — see Appendix #10, the
  counter-reset across the deploy boundary). EMF → CloudWatch would give a durable
  time series the deploy-gate could query *after* the soak. Value is real but
  **post-soak by nature** (the soak's clock is held by content receipts, not by a
  durable SLI series).
- **Chaos-design precondition**: the EXP-1/2/4/5 self-proving chain (per the
  storage-namespace / cure-recovery game-day lineage) listed the EMF self-measure
  as a precondition for receiver-side self-attestation under fault. The flag-dark
  state means those experiments cannot read a durable receiver SLI; flipping it
  (post-soak) unblocks that self-proving.

### (b) What it COSTS
- **CloudWatch custom-metric dollars**: EMF extraction creates custom metrics per
  unique dimension set. Dimension is `arm` (R5) → 2 cardinality (project, section)
  × up to 3 metric names = ≤6 custom metrics. Low. (~$0.30/metric/mo order — trivial.)
- **PutLogEvents / log-ingest dollars**: ONE EMF JSON line per body-parameterized
  request (R6, R7). At the observed organic cadence **~98 req/hr** (R19) ≈ 2.4k
  docs/day ≈ ~71k/mo. Each EMF doc is ~300–400 bytes → ~25 MB/mo ingest. At
  CloudWatch Logs ingest pricing (~$0.50/GB) this is **cents/month** at current
  organic volume. The *real* cost risk is a traffic spike or a retry storm
  multiplying per-request stdout volume — which is exactly the "stdout-volume
  surprise before the sink exists" the ship-dark default was designed to prevent
  (`metrics.py:348-350`). At today's ~100/hr cadence the dollar cost is negligible;
  the discipline cost is that you are paying *anything* for a plane nobody reads.
- **stdout contention**: the EMF line shares the structured-log stdout stream
  (`metrics.py:433-436`); at higher volume it dilutes log density. Bounded, but real.

### (c) The RISK of flipping it mid-soak — DISQUALIFYING
Setting `RECEIVER_SLI_EMF_ENABLED` is an **ECS env change → a new task-def revision
→ a deploy** (operator lever, post-soak). A deploy replaces the running task, which:
1. **Resets the soak clock.** The grandeur anchor holds the 7-day telos-soak
   (anchor `2026-06-11T15:24:21Z` on `:511`/`49099b1`, clear `2026-06-18`) as a
   sentinel proven by live content receipts on a stable substrate. A task-def roll
   re-anchors the soak — the exact failure mode already burned once this saga (the
   14:59 anchor "raced by the self-inflicted #129 deploy," per MEMORY). **This alone
   sequences any flip to POST-soak.**
2. Resets the process-local AMP counter (cosmetic, but adds noise to the very SLI
   under discussion — see Appendix #10).
3. Would light up a *new, unconsumed* CloudWatch plane mid-soak, adding a moving
   part during the watch window for zero in-soak benefit.

### (d) Options enumerated

| Option | Consequence | Verdict |
|--------|-------------|---------|
| **flip-at-next-deliberate-post-soak-deploy** | Lights the second plane. But UNCONDITIONALLY flipping still feeds a namespace with no consumer (R13) — pays ingest for a silent-dead plane. Only sound if *bundled with* building the CloudWatch alarm + confirming the EMF extraction sink first. | Acceptable ONLY as a conditional bundle, not as a bare env flip. |
| **leave-dark-and-delete-the-dead-code** | Removes ~80 lines (`metrics.py:326-446`) + the call-site EMF arm (`query.py:601-608`) + the test. Eliminates the optionality permanently. The emitter is hot-path-safe, test-covered, costs nothing while dark (R1), and its co-read design (ServingStaleTotal in-document, R5) is non-trivial to re-derive. Deleting forecloses the chaos-self-proving precondition and the AMP-scrape-independent plane for no cost saving (dark = free). | Rejected — destroys a correct, free, future-load-bearing capability to remove imaginary cost. |
| **leave-dark-keep-optionality** | The emitter stays dark (free, R1), the soak clock is untouched, the deployed AMP alert plane (R10–R12) continues to carry the dead-man, and the flip remains a one-env-var operator lever available the moment a consumer is built post-soak. Carries the AMBER-2 deferral forward honestly. | **SELECTED.** |

### RECOMMENDATION

**leave-dark-keep-optionality.** Do NOT flip `RECEIVER_SLI_EMF_ENABLED` before the
soak clears (`2026-06-18T15:24:21Z`) — the flip is an operator lever, post-soak, and
mid-soak it would reset the very clock this station guards (§(c)). Keep the emitter
code (it is dark = free per R1, hot-path-safe per R6, and unblocks chaos
self-proving). When the flip IS pursued, it MUST be a *conditional bundle* on a
deliberate post-soak deploy: (1) the cross-repo EMF extraction sink confirmed
present, AND (2) at least one CloudWatch alarm built to consume
`Autom8y/AsanaReceiverSLI` — otherwise the second plane is a silent-dead write
(R13/R15), paying ingest for a namespace nothing reads. The bare env flip alone is
NOT recommended. This routes to **platform-engineer** (the env/task-def change + the
monorepo CloudWatch alarm are infra; the flip is operator-executed) and to the
**incident-commander** for soak-clock sequencing.

Justification, one line: the flag's only product is a *second plane*, and a second
plane with no consumer (R13) and a clock-reset cost (§c) is negative-value
in-soak and zero-value out-of-soak until the consumer exists — so the dominant move
is to preserve the free, correct optionality and gate the flip on its consumer.

---

## Recommendations (by time horizon)

### Quick Wins (< 1 week) — all READ-ONLY / no deploy
1. Record this decision (this artifact) and carry AMBER-2
   (`.know/telos/dataframe-resolution-coherence.md:128`) forward unchanged: flag
   stays dark through soak. No action that touches `:511`.
2. (incident-commander) Note in the soak ledger that `RECEIVER_SLI_EMF_ENABLED` is
   a known dark lever and that flipping it = re-anchor; keep it off the in-soak
   change surface.

### Medium-Term (1–4 weeks, POST-soak) — platform-engineer
1. Build the CloudWatch consumer FIRST: an EMF extraction config + a CloudWatch
   alarm on `Autom8y/AsanaReceiverSLI` (mirror the sibling `Autom8y/AsanaCacheWarmer`
   DMS alarm pattern at `terraform/services/grafana/alerting.tf:840`). Only after it
   exists does the flag have a downstream.
2. Then (operator) flip `RECEIVER_SLI_EMF_ENABLED=true` in the asana task-def env on
   a deliberate post-soak deploy, and template the var in the monorepo task-def
   (currently absent, R17) so the flip is codified, not hand-set.

### Long-Term (> 1 month)
1. Resolve the coherence gap (Important Gap #2): decide whether the
   receiver-self-measured SLI lives on the AMP counter (add a recording/alert rule
   reading `autom8y_asana_receiver_query_outcome_total`) OR the CloudWatch EMF plane —
   pick one canonical sink for the receiver SLI rather than carrying two half-wired
   planes.

## SLI/SLO Proposals

| Service | SLI | Current | Proposed SLO | Error Budget | Note |
|---------|-----|---------|--------------|--------------|------|
| asana receiver | availability = 1 − 5xx-rate (business routes), via `sli:asana_receiver:availability` | live, `health: ok`; instantaneous NaN at zero-traffic instants (R11) | 99.5% (burn budget 0.005, already encoded) | already deployed (#486) | This is the **HTTP-histogram** SLI — the deployed one. NOT EMF-dependent. |
| asana receiver | receiver-self-measured success = `Success/(Success+ServerError)` per arm | counter live (R9) but **no rule consumes it** | DEFER — define only after picking the canonical sink (Long-Term #1) | n/a | Neither plane alerts on it today; flag flip does not change this without a consumer. |

## Next Steps
1. Hold the flag dark through soak-clear `2026-06-18T15:24:21Z` (this station's verdict).
2. Hand the conditional-flip bundle to platform-engineer + incident-commander for
   post-soak sequencing (consumer-first, then operator flip, then codify the env var).

---

## Appendix — Watch Item #10 closure: the AC-6 organic cadence-gap

The monolith AC-6 organic burst is healthy and self-recovered. Empirical timeline
from the receiver project/success counter (`autom8y_asana_receiver_query_outcome_total{entity_type="project",outcome="success"}`,
hourly `increase[1h]`, AMP range query `13:00Z→17:00Z` 2026-06-11): 13:00Z≈60,
14:00Z≈107 (classic ~100-class organic cadence), then the 14:30/15:30 buckets read
0.0 — the GAP — which coincides with the two deploy boundaries (`:510`→`:511`); the
counter-reset across the ECS task replacement is visible as a duplicate timeseries
in the range result (the new instance starts its monotonic counter from zero, so the
old series' `increase` reads flat). The cadence then RESUMED at the 16:30Z bucket =
**98.8** (the value carried in the station context; the receiver-side `rate[1h]*3600`
proxy reads **98.4**, R19) — back to the ~100-class organic cadence, post-canary,
with zero intervention. The gap was a deploy-boundary artifact, not a pipeline
failure: the pipe is healthy (disambiguated by the 06-11 iris live-HTTP smoke, which
proved the serve-path + the receiver SLI counter incrementing on real traffic). The
IC's day-1 attestation carries the authoritative live numbers; this appendix records
the receiver-side counter corroboration only. **Watch item #10: CLOSED — organic,
self-recovered, no action.**

---

*Evidence grade: MODERATE. Single-author observability assessment; the live AMP/
terraform/source receipts are direct (api-probe / file-read / bash-probe per the
G-PROVE table), but the disposition (leave-dark-keep-optionality) is not corroborated
by a rite-disjoint attester, capping the artifact-level grade at MODERATE per
self-ref-evidence-grade-rule. The structural findings R9–R17 are independently
re-verifiable by re-running the cited probes against `ws-26b271ef-afd6-4158-82cc-74dbcb273976`.*
