---
type: decision
artifact_type: adr
adr_number: 008
title: "SRE-002a Runner-Sizing — NO-LEVER (autom8y-asana-local)"
status: accepted
date: 2026-04-30
rite: sre
session_id: session-20260430-115401-513947b2
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2
supplement: VERDICT-test-perf-2026-04-29-postmerge-supplement.md §8.4 (re-grounding source)
investigation: .sos/wip/sre/INVESTIGATION-runner-sizing-2026-04-30.md
evidence_grade: STRONG
provenance: zero-cost empirical falsification via direct file/log inspection (0 of 9 probe-CI runs consumed)
authored_by: platform-engineer
adjudication: NO-LEVER (autom8y-asana-local)
escalation_status: criteria-1+2-fire-but-Path-A-closes-locally
path_b_status: RESERVED (cross-repo upgrade probe; requires explicit user authorization per charter §7.1)
---

# ADR-008 — SRE-002a Runner-Sizing — NO-LEVER (autom8y-asana-local)

## §1 Context

Sprint-2 (`PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md`) inherited from the
parent post-merge supplement at
`.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` §8.4 a
sub-route SRE-002a — **runner-sizing investigation**.

The supplement §8.4 hypothesis cited (verbatim, `:609-610`):

> "(a) runner sizing (current ubuntu-latest may be CPU-bound on the heaviest
> shard's test mix)"

This hypothesis was elaborated upstream in the engagement chain as a
"2-vCPU runners thrash `pytest -n 4 --dist=load` (4 workers contending for
2 cores)" formulation — the binding-constraint claim that motivated opening
SRE-002a as a BLOCKING task in Sprint-2 charter §4.

The Sprint-2 charter §4 BLOCKING task SRE-002a was authorized to spend up to
9 probe-CI runs (charter §11.2, ≤9 for Sprint-2A) to confirm/refute the
hypothesis and adjudicate among four outcomes:

1. RUNNER-TIER-UPGRADE
2. WORKER-COUNT-REDUCTION
3. HYBRID
4. NO-LEVER

This ADR records the adjudication.

## §2 Decision

**NO-LEVER (autom8y-asana-local)** per investigation
`.sos/wip/sre/INVESTIGATION-runner-sizing-2026-04-30.md` §6.1.

**Probe runs consumed**: 0 of 9 (early termination per charter §4.2 step 4
escape valve; direct file/log inspection structurally falsified the probe
premise before any probe was spent).

**Evidence grade**: STRONG (zero-cost empirical falsification via direct file
and CI-log inspection; rite-disjoint substrate — investigation authored by
platform-engineer, supplement §8.4 hypothesis authored by observability-
engineer, charter authored by Pythia).

The supplement §8.4 hypothesis premise is structurally falsified: the runner
is empirically 4-vCPU and `-n auto` resolves to 4 workers, producing a 1:1
worker-to-core ratio. The "4-on-2 thrashing" precondition does not exist on
the current CI substrate.

Sprint-2A close-gate accepts NO-LEVER as the autom8y-asana-local outcome.
Path B (cross-repo runner-tier upgrade probe at `autom8y/autom8y-workflows`)
is RESERVED, not pursued in this engagement.

## §3 Empirical Falsification of Supplement §8.4 Thesis

The supplement §8.4 hypothesis cited "2-vCPU runners thrash `pytest -n 4
--dist=load`" as the binding constraint on CI shard wallclock. The
investigation directly inspected three load-bearing facts:

| Claim (per supplement §8.4 hypothesis) | Reality (per investigation §§2-3) | Source |
|---|---|---|
| "2-vCPU runner" | `ubuntu-24.04` standard hosted runner; **4-vCPU / 16GB RAM** | `gh run view 25138295569 --log` runner image stanza (investigation §2.3) + GitHub Actions standard Linux runner spec 2026-Q2 |
| "`-n 4` worker count (literal)" | `-n auto` (resolved by reusable workflow) | `autom8y-workflows@c88caabd:.github/workflows/satellite-ci-reusable.yml:527-528` (investigation §3.2) |
| Runtime worker count | **4 workers** (gw0..gw3 concurrent; matches `os.cpu_count() = 4`) | CI log run-25138295569 shard-1/4: `"created: 4/4 workers"` (investigation §3.4) |
| "4 workers contending for 2 cores → thrashing" | 4 workers on 4 cores = **1:1 ratio**; no thrashing precondition | direct from above three rows |

The supplement §8.4 prose was authored under an outdated runner specification
(the 2019-era 2-vCPU `ubuntu-latest`). GitHub Actions standard Linux hosted
runners were upgraded to 4 vCPU around early 2024. The CI substrate has
silently moved out from under the §8.4 hypothesis since the supplement was
authored — the hypothesis did not anticipate this, and the falsification is
detectable only by direct probe of the current substrate.

Investigation §3.5 records the falsification verdict; §9.1 records the
structural-verification receipts (SVR tuples) underlying each row of the
table above (`investigation §9.1`, file:line anchors verified).

## §4 Path A vs Path B Comparison

The investigation surfaced two paths forward (investigation §7.2):

### Path A (CHOSEN) — close-at-NO-LEVER + this ADR

- Author this ADR documenting the NO-LEVER adjudication.
- Sprint-2A closes locally at zero CI cost.
- Supplement §9 amendment re-grounds §8.4 prose without retroactive edit (see §5 forward routing).
- SRE-002b (xdist worker-count tuning) and SRE-002c (shard-balance refresh) inherit the actual empirical scope and proceed as Sprint-2B/C work — both are autom8y-asana-local per charter §8.4 in-scope.
- Slowest-shard p50 stays at 447s baseline (no regression risk introduced).

**Cost**: 0 probe-CI runs; 0 cross-repo PRs; 0 multi-satellite blast radius.

### Path B (REJECTED, RESERVED) — cross-repo PR for `ubuntu-latest-large` probe

- Open draft PR at `autom8y/autom8y-workflows` to change the test-job `runs-on:` directive at `satellite-ci-reusable.yml:393` from `ubuntu-latest` to `ubuntu-latest-large` (8-vCPU).
- Run 3-sample probe under the cross-repo PR's draft state.
- Charter §7.1 pre-flight protocol fires: `gh` permissions verify, CODEOWNERS identify, explicit user authorization grant, multi-satellite SHA pinning, chaos-engineer canary validation before promoting the merge SHA.
- Cross-repo blast radius: 8 satellite consumers of the reusable workflow (investigation §2.4 cross-repo grep).

**Cost projection** (investigation §4.2 scenario B):

- $/CI-run: $0.518 (vs current $0.238) — **+118% cost-per-CI-run**.
- Wallclock projection: ~30% reduction (extrapolated; could be 15-45% — actual measurement requires the probe).

**Why ROI is uncertain**: the current 4-vCPU substrate is NOT thrashing
(falsification per §3 above). A bigger runner may not move wallclock —
pytest-xdist is already parallel-saturated at 4 workers on 4 cores; Amdahl's
bound applies because tests have shared-state I/O and fixture setup that do
not parallelize. The expected gain is modest, and the cost is concrete.

### Why Path A wins this engagement

The empirical finding directly falsifies the hypothesis that motivated
opening SRE-002a as a BLOCKING task. With the premise gone, Path B becomes a
**SPECULATIVE optimization** — pursuing it would be:

1. **Out-of-proportion to the residual scope**: the supplement §8.4
   hypothesis was the only authority for opening 002a; with the hypothesis
   falsified, no charter authority remains for cross-repo work in this
   engagement.
2. **Multi-satellite blast radius for uncertain ROI**: 8 satellite repos
   consume the reusable workflow; a runner-tier change cascades fleet-wide.
3. **Charter §7.1 protocol is heavyweight**: explicit user authorization,
   multi-satellite SHA pinning, chaos-engineer canary — appropriate for a
   high-confidence positive-ROI lever, not a speculative one.

Path B remains a viable lever, just not for this engagement. See §5 for
forward routing.

## §5 Forward Routing

### §5.1 Sprint-2B inherits empirical scope from SRE-002b/c

The actual remaining wallclock-reduction surface is **shard-imbalance under
`--dist=load`**, not runner-sizing:

- **SRE-002b (xdist worker-count tuning)**: still has empirical scope. `-n auto` resolves to 4 workers, but `-n 2` may yield different ROI under shard-imbalance conditions (Amdahl effects shift when test mix is uneven). Sprint-2B will adjudicate.
- **SRE-002c (shard-balance refresh)**: still has empirical scope. The 561s shard-3/4 variance noted in investigation §5.4 (run `25138295569`, +25% above 447s p50) indicates `.test_durations` may need refresh under post-T1D `--dist=load` topology. Sprint-2B will adjudicate.

The 561s outlier is shard-imbalance noise, not a runner-sizing defect — it
is consistent with parent supplement §4.3 (`--dist=load` topology has
shard-imbalance variance). It routes cleanly to 002c.

### §5.2 Path B remains RESERVED for future engagement

If a future engagement determines that Sprint-2B's local-only ceiling is
insufficient AND positive-ROI for runner-tier upgrade is independently
established, Path B may be re-engaged via:

- A new architecture decision recording the runner-tier hypothesis with
  fresh substrate (HANDOFF-sre-to-arch).
- Or a re-engagement of /sre with explicit charter authority for cross-repo
  work (HANDOFF-sre-to-sre-v2).

Path B is not foreclosed permanently; it is foreclosed at THIS engagement's
altitude with THIS engagement's substrate.

### §5.3 Supplement §9 amendment

The parent supplement at `VERDICT-test-perf-2026-04-29-postmerge-supplement.md`
is amended in this same commit to append §9 (re-grounding amendment). The
§9 amendment:

- Does NOT retroactively edit §8.4 prose (preserves the historical record of
  /sre Sprint-1's hypothesis at that time).
- APPENDS a re-grounding clarification that records the Sprint-2 falsification
  finding and adjusts the actionable interpretation of §8.4 sub-routes
  post-falsification.
- References this ADR by number for the NO-LEVER adjudication anchor.

## §6 Consequences

### §6.1 Positive

- **Sprint-2A closes at zero CI cost**: 0 probe runs consumed; full 9-run
  budget preserved for Sprint-2B/C empirical probes.
- **Supplement §8.4 re-grounded transparently**: §9 amendment records the
  falsification without retroactive history rewriting.
- **No cross-fleet blast radius**: 8 satellite consumers of the reusable
  workflow are not perturbed.
- **Empirical record durable**: the investigation artifact and this ADR
  carry the verifiable receipts (file:line anchors + CI-log direct quotes)
  that make the falsification re-checkable in future engagements.

### §6.2 Negative

- **Parent VERDICT promotion depends on Sprint-2B/C delivering measurable
  wallclock reduction**: the runner-sizing lever is off the table in this
  engagement; if 002b/c yield <20% reduction, the parent VERDICT
  V2-002 promotion to PASS-CLEAN remains gated.
- **Velocity asymmetry preserved**: the 561s shard-3/4 outlier at run
  25138295569 (+25% above 447s p50) is not addressed by this ADR — it
  routes forward to Sprint-2B/C, but Sprint-2A does not improve the
  CI shard wallclock.

### §6.3 Trade-off accepted

- **Defer architectural runner-tier question for explicit future
  authorization**: this engagement does not absorb scope-creep into a
  cross-repo, multi-satellite, charter-§7.1-heavyweight decision.
- **Accept that the only positive-ROI lever (Path B) requires re-engagement**:
  if Sprint-2B/C ceiling is insufficient, the user must consciously
  authorize cross-repo work in a new engagement, not piggyback on this
  one's substrate.

## §7 References

### §7.1 Investigation artifact

- `.sos/wip/sre/INVESTIGATION-runner-sizing-2026-04-30.md` (630 lines, STRONG
  evidence-grade, 0 probe-CI consumed). This ADR's §3 falsification table
  rows trace to investigation §§2-3; §4 cost-benefit projection traces to
  investigation §4.2; §5 forward routing traces to investigation §6.3 +
  §8.4. SVR tuples for each load-bearing platform-behavior claim are at
  investigation §9.1.

### §7.2 Supplement (re-grounding source)

- `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` §8.4
  (`:598-623` — original hypothesis surface). The supplement is amended in
  this same commit at §9 to record the re-grounding without retroactive edit.

### §7.3 Charter (governing authority)

- `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md`:
  - §4 BLOCKING task definition for SRE-002a (`:81-112`).
  - §4.4 escalation criteria (`:99-107`) — criterion 1 (cross-repo
    modification) and criterion 2 (multi-satellite coupling) both fire;
    criterion 3 (production-code defect) does not fire.
  - §7.1 cross-repo escalation protocol (gates Path B).
  - §8.4 authority boundaries (`:177-192`) — autom8y-asana-local scope-fence.
  - §11.2 cost discipline (≤20 probe-CI runs total for Sprint-2; ≤9 for
    Sprint-2A).

### §7.4 BASELINE (wallclock anchor)

- `.ledge/reviews/BASELINE-test-perf-2026-04-29.md` §4 (`:312-328`) — 5-run
  main p50 slowest-shard = 447s. Anchor used in §4 cost-benefit projection
  scenario A baseline.

### §7.5 Cross-repo source-of-truth

- `autom8y-workflows@c88caabd:.github/workflows/satellite-ci-reusable.yml`:
  - `:393` — test-job `runs-on: ubuntu-latest` (the directive that Path B
    would modify).
  - `:527-528` — `-n auto` resolution under `test_parallel: true`
    (investigation §3.2).
  - 8 satellite consumers of this workflow (investigation §2.4).

---

END ADR-008. Adjudication: NO-LEVER (autom8y-asana-local). Probe-runs
consumed: 0/9 budget. Path B (cross-repo upgrade probe) RESERVED. Forward
routing: Sprint-2B inherits 002b/c empirical scope. Supplement §9 amendment
authored in same commit re-grounds §8.4 without retroactive edit.
