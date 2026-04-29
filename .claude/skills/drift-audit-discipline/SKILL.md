---
name: drift-audit-discipline
description: "Synthesis-altitude discipline for re-running drift-audit at any altitude where mixed-resolution upstream substrates are being consolidated. Use when: authoring any plan that consumes [UNATTESTED] upstream framing, consolidating inventory artifacts from different points in time, synthesizing substrates of mixed resolution into a new artifact. Triggers: plan-authoring step, consolidation-planner, inventory synthesis, mixed-resolution upstream substrates."
type: discipline
status: repo-local (Stage 1 of 2 — satellite-primitive-promotion deferred; see defer-watch id: drift-audit-discipline-fleet-promotion)
minted_by: janitor (hygiene rite)
minted_at: 2026-04-29
parent_initiative: actual-blockers-2026-04-29
promotion_track: satellite-primitive-promotion (DEFERRED — see .know/defer-watch.yaml)
---

# Drift-Audit Discipline

> Synthesis-altitude clause (canonical — do not paraphrase):
>
> "Re-run drift-audit at any altitude where mixed-resolution upstream substrates are being consolidated. Specifically: any plan-authoring step that consumes `[UNATTESTED]` inventory framing MUST verify ground truth against `origin/main` before propagating the framing forward. Failure mode: a planner reads earlier `[UNATTESTED]` framing from upstream inventory and propagates it forward as fact, even after a downstream sweep has resolved the question — because the planner does not re-run drift-audit at synthesis-altitude. Detection: any artifact citing `[UNATTESTED]` upstream while not citing the downstream resolution. Remediation: re-invoke drift-audit-discipline with the originating evidence anchor."

## §1 WHEN — Invocation Conditions

Apply this discipline whenever ANY of the following conditions hold:

1. **Plan-authoring step consuming inventory artifacts** — any consolidation-planner, executor, or orchestrator that reads inventory outputs (INVENTORY-pipelines, SWEEP reports, SCAN artifacts) to build a new plan or artifact.

2. **Mixed-resolution upstream substrates** — the authoring step combines artifacts from different points in time, where some have been resolved/swept AFTER the initial inventory was tagged `[UNATTESTED]`.

3. **Inheritance from `[UNATTESTED]` framing** — the authoring agent encounters any claim tagged `[UNATTESTED — DEFER-POST-INVENTORY]` or similar in upstream artifacts.

4. **Consolidation across branches** — when synthesizing claims about file presence/absence, branch state, or cross-repo facts derived from different audit passes.

**Canonical discrimination question:**

> *"Has any upstream substrate been tagged `[UNATTESTED]` at inventory time, and has a downstream sweep or audit potentially resolved that question after the inventory was authored?"*

If YES → MUST re-run drift-audit before propagating any claim from that substrate forward.

## §2 HOW — The Discipline's Mechanics

### §2.1 Re-run drift-audit before synthesizing

Before authoring any artifact that inherits framing from an upstream inventory or substrate containing `[UNATTESTED]` claims:

1. **Identify the resolution timeline** — determine when the upstream inventory was authored vs. when downstream sweeps/audits ran.
2. **Probe current ground truth** — for any `[UNATTESTED]` claim about file presence/absence or branch state, run a live probe:
   - File presence: `git ls-tree origin/main <path>` or `git ls-files --error-unmatch <path>`
   - Branch state: `git log origin/<branch> --oneline -1`
   - Cross-repo fact: probe the authoritative repo directly at the relevant SHA
3. **Verify resolution** — check whether downstream sweeps have discharged the `[UNATTESTED]` tag. Read the SWEEP/RESOLUTION artifacts explicitly, not just the INVENTORY.
4. **Anchor the re-verification** — cite the live probe result in the authoring artifact with a `{path}:{line_int}` anchor or verbatim command output per F-HYG-CF-A receipt-grammar.

### §2.2 Failure mode detection

The failure mode fires silently: a planner reads an `[UNATTESTED]` claim from INVENTORY, does NOT read the downstream SWEEP that resolved it, and propagates the stale framing forward as fact. There is no explicit error — the artifact simply carries an inverted or stale claim.

**Detection pattern:** any artifact citing `[UNATTESTED]` framing from an upstream source WITHOUT citing the downstream resolution is a potential Pattern 6 recurrence.

**Example of the failure mode (from SCAR-P6-001):**
- INVENTORY-pipelines L347 tagged a claim as `[UNATTESTED — DEFER-POST-INVENTORY]`
- SWEEP §6 subsequently resolved the question with ground truth
- consolidation-planner read INVENTORY but not SWEEP
- PLAN §3 L101 + §9 L230 carried the inverted claim (`test_source_stub.py` "absent on origin/main") as fact
- Ground truth: file IS present at blob `bf4f74180e15f07a698538afa14f6f82d47bf641` (PR #174 merge commit `f2dfc1c3`)

### §2.3 Remediation

When Pattern 6 is detected in a produced artifact:

1. STOP propagation — do not proceed to the next phase with the stale artifact
2. Identify the originating evidence anchor — which `[UNATTESTED]` claim was inherited?
3. Re-invoke drift-audit-discipline — probe ground truth per §2.1
4. Correct the artifact with the live probe result
5. Cross-reference the correction: cite both the original `[UNATTESTED]` source and the resolution sweep

## §3 Cross-References (originating evidence chain)

This skill was minted to codify Pattern 6 recurrence prevention. The originating evidence chain:

- **VERDICT §5 Pattern-6-Recurrence Meta-Finding**: `.ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md` §5 — Pattern 6 RECURS at PLAN-AUTHORING altitude; codification target identified; synthesis-altitude clause recommendation at L135-L137.

- **CASE Pattern 6 + §8 Q-1**: `.ledge/reviews/CASE-comprehensive-cleanliness-2026-04-29.md` Pattern 6 (§4 Q4, scan-altitude codification) + §8 Q-1 (initial promotion track to /go dashboard — "NOW URGENT" aspiration now codified here).

- **SCAR-P6-001**: `.know/scar-tissue.md` SCAR-P6-001 — durable scar entry for Pattern 6 recurrence at PLAN-AUTHORING altitude; the concrete case (inverted `test_source_stub.py` claim) and the defensive discipline are documented there. See also: this skill.

## §4 Authority Boundary

This is a **repo-local Stage 1 mint** (Option C of PLAN-actual-blockers-2026-04-29.md §3). Fleet-wide promotion to knossos shared-mena altitude is deferred via `.know/defer-watch.yaml` entry `id: drift-audit-discipline-fleet-promotion`.

**Stage 2 (deferred)**: satellite-primitive-promotion protocol will lift this skill to knossos canonical altitude when the watch_trigger fires (2026-05-29) or the deadline is reached (2026-09-29).

Until Stage 2 promotion, this skill is available to agents in the autom8y-asana repo context only.
