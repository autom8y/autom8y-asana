---
artifact_id: HANDOFF-eunomia-to-sre-2026-04-29
schema_version: "1.0"
type: handoff
source_rite: eunomia
target_rite: sre
handoff_type: execution
priority: high
blocking: false
initiative: "test-suite efficiency optimization (CI-shape residuals — sprint-orchestrated)"
created_at: "2026-04-29T17:04:00Z"
status: in_progress
handoff_status: accepted
sprint_3_continuation_session: session-20260430-203219-c8665239
items_status:
  SRE-001: closed (Sprint-1 supplement §1-§7; PASS-WITH-FLAGS-NEW)
  SRE-002: in_progress (Sprint-2 §8.4 sub-routes 002a/002b adjudicated NO-LEVER; 002c REGEN-WIN; Sprint-3 Path B scaffold only — runner_size parameter added via autom8y-workflows PR #14 commit 3a35dbc3; full realization gated on org-runner-tier enablement)
  SRE-003: closed (Sprint-2 ADR-010 STAY-AT-4)
  SRE-004: closed (Sprint-2 commit 29fdaad1; post-merge-coverage.yml + GLINT-003 closure)
  SRE-005: closed (Sprint-3 commit 288a52bc; ADR-013 hadolint integration; M-16 enforcement landed)
source_artifacts:
  - .ledge/reviews/VERDICT-test-perf-2026-04-29.md
  - .ledge/reviews/BASELINE-test-perf-2026-04-29.md
  - .ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md
  - .sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf.md
  - .sos/wip/eunomia/PLAN-test-perf-2026-04-29.md
  - .sos/wip/eunomia/EXPLORE-SWARM-SYNTHESIS-perf-2026-04-29.md
session_id: session-20260429-161352-83c55146
provenance:
  - source: VERDICT-test-perf-2026-04-29 §6 + §9.2 + §9.5
    type: artifact
    grade: strong
  - source: BASELINE-test-perf-2026-04-29 §4 (CI per-job timing extraction)
    type: artifact
    grade: strong
  - source: PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf §11.1 (CI-overhead opacity risk)
    type: artifact
    grade: strong
  - source: VERDICT-eunomia-final-adjudication-2026-04-29 §7 (M-16 carry-over)
    type: artifact
    grade: moderate
evidence_grade: strong
items:
  - id: SRE-001
    summary: "Discharge VERDICT-test-perf §9.2 — post-merge CI per-job wallclock measurement against the new Tier-1+2 commits"
    priority: critical
    acceptance_criteria:
      - "Branch `eunomia/test-perf-2026-04-29` merged to main (or PR opened and CI run captured against the unmerged HEAD)"
      - "5 successful main-branch CI runs captured post-merge via `gh run list --workflow=test.yml --branch=main --status=success --limit=5 --json databaseId,createdAt,conclusion,headSha`"
      - "Per-job wallclock extracted via `gh run view <run-id> --json jobs --jq '.jobs[] | {name, conclusion, started_at, completed_at}'` for each of the 5 runs"
      - "Per-job-name avg + p50 + p95 computed across the 5-run sample"
      - "Delta computed against BASELINE §4 (slowest shard p50 = 447s pre-engagement)"
      - "Verdict authored: VERDICT §9.2 supplement at `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` documenting CI delta + attribution between pytest-internal and infrastructure phases"
      - "If pytest-internal delta is dominant fraction of CI delta: discharge §11.1 risk; close PASS-WITH-FLAGS flag #2"
      - "If non-pytest CI overhead dominates: SRE-002 scope confirmed; record finding for downstream sizing"
    notes: |
      This is the load-bearing flag from VERDICT-test-perf §9.2. Phase-5
      verification could not directly attest the CI-side ROI because the
      branch was unmerged. This SRE-001 protocol DISCHARGES that flag.

      Without this measurement, the VERDICT remains at PASS-WITH-FLAGS in
      perpetuity. SRE-001 is the structural close-gate.

      The 6-step protocol is verbatim from VERDICT §5 deviation 3.
    estimated_effort: "2-4 hours (mostly waiting on CI; gh CLI extraction is fast)"
    dependencies: []

  - id: SRE-002
    summary: "Reusable-workflow optimization at autom8y/autom8y-workflows/satellite-ci-reusable.yml@c88caabd — the largest remaining CI lever"
    priority: high
    acceptance_criteria:
      - "Audit completed: per-step wallclock breakdown of `satellite-ci-reusable.yml@c88caabd` for the autom8y-asana repo's typical workflow run (5-run sample)"
      - "Audit identifies which steps account for the ~353s non-pytest CI overhead surfaced in BASELINE §4 (install / mypy / spec-check / cache restore / cache save / setup / teardown)"
      - "Optimization candidates ranked by ROI × risk; top-3 carried into remediation"
      - "Remediation: at least 2 of the top-3 candidates implemented. Likely surface area: uv-cache key strategy refinement, mypy incremental cache key tuning, dependency-install parallelism, or step ordering"
      - "Reusable-workflow PR opened against `autom8y/autom8y-workflows` (cross-repo) with measured before/after wallclock evidence"
      - "Post-merge CI shard p50 reduction: target ≥30% of the 353s overhead (i.e., aggregate ≥100s reduction off slowest-shard p50)"
      - "Cross-fleet impact assessed: changes to reusable-workflow propagate to all consuming satellites (autom8y-core, autom8y-asana, etc.) — coordinate ramp via GitHub Actions SHA pinning"
    notes: |
      Per BASELINE §4 + VERDICT §9.5: ~353s of the 447s slowest-shard p50 is
      non-pytest infrastructure overhead. This is now the dominant CI lever
      after Tier-1 unblocked the parallelism multiplier. Charter §11.1
      pre-named this as routing-to-/sre at close.

      Cross-repo authorization required: autom8y-asana cannot directly merge
      changes to `autom8y/autom8y-workflows`. Coordinate with workflow
      maintainers; pin SHAs during ramp to control blast radius.

      RISK: changes to reusable workflow affect the whole fleet. SRE rite's
      blast-radius-discipline applies; consider chaos-engineer involvement
      for canary validation.
    estimated_effort: "1 sprint (cross-repo coordination + audit + remediation + ramp + cross-fleet verification)"
    dependencies:
      - SRE-001  # need measured baseline post-merge before scoping optimizations

  - id: SRE-003
    summary: "4→8 shard expansion — newly eligible because Tier-1 unblocked --dist=load (parallelism ceiling raised)"
    priority: medium
    acceptance_criteria:
      - "Empirical sizing: with `.test_durations` refreshed under `--dist=load` topology (CHANGE-T2B already landed), compute optimal shard count by simulating 4-shard vs 6-shard vs 8-shard via pytest-split's offline planner"
      - "Decision: stay-at-4 / go-to-6 / go-to-8 — adjudicated based on (a) wallclock improvement per added shard, (b) GitHub Actions runner-pool capacity for the autom8y-asana repo, (c) cost vs benefit (each shard is a runner-minute)"
      - "If expansion approved: `.github/workflows/test.yml:line` updated with new `test_splits: N` value; reusable workflow's matrix dimension confirmed compatible"
      - "Post-expansion CI run shows measured shard-imbalance variance ≤15% (down from current 30%+ per BASELINE)"
      - "If stay-at-4: rationale documented in commit + `.ledge/decisions/` ADR-style note ('expansion not warranted because runner-pool / cost / diminishing-returns')"
    notes: |
      Pre-Tier-1, shard expansion was bounded by the loadfile band-aid (only
      ~570 files, can't usefully shard much further than file granularity).
      Post-Tier-1 with `--dist=load`, the suite redistributes at test
      granularity — 13,597 tests can shard much further with diminishing
      returns to be sized empirically.

      Per BASELINE: 4-shard p50 = 447s. Naive linear scaling: 8-shard p50
      ~225s. Real ROI is sublinear due to startup overhead per shard.
    estimated_effort: "1-2 days (sizing + decision + impl + verification)"
    dependencies:
      - SRE-001  # need post-Tier-1 CI baseline for empirical sizing
      - SRE-002  # if reusable-workflow optimization changes per-shard overhead, sizing math shifts

  - id: SRE-004
    summary: "Post-merge aggregate coverage job — close GLINT-003 coverage-gate-theater debt"
    priority: medium
    acceptance_criteria:
      - "New workflow job (or addition to existing post-merge workflow) authored that runs full pytest with `--cov=src/autom8_asana --cov-fail-under=80` against merged main commits"
      - "Job runs WITHOUT pytest-split (single-shard so coverage is meaningful) — accepts the wallclock cost of serial run because it's post-merge async"
      - "Job triggers on push to main; failure reports to a designated channel (Slack / GitHub issue auto-creation / etc — coordinate with repo conventions)"
      - "`pyproject.toml:126` `fail_under = 80` is now ENFORCED post-merge (no longer theater per `.know/test-coverage.md` GLINT-003 finding)"
      - "Documentation: `.know/test-coverage.md` GLINT-003 entry updated from 'theater' to 'enforced post-merge at <workflow:job>' with anchor file:line"
    notes: |
      Per BASELINE §3 / VERDICT §6 routing: `pyproject.toml:126` declares
      `fail_under = 80` (intent). `.github/workflows/test.yml:52` sets
      `coverage_threshold: 0` for sharded runs with comment "aggregate
      coverage should be validated in a separate post-merge job."

      That separate post-merge job DOES NOT EXIST. Per BASELINE direct
      verification: `gh run list` returned zero matches for any post-merge
      coverage workflow.

      This is `correctness governance` debt, not pace work. Routes to /sre
      because the implementation is CI-shape; could alternately route to
      /hygiene if /sre defers.
    estimated_effort: "4-6 hours (workflow authoring + threshold tuning + initial run)"
    dependencies: []

  - id: SRE-005
    summary: "M-16 Dockerfile pattern enforcement decision — carry-over from prior eunomia close (2026-04-29 structural-cleanliness adjudication)"
    priority: low
    acceptance_criteria:
      - "Decision adjudicated: hadolint vs grep-based vs other Dockerfile-pattern enforcement tooling"
      - "If tool selected: integrated into existing pre-commit / CI pipeline; runs against all repo Dockerfiles (count via `find . -name 'Dockerfile*' -not -path './.git/*'`)"
      - "Pattern set codified: at minimum the patterns the prior structural-cleanliness eunomia engagement flagged (cite VERDICT-eunomia-final-adjudication §7 for specific patterns)"
      - "If decision is no-tool: rationale documented; M-16 ASSESS-tier defer-watch entry resolved (not just deferred again)"
    notes: |
      Carry-over from VERDICT-eunomia-final-adjudication-2026-04-29 §7 (the
      prior structural-cleanliness eunomia close, 2026-04-29 morning). M-16
      was routed to /sre at that close as a design decision; perf-track
      eunomia engagement (afternoon) preserved this routing in its own
      VERDICT §6 to avoid double-routing or implicit deprioritization.

      Lower priority than SRE-001/002 but listed for completeness so /sre
      backlog visibility is one-stop. /sre may de-prioritize or pull this
      forward as sprint context dictates.
    estimated_effort: "1-2 days (audit + tool selection + integration)"
    dependencies: []

tradeoff_points:
  - attribute: "CI Wallclock vs Cross-Fleet Coordination"
    tradeoff: "SRE-002 reusable-workflow changes affect all autom8y satellites (autom8y-core, autom8y-asana, etc.) — cannot land in isolation."
    rationale: "The ~353s overhead lives in shared infrastructure by design. Optimizing it requires cross-repo coordination but yields fleet-wide benefit. Eunomia explicitly excluded reusable-workflow scope per charter §3.2.3 because the rite's authority surface is bounded to test-suite-internal changes."
  - attribute: "Coverage Enforcement vs Per-Shard Practicality"
    tradeoff: "SRE-004 accepts running a full single-shard serial pytest post-merge purely for coverage; this is wallclock-expensive but the only way to get meaningful aggregate coverage."
    rationale: "Per-shard coverage is meaningless with test_splits > 1 (each shard sees ~25%). Either accept the post-merge serial cost or accept the theater. /sre rite is well-positioned to make this trade because it owns CI-shape disposition."
  - attribute: "Verdict Discharge vs Time"
    tradeoff: "VERDICT-test-perf carries PASS-WITH-FLAGS in perpetuity until SRE-001 lands. /sre takes on the discharge work to close the engagement at full PASS rather than leaving the flag indefinitely open."
    rationale: "Eunomia could not self-discharge §9.2 because the measurement requires post-merge state that doesn't exist at engagement close. /sre is the structurally correct discharger because the measurement is CI-side."
---

## Context

The eunomia perf-track engagement (session `session-20260429-161352-83c55146`) closed 2026-04-29 with PASS-WITH-FLAGS verdict. Six atomic CHANGE specs landed on branch `eunomia/test-perf-2026-04-29` delivering 48.72% local-pytest wallclock reduction (374s → 192s under `-n 4 --dist=load`). Charter §10 + VERDICT §6 routed the CI-shape residuals to /sre; this handoff formalizes them.

User invocation framing: "/cross-rite-handoff --to=sre for /sprint remaining residuals with rigor and vigor sustained" — items are sprint-orchestrated, NOT /task increments. SRE-001 + SRE-002 likely fill one sprint; SRE-003/004/005 fit in subsequent sprints depending on /sre prioritization.

A parallel handoff to /hygiene was authored at `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md` for the test-surface residuals (mock spec, MockTask consolidation, parametrize compression, SCAR marker codification). Hygiene work proceeds independently; no blocking coordination.

## Item Prioritization

Recommended sprint sequencing:

**Sprint 1 (CRITICAL/HIGH — discharge VERDICT flag + biggest CI lever)**:
1. **SRE-001** (CRITICAL) — Post-merge §9.2 measurement protocol. Discharges PASS-WITH-FLAGS flag; provides empirical baseline for SRE-002/003 sizing. **Blocking dependency for SRE-002 + SRE-003.**
2. **SRE-002** (HIGH) — Reusable-workflow optimization. Largest remaining CI lever (~353s/447s slowest-shard p50). Cross-repo coordination required.

**Sprint 2 (MEDIUM — sized after Sprint 1 measurements)**:
3. **SRE-003** (MEDIUM) — 4→8 shard expansion. Sizing depends on SRE-001 measurements + SRE-002 outcomes (per-shard overhead changes math).
4. **SRE-004** (MEDIUM) — Post-merge aggregate coverage job. Independent; can run in parallel with SRE-003.

**Sprint 3 or backlog (LOW — prior-engagement carry-over)**:
5. **SRE-005** (LOW) — M-16 Dockerfile pattern enforcement. Carry-over from prior eunomia structural-cleanliness close. /sre may pull forward or defer based on sprint capacity.

## Notes for SRE Rite

### Branch context
- Branch `eunomia/test-perf-2026-04-29` is unmerged at handoff creation. SRE-001 acceptance criteria adapt depending on merge timing — measure either against unmerged-PR CI or against post-merge main CI.
- If SRE-002 changes the reusable workflow, cross-fleet ramp coordination is on /sre. Pin SHAs in consuming satellites until verification complete.

### Authority boundaries
- SRE-002 touches `autom8y/autom8y-workflows` (different repo). Ensure cross-repo authorization before opening PRs there.
- SRE-004 introduces a new CI job. Coordinate with repo conventions (notification channels, threshold tuning).
- SRE-005 may touch tooling outside the repo (hadolint or equivalent). Tool-selection authority is /sre's per the charter routing.

### What NOT to do
- Do NOT modify production code or test surface. That's eunomia/hygiene/10x-dev territory.
- Do NOT relax `pyproject.toml:126` `fail_under = 80` — SRE-004's job is to ENFORCE this, not relax it.
- Do NOT undo any of the 6 perf CHANGE commits on `eunomia/test-perf-2026-04-29` — those have STRONG verification per VERDICT §3-§5.

### Coordination with parallel /hygiene handoff
- HYG-001 (SCAR marker codification) and SRE-001 (post-merge measurement) are independent; can run in parallel.
- HYG-002 (mock spec adoption) might surface interface drift requiring CI tuning if mass spec'ing breaks tests — coordinate empirically if surfaced.
- No blocking edges between this handoff and the /hygiene handoff.

## Expected Outcomes

- **SRE-001 closed**: VERDICT-test-perf moves from PASS-WITH-FLAGS to PASS-CLEAN. Measured CI delta documented.
- **SRE-002 closed**: Slowest-shard p50 reduced from 447s baseline by ≥30% of overhead (~100s+ reduction). Cross-fleet benefit propagates.
- **SRE-003 closed**: Optimal shard count empirically determined; either expansion landed or stay-at-4 rationale documented.
- **SRE-004 closed**: GLINT-003 coverage-gate-theater debt resolved; `fail_under = 80` enforced post-merge.
- **SRE-005 closed**: M-16 Dockerfile pattern enforcement adjudicated and operational (or no-tool decision documented).

Aggregate impact: combined with Tier-1+2 perf work (already landed, -49% local pytest), the full engagement plus /sre residuals targets ≥50% CI shard p50 reduction (447s → ~225s) — meaningful end-to-end CI velocity improvement.

## Background

Full engagement substrate available at:
- `.ledge/reviews/VERDICT-test-perf-2026-04-29.md` — PASS-WITH-FLAGS adjudication; §9.2 + §9.5 are the load-bearing /sre routing
- `.ledge/reviews/BASELINE-test-perf-2026-04-29.md` — measured baseline; §4 has the CI per-job timing extraction protocol
- `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md` — parallel /hygiene handoff for context
- `.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf.md` — governing charter; §11.1 pre-named the CI-overhead opacity risk
- `.sos/wip/eunomia/PLAN-test-perf-2026-04-29.md` — 6 CHANGE specs (the work that landed)
- `.sos/wip/eunomia/EXPLORE-SWARM-SYNTHESIS-perf-2026-04-29.md` — opportunity-space substrate; Lane 3 mapped CI shape
- `.ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md` — prior structural-cleanliness eunomia close; §7 is the source of M-16 carry-over

## Contact

Eunomia rite session: `session-20260429-161352-83c55146`. After /sos wrap, re-engage eunomia rite if cross-engagement coordination is needed (e.g., SRE-001 measurements suggest the perf engagement needs a v2 follow-on).
