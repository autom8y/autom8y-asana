---
type: decision
subtype: adr
artifact_id: ADR-fm5-armb-contract-locus
title: "FM-5 ARM-B — consumer-required-column contract LOCUS (FORK-A) + sibling-signal shape"
created_at: "2026-06-26T00:00:00Z"
author: architect
status: accepted
context: "FM-5 ARM-B must turn a requested-but-absent REQUIRED column on /v1/query into a TYPED contract-incomplete signal (never a silent drop / daily KeyError / $0-7-row fossil). Resolving FORK-A (WHERE the consumer-required-column declaration lives and is enforced) and the signal shape is the design-lock the implementation builds against; the LOCUS was correctly declined by Pythia and is the architect's call."
decision: "Adopt O3 (two-layer: vendored consumer manifest seeds CI+canary, optional /v1/query required_columns wire field is the authoritative runtime contract, field_contract_maps.py is the SOLE derivation/propagation point). Emit the typed signal as a DISTINCT sibling meta field contract_complete co-derived at the ONE gate (engine.py:247-266), NOT by mutating honest_contract_complete. Derive completeness from SCHEMA membership (schema.column_names()), NEVER a physical-parquet presence check."
consequences:
  - type: positive
    description: "Consumer-declared completeness check is added to the no-select/default-projection path, which today silently drops (UnknownFieldError fires only on explicit-select). The genuine silent-drop gap is closed."
  - type: positive
    description: "Deriving from schema.column_names() (not df.columns) makes the signal immune to the 100%-NULL offer_id present in the production project parquet — a presence check would mis-read contract-COMPLETE."
  - type: positive
    description: "field_contract_maps.py is the single propagation point (G-PROPAGATE); no per-consumer orphan contract engine (C2 derive/delegate-never-replicate honored)."
  - type: negative
    description: "GLINT L1-2 says 'honest_contract_complete carries column-completeness'. We graft AT the one gate but emit a DISTINCT field, reading L1-2 as a location/no-sibling-PATH constraint, not a field-identity mandate. The rite-disjoint S4 critic must confirm this reconciliation."
    mitigation: "Mutating honest_contract_complete would route a STRUCTURAL column gap into 503/retry semantics (models.py:443-446) — a retry-forever conflation. The distinct field is the only shape that avoids it; documented in TDD §4.2 for the S4 critic."
  - type: neutral
    description: "Door-C projection widening (project_gid on section) is designed but its APPLICATION is deferred to SEAM-2 (operator-held), gated on premise-validation + the monolith manifest hand-back. offer_id on project is intentionally NOT widened so ARM-B fires a permanent loud signal driving the SEAM-2 rebind."
related_artifacts:
  - TDD-fm5-armb-honest-refusal-contract
  - SPEC-fm5-consumer-column-declaration-shape-2026-06-11
  - OPERATOR-RULING-fm5-scope-and-sequencing-2026-06-11
tags:
  - contract
  - query-engine
  - honest-refusal
  - fm5
  - arm-b
schema_version: "1.0"
---

## Context

receiver-contract-realization S3 design-lock. ARM-B must make a requested-but-absent
REQUIRED column on `/v1/query/*/rows` return a TYPED contract-incomplete signal — never
a silent drop, a daily KeyError, or the live $8,775 / 7-row BusinessOffers fossil. The
S2 premise (live, SUCCEEDED) confirmed `offer_id` is **ABSENT-at-serve** on the project
entity (not in the 16-column `PROJECT_SCHEMA`) while being **PRESENT_BUT_NULL-at-storage**
(0/1380 non-null in the 24-column production parquet). FORK-A — *where the consumer-required-
column declaration lives and is enforced* — and the signal shape are this ADR's subject.

Requirements substrate (no separate PRD artifact; bespoke procession): the operator ruling
(`OPERATOR-RULING-fm5-scope-and-sequencing-2026-06-11.md`), the ratified two-layer SPEC
(`SPEC-fm5-consumer-column-declaration-shape-2026-06-11.md`), and the telos
(`.know/telos/fm5-column-fidelity.md`).

## Decision

### D1 — FORK-A LOCUS: O3 (two-layer), runtime enforcement at the ONE gate

Enumerated slate (option-enumeration-discipline; the dispatched O1/O2/O3 was a truncated
slate — O4/O5/O6 added by self-audit):

| Opt | Mechanism | Verdict |
|-----|-----------|---------|
| O1 | Consumer-side replicated declare+check (each consumer re-implements the column check) | REJECT — replicates contract logic across consumers; violates C2 (derive/delegate-never-replicate). |
| O2 | `/v1/query` endpoint-only enforcement; ad-hoc `required_columns` on the wire, no manifest/SSOT | PARTIAL — gives the runtime typed signal but has NO build-time CI parity (a non-servable consumer column is caught only at runtime), NO canary seed, NO auditable declaration of record. |
| O3 | **Two-layer**: vendored manifest DECLARES (seed for CI + canary) → `field_contract_maps.py` SSOT DERIVES the per-query-shape required set → optional `/v1/query` `required_columns` wire field is the authoritative runtime contract → typed sibling meta signal | **ADOPT** — union of O2's runtime enforcement + a consumer-owned declaration of record + build-time CI parity (build-time RED, not prod KeyError) + the two-sided canary seed. |
| O4 (null) | Do nothing — status quo (silent narrow frame on no-select; generic UnknownFieldError only on explicit-select) | REJECT — fails the telos; the no-select path stays a silent $0 fossil. Baseline the others must beat. |
| O5 (inversion) | Server-declared required columns via `EntityDescriptor.key_columns` only — no consumer manifest | REJECT — required-ness is **consumer-relative**, not entity-intrinsic. `offer_id` is a key column of the OFFER entity (`entity_registry.py:527`), NOT the PROJECT entity; a server-only scheme would never flag `offer_id`-required-on-project — it misses the exact gap FM-5 exists to make loud. Confirms the consumer-owned declaration direction is load-bearing. |
| O6 (existing substrate) | Repurpose existing explicit-`select` + `UnknownFieldError` (`engine.py:204-218`) as the contract | REJECT — covers ONLY the explicit-select path; the genuine silent drop is the **no-select/default-projection** path. UnknownFieldError is a generic field-vs-schema 4xx; it cannot carry `population_expectation`, seed CI parity, or seed the canary. Strictly weaker; enumerating it sharpens why O3's declaration layer earns its complexity. |

**O3 survives the fuller slate.** O5 proves consumer knowledge is load-bearing (server cannot
self-derive `offer_id`-on-project); O6 proves the no-select-path + build-time-gate + canary-seed
gaps justify the manifest layer over a bare wire field.

### D2 — Signal shape: DISTINCT sibling meta field, co-derived at the ONE gate

The typed signal is a NEW `RowsMeta` field `contract_complete: bool` (+ `unservable_required_columns:
list[str]`, + `column_manifest`), co-derived at the ONE gate (`engine.py:247-266`, adjacent to
`honest_contract_complete`) and fed by the `field_contract_maps.py` SSOT. It is **NOT** a mutation
of `honest_contract_complete`.

Reconciliation with GLINT L1-2 ("honest_contract_complete carries column-completeness — the
One-Gate graft, NOT a sibling signal path"): we read L1-2 as a **location / no-parallel-path**
constraint (derive at the one gate, SSOT-fed, no separate endpoint or control-flow branch), not a
field-identity mandate. Mutating `honest_contract_complete` would route a STRUCTURAL column gap
into the section-completeness 503/retry semantics documented at `models.py:443-446`
("`honest_contract_complete=False -> 503`") — a retry-forever conflation (a missing schema column
is never fixed by retrying). The distinct field is the only shape that grafts at the one gate
without that collision. **This is the single decision the S4 rite-disjoint critic must confirm.**

### D3 — Completeness derives from SCHEMA, never the parquet

Completeness = `required_column ∈ schema.column_names()` (the 16-col served contract), NOT
`required_column ∈ df.columns`. The production project parquet carries a 100%-NULL `offer_id`
column that a physical-presence check would mis-read as contract-COMPLETE. Three-state model
PRESENT / PRESENT_BUT_NULL / ABSENT, governed at the **serve boundary** (schema). Population
(non-null) is surfaced as data-derived `column_manifest` metadata (belt-and-braces, SPEC option e),
NOT the blocking gate.

### D4 — RULING-1 re-confirm: contract-driven SUBSET

Re-confirmed against the actual declared union (the SPEC seed = 2 instances: `offer_id` on project,
`project_gid` on section). Required set = the declared union, NOT eager 30-column PG-02 parity.
Expand only as a consumer declares. The monolith manifest hand-back (DEFER, telos-pending) will
finalize the union; the freshness guard makes any drift CI-loud.

### D5 — Widen-vs-rebind DATA-CURE: deferred to SEAM-2 (operator-held)

- `offer_id` on project: widen is USELESS (100% NULL) → schema stays unwidened → ARM-B fires a
  **permanent loud typed-incomplete**, which is the correct signal driving the SEAM-2 rebind of
  `business_offers` onto `entity_type=offer` (where `offer_id` is 26.7% populated).
- `project_gid` on section: widen is potentially useful but **premise-unvalidated** (S2 validated
  only `offer_id`; no constant-injection source token exists for a section's project_gid today).
  Designed (TDD §6.2) and receiver-owned (C2/W1), but APPLICATION is SEAM-2 operator-held, gated on
  premise-validation + the manifest hand-back.

This is an OPERATOR-NOTE, not a now-blocker: ARM-B is cure-neutral and builds regardless.

## Consequences

See frontmatter. Net: the build is strictly-additive (only `field_contract_maps.py`, a new vendored
JSON, additive `RowsRequest`/`RowsMeta` fields, and an additive graft at the one gate are touched;
the `resolution/gfr/` spine is untouched). The one decision carrying residual risk is D2's GLINT
L1-2 reconciliation, explicitly routed to the S4 critic.
