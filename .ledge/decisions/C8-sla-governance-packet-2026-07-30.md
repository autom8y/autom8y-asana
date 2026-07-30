---
type: decision
decision_subtype: decision-packet
artifact_id: C8-sla-governance-packet
id: C8
title: "C8 — SLA governance: the dual-role TTL is the wound's re-entry vector, and it starves the parity window"
created_at: "2026-07-30"
author: main-thread orchestrator (S8 corridor session session-20260730-141905-058c4fd7)
status: proposed
lifecycle_status: READY-FOR-OPERATOR
rite: 10x-dev
initiative: substrate-v2-epoch
sprint: S8
carry: "adversary C8 / AV-3 (ADVERSARY-substrate-v2-design-s1) — the highest-residual carry; wave-2 handoff §4c: surface NO LATER than the S8 gate"
sharpened_deadline: "BEFORE S8-2 arms (upgraded from 'by PT-03') — see §The cadence math"
---

# C8 — per-entity SLA governance (operator ruling)

> **The problem in one sentence:** v2's freshness SLA (`sla_seconds_for`,
> `substrate/freshness.py:282-287`) reads the entity registry's
> `default_ttl_seconds` — a value that was authored as a CACHE TTL, is documented
> as dual-role, and was never governed as a freshness promise; an ungoverned
> value re-serves the wound with a green proof (AV-3), and the CURRENT values
> would make v2 refuse almost every offer serve.

## The values as they stand (verified 2026-07-30, entity_registry.py)

| entity | default_ttl_seconds (= v2 SLA today) | anchor |
|---|---|---|
| business | 3600s | :456 |
| unit | 900s | :483 |
| contact | 900s | :509 |
| **offer** | **180s** | :528 |
| asset_edit | 300s | :552 |
| process | 60s | :571 |

(Full table probe: `grep -nB8 default_ttl_seconds src/autom8_asana/core/entity_registry.py`.)

## The cadence math (why the deadline sharpens to before-S8-2)

Observed prod warm cadence for the wound offer plane (UV-P-2 discharge,
2026-07-29): writes at 15:08 / 15:25 / 15:50 UTC — **~17–25 minutes between
rebuilds**. With `offer SLA = 180s`, a v2 artifact is provably-fresh for only
3 minutes of every ~20-minute cycle: **v2 would REFUSE offer serves ~85–90% of
the time.** Two consequences:

1. **The parity window starves.** S8-2 compares v2's number beside v1's; a v2
   that mostly refuses yields almost no comparable observations — the window
   cannot close its divergence ledger. C8 is therefore a **hard S8-2
   precondition**, not a by-PT-03 nicety.
2. **The semantic delta the operator must own (AV-3):** v2's promise is
   "provably ≤ SLA-old", NOT "current". Whatever value you ratify IS the
   staleness you are licensing with a green proof. 180s was never a decision —
   it is a cache-tuning fossil wearing an SLA costume.

## Ruling options (enumerated)

| # | Option | Consequence | Verdict |
|---|---|---|---|
| (a) | Accept 180s as the offer SLA | Truth-maximal but refusal-heavy: v2 refuses ~85-90% of offer serves at current warm cadence; parity starves; post-cutover consumers see mostly 424s until warm cadence is tightened to <3min (a real infra cost decision nobody has made) | REJECT as-is |
| (b) | Raise `default_ttl_seconds` for offer (e.g. 3600) | One-line change BUT dual-role: it also lengthens v1's offer CACHE TTL pre-extinction — a v1 behavior change in P6-frozen territory (gray-zone violation), and it permanently couples cache tuning to freshness promises (the AV-3 wound pattern itself) | REJECT (P6 + couples the roles harder) |
| (c) | **Introduce a distinct governed `freshness_sla_seconds` field** (registry-additive; `sla_seconds_for` reads it with fallback to `default_ttl_seconds`) — populated per-entity by THIS ruling | Decouples the roles permanently; v1 untouched (P6 clean); the SLA becomes a governed, named promise. Requires a small src change to a frozen-seam module's INTERNALS (signature/contract unchanged) → routed as an **architect DELTA ruling** per the C12–C16 house pattern, built in a small corridor PR before S8-2 arms | **RECOMMEND** |

## Recommended per-entity SLA values (for ruling under option c)

Derivation: SLA ≥ 2× observed warm cadence (a freshly-rebuilt artifact must
survive one full cycle plus jitter without refusing), aligned where possible to
the pre-existing SLO bar (`frame age < 3600s`, ADR-substrate-freshness-ownership).

| entity | recommended freshness_sla_seconds | rationale |
|---|---|---|
| offer | **3600** | 2× cadence ≈ 50min → round up to the standing 1h SLO bar |
| unit / contact / business | 3600 | same bar; their warm cadence is no faster |
| asset_edit / process | 3600 (provisional) | no measured cadence yet; UV-P-6's section-count discharge at S8-2 arm will carry real cadence data — re-ratify then if warranted |

**What this licenses, stated plainly (AV-3 discharge):** a served offer number
may be up to 1 hour old and still green-proofed. The alternative — "current" —
does not exist in a cached substrate; it is exactly the false promise the wound
made. Refusal fires at >1h, loudly.

## Requested ruling

1. **Mechanism:** `option-c` (recommended) | `option-a` | `option-b`
2. **Values:** `table-as-recommended` (recommended) | amended values inline
3. Acknowledge the semantic delta: "provably ≤ SLA-old, not current" — `ack`

On `option-c` + values: an architect DELTA ruling + one small corridor PR land
before S8-2 arms (P7 bar; qa-adversary review); the parity window then runs
against governed SLAs.

## Ratification record — 2026-07-30

**Ruling received:** operator in-channel grant, verbatim: *"Apply it on my behalf
with user-grade authority grant here through the ruling seam."* Recorded per the
house one-word precedent (DP-2/DP-3 pattern: **recommendations as staged,
unamended**) — the orchestrator notes explicitly that the grant's verb ("apply")
names DP-4a; its extension to this packet is the one-word-precedent reading of
"through the ruling seam" covering the queued rulings. **The operator was invited
to flag if a narrower ruling was intended; values remain one-word-amendable.**

| Sub-decision | Ruling |
|---|---|
| 1 · Mechanism | **option-c** — distinct governed `freshness_sla_seconds` (registry-additive; `sla_seconds_for` reads it with fallback). Architect DELTA + small corridor PR. |
| 2 · Values | **table-as-recommended** — offer/unit/contact/business = 3600s; asset_edit/process = 3600s provisional (re-ratify at UV-P-6 discharge if cadence data warrants). |
| 3 · Semantic delta | **ack** (by grant) — a green proof means "provably ≤ 1h old", never "current". |

**Consequence: C8's S8-2 gate OPENS when the option-c PR lands green + reviewed.**
