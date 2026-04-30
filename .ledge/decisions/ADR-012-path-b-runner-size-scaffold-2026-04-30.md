---
type: decision
artifact_type: adr
adr_number: 012
title: "SRE-002 Path (B) Cross-Repo Scaffold — runner_size parameter (test_workers DEFERRED)"
status: accepted
date: 2026-04-30
rite: sre
session_id: session-20260430-platform-engineer-sub-sprint-A2
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3
parent_adrs:
  - ADR-008-runner-sizing-no-lever-2026-04-30.md
  - ADR-009-xdist-worker-count-no-local-override-2026-04-30.md
predecessor_audit: .ledge/reviews/AUDIT-followon-ci-2026-04-29-delta-3.md
predecessor_dispatch: SUB-SPRINT-A1 (HALTED on test_workers semantic-overlap drift-finding)
cross_repo_pr: autom8y/autom8y-workflows#<pending — populated by Step 6>
cross_repo_branch: sre/scaffold-runner-size-2026-04-30
cross_repo_base_sha: 72eaee84786656bfff618831a05b0a1d1689c1af
evidence_grade: MODERATE
provenance: scaffold-only cross-repo modification; behavior-change deferred to org-runner-tier enablement gate
authored_by: platform-engineer
authority_grant: user-2026-04-30T18:31Z (full cross-repo file tree access)
path_b_status: SCAFFOLD-LANDED-DEFAULT-PRESERVED
test_workers_status: DEFERRED (semantic overlap with existing test_parallel; no tuning warrant)
realization_gate: org-runner-tier enablement (gh api shows total_count: 0 at 2026-04-30T18:31Z)
realization_deadline: 2026-05-14
telos_anchor: .know/telos/sprint3-path-b-2026-04-30.md
---

# ADR-012 — SRE-002 Path (B) Cross-Repo Scaffold (runner_size only)

## §1 Context

Sprint-2 closed two parent ADRs at NO-LEVER / NO-LOCAL-OVERRIDE dispositions
with the cross-repo escalation lane explicitly RESERVED pending user
authorization:

- **ADR-008** (SRE-002a runner-sizing): adjudicated NO-LEVER at autom8y-asana
  altitude — runner tier is fixed at `ubuntu-latest` inside the consumed
  reusable workflow `autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml`,
  so satellite-local override was structurally unavailable. Path (B)
  cross-repo upgrade RESERVED per charter §7.1.
- **ADR-009** (SRE-002b xdist-worker-count): adjudicated NO-LOCAL-OVERRIDE at
  autom8y-asana altitude — `pytest -n auto` is governed inside the reusable
  workflow's test-job step, again not satellite-callable. Path (B) RESERVED
  per charter §7.1 + §8.4.

Sprint-3 charter (`PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3.md` §1.1)
LIFTED the §7.1 cross-repo gate following user authority grant
2026-04-30T18:31Z (full cross-repo file tree access).

Sub-Sprint-A1 dispatched the lifted scope as a paired-input scaffold:
**add `runner_size` AND `test_workers` parameters** to
`satellite-ci-reusable.yml`. A1 audit (this dispatch's predecessor)
HALTED on a drift-finding: the original A1 audit's L527-528 citation of
"missing parallel-execution parameterization" was structurally wrong. Direct
cross-repo file-read at HEAD `72eaee84` revealed the workflow ALREADY carries:

- `test_parallel` (boolean, L79-82) → governs `pytest -n auto` toggle
- `test_dist_strategy` (string, L83-86) → governs `pytest --dist=` strategy
- `test_splits` (number, L87-90) → governs pytest-split sharding

Adding `test_workers` would have created **4-way semantic overlap** with
existing `test_parallel`: callers would have two redundant levers
(boolean-on-off vs integer-count) governing the same xdist surface, with no
canonical precedence rule. The A1 HALT was a correct refusal of scope.

The drift-audit follow-on
(`.ledge/reviews/AUDIT-followon-ci-2026-04-29-delta-3.md`) re-adjudicated the
scope: **runner_size only**; defer test_workers indefinitely.

## §2 Decision

**Path (B) re-adjudicated as scaffold-only single-input cross-repo PR.**

Add ONLY the `runner_size` parameter to
`autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml`:

### §2.1 Schema addition

Inserted at L207-211 (immediately after `test_timeout` block, before
`# --- Optional: Contract/governance test support ---`):

```yaml
# --- Optional: Runner tier (org-runner-tier-enablement-gated) ---
runner_size:
  description: 'Runner tier: "standard" (ubuntu-latest, 2-vCPU) or "large" (ubuntu-latest-large, 8-vCPU; requires org-runner-tier enablement)'
  type: string
  default: 'standard'
  required: false
```

### §2.2 L393 → L400 modification

The test-job `runs-on:` declaration changes from bare literal to ternary
expression keyed off the new input:

```yaml
# Before (L393):
    runs-on: ubuntu-latest

# After (L400, post-input-block-shift):
    runs-on: ${{ inputs.runner_size == 'large' && 'ubuntu-latest-large' || 'ubuntu-latest' }}
```

### §2.3 Sentinel-default back-compat

`runner_size: 'standard'` is the default. All existing satellite callers
that do NOT pass `runner_size` resolve the ternary to `ubuntu-latest` —
identical to the prior bare literal. **Zero behavior change for non-opt-in
callers.**

### §2.4 test_workers dropped from scope

`test_workers` is DEFERRED (not REJECTED). Future engagement may revisit if:
- A specific tuning warrant emerges (deterministic worker count under
  `large` tier where `-n auto` autosizing produces suboptimal allocation);
- AND a canonical precedence rule between `test_parallel` and a new
  `test_workers` parameter can be authored without ambiguity.

Until then, no parameter addition.

## §3 Authority Chain

The disposition rests on the following authority chain (each link
file:line-anchored):

1. **User authority grant 2026-04-30T18:31Z** — user explicitly granted
   full cross-repo file tree access for autom8y org repos this session.
2. **Sprint-3 charter §1.1 lift** —
   `PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3.md` §1.1 lifts the §7.1
   cross-repo gate inherited from Sprint-2 charter.
3. **ADR-008 framing** —
   `.ledge/decisions/ADR-008-runner-sizing-no-lever-2026-04-30.md` §1 +
   `path_b_status: RESERVED` frontmatter establishes runner-sizing as the
   canonical Path (B) handle.
4. **ADR-009 framing** —
   `.ledge/decisions/ADR-009-xdist-worker-count-no-local-override-2026-04-30.md`
   §1 + `path_b_status: RESERVED` frontmatter establishes xdist worker-count
   as the SECOND Path (B) handle (now DEFERRED per re-adjudication).
5. **A1 audit + drift-finding HALT** —
   `.ledge/reviews/AUDIT-followon-ci-2026-04-29-delta-3.md` records the
   semantic-overlap drift-finding that scope-fenced test_workers.
6. **THIS ADR** — formal Path (B) re-adjudication as scaffold-only
   single-input cross-repo PR.

## §4 Alternatives Rejected

### §4.1 Alternative (A): HALT entirely on the A1 drift-finding

**Rejection rationale**: A1 HALT correctly refused the BAD scope (paired
inputs with semantic overlap), not the WHOLE scope. The runner_size handle
is structurally orthogonal to existing parameterization (no overlap with
`test_parallel`/`test_dist_strategy`/`test_splits`); it adds a new axis
(runner-tier) rather than re-parameterizing an existing one. HALTing the
runner_size scaffold alongside test_workers would have:

- Lost preparation value (runner-tier opt-in lane stays unbuilt; future
  realization requires fresh dispatch);
- Forfeited the user-authority-grant window (cross-repo write authority
  may not always be available);
- Conflated drift-correction with scope-rejection.

### §4.2 Alternative (C): Add test_workers WITH a precedence rule

**Rejection rationale**: Authoring a precedence rule
("`test_workers` overrides `test_parallel` when both are set") would:

- Add scope creep beyond the empirical warrant (no evidence that current
  `-n auto` autosizing is suboptimal at standard tier);
- Create three-way conditional logic in the test-job step's `pytest` invocation
  (boolean toggle + dist-strategy + worker-count), increasing surface area
  for future drift between caller intent and resolved invocation;
- Risk the same drift-class A1 HALTed on (semantic ambiguity surfacing
  later as a real defect rather than a scoping artifact);
- Violate the "smallest revertible cross-repo unit" principle (PR diff
  expands from +8/-1 to ~+25/-1 with conditional logic edges).

The absence of empirical warrant is load-bearing: ADR-009 closed at
NO-LOCAL-OVERRIDE because the autom8y-asana satellite's measured CI
runtime under current `-n auto` was within target SLO, not because of a
known autosizing pathology. Adding a tuning lever without a tuning
warrant is YAGNI at platform-altitude.

### §4.3 Alternative (D): Add runner_size in autom8y-asana-local fork

**Rejection rationale**: Autom8y-asana consumes `satellite-ci-reusable.yml`
via `uses:` reference, not via vendored copy. There is no satellite-local
fork to modify. This alternative is structurally unavailable per ADR-008
§1 (the NO-LEVER finding rests precisely on this absence).

## §5 Risks

### §5.1 Cross-fleet PR review velocity

The PR sits at `autom8y/autom8y-workflows`, where reviewers may not have
the full Sprint-3 context. Mitigation: PR body cites this ADR + charter +
parent ADRs explicitly; commit message carries authority chain inline.
Risk realization: review-stalled PR → blocked realization gate →
indefinite scaffold dwell.

### §5.2 Org enablement gating

`gh api /orgs/autom8y/actions/hosted-runners` returned `total_count: 0` at
2026-04-30T18:31Z. The autom8y org has zero hosted larger-runners enabled.
This PR is **scaffold-only** — landing it does NOT enable larger-runner
usage. Realization requires:

1. Org admin authorizing paid larger-runner usage (out of platform-engineer
   exousia; escalates to Incident Commander or org owner);
2. A satellite (likely autom8y-asana itself) opting in via
   `runner_size: 'large'` post-enablement;
3. Wallclock-delta verification proving the upgrade actually delivers
   measurable runtime improvement (telos-realization gate per
   `.know/telos/sprint3-path-b-2026-04-30.md`).

Risk realization: PR lands; org enablement never materializes; scaffold
dwells unused indefinitely. **Acceptable risk** because the scaffold has
zero behavior cost (sentinel default preserves status quo) and the
preparation value (lane built) is preserved across the dwell.

### §5.3 Future test_workers re-litigation

DEFERRED is not REJECTED. A future engagement may surface a tuning warrant
and re-open the test_workers scope. Mitigation: this ADR records the
A1 drift-finding (semantic overlap rationale) so future re-litigation
inherits the prior structural analysis rather than re-discovering it.

### §5.4 Configuration drift between scaffold and consumers

Scaffold lands in autom8y-workflows; consumers (autom8y-asana and other
satellites) do not yet pass `runner_size`. If the input default ever
silently changes upstream (e.g., a future PR flips `default: 'standard'`
to `default: 'large'`), all consumers silently shift behavior. Mitigation:
this ADR's existence establishes the default as load-bearing semantic;
any future change to the default requires its own ADR.

## §6 Atomic-Revertibility

The cross-repo PR is a **single revertible unit**:

- Branch: `sre/scaffold-runner-size-2026-04-30` (cut from main at
  `72eaee84`)
- Diff: +8/-1 across one file (`.github/workflows/satellite-ci-reusable.yml`)
- Two atomic changes in one commit:
  - Input addition (5 lines, plus 2-line section comment, plus 1 blank)
  - L393 ternary (1-line replacement)

If realization fails or behavior regresses, `git revert <merge-sha>`
restores prior state without coupling concerns. No state migrations, no
schema changes outside the workflow inputs map, no consumer-side changes
required.

## §7 Verification

### §7.1 yaml.safe_load

`python3 -c "import yaml; yaml.safe_load(open('.github/workflows/satellite-ci-reusable.yml'))"`
returns exit 0 and produces a parsed document where:

- `inputs.runner_size` is present with `default='standard'`, `type='string'`,
  `required=False`
- `inputs.test_workers` is **absent** (Path (B) re-adjudication scope-fence
  enforced)
- `inputs.test_parallel`, `inputs.test_dist_strategy`, `inputs.test_splits`,
  `inputs.test_timeout` are all present (no inadvertent deletion)

### §7.2 L393 → L400 ternary

Direct file-read at the new `runs-on:` line confirms ternary literal:

```yaml
runs-on: ${{ inputs.runner_size == 'large' && 'ubuntu-latest-large' || 'ubuntu-latest' }}
```

### §7.3 Wallclock-delta verification (DEFERRED)

Wallclock-delta verification (does `runner_size: 'large'` actually deliver
measurable runtime improvement?) is **DEFERRED to post-org-enablement**. The
realization gate is tracked in `.know/telos/sprint3-path-b-2026-04-30.md`
with deadline 2026-05-14. If the org enablement does not materialize by
that deadline, the telos-realization watch fires per
`telos-integrity-ref` Gate-C protocol.

## §8 Telos Declaration Reference

Per `telos-integrity-ref` §2 schema, this initiative's telos declaration
lives at `.know/telos/sprint3-path-b-2026-04-30.md` with:

- `shipped_definition`: this ADR + cross-repo PR landing
- `verified_realized_definition.verification_method`: cross-stream-corroboration
  (org-enablement event + autom8y-asana opt-in CI run with measured wallclock
  delta vs baseline)
- `verified_realized_definition.verification_deadline`: 2026-05-14
- `verified_realized_definition.rite_disjoint_attester`: incident-commander
  (rite-disjoint from platform-engineer per SRE rite catalog §Cross-Rite Integration)

## §9 Receipt Grammar

Per `structural-verification-receipt` discipline, all platform-behavior
claims in this ADR carry verification:

- §1 cross-repo workflow line-citations (L79-82, L83-86, L87-90, L393): file-read
  receipt at HEAD `72eaee84`, captured at dispatch time.
- §2.1 / §2.2 diff: bash-probe receipt via `git diff --stat` showing +8/-1
  one-file change.
- §5.2 org enablement state: api-probe receipt via
  `gh api /orgs/autom8y/actions/hosted-runners` returning `total_count: 0`
  at 2026-04-30T18:31Z (cited in PR body).
- §6 atomic-revertibility: structural property of single-commit single-file
  diff; verifiable by `git log --stat <merge-sha>` post-merge.

## §10 Cross-References

- **Parent ADRs**: ADR-008 (NO-LEVER framing for runner-sizing),
  ADR-009 (NO-LOCAL-OVERRIDE framing for xdist; sibling Path (B) handle now
  DEFERRED).
- **Predecessor audit**:
  `.ledge/reviews/AUDIT-followon-ci-2026-04-29-delta-3.md` (drift-finding
  + Path (B) re-adjudication source).
- **Charter**: `PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3.md` §1.1
  (cross-repo gate lift).
- **Telos**: `.know/telos/sprint3-path-b-2026-04-30.md` (realization-gate
  watch).
- **Cross-repo PR**: `autom8y/autom8y-workflows#<pending>` (populated post Step 6).

## §11 Status Transition

- **Inscribed**: 2026-04-30 (this dispatch, Sub-Sprint-A2 RETRY)
- **Realized-pending**: cross-repo PR merge + org enablement + opt-in
  satellite verification
- **Realized-deadline**: 2026-05-14
- **Telos-watch fires if**: deadline lapses without org enablement OR PR
  unmerged at deadline (escalation per telos-integrity-ref Gate-C).

---

END ADR-012. Path (B) cross-repo scaffold landed as runner_size-only
single-input PR. test_workers DEFERRED indefinitely (no warrant; semantic
overlap with existing test_parallel). Sub-Sprint-C close-gate inherits
this disposition.
