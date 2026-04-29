---
artifact_id: HANDOFF-eunomia-to-hygiene-2026-04-29
schema_version: "1.0"
type: handoff
source_rite: eunomia
target_rite: hygiene
handoff_type: execution
priority: medium
blocking: false
initiative: "test-suite efficiency optimization (perf-track residual cleanup)"
created_at: "2026-04-29T17:01:00Z"
status: proposed
handoff_status: pending
source_artifacts:
  - .ledge/reviews/VERDICT-test-perf-2026-04-29.md
  - .ledge/reviews/BASELINE-test-perf-2026-04-29.md
  - .sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf.md
  - .sos/wip/eunomia/PLAN-test-perf-2026-04-29.md
  - .sos/wip/eunomia/EXPLORE-SWARM-SYNTHESIS-perf-2026-04-29.md
session_id: session-20260429-161352-83c55146
provenance:
  - source: VERDICT-test-perf-2026-04-29 §6
    type: artifact
    grade: strong
  - source: PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf §10
    type: artifact
    grade: strong
  - source: BASELINE-test-perf-2026-04-29 §3
    type: artifact
    grade: strong
evidence_grade: strong
items:
  - id: HYG-001
    summary: "Codify SCAR marker — close drift between .know/test-coverage.md '33+ SCAR regression tests' claim and the operationally-absent @pytest.mark.scar in code"
    priority: high
    acceptance_criteria:
      - "Decision adjudicated: register-and-apply (define `@pytest.mark.scar` in pyproject.toml + apply to the documented 33+ regression tests) OR remove-the-claim (update `.know/test-coverage.md` to reflect operational state)"
      - "If register-and-apply: pyproject.toml `[tool.pytest.ini_options].markers` section lists `scar: regression test for documented production failure`"
      - "If register-and-apply: each of the 33+ documented SCAR tests carries `@pytest.mark.scar` (cross-ref `.know/scar-tissue.md` for canonical list)"
      - "If register-and-apply: `pytest -m scar --collect-only -q` returns N >= 33 (no longer vacuous)"
      - "If remove-the-claim: `.know/test-coverage.md` line referencing 'SCAR regression tests' removed or qualified"
      - "Decision documented in commit message with chosen interpretation rationale"
    notes: |
      Surfaced by VERDICT-test-perf §5 deviation 1. The eunomia perf engagement
      attempted `pytest -m scar` per charter §8.1 inviolable constraint. Marker
      didn't exist; the executor substituted full unit-suite passing (12,713
      preserved) as the spirit-equivalent. PASS-WITH-FLAGS verdict cites this
      as the load-bearing flag.

      Either resolution is valid. Pick one and commit. Do NOT leave the drift.
    estimated_effort: "register-and-apply: 1-2 hours (manual marker application across 33+ files); remove-the-claim: 15 min (single doc edit)"

  - id: HYG-002
    summary: "Mock spec= adoption campaign — apply spec= to root mock fixtures and high-density test files (SCAR-026 correctness surface)"
    priority: medium
    acceptance_criteria:
      - "Root mock fixtures at `tests/conftest.py:98-123` (mock_http, logger, config, auth_provider) carry `spec=` against canonical types"
      - "Top-5 highest-density unspec'd files spec'd: `tests/integration/test_lifecycle_smoke.py` (133 instances), `tests/unit/lifecycle/test_engine.py` (100), `tests/unit/lambda_handlers/test_workflow_handler.py` (105), `tests/unit/lifecycle/test_hydration.py` (62), `tests/unit/cache/test_workspace_registry.py` (48)"
      - "Repo-wide `MagicMock(spec=` count increased from current 66 toward 500+ target (charter §10)"
      - "Each file's tests pass post-spec'ing (mock interface drift surfaces if any — that is the intended SCAR-026 mitigation)"
      - "If spec'ing reveals broken interface assumptions: file separate sub-issue per finding rather than absorb silently"
    notes: |
      Source: VERDICT §6 routing + EXPLORE-SWARM-SYNTHESIS Lane 5 (97.8% unspec
      rate confirmed; 3,110 mock sites with 67 spec'd). This is correctness
      debt, not pace work — Lane 5 §8 bounded pace impact at 2-8%. Eunomia
      perf-track did NOT touch this surface per charter §3.2.2.

      SCAR-026 exposure: unspec'd mocks accept attribute access on non-existent
      methods, allowing tests to pass on interfaces that no longer exist. This
      is the structural reason a real API change can pass through CI silently.

      Approach as a campaign: file-by-file or directory-by-directory, /task
      sized increments. Don't try to do all 3,000+ sites in one PR.
    estimated_effort: "per /task: 2-4 hours per high-density file; campaign overall: 2-3 sprints of incremental work"

  - id: HYG-003
    summary: "MockTask consolidation — eliminate 11 bespoke MockTask redefinitions in favor of canonical at tests/_shared/mocks.py:10"
    priority: low
    acceptance_criteria:
      - "All 11 bespoke MockTask classes removed from their files (list in `.know/test-coverage.md` GLINT-004)"
      - "All consumers import from `tests/_shared/mocks` (canonical)"
      - "If canonical MockTask lacks attributes used by bespoke versions, canonical is extended (superset of all current bespoke schemas) rather than splitting into multiple canonicals"
      - "Each affected test file's tests pass post-migration"
      - "Convention added to `.know/conventions.md`: 'New tests requiring MockTask MUST import from tests/_shared/mocks'"
    notes: |
      Source: GLINT-004 in `.know/test-coverage.md`. 11 bespoke files identified
      (per Lane 5 §4 / inventory F-MD-3). Divergence shapes vary: some are
      subset, some superset, some divergent (different attributes entirely).

      Strategy: extend canonical to be a superset (all attributes used by ANY
      bespoke), then migrate consumers. This avoids the "multiple canonicals"
      anti-pattern.

      Bespoke files (from `.know/test-coverage.md`):
        - tests/unit/dataframes/test_cascading_resolver.py:34
        - tests/unit/dataframes/test_resolver.py:58
        - tests/unit/automation/test_templates.py:24
        - tests/unit/automation/test_onboarding_comment.py:19
        - tests/unit/automation/test_pipeline_hierarchy.py:77
        - tests/unit/automation/test_pipeline.py:72
        - tests/unit/automation/test_assignee_resolution.py:18
        - tests/unit/automation/test_integration.py:103
        - tests/integration/test_unit_cascade_resolution.py:61
        - tests/integration/test_platform_performance.py:52
        - tests/integration/test_cascading_field_resolution.py:43
    estimated_effort: "1 task per file (~30-60 min each); 11 task increments OR 1 sprint"

  - id: HYG-004
    summary: "Parametrize-promote 4 adversarial test files (DEFER-T3A carry-forward from perf engagement)"
    priority: low
    acceptance_criteria:
      - "tests/unit/test_tier1_adversarial.py: TestModelRequiredFields class (lines 54-96, 14 tests) collapsed via @pytest.mark.parametrize over model classes"
      - "tests/unit/test_tier2_adversarial.py: signature validation cluster (lines 144-241, 11 tests) collapsed via @pytest.mark.parametrize over (body, secret, signature) tuples"
      - "tests/unit/test_batch_adversarial.py: upload edge-case cluster (lines 356-438, 12 tests) collapsed via @pytest.mark.parametrize"
      - "tests/unit/test_config_validation.py: rejection clusters (lines 43-71 + 110-138, 28 tests) collapsed via @pytest.mark.parametrize over value ranges"
      - "Net test count reduction: 295 -> ~80 parametrized cases; assertion specificity preserved"
      - "Coverage delta >= 0 (no coverage loss)"
      - "All affected tests pass post-promotion"
    notes: |
      Source: PLAN-test-perf-2026-04-29 §11 RISK-DEFER-T3A. Originally Tier-3
      in the perf-track plan; deferred during execution because (a) ROI is
      collection-time-only with bounded wallclock impact (~few hundred ms vs
      Tier-1's 3-5x multiplier), (b) 4 sub-specs would have exceeded the lean
      plan budget, (c) verification-auditor PASS-WITH-FLAGS already landed
      without it.

      Now appropriate for /task-sized hygiene work since the perf engagement
      already delivered the headline wallclock improvement. This is pure
      compression hygiene; no new ROI projection — it's about test-count
      compression for maintenance velocity.

      Each file is one /task. Order doesn't matter; all 4 are independent.
    dependencies: []
    estimated_effort: "1 task per file (~2-4 hours each, 4 tasks total); SCAR-safe (no behavioral change)"

tradeoff_points:
  - attribute: "Pace vs Correctness"
    tradeoff: "Eunomia perf-track explicitly excluded mock-spec adoption (HYG-002) from scope per charter §3.2.2 to keep authority surface bounded to system_context.py. Hygiene picks up the correctness debt."
    rationale: "Mock-spec adoption is high-touch (3,000+ sites) and the perf engagement's bounded src-tree authority would have been violated. Hygiene rite is the canonical home for this campaign per ecosystem routing tables."
  - attribute: "Velocity vs Compression"
    tradeoff: "DEFER-T3A (HYG-004) was excluded from perf-track because its ROI is bounded to collection-time only; perf engagement chose to ship -49% wallclock without it rather than delay the keystone."
    rationale: "Test-count compression is real maintenance value but does not move CI wallclock proportionally. Decoupling lets the headline perf delta land first; compression follows as hygiene."
---

## Context

The eunomia perf-track engagement (session `session-20260429-161352-83c55146`) closed 2026-04-29 with PASS-WITH-FLAGS verdict. **6 atomic CHANGE specs landed on branch `eunomia/test-perf-2026-04-29` delivering 48.72% local-pytest wallclock reduction** (374s → 192s under `-n 4 --dist=load`). Charter §10 pre-named four scope items routed to /hygiene at close; this handoff formalizes them.

User invocation framing: "/cross-rite-handoff --to=hygiene for /task residual cleanup" — items are scoped for incremental /task-by-task pickup, NOT a sprint orchestration.

## Item Prioritization

Execute in this order (strictly by priority, no inter-item dependencies):

1. **HYG-001** (HIGH) — SCAR marker codification. This is the load-bearing flag from VERDICT §5 deviation 1; resolves a documentation-vs-operational drift that will recur as a flag in any future eunomia engagement until adjudicated.
2. **HYG-002** (MEDIUM) — Mock spec= adoption campaign. Long-running; pick high-density files first.
3. **HYG-003** (LOW) — MockTask consolidation. Independent of HYG-002.
4. **HYG-004** (LOW) — Parametrize-promote DEFER-T3A. Pure compression; do when other items idle.

## Notes for Hygiene Rite

### Branch context
- The perf-track branch `eunomia/test-perf-2026-04-29` is **unmerged** as of handoff creation. Hygiene work should branch off **main** (or off the perf branch if hygiene picks up before perf merges — make that call empirically based on merge timing).
- If hygiene work touches the same files as perf-track work: rebase coordination is on the picking-up agent.

### Charter §8 inviolable constraints (carry forward)
- 33+ SCAR regression tests are inviolable. HYG-001 specifically operationalizes the marker that protects them.
- Drift-audit re-dispatch discipline: per VERDICT-eunomia-final-adjudication-2026-04-29 §5 Pattern-6 carry-forward, re-run drift-audit at each /task dispatch time.

### What NOT to do
- Do NOT modify production code outside test surface (HYG-002 may surface interface drift requiring src changes — file as separate sub-issue per HYG-002 acceptance criteria, do not absorb silently)
- Do NOT touch CI shape (`.github/workflows/`, reusable workflows) — that's /sre territory per VERDICT §6 and a parallel handoff
- Do NOT re-derive baseline measurements — use BASELINE-test-perf-2026-04-29 as authoritative for any wallclock reasoning

## Expected Outcomes

- HYG-001 resolved: future eunomia engagements no longer hit the vacuous-SCAR flag
- HYG-002 in flight: SCAR-026 surface area shrinks as adoption progresses (multi-sprint horizon acceptable)
- HYG-003 closed: 11 bespoke MockTask redefinitions consolidated; convention codified
- HYG-004 closed: 295 → ~80 parametrized tests; collection-time savings; maintenance burden reduced

## Cross-Rite Coordination

A parallel handoff to /sre is also recommended (and may be authored separately) for the larger residual:
- Reusable-workflow optimization at `autom8y/autom8y-workflows/satellite-ci-reusable.yml@c88caabd` (~353s non-pytest CI overhead per BASELINE §4)
- 4→8 shard expansion (newly eligible post-T1D)
- Post-merge §9.2 wallclock measurement discharge

Hygiene work proceeds independently of the /sre handoff; no blocking coordination required.

## Background

Full engagement substrate available at:
- `.ledge/reviews/VERDICT-test-perf-2026-04-29.md` — Phase-5 PASS-WITH-FLAGS adjudication
- `.ledge/reviews/BASELINE-test-perf-2026-04-29.md` — measured baseline (rigor anchor)
- `.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf.md` — governing charter
- `.sos/wip/eunomia/PLAN-test-perf-2026-04-29.md` — 6 CHANGE specs (T3A deferred → HYG-004 here)
- `.sos/wip/eunomia/EXPLORE-SWARM-SYNTHESIS-perf-2026-04-29.md` — opportunity-space substrate
- `.sos/wip/eunomia/EXECUTION-LOG-test-perf-2026-04-29.md` — per-CHANGE execution receipts

## Contact

Eunomia rite session: `session-20260429-161352-83c55146` (active until /sos wrap). After wrap, route questions to potnia (hygiene-rite orchestrator) or surface to user for re-engagement of the eunomia rite.
