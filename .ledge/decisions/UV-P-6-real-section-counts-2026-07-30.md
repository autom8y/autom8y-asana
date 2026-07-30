---
type: decision
decision_subtype: uv-p
id: UV-P-6
artifact_id: UV-P-6-real-section-counts
status: proposed
initiative: substrate-v2-epoch
date: "2026-07-30"
registered_by: S8-0 pre-gate hardening (principal-engineer)
owner: WS-B/S8-2
consumer: per-day budget counter (PerDayBudgetLedger) cap calibration
---

# UV-P-6 — real per-entity section counts are UNVERIFIED

## Premise (the open UV-P)

The per-day P10 budget model (`tests/harness/substrate_gate/budget.py`,
`PerDayBudgetLedger`) charges one unit per upstream fetch ATTEMPT and refuses at a
per-day cap. Calibrating that cap to a real API-allowance requires the **real per-entity
section counts** — how many section artifacts a rebuild fetches per (project, entity).
Those counts are **UNVERIFIED**.

The wave-2 → S8 handoff named this as an open UV-P but never REGISTERED it:

> "Per-day budget counter (net-new): ... Real section counts for the model = an open
> UV-P (S2/S4 entry, still open)."
> — `.ledge/handoffs/HANDOFF-wave2-to-s8-cutover-gate-2026-07-29.md:100-102`

This artifact registers it so it cannot silently ride into cap calibration as a guess.

## Why it matters (consumer)

`PerDayBudgetLedger.cap` is a hard REFUSE threshold. If it is set against a guessed
section count, the budget either (a) refuses real work early (cap too low) or (b) fails
to protect the daily allowance (cap too high). The cap must be derived from the real
per-entity section fan-out, not assumed.

## Partial observation from the S8-0 recapture (does NOT discharge)

The S8-0 fixture recapture (`.ledge/reviews/RECEIPT-s8-0-fixture-recapture-2026-07-30.md`)
observed, for the OFFER entity of project 1143843662099250 ONLY:

- **33** section artifacts under `offer/sections/` (S3 LIST).
- **15** distinct `section` names in the assembled offer frame (row_count 4180).

This is a single-entity, single-project first data point. It informs but does **NOT**
discharge UV-P-6, which requires the full per-entity fan-out across the entity classes a
rebuild serves, captured at the S8-2 arm window.

## Discharge route

Derive the real per-entity section counts from the **live S3 section listing** during
the O4 leg-2 window-open re-snapshot at **S8-2 arm** (`aws s3 ls .../<entity>/sections/`
per entity class; no Asana call). Feed the observed counts into the budget counter's cap
calibration. On discharge, flip this artifact `status: accepted` and cite the
S8-2 re-snapshot receipt.

## Owner / status

- **Owner:** WS-B / S8-2.
- **Consumer:** `PerDayBudgetLedger` cap calibration.
- **Status:** `proposed` (open; partial single-entity observation only).
