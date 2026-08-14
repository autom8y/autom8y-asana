---
type: decision
status: accepted
id: RULINGS-coc-operator-sitting-2026-08-13
wave: chain-of-custody-closure
date: 2026-08-13
method: "operator sitting via /consult ingest of HANDOFF-coc-wave-close-2026-08-13 (AskUserQuestion, 4 rulings), conducted from the autom8y attribution-lane session; materialized here for the coc lane"
self_assessment_cap: MODERATE
---

# OPERATOR RULINGS — chain-of-custody-closure decision surface

Consumes: `HANDOFF-coc-wave-close-2026-08-13.md` §3/§5. All four next-words
given 2026-08-13.

## R-1 — F-1 RULED: Tier 1, CC-5 builds now (coc lane owns)

Offers-only scope (~4,192 tasks, one Lambda). **CC-5 is OPEN** at this ruled
scope. Rationale accepted with the ruling: the only branch that both fits the
fences and beats the AL-5 clock. **Clock binding: AL-5 opens
~2026-08-15T12:45Z** — a warming fix landed before it buys one clean
measurement regime; if the build slips past the window, O-7a segmentation is
mandatory (per the handoff, not renegotiable at build time). Tier 2 remains
forbidden here (fleet redesign; DW-COC-01 pegs it).

## R-2 — RE-2 determinant RESOLVED YES; severity routed to SEC-002 for independent trace

Probe receipts (own-hands, `autom8y/services/auth/service-accounts.yaml`,
2026-08-13): **`ace` and `iris` are BOTH registry-declared exempt-SAs** —
`business_scoped: false` (Bucket 1, the bucket whose terraform emits
`can_issue_service_token` / `bypass_scope_enforcement` OpenFGA tuples per the
registry header), each with a formal `exemption` block (`category: ai_agent`,
`approved_by: tomtenuta`, 2026-04-11 / 2026-04-13, TENSION-005 mitigated via
D5 5-min TTL), scope sets read-only (`data/analytics/scheduling/sms/ads:read`).

**Operator ruling: route to SEC-002 for an independent trace BEFORE any
re-grade** — the registry receipt is necessary but the grant CHAIN
(registry → OpenFGA tuples → issuance-time behavior) gets a security-rite
re-derivation first. Until SEC-002 reports, RE-2 F-001 stays **High** with the
determinant-YES receipts attached to DW-COC-02; the CF-1 widening (iris's
logical identity also holds `asana:read` via OAuth-client terraform — a second
uncounted population) rides the same SEC-002 charge.

## R-3 — CC-7 RULED: proceed on defaults with the AMENDED TWO-ACTION boundary

F-7 (enforce-with-baseline, fingerprint-keyed, covering every historical trip)
and F-8 (in-repo) stand as ratified. CC-7's boundary is WIDENED to both
actions — local job **+** branch-protection contexts registration — per MC-1;
CC-7 must ingest `CRITIQUE-cc6-gitleaks-recon-2026-08-13.md:99-149`. **CC-7 is
OPEN**; CC-8 (attest limbs) unblocks behind it per the handoff's chain.

## R-4 — Held PR word GIVEN: opened un-armed

CC-1 committed on `coc-cc1-reconverge` @ `79d9f4a1` (the worktree's 12
authored entries incl. the exit note; anti-collision guard was CLEAN at
commit) and opened as **autom8y-asana PR #365** — NO auto-merge (enforce_admins
noted in the PR body), merge HELD. Rung: PR-UP-MERGE-HELD once CI is observed.
**F-4 fence-lift NOT given** — explicitly withheld pending AL-5 re-pricing per
the handoff's own instruction; no merge word exists.

## Standing state after this sitting

OPEN: CC-5 (Tier-1, clocked), CC-7 (two-action boundary), SEC-002 charge
(RE-2 trace + CF-1 widening). HELD: PR #365 merge; F-4 fence. UNCHANGED:
DW-COC-01..04 pegs; CF-2..CF-22 carries; CC-8 blocked behind CC-7; eunomia
limb-(a) blocked until both WS-A halves LAND.
