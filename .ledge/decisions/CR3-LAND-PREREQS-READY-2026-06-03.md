---
type: decision
id: CR3-LAND-PREREQS-READY-2026-06-03
title: "CR-3 land — reversible prerequisites READY for IC-GATE 1"
rite: releaser
status: proposed
date: 2026-06-03
initiative: cr3-fleet-data-plane-foundation-cutover
reversible_only: true   # nothing merged/applied/deployed; origin/main == 3c1dca57
evidence_grade: moderate # self-ref releaser; STRONG only where source-re-verified this pass
verifies: CR3-COORDINATED-LAND-RUNBOOK-2026-06-03 (step a + IC-GATE-1 readiness)
---

# CR-3 LAND — REVERSIBLE PREREQUISITES READY (releaser certification)

> Authored by the releaser (main thread) after the prerequisites workflow's adjudication step
> aborted on an agentType bug (`chaos-engineer` absent from the releaser registry). The three
> reversible work lanes had ALREADY completed; their outputs are re-verified here AT SOURCE
> (REST GET / git ls-remote / git grep), not trusted from the lane reports. `default-to-REFUTED`.

## Invariant (re-asserted this pass)
- **origin/main HEAD == `3c1dca57`** (`git ls-remote origin refs/heads/main`) — UNCHANGED. Nothing merged/applied/deployed/secret-op'd. FROZEN=4 holds.

## Prerequisite status — 3/3 COMPLETE

| # | Prerequisite | Verdict | Source receipt |
|---|--------------|---------|----------------|
| P-a | Strip-rebase #99/#100/#101/#102 off origin/main | **DONE** | Corrected cutpoint `873653e7` (not the runbook's `25d466ca^`, which would have KEPT the delta). Each branch now: 1 commit vs main, fast-lane STRIPPED, `mergeable_state=clean`. Heads: #99 `cb32b964`, #100 `6e302ba9`, #101 `3a20ed73`, #102 `93175d0d` (correctly STACKED: base=`sre/serve-stale-adr-stale-served-knob-2026-06-03`). |
| P-103 | Fix #103 (PQ-5 guard) CI-red | **DONE** | head `b35c80c8`, `mergeable_state=clean`, all checks success (CodeQL, gitleaks, 4 Test shards, dep-review, OpenAPI-drift). |
| P-lane | Build the greenfield §B SECTION warm lane | **DONE (PR #104)** | `6ee7b67c` on origin. `section_only_prematerialization_keys()` `project_registry.py:357` (34 keys, heaviest-first, backstop ⊆ bulk `:393-401`); `prematerialize_section_set` 3rd key_source `cache_warmer.py:1217`/`:1315` + `timeout.py` continuation; disjoint prefix rides existing `CACHE_WARMER_CHECKPOINT_PREFIX` (`section-fast/`); TF spec `.ledge/specs/cr3-section-warm-lane-tf-spec-2026-06-03.md` (gate-5 land dep). 19 new tests, 210 pass, ruff/mypy clean. CI in-flight (14✓/7-pending) — gates at step g, NOT IC-GATE 1. |

## IC-GATE 1 readiness — GO
All five merge-order PRs are `mergeable_state=clean`, `merged=false`, base main (except #102 stacked on #99):
`#98 → #100 → #99 → #101 → #102`. #103 is clean/green but OUT of the IC-GATE-1 batch (it merges on its own clean state; not in the §B dep chain).

**Merge mechanics for the gate (per runbook step b):**
1. Merge in dep order; after EACH merge, confirm `merged=true` + main-Test green BEFORE the next.
2. **#102 retarget:** after #99 merges, retarget #102 base→main (GitHub auto-retargets on #99 merge; else `gh api -X PATCH .../pulls/102 -f base=main`) then merge.
3. **Deploy-trap guard:** each merge fires `satellite-dispatch → a8 deploy` which re-overlays cpu/mem from the **A8_VERSION=v1.3.8** manifest = **1024/2048** (the current baseline — NOT a regression; the 2048/8192 bump is the later IC-GATE 4 / step e). Confirm PR #94 (`concurrency` guard) is merged or quiesce in-flight dispatches between merges.
4. **ABORT:** any merge turning main-Test red → STOP, do not merge the next.

**This is the first `[IRREVERSIBLE]` one-way door — held for the operator's (IC) explicit sign-off.**
