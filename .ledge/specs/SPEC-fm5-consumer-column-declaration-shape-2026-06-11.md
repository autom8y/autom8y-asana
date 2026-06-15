---
type: spec
status: proposed
title: "SPEC — FM-5 consumer-required-column declaration shape (the cross-repo round-trip input)"
date: 2026-06-11
initiative: g2-column-fidelity-contract (FPC Phase-3, CONSUMER axis / telos FM-5)
audience: autom8 monolith sre (the declaring side) + the FM-5 /frame (the ingesting side)
evidence_grade: MODERATE  # design-shape proposal; ratified by the operator ruling; PV at design-lock re-confirms
---

# The declaration shape — two layers, one truth

> Answering the operator's reciprocity question: *"Tell me the shape you want that declaration in."*
> The shape is **a consumer-owned JSON manifest (static seed, monolith repo) + a runtime
> `required_columns` request field (the authoritative wire contract)**. One truth, two carriers:
> the manifest seeds the canary + CI; the wire field makes the contract self-enforcing per request
> with zero cross-repo drift. This mirrors the proven SNC pattern (registry SSOT → gen.json →
> vendored copy + freshness guard), reversed in direction because the KNOWLEDGE owner here is the
> CONSUMER.

## Layer 1 — the static manifest (the seed; consumer-owned, producer-ingested)

**File**: `apis/asana_api/satellite/consumer_column_requirements.json` — committed in the
**MONOLITH** repo (the consumer owns its declaration; it goes stale only when the consumer's own
code changes, which is exactly when the consumer's CI can re-derive it). Vendored into
autom8y-asana at `src/autom8_asana/dataframes/contracts/consumer_column_requirements.vendored.json`
with a **freshness guard** (the `check_namespaces_gen.sh` pattern, reversed direction) so drift is
CI-loud, never silent.

**Schema (v1)**:
```json
{
  "schema_version": 1,
  "declared_by": "autom8-monolith",
  "declared_at": "2026-06-11",
  "consumers": [
    {
      "consumer_id": "business_offers.active_offers_frame",
      "code_anchor": "apis/asana_api/objects/project/models/business_offers/main.py:203",
      "query_shape": { "endpoint": "/v1/query/project/rows", "entity_type": "project" },
      "required_columns": ["offer_id"],
      "population_expectation": "nonnull_over_active_subset",
      "on_missing": "typed_incomplete"
    },
    {
      "consumer_id": "fetch_section_rows",
      "code_anchor": "<monolith #85 call site>",
      "query_shape": { "endpoint": "/v1/query/section/rows", "entity_type": "section" },
      "required_columns": ["project_gid"],
      "population_expectation": "present_all_rows",
      "on_missing": "typed_incomplete"
    }
  ]
}
```

Field semantics:
- `consumer_id` — stable, human-auditable; one entry per get_df CALL SITE class (not per column).
- `code_anchor` — file:line in the monolith; the sweep's receipt (SVR-style; staleness tolerated,
  the guard catches structural drift).
- `query_shape` — the CURRENT call shape (endpoint + entity_type as actually sent). NOTE: the FM-5
  design decides per-consumer whether the cure is widen-the-schema (PG-02 subset) or REBIND the
  consumer to the right entity_type (e.g. business_offers arguably wants `entity_type=offer` —
  that is SEAM-2 territory). The manifest declares what IS; the design rules what SHOULD BE.
- `required_columns` — non-key columns the consumer's code INDEXES (the sweep: every `_df["col"]` /
  `.loc[...,"col"]` on a get_df frame outside {office_phone, vertical, gid}).
- `population_expectation` — G-DENOM honesty: `present_any` (column exists) ·
  `present_all_rows` (no nulls) · `nonnull_over_active_subset` (the floor's denominator).
  Per-column granularity beats a blanket rule.
- `on_missing` — always `typed_incomplete` in v1 (mirrors the honest 503; never silent).

**Derivation (producer side, G-PROPAGATE)**: the FieldContract SSOT (`field_contract_maps.py`,
#114's home) ingests the vendored manifest → derives the per-query-shape REQUIRED-COLUMN SET
(union over consumers) → feeds (i) the EntityDescriptor schema-selection validation, (ii) the
coherence-canary column assertion (RED-by-construction until the schema-selection fix lands),
(iii) CI parity (a consumer entry whose column the shape cannot serve = build-time RED, not a
prod KeyError).

## Layer 2 — the wire field (the authoritative runtime contract; drift-free)

`/v1/query/*/rows` request body grows an optional `required_columns: [str]`. The monolith's
satellite bridge (`apis/asana_api/satellite/consumer.py` — ONE edit point, all callers inherit)
populates it from the same manifest. Producer behavior:
- All present+population-met → serve, and stamp the response metadata `column_manifest`
  (option e: served-columns + per-column population) so consumers can fail fast loudly.
- Any missing/unservable → **typed contract-incomplete signal** (the column analogue of
  `honest_contract_complete=False`), NEVER a silent narrow frame.
The wire field is authoritative at runtime; the static manifest is its seed + the canary/CI input.
A consumer that declares nothing gets today's behavior (additive, two-way door).

## Round-trip protocol
1. Monolith sre sweeps get_df callers → authors the manifest in the monolith repo (entries above
   as seed) → hands the file path + sha over the next cross-repo handoff.
2. autom8y-asana FM-5 frame ingests it: vendored copy + freshness guard + SSOT derivation.
3. Design-lock re-confirms RULING-1 (contract-driven subset) against the actual declared union.
4. The bridge `required_columns` wiring lands monolith-side AFTER our producer contract serves it
   (sequencing: producer first, so the wire field never hard-fails a live consumer).

## Out of scope here
The widen-vs-rebind ruling per consumer (design-lock, intersects SEAM-2); UK-2 floor calibration;
the monolith's alarm-coverage + zombie-schedule cleanups (monolith-owned).
