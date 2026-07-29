---
type: decision
decision_subtype: decision-packet
artifact_id: DP-1F-v1-live-path-p6-boundary
id: DP-1F
title: "DP-1F — v1 live-service/MCP path vs the P6 freeze boundary (emergent, pre-ruled)"
created_at: "2026-07-29T08:52:09Z"
author: architect
status: accepted                       # recognized lifecycle value
lifecycle_status: RATIFIED-BY-OPERATOR
ratified_on: "2026-07-28"
ratified_by: operator (in-dispatch pre-ruling, 2026-07-28)
schema_version: "1.0"
rite: 10x-dev
initiative: substrate-v2-epoch
sprint: S1
door: "emergent (not in the initial one-way-door register) — surfaced during Phase-3 finalize"
evidence_grade: MODERATE
context: >
  Emergent boundary question surfaced while finalizing the serving seam: the #276 honesty
  floor (entity-aware prober, PlaneDivergenceError refuse, verification-axis warnings) guards
  the OFFLINE/CLI path where active_mrr is computed (metrics/**). But the live-service + MCP
  path serves GENERIC query_rows/query_aggregate over the same v1 DataFrameCache, unguarded —
  so a secondary consumer issuing an MRR-equivalent aggregate over the stale v1 plane can be
  served a stale number the CLI refuses. Question: does closing that live/MCP gap on v1 violate
  the P6 freeze (no v1 investment), or is it a one-time floor-completion?
decision: >
  RATIFIED-BY-OPERATOR (2026-07-28): (c-i) HOLD P6 — do NOT invest in v1 to close the live/MCP
  aggregate gap. Log the live-service/MCP stale-aggregate residual as an EXTINCTION-URGENCY
  ACCELERANT feeding WS-C: the gap is answered by getting to v1 extinction faster (v2 cutover +
  S11 deletion), not by hardening v1. The v2 serving seam (F5-2 choke-point) closes it by
  construction at cutover.
consequences:
  - type: positive
    description: "Preserves P6 (v1 frozen, zero new investment; a v1 refusal is answered by re-baseline, never new v1 code). Avoids re-opening v1 hardening the epoch exists to end."
  - type: negative
    description: "Until cutover, a secondary live/MCP consumer issuing an MRR-equivalent aggregate over the stale v1 plane CAN be served a stale number the CLI would refuse (the gap is real, unguarded)."
    mitigation: "Logged as an extinction-urgency accelerant (WS-C): minimize the v1-live window; the v2 F5-2 choke-point closes the class by construction at cutover. Track live/MCP aggregate refusal-worthiness as an extinction-priority signal."
related_artifacts:
  - TDD-substrate-v2
  - CHARTER-substrate-v2-epoch-2026-07-27
  - DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27
tags: [substrate-v2, p6-boundary, v1-extinction, emergent, operator-ruled]
---

# DP-1F — v1 live-service/MCP path vs the P6 freeze boundary

> **Emergent operator decision-packet. status: RATIFIED-BY-OPERATOR (2026-07-28, in-dispatch
> pre-ruling).** Surfaced during Phase-3 finalize; the operator ruled in the same dispatch. Recorded
> here for the register; NOT re-asked.

## The deciding fact

`active_mrr` is computed **only** in the `metrics/**` offline/CLI path, which IS guarded by the #276
honesty floor (entity-aware prober, `PlaneDivergenceError` refuse, verification-axis warnings). But
the **live-service + MCP path** serves generic `query_rows` / `query_aggregate` over the SAME v1
`DataFrameCache` (`universal_strategy.py` → `DataFrameCache` → `storage.load_dataframe`), and that
path is **unguarded** (TDD premise P5/P6). So a secondary consumer issuing an MRR-equivalent
aggregate (e.g. sum of the offer value column over the active-classified sections) over the stale v1
plane can be served a stale number the CLI would refuse — the wound's shape, one consumer-surface over.

## The boundary question

Closing that live/MCP gap on v1 would require investing in v1 (a guard on the service/MCP read path)
— which the charter P6 freeze forbids ("no further v1 hardening; a v1 refusal is answered by an
operator re-baseline, never by new v1 code"). Is the live/MCP stale-aggregate gap:

- **(c-i) HOLD P6** — leave v1 frozen; the gap is answered by reaching v1 extinction faster (v2
  cutover + S11 deletion), not by hardening v1; the v2 F5-2 choke-point closes the class by
  construction at cutover; OR
- **(c-ii) one-time floor-completion** — treat the live/MCP guard as part of the #276 honesty floor
  (a completion of the floor, not new investment) and add it to v1.

## Operator ruling (2026-07-28, pre-ruled in-dispatch)

**RATIFIED as (c-i) HOLD P6.** Do NOT invest in v1 to close the live/MCP aggregate gap. **Log the
live-service/MCP stale-aggregate residual as an extinction-urgency accelerant** feeding WS-C
(v1-extinction): the correct answer to the gap is to get to v1 deletion faster, because the v2
serving seam (F5-2 typed choke-point + `Provable | Refused`) closes the class BY CONSTRUCTION at
cutover — every consumer, CLI and live/MCP alike, reads through the one gate. Hardening v1 would
re-open the investment the epoch exists to end (P6), and would be thrown away at S11.

## Residual — watch item (WS-C extinction urgency)

| Watch | Signal | Feeds |
|-------|--------|-------|
| Live/MCP stale-aggregate exposure | a secondary consumer issues an MRR-equivalent aggregate over the stale v1 plane and is served a number the CLI refuses | WS-C extinction-urgency: shorten the v1-live window; prioritize cutover + S11 |

The residual is BOUNDED by the v1-live window: it exists only until cutover (v2 serves all consumers)
and vanishes at S11 (v1 deleted). It is an accelerant on extinction urgency, not a new work item on
v1. No S5 dependency — the v2 serving seam already covers the live/MCP path by construction.

*Recorded by architect (10x-dev), S1 Phase-3 finalize, 2026-07-29. Operator pre-ruling 2026-07-28.*
