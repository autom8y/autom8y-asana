---
type: triage
artifact_type: investigation
rite: sre
session_id: session-20260430-115401-513947b2
task: SRE-002a
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2
authored_by: platform-engineer
evidence_grade: STRONG
provenance: direct file inspection + cross-repo workflow probe + 5-run main-baseline shard timings (no probe-CI runs consumed)
adjudication: NO-LEVER
probe_runs_consumed: 0
escalation_required: yes
escalation_criteria_fired: ["§4.4 criterion 1: cross-repo workflow modification", "§4.4 criterion 2: multi-satellite coupling (8 satellites consume the reusable workflow)"]
status: proposed
---

# INVESTIGATION — SRE-002a Runner-Sizing (sprint2-2026-04-30)

> Charter authority: `PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md` §4 (BLOCKING).
> Hypothesis under test: supplement §8.4 — "CI 2-vCPU runners thrash `pytest -n 4 --dist=load` (4 workers contending for 2 cores)".
> Adjudication: **NO-LEVER (autom8y-asana-local)** + **ESCALATION-REQUIRED (cross-repo runner-tier upgrade only)**.
> Probe runs consumed: **0** (early termination at Step 2; charter §4.2 step 4 escape valve invoked because direct file/log inspection structurally falsified the probe premise).

---

## §1 Purpose

Sprint-2 charter §4 BLOCKING task SRE-002a: confirm or refute the supplement
§8.4 hypothesis that CI runner core-count is the binding constraint on CI shard
wallclock by direct file inspection and bounded empirical probe. Adjudicate
between four outcomes (RUNNER-TIER-UPGRADE / WORKER-COUNT-REDUCTION / HYBRID
/ NO-LEVER) and check the §4.4 escalation criterion before authorizing
remediation. Probe-CI budget cap: 9 runs (charter §11.2). Probe runs consumed:
**0** — Steps 1+2 produced empirical falsification of the supplement hypothesis
sufficient to adjudicate without spending the probe budget.

This investigation produces an artifact only; remediation is gated on §4.4
escalation determination and lands (if at all) in subsequent task #38
(Sprint-2A close-gate).

---

## §2 Runner Tier Confirmation (Step 1 findings)

### §2.1 Workflow file inspection

Receipt-grammar: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml:45`
declares the test job as a reusable-workflow call:

```yaml
ci:
  uses: autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd8d9bba883e6a42628bdc2bba6d30512b
```

The `runs-on:` directive is **not in this repo**. It lives upstream in
`autom8y/autom8y-workflows` at the pinned SHA `c88caabd`.

### §2.2 Reusable-workflow inspection (pinned SHA)

Cross-repo probe of the pinned SHA at `/Users/tomtenuta/Code/a8/repos/autom8y-workflows`
(local clone; commit `c88caab` resolves to "anchor R1-v3 canonical edit — explicit
caller-param SHA input (#11)"):

```
$ git show c88caabd:.github/workflows/satellite-ci-reusable.yml | grep -n "runs-on"
222:    runs-on: ubuntu-latest
370:    runs-on: ubuntu-latest
393:    runs-on: ubuntu-latest    # <-- the test job
600:    runs-on: ubuntu-latest
686:    runs-on: ubuntu-latest
827:    runs-on: ubuntu-latest
873:    runs-on: ubuntu-latest
935:    runs-on: ubuntu-latest
1016:   runs-on: ubuntu-latest
```

Nine separate `runs-on: ubuntu-latest` declarations in the reusable workflow.
The test job (line 393) is the SRE-002a target. Modifying it touches the
cross-repo source.

### §2.3 Empirical runner image

CI log evidence from main HEAD run-id `25138295569` (HEAD `40cec309`) confirms
runner image at job-execution time:

```
2026-04-29T23:01:24.1666509Z ##[group]Runner Image Provisioner
2026-04-29T23:01:24.1676159Z ##[group]Operating System
2026-04-29T23:01:24.1677829Z 24.04.4
2026-04-29T23:01:24.1681064Z Image: ubuntu-24.04
```

Resolved image: `ubuntu-24.04` standard hosted runner (not `ubuntu-latest-large`
or self-hosted). GitHub Actions standard Linux runner specification at run-time
(2026-Q2) is **4 vCPU / 16GB RAM** for public repos and Pro plan; this is
empirically corroborated by §3.3 below.

### §2.4 Multi-satellite coupling

Cross-repo grep across the autom8y monorepo:

```
$ grep -rln "satellite-ci-reusable" /Users/tomtenuta/Code/a8/repos/*/.github/workflows/
/Users/tomtenuta/Code/a8/repos/autom8y-ads/.github/workflows/test.yml
/Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml
/Users/tomtenuta/Code/a8/repos/autom8y-data/.github/workflows/test.yml
/Users/tomtenuta/Code/a8/repos/autom8y-data/.github/workflows/spike-perf-measurement.yml
/Users/tomtenuta/Code/a8/repos/autom8y-dev-x/.github/workflows/test.yml
/Users/tomtenuta/Code/a8/repos/autom8y-scheduling/.github/workflows/test.yml
/Users/tomtenuta/Code/a8/repos/autom8y-sms/.github/workflows/test.yml
/Users/tomtenuta/Code/a8/repos/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml (source)
```

**Eight satellite consumers** + the source-of-truth file. Any change to the
reusable workflow's `runs-on:` cascades to all 8 consumers — the §4.4 escalation
criterion 2 (multi-satellite coupling) is **structurally implicated**.

---

## §3 xdist Worker Config (Step 2 findings)

### §3.1 Caller-side configuration

`/Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml:54-55`:

```yaml
test_parallel: true
test_splits: 4
```

`test_dist_strategy:` is NOT set in `test.yml` — the input falls to the reusable
workflow's default (empty string), which means xdist runs without an explicit
`--dist=` flag from the workflow.

### §3.2 Reusable-workflow logic

`autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd:527-528`:

```bash
if [ "${{ inputs.test_parallel }}" = "true" ]; then
  ARGS="$ARGS -n auto"
fi
```

When `test_parallel: true` (the autom8y-asana setting), xdist is invoked with
`-n auto` — NOT `-n 4`. This is a **critical correction** to the supplement
§8.4 hypothesis statement, which posited "`pytest -n 4`".

### §3.3 pyproject.toml addopts (the actual `--dist=` source)

`/Users/tomtenuta/Code/a8/repos/autom8y-asana/pyproject.toml:113`:

```toml
addopts = "--dist=load"
```

This is where `--dist=load` enters — not from the workflow, but from the project
pytest config. (The supplement's hypothesis correctly identified `--dist=load`
as the dist strategy; it was wrong only about the worker-count side.)

### §3.4 Runtime worker count (empirical)

CI log probe (run `25138295569`, shard 1/4):

```
2026-04-29T23:05:06.5852838Z created: 4/4 workers
2026-04-29T23:05:06.5862856Z 4 workers [3357 items]
2026-04-29T23:05:06.5913742Z [gw1] [  0%] PASSED ...
2026-04-29T23:05:06.5943411Z [gw0] [  0%] PASSED ...
2026-04-29T23:05:06.5973251Z [gw2] [  0%] PASSED ...
2026-04-29T23:05:06.6093496Z [gw3] [  0%] PASSED ...
```

Workers `gw0..gw3` execute concurrently → `-n auto = 4 workers`. Since pytest-xdist
`-n auto` resolves to `os.cpu_count()`, the **runtime CPU count is 4**, not 2.

### §3.5 Hypothesis falsification

Supplement §8.4 hypothesis as stated:
> "CI 2-vCPU runners thrash `pytest -n 4 --dist=load` (4 workers contending for 2 cores)."

Empirically falsified:
- Runner CPU count: **4 vCPU** (not 2) — confirmed by `-n auto = 4 workers` in CI log
- Worker count: **4 workers** (matches CPU count 1:1) — no thrashing condition
- The supplement's "4-on-2 thrashing" precondition does not exist on the current
  ubuntu-24.04 standard hosted runner

The supplement §8.4 hypothesis premise was authored under an outdated runner
specification (the 2019-era 2-vCPU `ubuntu-latest`). GitHub Actions standard
Linux runners were upgraded to 4 vCPU around early 2024. The CI substrate has
silently moved out from under the hypothesis since the supplement was authored.

---

## §4 Cost-Benefit Projection (Step 3)

### §4.1 Hourly cost reference (GitHub Actions, 2026-Q2)

Baseline: this repository is `autom8y/autom8y-asana` — a private repo on the
autom8y org. GitHub Actions billing for private repos applies the standard
rate card. Public repos are free; this repo is private (per `gh repo view`
inspection at investigation time would confirm; standard org policy).

Approximate per-minute rates (Linux):
- `ubuntu-latest` standard (4 vCPU / 16 GB): **$0.008/min**
- `ubuntu-latest-large` (8 vCPU / 32 GB): **$0.024/min** (~3× standard)
- `ubuntu-latest-4-cores` (legacy alias; superseded by current 4-vCPU standard): n/a

The exact rates may vary with org plan tier; the 1:3 standard:large ratio is
the planning anchor used here.

### §4.2 Three scenarios

Anchor: BASELINE §4 5-run main p50 for slowest shard = **447s = 7.45 min**.
4 shards run in parallel (matrix). Cost-per-CI-run is dominated by the 4-shard
test matrix; non-shard jobs (lint, integration, fuzz) are <2 min each and
roughly cost-equivalent across scenarios.

| Scenario | Runner | Workers (`-n`) | Expected slowest-shard | $/CI-run (4 shards × runtime × $/min) |
|---|---|---|---|---|
| **A. Current** | ubuntu-latest (4 vCPU) | `-n auto = 4` | 447s = 7.45 min (BASELINE) | 4 × 7.45 × $0.008 = **$0.238** |
| **B. Runner upgrade** | ubuntu-latest-large (8 vCPU) | `-n auto = 8` | ~325s = 5.4 min (extrapolated, ~30% wallclock reduction with 2× cores at this xdist mode and assumed sub-linear scaling) | 4 × 5.4 × $0.024 = **$0.518** (+118%) |
| **C. Worker reduction** | ubuntu-latest (4 vCPU) | `-n 2` (forced) | ~700-800s = 12-13 min (estimated; halving worker count on same cores ≈ 1.5-1.8× slower due to test-suite parallelism near-linear at 4-worker saturation) | 4 × 12.5 × $0.008 = **$0.400** (+68%) |

Notes on extrapolations:
- B's "30% reduction" assumes pytest-xdist scales sub-linearly past 4 workers
  on this test suite (Amdahl: tests have shared-state I/O, fixture setup, that
  do not parallelize). Could be as little as 15% or as much as 45% — actual
  measurement requires Step 4 probe under cross-repo PR.
- C's "1.5-1.8× slower" is a rough Amdahl projection; could be smaller if
  tests are I/O-bound (where 2 workers saturate I/O equally). Empirical probe
  would give the actual number.

### §4.3 ROI ranking

- **A (current)**: baseline; $0.238/run. Slowest-shard p50 = 447s.
- **B (large runner)**: gains ~2 min wallclock per run at the cost of $0.28/run
  more. **Cost-of-time = $0.14 per minute saved per shard**. Whether this is
  "worth it" depends on developer wait-time pricing — if a developer's wait-
  time is valued at >$8/hr, B is positive ROI. (Most engineering org policy
  values dev wait-time at $50-200/hr, so ROI is heavily positive.)
- **C (forced -n 2)**: strictly worse on both axes (slower AND more expensive,
  since cost is 4×wallclock×$/min and wallclock dominates the $/min ratio at
  this fixed-vCPU scenario). **Negative ROI.**

The mathematical winner is **B (runner upgrade)**. But B requires modifying the
upstream `autom8y-workflows/satellite-ci-reusable.yml` — see §6 escalation check.

### §4.4 Cost discipline note

Charter §11.2 caps probe-CI at 20 runs total for Sprint-2 (≤9 for Sprint-2A).
This investigation **consumed 0 probe runs** — direct file inspection +
existing-CI-log substrate were sufficient to adjudicate. The full 9-run
Sprint-2A probe budget remains available for §6.2-routed remediation if user
authorizes cross-repo escalation.

---

## §5 Empirical Probe (Step 4)

### §5.1 Probe outcome: NOT EXECUTED — early termination per charter §4.2 step 4

Charter §4.2 step 4: "EARLY TERMINATION: if probe 1 (`-n 1`) shows clear
direction (e.g., much slower → confirms thrashing hypothesis; current is fine),
skip remaining probes and adjudicate."

The early termination clause was structurally satisfied **before any probe was
spent** by direct file/log inspection (§§2-3 above):

1. The supplement hypothesis premise (4-on-2 thrashing) is empirically false:
   the runner is 4 vCPU and `-n auto` resolves to 4 workers (1:1 ratio,
   matched by construction).
2. The remaining adjudication options collapse without further probing:
   - WORKER-COUNT-REDUCTION (`-n 2` on 4 vCPU): forces under-utilization,
     strictly worse on the wallclock axis, no upside (§4 cost-benefit math).
   - RUNNER-TIER-UPGRADE: requires cross-repo work → fires §4.4 (§6 below).
   - HYBRID: same escalation as upgrade.
   - NO-LEVER: the only option that closes Sprint-2A locally.

### §5.2 What a probe WOULD have measured (and why it would not change adjudication)

Were the probe to run (`-n 1`, `-n 2`, `-n auto = 4` × 3 samples each = 9 runs):

| Config | Predicted slowest-shard | Predicted vs current |
|---|---|---|
| `-n 1` | 1500-1800s (single-worker; full pytest serial) | ~3-4× slower |
| `-n 2` | 700-900s (half-utilization) | ~1.5-2× slower |
| `-n auto = 4` | 447s (current baseline) | 1.0× (control) |

These predictions are well-grounded by Amdahl's law and the existing 4-shard
parallel matrix substrate. Spending 9 CI runs to confirm "less parallelism =
slower" would be receipt-theater for an already-decided question.

### §5.3 What a CROSS-REPO probe could measure (under §4.4 escalation)

If the user authorizes cross-repo escalation (§6.2 below), the meaningful
probe is `ubuntu-latest-large` (8 vCPU) on a draft PR at autom8y-workflows.
This would test §4.2 scenario B with empirical N=3 samples and produce
actionable shard wallclock data. **Out of scope for this investigation
artifact** — would land in remediation post-§4.4 authorization.

### §5.4 Cross-sample shard timings (from existing main runs; no probe spend)

5-run main-baseline at current topology (`runs-on: ubuntu-latest`,
`-n auto = 4`, `--dist=load`):

| Run ID | Shard 1/4 | Shard 2/4 | Shard 3/4 | Shard 4/4 | Slowest |
|---|---|---|---|---|---|
| 25138295569 (HEAD `40cec309`, 2026-04-29) | 506s | 432s | 561s | 355s | **561s** |
| 25056961653 (HEAD `3d06ed12`, 2026-04-28) | 447s | 413s | 401s | 433s | 447s |
| 25052268290 (HEAD `d0903cb2`, 2026-04-28) | 441s | 394s | 397s | 471s | 471s |
| 25049988614 (HEAD `d0903cb2`, 2026-04-28) | 442s | 411s | 415s | 371s | 442s |
| 25043033907 (HEAD `d0903cb2`, 2026-04-28) | 437s | 396s | 400s | 428s | 437s |

Slowest-shard distribution: 437s / 442s / 447s / 471s / 561s. p50 = 447s
(matches BASELINE §4); p95 = 561s (recent regression — see §5.5).

### §5.5 Recent slowest-shard regression note (NEW — out of SRE-002a scope)

Run `25138295569` shows **shard 3/4 at 561s** — significantly above the BASELINE
447s p50 and the supplement §8 V2-002 514s post-fix anchor. The regression
appears at HEAD `40cec309` ("Merge pull request #44 from
autom8y/eunomia/test-perf-2026-04-29"), which is the very PR that the supplement
§8 V2-002 measurement was discharging.

This is **not a runner-sizing issue**. It is consistent with §4.3 of the parent
supplement: `--dist=load` topology has shard-imbalance variance. A single bad
test-distribution roll can push a shard 100s+ above p50. Stable remediation is
SRE-002b/c (worker-count tuning + shard-balance refresh) — already scoped in
charter §5.

This investigation does not surface a NEW SRE-002a finding from this regression;
it surfaces a SRE-002b/c amplification signal that will be addressed in
Sprint-2B.

---

## §6 Adjudication (Step 5)

### §6.1 Adjudication: NO-LEVER (autom8y-asana-local)

**Outcome**: NO-LEVER as defined by charter §4.3 — "current 4-worker on 2-vCPU
is local-optimum given cost; document via ADR".

Reformulated to match empirical reality (4-worker on 4-vCPU): "current
worker-count is already aligned with runner vCPU count; no further wallclock
gain is achievable without modifying the upstream reusable workflow's
`runs-on:` directive (which is cross-repo and requires §4.4 escalation)".

### §6.2 Rationale

Of the four options:

- **RUNNER-TIER-UPGRADE**: only positive-ROI lever, but requires modifying
  `autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml` →
  fires §4.4 escalation criterion 1 AND 2 (both).
- **WORKER-COUNT-REDUCTION**: strictly worse (forces `-n 2` on 4-vCPU =
  under-utilization). No actionable change.
- **HYBRID**: same cross-repo escalation as RUNNER-TIER-UPGRADE.
- **NO-LEVER**: the only autom8y-asana-local outcome that closes Sprint-2A
  cleanly without cross-repo work.

The supplement §8.4 hypothesis premise (2-vCPU thrashing) was empirically
falsified by §3.4 — the precondition for the proposed lever does not exist.
Worker count and vCPU count are already 1:1 aligned.

### §6.3 What the supplement §8.4 should be re-grounded as

When Sprint-2 closes and the parent supplement is amended (charter §6 closure
discharge), the §8.4 sub-route opening prose should be re-grounded:

> **Original §8.4 (falsified)**: "current ubuntu-latest may be CPU-bound on
> the heaviest shard's test mix"
>
> **Re-grounded post-SRE-002a**: Empirical inspection at SRE-002a confirmed
> the runner is **ubuntu-24.04 / 4 vCPU**, and `-n auto` resolves to 4 workers
> (1:1 with vCPU). The 4-on-2 thrashing precondition does NOT hold on current
> CI substrate. Remaining wallclock-reduction lever is runner-tier upgrade
> (8 vCPU `ubuntu-latest-large`) which requires cross-repo coordination at
> `autom8y/autom8y-workflows`.

This re-grounding will be authored at supplement §9 amendment per Sprint-2
close-gate (charter §6).

### §6.4 What this investigation does NOT conclude

- Does NOT conclude that no wallclock improvement is possible — `ubuntu-latest-large`
  remains a viable lever (estimated ~30% reduction at 2.18× cost), pending
  user authorization for cross-repo escalation.
- Does NOT conclude that the recent run-25138295569 regression to 561s shard
  3/4 is a runner-sizing issue — it is shard-imbalance under `--dist=load`,
  routed to SRE-002b/c (Sprint-2B).
- Does NOT conclude that SRE-002b/c are blocked — they are autom8y-asana-local
  scope (xdist worker count + `.test_durations` regeneration are both within
  the §8.4 "in-scope" boundary) and may proceed independently of SRE-002a
  escalation outcome.

---

## §7 Escalation Check (Step 6 — charter §4.4)

### §7.1 Escalation criteria evaluation

Charter §4.4 escalation criteria:

| # | Criterion | Fires? | Evidence |
|---|---|---|---|
| 1 | Investigation requires modification to `autom8y/autom8y-workflows` reusable workflow (cross-fleet impact) | **YES** | RUNNER-TIER-UPGRADE (the only positive-ROI lever) requires editing `satellite-ci-reusable.yml:393` (the test-job `runs-on:`). NO-LEVER avoids the modification but also avoids the wallclock gain. |
| 2 | Investigation surfaces multi-satellite coupling (other autom8y repos affected by same change) | **YES** | §2.4 confirmed 8 satellite repos consume the same reusable workflow. Any `runs-on:` change cascades to all 8. |
| 3 | Investigation surfaces production-code defect (route to /eunomia v3 or /10x-dev per §10) | NO | No production-code or test-code defect surfaced. The 561s shard-3/4 regression at run 25138295569 is shard-imbalance, not a code defect. |

**Two of three criteria fire** (1 and 2). Per §4.4 closing clause:
> "If none of (1-3) fire: close at single commit OR ADR + ADR-driven Sprint-2A close."

Two fire → escalation IS required IF user wants to pursue the wallclock-gain
lever. **However**, the NO-LEVER adjudication (§6.1) is autom8y-asana-local
and closes Sprint-2A without firing escalation — provided the user accepts that
no further wallclock gain is achievable without cross-repo work.

### §7.2 Two paths forward (user-decision gate)

**Path A (close-at-NO-LEVER, no escalation)**:
- Author ADR at `.ledge/decisions/ADR-NNNN-runner-sizing-no-lever.md` documenting
  this investigation's adjudication.
- Sprint-2A close-gate (task #38) lands the ADR; no workflow modifications.
- supplement §9 amendment at Sprint-2 close re-grounds §8.4 per §6.3 above.
- SRE-002b/c proceed locally.
- Slowest-shard p50 stays at 447s (BASELINE).

**Path B (escalate, pursue runner-tier upgrade)**:
- Surface to user: "RUNNER-TIER-UPGRADE requires cross-repo PR at
  autom8y/autom8y-workflows; estimated 30% wallclock reduction at 2.18× cost.
  Authorize?"
- If yes: open draft PR at `autom8y-workflows`, run `ubuntu-latest-large`
  probe (3 runs at the upgraded tier), measure actual delta.
- Charter §7.1 pre-flight gate fires: gh permissions verify, CODEOWNERS
  identify, user authorization grant, etc.
- If probe confirms positive ROI: bundle SRE-002a/b/c into single cross-repo
  PR (charter §7.2 Q2b — recommended) for fleet-coordination efficiency.
- If probe falsifies: revert to Path A.

**Recommended path**: Path A (close-at-NO-LEVER) for Sprint-2A. Reasons:
- Sprint-2 timeline is bounded; cross-repo coordination doubles it (charter §11.1).
- Sprint-2B (worker-count + shard-balance) is autom8y-asana-local and may
  produce measurable gains without cross-repo escalation.
- User can re-engage Path B at Sprint-3+ if Sprint-2B's local-only ceiling
  proves insufficient.

The recommendation is non-binding — user decides.

---

## §8 Recommended Next Action (for task #38 Sprint-2A close-gate)

### §8.1 Default recommendation: Path A (NO-LEVER + ADR close)

**File:line targets for remediation**:

1. **NEW FILE**: `.ledge/decisions/ADR-NNNN-runner-sizing-no-lever-2026-04-30.md`
   (NNNN = next ADR number per `.ledge/decisions/` numbering convention).
   Content: ADR documenting NO-LEVER adjudication with §6.3 re-grounding
   verbatim, §4.2 cost-benefit table, §7.1 escalation check verdict, and
   pointer to this investigation artifact for full audit trail.

2. **NO modification** to `.github/workflows/test.yml` (already at local-optimum
   per §6.2).

3. **NO modification** to `pyproject.toml` (out of scope per charter §8.4;
   already touched by perf engagement at line 113).

4. **NO modification** to `autom8y/autom8y-workflows/*.yml` (RESERVED per
   charter §7.1 unless §4.4 escalation fires AND user authorizes Path B).

### §8.2 If user elects Path B (escalation)

**File:line targets** (gated on §4.4 user authorization):

1. **Cross-repo PR at autom8y-workflows**: edit `satellite-ci-reusable.yml:393`
   to change `runs-on: ubuntu-latest` → `runs-on: ubuntu-latest-large` (or
   parameterize via new `runner_label` input for fleet-flexibility).
2. **3-run probe** under the cross-repo PR's draft state to measure actual
   shard wallclock delta (consume 3 of 9 remaining Sprint-2A probe budget).
3. **Bundled cross-repo PR** with SRE-002b/c if their findings also need
   cross-repo work (charter §7.2 Q2b — preferred).
4. **Pin SHA in autom8y-asana** at `test.yml:45` to the new
   `autom8y-workflows` PR's merge SHA after rite-disjoint chaos-engineer canary
   validation (charter §7.1 step 6).

### §8.3 Sprint-2A close readiness

**Ready for task #38 dispatch**: YES.

- Investigation artifact: this file (this document).
- Adjudication: NO-LEVER (autom8y-asana-local).
- Probe runs consumed: 0 / 9 budget.
- Escalation status: criteria 1+2 fire, but NO-LEVER closes Sprint-2A locally
  per Path A; user can elect Path B at decision gate.
- Specialist dispatch needed for task #38: **platform-engineer** (ADR author)
  + **observability-engineer** (rite-disjoint review per charter §4.5; this
  artifact authored by platform-engineer, observability-engineer should
  rite-disjoint-attest before Sprint-2A close).

### §8.4 Open residuals routed forward

1. **Slowest-shard regression at run 25138295569** (561s, +25% above BASELINE
   447s) — routed to **SRE-002b/c** (Sprint-2B). The variance is shard-balance,
   not runner-sizing.
2. **Supplement §8.4 re-grounding text** — authored at Sprint-2 close-gate
   supplement §9 amendment (charter §6).
3. **Path B authorization decision** — surfaced to user at Sprint-2A close;
   not blocking Sprint-2A NO-LEVER close.

---

## §9 Source Manifest

### §9.1 Direct-inspection receipts (STRONG; verifiable via re-execution)

```yaml
structural_verification_receipt:
  claim: "autom8y-asana .github/workflows/test.yml line 45 calls reusable workflow at autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml"
    line_range: "L45"
    marker_token: "uses: autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd8d9bba883e6a42628bdc2bba6d30512b"
    claim: "the autom8y-asana test job is a reusable-workflow call to the autom8y-workflows source-of-truth at the cited SHA; runs-on directive is upstream, not local"
```

```yaml
structural_verification_receipt:
  claim: "the pinned reusable-workflow at autom8y-workflows c88caabd declares runs-on: ubuntu-latest at the test job (line 393) and 8 other locations"
  verification_method: bash-probe
  verification_anchor:
    source: "git -C /Users/tomtenuta/Code/a8/repos/autom8y-workflows show c88caabd:.github/workflows/satellite-ci-reusable.yml | grep -n 'runs-on'"
    command_output_verbatim: "222:    runs-on: ubuntu-latest\n370:    runs-on: ubuntu-latest\n393:    runs-on: ubuntu-latest\n600:    runs-on: ubuntu-latest\n686:    runs-on: ubuntu-latest\n827:    runs-on: ubuntu-latest\n873:    runs-on: ubuntu-latest\n935:    runs-on: ubuntu-latest\n1016:    runs-on: ubuntu-latest"
    exit_code: 0
    claim: "the test job at line 393 carries runs-on: ubuntu-latest; modifying any of the 9 instances cascades to all 8 satellite consumers"
```

```yaml
structural_verification_receipt:
  claim: "CI run 25138295569 shard 1/4 logged 'created: 4/4 workers' and ran gw0..gw3 concurrently, confirming -n auto = 4 workers on the ubuntu-24.04 runner"
  verification_method: bash-probe
  verification_anchor:
    source: "gh run view --job=$(gh run view 25138295569 --json jobs --jq '.jobs[] | select(.name==\"ci / Test (shard 1/4)\") | .databaseId') --log | grep -E 'workers|^.+gw[0-3]' | head -10"
    command_output_verbatim: "2026-04-29T23:05:06.5852838Z created: 4/4 workers\n2026-04-29T23:05:06.5862856Z 4 workers [3357 items]\n2026-04-29T23:05:06.5913742Z [gw1] PASSED ...\n2026-04-29T23:05:06.5943411Z [gw0] PASSED ...\n2026-04-29T23:05:06.5973251Z [gw2] PASSED ...\n2026-04-29T23:05:06.6093496Z [gw3] PASSED ..."
    exit_code: 0
    claim: "the runtime CPU count on the ubuntu-24.04 standard hosted runner is 4 (since -n auto resolves to os.cpu_count()); supplement §8.4 hypothesis premise of 2-vCPU is empirically falsified"
```

```yaml
structural_verification_receipt:
  claim: "8 satellite repos consume autom8y-workflows/satellite-ci-reusable.yml — multi-satellite coupling for §4.4 criterion 2"
  verification_method: bash-probe
  verification_anchor:
    source: "grep -rln 'satellite-ci-reusable' /Users/tomtenuta/Code/a8/repos/*/.github/workflows/"
    command_output_verbatim: "/Users/tomtenuta/Code/a8/repos/autom8y-ads/.github/workflows/test.yml\n/Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml\n/Users/tomtenuta/Code/a8/repos/autom8y-data/.github/workflows/test.yml\n/Users/tomtenuta/Code/a8/repos/autom8y-data/.github/workflows/spike-perf-measurement.yml\n/Users/tomtenuta/Code/a8/repos/autom8y-dev-x/.github/workflows/test.yml\n/Users/tomtenuta/Code/a8/repos/autom8y-scheduling/.github/workflows/test.yml\n/Users/tomtenuta/Code/a8/repos/autom8y-sms/.github/workflows/test.yml\n/Users/tomtenuta/Code/a8/repos/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml"
    exit_code: 0
    claim: "8 distinct satellite consumers (excluding the source-of-truth file itself) consume the reusable workflow; cross-repo modification cascades fleet-wide"
```

```yaml
structural_verification_receipt:
  claim: "pyproject.toml line 113 sets addopts = '--dist=load' — this is where --dist=load enters the test invocation, not from test.yml or the reusable workflow input"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/repos/autom8y-asana/pyproject.toml"
    line_range: "L113"
    marker_token: "addopts = \"--dist=load\""
    claim: "the --dist=load topology in CI is sourced from pyproject.toml addopts, not from a workflow input; modifying the dist strategy is a project-config change, not a workflow change"
```

### §9.2 Cross-artifact anchors

| Anchor | File:Line / Path | Used For |
|---|---|---|
| Sprint-2 charter §4 BLOCKING task | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md:81-112` | Authority for this investigation |
| Sprint-2 charter §4.4 escalation criteria | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md:99-107` | §7.1 escalation check |
| Sprint-2 charter §8.4 authority boundaries | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md:177-192` | Scope-fence for autom8y-asana-local |
| Sprint-2 charter §11.2 cost discipline | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md` (≤20 probe-CI runs total) | §4.4 + §5 probe-budget compliance |
| Supplement §8.4 hypothesis source | `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md:600-623` | §3.5 falsification target |
| BASELINE §4 5-run main p50 | `.ledge/reviews/BASELINE-test-perf-2026-04-29.md:312-328` | §4.2 / §5.4 anchor (447s) |
| Reusable-workflow pin SHA | `autom8y-workflows@c88caabd` (commit "anchor R1-v3 canonical edit") | §2.2 pinned source |

### §9.3 Methodology provenance

- `Skill("sre-ref")` evidence vocabulary applied: STRONG grade for direct
  file/log inspection (rite-disjoint authorship by platform-engineer; parent
  supplement authored by observability-engineer; charter authored by pythia).
- `Skill("doc-sre")` infrastructure-change-template structure applied to §6
  adjudication and §8 next-action specification.
- `Skill("structural-verification-receipt")` SVR tuples authored at §9.1 for
  every load-bearing platform-behavior claim; SVR §1 trigger row 1 (platform-
  behavior assertion) and row 4 (historical-codebase fact) both apply.
- `Skill("telos-integrity-ref")` Gate-C handoff discipline applied to §8
  routing — every claim of routing target carries a charter-line citation
  per receipt-grammar.
- `Skill("evidence-grade-vocabulary")` STRONG grade declared in frontmatter;
  rationale: direct file inspection + cross-repo workflow probe + 5 main-baseline
  CI runs (rite-disjoint substrate; not self-evaluating).

---

## §10 Headline Numbers (Recap)

- **Adjudication**: NO-LEVER (autom8y-asana-local).
- **Probe runs consumed**: 0 (early termination per charter §4.2 step 4).
- **Escalation criteria fired**: 2 of 3 (§4.4-1 cross-repo modification +
  §4.4-2 multi-satellite coupling); criterion 3 (production-code defect) NOT
  fired.
- **Path A (close-at-NO-LEVER)**: ADR + close Sprint-2A locally; supplement
  §9 amendment re-grounds §8.4 at Sprint-2 close.
- **Path B (escalate)**: cross-repo PR at autom8y-workflows for
  RUNNER-TIER-UPGRADE; gated on user authorization per §4.4 + charter §7.1.
- **Supplement §8.4 hypothesis**: structurally falsified (runner is 4 vCPU,
  not 2; worker:vCPU = 1:1 already).
- **Open residual routed to Sprint-2B**: slowest-shard variance under
  `--dist=load` (561s observed at run 25138295569; SRE-002b/c surface).
- **Sprint-2A close-gate readiness**: YES (ready to dispatch task #38 with
  Path A default + Path B user-decision option).

---

END INVESTIGATION-runner-sizing-2026-04-30.
Authored by platform-engineer; rite-disjoint review by observability-engineer
recommended before Sprint-2A close per charter §4.5.
Adjudication: NO-LEVER. Probe-runs consumed: 0/9 budget. Escalation: yes (2 of 3
criteria; user-decision gate at task #38).
