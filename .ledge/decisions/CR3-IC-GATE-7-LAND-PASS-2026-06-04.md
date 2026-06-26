---
type: decision
status: proposed
date: 2026-06-04
rite: SRE (asana satellite) — Incident Commander land pass
initiative: cr3-clean-break-cutover
evidence_grade: moderate   # SRE-authored synthesis → MODERATE ceiling. STRONG-lift items are the rite-disjoint live chaos measurement (§D both-arms PASS) + consumer-corroborated QA/PRE-SB-1, cited at source inline.
reversibility: READ-ONLY ASSEMBLE-AND-PRESENT. This artifact mutates NOTHING operational. The irreversible cutover bundle stays HELD. No #55 merge, no Stage-B, no Secret-2 decommission, no flag flip fired by this pass.
---

# CR-3 IC-GATE-7 — LAND PASS (ASSEMBLE-AND-PRESENT)

> **This document does not execute the cutover. It assembles the runbook and presents the
> irreversible bundle for the deliberate human/IC sign-off.** Everything below STAYS HELD until
> the operator/IC signs the §6 gate. Firing is a human decision; this runbook is its dossier.

- **AWS:** acct `696318035277` · `us-east-1` · cluster `autom8y-cluster` · service `autom8y-asana-service`
- **Authored by:** SRE main thread acting as Incident Commander (war-room close → land coordination).
- **Self-ref ceiling:** SRE-authored synthesis = **MODERATE**. The §D both-arms chaos PASS is the
  rite-disjoint **STRONG-lift** (live AWS measurement, disjoint observability re-read); the consumer
  half (QA-green + PRE-SB-1) is consumer-corroborated. Both cited at source below.

---

## 0. Live substrate re-confirmation (re-probed at source THIS pass — one drift correction)

| Invariant | Briefing asserted | Live receipt (verbatim, this pass) | Status |
|---|---|---|---|
| origin/main | (briefing implied prior refs) | `git rev-parse origin/main` → `28ae50b8666cc0b131af8d803f2fca0f42796662` | **CORRECTION** — advanced past `e57a3cba`/`3ff73567` to `28ae50b8` (the #106 merge) |
| Deployed commit | image `asana:28ae50b` | `28ae50b8` = `feat(cache): recalibrate section freshness bound 576->3000 (GATED on CQ-RETURN-3) (#106)` (`git log --oneline -1 28ae50b8`) | CONFIRMED — origin/main HEAD == deployed image lineage |
| Section knob | `section=3000` live | `git show 28ae50b8:src/autom8_asana/config.py:160-167` → `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` block, section bound recalibrated 576→3000 at the deployed commit | CONFIRMED at deployed commit |
| ECS task-def | `:477` (cpu2048/mem8192, COMPLETED) | raw-capture t0 `autom8y-asana-service:477`, rollout `COMPLETED`, running=desired=1, image `…/autom8y/asana:28ae50b`, cpu="2048" mem="8192" | CONFIRMED (`crg3_dual_arm_raw_capture.json` t0_go_checklist) |
| Section warm lane | reserved=0 + EventBridge DISABLED | raw-capture t0: `reserved_concurrent_executions:0` (authoritative `get-function-concurrency`) + `autom8-asana-cache-warmer-section-schedule:DISABLED`; durable via autom8y/autom8y #353 | CONFIRMED — PAUSED holds (durable IaC landed) |
| #55 (consumer repoint) | HELD, not merged | `gh pr view 55 --repo autom8y/autom8` → `state:OPEN`, `mergeable:MERGEABLE`, head `09e0f64b270fc504b9f5d2ce57d32afd41347fde`, base `main` | CONFIRMED — open + mergeable, NOT merged |
| A8_VERSION | v1.3.12 | carried from briefing, not re-probed | UV-P (non-load-bearing) |

> **Drift correction (the only one).** The briefing's substrate-state line carries `e57a3cba` as a prior
> anchor; the `CR3-SRE-PHASE-RESCOPED-D-VERDICT` §0 git table is **pre-#106-merge and now stale**. The
> live chain is `e57a3cba → 3ff73567 (#107 obs-wiring) → 28ae50b8 (#106 section knob 576→3000)`. The
> briefing's image `asana:28ae50b` and `knob[section]=3000 live` are **correct at source**; only the
> §D-VERDICT §0 SHA snapshot is stale. The §D-VERDICT §9 (both-arms re-gate) was authored AGAINST the
> correct `28ae50b8` substrate — so the GREEN-half evidence is sound. Recorded for IC awareness; not a blocker.

---

## 1. IC-GATE-7 PRECONDITIONS CHECKLIST — both halves GREEN (cited at source)

| # | Precondition | Status | Source receipt (verified this pass) |
|---|---|---|---|
| **1** | **Chaos half — §D PROJECT PASS** | **GREEN** | `CR3-SRE-PHASE-RESCOPED-D-VERDICT-2026-06-04.md` §8.2 — PROJECT 243/243 = 100.0% on a LIVE SLI; `data_2xx=243`; CPU 4-signal (semaphore 4/0/0, ell 0.0028s, CPU peak 12.5%); content_violations=0; abort-arms never tripped. |
| **2** | **Chaos half — §D both-arms re-gate (PROJECT+SECTION)** | **GREEN** | `…§D-VERDICT` §9.2 + `crg3_dual_arm_raw_capture.json` — PROJECT 480/480=100% + SECTION 484/484=100%; SECTION `capacity_502=0` **dispositive** (verified 3 ways); `serving_stale_total{section}=458` genuinely exercised (all serves in the (900s,1800s] band, ≤3000s ceiling, zero breach); rite-disjoint observability re-read CONFIRMED every dispositive number at source, zero mismatch. |
| **3** | **Chaos half — anti-theater fence** | **GREEN** | raw-capture: `up{job=asana}=1` throughout; counters EMPTY pre-load → minted REAL child series under the run (outcome/cause/serving_stale/lkg_age 0→minted on actual 2xx); knob=3000 resolved at deployed commit `28ae50b8` (NOT inferred). |
| **4** | **Consumer half — QA-green** | **GREEN** | RETURN-3 §5 (`HANDOFF-autom8-to-asana-sre-cr3-consumer-return-3-2026-06-04.md`) — full battery **249 passed**, 0 failures; `ruff check` clean; resolver-auth contract suite 12/12; content-binding parity harness STRONG-PASS (EXACT 0-drop/0-extra membership, `path_ledger==['satellite']` false-pass guard). |
| **5** | **Consumer half — PRE-SB-1 Section rollback-lever test** | **GREEN** | RETURN-3 §4 — commit `14586df8`, `tests/apis/asana_api/objects/section/test_get_df_flag_rollback.py`, **2/2 passing**: flag-OFF forces legacy SDK + skips satellite; config-read-raises preserves satellite attempt (locks `is False`-not-`not` semantics). DISCHARGES the BLOCKS-Stage-B(section) prong consumer-side. |
| **6** | **CQ-RETURN-3 ANSWERED** | **GREEN = (a) accept-interim** | RETURN-3 §2 — 576s SECTION freshness NOT load-bearing for offer-join (offer-join rests on PROJECT-frame `office_phone`+`vertical`, `offer_holders/main.py:56`; sections column-EXEMPT, `section/main.py:789`). → both arms ride serve-stale; section freshness chased by CDC off the critical path. |
| **7** | **Substrate landed** | **GREEN** | §0 above — image `28ae50b`/`:477`, cpu2048/mem8192 rollout COMPLETED; section knob=3000 live; creds-IaC #343 applied; section warm lane durably PAUSED (#353). |
| **8** | **UV-P #2 (#55 flag arm-granularity) resolved** | **GREEN = all-or-nothing → unified cut sufficient** | RETURN-3 §3 — both chokepoints read the single global `satellite_get_df_enabled` (`project/main.py:1620`, `section/main.py:674`); tri-state exists but get_df does not call it. Since CQ-RETURN-3=(a), both arms move to serve-stale together → a UNIFIED both-arms cut is sufficient; no arm-granular work required. |
| **9** | **Prior open items discharged** | **GREEN** | Durable section pause LANDED (#353); section knob LANDED (#106 → `28ae50b8`); SLI-restore LANDED (#107 → `3ff73567`); CQ-RETURN-3 ANSWERED (#6). |

**Verdict on preconditions: ALL NINE GREEN.** The chaos half is DISCHARGED (both arms PASS on a live SLI,
disjoint-verified); the consumer half is confirmed (QA-green + PRE-SB-1 + CQ-RETURN-3=(a)). The ONLY thing
remaining is the deliberate IC sign-off of the irreversible cutover bundle (§2).

> **One carried caveat (does NOT gate the project-first cut):** the §9.3 ell-lag HEADROOM_FOLLOWUP — see §4.

---

## 2. THE IRREVERSIBLE CUTOVER BUNDLE (the only thing remaining) — SEQUENCED, HELD

> **HELD. None of the three steps below has fired.** This section lays out the sequence, the actor who
> fires each, and the irreversibility class. **The all-or-nothing flag is SUFFICIENT for a unified
> both-arms cut** because BOTH arms PASS §D (precondition #2/#8). Sequence is authoritative per
> `CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md` step-j + §2 sequencing table.

```
  STEP 1 ── #55 repoint (consumer, autom8y/autom8)            [IRREVERSIBLE — cutover begins]
            flip global `satellite_get_df_enabled` (one bool) → BOTH arms route to satellite/serve-stale
            + repoint resolver secret pointer → authoritative store (Secret 1)
            head 09e0f64b · base main · OPEN + MERGEABLE
                    │
                    ▼   (project-first soak window — §5; section rides serve-stale knob=3000)
  STEP 2 ── Stage-B (project) — fallback retirement              [IRREVERSIBLE — removes legacy fallback]
            retire the legacy-SDK fallback for the PROJECT arm; PROJECT now satellite-only
            gated BEHIND #55 live + the soak abort-criteria clean (§5)
                    │
                    ▼   (AFTER #55 repoint is live-verified)
  STEP 3 ── Secret-2 decommission                               [IRREVERSIBLE — destroys credential]
            sequenced AFTER the task-#73 baked-.env SPOF is resolved (env-collision on
            ASANA_RESOLVER_CLIENT_SECRET, Dockerfile:294). Secret 2 is ACTIVELY CONSUMED
            (LastAccessedDate 2026-06-03) — decommission ONLY after #55 repoint is live-verified.
            #343 declares the client_id-drift alarm, NOT the decommission. NOT a same-window step.
```

### 2.1 Step detail + actor

| Step | What fires | Who fires it | Irreversibility | Source |
|---|---|---|---|---|
| **1 — #55 repoint** | Merge PR autom8y/autom8 **#55** (head `09e0f64b`): flips the single global `satellite_get_df_enabled` (`satellite_config.py:175`) **+** repoints the resolver secret pointer to the authoritative store. A **UNIFIED both-arms cut** (flag is all-or-nothing; both arms PASS §D so this is sufficient). | **Consumer (autom8 10x-dev)**, on IC sign-off. Pre-merge gate: consumer QA-adversary re-gate green on main + live monolith auth path fetches Secret 1 (HTTP 200), not Secret 2. | **IRREVERSIBLE** (cutover begins; rollback = flag-OFF lever, §3). | RETURN-3 §3/§6; `CR3-COORDINATED-LAND-RUNBOOK` step-j (L296-312). |
| **2 — Stage-B (project)** | Retire the legacy-SDK fallback for the PROJECT arm (PROJECT becomes satellite-only). | **Consumer (autom8)**, on IC sign-off, **gated behind** #55 live + clean soak (§5). | **IRREVERSIBLE** (removes the fallback path). | `CR3-FINAL-REGATE-PLAN` §7 (PASS → 7d soak → Stage-B, human/IC-gated); `CR3-COORDINATED-LAND-RUNBOOK` §0/§2. |
| **3 — Secret-2 decommission** | Decommission resolver client Secret 2. | **IC/Platform**, **AFTER** #55 repoint live-verified AND task-#73 baked-`.env` SPOF resolved. | **IRREVERSIBLE** (credential destroyed). | `CR3-COORDINATED-LAND-RUNBOOK` §2 table (L343): IC-gated, sequenced with task #73, `Dockerfile:294`, Secret 2 actively consumed. |

> **Secret-2 ordering is load-bearing.** Secret 2 is still actively consumed (`LastAccessedDate=2026-06-03`)
> and there is a task-#73 baked-`.env` SPOF: the env var `ASANA_RESOLVER_CLIENT_SECRET` is baked at
> `Dockerfile:294`. Decommissioning Secret 2 before that SPOF is resolved AND before #55 repoint is
> live-verified would strand the live auth path. **Step 3 is NOT a same-window action with steps 1–2.**

---

## 3. ROLLBACK LEVERS — per cutover step

| Cutover step | Rollback lever | How it reverses | Tested? | Source |
|---|---|---|---|---|
| **Step 1 — #55 repoint** | **PRE-SB-1 flag-OFF lever** | Drive `satellite_get_df_enabled` **OFF** → both `Section.get_df` and `Project.get_df` route to the legacy SDK path (satellite skipped before attempt). Surgical, no redeploy of the receiver. | **YES — 2/2** | PRE-SB-1 commit `14586df8`; H-2 branch `section/main.py:679`; project branch `project/main.py:1620`. Test: flag-OFF forces legacy SDK + emits `REASON_FLAG_DISABLED` + does NOT call `fetch_section_rows`. |
| **Step 1 — #55 repoint** (safety net) | **serve-stale + section-paused safety net** | Even without a flag flip, the receiver rides LKG: PROJECT on 86400s, SECTION on 3000s. No build pressure under load (§D measured: 0 builds, `capacity_502=0`). Section warm lane stays PAUSED (reserved=0 + DISABLED, durable #353) so no 429-storm/knob-inverted-502 recurs. | live (measured §D) | `…§D-VERDICT` §9.2; #353 (durable pause); knob=3000 at `28ae50b8`. |
| **Step 2 — Stage-B (project)** | **Flag-OFF re-enables fallback path before retirement is irreversible** | Pre-Stage-B, the flag-OFF lever restores legacy fallback. Stage-B must NOT fire until PRE-SB-1 is green (it is) AND the soak abort-criteria are clean (§5). | **YES — 2/2** (lever); soak-gated | `CR3-FINAL-REGATE-PLAN` §1 (PRE-SB-1 BLOCKING precondition; Stage-B must not trust surgical rollback until PRE-SB-1 green). |
| **Step 3 — Secret-2 decommission** | **No clean rollback once destroyed → mitigate by ordering** | Irreversible by nature. Mitigation = sequence AFTER #55 repoint live-verified (Secret 1 serving 200) + task-#73 SPOF resolved; #343 drift alarm gives early warning of a client_id mismatch BEFORE decommission. | ordering-gated | `CR3-COORDINATED-LAND-RUNBOOK` §2 (L343); #343 (drift alarm). |

**Net rollback posture:** Steps 1–2 are **reversible via the tested (2/2) flag-OFF lever** plus the
serve-stale/section-paused safety net. Step 3 is the genuinely irreversible one — its protection is
**sequencing discipline**, not a rollback lever, which is why it is sequenced last and behind the
task-#73 SPOF.

---

## 4. THE ELL-LAG HEADROOM_FOLLOWUP CAVEAT (§9.3) — full-rate caveat, NOT a project-first blocker

**What surfaced.** Under **A3 compound load only** (both arms 2×40rpm concurrent), event-loop-lag p99
transiently hit **0.9475s** (~1.8× the 0.5s internal guard) for ~2.5 min @11:36Z, then **self-recovered**
to 0.005s by 11:37:30Z. **Zero downstream impact** — ALB `ELB_502=0`/`5XX=0` (positive-control-verified:
the 502 metric fired 9× elsewhere in 24h but NONE in the run window), host continuously healthy/no-flap,
real 2xx flowed at 100% ratio, `up{job=asana}=1` throughout, build_coordinator=0.

**Root cause.** **Single-uvicorn-worker event-loop saturation** — NOT CPU (peak ~18% vs 85% guard,
~66pt headroom) and NOT thread-pool (semaphore waiting `max_over_time[60m]=0`). The single-fault arms
(A1/A2) kept ell p99 ≤0.45s (within guard).

**Disposition: `HEADROOM_FOLLOWUP, blocks_cutover=False`.**
- It does **NOT block the gated project-first cutover** — the single-fault project arm (A1) ell p99 stayed
  0.365s, well under the 0.5s guard; PROJECT is DISSOLVE-PROVEN at single-fault width.
- **Route to Platform Engineer** for a compound-load headroom review (>2×40rpm/arm) + a possible
  multi-worker / async-offload lift **BEFORE full-rate both-arms production**.

**How it folds into the sequencing** (drives the §5 ordering):
```
  project-first cut (#55, unified flag flip; section rides serve-stale knob=3000)
        → 7-day S7 soak (project at production rate; section on LKG, low traffic)
        → Platform Engineer compound-load headroom review (the §9.3 ell-lag follow-up)
        → section/full-rate both-arms production (only after the headroom review clears)
```
The unified #55 flip routes both arms, but production RATE ramps project-first; section stays on its
low-traffic serve-stale path until the Platform headroom review clears the compound-load ceiling.

---

## 5. S7 7-DAY SOAK → STAGE-B PLAN + abort/rollback criteria

**Plan (per `CR3-FINAL-REGATE-PLAN-2026-06-03.md` §7 outcome routing — PASS → 7-day S7 soak → Stage-B, human/IC-gated):**

1. **Enter soak** the moment Step 1 (#55 repoint) is live-verified (Secret 1 serving 200; both arms routing to satellite/serve-stale).
2. **Soak duration:** 7 days, PROJECT at production rate, SECTION on LKG/low-traffic (serve-stale knob=3000).
3. **Soak instrumentation (live SLI, restored via #107):** watch the #98 3-cause EMF split per arm:
   `receiver_query_outcome_total` ratio ≥99%, `receiver_query_fallback_cause_total{cause="capacity_502"}=0`
   (section dispositive), `serving_stale_total{section}` all ≤3000s, CPU ≪85%, event-loop-lag p99 (the §9.3
   watch item) under compound, ALB 502 not above baseline, `up{job=asana}=1`.
4. **Soak exit → Stage-B (project):** clean 7-day soak + PRE-SB-1 green (it is) → Stage-B fires on a
   **deliberate human/IC sign-off** (not automatic).

**Abort / rollback criteria DURING soak** (any single trigger → halt the ramp, pull the flag-OFF lever, do NOT proceed to Stage-B):

| Trigger | Action |
|---|---|
| Per-arm serve ratio < 99% sustained | Flag-OFF rollback (§3); iterate; no Stage-B. |
| `capacity_502 > 0` sustained (section dispositive) | Flag-OFF rollback; the knob/lane is mis-calibrated; recede. |
| section serve age > 3000s (ceiling breach) | Flag-OFF rollback; re-examine knob/LKG. |
| ECS CPU > 85% sustained OR `cpu_thread_semaphore_waiting > 0` sustained | Flag-OFF rollback; route to Platform (headroom). |
| event-loop-lag p99 > 0.5s sustained under production rate (the §9.3 watch item) | Hold the full-rate ramp; route to Platform headroom review BEFORE proceeding; do NOT advance section to full rate. |
| ALB 502 above the pre-cut baseline OR target flap | Flag-OFF rollback; investigate. |
| `up{job=asana}` → 0 or task replacement churn | Flag-OFF rollback; incident. |

> **ABORT ≠ FAIL.** An abort means the substrate became unsafe → recede + re-land + re-gate, no Stage-B.
> A clean-miss FAIL (ratio <99% on a safe substrate) → iterate the lever, no Stage-B. Both block Stage-B.

---

## 6. THE DELIBERATE SIGN-OFF GATE — the precise decision the operator/IC must make

> **This runbook PRESENTS the cutover. It does not EXECUTE it.** Firing the bundle is the **HUMAN/IC
> decision.** Everything stays HELD until the operator/IC signs off below. Nothing in this artifact has
> mutated operational state.

**The decision before the IC is binary, with a defined sequence on the GO branch:**

- **GO (fire the cutover):** authorize the consumer to **merge #55** (unified both-arms flag flip +
  resolver secret repoint) → enter the **7-day S7 soak** (project-first rate) → on clean soak +
  Platform headroom review clearing the §9.3 ell-lag compound caveat, authorize **Stage-B (project)** →
  and, separately and last, **Secret-2 decommission** ONLY after #55 repoint is live-verified AND the
  task-#73 baked-`.env` SPOF (`Dockerfile:294`) is resolved.
- **HOLD (do not fire):** the substrate stays exactly as-is — both arms ride serve-stale on the current
  deployed image (`28ae50b`/`:477`), section warm lane stays durably PAUSED, #55 stays open-not-merged,
  Secret 2 stays live. No reliability degradation from holding (the receiver is steady-state near-idle).

**What the IC is signing that they have weighed:**
1. Both halves of IC-GATE-7 are GREEN (§1, all nine preconditions) — chaos both-arms PASS on a live SLI,
   disjoint-verified; consumer QA-green + PRE-SB-1 + CQ-RETURN-3=(a).
2. The cutover is a **unified both-arms cut** (all-or-nothing flag is sufficient because both arms PASS §D).
3. Rollback is the **tested (2/2) flag-OFF lever** + serve-stale/section-paused safety net for steps 1–2;
   Secret-2 (step 3) is protected by **sequencing**, not rollback, and stays last.
4. The **§9.3 ell-lag HEADROOM_FOLLOWUP** is a **full-rate caveat routed to Platform**, NOT a project-first
   blocker — the full-rate both-arms ramp waits on the Platform compound-load headroom review.

**Sign-off line (to be completed by the operator/IC — this runbook does not fill it):**

```
IC-GATE-7 DECISION: [ GO | HOLD ]   Signed: __________   Date: __________
  If GO:  Step-1 #55 merge authorized → soak entry → (headroom review) → Stage-B authorized → Secret-2 (sequenced last)
  If HOLD: substrate remains as-is; bundle stays HELD; re-present when conditions change.
```

---

## 7. Reversibility attestation (this pass)

Read-only ASSEMBLE-AND-PRESENT. **No merge / terraform apply / deploy / knob-value land / secret op /
lambda mutation / flag flip fired this pass.** The section warm lane stays PAUSED (re-confirmed at source,
§0). The irreversible cutover bundle `{#55 repoint / Stage-B / Secret-2 decommission}` is **untouched and
HELD**. No secret VALUES printed (SecretId names / SSM-path constants / JWT length only). Every platform
claim above carries a file:line / SHA / live-AMP receipt verified at source this pass (default-to-REFUTED;
the one drift correction — stale §D-VERDICT §0 SHA snapshot — is recorded in §0, not buried).

## 8. Evidence ledger (this-pass source receipts)

- `git rev-parse origin/main` → `28ae50b8666cc0b131af8d803f2fca0f42796662`; `git log --oneline -1 28ae50b8` → `feat(cache): recalibrate section freshness bound 576->3000 (GATED on CQ-RETURN-3) (#106)`
- `git show 28ae50b8:src/autom8_asana/config.py:160-167` → section bound recalibrated 576→3000 at deployed commit
- `gh pr view 55 --repo autom8y/autom8` → `state:OPEN`, `mergeable:MERGEABLE`, head `09e0f64b270fc504b9f5d2ce57d32afd41347fde`, base main
- `crg3_dual_arm_raw_capture.json` — t0 (`:477`/`28ae50b`/2048-8192, rollout COMPLETED, up=1, section reserved=0+DISABLED), A1 PROJECT 480/480, A2 SECTION 484/484 capacity_502=0, A3 compound PASS-with-flag (ell p99 0.9475s self-recovered), VERDICT BOTH ARMS PASS
- `CR3-SRE-PHASE-RESCOPED-D-VERDICT-2026-06-04.md` §8.2 (PROJECT 243/243), §9.2 (both-arms PASS), §9.3 (ell-lag HEADROOM_FOLLOWUP), §9.4 (IC-GATE-7 both halves green)
- `HANDOFF-autom8-to-asana-sre-cr3-consumer-return-3-2026-06-04.md` §2 (CQ-RETURN-3=(a)), §3 (UV-P #2 all-or-nothing), §4 (PRE-SB-1 14586df8, 2/2), §5 (QA-green 249 passed), §6 (IC-GATE-7 staged)
- `CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md` step-j (L296-312, #55 merge sequence) + §2 table (L343, Secret-2 IC-gated + task-#73 + Dockerfile:294)
- `CR3-FINAL-REGATE-PLAN-2026-06-03.md` §1 (PRE-SB-1 BLOCKING precondition), §7 (PASS → 7d S7 soak → Stage-B), §6 (abort criteria)

---

*CR3-IC-GATE-7 land pass assembled 2026-06-04 by the SRE main thread acting as Incident Commander.
ASSEMBLE-AND-PRESENT only — the irreversible cutover bundle is HELD for the deliberate human/IC sign-off
(§6). This artifact mutated nothing operational. Both halves of IC-GATE-7 are GREEN at source.*
