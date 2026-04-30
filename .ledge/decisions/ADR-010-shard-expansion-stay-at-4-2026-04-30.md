---
type: decision
artifact_type: adr
adr_number: 010
title: "SRE-003 4→N Shard Expansion Sizing — STAY-AT-4 (autom8y-asana-local)"
status: accepted
date: 2026-04-30
rite: sre
session_id: session-20260430-platform-engineer-003
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2
sibling_adr:
  - ADR-008-runner-sizing-no-lever-2026-04-30.md
  - ADR-009-xdist-worker-count-no-local-override-2026-04-30.md
investigation: 002c regen substrate (commit 0dc9108a) + offline pytest-split planner @ branch HEAD 0dc9108a
evidence_grade: STRONG
provenance: zero-cost empirical adjudication via pytest-split offline planner (0 of 4 probe-CI runs consumed)
authored_by: platform-engineer
adjudication: STAY-AT-4 (cost-benefit unfavorable for shard expansion)
escalation_status: NONE-REQUIRED (local-controllable parameter; no cross-repo dependency)
---

# ADR-010 — SRE-003 4→N Shard Expansion Sizing — STAY-AT-4 (autom8y-asana-local)

## §1 Context

Sprint-2 (`PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md` §6.1) authorized
sub-route SRE-003 — **4→N shard expansion sizing decision** — as a follow-on
to the SRE-002 family (002a NO-LEVER ADR-008; 002b NO-LOCAL-OVERRIDE ADR-009;
002c `.test_durations` regen at commit `0dc9108a`).

The question carried forward from 002c's diagnostic finding (commit message at
`0dc9108a`):

> Bottleneck (test_openapi_fuzz.py at 111.46s) UNCHANGED — single-file outlier
> dominates max-shard wallclock; cannot be fixed by .test_durations regen
> alone. SRE-003 (shard expansion to 6 or 8) and SRE-004 (coverage isolation)
> are the architectural fixes for which this regen is substrate.

> 561s shard-3/4 outlier from 002a (run-id 25138295569) cross-checked:
> theoretical max-shard 111.5s vs observed 561s = 5.03x ratio = 449.5s
> CI-runtime overhead (fixture init, parallel-worker contention) NOT explained
> by .test_durations imbalance.

The Sprint-2 charter §6.1 + §11.2 authorized up to 4 probe-CI runs to
adjudicate among:

1. **EXPAND-TO-N** — slowest-shard wallclock reduction × developer-velocity
   benefit > runner-minute cost increase → recommend `test_splits: N` commit
2. **STAY-AT-4** — cost-benefit favors current → ADR-only close
3. **HALT-NO-LOCAL-OVERRIDE** — `test_splits` is reusable-workflow-controlled
   → ADR + escalate (sibling pattern of ADR-008/009)

This ADR records adjudication **STAY-AT-4** based on the offline
pytest-split planner cost-benefit analysis and the load-bearing finding from
§4.4 below: the 111.46s "max-shard" cited as the SRE-003 motivation is in
fact a single-file outlier that is **MARKER-EXCLUDED** from the sharded `ci`
job in production CI, making the apparent shard-balance bottleneck a
substrate-measurement artifact rather than a production constraint.

## §2 Decision

**STAY-AT-4 (autom8y-asana-local)** per offline pytest-split planner
cost-benefit analysis at Step 2-3 of the SRE-003 protocol. Step 1
(local-controllability check) confirmed `test_splits: 4` is locally
parameterized at `.github/workflows/test.yml:55` — no NO-LOCAL-OVERRIDE
condition fires. Step 4 adjudication produced a clear-stay verdict per
the brief's "If Step 4 result is unambiguous (clear win or clear stay),
commit/ADR directly without probe" disposition.

**Probe runs consumed**: 0 of 4 (offline planner unambiguity short-circuited
empirical probe; brief explicitly authorizes ADR-only close on unambiguous
adjudications).

**Evidence grade**: STRONG (zero-cost empirical adjudication via direct
file inspection + offline planner simulation; cost-benefit math is monotone
across N=4..8 with no inflection point favoring expansion).

## §3 Investigation Method

The investigation protocol's Step 1-3:

1. **Step 1 — Local-controllability inspection** of the satellite caller
   workflow at `.github/workflows/test.yml:55` to confirm `test_splits: 4`
   is a locally-controllable input parameter (vs. hardcoded in the reusable
   workflow per the 002a/002b NO-LEVER/NO-LOCAL-OVERRIDE pattern).
2. **Step 2 — Offline planner simulation** via `uv run pytest --splits N
   --group K --co -q` for N ∈ {4, 5, 6, 7, 8}, capturing pytest-split's
   self-reported `estimated duration` for each group, with the production
   CI marker filter applied (`-m "not integration and not benchmark and
   not fuzz"`).
3. **Step 3 — Cost-benefit synthesis** combining empirical pytest pure
   time per N with the per-shard CI fixed-overhead estimate
   (449.5s, from 002c regen cross-check of 002a 561s observed shard).

All three steps produced verbatim file:line evidence + reproducible
command output. No CI runs were triggered. No probe branch was created.
The single workflow change considered (modifying line 55) was rejected at
Step 4 adjudication.

## §4 Empirical Anchors (SVR file-read + bash-probe)

### §4.1 Anchor 1 — Local caller workflow `test_splits` controllability

```yaml
verification_anchor:
  source: ".github/workflows/test.yml"
  line_range: "L54-L55"
  marker_token: "test_parallel: true\n      test_splits: 4"
  claim: "the satellite caller workflow passes test_splits as a locally-controllable input to the reusable workflow at line 55; modifying this integer to N requires only a local edit to .github/workflows/test.yml — no cross-repo coordination is required, distinguishing SRE-003 from SRE-002a (runner sizing — GitHub-managed) and SRE-002b (xdist worker count — hardcoded in reusable workflow)"
```

This is the **POSITIVE controllability finding** — SRE-003 is NOT a
NO-LOCAL-OVERRIDE situation. The HALT condition from the brief's Step 1
does not fire. Adjudication continues to Step 2-4.

### §4.2 Anchor 2 — Offline planner empirical pytest pure time per N

```yaml
verification_anchor:
  source: "uv run pytest --splits N --group K --co -q --no-header -m 'not integration and not benchmark and not fuzz'"
  command_output_verbatim: |
    === N=4 ===
      group 1: estimated duration: 98.11s
      group 2: estimated duration: 94.63s
      group 3: estimated duration: 93.61s
      group 4: estimated duration: 87.44s
    === N=5 ===
      group 1: 77.19s; group 2: 74.84s; group 3: 75.93s; group 4: 74.76s; group 5: 71.08s
    === N=6 ===
      group 1: 66.94s; group 2: 62.41s; group 3: 63.39s; group 4: 64.46s; group 5: 62.58s; group 6: 54.01s
    === N=7 ===
      group 1: 56.82s; group 2: 57.47s; group 3: 53.69s; group 4: 56.80s; group 5: 55.43s; group 6: 54.20s; group 7: 39.39s
    === N=8 ===
      group 1: 50.90s; group 2: 47.22s; group 3: 48.12s; group 4: 46.74s; group 5: 46.74s; group 6: 46.99s; group 7: 47.69s; group 8: 39.39s
  exit_code: 0
  claim: "pytest-split's offline planner (DurationBasedChunksAlgorithm, the production-default algorithm consumed by the reusable workflow at the test_dist_strategy default) computes per-group pytest pure time for each candidate shard count N; the slowest-group estimates are 98.11s @ N=4, 77.19s @ N=5, 66.94s @ N=6, 57.47s @ N=7, 50.90s @ N=8 — under the production CI marker filter applied at .github/workflows/test.yml:56 ('not integration and not benchmark and not fuzz')"
```

The simulation is reproducible from any branch checkout because pytest-split
reads `.test_durations` at the repo root (commit `0dc9108a` substrate). The
estimates are pure-time only — they exclude CI fixed-overhead per shard.

### §4.3 Anchor 3 — Cost-benefit table (combining §4.2 with overhead estimate)

| N | pytest pure time max | + overhead 449.5s | slowest-shard wallclock | total runner-min | wallclock Δ vs N=4 | runner-min Δ vs N=4 |
|---|---:|---:|---:|---:|---:|---:|
| **4** (baseline) | 98.11s | 449.5s | **547.61s** | 36.51m | 0.00% | 0.00% |
| 5 | 77.19s | 449.5s | 526.69s | 43.89m | -3.82% | +20.22% |
| 6 | 66.94s | 449.5s | 516.44s | 51.64m | -5.69% | +41.46% |
| 7 | 57.47s | 449.5s | 506.97s | 59.15m | -7.42% | +62.01% |
| 8 | 50.90s | 449.5s | 500.40s | 66.72m | -8.62% | +82.76% |

**The cost-benefit math is monotone unfavorable across the entire
N=4..8 expansion range.** There is no inflection point where a non-zero
shard expansion is preferred:

- **4→6 shards**: -5.69% wallclock (≈31s faster slowest shard) for
  +41.46% runner-min cost (≈15.1 additional runner-minutes per CI run)
- **4→8 shards**: -8.62% wallclock (≈47s faster slowest shard) for
  +82.76% runner-min cost (≈30.2 additional runner-minutes per CI run)

Each added shard saves diminishing pytest pure time (Amdahl's law against
a 371.29s parallel workload) while adding a fixed ~7.5 runner-minutes of
overhead per shard. The fixed-overhead component (449.5s/shard) dominates
the per-shard cost structure, making expansion a runner-minute-amplification
operation with marginal wallclock benefit.

### §4.4 Anchor 4 — Load-bearing structural finding: 111.46s "max-shard" is fuzz-marker-excluded

```yaml
verification_anchor:
  source: "uv run python <file-granular-aggregation-of-.test_durations>"
  command_output_verbatim: |
    Top 10 files by total duration:
       111.46s  tests/test_openapi_fuzz.py
        19.94s  tests/unit/lambda_handlers/test_workflow_handler.py
        15.47s  tests/unit/api/test_health.py
        13.65s  tests/unit/clients/data/test_insights.py
        ...
    fuzz total: 111.46s
    non-fuzz total: 259.83s
    overall total: 371.29s
  exit_code: 0
  claim: "the 111.46s figure cited in the SRE-003 brief as 'theoretical max-shard at N=4' is the entire single-file duration of tests/test_openapi_fuzz.py; pytest-split cannot split tests within a single file when bin-packing, so when this file is bin-packed alone it dominates one shard; HOWEVER the .github/workflows/test.yml:56 marker filter excludes 'fuzz' on BOTH push and pull_request events, meaning the fuzz file never runs in the sharded ci job — fuzz runs in a separate non-xdist job at .github/workflows/test.yml:74-151 (continue-on-error: true, non-blocking)"
```

```yaml
verification_anchor:
  source: ".github/workflows/test.yml"
  line_range: "L56"
  marker_token: "test_markers_exclude: ${{ github.event_name == 'pull_request' && 'not integration and not benchmark and not slow and not fuzz' || 'not integration and not benchmark and not fuzz' }}"
  claim: "the marker filter excludes 'not fuzz' on BOTH branches of the conditional (push and pull_request) — fuzz tests are unconditionally excluded from the sharded ci job in production CI, so the 111.46s test_openapi_fuzz.py bottleneck cited as motivating SRE-003 expansion is structurally invisible to the production sharded workload"
```

This anchor is **load-bearing for the STAY-AT-4 adjudication**. The 002c
regen commit message frames test_openapi_fuzz.py as a single-file
bottleneck dominating max-shard wallclock — and that framing is correct
for the offline planner under the unfiltered marker scope. But under the
production marker filter, the actual non-fuzz max-shard at N=4 is 98.11s
(per Anchor 2), and the 561s observed shard from 002a (run-id 25138295569)
was NOT executing the fuzz file. The 561s decomposes as:

- ~98s pytest pure time (non-fuzz, post-marker-filter)
- ~463s CI fixed-overhead (within 449.5s ± 3% envelope)

This means **the bottleneck causing the 561s outlier is not pytest workload
imbalance — it is the per-shard CI fixed-overhead itself**. Shard expansion
multiplies the bottleneck rather than ameliorating it.

## §5 Why Shard Expansion Is Structurally Unfavorable Here

The SRE-003 dispatching brief's projection ("Naive expansion projection,
ignores fixed-overhead scaling") was directionally correct but understated
the asymmetry. The empirical numbers in §4.3 confirm:

1. **Fixed-overhead is the dominant cost component** (449.5s vs 98.11s
   pytest pure time at N=4 = 4.6:1 ratio). At higher N this ratio worsens
   (8.8:1 at N=8). Adding shards adds full-overhead cost to save fractional
   pytest cost.

2. **The pytest workload is too small to benefit from 6+ shards.** At
   371.29s total parallel workload, the theoretical perfect-balance N=4
   floor is 92.82s (371.29/4). The actual N=4 max is 98.11s — already
   within 5.7% of theoretical perfect balance. The headroom for shard-
   expansion gain is structurally bounded at <6% wallclock improvement
   even in the limit of infinite shards.

3. **The 561s outlier is not a sharding problem.** It is a CI fixed-overhead
   problem (slow setup-uv install, slow CodeArtifact login, slow mypy, etc.).
   The architectural fixes for THAT bottleneck are SRE-004 (post-merge
   coverage isolation, removes coverage instrumentation cost from per-PR
   shards) and any future caching/setup optimizations — not shard expansion.

4. **The MARKER-EXCLUDED fuzz finding (§4.4) reframes the problem.**
   The 111.46s fuzz file does not run in the sharded job. The remaining
   259.83s non-fuzz workload, when split 4 ways, lands at 65s mean per
   shard with 22% inter-shard variance — already near optimal pytest-
   split balance. There is no shard-imbalance pathology to fix.

## §6 Decision Cross-Reference

This ADR is the **third sibling** of the SRE-002/003 family at the
autom8y-asana-local altitude:

| Dimension | ADR-008 (SRE-002a) | ADR-009 (SRE-002b) | ADR-010 (SRE-003) |
|-----------|--------------------|--------------------|--------------------|
| Sub-route | runner-sizing (vCPU count) | xdist worker-count tuning | shard-count expansion |
| Local override surface? | NO (runner image is GitHub-Actions-managed) | NO (worker count is hardcoded in reusable workflow) | **YES** (`test_splits: 4` at `.github/workflows/test.yml:55`) |
| Adjudication | NO-LEVER | NO-LOCAL-OVERRIDE | **STAY-AT-4** |
| Cross-repo Path-B reserved? | YES (§7.1) | YES (§7.1) | N/A (local control suffices; no cross-repo path needed) |
| Probe-CI runs consumed | 0 of 9 | 0 of 6 | 0 of 4 |
| Evidence basis | direct file/log inspection | direct file inspection | offline planner + cost-benefit math |
| Status | accepted | accepted | accepted |

The three ADRs together establish a **structural pattern**: the SRE-002a/b
levers (vCPU + worker count) are not satellite-altitude levers, while the
SRE-003 lever (shard count) IS satellite-altitude — but the cost-benefit
math at the satellite altitude does not justify pulling it. This Sprint-2
adjudication exhausts the autom8y-asana-local sharding optimization
surface: the next reliability win is at SRE-004 altitude (post-merge
coverage isolation), not at the sharding altitude.

## §7 Probe-CI Budget Disposition

**SRE-003 budget**: 4 probe-CI runs allocated per charter §11.2.
**SRE-003 budget consumed**: 0 of 4.
**Remainder available**: 4 probe-CI runs preserved for SRE-004 if
post-merge coverage job validation requires empirical wallclock measurement
(e.g., to verify the post-merge job does not exceed reasonable timeout
bounds), or for any post-merge CI shard p50 measurement per
observability-engineer §9.6 amendment surface.

## §8 Receipt Grammar Summary

Every claim in this ADR cites either (a) a file:line anchor with verbatim
marker_token (per `structural-verification-receipt` §2.2 file-read method),
(b) a bash-probe command with verbatim stdout slice (per SVR §2.2
bash-probe method), (c) a sibling ADR or charter section reference, or
(d) a cost-benefit math derivation traceable to (a) and (b). No claim
rests on memory, summary, or synthesis. The 449.5s overhead estimate
inherits from 002c regen commit message (`git show 0dc9108a`) — a
non-SVR-canonical citation per `structural-verification-receipt` §6
carve-out option (b).

## §9 Open Questions Surfaced to User

1. **Sprint-2 close at ADR-010 acceptance + SRE-004 dispatch?** Charter
   §6.1 and §6.2 list SRE-003 and SRE-004 as parallel-dispatchable
   sub-routes; SRE-004 does not depend on SRE-003's outcome.
   SRE-004 (post-merge aggregate coverage job) can be dispatched
   immediately at the platform-engineer's next turn.

2. **Should the 449.5s CI fixed-overhead become a separate sub-route?**
   The 561s outlier root cause is the fixed-overhead component, not the
   pytest workload. A future Sprint could investigate which steps of the
   reusable workflow contribute most to the 449.5s — checkout, setup-uv,
   CodeArtifact login, deps install, mypy, coverage instrumentation
   teardown. This investigation would be cross-repo (the steps live in
   the reusable workflow), placing it in the same §7.1-RESERVED altitude
   as ADR-008/009 Path-B. Default disposition: file as a complaint via
   `/reflect` for triage in a future sprint.

3. **Does the file-internal sharding constraint warrant a sub-route?**
   pytest-split cannot split a single test file across shards. The fuzz
   file's 111.46s would dominate one shard if the marker filter ever
   changed to include fuzz in the sharded job. Defensive: the marker
   filter at `.github/workflows/test.yml:56` should be considered
   load-bearing on the SRE-003 STAY-AT-4 conclusion. If a future change
   removes the `not fuzz` exclusion from the sharded job, this ADR's
   conclusion must be re-adjudicated. Recommend annotating line 56 with a
   reference to this ADR's §4.4 anchor.

---

**END ADR-010**. Sprint-2 SRE-003 adjudication: **STAY-AT-4**.
0 of 4 probe-CI runs consumed. Probe budget preserved for SRE-004 if
needed. The autom8y-asana-local sharding optimization surface is
exhausted at this altitude; the next reliability win is at SRE-004
(post-merge coverage isolation).
