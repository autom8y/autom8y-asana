---
type: spec
status: draft
---

# CHAOS-DESIGN — Post-Soak-Clear Verification Blast (re-grounded on `:511`)

> **Station**: SOAK-S4 DESIGN-ONLY. **ZERO injection this procession.** The 7-day
> telos-soak is RUNNING (anchor `2026-06-11T15:24:21Z` on ECS `:511` / image
> `49099b1`, clear `2026-06-18T15:24:21Z`). Mid-soak fault injection against prod
> asana is an operator strict-impossibility. **Every injection below is a labeled
> operator lever for AFTER soak-clear.** This artifact is the only mutation made
> authoring it. Production READS + repo reads only.
>
> **Grandeur anchor.** We hold the 7-day telos-soak as a SENTINEL — and the 06-18
> clear-day unlock bundle AUTHORED-READY, so the moment the clock clears, the
> acceptance is pre-written, never improvised.

- **Date authored**: 2026-06-11
- **Target**: `autom8y-asana` receiver (ECS `:511`, image `49099b1`, 1/1, single
  uvicorn worker) + warmer Lambdas (main / bulk / section) + durable S3
  task-cache reads (`S3DurableTaskCacheRead`).
- **Engineer**: chaos-engineer (SRE rite, station SOAK-S4)
- **Re-grounds**: `.ledge/specs/CHAOS-DESIGN-receiver-post-cure-blast-2026-06-10.md`
  (targeted `:503` / image `b114530`; carried UV-P labels now resolvable).
- **Evidence grade**: `[STRUCTURAL | MODERATE]` (sre self-attest ceiling per
  `self-ref-evidence-grade-rule`; the soak-CLEARED STRONG re-cert is eunomia's at
  the next seam, rite-disjoint, simultaneous five-signal). Chaos principles cite
  STRONG sources (`[SR:SRC-005 Rosenthal & Jones 2020]`,
  `[SR:SRC-001 Beyer et al. 2016]`, `[II:SRC-001 Cook 1998]`).

---

## 0. Re-Grounding Verdict — Stale Facts Corrected (the G-PROVE delta)

Every code claim below carries a `file:line` receipt verified against current
`autom8y-asana` main (HEAD `3bbb9bc8`) and the autom8 worktree this hour. The
prior 06-10 doc's stale facts are pasted alongside their correction.

| # | OLD doc (06-10) claim | Corrected fact (today, `:511`) | Receipt |
|---|---|---|---|
| C-1 | "ECS task sizing `cpu=1024 / memory=2048`" (06-10 §0 row, citing `main.tf:158-159`) | **LIVE `:511` task-def is `cpu=2048 / memory=8192`.** The TF in the autom8 worktree STILL declares `cpu=1024`/`memory=2048` at `main.tf:158-159` — that is a STALE TF declaration vs the live task-def. | TF still says `cpu = 1024` / `memory = 2048` at `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/asana/main.tf:158-159`; live `:511` floor = 2048/8192 per `cure-recovery-hardening-127` auto-memory ("floor 2048/8192") + IC-SOAK-REANCHOR. **UV-P below.** |
| C-2 | Target = ECS `:503` / image `b114530` | Target = ECS `:511` / image `49099b1` (soak substrate) | `IC-SOAK-REANCHOR-telos-soak-RUNNING-2026-06-11.md`; auto-memory `cure-recovery-hardening-127` |
| C-3 | EXP-2 UV-P: "does `ASANA_SLI_HEARTBEAT_DISABLED` env even exist?" | **RESOLVED — the toggle does NOT exist (grep exit 1, repo-wide).** The dead-man is an AMP-native `absent()` rule over the telemetry-SDK `route_class=probe` series; there is no process heartbeat emitter and no disable env. EXP-2 redesigned honestly (§2, EXP-2). | `grep -rn ASANA_SLI_HEARTBEAT_DISABLED src/` = no matches; only `route_class` probe classifier emits the series (`route_class.py:42-48`) |
| C-4 | LKG `LKG_MAX_STALENESS_MULTIPLIER = 10.0` at `config.py:117` | **HOLDS** — re-verified `LKG_MAX_STALENESS_MULTIPLIER: float = 10.0` | `src/autom8_asana/config.py:117` |
| C-5 | Serve-stale ceilings `project=86400 / section=576` at `config.py:162-165` | **HOLDS** — `FRESHNESS_CONTRACT_MAX_AGE_SECONDS = {"project": 86400.0, "section": 576.0}` | `src/autom8_asana/config.py` (FRESHNESS_CONTRACT map, project=86400.0 / section=576.0) |
| C-6 | (06-10 had no EXP-1 precedent) | **EXP-1 was RUN and PASSED 2026-06-11** (re-game-day GREEN by CONTENT at both altitudes); its exact mechanics are the strongest paste-ready precedent (§4). | `SRE-IGNITION-MATRIX-realization-tail-2026-06-11.md:46`; auto-memory `cure-recovery-hardening-127` |

### UV-P labels (claims not first-party-receiptable from the receiver repo this hour)

- `[UV-P: the LIVE :511 ECS task-def runs cpu=2048/memory=8192 (NOT the cpu=1024/memory=2048 the autom8 TF declares at main.tf:158-159) | METHOD: deferred-to-operator-probe (aws ecs describe-task-definition --task-definition autom8y-asana-service) | REASON: live task-def is TF-drifted (the IGNITION matrix already recorded autom8y-asana-service-task-s3 as TF-NEVER-OWNED, PV-DRIFT CONFIRMED); auto-memory records the 2048/8192 floor but a first-party describe-task-definition is the operator's pre-flight receipt — do NOT fabricate a TF file:line that contradicts the live fact]`
- `[UV-P: the autom8y vendored namespaces.gen.json lags the asana canonical external_name post-#126 | METHOD: deferred-to-cross-repo (check_namespaces_gen.sh next CI) | REASON: cross-repo, no live-infra impact (prefix/ARN roots unchanged); recorded as a soak residual, not a blast input]`
- `[UV-P: the canary section-arm fix PR (judging the section arm correctly) is authored-held by a sibling SOAK station | METHOD: deferred-to-sibling-merge | REASON: until it merges, the blast judges by the PROJECT arm + content checks (§2 EXP-5); the section arm is column-contract-EXEMPT today (receiver_bulk_fanout_deploy_gate.py:711-714) and the SA-section path FAILs by design]`

---

## 1. Steady-State Baseline (today's `:511` numbers — measure BEFORE any injection)

| Metric | Normal Range (today) | Source |
|---|---|---|
| Coherent (envelope) | **593** (envelope 579–593, floor 561) | auto-memory `storage-namespace-contract`; IGNITION §4 (post-restore 578, ≥100 bar) |
| Gun (drift cells) | **10** | auto-memory `fpc-phase2-deploy-node-fired` (gun 571→10) |
| Unit band | **724 / 3027** (23.9% sold band) | dispatch baseline (was 723/3021 at #128; 724/3027 today) |
| Offer band | **1352 / 4079** | dispatch baseline (was 1332/4079; 1352/4079 today) |
| Active-offer set | 62 / $79,485 | auto-memory `seam1-entity-blind-reader-gap` |
| AC-6 receiver outcome | organic **~100-class hourly :30 bursts** (zero-floors between) on the PREFIXED `autom8y_asana_receiver_query_outcome_total` | IGNITION §0 PV-AC6 (1801/24h, 409/6h, 107/1h); auto-memory (~105/burst, bursty) |
| Receiver query success rate (both arms) | ≥ 99% sustained 10-min | `record_receiver_query_outcome` (`metrics.py`); deploy-gate (`query.py`) |
| Alarms | **FastBurn / SlowBurn / HeartbeatAbsent INACTIVE-armed** (materialized in AMP `slo_asana_receiver_alerts`, state `inactive`, drill-proven 07:51Z) | `IC-SOAK-REANCHOR-…-2026-06-11.md:49,85`; IGNITION §1 S3 |

**Steady-state pre-flight (operator, read-only, AFTER soak-clear):** confirm all of
the above green for 10 min AND `RECEIVER_SLI_EMF_ENABLED=on` (`metrics.py:355`)
so the receiver self-proves. The unit-floor `population-receipt-below-floor` is in
ALARM since 06-10 (sold band 0.237 vs 0.8 threshold) — a NAMED soak exception
(ship-dark, not a reset trigger; routed UK-2/FPC-Phase-3); it is **expected** and
must not be read as a fresh fault during baseline.

---

## 2. EXP-2 + EXP-5 (re-grounded) and the standing blast set

(EXP-1 re-game-day mechanics are §4 — the clear-day acceptance. EXP-3/4/6 carry
forward from the 06-10 doc unchanged in substance; this artifact re-grounds the
two the dispatch named: EXP-2 toggle-resolution and EXP-5 facts.)

### EXP-2 — Heartbeat dead-man (probe-class), RE-GROUNDED — UV-P RESOLVED

**THE TOGGLE-EXISTENCE VERDICT (the 06-10 UV-P resolution):**

> `ASANA_SLI_HEARTBEAT_DISABLED` **DOES NOT EXIST.** `grep -rn` across `src/` (and
> repo-wide, all forms `HEARTBEAT_DISABLED|HEARTBEAT_ENABLED|SLI_HEARTBEAT`)
> returns **exit 1, no matches**. The only `heartbeat` in `src/` is the preload
> progressive heartbeat — a 30-second **log line** (`preload_heartbeat`,
> `src/autom8_asana/api/preload/progressive.py:182-191`), NOT an AMP-emitted SLI
> series and NOT alarmable on absence. The 06-10 design's injection rested on a
> **phantom env var**.

**What actually emits the series behind `AsanaReceiverHeartbeatAbsent`:** the
alarm is an **AMP-native `absent()` rule** — `absent(...route_class=probe)` —
that fires when the telemetry-SDK request series tagged `route_class=probe`
STOPS arriving (PV-DEADMAN CONFIRMED,
`SRE-IGNITION-MATRIX-realization-tail-2026-06-11.md:31`). The `probe` series is
emitted by the `autom8y-telemetry` FastAPI middleware on every request whose
route-template path classifies as a probe — exact-match `/ready`, `/live`,
`/metrics`, `/health` or the `/health/` sub-tree
(`/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-telemetry/src/autom8y_telemetry/fastapi/route_class.py:42-48,60-83`).
So **there is no emitting process to stop and no env to flip** — the dead-man is
fed by the request counter itself.

**Consequence — the experiments MERGE, honestly.** "Disable the heartbeat" is not
a real, isolated injection on this substrate. The ONLY honest way to make the
`route_class=probe` series go absent is to **stop the thing emitting it** — i.e.
stop the receiver task (no requests → no probe series) — which is **EXP-5's
territory**. Therefore:

- **EXP-2 is NOT a standalone env-flip experiment. It is the observability
  ASSERTION RIDING ON EXP-5**: when the sole `:511` task is stopped (EXP-5), the
  `route_class=probe` series goes absent and the `AsanaReceiverHeartbeatAbsent`
  dead-man MUST fire within its `absent()` window (~10 min). EXP-2's hypothesis is
  verified as a co-observation of EXP-5, not a separate injection.
- An **alternative isolated probe-absence injection** — a network-level block of
  the probe path (e.g. an ALB/security-group rule that drops `/ready|/live|
  /metrics|/health` while leaving `/v1/query` business traffic flowing) — WOULD
  isolate probe-absence from business-availability, but it is a heavier
  infrastructure lever (ALB rule edit, prod-network adjacent) and is recorded here
  as the **fallback isolated form** if the operator wants probe-decoupling proof
  without a full task-stop. It is NOT the recommended first form.

- **Hypothesis (falsifiable)** — *Given* the dead-man is `absent(route_class=probe)`
  and business-class SLIs derive from the separate `route_class=business`
  denominator (`autom8y_http_requests_total{service="asana"}`, the `/v1/query`
  path; `slo_ecs_services.yaml` asana availability rules), *When* the
  `route_class=probe` series goes absent (EXP-5 task-stop, OR the fallback
  network-block of the probe paths), *Then* `AsanaReceiverHeartbeatAbsent` fires
  within ~10 min AND — in the network-block fallback — the business-availability
  SLO is UNAFFECTED (proving the two classes are decoupled and the dead-man is
  real, not decorative).
  - **REFUTED if**: the dead-man does NOT fire within 2× its window (⇒ the
    `absent()` rule is mis-configured or the probe series is not what the alarm
    keys on — silent blindness), OR (network-block form) the business SLO degrades
    when only the probe paths are blocked (⇒ false coupling).
- **Injection (operator lever — POST-SOAK, NOT executed here)**:
  - **Recommended form**: ride EXP-5 (§2 EXP-5). No separate injection.
  - **Fallback isolated form** (ALB/SG rule edit, prod-network adjacent → operator
    decision + IC sign-off): drop `/ready`, `/live`, `/metrics`, `/health` at the
    edge for ≤ 1 `absent()` window; leave `/v1/query` flowing; observe.
- **Status note (proven 06-11):** the AMP→SNS→Slack route is ALREADY drill-proven
  (synthetic `DrillIgnS3FaultToAlarm` 07:51:25Z → SNS publish +1 →
  `autom8-slack-alert`); and the full sole-replica heartbeat-kill was
  **DEFERRED to scheduled game-day** (IGNITION §1 S7 EXP-2: "route-proven /
  injection-deferred"). This spec IS that scheduled game-day.
- **Abort criteria** (fallback form): business SLO success rate drops > 0.5%
  absolute (means the block caught more than the probe paths) → ABORT + revert
  the rule. Dead-man pages the wrong sev → ABORT (alarm-routing defect, separate
  finding).
- **Expected LOUD signal**: `AsanaReceiverHeartbeatAbsent` (AMP, 10m `absent()`)
  → SNS → Slack. Distinguish from `cache_warmer_DMS_24h` (warmer-side dead-man) —
  this targets the RECEIVER probe-class absence.
- **Rollback** (fallback form): remove the edge rule; probe series resumes < 1
  window; dead-man clears.
- **Residual risk if skipped**: a decorative dead-man means a true receiver stall
  (no requests at all) would go unpaged. MODERATE-HIGH residual — but materially
  reduced by the 06-11 route-drill; the open question is purely "does absence of
  the probe series trip it," which EXP-5 answers as a free co-observation.

### EXP-5 — Sole-replica task-kill under load (serve-stale + ALB recovery), RE-GROUNDED

**Fault class**: Process. **Blast**: single ECS task (1/1 → forced stop). This is
the highest-blast experiment (sole replica) — run LAST, staging-heavy, prod only
with IC sign-off + stakeholder notice.

**Corrected facts (vs 06-10):**

| Fact | OLD (06-10) | Today (`:511`) | Receipt |
|---|---|---|---|
| Task target | `:503` / `b114530` | `:511` / `49099b1` | IC-SOAK-REANCHOR |
| Task sizing | `cpu=1024 / memory=2048` (STALE) | `cpu=2048 / memory=8192` | UV-P §0 (live describe-task-definition; auto-memory floor 2048/8192) |
| Replica count | 1/1 single task | 1/1 single task (unchanged) | dispatch |
| LKG ceiling | `=10.0` | `=10.0` (HOLDS) | `src/autom8_asana/config.py:117` |
| Serve-stale ceiling | project=86400 / section=576 | unchanged (HOLDS) | `src/autom8_asana/config.py` FRESHNESS_CONTRACT map |
| Deploy-lock | "job-split landed post-#485" | re-verify the job-split is live before the kill (so the stop is not mistaken for a deploy) | operator pre-flight |
| Load instrument | (not specified) | the **canary** `scripts/canary/receiver_bulk_fanout_deploy_gate.py`, judged by the **PROJECT arm + content checks** (section arm FAILs by design today — UV-P §0) | `scripts/canary/receiver_bulk_fanout_deploy_gate.py:711-714,730-748` |

- **Hypothesis (falsifiable)** — *Given* serve-stale/LKG holds (`config.py:117`)
  and the deploy-lock job-split is live, *When* the single `:511` ECS task is
  stopped under steady PROJECT-arm canary load, *Then* the ALB drains +
  reschedules, serve-stale/LKG covers the gap (honest 503 + Retry-After when cold,
  never a silent empty-200 or a 500), the task recovers, the `route_class=probe`
  series goes absent and the `AsanaReceiverHeartbeatAbsent` dead-man fires
  (this is EXP-2's co-observation), and the **deploy-lock is NOT burned**.
  - **REFUTED if**: requests during the gap return 500 or silent empty-200 (⇒
    guard bypass, P1), OR the deploy-lock is burned by the restart (⇒ job-split
    regression), OR recovery exceeds the LKG ceiling so frames hard-reject en
    masse (`config.py:117` + FRESHNESS_CONTRACT), OR the dead-man does NOT fire on
    the probe-series absence (⇒ EXP-2 REFUTED — decorative dead-man).
- **Injection (operator lever — POST-SOAK, NOT executed here)**:
  ```
  # Drive PROJECT-arm load first (content-bound, the trustworthy arm):
  python scripts/canary/receiver_bulk_fanout_deploy_gate.py \
    --base-url <receiver-url> --project-gid 1201081073731555 \
    --duration-minutes 10 --target-rpm <peak> --success-threshold 0.99
  # Then operator stops the single replica mid-window:
  aws ecs stop-task --cluster <c> --task <arn> --reason "SOAK-S4 EXP-5"
  # ECS reschedules to restore desired_count=1.
  ```
  The canary judges by the PROJECT arm (column contract office_phone/vertical/gid,
  `PROJECT_CONTRACT_COLUMNS`, `receiver_bulk_fanout_deploy_gate.py:135`) +
  success-rate; the SECTION arm is column-contract-EXEMPT and FAILs by design
  today (UV-P §0) — **ignore the section verdict until the sibling fix merges**.
- **Blast radius / duration**: single task, the only replica → full receiver
  unavailability for the reschedule window. ~10–15 min. Prod ONLY with IC sign-off
  + stakeholder notice + calendar window.
- **Abort criteria**: 500s or silent empty-200 observed → ABORT (guard bypass,
  P1). Reschedule exceeds 5 min → ABORT + manual intervention. Deploy-lock burned
  → ABORT.
- **Expected LOUD signal**: `serving_stale_total` rises during the gap;
  `cadence_503` / `CACHE_NOT_WARMED` 503s with Retry-After (NOT 500s);
  `ReceiverQueryOutcomeServerError` rises then recovers (honest, bounded);
  `AsanaReceiverHeartbeatAbsent` fires on probe-series absence (EXP-2 co-obs); ALB
  target-health flap. Single-worker means this is a HARD availability hit —
  expected and bounded; the test is that it is LOUD + bounded, not silent.
- **Rollback**: ECS auto-reschedules; if not, operator forces new deployment.
- **Residual risk if skipped**: an unverified restart path could hide a
  guard-bypass under task loss; MODERATE residual; run LAST (sole replica).

### Standing set carried from 06-10 (unchanged in substance)

- **EXP-3** — Warm-path S3 latency / concurrency exhaustion (`ASANA_CURE_COLD_CONCURRENCY=1`
  on one warmer lane, staging; envelope/self-invoke proof). Cross-repo env per
  UV-P; operator pre-flight. See 06-10 §2 EXP-3.
- **EXP-4** — Section-warm clobber replay (SEAM-1 entity-keying guard; staging
  cache keyspace; active-offer-collapse(<40) is the loud net, DOWNGRADE to
  read-assert if the alarm is unapplied). See 06-10 §2 EXP-4.
- **EXP-6** — Asana 429 storm on the warmer (OBSERVE-only, no injection; instrument
  the next natural 429 window; AIMD `config.py:239-256`). See 06-10 §2 EXP-6.

### Global safety gates (carried + re-grounded)

- **G0 — APPLY gate (BLOCKING)**: any experiment whose LOUD signal is a
  merged-not-applied alarm runs log-only/read-assert until APPLY is confirmed.
  Note: FastBurn/SlowBurn/HeartbeatAbsent ARE materialized + armed (state
  `inactive`) as of 06-11 — so EXP-2/EXP-5's dead-man signal is APPLIED (no
  downgrade). The floor-breach / active-offer-collapse alarms remain operator
  pre-flight per their APPLY status.
- **G1 — EMF self-measure ON**: `RECEIVER_SLI_EMF_ENABLED=on` (`metrics.py:355`).
- **G2 — Blast-radius progression**: dev/staging → prod canary → prod partial →
  prod full. EXP-3/EXP-4 staging-gated. EXP-2-fallback (network-block) and EXP-5
  touch prod-network / the sole replica → IC sign-off + stakeholder notice.
- **G3 — Error-budget check**: remaining budget < 20% → staging only
  (`[SR:SRC-001 Beyer et al. 2016] [STRONG]`).
- **G4 — Monitoring active + rollback rehearsed in staging before prod**.

---

## 4. CLEAR-DAY RE-GAME-DAY (06-18 acceptance, PRE-WRITTEN — paste-ready)

This is the EXACT EXP-1 rerun proven 2026-06-11 (re-game-day GREEN by CONTENT at
both altitudes, zero interventions — the strongest precedent). It is **read-only +
IAM-revoke-scoped**. Success = `self-heal-game-day-proven` re-earned on whatever
substrate is live at clear-day.

**RESET-WARNING (load-bearing):** the re-game-day itself does **NOT reset the soak
clock** — proven 06-11: the soak law treats EXP-1 as **acceptance, not a deploy**
(the 14:59:07Z anchor was raced only by the self-inflicted #129 DEPLOY 16 min
later, not by the game-day). The fault is an IAM-policy revoke + a serve READ; no
image, no task-def, no code lands. **BUT any DEPLOY to fix a RED finding DOES reset
the clock** — so if the re-game-day goes RED, the fix-deploy re-anchors a fresh
7-day soak. Plan the run for the START of a fresh window, not the tail.

**Lesson from 06-11 (why CONTENT, not the log):** the warmer's
`fail_closed_write_preserve_prior_good` PRESERVE log **lied twice** — first as
decided-not-enforced (game-day RED: logged preserve yet still wrote degraded
0/3021), then only enforced-GREEN after the #128 convergence onto one gated write
primitive + one gated serve accessor. **The PRESERVE log is INADMISSIBLE as
proof.** Assert by CONTENT at both altitudes (disk byte-identity under fault AND a
live serve read), never by the log.

### Step 0 — capture prior-good FIRST (before any revoke)

```
# (a) Unit parquet + count, captured from LIVE S3 BEFORE the fault.
#     The unit frame lives under a namespaced prefix (StorageNamespaceContract;
#     read via DurableTaskCacheReader, NOT a single hardcoded path) — the
#     operator resolves <unit-frame-key> at game-day from the SNC registry /
#     a live `aws s3 ls` (do NOT trust ASANA_CACHE_S3_PREFIX — ZERO live
#     readers, latent overload per auto-memory storage-namespace-contract).
#     Record mrr non-null count (sold band ~0.24) + object etag (byte-identity).
aws s3 cp s3://autom8-s3/<unit-frame-key>/dataframe.parquet /tmp/sgd/unit_prior_good.parquet
#   record: row count, count(mrr non-null), etag.
# (b) The LIVE 4-Sid warmer policy (the restore source — NEVER a stale file):
aws iam get-role-policy \
  --role-name autom8-asana-cache-warmer-lambda-role \
  --policy-name autom8-asana-cache-warmer-s3-cache \
  > /tmp/sgd/warmer-policy-LIVE.json
```

### Step 1 — revoke (derive the revoked doc FROM the live capture)

```
# Strip the S3DurableTaskCacheRead Sid from the LIVE-captured doc (Step 0b),
# producing the revoked doc. DERIVE from the live capture, never a stale file —
# the live doc had 4 Sids on 06-11; the revoked doc is live-minus-that-one-Sid.
aws iam put-role-policy \
  --role-name autom8-asana-cache-warmer-lambda-role \
  --policy-name autom8-asana-cache-warmer-s3-cache \
  --policy-document file:///tmp/sgd/warmer-policy-REVOKED.json
```

### Step 2 — force warm (Event + queue; reserved-concurrency=1)

```
# reserved-concurrency=1: a SYNC invoke self-collides on CLI retry. Use Event
# (async) + queue — the queued invoke starts when the single slot frees.
aws lambda invoke \
  --function-name autom8-asana-cache-warmer \
  --invocation-type Event \
  --payload '{"entity_types":["unit"],"resume_from_checkpoint":false}' \
  /tmp/sgd/warm-out.json
```

### Step 3 — assert PRESERVE by CONTENT at BOTH altitudes (the log is INADMISSIBLE)

- **Altitude 1 — S3 disk byte-identity under fault**: re-read the unit parquet
  from S3; assert the etag is UNCHANGED vs Step 0a (the enforced path writes
  ZERO `final_artifacts_written` and leaves disk byte-identical; the RED path
  rewrote 0/3021 with a new etag). AND assert `count(mrr non-null)` ratio still
  holds the sold band ~0.24.
- **Altitude 2 — live serve via a FRESH origin/main worktree probe** (deployed
  code reading live S3):
  ```
  # In a fresh origin/main worktree:
  PYTHONPATH=<worktree>/src ASANA_CACHE_S3_BUCKET=autom8-s3 python - <<'PY'
  import asyncio
  from autom8_asana.cache.dataframe.factory import initialize_dataframe_cache
  cache = initialize_dataframe_cache()  # factory.py:149
  async def main():
      entry = await cache.get_async("1201081073731555", "unit")  # dataframe_cache.py:235; UNIT_PROJECT project_registry.py:24
      # assert the served frame holds 724/3027 (sold band ~0.24), NOT 0/3027
      print(entry)
  asyncio.run(main())
  PY
  ```
  Assert the served unit frame holds the band (724/3027 today; whatever the live
  band is at clear-day), NOT a null-degraded 0/3027.

### Step 4 — restore (finally-discipline, the EXACT captured doc)

```
# ALWAYS restore from the Step-0b LIVE capture (4 Sids), in a finally block —
# never leave the revoke applied. Re-warm once; assert zero AccessDenied.
aws iam put-role-policy \
  --role-name autom8-asana-cache-warmer-lambda-role \
  --policy-name autom8-asana-cache-warmer-s3-cache \
  --policy-document file:///tmp/sgd/warmer-policy-LIVE.json
```

### Step 5 — Fork-2 re-heal assert (fresh write, in-band counts)

After restore, force one more warm (grant present) and assert the unit frame
re-heals to in-band counts via a FRESH write (new etag, `final_artifacts_written`
non-zero, `count(mrr non-null)` back in the sold band) — proving the cure
self-corrects once the dependency returns.

### Success criterion

`self-heal-game-day-proven` re-earned: HONEST-NULL under fault (LOUD
`durable_task_cache_read_gid_failed` AccessDenied ×N, floor WARNs) + zero silent
fabrication (REFUTED-condition did NOT occur) + disk byte-identical under fault +
live serve holds the band + Fork-2 re-heal. **Bit-exact band/coherent re-cert
(561/10/724/3027/1352/4079) is eunomia's at soak-clear (rite-disjoint, simultaneous
five-signal) — NOT sre's; this game-day proves the SUBSTRATE, not the telos.**

### Carry-forward findings to re-verify at clear-day (the 06-11 EXP-1 gaps)

Two MODERATE gaps surfaced 06-11, routed to 10x-dev — confirm their disposition
before the re-game-day so a known-issue is not re-litigated as a new RED:
1. **Write-not-fail-closed on cure-failure** — #128 converged this onto the gated
   write primitive (enforced GREEN). Re-verify the enforced path still holds on
   the clear-day substrate (assert disk byte-identity, Step 3 Altitude 1).
2. **Freshness-skip blocks auto-recovery** — keyed on watermark age, not
   data-quality (floor breach). If still open, the Fork-2 re-heal (Step 5) may
   need a forced rebuild rather than relying on auto-recovery; note it, don't
   treat the skip as a fresh fault.

---

## 5. Anti-Pattern Self-Check (per the original §6)

- **Chaos without hypothesis** — AVERTED: every experiment carries a falsifiable
  Given/When/Then + explicit REFUTED condition. EXP-2 was REDESIGNED rather than
  left resting on a phantom env (the toggle grep-resolved to non-existence).
- **Unbounded blast radius** — AVERTED: per-experiment blast + duration + abort;
  G0–G4 global gates; G3 error-budget check.
- **Skipping non-prod** — AVERTED: G2 progression; EXP-3/EXP-4 staging-gated;
  EXP-5 (sole replica) + EXP-2-fallback (prod-network) IC-gated.
- **Resilience theater** — AVERTED: distinct fault classes (dependency / process /
  resource / data-integrity / observability); EXP-1 already PASSED once, so per the
  Resilience-Theater correction it GRADUATES — the re-game-day re-runs it on a NEW
  substrate (`:511` vs `:510`) as soak-clear acceptance, not a third identical run
  for theater; EXP-5 is the genuinely-new compound (process-kill + dead-man co-obs).
- **Ignoring findings** — every REFUTED/PARTIAL routes to a tracked action item;
  the two 06-11 EXP-1 gaps are already routed to 10x-dev (§4 carry-forward).
- **Surprising stakeholders** — §EXP-2-fallback/EXP-5 mandate IC + service-owner +
  calendar notice for prod-network / sole-replica injection.
- **Mid-soak injection** — STRUCTURALLY AVERTED: this is DESIGN-ONLY; zero
  injection executed; every lever is labeled operator + POST-SOAK.

---

## 6. Handoff

- **To Incident Commander**: EXP-2-fallback (network-block) + EXP-5 (sole-replica)
  prod authorization; acceptable prod-risk levels; scheduling of the sole-replica
  window AFTER soak-clear; whether the clear-day re-game-day runs at the START of a
  fresh window (so a RED-fix-deploy re-anchor is clean).
- **To Platform Engineer**: confirm the live `:511` task sizing via
  `describe-task-definition` (UV-P §0); confirm the deploy-lock job-split is live
  before EXP-5; merge the canary section-arm fix (sibling-held) so EXP-5 can judge
  both arms; confirm APPLY status of the floor-breach / active-offer-collapse
  alarms (G0).
- **To self / sre at soak-clear**: §4 is the pre-written acceptance — run it
  verbatim against the live substrate; eunomia does the rite-disjoint five-signal
  STRONG re-cert.
- **Execution is NOT in this artifact** — SOAK-S4 is design-only. Every injection
  above is an operator lever for AFTER 2026-06-18T15:24:21Z.
