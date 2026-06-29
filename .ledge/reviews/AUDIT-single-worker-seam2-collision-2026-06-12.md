---
type: review
subtype: capacity-concurrency-audit
status: accepted
title: "AUDIT — single-worker × SEAM-2 collision: in-process invariant inventory, load model, capacity envelope, option slate, iris probe spec"
date: 2026-06-12
evidence_grade: MODERATE
authority: OPERATOR-INTERVIEW ruling R2-Q3 (.ledge/decisions/OPERATOR-INTERVIEW-RULINGS-freeze-week-and-unlock-2026-06-12.md) — "Audit in freeze, design post-clear — with iris as the live instrument"
code_anchor: all src reads at origin/main fa265ce1 (local checkout is a stale branch; verified via `git show`/`git grep fa265ce1`)
constraints: READ-ONLY vs production; soak clock RUNNING (anchor 2026-06-12T09:02:05Z on :516 → clear 06-19T09:02:05Z); probe fires SEPARATELY, design-only here
evidence_ceiling_note: self-authored audit; MODERATE ceiling per self-ref-evidence-grade-rule. Live-AMP load-shape reads NOT executed from this station (no AWS session here); marked UV-P where load numbers are projected.
---

# AUDIT — single-worker × SEAM-2 collision (freeze-week, 2026-06-12)

## 0. The single-worker fact (SVR)

The ECS receiver runs **one uvicorn worker**: `scripts/entrypoint.sh:52-56` execs
`python -m uvicorn autom8_asana.api.main:create_app --host … --port … --factory`
with **no `--workers` flag** → uvicorn default = 1 worker, 1 process, 1 event loop.
(The prompt's `src/autom8_asana/api/entrypoint.py:52` path does not exist at
fa265ce1; the real anchor is `scripts/entrypoint.sh`, baked as the Dockerfile
ENTRYPOINT, `Dockerfile:155`.) Lambda mode is per-invoke single-process by
construction. Every invariant below therefore currently holds *globally* because
process == fleet. That equality is what SEAM-2 pressure + any future
multi-worker move breaks.

## 1. In-process invariant inventory (serve + write paths)

Classification key: **PLD** = process-local-by-design (a per-process budget;
N workers multiplies the aggregate — semantics change but no dedup is lost) ·
**APL** = accidentally-process-local (plays a *global* singleflight/dedup/state
role that silently breaks under N>1 workers) · **DIST** = already-distributed.

| # | Primitive | Anchor (fa265ce1) | Role | Class |
|---|---|---|---|---|
| 1 | FROZEN-4 lever: `dataframe_max_concurrent_builds=4` | `settings.py:287-312`; guard `tests/unit/dataframes/test_concurrency_invariants_guard.py:79-92` | per-process build cap (mem math: 4×~2GB worst case vs 8GB task) | **PLD** — N workers ⇒ 4N builds ⇒ memory math invalidated |
| 2 | FROZEN-4 lever: `cpu_thread_concurrency=4` | `settings.py:287`; guard `test_concurrency_invariants_guard.py:60-77` | per-process `to_thread` CPU budget | **PLD** — multiplies |
| 3 | BuildCoordinator `_build_semaphore` (cap role) | `cache/dataframe/build_coordinator.py:131,148,153`; constructed in-lifespan `api/lifespan.py:229-247` (asyncio.Semaphore needs running loop) | concurrency cap | **PLD** |
| 4 | BuildCoordinator `_lock` + per-key registry (singleflight role) | `build_coordinator.py:147` | cross-key build dedup — assumed GLOBAL by ADR-ARCH-001 | **APL** — dual-role primitive; N workers ⇒ duplicate concurrent builds of the same (gid, entity) |
| 5 | Dataframe coalescer (per-key asyncio.Event/Lock) | `cache/dataframe/coalescer.py:84,130,176` | request coalescing / thundering-herd suppression | **APL** |
| 6 | Policies coalescer | `cache/policies/coalescer.py:68` | same, policy layer | **APL** |
| 7 | `universal_strategy._background_builds` module set | `services/universal_strategy.py:47,1093-1097` | background-build dedup (delegation to coordinator documented :938-969 but module set still live) | **APL** |
| 8 | Circuit breaker per-project `_circuits` dict | `cache/dataframe/circuit_breaker.py:84,111` | failure isolation — state diverges per worker (one worker open, another hammering) | **APL** |
| 9 | Client pool lock + rate-limiter/AIMD/breaker accumulation | `api/client_pool.py:103,151`; `api/dependencies.py:259` | **Asana-API rate budget** — N workers ⇒ N× the upstream 429 budget | **APL** |
| 10 | Modification cache + lock (invalidation path) | `cache/integration/batch.py:84,237`; MutationInvalidator wired in lifespan | REST-mutation cache invalidation — only invalidates *this* process's tiers | **APL** |
| 11 | Memory tier RLock + in-proc store | `cache/dataframe/tiers/memory.py:86`; `cache/backends/memory.py:42`; sync read note `cache/integration/dataframe_cache.py:389` | per-process hot tier | **PLD** — N× memory duplication + per-worker cold-start, cost not correctness |
| 12 | Durable task cache cold-read semaphore + reader locks | `cache/durable_task_cache.py:144,294,325` | per-process S3/IO cap | **PLD** |
| 13 | Unified provider hierarchy semaphore | `cache/providers/unified.py:77-84` | per-process fan-out cap | **PLD** |
| 14 | Preload PROJECT_CONCURRENCY semaphore | `api/preload/progressive.py:425` | startup preload cap | **PLD** |
| 15 | Lifespan drain `_drain_background_builds` | `api/lifespan.py:34,390-398` | per-process graceful shutdown (ADR-002) — correct per-worker | **PLD** |
| 16 | S3 durable tier single-writer: warmer reserved-concurrency=1 + γ-0 monolith write pin + storage-namespace IAM (β-wave) | infra (autom8y TF); ADR-storage-namespace-contract-2026-06-10 | cross-process write serialization at the *infrastructure* level | **DIST** |

**Count: 8 PLD · 7 APL · 1 DIST.** The 7 APL rows are the worker-model ADR's
blocking set: any multi-worker option must distribute or shard exactly these.
Row 4 is the sharpest: the FROZEN-4 *cap* is honest under N workers (just
multiply the floor), but the *singleflight* role silently vanishes.
EventLoopLagMonitor (`api/event_loop_monitor.py`, 5s sampler →
`autom8y_asana_event_loop_lag_seconds`, `api/metrics.py:523-528`) is per-loop
observability, not an invariant — but under N>1 workers the histogram mixes
loops unlabeled.

## 2. Load model (UV-P where projected — the probe converts these to receipts)

Current organic (receiver-inbound, steady):

| Source | Cadence | Shape |
|---|---|---|
| Bulk warmer (project+section × warm-set GIDs) | `cron(0,30 * * * ? *)` — every 30 min (autom8y `terraform/services/asana/variables.tf:73-88`) | AC-6 ~100-class burst per firing, ~34 warm-set GIDs both arms |
| Section warmer lane | dedicated schedule, ~10-min freshness contract (ADR-section-10min, `variables.tf:91+`) | smaller, steadier section-arm reads |
| Frame-freshness warmer | `cron(0 */4 * * ? *)` (`variables.tf:67-71`) | 4-hourly |
| Canary/deploy-gate + sentinel | deploy-time + daily attestation | 100rpm × 10min both-arms, episodic (06-11 iris precedent: ruled non-resetting) |

Projected SEAM-2 increments (consumer call sites in the monolith, /Users/tomtenuta/Code/autom8):

| Phase | Consumer | Cadence evidence | Projected increment |
|---|---|---|---|
| +C3 first | OfferHolders registry reads (`apis/asana_api/objects/project/models/offer_holders/main.py`) | interactive/agent-driven, no cron | LOW: <10 rpm sustained, single-arm reads [UV-P] |
| +C1 | ad_reporting (`entry_points/jobs/ecs/ad_reporting/` via `ecs_cluster_manager`) + reconcile lanes (`reconcile-spend` `cron(30 12 ? * MON-FRI *)`, `reconcile-ads` `cron(0 13 ? * MON-FRI *)`) | daily weekday bursts | BURST: 50–150-rpm-class for minutes when a job fans out per-project reads [UV-P] |
| +C2 | payments/mrr (`entry_points/jobs/pull_payments/`, `terraform/services/pull-payments/main.tf:131` `cron(15 0,12,23 * * ? *)`) | 3×/day bursts | BURST: 50–100-rpm-class per firing [UV-P] |

**Headline: SEAM-2 is burst-multiplexing, not sustained-rpm growth. Projected
worst case = a C1 or C2 job burst landing on a :00/:30 warm burst ≈ 200–250
rpm-class combined for single-digit minutes — i.e. 2–2.5× the only rpm point we
have ever measured (100).** The probe's ramp ceiling (250) is chosen to cover
exactly this overlap regime.

## 3. Capacity envelope — KNOWN vs NOT KNOWN

KNOWN (receipts):
- GATE-2/§D both-arms PASS: 10min @ 100rpm/arm, ≥99% mirror-SLI, on the capacity
  floor cpu 2048 / mem 8192 (IC-GATE-7 GO 2026-06-04; floor held through every
  :512→:516 revision per the RESET-RECOMMENDATION receipts).
- The starvation receipt: 06-02 bulk validation 86.8% (<99%) at 0.25 vCPU
  pre-floor — root-caused to single-worker CPU starvation, **mitigated by the
  floor, not removed** (the mechanism — sync Polars on/near the loop — is
  bounded by FROZEN-4, not eliminated).
- Leading indicator exists and is scrapeable:
  `autom8y_asana_event_loop_lag_seconds` (buckets to 5.0s, `api/metrics.py:527`);
  plus `cpu_starvation_precondition()` formalizes lag×semaphore-wait
  (`api/metrics.py:678-681`).
- iris 06-11 smoke: 100rpm both-arms tolerated, ruled non-soak-resetting
  (canary-class precedent this spec inherits).

NOT KNOWN (the probe's job):
- The actual rpm ceiling on the current floor (we have ONE load point: 100).
- The latency curve (p50/p99 vs rpm) and the event-loop-lag knee.
- Behavior when read-rpm collides with build-on-miss (coalescer + FROZEN-4
  semaphore saturation → 503/Retry-After onset point).
- Live AMP load shape (not read from this station — first probe stage doubles
  as the baseline read).

## 4. Option slate (enumerated, NOT picked — the post-clear ADR rules)

| Option | FROZEN-4 / inventory implication | Blast radius | What the probe must measure to discriminate |
|---|---|---|---|
| **A. Multi-worker + distributed singleflight (Redis/Dynamo-class lease)** | rows 4–10 (all 7 APL) must move to a shared store; FROZEN-4 levers become per-worker (floor ÷ N math redone); row 16 already compatible | LARGE: new infra dependency on the hot path + 7 primitives rewritten | whether the ceiling is loop-bound (helps) vs build-bound (doesn't) |
| **B. Multi-worker + sticky routing by cache key (ALB/target hashing or path-shard)** | APL rows survive *per shard* (each key owned by one worker); breaker/rate budget (rows 8–9) still fragment; routing layer becomes correctness-critical | MEDIUM-LARGE: infra routing + key→shard contract; rebalance on deploy | per-key hot-spot concentration: does load skew to few GIDs (sticky works) or spread (it degrades to A)? |
| **C. Deliberate single-worker + vertical headroom + codified envelope + backpressure (429/503+Retry-After at the measured ceiling)** | ZERO inventory churn — every APL row stays correct by construction; FROZEN-4 untouched; honest-400/503 path already carries Retry-After | SMALL: settings + alarm thresholds + an envelope doc the consumers must respect | the measured ceiling itself: if ≥250rpm-class with p99 flat, C is sufficient for all of SEAM-2 |
| **D. Sidecar read-replica split (read-only serve worker(s) + single writer process)** | write-path APL rows (4,7,10) stay single-writer-true; read-path rows (5,8,9,11) replicate per reader — breaker/rate fragmentation returns in read form; memory tier ×N | MEDIUM: process supervisor + intra-task routing inside the container, no new infra | read/write mix: if serve latency degrades only during builds, splitting helps; if reads alone saturate, D ≈ B |

## 5. THE IRIS PROBE SPEC (paste-ready dispatch; fires SEPARATELY, post-review)

**Instrument**: iris (operator-chosen, R2-Q3). **Target**: live `:516` receiver,
`https://asana.api.autom8y.io`. **Class**: canary-class synthetic (06-11
precedent: non-soak-resetting). **Posture**: READ-ONLY business surface;
project-arm content-bound reads + section-arm honest-400 cadence; no writes, no
cache mutation beyond organic build-on-miss.

**Pre-flight gate (G3, chaos-design): NO probe unless**
1. 30-day availability error budget remaining ≥ 20%:
   `1 - ((1 - slo:asana_receiver:availability_sli:30d… ratio) / 0.005) ≥ 0.20`
   — equivalently confirm burn-rate recording rules ≪ 1 over 30d; abort if budget < 20%.
2. `ALERTS{alertname=~"AsanaReceiverAvailability(FastBurn|SlowBurn)", alertstate!="inactive"}` returns empty.
3. Not within ±10 min of a `:00`/`:30` bulk-warm firing for stage starts ≥ 200rpm (don't stack the organic burst on the top stages; the overlap regime is measured at 150–200 instead, deliberately).
4. Soak-sentinel day-record for today is GREEN.

**Stages** (project arm; 3 min each; section arm runs the canary's built-in fixed cadence each stage):

| Stage | --target-rpm | Purpose |
|---|---|---|
| S0 | 50 | baseline + AMP load-shape read (fills §3 gap) |
| S1 | 100 | reproduce the GATE-2 known-good point |
| S2 | 150 | C3+C1 overlap regime |
| S3 | 200 | warm-burst + job-burst collision proxy |
| S4 | 250 | projected SEAM-2 worst case + margin |

**Per-stage invocation** (the deploy-gate canary IS the load instrument; flags verified at fa265ce1 `scripts/canary/receiver_bulk_fanout_deploy_gate.py:849-895`):

```bash
uv run python scripts/canary/receiver_bulk_fanout_deploy_gate.py \
  --base-url https://asana.api.autom8y.io \
  --project-gid "$WARM_SET_PROBE_GID" \
  --duration-minutes 3 \
  --target-rpm {50|100|150|200|250} \
  --success-threshold 0.99 \
  --content-limit 5
# exit 0 = stage PASS (mirror-SLI ≥0.99 both arms, zero 429-SA, content binding)
```

Traffic labeling: the canary's synthetic traffic is the established
canary-class shape (same script, same arms as the 06-11 non-resetting
precedent); iris MUST log stage boundaries (UTC) into the dispatch record so
the sentinel can attribute any metric movement to the probe.

**Inter-stage abort loop** (run between every stage; awscurl SigV4 against the prod AMP workspace query API):

```bash
AMP="https://aps-workspaces.{region}.amazonaws.com/workspaces/{ws_id}/api/v1/query"
q() { awscurl --service aps --region {region} "$AMP" -d "query=$1" | jq -r '.data.result'; }

# A1 — ANY 5xx during the stage window: abort if > 0
q 'sum(increase(autom8y_http_requests_total{service="asana",status=~"5.."}[4m]))'
# A2 — p99 sustained: abort if p99 > 2s across two consecutive 1m evals (60s sustained)
q 'histogram_quantile(0.99, sum by (le) (rate(autom8y_http_request_duration_seconds_bucket{service="asana"}[1m])))'
# A3 — burn alarms must be inactive: abort if non-empty
q 'ALERTS{alertname=~"AsanaReceiverAvailability(FastBurn|SlowBurn)",alertstate!="inactive"}'
# A4 — event-loop-lag knee (leading indicator): abort if p99 lag > 0.25s
q 'histogram_quantile(0.99, rate(autom8y_asana_event_loop_lag_seconds_bucket[4m]))'
# A5 — re-check error budget ≥ 20% (G3 continuous)
```

**HARD abort = stop ramp, record ceiling = last fully-PASS stage.** Abort also
on canary exit≠0 mid-stage. No retry of a failed stage. One run, daytime UTC,
operator-pinged at start/finish.

**Deliverable**: per-stage table {rpm, success-rate/arm, p50/p99 HTTP, p99
loop-lag, 5xx count, alarm states} + the measured ceiling + the
latency-vs-rpm curve → feeds §4's discriminator column → the post-clear
worker-model ADR.

**Soak-law compatibility**: read-only, canary-class, alarms-must-stay-inactive
by abort-loop construction, error-budget-gated, stage-bounded (max 15 min
load + gaps) — squarely inside the iris 06-11 non-resetting precedent. The
probe does NOT touch the deploy chain, the image, or the floor.
