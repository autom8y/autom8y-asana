---
type: decision
status: proposed
---

# CR-3 SRE-Phase Re-Scoped §D Verdict — Serve-Stale-Section (V6) Paradigm

- **Date:** 2026-06-04
- **Rite:** SRE (asana satellite)
- **Scope:** §D re-gate of the CR-3 receiver bulk-fanout cutover, **re-scoped** to the serve-stale-section (V6) paradigm per `CR3-FINAL-REGATE-PLAN-2026-06-03.md`
- **AWS:** acct `696318035277` · `us-east-1` · cluster `autom8y-cluster` · service `autom8y-asana-service`
- **Self-ref ceiling:** This is an SRE-authored synthesis of SRE-phase lanes → **MODERATE** ceiling on the synthesis. The PROJECT-arm §D result is the **rite-disjoint STRONG-lift** (live AWS measurement), and applies to the PROJECT arm ONLY.
- **Reversibility:** Read-only. NO merge / terraform apply / deploy / knob-value land / secret op / lambda mutation fired this phase. §B SECTION warm lane STAYS PAUSED.

---

## 0. Live-invariant re-assertion (re-probed at source this pass — two corrections + one API-surface nuance)

| Invariant | Briefing asserted | Live receipt (verbatim, this pass) | Status |
|---|---|---|---|
| origin/main | e57a3cba | `git rev-parse origin/main` → `e57a3cbaa24d5671133daf351b396dfbdce7b0a2` | CONFIRMED |
| Branch HEAD | (implicit) | `git rev-parse HEAD` → `a62fd40117723a2073043addf4164a835a1054ca` (obs-wiring, +1 ahead, **UNDEPLOYED**) | NOTED |
| Running task-def | **:471** | `aws ecs describe-services` → `…/autom8y-asana-service:473`; rollout `COMPLETED`; running=desired=1 | **CORRECTION** — :471 stale-by-2; live = **:473** |
| cpu/mem | 2048/8192 | `describe-task-definition :473` → cpu="2048" mem="8192" | CONFIRMED (headroom intact) |
| Deployed image = origin/main | e57a3cba | `:473` image `…/autom8y/asana:e57a3cb` = origin/main HEAD | CONFIRMED |
| Section lane reserved | =0 | `get-function-concurrency autom8-asana-cache-warmer-section` → `ReservedConcurrentExecutions: 0` | CONFIRMED (see nuance) |
| Section schedule rule | DISABLED | `describe-rule autom8-asana-cache-warmer-section-schedule` → `state:DISABLED`, `cron(0/10 * * * ? *)` | CONFIRMED |
| Knob | project=86400 / section=576 | `config.py:162-165` → project=86400.0, section=576.0 (at e57a3cba) | CONFIRMED |
| A8_VERSION | v1.3.12 | (carried — not re-probed this pass) | UV-P (non-load-bearing) |

**:471→:473 discharge.** The :471 LIVE INVARIANT is **stale-by-2-revisions**. The live running revision is **:473**, carrying the **identical** headroom (2048/8192) and the **correct** origin/main image (`e57a3cb`). Per Lane A: :471 image was `6a2465b`, :473 image is `e57a3cb` — a **benign forward revision** (same headroom, newer image folding in obs-wiring/warmer-section/serve-stale lands). **NOT a regression.** The headroom substrate is intact and current.

**API-surface nuance (re-probe catch).** `aws lambda get-function-configuration` and `describe` return `ReservedConcurrentExecutions: null` for the section warmer; the **authoritative** `aws lambda get-function-concurrency` returns `ReservedConcurrentExecutions: 0`. The lane is hard-paused at **reserved=0** — confirmed via the authoritative API. The `null` on the config object is an AWS API-surface artifact, not an un-pause. **Section lane PAUSED holds.**

---

## 1. §D PROJECT-ARM VERDICT (deliverable 1)

### VERDICT = **PARTIAL** (read-only baseline PASS; live load-injection HELD on a dual gate)

The PROJECT-arm §D re-gate **could not be driven to a load-injected ≥99% satellite/fallback-ratio PASS** this phase, because the criterion's measurement substrate is not readable. The read-only steady-state baseline is **GREEN and consistent with the §D thesis** (project rides 24h LKG-serve → near-zero build pressure → headroom absorbs the rare build), but the headline ≥99% ratio PASS remains **the chaos §D re-gate's to issue once the SLI substrate is restored.**

### Verbatim measured results (Lane A, live AWS, read-only)

| Criterion | Result (verbatim) | Verdict |
|---|---|---|
| **CPU_STARVATION** (the falsified-thesis check) | CPUUtilization avg **~1.28%**, max **~3.06%** over trailing 2h (AWS/ECS, 6×5min buckets) — **near-idle** | **NO STARVATION** (refutes the single-worker/0.25-vCPU starvation regime; the project arm on 2048/8192 + LKG-serve is not CPU-bound) |
| **502 / fallback ratio** (the headline §D criterion) | ELB `HTTPCode_ELB_502_Count` = 1.0+1.0 over 3h (≈1/5min transient health-check noise); target-5XX on green TG = **0** | baseline GREEN; **ratio criterion #1 UNMEASURABLE from EMF** (see §1.3) → ratio **HELD** |
| /health p99 | ~0.44s wall (live: 0.486 / 0.438 / 0.442s incl. TLS) → 200/200/200 | PASS |
| ALB target health | green TG `a8-asana-green` = 1 target `10.0.158.124:8000` **healthy**, no flap (blue TG empty = B/G topology) | PASS |

### Why load-injection was HELD (the dual gate — FALLBACK taken, NOT fabricated)

1. **SLI gate (the binding one):** the §D PASS criterion is a per-arm **satellite/fallback ratio** sourced from the EMF 3-cause split (#98). That metric is **not readable on the deployed substrate** (§1.3). Driving synthetic load with no readable success/fallback ratio would produce a **paradigm-blind datum** — exactly the stale-datum trap §D exists to avoid. Read-only baseline taken instead.
2. **Reversibility gate:** live load-injection against the single prod green target is a deliberate-gate action (chaos §D), not a read-only SRE-phase step.

### 1.3 SLI-readiness sub-finding (Lane C, rite-disjoint live-execution proven) — **REFUTED-on-substrate**

The §D SLI (#98 EMF 3-cause split) is **code-correct but NOT readable on the deployed substrate.**

- **Code present:** `metrics.py:135-157` — Counter `autom8y_asana_receiver_query_fallback_cause_total`, labels `["entity_type","cause"]`, causes `{cadence_503, capacity_502, honest_refusal}` + `data_2xx`; emission at `query.py:580-598`. Per-arm IS the design (`entity_type ∈ {project,section}`).
- **Egress REFUTED:** AMP query `count({__name__=~"autom8y_asana_.+"})` → `result:[]` (ZERO asana app metrics in AMP, ws `ws-26b271ef…`). CloudWatch `autom8y/asana` namespace contains only `autom8y-asana-service-error-count`.
- **Root cause (source-proven this pass):** `instrument_app(app, InstrumentationConfig(service_name="asana"))` — the call that mounts `/metrics` — exists at `main.py:866` **only on HEAD `a62fd401`** (`git grep instrument_app a62fd401` → main.py:48,854,866). On deployed origin/main `e57a3cba` it is **absent** (`git grep instrument_app e57a3cba` → only metrics.py comments :5,:51). The counters register in-process on the default REGISTRY but the scrape target returns nothing.
- **Live proof:** `up{job="asana"}=0`; `max_over_time(up{job="asana"}[3h])=0`; `scrape_samples_scraped{job="asana"}=0` vs `{job="data"}=898`.
- **Fix path:** deploy HEAD `a62fd401` (the obs-wiring commit, +1 ahead) → `/metrics` exposition lights up → ADOT sidecar scrape → AMP remote_write → SLI becomes live-readable → the §D ratio PASS becomes measurable.

> **In-band attestation still works:** `meta.stale_served` (#99) is derived in the HTTP response body (`engine.py:517-522`, `stale_served = freshness_info.freshness != "fresh"`), NOT gated by `/metrics`. It is LIVE on the deployed image. The serve-stale fact is observable in-band today; only the aggregated SLI ratio is dark.

### SECTION arm — **HELD this phase** (explicitly NOT measured)

The SECTION arm is **NOT given a §D verdict this phase** by design. With knob `section=576` + lane-paused, section age (~30-50min under serve-stale) exceeds the 576s ceiling → the cache returns `None` → **forced build → 502 under load** (the T1 knob inversion, §2). Measuring section now would re-run the **82% stale-datum trap** — a paradigm-wrong datum. SECTION is gated on **(T1)** the knob re-think AND **(consumer)** the CQ-RETURN-3 answer. **Held, not failed.**

---

## 2. SECTION-FRAME-AGE PRE-COMPUTE (deliverable 2) — consumer evidence

This is the data the offer-join correctness owner needs to answer CQ-RETURN-3. All source/measurement-anchored.

### What serve-stale-section delivers TODAY (if the knob is lifted off the build path)

- **576s-warm is INFEASIBLE.** The ≤10-min (576s) section warm cadence is **~8× over the achievable inter-warm cadence** for the 34-GID section contract, bounded by the upstream Asana 429/rate-limit ceiling (`ADR-section-10min-x-502-headroom-2026-06-03.md`). The 576s-warm hypothesis is **FALSIFIED** (the SRE-phase thesis correction).
- **Serve-stale-section delivers ~30-50 min frame-age.** Bound by the bulk warmer's heaviest-GID inter-warm cadence (~46 min, `ADR-section-10min-x-502-headroom §B.1`) and the LKG multiplier ceiling (3000s = 50min). Under serve-stale, the section frame is at most ~30-50 min stale and **served immediately from LKG** — no build, no 502.
- **The headroom (2048/8192) absorbs the rare rebuild** the same way it does for project — the §D thesis is paradigm-uniform across both arms once both are on LKG-serve.

### The knob bound that puts section on LKG-serve

| Knob `section` value | Section behavior | Receipt |
|---|---|---|
| **576** (current, deployed) | age > 576 → cache returns `None` → **forced build → 502 under load** | `dataframe_cache.py:540` `.get("section")=576` → `:550 if age>max_age: return None`; knob `config.py:164` |
| **3000** (= multiplier ceiling) | section rides LKG exactly to the multiplier ceiling → **joins project on serve-stale**; maximal relief | `LKG_MAX_STALENESS_MULTIPLIER=10.0` (`config.py:117`) × `DEFAULT_TTL=300` (`config.py:93`) = 3000s; override at `dataframe_cache.py:540-546` |
| **drop the key** | `.get("section")` → None → falls back to multiplier ceiling (3000s) → identical runtime to 3000, but stops declaring a "contract" | `dataframe_cache.py:540` `.get()` default-None → `:547 elif LKG_MAX_STALENESS_MULTIPLIER>0` |

**Consumer-facing read:** serve-stale-section at **~30-50 min** is the realistic interim. The question for the offer-join owner: **is 576s SECTION freshness load-bearing for offer-join correctness, or is ~30-50 min acceptable as an interim until CDC materialization lands?** (This is CQ-RETURN-3; the IC states no preference — see Lane D / §4.)

---

## 3. KNOB-RECALIBRATION PR (deliverable 3) — authored, gated, NOT merged

- **PR:** **#106** (draft) — `https://github.com/autom8y/autom8y-asana/pull/106`
- **Branch:** `feat/section-knob-recalibration` (off origin/main `e57a3cba`), commit `3bc4e275`
- **State:** draft, base=main, `mergeable_state=blocked` (correctly NOT mergeable). *(PR metadata carried from Lane B return; GitHub API rate-limited at synthesis time — `gh api rate_limit` exceeded — so PR state is Lane-B-sourced, marked **UV-P-egress** until re-confirmable.)*
- **The change:** `FRESHNESS_CONTRACT_MAX_AGE_SECONDS["section"]: 576.0 → 3000.0` at `config.py:162-165`, plus rationale comment block and the updated assertion test (`test_calibrated_knob_matches_recalibrated_contract`). `project=86400` unchanged.

### Recommended bound: **(i) `3000.0` (50 min)**

Exactly the LKG multiplier ceiling (`10.0 × 300 = 3000`), so the override is a no-op vs the multiplier → **maximal relief, zero surprise**, and it is a concrete declared value (vs option (iii)'s silent default). Runner-up: **(iii) drop the key** (identical runtime, honest if 576s was never load-bearing). **(ii) ~2760** (pin to ~46-min warm cadence) if the consumer wants the bound pinned to achievable warm cadence.

### Gate (explicit)
The section VALUE is GATED on **(a)** the consumer's CQ-RETURN-3 answer (is 576s load-bearing?) **and (b)** a deliberate land gate. If the consumer chooses **WAIT-for-CDC**, the section arm stays HELD and this value is moot until the CDC R&D lands. **Authored-not-merged; reversible.**

---

## 4. DEPENDENCY GRAPH + GATES (deliverable 4) — from Lane D (IC), source-anchored

Full disposition: `.ledge/decisions/IC-DISPOSITION-cr3-serve-stale-section-sequencing-2026-06-04.md`.

```
                         ┌─────────────────────────────────────────────┐
                         │ RUNNABLE-NOW (no consumer gate)              │
                         │  • §D PROJECT-arm re-gate (chaos)            │
                         │  • SLI restore = deploy HEAD a62fd401        │  ◀── PREREQ for the
                         │    (lights up /metrics → AMP → ratio PASS)   │      ratio criterion
                         │  • Lane C frame-age / Lane A project §D      │
                         └───────────────────┬─────────────────────────┘
                                             │ §D PASS (ratio ≥99%)
                                             ▼
   PROJECT arm ─── decoupled cutover (RECOMMENDED, §4 below) ─── independent of section
                                             │
                                             ▼
                         ┌─────────────────────────────────────────────┐
                         │ CONSUMER-GATED                              │
                         │  • CQ-RETURN-3 answer (576s load-bearing?)  │
                         │  • PRE-SB-1: Section rollback-lever TEST    │ ◀ BLOCKS Stage-B(section)
                         │    (consumer-prong, REGATE-PLAN:106-122)    │   independent of re-gate verdict
                         │  • T1: knob section 576→3000 (PR #106)      │ ◀ PRECONDITION of any section §D run
                         │  • IC-GATE-7 (LAND-RUNBOOK:369)             │   (fires on §D PASS + consumer QA green)
                         │  • #55 repoint / Stage-B(section) /         │
                         │    Secret-2 decommission                    │
                         └───────────────────┬─────────────────────────┘
                                             │ (real fix, OFF critical path)
                                             ▼
                         section → CDC materialization track
                         HANDOFF-sre-to-rnd-cr3-section-cdc-materialization-2026-06-04
                         (status: pending; consumer PRE-ACCEPTED at CQ-5)
```

### Gate table

| Gate | Fires on | Source | This phase |
|---|---|---|---|
| **SLI-restore** (deploy a62fd401) | obs-wiring deploy | main.py:866 (HEAD only) | PREREQ for ratio PASS — **not yet deployed** |
| **§D PROJECT re-gate** | live load + readable SLI | REGATE-PLAN | runnable-now; HELD on SLI-restore this phase |
| **T1 knob** (section 576→3000) | PR #106 land | config.py:164; PR #106 | authored, GATED |
| **PRE-SB-1** (section rollback-lever TEST) | consumer-prong | REGATE-PLAN:106-122 | BLOCKS Stage-B(section); consumer-owned |
| **IC-GATE-7** | §D PASS + consumer QA green | LAND-RUNBOOK:369 | HELD |
| **#55 repoint / Stage-B / Secret-2 decommission** | IC-GATE-7 | LAND-RUNBOOK | HELD |
| **section→CDC** | rnd pickup | HANDOFF-…-cdc-materialization | routed, status:pending, PRE-ACCEPTED at CQ-5 |

### Project-arm decoupled cutover (the recommended option, §4 of IC)
**YES — cut PROJECT over independently.** It rides 24h LKG, has no section-lane dependence, and the knob is not in tension for project (project=86400 unchanged). SECTION waits on the consumer answer + CDC.

**One honest UV-P (cross-repo, unverifiable from the receiver subtree):** if #55's repoint flag is **all-or-nothing**, the arms cannot split at the merge boundary — flagged for consumer confirm.

---

## 5. STRATEGIC READ (deliverable 5) — DISSOLVE vs CDC-blocked

The evidence supports a **SPLIT disposition**, not a single global path:

### PROJECT arm → **DISSOLVE path** (serve-stale + headroom holds) — STRONG-leaning, one gate short
- The CPU_STARVATION thesis is **refuted live** (~1.28% avg / ~3.06% max). The 2048/8192 headroom + 24h LKG-serve means the project arm is **not build-bound**; the rare rebuild is absorbed.
- The serve-stale paradigm (V6) **dissolves** the project bulk-fanout 502 problem without CDC.
- **The one thing standing between "DISSOLVE-supported" and "DISSOLVE-proven" is the SLI substrate** (deploy `a62fd401`) so the ≥99% ratio PASS is *measurable*, not just *baseline-consistent*. → §D PROJECT verdict is **PARTIAL** today, **upgradeable to PASS** after SLI-restore + chaos drive. **The 502 problem is dissolvable for PROJECT.**

### SECTION arm → **CDC-blocked path** (the real fix is out-of-band)
- 576s-warm is FALSIFIED (~8× over the Asana-429 ceiling). Serve-stale-section delivers only ~30-50 min — acceptable as interim ONLY if 576s is not load-bearing.
- If the consumer needs <576s section freshness for offer-join correctness, **no knob dissolves it** — the real fix is **CDC materialization** (routed to rnd, off the CR-3 critical path).
- The knob (T1, PR #106 → 3000) is the **interim mitigation** that takes section off the forced-build/502 path while CDC is built — it makes section *safe* (LKG-serve, no 502) but does not make it *fresh*.

**Net:** CR-3 is NOT one verdict. **PROJECT dissolves now** (serve-stale + headroom; cut it over). **SECTION is CDC-blocked** and rides the interim knob + serve-stale (~30-50 min) until CDC lands. The DISSOLVE path is real for the arm that matters most on the critical path; the CDC-blocked path is correctly isolated to the section arm and routed out-of-band.

---

## 6. RETURN-4 STUB to the consumer (deliverable 6)

> **RETURN-4 — CR-3 §D re-scoped (serve-stale-section / V6): PROJECT clears, SECTION needs your call**
>
> **1. PROJECT arm §D = PARTIAL→PASS-pending.** Steady-state is near-idle (CPU ~1.28% avg / ~3.06% max — the single-worker starvation thesis is **refuted live**), /health p99 ~0.44s, green target healthy, target-5XX=0. The serve-stale + 2048/8192 headroom paradigm **dissolves the project 502 problem**. The ≥99% satellite/fallback-ratio PASS is **baseline-consistent but not yet load-measured**, because the EMF SLI (#98) is dark on the deployed image — the `/metrics` exposition (`instrument_app`) is on HEAD `a62fd401`, **one commit ahead and undeployed**. **Deploy `a62fd401` → SLI lights up → chaos §D drives the ratio PASS.** Recommend **cutting PROJECT over independently** (24h LKG; no section dependence).
>
> **2. SECTION frame-age data (your decision input).** 576s-warm is **infeasible** (~8× over the Asana-429 ceiling — falsified). Serve-stale-section delivers **~30-50 min** frame-age today, served from LKG with no 502 — *if* we lift the knob off the build path. As-deployed (`section=576`), section is forced onto build→502 under load, so it stays **HELD** this phase.
>
> **3. Knob recommendation.** **PR #106** (draft, gated) sets `section: 576 → 3000` (the LKG ceiling) so section **joins project on serve-stale**. Recommended bound **(i) 3000**. Not merged; gated on your answer + a land gate.
>
> **4. ACTION — answer CQ-RETURN-3:** *Is 576s SECTION freshness load-bearing for offer-join correctness, or is serve-stale-section at ~30-50 min acceptable as an interim?*
>   - **(a) accept-interim** → land PR #106 (section→3000), cut both arms on serve-stale, section freshness chased by CDC (rnd, off critical path).
>   - **(b) wait-for-CDC** → section stays HELD; PR #106 moot until CDC lands; cut PROJECT over alone now.
>
> Either way, **PROJECT is ready to cut over independently** once `a62fd401` is deployed and the §D ratio PASS is measured. Open UV-Ps for your confirm: #55 repoint flag arm-granularity (all-or-nothing?), and PR #106 state (re-confirm post rate-limit).

---

## 7. Open UV-Ps carried

1. **#55 repoint flag arm-granularity** — if all-or-nothing, project/section cannot split at the merge boundary (cross-repo, unverifiable from receiver subtree). Consumer confirm.
2. **§D PROJECT ratio PASS** — UNMEASURED until SLI-restore (deploy `a62fd401`) + chaos load drive. The ≥99% PASS is the chaos §D re-gate's to issue.
3. **PR #106 live state** — GitHub API rate-limited at synthesis (`gh api rate_limit` exceeded); PR metadata is Lane-B-sourced. Re-confirm post-reset.
4. **A8_VERSION=v1.3.12** — carried from briefing, not re-probed (non-load-bearing this phase).

---

## Evidence ledger (this-pass source receipts)

- `git rev-parse origin/main` → `e57a3cbaa24d…`; `HEAD` → `a62fd40117…`
- `aws ecs describe-services` → task-def `:473`, rollout COMPLETED, running=desired=1
- `aws ecs describe-task-definition :473` → cpu="2048" mem="8192" image `autom8y/asana:e57a3cb`
- `aws lambda get-function-concurrency autom8-asana-cache-warmer-section` → `ReservedConcurrentExecutions: 0` (authoritative; `get-function-configuration` shows `null` = API-surface artifact)
- `aws events describe-rule autom8-asana-cache-warmer-section-schedule` → state DISABLED, `cron(0/10 * * * ? *)`
- `git show e57a3cba:src/autom8_asana/config.py:162-165` → project=86400.0 section=576.0; `:93` DEFAULT_TTL=300; `:117` LKG_MAX_STALENESS_MULTIPLIER=10.0
- `git show e57a3cba:src/autom8_asana/cache/integration/dataframe_cache.py:533-575` → `.get(entity_type)` contract override; `if age>max_age: return None` (forced-build path)
- `git grep instrument_app a62fd401` → main.py:48,854,866 (HEAD only); `e57a3cba` → metrics.py:5,51 only (no exposition on deployed)
- Lane returns (A project §D / C SLI+frame-age / B knob PR / D IC sequencing) consolidated; AMP/CloudWatch/AWS measurements carried from lanes where live re-probe was rite-disjoint.

---

## 8. SLI-RESTORE + §D PROJECT RE-RUN (2026-06-04)

This section supersedes §1's PARTIAL/HELD disposition for the PROJECT arm. The blocking prerequisite identified throughout §§1–7 — the dark EMF SLI substrate — was discharged by merging and deploying the obs-wiring change (`instrument_app`). With the SLI live, the chaos §D PROJECT load-drive was executed and the headline ≥99% ratio is now **live-measured**, not baseline-inferred.

**Self-ref ceiling reminder:** this synthesis is SRE-authored → **MODERATE**. The live §D PROJECT measurement (up-state, ratio, CPU) is the **rite-disjoint STRONG-lift** — the dgate lane self-gated SLI-LIVE independently at source (did NOT trust prior-stage narrative) and verified the deployed-image lineage empirically before scoring. **Verified at synthesis** (this pass): `git rev-parse origin/main` → `3ff73567394abc54d4ac2214351288f61e67c4e2`; `gh pr view 107` → `state:MERGED`, `mergeCommit.oid:3ff73567…`, `mergedAt:2026-06-04T08:36:40Z`, `mergedBy:tomtenuta`.

### 8.1 SLI-restore deploy (deliverable 1) — SUCCEEDED

| Item | Receipt (verbatim) | Status |
|---|---|---|
| **PR #107 merge** | `state:MERGED`, `merged:true`, `merged_at:2026-06-04T08:36:40Z`, `merged_by:tomtenuta` | CONFIRMED at source |
| **Merge SHA (squash)** | **`3ff73567394abc54d4ac2214351288f61e67c4e2`** | = new origin/main (advanced from `e57a3cba`) |
| **Merge content** | `feat(obs): wire instrument_app for asana` — `api/main.py +16`, `tests/unit/api/test_instrument_app_wiring.py +182`, `uv.lock`, `pyproject.toml` (head `0a195db8` not an ancestor — expected squash, confirmed by src-diff per prior scar) | CONFIRMED |
| **main-Test on `3ff73567`** | `completed \| success` (all 4 shards `success`). Only non-success terminal job = `update-uv-graph`/"Dependency Graph" = `failure` — the independent GitHub dependency-graph submission job, **NOT** part of the deploy-gated Test conclusion | GREEN (deploy-gated Test = success) |
| **Post-#107 image** | **`asana:3ff7356`** built + pushed; new ECS task came up **08:48 UTC** | DEPLOYED |
| **SLI-live: `up{job="asana"}`** | **0 → 1** on `ip-10-0-149-67.ec2.internal:8000` (dgate self-gate; independently confirmed at source) | RESTORED |
| **SLI-live: scrape samples** | `scrape_samples_scraped=39` (vs `0` pre-deploy); **9 metric families egressing** (22 series at sli-lane time → 39 samples / 9 families post-load) | EGRESSING |
| **EMF #98 counter** | `receiver_query_fallback_cause_total{entity_type,cause}` registered in-process AND now exposable; minted real child series under load (§8.2 #2). Empty-at-gate was zero-qualifying-traffic-since-08:48, **NOT** a wiring miss / dark SLI (dgate read `query.py:585-600`, `metrics.py:135-342`; the increment fires for body-parameterized arms `ctx.project_gid is None` on EVERY outcome incl. success `fallback_cause="data_2xx"`) | LIVE |

The §1.3 "REFUTED-on-substrate" finding is hereby **DISCHARGED**: the EMF SLI is no longer dark. `up{job=asana}` 0→1 and exposition is live. The fix path named at §1.3 ("deploy the obs-wiring commit → `/metrics` lights up → ADOT scrape → AMP remote_write → SLI live-readable") executed as predicted.

### 8.2 §D PROJECT-arm verdict (deliverable 2) — **PASS** (all applicable criteria green)

**Load driver / width:** PROJECT arm ONLY — `POST /v1/query/project/rows`, project_gid `1143843662099250` (canonical offer project, warmed S3 parquet), **2 concurrent streams × 40 rpm × 180s = 240 calls**. Content-binding ON (`assert_column_contract=True`; office_phone/vertical/gid contract per #101). Auth: hermes/TokenManager S2S, SA creds from SSM/SM (JWT len=1295). Reused canonical `receiver_bulk_fanout_deploy_gate.py` `_run_arm`/`_one_call`/`_classify_project_content` verbatim, driving PROJECT in isolation via its own functions (the built-in driver hardcodes both arms — STATED). **SECTION arm NOT launched (HELD).** Load driven by the metric's real traffic — NOT manufactured load into a dark SLI (anti-theater fence held).

| Criterion | Receipt (verbatim) | Verdict |
|---|---|---|
| **#1 project satellite-serve ratio ≥99%** (headline) | probe `successes=240/success_rate=1.0000`; server-side AMP `receiver_query_outcome_total{entity_type="project",outcome="success"}=243`, `outcome="server_error"` series **absent (empty)** → **243/243 = 100.0%** | **PASS** |
| **#2 3-cause EMF reads cause** | `receiver_query_fallback_cause_total{entity_type="project",cause="data_2xx"}=243`; `{cause=~"cadence_503\|capacity_502\|honest_refusal"}` **empty** → cause-disaggregation live; only cause = healthy data_2xx | **PASS** |
| **#4 CPU_STARVATION=0 (4-signal)** | `cpu_thread_semaphore_max=4`, `in_use=0`, `waiting=0`; event-loop lag mean **0.0028s**; CloudWatch ECS CPU peak under load **9.9% (max 12.5%)** — all ≪ 85% | **PASS** |
| **#5 singleflight builds_coalesced>0 IF builds occur** | `build_coordinator_semaphore_utilization=0` throughout; no build occurred (all 243 served warm); antecedent did not fire | **N/A — vacuously satisfied** |
| **#7 content-bound (empty/wrong 2xx FAILS)** | `content_ok=240`, `content_honest_empty=0`, `content_violations=0` — every 2xx carried office_phone/vertical/gid contract; zero liveness-masquerade | **PASS** |

**Abort-arm status (§6 / chaos abort gate): NEVER TRIPPED.** CPU max 12.5% (<85%); probe p99 805.5ms (≪ ALB idle 60s); ALB `10.0.149.67` healthy pre/mid/post (no flap); 502/5xx = 0 (= baseline); `up{job=asana}=1` post-load (no crash); smoke pre-flight + 3 mid-flight samples clean.

**Anti-theater (honest ratio):** PROJECT ratio = **100.0% (243/243)** — a genuine inversion of the prior **86.8% FAIL** (whose root cause was single-worker/0.25-vCPU starvation; refuted here by the 4-signal CPU read on 2048/8192).

### 8.3 PROJECT is DISSOLVE-PROVEN — project-decoupled cutover is the next gate (IC-sequenced)

Because §D PROJECT = **PASS** on a **live SLI** (not baseline-inferred), the §5 disposition upgrades:

- **PROJECT arm: DISSOLVE-PROVEN.** §1/§5's "DISSOLVE-supported, one gate short (SLI substrate)" is now **DISSOLVE-PROVEN** — the rite-disjoint STRONG-lift (live AWS measurement) issued the ≥99% ratio PASS (100.0%) with CPU_STARVATION refuted live. The serve-stale (V6) + 2048/8192-headroom paradigm **dissolves** the PROJECT bulk-fanout 502 problem without CDC, **measured not inferred**.
- **Next gate: the project-decoupled cutover** (RECOMMENDED at §4 / IC §4). Cut PROJECT over independently — it rides 24h LKG, has no section-lane dependence, project knob unchanged (86400). This is **IC-sequenced**: fires through **IC-GATE-7** (§D PASS + consumer QA green, `LAND-RUNBOOK:369`) → `#55 repoint / Stage-B(project) / Secret-2 decommission`. The §D PROJECT PASS discharges the chaos-side precondition of IC-GATE-7; the consumer-QA prong + the deliberate land gate remain.
- **Carried UV-P (unchanged):** if #55's repoint flag is **all-or-nothing** (cross-repo, unverifiable from the receiver subtree), the arms cannot split at the merge boundary — consumer confirm required before cut.

### 8.4 Unchanged holds (deliverable 4) — re-affirmed, NOT touched this run

- **SECTION arm: HELD.** No §D verdict; not load-driven. Gated on (T1) knob re-think AND (consumer) CQ-RETURN-3. Measuring section now would re-run the 82% stale-datum trap.
- **Section warm lane: PAUSED holds.** Per the deploy report, the satellite deploy re-overlaid all three warmer lanes at `2026-06-04T08:47:30 UTC` and **un-paused the section lane** (now `reserved=2`, schedule `ENABLED`) — an **ABORT-condition VIOLATION by the deploy**, NOT by this run. The §D PROJECT load-drive did not mutate it (scope-fence binding; dgate reported verbatim, mutated nothing). **The section lane MUST be re-paused** (`reserved_concurrency=0` + EventBridge `autom8-asana-cache-warmer-section-schedule` DISABLED) — flagged as a follow-up remediation, owned by the next deliberate op. Do NOT re-enable; this run did not.
- **Knob #106: consumer-gated.** `section: 576 → 3000` (PR #106, draft) untouched; gated on CQ-RETURN-3 + a land gate.
- **#55 / Stage-B: consumer/CDC-gated.** Untouched.
- **SECTION → CDC: routed to rnd** (`HANDOFF-sre-to-rnd-cr3-section-cdc-materialization-2026-06-04`, status pending, consumer PRE-ACCEPTED at CQ-5). Off the CR-3 critical path.

### 8.5 Updated open items

1. **Section-lane re-pause (DONE) + durable IaC fix (IN FLIGHT):** the 08:47:30 deploy un-paused section (`reserved=2`, schedule ENABLED). **RE-PAUSED by the SRE main thread 2026-06-04** (`put-function-concurrency reserved=0` + `disable-rule autom8-asana-cache-warmer-section-schedule` → DISABLED; re-verified). ROOT CAUSE = a **snowflake pause** (console-only state, not IaC) → every satellite `tf-apply` re-overlays the armed TF default. **DURABLE FIX (in flight): an autom8y-TF PR setting the `cache_warmer_section` module `reserved_concurrent_executions=0` + EventBridge rule disabled by default**, so deploys stop re-arming it (else the 429 storm + knob-inverted 502 recur every deploy). 
2. **#55 repoint flag arm-granularity** (carried) — all-or-nothing? blocks the project-only split at the merge boundary. Consumer confirm.
3. **IC-GATE-7 consumer-QA prong** — the §D PROJECT PASS discharged the chaos precondition; consumer QA green still required before project cutover.
4. **CQ-RETURN-3** (carried) — is 576s SECTION freshness load-bearing? Gates the section interim knob + whether section cuts on serve-stale or waits for CDC.

---

## 9. RE-SCOPED §D BOTH-ARMS RE-GATE (2026-06-04, post-#106) — **BOTH ARMS PASS**; IC-GATE-7 chaos precondition FULLY DISCHARGED

> Supersedes §8.4's "SECTION HELD" disposition. After CQ-RETURN-3=(a) accept-interim (consumer RETURN-3) and the durable-first land, the section arm was re-scoped onto serve-stale (knob 3000) and the §D was re-run measuring BOTH arms. Verdict: **PASS_WITH_FOLLOWUP**, rite-disjoint-verified at source.

### 9.1 State change since §8 (durable-first executed)
- **#353 (durable section pause) MERGED** to autom8y/autom8y main (`schedule_enabled=false` + `reserved_concurrency=0` on the `cache_warmer_section` module) — §8.5 item 1's "durable IaC fix in flight" is now **LANDED**. Trap-4 neutralized: future satellite tf-applies compute reserved=0 (no re-arm).
- **#106 (section 576→3000) MERGED + DEPLOYED** — image `asana:28ae50b` on ECS task-def `autom8y-asana-service:477`; section knob `FRESHNESS_CONTRACT_MAX_AGE_SECONDS["section"]=3000.0` live. The section lane stayed `reserved=0` + DISABLED through the entire deploy (durable-first held; no re-arm).
- **CQ-RETURN-3 = (a) accept-interim** (consumer RETURN-3, source-cross-checked): 576s section freshness NOT load-bearing (offer-join rests on the project-frame office_phone/vertical contract; sections column-exempt). **UV-P #2 = all-or-nothing** flag → a UNIFIED both-arms cut is sufficient (no arm-granular work needed).

### 9.2 §D both-arms verdict = **PASS_WITH_FOLLOWUP** (rite-disjoint chaos run + disjoint observability re-read)
| Arm | Ratio (server-side AMP) | Dispositive | CPU 4-signal |
|---|---|---|---|
| **PROJECT** (re-confirm) | `receiver_query_outcome_total{project,success}=480` / 480 = **100.0%** (server_error series provably absent fleet-wide) | `data_2xx=480`; `content_violations=0` | peak ~12% / max ~18%; semaphore 4/0/0 |
| **SECTION** (new arm, serve-stale) | `{section,success}=484` / 484 = **100.0%** | **`capacity_502=0` (dispositive, verified 3 ways)**; `serving_stale_total{section}=458` genuinely exercised (all serves in the (900s,1800s] staleness band — true LKG, not fresh masquerade); `lkg_serve_age` le=3000 (458) == +Inf (458) == _count → zero serves >3000s ceiling | peak ~14%; semaphore 0/0 |

The serve-stale (V6) + 2048/8192-headroom paradigm **dissolves the SECTION bulk-fanout 502 — measured, not inferred** — including under **A3 both-arms-concurrent** load. Both arms DISSOLVE-PROVEN.

**Disjoint corroboration (the STRONG-lift):** a rite-disjoint observability re-read independently re-queried live AMP/CloudWatch — every dispositive number CONFIRMED at source, **zero mismatch, zero unreadable**, process did NOT restart (counters carry the run totals), anti-theater satisfied (counters empty pre-load → minted real child series under the run; `up{job=asana}=1` throughout). Raw capture: `.sos/wip/chaos/crg3_dual_arm_raw_capture.json`; runbook: `.sos/wip/chaos/CR3-DUAL-ARM-REGATE-RUNBOOK-2026-06-04.md`.

### 9.3 The one boundary flag — event-loop-lag HEADROOM_FOLLOWUP (does NOT block the gated cutover)
Under **A3 compound load only** (both arms 2×40rpm concurrent), event-loop-lag p99 transiently hit **0.9475s** (~1.8× the 0.5s internal guard) for ~2 min @11:36Z, then self-recovered to 0.005s. **Zero downstream impact** — ALB `ELB_502=0`/`5XX=0` (positive-control-verified: the 502 metric fired 9× elsewhere in 24h but NONE in the run window), host continuously healthy/no-flap, real 2xx flowed. Root: **single-uvicorn-worker event-loop saturation** — NOT CPU (peak ~18% vs 85% guard, ~66pt headroom) and NOT thread-pool (semaphore waiting `max_over_time[60m]=0`). Disposition: **HEADROOM_FOLLOWUP, blocks_cutover=False.** Route to Platform Engineer for a compound-load headroom test (>2×40rpm/arm) + a possible multi-worker/async-offload lift **before full-rate both-arms production**; the single-fault (A1/A2) ell-lag stayed ≤0.45s (under guard), so it does not block the gated project-first cutover.

### 9.4 IC-GATE-7 — both halves GREEN; cutover bundle HELD for the deliberate sign-off
- **Chaos half: DISCHARGED** — §D PROJECT PASS (§8.2) + §D SECTION PASS (§9.2), both on a live SLI, disjoint-verified.
- **Consumer half: confirmed** — consumer-QA-green (249 passed, ruff clean) + PRE-SB-1 (commit `14586df8`, 2/2) per RETURN-3, cross-checked rite-disjoint.
- **Next = the deliberate IC sign-off** of the irreversible cutover bundle `{#55 repoint / Stage-B(project) / Secret-2 decommission}`. **HELD — none fired.** The UV-P (all-or-nothing flag) is satisfied for a unified both-arms cut; the ell-lag item is a full-rate caveat, not a project-first blocker. Secret-2 decommission stays sequenced after the task-#73 baked-.env SPOF.

*§9 recorded 2026-06-04 by the SRE main thread. Rite-disjoint chaos verdict + disjoint observability re-read. Reversible/read-load; section lane stayed PAUSED throughout (re-confirmed at source); irreversible cutover bundle untouched.*
