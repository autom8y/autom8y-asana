---
type: handoff
handoff_kind: emit-and-wait
handoff_type: assessment
schema_version: "1.0"
status: proposed
cross_repo: true
from: arch (fleet-three-way-reconciliation-keystone · N3 · GATED axis)
to: autom8y-asana CR-3 offer-axis producer (warm-lane / cutover single-writer)
date: 2026-06-08
severity: P0-consumer-blocking — but DELIBERATELY PAUSED (Trap-4); NOT a defect to fix on arch's timeline
non_prescriptive: true
discipline: "EMIT-AND-WAIT. arch surfaces ONE gating question (A-2: the named rung) + ONE contract obligation (INV-C8). arch does NOT un-pause the warm lane and does NOT prescribe the cutover. The warm-lane re-arm is RESERVED to CR-3's own discipline."
reserved_levers:
  - "CR-3 warm-lane un-pause / re-arm — CR-3 PRODUCER ONLY, inside the GATE-2 soak discipline"
feeds_contract:
  - "FFG-FLEET-RECON-AXIS-TRUSTWORTHINESS-CONTRACT-v1-DRAFT-2026-06-08.md INV-C8 (a deliberate Trap-4 quiesce MUST be a DECLARED loud state — byte-distinguishable from an unplanned cold) + INV-C5 (warmed-EMPTY must stay loud, never silent-green)"
upstream_signal:
  - "autom8y-asana/.ledge/handoffs/HANDOFF-account-status-recon-to-autom8y-asana-offer-axis-cache-not-warmed-2026-06-08.md  ← the full consumer escalation: 503 CACHE_NOT_WARMED receipt, A-1..A-6, the Trap-4 read. READ IT FIRST."
---

# HANDOFF — arch→CR-3: offer-axis named-rung question (N3, emit-and-wait)

> **Read the upstream signal first.** It carries the live 503 `CACHE_NOT_WARMED` receipt (×3 over 8 min,
> persistent — not a warm-up window), the candidate causes, and questions A-1..A-6. The upstream read is
> almost certainly correct: **the cold offer axis is the expected shadow of the deliberately-quiesced
> CR-3 GATE-2 warm lane (Trap-4: warmer reserved=0 + schedule DISABLED)**, not a fault. arch affirms that
> read and does **not** ask you to un-pause outside your cutover discipline.

## What arch is NOT doing

- **NOT un-pausing the warm lane.** Touching the Trap-4 quiesce mid-soak risks corrupting an in-flight
  production cutover. The re-arm is yours, on your sequencing.
- **NOT prescribing the remediation.** A-1/A-3/A-4/A-5/A-6 (warmer materialization, the retry-contract
  contradiction, fleet scope, population-floor, vertical semantics) are the producer's design space.

## The ONE gate arch needs answered (A-2)

> **At what named rung of the CR-3 cutover does the offer axis become reliably warm for downstream
> consumers?**

The keystone N5 (the ASR dry-run that proves the three-way reconciliation) is gated on this rung. arch needs
the rung label — whether that is a re-armed warmer inside the GATE-2 soak, a post-cutover warm-lane
restoration, or an interim warm of the offer entity only. **arch does not choose which; it needs to know
which, so N5 can be sequenced behind it.**

## HALT-FORK (G-HALT → Pythia)

**If the CR-3 named rung contends with the N5 sequencing** — e.g. the offer axis cannot be warm until after
a cutover stage that lands past the eunomia wall (2026-08-15), or the rung depends on the campaigns axis or
the auth arc — HALT and fork back to Pythia to re-navigate. Do not silently absorb a sequencing conflict.

## The ONE contract obligation arch adds (INV-C8)

The fleet trustworthiness contract codifies: **a deliberate pause MUST be a declared loud state.** Today the
Trap-4 quiesce and an unplanned cold failure are **byte-identical** (both `503 CACHE_NOT_WARMED`). The
contract requires they become distinguishable — a `paused_until` marker / a distinct planned-maintenance
code on the 503 envelope — so a planned pause cannot be mistaken for an outage and an outage cannot hide
behind "it's just paused." This is **not** an ask to un-pause; it is an ask to make the pause *honest*. It
is an INV-C8 obligation feeding the N4 enforcement build, sequenced at whatever rung you name in A-2 — not
a blocker on the pause itself.

Paired obligation (INV-C5): when the warm lane re-arms, a warmed-EMPTY offer frame MUST stay **loud**
(503 / `CASCADE_NOT_READY` / degraded), never a silent 200-empty. ASR exists to refuse "empty == clean";
the contract codifies that refusal as a producer obligation.

## Acceptance rung (G-RUNG — no rounding)

Per the upstream realization rung: offer axis **cold-never-warmed** → **warm-verified** only on a
producer-confirmed materialized+persisted offer frame **and** an ASR live **200-with-rows on both `active`
and `activating`** — not a 200-empty, not a producer assertion, not a log line. This clears the offers axis;
the keystone closes only at the N5 dry-run (offers ∧ campaigns ∧ billing, `accounts_analyzed >> 0`).

## Open semantics flag (load-bearing, both arcs)

`(office_phone, vertical)` G2 semantics are `telos_status: DECLARED — NOT frozen`
(`.sos/wip/frames/g2-vertical-semantics-contract.md`). The offer frame's `vertical` column meaning, once
warm, depends on that adjudication, and it gates join-correctness in **both** the reconciliation arc and the
auth resolver arc (contract §6). Any warm-lane remediation must not silently assume frozen vertical
semantics.
