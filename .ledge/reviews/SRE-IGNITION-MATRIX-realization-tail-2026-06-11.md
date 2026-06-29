---
type: review
subtype: ignition-matrix
status: accepted
title: "SRE REALIZATION-IGNITION matrix — β-applies · #486 armed · AC-6 live · β-3 canary · chaos · soak-anchor"
date: 2026-06-11
rite: sre
evidence_grade: MODERATE  # sre self-attest ceiling per self-ref-evidence-grade-rule; the soak-CLEARED STRONG is eunomia's at the next seam (rite-disjoint, simultaneous five-signal observation)
ceiling_rung: soak-RUNNING  # authored<merged<applied<ARMED<fault-proven<cutover-live<soak-RUNNING<soak-CLEARED(next seam)<telos-verified-realized
heads:
  asana: bafd2508   # b48452d5 (entry) → 1c503339 (#125 nightly live-smoke) → bafd2508 (#126 γ-0 attribution)
  autom8y: post-#490(a3e74205-squash)+#491(80385bed-squash) on main
---

# SRE IGNITION MATRIX — Realization Tail (2026-06-11)

> **Grandeur anchor.** We IGNITE the realization tail of a plane already certified STRONG
> receiver-side (coherent=561, gun=10, unit.mrr=723/3021 — eunomia bit-exact). Every row below is a
> PASTED LIVE RECEIPT — AMP series, alarm-config, apply outputs, drill timestamps, the 5-signal
> bilateral — never a green dashboard, an `ActionsEnabled` read-back alone, or an optimistic merge.

## §0. PV verdicts (re-derived live, default-to-REFUTED)

| Premise | Verdict | Receipt |
|---|---|---|
| PV-HEAD | **CONFIRMED** | asana origin/main `b48452d5` at entry; ECS `:507`/`b48452d` COMPLETED both faces; warmer image `b48452d`; `git diff 2f0e7dc..b48452d -- src/` EMPTY (certified substrate) |
| PV-AC6 | **INVERTED → flowing** | `autom8y_asana_receiver_query_outcome_total` PRESENT: 1801/24h, 409/6h, 107/1h; entity=project, outcome=success; the "ABSENT/RED" premise was STALE |
| PV-486 | **INVERTED → already-applied (root) / alerts-dark** | the SRE-N6 CW filters/alarms from #486 were live (`autom8-asana-population-receipt-below-floor` et al.); only the AMP `slo_asana_receiver_alerts` namespace was unmaterialized |
| PV-DRIFT | **CONFIRMED** | live ECS `autom8y-asana-service-task-s3` = full-bucket (`autom8-s3` + `/*`), TF-NEVER-OWNED — β-3 target |
| PV-MONOLITH | **DISCOVERED** | monolith repo = `/Users/tomtenuta/Code/autom8`; running `monolith-prod:385` digest `sha256:c362f65e…`; `satellite_get_df_enabled` env-default true, live-echoed |
| PV-DEADMAN | **CONFIRMED** | AMP-native `AsanaReceiverHeartbeatAbsent` = `absent(...route_class=probe)` (inherently breaching-on-absence) |
| PV-TFTRAP | **HONORED** | every asana TF plan/apply pinned `-var image_tag=b48452d` |

## §1. The ignition matrix (GREEN/RED, no adjectives)

| Node | Action | Receipt | Rung |
|---|---|---|---|
| **S1 β-1 #490** | derive warmer env+IAM from `namespaces.gen.json` | fresh plan `No changes` (3 IAM policies + 3 lambdas, pinned); merged `a3e74205`; **applied**; live IAM ≡ registry on 3/3 warmer roles (`S3CacheAccess` 3-prefix, no `project-frames` write) | **applied** |
| **S2 β-2 #491** | strip fossil `project-frames` PUT/DELETE | rebased past squash-conflict; fresh plan = exactly 3 policy changes; merged `80385bed`; **applied**; fossil PUT/DELETE **GONE** all 3 roles, GET-only `S3FossilFramesRead` retained | **applied** |
| **S3 #486 arm** | materialize burn-rate SLO + probe dead-man | `slo_asana_receiver_alerts` ACTIVE in AMP (FastBurn+SlowBurn+HeartbeatAbsent); burn-rate recording rules evaluate (6h=0, 1h=NaN NO-DATA-honest) | **armed** |
| **S3 drill** | fault→alarm→page proof | synthetic `DrillIgnS3FaultToAlarm` (07:51:25Z) → AMP ruler `pending`→fired → **SNS publish +1** on `autom8y-platform-alerts` → `autom8-slack-alert` invoked → namespace deleted, cleared | **fault-proven** |
| **S4 β-3** | scope ECS task-s3 full-bucket → declared set | rollback byte-verified vs live (sha `730841e1`); module.service ref re-confirmed (no `task_s3`); scoped policy applied 07:57:42Z (3 Sids); **live write-through-scoped observed** `progressive_tier_put_success` 2537 rows 08:05:04Z; zero ECS AccessDenied | **applied + canary-running** (2h window + soak co-monitored) |
| **S5 AC-6** | monolith→receiver cutover live | 5-signal bilateral: monolith `Path:satellite GetDfSatellite:1.0 fallback:0`; SM-fetch Secret-2; SA paired `f55e4cdd↔sa_1a95b7c0↔asana-dataframe-resolver` (auth log); receiver 1947×200/24h; **zero fallback fires** | **cutover-live** |
| **S5 γ-0** | pin tasks/-writer | monolith `apis/aws_api/services/s3/models/asana_cache/tasks/main.py:447-448`; attributed in SNC registry via #126 (`bafd2508`); tests/arch 20/20 | **pinned + codified** |
| **S6 P1–P8** | soak preconditions | P1 AC-6 6h=409 / P2 #486-applied / P3a must-arm materialized+drill-proven / P4 dead-man absent()-healthy / P5 deploy 27293754687+27312946195 ≤20min clean / P6 band bit-identical (723/3021, 1332) / P7 up=1 + business-denom 107/1h / P8 not-a-blocker | **all GREEN** |
| **S7 EXP-1** | durable-read revocation drill | fault injected 08:03:28Z (S3DurableTaskCacheRead revoked, main lane); warm → `null_number_recovery_no_op healed:0 cold_present:0 cache_miss:3021` + floor WARNed `unit mrr:0.0` + `durable_task_cache_read_gid_failed` AccessDenied ×3021 — **HONEST-NULL, zero silent fabrication (REFUTED-condition did NOT occur — PASS)**; grant restored 08:07:27Z (4 Sids, zero AccessDenied in post-restore warm); side-effect frame restored 08:41:12Z (see §4) | **fault-proven (PASS) + cleaned-up** |
| **S7 EXP-2** | heartbeat dead-man real | route proven by S3 drill (AMP→SNS→Slack); `absent()` live-evaluating against present probe series; full sole-replica heartbeat-kill **DEFERRED to scheduled game-day** (sole-replica blip not run speculatively pre-soak) | **route-proven / injection-deferred** |
| **SX #125** | CHANGE-001 nightly OIDC live-smoke | merged `1c503339`; 5/5 live-smoke MRR=1500 local; actionlint clean; **nightly RED-until-IAM-grant** (no OIDC role grants `asana-cache/tasks/*` read — follow-up) | **merged / forcing-function-pending-grant** |

## §2. Rungs — never round up
**applied** (β-1/β-2 IAM, β-3 scoped policy) · **armed + fault-proven** (#486 dead-man via drill) ·
**cutover-live** (AC-6, MODERATE — SA-authenticated callers dominate, monolith get_df live+minority,
single trace not end-to-end-joined) · **soak-RUNNING** (this procession's ceiling). **soak-CLEARED**
and the **telos five-signal verified-realized** belong to the next seam (eunomia rite-disjoint,
simultaneous five-signal). Nothing here certifies the telos.

## §4. EXP-1 chaos findings (two genuine resilience gaps — routed, not papered)
The drill PASSED its hypothesis (honest-null, no silent fabrication) but surfaced two real gaps in
the warm/recovery path, plus a self-inflicted side-effect I rolled back:

1. **Write-not-fail-closed on cure-failure (MODERATE).** Under the revoked grant, the warm rebuilt the
   unit frame from source and **PERSISTED it null-degraded** (`dataframe.parquet` 08:06:28Z: mrr_nonnull
   0/3021) rather than fail-closing the write to preserve the prior-good frame. The floor WARNed
   (LOUD — the designed honest-null), so it is not silent; but a consumer reading between the
   degraded write and a re-heal gets nulls. **The offer frame (live MRR, 1332/4079) was untouched —
   blast bounded to the unit cure path; unit consumers are SEAM-2-deferred (no live reader).** Route
   to 10x-dev: should cure-failure fail the frame WRITE (keep prior-good) instead of persisting degraded?
2. **Freshness-skip blocks auto-recovery (MODERATE).** The post-restore warm refreshed `manifest.json`
   (08:34:39Z) but **freshness-skipped the dataframe rebuild** (watermark 08:06:28Z < 6h MaxParquetAge),
   so the degraded frame was NOT auto-re-healed — the cure cannot self-correct a degraded-but-recent
   frame until the staleness window (~14:06Z) or a forced rebuild. Route to 10x-dev: freshness should
   key on data-quality (floor breach), not only watermark age.
3. **Cleanup (done, not deferred).** Rolled back the chaos side-effect by restoring the captured
   pre-experiment frame (3021/723/719/335, byte-verified) at 08:41:12Z; degraded frame saved as forensic
   evidence (`/tmp/ign-frames/unit_degraded_0806.parquet`). Post-restore coherence band (substrate raw,
   non-simultaneous frame-pair): **coherent=578 (5.8× the ≥100 bar), gun=19, total_joined=2020** — the
   plane is converged and clean for the soak. (Bit-exact 561/10 re-cert is eunomia's at soak-clear, not sre's.)

## §3. Residuals / DEFER (watch-registered, not scope-crept)
- **β-3 2h canary window** — write observed + zero denials so far; continues under soak co-monitoring; rollback JSON staged (`/tmp/ign-receipts/beta3-rollback-task-s3-fullbucket.json`, sha `730841e1`).
- **CHANGE-001 nightly RED-until-IAM** — needs a read-only `asana-cache/tasks/*` grant on an OIDC-assumable role (dedicated `LIVE_SMOKE_ROLE` preferred over widening `github-actions-deploy`).
- **autom8y vendored gen.json re-vendor** — #126 changed the asana canonical `external_name`; the autom8y copy lags; `check_namespaces_gen.sh` flags next CI (no live-infra impact — prefix/ARN roots unchanged).
- **unit-floor calibration** — `population-receipt-below-floor` in ALARM since 06-10 20:07Z (sold band ~0.237 vs 0.8 threshold); ship-dark; carried as a NAMED soak exception, not a reset trigger; routed UK-2/FPC-Phase-3.
- **EXP-2 full heartbeat-kill** · **EXP-3/4/5** — scheduled game-day, staging-first.
- **Node20 non-deploy sweep — deadline 2026-06-16 (5 days).**
- Stage-B→Secret-2 (irreversible, soak-clear-gated) · SEAM-2 rebind · fleet-export N≥2.
