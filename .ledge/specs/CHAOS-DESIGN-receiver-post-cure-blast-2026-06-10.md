---
type: spec
status: draft
---

# CHAOS-DESIGN — SRE-N5 Controlled Blast for the Post-:503 Receiver

> **Station**: R4 DESIGN-ONLY. NO execution. Every injection below is an
> **operator lever** — a command an operator runs deliberately, never the
> chaos-engineer. This artifact is the only mutation made authoring it.
> **Read-only against prod.** Code/TF cited by file:line to ground hypotheses.

- **Date authored**: 2026-06-10
- **Target**: `autom8y-asana` receiver (ECS `:503`, image `b114530`, 1/1, single
  uvicorn worker, SlowAPI `100/min` global + SA `600/min` namespaced) + warmer
  Lambdas (main / bulk / section, same image) + durable S3 task-cache reads.
- **Engineer**: chaos-engineer (SRE rite, R4)
- **Grandeur anchor**: prove the certified plane DEGRADES LOUDLY, never silently
  — guards / serve-stale / population-floor HOLD under fault — by *designed*
  experiments with hypotheses, blast radius, abort criteria, rollback; never by
  assuming green.

---

## 0. System-Under-Test — Grounded Inventory (file:line receipts)

| Component | Fact | Receipt |
|---|---|---|
| LKG ceiling | `LKG_MAX_STALENESS_MULTIPLIER = 10.0` (NOT 0.0 — honest backpressure restored; 0.0 flatters by serving unbounded-stale 2xx) | `src/autom8_asana/config.py:117` |
| Serve-stale within bound | per-entity absolute max-age ceiling: `project=86400s`, `section=576s` | `src/autom8_asana/config.py:162-165` |
| Cold build-on-miss → 503 | body-parameterized entities build on miss; typed 503 + `retry_after`; "NEVER a 500, NEVER a silent empty-200" | `src/autom8_asana/api/routes/query.py:551-563` |
| Cache-not-warm → honest 503 | `CACHE_NOT_WARMED` → 503 + `retry_after_seconds:30`, classified `cadence_503` | `src/autom8_asana/api/routes/query.py:564-575` |
| Honest-empty 2xx is NOT counted healthy | 2xx split into `honest_refusal` vs `data_2xx` (liveness-masquerade defeat) | `src/autom8_asana/api/routes/query.py:576-584` |
| Receiver SLI EMF self-measure | `emit_receiver_sli_emf(...)` ship-dark behind `RECEIVER_SLI_EMF_ENABLED` (default off); namespace `Autom8y/AsanaReceiverSLI`; co-emits `ServingStaleTotal` in same EMF doc | `src/autom8_asana/api/metrics.py:354-355,373-437`; call site `query.py:601-608` |
| EMF outcome metrics | `ReceiverQueryOutcomeSuccess` / `ReceiverQueryOutcomeServerError` / `ServingStaleTotal`, dimension `arm` | `src/autom8_asana/api/metrics.py:417-431` |
| Fallback cause vocabulary | `cadence_503` / `capacity_502` / `honest_refusal` / `data_2xx` | `src/autom8_asana/api/metrics.py:154-157` |
| Rate-limit (global) | `{rate_limit_rpm}/minute` default 100/min via SlowAPI; 429 + Retry-After | `src/autom8_asana/api/rate_limit.py:8,202-214,225-227` |
| Rate-limit (SA namespace) | SA `asana-dataframe-resolver` exempted to `600/minute` via `SA_NAMESPACE_LIMIT`; bucket-routed on `service_account_id` JWT claim | `src/autom8_asana/api/rate_limit.py:65-80,161-189` |
| Warmer self-invoke continuation | timeout-exit + key-budget-exit both checkpoint+self-invoke; OOM-kill skips timeout branch (key-budget is the OOM guard) | `src/autom8_asana/lambda_handlers/cache_warmer.py:460-518` |
| Non-durable write ≠ SUCCESS | S3 write reporting non-durable must NOT present as warm SUCCESS | `src/autom8_asana/cache/dataframe/warmer.py:414-438`; `cache/integration/dataframe_cache.py:633-699` |
| Story-warm bounded concurrency | `asyncio.Semaphore(3)` over `list_for_task_cached_async` | `src/autom8_asana/lambda_handlers/story_warmer.py:64,91,126` |
| ECS task sizing | `cpu=1024 / memory=2048` (raised from 256/1024); collector reserves cpu=256 | `autom8y/terraform/services/asana/main.tf:158-159,251` |
| Warmer Lambda sizing | `memory_size=2048`, `timeout=900` | `autom8y/terraform/services/asana/main.tf:311-312` |
| Main warmer cron | `cron(0 */4 * * ? *)` (every 4h, offer-domain, `prematerialize_bulk_set` defaults False) | `autom8y/terraform/services/asana/variables.tf:67-70`; flag default `cache_warmer.py:1235` |
| Bulk warmer cron | `cron(0,30 * * * ? *)` (30-min, `prematerialize_bulk_set=true`, 68-key) | `autom8y/terraform/services/asana/variables.tf:73-88`; `main.tf:408-413` |
| Section warmer cron | `cron(0/10 * * * ? *)` (10-min, `prematerialize_section_set=true`, 34-key, disjoint checkpoint prefix) | `autom8y/terraform/services/asana/variables.tf:91-106`; `main.tf:550-557` |
| Warmer S3 read grant | `cache_warmer_s3` inline policy: `s3:GetObject` on `autom8-s3/asana-cache/project-frames/*` | `autom8y/terraform/services/asana/main.tf:939-956` |
| DMS heartbeat alarms (LIVE) | `cache_warmer_bulk_cadence_DMS`, `cache_warmer_DMS_24h`, `cache_freshness_warning/sustained_p1` | `autom8y/terraform/services/asana/main.tf:644-645,704-705,736-737,817-818` |

### Cross-repo context inputs (NOT receiver-repo facts — UV-P labeled)

The following are *design-context inputs* from the dispatch + auto-memory
(`fpc-phase2-deploy-node-fired`), living in the autom8 monorepo data layer / TF,
not the `autom8y-asana` tree. They are **operator-owned** levers. Per SVR §6 they
carry UV-P labels rather than fabricated receiver-repo receipts:

- `[UV-P: durable S3 task-cache read uses bounded concurrency cap=24 via ASANA_CURE_COLD_CONCURRENCY (raw boto3) on the FPC Phase-2 cure path | METHOD: deferred-to-cross-repo-probe | REASON: env + reader live in autom8/autom8y-data data layer, not the autom8y-asana tree grepped this hour; operator must confirm exact env name + reader module at game-day prep]`
- `[UV-P: IAM role S3DurableTaskCacheRead is attached to 3 warmer roles granting the durable cold-read | METHOD: deferred-to-cross-repo-probe | REASON: the receiver-repo grant grepped here is cache_warmer_s3 (main.tf:939-956); the S3DurableTaskCacheRead role named in the dispatch is a separate cross-repo grant the operator must locate in autom8 TF before EXP-1]`
- `[UV-P: merged-not-applied alarms floor-breach / active-offer-collapse(<40) / resolver-loop + burn-rate SLO rules exist on a branch | METHOD: deferred-to-cross-repo-probe | REASON: not present in autom8/terraform/services/asana/main.tf canonical HEAD this hour (only DMS + freshness alarms are LIVE); these are the LOUD nets several experiments depend on, so their APPLY status is an operator pre-flight gate — see §3 Global Abort Gate G0]`

**Consequence for design**: any experiment whose LOUD signal is one of the
merged-not-applied alarms is **DOWNGRADED to log-only verification** until the
operator confirms the alarm is APPLIED. This is recorded per-experiment.

---

## 1. Steady-State Definition (baseline BEFORE any injection)

| Metric | Normal Range | Source |
|---|---|---|
| Receiver query success rate (both arms) | ≥ 99% sustained 10-min | `receiver_query_success_rate` gauge ← `record_receiver_query_outcome` (`metrics.py`), deploy-gate (`query.py:523-525`) |
| `ReceiverQueryOutcomeServerError` (arm=project, arm=section) | ~0 | EMF `Autom8y/AsanaReceiverSLI` (`metrics.py:417-431`) — **requires `RECEIVER_SLI_EMF_ENABLED=on`** |
| `serving_stale_total` | low + stable (occasional LKG serves OK) | `autom8y_asana_serving_stale_total` (`metrics.py:551`) |
| `data_2xx` : `honest_refusal` ratio | data_2xx dominant | `record_query_fallback_cause` (`metrics.py:449`) |
| Coherent / gun / unit.mrr | coherent=561 / gun=10 / unit.mrr=723/3021 (stable ×3 warms) | FPC Phase-2 eunomia-STRONG (auto-memory `fpc-phase2-deploy-node-fired`) |
| Active-offer count | 62 / $79,485 | SEAM-1 live (auto-memory `seam1-entity-blind-reader-gap`) |
| Warmer DMS heartbeat | fresh < 24h | `cache_warmer_DMS_24h` (`main.tf:817`) |

**Steady-state pre-flight (operator, read-only)**: confirm all of the above are
green for 10 min AND `RECEIVER_SLI_EMF_ENABLED=on` (otherwise the receiver cannot
self-prove and several LOUD signals are blind — see G0).

---

## 2. Experiments — Ordered by Value / Risk

Ranked highest **value-per-unit-risk** first. EXP-1 and EXP-2 are the
recommended first pair (rationale in §5).

### EXP-1 — Durable-read IAM revocation drill (game-day, TF-revert)
**Fault class**: Dependency (S3 durable task-cache read). **Blast**: staging
first; prod requires IC sign-off (§4 escalation).

- **Hypothesis (falsifiable)** — *Given* the FPC Phase-2 cure serving
  coherent=561 with the durable cold-read path live, *When* the `s3:GetObject`
  grant on the durable task-cache prefix is revoked for ONE warmer lane (TF
  edit + apply, or scoped deny), *Then* the cure DEGRADES TO HONEST-NULL —
  `cold_read_gid_failed`-class logs fire, the population-floor WARN observer
  surfaces a drop, coherent count falls toward the null mechanism, and **NO
  fabricated/stale values are served** (no silent green). The receiver continues
  to serve `honest_refusal` 2xx / honest 503, never a flattered `data_2xx`.
  - **REFUTED if**: coherent count holds at 561 with the grant revoked (⇒ the
    "cure" is reading a different/cached source, OR a fabrication path exists), OR
    a value appears that the live read can no longer source (⇒ silent fabrication
    — the worst outcome, a P1 finding).
- **Injection (operator lever — NOT executed here)**:
  ```
  # GAME-DAY, staging. In the autom8 monorepo TF (operator locates the
  # S3DurableTaskCacheRead grant per UV-P above), comment the GetObject
  # statement for ONE lane, then:
  terraform plan   # operator reviews: exactly one lane, one statement
  terraform apply  # operator executes
  # REVERT is the rollback (below).
  ```
- **Blast radius / duration**: ONE warmer lane (section preferred — smallest
  denominator, 34 keys); 1 warm cycle (≤ 10 min) + 10-min observation = ~20 min.
- **Abort criteria**: any `data_2xx` value served that the revoked read cannot
  source (silent fabrication) → ABORT + REVERT immediately, escalate P1.
  Receiver server-error rate on the OTHER (un-revoked) arm rises > 1% absolute →
  ABORT (blast bleed). Duration > 30 min → ABORT.
- **Expected LOUD signal (tie to R3 bundle)**: `cold_read_gid_failed`-class
  WARN logs; population-floor breach observer (WARN). **floor-breach alarm**
  fires ONLY IF the merged-not-applied alarm is APPLIED — otherwise
  **DOWNGRADE to log-only**: assert the `cold_read_gid_failed` log lines + a
  coherent-count drop visible in the FPC eunomia read. `ReceiverQueryOutcomeServerError`
  must NOT spike (honest-null is a 2xx honest_refusal, not a 5xx).
- **Rollback**: `terraform apply` of the reverted grant; re-run the lane warmer
  once; confirm coherent returns to 561.
- **Residual risk if skipped**: a silent fabrication path on durable-read failure
  would ship flattered numbers to consumers with zero alarm — the exact
  "degrade silently" failure the grandeur anchor exists to refute. HIGH residual.

### EXP-2 — Heartbeat kill (probe-class dead-man)
**Fault class**: Process / observability. **Blast**: `:503` task-def env flip,
single service.

- **Hypothesis (falsifiable)** — *Given* the heartbeat probe-class SLI emits to
  AMP and business-class SLIs are independent, *When* the heartbeat is disabled
  (`ASANA_SLI_HEARTBEAT_DISABLED=on` on the `:503` task def), *Then* the
  probe-class dead-man alarm fires within its window (~10 min) AND the
  business-class SLO (`receiver_query_success_rate`) is UNAFFECTED — proving the
  two SLI classes are decoupled and the dead-man is real, not decorative.
  - **REFUTED if**: the dead-man does NOT fire within 2× its window (⇒ the
    probe is decorative — silent blindness), OR the business SLO degrades when
    only the heartbeat is killed (⇒ false coupling).
- **Injection (operator lever — NOT executed here)**:
  ```
  # Operator updates the :503 ECS task def env, forces new deployment:
  ASANA_SLI_HEARTBEAT_DISABLED=on
  # (touches a prod env var → REQUIRES operator decision beyond execution; see §4)
  ```
- **Blast radius / duration**: single receiver service, heartbeat only;
  one alarm window + margin = ~25 min.
- **Abort criteria**: business SLO success rate drops > 0.5% absolute (means the
  flip touched more than the heartbeat) → ABORT + revert. Dead-man fires AND
  pages the wrong sev → ABORT (alarm-routing defect, separate finding).
- **Expected LOUD signal**: probe-class heartbeat dead-man (AMP / Grafana) within
  ~10 min. `cache_warmer_DMS_24h` is a DIFFERENT dead-man (warmer-side,
  `main.tf:817`) — this experiment targets the RECEIVER probe-class heartbeat;
  verify the correct one fires. `[UV-P: receiver probe-class heartbeat SLI + its ASANA_SLI_HEARTBEAT_DISABLED env toggle | METHOD: deferred-to-operator-prep | REASON: the heartbeat code grepped this hour is the preload progressive heartbeat (progressive.py:182-191); the probe-class SLI heartbeat + its disable env named in the dispatch must be confirmed by operator at prep — if the toggle does not exist, this experiment becomes a code-gap finding, not an injection]`
- **Rollback**: remove the env var, force new deployment; confirm heartbeat
  resumes < 1 window.
- **Residual risk if skipped**: a decorative probe-class heartbeat means a true
  receiver stall would go unpaged — the dead-man is the last line when the EMF
  SLI itself is starved. MODERATE-HIGH residual.

### EXP-3 — Warm-path S3 latency / concurrency exhaustion (envelope proof)
**Fault class**: Resource (concurrency) + dependency latency. **Blast**: ONE
warmer lane env, staging.

- **Hypothesis (falsifiable)** — *Given* the durable cold-read uses a bounded
  concurrency cap (=24 per UV-P) and the warmer link is wall-clock-bounded by
  per-link key-budget chunking well under the 900s Lambda timeout
  (`cache_warmer.py:108-122,497-518`), *When* `ASANA_CURE_COLD_CONCURRENCY` is
  reduced to 1 (serializing the cold reads) for one lane, *Then* the warm cycle
  still completes WITHIN the 900s budget via self-invoke continuation (the
  key-budget-exit checkpoints + continues, `cache_warmer.py:514-518`) and
  coverage reaches 1.0 across continuations — proving the latency envelope qa
  estimated holds even at concurrency=1.
  - **REFUTED if**: the link OOM-kills or hard-times-out without checkpointing
    (⇒ the continuation does not cover the serialized-read tail — the envelope is
    thinner than estimated), OR coverage stalls < 1.0 with no further self-invoke
    (⇒ stranded chain).
- **Injection (operator lever — NOT executed here)**:
  ```
  # Operator sets on ONE warmer lane (section) env, staging:
  ASANA_CURE_COLD_CONCURRENCY=1
  # (touches an env var → operator decision; staging-only without IC sign-off)
  ```
- **Blast radius / duration**: one warmer lane (section, 34 keys), staging;
  2-3 warm cycles to observe continuation = ~30 min.
- **Abort criteria**: warm cycle exceeds 900s without a checkpoint save
  (`CheckpointSaved` metric absent) → ABORT (stranded chain risk). Coverage
  regresses below the prior cycle → ABORT.
- **Expected LOUD signal**: `WarmerKeyBudgetExhausted` + `CheckpointSaved` +
  `CheckpointResumed` metrics (`cache_warmer.py:401,475,517`); coverage rate via
  `emit_warmer_coverage_rate` reaching 1.0 (`cache_warmer.py:442`). On the bulk
  cadence DMS (`main.tf:644`) — must NOT trip (continuation keeps the lane fresh).
- **Rollback**: unset the env on the lane; next scheduled cycle restores parallel
  reads.
- **Residual risk if skipped**: the 900s envelope is an estimate; under real S3
  latency spikes a serialized fallback could strand the chain and silently stop
  warming until the 24h DMS — a slow-bleed staleness the LKG ceiling would then
  surface as honest 503s. MODERATE residual.

### EXP-4 — Section-warm clobber replay (SEAM-1 entity-keying guard)
**Fault class**: Dependency / data-integrity (entity collision). **Blast**:
staging cache keyspace; prod requires IC sign-off (data-integrity adjacent).

- **Hypothesis (falsifiable)** — *Given* SEAM-1 entity-keying keeps the active
  offer set at 62 / $79,485 and the legacy `entity=project` warm path is the
  collision risk, *When* the legacy entity=project warm path is replayed against
  the section keyspace (staging), *Then* entity-keying PREVENTS the 62→7 collapse
  — the active-offer count holds, and IF the merged active-offer-collapse(<40)
  alarm is APPLIED it stays silent (a clean bill of health is a POSITIVE result).
  - **REFUTED if**: active-offer count collapses toward 7 (⇒ entity-keying does
    NOT isolate the legacy path — the regression that #111 was supposed to cure
    is reachable again).
- **Injection (operator lever — NOT executed here)**:
  ```
  # Operator replays the legacy project-entity warm against staging keyspace.
  # The exact replay handler/event is operator-owned; this is a GAME-DAY with a
  # staging cache snapshot, NEVER prod first (data-integrity adjacent).
  ```
- **Blast radius / duration**: staging cache keyspace only; one replay + read
  verification = ~20 min.
- **Abort criteria**: active-offer count drops below 40 on staging (⇒ collapse
  reproducing) → ABORT, capture the collided keys, file P1. Any write toward a
  PROD key → immediate ABORT (must be staging-isolated).
- **Expected LOUD signal**: active-offer-collapse(<40) alarm IS the loud net —
  but **merged-not-applied** ⇒ **DOWNGRADE to read-assert**: query the active
  offer count (62 expected) post-replay; assert it did not collapse. Tie to the
  FPC coherent read (561) as the corroborating loud signal.
- **Rollback**: restore the staging cache snapshot; re-run section warmer once.
- **Residual risk if skipped**: if a legacy project-entity warm can still clobber
  the section keyspace, a routine ops action could silently collapse the active
  offer set in prod with no alarm (until the unapplied alarm lands). HIGH residual
  while the alarm is unapplied; MODERATE once applied.

### EXP-5 — Receiver kill / restart under load (serve-stale + ALB recovery)
**Fault class**: Process. **Blast**: single ECS task (1/1 → forced restart).

- **Hypothesis (falsifiable)** — *Given* serve-stale/LKG holds and the deploy-lock
  job-split landed (post-#485), *When* the single `:503` ECS task is stopped under
  steady read load, *Then* the ALB drains + reschedules, serve-stale/LKG covers
  the gap (honest 503 + Retry-After when cold, never silent empty-200), the task
  recovers, and the **deploy-lock is NOT burned** (the kill is not mistaken for a
  deploy).
  - **REFUTED if**: requests during the gap return 500 or silent empty-200
    (⇒ guard bypass), OR the deploy-lock is burned by the restart (⇒ job-split
    regression), OR recovery exceeds the LKG ceiling so frames hard-reject en
    masse (`config.py:105-117`).
- **Injection (operator lever — NOT executed here)**:
  ```
  # Operator stops the running ECS task (single replica):
  aws ecs stop-task --cluster <c> --task <arn> --reason "SRE-N5 EXP-5"
  # ECS reschedules to restore desired_count=1.
  ```
- **Blast radius / duration**: single task, the only replica → full receiver
  unavailability for the reschedule window (this is the highest-blast experiment;
  prod ONLY with IC sign-off + stakeholder notice). ~10-15 min.
- **Abort criteria**: 500s or silent empty-200 observed → ABORT (guard bypass,
  P1). Reschedule exceeds 5 min → ABORT + manual intervention. Deploy-lock burned
  → ABORT.
- **Expected LOUD signal**: `serving_stale_total` rises during the gap;
  `cadence_503` / `CACHE_NOT_WARMED` 503s with Retry-After (`query.py:564-575`),
  NOT 500s; `ReceiverQueryOutcomeServerError` rises then recovers (honest, bounded);
  ALB target-health flap. Single-worker means this is a HARD availability hit —
  expected and bounded, the test is that it is LOUD + bounded, not silent.
- **Rollback**: ECS auto-reschedules; if not, operator forces new deployment.
- **Residual risk if skipped**: an unverified restart path could hide a
  guard-bypass (500 / empty-200) under task loss — but EXP-5 is also the highest
  blast (sole replica). Net: MODERATE residual, run LAST and staging-heavy.

### EXP-6 — Asana 429 storm on the warmer (OBSERVE, do not inject)
**Fault class**: Dependency rate-limit. **Blast**: NONE (observation only).

- **Hypothesis (falsifiable)** — *Given* the warmer already rate-limits via AIMD
  (`config.py:239-256`: halve-on-429, +1-on-success, floor=1) and SA reads are
  namespaced to 600/min (`rate_limit.py:65-80`), *When* Asana returns a natural
  429 burst during a warm cycle, *Then* AIMD multiplicatively decreases
  concurrency, the cycle continues (possibly via self-invoke continuation), and
  no 429 escapes as a receiver 5xx — observable in existing telemetry without
  injection.
  - **REFUTED if**: a 429 burst drives the warm cycle to strand (no continuation)
    OR surfaces as a receiver `capacity_502`.
- **Injection**: **NONE** — this is an OBSERVATION design. Injecting a synthetic
  429 storm against live Asana risks the shared org rate-limit budget and is
  out-of-scope. The operator instead instruments the NEXT natural 429 event:
  watch `rate_limit_429_total{namespace="sa"}` (Alert A3, `rate_limit.py:19`),
  AIMD concurrency stats, and warmer coverage across the burst.
- **Blast radius / duration**: zero injection; passive over one natural-429
  window.
- **Abort criteria**: N/A (no injection). If a 429 burst is observed to strand a
  warm cycle, that is a FINDING, not an abort.
- **Expected LOUD signal**: `rate_limit_429_total{namespace="sa"}` (A3); AIMD
  decrease events; coverage rate holds across the burst.
- **Rollback**: N/A.
- **Residual risk if skipped**: LOW — AIMD is well-grounded and the path is
  already exercised in steady state; observation is opportunistic.

---

## 3. Global Safety Gates

### G0 — Pre-flight APPLY gate (BLOCKING)
Before ANY experiment whose LOUD signal is a merged-not-applied alarm
(floor-breach EXP-1, active-offer-collapse EXP-4, resolver-loop, burn-rate):
the operator MUST confirm the alarm is APPLIED (`terraform plan` shows no diff
for it) OR the experiment runs in **log-only / read-assert** mode (recorded
per-experiment above). No experiment depends on an alarm that may not exist.

### G1 — EMF self-measure must be ON
`RECEIVER_SLI_EMF_ENABLED=on` (`metrics.py:355`) before EXP-1/2/4/5 — otherwise
the receiver cannot self-prove and the success-rate LOUD signal is blind.

### G2 — Blast-radius progression
dev/staging → prod canary → prod partial → prod full. EXP-1, EXP-3, EXP-4
**MUST** pass staging before any prod execution. EXP-2 and EXP-5 touch prod env /
the sole prod replica → **operator decision beyond execution + IC sign-off + stakeholder
notice** required (§4).

### G3 — Error-budget check
If remaining error budget < 20%, prod experiments are forbidden — staging only
(per `[SR:SRC-001 Beyer et al. 2016] [STRONG]`).

### G4 — Monitoring active + rollback tested
All LOUD-signal dashboards open; each rollback rehearsed in staging before the
prod run.

---

## 4. Operator-Decision Flags (beyond mere execution)

| Experiment | Why it needs an operator decision | Escalate to |
|---|---|---|
| EXP-1 | Revokes a live IAM grant (TF apply); prod = data-source availability risk | Incident Commander |
| EXP-2 | Flips a PROD env var on `:503` | Incident Commander + service owner notice |
| EXP-3 | Flips a PROD-adjacent warmer env var (staging default) | Operator; IC if prod |
| EXP-4 | Data-integrity adjacent (active-offer set); staging-isolated mandatory | Incident Commander |
| EXP-5 | Stops the SOLE prod replica → full receiver unavailability window | Incident Commander + stakeholder notice (calendar window) |

All cross-repo TF / env levers (EXP-1, EXP-3 env names per the §0 UV-P labels)
require operator confirmation of the exact resource at game-day prep — the
chaos-engineer does NOT author or execute them.

---

## 5. Which Two To Run First — and Why

**First: EXP-1 (durable-read IAM revocation drill) + EXP-2 (heartbeat kill).**

1. **EXP-1 directly tests the grandeur anchor's load-bearing claim** — that the
   FPC Phase-2 cure DEGRADES TO HONEST-NULL, never to silent fabrication. The
   triple-defect saga (`fpc-phase2-deploy-node-fired`: stub-green ≠ production-real)
   makes "does it fail honest?" the single highest-value question. Its residual
   risk if skipped is HIGH (silent flattered numbers to consumers with zero
   alarm). Blast is bounded to one staging lane; it is read-only against prod by
   construction (staging-first, TF-revert rollback).

2. **EXP-2 is the cheapest high-value experiment and a prerequisite-validator
   for the others** — it proves the probe-class dead-man is REAL before we lean
   on alarms in EXP-1/3/4/5. If the dead-man is decorative (REFUTED), every
   downstream experiment's "LOUD signal" assumption weakens. Blast is a single
   env flip on the heartbeat only, business SLO held as the control. Running it
   second validates the observability substrate the whole blast depends on.

EXP-3/4 follow once EXP-2 confirms the alarm substrate; EXP-5 runs LAST (highest
blast — sole replica). EXP-6 is opportunistic observation, no scheduling.

---

## 6. Anti-Pattern Self-Check (this design)

- **Chaos without hypothesis** — AVERTED: every experiment has a falsifiable
  Given/When/Then + an explicit REFUTED condition.
- **Unbounded blast radius** — AVERTED: per-experiment blast + duration + abort
  criteria; global G0-G4 gates; G3 error-budget check.
- **Skipping non-prod** — AVERTED: G2 progression; EXP-1/3/4 staging-gated.
- **Resilience theater** — AVERTED: six distinct fault classes (dependency /
  process / resource / data-integrity / observability), not the same fault
  repeated; EXP-1 and EXP-4 are compound-adjacent (cure + collision).
- **Ignoring findings** — every REFUTED/PARTIAL outcome routes to a tracked
  action item (EXP-1 silent-fab → P1 IC; EXP-2 decorative-dead-man → P1; etc.).
- **Surprising stakeholders** — §4 mandates IC + service-owner + calendar notice
  for prod EXP-2/EXP-5.

---

## 7. Handoff

- **To Incident Commander**: EXP-1/EXP-4/EXP-5 prod execution authorization;
  acceptable prod-risk levels; scheduling of the sole-replica EXP-5 window.
- **To Platform Engineer**: confirm exact resource identifiers for the §0 UV-P
  cross-repo levers (`ASANA_CURE_COLD_CONCURRENCY`, `S3DurableTaskCacheRead`,
  the merged-not-applied alarms' APPLY status); apply the floor-breach /
  active-offer-collapse / resolver-loop / burn-rate alarms (G0 unblocks
  full-fidelity EXP-1/EXP-4).
- **Execution is NOT in this artifact** — R4 is design-only. Each injection above
  is an operator lever.

---

### Evidence grade

`[STRUCTURAL | MODERATE]` — self-authored design by the SRE rite (self-ref ceiling
per `self-ref-evidence-grade-rule`). Chaos principles cite STRONG sources
(`[SR:SRC-005 Rosenthal & Jones 2020]`, `[SR:SRC-001 Beyer et al. 2016]`,
`[II:SRC-001 Cook 1998]`). Receiver-repo facts carry file:line receipts (§0);
cross-repo claims carry UV-P labels pending operator probe.
