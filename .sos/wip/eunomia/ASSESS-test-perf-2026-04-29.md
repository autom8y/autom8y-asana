---
artifact_id: ASSESS-test-perf-2026-04-29
schema_version: "1.0"
type: triage
artifact_type: assessment
rite: eunomia
track: test
session_id: session-20260429-161352-83c55146
authored_by: entropy-assessor
authored_at: 2026-04-29
evidence_grade: STRONG
evidence_grade_rationale: "Grading anchored to charter rubric (external authority, PYTHIA §6.1/§6.2), measured baseline (rite-disjoint STRONG substrate, BASELINE-test-perf-2026-04-29), and 5-lane Explore swarm synthesis (rite-disjoint, MODERATE substrate). Multi-source corroboration satisfies STRONG unblock per self-ref-evidence-grade-rule."
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf
predecessor_inventory: INVENTORY-test-perf-2026-04-29
predecessor_baseline: BASELINE-test-perf-2026-04-29
target_categories_count: 7
---

# Assessment — Test-Suite Perf (perf-2026-04-29)

## §1 Assessment Purpose

This artifact applies the charter §6.1 (Suite Velocity), §6.2 (Parallelization
Health), and canonical eunomia-ref rubrics (Mock Discipline, Test Organization,
Fixture Hygiene, Coverage Governance, Semantic Adequacy) to the 34 findings
catalogued in INVENTORY-test-perf-2026-04-29, computes a weakest-link overall
grade per charter §6.3 (Overall = min of all 7 category grades), and emits
severity adjudications and cross-rite routing recommendations. No new measurement
is performed; grading derives solely from the measured baseline and multi-source
inventory. The VERDICT-eunomia-final-adjudication-2026-04-29 pipeline-track
close is not contested — this assessment is test-track scoped only.

---

## §2 Per-Category Grades

### Category 1 — Mock Discipline

| Field | Value |
|---|---|
| Category | Mock Discipline |
| Grade | **C** |
| Anchor finding(s) | F-MD-1 (dominant negative), F-MD-3 (MED negative), F-MD-4 (positive) |
| Rubric criteria met / unmet | eunomia-ref SCAR-EA-003: proliferation index F-MD-3 = 11:1 (bespoke vs canonical shared) → C band (5:1–10:1 is C; 11:1 is at the D border but shared infra exists at `tests/_shared/mocks.py:10`, so ratio is meaningful divergence, not orphaned duplication). F-MD-1: 97.8% unspec rate is systemic correctness debt, not a parallelism blocker — graded in context of pace-track scope (charter §3.2 routes this to /hygiene; pace impact bounded 2-8% per Swarm §7). Teardown discipline (F-MD-4) is sound (positive). Net: systemic but not D-level within pace-track grading frame. |
| Evidence chain | F-MD-1: Swarm Lane 5 §3 — 3,110 patch() sites, 67 spec'd; Inventory §3. F-MD-3: Swarm Lane 5 §4, `.know/test-coverage.md` GLINT-004 — 11 bespoke MockTask vs `tests/_shared/mocks.py:10`; Inventory §3. F-MD-4: Swarm §3 item 4 — 1,079 context-manager vs 206 decorator (5.2:1). |
| Severity disposition | HIGH (F-MD-1 correctness debt at 97.8%), MED (F-MD-3 MockTask drift), LOW (F-MD-4 sound). |
| Routing tag | route-/hygiene (F-MD-1, F-MD-3 per charter §10); in-rite-grade-only (F-MD-4 closed positive) |

### Category 2 — Test Organization

| Field | Value |
|---|---|
| Category | Test Organization |
| Grade | **B** |
| Anchor finding(s) | F-TO-1 (MED structural), F-TO-2 (MED structural), F-TO-3 (positive), F-TO-4 (positive) |
| Rubric criteria met / unmet | eunomia-ref canonical: F-TO-1 (3,570-line file, 272 tests) is a structural maintenance burden but fast tests (0.23s stored) — organizational debt, not a pace blocker under loadfile. F-TO-2: 4 adversarial files with 369 tests (Baseline M-6 empirical) and zero parametrize use across 5,197 lines is systemic org debt. Positive signals: slow-test gating operative (F-TO-3, test.yml:56 confirmed), asyncio_mode overhead bounded (F-TO-4). No agent-provenance epoch-tagged naming patterns detected (adversarial file names are domain-semantic, not epoch-tagged). Two MED negatives with two closed positives = B (minor entropy, isolated patterns, foundation sound). |
| Evidence chain | F-TO-1: Swarm Lane 4 §4; Baseline M-6 (272 tests, 0.23s stored). F-TO-2: Swarm Lane 2 §5; Baseline M-6 (102+99+94+74=369 measured tests). F-TO-3: Swarm Lane 4 §9, `test.yml:56`. F-TO-4: Swarm Lane 4 §8. |
| Severity disposition | MED (F-TO-1, F-TO-2), POSITIVE (F-TO-3, F-TO-4) |
| Routing tag | in-rite-fix (F-TO-2 via CHANGE-T3A per charter §7.2); preserve-status (F-TO-1, F-TO-3, F-TO-4) |

### Category 3 — Fixture Hygiene

| Field | Value |
|---|---|
| Category | Fixture Hygiene |
| Grade | **C** |
| Anchor finding(s) | F-FH-3 (HIGH structural cost driver), F-FH-4 (MED compound overhead), F-FH-1 (positive correction), F-FH-2 (contextual), F-FH-5 (positive) |
| Rubric criteria met / unmet | eunomia-ref canonical: fixture count at 65 across 15 conftests (F-FH-1) is manageable — corrected from prior inflated 687. Root cause concern is autouse scope: `reset_all_singletons` fires function-scoped before AND after every test (F-FH-3), generating ~299,310 reset callback invocations per run (11 singletons × 13,605 tests × 2). This is a quantified structural cost driver, not a cleanliness smell. API subdirectory double-autouse (F-FH-4) compounds overhead for ~50 API modules. Fixture chain depth max 5 is benign (F-FH-5 positive). Total fixture count manageable. Grade C: moderate entropy with quantified structural cost; foundation legible but autouse design is actively driving test-execution overhead. |
| Evidence chain | F-FH-3: Swarm Lane 1 §3; Baseline §5 anchor `tests/conftest.py:193-204` CONFIRMED; computation 11 × 13,605 × 2 = 299,310. F-FH-4: Swarm Lane 2 §3. F-FH-1: Swarm §1 correction table (65 not 687). F-FH-5: Swarm Lane 2 §6. |
| Severity disposition | HIGH (F-FH-3 — 300K reset ops per run, direct coupling to parallelism blocker), MED (F-FH-4 double autouse for API subset), POSITIVE (F-FH-1, F-FH-5) |
| Routing tag | in-rite-fix (F-FH-3 is keystone compound target — CHANGE-T1A resolves root cause per charter §7.1); preserve-status (F-FH-1, F-FH-5) |

### Category 4 — Coverage Governance

| Field | Value |
|---|---|
| Category | Coverage Governance |
| Grade | **C** |
| Anchor finding(s) | F-CG-1 (coverage-gate-theater, GLINT-003 carry-forward), F-CG-2 (missing post-merge aggregation), F-CG-3 (4 packages uncovered), F-CG-4 (9 modules uncovered) |
| Rubric criteria met / unmet | eunomia-ref canonical: F-CG-1 is coverage-gate-theater: `pyproject.toml:126` declares fail_under=80 but `test.yml:52` sets coverage_threshold=0 for sharded runs. Declared threshold is never enforced in CI. This is GLINT-003 carry-forward — a systemic governance gap, not a pace issue. F-CG-2 (no post-merge aggregation) means full-suite coverage is unmeasurable. F-CG-3+4 are correctness routing candidates (4 untested packages, 9 uncovered modules). All four findings are out-of-scope for perf-track execution per charter §3.2 and inventory §6 routing note. Grade C: systemic pattern (theater gap + missing aggregation infrastructure) but test infra foundation is intact; correctness gaps are bounded. |
| Evidence chain | F-CG-1: Swarm Lane 3 §3; `pyproject.toml:126` (fail_under=80), `test.yml:52` (coverage_threshold=0); GLINT-003. F-CG-2: Swarm Lane 3 §3. F-CG-3: `.know/test-coverage.md`. F-CG-4: `.know/test-coverage.md`. |
| Severity disposition | MED (F-CG-1 — policy declared but unenforced = false assurance; F-CG-2 — unmeasurable coverage state), LOW (F-CG-3, F-CG-4 correctness gaps) |
| Routing tag | route-/sre (F-CG-1, F-CG-2 per charter §10); route-/hygiene (F-CG-3, F-CG-4 per charter §10); not acted upon in perf-track Phase 3/4 |

### Category 5 — Semantic Adequacy

| Field | Value |
|---|---|
| Category | Semantic Adequacy |
| Grade | **B** |
| Anchor finding(s) | F-SA-1 (SCAR cluster positive), F-SA-2 (Hypothesis positive), F-SA-3 (fuzz module MED), F-SA-4 (8 permanently skipped MED), F-SA-5 (I/O isolation positive) |
| Rubric criteria met / unmet | eunomia-ref canonical: F-SA-1 (33+ SCAR regression tests inviolable, cluster intact) is a structural protection signal — tests/unit/scars/ preserved and gated per charter §8.1. F-SA-2 (Hypothesis property-based testing calibrated at max_examples=100, derandomize=True per TRIAGE-005) demonstrates intentional property coverage. F-SA-5 (all real I/O mocked — moto, respx, fakeredis) is closed positive. Negative signals: F-SA-3 (xfail strict=False on fuzz module masks regression detection; 47 pre-existing violations; 2/5 CI runs fail non-blockingly) and F-SA-4 (8 workspace tests permanently skipped due to singleton design — an acknowledged scar). Two MED negatives against three strong positives = B (minor entropy; foundation sound; isolated adequacy gaps). |
| Evidence chain | F-SA-1: `.know/test-coverage.md`; `.know/scar-tissue.md`; charter §8.1. F-SA-2: Swarm Lane 4 §2; `tests/unit/persistence/test_reorder.py` (max_examples=100). F-SA-3: Swarm Lane 4 §3; Baseline §4 (2/5 fuzz CI failures). F-SA-4: `.know/test-coverage.md`. F-SA-5: Swarm §3 item 1; Lane 4 §5. |
| Severity disposition | MED (F-SA-3 fuzz mask, F-SA-4 permanent skip), POSITIVE (F-SA-1, F-SA-2, F-SA-5) |
| Routing tag | in-rite-fix (F-SA-3 partially addressed by CHANGE-T2A fuzz budget; F-SA-4 preserve-status — acknowledged scar); preserve-status (F-SA-1, F-SA-2, F-SA-5) |

### Category 6 — Suite Velocity (PERF OVERLAY)

| Field | Value |
|---|---|
| Category | Suite Velocity |
| Grade | **D** |
| Anchor finding(s) | F-SV-1 (serial wallclock), F-SV-2 (CI shard p50 = 447s, dominant anchor), F-SV-3 (14-day stale durations), F-SV-4 (fuzz file 111.46s = 29.8% of stored total), F-SV-5 (fuzz budget ceiling), F-SV-6 (collection floor) |
| Rubric criteria met / unmet | Charter §6.1 rubric applied directly to measured anchors: (a) Serial wall-clock: fresh `tests/unit/` = 215.34s (3:35) — maps to A on raw time alone (< 5min). Stored full-suite = 374.41s (6.2min) — maps to B on stored total. Neither criterion alone drives grade below B. (b) Slowest CI shard p50 = 447.0s (Baseline §4 M-5, 5-run measurement) — falls in 300-600s band = **D** per §6.1 rubric. (c) `.test_durations` staleness = 14 days at baseline — falls in 7-21 day band = **B** per §6.1 rubric. Weakest criterion among the three is slowest shard at D. Charter §6.3 variant (weakest criterion within a category anchors the grade): grade = **D**. Charter pre-flagged D as initial expectation; confirmed empirically. |
| Evidence chain | F-SV-1: Baseline §3 M-4 (215.34s fresh unit/); Baseline §3 M-2 (374.41s stored total). F-SV-2: Baseline §4 M-5 (447.0s p50, 5-run extraction via `gh run list/view`). F-SV-3: Baseline §3 M-2 (last commit 2026-04-15, 14 days stale). F-SV-4: Baseline §3 M-6 duration table (111.46s for test_openapi_fuzz.py). F-SV-5: Swarm Lane 4 §3 (900s ceiling). F-SV-6: Baseline §3 M-3 (29.90s median, 3-run). |
| Severity disposition | HIGH (F-SV-2 — CI shard p50 at 447s drives D grade; F-SV-4 — fuzz file 143× mean pins one worker), MED (F-SV-3 stale durations, F-SV-5 fuzz ceiling risk), LOW (F-SV-1 local serial floor acceptable, F-SV-6 collection bounded) |
| Routing tag | in-rite-fix (F-SV-4 via CHANGE-T1C + CHANGE-T2A; F-SV-3 via CHANGE-T2B; F-SV-2 pytest-internal component via Tier-1 parallelism unlock); route-/sre (F-SV-2 CI infrastructure overhead component — 353s gap outside pytest-internal) |

### Category 7 — Parallelization Health (PERF OVERLAY)

| Field | Value |
|---|---|
| Category | Parallelization Health |
| Grade | **F** |
| Anchor finding(s) | F-PH-1 (loadfile band-aid), F-PH-2 (11 singletons — structural blocker), F-PH-3 (hypothesis DB process-global), F-PH-4 (module-level fuzz app/schema), F-PH-5 (4 os.environ mutations), F-PH-6 (worker duration imbalance) |
| Rubric criteria met / unmet | Charter §6.2 rubric applied: F criterion = "`--dist=loadfile` AND blocker is structural module-level global with > 5 registered singletons AND fix has > 3-5× parallel multiplier ceiling unrealized." All three conditions are met: (1) `pyproject.toml:113` declares `--dist=loadfile` as addopts (Baseline §5 anchor 1 CONFIRMED); (2) `src/autom8_asana/core/system_context.py:28` defines module-level `_reset_registry` with 11 registered singletons — 11 > 5 threshold (Baseline §5 anchor 2 CONFIRMED); (3) theoretical parallel multiplier = 3-5× unrealized (Swarm §4 §4.2, Lane 1 hypothesis 1+4). All three F-criteria met; grade = **F**. Charter pre-flagged F as initial expectation; confirmed empirically. |
| Evidence chain | F-PH-1: `pyproject.toml:113` — Baseline §5 CONFIRMED `addopts = "--dist=loadfile"`; commit c5d2930d 2026-04-10. F-PH-2: `src/autom8_asana/core/system_context.py:28` — Baseline §5 CONFIRMED `_reset_registry: list[Callable[[], None]] = []`; 11 registered singletons enumerated at Inventory §9. F-PH-3: Swarm Lane 1 §4; `tests/test_openapi_fuzz.py:72-81`. F-PH-4: `tests/test_openapi_fuzz.py:113-115` — Baseline §5 CONFIRMED `app = _create_fuzz_app()` and `schema = from_asgi(...)`. F-PH-5: Swarm Lane 1 §5. F-PH-6: Baseline §3 M-6 (111.46s fuzz duration vs 0.78s mean = 143× imbalance). |
| Severity disposition | CRITICAL (F-PH-2 + F-PH-1 together: structural blocker preventing 3-5× parallelism gain), HIGH (F-PH-4 module-level fuzz state; F-PH-3 hypothesis DB contention), MED (F-PH-5 os.environ mutations), LOW (F-PH-6 test-count imbalance — fast file) |
| Routing tag | in-rite-fix (F-PH-1, F-PH-2 via CHANGE-T1A; F-PH-4 via CHANGE-T1C; F-PH-3 via CHANGE-T1B) |

---

## §3 Weakest-Link Rollup

Charter §6.3 invariant: `Overall = min(MD, TO, FH, CG, SA, SV, PH)`

Grade mapping for min computation (A=4, B=3, C=2, D=1, F=0):

```
min(C, B, C, C, B, D, F)
  = min(2, 3, 2, 2, 3, 1, 0)
  = 0
  = F
```

**Overall Grade: F**

Parallelization Health (F) drives the overall grade. Per charter §6.3 and
VERDICT-eunomia-final-adjudication §2 EUN-003, the weakest-link invariant is
non-negotiable: an F in any single category caps Overall at F regardless of
canonical-5 strength. The canonical 5 categories span B to C — solidly mediocre
but not failing. The two perf-overlay categories (D and F) hold the engagement
floor. Even if mock discipline improved to A and coverage governance improved to A,
the Parallelization Health F would hold Overall at F until CHANGE-T1A resolves the
keystone structural blocker.

---

## §4 Compound Severity Adjudications

### Compound 1 — F-PH-2 + F-FH-3 + F-PH-1 (Keystone Chain)

**Chain**: `system_context.py:28` module-level `_reset_registry` (F-PH-2) is the
root cause of `~299,310 reset callback invocations per run` (F-FH-3), which is the
direct cause of the `--dist=loadfile` band-aid at `pyproject.toml:113` (F-PH-1) — added
2026-04-10 to prevent worker races on the shared global.

**Severity: CRITICAL**

These three findings are not independent — they form a single causal chain. The
reset callbacks fire before AND after every test (autouse function-scoped at
`tests/conftest.py:193-204`), making parallel worker isolation impossible without
the loadfile constraint. The constraint in turn caps parallelism at file-count
granularity rather than test-count granularity, forfeiting the 3-5× multiplier.

**Routing**: in-rite-fix. CHANGE-T1A (refactor `_reset_registry` to worker-local) is
the single keystone that dissolves all three findings simultaneously.

**Phase-3 ordering signal**: CHANGE-T1A MUST land before any other change in the
dependency graph per charter §7.2. The `--dist=loadfile` removal at
`pyproject.toml:113` cannot be safely executed until T1A (and T1B, T1C) resolve all
process-global shared state. No Tier-2 or Tier-3 change may precede Tier-1 completion.

### Compound 2 — F-SV-4 + F-PH-4 (Fuzz File Dual Role)

**Chain**: `tests/test_openapi_fuzz.py` is simultaneously: (a) the largest single-file
duration consumer at 111.46s = 29.8% of stored total (F-SV-4, 143× the 0.78s mean);
and (b) the source of module-level `app = _create_fuzz_app()` and `schema = from_asgi()`
at lines 113-115 that block `--dist=load` transition (F-PH-4).

**Severity: HIGH**

The dual role makes this file both a velocity drain AND a parallelism blocker. Under
`--dist=loadfile`, it pins one worker for the duration of the fuzz run. If only the
duration were the issue, it would be a medium-priority Tier-2 concern. The module-level
state making it a parallelism blocker elevates it to HIGH and promotes the corresponding
changes into Tier-1. Under `--dist=load` (post-T1A), the file would still represent
29.8% of stored duration on one worker — meaning Tier-2 fuzz budget reduction remains
independently valuable after the parallelism fix.

**Routing**: in-rite-fix. CHANGE-T1C (resolve module-level state) addresses the
parallelism dimension; CHANGE-T2A (SCHEMATHESIS_MAX_EXAMPLES=5 for PR runs) addresses
the velocity dimension. Both changes are warranted; T1C precedes T2A per charter §7.2
dependency graph.

**Phase-3 ordering signal**: T1C (with T1A, T1B) must land before T2A. T2A has no
Tier-1 dependency in logic but should not be committed before the loadfile removal
is ready, as its ROI calculation changes post-T1A ceiling-rise.

### Compound 3 — F-SV-2 + CI Overhead Gap

**Chain**: slowest CI shard p50 = 447.0s (F-SV-2, Baseline §4 M-5). Theoretical
pytest-internal floor at 4-shard split = ~94s. Gap = ~353s = 79% of current CI shard
wall-clock attributable to infrastructure overhead in
`autom8y/autom8y-workflows/satellite-ci-reusable.yml@c88caabd` (install, mypy,
spec-check, cache restore/save, xdist startup). This overhead is opaque from this
repo.

**Severity: HIGH**

The implication is structural: even after Tier-1+2 changes eliminate all
pytest-internal overhead above the 94s floor, CI shard duration will drop from ~447s
to approximately 94s + 353s overhead = 447s if infrastructure phases dominate. In
other words, suite-internal optimization alone cannot move CI shard wall-clock
proportionally. The 353s overhead is the majority of shard wall-clock. This means
the D grade in Suite Velocity has a ceiling: Tier-1+2 can potentially push pytest
time from ~94s to near zero (theoretical), but CI wall-clock will not descend below
the infrastructure floor.

**Routing**: SPLIT. Pytest-internal component → in-rite-fix (Tier-1+2 changes in this
engagement). Infrastructure overhead component → route-/sre (reusable-workflow
optimization in `autom8y/autom8y-workflows/satellite-ci-reusable.yml@c88caabd`).
Phase-5 §9.2 per-job CI timing re-extraction will attribute the post-execution delta
between pytest-internal savings and infrastructure savings. If non-pytest overhead
dominates post-execution, PASS-WITH-FLAGS + /sre routing per charter §9.5.

**Phase-3 ordering signal**: This compound does not impose an ordering constraint
within the perf-track dependency graph, but it imposes a verification expectation:
Phase-5 must measure CI delta per-job (charter §9.2), not just suite-internal delta,
to avoid PASS-theater. If CI wall-clock does not proportionally improve, the /sre
routing recommendation becomes urgent.

---

## §5 Routing Recommendations

### /hygiene

| Finding | Evidence | Item |
|---|---|---|
| F-MD-1 | Swarm Lane 5 §3; Inventory §3 — 3,110 patch() sites, 67 spec'd (97.8% unspec) | spec= adoption campaign; SCAR-026 surface |
| F-MD-3 | Swarm Lane 5 §4; `.know/test-coverage.md` GLINT-004 — 11 bespoke MockTask vs `tests/_shared/mocks.py:10` | MockTask consolidation; 11:1 proliferation index |
| F-CG-3 | `.know/test-coverage.md` — 4 packages with no test directories | Correctness gap routing; `_defaults/`, `batch/`, `observability/`, `protocols/` |
| F-CG-4 | `.know/test-coverage.md` — 9 modules with no dedicated test files | Correctness gap routing; within-package coverage gaps |

### /sre

| Finding | Evidence | Item |
|---|---|---|
| F-CG-1 | Swarm Lane 3 §3; `pyproject.toml:126`, `test.yml:52` — GLINT-003 | Coverage-threshold theater; fix requires CI workflow authorship |
| F-CG-2 | Swarm Lane 3 §3 — no post-merge aggregation job | Post-merge coverage aggregation infrastructure |
| F-SV-2 (CI overhead component) | Baseline §4 M-5 — 353s gap between 447s p50 and 94s pytest floor | Reusable-workflow optimization in `autom8y/autom8y-workflows/satellite-ci-reusable.yml@c88caabd` |
| F-SV-2 (shard expansion) | Swarm Lane 3 §2 — 4→8 shard expansion feasibility | Shard topology expansion; requires reusable-workflow visibility eunomia lacks |

### /10x-dev

CP-01 carry-forward (VERDICT §6.1): `tests/unit/lambda_handlers/test_import_safety.py`
lazy-load regression guard. Out-of-rite for this engagement; named for routing
completeness only.

---

## §6 Defer-Watch Candidates

Per charter §4.3: ASSESS surfaces candidates only. `.know/defer-watch.yaml` MUST NOT
be mutated at ASSESS tier. User adjudicates promotion.

1. **Tier-1 rejection at executor halt**: If CHANGE-T1A at Phase 4 surfaces
   unanticipated cross-subsystem coupling requiring src-tree changes outside
   `system_context.py` (charter §11.2 risk), executor halts per charter §8.4.
   Watch-trigger: executor HALT event on T1A → re-grade Parallelization Health at
   next eunomia engagement with revised scope authority.

2. **CI overhead reduction deferral**: If Phase-5 §9.2 measurement confirms non-pytest
   CI overhead dominates post-execution delta AND /sre does not engage within 30 days
   of VERDICT issuance → re-route through eunomia perf-track v2 with explicit CI-shape
   scope. Suite Velocity cannot reach above C without addressing the 353s infrastructure
   floor; this is the leading indicator of a second engagement requirement.

3. **Fuzz xfail mask**: F-SA-3 (xfail strict=False on fuzz module masking regression
   detection; 47 pre-existing violations). Watch-trigger: if violation count grows
   past 60 at any Phase-5 re-measurement → route to /hygiene as semantic adequacy
   regression, not fuzz noise.

---

## §7 Phase-3 Sequencing Implication

Charter §7 invariant: Tier-1 precedes Tier-2/3. The assess-altitude reasoning is:

An F grade in Parallelization Health cannot reach C without resolving the keystone
chain (F-PH-2 + F-FH-3 + F-PH-1 compound, §4 Compound 1). The F arises from three
simultaneous criteria being met — not from one marginal threshold. Tier-2 and Tier-3
changes optimize within the existing `--dist=loadfile` ceiling. Their ROI calculations
were derived at pre-Tier-1 parallelism. After CHANGE-T1A unlocks `--dist=load` and
the parallelism multiplier rises to 3-5×, Tier-2 ROI re-computes against a higher
ceiling: for example, CHANGE-T2C (split `test_insights_formatter.py`) yields
loadfile-imbalance relief that attenuates under `--dist=load` because the formatter
file's 272 fast tests (0.23s stored) redistribute across workers. Similarly,
CHANGE-T3A (parametrize-promote) yields collection-time savings whose relative
wall-clock fraction changes post-ceiling-rise.

The SV grade (D, driven by CI shard p50 = 447s) cannot reach A or B without:
(a) Tier-1 parallelism unlock reducing pytest-internal CI time from ~94s toward the
3-5× multiplier floor, AND (b) /sre addressing the 353s infrastructure overhead.
Tier-1 is necessary but not sufficient for SV grade improvement to A; /sre is the
co-required condition. Tier-2/3 are not capable of moving SV grade above D on their
own because the CI shard wall-clock is dominated by infrastructure overhead that
Tier-2/3 cannot touch.

Therefore the dependency graph in charter §7.2 (T1A → T1B, T1C → loadfile removal
→ T2A, T2B, T2C → T3A) is not merely recommended but structurally required for
correct ROI accounting.

---

## §8 Open Assessment Risks

1. **F-SV-2 grade conditionality on CI per-job attribution**: The D grade in Suite
   Velocity is anchored to the CI shard p50 of 447.0s (Baseline §4 M-5). This
   measurement extracts per-job wall-clock from `gh run view` but cannot decompose
   the per-shard time between pytest-internal and infrastructure phases within the
   reusable workflow. Phase-5 §9.2 re-extracts this. If post-execution CI delta shows
   pytest was only 94s of the 447s (i.e., nearly all savings came from Tier-1+2),
   but CI wall-clock only drops to ~350s, the SV grade remains D post-execution —
   not a grading error but a scope-limit of the perf-track engagement.

2. **F-PH grade dependency on singleton refactor producing no production-code coupling**:
   The F grade in Parallelization Health is resolved only if CHANGE-T1A can be
   executed within the scoped `system_context.py` file per charter §11.2. If the
   refactor surfaces coupling to other production files (e.g., singleton consumers
   that hold references to the module-level registry), the F persists and the
   engagement must pause for user re-authorization per charter §8.4. This risk is
   MEDIUM (11 registered singletons across 11 distinct subsystems creates non-trivial
   coupling surface). Mitigation: consolidation-planner must trace all 11 singleton
   registration sites before authoring CHANGE-T1A spec.

3. **F-MD grade could shift to D if SCAR-026 is re-interpreted**: Current C grade for
   Mock Discipline holds because (a) F-MD-1 (97.8% unspec) is correctly scoped as
   correctness debt routed to /hygiene, not a pace blocker graded in perf-track
   context, and (b) F-MD-4 teardown is sound. If the verification-auditor or a
   subsequent engagement re-classifies F-MD-1 as a D-level structural failing (e.g.,
   because spec= absence generates false-confidence in test coverage adequacy that
   interacts with F-CG findings), Mock Discipline drops to D and the canonical-5
   aggregate worsens but does not change Overall (PH F still dominates).

4. **Baseline reproducibility for Phase-5 delta**: Baseline M-4 (215.34s) was one
   fresh run, not a 3-run median per charter §5.2 specification (relaxation documented
   at Baseline §2). If post-execution measurement uses a 3-run median, comparison
   is methodologically asymmetric. Phase-5 auditor should either (a) use a single
   fresh run to match Baseline M-4 method, or (b) run 3 repetitions and accept that
   the delta confidence interval may span the PASS/PASS-WITH-FLAGS boundary.

5. **F-FH-4 double-autouse scope**: The API subdirectory conftest double-autouse
   (F-FH-4) was identified from Swarm Lane 2 §3 but not directly confirmed with a
   file:line anchor in the baseline. If the double-autouse was removed by a recent
   commit (the working tree shows hygiene-branch modifications), the compound overhead
   estimate could be lower. This does not change the F in PH or D in SV but may
   affect the F-FH-3 invocation count estimate by a factor of ~1.0 to ~1.1.

---

## §9 Assessment vs Prior Eunomia Close

The prior eunomia engagement closed 2026-04-29 with VERDICT-eunomia-final-adjudication
issuing an overall F grade driven by Safety Configuration F at the fleet (pipeline-track)
level. That engagement was pipeline-scoped; its F grade and its findings are CLOSED and
are not contested here. This perf-track assessment is strictly test-track scoped per
charter §2 (track locked, pipeline track adjudicated CLOSED). The pipeline-track Safety
Configuration F finding does not appear in this 7-category test-track schema. The
current engagement's F grade is independently derived from Parallelization Health
(charter §6.2 criteria, structural module-level singleton blocker) and has no overlap
with the pipeline-track Safety Configuration finding. Two distinct F grades for two
distinct reasons across two distinct engagements; the prior one is CLOSED.

---

## §10 Source Manifest

| Role | Artifact | Path |
|---|---|---|
| Governing rubric source | PYTHIA INAUGURAL CONSULT (perf-track charter) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf.md` |
| Predecessor inventory | Test Ecosystem Inventory (34 findings, 7 categories) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/INVENTORY-test-perf-2026-04-29.md` |
| Predecessor baseline | Empirical baseline (STRONG; direct measurement) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/BASELINE-test-perf-2026-04-29.md` |
| Compound-severity reasoning anchor | Explore Swarm Synthesis (5-lane opportunity map) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/EXPLORE-SWARM-SYNTHESIS-perf-2026-04-29.md` |
| Prior VERDICT (carry-forward integrity reference) | Structural-cleanliness adjudication (CLOSED) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md` |

---

*Assessment authored 2026-04-29 by entropy-assessor. STRONG evidence-grade per
multi-source corroboration: charter §6 rubric (external authority) + STRONG-graded
empirical baseline (rite-disjoint measurement substrate) + 5-lane Explore swarm
(rite-disjoint synthesis). Receipt-grammar applied throughout: every grade cites
(a) charter rubric criterion, (b) inventory finding ID, (c) baseline measurement
where applicable. F-HYG-CF-A discipline observed: no wave-level tokens without
per-item anchors. Ready for consolidation-planner Phase-3 dispatch.*
