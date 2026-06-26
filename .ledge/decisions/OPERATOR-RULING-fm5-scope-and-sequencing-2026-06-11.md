---
type: decision
subtype: operator-ruling
status: accepted
title: "OPERATOR RULING — FM-5 (FPC Phase-3, CONSUMER axis) accepted: PG-02 contract-driven subset · #114 extends · soak-safe sequencing"
date: 2026-06-11
ratifies: .sos/wip/CONSULT-column-fidelity-orientation-2026-06-11.md
inputs:
  - .ledge/handoffs/HANDOFF-sre-to-autom8y-asana-satellite-column-fidelity-gap-2026-06-11.md
binding_on: the FM-5 /frame + /shape (10x-dev, post-release-seam) — inherit VERBATIM, re-confirm PG-02 scope at design-lock
---

# OPERATOR RULING — FM-5 column-fidelity contract (accepted 2026-06-11)

## Ratified verbatim (from the orientation consult)
- **The S-07/PG-02 reframe**: the gap is the documented minimal-schema shortcut's deferred bill
  arriving on fleet re-enable (`entity_registry.py:885` T1.3 comment), NOT a defect.
- **Producer-side cure, NO consumer band-aid** (telos lens; the monolith's refusal to `.get()` stands).
- **The blend d + a + b + c-ordered + e**: schema-selection fix at the EntityDescriptor +
  FieldContract-driven derivation as the ROOT (d); the consumer-required-column contract spine with
  populate-or-typed-incomplete (a); the coherence-canary column assertion RED-by-construction (b);
  `offer_id` + `project_gid` land as the contract's first two INSTANCES, never orphan point-fixes (c);
  response-metadata column-manifest as loud-fail belt-and-braces (e).

## RULING 1 — PG-02 activation scope: CONTRACT-DRIVEN SUBSET (not eager 30-column parity)
Derive required-columns per query-shape from the FieldContract SSOT + EntityDescriptor
`key_columns`; **expand only as a consumer DECLARES the need.** UK-class; intersects UK-2.
**RE-CONFIRM at design-lock** — this is the load-bearing scope decision; the frame must surface it
explicitly.

## RULING 2 — #114 relationship: FM-5 EXTENDS the open FieldContract SSOT PR
#114 (`fpc/phase1-dtype-parity`, `field_contract_maps.py`) stays OPEN; FM-5 design starts now;
**derivation/build GATES on #114 landing** — the shape must name that dependency edge.

## RULING 3 — Sequencing (soak discipline)
FM-5 design+build is soak-safe; **any schema-selection DEPLOY waits for soak-clear** (a deploy
resets the clock). The #127/`7973c10` release seam + game-day EXP-1 + soak re-anchor land FIRST.
Then: `/10x` → `/frame g2-column-fidelity-contract` → premise-validation BEFORE design-lock
(PV re-pulls live with SVR receipts, never inherits) → `/shape`.

## TELOS riders (carry into the frame)
FM-5 is a PRECONDITION for: (1) **honest S7** — retiring the monolith's legacy get_df fallback on a
column-blind contract converts silent-degrade into a HARD outage for 3 consumers (dependency
direction: monolith S7 DEPENDS-ON our FM-5); (2) **SEAM-2 rebind** — a rebound consumer missing
`offer_id` exit-1s exactly as `business_offers` does today. **The five-signal GROWS**: a
representative consumer frame must carry its full declared required-column set, populated.

## CROSS-REPO RECIPROCITY — the declaration shape (the contract's INPUT)
The monolith sre side will hand back a consumer-required-column manifest (seed: `offer_id` on
project frames + `project_gid` on section frames) after sweeping the other get_df callers.
**The requested shape is the TWO-LAYER form specified in
`.ledge/specs/SPEC-fm5-consumer-column-declaration-shape-2026-06-11.md`** (the round-trip input):
a consumer-owned JSON manifest in the MONOLITH repo (vendored here with a freshness guard — the
SNC gen.json pattern, reversed direction) + a runtime `required_columns` request-field mirror.
Monolith keeps its own cleanups (controller-exit alarm coverage, the zombie schedule).
