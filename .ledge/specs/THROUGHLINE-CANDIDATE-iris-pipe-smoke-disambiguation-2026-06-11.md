---
type: spec
status: draft
name: iris-pipe-smoke-disambiguation
throughline_status: CANDIDATE
candidate_class: technique (disambiguation primitive, narrower than a full discipline)
origin: "2026-06-11 15:40–15:56Z (autom8y-asana telos-soak day-1): counter-dark ambiguity on the receiver SLI (no organic traffic vs broken pipe) resolved by iris driving known live-HTTP traffic at the real serve surface; synthetic burst landed LABELED (16:00Z=1302.9, ~10x envelope) and was excluded from organic denominators (E1 §2(d))."
custodian_of_record: "eunomia governance rite (autom8y-asana residency at mint); registered at station E3"
custodian_primary: [eunomia]
custodian_meta: Pythia
evidence_grade: "[MODERATE, self-ref-capped]"
evidence_annotation: "N_applied=1, single execution, same-satellite (autom8y-asana receiver). E1 independently observed the labeled synthetic burst in its own AMP query_range and excluded it per denominator-integrity — rite-disjoint corroboration of the SAME execution, non-incrementing. Same-satellite evidence NON-promoting per the O-2 precedent on integration-boundary-fidelity."
n_applied: "1 (single execution 2026-06-11 15:40–15:56Z; E1 same-execution corroboration non-incrementing)"
n_prevented_incidents: 0
siblings: [soak-sentinel-schema, integration-boundary-fidelity]
registered_caveats: [MF-3]
user-invocable: false
---

# Throughline (candidate): iris-pipe-smoke-disambiguation

> Registered 2026-06-11 by eunomia entropy-assessor (E3). CANDIDATE at N=1,
> technique-grade. Ruled narrow: this is a disambiguation PRIMITIVE consumed by
> the soak-sentinel schema's §4, not a standalone discipline with its own
> obligation surface. Custody is held separately so its N-counter stays honest
> if other watch protocols adopt it.

## §1 Statement

**When a counter goes dark, drive known traffic at the real surface before
ruling: if the known traffic tracks, the pipe is healthy and the dark window is
a cadence gap (LOG-grade); if the surface stays dark under ~200s of known
traffic, the pipe is broken (RESET-grade).**

Counter-dark is ambiguous between "nothing happened" and "we are blind."
Passive waiting cannot distinguish them; only injected, LABELED traffic at the
production surface (not a replica, not a mock) collapses the ambiguity. The
injected traffic MUST be labeled/excludable so it never contaminates organic
denominators (denominator-integrity sibling obligation).

## §2 N-Applied Evidence (N=1, same-satellite)

- 2026-06-11 15:40–15:56Z: iris live-HTTP smoke drove the receiver serve path;
  the SLI lit (proving pipe-healthy), the burst landed labeled synthetic and
  was excluded from organic cadence analysis. E1 §2(d) re-derived the window
  first-party: "16:00Z = 1302.9 LABELED SYNTHETIC (iris-smoke, ~10× envelope)
  and EXCLUDED (denominator-integrity)" with organic bursts continuing
  (16:30Z=98.8, 17:30Z=106.9, 18:30Z=112.9).
- Honest counter: one execution, one satellite, one surface class (AMP-scraped
  receiver SLI). The dark-under-200s RESET branch has NEVER fired empirically —
  the RESET arm of the statement is design-asserted, not yet evidence-backed.

## §3 Registered Caveat — MF-3 (stale-tree trap)

Carried verbatim from E1: "the §4 disambiguation command path assumes a
non-stale local checkout ... a stranger running §4 from the local checkout
could execute a stale gate script." Remediation recommended by E1: a §0
preflight pinning the operator checkout to the substrate SHA (worktree at
origin/main) before driving the canary. This caveat travels with the candidate
until the protocol text adopts the preflight.

## §4 Promotion Gate

Per the ibf-precedent criteria (quoted): N>=2 requires "a DISTINCT incident at
a DISTINCT satellite"; INDEX row requires "N_applied >= 3 across at least two
distinct incidents"; STRONG requires an anchor that is "rite-disjoint AND ...
*preventing* ... not merely detecting". Additionally, candidate-specific:
at least one promoted anchor SHOULD exercise the dark-under-200s RESET branch
(or a controlled equivalent) so both arms of the statement carry evidence.
Same-satellite executions accumulate as corroboration only (O-2 precedent).

*Authored 2026-06-11, eunomia entropy-assessor (E3). N=1,
[MODERATE, self-ref-capped]. Pythia ruling deferred.*

2026-06-12: runbook-exported to autom8y-data (PR https://github.com/autom8y/autom8y-data/pull/148) — second-satellite application REGISTERED-PENDING-FIRST-FIRING; N increments on first live use, not on doc landing.
