---
title: "TDD: CR-3 GATE-2 P2-a — Receiver Self-Measurement Export"
type: tdd
status: draft
date: 2026-06-08
author: architect (10x-dev)
initiative: cr3-gate2-receiver-self-measurement-export
provenance_sha: 63b9a831
impact: high
impact_categories: [performance, breaking-change]
supersedes: none
related:
  - scripts/canary/receiver_bulk_fanout_deploy_gate.py
  - src/autom8_asana/api/metrics.py
  - .know/obs.md
  - .ledge/decisions/CR3-RELEASE-GATE2-DEPLOY-READINESS-2026-06-05.md
---

# TDD: CR-3 GATE-2 P2-a — Receiver Self-Measurement Export

## Overview

The CR-3 deploy gate currently proves `>=99%` success by having a canary process
(`receiver_bulk_fanout_deploy_gate.py`) hammer the receiver over HTTP and count
its own observed 2xx/5xx. The receiver already owns the authoritative per-arm SLI
counter (`RECEIVER_QUERY_OUTCOME`), but that counter never reaches a durable metric
backend (AMP/CloudWatch) in a way the gate consumes. This TDD decides HOW the
receiver's self-measured per-arm SLI reaches a durable backend so the gate can
self-prove from the **receiver counter** instead of inferring from canary HTTP.

The decision: emit an **additive EMF-stdout metric** at the existing request seam
(in-repo, fire-and-forget, hot-path-safe), honoring the co-read prohibition by
emitting `serving_stale_total` in the *same* EMF blob; and **hand off** the
backend-binding (log-driver/EMF-extraction or AMP scrape target) and the
alarm/gate IaC to the autom8y monorepo, because that substrate does not exist
in this repo and cannot be created here.

## Context

Source PRD/initiative: CR-3 GATE-2 deploy-readiness (`CR3-RELEASE-GATE2-DEPLOY-READINESS-2026-06-05.md`).
Constraints inherited from ground truth (all verified at `src/` and `.know/` at SHA `63b9a831`):

- `api/metrics.py:103-107` — `RECEIVER_QUERY_OUTCOME` Counter (labels `entity_type`, `outcome`).
- `api/metrics.py:305-318` — `record_receiver_query_outcome(entity_type, success)`; called once per request at `api/routes/query.py:596`.
- `api/metrics.py:477-509` — `receiver_query_success_rate(entity_type)` reads `RECEIVER_QUERY_OUTCOME.collect()` (line 496) — **PROCESS-LOCAL**; the in-process counter resets to zero on every ECS task replacement, so a point-in-time read cannot prove a sustained 10-min `>=99%` across a deploy that itself replaces tasks.
- `api/metrics.py:522-537` — `success_rate_with_stale_context()` enforces the co-read **PROHIBITION** structurally: the success rate is NEVER returned without `serving_stale_total`. **This TDD honors that prohibition at the export boundary.**
- `api/metrics.py:580-587` — OBS-EXPORTS-001 additive-emitter precedent: "Emission is ADDITIVE — no pipeline step, helper, or engine surface is altered." This is the precedent the new emitter follows.
- `api/metrics.py:7` — module contract: "All metric recording is in-memory (fire-and-forget) with no synchronous I/O."

## The Gap (Part a) — Decision

**Question:** Is the gap "counters not exported to AMP" OR "counters scraped but the gate does not consume them"?

**Verified answer: BOTH, but the dominant, blocking gap is "counters not exported to a durable backend at all." The "scraped-but-not-consumed" framing is aspirational — it presumes a scrape pipeline whose existence is unverified.**

### What is `/metrics → AMP` topology, actually?

The receiver runs ECS (`autom8y-asana-service`) and is therefore **scrape-pull**, not push (`.know/obs.md:139-141,176,184-187`). `instrument_app(app, InstrumentationConfig(service_name="asana"))` is wired at `api/main.py:866` and serves `/metrics` locally. But:

- **No AMP / remote-write / managed-prometheus reference exists anywhere in `src/` or `.know/`.** A repo-wide grep for `amp|remote_write|aps-workspace|prometheusremotewrite|managed.?prometheus` returned only false positives (`timestamp`, `amplification`). [SVR receipt R-1 below.]
- **Zero scrape config in-repo** (`prometheus*.yml`, ADOT/otel-collector, `*scrape*`): `find` count = 0. [SVR receipt R-2.]
- **Zero IaC in-repo** (`*.tf` count = 0). The asana satellite has no Terraform; alarm + scrape IaC live in the autom8y MONOREPO (`.know/obs.md:385,441`; `api/metrics.py:587` "SLO targets + burn-rate alert rules live in the autom8y MONOREPO Terraform (asana has 0 .tf)"). [SVR receipt R-3.]
- `.know/obs.md:415,437` — "No scraper configuration in-repo; **scraper identity unknown**." The "Unknown scraper" cell at `obs.md:176` is the authoritative statement: whether `/metrics` is genuinely scraped into AMP is a **cross-repo fact this repo cannot assert**.

**Conclusion on (a):** From this repo's vantage, `/metrics → AMP` is an *unverified-to-nonexistent* pipeline. We MUST NOT design as if "the counter is already in AMP and we just need the gate to read it" — that premise is unverifiable here (it would violate premise-integrity). The export gap is real and primary. The consumption gap is also real (the gate reads canary HTTP — `_evaluate_gate` at `scripts/canary/...:638-690` computes `ArmResults.success_rate` from HTTP status the probe itself observed, never the receiver counter), but it is *downstream* of the export gap: there is nothing durable to consume yet.

### Why the process-local counter cannot self-prove the gate today

`receiver_query_success_rate()` reads `RECEIVER_QUERY_OUTCOME.collect()` from the **calling process's** registry (`api/metrics.py:496`). Three structural defeaters:

1. **Task-replacement amnesia.** A deploy replaces ECS tasks; each new task starts the counter at 0. A 10-min `>=99%` claim spanning the deploy cannot be reconstructed from any single live process.
2. **Multi-task aggregation.** The service runs >1 task in steady state; no single process sees the fleet-wide denominator. (Single-uvicorn-worker per task per scar-tissue, but >1 task.)
3. **No durable sink.** Even within one task's lifetime, the value evaporates on restart; the gate needs a time-series a deploy decision can query *after* the soak window.

A durable, fleet-aggregated, deploy-survivable time series is required. That is exactly what a metric backend provides — and exactly what is missing in-repo.

## Mechanism (Part b) — Decision

**Decision: EMF-stdout additive emitter, in-repo, at the existing request seam — NOT an in-repo AMP remote-write/scrape config.**

### Option slate (genuine alternatives, per option-enumeration discipline)

| # | Option | Architecture | In-repo? | Verdict |
|---|--------|-------------|----------|---------|
| **A** | **EMF-stdout additive emitter** | At `query.py:596` request seam (or a thin post-seam), emit one Embedded Metric Format JSON line to stdout per request carrying `ReceiverQueryOutcome{arm,outcome}` AND the co-required `ServingStaleTotal`. CloudWatch's `awslogs`/EMF extraction turns log lines into CW metrics. | **YES** (emit side) | **SELECTED** |
| B | AMP remote-write from the receiver | Add a `prometheus-remote-write` exporter / ADOT sidecar pushing `RECEIVER_QUERY_OUTCOME` to an AMP workspace. | NO — requires sidecar/IaC + AMP workspace ARN + SigV4 auth, none of which exist in-repo (0 .tf, unknown workspace). | Rejected as in-repo work; this IS the cross-repo handoff. |
| C | In-repo `/metrics` self-scrape + gate reads `/metrics` | Gate scrapes `/metrics` text directly and parses `RECEIVER_QUERY_OUTCOME`. | Partially | Rejected: re-introduces task-replacement amnesia (a single `/metrics` read is one task's process-local view); does not survive the deploy; not fleet-aggregated. |
| D | `boto3.put_metric_data` from the ECS hot path | Reuse the freshness CLI emit pattern (`metrics/cloudwatch_emit.py:217`) on every request. | YES (lib present) | Rejected: **violates the hot-path-no-synchronous-I/O contract** (`api/metrics.py:7`); a per-request boto3 API call is synchronous network I/O on the request path. Acceptable for a CLI/Lambda batch (freshness), unacceptable for the receiver request hot path. |

### Why A over B/C/D

- **Hot-path safety (the decisive constraint).** EMF emission is a `print()` of a JSON line to stdout — non-blocking, no synchronous network I/O — satisfying `api/metrics.py:7`. Option D fails this; option B's in-process exporter is also acceptable on this axis but fails the in-repo-substrate axis.
- **Additive, zero-pipeline-mutation.** Mirrors the OBS-EXPORTS-001 precedent verbatim (`api/metrics.py:580-587`): no engine/helper/pipeline surface changes; we add an emitter at an existing seam.
- **Survives task replacement + fleet-aggregates.** Each task's stdout flows to the (cross-repo-configured) log sink; CloudWatch aggregates across tasks and across the deploy window into a durable time series — defeating the three defeaters above.
- **Reversible (two-way door).** An EMF emitter is additive code behind a feature seam; it can be removed without schema or contract change. Contrast option B (sidecar + IaC) which is closer to a one-way door once a monorepo scrape target is provisioned around it.

### Honoring the co-read PROHIBITION (load-bearing)

`api/metrics.py:484-488,522-537` prohibits exporting `success_rate` "bare" — it must be co-available with `serving_stale_total`. The export boundary MUST preserve this:

- The EMF emitter MUST NOT emit a pre-computed `success_rate`. It emits the **raw constituents** (`outcome=success|server_error` increments per arm) so the rate is derived downstream — *and* it emits `serving_stale_total` in the **same EMF document**, so any consumer that reads the rate has the stale-context in the identical record. There is no temporal or structural seam at which a flattered rate can be read in isolation.
- Concretely, the in-repo emitter is specified to source its values through `success_rate_with_stale_context()` semantics — i.e., the inseparable `(rate-constituents, serving_stale_total)` tuple — rather than `receiver_query_success_rate()` alone. This is the structural enforcement of observability-plan §2 at the export boundary, identical in spirit to the accessor at `api/metrics.py:522-537`.
- A reviewer check (and a unit test) asserts that any EMF document containing the outcome metric ALSO contains the stale-total metric. A document with the rate-constituents but no stale-total is a contract violation and fails CI.

### EMF document shape (in-repo contract)

```jsonc
// one line to stdout per request (or per small batch on the seam)
{
  "_aws": {
    "Timestamp": 1717804800000,
    "CloudWatchMetrics": [{
      "Namespace": "Autom8y/AsanaReceiverSLI",
      "Dimensions": [["arm"]],
      "Metrics": [
        {"Name": "ReceiverQueryOutcomeSuccess", "Unit": "Count"},
        {"Name": "ReceiverQueryOutcomeServerError", "Unit": "Count"},
        {"Name": "ServingStaleTotal", "Unit": "Count"}   // CO-READ ENFORCEMENT
      ]
    }]
  },
  "arm": "project",
  "ReceiverQueryOutcomeSuccess": 1,
  "ReceiverQueryOutcomeServerError": 0,
  "ServingStaleTotal": 0
}
```

(Namespace mirrors the existing `Autom8y/*` convention at `.know/obs.md:148`. `success_rate` is intentionally NOT a field — it is `Sum(success)/(Sum(success)+Sum(serverError))` derived in the dashboard/gate, with `ServingStaleTotal` always alongside.)

## System Design

### Architecture Diagram

```
 request hot path (ECS, per task)
   api/routes/query.py:596
        │ record_receiver_query_outcome(arm, success)   [EXISTING — process-local counter]
        │ record_serving_stale(...) where applicable     [EXISTING]
        ├─────────────────────────────────────────────┐
        │                                               │  NEW (additive, this TDD):
        ▼                                               ▼  emit_receiver_sli_emf(arm, success, stale_total)
  RECEIVER_QUERY_OUTCOME (in-proc)               print(EMF JSON line) ── stdout
  /metrics (scrape-pull, scraper UNKNOWN)              │
                                                       ▼
                                          ECS log driver  ◄── awslogs? UNCONFIRMED in-repo (obs.md:187)
                                                       │            [CROSS-REPO HANDOFF #1]
                                                       ▼
                                       CloudWatch Logs → EMF metric extraction
                                                       │
                                                       ▼
                                       durable CW metric: Autom8y/AsanaReceiverSLI
                                                       │
                                                       ▼
                                CW alarm / gate query (Sum success / Sum(success+err) >= 0.99)
                                                       │   + ServingStaleTotal co-read
                                          [CROSS-REPO HANDOFF #2: alarm/gate IaC, 0 .tf in-repo]
```

### Components

| Component | Responsibility | Technology | Locus |
|-----------|----------------|------------|-------|
| `emit_receiver_sli_emf()` (new) | Format + `print()` one EMF line carrying outcome constituents + `serving_stale_total` | stdlib `json` + `print` (no new dep) | **IN-REPO** `api/metrics.py` |
| Call site wiring | Invoke the emitter at the existing `record_receiver_query_outcome` seam (`query.py:596`) | Python | **IN-REPO** `api/routes/query.py` |
| Co-read guard test | Assert EMF doc with outcome metric also carries stale-total | pytest | **IN-REPO** `tests/` |
| ECS log driver = `awslogs` + EMF extraction | Route stdout → CW Logs and extract EMF → CW metric | ECS task def + CW IaC | **CROSS-REPO** autom8y monorepo |
| Alarm / deploy-gate query on CW metric | Evaluate `>=99%` over the soak window from the durable metric | CW alarm / gate script IaC | **CROSS-REPO** autom8y monorepo |

### Data Model

No persistent schema change. The EMF document (above) is the wire contract. The
metric namespace `Autom8y/AsanaReceiverSLI` with dimension `arm ∈ {project, section}`
and metrics `{ReceiverQueryOutcomeSuccess, ReceiverQueryOutcomeServerError, ServingStaleTotal}`
is the published contract that the cross-repo alarm/gate binds to.

### API Contracts

No HTTP API change. The "contract" surfaced by this work is the EMF metric
contract consumed by the monorepo alarm/gate (namespace + dimensions + metric
names above). Changing those names later is a breaking change to the cross-repo
consumer — see Risks.

### Sequence (gate self-proof, target state)

1. Deploy lands; ECS tasks emit per-request EMF lines to stdout.
2. CW Logs + EMF extraction produce `Autom8y/AsanaReceiverSLI` time series (fleet-aggregated, deploy-surviving).
3. Soak window (10 min) elapses.
4. Gate queries CW: `Sum(Success)/(Sum(Success)+Sum(ServerError)) >= 0.99` per arm, AND reads `ServingStaleTotal` co-context.
5. Gate PASS/FAIL from the **receiver counter**, not canary HTTP.

## Non-Functional Considerations

### Performance
EMF emission is one `print()` of a small JSON line per request. P99 added latency target: **< 1ms** per request (in-process string format + buffered stdout write; no network I/O). Measurement: micro-benchmark the emitter in isolation + before/after P99 on the query hot path under the existing canary load (`target_rpm=100`). Acceptance: no statistically significant P99 regression on `/v1/query/*/rows`. To bound stdout volume at high RPM, the emitter MAY batch-aggregate per N-second flush (design-permitted; default per-request for fidelity).

### Security
No new auth surface. EMF lines carry only `arm`, outcome counts, and stale-total — no PII, no credentials, no GIDs. Stdout already carries structured logs (`autom8y_log`); EMF lines join the same stream under the existing log sink trust boundary. No change to the S2S/dual-mode auth boundary.

### Reliability
Fire-and-forget: an emit failure (e.g., serialization error) MUST be swallowed and MUST NOT affect the request (mirrors the fire-and-forget contract at `api/metrics.py:7` and the "never raises on the fire-and-forget path" convention at `api/metrics.py:339-341`). Liveness of the *exported* metric depends on cross-repo handoff #1 (log driver = awslogs + EMF extraction); until that lands, the emitter is "designed, not exported live" (see G-RUNG below).

## Implementation Guidance

- Add `emit_receiver_sli_emf(entity_type: str, success: bool, serving_stale_total: float) -> None` to `api/metrics.py`, adjacent to `record_receiver_query_outcome` (`:305`). Wrap the body in a broad try/except that swallows + best-effort logs at debug.
- Source `serving_stale_total` via the same path `success_rate_with_stale_context` uses (`_serving_stale_total_value()`, `api/metrics.py:512-519`) so the co-read is structurally inseparable.
- Wire the call at `api/routes/query.py:596` immediately after `record_receiver_query_outcome(...)`, passing the already-computed `success_for_metric` and the current stale-total.
- Do NOT introduce `aws-embedded-metrics` as a dependency — it is absent from deps and hand-rolled EMF JSON (≈15 lines) avoids a new transitive. (If the team later wants the lib, that is a separate ADR.)
- Gate the emitter behind an env flag (e.g., `RECEIVER_SLI_EMF_ENABLED`, default off until cross-repo #1 is confirmed) so it can ship dark and be flipped on once the log driver/extraction is verified — preventing stdout-volume surprise before the sink exists.

## In-Repo NOW vs Cross-Repo Handoff (Part c) — Decision

**`in_repo_implementable = true`** and **`handoff_needed = true`** (both — this is a split, not an either/or).

### IN-REPO, implementable NOW
1. `emit_receiver_sli_emf()` additive emitter in `api/metrics.py` (co-read-enforced).
2. Call-site wiring at `api/routes/query.py:596`.
3. Env flag `RECEIVER_SLI_EMF_ENABLED` (ship-dark default).
4. Unit tests: emitter shape, fire-and-forget swallow, **co-read invariant** (outcome metric ⇒ stale-total present).

### CROSS-REPO HANDOFF (autom8y monorepo — cannot be done here; 0 .tf, unknown scraper)
1. **Backend binding:** confirm/set the asana ECS task log driver to `awslogs` (→ CloudWatch Logs) AND configure EMF metric extraction (OR, alternatively, provision an AMP scrape target + recording rule — monorepo's choice of backend). This is the load-bearing unknown at `.know/obs.md:187,415,437`.
2. **Alarm/gate IaC:** the CW alarm or deploy-gate query that evaluates `>=99%` from `Autom8y/AsanaReceiverSLI` over the soak window, with `ServingStaleTotal` co-read. Lives in monorepo TF per `api/metrics.py:587`, `.know/obs.md:385`.
3. **Gate cutover:** switch `receiver_bulk_fanout_deploy_gate.py`'s pass/fail source from canary-observed HTTP to the durable receiver metric (or run both during a confidence window). This is the "consumption gap" close — it is gated on handoffs #1+#2 existing.

### G-RUNG honesty
This TDD, when implemented in-repo, yields **"designed + emitting to stdout"** — NOT **"exported live to a durable backend"**. The transition from emit→durable is owned by cross-repo handoff #1. No in-repo artifact can attest the metric is live in AMP/CloudWatch; that attestation is cross-repo and post-handoff. Stated explicitly to avoid the "designed != exported live" conflation.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Log driver is NOT `awslogs` → EMF lines never become metrics (silent no-export) | M | H | Ship-dark env flag; handoff #1 must CONFIRM driver before flip; do not declare gate-self-proof until a live CW metric is observed (G-RUNG). |
| Co-read prohibition bypassed at export (bare flattered rate) | M | H | Emitter emits constituents + stale-total in ONE doc; CI invariant test; never emit pre-computed `success_rate`. |
| Per-request stdout volume at 100+ rpm × N tasks inflates log cost | M | M | Optional N-second batch-aggregate flush; flag-gated rollout; monitor log volume in soak. |
| Metric name/namespace drift breaks the cross-repo alarm consumer | L | H | Treat namespace+dimensions+names as a published contract (ADR); change = breaking-change ADR + monorepo coordination. |
| Hot-path latency regression | L | M | < 1ms target; before/after P99 under canary load; broad try/except so emit never blocks/raises. |
| Premise drift: assuming `/metrics` is already scraped into AMP | M | H | Verified FALSE in-repo (0 scrape config, 0 AMP ref); design does not depend on that premise. |

## ADRs

Recommend extracting two discrete decisions into standalone ADRs:
- **ADR-EMF-RECEIVER-SLI-EXPORT:** "EMF-stdout additive emitter over AMP remote-write / boto3-hot-path / self-scrape" (the Part-b mechanism decision + option slate).
- **ADR-RECEIVER-SLI-METRIC-CONTRACT:** the `Autom8y/AsanaReceiverSLI` namespace/dimensions/metric-names as a cross-repo published contract (one-way-door flag: renaming is breaking).

## Open Items
1. Cross-repo confirmation of the ECS log driver (awslogs?) — blocks "exported live." Owner: autom8y monorepo / SRE.
2. Backend choice: CW Logs+EMF extraction vs AMP scrape target+recording rule. Owner: monorepo.
3. Per-request vs batched EMF flush default — resolve against soak-window log-volume measurement.
4. Whether the gate runs dual-source (canary HTTP AND receiver metric) for one confidence window before cutover. Owner: IC / SRE.

## SVR Receipts (platform-behavior claims)

- **R-1** `verification_method: bash-probe` — `source: grep -rniE "amp|remote[_-]write|aps-workspace|prometheusremotewrite|managed.?prometheus" --include=*.py --include=*.md --include=*.yaml src/ .know/` → only false positives (`timestamp`,`amplification`); `exit_code: 0`. **claim:** no AMP/remote-write/managed-prometheus pipeline is referenced anywhere in this repo's source or knowledge, so `/metrics → AMP` is unverifiable in-repo.
- **R-2** `verification_method: bash-probe` — `source: find ... -name 'prometheus*.y*ml' -o -name '*scrape*' -o -name 'otel-collector*' (excl .venv)` → `result_count: 0`. **claim:** there is zero in-repo scrape configuration; whatever scrapes `/metrics` (if anything) is configured cross-repo.
- **R-3** `verification_method: bash-probe` — `source: find /Users/tomtenuta/Code/a8/repos/autom8y-asana -name '*.tf'` → `result_count: 0`. **claim:** the asana satellite holds no Terraform; alarm + scrape IaC necessarily live in the autom8y monorepo, making the alarm/gate-IaC step a mandatory cross-repo handoff.
- **R-4** `verification_method: file-read` — `source: scripts/canary/receiver_bulk_fanout_deploy_gate.py:638-690` marker `_evaluate_gate(...) project.success_rate < success_threshold`. **claim:** the deploy gate's pass/fail is computed from `ArmResults.success_rate` (HTTP status the probe observed at `:582-598`), not from `RECEIVER_QUERY_OUTCOME` — confirming the consumption gap.
- **R-5** `verification_method: file-read` — `source: src/autom8_asana/api/metrics.py:522-537` marker `Return (success_rate, serving_stale_total) as ONE inseparable reading`. **claim:** the co-read prohibition is already enforced in-process by `success_rate_with_stale_context`; the export boundary must replicate that inseparability, which the EMF single-document design does.
