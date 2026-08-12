---
type: review
artifact_type: DEFECT
initiative: substrate-v2-epoch
wave: S8-2 (P5 live-parity window)
date: 2026-08-12
status: accepted
lifecycle_note: root-caused; cure in PR #351 (this branch)
severity: HIGH (observability plane) — serve path unaffected
consumes:
  - .sos/wip/parity/receipts/2026-08-11 + 2026-08-12 (prov blocks: completeness 0.0 / evaluated 0 / expected 1)
  - sweep_r4 stdout:99505 (substrate_provability_indeterminate_check traceback)
  - src/autom8_asana/substrate/prov_sweep.py:73 (pre-fix)
  - scratchpad wu4r2/proof_e_prov_digest.py (two-sided offline proof, PROOF_E_RESULT=PASS)
---

# DEFECT — PROV evaluator digest re-derivation dies on bare schema inference

## Symptom (the HANDOFF-s8-parity-2026-08-11 watch item, converted to a finding)

Every in-run PROV block since the first v2 publish read `completeness 0.0 /
evaluated_count 0 / expected_count 1 / expected_set_mismatch_count 0`. The addendum's
"first-publish evaluator-vs-swap ordering" hypothesis is FALSIFIED: cycle 2 (2026-08-12
09:56Z, served penny-exact) evaluated 0 with cycle 1's artifact a day old in the store.

## Root cause (reproduced, then proven against the live artifact)

`digest_of_canonical_frame_bytes` (prov_sweep.py:73 pre-fix) reconstructed the FULL
stored frame with bare `pl.DataFrame(rows)` schema inference. The live offer artifact
carries `trackstat_id` null in 4,181/4,191 rows: polars' default 100-row inference
prefix infers Null dtype, then the first real value (`"BETTER25CTWA"`, a str) raises
`ComputeError: could not append value` — the EXACT construction class #313 cured in the
rebuild path (`safe_dataframe_construct`), missed in the evaluator path. The evaluator
correctly recorded an [H20] indeterminate skip (loud, never false-green) — but that
left the RC-F scheduled evaluator blind to the ONE artifact v2 publishes: PROV-1
(unprovable) and the [H19] CORRUPT-catching re-derivation were non-functional for it.

Why it hid: the `substrate_provability_indeterminate_check` warning goes to structlog
JSON on STDOUT (line 99505 of the 23MB sweep capture), not stderr.

## Two-sided honesty of the alarm channel (verified live)

- The evaluator NEVER lied: 0.0 completeness was emitted truthfully on every run.
- PROV-3-incomplete FIRED on the 09:58Z datapoint (ALARM observed 10:0xZ; period 900s,
  Minimum < 100). It reads OK between sweeps only because `treat_missing_data =
  notBreaching` releases it when the sparse in-process cadence emits nothing — the qa
  F-2 adjacency, carried to PT-03: the alarm cannot HOLD state between sweeps.

## Cure (this PR)

Reconstruct ONLY the digest-pinned `_VALUE_COLUMNS`: `canonical_digest` consumes
nothing else, full-scan inference over columns serialized from a typed frame is safe
(type-homogeneous), and the digest's type-erasure pin (freshness F4) makes numeric
dtype detail irrelevant. Rows missing a pinned column refuse loudly (partial/foreign
artifact — [H20] skip semantics preserved). Rejected alternative: reconstructing with
`safe_dataframe_construct(rows, OFFER_SCHEMA)` fails on the JSON round-trip's
stringified dates (`"2025-11-26"`) — proven, not assumed.

## Proof

1. **Offline two-sided vs the LIVE artifact** (S3 read only — zero Asana touch, zero
   budget charge): old path reproduces the ComputeError; cure re-derives
   `sha256:58345ed7…` == `proof.content_digest` byte-exact; `is_provable → PROVABLE`.
2. **Discriminating tests**: the two new wound-shape tests (function-level round-trip +
   whole-evaluator-loop completeness-100) FAIL against the pre-fix code, PASS on the fix
   (verified both directions via stash).

## Residuals

- The NEXT sweep must read `completeness 100 / evaluated 1 / unprovable 0` — the live
  clear receipt for this defect (window cycle 3, or a dedicated verification sweep).
- PT-03 disclosure: cycles 1 and 2 banked with the evaluator blind; parity legs and
  serve-path proofs are unaffected (digest match was verified in-leg by build_parity_outbound,
  not by the evaluator).
- F-2 adjacency (alarm cannot hold between sparse in-process sweeps) rides to PT-03 as
  already ledgered; the post-window EventBridge schedule (G2 option-b) is its cure.
