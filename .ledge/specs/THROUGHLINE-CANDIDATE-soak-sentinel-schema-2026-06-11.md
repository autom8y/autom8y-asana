---
type: spec
status: draft
name: soak-sentinel-schema
throughline_status: CANDIDATE
origin: "2026-06-11 telos-soak (autom8y-asana, anchor 06-11T15:24:21Z, clear 06-18): daily 4-receipt attestation schema — (a) deploy-freeze, (b) band, (c) alarm states, (d) AC-6 cadence — plus a boolean-decidable RESET-vs-LOG law. Day-1 executed by sre (SOAK-DAY-1-ATTESTATION / SOAK-SENTINEL-PROTOCOL, .ledge/decisions/); E1 dogfooded all four sections AS WRITTEN, stranger-test PASS."
custodian_of_record: "eunomia governance rite (autom8y-asana residency at mint); registered at station E3"
custodian_primary: [eunomia]
custodian_meta: Pythia
evidence_grade: "[MODERATE, self-ref-capped]"
evidence_annotation: "N_executed=1 day (day-1, sre). E1 dogfood (EUNOMIA-INTERIM-CORROBORATION-keystone-day1-2026-06-11.md) is rite-disjoint — 'the sentinel protocol's four receipt sections all execute as written by a stranger and yield decidable rulings' — but SAME-satellite and SAME-day; it hardens day-1, it does not increment N. Method verdict: method-SOUND-with-findings (3 method findings, ZERO blocking). Same-satellite evidence NON-promoting per the O-2 precedent."
n_applied: "1 day executed (+1 rite-disjoint same-day dogfood, non-incrementing)"
n_prevented_incidents: 0
siblings: [iris-pipe-smoke-disambiguation, telos-integrity, integration-boundary-fidelity]
registered_caveats: [MF-1, MF-2, MF-3]
user-invocable: false
---

# Throughline (candidate): soak-sentinel-schema

> Registered 2026-06-11 by eunomia entropy-assessor (E3). CANDIDATE at N=1.
> This registration takes the SCHEMA into custody — the four-receipt shape and
> the RESET-vs-LOG law — not the soak's verdict. The 06-18 STRONG seam stays
> clock-gated and reserved; nothing here touches the clock.

## §1 Statement

**A long-soak is attestable iff a daily, stranger-executable, four-receipt
attestation — (a) deploy-freeze identity, (b) content band, (c) alarm armed-state,
(d) traffic cadence — routes every observation through a boolean-decidable
RESET-vs-LOG law, such that clock-resetting events and log-only exceptions are
classified mechanically, never by judgment.**

The schema's load-bearing property is decidability by a stranger: E1's dogfood
("Walking §3 against my live receipts, every branch was boolean-decidable
without interpretation") is the empirical PASS of exactly this property.

## §2 N-Applied Evidence (N=1, same-satellite)

- **Day-1 execution (sre)**: all four sections GREEN on :511/49099b12;
  artifacts at `.ledge/decisions/SOAK-DAY-1-ATTESTATION-telos-soak-2026-06-11.md`
  and `SOAK-SENTINEL-PROTOCOL-telos-soak-2026-06-11.md`.
- **E1 rite-disjoint dogfood (same day, same satellite)**: §2(a) deploy-freeze
  GREEN (sole :511 COMPLETED, warmer lockstep), §2(b) band GREEN first-party
  (unit 724/3027=0.2392, offer 1352/4079, gun 10, coherent 593), §2(c) three
  alarms present+inactive, §2(d) 20 organic bursts + labeled-synthetic
  exclusion. Verdict pair: "method-SOUND-with-findings × day-1-CORROBORATED",
  ZERO disputes.
- **Honest counter**: one executed day on one satellite. A 7-day soak needs 7
  attestations; N stays 1 until distinct-satellite (or at minimum
  distinct-incident) adoption per the gate.

## §3 Registered Caveats (carried verbatim from E1 method findings)

- **MF-1 (friction/blindspot)** — "§2(a) deploy-freeze is a point-in-time
  snapshot — blind to a merge that deploys AND self-reverts BETWEEN daily
  attestations." E1's remedy: add §2(a3) diffing ECS `deployments[].createdAt`
  + `events[]` against the prior attestation; "any new deployment event in the
  window = RESET-class even if HEAD is back to 49099b12." This blindspot
  already bit (the #129 deploy raced the 14:59 anchor → re-anchor 15:24:21Z).
- **MF-2 (cosmetic/over-deferral)** — gun/coherent are declared cross-repo
  UV-P but "ARE first-party re-derivable from the two parquets via the
  canonical office_phone join." Remedy: upgrade §2(b) to first-party
  re-derivation for the 2-frame coherence counts (full 82-cell lattice remains
  cross-repo).
- **MF-3 (cosmetic/stale-tree trap)** — §4 assumes a non-stale local checkout;
  remedy: §0 preflight pinning operator checkout to the substrate SHA. (Shared
  with the iris-pipe-smoke candidate.)

Caveats travel with the candidate; adoption of the three remedies into the
protocol text is the first LOG-grade improvement available without touching
the clock.

## §4 Promotion Gate

Per the ibf-precedent criteria (quoted): N>=2 requires "a DISTINCT incident at
a DISTINCT satellite"; INDEX row requires "N_applied >= 3 across at least two
distinct incidents"; STRONG requires an anchor "rite-disjoint AND ...
*preventing* a stub-green cure from deploying inert — not merely detecting it
post-hoc" — for this schema, STRONG-grade evidence would be a RESET branch
firing on a real mid-window event (MF-1 class) and provably saving a soak from
a false clear. Same-satellite daily executions accumulate as corroboration
only (O-2 precedent).

*Authored 2026-06-11, eunomia entropy-assessor (E3). N=1,
[MODERATE, self-ref-capped]. Pythia ruling deferred. The 06-18 STRONG remains
reserved; this file holds the schema, not the verdict.*
