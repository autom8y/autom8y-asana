---
type: decision
artifact_type: adr
adr_number: 009
title: "SRE-002b xdist Worker-Count Tuning — NO-LOCAL-OVERRIDE (autom8y-asana-local)"
status: accepted
date: 2026-04-30
rite: sre
session_id: session-20260430-platform-engineer-002b
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2
sibling_adr: ADR-008-runner-sizing-no-lever-2026-04-30.md
investigation: .sos/wip/sre/INVESTIGATION-runner-sizing-2026-04-30.md (§3 baseline finding inherited)
evidence_grade: STRONG
provenance: zero-cost empirical falsification via direct file inspection (0 of 6 probe-CI runs consumed)
authored_by: platform-engineer
adjudication: NO-LOCAL-OVERRIDE (autom8y-asana-local)
escalation_status: §7.1-cross-repo-escalation-required
path_b_status: RESERVED (reusable-workflow modification; requires explicit user authorization per charter §7.1 + §8.4)
---

# ADR-009 — SRE-002b xdist Worker-Count Tuning — NO-LOCAL-OVERRIDE (autom8y-asana-local)

## §1 Context

Sprint-2 (`PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md` §5.1) authorized
sub-route SRE-002b — **xdist worker-count tuning probe** — as a follow-on to
SRE-002a (closed at ADR-008 NO-LEVER). The hypothesis carried forward from
Sprint-2A's investigation (`INVESTIGATION-runner-sizing-2026-04-30.md` §3 +
post-merge supplement §3-§5):

> On a 4-vCPU runner where `-n auto` resolves to 4 workers (1:1 ratio),
> `-n auto = 4 workers` may NOT be the optimum. Each pytest-xdist worker
> pays independent fixture setup cost (root conftest fixtures × N workers),
> independent `_bootstrap_session` autouse Pydantic forward-ref resolution
> × N, and independent test collection (13,605 tests collected per worker
> for the subset they run). If `-n 2` (intentionally undersized to half of
> vCPUs) reduces these collective overheads enough, total wallclock may
> drop despite halving parallelism.

The Sprint-2 charter §11.2 authorized up to 6 probe-CI runs (3 probe `-n 2`
samples + ≤3 baseline `-n auto` samples) to adjudicate among:

1. **WIN** — `-n 2` ≥10% faster slowest-shard p50 → recommend commit
2. **NO-WIN** — `-n 2` within ±5% → ADR documenting test, no commit
3. **LOSE** — `-n 2` >5% slower → ADR rejecting hypothesis, no commit

This ADR records a fourth adjudication that was not in the original protocol's
outcome enumeration: **NO-LOCAL-OVERRIDE** — the probe could not be run within
the autom8y-asana-local altitude because no local override surface exists for
the xdist `-n N` parameter.

## §2 Decision

**NO-LOCAL-OVERRIDE (autom8y-asana-local)** per direct file inspection at
Step 2 of the SRE-002b probe protocol. The probe protocol's §3 HALT condition
fired and prevented Step 3 (probe branch creation) from being initiated.

**Probe runs consumed**: 0 of 6 (early termination per protocol §3 HALT
condition; direct file inspection structurally established the absence of
the override surface before any probe was spent).

**Evidence grade**: STRONG (zero-cost empirical falsification via direct
file inspection at three independent file:line anchors below).

## §3 Investigation Method

The probe protocol's Step 1-2 read-only inspection of three sources:

1. The local satellite caller workflow at
   `.github/workflows/test.yml` (the "what does autom8y-asana pass to the
   reusable workflow?" surface).
2. The local pytest configuration at `pyproject.toml`
   `[tool.pytest.ini_options]` (the "is there a local pytest config that
   overrides `-n N` from CLI?" surface).
3. The reusable workflow at
   `/Users/tomtenuta/Code/a8/repos/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml`
   (the "where is `-n auto` actually emitted, and is the worker count
   parameterized as a workflow input?" surface).

All three inspections produced verbatim file:line evidence corroborating the
NO-LOCAL-OVERRIDE finding. No CI runs were triggered. No probe branch was
created. No commits were made.

## §4 Empirical Anchors (SVR file-read)

### §4.1 Anchor 1 — Local caller workflow (autom8y-asana satellite)

```yaml
verification_anchor:
  source: ".github/workflows/test.yml"
  line_range: "L54-L55"
  marker_token: "test_parallel: true\n      test_splits: 4"
  claim: "the satellite caller workflow's full xdist-relevant input surface to the reusable workflow consists of two fields: a boolean toggle for parallel-on/off (test_parallel) and a shard-count integer (test_splits); no -n N input is passed because no -n N input parameter exists in the consumed reusable workflow's input schema"
```

**Surrounding context** (`.github/workflows/test.yml:39-72`): the entire `ci`
job is a thin caller that delegates to
`autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd`
with 16 input fields (mypy_targets, coverage_package, coverage_threshold,
test_timeout, test_parallel, test_splits, test_markers_exclude,
run_integration, test_env, spectral_enabled, openapi_spec_path,
spec_check_enabled, spec_check_validate_script, spec_check_extras,
spec_check_env, semantic_score_enabled). None of these 16 fields parameterize
xdist worker count.

### §4.2 Anchor 2 — Reusable workflow input surface (autom8y-workflows)

```yaml
verification_anchor:
  source: "../autom8y-workflows/.github/workflows/satellite-ci-reusable.yml"
  line_range: "L79-L90"
  marker_token: "test_parallel:\n        description: 'Enable pytest-xdist parallel execution (-n auto)'"
  claim: "the reusable workflow's input description verbatim reveals the design constraint: 'Enable pytest-xdist parallel execution (-n auto)' — the parenthesized 'auto' is the only mode the boolean input toggles; no companion input (test_workers, test_n, test_xdist_workers) parameterizes the integer worker count; the closest siblings test_dist_strategy (L83-86) controls --dist scheduler not -n N, and test_splits (L87-90) controls shard count not per-shard worker count"
```

**Full xdist input surface enumeration** (verified by grep across the
reusable workflow's `inputs:` block, L39-L256):

| Input | Type | Default | Controls `-n N`? |
|-------|------|---------|------------------|
| `test_parallel` | boolean | false | NO — toggle only (`-n auto` ON/OFF) |
| `test_dist_strategy` | string | '' | NO — `--dist=` scheduler (e.g. loadfile/loadscope) |
| `test_splits` | number | 1 | NO — number of shard runners |
| `test_durations_path` | string | '.test_durations' | NO — bin-packing input |

There is no `test_workers`, `test_n`, `test_xdist_workers`, or any
synonym. The reusable workflow's design intent is binary parallelism
(on/off), with worker count delegated to xdist's `auto` resolution.

### §4.3 Anchor 3 — Reusable workflow worker-count emission point

```yaml
verification_anchor:
  source: "../autom8y-workflows/.github/workflows/satellite-ci-reusable.yml"
  line_range: "L527-L529"
  marker_token: "if [ \"${{ inputs.test_parallel }}\" = \"true\" ]; then\n            ARGS=\"$ARGS -n auto\""
  claim: "the reusable workflow's pytest-args builder unconditionally appends the literal string '-n auto' (no parameterization on worker count) whenever the boolean test_parallel input is true; modifying the worker count from 'auto' to a fixed integer requires editing this string literal at line 528 of the reusable workflow source — there is no caller-side path"
```

The string `-n auto` is hardcoded at line 528. Per Sprint-2A
investigation §3 + post-merge supplement §3-§5, on the 4-vCPU
`ubuntu-latest` runner pytest-xdist resolves `auto` to `nproc()` = 4
workers (1:1 worker-to-vCPU ratio). To probe `-n 2`, this literal must
become `-n 2` (or a parameterized `-n ${{ inputs.test_workers }}` with a
new input definition added to the reusable workflow's `inputs:` block).

### §4.4 Anchor 4 — Local pytest configuration (no override path)

```yaml
verification_anchor:
  source: "pyproject.toml"
  line_range: "L113"
  marker_token: "addopts = \"--dist=load\""
  claim: "the project's pytest addopts set only the --dist scheduler (load), with no -n parameter; per pytest-xdist precedence, CLI flags override addopts but addopts can only ADD flags not REMOVE them, so even if a local pytest.ini set -n 2 it would conflict with the reusable workflow's -n auto CLI emission rather than override it; in practice, autom8y-asana's pyproject contains no -n directive at all, so the CLI flag is the sole authority"
```

Note (incidental finding, not load-bearing on the NO-LOCAL-OVERRIDE
adjudication): the comment at L103-L112 of `pyproject.toml` claims
`--dist=loadfile` is the chosen scheduler, but `addopts = "--dist=load"` at
L113 is what's actually configured. The L103 rationale (cross-item state
corruption from `--dist=load` round-robin) describes the historical reason
for choosing `loadfile`; the actual addopts string says `load`. This
deserves a separate ADR or correction sweep but is OUT-OF-SCOPE for
SRE-002b.

## §5 Why This Is OUT-OF-SCOPE for autom8y-asana-local

Sprint-2 charter §8.4 (`PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md`)
declares **cross-repo modification is OUT-OF-SCOPE** under §7.1 escalation
gate. The reusable workflow at
`autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml`
is a separate repository (`autom8y/autom8y-workflows`, not
`autom8y/autom8y-asana`). Modifying line 528 — even by a one-character
edit (`auto` → `2`) — constitutes:

1. A change to a different git repository's main-line workflow
2. A potential blast-radius event affecting all satellites that consume the
   reusable workflow at any pinned SHA forward of the change
3. A coordination requirement with the autom8y-workflows release process
   (PR review, version pinning, downstream satellite SHA bumps)

Per charter §7.1, cross-repo work requires **explicit user authorization** to
proceed. This ADR is the §7.1 escalation surface — the user reads this ADR
and decides whether to authorize a cross-repo Sprint-2C (or to defer the
worker-count tuning question entirely).

## §6 Path-B (RESERVED) — What an authorized cross-repo probe would look like

If the user authorizes §7.1 escalation, the minimum viable scope of a
cross-repo SRE-002b-Path-B probe is:

1. **autom8y-workflows PR**: parameterize line 528 from hardcoded `-n auto`
   to `-n ${{ inputs.test_workers }}` with a new
   `test_workers: { type: number, default: 0 }` input where
   `default: 0` triggers the legacy `auto` behavior to preserve backward
   compatibility for all other satellites.
2. **autom8y-asana caller PR**: a probe branch that bumps the SHA pin to the
   autom8y-workflows PR's head and adds `test_workers: 2` to the caller's
   `with:` block.
3. **Probe protocol** (per the original §3-§7 of the SRE-002b dispatch):
   3 probe runs at `-n 2` + 3 baseline runs at `-n auto` (or 0, the new
   default-auto sentinel) → adjudicate WIN/NO-WIN/LOSE per slowest-shard
   p50 comparison.
4. **Cleanup**: if NO-WIN/LOSE, revert both PRs (the caller revert is
   trivial; the autom8y-workflows revert can be either a full revert of
   the new input or — a softer stance — leave the input in place for
   future tuning while reverting only the autom8y-asana caller's
   `test_workers: 2` declaration).

Estimated effort: 4-6 hours of cross-repo coordination + 6 probe-CI runs
(within charter §11.2 budget, which currently has 11 unspent probe-runs:
9 preserved from 002a non-spend + 6 reserved for 002b minus 0 spent).

## §7 Decision Cross-Reference

This ADR is the **sibling** of ADR-008-runner-sizing-no-lever-2026-04-30 at
the same cross-repo altitude:

| Dimension | ADR-008 (SRE-002a) | ADR-009 (SRE-002b) |
|-----------|---------------------|---------------------|
| Sub-route | runner-sizing (vCPU count) | xdist worker-count tuning |
| Local override surface? | NO (runner image is GitHub-Actions-managed) | NO (worker count is hardcoded in reusable workflow) |
| Adjudication | NO-LEVER (autom8y-asana-local) | NO-LOCAL-OVERRIDE (autom8y-asana-local) |
| Cross-repo Path-B reserved? | YES (§7.1 reservation) | YES (§7.1 reservation) |
| Probe-CI runs consumed | 0 of 9 | 0 of 6 |
| Evidence basis | direct file/log inspection | direct file inspection |
| Status | accepted | accepted |

The two ADRs together establish a **structural pattern**: when a
satellite-altitude probe targets a parameter owned by the reusable workflow,
the satellite-altitude probe surface is empty by design — these levers live
upstream. The autom8y-asana-local altitude is the wrong altitude for either
question.

## §8 Receipt Grammar Summary

Every claim in this ADR cites either (a) a file:line anchor with verbatim
marker_token (per `structural-verification-receipt` §2.2 file-read method),
(b) a sibling ADR or charter section reference, or (c) a probe-protocol
clause from the originating dispatch. No claim rests on memory, summary, or
synthesis.

## §9 Open Questions Surfaced to User

1. **Authorize §7.1 cross-repo escalation for SRE-002b-Path-B?** The
   per-item ADR discipline (charter §3.2) requires this question be
   surfaced explicitly rather than absorbed into a follow-on task without
   user knowledge. Trade-off: 4-6 hours of cross-repo coordination + 6
   probe-CI runs vs. unknown-magnitude potential wallclock improvement
   (the hypothesis is plausible but unmeasured).

2. **Does Sprint-2 close at ADR-009 acceptance, or proceed to SRE-002c
   (shard-balance refresh)?** Charter §5.1 lists SRE-002b and SRE-002c as
   independent residuals; SRE-002c does not depend on SRE-002b's outcome.
   SRE-002c can be dispatched immediately at the platform-engineer's next
   turn if the user accepts NO-LOCAL-OVERRIDE for 002b.

3. **Should the incidental finding in §4.4 (loadfile-vs-load addopts
   discrepancy) become a separate sub-route?** It is genuine scar-tissue —
   the comment block describes a defensive choice that the addopts string
   doesn't actually implement. Sprint-2 charter does not currently list
   this as a sub-route, so the default disposition is to file a
   complaint via `/reflect` and let the next sprint's sifting decide.

---

**END ADR-009**. Sprint-2 SRE-002b adjudication: **NO-LOCAL-OVERRIDE**.
Path-B reserved per charter §7.1. 0 of 6 probe-CI runs consumed. Probe
budget preserved for downstream tasks.
