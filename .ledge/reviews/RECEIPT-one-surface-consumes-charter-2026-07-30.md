---
type: review
status: final
artifact_class: consumption-receipt
initiative: decision-charter-inheritance
sprint: S3 (WS-C fleet-propagation)
discharges: "LEG 3 — at least one surface beyond this repo consumes the record"
date: 2026-07-30
self_grade: MODERATE  # self-ref cap; rite-disjoint critic CONCUR-WITH-FLAGS rendered; eunomia re-derives at S5
consumed_by:
  repo: autom8y-data
  artifact: .ledge/decisions/DECISION-adopt-fleet-decision-space-charter-2026-07-30.md
  merged: "autom8y-data@263ec81f (#365, squash of 4e0ad3d5)"
consumes:
  record: .ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md
  landed: "autom8y-asana@c5ab0205 (#290)"
---

# RECEIPT — one surface beyond this repo consumes the charter-of-record

**Claim (LEG 3 of the realization predicate):** at least one surface beyond autom8y-asana consumes the charter-of-record. **Landed:** autom8y-data adopted the record by reference on its tracked governing surface, merged to its main as `263ec81f` (#365).

## 1. What was consumed, and how

`autom8y-data/.ledge/decisions/DECISION-adopt-fleet-decision-space-charter-2026-07-30.md` (46L) — an adoption-of-record in autom8y-data's native governing idiom: adoption + binding + composition (strictest-applicable-gate-wins vs its local rulings) + provenance/resolution. **Pointer-only: zero charter bytes reproduced** (single-source-of-truth preserved; the asana record remains the sole holder of the operative core). Provenance pin `autom8y-asana@c5ab0205` is the declared isolated-clone backstop (KNOWN-GAP, stated not hidden).

## 2. Post-merge consumption probe (mechanical, canonical root, 2026-07-30)

```
$ git ls-tree origin/main --name-only .ledge/decisions/ | grep adopt-fleet-decision-space
.ledge/decisions/DECISION-adopt-fleet-decision-space-charter-2026-07-30.md

$ git show origin/main:.ledge/decisions/DECISION-adopt-fleet-...-2026-07-30.md | grep -n 'record: autom8y-asana'
9:  record: autom8y-asana/.ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md

$ FLEET_ROOT="$(cd "$(git rev-parse --show-toplevel)/.." && pwd)"   # /Users/tomtenuta/Code/a8/a8/repos
$ test -f "$FLEET_ROOT/autom8y-asana/.ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md"  → exit 0
$ grep -c 'BEGIN VERBATIM CORE' "$ASANA_RECORD"  → 1
```

Locate (tracked at merged main) ✓ · Quote (pointer well-formed) ✓ · Resolve (record exists, exactly one fenced core) ✓. Pre-merge probes (branch state) were identical — recorded in the S3 build return.

## 3. Independent verification (R31)

structure-evaluator (arch, rite-disjoint, own-hands): **CONCUR-WITH-FLAGS** — X1 genuine-consume (binding language, native idiom vs autom8y-data's own DECISION/RULINGS artifacts, 4 real local rulings cited and verified) · X2 one-surface-only (exactly 1 file; no kit/knossos/sibling touch — S10 not front-run) · X3 single-SoT (**0 shared 5-grams** vs the record's verbatim core, two tokenizations) · X4 mechanical-probe-only (no LEG-1 front-run) · X5 clean single-commit revert · X6 composition integrity (fleet-vs-local gate distinction held) · frontmatter fidelity (pin verified ancestor-of-main; fence-marker byte-exact, 67==67) · KNOWN-GAP honesty.

**FLAG-1 (remedied pre-merge):** the frontmatter had pre-inscribed the critic's CONCUR before it was rendered — replaced with the critic's exact wording ("pending structure-evaluator attestation per R31 (rendered rite-disjoint, never pre-inscribed)"), amend `0c0e6958 → 4e0ad3d5`; the delta IS the critic's prescription (PT-03 ruling c: no re-review required). **Carry-forward:** this wording MUST propagate into the future S10-kit template so the pre-inscription idiom does not replicate fleet-wide.

## 4. Gate + rulings

PT-03 throughline gate: **OPEN** (Q1 consumption proven at branch by the rite-disjoint critic — receipt is post-merge mechanical completion, not a gate precondition; Q2 S10-independent path clean; Q3 OS-5 emission ruled at merge). DEFER-1 **not invoked**. The S10 kit propagation, when it ships, **absorbs** this direct placement (same pointer form the kit will inscribe; mechanism upgrade, not content change) — the adoption record remains the durable of-record attestation.

## 5. OS-5 new-standard heads-up (charter §5 watch-trigger — EMITTED at this merge)

> The pointer-reference inheritance standard (FORK-1, reversible) has now propagated to its first sibling surface: the autom8y-data adoption record (`263ec81f`, #365). Reversible via un-place (single-commit revert). Informational — no action required unless the pattern looks wrong.

## 6. For the S5 attester (re-derive, inherit nothing)

1. Re-run the 0-shared-5-gram check with your own tokenization. 2. Re-run the §4 resolver from the canonical autom8y-data checkout (NOT a `.knossos/worktrees/` path — the worktree trap is real). 3. Re-derive the fleet-vs-local gate distinction (the R-A un-refusal is a local gate, orthogonal to the fleet floor). 4. Render your own verdict — never inherit a pre-inscribed CONCUR. 5. Cheap re-confirms: pin ancestor-of-main; fence count == 1; single-file delta at `263ec81f`.
