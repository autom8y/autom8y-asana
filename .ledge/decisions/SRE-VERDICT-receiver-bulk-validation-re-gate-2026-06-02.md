---
type: decision
status: accepted
---

# SRE-VERDICT (TERMINAL) — Receiver Bulk Fan-out Re-Gate (Phase 4)

- **Date**: 2026-06-02 (Phase 4 re-gate, terminal)
- **Author**: incident-commander (SRE rite) — terminal adjudicator. Resilience-axis evidence produced by the chaos-engineer gameday; ≥99%-axis evidence produced by the rite-disjoint observability SLI audit.
- **Posture**: DEFAULT-TO-REFUTED. Burden on the receiver to clear ALL gate conjuncts under honest measurement.
- **Initiative**: receiver-bulk-fanout-integration-readiness — Phase 4 re-gate of the fix package (PRs #92 app-code, #313 TF).
- **Supersedes adjudication of**: `.ledge/decisions/SRE-VERDICT-receiver-bulk-validation-2026-06-02.md` (the original 86.8%/60.4% FAIL). That verdict pinned the root cause; this one adjudicates the fix.
- **Inputs adjudicated**:
  - 10x-dev → sre re-gate handoff: `.sos/wip/handoffs/HANDOFF-10x-dev-to-sre-receiver-bulk-regate-2026-06-02.md` (VG-001..006, reactivation hook).
  - Chaos gameday blast-radius declaration: `.sos/wip/chaos/BLAST-RADIUS-DECLARATION.md` (cpu=1024 :453 before/after, abort criteria).
  - The rite-disjoint observability SLI audit (VG-001 deploy-order artifact diagnosis + VG-004 warm-set under-count).
- **One-line**: The targeted fix WORKED on the axis it targeted (resilience), but two REAL, newly-surfaced defects (warmer convergence + warm-set under-count) plus a deploy-durability blocker keep the ≥99% honest certification — and therefore CR-3 — BLOCKED.

---

## TERMINAL VERDICT

Three-part split verdict. The single "FAIL/PASS" frame is inadequate — per Cook 1998 [II:SRC-001 STRONG] and Reason 1997 [II:SRC-003 STRONG], the system has multiple independent axes and they did not resolve together.

| Axis | Verdict | Grade | Meaning |
|------|---------|-------|---------|
| **Resilience (RECV-BULK-001)** — the original FAIL root cause | **RESOLVED** | STRONG | The event-loop-stall → UnHealthy → ECS-replacement → ELB-502 cascade is GONE at cpu=1024 + offload + Semaphore(4). Decisive live-prod before/after, ≥2-stream. |
| **≥99% honest over the real 34-GID workload** | **NOT CERTIFIED** | REFUTED / incomplete | Blocked by two REAL defects (warmer convergence + warm-set under-count). The measured 39% was a VG-001 deploy-order artifact (cold/hydrating cache), NOT a fix failure and NOT a capacity-architecture ceiling. |
| **TH-004 (horizontal / Redis / multi-worker) reactivation** | **DOES NOT FIRE** | n/a | Precondition (≥99% failing AFTER a completed warm cycle under honest measurement) was never met — the warm cycle never completed. Do NOT route back to thermia. |

**Net**: the fix is directionally CORRECT and the capacity-architecture decision (vertical, not horizontal) is VINDICATED. CR-3 cutover remains **BLOCKED** pending the routed fixes + a clean re-gate on a durably-cpu=1024 substrate. No cutover-resume handoff to the monolith is authored.

**Honest residual**: the resilience axis is STRONG (live-prod, ≥2-stream, rite-disjoint corroboration on the SLI audit). The ≥99% axis is REFUTED/incomplete and self-ref-capped — the thermia design and 10x-dev implementation were the same actor; only the observability SLI audit was rite-disjoint (partial external validation). The clean re-gate is the MODERATE→STRONG lift that closes this.

---

## Axis 1 — Resilience (RECV-BULK-001): RESOLVED [STRONG]

The original 86.8%-FAIL mechanism was a capacity/topology starvation cascade: at 0.25 vCPU (`autom8y-asana-service:445`), one CPU-bound Polars build pegged the single-worker event loop → 30s timeouts → ALB killed the lone task → ECS replacement → ELB-502s for in-flight callers. That mechanism is **GONE**.

### The decisive before/after (ONLY variable changed: task CPU)

| Signal | BEFORE (cpu=256, `:445`) | AFTER (cpu=1024, `:453`) |
|--------|--------------------------|---------------------------|
| ECS task replacements | task killed + reborn under width | **0** |
| ALB UnHealthyHostCount | >0 (target deregistered) | **0** |
| ELB-5XX | 502 cascade 09:19–09:20 | **0** |
| Event loop | stalled → 30s timeouts | **responsive at 97% peak CPU** |
| p99 latency | 30s timeouts | **2.2s** |

Configuration under test (per `.sos/wip/chaos/BLAST-RADIUS-DECLARATION.md`): PRIMARY taskdef `:453` cpu=1024/mem=2048 (adot sidecar capped 256 → app effective ~768), image `ab306f1`, LKG=10.0 live, blue/green active TG `a8-asana-green`, HC=`/health`, 1 healthy target. The vCPU raise was achieved via the correct a8-manifest lever + the TD-001 event-loop offload (`asyncio.to_thread` of the unoffloaded `pl.concat`) + the new `asyncio.Semaphore(4)` CPU gate.

### Evidence quality
- **≥2-stream corroboration**: ALB metrics (ELB_5XX, UnHealthyHostCount, HealthyHostCount) + ECS/ContainerInsights (task-replacement count, CPU). Both streams show the cascade is absent.
- **Live-prod, not synthetic**: bounded gameday on real prod infra; CR-3 BLOCKED means ~zero competing consumer traffic, so the gameday was the dominant load (clean signal).
- **Default-to-refuted honored**: abort criteria were pre-declared (5xx>25% sustained 60s excluding by-design Arm-B cold 503s; any UnHealthyHost>0; any task replacement; any taskdef revert off `:453`). None of the FAIL-signal abort criteria fired.

### TH-007 correctness proofs (VG-003) — PASSED
- **Singleflight collision**: N concurrent same-key requests → exactly **1** build (`build_coordinator_builds_coalesced > 0`, one `completed`). The dedup path that was UNPROVEN in the original gate now has a live receipt.
- **503 + Retry-After live-firing**: **128/128** intentional cold-build 503s carried `Retry-After: 30` (`errors.py:621-627`). The structurally-present-but-live-unproven header is now proven firing.

**Verdict on Axis 1: RESOLVED [STRONG].** The targeted fix is proven on the axis it targeted. The vertical-scale capacity decision (over horizontal/Redis) is the right one — confirmed by the loop staying responsive at 97% CPU with zero replacements.

---

## Axis 2 — The ≥99% Honest Gate: NOT CERTIFIED

The VG-002 ≥99% conjunct is **NOT MET**. Measured combined honest success = **39%**. But the cause is decisive and must be stated precisely, because it changes the routing entirely.

### The 39% is a deploy-order artifact, NOT a fix failure

The rite-disjoint observability SLI audit proved the 39% was a **VG-001 deploy-order artifact**: the gameday probed a cold/hydrating cache. The last cold-503 landed at **17:14Z** — exactly when frames were finishing landing. The 12 "503" GIDs are **real, data-bearing, fully-buildable projects with valid S3 frames**; there is no denominator pollution (every GID is a legitimate workload member, not a synthetic or non-existent project). The hard deploy-order discipline (warm to coverage=1.0 BEFORE activating LKG=10.0 honest-staleness, per VG-001) was NOT satisfied at gameday time — and the reason it was not satisfied is the first of two REAL defects below.

This is NOT a capacity-architecture ceiling. The resilience axis proved the substrate carries the load at 97% CPU with zero replacements. The 39% is a *coverage* failure (cache not warm), not a *throughput* failure (substrate too small).

### REAL defect #1 — Warmer cannot converge to coverage=1.0 within its 900s Lambda budget

- The warmer times out at **~23/46 keys** (`prematerialize_exiting_early_timeout completed=23 pending=23`). The ≤162s convergence estimate is **~5x wrong in prod**.
- **Registry-declaration-order bias**: the warmer pre-materializes in registry-declaration order and systematically drops the 12 pipeline/holder GIDs **last** → they are the first dropped at timeout. The 12 cold-503 GIDs are precisely the tail the timeout amputates.
- **VG-001 `coverage=1.0` was a FALSE-GREEN** — `warmer_coverage_rate == 1.0` was a precondition for VG-002 but was NEVER achieved in telemetry. The deploy-order gate that should have caught this reported green on a coverage value that was never reached.

### REAL defect #2 — Warm-set under-count (VG-004 REAL)

- The warmer pre-materializes **23 GIDs**, but the consumers `refresh_frames.py` queries **34** distinct `Project` subclasses.
- **11 consumer-queried GIDs are absent** from the warm set. Of those, **3 have no frame at all** (`Commission`, `PauseABusinessUnit`, `CustomerHealth`).
- Consequence: even at `warmer_coverage_rate=100%` over the 23/46 it knows about, those 11 GIDs **cold-build (503) under cutover** — and 3 are guaranteed-503 because no frame exists to serve. VG-004s static-registry ⊇ live-discovered-GID correspondence is REFUTED at source: the static warm set is a strict, deficient subset of the live-discovered set.

### Why this is NOT MET but also NOT the fixs fault
The targeted fix (offload + vCPU + Semaphore + SIGTERM + LKG honesty) addressed RECV-BULK-001/002/003 — and it did. The ≥99% gate is blocked by two defects that were *latent contributing conditions* the fix package did not target: the warmers convergence budget and the warm-set/consumer-set divergence. Per Cook 1998 [II:SRC-001 STRONG], the system was running in degraded mode (under-warm cache, under-counted warm set) before the trigger; certifying ≥99% requires closing those latent conditions, not re-litigating the resilience fix.

**Verdict on Axis 2: NOT CERTIFIED.** Honest ≥99% is unproven; the path to it is the two routed fixes below + a clean re-gate.

---

## TH-004 Reactivation Hook: DOES NOT FIRE

Per the re-gate handoff reactivation hook: *"If VG-002 FAILS ≥99% AFTER the full package (TD-001..007 + vCPU + LKG=10.0 + warm cycle) deploys under honest measurement, then TH-004 (horizontal/multi-worker/Redis) reactivates per cache-architecture ADR-003 → route BACK to thermia."*

**The precondition is conjunctive and was NOT met.** TH-004 fires only if ≥99% fails AFTER a *completed warm cycle* under *honest measurement*. The warm cycle **never completed** — REAL defect #1 (warmer convergence timeout at 23/46) means the "AFTER the full warm cycle" clause was never satisfied. The 39% was measured against a cold/hydrating cache, not against a warmed steady state.

**Therefore TH-004 does NOT fire.** Routing back to thermia for a horizontal/Redis build would be a category error: it would attempt to solve a *coverage/convergence* problem (warmer cant finish in 900s; warm set is under-counted) with a *throughput/coalescing* architecture (Redis-backed shared cache + multi-worker). The thermia gate already refuted the horizontal premise three times (TH-001 heat-mapper + 3 adversarial critics, 3/3 refuted; the bulk cold-miss path is fire-and-forget 503 with no synchronous caller queue). Nothing in this re-gate re-opens that.

**Routing consequence**: the two REAL defects route to **10x-dev / platform** (warmer convergence + warm-set reconciliation are implementation/config fixes interior to the frozen contract), NOT to thermia. The vertical-scale architecture stands.

---

## Deploy-Integrity Blocker (cpu=1024 not durably landed)

cpu=1024 (`autom8y-asana-service:453`) is **LIVE but NOT durably landed**. The re-gate ran on a substrate that the next deploy will revert.

### The race
- A recurring **CI-writer race** re-registers cpu=256 taskdefs and reverts the service. The satellite-dispatch fires on three triggers (sdk-published / main-Test-success / manual) with **no concurrency guard**, and the CI deploy path **ignores the manifest cpu/mem override**. Observed reverts: `:454`, `:455`, `:456` — all cpu=256 — present in the registry during the window (per `BLAST-RADIUS-DECLARATION.md` line 11). The CI-writer guard held only because satellite PR #93 was OPEN/unmerged and no SDK publish occurred during the gameday window; the service PRIMARY was manually pinned to `:453`.
- **PR #47 (the manifest 1024 raise) is NOT in the canonical checked-out manifest.** So even absent the race, a clean deploy from the canonical manifest re-applies cpu=256.

### Why this is a BLOCKER, not a footnote
A ≥99% certification on a cpu=1024 substrate is **meaningless if the next deploy silently reverts to cpu=256** — that would re-introduce the exact RECV-BULK-001 starvation cascade the resilience axis just proved resolved. The durability of the resilience fix is conditional on the deploy path honoring cpu=1024. Until that holds, the STRONG resilience result is true *for the running task* but not *for the services steady-state deploy contract*.

This is a `[STRUCTURAL]` finding (deploy-topology / CI-writer concurrency), not a `[TACTICAL]` one — it requires the CI deploy path to honor the manifest override AND a concurrency guard AND PR #47 landed. Routed to platform / governance below.

---

## VG-005 — Open Observability Gap

The `CPU_STARVATION_REPLACEMENT` classification cannot be assembled in a single alarm without a metrics bridge.

- **Leading signals** (the receiver CAN emit, scraped by Prometheus/AMP): `event_loop_lag_seconds`, semaphore saturation.
- **Lagging signals** (the receiver CANNOT emit, CloudWatch-native): `alb_unhealthy_host_count`, `ecs_task_replacement_count`.

These two stores cannot be joined in one alarm without an **EMF / `put_metric_data` bridge** from AMP to CloudWatch (or vice versa). Until bridged, the leading and lagging halves of the starvation signature live in separate panes — an operator cannot get a single end-to-end alarm that says "CPU starvation is driving replacements." The 27-unattributed-5xx blind spot from the original gate is therefore only *partially* closed: the resilience gameday confirmed the cascade is absent, but the *standing* detector that would catch a regression is not yet wired end-to-end.

This is a `[TACTICAL]` observability gap (a bounded instrumentation task), not a blocker for the resilience verdict. Routed to an observability follow-up below. It IS, however, a precondition for safely operating cpu=1024 in steady state, because without it a slow drift back toward starvation (e.g., after a partial cpu revert) would not surface as a joined alarm.

---

## Contributing Factors (NOT a single root cause)

Per Cook 1998 [II:SRC-001 STRONG] and Reason 1997 [II:SRC-003 STRONG], the ≥99% NON-CERTIFICATION is multi-factor. The 39% measurement is the TRIGGER signal, not the root cause. Minimum-three contributing factors (anti-Root-Cause-Fixation discipline):

### CF-1 — Warmer convergence-budget under-provisioned (PRIMARY for ≥99%)
The warmer cannot reach coverage=1.0 inside its 900s Lambda budget; it times out at 23/46. The ≤162s estimate was ~5x optimistic. This is a *latent capacity condition of the warmer*, distinct from the *receiver* capacity condition the fix resolved.

### CF-2 — Registry-declaration-order bias amputates the wrong tail
The warmer processes keys in registry-declaration order and drops the 12 pipeline/holder GIDs last → they are precisely the GIDs the timeout cuts. A warm-heavy-GIDs-first ordering would change *which* GIDs survive a partial warm; the current ordering maximizes the cold-503 surface.

### CF-3 — Warm-set / consumer-set divergence (23 vs 34)
The warmers static key set (23 GIDs) is a strict, deficient subset of the consumers live-queried set (34 `Project` subclasses). 11 GIDs absent; 3 frameless. A guaranteed cold-503 surface independent of warmer convergence.

### CF-4 — Deploy-order gate reported a FALSE-GREEN coverage=1.0
VG-001s `warmer_coverage_rate == 1.0` precondition was treated as satisfied when telemetry never showed 1.0. A gate that green-lights on an unverified precondition is a latent process defect (the gate did not actually gate).

### CF-5 — cpu=1024 not durably landed (CI-writer race + PR #47 not in canonical manifest)
The substrate the result rests on is reverted by the next deploy. A latent deploy-topology condition that would silently re-introduce RECV-BULK-001.

### CF-6 — Leading/lagging starvation signals unjoinable (VG-005)
AMP and CloudWatch halves of the starvation signature are not bridged; the standing regression detector is incomplete.

**No single action item closes ≥99%.** Per the counter-case discipline [II:SRC-003 STRONG], this is a contributing-factor web requiring a coordinated fix set (warmer + reconciliation + deploy-integrity + obs bridge), not a point patch. The clean re-gate is the verification that the web is closed.

---

## CR-3 Cutover Decision: BLOCKED

**Decision: BLOCKED.** The consumer (legacy `autom8` monolith) CR-3 cutover may NOT resume. No cutover-resume handoff to the monolith is authored (`handoff_back: NONE`).

### Rationale
The resilience axis is RESOLVED, but CR-3 is gated on the ≥99% honest conjunct, which is NOT CERTIFIED, AND on the substrate being durable. Cutting over to a receiver whose cache reaches only ~half coverage (warmer timeout) and whose warm set misses 11 consumer-queried GIDs (3 frameless) would produce guaranteed cold-503s for real consumer reads under cutover. Cutting over onto a cpu=1024 task that the next deploy reverts to cpu=256 would re-introduce the starvation cascade.

### Exact gating conditions (ALL must hold to lift BLOCKED → resume)
1. **Warmer converges to true 46/46 + `checkpoint_cleared`** within budget — coverage=1.0 actually observed in telemetry (not a FALSE-GREEN). [closes CF-1, CF-2, CF-4]
2. **Warm-set reconciled 23 → 34** including the 3 frameless GIDs (`Commission`, `PauseABusinessUnit`, `CustomerHealth`); `bulk_prematerialization_keys` corrected; the false registry docstring claim fixed; VG-004 static ⊇ live correspondence holds on a LIVE probe. [closes CF-3]
3. **cpu=1024 durably landed**: CI deploy path honors the manifest cpu/mem override, a concurrency guard is added to satellite-dispatch, and PR #47s 1024 raise is in the canonical manifest — so a clean deploy does NOT revert to cpu=256. [closes CF-5]
4. **Clean independent re-gate** clears **≥99% honest** (LKG-unflattered, post-warm to true coverage over the reconciled 34-GID set, on the durably-cpu=1024 substrate), with `CPU_STARVATION_REPLACEMENT == 0`, ≥2-stream corroborated, SLI computed by a non-author stream. [the verification]
5. **VG-005 bridge** wired so the standing starvation detector is end-to-end (precondition for safe steady-state operation, not for the gameday itself). [closes CF-6]

When 1–5 hold, the evidence ceiling lifts to STRONG and a cutover-resume handoff to the monolith may be authored. Until then: BLOCKED.

---

## Routed Follow-Ups (with owners)

Per Dekker 2006 [II:SRC-002 STRONG], every item is a SYSTEM/process change, not a "be more careful" human-behavior item. All are interior to the FROZEN external contract.

| # | Follow-up | Targets CF | Owner | Type |
|---|-----------|-----------|-------|------|
| 1 | **Warmer convergence**: fix timeout/memory/chunking + warm-heavy-GIDs-first ordering so it reaches true **46/46 + `checkpoint_cleared`** within budget. Reconcile `reserved-concurrency=1` vs self-invoke fragility + the OOM-skips-self-invoke (warmer) findings. | CF-1, CF-2, CF-4 | **10x-dev / platform** | STRUCTURAL |
| 2 | **Warm-set reconciliation 23 → 34**: fix `bulk_prematerialization_keys` to cover all 34 consumer-queried `Project` subclasses incl. the 3 frameless GIDs (`Commission`, `PauseABusinessUnit`, `CustomerHealth`); fix the false registry docstring claim. | CF-3 | **10x-dev** | TACTICAL |
| 3 | **Deploy-integrity**: make the CI deploy path honor the manifest cpu/mem override; add a concurrency guard to satellite-dispatch (sdk-published / main-Test-success / manual); land PR #47s 1024 raise into the canonical manifest. This is the durability blocker for cpu=1024. | CF-5 | **platform / governance** | STRUCTURAL |
| 4 | **VG-005 AMP↔CloudWatch bridge** for the 2 leading signals (`event_loop_lag_seconds`, semaphore saturation) so `CPU_STARVATION_REPLACEMENT` joins leading + lagging end-to-end. | CF-6 | **observability follow-up** | TACTICAL |
| 5 | **Clean re-gate** (the precondition to lift the ceiling to STRONG + unblock CR-3): warm to true coverage over the reconciled 34-GID set, on a durably-cpu=1024 substrate, honest ≥99% with `CPU_STARVATION_REPLACEMENT==0`, SLI validated by a non-author stream. | verification | **sre / chaos** (this rite) | n/a |

**Routing summary**: items 1–2 → 10x-dev/platform (implementation/config interior to contract); item 3 → platform/governance (deploy-topology + CI concurrency); item 4 → observability; item 5 → sre/chaos re-gate. **NO route back to thermia** (TH-004 does not fire). **NO cutover-resume handoff to the monolith** until item 5 clears.

---

## Evidence Ceiling Per Claim (Self-Ref Honesty)

Self-ref ceiling: the thermia design + 10x-dev implementation were the SAME actor (a single design→impl stream). The observability SLI audit was **rite-disjoint** (partial external validation). Evidence on the resilience axis is STRONG (live-prod, ≥2-stream, rite-disjoint corroboration via the SLI audit on the deploy-order diagnosis); evidence on the ≥99% axis is REFUTED/incomplete and self-ref-capped.

| Claim | Grade | Corroboration |
|-------|-------|---------------|
| RECV-BULK-001 cascade RESOLVED at cpu=1024 (0 replacements / 0 UnHealthyHost / 0 ELB-5XX; loop responsive 97% CPU; p99 2.2s) | **STRONG** | Live-prod gameday, ≥2-stream (ALB + ECS/ContainerInsights); pre-declared abort criteria none fired; rite-disjoint SLI audit corroborates. |
| Decisive before/after attributable to cpu raise (only variable changed) | **STRONG** | Blast-radius declaration isolates CPU 256→1024 as the sole variable; image/LKG/TG held constant. |
| TH-007 singleflight collision → exactly 1 build | **STRONG** | Live `builds_coalesced > 0` + one `completed` under concurrent same-key. |
| TH-007 503 + Retry-After live-firing (128/128) | **STRONG** | Live header capture on intentional cold-build 503s. |
| 39% combined honest = VG-001 deploy-order artifact (cold/hydrating cache), not fix failure | **STRONG** | Rite-disjoint SLI audit; last cold-503 at 17:14Z = frames finishing landing; 12 GIDs real + buildable; no denominator pollution. |
| Warmer convergence timeout at 23/46 (`prematerialize_exiting_early_timeout completed=23 pending=23`) | **STRONG** | Direct warmer telemetry. |
| Registry-declaration-order bias drops the 12 pipeline/holder GIDs last | **MODERATE** | Inferred from ordering + which GIDs were dropped; single observation. |
| VG-001 `coverage=1.0` was a FALSE-GREEN (never in telemetry) | **STRONG** | Telemetry absence of coverage=1.0 at gate time. |
| Warm-set under-count 23 vs 34; 11 absent; 3 frameless | **STRONG** | Source: warmer `bulk_prematerialization_keys` (23) vs consumer `refresh_frames.py` 34 subclasses; 3 GIDs have no frame. |
| cpu=1024 not durably landed (CI-writer race; PR #47 not in canonical manifest) | **STRONG** | `:454/:455/:456` cpu=256 reverts observed in registry; PR #47 absent from checked-out manifest; CI deploy ignores manifest override. |
| ≥99% honest over the real 34-GID workload | **REFUTED / UNPROVEN** | Never measured post-warm-to-true-coverage on durable substrate; the clean re-gate is the lift. |
| TH-004 reactivation precondition met | **REFUTED** | Conjunctive precondition (≥99% fail AFTER completed warm cycle) unmet — warm cycle never completed. |
| VG-005 leading/lagging join | **OPEN** | No AMP↔CloudWatch bridge; standing detector incomplete. |

**Net ceiling**: resilience axis STRONG; ≥99% axis REFUTED/incomplete (MODERATE→STRONG lift gated on the clean re-gate). Per `self-ref-evidence-grade-rule`, only the rite-disjoint clean re-gate over the reconciled set on a durable substrate lifts the ≥99% axis to STRONG.

---

## What Went Well

- **The targeted fix worked on its target.** RECV-BULK-001 — the decisive root cause of the original 86.8% FAIL — is RESOLVED with a clean live-prod before/after. The offload + vCPU + Semaphore(4) package did exactly what it was designed to do.
- **The capacity-architecture call was vindicated.** The thermia gates 3/3 refutation of the horizontal/Redis premise held up: at 97% CPU with zero replacements, the vertical-scale substrate carries the load. No unnecessary Redis build.
- **The two previously-UNPROVEN resilience claims are now PROVEN.** Singleflight coalescing (1 build from N concurrent same-key) and 503+Retry-After (128/128) both have live receipts — the exact gaps the original gate flagged.
- **The default-to-refuted discipline caught the right things.** Pre-declared abort criteria + honest LKG measurement meant the 39% was *interrogated* (→ deploy-order artifact + two real defects) rather than accepted at face value or dismissed.
- **A rite-disjoint stream did the SLI audit.** The observability audit (not the fix author) diagnosed the deploy-order artifact and the warm-set under-count — partial external validation that lifted the resilience axis to STRONG and surfaced the real ≥99% blockers.

---

## Where We Got Lucky

- **The CI-writer race did NOT fire during the gameday window — by luck, not by guard.** The substrate stayed at `:453` cpu=1024 only because satellite PR #93 happened to be unmerged and no SDK publish occurred in-window. A merge or publish mid-gameday would have reverted to cpu=256 and invalidated the run (or worse, silently degraded a "passing" cutover). This is a latent failure waiting to align (Reason 1997 [II:SRC-003 STRONG]).
- **VG-001 reported a FALSE-GREEN `coverage=1.0`.** The deploy-order gate that was supposed to guarantee the cache was warm before honest-staleness activated did not actually verify coverage. If the SLI audit had not been rite-disjoint, the 39% could have been mis-attributed to the fix (→ wrongful TH-004 reactivation + an unnecessary thermia Redis build).
- **The warm-set under-count would have surfaced as consumer-facing cold-503s only AT cutover.** 11 absent + 3 frameless GIDs would have hit real consumer reads. We caught it pre-cutover via the VG-004 live-probe discipline, not in production.
- **The convergence estimate was ~5x optimistic (162s vs 900s timeout).** Had the warm cycle been assumed-complete, the cutover would have run on a half-warm cache.

---

## Acid Test

*"If this incident happens again, will this verdict prevent a repeat?"*

**Resilience axis: YES.** The cpu=256 starvation cascade is root-caused, fixed, and proven — and the fix mechanism (offload + vCPU + Semaphore) is documented with a decisive before/after. A recurrence would be a *deploy-integrity* regression (cpu revert), which follow-up #3 closes.

**≥99% axis: NOT YET.** The verdict identifies the contributing-factor web (warmer convergence, ordering bias, warm-set divergence, false-green gate, deploy durability, obs bridge) but the fixes are routed, not yet landed. Per the acid test, the verdict is INCOMPLETE until the clean re-gate (follow-up #5) verifies the web is closed under honest measurement on a durable substrate. The gating conditions are explicit and falsifiable, so the path to "would prevent a repeat" is concrete — but the box is not yet checked. **Dig no deeper on the fix; execute the routed follow-ups and re-gate.**

---

## Cross-References

- **This verdict supersedes adjudication of**: `.ledge/decisions/SRE-VERDICT-receiver-bulk-validation-2026-06-02.md` (original FAIL; root-cause evidence).
- **Re-gate handoff (inputs)**: `.sos/wip/handoffs/HANDOFF-10x-dev-to-sre-receiver-bulk-regate-2026-06-02.md` (VG-001..006, reactivation hook).
- **Resilience gameday**: `.sos/wip/chaos/BLAST-RADIUS-DECLARATION.md` (cpu=1024 `:453` before/after, abort criteria, steady-state baseline).
- **Design lineage**: `.sos/wip/handoffs/HANDOFF-sre-to-thermia-receiver-integration-readiness-2026-06-02.md`; `.sos/wip/handoffs/HANDOFF-thermia-to-10x-dev-2026-06-02.md`; thermia design suite `.sos/wip/thermia/` (TH-001/004/007, observability-plan.md §2/§4/§5).
- **Implementation**: PR #92 (autom8y-asana — TD-001/004/005/006/007, app-code); PR #313 (autom8y TF — TD-002 vCPU, TD-003 no-op); PR #47 (manifest 1024 raise — NOT in canonical manifest); PR #93 (satellite — OPEN, CI-writer guard).
- **Source anchors**: `cache_warmer.py` (warmer + `bulk_prematerialization_keys`); `refresh_frames.py` (consumer 34 `Project` subclasses); `dataframes/concurrency.py` (offload + Semaphore(4)); `api/lifespan.py` (SIGTERM drain); `errors.py:621-627` (503 + Retry-After); `config.py` (`LKG_MAX_STALENESS_MULTIPLIER`); `universal_strategy.py:1037-1041` (fire-and-forget 503).
- **Routing**: follow-ups 1–2 → 10x-dev/platform; 3 → platform/governance; 4 → observability; 5 → sre/chaos re-gate. NO route to thermia. NO cutover-resume handoff to monolith.

---

*Terminal SRE verdict. Resilience RESOLVED [STRONG]; ≥99% NOT CERTIFIED; TH-004 does not fire; CR-3 BLOCKED. Default-to-refuted held; contributing-factors framing per Cook 1998 / Reason 1997 / Dekker 2006 [II:SRC-001/003/002 STRONG]; self-ref ceiling honored. No single root cause; no blame; every action item a system change.*
