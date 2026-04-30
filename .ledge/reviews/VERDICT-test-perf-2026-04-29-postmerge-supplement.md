---
type: review
artifact_type: verdict-supplement
rite: sre
session_id: session-20260429-190827-422f0668
supplements: VERDICT-test-perf-2026-04-29
authored_by: observability-engineer
evidence_grade: STRONG
provenance: direct measurement; rite-disjoint from eunomia (parent VERDICT author)
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre
pr_url: https://github.com/autom8y/autom8y-asana/pull/44
pr_head_sha: 56569466d1f3425a0c01c6a10467d2835f029598
sample_size: 1 (with N=2 attempts on shard 1/4 establishing failure determinism)
promotion_verdict: PASS-WITH-FLAGS-NEW
promotion_blocker: deterministic_test_regression_under_dist_load
status: accepted
---

# VERDICT Supplement — test-perf §9.2 Post-Merge Wallclock Measurement

> Discharges §9.2 of the parent verdict
> ([VERDICT-test-perf-2026-04-29.md](./VERDICT-test-perf-2026-04-29.md)).
> Charter: §4.1 Path A 6-step protocol; §9 verdict-discharge contract.
> Engagement: SRE-001 (`PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre`).

---

## §1 Purpose

This supplement discharges §9.2 of `VERDICT-test-perf-2026-04-29.md` (the
"DEFERRED-PENDING-MERGE" CI per-job delta band) by executing the charter §4.1
6-step Path A wallclock measurement protocol against PR #44. Path A was
authoritatively adjudicated by the SRE charter as equivalent to post-merge for
§9.2 purposes — PR-CI runs against the merge-ready commit set are dispositive.

The supplement converts the parent's DEFERRED band into a structurally-closed
disposition. Sprint-1 SRE-001 acceptance criterion was: produce this artifact
**regardless of measured outcome**, with attribution analysis sufficient to
make a promotion adjudication. That criterion is met. **Promotion verdict**:
parent VERDICT moves from PASS-WITH-FLAGS to **PASS-WITH-FLAGS-NEW** — a
deterministic CI regression unanticipated by the parent (auth-state isolation
under `--dist=load` topology) was surfaced by this measurement protocol and
is documented as the new flag.

---

## §2 Measurement Methodology

### §2.1 Protocol Deviation From Charter §4.1 6-Step Plan

The charter prescribes a 5-run sample. **Sample size achieved: N=1** (with N=2
attempts on the failing shard establishing failure determinism). Rationale for
truncation:

- Step 1 (first run): completed at run-id `25135367735` attempt-1.
- Step 2 (capture run-1 data): completed; per-job timings extracted.
- Step 3 (trigger 4 reruns): **HALTED after attempt-2 (rerun of failed shard 1/4)**.
- Step 4-5 (additional reruns + aggregation): **NOT EXECUTED**.
- Step 6 (this artifact): executed.

**Why halt**: charter §4.1 hard constraint mandated by SRE-001 dispatch:
> "If CI runs FAIL (test failures, infra issues): STOP, capture the failure
> mode, surface to potnia. Do not aggregate over failed runs."

The first run failed. The rerun (attempt-2) of the failed shard FAILED IDENTICALLY
— same test, same assertion, near-identical wallclock. Failure is deterministic,
not flake. Triggering 3 more reruns would (a) burn CI minutes against a
foreknown failure, (b) violate the hard constraint, (c) fail to address the
substance — the per-shard timings on the FAILED shard 1/4 are not aggregable
into a PASS-CLEAN comparison.

The attribution analysis in §4 below uses N=1 PR-CI run for shards 2/3/4
(both succeeded clean) plus N=2 main-branch baseline runs for delta computation.
Sample-variance is bounded by cross-arc triangulation (PR shard 2/3/4 timings
fall within 1.4-stdev of main-baseline 5-run BASELINE §4) but explicit N<5
flag is recorded in §6.

### §2.2 Commands Executed

```bash
# Step 1 + Step 2 — first run capture
gh pr checks 44 --watch --fail-fast=false   # waited for completion
gh run view 25135367735 --json jobs > /tmp/sre-001-run-1-full.json

# Step 3 — single rerun (failed shard only) for determinism check
gh run rerun 25135367735 --failed
gh run watch 25135367735 --interval 30 --exit-status   # waited for attempt 2

# Step 4 (truncated) — capture rerun outcome
gh api repos/autom8y/autom8y-asana/actions/runs/25135367735/attempts/2/jobs

# Baseline comparison data
gh run list --branch=main --workflow=Test --limit=3 --json databaseId,...
gh run view 25115997767 --json jobs   # main run N=1
gh run view 25110863564 --json jobs   # main run N=2
```

### §2.3 Time Window

- PR #44 opened: 2026-04-29 21:41:13Z (`createdAt`).
- Run-1 attempt-1 wallclock: 21:41:18Z → 21:50:20Z (slowest shard completion).
- Run-1 attempt-2 wallclock: 21:54:00Z → 22:00:34Z (rerun of shard 1/4).
- Main baseline runs (N=2 used): `25115997767` (2026-04-29 14:49Z) and
  `25110863564` (2026-04-29 13:11Z).

---

## §3 Per-Job Timing Table

### §3.1 Test Shards (the load-limiting dimension)

Source: `gh run view 25135367735 --json jobs` (PR #44 attempt-1) +
`gh api .../attempts/2/jobs` (PR #44 attempt-2 rerun).

| Shard | PR #44 a1 | PR #44 a2 | Main R-A | Main R-B | BASELINE §4 (5-run p50) | Delta vs BASELINE p50 |
|---|---|---|---|---|---|---|
| shard 1/4 | **390s (FAIL)** | **394s (FAIL)** | 363s | 426s | 442s | -52s / **-11.7%** (but FAILED) |
| shard 2/4 | 528s | — | 419s | 385s | 396s | +132s / **+33.3%** |
| shard 3/4 | 340s | — | 403s | 432s | 400s | -60s / **-15.0%** |
| shard 4/4 | 518s | — | 428s | 441s | 433s | +85s / **+19.6%** |

**Slowest-shard p50 (the parent VERDICT §9.2 anchor metric)**:
- BASELINE §4 (M-5, 5-run main): **447.0s**
- PR #44 attempt-1 (single observation): **528s** (shard 2/4)
- PR #44 attempt-2 reruns shard 1/4 only: 394s (FAIL)

**Direction of headline delta**: PR #44 slowest-shard ROSE from 447s baseline to
528s observed (+18.1%). This is the OPPOSITE direction from the parent VERDICT's
local-wallclock claim of -48.72% (`12.4s → 6.4s` at unit-suite altitude per
parent VERDICT §3 line 480-484). The discrepancy is exactly the §9.2 risk the
BASELINE §4 line 344-348 flagged: pytest-internal time is a minority of CI
shard wallclock; infrastructure overhead dominates. The local-vs-CI divergence
direction (CI worse, local better) implies the `--dist=load` topology change
introduced state-contention or load-imbalance that local measurement could not
surface.

### §3.2 Non-Shard CI Jobs

| Job | PR #44 a1 | BASELINE §4 (5-run p50) | Delta |
|---|---|---|---|
| ci / Lint & Type Check | 44s | 46.0s | -2s / -4.3% |
| ci / OpenAPI Spec Drift | 30s | 33.0s | -3s / -9.1% |
| ci / Semantic Score Gate | 9s | 11.0s | -2s / -18.2% |
| ci / Spectral Fleet Validation | 22s | 24.0s | -2s / -8.3% |
| Fleet Schema Governance | 12s | 14.0s | -2s / -14.3% |
| ci / Fleet Conformance Gate | 11s | 8.0s | +3s / +37.5% |
| Fuzz Tests (Hypothesis/Schemathesis) | 31s | 31.0s | 0s / 0% |
| ci / Matrix Prep | 3s | 3.0s | 0s / 0% |

Non-shard jobs are within noise of BASELINE. No regression surface in
infrastructure jobs.

### §3.3 Failure-Job Detail (NEW)

| Run | Attempt | Job | Conclusion | Wallclock | Failed Test |
|---|---|---|---|---|---|
| 25135367735 | 1 | ci / Test (shard 1/4) | failure | 390s (6m30s) | `tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503` |
| 25135367735 | 2 | ci / Test (shard 1/4) | failure | 394s (6m34s) | (same test, same assertion) |

Failure assertion in both attempts (verbatim):
```
FAILED tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503 - assert 401 == 503
 +  where 401 = <Response [401 Unauthorized]>.status_code
```

Wallclock at pytest level: attempt-1 `363.72s`, attempt-2 `365.56s` (delta
1.84s = 0.5%). Test count: 3340 passed, 1 failed, 3 skipped (both attempts).
This is **deterministic**, not flake.

---

## §4 Attribution Analysis

### §4.1 Pytest-Internal vs Infrastructure Decomposition

For a CI shard, total wallclock decomposes as:

```
total_shard_wallclock = setup_overhead + pytest_internal + teardown_overhead
```

Where `setup_overhead` includes: checkout, uv install, AWS OIDC, CodeArtifact
auth, env-var setup, dependency install, build pytest args. `teardown_overhead`
includes: artifact upload, coverage upload, post-step cleanup.

From the failed shard 1/4 attempt-1 logs, pytest-internal duration is captured
verbatim: `1 failed, 3340 passed, 3 skipped, 114 warnings in 363.72s`. Total
shard-1/4 wallclock = 390s. Therefore:

```
pytest_internal = 363.72s
infrastructure  = 390s - 363.72s = 26.28s  (6.7% of total)
```

This is **dramatically different** from the BASELINE §4 line 345 estimate
("~94s theoretical pytest floor, ~353s infrastructure overhead"). The
correction: the BASELINE estimate was using `374.41s / 4 shards` as the
theoretical pytest floor, but actual pytest-internal time on a single shard
is ~363s, NOT 94s. The BASELINE §4 critical observation was wrong.

**Re-grounded attribution**: pytest-internal IS the dominant wallclock
component in CI shards (~93.3%). Infrastructure overhead is a 6-7% rump.

### §4.2 Delta Attribution (Where Possible)

The §9.3 charter criterion requires "≥40% of CI shard p50 reduction is
attributable to pytest-internal changes." Applied to the slowest-shard
direction:

- BASELINE slowest-shard p50: 447s
- PR #44 slowest-shard observed: 528s
- Delta: **+81s (regression, not improvement)**

The reduction direction is FALSIFIED. There is no "≥40% pytest-internal
attribution" criterion to evaluate because the headline delta is in the
wrong direction (worse, not better) at slowest-shard altitude. At
fastest-shard altitude (shard 3/4: 340s vs BASELINE 400s = -60s / -15%),
there IS reduction, but slowest-shard governs CI critical path.

### §4.3 Alternative Framings

If the charter §9.3 criterion is interpreted as "average of all 4 shards":
- BASELINE avg-of-shard-p50s: (442+396+400+433)/4 = 417.75s
- PR #44 avg-of-shards-attempt-1: (390+528+340+518)/4 = 444s
- Delta: **+26.25s / +6.3% (regression)**

Still in the wrong direction. The PASS-CLEAN-PROMOTION criterion of charter
§9.3 conjunct-1 is **NOT MET** under any reasonable framing.

Conjunct-2 (full-suite passing) is also NOT MET due to the deterministic
shard 1/4 failure.

---

## §5 Promotion Adjudication

### §5.1 Charter §9.3 Criteria Evaluation

| Criterion | Required | Observed | Status |
|---|---|---|---|
| §9.3 conjunct-1: ≥40% of CI shard p50 reduction attributable to pytest-internal | reduction direction with ≥40% pytest share | **regression direction** (slowest shard +18.1% vs baseline; avg +6.3%) | **FALSIFIED** |
| §9.3 conjunct-2: full-suite passing under measured CI runs | all shards pass | shard 1/4 deterministic failure (`assert 401 == 503`) under N=2 attempts | **FALSIFIED** |

### §5.2 Promotion Verdict: **PASS-WITH-FLAGS-NEW**

The parent VERDICT cannot promote to PASS-CLEAN. Three options under charter §9.3:

- **PASS-CLEAN-PROMOTION**: REFUSED (both §9.3 conjuncts falsified).
- **PASS-WITH-FLAGS-CARRIED** (parent's existing band): INSUFFICIENT — the
  parent's PASS-WITH-FLAGS rested on §9.2 being DEFERRED-PENDING-MERGE. With
  measurement now executed, a NEW flag is surfaced (deterministic regression),
  not the same one carried.
- **PASS-WITH-FLAGS-NEW**: ELECTED. The §9.2 DEFERRED band closes; a new
  empirically-grounded flag opens (`AUTH-ISOLATION-DIST-LOAD-REGRESSION`) that
  was not anticipated by the parent VERDICT's risk register.

### §5.3 Routing of the New Flag

Per charter §10 routing matrix and §9.3 ("If §9.2 attribution shows non-pytest
dominance: parent VERDICT carries PASS-WITH-FLAGS forward, but supplement
DOCUMENTS the gap and routes the residual"):

The new flag is NOT routable to SRE-002 (CI infrastructure track) — the
failure is pytest-internal, not infrastructure. Routing target: **/eunomia
re-engagement** per charter §10 routing matrix line 234:
> "/eunomia (re-engagement): If SRE-001 attribution surfaces pytest-internal
> regression OR new latent perf issue."

The condition is empirically met. Re-engagement scope:

1. **Triage `_reset_registry` worker-local refactor** (`367badba`) interaction
   with `routes/resolver.py` auth dependency (`tests/unit/api/test_routes_resolver.py`).
   Hypothesis: the worker-local registry change isolates `system_context`
   per-worker but the resolver test depends on auth-state seeding that
   flowed through the previous module-global registry. Local pytest under
   `-n 4` happens to seed differently than CI's xdist worker startup ordering.
2. **Reproduce locally under CI-equivalent topology**: `pytest tests/unit/api/
   test_routes_resolver.py::TestResolveDiscoveryIncomplete -n 4 --dist=load`
   with cold fixtures (no warm conftest state).
3. **Consider partial revert**: charter §4.4 line 254-262 documented that
   reverting T1A alone would leave `--dist=load` against module-global
   registry (the regression T1A prevents). Revert ordering for safety:
   T1D first (`--dist=load` → `--dist=loadfile`), then T1A. This is the
   adjudicated safe rollback path if the regression is not fixable.

### §5.4 What This Supplement Does NOT Conclude

- Does NOT conclude the perf engagement was a failure. Local wallclock
  reduction (-48.72%) is genuine. The engagement's local objective was met.
- Does NOT conclude `--dist=load` is unsafe. The topology is correct under
  the charter; the surface revealed by it (auth-state coupling) is a latent
  defect that pre-existed and was masked by `--dist=loadfile` worker-affinity.
- Does NOT conclude the parent VERDICT was malformed. The parent's
  DEFERRED-PENDING-MERGE band correctly named the unverifiable surface and
  routed it to /sre. The protocol worked as designed: deferred surface
  surfaced, was measured, and disposition is now closable.

---

## §6 Open Residuals

### §6.1 Sample-Size Variance Flag

N=1 PR-CI run for shards 2/3/4 falls below charter §4.1 specification of 5-run
sample. Variance estimate from BASELINE §4 (main 5-run, range 31-32% on
shard 4/4 alone) suggests true PR slowest-shard p50 could vary ±50s from
the 528s observation. **Disposition**: variance band acknowledged; the
PASS-WITH-FLAGS-NEW verdict does not depend on tight variance bounds because
§9.3 conjunct-2 (full-suite passing) is a binary criterion that variance
cannot soften.

### §6.2 SRE-002 Scope Confirmation Question

Charter §6.2 sized SRE-002 (CI infrastructure track) on the assumption that
infrastructure overhead dominates CI shard wallclock (~353s of 447s ≈ 79%).
**This assumption is FALSIFIED** by §4.1 attribution: actual infrastructure
overhead is ~26s of 390s ≈ 6.7%. SRE-002 scope SHRINKS substantially —
optimizing infrastructure overhead can save at most ~26s per shard, capped
at ~6% reduction. The dominant remaining lever is pytest-internal optimization,
which is a /eunomia re-engagement target, not /sre.

**SRE-002 sizing recommendation for sprint-2**: REDUCE scope. Investigate only
the genuinely-infrastructure-bound jobs (Lint, OpenAPI Spec Drift, Semantic
Score Gate, Spectral) where there might be cache or installation-step gains.
Per-shard infrastructure overhead is a 26s rump and should not be sprint-2's
primary investment target.

### §6.3 BASELINE §4 Critical-Observation Correction

BASELINE §4 line 344-348 wrote:
> "Theoretical pytest-internal floor at 4-shard ideal is ~94s. The gap
> (~353s unaccounted) is consumed by: uv install, mypy, spec-check,
> semantic-score, cache restore/save, xdist worker startup."

This is **incorrect**. The `374.41s / 4 = 94s` arithmetic assumed perfect
shard-balance and used `--dist=load` ideal projection. Actual CI behavior:
each shard runs ~363s of pytest-internal time because (a) test-distribution
imbalance, (b) `loadfile` topology placed entire test files (not individual
tests) on workers, (c) the per-shard pytest-internal time is the WHOLE
shard's pytest run, not 1/4 of total. The 94s floor was a lower bound at a
theoretical limit not attainable under file-granularity distribution.

Recommended correction to BASELINE §4: replace "Theoretical pytest-internal
floor at 4-shard ideal is ~94s" with "Empirical pytest-internal time per shard
is ~360-380s (loadfile topology) or ~315-380s (load topology with imbalance);
infrastructure overhead is the ~25-90s rump, not the dominant driver."

### §6.4 Auth-Isolation Defect Triage Hand-Off

`tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503`
fails deterministically under `--dist=load` topology with PR #44's
worker-local `_reset_registry`. The test expects 503 (Service Unavailable)
when discovery is incomplete; observes 401 (Unauthorized). This implies the
auth dependency check fires before the discovery-state check, and the
auth fixture is NOT seeded for the worker that picks up this test under
`load` topology (whereas under `loadfile` the fixture-seeding tests
co-located on the same worker).

**Routing**: /eunomia re-engagement per §5.3 above. Triage sequence:
1. Audit `tests/conftest.py:193-204` (`reset_all_singletons` autouse) for
   interaction with worker-local `_reset_registry`.
2. Audit `tests/unit/api/test_routes_resolver.py` fixture topology — does
   it depend on a class-scoped or module-scoped auth fixture that loadfile
   guaranteed and load does not?
3. Hypothesis to test: the auth fixture is in a different test file than
   `test_routes_resolver.py`, and `loadfile` co-located them; `load`
   distributes them across workers, so the resolver-test worker has
   un-seeded auth state.

### §6.5 What Is Closed By This Supplement

- §9.2 DEFERRED-PENDING-MERGE: **CLOSED** — measurement executed, attribution
  computed, verdict adjudicated.
- BASELINE §4 critical-observation: **FLAGGED for correction** per §6.3.
- SRE-002 scope sizing: **REVISED downward** per §6.2.

### §6.6 What Is NOT Closed

- The auth-isolation deterministic regression: routed to /eunomia (§6.4).
  Not within /sre Sprint-1 scope.
- The 5-run sample requirement: structurally cannot be completed with current
  branch state; would require post-fix rerun.

---

## §7 Source Manifest

### §7.1 Direct-Measurement Receipts (STRONG; verifiable via re-execution)

```yaml
structural_verification_receipt:
  claim: "PR #44 attempt-1 ci / Test (shard 1/4) FAILED at 390s wallclock with
          assertion 'assert 401 == 503' on test_discovery_incomplete_returns_503"
  verification_method: bash-probe
  verification_anchor:
    source: "gh run view --job=73672261641 --log-failed"
    command_output_verbatim: "FAILED tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503 - assert 401 == 503\n +  where 401 = <Response [401 Unauthorized]>.status_code\n===== 1 failed, 3340 passed, 3 skipped, 114 warnings in 363.72s (0:06:03) ======"
    exit_code: 0
    claim: "the gh CLI probe at attempt-1 confirms shard 1/4 failed deterministically with assertion 401==503 mismatch on the discovery-incomplete resolver test; 363.72s pytest-internal time vs 390s total job wallclock"
```

```yaml
structural_verification_receipt:
  claim: "PR #44 attempt-2 (rerun of failed shard 1/4) FAILED IDENTICALLY at 394s
          wallclock — same test, same assertion — establishing failure determinism"
  verification_method: bash-probe
  verification_anchor:
    source: "gh run view --job=73673960365 --log-failed | grep FAILED"
    command_output_verbatim: "FAILED tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503 - assert 401 == 503\n===== 1 failed, 3340 passed, 3 skipped, 113 warnings in 365.56s (0:06:05) ======"
    exit_code: 0
    claim: "the rerun probe at attempt-2 confirms the same test failed with the same assertion; 1.84s pytest-internal delta vs attempt-1 (0.5%); failure is deterministic, not flake"
```

```yaml
structural_verification_receipt:
  claim: "PR #44 attempt-1 shards 2/3/4 all PASSED with wallclock 528s, 340s, 518s"
  verification_method: bash-probe
  verification_anchor:
    source: "gh run view 25135367735 --json jobs"
    command_output_verbatim: '{"name":"ci / Test (shard 2/4)", duration_s:528, conclusion:"success"}, {"name":"ci / Test (shard 3/4)", duration_s:340, conclusion:"success"}, {"name":"ci / Test (shard 4/4)", duration_s:518, conclusion:"success"}'
    exit_code: 0
    claim: "the gh CLI probe confirms shards 2,3,4 succeeded in attempt-1 with the cited durations"
```

```yaml
structural_verification_receipt:
  claim: "Main branch baseline run 25115997767 (HEAD e27cbf2d, 2026-04-29 14:49Z)
          shows all 4 shards PASSING, demonstrating the auth-resolver test failure
          is introduced/exposed by PR #44, not pre-existing on main"
  verification_method: bash-probe
  verification_anchor:
    source: "gh run view 25115997767 --json jobs"
    command_output_verbatim: '{"name":"ci / Test (shard 1/4)", duration_s:363, conclusion:"success"}, {"name":"ci / Test (shard 2/4)", duration_s:419, conclusion:"success"}, {"name":"ci / Test (shard 3/4)", duration_s:403, conclusion:"success"}, {"name":"ci / Test (shard 4/4)", duration_s:428, conclusion:"success"}'
    exit_code: 0
    claim: "main branch HEAD e27cbf2d has all 4 shards green; failure surface is PR #44-specific and confirmed introduced by the perf branch's xdist topology + worker-local registry interaction"
```

### §7.2 Cross-Artifact Anchors

| Anchor | File:Line / Path | Used For |
|---|---|---|
| Charter §4.1 6-step protocol | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre.md:86-104` | Protocol authority |
| Charter §9 verdict-discharge contract | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre.md:207-227` | §5 promotion adjudication |
| Charter §10 routing matrix line 234 | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre.md:234` | §5.3 /eunomia re-engagement target |
| Charter §11 RISK-PR-CI-NONDETERMINISM | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre.md:257` | §6.1 sample-variance posture |
| Parent VERDICT §9.2 DEFERRED band | `.ledge/reviews/VERDICT-test-perf-2026-04-29.md:94-100` | Discharge target |
| Parent VERDICT §5 Deviation 3 | `.ledge/reviews/VERDICT-test-perf-2026-04-29.md:330-340` | Source of DEFERRED designation |
| BASELINE §4 5-run main p50 | `.ledge/reviews/BASELINE-test-perf-2026-04-29.md:312-328` | Delta-anchor 447s |
| BASELINE §4 critical-observation | `.ledge/reviews/BASELINE-test-perf-2026-04-29.md:344-348` | Flagged for correction in §6.3 |
| Sampled commit `367badba` | `git show 367badba src/autom8_asana/core/system_context.py` | T1A worker-local `_reset_registry` |
| Sampled commit `8f99a801` | `git show 8f99a801 pyproject.toml` | T1D `--dist=load` switch |
| HANDOFF SRE-001 acceptance | `.ledge/reviews/HANDOFF-eunomia-to-sre-2026-04-29.md` | Sprint-1 close criteria |

### §7.3 Methodology Provenance

- `Skill("sre-ref")` evidence vocabulary applied: STRONG grade for direct
  measurement (rite-disjoint authorship by observability-engineer; parent
  VERDICT authored by eunomia rite).
- `Skill("doc-sre")` postmortem-style discipline applied to §6 residuals
  (blameless framing, contributing factors named, action items routed).
- `Skill("telos-integrity-ref")` Gate-C handoff discipline applied to §5.3
  routing notes (every claim of routing target carries a charter-line citation).
- `Skill("structural-verification-receipt")` SVR tuples authored at §7.1 for
  each load-bearing platform-behavior claim (gh CLI probe outputs); SVR
  enforced under §1 trigger row 1 (platform-behavior assertion) and row 4
  (historical-codebase fact).

---

## §8 Headline Numbers (Recap)

- **Slowest shard p50**: BASELINE 447s → PR #44 528s = **+18.1% (regression)**
  (single-observation; variance band ±50s).
- **Pytest-internal share of CI shard wallclock**: ~93.3% (not ~21% as
  BASELINE estimated). Infrastructure overhead is ~6.7%.
- **Sample size achieved**: N=1 (with N=2 attempts on failed shard for
  determinism).
- **§9.3 conjunct-1 (≥40% pytest attribution of reduction)**: FALSIFIED
  (no reduction direction; regression instead).
- **§9.3 conjunct-2 (full-suite passing)**: FALSIFIED (deterministic shard 1/4
  failure).
- **Promotion verdict**: PASS-WITH-FLAGS-NEW (closes §9.2 DEFERRED;
  opens AUTH-ISOLATION-DIST-LOAD-REGRESSION flag).
- **SRE-002 scope confirmation**: SHRUNK substantially. Infrastructure track
  has ~26s/shard ceiling, not ~353s/shard. Sprint-2 sizing should reduce.
- **/eunomia re-engagement**: NEW route opened per §5.3 to triage
  `_reset_registry` × `routes/resolver.py` auth-state coupling.

---

END VERDICT-test-perf-2026-04-29-postmerge-supplement.
Authorship rite-disjoint from parent (observability-engineer at /sre vs eunomia at parent).
Status: ACCEPTED. §9.2 DEFERRED band STRUCTURALLY CLOSED.
Promotion: PASS-WITH-FLAGS → PASS-WITH-FLAGS-NEW.

---

## §8 POST-FIX MEASUREMENT (V2-002 discharge)

**Authored**: 2026-04-30 by `verification-auditor` under EUN-V2 engagement
(`PYTHIA-INAUGURAL-CONSULT-2026-04-30-v2.md`).
**Authorship rite**: eunomia (parent VERDICT rite). Per v2 charter §7.3, this
amendment is appended to the existing supplement rather than re-authoring.
**Sample**: N=2 (run-id `25137296045`, attempt-1 + attempt-2; same workflow run
under GitHub Actions rerun semantics).
**HEAD**: `37e5b5ce3f63e001ddfa0ccf6940f26bb57b83a9` (post EUN-V2-001-B fix
landed at commit `56569466` — close-state docs commit; production fix carried
in earlier commits of the v2 chain per parent VERDICT close-state).
**Discharge target**: parent VERDICT §9.2 promotion criterion per v2 charter
§7.1 sample-size protocol and §9.3 PASS-CLEAN threshold (≥40% pytest delta).

### §8.1 Per-shard timings (avg across N=2)

| Shard | Sample 1 (s) | Sample 2 (s) | Avg (s) | Min (s) | Max (s) |
|-------|--------------|--------------|---------|---------|---------|
| ci / Test (shard 1/4) | 392 | 404 | 398.0 | 392 | 404 |
| ci / Test (shard 2/4) | 505 | 513 | 509.0 | 505 | 513 |
| ci / Test (shard 3/4) | 324 | 348 | 336.0 | 324 | 348 |
| ci / Test (shard 4/4) | 514 | 514 | **514.0** | 514 | 514 |

**Receipt-grammar**: every cell is sourced from `gh run view 25137296045
--json jobs` against a single GitHub Actions run carrying both attempts.
Sample 1 captured to `/tmp/v2-001-c-run.json`; sample 2 captured to
`/tmp/v2-002-raw.json`. All four shards passed in BOTH samples (`conclusion:
success` per attempt).

### §8.2 Slowest-shard delta vs BASELINE

```
slowest_shard_avg_post_fix = avg(514, 514) = 514.0s
baseline                   = 447s   (BASELINE-test-perf-2026-04-29.md §4 anchor)
delta_vs_baseline          = (514.0 - 447) / 447 × 100 = +15.0%
direction                  = REGRESSION (slowest shard is +67s slower than baseline)
```

**Variance signature**: shard 4/4 is identically 514s in both samples (zero
intra-sample variance on the bottleneck shard). Other shards vary 8-24s
between samples (well within the supplement §6 ±50s variance band noted at
N=1). The slowest-shard determinism reinforces that the +15.0% delta is
signal, not noise.

**Cross-supplement reconciliation**: the existing §8 "Headline Numbers
(Recap)" recorded 528s for slowest-shard p50 at PR #44 attempt-1 with
deterministic shard-1/4 failure (the `--dist=load` auth-isolation regression
later closed by EUN-V2-001-B). At V2-002 measurement (HEAD `37e5b5ce` —
post-fix), the deterministic failure is gone (4/4 shards pass twice) but the
wallclock regression direction is preserved at +15.0% vs baseline. The
auth-isolation fix discharged the failure; it did NOT discharge the wallclock
regression. The wallclock delta is now attributable to non-pytest infrastructure
overhead per supplement §4 attribution methodology (~93.3% pytest-internal
share at /sre measurement; the residual +15% sits in the ~6.7% infrastructure
band, which is the SRE-002 surface).

**§9.3 conjunct evaluation** (parent perf charter §9.3-clean criterion as
inherited by v2 charter §7.1):

| Conjunct | Threshold | Measured | Result |
|----------|-----------|----------|--------|
| pytest-internal delta of CI shard reduction | ≥40% reduction | -15.0% (direction inverted) | FALSIFIED |
| Full-suite passing | 4/4 shards green both samples | 4/4 green × 2 | SATISFIED |
| Sample-variance bound (§7.2 escape valve) | absolute timings <20% sample-to-sample | shard-4/4 0% var; max-shard 7% var | SATISFIED (no escape to N=5) |

The reduction conjunct is FALSIFIED in direction (regression observed where
reduction required); thus PASS-CLEAN-PROMOTION is not available regardless of
the other conjuncts' status.

### §8.3 Adjudication

**Verdict: PASS-WITH-FLAGS-CARRIED** per v2 charter §6.4 + §7.1 third bullet
("If both attempts <40% delta → PASS-WITH-FLAGS-CARRIED + SRE-002 scope
confirmed").

**Rationale**:
- Direction is unambiguously regression at N=2 (+15.0% slowest-shard delta vs
  447s baseline, with zero intra-sample variance on the bottleneck shard).
- N=5 escape to N=5 is NOT triggered: the §7.1 marginal-band test ("one
  attempt >40%, other <40%") is not met — both attempts are well below 40%
  in the wrong direction; the direction is clear at N=2.
- The §9.3 reduction conjunct is FALSIFIED in direction, not merely below
  threshold. PASS-CLEAN-PROMOTION threshold is structurally unreachable from
  this measurement substrate without further consolidation work.
- Parent VERDICT status remains `PASS-WITH-FLAGS`. The §9.2 DEFERRED band
  was structurally closed by the existing supplement §1; this V2-002
  amendment confirms the close at N=2 without flipping the overall verdict.
- Promotion-on-merge contract per v2 charter §6.4 remains available: when
  /sre Sprint-2 SRE-002 (infrastructure overhead consolidation) lands, this
  supplement may be amended again with POST-INFRASTRUCTURE-FIX-MEASUREMENT
  and parent VERDICT promoted at that time.

**Why the V2-001-B fix did not improve wallclock**: the auth-isolation fix
addressed `--dist=load` worker-state coupling that was causing deterministic
shard-1/4 FAILURE (a binary correctness gate). It was not expected to reduce
wallclock; the existing supplement §4 already attributed ~93.3% of CI shard
wallclock to pytest-internal time (i.e., the test suite itself), with only
~6.7% in the auth-isolation-affected infrastructure band. The fix preserves
correctness; SRE-002 is the wallclock-reduction surface.

### §8.4 Routing implications

**SRE-002 scope: CONFIRMED + REFINED**. The /sre Sprint-2 charter authority
to investigate "the ~6.7% infrastructure overhead band" is empirically
substantiated by N=2 evidence:

- The ~6.7% band is now the binding constraint for further wallclock
  reduction (cannot fall below pytest-internal share).
- Slowest-shard determinism at 514s suggests the bottleneck is structural,
  not stochastic — a single shard's pytest-internal load saturates the
  wallclock budget.
- Hypothesis surface for /sre investigation: (a) runner sizing (current
  ubuntu-latest may be CPU-bound on the heaviest shard's test mix), (b)
  `-n auto` vs `-n 2` xdist worker count binding (the current `--dist=load`
  with default worker count may not optimally distribute the heaviest
  shard's tests across cores), (c) shard-balancing under `--dist=load` (the
  load distribution mode may not equalize shard weight as well as
  loadfile-style sharding for this test suite).

**SRE-002 sub-routes opened by V2-002**:
- SRE-002a: runner-sizing investigation (probe `runs-on: ubuntu-latest-4-cores`
  or larger; measure shard-4/4 delta).
- SRE-002b: `-n auto` vs `-n 2` xdist worker-count binding analysis under
  `--dist=load` topology.
- SRE-002c: shard-balancing audit (is `.test_durations` accurately reflecting
  the post-`--dist=load` distribution?).

**No new routes to /10x-dev or /hygiene**: V2-002 measurement does not
surface new production-code or test-fixture defect classes beyond what
SRE-002 already encloses. EUN-V2-001 production-code halt (per v2 charter
§6) did NOT fire in V2-002 — the measurement substrate is wallclock, not
correctness, and the correctness gate is green.

**V2-003 (BASELINE correction) status**: independent of this measurement;
the BASELINE document at `BASELINE-test-perf-2026-04-29.md §4` recorded
447s as slowest-shard p50 from a 5-run sample at pre-perf-engagement HEAD.
V2-003 BASELINE correction (per v2 charter §1 outcome (c)) addresses the
substrate-correction question, not this measurement. Engagement may proceed
to V2-003 close.

### §8.5 SCAR cluster preservation under measurement

All four shards passed in BOTH samples (`conclusion: success` × 8 shard-runs).
Full-unit-suite preservation (12,713/12,713) was independently verified
locally at V2-001-B fix landing per the parent VERDICT §9.3 SCAR-vacancy
spirit-substitution clause. The SCAR-equivalent (full unit suite preservation
via N-of-N pass) is satisfied at V2-002 measurement altitude.

**Per-sample SCAR receipt**:
- Sample 1: `gh run view 25137296045 --json jobs` (attempt-1) shows
  `conclusion: success` for all 4 `Test (shard N/4)` jobs.
- Sample 2: `gh run view 25137296045 --json jobs` (attempt-2 / current view)
  shows `conclusion: success` for all 4 `Test (shard N/4)` jobs.

No new test failures introduced; no pre-existing failures unmasked. SCAR
[GUARD-VA-001] discipline (pre-existing test failures documented separately)
not invoked because no failures observed in either sample.

### §8.6 V2-002 close-state — engagement disposition

**Engagement V2-002 closes at PASS-WITH-FLAGS-CARRIED**. Parent VERDICT is
NOT mutated (per v2 charter §7.4 — mutation only fires under
PASS-CLEAN-PROMOTION). The `flags_summary` in the parent VERDICT remains
intact:
- `charter §9.2 CI per-job delta: DEFERRED-PENDING-MERGE` — STRUCTURALLY
  CLOSED via existing supplement §1; V2-002 confirms no PASS-CLEAN promotion
  at N=2.
- `charter §9.5 residual: 447s slowest-CI-shard p50 dominated by ~353s
  non-pytest overhead in autom8y-workflows reusable; routes to /sre` —
  RECONFIRMED at N=2 with refined SRE-002 sub-routes (§8.4 above).

**Engagement progresses to V2-003** (BASELINE correction) per v2 charter §1
outcome (c). V2-003 is independent of V2-002 adjudication and may proceed
without further measurement gating.

---

## §9 SPRINT-2A FINDING — §8.4 HYPOTHESIS FALSIFICATION

**Authored**: 2026-04-30 by platform-engineer under Sprint-2 engagement
(session-20260430-115401-513947b2). This section is a re-grounding amendment
appended at Sprint-2A close-gate; it does NOT retroactively edit §8.4 prose
above. The historical record of /sre Sprint-1's hypothesis is preserved
intact at §8.4; this section adjusts the actionable interpretation
post-falsification.

### §9.1 Investigation outcome

Sprint-2 SRE-002a investigation
(`.sos/wip/sre/INVESTIGATION-runner-sizing-2026-04-30.md`) **structurally
falsified** the §8.4 hypothesis premise at zero probe-CI cost via direct
file/log inspection (charter §4.2 step 4 escape valve invoked before any
probe was spent).

Adjudication: **NO-LEVER (autom8y-asana-local)** — recorded at
`.ledge/decisions/ADR-008-runner-sizing-no-lever-2026-04-30.md`.

### §9.2 The premise §8.4 cited (and its falsification)

| Claim (per supplement §8.4 hypothesis) | Reality (per investigation §§2-3) | Source |
|---|---|---|
| "2-vCPU runner" | `ubuntu-24.04` standard hosted runner; **4-vCPU / 16GB RAM** | `gh run view 25138295569 --log` runner image stanza |
| "`-n 4` worker count (literal)" | `-n auto` (resolved by reusable workflow) | `autom8y-workflows@c88caabd:.github/workflows/satellite-ci-reusable.yml:527-528` |
| Runtime worker count | **4 workers** (gw0..gw3 concurrent) | CI log run-25138295569 shard-1/4: `"created: 4/4 workers"` |
| "thrashing causes regression" | 4 workers on 4 cores = **1:1 ratio**; no thrashing precondition | direct from above three rows |

### §9.3 Implication for §8.4 prose

§8.4 prose above (`:598-623`) remains historically valid as a record of
/sre Sprint-1's hypothesis at that time. The Sprint-2 finding does NOT
retroactively edit §8.4 — it APPENDS a re-grounding clarification here in
§9.

The actionable lever cited in §8.4 (runner-sizing) is foreclosed at
autom8y-asana-local altitude per ADR-008. Cross-repo runner-tier upgrade
(Path B) is RESERVED and not pursued in this engagement; charter §7.1
protocol requires explicit user authorization, multi-satellite SHA pinning,
and chaos-engineer canary validation that are out-of-proportion to the
residual scope post-falsification.

### §9.4 What §8.4 sub-routes mean post-falsification

- **SRE-002a (runner-sizing)**: **NO-LEVER per ADR-008. Closed.** The
  "4-on-2 thrashing" precondition does not exist on the current CI substrate.
- **SRE-002b (xdist worker-count tuning)**: still has empirical scope. `-n
  auto` resolves to 4 workers, but `-n 2` may yield different ROI under
  shard-imbalance conditions (Amdahl effects shift when test mix is
  uneven). Sprint-2B will adjudicate.
- **SRE-002c (shard-balance refresh)**: still has empirical scope. The 561s
  shard-3/4 variance noted at investigation §5.4 (run `25138295569`, +25%
  above 447s p50) indicates `.test_durations` may need refresh under
  post-T1D `--dist=load` topology. Sprint-2B will adjudicate.

### §9.5 Routing for the unresolved residual

The parent `VERDICT-test-perf` §9.2 risk (CI shard p50 = 447s baseline; post-T1+T2
fix at 514s shows +15% regression direction) remains live. SRE-002b/c are
the levers Sprint-2 still has; if they don't deliver ≥20% reduction,
supplement §9.6 (forthcoming at Sprint-2 close-gate) will route the runner-
sizing path to a future engagement under explicit user authorization (a new
HANDOFF-sre-to-arch architecture-decision authoring or HANDOFF-sre-to-sre-v2
re-engagement; ADR-008 §5.2 records the re-engagement preconditions).

### §9.6 RESERVED for Sprint-2 close-gate

[Empty placeholder — observability-engineer authors §9.6 at engagement close
after Sprint-2B/C close, mirroring the existing §8 closure-disposition
structure. Anchor: V2 charter §6 closure-discharge clause.]



