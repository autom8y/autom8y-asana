---
type: decision
status: proposed
id: ADR-honest-empty-200-serving
date: 2026-06-02
author: architect (10x-dev)
initiative: receiver-bulk-fanout-integration-readiness
consumer_visible: true
review_required_before_impl: true
supersedes: none
related:
  - ADR-build-gap-commission-pauseabusiness-2026-06-02
  - ADR-warm-set-reconcile-and-converge-2026-06-02
tdd: .sos/wip/thermia/TDD-receiver-warm-convergence-2026-06-02.md
---

# ADR — Honest-empty-200 serving semantics for legitimately-empty projects

## Status

PROPOSED. **CONSUMER-VISIBLE — requires review + consumer-coordination signoff before
implementation.** This is the load-bearing decision of the warm-convergence sprint.

## Context

A genuinely-empty project (build complete, zero Asana rows) currently 503s **forever**.
Source-verified mechanism (canonical `src/`, not a worktree):

- The builder gates the final merged-frame write on `if total_rows > 0:`
  (`src/autom8_asana/dataframes/builders/progressive.py:771` → `write_final_artifacts_async`
  at `:773-779`). An all-empty project builds an empty-but-schema'd frame in memory
  (`progressive.py:611`; also the no-sections early return at `:653-664`) but **never
  persists it**. This is *correct* — there is no data to merge.
- The read path maps the absent `dataframe.parquet` to a perpetual 503:
  `storage.load_dataframe` returns `None` on `NoSuchKey` (`storage.py:821-827`) → progressive
  tier cold-miss (`cache/dataframe/tiers/progressive.py:~134`) → `_build_on_miss` launches a
  background build and unconditionally raises `CACHE_BUILD_IN_PROGRESS`
  (`services/universal_strategy.py:1037-1040`). The rebuild re-yields `total_rows==0` → no
  persist → `df is None` again → **the 503 never clears**. Same trap in the decorator
  wait-timeout (`cache/dataframe/decorator.py:158-163`).

This is GENERAL: any zero-row project 503s forever (the original-crux EmptyFrame=26 class).
Live instance: CustomerHealth `1208848470341588` (6/6 sections complete, `total_rows=0`, every
section `gid_hash=e3b0c44298fc1c14` = SHA-256 of empty string, re-confirmed against Asana
2026-06-02 per the P0 spike).

The query endpoint intentionally re-raises rather than swallowing the build error —
`query.py:541`: *"NEVER a 500, NEVER a silent empty-200."* That invariant is correct and must
be preserved: honest-empty must be **attested**, not silent (a failed build must never
masquerade as empty).

## Decision

Serve a legitimately-empty project as **honest-empty-200**: a valid double-envelope, empty
`data` array, and a `meta` block carrying `honest_contract_complete: true`, a new additive
`honest_empty: true` signal, and the manifest freshness watermark. "Legitimately empty" =
the manifest is honest-complete (`is_honest_complete(manifest)`,
`section_persistence.py:251-270`) AND `total_rows==0`.

Two edits, both required:

1. **Persist a zero-row frame when honest-complete** (`progressive.py:771` + the `:653`
   cold-empty branch). Drop the `total_rows > 0` gate for the *final-artifact write only*
   (keep cascade-validation `:756` and hierarchy-warm `:740` gated — an empty frame has
   nothing to validate/warm). This makes the empty project a first-class cached artifact:
   `load_dataframe` returns an empty frame, the cold-miss/503 trap is never entered, and the
   freshness prober (gated on `manifest.is_complete()`, `progressive.py:350`) keeps stamping
   it. Primary fix — closes the defect at source for both the warmer and the request path.

2. **Honest-empty-200 read branch** at the miss-decision (`universal_strategy.py:821-839`) and
   the decorator wait-timeout (`decorator.py:158-163`): a `None`/empty that resolves to an
   honest-complete manifest is honest-empty, not build-in-progress. Closes the transient
   window (first request after manifest completes but before persist) and the
   manifest-complete-but-frame-missing state the affected GIDs are in TODAY.

The warm denominator INCLUDES empty projects (they are consumer-queried under cutover); do NOT
carve empties out of the coverage denominator — that re-introduces the FALSE-GREEN class (CF-4).

## Consumer coordination (the reason this ADR gates on review)

Source-verified against the live monolith (`/Users/tomtenuta/Code/autom8`): the change is
consumer-**improving**, not breaking, but consumer-**visible**.

- `refresh_frames._process_project` already treats an empty frame as a first-class non-error
  outcome (`if df.empty: LOG.warning(...)`, returns `(name, df)`) —
  `refresh_frames.py:72-74`.
- The satellite shim parses the 200 envelope via `bridge_response_to_df` and bridges
  `meta.honest_contract_complete` into `df.attrs` (`satellite/consumer.py:312-314,395-407`).
  An empty `data` array yields an empty DataFrame, no special-casing.
- The CURRENT 503 is the worse path: `CACHE_BUILD_IN_PROGRESS` retries ≤2× then raises
  `SatelliteClientError` → get_df **falls back** to the legacy in-monolith build
  (`consumer.py:68,332-334`). For a forever-503 empty project this wastes 2 retries + a
  fallback every bulk run. honest-empty-200 removes that waste.

**Pre-impl verification owed (NOT yet asserted):** confirm `bridge_response_to_df` does not
strict-reject the additive `meta.honest_empty` key. If it strict-validates `meta`, coordinate a
consumer-side bridge update first.

**Stale-comment flag (not load-bearing):** `consumer.py:65-66` claims the 503 has no HTTP
`Retry-After` header — now FALSE (`errors.py` Stage-1 F emits it). No action; documented so the
re-gate SLI is read correctly.

## Alternatives considered

1. **Status quo (perpetual 503).** Rejected: guaranteed cold-503 for every empty project under
   cutover; the consumer wastes retries+fallback; violates WS-2 AC-3.
2. **Read-branch fix only (no persist).** Map `None`+honest-complete-manifest → empty-200 at the
   serve layer, never persist a zero-row frame. Advantage: no new S3 artifact shape (pure
   two-way door). Disadvantage: every request re-derives "is this honest-empty?" from the
   manifest on a cache miss, and the warmer still sees `df is None` (coverage accounting needs a
   manifest-aware special case in two places). Rejected as *sole* fix because it leaves the
   warmer/coverage path reasoning about absence; kept as edit-2 belt-and-braces for the
   transient window.
3. **Persist-only (no read branch).** Persist the zero-row frame; rely on the normal hit path.
   Advantage: simplest steady state. Disadvantage: does not cover the transient window (manifest
   complete, frame not yet persisted) nor the legacy manifest-complete-but-frameless state the 3
   GIDs are in now → those still 503 until a rebuild persists. Rejected as *sole* fix.
4. **Sentinel marker object in S3** (e.g., an `empty.marker` instead of a parquet). Rejected:
   adds a new artifact type the read path must learn; a zero-row parquet is already a valid frame
   the read path handles unchanged — less surface, same outcome.

**Selected: 1+2 combined** (persist zero-row frame AS edit 1 + honest-empty read branch AS edit
2). Each alternative is a genuinely different locus (serve-layer vs persist-layer vs marker), not
a strawman; the combination is chosen because edit 1 fixes the steady state and edit 2 fixes the
transient + legacy state, and together they keep coverage accounting honest.

## Consequences

- Empty projects serve correctly (200 + empty data + attested meta); the consumer gets the right
  empty frame on the first call.
- A new persisted artifact shape (zero-row `dataframe.parquet`) — forward-compatible with the
  read path, but a soft one-way door (the warmer/coverage math now assumes empties exist).
- `meta.honest_empty` is a new additive response field — additive, but consumer-visible; covered
  by the coordination signoff.
- The "NEVER a silent empty-200" invariant is preserved: honest-empty is gated on
  `is_honest_complete(manifest)`, so a failed/incomplete build still 503s.

## Reversibility

Two-way door at the response layer (status code + meta flag are revertible). Soft one-way door at
the persist layer (zero-row parquets, once written, are assumed-present by coverage math). The
consumer-coordination signoff covers the persisted-state commitment.
