---
type: review
status: proposed
---

# DEFECT — delta path can persist rows=0 beside a live-GIDs gid_hash (empty-poison)

- Date: 2026-08-03 · Discovered by: qa-adversary (PR #299 review, F1 — constructed
  empirically against the real `_apply_section_delta` with a mocked client)
- Severity: MEDIUM (high impact × low likelihood; all ingredient events individually
  documented in this system's history)
- Class: PRE-EXISTING v1 delta-path defect (predates FIX-1; out of FIX-1's scope)

## Mechanism

`builders/freshness.py:_apply_section_delta` on a FULL-TURNOVER section
(STRUCTURE_CHANGED, all old tasks out, new tasks in) with EVERY added-task
`tasks.get_async` failing (429 burst): the merge yields 0 rows, yet
`new_gid_hash` is computed from the LIVE `current_gids` (freshness.py:535) and
the apply still returns True → persisted: parquet 0 rows, manifest `rows=0`,
`watermark=None`, `gid_hash=hash(live non-empty set)`. Subsequent warms probe
CLEAN against the poisoned hash while cache (empty) ≠ live (populated).

## Containment + routing

- **Contained for the stamp channel** by FIX-1's coherence clause (incoherent
  rows=0 never stamps → verification age climbs → detected — the pre-FIX-1
  detection channel is preserved for exactly this state).
- **Root fix** (apply-must-not-return-True on total fetch failure / hash-from-
  merged-not-live) is REAL v1 surgery beyond the floor-integrity law's "fixed
  small" bar → NOT fixed in v1. The class dies at S11 extinction with the delta
  path itself; v2's stage-validate-swap rebuild (RC-E, C16 fetch-completeness-
  by-construction) makes the state unconstructable.
- Watch: if a poisoned section is OBSERVED in prod pre-S11 (symptom: a rows=0
  section whose verification age climbs while its section shows tasks in Asana),
  the operator re-baseline (P6 standard answer) clears it.
