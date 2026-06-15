---
type: decision
subtype: ordering-pin
status: accepted
title: "ORDERING PIN — #114 merge ≺ FM-5 design-lock ≺ FM-5 deploy (post-soak); amends-by-reference CLEAR bundle §B.5"
date: 2026-06-11
authored_by: hygiene station K3 (architect-enforcer) — Freeze-Window Capitalization
code_truth_anchor: origin/main fa265ce1bde8be1d003f39501877d17fe600b0c0
amends_by_reference: .ledge/decisions/CLEAR-READINESS-BUNDLE-telos-soak-2026-06-18-2026-06-11.md §B.5  # cited, NOT edited — this pin is its own record
inputs:
  - .ledge/decisions/OPERATOR-RULING-fm5-scope-and-sequencing-2026-06-11.md   # RULING 2: FM-5 EXTENDS #114; derivation/build GATES on #114 landing
  - .ledge/specs/SPEC-fm5-consumer-column-declaration-shape-2026-06-11.md     # §Layer-1 Derivation: "the FieldContract SSOT (field_contract_maps.py, #114's home)"
  - .sos/wip/glints/GLINT-path-forward-post-keystone-2026-06-11.md            # L1-3: "#114 ordering is load-bearing... this ordering is implicit nowhere"
  - .know/telos/fm5-column-fidelity.md                                        # the Gate-A declaration this pin gates
---

# ORDERING PIN — #114 merge ≺ FM-5 design-lock ≺ FM-5 deploy (post-soak)

## The pin (binding sequence)

```
#114 merge  ≺  FM-5 design-lock  ≺  FM-5 deploy
(post-soak     (operator-held,       (post-soak-clear per
 bundle PR)     RULING 1 re-confirm)   RULING 3 — a deploy resets the clock)
```

## Why it is load-bearing (receipts, all re-fired this pass at fa265ce1)

1. **The FM-5 derivation engine's home DOES NOT EXIST on main.** Probe (this station,
   this pass):
   ```
   $ git show origin/main:src/autom8_asana/dataframes/contracts/
   fatal: path 'src/autom8_asana/dataframes/contracts/' does not exist in 'origin/main'
   (exit 128)
   ```
2. **#114 carries that home.** `gh pr view 114 --json files` (re-fired this pass) — PR #114
   (`fpc/phase1-dtype-parity`, OPEN, "FPC Phase-1: dtype-SSOT parity check + D3 reconcile
   (asset_edit.score)") carries exactly:
   - `src/autom8_asana/dataframes/contracts/__init__.py`
   - `src/autom8_asana/dataframes/contracts/field_contract_maps.py`  ← the FieldContract SSOT
   - `src/autom8_asana/dataframes/schemas/asset_edit.py`
   - `tests/unit/dataframes/test_field_contract_parity.py`
3. **FM-5's derivation is specified INTO that file.** SPEC-fm5 §Layer-1 Derivation: "the
   FieldContract SSOT (`field_contract_maps.py`, #114's home) ingests the vendored manifest
   → derives the per-query-shape REQUIRED-COLUMN SET". RULING 2 makes the dependency edge
   normative: "derivation/build GATES on #114 landing — the shape must name that
   dependency edge."
4. **Therefore FM-5 design-lock literally has nowhere to land until #114 merges**
   (GLINT L1-3). Without this pin, the ordering is implicit nowhere: the CLEAR bundle §B.5
   deploy bundle does not currently name #114, and the FM-5 ruling names the gate but not
   the bundle slot.

## Amendment-by-reference to CLEAR bundle §B.5

The CLEAR-READINESS bundle §B.5 ("the held-merge + post-soak deploy bundle": #130 merge,
conditional EMF, floor codification, β-3, Node20 residue) is hereby READ AS ALSO carrying
**#114 as the bundle's first merge**. The bundle file itself is NOT edited — it is an
accepted record under the freeze; this pin is the standalone amending record, per the same
discipline that ratified-spec §B.3 amendments used.

## Recommended post-soak deploy-bundle sequence

One deploy window, one reset-free bundle, then re-anchor whatever soak follows
(bundle §B.5 discipline):

1. **#114** (`fpc/phase1-dtype-parity`) — creates `dataframes/contracts/` + the
   FieldContract SSOT; dtype-parity RED guard + asset_edit.score reconcile.
2. **#132** (eunomia E4 pre-clear CI debt consolidation — node24 brownout + coverage
   dotfile + CA retry + conftest extraction) — CI substrate next, so the bundle's own
   checks run on the consolidated pipeline.
3. **#130** (canary section-arm selector fix, AUTHORED-HELD per DEFER #12) — restores
   the section arm's verdict for any post-bundle canary/blast run (the post-clear blast
   judges PROJECT-arm-only until this lands — CHAOS-DESIGN §0 UV-P-3).

All three verified OPEN this pass (`gh pr view {114,130,132}`). **Then FM-5 design-lock
can start**: the SSOT home exists on main, design-lock re-confirms RULING 1
(contract-driven subset) against the actual declared union, and any schema-selection
DEPLOY still waits for its own soak discipline per RULING 3.

## What this pin does NOT do

- Does not merge anything (asana main is MERGE-FROZEN through 06-18; Trap 6 — the merge
  IS the deploy).
- Does not edit the CLEAR bundle, the operator ruling, or SPEC-fm5.
- Does not touch the soak clock, any task-def, or any live infrastructure.
- Does not rule widen-vs-rebind per consumer (design-lock territory, intersects SEAM-2).

## Evidence Grade

`[STRUCTURAL | MODERATE]` — hygiene-station self-ref ceiling; every probe in §Why
re-fired first-party at fa265ce1 this pass (git show exit-128 nonexistence, gh PR file
list, PR open-states). The pin's force derives from the operator ruling (RULING 2) it
operationalizes, not from this station's authority.
