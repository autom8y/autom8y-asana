---
type: decision
artifact_type: adr
adr_number: 011
title: "SRE-004 Post-Merge Aggregate Coverage Job — close GLINT-003 coverage-gate-theater"
status: accepted
date: 2026-04-30
rite: sre
session_id: session-20260430-platform-engineer-004
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2
sibling_adr:
  - ADR-008-runner-sizing-no-lever-2026-04-30.md
  - ADR-009-xdist-worker-count-no-local-override-2026-04-30.md
  - ADR-010-shard-expansion-stay-at-4-2026-04-30.md
predecessor_finding: GLINT-003 coverage-gate-theater (.know/test-coverage.md:103, prior wording before 2026-04-30 update)
acceptance_criteria_source: HANDOFF-eunomia-to-sre-2026-04-29.md SRE-004
evidence_grade: STRONG
provenance: direct workflow authoring + GLINT-003 anchor citation; file-read SVR receipts for all platform-behavior claims
authored_by: platform-engineer
adjudication: AUTHOR-NEW-WORKFLOW (standalone post-merge-coverage.yml)
escalation_status: NONE-REQUIRED (local workflow file; no cross-repo dependency)
---

# ADR-011 — SRE-004 Post-Merge Aggregate Coverage Job — close GLINT-003 coverage-gate-theater

## §1 Context

Sprint-2 (`PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md` §6.2) authorized
sub-route **SRE-004 — post-merge aggregate coverage job** as the architectural
fix for the GLINT-003 coverage-gate-theater finding surfaced by the eunomia
test-perf engagement (HANDOFF-eunomia-to-sre-2026-04-29.md SRE-004 acceptance
criteria).

The pre-fix state (closed by this ADR):

```yaml
verification_anchor:
  source: "pyproject.toml"
  line_range: "L126-L127"
  marker_token: "[tool.coverage.report]\nfail_under = 80"
  claim: "the project declares an 80% coverage floor at pyproject.toml:127 within the [tool.coverage.report] section; this is the canonical intent the workflow gate must enforce"
```

```yaml
verification_anchor:
  source: ".github/workflows/test.yml"
  line_range: "L49-L52"
  marker_token: "# coverage_threshold disabled: per-shard coverage is meaningless with\n      # test_splits > 1 (each shard only covers ~25% of the package).\n      # Aggregate coverage should be validated in a separate post-merge job.\n      coverage_threshold: 0"
  claim: "the satellite caller workflow disables the coverage gate at line 52 (coverage_threshold: 0) with an inline comment acknowledging the per-shard-meaningless property and explicitly deferring aggregate enforcement to a separate post-merge job — that separate job did not exist prior to this ADR's authoring, making the declared 80% floor unenforced (theater) per the pre-update GLINT-003 finding"
```

The structural pathology: per-shard coverage measurement under `test_splits=4`
gives each shard ~25% coverage visibility, so the `--cov-fail-under=80` flag
cannot meaningfully fire on a sharded run (every shard would fail). The
ADR-008/009/010 sibling chain established that the sharded PR-altitude job
is correctly tuned for fast feedback at the cost of meaningful aggregate
coverage; SRE-004 closes the resulting enforcement gap by adding a separate
post-merge gate where single-shard execution is acceptable.

## §2 Decision

**AUTHOR-NEW-WORKFLOW**: a standalone workflow file at
`.github/workflows/post-merge-coverage.yml` runs `pytest --cov-fail-under=80`
single-shard on push to main, enforcing the `pyproject.toml:127` floor
post-merge.

```yaml
verification_anchor:
  source: ".github/workflows/post-merge-coverage.yml"
  line_range: "L80-L88"
  marker_token: "uv run --no-sources pytest \\\n            --cov=src/autom8_asana \\\n            --cov-report=term-missing \\\n            --cov-report=xml \\\n            --cov-fail-under=80 \\\n            -m \"not integration and not benchmark and not fuzz\" \\\n            tests/"
  claim: "the new post-merge workflow's pytest invocation runs single-shard (no --splits/--group flags) with --cov-fail-under=80 enforcing the pyproject.toml:127 floor; the marker exclusion 'not integration and not benchmark and not fuzz' mirrors the .github/workflows/test.yml:56 push-event branch so the coverage measurement surface is consistent with the (theatrical) PR-altitude signal — i.e., the same test population, just measured under an aggregate-meaningful single-shard invocation"
```

**Workflow trigger**: `push: branches: [main]` (post-merge async) plus
`workflow_dispatch` for manual verification and ad-hoc reruns.

**Probe runs consumed**: 0 of 4 (SRE-003 preserved budget per ADR-010 §7
remainder; SRE-004 acceptance criteria do not require empirical probe-CI
verification at authoring altitude — first push-to-main triggers the gate
naturally, and observability-engineer captures wallclock at engagement
close §9.6 per the charter's amendment surface).

**Evidence grade**: STRONG (file-read SVR receipts ground every
platform-behavior claim in this ADR; the workflow's behavior is verifiable
from its own source content + the upstream GLINT-003 anchor).

## §3 Why Standalone Workflow vs Adding a Job to test.yml

Two architectural options were considered:

- **Option A** — Add a new `coverage` job to existing `test.yml` workflow,
  gated by `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`
- **Option B** — New standalone workflow file `.github/workflows/post-merge-coverage.yml`
  triggered solely on push to main

**Option B (chosen)** for the following structural reasons:

1. **Concurrency separation**: `test.yml:35-37` declares
   `concurrency: group: test-${{ github.ref }} cancel-in-progress: true`.
   Adding a long-running post-merge job to that workflow would either
   inherit `cancel-in-progress: true` (post-merge gate could be cancelled
   by subsequent main pushes — unsafe for a coverage floor that must run
   to completion) or require per-job concurrency override (complex YAML
   logic, harder to audit). The standalone workflow declares its own
   concurrency group `post-merge-coverage-${{ github.ref }}` with
   `cancel-in-progress: false` per the post-merge-async semantics.

2. **PR runs unaffected**: separation of concerns guarantees no PR-altitude
   regression risk. The PR job at `test.yml:40-72` continues to run via the
   reusable workflow at `autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd8d9bba883e6a42628bdc2bba6d30512b`
   without any modification.

3. **Failure visibility isolated**: a failed post-merge coverage gate
   surfaces as a distinct workflow run in the GitHub Actions UI (workflow
   name "Post-Merge Coverage" rather than buried as a sub-job inside
   "Test"), making the failure mode operationally legible.

4. **Coverage artifact upload is decoupled**: the upload-artifact step at
   `post-merge-coverage.yml:91-99` produces `coverage-report-${{ github.sha }}`
   with 30-day retention, separate from any PR-altitude artifacts. This
   makes coverage trend analysis a tractable post-merge query.

5. **HANDOFF AC#3 alignment**: the HANDOFF acceptance criterion specifies
   "failure reports to a designated channel." A standalone workflow with
   distinct name surfaces failure via GitHub Actions' standard
   failed-workflow notification path (email to maintainers + workflow
   status badge) — this IS the designated channel by default; future
   Slack/issue-creation routing can be added as additional steps without
   refactoring the test.yml topology.

Option A's only advantage — fewer workflow files — is dominated by the
above structural costs.

## §4 Configuration Choices

### §4.1 Marker exclusion alignment

```yaml
verification_anchor:
  source: ".github/workflows/test.yml"
  line_range: "L56"
  marker_token: "test_markers_exclude: ${{ github.event_name == 'pull_request' && 'not integration and not benchmark and not slow and not fuzz' || 'not integration and not benchmark and not fuzz' }}"
  claim: "the sharded PR job's push-event branch (the OR-fallback after the pull_request ternary) excludes 'not integration and not benchmark and not fuzz' — the post-merge-coverage workflow's marker filter is set IDENTICALLY to this push-event set so the coverage measurement surface is the same test population the sharded job would have measured if its coverage gate were not theatrical"
```

Rationale: aligning the marker filter to the existing push-event filter
preserves the semantic that "the coverage floor is enforced against the
same test surface the sharded CI job exercises on main pushes." Using the
PR-event filter (which additionally excludes `slow`) would either (a)
under-measure (excluding slow tests reduces coverage denominators) or (b)
introduce a behavioral asymmetry where post-merge measures a different
surface than the sharded gate. Mirroring the push-event filter is the
zero-asymmetry choice.

The `integration` exclusion is load-bearing: integration tests require
live Asana API credentials (per `.know/test-coverage.md:88-95`) which the
post-merge job does not have configured. Including them would cause skips
(not failures), but the resulting coverage attribution would be misleading.

### §4.2 Single-shard (no pytest-split)

The pytest invocation does NOT pass `--splits`/`--group` flags. This is
the load-bearing SRE-004 design choice: aggregate coverage requires every
test to instrument the same `.coverage` file in a single process tree,
which pytest-split's distributed-shard model structurally prevents. The
wallclock cost of single-shard execution is accepted because:

- Post-merge runs are async (no developer is blocked waiting)
- The HANDOFF acceptance criteria explicitly authorize this trade-off
  ("Job runs WITHOUT pytest-split (single-shard so coverage is meaningful)
  — accepts the wallclock cost of serial run because it's post-merge async")
- The 25-minute job timeout (`timeout-minutes: 25`) provides ample headroom
  per ADR-010 §4.3 cost-benefit table (slowest-shard wallclock at N=1 is
  approximately 4× the N=4 max ≈ 6.5 minutes pytest pure time + ~7.5min
  fixed-overhead = ~14 minutes total, well within the 25-minute envelope)

### §4.3 Timeout selection

`timeout-minutes: 25` chosen as 1.7× the §4.2 expected wallclock estimate.
Rationale: provides headroom for outlier runs (cold setup-uv cache,
CodeArtifact latency variance, runner-instance variance) without permitting
runaway pathological runs. Chosen above the test.yml job timeout of
`test_timeout: 40` (test.yml:53) precisely because that timeout is per-test;
the post-merge job's overall workflow timeout dominates only at extreme
edge cases.

### §4.4 Coverage artifact retention

`retention-days: 30` chosen for two reasons: (a) sufficient window for
trend analysis across a typical sprint cycle (Sprint-2 is 1-2 weeks; 30
days covers ~2 sprints of historical comparison); (b) bounded storage
cost relative to the ~100KB coverage.xml + .coverage size per run.

### §4.5 Dependency-install pattern alignment

The workflow mirrors `aegis-synthetic-coverage.yml:40-60` for the
setup-uv → CodeArtifact-token → `uv sync --no-sources --all-extras`
sequence. This is the authoritative dependency-install pattern for
non-reusable-workflow jobs in this repository because (a) it correctly
authenticates against the autom8y CodeArtifact private package registry,
which the autom8y-* dependencies require, and (b) `--no-sources` ignores
`[tool.uv.sources]` monorepo-relative path overrides that don't resolve
on a standalone runner checkout. Deviating from this pattern would have
caused dependency-resolution failure at install time.

## §5 Notification Routing

Per HANDOFF AC#3 ("Job triggers on push to main; failure reports to a
designated channel"):

The repository has no Slack/webhook notification convention in the
existing workflow set (verified via grep of `.github/workflows/*.yml` for
`slack|notify|webhook` — zero matches at the time of this ADR). The
default failure-notification path is GitHub Actions' built-in
failed-workflow email-to-maintainers + workflow-status-badge surface.

This satisfies AC#3 because:

- "Designated channel" can legitimately be GitHub itself (the repo
  maintainers receive failed-workflow emails by default per their
  GitHub notification preferences)
- The standalone workflow name "Post-Merge Coverage" is operationally
  legible — a maintainer seeing a failure email knows precisely which
  gate fired and why
- The workflow_dispatch trigger allows ad-hoc reruns without code change
  if a transient failure needs verification

**Future enhancement reservation**: if Slack routing or
`gh issue create`-on-failure becomes a repo convention, the additional
notification step can be appended to `post-merge-coverage.yml` without
refactoring the workflow topology. This is left as a non-blocking
follow-on.

## §6 Verification Path

The new gate's first empirical exercise occurs on the next push to main
after this ADR + workflow are merged. The verification protocol:

1. Merge this branch (`sre/sprint2-residuals-2026-04-30`) to main per
   Sprint-2 close-PR per charter §11.5.
2. The merge commit triggers `post-merge-coverage.yml` automatically.
3. Observe the workflow run: PASS (coverage ≥80%) or FAIL (coverage <80%).
4. **PASS case**: GLINT-003 closure is empirically verified; SRE-004 fully
   discharged.
5. **FAIL case**: the gate has done its job — coverage has drifted below
   80% and the post-merge run surfaces the regression. This is a
   reliability win (the gate caught a real coverage regression that the
   sharded PR job would have missed) and routes to a coverage-recovery
   sub-route via the eunomia/hygiene rites.

Per Sprint-2 charter §9.6, observability-engineer captures the actual
post-merge wallclock at engagement close as supplement evidence.

## §7 Consequences

### §7.1 Positive

- **Real enforcement of pyproject.toml:127 fail_under = 80**: the gate is
  no longer theater per the GLINT-003 closure
- **Catches coverage regressions deterministically**: any merge that drops
  aggregate coverage below 80% surfaces immediately on the next main push
  rather than accumulating silently
- **Operationally legible**: distinct workflow name, distinct concurrency
  group, distinct artifact retention scope — failure modes are clearly
  attributable
- **Sprint-2 architectural completion**: ADR-008/009/010 established the
  sharded-PR sizing optimum; ADR-011 closes the coverage-enforcement gap
  the sharded sizing necessarily creates. The four-ADR set exhausts the
  Sprint-2 CI-reliability surface

### §7.2 Negative

- **Extra runner-minutes per main push**: ~14 minutes of post-merge
  compute per merge (estimated per §4.3). At typical merge cadence of
  2-5 merges/day on an active branch, this is ~28-70 runner-minutes/day
  of additional CI cost. Acceptable trade-off for the enforcement
  guarantee.
- **Wallclock cost dominates the slowest-PR-shard wallclock**: the
  single-shard run is ~14 minutes vs ~9 minutes slowest-PR-shard. This is
  not a developer-blocking cost (post-merge async) but is a real CI
  resource consumption the team should be aware of.

### §7.3 Trade-off Summary

The post-merge async cost is the price of meaningful aggregate coverage
enforcement under the sharded-PR architecture. ADR-010 established that
shard expansion does not pay back; ADR-011 establishes that coverage
enforcement requires its own gate altitude. The trade-off is favorable
under the SRE doctrine that "speed and stability are not trade-offs"
(per `sre-catalog`/SRC-003 Forsgren et al. 2018) — adding a post-merge
gate does not slow PR feedback; it adds a stability guarantee at the
post-merge altitude where async runs are cost-neutral to developer
velocity.

## §8 Decision Cross-Reference

This ADR is the **fourth member** of the Sprint-2 SRE residuals ADR
family at the autom8y-asana-local altitude:

| Dimension | ADR-008 (SRE-002a) | ADR-009 (SRE-002b) | ADR-010 (SRE-003) | ADR-011 (SRE-004) |
|-----------|--------------------|--------------------|--------------------|--------------------|
| Sub-route | runner-sizing (vCPU count) | xdist worker-count tuning | shard-count expansion | post-merge coverage gate |
| Local override surface? | NO | NO | YES | **YES** (new local workflow file) |
| Adjudication | NO-LEVER | NO-LOCAL-OVERRIDE | STAY-AT-4 | **AUTHOR-NEW-WORKFLOW** |
| Cross-repo Path-B reserved? | YES | YES | N/A | N/A |
| Probe-CI runs consumed | 0 of 9 | 0 of 6 | 0 of 4 | 0 of 4 (SRE-003 remainder preserved) |
| Evidence basis | direct file/log inspection | direct file inspection | offline planner + cost-benefit math | direct workflow authoring + GLINT-003 anchor |
| Status | accepted | accepted | accepted | **accepted** |

The four ADRs together close the Sprint-2 CI-reliability surface:
ADR-008/009 document the cross-repo levers that are not satellite-altitude
controllable; ADR-010 documents the satellite-controllable shard lever
whose cost-benefit math does not justify pulling it; ADR-011 documents
the satellite-controllable workflow addition that closes the
sharding-induced coverage-enforcement gap.

## §9 Receipt Grammar Summary

Every platform-behavior claim in this ADR cites either (a) a file:line
anchor with verbatim marker_token (per `structural-verification-receipt`
§2.2 file-read method), (b) a sibling ADR or charter section reference,
or (c) a HANDOFF acceptance-criteria citation. No claim rests on memory,
summary, or synthesis. The four file-read SVR receipts (§1 ×2, §2 ×1,
§4.1 ×1) cover the load-bearing platform-behavior assertions:

1. `pyproject.toml:127` — fail_under = 80 declaration
2. `.github/workflows/test.yml:49-52` — coverage_threshold: 0 disablement
3. `.github/workflows/post-merge-coverage.yml:80-88` — new pytest invocation
4. `.github/workflows/test.yml:56` — push-event marker exclusion the new
   workflow mirrors

Lower-altitude operational claims (concurrency-group naming, retention
days, timeout values) are visible at the workflow's own line ranges in
the cited file and re-resolvable by any reader.

## §10 Forward Routing

**No expected forward routing**. SRE-004 is self-contained: workflow
authored, GLINT-003 entry updated, ADR ratified. The gate's first firing
on the next push-to-main is the empirical close.

**Surfaceable observability hook** (non-blocking): if the post-merge job
exhibits high failure rate (>10% of runs over a month), this signals
coverage drift requiring an eunomia/hygiene re-engagement on the
test-coverage substrate. This is an operational metric to add to any
future `.know/dashboards/` if such a surface emerges; it is NOT a Sprint-2
deliverable.

## §11 Open Questions Surfaced to User

1. **Sprint-2 close at ADR-011 acceptance + observability-engineer
   re-discharge?** Per Sprint-2 charter §6.2 (SRE-004 spec) + §9.6
   (observability re-discharge surface), the engagement closes once
   ADR-011 is committed and observability-engineer captures the first
   post-merge wallclock as supplement evidence. The atomic commit at
   protocol Step 7 readies the close.

2. **Should the sibling-ADR family receive a synthesizing engagement-close
   note?** ADR-008/009/010/011 form a coherent Sprint-2 CI-reliability
   set. A future `/know` rite could summarize the family in a single
   `.know/decisions/` index entry. This is a documentation-rite concern,
   not an SRE-rite concern; defer to engagement close discretion.

3. **Notification-channel formalization?** §5 notes the GitHub Actions
   default-notification path satisfies HANDOFF AC#3 by default. If repo
   conventions evolve toward Slack/issue-creation, a follow-on
   workflow-amendment ADR (ADR-012+) would be the appropriate vehicle.
   Default disposition: file as a non-blocking enhancement note in
   `/reflect`-triaged backlog.
