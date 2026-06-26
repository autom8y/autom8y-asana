---
type: decision
subtype: clock-doctrine
status: accepted
title: "CLOCK DOCTRINE — src-identity-carry: behavior-neutral deploys CONTINUE the soak (no restart, no re-game-day); only src-material deploys reset"
date: 2026-06-15
authority: operator stakeholder-interview ruling 2026-06-15 (freeze-fix Q: 'Adopt src-identity-carry as standing clock doctrine')
supersedes_clause: the unqualified reset law in IC-SOAK-REANCHOR-telos-soak-2026-06-11.md §"What RESETS" — for the BEHAVIOR-NEUTRAL case only
motivation: 5 soak resets across the arc (#129 node20, #131 pyjwt, the :513 fleet wave, the :516→:525 rerolls, #136 reusable-pin) were ALL behavior-neutral CI/dep churn the rung carried through anyway; the brittle 'any new task-def = new soak from zero' created ceremony without epistemic gain and made a 7-day contiguous window structurally unreachable under live fleet churn
---

# CLOCK DOCTRINE — src-identity-carry

## The rule
Classify every mid-soak deploy by its **application-source diff vs the soak anchor's source commit**:

```
src_material_diff = git diff <anchor_sha>..<new_sha> -- src/ Dockerfile tests/ pyproject.toml
                    (+ uv.lock IFF the changed package is imported by src/ — else uv.lock is behavior-neutral)
```

- **Behavior-neutral deploy** (`src_material_diff` EMPTY): the soak clock **CONTINUES** — it does NOT
  restart. The rerolled task-def is the SAME LOGICAL SUBSTRATE (byte-identical application behavior);
  accrued soak time is preserved. The rung **CARRIES** (self-heal-game-day-proven, corroboration,
  serve-proof) — **no re-game-day owed**. Logged in the daily attestation, not escalated.
- **Src-material deploy** (`src_material_diff` NON-EMPTY): the clock **RESTARTS** at the new task-def's
  steady-state moment, and the rung **RESETS** — re-acceptance (re-game-day + re-corroboration) is owed.
  This is the only deploy class that is RESET-grade. Surface to operator.

## Why "continue, not just re-anchor"
The prior law re-anchored the clock on EVERY new task-def. Under live fleet pin-propagation that
deploys behavior-neutral churn repeatedly, the 7-day window could never complete — each CI bump
restarted it (it restarted 5×). The soak tests the APPLICATION's sustained correctness; if the
application source is byte-identical, a task-def reroll (new image TAG, same SOURCE) does not
invalidate accrued soak time. Continue-through is the epistemically honest treatment.

## Sentinel integration
The daily attestation's receipt-section (a) already pulls the main sha. It now ALSO computes
`src_material_diff` vs the anchor source when main has moved: EMPTY → LOG "behavior-neutral deploy,
clock continues" (record the new task-def + tag); NON-EMPTY → AMBER/RED "src-material deploy —
RESET-candidate" → surface to operator (do not rule). This makes the classification automatic and
removes the human-judgment gap that let the #136 reset slip through a 3-day blackout unnoticed.

## What is unchanged
- Operator sovereignty over RESET-class declarations (src-material) stands.
- The merge-freeze intent stands as a SOFT freeze (prefer no mid-soak merges); but behavior-neutral
  breaches no longer cost a reset — they cost a log line. Hard enforcement was NOT chosen (it fights
  the fleet's propagation machinery); this doctrine makes hard enforcement unnecessary for the
  behavior-neutral class, which was 5/5 of the actual breaches.
- Band/content floors, alarm, and AC-6 sections are unaffected — a behavior-neutral deploy that
  ALSO degrades content is still caught by sections (b)/(c)/(d) on their own merits (see the live
  Finding-3 band anomaly, which is being disambiguated independently of this clock doctrine).

## Applied to the current window
The :512→:526 chain (fa265ce1 ≡ 6517f0b3, src-identical; the only diffs are the pyjwt uv.lock pin —
unimported by src/ — and workflow files) is ONE logical substrate under this doctrine. The soak
CONTINUES across it; the re-anchor recorded separately (INCIDENT-soak-blackout-and-136-reset) places
the window's anchor at the first clean steady moment on this substrate, gated on the Finding-3 band
disambiguation clearing.
