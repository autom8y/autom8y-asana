---
type: decision
subtype: adr
status: accepted
title: "ADR — FM-5 ARM-B: consumer-required-column contract LOCUS, the One-Gate sibling-field signal, and the Door-C widen-vs-rebind ruling"
date: 2026-06-26
rite: 10x-dev
station: S3 design-lock (architect)
initiative: receiver-contract-realization / fm5-column-fidelity
code_truth_anchor: origin/main b9648de494115063161cd1e019ec1a931c05d725
self_assessment_ceiling: MODERATE  # STRONG + the canary RUN belong to the S4 rite-disjoint review critic
supersedes_fork: FORK-A (shape §3) — Pythia correctly REFUSED to author the LOCUS; routed to architect
inputs:
  - .ledge/specs/SPEC-fm5-consumer-column-declaration-shape-2026-06-11.md   # the ratified two-layer shape
  - .know/telos/fm5-column-fidelity.md                                      # Gate-A predicate; RULING-1 OPERATOR-HELD
  - .ledge/decisions/ORDERING-PIN-114-before-fm5-design-lock-2026-06-11.md  # E1 — SSOT home gate (now satisfied)
  - .claude/agent-memory/architect/project_fm5_offer_id_serve_premise.md    # S2 PREMISE receipt (offer_id NOT served by project frame)
  - .sos/wip/frames/receiver-contract-realization.shape.md                  # S2-S5, FORK-A, FORK-B, the ARM-AB canary gate
---

# ADR — FM-5 ARM-B: required-column contract LOCUS + One-Gate signal + Door-C ruling

## Status

Accepted (design-lock). Self-grade **MODERATE** (builder-altitude ceiling). The STRONG
attestation and the two-sided canary RUN are the S4/S9 rite-disjoint review critic's, never
this builder's.

## Context

`/v1/query/*/rows` is **column-blind by documented shortcut, not defect**. The S-07 minimal
project schema serves 16 columns and the PG-02 full-parity widen is deferred:

- `src/autom8_asana/dataframes/schemas/project.py:46-54` — `PROJECT_SCHEMA = BASE_COLUMNS (13) + [status, office_phone, vertical]`, `version="1.1.0"`. **`offer_id` ABSENT.**
- `src/autom8_asana/dataframes/schemas/base.py:12` — `BASE_COLUMNS` (13, `gid`..`parent_gid`).
- `src/autom8_asana/core/entity_registry.py` project descriptor `default_projection` = the same 16; PG-02 deferral inscribed in `schemas/project.py:5-7` ("Full column-parity (30+ columns) is PG-02, deferred to Sprint 2").

The S2 premise (verified LIVE, S3 account, both arms ran) confirmed the **serve boundary is
schema-governed, not parquet-governed**: a consumer that explicit-`select`s `offer_id` gets a
typed `UnknownFieldError` (`src/autom8_asana/query/engine.py:213-218`); a consumer that omits
`select` gets the 16-col `default_projection` and `offer_id` is **silently never selected**
(`engine.py:209-210, 235-237`). The production project parquet carries a 24-col **superset incl.
a 100%-NULL `offer_id` (0/1380)**; the populated `offer_id` (26.7%) lives only on the **offer**
frame (`entity_registry.py:511-531`, `key_columns=("office_phone","vertical","offer_id")` at
`:527`, same `primary_project_gid="1143843662099250"` at `:517`). Premise receipt:
`.claude/agent-memory/architect/project_fm5_offer_id_serve_premise.md`.

The harm: on fleet re-enable, a monolith consumer indexing a never-selected column gets a silent
null or a daily prod `KeyError` instead of a typed refusal — the live **$8,775 / $0 / 7-row
BusinessOffers fossil**. FM-5 ARM-B converts a requested-but-absent **required** column into a
**TYPED contract-incomplete signal** — never a silent drop, a `KeyError`, or a fossil.

The SSOT home now exists on main (E1 satisfied, #114 merged at `b9648de4`):
`src/autom8_asana/dataframes/contracts/field_contract_maps.py` (96 lines). Its docstring scopes
the consumer-manifest work to this file: *"the full `FieldContract` dataclass/registry,
schema-FROM-model derivation, and the in-repo generator are explicitly Phase-3 work and are NOT
built here."* FM-5 IS that Phase-3 consumer-manifest slice, built INTO this SSOT as the **sole
propagation point** (G-PROPAGATE).

This ADR locks three coupled decisions: **D1** the contract LOCUS (FORK-A), **D2** the typed
signal shape (the One-Gate graft), **D3** the Door-C widen-vs-rebind ruling. It also re-confirms
**RULING-1** and surfaces the **OPERATOR-SURFACE** sovereign sub-decision.

---

## Decision D1 — Contract LOCUS = O3 two-layer (vendored manifest DECLARES → SSOT DERIVES → wire field ENFORCES)

The consumer-required-column declaration lives in **two coherent carriers, one truth**: a
consumer-owned static manifest vendored into this repo with a freshness guard (Layer-1, the seed
for canary + CI), and an authoritative runtime `required_columns` request field (Layer-2, the
drift-free wire contract). The producer derives the per-query-shape required-column SET from the
SSOT (`field_contract_maps.py`) and enforces it at the One-Gate. This is the SPEC's ratified shape.

### Alternatives Considered (FORK-A)

#### Option O1 — Consumer-side declare + check (each consumer re-implements the column check)
- Pros: zero producer change; consumer has full local context; fastest to ship for a *single*
  consumer; no cross-repo round-trip.
- Cons: replicates contract logic per consumer (N consumers → N divergent checks) — violates **C2
  (derive/delegate-never-replicate)**; each rolled check tends to read raw frame columns, so every
  consumer independently re-acquires the **premise-implication-#1 null-trap** (a 100%-NULL
  `offer_id` column reads as "present"); no central typed signal.

#### Option O2 — Endpoint-side declare + enforce, wire-only (no static manifest / no SSOT seed)
- Pros: centralized enforcement (one implementation at the authoritative serve boundary); typed
  signal; no per-consumer replication.
- Cons: the required-column set exists **only on the wire** — invisible to producer tests until a
  live request arrives; **no build-time CI parity** (a consumer column the shape cannot serve is
  caught at RUNTIME, never at build → the prod-`KeyError` failure mode the initiative exists to
  kill); no canary seed; no freshness guard against silent consumer drift.

#### Option O3 — Two-layer (vendored manifest → SSOT derivation → wire field) **[SELECTED]**
- Pros: consumer declares (O1's expressiveness) **without** replicating the check (honors C2);
  endpoint enforces centrally (O2's strength); the static manifest **seeds** the two-sided canary,
  the CI parity (a declared-but-unservable+unruled column is a **build-time RED, not a prod
  KeyError**), and a freshness guard; rides the #114 FieldContract SSOT as the single propagation
  point; the wire field is authoritative at runtime (drift-free). Mirrors the proven SNC
  registry→gen.json→vendored-copy+freshness pattern, reversed because the KNOWLEDGE owner is the
  CONSUMER.
- Cons: a cross-repo round-trip (monolith authors the manifest; receiver vendors it) plus
  freshness-guard machinery; two carriers to keep coherent; more upfront build than O1/O2.

### Rationale
O1 and O2 are each a strict subset of O3's value and each forfeits a load-bearing property: O1
forfeits centralization and re-spreads the null-trap; O2 forfeits build-time parity (the exact
silent→typed conversion is the initiative's telos). O3 is the only option that delivers the
**build-time RED instead of prod KeyError** guarantee while honoring C2 and riding the SSOT.

---

## Decision D2 — Typed signal = a SIBLING FIELD at the One-Gate SITE, NOT a mutation of `honest_contract_complete`, NOT a sibling path

The column-contract signal is grafted at the **One-Gate SITE** (`engine.py:247-255`, the
`honest_contract_complete` derivation block) as a **sibling typed field** — distinct from the
section-completeness boolean — exposed on `RowsMeta` as `required_columns_complete: bool` (default
`True`) + `missing_required_columns: list[str]` (default empty). It is the *column analogue* of
`honest_contract_complete=False`, computed at the same site, behind an `if request.required_columns
is not None` guard (additive, two-way door).

### Alternatives Considered

#### Option D2-A — Fold column-completeness INTO `honest_contract_complete` (set the existing boolean False)
- Pros: literally one boolean; maximal "One-Gate" reading.
- Cons: **SEMANTIC COLLISION (load-bearing reject).** `engine.py`'s existing field maps to
  transient-retry: `src/autom8_asana/query/models.py:446` — *"(honest_contract_complete=False ->
  503)"*, i.e. "still-building / FAILED sections, retry." A **permanent** column gap (`offer_id`
  will *never* appear on the project arm) folded into that boolean would be read by every existing
  consumer as a transient build-in-progress → infinite retry on an unfixable gap. Corrupts live
  retry logic. **REJECT.**

#### Option D2-B — Sibling FIELD at the One-Gate SITE (distinct boolean + named columns) **[SELECTED]**
- Pros: the One-Gate **SITE** is preserved — one place in the code decides contract-honesty
  (section AND column dimensions derived together at `:247-255`); the column dimension is typed and
  *names* the gap; semantically distinct from the 503-mapped section boolean (no retry corruption);
  additive (default `True` + empty when undeclared).
- Cons: two attestation booleans on `RowsMeta` instead of one — marginally more surface (already the
  established pattern: `stale_served`, `honest_contract_complete`, `honest_empty` are all additive
  meta attestations at `models.py:417/432/451`).

#### Option D2-C — Sibling SIGNAL PATH (separate derivation far from the One-Gate, or a 4xx error envelope)
- Pros: total isolation from the section logic.
- Cons: a second derivation site = two places decide contract-honesty → violates One-Gate and **C2
  (replicate)** — this is exactly the *"sibling signal path"* the dispatch forbids. A 4xx envelope
  would **hard-fail every live `business_offers` call** the moment the monolith wires
  `required_columns=["offer_id"]`, breaking producer-first sequencing (SPEC round-trip step 4) and
  the E3 rider. **REJECT.**

### Rationale
"One-Gate, not a sibling path" is a constraint on the **SITE** (one place decides), not on the
**field count**. D2-B keeps the SITE singular while keeping the *semantics* of a permanent column
gap separate from a transient section gap — the only shape that is simultaneously One-Gate-faithful,
retry-safe, and additive. A 200-with-typed-meta is strictly louder than today's silent drop (the
meta now carries a typed, named marker the consumer branches on — e.g. the monolith's existing
`OfferIdAbsent` emitter) while never forcing a producer-side hard outage.

---

## Decision D3 — Door-C ruling: contract-driven subset, widen-vs-rebind PER CONSUMER

Against the **actual declared union** from the SPEC §Layer-1 manifest seed —
`{offer_id (project shape), project_gid (section shape)}` — the Door-C disposition is recorded in
the SSOT as a small, auditable table. FM-5 widens **nothing eagerly**.

| Consumer (declared) | Shape | Column | Disposition | Reasoning |
|---|---|---|---|---|
| `business_offers.active_offers_frame` | `project` | `offer_id` | **REBIND → SEAM-2 (do NOT widen)** | `offer_id` is structurally **100%-NULL on the project frame** (0/1380, premise receipt) vs **26.7% on the offer frame**. Widening project to serve it yields a dead-weight column and a FALSE "servable" signal (premise implication #1). The populated data lives on `entity_type=offer` (`entity_registry.py:511-531`). The cure is a consumer **rebind** (SEAM-2 / S6). FM-5's deliverable here is the **typed refusal** — which IS the E3 precondition that makes the rebind safe (a rebound consumer missing `offer_id` gets a typed refusal, not a `KeyError`). |
| `fetch_section_rows` | `section` | `project_gid` | **WIDEN (receiver-owned, separable/in-scope-optional)** | `project_gid` is in **no schema** (`grep` across `schemas/` returns zero) yet is **known at query time** — the query is project-scoped (`RowsRequest.project_gid`, `models.py:322`). Populating it is a **context-copy** (present_all_rows, 100%), not a data-fetch. Receiver owns this widen (C2). NOT on the keystone-canary critical path (the GREEN arm uses an already-served column). |

### Alternatives Considered

#### Option D3-A — Eager 30-column PG-02 parity (widen project to full parity)
- Pros: every conceivable consumer column is servable at once.
- Cons: violates **RULING-1** (over-serves far beyond the declared union); re-introduces the
  premise's dead-weight-null risk at 30× scale; couples FM-5 to the deferred PG-02 work. **REJECT.**

#### Option D3-B — Widen project to serve `offer_id`
- Pros: `required_columns=["offer_id"]` would pass a naive servability check.
- Cons: serves a structurally-100%-NULL column → the consumer gets dead weight and a **false
  contract-COMPLETE** signal (the exact premise-implication-#1 trap); the real cure (rebind to the
  26.7%-populated offer frame) is forgone. **REJECT.**

#### Option D3-C — Contract-driven subset `{offer_id→REBIND-SEAM2, project_gid→WIDEN-receiver}` **[SELECTED]**
- Pros: honors RULING-1 (only the declared union, no eager parity); routes each column to its
  *correct* cure (rebind where the data lives populated; cheap receiver widen where the data is free
  from query context); makes the Door-C decision **executable** (the CI parity check reds on any
  declared column that is neither servable nor ruled).
- Cons: `offer_id`'s economics cure is deferred to SEAM-2 (acceptable — FM-5 is explicitly a
  *precondition* for SEAM-2, telos riders).

### RULING-1 RE-CONFIRM (operator-held, telos Gate)
RULING-1 (contract-driven subset, **NOT** eager 30-column parity) **HOLDS** against the actual
declared union `{offer_id, project_gid}`. FM-5 serves the typed-refusal contract for exactly these
two declared columns; it does not widen toward PG-02 parity. Stated explicitly per the telos gate
(`.know/telos/fm5-column-fidelity.md` §Gates 1).

---

## OPERATOR-SURFACE — sovereign sub-decision (surfaced, not silently absorbed)

Per the FORK-A refusal's escalation flag and `.know/telos/fm5-column-fidelity.md`
(design-lock OPERATOR-HELD): the choice **widen `entity_type=project` to serve `offer_id`** vs
**rebind `business_offers` to `entity_type=offer`** is a sovereign decision. This ADR **recommends
REBIND** (D3, REJECT D3-B) on premise evidence (100%-NULL vs 26.7%-populated). The SPEC already
locates the rebind in **SEAM-2 territory** (§Out-of-scope). **Operator ratification requested at
design-lock**; if the operator overrides to WIDEN, D3-B's dead-weight-null consequence and the
population dimension (below) become load-bearing and the canary's GREEN arm must move to a
population assertion.

## Consequences

### Positive
- A requested-but-absent required column returns a **typed, named** contract-incomplete signal
  (`required_columns_complete=False`, `missing_required_columns=[...]`) — never silent, never a
  `KeyError`, never a fossil. The monolith's existing `OfferIdAbsent` emitter consumes it.
- The signal is **retry-safe** (distinct from the 503-mapped section boolean) and **additive**
  (undeclared consumers see byte-identical behavior — two-way door).
- The contract is **build-time enforced** (CI parity: declared-but-unservable+unruled → RED).
- E3 precondition for SEAM-2 is satisfied: a rebound consumer missing `offer_id` gets a typed
  refusal, not a `KeyError`.

### Negative
- A cross-repo round-trip (monolith authors the manifest; receiver vendors it) and a freshness
  guard must be maintained. The vendored manifest can go stale — the guard makes that CI-loud.
- `offer_id` economics remain $0 on the project arm until SEAM-2 rebind lands (by design — FM-5 is
  the precondition, not the cure).

### Neutral
- Two attestation booleans now exist on `RowsMeta` (section + column dimensions of contract honesty).
- Population-dimension enforcement (`population_expectation`) is **designed but deferred** to a
  fast-follow; v1 enforces **servability** (schema + materialization), which is the deterministic,
  null-trap-immune discriminator for the declared union.

## Reversibility Assessment
- **D1 (LOCUS), D2 (sibling field), D3 (rulings)**: **two-way doors.** The request/response fields
  are additive and optional; the manifest is data; the Door-C table is a small mapping. Reverting =
  delete the optional fields + the derivation (no consumer is forced to depend on them).
- **WIDEN of `project_gid` into the section schema**: **near-two-way** (a schema `version` bump; a
  removed column is a contract narrowing — coordinate via the freshness guard). Separable from the
  keystone.
- **REBIND of `business_offers` (SEAM-2)**: out of scope here; a SEAM-2 one-way-ish consumer change.

## ADRs / specs referenced
- SPEC-fm5-consumer-column-declaration-shape-2026-06-11 (the two-layer shape this locks).
- ADR-S4-001 (model-codegen is a one-way door — **FORBIDDEN**; FM-5 uses the WARN-first drift gate).
- TDD-fm5-armb-typed-contract-incomplete-2026-06-26 (the build surface deriving from this ADR).
