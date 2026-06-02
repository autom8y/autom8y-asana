---
type: decision
status: accepted
---

# SRE-VERDICT — Receiver Bulk Fan-out Validation Crux

- **Date**: 2026-06-02
- **Author**: incident-commander (SRE rite), adversarial /qa gate
- **Posture**: DEFAULT-TO-REFUTED. Burden on the receiver to clear the ≥99% S7 gate.
- **Initiative**: receiver-bulk-fanout-reliability — Stage-1 IMPL-1 (PRs #69–#89)
- **Cred gate**: GATE-PASS (canary credential representative of monolith-read store; N4 guard clear; prod live)

---

## GATE VERDICT: **FAIL**

The post-fix receiver does NOT clear the ≥99% S7 gate under representative multi-project
bulk fan-out. The single-project shape passed; the representative multi-project WIDTH
collapsed the receiver below even the consumer's prior 82% rate. Three of the four gate
conjuncts are unmet; one (singleflight proof) is UNPROVEN rather than proven.

**Do NOT return to the monolith for cutover until the receiver-side items below close.**
No cutover-resume handoff is authored. The consumer cutover (shape sprints 2–3 → 7-day S7
soak → Stage-B) remains BLOCKED.

---

## Gate-Conjunct Adjudication

The PASS gate requires ALL of (1) AND (2) AND (3) AND (4). Each is adjudicated independently
under default-to-refuted.

| # | Conjunct | Result | Basis |
|---|----------|--------|-------|
| 1 | Canary representative (cred-gate PASS) | MET | GATE-PASS given; cred path representative of monolith-read store. |
| 2 | Measured ≥99% under realistic bulk | **NOT MET** | Best observed = 82% (85 sat / 19 fb) on consumer run; chaos gameday at representative multi-project width classified FAIL (collapsed below 82%). 19/104 still fell back. |
| 3 | Residual 5xx root-caused AND closed | **NOT MET (root-caused, NOT closed)** | 5xx traced to ECS task restart mid-build (new `build_coordinator_initialized` at 09:20:18; ELB-502s 09:19–09:20; ECS task replacement). Root cause identified; failure mode OPEN. |
| 4 | singleflight / Retry-After / SA-isolation PROVEN under live load | **NOT MET (UNPROVEN)** | Load generated only 2 builds for one gid; ZERO coalesced/completed/failed/timeout events. Singleflight dedup never exercised to proof. In-place graceful degradation NOT observed — only auto-recovery via task replacement. |

**Verdict**: 1 of 4 conjuncts met. Gate is **REFUTED**. Default-to-refuted held: representative
width was the falsifier, exactly as the discipline anticipated.

---

## Measured Success Rate

- **measured_success_rate = 82%** (85 satellite / 19 fallback of 104 projects) — this is the
  consumer-run high-water mark (06-02 trajectory: 05-29 15% → 05-31 63% → 06-02 82%).
- Under chaos gameday at representative multi-project width, the rate **collapsed below 82%**
  (FAIL classification; the receiver did not survive the width). The ≥99% S7 gate is REFUTED
  at both the consumer-observed rate and the gameday-observed rate.

---

## Contributing Factors (NOT a single root cause)

Per Cook 1998 [II:SRC-001 STRONG] and Reason 1997 [II:SRC-003 STRONG], complex-system failure
is multi-factor. The "task restart" is the TRIGGER, not the root cause. Contributing factors,
ranked by reliability impact:

### CF-1 — Worker/build concurrency starvation under width (PRIMARY)
- `BuildCoordinator.max_concurrent_builds = 4` (build_coordinator.py:130–131); single uvicorn
  worker (per session memory: receiver-bulk-fanout-reliability-design). Under a 104-project
  bulk fan-out the build semaphore + single worker is the saturation surface that drove the
  task to the unhealthy threshold and triggered ECS replacement.
- **Source-verified**: `max_concurrent_builds: int = 4`, `_build_semaphore = asyncio.Semaphore(self.max_concurrent_builds)` (build_coordinator.py:130–141). `default_timeout_seconds: float = 60.0` (line 130) — coalesced waiters time out at the 60s budget under saturation.

### CF-2 — Task restart orphans in-flight builds (TRIGGER → cascade)
- 2 builds started 09:17:39–40 for gid `1207984018149338` (project + section arm), each preceded
  by `background_build_launched`. ZERO `build_coordinator_completed`. A NEW coordinator instance
  initialized at 09:20:18 (`build_coordinator_initialized`) = task restarted mid-build, orphaning
  both. ELB-502s at 09:19–09:20 corroborate (cross-stream: ECS task-replacement + ELB 502 +
  coordinator-init log).
- The build was killed/replaced, not gracefully drained. This converts a degradation into a
  hard 5xx for in-flight callers.

### CF-3 — Auto-recovery via replacement masquerades as resilience
- Target self-recovered to `healthy` ~90s post-abort, transitioning unhealthy → initial → healthy
  via ECS task replacement, with NO further load applied. This is **auto-recovery via task
  replacement, NOT graceful in-place degradation**. The receiver did not shed load gracefully;
  it died and was reborn. Resilience claim (graceful extensibility, Woods 2015 [RE:SRC-002]) is
  UNPROVEN.

### CF-4 — Singleflight dedup UNPROVEN under live load (latent, untested)
- The fan-out hypothesis from Task 1/2 ("a project with N sections triggers N concurrent builds
  that singleflight treats as N distinct keys") is **REFUTED AT SOURCE** (see Refuted-At-Source
  below). But the converse — that singleflight DOES coalesce correctly under real concurrency —
  is also UNPROVEN: the load only ever generated 2 distinct-key builds for one gid, and both were
  orphaned by the restart before any `coalesced` event. The dedup path has no live receipt.

### CF-5 — EmptyFrame + ColumnContract failures are CONSUMER-SIDE (not receiver defects)
- EmptyFrame=26, ColumnContractFailures=30 of 104 both adjudicate to consumer-side expectation
  mismatch, not receiver degradation. Column set is consumer-driven (via `select` inside
  `FleetQuery.filters`) or receiver-default per-entity (`DEFAULT_SELECT_FIELDS = ["gid","name","section"]`,
  query.py:117; or registry `default_projection`), never governed by the shared `autom8y-api-schemas`
  package. These do NOT count against the receiver gate but DO mean the consumer's static column
  contract must adapt to the frozen receiver projection contract.

---

## Refuted-At-Source: the per-section fan-out hypothesis

The Task 1/2 premise that per-section queries create N distinct singleflight keys is **FALSE in
this codebase**. Source-verified, grep-zero:

- Build key is `(project_gid, entity_type)` — `CoalescingKey = tuple[str, str]  # (project_gid, entity_type)`
  (build_coordinator.py:51); `make_coalescing_key(project_gid, entity_type)` (line 54); and at the
  consumer site `key = (project_gid, self.entity_type)` (universal_strategy.py:922).
- `section_gid` and `section_index` appear **ZERO times** in `universal_strategy.py` (grep count = 0
  across 1277 lines). They never reach the build path.
- Section is a POST-build column classification (universal_strategy.py:447–513: `_classify_*`,
  `has_section = "section" in available_columns`), not a build-key dimension.

**Consequence**: section width does NOT multiply build keys. CF-1 (concurrency starvation from
project COUNT, not section count) is the real width axis. The original fan-out framing must be
retired from the receiver model.

---

## Receiver-Side Fix-Forward Plan (WITHIN the frozen external contract)

All directions below are interior to the FROZEN external contract (A1 body-parameterized,
require_business_scope=True, honest_contract, 27-entity offer-domain, SA OAuth chain, router
mount-order, P1-C-04, HC-7, Sprint-1 IMPL-1 production source). None relaxes the contract for
the monolith. Per Dekker 2006 [II:SRC-002 STRONG], each item is a SYSTEM/process change, not a
"be more careful" human-behavior item.

| Rank | Fix direction | Targets CF | Owner rite | Frozen-contract safe? |
|------|---------------|-----------|-----------|----------------------|
| R1 | Raise worker count (uvicorn workers > 1) AND/OR tune `max_concurrent_builds` semaphore for the 104-project width; size against measured saturation, not guess | CF-1 | Platform Engineer | Yes — interior concurrency tuning |
| R2 | Graceful drain on ECS task replacement: hold SIGTERM until in-flight coordinator builds complete or hit a bounded drain deadline, so builds are not orphaned mid-flight | CF-2, CF-3 | Platform Engineer | Yes — deployment lifecycle |
| R3 | ECS health-check threshold / deregistration-delay tuning so transient build-saturation does not trip task replacement under bounded bulk load | CF-2 | Platform Engineer | Yes — infra config |
| R4 | Prove singleflight coalescing under live concurrent load (chaos experiment: concurrent same-key requests; assert `build_coordinator_coalesced` count > 0 and one `completed`) | CF-4 | Chaos Engineer | Yes — verification only |
| R5 | Verify 503 `Retry-After` HTTP header fires on the live build-in-progress path under bulk (header wired at errors.py:621–627, conditional on `exc.details["retry_after_seconds"]`; structurally PRESENT but live-unproven) | CF-2 | Chaos Engineer | Yes — verification only |
| R6 | SA-namespace rate-limit isolation proof under bulk (SlowAPI limiter; verify SA routes are not starved by the 100/min global; memory flags SA exemption missing) | (isolation) | Platform Engineer + Chaos Engineer | Yes — interior rate-limit config |
| R7 | Consumer-side (NOT receiver, routed to 10x-dev): reconcile static column contract with receiver per-entity default projection / `select` semantics to clear the 30 ColumnContract + 26 EmptyFrame non-defects | CF-5 | 10x-dev (cross-rite) | N/A — consumer adapts |

**Handoff routing**: R1–R3, R6 → Platform Engineer. R4, R5 (+ R6 verification) → Chaos Engineer.
R7 → 10x-dev (consumer-side, outside receiver gate). NO cutover-resume handoff to monolith.

---

## Evidence Ceiling Per Claim

Self-ref ceiling: this session's rite is producer-side to the receiver fix. Evidence caps at
MODERATE unless LIVE-PROD-UNDER-BULK data corroborates. Isolation tests and design claims do NOT
lift above MODERATE; only real load counts.

| Claim | Grade | Corroboration |
|-------|-------|---------------|
| Build key = `(project_gid, entity_type)`; section not in key | **STRONG** | Source-verified file:line (build_coordinator.py:51,54,130; universal_strategy.py:922) + grep-zero. Structural, not self-ref. |
| Per-section fan-out hypothesis REFUTED | **STRONG** | grep-zero `section_gid`/`section_index` in universal_strategy.py (0/1277); post-build classification at 447–513. |
| 503 Retry-After header is wired in-repo | **STRONG (structural-presence) / MODERATE (live-firing)** | errors.py:621–627 source-verified for presence; live-firing-under-bulk UNPROVEN. |
| `max_concurrent_builds=4` semaphore | **STRONG** | build_coordinator.py:130–141 source-verified. |
| measured_success_rate ≤ 82% (gate REFUTED) | **MODERATE** | Live consumer-run + gameday counts; producer-side observed, self-ref-capped per crux rule. The 82% IS live data but is corroborated by a single run lineage; treat as MODERATE until repeated. |
| 5xx = task-restart-orphaned-builds (CF-2) | **MODERATE** | Cross-stream concurrence ≥2 (coordinator-init log 09:20:18 + ELB-502 09:19–20 + ECS task-replacement). Live-corroborated but single-incident; MODERATE per self-ref ceiling. |
| Concurrency starvation under width (CF-1) | **MODERATE** | Inferred from semaphore=4 + single worker + observed collapse; not yet isolated to a clean repro. |
| Auto-recovery ≠ graceful degradation (CF-3) | **MODERATE** | Live-observed recovery transition unhealthy→initial→healthy via task replacement; single observation. |
| Singleflight dedup correctness | **REFUTED-AS-PROVEN / UNPROVEN** | No `coalesced` event ever emitted under load; cannot be graded as working. |
| EmptyFrame/ColumnContract = consumer-side | **MODERATE** | Source (query.py:117 `DEFAULT_SELECT_FIELDS`; FleetQuery.filters `select`) + package introspection + .know docs; consumer-driven projection confirmed. |

**STRONG claims** = structural source facts (build-key shape, grep-zero, header wiring presence,
semaphore value). **MODERATE-capped** = all load-outcome and failure-mode claims (success rate,
CF-1/2/3, consumer-side adjudication) — live data exists but is self-ref-producer-side and
single-run; repeated independent bulk runs would lift these.

---

## Acid Test

*"If this incident happens again, will this verdict prevent a repeat?"*

Partially. R1–R3 (concurrency + graceful drain + health-check tuning) address the trigger and
cascade. R4–R5 close the UNPROVEN resilience claims. The verdict does NOT yet have a clean,
repeatable bulk repro isolating CF-1 from CF-2 — that is the first item Platform/Chaos must
produce before re-gating. Until R1–R6 close with live-under-bulk corroboration, the ≥99% gate
stays REFUTED.

---

## Cross-References

- Source: `src/autom8_asana/cache/dataframe/build_coordinator.py` (51,54,130–141,194,288,334,366)
- Source: `src/autom8_asana/services/universal_strategy.py` (447–513, 922, 1117–1135)
- Source: `src/autom8_asana/api/routes/query.py` (117 DEFAULT_SELECT_FIELDS)
- Source: `src/autom8_asana/api/errors.py` (590–634 ApiDataFrameBuildError 503 handler + Retry-After)
- Source: `src/autom8_asana/api/exception_types.py` (121–151 ApiDataFrameBuildError)
- Obs gaps logged: `.know/obs.md` (RECV-BULK-001 single-worker/semaphore starvation; RECV-BULK-002 task-restart orphans builds; RECV-BULK-003 singleflight-unproven)
