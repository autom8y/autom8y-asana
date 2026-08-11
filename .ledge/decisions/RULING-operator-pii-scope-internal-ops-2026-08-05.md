---
type: decision
artifact_type: RULING
status: accepted
initiative: substrate-v2-epoch
wave: S8-2
date: 2026-08-05
session: session-20260803-220334-f2a75514
author: OPERATOR (in-channel word, verbatim below) — inscribed by the main thread
ratification: OPERATOR-DIRECT (not P13 staged-auto; no amend window needed — this IS the operator word)
amends:
  - RULING-pythia-f305-1-active-mrr-referent-2026-08-04.md §6 #8 (PII discipline clause)
  - RULING-pythia-s8-2-adjudication-rubric-2026-08-03.md (PII-projection references)
  - RECEIPT-s8-0-fixture-recapture-2026-07-30.md "PII-SAFE projection" judgment call (leg-1, carried to leg-2/#303)
---

# OPERATOR RULING — PII scope for the internal-ops offer plane

**Operator (verbatim, 2026-08-05):** "these are def not PII (I think you're overcomplicating
with unecessary PII for the internal ops asana projects which dont require this kind of
filtering)" — in reference to `cost` / `offer_id`, following "these should both indeed come
from the offers custom field."

## Effect

1. The offer-plane fields (`office_phone`, `vertical`, `cost`, `offer_id`, `mrr`,
   `weekly_ad_spend`, business names/ids, booking URLs) in the internal-ops Asana projects
   are **business-operational data, not PII** requiring filtering from receipts, fixtures,
   or ledger records.
2. **Parity receipts and divergence ledgers MAY carry per-offer rows** (gids, names, field
   values) — this materially upgrades divergence decomposition: pythia's rubric §2 noted
   per-offer attribution was "prospectively available"; it is now unencumbered.
3. Committed fixtures MAY carry fuller column sets. The existing `(section, mrr)`
   projection fixtures REMAIN VALID (no rework — P7 economy; the projection was never
   wrong, only conservatively narrow).
4. Diagnostic dumps (raw page `custom_fields`, parent-chain contents) may be written to
   scratchpad/receipts without column stripping — relevant immediately to the
   `cost`/`offer_id` extraction hunt.
5. The referent ruling's §6 #8 capture-mechanics condition relaxes from "only the scalar +
   digest land in the ledger" to "receipts may carry the full comparison substrate."
   All OTHER §6 conditions (classifier-sourced set, fail-closed coverage, dedup/filter/cast
   identity, refusal semantics) are UNTOUCHED.

## Boundary

This ruling covers the INTERNAL-OPS Asana projects' offer-plane data. It does not rule on
any other data class; genuinely personal data (if ever encountered) defaults back to
conservative handling.
