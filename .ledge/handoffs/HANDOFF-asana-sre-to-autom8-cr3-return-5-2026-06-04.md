---
type: handoff
status: draft
handoff_status: pending
source_rite: sre
target_rite: arch/10x-dev
from_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
to_repo: /Users/tomtenuta/Code/autom8
created: 2026-06-04
in_reply_to: HANDOFF-asana-sre-to-autom8-cr3-return-4-2026-06-04
supersedes_item: "RETURN-4 §1 — the SLI-restore prerequisite (instrument_app / PR #107) is now DISCHARGED; §D PROJECT PASS is live-measured, no longer 'baseline-consistent but not yet load-measured'"
ledge_status: AUTHORED-and-delivered
reversible: true
evidence_ceiling: STRONG  # §D PROJECT PASS = rite-disjoint, live-measured chaos re-gate verdict (up-state/ratio/CPU). MODERATE elsewhere (SRE-authored synthesis).
discipline: REVERSIBLE/READ-ONLY authorship. Section lane STAYS PAUSED. No merge/apply/deploy/secret/knob-land by this artifact. Secrets redacted.
---

# HANDOFF — autom8y-asana (SRE) → autom8 (consumer): CR-3 RETURN-5 — §D PROJECT arm PASS (measured) → project cutover-ready; section stays HELD

> Update to RETURN-4. The one prerequisite RETURN-4 §1 named — the receiver SLI-restore (`instrument_app` / PR #107) — is **DISCHARGED**. The chaos §D PROJECT re-gate has now been **run on a live SLI** and **PASSED at 100.0% (243/243)**. The §D chaos precondition for the project cutover is therefore **DISCHARGED**: PROJECT is **cutover-ready**. SECTION is **unchanged: HELD/paused** (now durably, via IaC PR #353), awaiting your CQ-RETURN-3 answer. Reversible/read-only; section lane STAYS PAUSED; this artifact does NOT itself issue the cutover.

## §0. DECISION / STATUS FIRST — §D PROJECT = MEASURED PASS

The §D PROJECT-arm chaos re-gate was executed this phase on a **live SLI** and **PASSED** (verdict doc `CR3-SRE-PHASE-RESCOPED-D-VERDICT-2026-06-04.md` §8.2). RETURN-4's PROJECT disposition ("PASS-pending / SLI dark") is **superseded by a measured PASS**.

- **§D PROJECT = PASS — ratio live-measured 100.0% (243/243).** Server-side AMP `receiver_query_outcome_total{entity_type="project",outcome="success"}=243`; `outcome="server_error"` series **absent** → 243/243 = **100.0%**. A genuine inversion of the prior **86.8% FAIL**. Probe-side `successes=240/success_rate=1.0000` (the 3-call delta is server-observed smoke/health traffic; headline computed 243/243). Cause-disaggregation is **live**: `receiver_query_fallback_cause_total{...cause="data_2xx"}=243`; the three failure causes (`cadence_503|capacity_502|honest_refusal`) returned **empty** → only cause is healthy `data_2xx`.
- **SLI-restore prereq (RETURN-4 §1) DISCHARGED.** PR **#107** (`feat(obs): wire instrument_app for asana`) **MERGED** `2026-06-04T08:36:40Z` (merge SHA `3ff73567…` = current `origin/main` HEAD of the producer repo). Image **`asana:3ff7356`** deployed (ECS task up **08:48 UTC**). `up{job="asana"}` **0 → 1** on `ip-10-0-149-67.ec2.internal:8000`; `scrape_samples_scraped=39` (vs `0` pre-deploy), **9 metric families egressing**. The §1.3 "REFUTED-on-substrate / dark SLI" finding is DISCHARGED.
- **Starvation thesis REFUTED LIVE.** 4-signal CPU read on 2048/8192: CloudWatch ECS CPU peak **9.9% (max 12.5%)**, event-loop lag mean **0.0028s**, thread-semaphore `max=4 / in_use=0 / waiting=0` — all ≪ 85%. The single-worker/0.25-vCPU starvation root cause of the 86.8% FAIL does not recur on the headroom-applied substrate.
- **Content-bound clean.** `content_ok=240`, `content_honest_empty=0`, `content_violations=0` — every 2xx carried the office_phone/vertical/gid contract; zero liveness-masquerade. **Abort-arms NEVER TRIPPED** (probe p99 805.5ms ≪ ALB idle 60s; ALB healthy no flap; 502/5xx=0; `up=1` post-load).
- **DISSOLVE-PROVEN.** The serve-stale (V6) + 2048/8192-headroom paradigm **dissolves the PROJECT bulk-fanout 502 problem without CDC — measured not inferred**. The §D chaos-side precondition of **IC-GATE-7 is DISCHARGED**.
- **SECTION unchanged: HELD.** No §D verdict; not load-driven (measuring section now re-runs the stale-datum trap). Now **durably paused in IaC** (PR #353, open) on top of the live re-pause (`reserved=0` + schedule DISABLED). Still gated on your **CQ-RETURN-3** answer + the T1 knob (#106).

**Evidence grade:** the §D PROJECT PASS is **STRONG** — it is the rite-disjoint, live-AWS-measured chaos verdict (the dgate lane self-gated SLI-LIVE at source and verified deployed-image lineage empirically before scoring). The surrounding synthesis is SRE-authored → **MODERATE**.

## §1. What is now cutover-ready (PROJECT) — and what YOU still own to reach IC-GATE-7

PROJECT is **cutover-ready**: the ≥99% chaos §D verdict is **issued (PASS, 100.0%)**, project rides 24h LKG (`project=86400` unchanged), has no section-lane dependence, and the knob is not in tension for project. **This artifact does NOT itself issue the cutover.** The chaos precondition is discharged; the remaining IC-GATE-7 prongs are **yours + the deliberate IC land sign-off**:

1. **Consumer-QA-green** — your prong. IC-GATE-7 = §D PASS **+** consumer QA green (`LAND-RUNBOOK:369`). The §D PASS discharged the chaos side; QA-green is still required before project cuts over.
2. **#55 arm-granularity UV-P (please confirm):** *"is the #55 repoint flag arm-granular, or all-or-nothing? If all-or-nothing, the arms can't split at the merge boundary."* If #55's flag is all-or-nothing, PROJECT cannot cut independently of SECTION at the merge boundary — confirm before cut.
3. **Deliberate IC land gate** — the cutover is IC-sequenced: IC-GATE-7 → `#55 repoint / Stage-B(project) / Secret-2 decommission`. None of these is fired by this handoff.

## §2. SECTION still needs your call — CQ-RETURN-3 (verbatim)

> **Is 576s SECTION freshness load-bearing for offer-join correctness, or is serve-stale-section at ~30-50 min acceptable as an interim until CDC materialization lands?**

- **(a) accept-interim** → we land PR #106 (section→3000), the re-scoped §D measures BOTH arms on serve-stale, both cut over; section freshness chased by CDC (rnd, off critical path).
- **(b) wait-for-CDC** → section stays HELD, PR #106 moot until CDC lands; **cut PROJECT over alone now.**

You can answer **now, in parallel** — it is independent of our (now-completed) SLI-restore work. SECTION is **durably paused in IaC** this phase: the 08:47:30 satellite deploy un-paused the section warm lane (`reserved=2`, schedule ENABLED — an ABORT-condition violation **by the deploy**, not by the §D run); the SRE main thread **RE-PAUSED** it (`reserved=0` + EventBridge `autom8-asana-cache-warmer-section-schedule` DISABLED, re-verified), and the durable fix — **autom8y-TF PR #353** (`cache_warmer_section` module `reserved_concurrent_executions=0` + rule disabled by default) — is **open/in-flight** so deploys stop re-arming it.

## §3. Knob PR #106 status (gated)

PR **#106** (DRAFT, in `autom8y/autom8y-asana`) sets `FRESHNESS_CONTRACT_MAX_AGE_SECONDS["section"]: 576 → 3000` — the LKG ceiling (`LKG_MAX_STALENESS_MULTIPLIER 10.0 × ttl 300 = 3000s`), so section **joins project on serve-stale**. Explicitly **GATED on CQ-RETURN-3** + a deliberate land gate. Recommended bound **3000** (maximal relief, zero surprise). Project knob unchanged (`project=86400` = 24h, well above the 3000s multiplier ceiling — project reads ride serve-stale/LKG and almost never rebuild).

## §4. ACTION — for the consumer (arch/10x-dev), numbered

1. **Answer CQ-RETURN-3** (a accept-interim / b wait-for-CDC) — via the offer-join-correctness lens. Answerable now, in parallel.
2. **Confirm the #55 arm-granularity UV-P** — arm-granular vs all-or-nothing (gates whether PROJECT can cut independent of SECTION).
3. **Author + run the PRE-SB-1 Section rollback-lever TEST** — your prong; BLOCKS Stage-B(section) independent of the re-gate verdict (detail in §5).
4. **Drive consumer-QA-green toward IC-GATE-7** — the §D chaos precondition is discharged; QA-green is the remaining your-side prong for the project cutover.
5. **Hold the irreversible steps behind the deliberate IC land gate** — #55 repoint stays HELD behind §D PASS + your QA-green (IC-GATE-7); **Secret-2 decommission stays IC-gated.**

## §5. Carry-forward (your prong, unchanged)

- **PRE-SB-1** — the Section rollback-lever TEST: drive `Section.get_df` flag-OFF → assert `emit_fallback_signals(reason=REASON_FLAG_DISABLED, source=SOURCE_SECTION)` → `_get_df_legacy_sdk`. **BLOCKS Stage-B(section)** independent of the re-gate verdict. The H-2 branch is **code-present** at `/Users/tomtenuta/Code/autom8/apis/asana_api/objects/section/main.py:679` (`if _flag_enabled is False:`); the **TEST is the gap**.
- **#55** repoint stays HELD behind the §D PASS + your QA-green (**IC-GATE-7**). **Secret-2 decommission stays IC-gated.**

*RETURN-5 from the autom8y-asana SRE rite, 2026-06-04. AUTHORED-and-delivered (`pending` until accepted). Reversible/read-only; section lane PAUSED; secrets redacted. The §D PROJECT ≥99% chaos verdict is issued (PASS, 100.0%); the cutover itself remains consumer-QA + IC-land gated.*
