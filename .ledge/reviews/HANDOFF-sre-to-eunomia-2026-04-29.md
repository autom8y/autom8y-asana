---
artifact_id: HANDOFF-sre-to-eunomia-2026-04-29
schema_version: "1.0"
type: handoff
source_rite: sre
target_rite: eunomia
handoff_type: execution
priority: critical
blocking: true
initiative: "test-perf v2 — auth-isolation defect fix + verdict re-discharge"
created_at: "2026-04-29T22:10:00Z"
status: in_progress
handoff_status: accepted
accepted_at: "2026-04-29T22:12:57Z"
accepted_by_session: session-20260430-001257-0f7223d6
source_artifacts:
  - .ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md
  - .ledge/reviews/VERDICT-test-perf-2026-04-29.md
  - .ledge/reviews/HANDOFF-eunomia-to-sre-2026-04-29.md
  - .ledge/reviews/BASELINE-test-perf-2026-04-29.md
  - .sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre.md
session_id: session-20260429-190827-422f0668
provenance:
  - source: VERDICT-test-perf-2026-04-29-postmerge-supplement (SRE-001 measurement output; rite-disjoint authorship)
    type: artifact
    grade: strong
  - source: gh actions run 25135367735 (PR #44 attempt-1 failure evidence)
    type: code
    grade: strong
  - source: gh actions main HEAD e27cbf2d (regression provenance — main green, PR red)
    type: code
    grade: strong
evidence_grade: strong
items:
  - id: EUN-V2-001
    summary: "Fix AUTH-ISOLATION-DIST-LOAD-REGRESSION — test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503 fails deterministically under --dist=load (assertion: 401 == 503)"
    priority: critical
    acceptance_criteria:
      - "Reproduce the failure deterministically locally: pytest -n 4 --dist=load tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503 fails with assertion 401 == 503"
      - "Root-cause traced: identify the auth fixture / setup pattern that depends on co-location with another test under loadfile distribution. Likely surfaces at the intersection of (a) `_reset_registry` worker-local refactor commit `367badba`, (b) `--dist=load` switch commit `8f99a801`, (c) `routes/resolver.py` auth dependency"
      - "Fix landed on branch `eunomia/test-perf-2026-04-29` (extending PR #44) — likely a fixture-isolation change in tests/unit/api/conftest.py or tests/conftest.py that ensures auth-token / dependency-override is worker-scoped"
      - "After fix: pytest -n 4 --dist=load tests/unit/ passes 100% (12,713 unit tests + 200 fuzz xfail-allowed); SCAR cluster preservation invariant unchanged"
      - "PR #44 CI shard 1/4 passes after fix lands — verify via `gh pr checks 44`"
      - "Out-of-scope refusal preserved: do NOT modify routes/resolver.py production code; the fix MUST be in test/fixture surface only. If production-code root cause discovered: HALT and route to /10x-dev for proper auth-state-management refactor"
    notes: |
      This is the load-bearing finding from SRE-001 §9.2 measurement. The
      postmerge-supplement adjudicated PASS-WITH-FLAGS-NEW because:
      
      - Local pytest -n 4 --dist=load PASSED (12,918 tests; verified during executor run)
      - PR #44 CI shard 1/4 FAILED deterministically (N=2 attempts, 0.5% timing delta)
      - Failure is BRANCH-INTRODUCED (main HEAD `e27cbf2d` shows all 4 shards green)
      
      Hypothesis from supplement §6.4: T1A's worker-local `_reset_registry`
      refactor + T1D's `--dist=load` switch interact with `routes/resolver.py`
      auth dependency in a way that `--dist=loadfile` masked by co-locating
      auth-fixture and resolver tests on the same xdist worker. Under load
      mode, they distribute, leaving the resolver-test worker un-seeded.
      
      The local-vs-CI divergence (local passes, CI fails) is itself the SCAR-026-class
      blindspot — a hidden test-isolation defect that loadfile masked. Fixing
      it properly is exactly the discipline that makes the perf gain durable.
      
      Why eunomia and not /sre: the defect is pytest-internal (auth fixture ×
      xdist worker × _reset_registry interaction). /sre's authority is bounded
      to CI-shape (workflow YAML, runner config); test-fixture refactor is
      out-of-scope per /sre charter §8.4.
      
      Why eunomia and not /10x-dev or /hygiene: this is a perf-engagement
      regression specifically caused by Tier-1 changes (T1A + T1D). The eunomia
      rite that authored those changes is the structurally-correct owner of
      the fix. /10x-dev would be appropriate only if root cause is in
      production code (routes/resolver.py auth dependency), per acceptance
      criterion §6.
      
      Branch context: PR #44 is OPEN. Fix should commit on the same branch
      `eunomia/test-perf-2026-04-29` (not a fresh branch off main). PR will
      auto-update; CI re-runs on push.
    estimated_effort: "moderate (4-8h): reproduce + root-cause + fix + verify locally + verify CI"
    dependencies: []

  - id: EUN-V2-002
    summary: "Re-discharge §9.2 verdict supplement after EUN-V2-001 fix — promote parent VERDICT-test-perf from PASS-WITH-FLAGS-NEW to PASS-CLEAN"
    priority: high
    acceptance_criteria:
      - "After EUN-V2-001 lands and PR #44 CI shows all 4 shards passing: re-trigger workflow runs (gh run rerun, OR push trigger) until 5 successful CI runs are captured against the new HEAD"
      - "Per-job timing extraction repeated per VERDICT supplement §2 methodology: avg/p50/p95 across 5 runs"
      - "Delta vs BASELINE §4 (slowest-shard p50 = 447s pre-engagement) re-computed under FIXED state"
      - "Author or update `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` with §8 'POST-FIX MEASUREMENT' section showing the corrected delta + final attribution split"
      - "Promotion verdict adjudicated: PASS-CLEAN-PROMOTION if pytest-internal delta ≥40% of CI shard reduction (charter §9.3 criterion). PASS-WITH-FLAGS-CARRIED if <40% (then SRE-002 sized scope confirmed)"
      - "If PASS-CLEAN-PROMOTION: parent VERDICT-test-perf-2026-04-29 frontmatter updated `overall_verdict: PASS-WITH-FLAGS → PASS-CLEAN`; verdict §1 amended with promotion timestamp + supplement reference"
    notes: |
      The supplement found pytest-internal is ~93.3% of CI shard wallclock
      (BASELINE §4's 21% estimate was wrong — the 94s theoretical floor
      arithmetic was 4× under). This means local-pytest optimization SHOULD
      translate to CI gains directly — but EUN-V2-001's regression masks that
      gain. After the fix, expect ~40-60% CI shard wallclock reduction
      (vs BASELINE 447s slowest-shard p50 → ~180-280s post-fix).
      
      EUN-V2-002 is the structural close that the parent VERDICT requires.
      Without it, the verdict carries PASS-WITH-FLAGS forward indefinitely.
    estimated_effort: "small (2-3h): mostly waiting on CI reruns; gh CLI extraction is fast"
    dependencies:
      - EUN-V2-001  # cannot re-discharge until the fix lands and CI is green

  - id: EUN-V2-003
    summary: "BASELINE §4 attribution correction — update substrate to reflect empirical pytest-internal-vs-infrastructure split (~93/7 not ~21/79)"
    priority: medium
    acceptance_criteria:
      - "Author `.ledge/reviews/BASELINE-test-perf-2026-04-29-supplement.md` (or amend BASELINE-test-perf-2026-04-29.md §4 with a corrigendum block) reflecting empirical SRE-001 measurement"
      - "Document the source of the original error: BASELINE §4 used `~94s theoretical floor` arithmetic (94s × 4 shards = 376s for ideal parallel pytest). Empirical PR #44 attempt-1 showed pytest-internal time per shard ≈ 363s, NOT 94s. The 4× under-estimate came from the assumption that --dist=load would distribute tests at the test-granularity ideal — which it does, but per-test overhead (fixture setup + autouse + bootstrap) was not accounted for"
      - "Update VERDICT-test-perf-2026-04-29 §11.1 risk-discharge framing: the 'CI-overhead opacity HIGH' risk discharged with INVERTED finding (pytest dominant, not infrastructure)"
      - "Update HANDOFF-eunomia-to-sre-2026-04-29 SRE-002 scope reduction note (~6% headroom in pure infrastructure, not ~30%)"
    notes: |
      Substrate-correction work that future engagements will benefit from.
      Recording the underlying error (theoretical vs empirical pytest cost)
      improves the next baseline-capturing engagement's accuracy.
      
      Lower priority than EUN-V2-001/002 because it's documentation hygiene,
      not load-bearing for the verdict close. Can be deferred to engagement-
      close if sprint capacity is constrained.
    estimated_effort: "small (1-2h): substrate authoring"
    dependencies: []

tradeoff_points:
  - attribute: "Test-isolation rigor vs --dist=load parallelism"
    tradeoff: "The Tier-1 keystone work assumed worker-local _reset_registry would suffice for full --dist=load safety. SRE-001 measurement revealed a latent auth-fixture coupling that loadfile masked by co-location. Properly fixing the fixture isolation is required to durably realize the parallelism gain."
    rationale: "Local-passes-but-CI-fails is the SCAR-026-class blindspot the prior eunomia structural-cleanliness engagement flagged at scan altitude. The perf engagement preserved the parallelism keystone but the test-fixture surface required additional isolation work that wasn't visible without merge-time CI. EUN-V2-001 closes this gap."
  - attribute: "Verdict promotion vs sprint scope"
    tradeoff: "EUN-V2-002 (verdict re-discharge) is structurally required to close the parent VERDICT, but operationally simple after EUN-V2-001 lands. Including it in this v2 handoff (vs deferring to a subsequent engagement) front-loads the sprint scope to ensure structural close in one pass."
    rationale: "Splitting the fix and the re-discharge across separate engagements would leave the parent VERDICT in PASS-WITH-FLAGS-NEW state for an extended period. Bundling them ensures the close-gate fires immediately after the fix lands."
---

## Context

The /sre engagement (session `session-20260429-190827-422f0668`) executed Sprint-1 SRE-001 §9.2 measurement protocol against PR #44 (the open PR for eunomia perf branch). Measurement adjudicated **PASS-WITH-FLAGS-NEW** (not PASS-CLEAN-PROMOTION) because:

1. **Empirical attribution inversion**: BASELINE §4's 21%-pytest-internal estimate was 4× under-estimated. Actual: pytest-internal is ~93.3% of CI shard wallclock; infrastructure is ~6.7%. This is GOOD news for the perf engagement (local optimization SHOULD translate directly to CI), BUT...

2. **Deterministic regression revealed**: PR #44 CI shard 1/4 fails on `tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503` with assertion `401 == 503`. Confirmed N=2 attempts (0.5% timing delta = deterministic, not flaky). Branch-introduced (main HEAD green; PR red).

3. **Routing implication**: the defect is pytest-internal (auth fixture × xdist worker × `_reset_registry` interaction). /sre's authority surface is bounded to CI-shape; test-fixture refactor is out-of-scope. Routes back to **eunomia** for v2 re-engagement.

The supplement at `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` documents the full measurement methodology + attribution + new flag. This handoff is the formal route-back artifact.

## Item Prioritization

**Sprint v2 (single sprint, sequential)**:
1. **EUN-V2-001** (CRITICAL, blocking) — fix AUTH-ISOLATION-DIST-LOAD-REGRESSION. Restores PR #44 CI shard 1/4 to green.
2. **EUN-V2-002** (HIGH, blocked-by V2-001) — re-discharge §9.2 supplement; promote parent VERDICT to PASS-CLEAN.
3. **EUN-V2-003** (MEDIUM, parallel) — BASELINE §4 attribution correction; substrate hygiene.

## Notes for Eunomia Rite

### Branch context
- PR #44 is OPEN at https://github.com/autom8y/autom8y-asana/pull/44
- Fix MUST commit on the same branch `eunomia/test-perf-2026-04-29` (extending the existing 8 commits, not branching anew)
- PR auto-updates on push; CI re-fires on push trigger

### Authority boundary (preserved from parent perf charter §3)
- **In-scope**: test/fixture surface (`tests/conftest.py`, `tests/unit/api/conftest.py`, possibly the failing test file itself for assertion-level fix); BASELINE supplement authoring; VERDICT supplement amendment
- **Out-of-scope**: production code (`src/autom8_asana/api/routes/resolver.py` and any other src file beyond the parent charter's `core/system_context.py` allowance). If root cause is in production-code auth dependency: HALT and route to /10x-dev for proper auth-state-management refactor.

### Charter inheritance
- Pattern-6 drift-audit re-dispatch (per VERDICT-eunomia-final-adjudication §5)
- SCAR cluster preservation through any test-fixture changes
- Halt-on-fail discipline at every commit
- Single-commit-per-change atomicity

### What NOT to do
- Do NOT revert any of the 8 commits on `eunomia/test-perf-2026-04-29` — those have STRONG verification per parent VERDICT §3-§5. The fix EXTENDS, does not replace.
- Do NOT modify `pyproject.toml:113` back to `--dist=loadfile` — Path A "rollback" was explicitly rejected when user chose Path B (fix forward).
- Do NOT touch CI shape or workflow YAML — that remains /sre territory; this engagement is bounded to test-fixture work.
- Do NOT close the supplement artifact `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` — amend it with §8 POST-FIX MEASUREMENT after EUN-V2-002 lands.

## Cross-Coordination

- **Parallel /hygiene HANDOFF** (`.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md`): independent of this v2; can run in parallel.
- **Parallel /sre HANDOFF** (`.ledge/reviews/HANDOFF-eunomia-to-sre-2026-04-29.md`): SRE-001 closed (this artifact is its discharge route-back); SRE-002 SCOPE SHRINKS dramatically (per supplement §6); SRE-003/004/005 remain valid but with revised expectations. Recommend /sre re-engages AFTER EUN-V2-002 promotion to PASS-CLEAN; will re-author SRE-001-discharged HANDOFF-RESPONSE at that time.

## Expected Outcomes

- **EUN-V2-001 closed**: PR #44 CI shard 1/4 passes; full 4-shard run succeeds; auth-isolation defect documented as fixed in test/fixture layer.
- **EUN-V2-002 closed**: Parent VERDICT-test-perf-2026-04-29 promoted PASS-WITH-FLAGS → PASS-CLEAN. Supplement §8 documents post-fix per-job timings showing the projected ~40-60% CI shard wallclock reduction realized.
- **EUN-V2-003 closed**: BASELINE substrate corrected; future engagements have accurate pytest-vs-infrastructure attribution.

Aggregate impact: PR #44 mergeable; parent eunomia perf engagement closes at PASS-CLEAN; CI shard p50 lands in target band (180-280s vs 447s baseline = ~40-60% reduction).

## Background

Full supplement substrate at `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` (494 lines, evidence-grade STRONG). Includes:
- §3 per-job timing table (PR #44 attempt-1 measurement)
- §4 attribution analysis (~93/7 split inverting BASELINE §4 estimate)
- §5 promotion adjudication (PASS-WITH-FLAGS-NEW with conjunct-1+2 falsification rationale)
- §6 open residuals (sample-size flag, attribution correction recommendation, auth-isolation triage)
- §7 SVR receipts for the new flag
- §8 (TO BE AUTHORED by EUN-V2-002 after fix lands)

## Contact

/sre session: `session-20260429-190827-422f0668` (auto-wrapped on rite-switch to eunomia). Re-engage /sre after EUN-V2-002 PASS-CLEAN promotion if SRE-002/003/004/005 sprint-2 work resumes. New /eunomia v2 session to be created post this handoff acceptance.
